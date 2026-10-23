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
#[cfg(test)]
use projection::{completed_account, event_fields, INTEGER_FIELDS};
use projection::{integer, Result, Stocks};

use super::ProductionProjectionError;
#[cfg(test)]
use crate::michigan_economy::digest_hex;
#[cfg(test)]
use crate::production_observation::ProductionStaffingAccount;
#[cfg(test)]
use crate::stored_tick::StoredEvent;
#[cfg(test)]
use babylon_bsl::identity_codec::StableBslValue;
#[cfg(test)]
use babylon_graph::stable_element::StableElementKey;
#[cfg(test)]
use babylon_graph::stable_state::StableGraphState;
#[cfg(test)]
use babylon_tick::material_staffing::StaffingComposition;
#[cfg(test)]
use babylon_tick::material_world::{MaterialTickReceipts, MaterialWorldRegister};
#[cfg(test)]
use members::StaffingGraph;
