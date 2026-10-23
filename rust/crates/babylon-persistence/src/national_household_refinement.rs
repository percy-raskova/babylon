//! Designed sparse child margins subtract from source-controlled parent budgets.
#[cfg(test)]
mod tests;

#[path = "national_household_refinement/refine.rs"]
mod refine;

#[cfg(test)]
use refine::refine_parent;
pub use refine::{
    refine_households, HouseholdLeaf, HouseholdLeafMargins, HouseholdRefinementError,
    HouseholdRefinementSpec, NationalHouseholdLeafRoster,
};

#[cfg(test)]
use crate::national_economy::household_principal;
#[cfg(test)]
use crate::national_household_allocation::HouseholdBudgetKey;
#[cfg(test)]
use babylon_kernel::economic_location::EconomicLocation;
#[cfg(test)]
use babylon_kernel::geography::CountyGeoid;
