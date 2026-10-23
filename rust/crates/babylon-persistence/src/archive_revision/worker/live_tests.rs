//! Live Archive worker proofs against the task-owned disposable `PostgreSQL` runtime.
//!
//! Each test clones the validated current runtime template, commits real
//! ticks through `DurableMaterialRuntime`, and then proves one worker
//! acceptance property against the committed dirty receipts.

#[path = "../../../tests/support/current_material.rs"]
mod current_material;

#[path = "live_tests/checkpoint_membership.rs"]
mod checkpoint_membership;

#[path = "live_tests/short_publication.rs"]
mod short_publication;

#[path = "live_tests/provenance.rs"]
mod provenance;

#[path = "live_tests/packed_membership.rs"]
mod packed_membership;

#[path = "live_tests/bounds.rs"]
mod bounds;

#[path = "../../../tests/support/archive_reader.rs"]
mod archive_reader;

#[path = "live_tests/organizer_capture.rs"]
mod organizer_capture;

#[path = "live_tests/revisions.rs"]
mod revisions;

#[path = "live_tests/wakeup.rs"]
mod wakeup;

#[path = "live_tests/support.rs"]
mod support;

#[allow(unused_imports)]
use support::{
    archive_page_count, assert_foundation_grant_census, commit_ticks, dirty_receipt_count,
    grant_stub_knowledge, insert_orphan_dirty_receipt,
    live_foundation_grants_seed_at_campaign_foundation_and_reconcile_exactly,
    live_search_bounds_results_to_the_requested_limit, live_search_refuses_tampered_page_content,
    live_worker_consumes_empty_batches_once_without_publishing_content,
    live_worker_consumes_pending_receipts_in_tick_order,
    live_worker_crash_between_receipts_resumes_exactly,
    live_worker_refuses_batch_identity_mismatch_without_consuming,
    live_worker_rerun_reconciles_without_duplicate_publication,
    live_worker_skips_orphan_dirty_receipt_without_marker, receipt_consumption_count,
    stub_page_input, stub_place_page_ref, stub_subject_spec, validated_base_config,
    validated_template_name, ChangedExceptProducer, FailAtTickProducer, LiveWorkerTarget,
    QuietExceptProducer, StubPageProducer, StubSubjectSpec, TestDatabase, UndrainedProducer,
    WrongTickProducer, ACK, ACK_ENV, CANARY_ENV, DSN_ENV, TEMPLATE_DB_ENV,
};

#[allow(unused_imports)]
use crate::archive_revision::ArchiveReadScope;
#[allow(unused_imports)]
use crate::archive_revision::{ArchiveDossierBounds, ArchiveDossierState};
#[allow(unused_imports)]
use crate::material_runtime::DurableMaterialRuntime;
#[allow(unused_imports)]
use crate::{
    identity::CampaignId, postgres_catalog::validate_connection_target, seed_foundation_grants,
    ArchiveCitation, ArchiveDirtyBatch, ArchiveDossierProducer, ArchiveKnowledgeGrant,
    ArchivePageInput, ArchivePageRef, ArchiveProducerOutcome, ArchiveReceiptDisposition,
    ArchiveSignal, ArchiveSubject, ArchiveSubjectKind, ArchiveWorker, FoundationGrantsError,
    NullArchiveDossierProducer, PendingArchiveReceipt, SemanticArchiveError, SemanticArchiveStore,
};
#[allow(unused_imports)]
use crate::{install_reader_role, SemanticArchiveReader};
#[allow(unused_imports)]
use crate::{material_runtime, michigan_content, michigan_material};
#[allow(unused_imports)]
use archive_reader::{scope_at, with_reader};
#[allow(unused_imports)]
use babylon_bsl::structural_verbs::CollectingSink;
#[allow(unused_imports)]
use babylon_practice_contract::OrderedPracticeActionBatch;
#[allow(unused_imports)]
use postgres::{Config, NoTls};
#[allow(unused_imports)]
use std::str::FromStr;
#[allow(unused_imports)]
use uuid::Uuid;
