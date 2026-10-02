//! Actual productive equipment; money alone supplies no productive capacity.
mod installation;
mod investment;
mod model;
mod receipts;
mod validation;
use crate::{
    CapacitySupply, InstalledProcessCapacity, MaterialCircuitError, MaterialCircuitState, ProcessId,
};
pub use installation::equipment_installation_id;
pub(crate) use installation::{install, work_requests};
pub use investment::equipment_purchase_order_id;
pub(crate) use investment::invest;
pub use model::*;
pub use receipts::*;
pub(crate) use validation::{canonicalize, row_limits, validate};
type Result<T> = std::result::Result<T, MaterialCircuitError>;
pub(crate) fn get(state: &MaterialCircuitState) -> Option<&ProductiveEquipment> {
    match &state.capacity_supply {
        CapacitySupply::Rolling(r) => match &r.processes {
            RollingProcessSupply::Equipment(e) => Some(e),
            RollingProcessSupply::CapturedNameplate(_) => None,
        },
        CapacitySupply::FiniteSchedule => None,
    }
}
pub(crate) fn get_mut(state: &mut MaterialCircuitState) -> Option<&mut ProductiveEquipment> {
    match &mut state.capacity_supply {
        CapacitySupply::Rolling(r) => match &mut r.processes {
            RollingProcessSupply::Equipment(e) => Some(e),
            RollingProcessSupply::CapturedNameplate(_) => None,
        },
        CapacitySupply::FiniteSchedule => None,
    }
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
    pub(crate) fn cohorts_for(&self, process: ProcessId) -> std::ops::Range<usize> {
        self.cohorts.partition_point(|r| r.process_id < process)
            ..self.cohorts.partition_point(|r| r.process_id <= process)
    }
}
impl RollingProcessSupply {
    /// Exact gross current-period supply, with one captured owner.
    /// # Errors
    /// Refuses missing bindings or overflowing aggregate capacity.
    pub fn capacities(&self, period: u64) -> Result<Vec<InstalledProcessCapacity>> {
        match self {
            Self::CapturedNameplate(rows) => Ok(rows.clone()),
            Self::Equipment(e) => {
                let mut rows = Vec::with_capacity(e.bindings.len());
                for b in &e.bindings {
                    let (_, d) = e.definition(b.process_id)?;
                    let mut capacity = 0_u64;
                    for c in &e.cohorts[e.cohorts_for(b.process_id)] {
                        if c.usable_from_period <= period {
                            let nameplate = c
                                .units
                                .checked_mul(d.batches_per_unit_per_period)
                                .ok_or(MaterialCircuitError::Arithmetic)?;
                            capacity = capacity
                                .checked_add(nameplate.min(c.remaining_service_batches))
                                .ok_or(MaterialCircuitError::Arithmetic)?;
                        }
                    }
                    rows.push(InstalledProcessCapacity {
                        process_id: b.process_id,
                        site_id: b.site_id,
                        batches_per_period: capacity,
                    });
                }
                rows.sort_by_key(|r| (r.site_id, r.process_id));
                Ok(rows)
            }
        }
    }
}
