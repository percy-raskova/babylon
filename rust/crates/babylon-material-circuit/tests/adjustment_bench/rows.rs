//! The row writer: one run of the doubled world through `Runner`, reduced to the prototype's columns.

use super::compare;
use super::runs::BenchRun;
use babylon_circuit_worlds::{ids, Good, Household, Kind, PeriodResult, Place, Runner, Workplace};
use babylon_material_circuit::{
    self as engine, AccountId, CircuitAccounting, GoodId, HouseholdStandard, LaborCompensation,
    MarketMoment, MaterialCatalog, MaterialCircuitState, MonetaryCircuit, RecurringEconomy, SiteId,
    WantTier,
};
use std::collections::BTreeMap;
use std::fmt::Write as _;

const KINDS: [&str; 4] = ["utility", "farm", "clinic", "shop"];
const PLACES: [&str; 2] = ["a", "b"];
const GOODS: [&str; 3] = ["food", "utility", "care"];

/// Exact dollars from micro-units, as the prototype writes them: whole numbers bare, fractions with their
/// significant digits.
pub(crate) fn money(micro: i128) -> String {
    let sign = if micro < 0 { "-" } else { "" };
    let magnitude = micro.unsigned_abs();
    let (whole, fraction) = (magnitude / 1_000_000, magnitude % 1_000_000);
    if fraction == 0 {
        format!("{sign}{whole}")
    } else {
        let digits = format!("{fraction:06}");
        format!("{sign}{whole}.{}", digits.trim_end_matches('0'))
    }
}

fn site_name(workplace: Workplace) -> String {
    format!(
        "{}_{}",
        KINDS[workplace.kind.index()],
        PLACES[workplace.place.index()]
    )
}

fn place_name(place: Place) -> &'static str {
    PLACES[place.index()]
}

fn account_name(id: AccountId) -> String {
    match id {
        AccountId::Site(site) => Workplace::from_site(site)
            .map_or_else(|| panic!("a site outside the doubled world"), site_name),
        AccountId::Household(principal) => match Household::from_principal(principal) {
            Some(Household::Workers(workplace)) => format!("w_{}", site_name(workplace)),
            Some(Household::Owner(place)) => format!("owner_{}", place_name(place)),
            Some(Household::Supported(place)) => format!("supported_{}", place_name(place)),
            None => panic!("a household outside the doubled world"),
        },
        AccountId::Public(public) if public == ids::fund() => "fund".to_owned(),
        AccountId::Public(_) => "public".to_owned(),
        other => panic!("an account outside the doubled world: {other:?}"),
    }
}

fn standard_name(standard: HouseholdStandard) -> &'static str {
    match standard {
        HouseholdStandard::GoingWithout => "going_without",
        HouseholdStandard::GettingBy => "getting_by",
        HouseholdStandard::Comfortable => "comfortable",
        HouseholdStandard::Affluent => "affluent",
    }
}

/// One line of a run, in column order.
#[derive(Default)]
struct Line {
    columns: Vec<(String, String)>,
}

impl Line {
    #[allow(
        clippy::needless_pass_by_value,
        reason = "callers pass small Copy numbers and literals by value"
    )]
    fn put(&mut self, name: impl Into<String>, value: impl ToString) {
        self.columns.push((name.into(), value.to_string()));
    }

    fn money(&mut self, name: impl Into<String>, micro: i128) {
        self.put(name, money(micro));
    }

    /// One column for each workplace, in the order of the prototype's sites.
    fn each_site(&mut self, prefix: &str, values: &[u64; 8]) {
        for workplace in Workplace::ALL {
            self.put(
                format!("{prefix}_{}", site_name(workplace)),
                values[workplace.index()],
            );
        }
    }
}

fn economy(state: &MaterialCircuitState) -> &MonetaryCircuit {
    match &state.accounting {
        CircuitAccounting::Monetary(circuit) => circuit,
        CircuitAccounting::PhysicalControl => panic!("the doubled world is monetary"),
    }
}

fn recurring(circuit: &MonetaryCircuit) -> &RecurringEconomy {
    circuit
        .recurring
        .as_ref()
        .unwrap_or_else(|| panic!("the doubled world is recurring"))
}

