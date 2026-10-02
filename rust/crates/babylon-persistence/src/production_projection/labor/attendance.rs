//! Receipt reconciliation only; attendance and work allocation remain engine decisions.
use super::{
    add_time, Budgets, MaterialCircuitState, MaterialTickReceipts, Principal,
    ProductionProjectionError, Totals,
};
use babylon_material_circuit::{CircuitAccounting, MemberLaborUseReceipt};
use std::collections::{BTreeMap, BTreeSet};
type Result<T> = std::result::Result<T, ProductionProjectionError>;

#[derive(Default)]
struct MemberUses {
    available: u64,
    production: u64,
    handling: u64,
    maintenance: u64,
}
impl MemberUses {
    fn add(&mut self, row: &MemberLaborUseReceipt) -> Result<()> {
        self.available = add_time(self.available, row.available_hours, 1)?;
        self.production = add_time(self.production, row.production_hours, 1)?;
        self.handling = add_time(self.handling, row.handling_hours, 1)?;
        self.maintenance = add_time(self.maintenance, row.maintenance_hours, 1)?;
        Ok(())
    }
}

pub(super) fn reconcile(
    opening: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    actual: &Totals,
    available: &Budgets,
) -> Result<()> {
    let CircuitAccounting::Monetary(economy) = &opening.accounting else {
        return Ok(());
    };
    let mut terms: BTreeMap<_, _> = economy
        .employment
        .iter()
        .map(|r| (r.member_id, r))
        .collect();
    let hours: BTreeMap<_, _> = economy
        .member_labor
        .iter()
        .filter(|r| r.period == opening.period)
        .map(|r| (r.member_id, r.available_hours))
        .collect();
    let mut member_uses = BTreeMap::<Principal, MemberUses>::new();
    for row in &receipt.member_labor_use {
        let term = terms
            .remove(&row.member_id)
            .ok_or(ProductionProjectionError::History)?;
        row.validate()
            .map_err(|_| ProductionProjectionError::History)?;
        if row.period != opening.period
            || (row.site_id, row.unit_id, row.payee, row.compensation)
                != (term.site_id, term.unit_id, term.payee, term.compensation)
            || row.available_hours != hours.get(&row.member_id).copied().unwrap_or(0)
        {
            return Err(ProductionProjectionError::History);
        }
        member_uses
            .entry((row.site_id, row.unit_id))
            .or_default()
            .add(row)?;
    }
    if !terms.is_empty() {
        return Err(ProductionProjectionError::History);
    }
    let mut seen = BTreeSet::new();
    for row in &receipt.labor_use {
        let key = (row.site_id, row.unit_id);
        let members = member_uses
            .remove(&key)
            .ok_or(ProductionProjectionError::History)?;
        let physical = actual.get(&key).copied().unwrap_or_default();
        let production = physical
            .used
            .checked_sub(physical.handling_used)
            .and_then(|n| n.checked_sub(physical.maintenance_used))
            .ok_or(ProductionProjectionError::Arithmetic)?;
        if !seen.insert(key)
            || row.period != opening.period
            || row.available_hours != available.get(&key).copied().unwrap_or(0)
            || row.available_hours != members.available
            || row.used_hours != physical.used
            || (members.production, members.handling, members.maintenance)
                != (
                    production,
                    physical.handling_used,
                    physical.maintenance_used,
                )
        {
            return Err(ProductionProjectionError::History);
        }
    }
    if !member_uses.is_empty()
        || actual
            .iter()
            .any(|(key, row)| row.used > 0 && !seen.contains(key))
    {
        return Err(ProductionProjectionError::History);
    }
    Ok(())
}
