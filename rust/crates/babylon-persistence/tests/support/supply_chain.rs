//! The sellers that Wayne's households buy their needs from, and one step upstream of each, read
//! period by period from the engine's own state and receipts. Nothing here is a model of them.
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, CommodityKind, FinalDemandPrincipalId, GoodId,
    MaterialCircuitState, MonetaryCircuit, ProcessId, SiteId, UnitId,
};
use babylon_persistence::economic_catalog::{CommodityLabel, EconomicOpening};
use babylon_tick::material_replay::MaterialReplaySession;
use babylon_tick::material_world::MaterialTickReceipts;
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, BTreeSet};

pub type Session = MaterialReplaySession<HypergraphStore>;

/// The needs the recorder follows, by commodity key.
pub const NEEDS: [&str; 4] = ["food", "utility", "housing", "household_services"];

/// One site in the chain: who it is and why it is here.
#[derive(Clone, Debug)]
pub struct ChainSite {
    pub site: SiteId,
    pub label: String,
    pub location: String,
    pub roles: BTreeSet<String>,
}

/// Fixed names for the chain's ids, from the opening.
pub struct Names {
    goods: BTreeMap<(GoodId, UnitId), String>,
    sites: BTreeMap<SiteId, (String, String)>,
    processes: BTreeMap<ProcessId, (SiteId, String)>,
}

impl Names {
    /// The labels and site names are read from the opening before the catalog becomes a session.
    pub fn new(opening: &EconomicOpening) -> Self {
        let goods: BTreeMap<_, _> = opening
            .commodity_labels
            .iter()
            .map(|row: &CommodityLabel| ((row.good_id, row.unit_id), row.key.clone()))
            .collect();
        let sites = opening
            .sites
            .iter()
            .map(|row| (row.site_id, (row.label.clone(), row.location.to_string())))
            .collect();
        Self {
            goods,
            sites,
            processes: BTreeMap::new(),
        }
    }

    /// Adds the processes' sites and outputs from the session's catalog.
    pub fn with_processes(mut self, session: &Session) -> Self {
        let goods = &self.goods;
        self.processes = session
            .catalog()
            .process_outputs
            .iter()
            .map(|row| {
                let key = goods
                    .get(&(row.good_id, row.unit_id))
                    .cloned()
                    .unwrap_or_default();
                (row.process_id, (row.site_id, key))
            })
            .collect();
        self
    }

    pub fn good(&self, good: GoodId, unit: UnitId) -> String {
        self.goods
            .get(&(good, unit))
            .cloned()
            .unwrap_or_else(|| "unlabelled".to_owned())
    }

    fn key_of(&self, key: &str) -> (GoodId, UnitId) {
        *self
            .goods
            .iter()
            .find(|(_, name)| name.as_str() == key)
            .unwrap_or_else(|| panic!("a commodity labelled {key}"))
            .0
    }

    pub fn site(&self, site: SiteId) -> String {
        self.sites.get(&site).map_or_else(
            || format!("site {}", short(site)),
            |(label, location)| format!("{label} [{location}]"),
        )
    }

    fn process_good(&self, process: ProcessId) -> String {
        self.processes
            .get(&process)
            .map_or_else(|| "unlabelled".to_owned(), |(_, key)| key.clone())
    }

    fn processes_of(&self, site: SiteId) -> Vec<ProcessId> {
        self.processes
            .iter()
            .filter(|(_, (owner, _))| *owner == site)
            .map(|(process, _)| *process)
            .collect()
    }
}

/// The first six bytes of a site id, enough to tell two sites with one label apart.
pub fn short(site: SiteId) -> String {
    use std::fmt::Write as _;
    site.as_bytes()[..6]
        .iter()
        .fold(String::new(), |mut text, byte| {
            write!(text, "{byte:02x}").expect("writing to a string");
            text
        })
}

pub fn economy(session: &Session) -> &MonetaryCircuit {
    let CircuitAccounting::Monetary(economy) = &session.material().state().accounting else {
        panic!("the national campaign accounts in money")
    };
    economy
}

