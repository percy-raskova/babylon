//! The health of the whole national economy, read period by period from the engine's own state
//! and receipts: supply to the households of every county and foreign region, jobs, businesses,
//! products, trade and money. Nothing here is a model of them. Every figure is a sum (a share is
//! computed from two sums, in basis points, never averaged) and money is millionths.
use super::country_bench::BenchError;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_material_circuit::{
    AccountId, AdjustmentReceipt, CapacitySupply, CircuitAccounting, CommodityKind, CorridorId,
    FinalDemandPrincipalId, GoodId, LaborCompensation, MarketClearingReceipt, MaterialCatalog,
    MaterialCircuitState, MonetaryCircuit, OrderId, OutboundOrderId, PoolMembers,
    PublicProgramReceipt, PublicTransferTreatment, RestartTest, RouteId, SiteId,
    StaffingMemberState, StaffingPoolId, StaffingState, StopHold, UnitId,
};
use babylon_persistence::economic_catalog::{
    EconomicCatalogError, EconomicOpening, RecipeTemplate,
};
use babylon_tick::material_world::MaterialTickReceipts;
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, BTreeSet};

type Key = (GoodId, UnitId);

/// The six needs of a household, by commodity key.
pub const NEEDS: [&str; 6] = [
    "food",
    "materials",
    "utility",
    "housing",
    "household_services",
    "public_provision",
];

/// The four counties named by the task; the other two panel counties are picked by rule.
const FIXED_PANEL: [(&str, &str); 4] = [
    ("Wayne MI", "26163"),
    ("Cook IL", "17031"),
    ("Los Angeles CA", "06037"),
    ("Harris TX", "48201"),
];

#[derive(Clone, Debug)]
struct SiteFacts {
    function: String,
    scope: &'static str,
    location: String,
}

/// A designed process: what one batch takes and makes.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct Recipe {
    output: Key,
    output_units: u64,
    labor_hours: u64,
    inputs: Vec<(Key, u64)>,
}

/// One county of the fixed panel and why it is there.
#[derive(Clone, Debug)]
pub struct PanelCounty {
    pub name: String,
    pub geoid: String,
    pub rule: String,
}

/// Fixed facts read once from the opening.
pub struct Census {
    goods: BTreeMap<Key, String>,
    grams: BTreeMap<Key, u64>,
    sites: BTreeMap<SiteId, SiteFacts>,
    places: BTreeMap<FinalDemandPrincipalId, String>,
    recipes: BTreeSet<Recipe>,
    service_floor: BTreeMap<SiteId, i128>,
    merchants: BTreeMap<SiteId, CorridorId>,
    /// Every route's corridors, each with its departure offset from the dispatch period.
    route_corridors: BTreeMap<RouteId, Vec<(u64, CorridorId)>>,
    /// The routes from a supplier abroad to a domestic buyer.
    import_routes: BTreeSet<RouteId>,
    default_wage_micros: i128,
    /// The observed wage of each designed process (twelve trades); empty when one wage pays all.
    recipe_wages: BTreeMap<Recipe, i128>,
    pub panel: Vec<PanelCounty>,
}

/// Where an account operates, in the record's three scopes.
pub fn scope(location: &str) -> &'static str {
    if location.starts_with("county:") {
        "domestic"
    } else if location.starts_with("foreign:") {
        "foreign"
    } else {
        "dependency"
    }
}

fn function_name(function: EconomicFunction) -> String {
    format!("{function:?}")
}

fn money(amount: i128) -> Value {
    json!(amount.to_string())
}

/// Unmet over required in basis points, from the two sums; `null` when nothing was required.
fn share_bps(part: u64, whole: u64) -> Value {
    if whole == 0 {
        Value::Null
    } else {
        json!(u128::from(part) * 10_000 / u128::from(whole))
    }
}

fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write as _;
    bytes.iter().fold(String::new(), |mut text, byte| {
        write!(text, "{byte:02x}").expect("writing to a string");
        text
    })
}

impl Census {
    /// Reads the fixed facts from the opening; `default_wage_micros` is the policy's default wage.
    pub fn new(opening: &EconomicOpening, default_wage_micros: i128) -> Self {
        let goods = opening
            .commodity_labels
            .iter()
            .map(|row| ((row.good_id, row.unit_id), row.key.clone()))
            .collect();
        let mut grams = BTreeMap::new();
        for row in &opening.commodities {
            match row.kind {
                CommodityKind::PeriodService { .. } => {}
                CommodityKind::Storable { grams_per_unit } => {
                    grams.insert((row.good_id, row.unit_id), grams_per_unit);
                }
            }
        }
        let sites: BTreeMap<SiteId, SiteFacts> = opening
            .sites
            .iter()
            .map(|row| {
                let location = row.location.to_string();
                let facts = SiteFacts {
                    function: function_name(row.function),
                    scope: scope(&location),
                    location,
                };
                (row.site_id, facts)
            })
            .collect();
        let places = opening
            .households
            .iter()
            .map(|row| (row.principal_id, row.location.to_string()))
            .collect();
        let (route_corridors, import_routes) = routes(opening, &sites);
        let panel = panel(opening, &sites);
        Self {
            goods,
            grams,
            places,
            recipes: recipes(opening),
            service_floor: service_floors(opening),
            merchants: opening
                .sites
                .iter()
                .filter_map(|row| row.merchant.as_ref().map(|m| (row.site_id, m.capacity_id)))
                .collect(),
            route_corridors,
            import_routes,
            default_wage_micros,
            recipe_wages: BTreeMap::new(),
            panel,
            sites,
        }
    }

    /// Reads the facts of an opening that pays each workplace its own observed wage: the labor of a
    /// batch costs, for each designed process, the wage of the persons employed at its sites (see
    /// `process_wages`); a process with no paid person at any site costs the opening's own average.
    ///
    /// # Errors
    /// `BenchError::Opening` when no member of the opening is paid a wage, or a sum overflows.
    pub fn observed(opening: &EconomicOpening) -> Result<Self, BenchError> {
        let (recipe_wages, average) = process_wages(opening)?;
        let mut census = Self::new(opening, average);
        census.recipe_wages = recipe_wages;
        Ok(census)
    }

    /// The wage that pays one hour of a process's labor.
    fn labor_wage(&self, recipe: &Recipe) -> i128 {
        self.recipe_wages
            .get(recipe)
            .copied()
            .unwrap_or(self.default_wage_micros)
    }

    fn good(&self, key: Key) -> &str {
        self.goods.get(&key).map_or("unlabelled", String::as_str)
    }

    fn place(&self, principal: FinalDemandPrincipalId) -> &str {
        self.places
            .get(&principal)
            .map(String::as_str)
            .expect("every household principal is in the opening")
    }

    fn site(&self, site: SiteId) -> &SiteFacts {
        self.sites.get(&site).expect("every site is in the opening")
    }
}

fn recipe_of(row: &RecipeTemplate) -> Recipe {
    Recipe {
        output: (row.output.good_id, row.output.unit_id),
        output_units: row.output.quantity,
        labor_hours: row.labor.as_ref().map_or(0, |labor| labor.hours_per_batch),
        inputs: row
            .inputs
            .iter()
            .map(|input| ((input.good_id, input.unit_id), input.quantity))
            .collect(),
    }
}

fn recipes(opening: &EconomicOpening) -> BTreeSet<Recipe> {
    opening.recipes.iter().map(recipe_of).collect()
}

