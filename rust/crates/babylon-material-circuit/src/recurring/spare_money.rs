//! Rule A6 (ADR314): the arithmetic of a workplace that plans from spare money.
//!
//! Pure functions. What was asked of a seller and not paid for, one period of what a site pays out,
//! how many batches or units its spare money carries, and how much a stocked input leaves room for.

use std::collections::BTreeMap;
use std::result::Result as StdResult;

use super::firms::{ProcurementReceipt, StockKey, Wanted};
use crate::inventory::InventoryLedger;
use crate::{
    AccountId, CircuitAccounting, GoodId, HouseholdDemandReceipt, LaborCompensation,
    MaterialCatalog, MaterialCircuitError, MaterialCircuitState, MonetaryCircuit, ProcessId,
    ProcessOutput, RecurringEconomy, ServiceMarketReceipt, SiteId, UnitId,
};

type Result<T> = StdResult<T, MaterialCircuitError>;

fn add(rows: &mut BTreeMap<StockKey, u64>, key: StockKey, quantity: u64) -> Result<()> {
    if quantity == 0 {
        return Ok(());
    }
    let row = rows.entry(key).or_insert(0);
    *row = row
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}

/// What was asked of each seller and not paid for at its posted price, by seller and product, rows
/// above 0 only: a service's requested quantity above its paid-for plan; a goods seller's restock
/// orders and household requests not admitted, less what its buyers were priced out of.
pub(crate) fn unpaid_asking(
    services: &[ServiceMarketReceipt],
    procurement: &[ProcurementReceipt],
    demand: &[HouseholdDemandReceipt],
    priced_out: impl Fn(StockKey) -> u64,
) -> Result<BTreeMap<StockKey, u64>> {
    let mut services_unpaid = BTreeMap::new();
    for row in services {
        let key = (row.site_id, row.good_id, row.unit_id);
        add(
            &mut services_unpaid,
            key,
            row.requested_quantity.saturating_sub(row.planned_quantity),
        )?;
    }
    let mut goods = BTreeMap::new();
    for row in procurement {
        let key = (row.supplier_site_id, row.good_id, row.unit_id);
        add(
            &mut goods,
            key,
            row.desired_quantity.saturating_sub(row.admitted_quantity),
        )?;
    }
    for row in demand {
        let key = (row.retailer_site_id, row.good_id, row.unit_id);
        add(
            &mut goods,
            key,
            row.requested_quantity.saturating_sub(row.admitted_quantity),
        )?;
    }
    let mut rows = services_unpaid;
    for (key, asked) in goods {
        add(&mut rows, key, asked.saturating_sub(priced_out(key)))?;
    }
    Ok(rows)
}

fn priced(quantity: u64, price: Option<i128>) -> Result<Option<i128>> {
    if quantity == 0 {
        return Ok(Some(0));
    }
    match price {
        None => Ok(None),
        Some(price) => i128::from(quantity)
            .checked_mul(price)
            .map(Some)
            .ok_or(MaterialCircuitError::Arithmetic),
    }
}

