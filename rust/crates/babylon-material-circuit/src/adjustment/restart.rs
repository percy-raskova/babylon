//! An owner restarts a stopped workplace with the owner's own money (A17, A19 of ADR314; ADR318 L1), as mended in
//! round ten: the restart sits at the very end of the close, before staffing.
//!
//! In the order they act: a price that rested under one unit's cost is raised to it; every workplace counts
//! its quiet periods; a workplace that employed nobody for three quiet periods is tested on what its buyers
//! would pay and on whether the inputs of one batch can be had; its owner puts in the money from the owner's
//! own spare; and the bound of the next period is reckoned again, so that a restarted workplace may hire at
//! once. The money is capital: never paid back, never earnings.

use std::collections::{BTreeMap, BTreeSet};
use std::result::Result as StdResult;

use babylon_kernel::currency::Currency;

use super::bound::{self, HiringBound};
use super::policy;
use super::receipts::{
    AdjustmentReceipt, OwnerSpareReceipt, RestartReceipt, RestartTest, RestingPriceReceipt,
    RestingPriceToCostReceipt,
};
use super::rest::{self, Product};
use super::standing::{StopHold, WorkplaceStanding, WorkplaceStandingRow};
use crate::{
    AccountId, CashTransferPurpose, CircuitAccounting, FinalDemandPrincipalId, GoodId,
    HistoricalCostBook, MaterialCatalog, MaterialCircuitError, MaterialCircuitState,
    MaterialCircuitTransition, MonetaryBook, MonetaryCircuit, MoneyTransferReceipt, PricePolicy,
    ProcessId, PublicTransferTreatment, RecurringEconomy, SiteId, UnitId,
};

type Result<T> = StdResult<T, MaterialCircuitError>;

/// The quiet periods a workplace counts before its restart is tested.
pub const RESTART_QUIET_PERIODS: u64 = 3;

/// What one batch of a workplace costs, makes, and sells for.
struct Output {
    /// The units of one batch: the process's output, or one unit for a merchant.
    per_batch: u64,
    /// The batches its capacity runs: the nameplate, or without limit for a merchant.
    nameplate: u64,
    /// The posted price of its product.
    price: i128,
}

/// One workplace that passed the sales test, with the figures its buyer reads.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Candidate {
    pub(crate) site: SiteId,
    /// What the batches it would run cost over the periods of outlay.
    pub(crate) plan: i128,
    /// What it would earn in a period by the test's own figures.
    pub(crate) earn: i128,
    /// What its owner puts in: the plan less the cash it holds.
    pub(crate) money: i128,
}

/// What the restart's test found of one workplace.
struct Tried {
    site: SiteId,
    cost: i128,
    turned: u64,
    inputs_short: bool,
    candidate: Option<Candidate>,
}

/// The money a restart puts in: the plan less the cash the workplace holds. `None` when that is nothing.
pub(crate) fn money_to_put_in(plan: i128, cash: i128) -> Option<i128> {
    let money = plan.checked_sub(cash)?;
    (money > 0).then_some(money)
}

/// The candidates in the order of what each would earn on the money put in, highest first; ties by site.
pub(crate) fn rank(candidates: &mut [Candidate]) {
    candidates.sort_by(|a, b| {
        let left = a.earn.checked_mul(b.plan);
        let right = b.earn.checked_mul(a.plan);
        right.cmp(&left).then(a.site.cmp(&b.site))
    });
}

/// The price a resting price is raised to: one unit's cost, rounded up to the micro-unit. `None` when the price
/// stands at it or above, or the batch makes nothing.
pub(crate) fn raised_price(batch_cost: i128, per_batch: u64, price: i128) -> Option<i128> {
    let output = i128::from(per_batch);
    if output <= 0 {
        return None;
    }
    let unit = batch_cost.checked_add(output.checked_sub(1)?)? / output;
    (price < unit).then_some(unit)
}

/// Whether a workplace is tested: it offered no hours and has been quiet long enough.
pub(crate) fn is_tested(row: &WorkplaceStandingRow, offered_hours: bool) -> bool {
    !offered_hours && row.quiet_periods >= RESTART_QUIET_PERIODS
}

/// One more close of a workplace: both counters go to 0 if it made or sold anything, else up by one.
pub(crate) fn count(row: &mut WorkplaceStandingRow, made_or_sold: bool) -> Result<()> {
    if made_or_sold {
        row.periods_since_work = 0;
        row.quiet_periods = 0;
    } else {
        row.periods_since_work = row
            .periods_since_work
            .checked_add(1)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        row.quiet_periods = row
            .quiet_periods
            .checked_add(1)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(())
}

/// Seat the candidates in order: each is bought by its owner when what is left of that owner's spare covers the
/// money, and takes it out. A candidate whose owner cannot pay, or that has no owner, gets `None`.
pub(crate) fn seat(
    candidates: &[Candidate],
    owner_of: impl Fn(SiteId) -> Option<AccountId>,
    spare: &mut BTreeMap<AccountId, i128>,
) -> Vec<(SiteId, Option<AccountId>)> {
    candidates
        .iter()
        .map(|candidate| {
            let owner = owner_of(candidate.site).filter(|owner| {
                spare
                    .get(owner)
                    .is_some_and(|left| *left >= candidate.money)
            });
            if let Some(left) = owner.and_then(|owner| spare.get_mut(&owner)) {
                *left -= candidate.money;
            }
            (candidate.site, owner)
        })
        .collect()
}

/// An owner's capital paid into a workplace: the money moves with its receipt and the cost book carries it.
///
/// # Errors
/// A circuit refusal when the owner holds less than `money` or the book does not hold the accounts.
pub(crate) fn put_in(
    book: &mut MonetaryBook,
    costs: &mut HistoricalCostBook,
    owner: AccountId,
    site: SiteId,
    money: i128,
) -> Result<MoneyTransferReceipt> {
    let amount = Currency::from_micro_units(money);
    let receipt = book.transfer_cash(
        owner,
        AccountId::Site(site),
        amount,
        CashTransferPurpose::CapitalContribution,
    )?;
    costs.add_contribution(owner, site, amount)?;
    Ok(receipt)
}

fn economy_of(state: &MaterialCircuitState) -> Result<(&MonetaryCircuit, &RecurringEconomy)> {
    match &state.accounting {
        CircuitAccounting::Monetary(economy) => economy
            .recurring
            .as_deref()
            .map(|recurring| (&**economy, recurring))
            .ok_or(MaterialCircuitError::MonetaryInvariant),
        CircuitAccounting::PhysicalControl => Err(MaterialCircuitError::MonetaryInvariant),
    }
}

/// The first row of each key, in row order: what a `find` from the start of the rows returned.
fn first_by<T, K: Ord, V>(
    rows: &[T],
    key: impl Fn(&T) -> K,
    value: impl Fn(&T) -> V,
) -> BTreeMap<K, V> {
    let mut table = BTreeMap::new();
    for row in rows {
        table.entry(key(row)).or_insert_with(|| value(row));
    }
    table
}

/// Every row of each key, in row order: what a `filter` over the rows returned.
fn all_by<T, K: Ord, V>(
    rows: &[T],
    key: impl Fn(&T) -> K,
    value: impl Fn(&T) -> V,
) -> BTreeMap<K, Vec<V>> {
    let mut table: BTreeMap<K, Vec<V>> = BTreeMap::new();
    for row in rows {
        table.entry(key(row)).or_default().push(value(row));
    }
    table
}

/// The rows of a table at a key, or none.
fn rows_at<'a, K: Ord, V>(table: &'a BTreeMap<K, Vec<V>>, key: &K) -> &'a [V] {
    table.get(key).map_or(&[], Vec::as_slice)
}