/// For each designed process, the sum of wage times employed persons over the members paid a wage at
/// its sites, divided by the sum of those persons, rounded down; and the same over every member of the
/// opening. A process with no such person has no entry.
///
/// # Errors
/// `BenchError::Opening` when no member of the opening is paid a wage, or a sum overflows.
fn process_wages(opening: &EconomicOpening) -> Result<(BTreeMap<Recipe, i128>, i128), BenchError> {
    let overflow = || BenchError::Opening(EconomicCatalogError::Arithmetic);
    let rates: BTreeMap<_, i128> = opening
        .employment
        .iter()
        .filter_map(|term| match term.compensation {
            LaborCompensation::Wage(rate) => Some((term.member_id, rate.micro_units())),
            LaborCompensation::WorkingOwner | LaborCompensation::UnpaidFamily => None,
        })
        .collect();
    let mut by_site: BTreeMap<SiteId, (i128, i128)> = BTreeMap::new();
    for seed in &opening.staffing {
        let total = by_site.entry(seed.pool.site_id()).or_default();
        for member in &seed.members {
            if let Some(rate) = rates.get(&member.member.member_id()) {
                let persons = i128::from(member.employed);
                total.0 = rate
                    .checked_mul(persons)
                    .and_then(|pay| total.0.checked_add(pay))
                    .ok_or_else(overflow)?;
                total.1 = total.1.checked_add(persons).ok_or_else(overflow)?;
            }
        }
    }
    let template_recipe: BTreeMap<u16, Recipe> = opening
        .recipes
        .iter()
        .map(|row| (row.id.0, recipe_of(row)))
        .collect();
    let mut sums: BTreeMap<Recipe, (i128, i128)> = BTreeMap::new();
    for site in &opening.sites {
        let Some(&(paid, persons)) = by_site.get(&site.site_id) else {
            continue;
        };
        let made: BTreeSet<&Recipe> = site
            .processes
            .iter()
            .filter_map(|process| template_recipe.get(&process.recipe.0))
            .collect();
        for recipe in made {
            let sum = sums.entry(recipe.clone()).or_default();
            sum.0 = sum.0.checked_add(paid).ok_or_else(overflow)?;
            sum.1 = sum.1.checked_add(persons).ok_or_else(overflow)?;
        }
    }
    let everyone = by_site.values().try_fold((0_i128, 0_i128), |a, b| {
        Some((a.0.checked_add(b.0)?, a.1.checked_add(b.1)?))
    });
    let everyone = everyone.ok_or_else(overflow)?;
    if everyone.1 == 0 {
        return Err(BenchError::Opening(EconomicCatalogError::Opening(
            "no member of the opening is paid a wage",
        )));
    }
    let average = everyone.0 / everyone.1;
    let wages = sums
        .into_iter()
        .filter(|(_, (_, persons))| *persons > 0)
        .map(|(recipe, (paid, persons))| (recipe, paid / persons))
        .collect();
    Ok((wages, average))
}

/// The highest service-input floor of each buyer site (all of a site's floors are its payroll).
fn service_floors(opening: &EconomicOpening) -> BTreeMap<SiteId, i128> {
    let mut floors = BTreeMap::<SiteId, i128>::new();
    for row in &opening.policies.service_inputs {
        let floor = floors.entry(row.buyer_site_id).or_default();
        *floor = (*floor).max(row.cash_floor.micro_units());
    }
    floors
}

type RouteMap = BTreeMap<RouteId, Vec<(u64, CorridorId)>>;

/// Each route's corridors with their departure offsets, and the routes that import.
fn routes(
    opening: &EconomicOpening,
    sites: &BTreeMap<SiteId, SiteFacts>,
) -> (RouteMap, BTreeSet<RouteId>) {
    let logistics = &opening.logistics;
    let mut offsets = BTreeMap::<(RouteId, u16), u64>::new();
    let mut stages: Vec<_> = logistics.route_stages.iter().collect();
    stages.sort_by_key(|row| (row.route_id, row.stage_index));
    let mut running = BTreeMap::<RouteId, u64>::new();
    for stage in stages {
        let at = running.entry(stage.route_id).or_default();
        offsets.insert((stage.route_id, stage.stage_index), *at);
        *at += u64::from(stage.travel_periods);
    }
    let mut corridors = RouteMap::new();
    for row in &logistics.memberships {
        let offset = offsets
            .get(&(row.route_id, row.stage_index))
            .copied()
            .expect("a membership names a declared stage");
        corridors
            .entry(row.route_id)
            .or_default()
            .push((offset, row.corridor_id));
    }
    let imports = logistics
        .supplier_routes
        .iter()
        .filter(|row| {
            let supplier = sites.get(&row.supplier_site_id).map(|s| s.scope);
            let buyer = sites.get(&row.buyer_site_id).map(|s| s.scope);
            supplier.is_some_and(|s| s != "domestic") && buyer == Some("domestic")
        })
        .map(|row| row.route_id)
        .collect();
    (corridors, imports)
}

/// Households of each domestic county at the opening.
fn county_households(opening: &EconomicOpening) -> BTreeMap<String, u64> {
    let mut counties = BTreeMap::<String, u64>::new();
    for row in &opening.households {
        let location = row.location.to_string();
        if let Some(geoid) = location.strip_prefix("county:") {
            *counties.entry(geoid.to_owned()).or_default() += row.households;
        }
    }
    counties
}

/// The four named counties, then two picked by rule from the opening.
fn panel(opening: &EconomicOpening, sites: &BTreeMap<SiteId, SiteFacts>) -> Vec<PanelCounty> {
    let mut panel: Vec<PanelCounty> = FIXED_PANEL
        .iter()
        .map(|(name, geoid)| PanelCounty {
            name: (*name).to_owned(),
            geoid: (*geoid).to_owned(),
            rule: "named".to_owned(),
        })
        .collect();
    let fewest = county_households(opening)
        .into_iter()
        .filter(|(_, households)| *households > 0)
        .min_by_key(|(geoid, households)| (*households, geoid.clone()))
        .expect("domestic counties with households");
    panel.push(PanelCounty {
        name: format!("fewest households ({})", fewest.1),
        geoid: fewest.0,
        rule: "the domestic county with the fewest households at the opening (sum over its \
               household rows, households > 0); ties to the lower geoid"
            .to_owned(),
    });
    let mut employed = BTreeMap::<String, u64>::new();
    for pool in &opening.staffing {
        let facts = sites
            .get(&pool.pool.site_id())
            .expect("a staffed site is in the opening");
        let primary = ["Food", "Extraction"].contains(&facts.function.as_str());
        if let (true, Some(geoid)) = (primary, facts.location.strip_prefix("county:")) {
            *employed.entry(geoid.to_owned()).or_default() +=
                pool.members.iter().map(|m| m.employed).sum::<u64>();
        }
    }
    let most = employed
        .into_iter()
        .max_by_key(|(geoid, people)| (*people, std::cmp::Reverse(geoid.clone())))
        .expect("domestic farm and extraction workplaces");
    panel.push(PanelCounty {
        name: format!("most employed in farm or extraction ({})", most.1),
        geoid: most.0,
        rule: "the domestic county whose Food and Extraction workplaces employ the most people \
               at the opening (staffing members employed, by the workplace's county); ties to \
               the lower geoid"
            .to_owned(),
    });
    panel
}

/// Facts of an order: who supplies whom with what.
#[derive(Clone, Copy, Debug)]
struct Order {
    supplier: SiteId,
    buyer: SiteId,
    key: Key,
    backlog: u64,
}

/// The state at the open of a period, read before the close is prepared.
pub struct Opening {
    period: u64,
    offers: BTreeMap<(SiteId, Key), i128>,
    planned: BTreeMap<SiteId, u64>,
    orders: BTreeMap<OrderId, Order>,
    stock: BTreeMap<(SiteId, Key), u64>,
    available: BTreeMap<(u64, CorridorId), u64>,
    providers: BTreeMap<SiteId, Provider>,
}

