//! Worker accounts from authenticated adjacent graph states and native event rows.
//! This projection checks receipt/end-point agreement; it never runs hiring policy.

mod members;

#[cfg(test)]
mod tests;

#[cfg(test)]
mod paid_tests;

#[path = "staffing/projection.rs"]
mod projection;

#[allow(unused_imports)]
pub(crate) use projection::project_staffing_accounts;
#[allow(unused_imports)]
use projection::{
    completed_account, current_labor, event_fields, event_receipts, integer,
    reconcile_member_changes, Result, Stocks, EVENT, INTEGER_FIELDS,
};

#[allow(unused_imports)]
use super::ProductionProjectionError;
#[allow(unused_imports)]
use crate::{
    michigan_economy::digest_hex, production_observation::CompletedProductionStaffing,
    production_observation::ProductionStaffingAccount,
    production_observation::ProductionStaffingSubject, stored_tick::StoredEvent,
};
#[allow(unused_imports)]
use babylon_bsl::identity_codec::StableBslValue;
#[allow(unused_imports)]
use babylon_graph::{stable_element::StableElementKey, stable_state::StableGraphState};
#[allow(unused_imports)]
use babylon_tick::{
    material_staffing::{StaffingComposition, STAFFING_COMPOSITION_ID},
    material_world::{MaterialTickReceipts, MaterialWorldRegister},
};
#[allow(unused_imports)]
use members::{StaffingGraph, StaffingWitnesses};
#[allow(unused_imports)]
use std::collections::BTreeMap;
