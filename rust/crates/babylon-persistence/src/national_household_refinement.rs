//! Designed sparse child margins subtract from source-controlled parent budgets.
#[cfg(test)]
mod tests;

#[path = "national_household_refinement/refine.rs"]
mod refine;

pub use refine::{
    consolidate_background, refine_households, AuthoredCommitment, BackgroundHouseholdCohort,
    BackgroundWorkplaceCohort, CohortConservation, ConsolidationError, DetailConservation,
    ForegroundIdentities, ForegroundSelection, HouseholdCohortCounts, HouseholdLeaf,
    HouseholdLeafMargins, HouseholdRefinementError, HouseholdRefinementSpec,
    NationalDetailPartition, NationalHouseholdLeafRoster,
};