/// One period of what a site pays out: each (hours, wage) of its planned hours, each (batches,
/// inputs of one batch) of its planned processes, and each (units, price) of a merchant's
/// restocking. `Ok(None)` when a positive quantity has no price.
pub(crate) fn outlay(
    hours: &[(u64, Option<i128>)],
    batches: &[(u64, Option<i128>)],
    restock: &[(u64, Option<i128>)],
) -> Result<Option<i128>> {
    let mut total: i128 = 0;
    for &(quantity, price) in hours.iter().chain(batches).chain(restock) {
        let Some(cost) = priced(quantity, price)? else {
            return Ok(None);
        };
        total = total
            .checked_add(cost)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(Some(total))
}

/// How many of `asked` (batches or units) `spare` pays for at `per` each: 0 when `spare <= 0` or
/// nothing is asked; all of it when `per == 0`; else `min(asked, spare / per)`.
pub(crate) fn affordable(asked: u64, per: i128, spare: i128) -> Result<u64> {
    if per < 0 {
        return Err(MaterialCircuitError::MonetaryInvariant);
    }
    if spare <= 0 || asked == 0 {
        return Ok(0);
    }
    if per == 0 {
        return Ok(asked);
    }
    let carried = i128::from(asked).min(spare / per);
    u64::try_from(carried).map_err(|_| MaterialCircuitError::Arithmetic)
}

/// How many more batches a stocked input leaves room for, once the site's paid-for plans have
/// what they ask: `(available - paid_for) / per_batch`, 0 when they already ask for all of it.
pub(crate) fn input_room(available: u64, paid_for: u128, per_batch: u64) -> Result<u64> {
    if per_batch == 0 {
        return Err(MaterialCircuitError::Arithmetic);
    }
    let left = u128::from(available).saturating_sub(paid_for);
    u64::try_from(left / u128::from(per_batch)).map_err(|_| MaterialCircuitError::Arithmetic)
}

/// What the rule added at one close.
#[derive(Debug, Default)]
pub(crate) struct Extension {
    /// Some process's planned batches were raised, so its hours must be planned again.
    pub(crate) raised_batches: bool,
    /// Extra handling hours of merchants, by site and labor unit.
    pub(crate) handling: BTreeMap<(SiteId, UnitId), u64>,
}

/// The prices the rule reads: the largest wage of each site's labor unit and the posted offers.
struct Prices {
    wage: BTreeMap<(SiteId, UnitId), i128>,
    /// The largest posted price of a product, whoever sells it.
    input: BTreeMap<(GoodId, UnitId), i128>,
    /// The posted price of each seller's own offer.
    offer: BTreeMap<StockKey, i128>,
}

/// Everything `extend` reads that does not change while it works.
struct Reads<'a> {
    catalog: &'a MaterialCatalog,
    prices: Prices,
    /// What today's allocation reads as stock at the next period.
    inventory: InventoryLedger,
    /// The batches nameplate allows at the next period, of the processes of sites asked for more.
    nameplate: BTreeMap<ProcessId, u64>,
    hours: &'a BTreeMap<(SiteId, UnitId), u64>,
    procurement: &'a [ProcurementReceipt],
}

/// The largest `Wage` rate of each (site, labor unit).
fn wages(economy: &MonetaryCircuit) -> BTreeMap<(SiteId, UnitId), i128> {
    let mut wage = BTreeMap::new();
    for terms in &economy.employment {
        if let LaborCompensation::Wage(rate) = terms.compensation {
            let entry = wage.entry((terms.site_id, terms.unit_id)).or_insert(0);
            *entry = (*entry).max(rate.micro_units());
        }
    }
    wage
}

/// The largest posted price of each product, and each seller's own, as the offers stand now.
fn input_prices(recurring: &RecurringEconomy, wage: BTreeMap<(SiteId, UnitId), i128>) -> Prices {
    let mut input = BTreeMap::new();
    let mut offer = BTreeMap::new();
    for row in &recurring.offers {
        let price = row.unit_price.micro_units();
        let entry = input.entry((row.good_id, row.unit_id)).or_insert(0);
        *entry = (*entry).max(price);
        offer.insert((row.site_id, row.good_id, row.unit_id), price);
    }
    Prices { wage, input, offer }
}