fn state(session: &Session) -> &MaterialCircuitState {
    session.material().state()
}

fn add_role(chain: &mut BTreeMap<SiteId, BTreeSet<String>>, site: SiteId, role: String) {
    chain.entry(site).or_default().insert(role);
}

/// Each need's seller for the given households, then every site that seller buys from.
pub fn chain_sites(
    session: &Session,
    names: &Names,
    principals: &[FinalDemandPrincipalId],
) -> Vec<ChainSite> {
    let recurring = economy(session).recurring.as_ref().expect("recurring");
    let mut chain = BTreeMap::<SiteId, BTreeSet<String>>::new();
    for need in NEEDS {
        let (good, unit) = names.key_of(need);
        for policy in recurring.household_purchases.iter().filter(|row| {
            principals.contains(&row.principal_id) && (row.good_id, row.unit_id) == (good, unit)
        }) {
            add_role(&mut chain, policy.retailer_site_id, format!("sells {need}"));
        }
    }
    let sellers: Vec<(SiteId, String)> = chain
        .keys()
        .map(|site| (*site, names.site(*site)))
        .collect();
    for (seller, label) in &sellers {
        for policy in recurring
            .replenishment
            .iter()
            .filter(|row| row.buyer_site_id == *seller)
        {
            let good = names.good(policy.good_id, policy.unit_id);
            add_role(
                &mut chain,
                policy.supplier_site_id,
                format!("supplies {good} to {label}"),
            );
        }
        for policy in session
            .catalog()
            .service_inputs
            .iter()
            .filter(|row| row.buyer_site_id == *seller)
        {
            let good = names.good(policy.good_id, policy.unit_id);
            add_role(
                &mut chain,
                policy.provider_site_id,
                format!("serves {good} to {label}"),
            );
        }
    }
    second_step(session, names, &sellers, &mut chain);
    chain
        .into_iter()
        .map(|(site, roles)| {
            let (label, location) = names
                .sites
                .get(&site)
                .cloned()
                .unwrap_or_else(|| (format!("site {}", short(site)), String::new()));
            ChainSite {
                site,
                label,
                location,
                roles,
            }
        })
        .collect()
}

/// One step further for the input every producer upstream waits on: the sites that serve
/// business services to the sellers' suppliers.
fn second_step(
    session: &Session,
    names: &Names,
    sellers: &[(SiteId, String)],
    chain: &mut BTreeMap<SiteId, BTreeSet<String>>,
) {
    let business = names.key_of("business_services");
    let upstream: Vec<(SiteId, String)> = chain
        .keys()
        .filter(|site| !sellers.iter().any(|(seller, _)| seller == *site))
        .map(|site| (*site, names.site(*site)))
        .collect();
    for (buyer, label) in &upstream {
        for policy in session
            .catalog()
            .service_inputs
            .iter()
            .filter(|row| row.buyer_site_id == *buyer && (row.good_id, row.unit_id) == business)
        {
            add_role(
                chain,
                policy.provider_site_id,
                format!("serves business_services to {label}"),
            );
        }
    }
}

fn money(amount: i128) -> Value {
    json!(amount.to_string())
}

/// Every cash floor that applies to a site, and what it gates. Fixed at the opening.
pub fn floors(session: &Session, names: &Names, site: SiteId) -> Vec<Value> {
    let economy = economy(session);
    let recurring = economy.recurring.as_ref().expect("recurring");
    let mut rows = Vec::new();
    for policy in recurring
        .replenishment
        .iter()
        .filter(|row| row.buyer_site_id == site)
    {
        rows.push(json!({
            "gates": format!("buying {} from {}", names.good(policy.good_id, policy.unit_id), names.site(policy.supplier_site_id)),
            "rule": "recurring/firms.rs replenish: spendable = cash - floor",
            "floor_micros": money(policy.cash_floor.micro_units()),
            "target_stock": policy.target_stock,
            "maximum_purchase": policy.maximum_purchase,
        }));
    }
    for policy in session
        .catalog()
        .service_inputs
        .iter()
        .filter(|row| row.buyer_site_id == site)
    {
        rows.push(json!({
            "gates": format!("buying {} from {}", names.good(policy.good_id, policy.unit_id), names.site(policy.provider_site_id)),
            "rule": "service input admission",
            "floor_micros": money(policy.cash_floor.micro_units()),
            "quantity_per_period": policy.quantity_per_period,
            "maximum_purchase": policy.maximum_purchase,
        }));
    }
    rows.extend(financial_floors(session, site));
    rows
}

