//! Observed source members of a Designed economic function.
use super::{CohortReference, NationalCohortReference, NationalCohortReferenceError};
use babylon_kernel::economic_identity::EconomicFunction;
use std::collections::BTreeMap;

/// All admitted county/ownership observations for one captured source code.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct IndustrySourceRow {
    pub naics: String,
    pub known_jobs: u64,
    pub published_cells: usize,
    pub suppressed_cells: usize,
}

/// Campaign-wide 2024 QCEW job subtotals from the disjoint captured NAICS cut.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct IndustrySourceComposition {
    pub function: EconomicFunction,
    pub artifact_sha256: [u8; 32],
    pub mapping_sha256: [u8; 32],
    pub rows: Vec<IndustrySourceRow>,
}

impl NationalCohortReference {
    /// Group each admitted member once. A reported zero is a published cell.
    /// # Errors
    /// Refuses a job subtotal that exceeds the captured integer representation.
    pub fn industry_composition(
        &self,
        function: EconomicFunction,
    ) -> Result<IndustrySourceComposition, NationalCohortReferenceError> {
        let mut rows = BTreeMap::new();
        let groups = self
            .admitted_cohorts()
            .filter(|row| row.key().function == Some(function));
        for member in groups.flat_map(CohortReference::members) {
            let row = rows
                .entry(member.naics_code.as_str())
                .or_insert_with(|| IndustrySourceRow {
                    naics: member.naics_code.clone(),
                    known_jobs: 0,
                    published_cells: 0,
                    suppressed_cells: 0,
                });
            if let Some(jobs) = member.annual_average_jobs {
                row.known_jobs = row
                    .known_jobs
                    .checked_add(jobs)
                    .ok_or(NationalCohortReferenceError::NumericValue)?;
                row.published_cells += 1;
            } else {
                row.suppressed_cells += 1;
            }
        }
        Ok(IndustrySourceComposition {
            function,
            artifact_sha256: self.artifact_sha256(),
            mapping_sha256: self.function_mapping_sha256(),
            rows: rows.into_values().collect(),
        })
    }
}