/// The checked sum of quantities.
fn total<'a>(mut quantities: impl Iterator<Item = &'a u64>) -> Result<u64> {
    quantities
        .try_fold(0_u64, |sum, quantity| sum.checked_add(*quantity))
        .ok_or(MaterialCircuitError::Arithmetic)
}

/// What the restart reads of the offers, as they stand when the tables are made.
struct OfferTables {
    /// The price of the first offer of each product.
    first: BTreeMap<Product, i128>,
    /// The highest price among the offers of each product.
    own_top: BTreeMap<Product, i128>,
    /// The highest price of each good among all its sellers.
    top: BTreeMap<(GoodId, UnitId), i128>,
    /// The lowest `maximum` among a site's offers whose pricing has a range.
    ceiling: BTreeMap<SiteId, i128>,
}

impl OfferTables {
    fn of(recurring: &RecurringEconomy) -> Self {
        let mut tables = Self {
            first: BTreeMap::new(),
            own_top: BTreeMap::new(),
            top: BTreeMap::new(),
            ceiling: BTreeMap::new(),
        };
        for offer in &recurring.offers {
            let price = offer.unit_price.micro_units();
            let product = (offer.site_id, offer.good_id, offer.unit_id);
            tables.first.entry(product).or_insert(price);
            let own = tables.own_top.entry(product).or_insert(price);
            *own = (*own).max(price);
            let top = tables
                .top
                .entry((offer.good_id, offer.unit_id))
                .or_insert(price);
            *top = (*top).max(price);
            if let PricePolicy::ServiceResponsive { maximum, .. }
            | PricePolicy::Responsive { maximum, .. } = offer.pricing
            {
                let ceiling = tables
                    .ceiling
                    .entry(offer.site_id)
                    .or_insert(maximum.micro_units());
                *ceiling = (*ceiling).min(maximum.micro_units());
            }
        }
        tables
    }
}

/// What the restart reads of the catalog and of the recurring economy's policies: they stand through the close.
struct PlantTables {
    /// The process of the first production policy of each site.
    process_at: BTreeMap<SiteId, ProcessId>,
    /// The batches planned by the first production policy of each process.
    planned: BTreeMap<ProcessId, u64>,
    /// The hours of one batch of each process, row by row.
    labor: BTreeMap<ProcessId, Vec<u64>>,
    /// The input coefficients of each process: good, unit and units a batch.
    inputs: BTreeMap<ProcessId, Vec<(GoodId, UnitId, u64)>>,
    /// The handling coefficients of each site: good, unit and hours a unit.
    handling: BTreeMap<SiteId, Vec<(GoodId, UnitId, i128)>>,
    /// The provider of the first service input of each (buyer, good, unit), and the most it may buy a period.
    provider: BTreeMap<Product, (SiteId, u64)>,
    /// The supplier of the first replenishment row of each (buyer, good, unit).
    supplier: BTreeMap<Product, SiteId>,
    /// The first output of each process: good, unit and units a batch.
    output_of_process: BTreeMap<ProcessId, (GoodId, UnitId, u64)>,
    /// The outputs of each (site, good, unit): process and units a batch.
    outputs: BTreeMap<Product, Vec<(ProcessId, u64)>>,
    /// The retailer of the first purchase policy of each (principal, good, unit).
    retailer: BTreeMap<(FinalDemandPrincipalId, GoodId, UnitId), SiteId>,
}

impl PlantTables {
    fn of(catalog: &MaterialCatalog, recurring: &RecurringEconomy) -> Self {
        Self {
            process_at: first_by(
                &recurring.production,
                |row| row.site_id,
                |row| row.process_id,
            ),
            planned: first_by(
                &recurring.production,
                |row| row.process_id,
                |row| row.planned_batches,
            ),
            labor: all_by(
                &catalog.labor_coefficients,
                |row| row.process_id,
                |row| row.quantity_per_batch,
            ),
            inputs: all_by(
                &catalog.input_coefficients,
                |row| row.process_id,
                |row| (row.good_id, row.unit_id, row.quantity_per_batch),
            ),
            handling: all_by(
                &catalog.handling_coefficients,
                |row| row.site_id,
                |row| (row.good_id, row.unit_id, i128::from(row.hours_per_unit)),
            ),
            provider: first_by(
                &catalog.service_inputs,
                |row| (row.buyer_site_id, row.good_id, row.unit_id),
                |row| {
                    (
                        row.provider_site_id,
                        row.quantity_per_period.min(row.maximum_purchase),
                    )
                },
            ),
            supplier: first_by(
                &recurring.replenishment,
                |row| (row.buyer_site_id, row.good_id, row.unit_id),
                |row| row.supplier_site_id,
            ),
            output_of_process: first_by(
                &catalog.process_outputs,
                |row| row.process_id,
                |row| (row.good_id, row.unit_id, row.quantity_per_batch),
            ),
            outputs: all_by(
                &catalog.process_outputs,
                |row| (row.site_id, row.good_id, row.unit_id),
                |row| (row.process_id, row.quantity_per_batch),
            ),
            retailer: first_by(
                &recurring.household_purchases,
                |row| (row.principal_id, row.good_id, row.unit_id),
                |row| row.retailer_site_id,
            ),
        }
    }
}

/// What the restart reads of the period's receipts, row by row in the order they stand.
struct PeriodTables {
    /// What each seller's markets wanted at the quote and sold: both quantities of each clearing.
    clearings: BTreeMap<SiteId, Vec<(u64, u64)>>,
    /// The units each supplier's local transfers moved.
    shipped_by: BTreeMap<SiteId, Vec<u64>>,
    /// The units each buyer's local transfers took in.
    received_by: BTreeMap<SiteId, Vec<u64>>,
    /// The units each retailer's local fulfillments handed over.
    retailed_by: BTreeMap<SiteId, Vec<u64>>,
    /// The units each site's service markets performed.
    performed_by: BTreeMap<SiteId, Vec<u64>>,
    /// The production receipts of each site: process and batches made.
    made_by: BTreeMap<SiteId, Vec<(ProcessId, u64)>>,
    /// The batches made, by process.
    batches_of: BTreeMap<ProcessId, Vec<u64>>,
    /// What each provider performed of a service, by buyer.
    served: BTreeMap<Product, Vec<(AccountId, u64)>>,
    /// What each supplier's local transfers moved of a product, by buyer's site.
    sent: BTreeMap<Product, Vec<(SiteId, u64)>>,
    /// What each retailer's local fulfillments handed over of a product.
    retailed: BTreeMap<Product, Vec<u64>>,
    /// What each household requires of a good or a service, goods first.
    wanted: BTreeMap<FinalDemandPrincipalId, Vec<(GoodId, UnitId, u64)>>,
}

