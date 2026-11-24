//! The runner: the doubled world stepped by the engine's own period.

pub mod error;
pub mod hours;
pub mod result;
pub mod rules;
pub mod run;

pub use error::{HoursRun, RunnerError, Stage};
pub use hours::{
    HouseholdHours, LedgerTotals, MoveHours, MovedBy, PeriodHours, PlaceHours, WorkplaceHours,
};
pub use result::{Closing, PeriodReceipts, PeriodResult, PeriodSummary};
pub use rules::{rule_name, RuleError, RuleOn, Switch};
pub use run::Runner;
