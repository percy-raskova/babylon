//! Designed values for the one-provider Wayne maintenance witness.

use super::{statewide::DesignedEvidence, MichiganDefinesError, MAX_EXACT_INTEGER};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all = "SCREAMING_SNAKE_CASE")]
pub(crate) struct MaintenanceDefines {
    pub evidence_class: DesignedEvidence,
    pub consumer_opening_metal_stock: u64,
    pub opening_service_batches: u64,
    pub provider_opening_spare_parts: u64,
    pub shortage_opening_spare_parts: u64,
    pub spare_units_per_job: u64,
    pub labor_units_per_job: u64,
    pub enabled_batches_per_job: u64,
    pub maximum_jobs_per_period: u64,
    pub employed_people: u64,
    pub reserve_people: u64,
    pub shortage_employed_people: u64,
    pub shortage_reserve_people: u64,
    pub replenishment_order_units: u64,
}
impl MaintenanceDefines {
    pub(super) fn validate(&self, hours_per_person: u64) -> Result<(), MichiganDefinesError> {
        let bad = MichiganDefinesError::Value("bounded maintenance quantities and conserved crew");
        let force = self.employed_people.checked_add(self.reserve_people);
        if self.consumer_opening_metal_stock == 0
            || self.spare_units_per_job == 0
            || self.labor_units_per_job == 0
            || self.enabled_batches_per_job == 0
            || self.maximum_jobs_per_period == 0
            || self.replenishment_order_units == 0
            || force.is_none_or(|n| n == 0 || n > MAX_EXACT_INTEGER)
            || force
                != self
                    .shortage_employed_people
                    .checked_add(self.shortage_reserve_people)
            || self.shortage_employed_people > self.employed_people
            || self.shortage_opening_spare_parts > self.provider_opening_spare_parts
            || force
                .and_then(|n| n.checked_mul(hours_per_person))
                .is_none_or(|n| n > MAX_EXACT_INTEGER)
            || self
                .maximum_jobs_per_period
                .checked_mul(self.labor_units_per_job)
                .is_none_or(|n| n > MAX_EXACT_INTEGER)
            || self
                .maximum_jobs_per_period
                .checked_mul(self.spare_units_per_job)
                .is_none()
            || self
                .maximum_jobs_per_period
                .checked_mul(self.enabled_batches_per_job)
                .is_none_or(|n| self.opening_service_batches > n)
            || self
                .provider_opening_spare_parts
                .checked_add(self.replenishment_order_units)
                .and_then(|n| n.checked_mul(1000))
                .is_none()
            || self
                .consumer_opening_metal_stock
                .checked_mul(1000)
                .is_none()
        {
            return Err(bad);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::super::MichiganDefines;

    #[test]
    fn maintenance_authoring_refuses_untyped_invalid_or_unbounded_quantities() {
        let source = include_str!("../../../../../content/scenarios/michigan/defines.toml");
        let original: toml::Value = toml::from_str(source).unwrap();
        for (field, value) in [
            ("SPARE_UNITS_PER_JOB", 0),
            ("LABOR_UNITS_PER_JOB", 0),
            ("ENABLED_BATCHES_PER_JOB", 0),
            ("MAXIMUM_JOBS_PER_PERIOD", 0),
            ("OPENING_SERVICE_BATCHES", 17),
            ("REPLENISHMENT_ORDER_UNITS", 0),
            ("SHORTAGE_RESERVE_PEOPLE", 2),
            ("SHORTAGE_OPENING_SPARE_PARTS", 257),
            ("EMPLOYED_PEOPLE", i64::MAX),
            ("CONSUMER_OPENING_METAL_STOCK", -1),
        ] {
            let mut changed = original.clone();
            changed["maintenance"][field] = value.into();
            assert!(
                MichiganDefines::parse(&toml::to_string(&changed).unwrap()).is_err(),
                "{field}"
            );
        }
        for value in [
            toml::Value::String("Observed".to_owned()),
            toml::Value::Boolean(true),
        ] {
            let mut changed = original.clone();
            changed["maintenance"]["EVIDENCE_CLASS"] = value;
            assert!(MichiganDefines::parse(&toml::to_string(&changed).unwrap()).is_err());
        }
        let mut changed = original;
        changed.as_table_mut().unwrap().remove("maintenance");
        assert!(MichiganDefines::parse(&toml::to_string(&changed).unwrap()).is_err());
    }
}
