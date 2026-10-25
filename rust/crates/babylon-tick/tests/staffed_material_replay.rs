//! Graph-owned people and physical hours cross one real replay publication boundary.
//! This is a Designed circuit fixture, not admission of current Michigan content.

#[allow(
    dead_code,
    reason = "reuse the checked foundation loader, as replay_session does"
)]
#[path = "../../babylon-persistence/src/michigan_dynamic_hex_foundation.rs"]
mod michigan_dynamic_hex_foundation;

#[path = "staffed_material_replay/recurring.rs"]
mod recurring;

#[path = "staffed_material_replay/financial.rs"]
mod financial;

#[path = "staffed_material_replay/support.rs"]
mod support;

pub(crate) use support::Materials;
use support::{
    commit, good, live, owned_checkpoint_rows, paid_material, prepare, process, resident_member,
    site, staffed_labor, subject, try_session_with_material, unit, Session, MATERIAL_CYCLE,
};

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_material_circuit::{
    CorridorCapacity, CorridorId, StaffingPolicy, StaffingPoolBinding, StaffingPoolId,
    StaffingWorkSource,
};
use babylon_tick::material_replay::MaterialCommitError;
use babylon_tick::material_staffing::{StaffingComposition, StaffingNodeBinding};
use babylon_tick::material_world::{decode_material_receipts, MaterialWorldRegister};
use babylon_tick::replay_session::ReplayCommitDisposition;
