//! Transient installation eligibility; physical stock and sale principals stay authoritative.
use super::{
    InstallationDecisionReceipt, InstallationPolicy, InstallationTarget, ProductiveEquipment,
    Result,
};
use crate::inventory::InventoryLedger;
use crate::{CircuitAccounting, MaterialCircuitError, MaterialCircuitState};

pub(super) fn sale_commitments(state: &MaterialCircuitState) -> Result<InventoryLedger> {
    let mut rows = InventoryLedger::new();
    for order in &state.orders {
        let quantity = order
            .ordered
            .checked_sub(order.shipped)
            .ok_or(MaterialCircuitError::EquipmentInvariant)?;
        add(
            &mut rows,
            (order.supplier_site_id, order.good_id, order.unit_id),
            quantity,
        )?;
    }
    for order in &state.final_demand_orders {
        let quantity = order
            .ordered
            .checked_sub(order.fulfilled)
            .ok_or(MaterialCircuitError::EquipmentInvariant)?;
        add(
            &mut rows,
            (order.retailer_site_id, order.good_id, order.unit_id),
            quantity,
        )?;
    }
    Ok(rows)
}

fn add(
    rows: &mut InventoryLedger,
    key: (crate::SiteId, crate::GoodId, crate::UnitId),
    quantity: u64,
) -> Result<()> {
    let value = rows.entry(key).or_default();
    *value = value
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}

/// A temporary eligibility mask, not a stock reservation or another durable owner.
/// Uncovered pledges remain available to mask prospective inbound units too.
pub(super) fn protect_sales(available: &mut InventoryLedger, pledges: &mut InventoryLedger) {
    for (key, pledged) in pledges {
        if let Some(quantity) = available.get_mut(key) {
            let covered = (*quantity).min(*pledged);
            *quantity -= covered;
            *pledged -= covered;
        }
    }
}

pub(super) fn eligible_inventory(state: &MaterialCircuitState) -> Result<InventoryLedger> {
    let mut available = state
        .inventory
        .iter()
        .map(|r| ((r.site_id, r.good_id, r.unit_id), r.quantity))
        .collect();
    protect_sales(&mut available, &mut sale_commitments(state)?);
    Ok(available)
}

pub(super) fn planned_batches(
    state: &MaterialCircuitState,
    process: crate::ProcessId,
) -> Option<u64> {
    let CircuitAccounting::Monetary(m) = &state.accounting else {
        return None;
    };
    let rows = &m.recurring.as_ref()?.production;
    rows.binary_search_by_key(&process, |r| r.process_id)
        .ok()
        .map(|i| rows[i].planned_batches)
}

pub(super) fn decision(
    state: &MaterialCircuitState,
    e: &ProductiveEquipment,
    p: &InstallationPolicy,
) -> Result<InstallationDecisionReceipt> {
    let (binding, definition) = e.definition(p.process_id)?;
    let planned = planned_batches(state, p.process_id);
    let target = match p.target {
        InstallationTarget::FixedUnits(units) => units,
        InstallationTarget::ProductionPlan { replacement_units } => planned
            .ok_or(MaterialCircuitError::EquipmentInvariant)?
            .div_ceil(definition.batches_per_unit_per_period)
            .max(replacement_units),
    };
    let installed = e.cohorts[e.cohorts_for(p.process_id)]
        .iter()
        .filter(|r| r.remaining_service_batches > 0)
        .try_fold(0_u64, |n, r| {
            n.checked_add(r.units)
                .ok_or(MaterialCircuitError::Arithmetic)
        })?;
    let lo = e.pending.partition_point(|r| r.process_id < p.process_id);
    let hi = e.pending.partition_point(|r| r.process_id <= p.process_id);
    let pending = e.pending[lo..hi].iter().try_fold(0_u64, |n, r| {
        n.checked_add(r.units)
            .ok_or(MaterialCircuitError::Arithmetic)
    })?;
    let position = installed
        .checked_add(pending)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(InstallationDecisionReceipt {
        period: state.period,
        process_id: p.process_id,
        site_id: binding.site_id,
        captured_plan_batches: planned.unwrap_or(0),
        target_units: target,
        installed_units: installed,
        pending_units: pending,
        requested_units: target.saturating_sub(position),
        started_units: 0,
    })
}