/// The inputs of one batch of a process at their posted price; `None` when one has no price.
fn batch_inputs(
    catalog: &MaterialCatalog,
    prices: &Prices,
    process: ProcessId,
) -> Result<Option<i128>> {
    let mut total: i128 = 0;
    for row in catalog
        .input_coefficients
        .iter()
        .filter(|row| row.process_id == process)
    {
        let Some(&price) = prices.input.get(&(row.good_id, row.unit_id)) else {
            return Ok(None);
        };
        let cost = i128::from(row.quantity_per_batch)
            .checked_mul(price)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        total = total
            .checked_add(cost)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(Some(total))
}

fn process_of(catalog: &MaterialCatalog, key: StockKey) -> Option<&ProcessOutput> {
    catalog
        .process_outputs
        .iter()
        .find(|row| (row.site_id, row.good_id, row.unit_id) == key)
}

/// One period of what the site pays out: its hours at their wage, its planned batches' inputs, and
/// a merchant's restocking at its suppliers' offers. `None` when something has no price.
fn site_outlay(
    reads: &Reads<'_>,
    recurring: &RecurringEconomy,
    site: SiteId,
) -> Result<Option<i128>> {
    let hours: Vec<_> = reads
        .hours
        .iter()
        .filter(|((s, _), _)| *s == site)
        .map(|(&(s, unit), &h)| (h, reads.prices.wage.get(&(s, unit)).copied()))
        .collect();
    let mut batches = Vec::new();
    for row in recurring.production.iter().filter(|r| r.site_id == site) {
        let per = batch_inputs(reads.catalog, &reads.prices, row.process_id)?;
        batches.push((row.planned_batches, per));
    }
    let restock: Vec<_> =
        reads
            .procurement
            .iter()
            .filter(|row| {
                row.buyer_site_id == site
                    && reads.catalog.handling_coefficients.iter().any(|c| {
                        (c.site_id, c.good_id, c.unit_id) == (site, row.good_id, row.unit_id)
                    })
            })
            .map(|row| {
                let key = (row.supplier_site_id, row.good_id, row.unit_id);
                (row.desired_quantity, reads.prices.offer.get(&key).copied())
            })
            .collect();
    outlay(&hours, &batches, &restock)
}

/// What the site's paid-for plans ask of each stocked input, at its plans before any raise: the
/// batches planned, within nameplate, times the input of a batch.
fn paid_for(
    reads: &Reads<'_>,
    recurring: &RecurringEconomy,
    site: SiteId,
) -> Result<BTreeMap<(GoodId, UnitId), u128>> {
    let mut asked = BTreeMap::new();
    for row in recurring.production.iter().filter(|r| r.site_id == site) {
        let nameplate = reads.nameplate.get(&row.process_id).copied().unwrap_or(0);
        let batches = row.planned_batches.min(nameplate);
        for input in reads
            .catalog
            .input_coefficients
            .iter()
            .filter(|c| c.process_id == row.process_id)
        {
            let entry = asked
                .entry((input.good_id, input.unit_id))
                .or_insert(0_u128);
            *entry = u128::from(batches)
                .checked_mul(u128::from(input.quantity_per_batch))
                .and_then(|q| entry.checked_add(q))
                .ok_or(MaterialCircuitError::Arithmetic)?;
        }
    }
    Ok(asked)
}

/// The site's money and what it may still plan: its spare money and the stocked input its paid-for
/// plans and the raises so far have taken.
struct Purse {
    spare: i128,
    taken: BTreeMap<(GoodId, UnitId), u128>,
}

/// The extra batches of a process the site may plan for `gap` more units: the least of what was
/// asked, what its spare money pays, what nameplate leaves, and what every stocked input leaves
/// beyond the paid-for plans and the raises so far.
fn raise_maker(
    reads: &Reads<'_>,
    recurring: &mut RecurringEconomy,
    output: &ProcessOutput,
    gap: u64,
    purse: &mut Purse,
) -> Result<bool> {
    let catalog = reads.catalog;
    let site = output.site_id;
    let Some(labor) = catalog
        .labor_coefficients
        .iter()
        .find(|row| row.process_id == output.process_id)
    else {
        return Ok(false);
    };
    let Some(&wage) = reads.prices.wage.get(&(site, labor.unit_id)) else {
        return Ok(false);
    };
    let Some(inputs) = batch_inputs(catalog, &reads.prices, output.process_id)? else {
        return Ok(false);
    };
    let Some(policy) = recurring
        .production
        .iter_mut()
        .find(|row| row.process_id == output.process_id)
    else {
        return Ok(false);
    };
    let per = i128::from(labor.quantity_per_batch)
        .checked_mul(wage)
        .and_then(|hours| hours.checked_add(inputs))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let nameplate = reads
        .nameplate
        .get(&output.process_id)
        .copied()
        .unwrap_or(0);
    let mut batches = affordable(gap.div_ceil(output.quantity_per_batch), per, purse.spare)?
        .min(nameplate.saturating_sub(policy.planned_batches));
    let needs: Vec<_> = catalog
        .input_coefficients
        .iter()
        .filter(|row| row.process_id == output.process_id)
        .collect();
    for input in &needs {
        let key = (input.good_id, input.unit_id);
        let available = reads
            .inventory
            .get(&(site, input.good_id, input.unit_id))
            .copied()
            .unwrap_or(0);
        let room = input_room(
            available,
            purse.taken.get(&key).copied().unwrap_or(0),
            input.quantity_per_batch,
        )?;
        batches = batches.min(room);
    }
    if batches == 0 {
        return Ok(false);
    }
    for input in &needs {
        let used = u128::from(batches)
            .checked_mul(u128::from(input.quantity_per_batch))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let entry = purse
            .taken
            .entry((input.good_id, input.unit_id))
            .or_insert(0);
        *entry = entry
            .checked_add(used)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    let cost = i128::from(batches)
        .checked_mul(per)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    purse.spare = purse
        .spare
        .checked_sub(cost)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    policy.planned_batches = policy
        .planned_batches
        .checked_add(batches)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(true)
}

/// A merchant's extra handling hours for `gap` more units, as far as its spare money pays.
fn raise_merchant(
    reads: &Reads<'_>,
    key: StockKey,
    gap: u64,
    purse: &mut Purse,
    extension: &mut Extension,
) -> Result<()> {
    let catalog = reads.catalog;
    let Some(merchant) = catalog.merchants.iter().find(|row| row.site_id == key.0) else {
        return Ok(());
    };
    let Some(coefficient) = catalog
        .handling_coefficients
        .iter()
        .find(|row| (row.site_id, row.good_id, row.unit_id) == key)
    else {
        return Ok(());
    };
    let Some(&wage) = reads.prices.wage.get(&(key.0, merchant.labor_unit_id)) else {
        return Ok(());
    };
    let per = i128::from(coefficient.hours_per_unit)
        .checked_mul(wage)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let units = affordable(gap, per, purse.spare)?;
    let hours = units
        .checked_mul(coefficient.hours_per_unit)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let cost = i128::from(units)
        .checked_mul(per)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    purse.spare = purse
        .spare
        .checked_sub(cost)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    if hours > 0 {
        let slot = extension
            .handling
            .entry((key.0, merchant.labor_unit_id))
            .or_insert(0);
        *slot = slot
            .checked_add(hours)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(())
}

/// One site's unpaid products in key order, while it has spare money.
fn extend_site(
    reads: &Reads<'_>,
    recurring: &mut RecurringEconomy,
    cash: i128,
    products: &[(StockKey, u64)],
    extension: &mut Extension,
) -> Result<()> {
    let Some(&((site, ..), _)) = products.first() else {
        return Ok(());
    };
    let Some(outlay) = site_outlay(reads, recurring, site)? else {
        return Ok(());
    };
    let spare = cash
        .checked_sub(outlay)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    if spare <= 0 {
        return Ok(());
    }
    let mut purse = Purse {
        spare,
        taken: paid_for(reads, recurring, site)?,
    };
    for &(key, gap) in products {
        if purse.spare <= 0 {
            break;
        }
        if let Some(output) = process_of(reads.catalog, key) {
            if raise_maker(reads, recurring, output, gap, &mut purse)? {
                extension.raised_batches = true;
            }
        } else {
            raise_merchant(reads, key, gap, &mut purse, extension)?;
        }
    }
    Ok(())
}

/// The batches nameplate allows at the next period for the processes of these sites.
fn nameplates(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    sites: &[SiteId],
    next_period: u64,
) -> Result<BTreeMap<ProcessId, u64>> {
    let mut rows = BTreeMap::new();
    for output in catalog
        .process_outputs
        .iter()
        .filter(|row| sites.contains(&row.site_id))
    {
        let batches = crate::capacity::process_available(
            catalog,
            state,
            output.process_id,
            output.site_id,
            next_period,
        )?;
        rows.insert(output.process_id, batches);
    }
    Ok(rows)
}

/// Rule A6 at the close, after the paid-for plans of goods and services and before hours are
/// installed. Raises `planned_batches` in the state's recurring production; writes no receipt.
pub(crate) fn extend(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    hours: &BTreeMap<(SiteId, UnitId), u64>,
    wanted: Wanted<'_>,
    next_period: u64,
) -> Result<Extension> {
    let mut extension = Extension::default();
    let unpaid = unpaid_asking(
        wanted.services,
        wanted.procurement,
        wanted.demand,
        |(site, good, unit)| wanted.markets.priced_out(site, good, unit),
    )?;
    if unpaid.is_empty() {
        return Ok(extension);
    }
    let mut sites: Vec<SiteId> = unpaid.keys().map(|key| key.0).collect();
    sites.dedup();
    let inventory = crate::production::planning_inventory(catalog, state, next_period)?;
    let nameplate = nameplates(catalog, state, &sites, next_period)?;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(extension);
    };
    let wage = wages(economy);
    let recurring = economy
        .recurring
        .as_deref_mut()
        .ok_or(MaterialCircuitError::MonetaryInvariant)?;
    let reads = Reads {
        catalog,
        prices: input_prices(recurring, wage),
        inventory,
        nameplate,
        hours,
        procurement: wanted.procurement,
    };
    for site in sites {
        let products: Vec<_> = unpaid
            .iter()
            .filter(|(key, _)| key.0 == site)
            .map(|(&key, &gap)| (key, gap))
            .collect();
        let cash = economy.book.cash(AccountId::Site(site))?.micro_units();
        extend_site(&reads, recurring, cash, &products, &mut extension)?;
    }
    Ok(extension)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        FinalDemandPrincipalId, GoodId, OrderId, ProcessId, ServicePriceDecision, SiteId, UnitId,
    };
    use babylon_kernel::currency::Currency;

    #[test]
    fn no_spare_money_plans_nothing_more() {
        assert_eq!(affordable(10, 23_000_000, 0), Ok(0));
        assert_eq!(affordable(10, 23_000_000, -40_000_000), Ok(0));
    }

    #[test]
    fn spare_money_carries_part_of_what_was_asked() {
        assert_eq!(affordable(4, 23_000_000, 52_000_000), Ok(2));
    }

    #[test]
    fn spare_money_carries_all_that_was_asked() {
        assert_eq!(affordable(3, 23_000_000, 1_000_000_000), Ok(3));
    }

    #[test]
    fn a_free_batch_is_planned_in_full() {
        assert_eq!(affordable(7, 0, 1), Ok(7));
    }

    #[test]
    fn the_largest_values_do_not_overflow() {
        assert_eq!(affordable(u64::MAX, 1, i128::MAX), Ok(u64::MAX));
        assert_eq!(affordable(u64::MAX, i128::MAX, i128::MAX), Ok(1));
        assert_eq!(
            affordable(5, -1, 10),
            Err(MaterialCircuitError::MonetaryInvariant)
        );
        assert_eq!(
            outlay(&[(u64::MAX, Some(i128::MAX))], &[], &[]),
            Err(MaterialCircuitError::Arithmetic)
        );
    }

    #[test]
    fn the_outlay_of_the_opening_clinic_is_its_cash() {
        assert_eq!(
            outlay(&[(40, Some(10_000_000))], &[(40, Some(12_000_000))], &[]),
            Ok(Some(880_000_000))
        );
        assert_eq!(
            outlay(&[(40, None)], &[(40, Some(12_000_000))], &[]),
            Ok(None)
        );
        assert_eq!(
            outlay(&[(0, None)], &[(40, Some(12_000_000))], &[]),
            Ok(Some(480_000_000))
        );
    }

    #[test]
    fn the_outlay_of_the_opening_shop_is_its_cash() {
        assert_eq!(
            outlay(&[(40, Some(10_000_000))], &[], &[(40, Some(25_000_000))]),
            Ok(Some(1_400_000_000))
        );
        assert_eq!(
            outlay(&[(40, Some(10_000_000))], &[], &[(40, None)]),
            Ok(None)
        );
    }

    #[test]
    fn a_stocked_input_leaves_room_only_beyond_the_paid_for_plans() {
        assert_eq!(input_room(100, 100, 5), Ok(0));
        assert_eq!(input_room(100, 120, 5), Ok(0));
        assert_eq!(input_room(100, 60, 5), Ok(8));
        assert_eq!(
            input_room(100, 60, 0),
            Err(MaterialCircuitError::Arithmetic)
        );
    }

    fn site(n: u8) -> SiteId {
        SiteId::from_bytes([n; 32])
    }

    fn service(requested: u64, planned: u64) -> ServiceMarketReceipt {
        ServiceMarketReceipt {
            period: 1,
            next_period: 2,
            process_id: ProcessId::from_bytes([1; 32]),
            site_id: site(1),
            good_id: GoodId::from_bytes([1; 32]),
            unit_id: UnitId::from_bytes([1; 32]),
            requested_quantity: requested,
            admitted_quantity: 0,
            performed_quantity: 0,
            available_capacity: 0,
            direct_cost: Currency::from_micro_units(0),
            old_price: Currency::from_micro_units(0),
            next_price: Currency::from_micro_units(0),
            reason: ServicePriceDecision::Hold,
            planned_quantity: planned,
        }
    }

    fn restock(supplier: SiteId, desired: u64, admitted: u64) -> ProcurementReceipt {
        ProcurementReceipt {
            period: 1,
            order_id: OrderId::from_bytes([1; 32]),
            buyer_site_id: site(9),
            supplier_site_id: supplier,
            good_id: GoodId::from_bytes([1; 32]),
            unit_id: UnitId::from_bytes([1; 32]),
            on_hand: 0,
            outstanding_inbound: 0,
            target_stock: 0,
            desired_quantity: desired,
            admitted_quantity: admitted,
            unit_price: Currency::from_micro_units(0),
        }
    }

    fn household(retailer: SiteId, requested: u64, admitted: u64) -> HouseholdDemandReceipt {
        HouseholdDemandReceipt {
            period: 1,
            principal_id: FinalDemandPrincipalId::from_bytes([1; 32]),
            retailer_site_id: retailer,
            good_id: GoodId::from_bytes([1; 32]),
            unit_id: UnitId::from_bytes([1; 32]),
            order_id: OrderId::from_bytes([2; 32]),
            opening_stock: 0,
            required_quantity: 0,
            desired_quantity: 0,
            requested_quantity: requested,
            admitted_quantity: admitted,
            fulfilled_quantity: 0,
            expired_quantity: 0,
            unit_price: Currency::from_micro_units(0),
        }
    }

    fn key(n: u8) -> StockKey {
        (
            site(n),
            GoodId::from_bytes([1; 32]),
            UnitId::from_bytes([1; 32]),
        )
    }

    #[test]
    fn a_workplace_asked_nothing_plans_nothing_more() {
        assert_eq!(affordable(0, 23_000_000, 1_000_000_000_000), Ok(0));
        let rows = unpaid_asking(
            &[service(36, 36), service(30, 40)],
            &[restock(site(2), 10, 10)],
            &[household(site(3), 5, 5)],
            |_| 0,
        );
        assert_eq!(rows, Ok(BTreeMap::new()));
    }

    #[test]
    fn a_service_asked_above_its_paid_plan_is_unpaid_for_the_difference() {
        let rows = unpaid_asking(&[service(40, 36)], &[], &[], |_| 0);
        assert_eq!(rows, Ok(BTreeMap::from([(key(1), 4)])));
    }

    #[test]
    fn a_service_planned_above_its_asking_has_nothing_unpaid() {
        let rows = unpaid_asking(&[service(36, 40)], &[], &[], |_| 0);
        assert_eq!(rows, Ok(BTreeMap::new()));
    }

    #[test]
    fn restock_and_household_asking_add_at_their_sellers() {
        let rows = unpaid_asking(
            &[],
            &[restock(site(2), 40, 30)],
            &[household(site(3), 40, 35)],
            |at| if at == key(3) { 3 } else { 0 },
        );
        assert_eq!(rows, Ok(BTreeMap::from([(key(2), 10), (key(3), 2)])));
    }

    #[test]
    fn priced_out_is_not_counted_twice() {
        let rows = unpaid_asking(&[], &[], &[household(site(3), 5, 0)], |_| 9);
        assert_eq!(rows, Ok(BTreeMap::new()));
    }
}
