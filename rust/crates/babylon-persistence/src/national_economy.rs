//! Designed opening content for the shared national and world economic circuit.
//! Source observations establish coverage and allocation, not physical recipes.

mod identity;
mod policy;

pub use identity::{
    household_enterprise_target, household_principal, resident_employer_target,
    source_workplace_target, ResidentWorkplaceSource, ResidentWorkplaceTarget,
};
pub use policy::{
    GameCommodity, GameDependencyProfile, GameEquipmentPolicy, GameFinancialPolicy, GameNeed,
    GamePrice, GameProfile, GameRecipe, NationalGamePolicy, NationalGamePolicyError,
    ResidentOpeningCounts,
};
