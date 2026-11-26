//! Explicit native quantities and Designed opening policies; no equilibrium solver.

mod admission;
mod builder_keys;

#[path = "policy/game.rs"]
mod game;

pub use game::{
    GameAidPolicy, GameCityPdPolicy, GameCommodity, GameCountyReviewPolicy, GameDependencyProfile,
    GameEquipmentPolicy, GameFinancialPolicy, GameFundPolicy, GameHandling,
    GameHouseholdLifecyclePolicy, GameHouseholdPolicy, GameHouseholdSupportClaimant,
    GameHouseholdTimePolicy, GameJourneyTiming, GameLuxuryScale, GameMachines, GameMapBasis,
    GameMarketPolicy, GameNeed, GameOrganizerPolicy, GamePlaceGrant, GamePrice, GameProcurement,
    GameProfile, GameProfileWage, GameProgram, GameProgramRecipients, GameProgramTerms, GameRecipe,
    GameServiceReach, GameWages, GameWant, InitialAgeDistribution, NationalGamePolicy,
    NationalGamePolicyError, ResidentOpeningCounts, VenueLogReader, MAX_GAME_PROGRAM_SHARE_BPS,
    MAX_POLICY_BYTES, MAX_POLICY_BYTES_SCHEMA_8,
};