impl PeriodTables {
    fn of(transition: &MaterialCircuitTransition) -> Self {
        let mut wanted = all_by(
            &transition.household_consumption,
            |row| row.principal_id,
            |row| (row.good_id, row.unit_id, row.required_quantity),
        );
        for row in &transition.household_services {
            wanted.entry(row.principal_id).or_default().push((
                row.good_id,
                row.unit_id,
                row.required_quantity,
            ));
        }
        Self {
            clearings: all_by(
                &transition.market_clearings,
                |row| row.site_id,
                |row| (row.demand_at_quote, row.sold_quantity),
            ),
            shipped_by: all_by(
                &transition.local_transfers,
                |row| row.supplier_site_id,
                |row| row.quantity,
            ),
            received_by: all_by(
                &transition.local_transfers,
                |row| row.buyer_site_id,
                |row| row.quantity,
            ),
            retailed_by: all_by(
                &transition.local_fulfillments,
                |row| row.retailer_site_id,
                |row| row.quantity,
            ),
            performed_by: all_by(
                &transition.service_markets,
                |row| row.site_id,
                |row| row.performed_quantity,
            ),
            made_by: all_by(
                &transition.production,
                |row| row.site_id,
                |row| (row.process_id, row.produced_batches),
            ),
            batches_of: all_by(
                &transition.production,
                |row| row.process_id,
                |row| row.produced_batches,
            ),
            served: all_by(
                &transition.service_performance,
                |row| (row.provider_site_id, row.good_id, row.unit_id),
                |row| (row.buyer, row.performed_quantity),
            ),
            sent: all_by(
                &transition.local_transfers,
                |row| (row.supplier_site_id, row.good_id, row.unit_id),
                |row| (row.buyer_site_id, row.quantity),
            ),
            retailed: all_by(
                &transition.local_fulfillments,
                |row| (row.retailer_site_id, row.good_id, row.unit_id),
                |row| row.quantity,
            ),
            wanted,
        }
    }
}

/// What the restart reads of the state's own books: they stand through the restart.
struct LedgerTables {
    /// The units each site holds of each product.
    held: BTreeMap<Product, u64>,
    /// The holder of the first ownership claim of each workplace.
    holder: BTreeMap<SiteId, AccountId>,
    /// The sites named as recipients of an operating grant by some public allocation.
    granted: BTreeSet<SiteId>,
    /// The largest `Wage` rate of each site's employment terms.
    rate: BTreeMap<SiteId, i128>,
    /// The sites whose people made available any hours in the closing period.
    hours: BTreeSet<SiteId>,
}

impl LedgerTables {
    fn of(state: &MaterialCircuitState, economy: &MonetaryCircuit) -> Self {
        let mut held: BTreeMap<Product, u64> = BTreeMap::new();
        for row in &state.inventory {
            let units = held
                .entry((row.site_id, row.good_id, row.unit_id))
                .or_insert(0);
            *units = units.saturating_add(row.quantity);
        }
        let mut rate: BTreeMap<SiteId, i128> = BTreeMap::new();
        for ((site, _), wage) in crate::recurring::spare_money::wages(economy) {
            let largest = rate.entry(site).or_insert(0);
            *largest = (*largest).max(wage);
        }
        Self {
            held,
            holder: first_by(
                &economy.financial.ownership,
                |claim| claim.issuer_site_id,
                |claim| claim.beneficiary,
            ),
            granted: economy
                .financial
                .public_allocations
                .iter()
                .filter(|row| row.treatment == PublicTransferTreatment::ProviderOperatingGrant)
                .filter_map(|row| match row.recipient {
                    AccountId::Site(site) => Some(site),
                    _ => None,
                })
                .collect(),
            rate,
            hours: rest::sites_with_hours(state),
        }
    }
}

/// Everything the restart reads from a long list, indexed once: each table keeps the rows as the old read found
/// them, the first row of a key where the read took the first and every row of a key, in row order, where it
/// summed. It is made before the restart's first read, and the offers are made again when a price was raised;
/// nothing else the restart reads is changed before the last test of a workplace.
struct CloseTables {
    offers: OfferTables,
    plant: PlantTables,
    period: PeriodTables,
    ledger: LedgerTables,
}

impl CloseTables {
    fn build(catalog: &MaterialCatalog, transition: &MaterialCircuitTransition) -> Result<Self> {
        let (economy, recurring) = economy_of(&transition.state)?;
        Ok(Self {
            offers: OfferTables::of(recurring),
            plant: PlantTables::of(catalog, recurring),
            period: PeriodTables::of(transition),
            ledger: LedgerTables::of(&transition.state, economy),
        })
    }

    /// The posted price of a product: its first offer.
    fn posted(&self, site: SiteId, good: GoodId, unit: UnitId) -> Option<i128> {
        self.offers.first.get(&(site, good, unit)).copied()
    }

    /// The holder of a workplace's ownership claim: the first claim of the state's rows.
    fn holder_of(&self, site: SiteId) -> Option<AccountId> {
        self.ledger.holder.get(&site).copied()
    }
}

/// The largest `Wage` rate of a site's employment terms.
fn rate_of(tables: &CloseTables, site: SiteId) -> i128 {
    tables.ledger.rate.get(&site).copied().unwrap_or(0)
}

/// One batch's cost: a maker's hours at `rate` and each input at the highest posted price among its provider's
/// offers; a merchant's hours a unit at `rate` and its supplier's posted price (one unit a batch).
///
/// # Errors
/// `Arithmetic`.
fn batch_cost(tables: &CloseTables, site: SiteId, rate: i128) -> Result<Option<i128>> {
    let arithmetic = MaterialCircuitError::Arithmetic;
    let plant = &tables.plant;
    if let Some(process) = plant.process_at.get(&site) {
        let hours = total(rows_at(&plant.labor, process).iter())?;
        let mut cost = i128::from(hours).checked_mul(rate).ok_or(arithmetic)?;
        for &(good, unit, per_batch) in rows_at(&plant.inputs, process) {
            let price = match plant.provider.get(&(site, good, unit)) {
                Some(&(provider, _)) => tables.offers.own_top.get(&(provider, good, unit)),
                None => tables.offers.top.get(&(good, unit)),
            };
            let Some(&price) = price else {
                return Ok(None);
            };
            cost = i128::from(per_batch)
                .checked_mul(price)
                .and_then(|inputs| cost.checked_add(inputs))
                .ok_or(arithmetic)?;
        }
        return Ok(Some(cost));
    }
    let Some(&(good, unit, hours_per_unit)) = rows_at(&plant.handling, &site).first() else {
        return Ok(None);
    };
    let Some(price) = plant
        .supplier
        .get(&(site, good, unit))
        .and_then(|supplier| tables.posted(*supplier, good, unit))
    else {
        return Ok(None);
    };
    Ok(hours_per_unit
        .checked_mul(rate)
        .and_then(|hours| hours.checked_add(price)))
}

