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

#[allow(unused_imports)]
use support::{
    advance_material_period, assert_all_county_cards, assert_archive_progress,
    assert_authenticated_time_debits, assert_captured_foundation_denied,
    assert_combined_observation, assert_committed_accounting_observation,
    assert_corrupted_register_is_rejected, assert_foundation_byte_changes_refused,
    assert_foundation_clock_changes_refused, assert_foundation_identity_changes_refused,
    assert_known_material_absence, assert_material_accounts, assert_preview_blob_denied,
    assert_public_qcew_card, assert_restart_drains_and_verifies_quiet_periods,
    assert_retained_content, assert_revision_resume, assert_revision_statistics_absent,
    assert_scoped_page, assert_session_admits_stored_revision, assert_single_foundation_storage,
    assert_streamed_native_advance,
    cold_restart_and_history_refuse_corrupt_or_missing_earlier_period_lookup,
    current_archive_scope, identity_hex, insert_unadmitted_catalog_rows,
    live_material_observer_preserves_history_and_denies_preview_blob_authority,
    live_material_observer_reuse_authenticates_actual_foundation_bytes,
    live_michigan_all_county_cards_keep_public_source_and_quiet_restart_freshness,
    live_regional_content_revisions_resume_exactly_and_catalog_filters_before_its_limit,
    opening_roles, read_county, self_consistent_changed_period_lookup, DisposableTarget, ACK,
    NEXT_DISPOSABLE_TARGET, OBSERVER_GROUP_ROLES, PARAMETER_ACL_WRITE,
};

#[allow(unused_imports)]
use babylon_bsl::structural_verbs::CollectingSink;
#[allow(unused_imports)]
use babylon_persistence::archive_revision::{
    ArchiveDossierBounds, ArchiveDossierPage, ArchiveDossierPending, ArchiveDossierRead,
    ArchiveDossierState, ArchiveDossierUnavailable, ArchiveReadScope, ArchiveSearchState,
};
#[allow(unused_imports)]
use babylon_persistence::{
    captured_archive_producer,
    identity::CampaignId,
    install_reader_role,
    material_runtime::DurableMaterialRuntime,
    michigan_content::MichiganContentPreset,
    michigan_economy::{
        michigan_economy, MichiganCountyEconomy, QCEW_ECONOMICS_ARTIFACT_SHA256,
        QCEW_ECONOMICS_FIELD_KEYS, QCEW_ECONOMICS_SOURCE_ID,
    },
    michigan_material::MichiganDeliveryPreset,
    observer_reader::provision_observer_role,
    observer_reader::{ObserverEconomyError, ObserverEconomyReader, ObserverVisibility},
    postgres_catalog::validate_connection_target,
    ArchiveAtomSubjectKind, ArchiveAtomValue, ArchiveEvidenceClass, ArchivePageRef,
    ArchiveReceiptDisposition, ArchiveSubjectKind, ArchiveWorker, CompositeArchiveDossierProducer,
    CountyDossierProducer, PlaceDossierProducer, SemanticArchiveReader, SemanticArchiveStore,
};
#[allow(unused_imports)]
use babylon_practice_contract::OrderedPracticeActionBatch;
#[allow(unused_imports)]
use babylon_tick::material_world::MaterialWorldRegister;
#[allow(unused_imports)]
use postgres::{Config, NoTls};
#[allow(unused_imports)]
use std::sync::atomic::{AtomicU64, Ordering};
#[allow(unused_imports)]
use std::sync::{Mutex, Once};
#[allow(unused_imports)]
use uuid::Uuid;
