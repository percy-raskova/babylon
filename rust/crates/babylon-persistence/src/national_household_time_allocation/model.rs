use super::CountyGeoid;
use crate::{
    national_counties::ObservationStatus, national_household_allocation::HouseholdBudgetKey,
};

/// Age controls joined to an existing counted household budget identity.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HouseholdTimeAllocation {
    pub key: HouseholdBudgetKey,
    pub eligible_16_plus: u64,
    pub armed_forces: u64,
    pub inactive: u64,
    pub under_16: u64,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountyHouseholdTimeAllocation {
    pub(super) county: CountyGeoid,
    pub(super) budgets: Vec<HouseholdTimeAllocation>,
}
impl CountyHouseholdTimeAllocation {
    #[must_use]
    pub const fn county(&self) -> CountyGeoid {
        self.county
    }
    #[must_use]
    pub fn budgets(&self) -> &[HouseholdTimeAllocation] {
        &self.budgets
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalHouseholdTimeAllocation {
    pub(super) county_source_sha256: [u8; 32],
    pub(super) household_source_sha256: [u8; 32],
    pub(super) resident_workforce_source_sha256: [u8; 32],
    pub(super) counties: Vec<CountyHouseholdTimeAllocation>,
}
impl NationalHouseholdTimeAllocation {
    #[must_use]
    pub fn counties(&self) -> &[CountyHouseholdTimeAllocation] {
        &self.counties
    }
    #[must_use]
    pub const fn county_source_sha256(&self) -> [u8; 32] {
        self.county_source_sha256
    }
    #[must_use]
    pub const fn household_source_sha256(&self) -> [u8; 32] {
        self.household_source_sha256
    }
    #[must_use]
    pub const fn resident_workforce_source_sha256(&self) -> [u8; 32] {
        self.resident_workforce_source_sha256
    }
    /// # Errors
    /// Refuses a county outside the exact captured source roster.
    pub fn county(
        &self,
        county: CountyGeoid,
    ) -> Result<&CountyHouseholdTimeAllocation, HouseholdTimeAllocationError> {
        self.counties
            .binary_search_by_key(&county, CountyHouseholdTimeAllocation::county)
            .map(|index| &self.counties[index])
            .map_err(|_| HouseholdTimeAllocationError::CountyRoster)
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum HouseholdTimeMeasure {
    Population,
    Households,
    Eligible16Plus,
    Employed,
    Reserve,
    ArmedForces,
    Inactive,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum HouseholdTimeAllocationError {
    CountyRoster,
    HouseholdReference(crate::national_households::HouseholdReferenceError),
    WorkforceReference(crate::national_resident_workforce::ResidentWorkforceReferenceError),
    SourceDigest,
    UnavailableObservation {
        county: CountyGeoid,
        measure: HouseholdTimeMeasure,
        status: ObservationStatus,
        raw: String,
    },
    CountyMargin {
        county: CountyGeoid,
    },
    BudgetMargin {
        county: CountyGeoid,
    },
    BudgetIdentity {
        county: CountyGeoid,
    },
    Arithmetic {
        county: CountyGeoid,
    },
}
impl std::fmt::Display for HouseholdTimeAllocationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "household time allocation refused: {self:?}")
    }
}
impl std::error::Error for HouseholdTimeAllocationError {}
#[derive(Clone, Copy)]
pub(super) struct CountyTimeControls {
    pub population: u64,
    pub households: u64,
    pub eligible_16_plus: u64,
    pub employed: u64,
    pub reserve: u64,
    pub armed_forces: u64,
    pub inactive: u64,
}
