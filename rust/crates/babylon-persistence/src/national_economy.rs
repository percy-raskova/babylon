//! Designed opening content for the shared national and world economic circuit.
//! Source observations establish coverage and allocation, not physical recipes.

mod identity;
mod opening;
pub(crate) mod organizer;
mod policy;

pub use opening::aid::{AidChildCapture, NationalAidCapture};
pub use opening::{
    build_national_opening, NationalOpening, NationalOpeningError, NationalOpeningPolicy,
};

pub use identity::{
    household_enterprise_target, household_principal, resident_employer_target,
    source_workplace_target, ResidentWorkplaceSource, ResidentWorkplaceTarget,
    NATIONAL_SCENARIO_ID,
};
pub use policy::{
    GameAidPolicy, GameCommodity, GameDependencyProfile, GameEquipmentPolicy, GameFinancialPolicy,
    GameHouseholdPolicy, GameHouseholdTimePolicy, GameJourneyTiming, GameMarketPolicy, GameNeed,
    GamePrice, GameProfile, GameRecipe, GameServiceReach, NationalGamePolicy,
    NationalGamePolicyError, ResidentOpeningCounts,
};
