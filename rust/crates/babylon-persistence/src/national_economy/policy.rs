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

#[allow(unused_imports)]
use babylon_kernel::{
    currency::Currency, economic_identity::EconomicFunction, economic_location::ForeignCounterpart,
};
#[allow(unused_imports)]
use babylon_material_circuit::{CommodityKind, GoodId, HouseholdNeedBasis, UnitId};
#[allow(unused_imports)]
use std::collections::BTreeMap;
