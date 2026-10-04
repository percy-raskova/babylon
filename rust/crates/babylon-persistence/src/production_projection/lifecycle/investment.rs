//! Actual funded equipment purchase claims are joined to captured supplier policy.
use super::{offer_index, PeriodOrders, ProductionProjectionError, Result};
use babylon_material_circuit::{
    equipment_purchase_order_id, AccountId, InvestmentReceipt, MaterialCircuitState,
    OrderAccessMode, OrderRow, OutboundOrderId, PurchaseEscrow,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::BTreeMap;
pub(super) fn admit(
    prior: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    orders: &mut PeriodOrders,
    admissions: &mut BTreeMap<OutboundOrderId, PurchaseEscrow>,
) -> Result<()> {
    let Some(equipment) = super::super::equipment::get(prior) else {
        return if receipt.investment.is_empty() {
            Ok(())
        } else {
            Err(ProductionProjectionError::State)
        };
    };
    let definitions = super::super::equipment::Definitions::new(equipment)?;
    let mut policies: BTreeMap<_, _> = equipment
        .investment_policies
        .iter()
        .map(|r| (r.process_id, r))
        .collect();
    let offers = offer_index(prior)?;
    for r in &receipt.investment {
        r.validate().map_err(|_| ProductionProjectionError::State)?;
        let policy = policies
            .remove(&r.process_id)
            .ok_or(ProductionProjectionError::State)?;
        let (binding, definition) = definitions.get(r.process_id)?;
        if r.period != prior.period
            || r.order_id != equipment_purchase_order_id(prior.period, r.process_id)
            || r.site_id != binding.site_id
            || r.supplier_site_id != policy.supplier_site_id
            || r.admitted_units > policy.maximum_purchase_per_period
            || Some(&r.unit_price)
                != offers.get(&(
                    r.supplier_site_id,
                    definition.equipment_good_id,
                    definition.equipment_unit_id,
                ))
            || orders.deliveries.contains_key(&r.order_id)
        {
            return Err(ProductionProjectionError::State);
        }
        if r.admitted_units > 0 {
            admit_positive(r, definition, orders, admissions)?;
        }
    }
    if !policies.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}
fn admit_positive(
    r: &InvestmentReceipt,
    definition: &babylon_material_circuit::EquipmentDefinition,
    orders: &mut PeriodOrders,
    admissions: &mut BTreeMap<OutboundOrderId, PurchaseEscrow>,
) -> Result<()> {
    let order = OrderRow {
        order_id: r.order_id,
        access_mode: OrderAccessMode::CommoditySale,
        buyer_site_id: r.site_id,
        supplier_site_id: r.supplier_site_id,
        good_id: definition.equipment_good_id,
        unit_id: definition.equipment_unit_id,
        ordered: r.admitted_units,
        shipped: 0,
        delivered: 0,
        realized: 0,
        lost: 0,
    };
    orders.deliveries.insert(r.order_id, (order.clone(), order));
    orders.after_outbound.insert(r.order_id);
    let id = OutboundOrderId::Delivery(r.order_id);
    let purchase = PurchaseEscrow::new(
        id,
        AccountId::Site(r.site_id),
        AccountId::Site(r.supplier_site_id),
        r.admitted_units,
        r.unit_price,
    )
    .map_err(|_| ProductionProjectionError::State)?;
    if admissions.insert(id, purchase).is_some() {
        return Err(ProductionProjectionError::State);
    }
    Ok(())
}
