//! Designed opening content for the shared national and world economic circuit.
//! Source observations establish coverage and allocation, not physical recipes.

pub(crate) mod city_pd;
pub mod companies;
pub(crate) mod county_review;
pub mod grain;
mod identity;
mod opening;
pub(crate) mod organizer;
mod policy;

pub use opening::aid::{AidChildCapture, NationalAidCapture};
pub use opening::claimant::NationalSupportClaimant;
pub use opening::{
    build_national_opening, NationalOpening, NationalOpeningError, NationalOpeningPolicy,
};

pub use identity::{
    commodity_good_id, household_enterprise_target, household_principal, resident_employer_target,
    source_workplace_target, ResidentWorkplaceSource, ResidentWorkplaceTarget,
    NATIONAL_SCENARIO_ID,
};
pub use policy::{
    GameAidPolicy, GameCityPdPolicy, GameCommodity, GameCountyReviewPolicy, GameDependencyProfile,
    GameEquipmentPolicy, GameFinancialPolicy, GameHouseholdLifecyclePolicy, GameHouseholdPolicy,
    GameHouseholdSupportClaimant, GameHouseholdTimePolicy, GameJourneyTiming, GameMarketPolicy,
    GameNeed, GamePrice, GameProfile, GameRecipe, GameServiceReach, InitialAgeDistribution,
    NationalGamePolicy, NationalGamePolicyError, ResidentOpeningCounts, VenueLogReader,
};