fn index_of(site: SiteId) -> usize {
    Workplace::from_site(site)
        .map_or_else(|| panic!("a site of the doubled world"), Workplace::index)
}

fn good_index(id: GoodId) -> usize {
    Good::from_good(id)
        .and_then(|good| Good::ALL.iter().position(|g| *g == good))
        .unwrap_or_else(|| panic!("a good of the doubled world"))
}

/// One market of the period: what its buyers could pay for at the posted price, what was sold, what was
/// turned away and the price paid, with the quote and whether it was short.
struct Market {
    quote: i128,
    demand: u64,
    sold: u64,
    turned_away: u64,
    paid: i128,
    short: bool,
}

/// The eight markets, read from the period's receipts.
fn markets(result: &PeriodResult) -> Vec<Market> {
    let receipts = &result.receipts;
    let mut sold = [0_u64; 8];
    let mut quote: [Option<i128>; 8] = [None; 8];
    for row in &receipts.service_markets {
        let i = index_of(row.site_id);
        sold[i] += row.admitted_quantity;
        quote[i] = Some(row.old_price.micro_units());
    }
    for row in &receipts.local_transfers {
        let i = index_of(row.supplier_site_id);
        if i % 4 == Kind::Farm.index() {
            sold[i] += row.quantity;
        }
    }
    for row in &receipts.local_fulfillments {
        let i = index_of(row.retailer_site_id);
        if i % 4 == Kind::Shop.index() {
            sold[i] += row.quantity;
        }
    }
    for row in &receipts.prices {
        let i = index_of(row.site_id);
        if i % 4 == Kind::Farm.index() || i % 4 == Kind::Shop.index() {
            quote[i] = Some(row.old_price.micro_units());
        }
    }
    let moments = [
        MarketMoment::Utility,
        MarketMoment::Restocking,
        MarketMoment::LocalService,
        MarketMoment::HouseholdGoods,
    ];
    Workplace::ALL
        .iter()
        .map(|workplace| {
            let i = workplace.index();
            let quote = quote[i]
                .unwrap_or_else(|| panic!("period has a quote for {}", site_name(*workplace)));
            let short = receipts
                .market_clearings
                .iter()
                .find(|row| row.site_id == workplace.site_id() && row.moment == moments[i % 4]);
            match short {
                Some(row) => Market {
                    quote,
                    demand: row.demand_at_quote,
                    sold: row.sold_quantity,
                    turned_away: row.demand_at_quote - row.sold_quantity,
                    paid: row.clearing_price.micro_units(),
                    short: true,
                },
                None => Market {
                    quote,
                    demand: sold[i],
                    sold: sold[i],
                    turned_away: 0,
                    paid: quote,
                    short: false,
                },
            }
        })
        .collect()
}

/// Cash, quotes, next prices, output and stock.
fn put_prices_and_output(
    line: &mut Line,
    catalog: &MaterialCatalog,
    result: &PeriodResult,
    state: &MaterialCircuitState,
    markets: &[Market],
) -> BTreeMap<String, i128> {
    let circuit = economy(state);
    let mut cash = BTreeMap::new();
    for row in circuit.book.snapshot().accounts {
        let name = account_name(row.id);
        line.money(format!("cash_{name}"), row.cash.micro_units());
        cash.insert(name, row.cash.micro_units());
    }
    for (workplace, market) in Workplace::ALL.iter().zip(markets) {
        line.money(format!("quote_{}", site_name(*workplace)), market.quote);
    }
    let mut next_price = [0_i128; 8];
    for row in &recurring(circuit).offers {
        next_price[index_of(row.site_id)] = row.unit_price.micro_units();
    }
    for workplace in Workplace::ALL {
        line.money(
            format!("price_next_{}", site_name(workplace)),
            next_price[workplace.index()],
        );
    }
    let mut output = [0_u64; 8];
    for row in &result.receipts.production {
        let per_batch = catalog
            .process_outputs
            .iter()
            .find(|o| o.process_id == row.process_id)
            .unwrap_or_else(|| panic!("a process of the catalog"))
            .quantity_per_batch;
        output[index_of(row.site_id)] = row.produced_batches * per_batch;
    }
    for row in &result.receipts.local_transfers {
        output[index_of(row.buyer_site_id)] += row.quantity;
    }
    line.each_site("out", &output);
    let mut stock = [0_u64; 8];
    for row in &state.inventory {
        stock[index_of(row.site_id)] += row.quantity;
    }
    for place in Place::ALL {
        for kind in [Kind::Farm, Kind::Shop] {
            let workplace = Workplace { place, kind };
            line.put(
                format!("stock_{}", site_name(workplace)),
                stock[workplace.index()],
            );
        }
    }
    cash
}

