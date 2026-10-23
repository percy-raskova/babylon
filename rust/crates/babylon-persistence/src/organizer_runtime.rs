//! Durable organizer admission and actor-safe snapshots on the existing runtime.

mod collection_preview;

mod material_preview;

pub use collection_preview::OrganizerCollectionPreview;

pub use material_preview::*;

#[path = "organizer_runtime/snapshot.rs"]
mod snapshot;

pub use snapshot::OrganizerSnapshot;
#[allow(unused_imports)]
pub(crate) use snapshot::{
    aid_snapshot_matches, capture_pending, captured_organizer_snapshot, decode_commitment, pending,
    CapturedOrganizerCommand,
};
#[allow(unused_imports)]
use snapshot::{classify, collection_history, stored_commitment};

#[allow(unused_imports)]
use crate::{
    identity::CampaignId,
    material_runtime::{DurableMaterialRuntime, MaterialRuntimeError},
    runtime_session::RuntimeSessionErrorCode,
};
#[allow(unused_imports)]
use babylon_practice_contract::{
    admit_organizer, organizer_action_batch, organizer_view, preview_organizer,
    validate_organizer_commitment, OrganizerCommand, OrganizerCommitment, OrganizerPreview,
    OrganizerView,
};
#[allow(unused_imports)]
use postgres::GenericClient;
#[allow(unused_imports)]
use serde::{Deserialize, Serialize};
