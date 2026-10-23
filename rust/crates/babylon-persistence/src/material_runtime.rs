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
#[allow(unused_imports)]
pub(crate) use runtime::CommitFault;
#[allow(unused_imports)]
use runtime::{
    admit_archive_foundation, admit_archive_lookup, admit_lookup_chain, admitted_marker_matches,
    authenticated_organizer_actions, capture_marker, capture_material_lookup, commit_error,
    commit_material_envelope, commit_material_transaction, hydrate_material_foundation,
    marker_matches, observer_organizer_actions, read_authenticated_material_tick,
    read_material_lookup, read_stored_material_tick, read_stored_material_tick_rows,
    read_tail_tick, reconstruct_material_foundation, record_advance_timing,
    validate_component_identity, validate_foundation_spec, CapturedGraphFoundation,
    CapturedMaterialTick, MaterialEnvelopeRead, MaterialReadAuthority, StoredMaterialEnvelope,
    StoredMaterialFoundation, FOUNDATION_DOMAIN, WRITER_CONNECT_TIMEOUT, WRITER_STARTUP_OPTIONS,
    WRITER_TCP_USER_TIMEOUT,
};
#[allow(unused_imports)]
pub(crate) use runtime::{
    bounded_material_writer_config, capture_archive_organizer_register,
    capture_material_foundation_components, duration_columns, load_material_foundation_components,
    read_duration, read_observer_material_tick, ArchiveFoundationCandidate,
    CapturedArchiveOrganizerRegister, CapturedMaterialFoundation, FoundationReadSource,
    RegisterWitnesses, StoredMaterialTick,
};
pub use runtime::{
    DurableMaterialRuntime, MaterialAdvanceStage, MaterialFoundationSpec, MaterialRuntimeError,
    MaterialRuntimeFoundation,
};

#[allow(unused_imports)]
use crate::stored_tick::{StoredEvent, StoredTickReadSource, StoredTickRelation};
#[allow(unused_imports)]
use crate::CommittedTickReceipt;
#[allow(unused_imports)]
use crate::{
    checkpoint::{CommittedFullCheckpoint, CommittedResolveTick},
    committed_tick_envelope::CommittedTickRowFamilies,
    foundation::{CampaignFoundation, FoundationContentBundle},
    identity::CampaignId,
    material_envelope::{CommittedMaterialTickAttestation, CommittedMaterialTickEnvelope},
    runtime::{
        insert_campaign_foundation_rows, insert_typed_tick_pre_marker_rows, prepare_committed_tick,
        reconstruct_graph_foundation_session, verify_runtime_schema_client,
        RustPersistenceRuntimeError,
    },
    semantic_batches::{
        compose_graph_rows_with_encoder, compose_material_state_rows, StableGraphRowRef,
    },
    stored_tick,
};
#[allow(unused_imports)]
use crate::{material_storage, state_storage::TypedLookup};
#[allow(unused_imports)]
use babylon_bsl::structural_verbs::CollectingSink;
#[allow(unused_imports)]
use babylon_graph::hypergraph_store::HypergraphStore;
#[allow(unused_imports)]
use babylon_graph::stable_state::StableGraphState;
#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use babylon_material_circuit::MaterialCircuitState;
#[allow(unused_imports)]
use babylon_practice_contract::OrderedPracticeActionBatch;
#[allow(unused_imports)]
use babylon_tick::choice_receipt::ChoiceReceipt;
#[allow(unused_imports)]
use babylon_tick::{
    material_replay::{
        IdentifiedMaterialTick, MaterialCommitError, MaterialReplayError, MaterialReplaySession,
    },
    material_world::{MaterialWorldError, MaterialWorldRegister},
    replay_session::{ReplayCommitDisposition, ReplayTickSession},
};
#[allow(unused_imports)]
use observer_endpoints::AuthenticatedPreviousMaterialTick;
#[allow(unused_imports)]
use postgres::{fallible_iterator::FallibleIterator as _, Config, GenericClient, NoTls};
#[allow(unused_imports)]
use std::time::{Duration, Instant};

#[cfg(test)]
#[allow(unused_imports)]
pub(crate) use runtime::COMMIT_FAULT;

#[cfg(test)]
#[allow(unused_imports)]
use runtime::{
    foundation_session_shares_the_exact_opening_canonical_allocation, inject_marker_trigger_failure,
};
