//! Worker accounts from authenticated adjacent graph states and native event rows.
//! This projection checks receipt/end-point agreement; it never runs hiring policy.

mod members;

#[cfg(test)]
mod tests;

#[cfg(test)]
mod paid_tests;

#[path = "staffing/projection.rs"]
mod projection;

pub(crate) use projection::project_staffing_accounts;
use projection::{integer, Result, Stocks};

use super::ProductionProjectionError;
