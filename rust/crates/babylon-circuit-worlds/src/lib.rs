//! Small worlds for the exact material circuit.
//!
//! This crate builds worlds out of the engine's public API only: a catalog, an opening state and a
//! staffing, with typed names for their places, workplaces, households and goods. The engine is not
//! changed by anything here.

pub mod doubled;
pub mod error;
pub mod ids;
pub mod runner;
pub mod shocks;

pub use doubled::{Economy, OpeningPush, Pushed, Scale, World};
pub use error::WorldError;
pub use ids::{
    corridor, fund, goods_unit, hours_unit, location, route, treasury, Good, Household, Kind,
    Place, Workplace,
};
pub use runner::{
    rule_name, Closing, PeriodReceipts, PeriodResult, PeriodSummary, RuleError, RuleOn, Runner,
    RunnerError, Stage, Switch,
};
pub use shocks::{Lasts, Places, Shock, ShockBook, ShockError, Strike};