/// What one batch of a workplace makes, how many its capacity runs, and its posted price.
fn output_of(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    tables: &CloseTables,
    site: SiteId,
    next_period: u64,
) -> Result<Option<Output>> {
    let plant = &tables.plant;
    if let Some(&process) = plant.process_at.get(&site) {
        let Some(&(good, unit, per_batch)) = plant.output_of_process.get(&process) else {
            return Ok(None);
        };
        let nameplate =
            crate::capacity::process_available(catalog, state, process, site, next_period)?;
        return Ok(tables.posted(site, good, unit).map(|price| Output {
            per_batch,
            nameplate,
            price,
        }));
    }
    Ok(rows_at(&plant.handling, &site)
        .first()
        .and_then(|&(good, unit, _)| tables.posted(site, good, unit))
        .map(|price| Output {
            per_batch: 1,
            nameplate: u64::MAX,
            price,
        }))
}

/// Every workplace the rules count: the sites of the employment terms, in site order.
fn workplaces(state: &MaterialCircuitState) -> Result<BTreeSet<SiteId>> {
    let (economy, _) = economy_of(state)?;
    Ok(economy.employment.iter().map(|row| row.site_id).collect())
}

/// Step (b): a price that rested at this close and stands under one unit's cost is raised to that cost, or to
/// the lowest ceiling of the site's offers when that is lower; a provider funded by a grant is left alone. The
/// period's price and service market receipts get the new price, and each raise has a receipt. Whether any
/// price moved.
fn raise_resting_prices(
    catalog: &MaterialCatalog,
    transition: &mut MaterialCircuitTransition,
    tables: &CloseTables,
) -> Result<bool> {
    let rested: BTreeSet<SiteId> = transition
        .adjustments
        .iter()
        .filter_map(|row| match row {
            AdjustmentReceipt::RestingPrice(RestingPriceReceipt { site_id, .. }) => Some(*site_id),
            _ => None,
        })
        .collect();
    let closing = transition.state.period;
    let next_period = closing
        .checked_add(1)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let mut lifts = Vec::new();
    for site in rested {
        if tables.ledger.granted.contains(&site) {
            continue;
        }
        let rate = rate_of(tables, site);
        let (Some(cost), Some(output)) = (
            batch_cost(tables, site, rate)?,
            output_of(catalog, &transition.state, tables, site, next_period)?,
        ) else {
            continue;
        };
        if let Some(unit) = raised_price(cost, output.per_batch, output.price) {
            let unit = tables
                .offers
                .ceiling
                .get(&site)
                .map_or(unit, |ceiling| unit.min(*ceiling));
            if unit > output.price {
                lifts.push((site, output.price, unit));
            }
        }
    }
    apply_lifts(transition, &lifts, closing);
    Ok(!lifts.is_empty())
}

/// Write each raise: the offers of the site, the period's price and service market receipts, and the raise's own
/// receipt, in the order of the sites. Each site is raised once, so the rows of a site are found once.
fn apply_lifts(
    transition: &mut MaterialCircuitTransition,
    lifts: &[(SiteId, i128, i128)],
    closing: u64,
) {
    if lifts.is_empty() {
        return;
    }
    let at_offers = match &transition.state.accounting {
        CircuitAccounting::Monetary(economy) => economy
            .recurring
            .as_deref()
            .map_or_else(BTreeMap::new, |recurring| {
                positions(&recurring.offers, |row| row.site_id)
            }),
        CircuitAccounting::PhysicalControl => BTreeMap::new(),
    };
    let at_prices = positions(&transition.prices, |row| row.site_id);
    let at_markets = positions(&transition.service_markets, |row| row.site_id);
    for &(site, old, unit) in lifts {
        let raised = Currency::from_micro_units(unit);
        if let CircuitAccounting::Monetary(economy) = &mut transition.state.accounting {
            if let Some(recurring) = economy.recurring.as_mut() {
                for &at in rows_at(&at_offers, &site) {
                    recurring.offers[at].unit_price = raised;
                }
            }
        }
        for &at in rows_at(&at_prices, &site) {
            transition.prices[at].next_price = raised;
        }
        for &at in rows_at(&at_markets, &site) {
            transition.service_markets[at].next_price = raised;
        }
        transition
            .adjustments
            .push(AdjustmentReceipt::RestingPriceToCost(
                RestingPriceToCostReceipt {
                    period: closing,
                    site_id: site,
                    old: Currency::from_micro_units(old),
                    raised,
                },
            ));
    }
}

/// The positions of the rows of each site, in row order.
fn positions<T>(rows: &[T], site: impl Fn(&T) -> SiteId) -> BTreeMap<SiteId, Vec<usize>> {
    let mut table: BTreeMap<SiteId, Vec<usize>> = BTreeMap::new();
    for (at, row) in rows.iter().enumerate() {
        table.entry(site(row)).or_default().push(at);
    }
    table
}

/// What a workplace sold and made in the closing period, as the prototype read them: it made or sold anything
/// when it sold something, or it has a recurring production row and made or took in something.
fn made_or_sold(tables: &CloseTables, site: SiteId) -> Result<bool> {
    let arithmetic = MaterialCircuitError::Arithmetic;
    let period = &tables.period;
    let sold = total(
        rows_at(&period.shipped_by, &site)
            .iter()
            .chain(rows_at(&period.retailed_by, &site))
            .chain(rows_at(&period.performed_by, &site)),
    )?;
    if sold > 0 {
        return Ok(true);
    }
    if !tables.plant.process_at.contains_key(&site) {
        return Ok(false);
    }
    let mut made = 0_u64;
    for &(process, batches) in rows_at(&period.made_by, &site) {
        let per_batch = tables
            .plant
            .output_of_process
            .get(&process)
            .ok_or(MaterialCircuitError::ProcessInvariant)?
            .2;
        made = batches.checked_mul(per_batch).ok_or(arithmetic)?;
    }
    let taken = total(rows_at(&period.received_by, &site).iter())?;
    Ok(made.checked_add(taken).ok_or(arithmetic)? > 0)
}

/// An owner's money beyond one period of its own need at the posted prices: its cash less the goods and
/// services its household requires. Each owner of a workplace, in account order.
fn owner_spares(
    transition: &MaterialCircuitTransition,
    tables: &CloseTables,
) -> Result<BTreeMap<AccountId, i128>> {
    let arithmetic = MaterialCircuitError::Arithmetic;
    let (economy, _) = economy_of(&transition.state)?;
    let mut spares = BTreeMap::new();
    for owner in economy.financial.ownership.iter().map(|c| c.beneficiary) {
        let cash = economy.book.cash(owner)?.micro_units();
        let mut need = 0_i128;
        if let AccountId::Household(principal) = owner {
            for &(good, unit, quantity) in rows_at(&tables.period.wanted, &principal) {
                let Some(&retailer) = tables.plant.retailer.get(&(principal, good, unit)) else {
                    continue;
                };
                let price = tables
                    .posted(retailer, good, unit)
                    .ok_or(MaterialCircuitError::PurchaseInvariant)?;
                need = i128::from(quantity)
                    .checked_mul(price)
                    .and_then(|cost| need.checked_add(cost))
                    .ok_or(arithmetic)?;
            }
        }
        spares.insert(owner, cash.checked_sub(need).ok_or(arithmetic)?);
    }
    Ok(spares)
}

