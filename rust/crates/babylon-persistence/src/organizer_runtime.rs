//! Durable organizer admission and actor-safe snapshots on the existing runtime.

mod collection_preview;

mod material_preview;

pub use collection_preview::OrganizerCollectionPreview;

pub use material_preview::*;

#[path = "organizer_runtime/snapshot.rs"]
mod snapshot;

pub use snapshot::OrganizerSnapshot;
pub(crate) use snapshot::{
    aid_snapshot_matches, capture_pending, captured_organizer_snapshot, pending,
    CapturedOrganizerCommand,
};

use crate::runtime_session::RuntimeSessionErrorCode;
