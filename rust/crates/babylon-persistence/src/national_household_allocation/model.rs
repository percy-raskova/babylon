use babylon_kernel::geography::CountyGeoid;

/// Historical earnings and Designed ownership exposure are independent axes.
/// Labels describe opening authoring; subsequent hiring never changes identity.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum HouseholdBudgetKey {
    EarningNonowner = 1,
    EarningOwner = 2,
    NoEarnerNonowner = 3,
    NoEarnerOwner = 4,
    CollectiveResidence = 5,
    /// Explicit first-version abstraction for foreign and dependency residents.
    PooledExternal = 6,
}
impl HouseholdBudgetKey {
    #[must_use]
    pub const fn owner_exposure(self) -> bool {
        matches!(self, Self::EarningOwner | Self::NoEarnerOwner)
    }
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::EarningNonowner => "earning-nonowner",
            Self::EarningOwner => "earning-owner",
            Self::NoEarnerNonowner => "no-earner-nonowner",
            Self::NoEarnerOwner => "no-earner-owner",
            Self::CollectiveResidence => "collective-residence",
            Self::PooledExternal => "pooled-external",
        }
    }
}

/// One counted budget cohort, never one object per household or person.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HouseholdBudgetAllocation {
    pub key: HouseholdBudgetKey,
    pub persons: u64,
    pub households: u64,
    pub employed: u64,
    pub reserve: u64,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountyHouseholdAllocation {
    pub(super) county: CountyGeoid,
    pub(super) budgets: Vec<HouseholdBudgetAllocation>,
}
impl CountyHouseholdAllocation {
    #[must_use]
    pub const fn county(&self) -> CountyGeoid {
        self.county
    }
    #[must_use]
    pub fn budgets(&self) -> &[HouseholdBudgetAllocation] {
        &self.budgets
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalHouseholdAllocation {
    pub(crate) private_owner_households_bps: u16,
    pub(crate) county_source_sha256: [u8; 32],
    pub(crate) classes_source_sha256: [u8; 32],
    pub(super) household_source_sha256: [u8; 32],
    pub(super) counties: Vec<CountyHouseholdAllocation>,
}
impl NationalHouseholdAllocation {
    #[must_use]
    pub fn counties(&self) -> &[CountyHouseholdAllocation] {
        &self.counties
    }
    #[must_use]
    pub const fn household_source_sha256(&self) -> [u8; 32] {
        self.household_source_sha256
    }
    /// # Errors
    /// Refuses a county outside the exact source-controlled roster.
    pub fn county(
        &self,
        county: CountyGeoid,
    ) -> Result<&CountyHouseholdAllocation, HouseholdAllocationError> {
        self.counties
            .binary_search_by_key(&county, CountyHouseholdAllocation::county)
            .map(|index| &self.counties[index])
            .map_err(|_| HouseholdAllocationError::SourceScope)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum HouseholdAllocationError {
    SourceScope,
    MissingObservation,
    PopulationControl,
    DesignedAllocationInfeasible,
    Policy,
    Arithmetic,
}
impl std::fmt::Display for HouseholdAllocationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "household allocation refused: {self:?}")
    }
}
impl std::error::Error for HouseholdAllocationError {}

#[derive(Clone, Copy)]
pub(super) struct HouseholdCountyControls {
    pub population: u64,
    pub household_persons: u64,
    pub with_historical_earnings_households: u64,
    pub without_historical_earnings_households: u64,
    pub employed: u64,
    pub reserve: u64,
    pub working_owners: u64,
}