/// Whether the inputs of one batch of `site` can be had at this close: it holds each, or each it lacks is made
/// by a supplier that employs people and made it in the period that closed, and that the bound of this close lets
/// it buy: what the supplier plans to make for the next period (capped at nameplate and at its own bound) less
/// what its other buyers took, within the policy's caps for a service. A merchant's batch is one unit of each
/// good it handles.
fn inputs_can_be_had(
    catalog: &MaterialCatalog,
    transition: &MaterialCircuitTransition,
    tables: &CloseTables,
    bound: &HiringBound,
    site: SiteId,
) -> Result<bool> {
    let plant = &tables.plant;
    let needs: Vec<(GoodId, UnitId, u64)> = if let Some(process) = plant.process_at.get(&site) {
        rows_at(&plant.inputs, process)
            .iter()
            .filter(|row| row.2 > 0)
            .copied()
            .collect()
    } else {
        rows_at(&plant.handling, &site)
            .iter()
            .map(|&(good, unit, _)| (good, unit, 1))
            .collect()
    };
    for (good, unit, per_batch) in needs {
        let have = tables
            .ledger
            .held
            .get(&(site, good, unit))
            .copied()
            .unwrap_or(0);
        if have >= per_batch {
            continue;
        }
        let Some((supplier, limit)) = supplier_of(catalog, tables, site, good, unit) else {
            return Ok(false);
        };
        let planned = planned_by(catalog, transition, tables, bound, supplier, (good, unit))?;
        let Some(planned) = planned else {
            return Ok(false);
        };
        let service = crate::services::is_service(catalog, good, unit);
        let others = taken_by_others(tables, service, supplier, site, (good, unit))?;
        let for_me = planned.saturating_sub(others).min(limit);
        if for_me < per_batch.saturating_sub(have) {
            return Ok(false);
        }
    }
    Ok(true)
}

/// Who supplies `good` to `site`, and the most it may buy from them in a period.
fn supplier_of(
    catalog: &MaterialCatalog,
    tables: &CloseTables,
    site: SiteId,
    good: GoodId,
    unit: UnitId,
) -> Option<(SiteId, u64)> {
    if crate::services::is_service(catalog, good, unit) {
        tables.plant.provider.get(&(site, good, unit)).copied()
    } else {
        tables
            .plant
            .supplier
            .get(&(site, good, unit))
            .map(|supplier| (*supplier, u64::MAX))
    }
}