fn financial_floors(session: &Session, site: SiteId) -> Vec<Value> {
    let economy = economy(session);
    let financial = &economy.financial;
    let mut rows = Vec::new();
    for tax in financial
        .taxes
        .iter()
        .filter(|row| row.payer == AccountId::Site(site))
    {
        rows.push(json!({
            "gates": format!("{:?} tax", tax.basis),
            "floor_micros": money(tax.cash_floor.micro_units()),
        }));
    }
    for row in financial
        .distributions
        .iter()
        .filter(|row| row.issuer_site_id == site)
    {
        rows.push(json!({
            "gates": "distributions to owners",
            "floor_micros": money(row.cash_floor.micro_units()),
            "period_cap_micros": money(row.period_cap.micro_units()),
        }));
    }
    let processes: BTreeSet<_> = session
        .catalog()
        .process_outputs
        .iter()
        .filter(|row| row.site_id == site)
        .map(|row| row.process_id)
        .collect();
    if let Some(equipment) = session.catalog().equipment_content() {
        for row in equipment
            .investment_policies
            .iter()
            .filter(|row| processes.contains(&row.process_id))
        {
            rows.push(json!({
                "gates": "equipment investment",
                "floor_micros": money(row.cash_floor.micro_units()),
            }));
        }
    }
    rows
}

fn cash(session: &Session, site: SiteId) -> i128 {
    economy(session)
        .book
        .cash(AccountId::Site(site))
        .map_or(0, Currency::micro_units)
}

fn inventory(state: &MaterialCircuitState, names: &Names, site: SiteId) -> Map<String, Value> {
    state
        .inventory
        .iter()
        .filter(|row| row.site_id == site)
        .map(|row| (names.good(row.good_id, row.unit_id), json!(row.quantity)))
        .collect()
}

/// Goods ordered by the site and not yet shipped by the supplier, goods it was ordered and has not
/// shipped, and its goods in transit with the earliest and latest stage arrival.
fn order_book(state: &MaterialCircuitState, names: &Names, site: SiteId) -> Value {
    let mut awaited = BTreeMap::<String, u64>::new();
    let mut owed = BTreeMap::<String, u64>::new();
    for row in &state.orders {
        let backlog = row.ordered - row.shipped;
        if row.buyer_site_id == site {
            *awaited
                .entry(names.good(row.good_id, row.unit_id))
                .or_default() += backlog;
        }
        if row.supplier_site_id == site {
            *owed
                .entry(names.good(row.good_id, row.unit_id))
                .or_default() += backlog;
        }
    }
    let mut transit = BTreeMap::<String, [u64; 3]>::new();
    for lot in state
        .freight
        .iter()
        .filter(|lot| lot.destination_site_id == site)
    {
        let row = transit
            .entry(names.good(lot.good_id, lot.unit_id))
            .or_insert([0, u64::MAX, 0]);
        row[0] += lot.quantity;
        row[1] = row[1].min(lot.stage_arrival_period);
        row[2] = row[2].max(lot.stage_arrival_period);
    }
    json!({
        "ordered_not_shipped_to_it": awaited,
        "ordered_from_it_not_shipped": owed,
        "in_transit_quantity_first_last_stage_arrival": triples(transit),
    })
}

