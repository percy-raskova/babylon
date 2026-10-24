//! Explicit native quantities and Designed opening policies; no equilibrium solver.

mod admission;

#[path = "policy/game.rs"]
mod game;

pub use game::{
    GameAidPolicy, GameCommodity, GameDependencyProfile, GameEquipmentPolicy, GameFinancialPolicy,
    GameHouseholdPolicy, GameHouseholdTimePolicy, GameJourneyTiming, GameMarketPolicy, GameNeed,
    GameOrganizerPolicy, GamePrice, GameProfile, GameRecipe, GameServiceReach, NationalGamePolicy,
    NationalGamePolicyError, ResidentOpeningCounts,
};
