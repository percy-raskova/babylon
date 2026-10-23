//! Opt-in qualification of the actual captured statewide sources on owned `PostgreSQL`.
//! The ordinary reader focus excludes this full four-preset, sixteen-period run.

#[path = "statewide_qualified/maintenance.rs"]
mod maintenance;

#[path = "statewide_qualified/support.rs"]
mod support;

use support::{
    advance_pair, assert_history_and_preview, assert_same_foundation_bytes, observe,
    reopen_runtime, witnessed_output, Measurements, Session, SourceCopies,
};

use super::{
    identity_hex, install_reader_role, provision_observer_role, CampaignId, CollectingSink,
    DisposableTarget, DurableMaterialRuntime, MichiganContentPreset, MichiganDeliveryPreset, NoTls,
    ObserverEconomyReader, ObserverVisibility, OrderedPracticeActionBatch, Uuid,
};
use babylon_persistence::michigan_material::{MichiganMaterialCatalog, MAX_MICHIGAN_SOURCE_BYTES};
use babylon_persistence::production_observation::ProductionSnapshot;
use babylon_tick::material_world::{
    MAX_MATERIAL_TICK_RECEIPT_BYTES, MAX_MATERIAL_WORLD_REGISTER_BYTES,
};
use babylon_tick::replay_session::ReplayCommitDisposition;
