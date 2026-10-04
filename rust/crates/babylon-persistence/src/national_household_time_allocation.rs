//! Derived age-sixteen eligibility with Designed assignment across counted budgets.
//! These immutable joins create neither people nor workforce members. Age sixteen
//! eligibility describes the source control, not adulthood, consent or retirement.
mod allocation;
mod model;
mod source;

use allocation::allocate_county;
use babylon_kernel::geography::CountyGeoid;
use model::CountyTimeControls;
pub use model::{
    CountyHouseholdTimeAllocation, HouseholdTimeAllocation, HouseholdTimeAllocationError,
    HouseholdTimeMeasure, NationalHouseholdTimeAllocation,
};
pub use source::allocate_household_time;
#[cfg(test)]
use source::{observation, validate_roster};
#[cfg(test)]
mod tests;
