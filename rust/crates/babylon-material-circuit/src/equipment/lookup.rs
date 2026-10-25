//! Leaf implementation for the parent module; public paths stay on the parent.

use super::EquipmentBinding;
use super::EquipmentDefinition;
use super::ProductiveEquipment;

use crate::RollingProcessSupply;
use crate::{
    EquipmentPosition, InstalledEquipmentCohort, InstalledProcessCapacity, MaterialCircuitError,
    MaterialCircuitState, ProcessId,
};
use std::ops::Range;
use std::result::Result as StdResult;

pub(crate) type Result<T> = StdResult<T, MaterialCircuitError>;

/// Installed cohorts belonging to one process, in canonical order.
pub(crate) fn cohorts_for(
    cohorts: &[InstalledEquipmentCohort],
    process: ProcessId,
) -> Range<usize> {
    cohorts.partition_point(|r| r.process_id < process)
        ..cohorts.partition_point(|r| r.process_id <= process)
}

pub(crate) fn position_mut(state: &mut MaterialCircuitState) -> &mut EquipmentPosition {
    &mut state.capacity_reservations.equipment
}

pub(crate) fn position(state: &MaterialCircuitState) -> &EquipmentPosition {
    &state.capacity_reservations.equipment
}

impl ProductiveEquipment {
    pub(crate) fn definition(
        &self,
        process: ProcessId,
    ) -> Result<(&EquipmentBinding, &EquipmentDefinition)> {
        let i = self
            .bindings
            .binary_search_by_key(&process, |r| r.process_id)
            .map_err(|_| MaterialCircuitError::EquipmentInvariant)?;
        let b = &self.bindings[i];
        let i = self
            .definitions
            .binary_search_by_key(&b.definition_id, |r| r.id)
            .map_err(|_| MaterialCircuitError::EquipmentInvariant)?;
        Ok((b, &self.definitions[i]))
    }

    /// Exact gross current-period supply from installed cohorts.
    ///
    /// # Errors
    /// Refuses a missing binding or an overflowing aggregate.
    pub(crate) fn capacities(
        &self,
        cohorts: &[InstalledEquipmentCohort],
        period: u64,
    ) -> Result<Vec<InstalledProcessCapacity>> {
        let mut rows = Vec::with_capacity(self.bindings.len());
        for binding in &self.bindings {
            let (_, definition) = self.definition(binding.process_id)?;
            let mut capacity = 0_u64;
            for cohort in &cohorts[cohorts_for(cohorts, binding.process_id)] {
                if cohort.usable_from_period <= period {
                    let nameplate = cohort
                        .units
                        .checked_mul(definition.batches_per_unit_per_period)
                        .ok_or(MaterialCircuitError::Arithmetic)?;
                    capacity = capacity
                        .checked_add(nameplate.min(cohort.remaining_service_batches))
                        .ok_or(MaterialCircuitError::Arithmetic)?;
                }
            }
            rows.push(InstalledProcessCapacity {
                process_id: binding.process_id,
                site_id: binding.site_id,
                batches_per_period: capacity,
            });
        }
        rows.sort_by_key(|r| (r.site_id, r.process_id));
        Ok(rows)
    }
}

impl RollingProcessSupply {
    /// Exact gross current-period supply, with one captured owner.
    /// # Errors
    /// Refuses missing bindings or overflowing aggregate capacity.
    pub fn capacities(
        &self,
        cohorts: &[InstalledEquipmentCohort],
        period: u64,
    ) -> Result<Vec<InstalledProcessCapacity>> {
        match self {
            Self::CapturedNameplate(rows) => Ok(rows.clone()),
            Self::Equipment(content) => content.capacities(cohorts, period),
        }
    }
}