/// Hours planned, attended, used, idle and asked; people employed; the wage bill.
fn put_hours(line: &mut Line, result: &PeriodResult) {
    let mut planned = [0_u64; 8];
    let mut attended = [0_u64; 8];
    let mut used = [0_u64; 8];
    let mut idle = [0_u64; 8];
    for row in &result.receipts.labor_use {
        let i = index_of(row.site_id);
        planned[i] = row.planned_hours;
        attended[i] = row.funded_hours + row.non_wage_hours;
        used[i] = row.used_hours;
        idle[i] = row.paid_idle_hours;
    }
    line.each_site("hours_planned", &planned);
    line.each_site("hours_attended", &attended);
    line.each_site("hours_used", &used);
    line.each_site("idle_paid", &idle);
    line.each_site("asked_next", &result.asked);
    line.each_site("employed_next", &result.closing.employed);
    line.put("hours_attended", attended.iter().sum::<u64>());
    line.money(
        "wage_bill",
        result
            .receipts
            .wage_accruals
            .iter()
            .map(|row| row.amount.micro_units())
            .sum(),
    );
}

/// What each workplace must pay out before it sells in the next period: hours planned for it at its wage and
/// the service inputs of its planned batches at the posted price; the spare money is what is left.
fn put_plans(
    line: &mut Line,
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    cash: &BTreeMap<String, i128>,
) {
    let circuit = economy(state);
    let recurring = recurring(circuit);
    let mut next_hours = [0_u64; 8];
    for row in &recurring.attendance {
        if row.period == state.period {
            next_hours[index_of(row.site_id)] += row.planned_hours;
        }
    }
    let mut next_batches = [0_u64; 8];
    for row in &recurring.production {
        next_batches[index_of(row.site_id)] = row.planned_batches;
    }
    let mut wage = [0_i128; 8];
    for row in &circuit.employment {
        let LaborCompensation::Wage(rate) = row.compensation else {
            panic!("the doubled world pays wages")
        };
        wage[index_of(row.site_id)] = rate.micro_units();
    }
    let mut inputs = [0_i128; 8];
    for row in &catalog.input_coefficients {
        let user = catalog
            .process_outputs
            .iter()
            .find(|o| o.process_id == row.process_id)
            .unwrap_or_else(|| panic!("a process of the catalog"))
            .site_id;
        let i = index_of(user);
        let utility = Workplace {
            place: Workplace::ALL[i].place,
            kind: Kind::Utility,
        };
        let provider = recurring
            .offers
            .iter()
            .find(|o| o.good_id == row.good_id && o.site_id == utility.site_id())
            .unwrap_or_else(|| panic!("the utility sells the input"));
        inputs[i] += i128::from(next_batches[i] * row.quantity_per_batch)
            * provider.unit_price.micro_units();
    }
    line.each_site("next_hours", &next_hours);
    for workplace in Workplace::ALL.iter().filter(|w| w.kind != Kind::Shop) {
        line.put(
            format!("next_batches_{}", site_name(*workplace)),
            next_batches[workplace.index()],
        );
    }
    for workplace in Workplace::ALL {
        let i = workplace.index();
        let outlay = i128::from(next_hours[i]) * wage[i] + inputs[i];
        let name = site_name(workplace);
        let held = cash.get(&name).copied().unwrap_or(0);
        line.money(format!("spare_{name}"), held - outlay);
    }
}