/// A site of public provisioning: whether a public allocation of the state names it as the recipient
/// of an operating grant, and the scope of its place.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Provider {
    pub grant: bool,
    pub scope: &'static str,
}

/// The sites whose function is public provisioning, each with whether the state funds it by a
/// provider operating grant.
pub fn public_providers(
    census: &Census,
    state: &MaterialCircuitState,
) -> BTreeMap<SiteId, Provider> {
    let granted: BTreeSet<SiteId> = economy(state)
        .financial
        .public_allocations
        .iter()
        .filter(|row| row.treatment == PublicTransferTreatment::ProviderOperatingGrant)
        .filter_map(|row| match row.recipient {
            AccountId::Site(site) => Some(site),
            _ => None,
        })
        .collect();
    let public = function_name(EconomicFunction::PublicProvisioning);
    census
        .sites
        .iter()
        .filter(|(_, facts)| facts.function == public)
        .map(|(site, facts)| {
            let provider = Provider {
                grant: granted.contains(site),
                scope: facts.scope,
            };
            (*site, provider)
        })
        .collect()
}

pub fn economy(state: &MaterialCircuitState) -> &MonetaryCircuit {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        panic!("the national campaign accounts in money")
    };
    economy
}

/// Grams a corridor can still carry in `period`, read the way the engine reads it.
fn corridor_available(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    period: u64,
    corridor: CorridorId,
) -> u64 {
    if period > state.period {
        if let CapacitySupply::Rolling(rows) = &catalog.capacity_policy {
            let gross = rows
                .shared
                .binary_search_by_key(&corridor, |r| r.corridor_id)
                .ok()
                .map_or(0, |i| rows.shared[i].grams_per_period);
            let future = &state.capacity_reservations.future;
            let reserved = future
                .binary_search_by_key(&(period, corridor), |r| (r.departure_period, r.corridor_id))
                .ok()
                .map_or(0, |i| future[i].reserved_grams);
            return gross.saturating_sub(reserved);
        }
    }
    state
        .corridor_capacities
        .binary_search_by_key(&(period, corridor), |r| (r.period, r.corridor_id))
        .ok()
        .map_or(0, |i| state.corridor_capacities[i].available_grams)
}

impl Opening {
    pub fn read(census: &Census, catalog: &MaterialCatalog, state: &MaterialCircuitState) -> Self {
        let recurring = economy(state).recurring.as_ref().expect("recurring");
        let offers = recurring
            .offers
            .iter()
            .map(|row| {
                let key = (row.site_id, (row.good_id, row.unit_id));
                (key, row.unit_price.micro_units())
            })
            .collect();
        let mut planned = BTreeMap::<SiteId, u64>::new();
        for row in state
            .production_commitments
            .iter()
            .filter(|row| row.period == state.period)
        {
            *planned.entry(row.site_id).or_default() += row.planned_batches;
        }
        let orders = state
            .orders
            .iter()
            .map(|row| {
                let order = Order {
                    supplier: row.supplier_site_id,
                    buyer: row.buyer_site_id,
                    key: (row.good_id, row.unit_id),
                    backlog: row.ordered - row.shipped,
                };
                (row.order_id, order)
            })
            .collect();
        let stock = state
            .inventory
            .iter()
            .map(|row| ((row.site_id, (row.good_id, row.unit_id)), row.quantity))
            .collect();
        let mut keys = BTreeSet::new();
        for route in &census.import_routes {
            for (offset, corridor) in census.route_corridors.get(route).into_iter().flatten() {
                keys.insert((state.period + offset, *corridor));
            }
        }
        keys.extend(census.merchants.values().map(|c| (state.period, *c)));
        let available = keys
            .into_iter()
            .map(|(period, corridor)| {
                let grams = corridor_available(catalog, state, period, corridor);
                ((period, corridor), grams)
            })
            .collect();
        Self {
            period: state.period,
            offers,
            planned,
            orders,
            stock,
            available,
            providers: public_providers(census, state),
        }
    }

    /// The public providers at the open of the period.
    pub const fn providers(&self) -> &BTreeMap<SiteId, Provider> {
        &self.providers
    }
}

/// One need, summed: required, unmet, unpaid (requested less admitted) and unsupplied (admitted
/// less fulfilled or performed).
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct Need {
    required: u64,
    unmet: u64,
    unpaid: u64,
    unsupplied: u64,
}

impl Need {
    fn add(&mut self, other: Self) {
        self.required += other.required;
        self.unmet += other.unmet;
        self.unpaid += other.unpaid;
        self.unsupplied += other.unsupplied;
    }

    fn row(self) -> Value {
        json!([
            self.required,
            self.unmet,
            self.unpaid,
            self.unsupplied,
            share_bps(self.unmet, self.required)
        ])
    }
}

type NeedMap = BTreeMap<(String, String), Need>;

fn add_need(
    map: &mut NeedMap,
    census: &Census,
    principal: FinalDemandPrincipalId,
    key: Key,
    need: Need,
) {
    let place = census.place(principal).to_owned();
    map.entry((place, census.good(key).to_owned()))
        .or_default()
        .add(need);
}

/// Every household need of the period, by place and need.
fn need_sums(census: &Census, receipts: &MaterialTickReceipts) -> NeedMap {
    let mut map = NeedMap::new();
    for row in &receipts.household_consumption {
        let need = Need {
            required: row.required_quantity,
            unmet: row.unmet_quantity,
            ..Need::default()
        };
        add_need(
            &mut map,
            census,
            row.principal_id,
            (row.good_id, row.unit_id),
            need,
        );
    }
    for row in &receipts.household_demand {
        let need = Need {
            unpaid: row.requested_quantity - row.admitted_quantity,
            unsupplied: row.admitted_quantity - row.fulfilled_quantity,
            ..Need::default()
        };
        add_need(
            &mut map,
            census,
            row.principal_id,
            (row.good_id, row.unit_id),
            need,
        );
    }
    for row in &receipts.household_services {
        let need = Need {
            required: row.required_quantity,
            unmet: row.unmet_quantity,
            ..Need::default()
        };
        add_need(
            &mut map,
            census,
            row.principal_id,
            (row.good_id, row.unit_id),
            need,
        );
    }
    for row in &receipts.service_performance {
        let AccountId::Household(principal) = row.buyer else {
            continue;
        };
        let need = Need {
            unpaid: row.requested_quantity - row.admitted_quantity,
            unsupplied: row.admitted_quantity - row.performed_quantity,
            ..Need::default()
        };
        add_need(
            &mut map,
            census,
            principal,
            (row.good_id, row.unit_id),
            need,
        );
    }
    map
}

/// The band of one county's need: unmet share 0, up to 10%, up to 50%, above 50%, nothing required.
fn band(need: &Need) -> usize {
    if need.required == 0 {
        4
    } else if need.unmet == 0 {
        0
    } else if u128::from(need.unmet) * 10 <= u128::from(need.required) {
        1
    } else if u128::from(need.unmet) * 2 <= u128::from(need.required) {
        2
    } else {
        3
    }
}

/// National totals, county bands and the five counties with the most unmet, for each need.
fn national_supply(sums: &NeedMap) -> Value {
    let mut out = Map::new();
    for need in NEEDS {
        let counties: Vec<(&str, &Need)> = sums
            .iter()
            .filter(|((place, key), _)| key == need && place.starts_with("county:"))
            .map(|((place, _), value)| (&place["county:".len()..], value))
            .collect();
        let mut total = Need::default();
        let mut bands = [0_u64; 5];
        for (_, value) in &counties {
            total.add(**value);
            bands[band(value)] += 1;
        }
        let mut top: Vec<_> = counties.iter().filter(|(_, v)| v.unmet > 0).collect();
        top.sort_by_key(|(geoid, v)| (std::cmp::Reverse(v.unmet), *geoid));
        let top: Vec<Value> = top
            .iter()
            .take(5)
            .map(|(geoid, v)| json!([geoid, v.unmet, v.required]))
            .collect();
        out.insert(
            need.to_owned(),
            json!({"sum": total.row(), "county_bands": bands, "top_unmet": top}),
        );
    }
    Value::Object(out)
}

