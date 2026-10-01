//! Recurring evidence checks only relations carried by these rows.
//! Policy joins, affordability against opening cash and recipes belong to the host.
use std::collections::BTreeSet;

use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    FinalDemandPrincipalId, GoodId, HouseholdConsumptionReceipt, HouseholdDemandReceipt, OrderId,
    PriceDecision, PriceReceipt, ProcessId, ProcurementReceipt, ProductionPlanReceipt, SiteId,
    UnitId,
};

use super::{MaterialWorldError, ReceiptCursor};

pub(super) const DEMAND_BYTES: usize = 240;
pub(super) const CONSUMPTION_BYTES: usize = 144;
pub(super) const PROCUREMENT_BYTES: usize = 224;
pub(super) const PLAN_BYTES: usize = 120;
pub(super) const PRICE_BYTES: usize = 153;

fn ordered<T, K: Ord>(rows: &[T], key: impl Fn(&T) -> K) -> bool {
    rows.windows(2).all(|pair| key(&pair[0]) < key(&pair[1]))
}

pub(super) fn validate_order(
    demand: &[HouseholdDemandReceipt],
    consumption: &[HouseholdConsumptionReceipt],
    procurement: &[ProcurementReceipt],
    plans: &[ProductionPlanReceipt],
    prices: &[PriceReceipt],
) -> Result<(), MaterialWorldError> {
    let demand_ids: BTreeSet<_> = demand.iter().map(|row| row.order_id).collect();
    let procurement_ids: BTreeSet<_> = procurement.iter().map(|row| row.order_id).collect();
    if !ordered(demand, |row| (row.principal_id, row.good_id, row.unit_id))
        || !ordered(consumption, |row| {
            (row.principal_id, row.good_id, row.unit_id)
        })
        || !ordered(procurement, |row| {
            (
                row.buyer_site_id,
                row.supplier_site_id,
                row.good_id,
                row.unit_id,
            )
        })
        || !ordered(plans, |row| row.process_id)
        || !ordered(prices, |row| (row.site_id, row.good_id, row.unit_id))
        || demand_ids.len() != demand.len()
        || procurement_ids.len() != procurement.len()
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

fn funded_price(price: Currency, quantity: u64) -> bool {
    price.micro_units() > 0
        && price
            .micro_units()
            .checked_mul(i128::from(quantity))
            .is_some()
}

fn validate_demand(row: &HouseholdDemandReceipt, period: u64) -> Result<(), MaterialWorldError> {
    if row.period != period
        || row.required_quantity == 0
        || row.desired_quantity < row.required_quantity.saturating_sub(row.opening_stock)
        || row.requested_quantity > row.desired_quantity
        || row.admitted_quantity > row.requested_quantity
        || row.fulfilled_quantity.checked_add(row.expired_quantity) != Some(row.admitted_quantity)
        || !funded_price(row.unit_price, row.admitted_quantity)
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

fn validate_consumption(
    row: &HouseholdConsumptionReceipt,
    period: u64,
) -> Result<(), MaterialWorldError> {
    if row.period != period
        || row.required_quantity == 0
        || row.consumed_quantity != row.available_quantity.min(row.required_quantity)
        || row.consumed_quantity.checked_add(row.unmet_quantity) != Some(row.required_quantity)
        || row.consumed_quantity.checked_add(row.closing_quantity) != Some(row.available_quantity)
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

fn validate_procurement(row: &ProcurementReceipt, period: u64) -> Result<(), MaterialWorldError> {
    let position = row
        .on_hand
        .checked_add(row.outstanding_inbound)
        .ok_or(MaterialWorldError::Wire)?;
    if row.period != period
        || row.buyer_site_id == row.supplier_site_id
        || row.desired_quantity > row.target_stock.saturating_sub(position)
        || row.admitted_quantity > row.desired_quantity
        || !funded_price(row.unit_price, row.admitted_quantity)
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

fn validate_plan(row: &ProductionPlanReceipt, period: u64) -> Result<(), MaterialWorldError> {
    let target = row
        .dispatched_quantity
        .checked_add(row.unshipped_quantity)
        .and_then(|value| value.checked_add(row.output_buffer))
        .ok_or(MaterialWorldError::Wire)?;
    let wanted = target.saturating_sub(row.closing_output_stock);
    // Output per batch is absent. Any positive integer batch size entails only
    // these bounds; exact ceil division needs the captured process recipe.
    if row.period != period
        || period.checked_add(1) != Some(row.next_period)
        || (row.planned_batches == 0) != (wanted == 0)
        || row.planned_batches > wanted
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

fn validate_price(row: &PriceReceipt, period: u64) -> Result<(), MaterialWorldError> {
    let old = row.old_price.micro_units();
    let next = row.next_price.micro_units();
    let justified = match row.reason {
        PriceDecision::Fixed | PriceDecision::Hold => next == old,
        PriceDecision::UnservedDemand => row.unserved_quantity > 0 && next >= old,
        PriceDecision::ExcessStock => {
            row.unserved_quantity == 0 && row.closing_stock > 0 && next <= old
        }
    };
    if row.period != period || old <= 0 || next <= 0 || !justified {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}

fn append(ids: &[[u8; 32]], values: &[u64], bytes: &mut Vec<u8>) {
    for id in ids {
        bytes.extend_from_slice(id);
    }
    for value in values {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
}

fn currency(cursor: &mut ReceiptCursor<'_>) -> Result<Currency, MaterialWorldError> {
    Ok(Currency::from_micro_units(i128::from_be_bytes(
        cursor.take()?,
    )))
}

pub(super) fn encode_demand(
    row: &HouseholdDemandReceipt,
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    validate_demand(row, period)?;
    append(
        &[
            row.principal_id.as_bytes(),
            row.retailer_site_id.as_bytes(),
            row.good_id.as_bytes(),
            row.unit_id.as_bytes(),
            row.order_id.as_bytes(),
        ],
        &[
            row.period,
            row.opening_stock,
            row.required_quantity,
            row.desired_quantity,
            row.requested_quantity,
            row.admitted_quantity,
            row.fulfilled_quantity,
            row.expired_quantity,
        ],
        bytes,
    );
    bytes.extend_from_slice(&row.unit_price.micro_units().to_be_bytes());
    Ok(())
}

pub(super) fn decode_demand(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<HouseholdDemandReceipt, MaterialWorldError> {
    let row = HouseholdDemandReceipt {
        principal_id: FinalDemandPrincipalId::from_bytes(cursor.take()?),
        retailer_site_id: SiteId::from_bytes(cursor.take()?),
        good_id: GoodId::from_bytes(cursor.take()?),
        unit_id: UnitId::from_bytes(cursor.take()?),
        order_id: OrderId::from_bytes(cursor.take()?),
        period: cursor.u64()?,
        opening_stock: cursor.u64()?,
        required_quantity: cursor.u64()?,
        desired_quantity: cursor.u64()?,
        requested_quantity: cursor.u64()?,
        admitted_quantity: cursor.u64()?,
        fulfilled_quantity: cursor.u64()?,
        expired_quantity: cursor.u64()?,
        unit_price: currency(cursor)?,
    };
    validate_demand(&row, period)?;
    Ok(row)
}

pub(super) fn encode_consumption(
    row: &HouseholdConsumptionReceipt,
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    validate_consumption(row, period)?;
    append(
        &[
            row.principal_id.as_bytes(),
            row.good_id.as_bytes(),
            row.unit_id.as_bytes(),
        ],
        &[
            row.period,
            row.required_quantity,
            row.available_quantity,
            row.consumed_quantity,
            row.unmet_quantity,
            row.closing_quantity,
        ],
        bytes,
    );
    Ok(())
}

pub(super) fn decode_consumption(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<HouseholdConsumptionReceipt, MaterialWorldError> {
    let row = HouseholdConsumptionReceipt {
        principal_id: FinalDemandPrincipalId::from_bytes(cursor.take()?),
        good_id: GoodId::from_bytes(cursor.take()?),
        unit_id: UnitId::from_bytes(cursor.take()?),
        period: cursor.u64()?,
        required_quantity: cursor.u64()?,
        available_quantity: cursor.u64()?,
        consumed_quantity: cursor.u64()?,
        unmet_quantity: cursor.u64()?,
        closing_quantity: cursor.u64()?,
    };
    validate_consumption(&row, period)?;
    Ok(row)
}

pub(super) fn encode_procurement(
    row: &ProcurementReceipt,
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    validate_procurement(row, period)?;
    append(
        &[
            row.order_id.as_bytes(),
            row.buyer_site_id.as_bytes(),
            row.supplier_site_id.as_bytes(),
            row.good_id.as_bytes(),
            row.unit_id.as_bytes(),
        ],
        &[
            row.period,
            row.on_hand,
            row.outstanding_inbound,
            row.target_stock,
            row.desired_quantity,
            row.admitted_quantity,
        ],
        bytes,
    );
    bytes.extend_from_slice(&row.unit_price.micro_units().to_be_bytes());
    Ok(())
}

pub(super) fn decode_procurement(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<ProcurementReceipt, MaterialWorldError> {
    let row = ProcurementReceipt {
        order_id: OrderId::from_bytes(cursor.take()?),
        buyer_site_id: SiteId::from_bytes(cursor.take()?),
        supplier_site_id: SiteId::from_bytes(cursor.take()?),
        good_id: GoodId::from_bytes(cursor.take()?),
        unit_id: UnitId::from_bytes(cursor.take()?),
        period: cursor.u64()?,
        on_hand: cursor.u64()?,
        outstanding_inbound: cursor.u64()?,
        target_stock: cursor.u64()?,
        desired_quantity: cursor.u64()?,
        admitted_quantity: cursor.u64()?,
        unit_price: currency(cursor)?,
    };
    validate_procurement(&row, period)?;
    Ok(row)
}

pub(super) fn encode_plan(
    row: &ProductionPlanReceipt,
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    validate_plan(row, period)?;
    append(
        &[row.process_id.as_bytes(), row.site_id.as_bytes()],
        &[
            row.period,
            row.next_period,
            row.dispatched_quantity,
            row.unshipped_quantity,
            row.closing_output_stock,
            row.output_buffer,
            row.planned_batches,
        ],
        bytes,
    );
    Ok(())
}

pub(super) fn decode_plan(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<ProductionPlanReceipt, MaterialWorldError> {
    let row = ProductionPlanReceipt {
        process_id: ProcessId::from_bytes(cursor.take()?),
        site_id: SiteId::from_bytes(cursor.take()?),
        period: cursor.u64()?,
        next_period: cursor.u64()?,
        dispatched_quantity: cursor.u64()?,
        unshipped_quantity: cursor.u64()?,
        closing_output_stock: cursor.u64()?,
        output_buffer: cursor.u64()?,
        planned_batches: cursor.u64()?,
    };
    validate_plan(&row, period)?;
    Ok(row)
}

pub(super) fn encode_price(
    row: &PriceReceipt,
    period: u64,
    bytes: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    validate_price(row, period)?;
    append(
        &[
            row.site_id.as_bytes(),
            row.good_id.as_bytes(),
            row.unit_id.as_bytes(),
        ],
        &[row.period],
        bytes,
    );
    bytes.extend_from_slice(&row.old_price.micro_units().to_be_bytes());
    bytes.extend_from_slice(&row.next_price.micro_units().to_be_bytes());
    append(&[], &[row.unserved_quantity, row.closing_stock], bytes);
    bytes.push(match row.reason {
        PriceDecision::Fixed => 1,
        PriceDecision::Hold => 2,
        PriceDecision::UnservedDemand => 3,
        PriceDecision::ExcessStock => 4,
    });
    Ok(())
}

pub(super) fn decode_price(
    cursor: &mut ReceiptCursor<'_>,
    period: u64,
) -> Result<PriceReceipt, MaterialWorldError> {
    let row = PriceReceipt {
        site_id: SiteId::from_bytes(cursor.take()?),
        good_id: GoodId::from_bytes(cursor.take()?),
        unit_id: UnitId::from_bytes(cursor.take()?),
        period: cursor.u64()?,
        old_price: currency(cursor)?,
        next_price: currency(cursor)?,
        unserved_quantity: cursor.u64()?,
        closing_stock: cursor.u64()?,
        reason: match cursor.take::<1>()?[0] {
            1 => PriceDecision::Fixed,
            2 => PriceDecision::Hold,
            3 => PriceDecision::UnservedDemand,
            4 => PriceDecision::ExcessStock,
            _ => return Err(MaterialWorldError::Wire),
        },
    };
    validate_price(&row, period)?;
    Ok(row)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn roundtrip<T: std::fmt::Debug + PartialEq>(
        row: &T,
        encode: fn(&T, u64, &mut Vec<u8>) -> Result<(), MaterialWorldError>,
        decode: fn(&mut ReceiptCursor<'_>, u64) -> Result<T, MaterialWorldError>,
        width: usize,
    ) {
        let mut bytes = vec![123];
        encode(row, 7, &mut bytes).unwrap();
        assert_eq!(bytes.len(), width + 1);
        let mut cursor = ReceiptCursor {
            bytes: &bytes,
            position: 1,
        };
        assert_eq!(&decode(&mut cursor, 7).unwrap(), row);
        assert_eq!(cursor.position, bytes.len());
        let mut rejected = vec![123];
        assert_eq!(encode(row, 8, &mut rejected), Err(MaterialWorldError::Wire));
        assert_eq!(rejected, [123]);
    }

    #[test]
    fn typed_recurring_rows_roundtrip_exactly_and_wrong_period_never_appends() {
        let principal_id = FinalDemandPrincipalId::from_bytes([1; 32]);
        let site_id = SiteId::from_bytes([2; 32]);
        let good_id = GoodId::from_bytes([3; 32]);
        let unit_id = UnitId::from_bytes([4; 32]);
        let order_id = OrderId::from_bytes([5; 32]);
        let unit_price = Currency::from_micro_units((1_i128 << 90) + 7);
        roundtrip(
            &HouseholdDemandReceipt {
                period: 7,
                principal_id,
                retailer_site_id: site_id,
                good_id,
                unit_id,
                order_id,
                opening_stock: 2,
                required_quantity: 6,
                desired_quantity: 5,
                requested_quantity: 4,
                admitted_quantity: 3,
                fulfilled_quantity: 2,
                expired_quantity: 1,
                unit_price,
            },
            encode_demand,
            decode_demand,
            DEMAND_BYTES,
        );
        roundtrip(
            &HouseholdConsumptionReceipt {
                period: 7,
                principal_id,
                good_id,
                unit_id,
                required_quantity: 6,
                available_quantity: 4,
                consumed_quantity: 4,
                unmet_quantity: 2,
                closing_quantity: 0,
            },
            encode_consumption,
            decode_consumption,
            CONSUMPTION_BYTES,
        );
        roundtrip(
            &ProcurementReceipt {
                period: 7,
                order_id,
                buyer_site_id: SiteId::from_bytes([1; 32]),
                supplier_site_id: site_id,
                good_id,
                unit_id,
                on_hand: 2,
                outstanding_inbound: 3,
                target_stock: 10,
                desired_quantity: 4,
                admitted_quantity: 3,
                unit_price,
            },
            encode_procurement,
            decode_procurement,
            PROCUREMENT_BYTES,
        );
        roundtrip(
            &ProductionPlanReceipt {
                period: 7,
                next_period: 8,
                process_id: ProcessId::from_bytes([1; 32]),
                site_id,
                dispatched_quantity: 3,
                unshipped_quantity: 2,
                closing_output_stock: 1,
                output_buffer: 4,
                planned_batches: 4,
            },
            encode_plan,
            decode_plan,
            PLAN_BYTES,
        );
        roundtrip(
            &PriceReceipt {
                period: 7,
                site_id,
                good_id,
                unit_id,
                old_price: unit_price,
                next_price: unit_price,
                unserved_quantity: 1,
                closing_stock: 0,
                reason: PriceDecision::UnservedDemand,
            },
            encode_price,
            decode_price,
            PRICE_BYTES,
        );
    }

    #[test]
    fn planned_output_cannot_wrap_the_next_period_or_claim_a_missing_recipe() {
        let mut row = ProductionPlanReceipt {
            period: u64::MAX,
            next_period: 0,
            process_id: ProcessId::from_bytes([1; 32]),
            site_id: SiteId::from_bytes([2; 32]),
            dispatched_quantity: 7,
            unshipped_quantity: 0,
            closing_output_stock: 0,
            output_buffer: 0,
            planned_batches: 3,
        };
        assert_eq!(validate_plan(&row, u64::MAX), Err(MaterialWorldError::Wire));
        row.period = 7;
        row.next_period = 8;
        // Exact batch admission requires the absent process coefficient.
        assert!(validate_plan(&row, 7).is_ok());
    }
}
