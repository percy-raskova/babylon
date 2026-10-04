//! Instrument cost follows finite productive use; installation remains an asset.
use super::{add, portion, sub, zero, CostClose, HistoricalCostBook, Result};
use crate::{
    AccountId, EquipmentAssetId, EquipmentCohortId, EquipmentWearReceipt, InstallationId,
    MaterialCircuitError, MaterialCircuitState, ProcessId, SiteId, UnitId,
};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;
impl CostClose {
    pub(crate) fn wear(
        &mut self,
        state: &mut MaterialCircuitState,
        process: ProcessId,
        batches: u64,
    ) -> Result<Currency> {
        let period = state.period;
        let Some(e) = crate::equipment::get_mut(state) else {
            return Ok(zero());
        };
        if batches == 0 {
            return Ok(zero());
        }
        let (binding, definition) = e.definition(process)?;
        let site = binding.site_id;
        let rate = definition.batches_per_unit_per_period;
        let active = self
            .active
            .as_mut()
            .ok_or(MaterialCircuitError::EquipmentInvariant)?;
        let mut remaining = batches;
        let mut total = zero();
        let range = e.cohorts_for(process);
        for cohort in &mut e.cohorts[range] {
            if remaining == 0 {
                break;
            }
            if cohort.usable_from_period > period {
                continue;
            }
            let used = remaining
                .min(
                    cohort
                        .units
                        .checked_mul(rate)
                        .ok_or(MaterialCircuitError::Arithmetic)?,
                )
                .min(cohort.remaining_service_batches);
            if used == 0 {
                continue;
            }
            let key = EquipmentAssetId::Installed(cohort.id);
            let &(owner, opening) = active
                .book
                .equipment
                .get(&key)
                .ok_or(MaterialCircuitError::ValuationInvariant)?;
            if owner != site {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
            let taken = portion(opening, cohort.remaining_service_batches, used)?;
            let retained = sub(opening, taken)?;
            let row = EquipmentWearReceipt {
                period,
                cohort_id: cohort.id,
                process_id: process,
                site_id: site,
                opening_service_batches: cohort.remaining_service_batches,
                used_batches: used,
                remaining_service_batches: cohort.remaining_service_batches - used,
                opening_carrying: opening,
                carried_to_output: taken,
                closing_carrying: retained,
            };
            row.validate()?;
            self.wear_receipts.push(row);
            cohort.remaining_service_batches -= used;
            remaining -= used;
            if cohort.remaining_service_batches == 0 {
                active.book.equipment.remove(&key);
            } else {
                active.book.equipment.insert(key, (site, retained));
            }
            total = add(total, taken)?;
        }
        if remaining != 0 {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
        let statement = active.statement(AccountId::Site(site))?;
        statement.equipment_wear_capitalized = add(statement.equipment_wear_capitalized, total)?;
        Ok(total)
    }
    pub(crate) fn installation_start(
        &mut self,
        id: InstallationId,
        site: SiteId,
        amount: Currency,
    ) -> Result<()> {
        let a = self
            .active
            .as_mut()
            .ok_or(MaterialCircuitError::EquipmentInvariant)?;
        if a.book
            .equipment
            .insert(EquipmentAssetId::Installation(id), (site, amount))
            .is_some()
        {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        Ok(())
    }
    pub(crate) fn installation_work(
        &mut self,
        id: InstallationId,
        site: SiteId,
        unit: UnitId,
        hours: u64,
    ) -> Result<(Currency, Currency)> {
        let wages =
            self.attendance
                .consume(site, unit, hours, crate::payments::LaborUse::Installation)?;
        let a = self
            .active
            .as_mut()
            .ok_or(MaterialCircuitError::EquipmentInvariant)?;
        let (owner, amount) = a
            .book
            .equipment
            .get_mut(&EquipmentAssetId::Installation(id))
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        if *owner != site {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
        *amount = add(*amount, wages)?;
        let closing = *amount;
        let statement = a.statement(AccountId::Site(site))?;
        statement.installation_labor_capitalized =
            add(statement.installation_labor_capitalized, wages)?;
        Ok((wages, closing))
    }
    pub(crate) fn installation_carrying(&self, id: InstallationId) -> Result<Currency> {
        self.active
            .as_ref()
            .and_then(|a| a.book.equipment.get(&EquipmentAssetId::Installation(id)))
            .map(|r| r.1)
            .ok_or(MaterialCircuitError::ValuationInvariant)
    }
    pub(crate) fn installation_complete(
        &mut self,
        id: InstallationId,
        cohort: EquipmentCohortId,
    ) -> Result<()> {
        let a = self
            .active
            .as_mut()
            .ok_or(MaterialCircuitError::EquipmentInvariant)?;
        let value = a
            .book
            .equipment
            .remove(&EquipmentAssetId::Installation(id))
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        if a.book
            .equipment
            .insert(EquipmentAssetId::Installed(cohort), value)
            .is_some()
        {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        Ok(())
    }
    pub(crate) fn investment_earnings(&self, site: SiteId) -> Result<Currency> {
        let Some(a) = &self.active else {
            return Ok(zero());
        };
        let owner = AccountId::Site(site);
        Ok(sub(
            self.eligible_earnings(owner)?,
            a.distributions.get(&owner).copied().unwrap_or_else(zero),
        )?
        .max(zero()))
    }
}
pub(super) fn validate_assets(
    state: &MaterialCircuitState,
    book: &HistoricalCostBook,
) -> Result<()> {
    let mut expected = BTreeMap::new();
    if let Some(e) = crate::equipment::get(state) {
        for c in &e.cohorts {
            let (b, _) = e.definition(c.process_id)?;
            expected.insert(EquipmentAssetId::Installed(c.id), b.site_id);
        }
        for p in &e.pending {
            let (b, _) = e.definition(p.process_id)?;
            expected.insert(EquipmentAssetId::Installation(p.id), b.site_id);
        }
    }
    if expected.len() != book.equipment.len()
        || expected
            .iter()
            .any(|(id, owner)| book.equipment.get(id).is_none_or(|row| row.0 != *owner))
    {
        return Err(MaterialCircuitError::ValuationInvariant);
    }
    Ok(())
}