/// The site at the opening of a period: cash, stock, commitments, labor, capacity and prices.
pub fn site_opening(session: &Session, names: &Names, site: SiteId) -> Value {
    let state = state(session);
    let recurring = economy(session).recurring.as_ref().expect("recurring");
    let processes = names.processes_of(site);
    let by_process = |process: &ProcessId| names.process_good(*process);
    let commitments: Vec<Value> = state
        .production_commitments
        .iter()
        .filter(|row| row.site_id == site && row.period == state.period)
        .map(|row| json!([by_process(&row.process_id), row.planned_batches]))
        .collect();
    let capacity: Vec<Value> = state
        .capacities
        .iter()
        .filter(|row| row.site_id == site && row.period == state.period)
        .map(|row| json!([by_process(&row.process_id), row.available_batches]))
        .collect();
    let demand_cap: Vec<Value> = recurring
        .production
        .iter()
        .filter(|row| processes.contains(&row.process_id))
        .map(|row| {
            json!([
                by_process(&row.process_id),
                row.planned_batches,
                row.output_buffer
            ])
        })
        .collect();
    let labor: u64 = state
        .labor
        .iter()
        .filter(|row| row.site_id == site && row.period == state.period)
        .map(|row| row.available)
        .sum();
    let planned_hours: u64 = recurring
        .attendance
        .iter()
        .filter(|row| row.site_id == site)
        .map(|row| row.planned_hours)
        .sum();
    let prices: Map<String, Value> = recurring
        .offers
        .iter()
        .filter(|row| row.site_id == site)
        .map(|row| {
            (
                names.good(row.good_id, row.unit_id),
                money(row.unit_price.micro_units()),
            )
        })
        .collect();
    json!({
        "cash_micros": money(cash(session, site)),
        "inventory": inventory(state, names, site),
        "committed_batches": commitments,
        "capacity_batches": capacity,
        "demand_planned_batches_and_buffer": demand_cap,
        "labor_available_hours": labor,
        "attendance_planned_hours": planned_hours,
        "prices_micros": prices,
        "orders": order_book(state, names, site),
    })
}

/// The site after the commit: its cash and stock.
pub fn site_after(session: &Session, names: &Names, site: SiteId) -> Value {
    json!({
        "cash_micros": money(cash(session, site)),
        "inventory": inventory(state(session), names, site),
    })
}

fn add3(map: &mut BTreeMap<String, [u64; 3]>, key: String, values: [u64; 3]) {
    let row = map.entry(key).or_default();
    for (sum, value) in row.iter_mut().zip(values) {
        *sum += value;
    }
}

fn triples(map: BTreeMap<String, [u64; 3]>) -> Map<String, Value> {
    map.into_iter()
        .map(|(key, row)| (key, json!(row)))
        .collect()
}

/// What the site bought this period: goods by replenishment, services by input orders.
fn purchases(receipts: &MaterialTickReceipts, names: &Names, site: SiteId) -> Value {
    let goods: Vec<Value> = receipts
        .procurement
        .iter()
        .filter(|row| row.buyer_site_id == site)
        .map(|row| {
            json!({
                "good": names.good(row.good_id, row.unit_id),
                "from": names.site(row.supplier_site_id),
                "on_hand": row.on_hand,
                "inbound": row.outstanding_inbound,
                "target": row.target_stock,
                "desired": row.desired_quantity,
                "admitted": row.admitted_quantity,
                "price_micros": money(row.unit_price.micro_units()),
            })
        })
        .collect();
    let mut services = BTreeMap::new();
    for row in receipts
        .service_performance
        .iter()
        .filter(|row| row.buyer == AccountId::Site(site))
    {
        let key = format!(
            "{} from {}",
            names.good(row.good_id, row.unit_id),
            names.site(row.provider_site_id)
        );
        let values = [
            row.requested_quantity,
            row.admitted_quantity,
            row.performed_quantity,
        ];
        add3(&mut services, key, values);
    }
    let mut received = BTreeMap::new();
    for row in receipts
        .local_transfers
        .iter()
        .filter(|row| row.buyer_site_id == site)
    {
        *received
            .entry(names.good(row.good_id, row.unit_id))
            .or_insert(0_u64) += row.quantity;
    }
    json!({
        "goods_ordered": goods,
        "services_requested_admitted_performed": triples(services),
        "local_goods_received": received,
    })
}

