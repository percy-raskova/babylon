//! Explicit native quantities and Designed opening policies; no equilibrium solver.

mod admission;

#[path = "policy/game.rs"]
mod game;

pub use game::{
    GameAidPolicy, GameCommodity, GameDependencyProfile, GameEquipmentPolicy, GameFinancialPolicy,
    GameHouseholdLifecyclePolicy, GameHouseholdPolicy, GameHouseholdTimePolicy, GameJourneyTiming,
    GameMarketPolicy, GameNeed, GameOrganizerPolicy, GamePrice, GameProfile, GameRecipe,
    GameServiceReach, InitialAgeDistribution, NationalGamePolicy, NationalGamePolicyError,
    ResidentOpeningCounts, VenueLogReader,
};
