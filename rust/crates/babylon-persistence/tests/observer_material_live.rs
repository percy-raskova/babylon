//! Full material reads, historical identity, and SQL-denied preview on a disposable clone.

// Every deliberate metadata fault in these tests is confined to DisposableTarget's
// freshly created clone. Neither the template nor an existing user campaign is altered.

#[path = "observer_material_live/runtime_process.rs"]
mod runtime_process;

#[path = "observer_material_live/tick_components.rs"]
mod tick_components;

#[path = "observer_material_live/staffing_history.rs"]
mod staffing_history;

#[path = "observer_material_live/endpoint_reuse.rs"]
mod endpoint_reuse;

#[path = "observer_material_live/history_cursor.rs"]
mod history_cursor;

#[path = "observer_material_live/persisted_twins.rs"]
mod persisted_twins;

#[path = "observer_material_live/statewide.rs"]
mod statewide;

#[path = "observer_material_live/statewide_qualified.rs"]
mod statewide_qualified;

#[path = "support/material_config.rs"]
mod test_support;

#[path = "observer_material_live/organizer.rs"]
mod organizer;

#[path = "observer_material_live/support.rs"]
mod support;

use support::{
    advance_material_period, assert_known_material_absence, assert_material_accounts, identity_hex,
    DisposableTarget, NEXT_DISPOSABLE_TARGET,
};

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_persistence::archive_revision::{ArchiveDossierBounds, ArchiveDossierState};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::material_runtime::DurableMaterialRuntime;
use babylon_persistence::michigan_content::MichiganContentPreset;
use babylon_persistence::michigan_material::MichiganDeliveryPreset;
use babylon_persistence::observer_reader::{
    provision_observer_role, ObserverEconomyError, ObserverEconomyReader, ObserverVisibility,
};
use babylon_persistence::postgres_catalog::validate_connection_target;
use babylon_persistence::{
    install_reader_role, ArchiveEvidenceClass, ArchivePageRef, ArchiveSubjectKind, ArchiveWorker,
    CompositeArchiveDossierProducer, CountyDossierProducer, PlaceDossierProducer,
    SemanticArchiveReader,
};
use babylon_practice_contract::OrderedPracticeActionBatch;
use postgres::{Config, NoTls};
use uuid::Uuid;