/// Each place's needs, for the places `keep` selects, keyed by place.
fn places_supply(sums: &NeedMap, keep: impl Fn(&str) -> bool) -> Value {
    let mut out = BTreeMap::<String, Map<String, Value>>::new();
    for ((place, need), value) in sums {
        if keep(place) && NEEDS.contains(&need.as_str()) {
            out.entry(place.clone())
                .or_default()
                .insert(need.clone(), value.row());
        }
    }
    json!(out)
}

#[derive(Clone, Copy, Debug, Default)]
struct Jobs([u64; 6]);

/// People at work and looking for work, at the open and the close, with hires and layoffs.
fn jobs(census: &Census, receipts: &MaterialTickReceipts) -> Value {
    let mut by = BTreeMap::<(String, String), Jobs>::new();
    for row in &receipts.staffing_members {
        let facts = census.site(row.site_id);
        let values = [
            row.opening_employed,
            row.opening_reserve,
            row.closing_employed,
            row.closing_reserve,
            row.hires,
            row.separations,
        ];
        for key in [
            (facts.scope.to_owned(), facts.function.clone()),
            (facts.scope.to_owned(), "all".to_owned()),
        ] {
            let sums = by.entry(key).or_default();
            for (sum, value) in sums.0.iter_mut().zip(values) {
                *sum += value;
            }
        }
    }
    let mut out = BTreeMap::<String, Map<String, Value>>::new();
    for ((scope, function), sums) in by {
        out.entry(scope)
            .or_default()
            .insert(function, json!(sums.0));
    }
    json!(out)
}

#[derive(Clone, Copy, Debug, Default)]
struct Business {
    sites: u64,
    under_service_floor: u64,
    under_replenishment_floor: u64,
    idle_with_plan: u64,
    wages: i128,
    sales: i128,
    cash: i128,
}

/// Output of each site in the period: goods batches and service units.
fn output_by_site(receipts: &MaterialTickReceipts) -> BTreeMap<SiteId, (u64, u64)> {
    let mut out = BTreeMap::<SiteId, (u64, u64)>::new();
    for row in &receipts.production {
        let entry = out.entry(row.site_id).or_default();
        entry.0 += row.planned_batches;
        entry.1 += row.produced_batches;
    }
    for row in &receipts.service_outputs {
        out.entry(row.site_id).or_default().1 += row.produced_quantity;
    }
    out
}

/// Money the sites took and paid in the period: wages accrued and sales.
fn site_flows(receipts: &MaterialTickReceipts) -> BTreeMap<SiteId, (i128, i128)> {
    let mut flows = BTreeMap::<SiteId, (i128, i128)>::new();
    for row in &receipts.wage_accruals {
        if let AccountId::Site(site) = row.employer {
            flows.entry(site).or_default().0 += row.amount.micro_units();
        }
    }
    for row in &receipts.income {
        if let AccountId::Site(site) = row.account {
            flows.entry(site).or_default().1 += row.statement.sales.micro_units();
        }
    }
    flows
}

/// Sites, floors, idle plans, wages, sales and cash, by scope and economic function.
fn businesses(
    census: &Census,
    open: &Opening,
    receipts: &MaterialTickReceipts,
    after: &MaterialCircuitState,
) -> Value {
    let economy = economy(after);
    let recurring = economy.recurring.as_ref().expect("recurring");
    let mut replenishment = BTreeMap::<SiteId, i128>::new();
    for row in &recurring.replenishment {
        let floor = replenishment.entry(row.buyer_site_id).or_default();
        *floor = (*floor).max(row.cash_floor.micro_units());
    }
    let output = output_by_site(receipts);
    let flows = site_flows(receipts);
    let mut by = BTreeMap::<(&str, &str), Business>::new();
    for (site, facts) in &census.sites {
        let cash = economy
            .book
            .cash(AccountId::Site(*site))
            .map_or(0, Currency::micro_units);
        let (planned, produced) = output.get(site).copied().unwrap_or_default();
        let plan = planned + open.planned.get(site).copied().unwrap_or(0);
        let (wages, sales) = flows.get(site).copied().unwrap_or_default();
        let row = by.entry((facts.scope, &facts.function)).or_default();
        row.sites += 1;
        row.under_service_floor +=
            u64::from(census.service_floor.get(site).is_some_and(|f| cash < *f));
        row.under_replenishment_floor +=
            u64::from(replenishment.get(site).is_some_and(|f| cash < *f));
        row.idle_with_plan += u64::from(plan > 0 && produced == 0);
        row.wages += wages;
        row.sales += sales;
        row.cash += cash;
    }
    let mut out = BTreeMap::<String, Map<String, Value>>::new();
    for ((scope, function), b) in by {
        out.entry(scope.to_owned()).or_default().insert(
            function.to_owned(),
            json!([
                b.sites,
                b.under_service_floor,
                b.under_replenishment_floor,
                b.idle_with_plan,
                money(b.wages),
                money(b.sales),
                money(b.cash)
            ]),
        );
    }
    json!(out)
}

/// The lowest and highest offer of a commodity among the sellers of one scope.
fn price_range(census: &Census, open: &Opening, key: Key, domestic: bool) -> Option<(i128, i128)> {
    let prices: Vec<i128> = open
        .offers
        .iter()
        .filter(|((site, good), _)| {
            *good == key && (census.site(*site).scope == "domestic") == domestic
        })
        .map(|(_, price)| *price)
        .collect();
    Some((*prices.iter().min()?, *prices.iter().max()?))
}

/// Quantity sold and its value, by commodity: to households (fulfilled), to firms by delivery
/// order (admitted) and as services (performed), each at the price it was admitted at.
fn sold(receipts: &MaterialTickReceipts) -> BTreeMap<Key, (u64, i128)> {
    let mut sold = BTreeMap::<Key, (u64, i128)>::new();
    let mut add = |key: Key, quantity: u64, price: i128| {
        let row = sold.entry(key).or_default();
        row.0 += quantity;
        row.1 += i128::from(quantity) * price;
    };
    for row in &receipts.household_demand {
        add(
            (row.good_id, row.unit_id),
            row.fulfilled_quantity,
            row.unit_price.micro_units(),
        );
    }
    for row in &receipts.procurement {
        add(
            (row.good_id, row.unit_id),
            row.admitted_quantity,
            row.unit_price.micro_units(),
        );
    }
    for row in &receipts.service_performance {
        add(
            (row.good_id, row.unit_id),
            row.performed_quantity,
            row.unit_price.micro_units(),
        );
    }
    sold
}