/// What the site sold this period: to households, to sites by delivery orders, and services.
fn sales(receipts: &MaterialTickReceipts, names: &Names, site: SiteId) -> Value {
    let mut households = BTreeMap::new();
    for row in receipts
        .household_demand
        .iter()
        .filter(|row| row.retailer_site_id == site)
    {
        let values = [
            row.requested_quantity,
            row.admitted_quantity,
            row.fulfilled_quantity,
        ];
        add3(
            &mut households,
            names.good(row.good_id, row.unit_id),
            values,
        );
    }
    let mut orders = BTreeMap::new();
    for row in receipts
        .procurement
        .iter()
        .filter(|row| row.supplier_site_id == site)
    {
        let values = [row.desired_quantity, row.admitted_quantity, 0];
        add3(&mut orders, names.good(row.good_id, row.unit_id), values);
    }
    let mut services = BTreeMap::new();
    for row in receipts
        .service_performance
        .iter()
        .filter(|row| row.provider_site_id == site)
    {
        let buyer = match row.buyer {
            AccountId::Household(_) => "households",
            AccountId::Site(_) => "sites",
            _ => "others",
        };
        let key = format!("{} to {buyer}", names.good(row.good_id, row.unit_id));
        let values = [
            row.requested_quantity,
            row.admitted_quantity,
            row.performed_quantity,
        ];
        add3(&mut services, key, values);
    }
    let mut sent = BTreeMap::new();
    for row in receipts
        .local_transfers
        .iter()
        .filter(|row| row.supplier_site_id == site)
    {
        *sent
            .entry(names.good(row.good_id, row.unit_id))
            .or_insert(0_u64) += row.quantity;
    }
    json!({
        "households_requested_admitted_fulfilled": triples(households),
        "orders_desired_admitted": orders.into_iter().map(|(k, v)| (k, json!([v[0], v[1]]))).collect::<Map<_, _>>(),
        "services_requested_admitted_performed": triples(services),
        "local_goods_sent": sent,
    })
}

fn production(receipts: &MaterialTickReceipts, names: &Names, site: SiteId) -> Value {
    let produced: Vec<Value> = receipts
        .production
        .iter()
        .filter(|row| row.site_id == site)
        .map(|row| {
            json!({
                "output": names.process_good(row.process_id),
                "planned_batches": row.planned_batches,
                "produced_batches": row.produced_batches,
            })
        })
        .collect();
    let plans: Vec<Value> = receipts
        .production_plans
        .iter()
        .filter(|row| row.site_id == site)
        .map(|row| {
            json!({
                "output": names.process_good(row.process_id),
                "dispatched": row.dispatched_quantity,
                "unshipped": row.unshipped_quantity,
                "closing_stock": row.closing_output_stock,
                "buffer": row.output_buffer,
                "next_planned_batches": row.planned_batches,
            })
        })
        .collect();
    json!({ "produced": produced, "goods_plans": plans, "services": service_rows(receipts, names, site) })
}

fn service_rows(receipts: &MaterialTickReceipts, names: &Names, site: SiteId) -> Vec<Value> {
    let outputs: BTreeMap<_, _> = receipts
        .service_outputs
        .iter()
        .filter(|row| row.site_id == site)
        .map(|row| (row.process_id, row))
        .collect();
    receipts
        .service_markets
        .iter()
        .filter(|row| row.site_id == site)
        .map(|row| {
            let output = outputs.get(&row.process_id);
            json!({
                "output": names.good(row.good_id, row.unit_id),
                "requested": row.requested_quantity,
                "admitted": row.admitted_quantity,
                "performed": row.performed_quantity,
                "available_capacity": row.available_capacity,
                "produced": output.map(|o| o.produced_quantity),
                "expired": output.map(|o| o.expired_quantity),
                "next_planned_quantity": row.planned_quantity,
                "direct_cost_micros": money(row.direct_cost.micro_units()),
                "price_micros": [money(row.old_price.micro_units()), money(row.next_price.micro_units())],
                "price_reason": format!("{:?}", row.reason),
            })
        })
        .collect()
}