fn put_markets(line: &mut Line, markets: &[Market]) {
    for (workplace, market) in Workplace::ALL.iter().zip(markets) {
        let name = site_name(*workplace);
        line.put(format!("mkt_{name}_demand"), market.demand);
        line.put(format!("mkt_{name}_sold"), market.sold);
        line.put(format!("mkt_{name}_turned"), market.turned_away);
        line.money(format!("mkt_{name}_paid"), market.paid);
        line.put(format!("mkt_{name}_short"), u8::from(market.short));
    }
}

/// Needs required, bought and unmet, in all and by account; units bought for wants.
fn put_needs(line: &mut Line, result: &PeriodResult) {
    let receipts = &result.receipts;
    let mut required = [0_u64; 3];
    let mut bought = [0_u64; 3];
    let mut unmet = [0_u64; 3];
    let mut by_account: BTreeMap<String, [u64; 3]> = BTreeMap::new();
    for row in &receipts.household_demand {
        bought[good_index(row.good_id)] += row.fulfilled_quantity;
    }
    for row in &receipts.household_consumption {
        let g = good_index(row.good_id);
        required[g] += row.required_quantity;
        unmet[g] += row.unmet_quantity;
        by_account
            .entry(account_name(AccountId::Household(row.principal_id)))
            .or_insert([0; 3])[g] += row.unmet_quantity;
    }
    for row in &receipts.household_services {
        let g = good_index(row.good_id);
        required[g] += row.required_quantity;
        bought[g] += row.performed_quantity;
        unmet[g] += row.unmet_quantity;
        by_account
            .entry(account_name(AccountId::Household(row.principal_id)))
            .or_insert([0; 3])[g] += row.unmet_quantity;
    }
    for (prefix, values) in [("required", required), ("bought", bought), ("unmet", unmet)] {
        for (g, good) in GOODS.iter().enumerate() {
            line.put(format!("{prefix}_{good}"), values[g]);
        }
    }
    for (name, unmet) in &by_account {
        for (g, good) in GOODS.iter().enumerate() {
            line.put(format!("unmet_{name}_{good}"), unmet[g]);
        }
    }
    let mut want_bought = [0_u64; 3];
    for row in &receipts.household_wants {
        want_bought[good_index(row.good_id)] += row.bought_quantity;
    }
    for (g, good) in GOODS.iter().enumerate() {
        line.put(format!("want_units_{good}"), want_bought[g]);
    }
}

/// The tiers' values, each household's standard, the programs, the taxes and the money.
fn put_standards_and_public(line: &mut Line, result: &PeriodResult) {
    let receipts = &result.receipts;
    let mut tier = [[0_i128; 2]; 2];
    let mut standards: BTreeMap<String, HouseholdStandard> = BTreeMap::new();
    for row in &receipts.household_tiers {
        let slot = match row.tier {
            WantTier::Comfort => 0,
            WantTier::Luxury => 1,
        };
        tier[slot][0] += row.wanted_value.micro_units();
        tier[slot][1] += row.bought_value.micro_units();
        standards
            .entry(account_name(AccountId::Household(row.principal_id)))
            .or_insert_with(|| {
                engine::household_standard(
                    row.principal_id,
                    &receipts.household_consumption,
                    &receipts.household_services,
                    &receipts.household_tiers,
                )
                .unwrap_or_else(|error| panic!("every account has both tier rows: {error:?}"))
            });
    }
    line.money("want_comfort_wanted", tier[0][0]);
    line.money("want_comfort_bought", tier[0][1]);
    line.money("want_luxury_wanted", tier[1][0]);
    line.money("want_luxury_bought", tier[1][1]);
    for (name, standard) in &standards {
        line.put(format!("standard_{name}"), standard_name(*standard));
    }
    let mut programs: BTreeMap<String, (i128, i128, u64)> = BTreeMap::new();
    for row in &receipts.public_programs {
        let entry = programs.entry(row.program.as_str().to_owned()).or_default();
        entry.0 += row.due.micro_units();
        entry.1 += row.paid.micro_units();
        entry.2 += row.covered_persons;
    }
    for (key, (due, paid, covered)) in programs {
        line.money(format!("program_{key}_due"), due);
        line.money(format!("program_{key}_paid"), paid);
        line.put(format!("program_{key}_covered"), covered);
    }
    line.money(
        "taxes_collected",
        receipts
            .taxes
            .iter()
            .map(|r| r.collected.micro_units())
            .sum(),
    );
    line.money(
        "public_paid",
        receipts
            .public_budgets
            .iter()
            .map(|r| r.paid.micro_units())
            .chain(
                receipts
                    .public_programs
                    .iter()
                    .map(|r| r.paid.micro_units()),
            )
            .sum(),
    );
    line.money("total_money", result.summary.total_money);
}