/// Whether a designed process covers its cost: a batch's labor at the census's wage and its
/// inputs at the lowest domestic offer, against its output at the lowest and highest domestic
/// offer.
fn recipe_cost(census: &Census, open: &Opening, recipe: &Recipe) -> Value {
    let labor = i128::from(recipe.labor_hours) * census.labor_wage(recipe);
    let mut inputs = 0_i128;
    let mut unpriced = Vec::new();
    for (key, quantity) in &recipe.inputs {
        match price_range(census, open, *key, true) {
            Some((low, _)) => inputs += i128::from(*quantity) * low,
            None => unpriced.push(census.good(*key).to_owned()),
        }
    }
    let cost = labor + inputs;
    let Some((low, high)) = price_range(census, open, recipe.output, true) else {
        return json!({"batch_cost_micros": money(cost), "verdict": "no domestic offer"});
    };
    let units = i128::from(recipe.output_units);
    let verdict = if units * low >= cost {
        "covers cost"
    } else if units * high < cost {
        "below cost"
    } else {
        "below cost at the lowest seller"
    };
    json!({
        "output_units": recipe.output_units,
        "labor_hours": recipe.labor_hours,
        "batch_cost_micros": money(cost),
        "unit_cost_micros": money(cost / units),
        "batch_receipts_at_lowest_and_highest_micros": [money(units * low), money(units * high)],
        "unpriced_inputs": unpriced,
        "verdict": verdict,
    })
}

/// Each commodity's price range, sales and, for each process that makes it, its cost.
fn products(census: &Census, open: &Opening, receipts: &MaterialTickReceipts) -> Value {
    let sold = sold(receipts);
    let mut out = Map::new();
    for (key, name) in &census.goods {
        let range = |domestic| {
            price_range(census, open, *key, domestic)
                .map_or(Value::Null, |(low, high)| json!([money(low), money(high)]))
        };
        let (quantity, value) = sold.get(key).copied().unwrap_or_default();
        let costs: Vec<Value> = census
            .recipes
            .iter()
            .filter(|recipe| recipe.output == *key)
            .map(|recipe| recipe_cost(census, open, recipe))
            .collect();
        out.insert(
            name.clone(),
            json!({
                "domestic_price_low_high_micros": range(true),
                "abroad_price_low_high_micros": range(false),
                "sold_quantity": quantity,
                "sold_value_micros": money(value),
                "processes": costs,
            }),
        );
    }
    Value::Object(out)
}

/// One import flow: a foreign region's sellers of one good to domestic buyers.
#[derive(Clone, Debug, Default)]
struct Flow {
    open_backlog: u64,
    ordered: u64,
    shipped: u64,
    backlog_after: u64,
    supplier_stock: u64,
    handling_short: u64,
    corridors: BTreeSet<(u64, CorridorId)>,
    merchants: BTreeSet<SiteId>,
}

/// Grams one capacity carried this period, in all and by user.
#[derive(Clone, Debug, Default)]
struct Usage {
    grams: u64,
    users: BTreeMap<String, u64>,
}

type UseMap = BTreeMap<(u64, CorridorId), Usage>;

fn add_use(used: &mut UseMap, key: (u64, CorridorId), label: String, grams: u64) {
    let usage = used.entry(key).or_default();
    usage.grams += grams;
    *usage.users.entry(label).or_default() += grams;
}

/// Grams dispatched this period through each (departure period, corridor), over every route,
/// and through each merchant's handling capacity, with who used them.
fn corridor_use(
    census: &Census,
    open: &Opening,
    orders: &BTreeMap<OrderId, Order>,
    receipts: &MaterialTickReceipts,
) -> UseMap {
    let mut used = UseMap::new();
    let grams = |key: Key| census.grams.get(&key).copied().unwrap_or(0);
    let merchant = |site: SiteId, key: Key, quantity: u64, to: &str, used: &mut UseMap| {
        if let Some(capacity) = census.merchants.get(&site) {
            let label = format!(
                "{} handled at {} for {to}",
                census.good(key),
                census.site(site).location
            );
            add_use(used, (open.period, *capacity), label, quantity * grams(key));
        }
    };
    for row in &receipts.dispatches {
        let order = orders
            .get(&row.order_id)
            .expect("a dispatched order is known");
        let (from, to) = (
            &census.site(order.supplier).location,
            &census.site(order.buyer).location,
        );
        let label = format!("{} from {from} to {to}", census.good(order.key));
        for (offset, corridor) in census
            .route_corridors
            .get(&row.route_id)
            .into_iter()
            .flatten()
        {
            let key = (open.period + offset, *corridor);
            add_use(
                &mut used,
                key,
                label.clone(),
                row.quantity * grams(order.key),
            );
        }
        merchant(order.supplier, order.key, row.quantity, to, &mut used);
    }
    for row in &receipts.local_transfers {
        let to = census.site(row.buyer_site_id).location.clone();
        merchant(
            row.supplier_site_id,
            (row.good_id, row.unit_id),
            row.quantity,
            &to,
            &mut used,
        );
    }
    for row in &receipts.local_fulfillments {
        let key = (row.good_id, row.unit_id);
        merchant(
            row.retailer_site_id,
            key,
            row.quantity,
            "households",
            &mut used,
        );
    }
    used
}

/// Every known order this period: open orders and those admitted in the close.
fn known_orders(open: &Opening, receipts: &MaterialTickReceipts) -> BTreeMap<OrderId, Order> {
    let mut orders = open.orders.clone();
    for row in &receipts.procurement {
        orders.entry(row.order_id).or_insert(Order {
            supplier: row.supplier_site_id,
            buyer: row.buyer_site_id,
            key: (row.good_id, row.unit_id),
            backlog: 0,
        });
    }
    orders
}

fn is_import(census: &Census, order: &Order) -> bool {
    census.site(order.supplier).scope != "domestic" && census.site(order.buyer).scope == "domestic"
}

fn flow_key(census: &Census, order: &Order, watch: Option<&str>) -> (String, String) {
    let supplier = census.site(order.supplier).location.clone();
    let good = census.good(order.key).to_owned();
    match watch {
        Some(_) => (
            supplier,
            format!("{good} to {}", census.site(order.buyer).location),
        ),
        None => (supplier, good),
    }
}

/// The import flows of the period, by (supplier place, good). With `watch`, only the flows to
/// buyers in that location, keyed by buyer too.
fn import_flows(
    census: &Census,
    open: &Opening,
    orders: &BTreeMap<OrderId, Order>,
    receipts: &MaterialTickReceipts,
    after: &MaterialCircuitState,
    watch: Option<&str>,
) -> BTreeMap<(String, String), Flow> {
    let selected = |order: &Order| {
        is_import(census, order)
            && watch.is_none_or(|place| census.site(order.buyer).location == place)
    };
    let mut flows = BTreeMap::<(String, String), Flow>::new();
    for order in open.orders.values().filter(|o| selected(o)) {
        flows
            .entry(flow_key(census, order, watch))
            .or_default()
            .open_backlog += order.backlog;
    }
    for row in &receipts.procurement {
        let order = &orders[&row.order_id];
        if selected(order) {
            flows
                .entry(flow_key(census, order, watch))
                .or_default()
                .ordered += row.admitted_quantity;
        }
    }
    for row in &receipts.dispatches {
        let order = &orders[&row.order_id];
        if selected(order) {
            let flow = flows.entry(flow_key(census, order, watch)).or_default();
            flow.shipped += row.quantity;
            flow.corridors.extend(
                census
                    .route_corridors
                    .get(&row.route_id)
                    .into_iter()
                    .flatten()
                    .map(|(offset, corridor)| (open.period + offset, *corridor)),
            );
        }
    }
    for row in &after.orders {
        let order = orders.get(&row.order_id).copied().unwrap_or(Order {
            supplier: row.supplier_site_id,
            buyer: row.buyer_site_id,
            key: (row.good_id, row.unit_id),
            backlog: 0,
        });
        if selected(&order) {
            flows
                .entry(flow_key(census, &order, watch))
                .or_default()
                .backlog_after += row.ordered - row.shipped;
        }
    }
    flow_resources(census, open, orders, receipts, &mut flows, watch);
    flows
}