fn labor(receipts: &MaterialTickReceipts, site: SiteId) -> Value {
    let mut hours = [0_u64; 7];
    for row in receipts.labor_use.iter().filter(|row| row.site_id == site) {
        let values = [
            row.available_hours,
            row.planned_hours,
            row.funded_hours,
            row.unfunded_hours,
            row.used_hours,
            row.paid_idle_hours,
            row.non_wage_hours,
        ];
        for (sum, value) in hours.iter_mut().zip(values) {
            *sum += value;
        }
    }
    let wages: i128 = receipts
        .wage_accruals
        .iter()
        .filter(|row| row.employer == AccountId::Site(site))
        .map(|row| row.amount.micro_units())
        .sum();
    let mut staff = [0_u64; 4];
    for row in receipts
        .staffing_members
        .iter()
        .filter(|row| row.site_id == site)
    {
        let values = [
            row.opening_employed,
            row.closing_employed,
            row.hires,
            row.separations,
        ];
        for (sum, value) in staff.iter_mut().zip(values) {
            *sum += value;
        }
    }
    json!({
        "available_planned_funded_unfunded_used_paid_idle_non_wage_hours": hours,
        "wages_accrued_micros": money(wages),
        "employed_opening_closing_hires_separations": staff,
    })
}

fn finance(receipts: &MaterialTickReceipts, site: SiteId) -> Value {
    let taxes: Vec<Value> = receipts
        .taxes
        .iter()
        .filter(|row| row.payer == AccountId::Site(site))
        .map(|row| {
            json!([
                format!("{:?}", row.basis),
                money(row.assessed.micro_units()),
                money(row.collected.micro_units())
            ])
        })
        .collect();
    let distributed: i128 = receipts
        .distributions
        .iter()
        .filter(|row| row.issuer_site_id == site)
        .map(|row| row.paid.micro_units())
        .sum();
    let wear: u64 = receipts
        .equipment_wear
        .iter()
        .filter(|row| row.site_id == site)
        .map(|row| row.remaining_service_batches)
        .sum();
    let invested: u64 = receipts
        .investment
        .iter()
        .filter(|row| row.site_id == site)
        .map(|row| row.installed_units)
        .sum();
    json!({
        "taxes_basis_assessed_collected": taxes,
        "distributed_micros": money(distributed),
        "equipment_remaining_service_batches": wear,
        "equipment_installed_units": invested,
    })
}

/// The site's receipts for the period just closed.
pub fn site_close(receipts: &MaterialTickReceipts, names: &Names, site: SiteId) -> Value {
    json!({
        "purchases": purchases(receipts, names, site),
        "sales": sales(receipts, names, site),
        "production": production(receipts, names, site),
        "labor": labor(receipts, site),
        "finance": finance(receipts, site),
    })
}

/// Required and unmet quantities of each followed need, summed over the households of a county.
pub fn county_needs(
    session: &Session,
    receipts: &MaterialTickReceipts,
    names: &Names,
    principals: &BTreeSet<FinalDemandPrincipalId>,
) -> Map<String, Value> {
    let mut out = Map::new();
    let services: BTreeSet<_> = session
        .catalog()
        .commodities
        .iter()
        .filter(|row| matches!(row.kind, CommodityKind::PeriodService { .. }))
        .map(|row| (row.good_id, row.unit_id))
        .collect();
    for need in NEEDS {
        let key = names.key_of(need);
        let [required, unmet] = if services.contains(&key) {
            receipts
                .household_services
                .iter()
                .filter(|row| {
                    principals.contains(&row.principal_id) && (row.good_id, row.unit_id) == key
                })
                .fold([0, 0], |[r, u], row| {
                    [r + row.required_quantity, u + row.unmet_quantity]
                })
        } else {
            receipts
                .household_consumption
                .iter()
                .filter(|row| {
                    principals.contains(&row.principal_id) && (row.good_id, row.unit_id) == key
                })
                .fold([0, 0], |[r, u], row| {
                    [r + row.required_quantity, u + row.unmet_quantity]
                })
        };
        out.insert(
            need.to_owned(),
            json!({ "required": required, "unmet": unmet }),
        );
    }
    out
}
