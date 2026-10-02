//! Committed quote evidence joined to actual native flows; no valuation is rerun.
mod flows;
mod model;
use super::{lifecycle, ProductionProjectionError};
use babylon_material_circuit::{
    CommodityKind, GoodId, MaterialCircuitState, PriceDecision, PricePolicy, PriceReceipt,
    SellerOffer, SiteId, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
pub use model::{
    CompletedGoodsPrice, GoodsPriceBasis, GoodsPriceReason, ProductionGoodsPriceAccount,
};
use std::collections::BTreeMap;
type Result<T> = std::result::Result<T, ProductionProjectionError>;
type Key = (SiteId, GoodId, UnitId);

fn offers(state: &MaterialCircuitState) -> Result<BTreeMap<Key, &SellerOffer>> {
    let goods: BTreeMap<_, _> = state
        .commodities
        .iter()
        .map(|r| ((r.good_id, r.unit_id), r.kind))
        .collect();
    let mut result = BTreeMap::new();
    for row in lifecycle::recurring(state)
        .map(|r| r.offers.as_slice())
        .unwrap_or_default()
    {
        if matches!(
            goods.get(&(row.good_id, row.unit_id)),
            Some(CommodityKind::PeriodService { .. })
        ) {
            continue;
        }
        if !goods.contains_key(&(row.good_id, row.unit_id))
            || result
                .insert((row.site_id, row.good_id, row.unit_id), row)
                .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(result)
}

pub(super) fn validate(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    orders: &lifecycle::PeriodOrders,
) -> Result<()> {
    let before = offers(prior)?;
    let after = offers(current)?;
    if before.keys().ne(after.keys()) || before.len() != receipt.prices.len() {
        return Err(ProductionProjectionError::State);
    }
    let flows = flows::Flows::new(prior, current, receipt, orders)?;
    let inventory: BTreeMap<_, _> = current
        .inventory
        .iter()
        .map(|r| ((r.site_id, r.good_id, r.unit_id), r.quantity))
        .collect();
    let mut expected = before;
    for row in &receipt.prices {
        let key = (row.site_id, row.good_id, row.unit_id);
        let offer = expected
            .remove(&key)
            .ok_or(ProductionProjectionError::State)?;
        let next = after.get(&key).ok_or(ProductionProjectionError::State)?;
        if row.period != prior.period
            || row.old_price != offer.unit_price
            || row.next_price != next.unit_price
            || offer.pricing != next.pricing
            || row.closing_stock != inventory.get(&key).copied().unwrap_or(0)
            || row.unserved_quantity != flows.waiting.get(&key).copied().unwrap_or(0)
        {
            return Err(ProductionProjectionError::State);
        }
        flows.validate_cost(row)?;
        validate_reason(row, &offer.pricing)?;
    }
    if !expected.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    flows.validate_handling_wages(receipt)
}

// Check the declared reason and bounded policy, not a second quote planner.
fn validate_reason(row: &PriceReceipt, policy: &PricePolicy) -> Result<()> {
    let unit_cost = row
        .cost
        .unit_cost()
        .map_err(|_| ProductionProjectionError::State)?;
    let cost_pressure = unit_cost.is_some_and(|cost| cost > row.old_price);
    let valid = match policy {
        PricePolicy::Fixed => row.reason == PriceDecision::Fixed && row.old_price == row.next_price,
        PricePolicy::Responsive {
            minimum,
            maximum,
            step,
            target_stock,
        } => {
            let shortage = row.unserved_quantity > 0 && row.closing_stock <= *target_stock;
            let delta = row
                .next_price
                .micro_units()
                .checked_sub(row.old_price.micro_units())
                .ok_or(ProductionProjectionError::Arithmetic)?;
            let within = row.next_price >= *minimum
                && row.next_price <= *maximum
                && delta.unsigned_abs() <= step.micro_units().unsigned_abs();
            within
                && match row.reason {
                    PriceDecision::UnservedDemand => shortage && delta >= 0,
                    PriceDecision::CostPressure => !shortage && cost_pressure && delta >= 0,
                    PriceDecision::ExcessStock => {
                        !shortage
                            && !cost_pressure
                            && row.unserved_quantity == 0
                            && row.closing_stock > *target_stock
                            && delta <= 0
                    }
                    PriceDecision::Hold => {
                        !(shortage
                            || cost_pressure
                            || (row.unserved_quantity == 0 && row.closing_stock > *target_stock))
                            && delta == 0
                    }
                    PriceDecision::Fixed => false,
                }
        }
        PricePolicy::ServiceResponsive { .. } => false,
    };
    if valid {
        Ok(())
    } else {
        Err(ProductionProjectionError::State)
    }
}

pub(super) fn project_with_labels(
    current: &MaterialCircuitState,
    prior: Option<&MaterialCircuitState>,
    receipts: Option<&MaterialTickReceipts>,
    labels: impl Fn(GoodId, UnitId) -> Option<(String, String)>,
) -> Result<Vec<ProductionGoodsPriceAccount>> {
    match (prior, receipts) {
        (None, None) if current.period == 1 => {}
        (Some(prior), Some(receipts)) => {
            let orders = lifecycle::join(prior, current, receipts)?;
            validate(prior, current, receipts, &orders)?;
        }
        _ => return Err(ProductionProjectionError::History),
    }
    let completed: BTreeMap<_, _> = receipts
        .map(|r| r.prices.as_slice())
        .unwrap_or_default()
        .iter()
        .map(|r| ((r.site_id, r.good_id, r.unit_id), r))
        .collect();
    offers(current)?
        .into_iter()
        .map(|(key, offer)| {
            let (good, unit) = labels(key.1, key.2).ok_or(ProductionProjectionError::Content)?;
            Ok(ProductionGoodsPriceAccount {
                site_id: crate::michigan_economy::digest_hex(&key.0.as_bytes()),
                good_id: crate::michigan_economy::digest_hex(&key.1.as_bytes()),
                unit_id: crate::michigan_economy::digest_hex(&key.2.as_bytes()),
                good,
                unit,
                current_price_micro: offer.unit_price.micro_units(),
                completed: completed
                    .get(&key)
                    .map(|r| model::completed(r))
                    .transpose()?,
            })
        })
        .collect()
}
