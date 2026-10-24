//! Designed sparse child margins subtract from source-controlled parent budgets.
#[cfg(test)]
mod tests;

#[path = "national_household_refinement/refine.rs"]
mod refine;

pub use refine::{
    refine_households, HouseholdLeaf, HouseholdLeafMargins, HouseholdRefinementError,
    HouseholdRefinementSpec, NationalHouseholdLeafRoster,
};