/// The resources each flow's open orders compete for: supplier stock, route corridors (from
/// the supplier routes of the orders) and the supplier's handling.
fn flow_resources(
    census: &Census,
    open: &Opening,
    orders: &BTreeMap<OrderId, Order>,
    receipts: &MaterialTickReceipts,
    flows: &mut BTreeMap<(String, String), Flow>,
    watch: Option<&str>,
) {
    let mut suppliers = BTreeMap::<(String, String), BTreeSet<(SiteId, Key)>>::new();
    for order in orders.values().filter(|o| is_import(census, o)) {
        let key = flow_key(census, order, watch);
        if let Some(flow) = flows.get_mut(&key) {
            suppliers
                .entry(key)
                .or_default()
                .insert((order.supplier, order.key));
            if census.merchants.contains_key(&order.supplier) {
                flow.merchants.insert(order.supplier);
            }
        }
    }
    for (key, set) in suppliers {
        let flow = flows.get_mut(&key).expect("a flow for each supplier set");
        flow.supplier_stock = set
            .iter()
            .map(|k| open.stock.get(k).copied().unwrap_or(0))
            .sum();
    }
    for row in &receipts.handling {
        let OutboundOrderId::Delivery(id) = row.order else {
            continue;
        };
        let Some(order) = orders.get(&id).filter(|o| is_import(census, o)) else {
            continue;
        };
        if let Some(flow) = flows.get_mut(&flow_key(census, order, watch)) {
            flow.handling_short += row.feasible_quantity - row.handled_quantity;
        }
    }
}
/// A capacity's name in the record: its first six bytes and its departure period.
fn capacity_name(key: (u64, CorridorId)) -> String {
    format!("{}@{}", hex(&key.1.as_bytes()[..6]), key.0)
}

/// One flow as [open backlog, ordered, shipped, backlog after, supplier stock at open, bound by],
/// adding each saturated capacity it competes for to `bound`.
fn flow_json(
    census: &Census,
    open: &Opening,
    used: &UseMap,
    flow: &Flow,
    unit_grams: u64,
    bound: &mut BTreeSet<(&'static str, (u64, CorridorId))>,
) -> Value {
    let mut names = Vec::new();
    let to_ship = flow.open_backlog + flow.ordered;
    if to_ship > flow.shipped && flow.supplier_stock < to_ship {
        names.push("supplier stock".to_owned());
    }
    let capacities = flow
        .corridors
        .iter()
        .map(|key| ("route corridor", *key))
        .chain(flow.merchants.iter().map(|site| {
            let key = (open.period, census.merchants[site]);
            ("supplier handling capacity", key)
        }));
    for (kind, key) in capacities {
        let available = open.available.get(&key).copied().unwrap_or(0);
        let dispatched = used.get(&key).map_or(0, |u| u.grams);
        if available.saturating_sub(dispatched) < unit_grams {
            names.push(capacity_name(key));
            bound.insert((kind, key));
        }
    }
    if flow.handling_short > 0 {
        names.push(format!(
            "handling hours ({} units short)",
            flow.handling_short
        ));
    }
    json!([
        flow.open_backlog,
        flow.ordered,
        flow.shipped,
        flow.backlog_after,
        flow.supplier_stock,
        names
    ])
}

/// The grams of one unit of the good a flow carries (its key starts with the good's name).
fn flow_unit_grams(census: &Census, good: &str) -> u64 {
    let name = good.split(' ').next().unwrap_or(good);
    census
        .goods
        .iter()
        .find(|(_, label)| label.as_str() == name)
        .and_then(|(key, _)| census.grams.get(key))
        .copied()
        .unwrap_or(1)
        .max(1)
}

/// Each saturated capacity: what it could carry, what it carried and its three largest users.
fn bound_table(
    open: &Opening,
    used: &UseMap,
    bound: &BTreeSet<(&'static str, (u64, CorridorId))>,
) -> Value {
    let mut out = Map::new();
    for (kind, key) in bound {
        let usage = used.get(key).cloned().unwrap_or_default();
        let mut users: Vec<(String, u64)> = usage.users.into_iter().collect();
        users.sort_by_key(|(name, grams)| (std::cmp::Reverse(*grams), name.clone()));
        let top: Vec<Value> = users.iter().take(3).map(|(n, g)| json!([n, g])).collect();
        out.insert(
            capacity_name(*key),
            json!({
                "kind": kind,
                "available_grams": open.available.get(key).copied().unwrap_or(0),
                "dispatched_grams": usage.grams,
                "users": users.len(),
                "top_users_grams": top,
            }),
        );
    }
    Value::Object(out)
}

/// Imports by supplier place and good, in detail the imports to the watched county, and the
/// saturated capacities they compete for. Flows with nothing to ship are left out.
fn trade(
    census: &Census,
    open: &Opening,
    receipts: &MaterialTickReceipts,
    after: &MaterialCircuitState,
    watch: &str,
) -> Value {
    let orders = known_orders(open, receipts);
    let used = corridor_use(census, open, &orders, receipts);
    let state = after;
    let mut bound = BTreeSet::new();
    let mut render = |flows: BTreeMap<(String, String), Flow>| {
        let mut out = BTreeMap::<String, Map<String, Value>>::new();
        for ((place, good), flow) in flows {
            if flow.open_backlog + flow.ordered + flow.backlog_after == 0 {
                continue;
            }
            let unit = flow_unit_grams(census, &good);
            let row = flow_json(census, open, &used, &flow, unit, &mut bound);
            out.entry(place).or_default().insert(good, row);
        }
        json!(out)
    };
    let imports = render(import_flows(census, open, &orders, receipts, state, None));
    let watched = render(import_flows(
        census,
        open,
        &orders,
        receipts,
        state,
        Some(watch),
    ));
    json!({
        "imports": imports,
        "watched_imports": watched,
        "bound_capacities": bound_table(open, &used, &bound),
    })
}

/// Cash by kind of account after the close, with money held in escrow and wages owed.
pub fn money_record(census: &Census, after: &MaterialCircuitState) -> Value {
    let book = economy(after).book.snapshot();
    let mut kinds = BTreeMap::<String, i128>::new();
    for row in &book.accounts {
        let kind = match row.id {
            AccountId::Household(p) => format!("households_{}", scope(census.place(p))),
            AccountId::Site(s) => format!("businesses_{}", census.site(s).scope),
            AccountId::Company(_) => "companies".to_owned(),
            AccountId::Public(_) => "public_bodies".to_owned(),
            AccountId::Organization(_) => "organizations".to_owned(),
        };
        *kinds.entry(kind).or_default() += row.cash.micro_units();
    }
    let cash: i128 = kinds.values().sum();
    let escrow: i128 = book
        .purchases
        .iter()
        .map(|row| row.reserved_amount().expect("a valid escrow").micro_units())
        .sum();
    let owed: i128 = book
        .shifts
        .iter()
        .map(|row| {
            row.outstanding_wages()
                .expect("a valid shift")
                .micro_units()
        })
        .sum();
    let mut out: Map<String, Value> = kinds.into_iter().map(|(k, v)| (k, money(v))).collect();
    out.insert("cash_total".to_owned(), money(cash));
    out.insert("purchase_escrow".to_owned(), money(escrow));
    out.insert("wages_owed".to_owned(), money(owed));
    out.insert("total".to_owned(), money(cash + escrow + owed));
    Value::Object(out)
}

/// One period's record, read from the open, the close's receipts and the committed state.
pub fn period_record(
    census: &Census,
    open: &Opening,
    receipts: &MaterialTickReceipts,
    _catalog: &MaterialCatalog,
    after: &MaterialCircuitState,
) -> Value {
    let sums = need_sums(census, receipts);
    let panel: Vec<String> = census
        .panel
        .iter()
        .map(|county| format!("county:{}", county.geoid))
        .collect();
    json!({
        "period": open.period,
        "supply": national_supply(&sums),
        "panel": places_supply(&sums, |place| panel.iter().any(|p| p == place)),
        "abroad": places_supply(&sums, |place| scope(place) != "domestic"),
        "jobs": jobs(census, receipts),
        "businesses": businesses(census, open, receipts, after),
        "products": products(census, open, receipts),
        "trade": trade(census, open, receipts, after, "county:26163"),
        "money": money_record(census, after),
    })
}

/// The record's legend: what each array holds.
pub fn columns() -> Value {
    json!({
        "need": ["required", "unmet", "unpaid", "unsupplied", "unmet_share_bps"],
        "county_bands": ["unmet 0", "unmet up to 10%", "up to 50%", "above 50%", "nothing required"],
        "top_unmet": ["geoid", "unmet", "required"],
        "jobs": ["at_work_open", "looking_open", "at_work_close", "looking_close", "hires", "layoffs"],
        "trade_flow": [
            "open_backlog", "ordered", "shipped", "backlog_after", "supplier_stock_at_open",
            "bound_by"
        ],
        "businesses": [
            "sites", "under_service_input_floor", "under_replenishment_floor",
            "zero_output_with_a_plan", "wages_micros", "sales_micros", "cash_micros"
        ],
    })
}

/// Households and persons by scope, as [households, persons].
pub type Counts = BTreeMap<&'static str, [u64; 2]>;

/// Households and persons of the session's cohorts, by scope.
pub fn session_counts(census: &Census, state: &MaterialCircuitState) -> Counts {
    let recurring = economy(state).recurring.as_ref().expect("recurring");
    let mut counts = Counts::new();
    for row in &recurring.households {
        let entry = counts
            .entry(scope(census.place(row.principal_id)))
            .or_default();
        entry[0] += row.households;
        entry[1] += row.persons;
    }
    counts
}

/// Households and persons of the opening's household rows, by scope.
pub fn opening_counts(opening: &EconomicOpening) -> Counts {
    let mut counts = Counts::new();
    for row in &opening.households {
        let entry = counts.entry(scope(&row.location.to_string())).or_default();
        entry[0] += row.households;
        entry[1] += row.persons;
    }
    counts
}

/// The number of sites in the census, by scope.
pub fn site_counts(census: &Census) -> BTreeMap<&'static str, u64> {
    let mut counts = BTreeMap::new();
    for facts in census.sites.values() {
        *counts.entry(facts.scope).or_default() += 1;
    }
    counts
}

/// What the bench has beside `MaterialTickReceipts`.
pub struct BenchReceipts<'a> {
    pub market_clearings: &'a [MarketClearingReceipt],
    pub adjustments: &'a [AdjustmentReceipt],
    pub public_programs: &'a [PublicProgramReceipt],
    pub closing_members: &'a [PoolMembers],
    /// Production policies whose planned batches after the close exceed the period's plan receipt.
    pub spare_money_raised: u64,
}

