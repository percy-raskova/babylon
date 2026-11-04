//! Durable organizer admission and actor-safe snapshots on the existing runtime.

mod collection_preview;
pub(crate) mod encounter;
pub use encounter::{CityPdEncounter, CITY_PD_ENCOUNTER_SCHEMA_VERSION};

mod material_preview;

pub use collection_preview::OrganizerCollectionPreview;

pub use material_preview::*;

#[path = "organizer_runtime/snapshot.rs"]
mod snapshot;

pub(crate) use snapshot::{
    aid_snapshot_matches, capture_pending, captured_organizer_snapshot, opening_body_attribution,
    pending, CapturedOrganizerCommand, OrganizerBodyAttribution,
};
pub use snapshot::{
    OrganizerBodyDisclosure, OrganizerBodyPart, OrganizerBodyScope, OrganizerBodySource,
    OrganizerSnapshot,
};

use crate::runtime_session::RuntimeSessionErrorCode;