/// What a supplier plans to make of a product for the next period, when it works and made the product in the
/// period that closed; `None` when it does not.
fn planned_by(
    catalog: &MaterialCatalog,
    transition: &MaterialCircuitTransition,
    tables: &CloseTables,
    bound: &HiringBound,
    supplier: SiteId,
    (good, unit): (GoodId, UnitId),
) -> Result<Option<u64>> {
    let state = &transition.state;
    let outputs = rows_at(&tables.plant.outputs, &(supplier, good, unit));
    let mut counted = BTreeSet::new();
    let mut made_last = 0_u64;
    for &(process, _) in outputs {
        if counted.insert(process) {
            made_last = rows_at(&tables.period.batches_of, &process)
                .iter()
                .try_fold(made_last, |sum, batches| sum.checked_add(*batches))
                .ok_or(MaterialCircuitError::Arithmetic)?;
        }
    }
    if !tables.ledger.hours.contains(&supplier) || made_last == 0 {
        return Ok(None);
    }
    let mut planned = 0_u64;
    for &(process, per_batch) in outputs {
        let nameplate = crate::capacity::process_available(
            catalog,
            state,
            process,
            supplier,
            bound.next_period,
        )?;
        let mut batches = tables
            .plant
            .planned
            .get(&process)
            .copied()
            .unwrap_or(0)
            .min(nameplate);
        if let Some(&(own, _)) = bound.process.get(&process) {
            batches = batches.min(own);
        }
        planned = batches
            .checked_mul(per_batch)
            .and_then(|made| planned.checked_add(made))
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(Some(planned))
}

/// What a supplier's other buyers took of a product in the period that closed: a service it performed for
/// buyers other than `site`, or goods it sold to other buyers and to households.
fn taken_by_others(
    tables: &CloseTables,
    service: bool,
    supplier: SiteId,
    site: SiteId,
    (good, unit): (GoodId, UnitId),
) -> Result<u64> {
    let product = (supplier, good, unit);
    let period = &tables.period;
    let taken: Vec<u64> = if service {
        rows_at(&period.served, &product)
            .iter()
            .filter(|(buyer, _)| *buyer != AccountId::Site(site))
            .map(|(_, quantity)| *quantity)
            .collect()
    } else {
        rows_at(&period.sent, &product)
            .iter()
            .filter(|(buyer, _)| *buyer != site)
            .map(|(_, quantity)| *quantity)
            .chain(rows_at(&period.retailed, &product).iter().copied())
            .collect()
    };
    total(taken.iter())
}

/// The sales test of one stopped workplace, and the inputs test: what its buyers could pay for at its price and
/// were not sold must cover one batch's cost.
fn try_site(
    catalog: &MaterialCatalog,
    transition: &MaterialCircuitTransition,
    tables: &CloseTables,
    bound: &HiringBound,
    site: SiteId,
    outlay_periods: u64,
) -> Result<Option<Tried>> {
    let arithmetic = MaterialCircuitError::Arithmetic;
    let (economy, _) = economy_of(&transition.state)?;
    let rate = rate_of(tables, site);
    let (Some(cost), Some(output)) = (
        batch_cost(tables, site, rate)?,
        output_of(catalog, &transition.state, tables, site, bound.next_period)?,
    ) else {
        return Ok(None);
    };
    let turned = rows_at(&tables.period.clearings, &site)
        .iter()
        .try_fold(0_u64, |sum, &(demand, sold)| {
            let short = demand.checked_sub(sold)?;
            sum.checked_add(short)
        })
        .ok_or(arithmetic)?;
    let mut tried = Tried {
        site,
        cost,
        turned,
        inputs_short: false,
        candidate: None,
    };
    let per_batch = i128::from(output.per_batch);
    let revenue = i128::from(turned.min(output.per_batch))
        .checked_mul(output.price)
        .ok_or(arithmetic)?;
    if revenue <= cost {
        return Ok(Some(tried));
    }
    if !inputs_can_be_had(catalog, transition, tables, bound, site)? {
        tried.inputs_short = true;
        return Ok(Some(tried));
    }
    let batches = (turned / output.per_batch).min(output.nameplate).max(1);
    let made = per_batch
        .checked_mul(i128::from(batches))
        .ok_or(arithmetic)?;
    let earn = i128::from(turned)
        .min(made)
        .checked_mul(output.price)
        .and_then(|sales| {
            i128::from(batches)
                .checked_mul(cost)
                .and_then(|spent| sales.checked_sub(spent))
        })
        .ok_or(arithmetic)?;
    let plan = i128::from(batches)
        .checked_mul(cost)
        .and_then(|batch| batch.checked_mul(i128::from(outlay_periods)))
        .ok_or(arithmetic)?;
    let cash = economy.book.cash(AccountId::Site(site))?.micro_units();
    tried.candidate = money_to_put_in(plan, cash).map(|money| Candidate {
        site,
        plan,
        earn,
        money,
    });
    Ok(Some(tried))
}

/// The restart at the very end of the close, before staffing; the module's note says the order. The caller has
/// the catalog's own word that it asks for the restart; `standing` is the closed period's own and `bound` the
/// bound reckoned at this close.
///
/// # Errors
/// `MarketClearingInvariant` when the catalog does not ask for the restart; a circuit refusal for arithmetic,
/// a missing price or a transfer the book refuses.
pub(crate) fn restart_stopped(
    catalog: &MaterialCatalog,
    transition: &mut MaterialCircuitTransition,
    standing: &mut WorkplaceStanding,
    bound: &mut HiringBound,
    next_period: u64,
) -> Result<()> {
    let outlay_periods = catalog
        .market_clearing
        .as_ref()
        .and_then(|order| policy::restart_outlay_periods(&order.adjustments))
        .ok_or(MaterialCircuitError::MarketClearingInvariant)?;
    if bound.next_period != next_period {
        return Err(MaterialCircuitError::MonetaryInvariant);
    }
    let mut tables = CloseTables::build(catalog, transition)?;
    let mut moved = raise_resting_prices(catalog, transition, &tables)?;
    if moved {
        // The raise wrote the offers' prices: every other table stands as the close left it.
        let (_, recurring) = economy_of(&transition.state)?;
        tables.offers = OfferTables::of(recurring);
    }
    let sites = workplaces(&transition.state)?;
    for site in &sites {
        let did = made_or_sold(&tables, *site)?;
        count(standing.row_mut(*site), did)?;
    }
    let period = transition.state.period;
    let mut spares = owner_spares(transition, &tables)?;
    transition
        .adjustments
        .extend(spares.iter().map(|(owner, spare)| {
            AdjustmentReceipt::OwnerSpare(OwnerSpareReceipt {
                period,
                owner: *owner,
                spare: Currency::from_micro_units(*spare),
            })
        }));
    let mut tried = Vec::new();
    for site in &sites {
        let tested = is_tested(&standing.row_of(*site), tables.ledger.hours.contains(site));
        if tested {
            tried.extend(try_site(
                catalog,
                transition,
                &tables,
                bound,
                *site,
                outlay_periods,
            )?);
        }
    }
    let mut candidates: Vec<Candidate> = tried.iter().filter_map(|row| row.candidate).collect();
    rank(&mut candidates);
    let seated = seat(&candidates, |site| tables.holder_of(site), &mut spares);
    let seat_of: BTreeMap<SiteId, Option<AccountId>> =
        first_by(&seated, |(site, _)| *site, |(_, owner)| *owner);
    let money_of: BTreeMap<SiteId, i128> = first_by(&candidates, |row| row.site, |row| row.money);
    let mut receipts = Vec::new();
    for row in &tried {
        let seat = seat_of.get(&row.site);
        let money = money_of.get(&row.site).copied().unwrap_or(0);
        let (test, owner) = match seat {
            _ if row.candidate.is_none() => (RestartTest::Failed, None),
            Some(Some(owner)) => (RestartTest::Restarted, Some(*owner)),
            _ => (RestartTest::NoBuyer, tables.holder_of(row.site)),
        };
        if test == RestartTest::Restarted {
            moved = true;
            let Some(owner) = owner else { continue };
            let CircuitAccounting::Monetary(economy) = &mut transition.state.accounting else {
                return Err(MaterialCircuitError::MonetaryInvariant);
            };
            let transfer = put_in(
                &mut economy.book,
                &mut economy.costs,
                owner,
                row.site,
                money,
            )?;
            transition.money_transfers.push(transfer);
            let kept = standing.row_mut(row.site);
            kept.hold = StopHold::Free;
            kept.quiet_periods = 0;
        }
        receipts.push(AdjustmentReceipt::Restart(RestartReceipt {
            period,
            site_id: row.site,
            test,
            inputs_short: row.inputs_short,
            owner,
            money: Currency::from_micro_units(if test == RestartTest::Restarted {
                money
            } else {
                0
            }),
            batch_cost: Currency::from_micro_units(row.cost),
            turned: row.turned,
        }));
    }
    transition.adjustments.extend(receipts);
    if moved {
        bound_again(catalog, transition, bound)?;
    }
    Ok(())
}

/// Reckon the bound of the next period again from the state as it now stands, and put its receipts where the
/// earlier ones stood.
fn bound_again(
    catalog: &MaterialCatalog,
    transition: &mut MaterialCircuitTransition,
    bound: &mut HiringBound,
) -> Result<()> {
    let again = bound::rebound(
        catalog,
        &mut transition.state,
        bound,
        &transition.service_performance,
        transition.maintenance.as_ref(),
    )?;
    let at = transition
        .adjustments
        .iter()
        .position(|row| matches!(row, AdjustmentReceipt::HiringBound(_)))
        .unwrap_or(transition.adjustments.len());
    transition
        .adjustments
        .retain(|row| !matches!(row, AdjustmentReceipt::HiringBound(_)));
    let at = at.min(transition.adjustments.len());
    let rows = again
        .rows
        .iter()
        .cloned()
        .map(AdjustmentReceipt::HiringBound);
    transition.adjustments.splice(at..at, rows);
    *bound = again;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{CashAccount, FinalDemandPrincipalId};

    fn site(byte: u8) -> SiteId {
        SiteId::from_bytes([byte; 32])
    }

    fn dollars(whole: i128) -> i128 {
        whole * 1_000_000
    }

    fn candidate(byte: u8, plan: i128, earn: i128, money: i128) -> Candidate {
        Candidate {
            site: site(byte),
            plan: dollars(plan),
            earn: dollars(earn),
            money: dollars(money),
        }
    }

    #[test]
    fn a_restart_that_puts_in_nothing_is_refused() {
        assert_eq!(money_to_put_in(dollars(40), dollars(40)), None);
        assert_eq!(money_to_put_in(dollars(40), dollars(41)), None);
        assert_eq!(money_to_put_in(dollars(40), dollars(39)), Some(dollars(1)));
    }

    #[test]
    fn candidates_rank_by_earn_over_plan() {
        // Earn $10 on a plan of $100 against earn $3 on a plan of $20: the second first.
        let mut candidates = [candidate(1, 100, 10, 50), candidate(2, 20, 3, 10)];
        rank(&mut candidates);
        assert_eq!(candidates[0].site, site(2));
        // Equal ratios: the lower site first.
        let mut candidates = [candidate(9, 100, 10, 50), candidate(4, 50, 5, 25)];
        rank(&mut candidates);
        assert_eq!(candidates[0].site, site(4));
    }

    #[test]
    fn a_resting_price_under_cost_is_raised_to_it() {
        assert_eq!(raised_price(dollars(23), 1, dollars(12)), Some(dollars(23)));
        assert_eq!(raised_price(dollars(23), 1, dollars(30)), None);
        // $230 over 9 units is $25.555555..., rounded up to the micro-unit.
        assert_eq!(raised_price(dollars(230), 9, dollars(12)), Some(25_555_556));
        assert_eq!(raised_price(dollars(23), 1, dollars(23)), None);
    }

    #[test]
    fn an_owner_puts_in_only_its_own_spare() {
        let owner = AccountId::Household(FinalDemandPrincipalId::from_bytes([7; 32]));
        let candidates = [candidate(1, 80, 20, 40), candidate(2, 80, 10, 40)];
        let mut spare = BTreeMap::from([(owner, dollars(50))]);
        let seated = seat(&candidates, |_| Some(owner), &mut spare);
        assert_eq!(seated, vec![(site(1), Some(owner)), (site(2), None)]);
        assert_eq!(spare[&owner], dollars(10));
        // A workplace with no owner has no buyer.
        let mut spare = BTreeMap::from([(owner, dollars(500))]);
        assert_eq!(seat(&candidates, |_| None, &mut spare)[0], (site(1), None));
    }

    #[test]
    fn the_restart_moves_money_with_a_receipt() -> Result<()> {
        let owner = AccountId::Household(FinalDemandPrincipalId::from_bytes([7; 32]));
        let workplace = site(3);
        let mut book = MonetaryBook::open(vec![
            CashAccount {
                id: owner,
                cash: Currency::from_micro_units(dollars(100)),
            },
            CashAccount {
                id: AccountId::Site(workplace),
                cash: Currency::from_micro_units(dollars(15)),
            },
        ])?;
        let mut costs = HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![])?;
        let before = book.total_cash_and_reserves()?;
        let receipt = put_in(&mut book, &mut costs, owner, workplace, dollars(25))?;
        assert_eq!(receipt.credit.delta.micro_units(), dollars(25));
        assert_eq!(receipt.debit.delta.micro_units(), -dollars(25));
        assert_eq!(book.cash(owner)?.micro_units(), dollars(75));
        assert_eq!(
            book.cash(AccountId::Site(workplace))?.micro_units(),
            dollars(40)
        );
        assert_eq!(book.total_cash_and_reserves()?, before);
        let snapshot = costs.snapshot();
        assert_eq!(snapshot.equity.len(), 1);
        assert_eq!(snapshot.equity[0].amount.micro_units(), dollars(25));
        let capital = snapshot
            .accounts
            .iter()
            .find(|row| row.account == AccountId::Site(workplace))
            .map(|row| row.contributed_capital.micro_units());
        assert_eq!(capital, Some(dollars(25)));
        Ok(())
    }

    #[test]
    fn a_workplace_is_tested_at_its_third_quiet_close() -> Result<()> {
        let mut row = WorkplaceStandingRow::new(site(1));
        for close in 1..=4_u64 {
            count(&mut row, false)?;
            assert_eq!(
                is_tested(&row, false),
                close >= RESTART_QUIET_PERIODS,
                "close {close}"
            );
        }
        // One that offers hours is never tested; one that made or sold starts counting again.
        assert!(!is_tested(&row, true));
        count(&mut row, true)?;
        assert_eq!((row.periods_since_work, row.quiet_periods), (0, 0));
        Ok(())
    }

    /// The size test of the restart. A world of thousands of stopped workplaces, each tested at one close.
    mod size {
        use super::*;
        use babylon_kernel::economic_location::EconomicLocation;

        use crate::{
            AdjustmentRule, AidBook, CapacityReservations, CapacitySupply, CommodityDefinition,
            CommodityKind, CorridorId, EmploymentTerms, FinancialInstitutions,
            HouseholdTimeAccounting, LaborCompensation, LogisticsNodeId, MarketClearingPolicy,
            MaterialCatalogDefinition, MemberLaborCapacityRow, MerchantHandling,
            MerchantHandlingCoefficient, MerchantRole, MonetaryBook, OwnershipClaim,
            ReplenishmentPolicy, SellerOffer, SiteLogisticsNode, StaffingMemberId,
        };

        const STOPPED: u32 = 2_500;

        /// A workplace of the fixture, its id made from a `u32`.
        fn workplace(number: u32) -> SiteId {
            let mut bytes = [7_u8; 32];
            bytes[..4].copy_from_slice(&number.to_le_bytes());
            SiteId::from_bytes(bytes)
        }

        fn good() -> GoodId {
            GoodId::from_bytes([2; 32])
        }

        fn unit() -> UnitId {
            UnitId::from_bytes([1; 32])
        }

        fn hours() -> UnitId {
            UnitId::from_bytes([3; 32])
        }

        fn location() -> EconomicLocation {
            "county:26163"
                .parse()
                .expect("the authored literal parses as the declared type")
        }

        /// The catalog: `count` merchants, each handling one good at one hour a unit.
        fn catalog(count: u32) -> MaterialCatalog {
            let sites: Vec<SiteId> = (1..=count).map(workplace).collect();
            MaterialCatalog::try_new(MaterialCatalogDefinition {
                company_portfolios: None,
                company_payouts: vec![],
                capacity_policy: CapacitySupply::FiniteSchedule,
                site_logistics_nodes: sites
                    .iter()
                    .map(|site| SiteLogisticsNode {
                        site_id: *site,
                        node_id: LogisticsNodeId::from_bytes(site.as_bytes()),
                    })
                    .collect(),
                process_outputs: vec![],
                input_coefficients: vec![],
                labor_coefficients: vec![],
                commodities: vec![CommodityDefinition {
                    good_id: good(),
                    unit_id: unit(),
                    kind: CommodityKind::Storable { grams_per_unit: 1 },
                }],
                supplier_routes: vec![],
                route_stages: vec![],
                merchants: sites
                    .iter()
                    .map(|site| MerchantHandling {
                        site_id: *site,
                        location: location(),
                        role: MerchantRole::Retail,
                        capacity_id: CorridorId::from_bytes(site.as_bytes()),
                        labor_unit_id: hours(),
                    })
                    .collect(),
                handling_coefficients: sites
                    .iter()
                    .map(|site| MerchantHandlingCoefficient {
                        site_id: *site,
                        good_id: good(),
                        unit_id: unit(),
                        hours_per_unit: 1,
                    })
                    .collect(),
                maintenance_binding: None,
                aid_mandates: vec![],
                household_time_policy: vec![],
                service_inputs: vec![],
                household_needs: vec![],
                market_clearing: Some(MarketClearingPolicy {
                    paying_order: vec![(good(), unit())],
                    household_wants: vec![],
                    plans_from_spare_money: false,
                    adjustments: vec![
                        AdjustmentRule::HiringWithinMeans,
                        AdjustmentRule::SeekingInPlace,
                        AdjustmentRule::StopWithoutPay,
                        AdjustmentRule::RestingPrice,
                        AdjustmentRule::OwnerRestart { outlay_periods: 1 },
                    ],
                }),
            })
            .expect("the fixture catalog is valid")
        }

        /// The closing state: each workplace employs one member who offers no hours, sells nothing, buys its
        /// good from the next workplace, and is owned by one household.
        fn state(count: u32) -> MaterialCircuitState {
            let owner = FinalDemandPrincipalId::from_bytes([9; 32]);
            let sites: Vec<SiteId> = (1..=count).map(workplace).collect();
            let mut accounts = vec![CashAccount {
                id: AccountId::Household(owner),
                cash: Currency::from_micro_units(dollars(1_000_000)),
            }];
            accounts.extend(sites.iter().map(|site| CashAccount {
                id: AccountId::Site(*site),
                cash: Currency::from_micro_units(dollars(5)),
            }));
            let book = MonetaryBook::open(accounts).expect("the fixture opens");
            let costs = HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![])
                .expect("the fixture opens");
            let mut financial = FinancialInstitutions::empty();
            financial
                .ownership
                .extend(sites.iter().map(|site| OwnershipClaim {
                    issuer_site_id: *site,
                    beneficiary: AccountId::Household(owner),
                    shares: 1,
                }));
            let member = |site: &SiteId| StaffingMemberId::from_bytes(site.as_bytes());
            let recurring = RecurringEconomy {
                households: vec![],
                household_stocks: vec![],
                household_purchases: vec![],
                offers: sites
                    .iter()
                    .map(|site| SellerOffer {
                        site_id: *site,
                        good_id: good(),
                        unit_id: unit(),
                        unit_price: Currency::from_micro_units(dollars(3)),
                        pricing: PricePolicy::Fixed,
                    })
                    .collect(),
                replenishment: sites
                    .iter()
                    .enumerate()
                    .map(|(at, site)| ReplenishmentPolicy {
                        buyer_site_id: *site,
                        supplier_site_id: sites[(at + 1) % sites.len()],
                        good_id: good(),
                        unit_id: unit(),
                        target_stock: 0,
                        maximum_purchase: 0,
                        cash_floor: Currency::from_micro_units(0),
                    })
                    .collect(),
                production: vec![],
                attendance: vec![],
                last_household_admission_period: 0,
                last_household_consumption_period: 0,
            };
            MaterialCircuitState {
                period: 1,
                accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
                    aid: AidBook::default(),
                    household_time: HouseholdTimeAccounting::NotModeled,
                    financial,
                    member_labor: sites
                        .iter()
                        .map(|site| MemberLaborCapacityRow {
                            member_id: member(site),
                            period: 1,
                            available_hours: 0,
                        })
                        .collect(),
                    costs,
                    book,
                    recurring: Some(Box::new(recurring)),
                    employment: sites
                        .iter()
                        .map(|site| EmploymentTerms {
                            member_id: member(site),
                            site_id: *site,
                            unit_id: hours(),
                            payee: owner,
                            compensation: LaborCompensation::Wage(Currency::from_micro_units(
                                dollars(1),
                            )),
                        })
                        .collect(),
                })),
                service_connections: vec![],
                service_orders: vec![],
                route_stage_capacities: vec![],
                inventory: vec![],
                orders: vec![],
                freight: vec![],
                corridor_capacities: vec![],
                capacities: vec![],
                labor: vec![],
                production_commitments: vec![],
                final_demand_principals: vec![],
                final_demand_orders: vec![],
                maintenance_service: None,
                capacity_reservations: CapacityReservations::default(),
            }
        }

        /// A period's transition with no receipt but its state.
        fn transition(state: MaterialCircuitState) -> MaterialCircuitTransition {
            MaterialCircuitTransition {
                household_lifecycle: vec![],
                resident_workforce_attrition: vec![],
                agency_attendance: vec![],
                aid: vec![],
                collections: vec![],
                aid_contributions: vec![],
                household_time: vec![],
                installation: vec![],
                installation_decisions: vec![],
                equipment_wear: vec![],
                investment: vec![],
                public_budgets: vec![],
                public_programs: vec![],
                taxes: vec![],
                distributions: vec![],
                company_basis: vec![],
                company_distributions: vec![],
                contributions: vec![],
                staffing_members: vec![],
                member_labor_use: vec![],
                service_performance: vec![],
                household_services: vec![],
                service_markets: vec![],
                service_outputs: vec![],
                income: vec![],
                state,
                household_demand: vec![],
                household_consumption: vec![],
                procurement: vec![],
                production_plans: vec![],
                prices: vec![],
                money_transfers: vec![],
                wage_accruals: vec![],
                labor_use: vec![],
                production: vec![],
                dispatches: vec![],
                losses: vec![],
                arrivals: vec![],
                deliveries: vec![],
                realizations: vec![],
                handling: vec![],
                local_fulfillments: vec![],
                local_transfers: vec![],
                maintenance: None,
                market_clearings: vec![],
                household_wants: vec![],
                household_tiers: vec![],
                adjustments: vec![],
            }
        }

        /// A guard against a square coming back: thousands of stopped workplaces are tested at one close,
        /// each by reading the close's tables. It times nothing; it sees that the close returns, that each
        /// tested workplace has one restart receipt, and that the money is the same.
        #[test]
        fn many_stopped_workplaces_are_tested_for_a_restart() -> Result<()> {
            let catalog = catalog(STOPPED);
            let mut transition = transition(state(STOPPED));
            let money_before = economy_of(&transition.state)?
                .0
                .book
                .total_cash_and_reserves()?;
            // Each workplace has been quiet for two closes: this close is its third.
            let mut standing = WorkplaceStanding::opening();
            for number in 1..=STOPPED {
                standing.row_mut(workplace(number)).quiet_periods = RESTART_QUIET_PERIODS - 1;
            }
            let mut bound = HiringBound {
                next_period: 2,
                process: BTreeMap::new(),
                rows: vec![],
                cuts: BTreeMap::new(),
            };
            restart_stopped(&catalog, &mut transition, &mut standing, &mut bound, 2)?;
            let tested: BTreeSet<SiteId> = transition
                .adjustments
                .iter()
                .filter_map(|row| match row {
                    AdjustmentReceipt::Restart(receipt) => Some(receipt.site_id),
                    _ => None,
                })
                .collect();
            let restarts = transition
                .adjustments
                .iter()
                .filter(|row| matches!(row, AdjustmentReceipt::Restart(_)))
                .count();
            assert_eq!(restarts, usize::try_from(STOPPED).expect("a small count"));
            assert_eq!(tested.len(), restarts, "one receipt for each workplace");
            let money_after = economy_of(&transition.state)?
                .0
                .book
                .total_cash_and_reserves()?;
            assert_eq!(money_after, money_before, "the money is conserved");
            Ok(())
        }
    }
}