/// One market product and scope: short markets, demand at the quote, sold, and the row with the
/// highest clearing price (its price, its quote and the seller's place).
#[derive(Default)]
struct ShortMarkets {
    short: u64,
    demand_at_quote: u64,
    sold: u64,
    highest: Option<(i128, i128, String)>,
}

/// The short markets of the period by product label and by the seller's scope:
/// `[short_markets, demand_at_quote, sold_quantity, highest clearing price, the quote of that row,
/// county or region of that row]`. The highest is a maximum, never an average.
pub fn markets_record(census: &Census, bench: &BenchReceipts<'_>) -> Value {
    let mut by = BTreeMap::<(String, &'static str), ShortMarkets>::new();
    for row in bench.market_clearings {
        let facts = census.site(row.site_id);
        let entry = by
            .entry((
                census.good((row.good_id, row.unit_id)).to_owned(),
                facts.scope,
            ))
            .or_default();
        entry.short += 1;
        entry.demand_at_quote += row.demand_at_quote;
        entry.sold += row.sold_quantity;
        let price = row.clearing_price.micro_units();
        if entry
            .highest
            .as_ref()
            .is_none_or(|(best, _, _)| price > *best)
        {
            entry.highest = Some((price, row.quote_price.micro_units(), facts.location.clone()));
        }
    }
    let mut out = BTreeMap::<String, Map<String, Value>>::new();
    for ((product, scope), row) in by {
        let (price, quote, place) = row
            .highest
            .map_or((Value::Null, Value::Null, Value::Null), |(p, q, l)| {
                (money(p), money(q), json!(l))
            });
        out.entry(product).or_default().insert(
            scope.to_owned(),
            json!([
                row.short,
                row.demand_at_quote,
                row.sold,
                price,
                quote,
                place
            ]),
        );
    }
    json!(out)
}

/// Counts of what each adjustment rule did in the period. Every key is present, with zeros when
/// nothing acted.
pub fn rules_record(bench: &BenchReceipts<'_>) -> Value {
    let mut hiring = [0_u64; 3];
    let mut moves = [0_u64; 2];
    let mut stops = [0_u64; 3];
    let (mut resting, mut resting_to_cost, mut owner_spare) = (0_u64, 0_u64, 0_u64);
    let mut restarts = [0_u64; 3];
    let mut restart_money = 0_i128;
    let mut offers = [0_u64; 2];
    for row in bench.adjustments {
        match row {
            AdjustmentReceipt::HiringBound(r) => {
                hiring[0] += 1;
                if r.bound_hours < r.asked_hours {
                    hiring[1] += 1;
                    hiring[2] += r.asked_hours - r.bound_hours;
                }
            }
            AdjustmentReceipt::PlaceMove(r) => {
                moves[0] += 1;
                moves[1] += r.persons;
            }
            AdjustmentReceipt::Stop(r) => {
                stops[0] += 1;
                stops[1] += u64::from(r.could_not_pay);
                stops[2] += u64::from(r.hold == StopHold::Held);
            }
            AdjustmentReceipt::RestingPrice(_) => resting += 1,
            AdjustmentReceipt::RestingPriceToCost(_) => resting_to_cost += 1,
            AdjustmentReceipt::Restart(r) => {
                match r.test {
                    RestartTest::Restarted => restarts[0] += 1,
                    RestartTest::Failed => restarts[1] += 1,
                    RestartTest::NoBuyer => restarts[2] += 1,
                    RestartTest::NotTested => {}
                }
                restart_money += r.money.micro_units();
            }
            AdjustmentReceipt::OwnerSpare(_) => owner_spare += 1,
            AdjustmentReceipt::GoodsOffer(r) => {
                offers[0] += 1;
                offers[1] += u64::from(r.planned_gain > 0);
            }
        }
    }
    let rows = u64::try_from(bench.public_programs.len()).expect("few rows");
    let paid: i128 = bench
        .public_programs
        .iter()
        .map(|r| r.paid.micro_units())
        .sum();
    let unfunded: i128 = bench
        .public_programs
        .iter()
        .map(|r| r.unfunded.micro_units())
        .sum();
    json!({
        "hiring_bound": hiring,
        "moves": moves,
        "stops": stops,
        "resting_prices": resting,
        "resting_to_cost": resting_to_cost,
        "restarts": [restarts[0], restarts[1], restarts[2], money(restart_money)],
        "owner_spare": owner_spare,
        "goods_offers": offers,
        "spare_money_raised": bench.spare_money_raised,
        "programs": [rows, money(paid), money(unfunded)],
    })
}

/// The side of a public provider in a pair: 0 with a grant, 1 without one; `None` for any other site.
fn side(providers: &BTreeMap<SiteId, Provider>, site: SiteId) -> Option<usize> {
    providers
        .get(&site)
        .map(|provider| usize::from(!provider.grant))
}

/// What the rules did to the public providers in the period, each figure a pair
/// `[with a grant, without a grant]` summed over them. Every key is present, with zeros where nothing
/// acted. `price` is the lowest and the highest unit price among their offers at the close, in
/// micro-units written as money is written elsewhere (`null` for a side with no offer).
pub fn public_record(
    providers: &BTreeMap<SiteId, Provider>,
    bench: &BenchReceipts<'_>,
    state: &MaterialCircuitState,
    staffing: &StaffingState,
) -> Value {
    let mut at_work = [0_u64; 2];
    let mut stops = [0_u64; 2];
    let mut stops_held = [0_u64; 2];
    let mut hiring_bound_below = [0_u64; 2];
    let mut resting = [0_u64; 2];
    let mut raised = [0_u64; 2];
    // [failed, no buyer, restarted] on each side.
    let mut restarts = [[0_u64; 3]; 2];
    let mut prices: [Option<(i128, i128)>; 2] = [None, None];
    let pool_sites: BTreeMap<StaffingPoolId, SiteId> = staffing
        .pools()
        .iter()
        .map(|pool| (pool.binding().pool_id(), pool.binding().site_id()))
        .collect();
    for held in bench.closing_members {
        let site = pool_sites
            .get(&held.pool_id)
            .expect("every pool has a site");
        if let Some(at) = side(providers, *site) {
            at_work[at] += held
                .members
                .iter()
                .map(StaffingMemberState::employed)
                .sum::<u64>();
        }
    }
    for row in bench.adjustments {
        match row {
            AdjustmentReceipt::HiringBound(r) => {
                if let (Some(at), true) =
                    (side(providers, r.site_id), r.bound_hours < r.asked_hours)
                {
                    hiring_bound_below[at] += 1;
                }
            }
            AdjustmentReceipt::Stop(r) => {
                if let Some(at) = side(providers, r.site_id) {
                    stops[at] += 1;
                    stops_held[at] += u64::from(r.hold == StopHold::Held);
                }
            }
            AdjustmentReceipt::RestingPrice(r) => {
                if let Some(at) = side(providers, r.site_id) {
                    resting[at] += 1;
                }
            }
            AdjustmentReceipt::RestingPriceToCost(r) => {
                if let Some(at) = side(providers, r.site_id) {
                    raised[at] += 1;
                }
            }
            AdjustmentReceipt::Restart(r) => {
                if let Some(at) = side(providers, r.site_id) {
                    match r.test {
                        RestartTest::Failed => restarts[at][0] += 1,
                        RestartTest::NoBuyer => restarts[at][1] += 1,
                        RestartTest::Restarted => restarts[at][2] += 1,
                        RestartTest::NotTested => {}
                    }
                }
            }
            _ => {}
        }
    }
    for offer in &economy(state).recurring.as_ref().expect("recurring").offers {
        if let Some(at) = side(providers, offer.site_id) {
            let price = offer.unit_price.micro_units();
            prices[at] = Some(prices[at].map_or((price, price), |(low, high)| {
                (low.min(price), high.max(price))
            }));
        }
    }
    let price =
        |at: usize| prices[at].map_or(Value::Null, |(low, high)| json!([money(low), money(high)]));
    json!({
        "at_work": at_work,
        "stops": stops,
        "stops_held": stops_held,
        "hiring_bound_below": hiring_bound_below,
        "resting": resting,
        "raised": raised,
        "restarts": restarts,
        "price": [price(0), price(1)],
    })
}

/// What each public program paid in the period, by its key: `[rows, due_micros, paid_micros,
/// unfunded_micros]` summed over the period's program receipts (zeros where the program paid nothing),
/// and the fund's cash at the close (`null` where the set has no fund).
pub fn benefits_record(
    bench: &BenchReceipts<'_>,
    programs: &[&str],
    fund_cash: Option<i128>,
) -> Value {
    let mut out = Map::new();
    for key in programs {
        let mut rows = 0_u64;
        let (mut due, mut paid, mut unfunded) = (0_i128, 0_i128, 0_i128);
        for row in bench
            .public_programs
            .iter()
            .filter(|row| row.program.as_str() == *key)
        {
            rows += 1;
            due += row.due.micro_units();
            paid += row.paid.micro_units();
            unfunded += row.unfunded.micro_units();
        }
        out.insert(
            (*key).to_owned(),
            json!([rows, money(due), money(paid), money(unfunded)]),
        );
    }
    out.insert(
        "fund_cash_micros".to_owned(),
        fund_cash.map_or(Value::Null, money),
    );
    Value::Object(out)
}

/// People at work and looking for work after the period's moves, by scope of the pool's site:
/// `[at_work, looking]`, summed over the closing members.
pub fn jobs_after_moves(
    census: &Census,
    closing_members: &[PoolMembers],
    staffing: &StaffingState,
) -> Value {
    let sites: BTreeMap<StaffingPoolId, SiteId> = staffing
        .pools()
        .iter()
        .map(|pool| (pool.binding().pool_id(), pool.binding().site_id()))
        .collect();
    let mut by = BTreeMap::<&'static str, [u64; 2]>::new();
    for held in closing_members {
        let site = sites.get(&held.pool_id).expect("every pool has a site");
        let entry = by.entry(census.site(*site).scope).or_default();
        for member in &held.members {
            entry[0] += member.employed();
            entry[1] += member.reserve();
        }
    }
    json!(by)
}

/// The record's legend with the bench's own columns beside the tick's.
pub fn bench_columns() -> Value {
    let mut legend = columns();
    let object = legend.as_object_mut().expect("the legend is an object");
    object.insert(
        "market".to_owned(),
        json!([
            "short_markets",
            "demand_at_quote",
            "sold_quantity",
            "highest_clearing_price_micros",
            "quote_of_that_row_micros",
            "county_or_region_of_that_row"
        ]),
    );
    object.insert(
        "rules".to_owned(),
        json!({
            "hiring_bound": ["rows", "rows_bound_below_asked", "sum_asked_less_bound_hours"],
            "moves": ["rows", "persons"],
            "stops": ["rows", "could_not_pay", "held"],
            "resting_prices": "rows",
            "resting_to_cost": "rows",
            "restarts": ["restarted", "failed", "no_buyer", "money_micros"],
            "owner_spare": "rows",
            "goods_offers": ["rows", "rows_with_planned_gain"],
            "spare_money_raised": "production policies raised above the period's plan",
            "programs": ["rows", "paid_micros", "unfunded_micros"],
        }),
    );
    object.insert(
        "jobs_after_moves".to_owned(),
        json!({"scope": ["at_work", "looking"]}),
    );
    object.insert(
        "public".to_owned(),
        json!({
            "note": "every figure is a pair [with a grant, without a grant] over the sites of public provisioning",
            "at_work": "persons employed at the close",
            "stops": "stop rows",
            "stops_held": "stop rows held",
            "hiring_bound_below": "hiring bound rows with bound_hours < asked_hours",
            "resting": "resting price rows",
            "raised": "resting price to cost rows",
            "restarts": ["failed", "no_buyer", "restarted"],
            "price": "[lowest, highest] unit price of their offers at the close in micros, null when none",
        }),
    );
    object.insert(
        "benefits".to_owned(),
        json!({
            "no_earner": ["rows", "due_micros", "paid_micros", "unfunded_micros"],
            "laid_off": ["rows", "due_micros", "paid_micros", "unfunded_micros"],
            "fund_cash_micros": "the fund's cash at the close, null where the set has no fund",
        }),
    );
    legend
}
