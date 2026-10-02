//! Source-constrained household budgets with an explicitly Designed joint allocation.
//! This authoring result is not another mutable population or workforce authority.
mod allocation;
mod model;
mod source;

use allocation::allocate_county;
use model::HouseholdCountyControls;
pub use model::{
    CountyHouseholdAllocation, HouseholdAllocationError, HouseholdBudgetAllocation,
    HouseholdBudgetKey, NationalHouseholdAllocation,
};
pub use source::allocate_households;

#[cfg(test)]
mod tests;
