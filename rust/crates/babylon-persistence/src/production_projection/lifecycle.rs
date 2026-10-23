//! Period-local order witnesses, including admissions absent from both snapshots.
//! These joins authenticate receipts; they do not allocate, plan, or replay work.
mod investment;

mod services;

#[path = "lifecycle/period.rs"]
mod period;

pub(super) use period::{join, recurring};
use period::{monetary, offer_index, Result};
pub(crate) use period::{validate_period, PeriodOrders};

use super::ProductionProjectionError;