/// One period's line, in column order.
fn line(runner: &Runner, result: &PeriodResult) -> Line {
    let catalog = runner
        .catalog()
        .unwrap_or_else(|| panic!("a step has closed under a catalog"));
    let state = runner.state();
    let markets = markets(result);
    let mut line = Line::default();
    line.put("period", result.period);
    let cash = put_prices_and_output(&mut line, catalog, result, state, &markets);
    put_hours(&mut line, result);
    put_plans(&mut line, catalog, state, &cash);
    put_markets(&mut line, &markets);
    put_needs(&mut line, result);
    put_standards_and_public(&mut line, result);
    line
}

/// One run of `periods` periods through `Runner`, reduced to its projected rows (header and one line a
/// period).
pub(crate) fn rows(run: &BenchRun, periods: u64) -> String {
    rows_and_digests(run, periods, TurnedOn::AtOpening).0
}

/// When a run's rules are turned on.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum TurnedOn {
    /// With the world, as `Runner::open_world` does.
    AtOpening,
    /// After the strikes, before the first step.
    AfterStrikes,
}

/// As `rows`, with the state's digest after each period. With `AfterStrikes`, the world opens with no rule, the
/// strikes follow, and then each rule of the world is turned on, all before the first step.
pub(crate) fn rows_and_digests(
    run: &BenchRun,
    periods: u64,
    turned: TurnedOn,
) -> (String, Vec<[u8; 32]>) {
    let mut world = run.world.clone();
    let rules = if turned == TurnedOn::AfterStrikes {
        std::mem::take(&mut world.rules)
    } else {
        Vec::new()
    };
    let mut runner =
        Runner::open_world(&world).unwrap_or_else(|error| panic!("{} opens: {error:?}", run.name));
    for (shock, places, lasts) in &run.strikes {
        runner
            .strike(*shock, *places, *lasts)
            .unwrap_or_else(|error| panic!("{} strikes: {error:?}", run.name));
    }
    for rule in rules {
        runner
            .turn_on(rule)
            .unwrap_or_else(|error| panic!("{} turns on {rule:?}: {error}", run.name));
    }
    let mut digests = Vec::new();
    let mut text = String::new();
    for index in 0..periods {
        let result = runner
            .step()
            .unwrap_or_else(|error| panic!("{} steps period {}: {error:?}", run.name, index + 1))
            .clone();
        digests.push(result.state_digest);
        let row = line(&runner, &result);
        if index == 0 {
            let header: Vec<&str> = row.columns.iter().map(|(name, _)| name.as_str()).collect();
            let mut unique = header.clone();
            unique.sort_unstable();
            unique.dedup();
            assert_eq!(unique.len(), header.len(), "column names are distinct");
            text.push_str(&header.join("\t"));
            text.push('\n');
        }
        let values: Vec<&str> = row
            .columns
            .iter()
            .map(|(_, value)| value.as_str())
            .collect();
        let _ = writeln!(text, "{}", values.join("\t"));
    }
    (compare::project(&text), digests)
}

#[cfg(test)]
mod tests {
    use super::money;

    #[test]
    fn money_is_written_as_the_prototype_writes_it() {
        assert_eq!(money(12_000_000), "12");
        assert_eq!(money(625_000), "0.625");
        assert_eq!(money(-1_500_000), "-1.5");
        assert_eq!(money(0), "0");
    }
}
