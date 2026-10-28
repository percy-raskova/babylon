//! Explicit V3 durable material campaign, marker-last and checkpoint-complete.

mod capture_identity;

mod component_identity;

mod open;

mod runtime_checkpoint;

pub(crate) use capture_identity::rows_digest as capture_rows_digest;

mod decode;

mod envelope;

mod observer_actions;

mod observer_endpoints;

pub(crate) use component_identity::MaterialComponentIdentity;

pub use envelope::MAX_MATERIAL_FOUNDATION_BYTES;

pub(crate) use observer_endpoints::{read_observer_material_endpoints, ObserverEndpointLookup};

#[cfg(test)]
mod reconstruction_tests;

#[cfg(test)]
pub(crate) use reconstruction_tests::persisted_graph_copy;

#[cfg(test)]
mod diagnostics_tests;

#[cfg(test)]
mod maintenance_tests;

#[path = "material_runtime/runtime.rs"]
mod runtime;

#[cfg(test)]
pub(crate) use runtime::CommitFault;
use runtime::{
    admit_archive_lookup, capture_marker, capture_material_lookup,
    read_authenticated_material_tick, read_tail_tick, reconstruct_material_foundation,
    CapturedMaterialTick, MaterialEnvelopeRead, MaterialReadAuthority, StoredMaterialFoundation,
    FOUNDATION_DOMAIN,
};
pub(crate) use runtime::{
    bounded_material_writer_config, capture_archive_organizer_register,
    capture_material_foundation_components, read_duration, read_observer_material_tick,
    AdmittedMaterial, ArchiveFoundationCandidate, CapturedArchiveOrganizerRegister,
    CapturedMaterialFoundation, FoundationReadSource, ObserverReadAuthority, RegisterWitnesses,
    StoredMaterialTick,
};
pub use runtime::{
    DurableMaterialRuntime, MaterialAdvanceStage, MaterialFoundationSpec, MaterialRuntimeError,
    MaterialRuntimeFoundation,
};

use crate::foundation::CampaignFoundation;
use crate::identity::CampaignId;
use crate::material_storage;
use crate::runtime::verify_runtime_schema_client;
use crate::stored_tick::StoredTickReadSource;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_replay::{
    IdentifiedMaterialTick, MaterialReplayError, MaterialReplaySession,
};
use babylon_tick::material_world::MaterialWorldRegister;
use postgres::{Config, GenericClient, NoTls};

#[cfg(test)]
pub(crate) use runtime::COMMIT_FAULT;
