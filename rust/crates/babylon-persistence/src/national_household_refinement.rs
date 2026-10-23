//! Designed sparse child margins subtract from source-controlled parent budgets.
#[cfg(test)]
mod tests;

#[path = "national_household_refinement/refine.rs"]
mod refine;

#[allow(unused_imports)]
use refine::refine_parent;
pub use refine::{
    refine_households, HouseholdLeaf, HouseholdLeafMargins, HouseholdRefinementError,
    HouseholdRefinementSpec, NationalHouseholdLeafRoster,
};

#[allow(unused_imports)]
use crate::{
    national_economy::household_principal,
    national_household_allocation::{HouseholdBudgetKey, NationalHouseholdAllocation},
    national_household_time_allocation::NationalHouseholdTimeAllocation,
};
#[allow(unused_imports)]
use babylon_kernel::{
    content_digest::sha256_of, economic_location::EconomicLocation, geography::CountyGeoid,
};
#[allow(unused_imports)]
use babylon_material_circuit::{FinalDemandPrincipalId, MAX_MATERIAL_CIRCUIT_ROWS};
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
