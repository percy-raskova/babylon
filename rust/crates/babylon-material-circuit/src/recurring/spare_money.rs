//! Rule A6 (ADR314): the arithmetic of a workplace that plans from spare money.
//!
//! Pure functions. What was asked of a seller and not paid for, one period of what a site pays out,
//! how many batches or units its spare money carries, and how much a stocked input leaves room for.

use std::collections::BTreeMap;
use std::result::Result as StdResult;

use super::firms::{ProcurementReceipt, StockKey};
use crate::{HouseholdDemandReceipt, MaterialCircuitError, ServiceMarketReceipt};

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
#[cfg_attr(not(test), allow(dead_code, reason = "Task 3 calls them from extend"))]
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
#[cfg_attr(not(test), allow(dead_code, reason = "Task 3 calls them from extend"))]
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
#[cfg_attr(not(test), allow(dead_code, reason = "Task 3 calls them from extend"))]
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
#[cfg_attr(not(test), allow(dead_code, reason = "Task 3 calls them from extend"))]
pub(crate) fn input_room(available: u64, paid_for: u128, per_batch: u64) -> Result<u64> {
    if per_batch == 0 {
        return Err(MaterialCircuitError::Arithmetic);
    }
    let left = u128::from(available).saturating_sub(paid_for);
    u64::try_from(left / u128::from(per_batch)).map_err(|_| MaterialCircuitError::Arithmetic)
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
