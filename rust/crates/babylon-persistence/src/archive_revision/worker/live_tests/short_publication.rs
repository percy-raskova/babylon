//! Prepared inputs must survive only as owned Rust values during production.
use super::archive_reader;
use super::support;
use super::support::{
    archive_page_count, receipt_consumption_count, LiveWorkerTarget, StubPageProducer,
};
use crate::archive_revision::body_encoding::DecodeObservation;
use crate::archive_revision::publication::PreparedPublication;
use crate::archive_revision::record::RevisionRecord;
use crate::archive_revision::ArchiveReadScope;
use crate::archive_revision::{ArchiveDossierBounds, ArchiveDossierState};
use crate::identity::CampaignId;
use crate::ArchiveKnowledge;
use crate::ArchiveMaterializeMode;
use crate::ArchiveMaterializeReport;
use crate::ArchivePageRef;
use crate::ArchiveWorkerCancellation;
use crate::{
    ArchiveDirtyBatch, ArchiveDossierProducer, ArchivePageInput, ArchiveProducerOutcome,
    ArchiveSubject, ArchiveSubjectKind, ArchiveWorker, PendingArchiveReceipt, SemanticArchiveError,
    SemanticArchiveStore,
};
use postgres::Client;
use postgres::IsolationLevel;
use postgres::{Config, NoTls};
use std::cell::Cell;
use std::sync::mpsc::{self, Sender};
use std::time::Duration;
use uuid::Uuid;
use zstd::bulk::Compressor;
use zstd::zstd_safe::CParameter;

struct DuringProduce<F>(F);
impl<F: Fn() -> Result<(), SemanticArchiveError>> ArchiveDossierProducer for DuringProduce<F> {
    fn produce(
        &self,
        campaign: Uuid,
        receipt: &PendingArchiveReceipt,
        knowledge: &ArchiveKnowledge,
        budget: usize,
    ) -> Result<ArchiveProducerOutcome, SemanticArchiveError> {
        (self.0)()?;
        StubPageProducer.produce(campaign, receipt, knowledge, budget)
    }
}

fn assert_no_publication(target: &LiveWorkerTarget) {
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 0);
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        0
    );
    let mut client = target
        .config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    for relation in [
        "archive_tick_knowledge_v3",
        "archive_knowledge_membership_v3",
    ] {
        let count: i64 = client
            .query_one(
                &format!("SELECT count(*) FROM babylon_meta.{relation} WHERE campaign_id=$1"),
                &[target.campaign_id.as_uuid()],
            )
            .expect("the seeded row is present exactly once")
            .get(0);
        assert_eq!(count, 0, "no prepared pin survives in {relation}");
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_slow_producer_has_no_outer_transaction_at_short_idle_timeout() {
    let target = LiveWorkerTarget::create("shortpublication", 0x34101, 1);
    let store = SemanticArchiveStore::new(&target.config);
    let mut client = store
        .connect("short publication proof")
        .expect("the test database accepts the connection");
    client
        .batch_execute("SET idle_in_transaction_session_timeout='100ms'")
        .expect("the test database applies the schema statements");
    let pid: i32 = client
        .query_one("SELECT pg_backend_pid()", &[])
        .expect("the seeded row is present exactly once")
        .get(0);
    let producer = DuringProduce(|| {
        let mut observer = target
            .config
            .connect(NoTls)
            .expect("the test database accepts the connection");
        let row = observer
            .query_one(
                "SELECT state,xact_start IS NULL FROM pg_stat_activity WHERE pid=$1",
                &[&pid],
            )
            .expect("the seeded row is present exactly once");
        assert_eq!(row.get::<_, String>(0), "idle");
        assert!(
            row.get::<_, bool>(1),
            "producer must own no outer SQL snapshot"
        );
        assert_no_publication(&target);
        std::thread::sleep(Duration::from_millis(250));
        Ok(())
    });
    let report = crate::archive_revision::publication::with_campaign_lock(
        &mut client,
        target.campaign_id,
        |client| {
            super::super::sweep_locked(
                client,
                target.campaign_id,
                &producer,
                &ArchiveWorkerCancellation::default(),
                1,
            )
        },
    )
    .expect("production outlasts the unchanged short transaction idle timeout");
    assert_eq!(report.verified_tick(), 1);
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 1);
    drop(client);
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_cancel_or_fail_after_prepare_creates_no_pin() {
    for (label, cancel) in [("preparecancel", true), ("preparefail", false)] {
        let target = LiveWorkerTarget::create(label, if cancel { 0x34102 } else { 0x34103 }, 1);
        let cancellation = ArchiveWorkerCancellation::default();
        let producer = DuringProduce(|| {
            assert_no_publication(&target);
            if cancel {
                cancellation.request_stop();
                Ok(())
            } else {
                Err(SemanticArchiveError::InvalidText)
            }
        });
        let result = ArchiveWorker::new(&target.config).sweep_cancellable(
            target.campaign_id,
            &producer,
            &cancellation,
        );
        assert_eq!(
            result.expect_err("the fixture call returns its expected result"),
            if cancel {
                SemanticArchiveError::WorkerCanceled
            } else {
                SemanticArchiveError::InvalidText
            }
        );
        assert_no_publication(&target);
        target.finish();
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_prepared_grant_or_receipt_drift_refuses_publication() {
    for (label, grant) in [("preparegrant", true), ("preparereceipt", false)] {
        let target = LiveWorkerTarget::create(label, if grant { 0x34104 } else { 0x34105 }, 1);
        let producer = DuringProduce(|| {
            assert_no_publication(&target);
            let mut writer = target
                .config
                .connect(NoTls)
                .expect("the test database accepts the connection");
            if grant {
                writer
                    .execute(
                        "UPDATE babylon_meta.archive_knowledge_grant_v1 \
                    SET provenance_ref=babylon_meta.archive_provenance_intern_v1(campaign_id, \
                    (SELECT source_id FROM babylon_meta.archive_provenance_v1 p WHERE p.campaign_id=archive_knowledge_grant_v1.campaign_id AND p.provenance_ref=archive_knowledge_grant_v1.provenance_ref),'changed-after-prepare') WHERE campaign_id=$1 \
                    AND subject_kind='county' AND subject_id='99963' AND grant_key='subject'",
                        &[target.campaign_id.as_uuid()],
                    )
                    .expect("the test database applies the setup statement");
            } else {
                writer
                    .execute(
                        "UPDATE babylon_state.archive_dirty_receipt_v1 \
                    SET tick_content_hash=$2 WHERE campaign_id=$1 AND resolve_tick=1",
                        &[target.campaign_id.as_uuid(), &&[0xab_u8; 32][..]],
                    )
                    .expect("the test database applies the setup statement");
            }
            Ok(())
        });
        let error = ArchiveWorker::new(&target.config)
            .sweep_once(target.campaign_id, &producer)
            .expect_err("the fixture call `sweep_once` fails for the authored inputs");
        assert_eq!(
            error,
            if grant {
                SemanticArchiveError::ReceiptConflict
            } else {
                SemanticArchiveError::ReceiptMismatch
            }
        );
        assert_no_publication(&target);
        target.finish();
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_page_insert_failure_rolls_back_prepared_pin_and_consumption() {
    let target = LiveWorkerTarget::create("prepareinsert", 0x34106, 1);
    target
        .config
        .connect(NoTls)
        .expect("the test database accepts the connection")
        .batch_execute(
            "ALTER TABLE babylon_meta.archive_page_revision_v2 \
         ADD CONSTRAINT refuse_proof_page CHECK (subject_id <> '99963')",
        )
        .expect("the test database applies the schema statements");
    ArchiveWorker::new(&target.config)
        .sweep_once(target.campaign_id, &StubPageProducer)
        .expect_err("actual page insert must fail after the pin was staged");
    assert_no_publication(&target);
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_backdated_grant_after_prepare_refuses_new_knowledge_substitution() {
    let target = LiveWorkerTarget::create("preparebackdated", 0x34107, 1);
    let producer = DuringProduce(|| {
        target.config.connect(NoTls).expect("the test database accepts the connection").execute(
            "INSERT INTO babylon_meta.archive_knowledge_grant_v1 \
             (campaign_id,subject_kind,subject_id,grant_key,granted_tick,provenance_ref) \
             VALUES($1,'county','99963','identity',0,babylon_meta.archive_provenance_intern_v1($1,'late-proof','backdated'))",
            &[target.campaign_id.as_uuid()],
        ).expect("the test database applies the setup statement");
        Ok(())
    });
    assert_eq!(
        ArchiveWorker::new(&target.config)
            .sweep_once(target.campaign_id, &producer)
            .expect_err("the fixture call `sweep_once` fails for the authored inputs"),
        SemanticArchiveError::ReceiptConflict
    );
    assert_no_publication(&target);
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_prepared_publication_preserves_historical_receipt_identity() {
    let target = LiveWorkerTarget::create("preparehistorical", 0x34108, 2);
    let original = archive_reader::scope_at(&target.config, target.campaign_id, 1);
    let store = SemanticArchiveStore::new(&target.config);
    let mut client = store
        .connect("historical preparation proof")
        .expect("the test database accepts the connection");
    let report = crate::archive_revision::publication::with_campaign_lock(
        &mut client,
        target.campaign_id,
        |client| {
            super::super::sweep_locked(
                client,
                target.campaign_id,
                &StubPageProducer,
                &ArchiveWorkerCancellation::default(),
                1,
            )
        },
    )
    .expect("the fixture builder accepts the authored options");
    assert_eq!(report.verified_tick(), 1);
    assert_eq!(report.durable_tick(), 2);
    let row = target.config.connect(NoTls).expect("the test database accepts the connection").query_one(
        "SELECT resolve_tick,tick_content_hash FROM babylon_meta.archive_receipt_consumption_v1 \
         WHERE campaign_id=$1", &[target.campaign_id.as_uuid()],
    ).expect("the seeded row is present exactly once");
    assert_eq!(row.get::<_, i64>(0), 1);
    assert_eq!(
        row.get::<_, Vec<u8>>(1),
        original
            .tick_content_hash()
            .expect("the committed tick has a content hash")
    );
    assert_eq!(
        archive_reader::scope_at(&target.config, target.campaign_id, 1),
        original
    );
    drop(client);
    target.finish();
}

#[derive(Clone, Copy)]
struct ComparisonPlan(u64);

impl crate::archive_revision::publication::ArchivePagePlan for ComparisonPlan {
    fn page_ref(&self) -> Result<ArchivePageRef, SemanticArchiveError> {
        Ok(support::stub_subject_spec(self.0).page_ref)
    }
}

fn fixed_comparison_input(tick: u64, hash: [u8; 32]) -> ArchivePageInput {
    let base = support::stub_page_input(
        &PendingArchiveReceipt::try_new(1, hash)
            .expect("the authored fixture satisfies the constructor invariants"),
    );
    ArchivePageInput::try_new(
        base.subject().clone(),
        tick,
        hash,
        "Which neighbor should organizers investigate?".to_owned(),
        base.signals().to_vec(),
        Vec::new(),
    )
    .expect("the authored fixture satisfies the constructor invariants")
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_dirty_comparison_renders_after_capture_commit() {
    let target = LiveWorkerTarget::create("detachedcomparison", 0x34109, 2);
    let store = SemanticArchiveStore::new(&target.config);
    let first_scope = archive_reader::scope_at(&target.config, target.campaign_id, 1);
    let first_hash = first_scope
        .tick_content_hash()
        .expect("the committed tick has a content hash");
    let first =
        ArchiveDirtyBatch::try_new(1, first_hash, vec![fixed_comparison_input(1, first_hash)])
            .expect("the authored fixture satisfies the constructor invariants");
    store
        .materialize_receipt(target.campaign_id, &first, ArchiveMaterializeMode::Consume)
        .expect("the fixture materializes the receipt");
    let scope = archive_reader::scope_at(&target.config, target.campaign_id, 2);
    let receipt = PendingArchiveReceipt::try_new(
        2,
        scope
            .tick_content_hash()
            .expect("the committed tick has a content hash"),
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let mut reader = target
        .config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let known = crate::archive_revision::tick_knowledge::capture(&mut reader, &scope)
        .expect("the fixture captures the authored state");
    let mut config = target.config.clone();
    config.application_name("per341-detached-comparison");
    let historical_calls = Cell::new(0);
    let outcome = crate::archive_revision::publication::select_dirty_pages(
        &config,
        target.campaign_id,
        &receipt,
        &known,
        &[ComparisonPlan(1)],
        1,
        |_plan, tick, hash| {
            if tick == 1 {
                historical_calls.set(historical_calls.get() + 1);
                let mut observer = target
                    .config
                    .connect(NoTls)
                    .expect("the test database accepts the connection");
                let row = observer
                    .query_one(
                        "SELECT count(*),bool_and(state='idle' AND xact_start IS NULL) \
                     FROM pg_stat_activity WHERE application_name='per341-detached-comparison'",
                        &[],
                    )
                    .expect("the seeded row is present exactly once");
                assert_eq!(row.get::<_, i64>(0), 1);
                assert_eq!(
                    row.get::<_, Option<bool>>(1),
                    Some(true),
                    "historical composition/rendering must be detached"
                );
                std::thread::sleep(Duration::from_millis(250));
            }
            Ok(fixed_comparison_input(tick, hash))
        },
    )
    .expect("historical comparison renders after its SQL capture commits");
    assert_eq!(historical_calls.get(), 1);
    assert!(
        outcome.batch().pages().is_empty(),
        "unchanged emission retains its original source"
    );
    assert_eq!(outcome.remaining(), 0);
    drop(reader);
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_detached_direct_materialization_restages_exact_bytes_and_refuses_corruption() {
    let target = LiveWorkerTarget::create("detachedrestage", 0x34110, 1);
    let store = SemanticArchiveStore::new(&target.config);
    let scope = archive_reader::scope_at(&target.config, target.campaign_id, 1);
    let hash = scope
        .tick_content_hash()
        .expect("the committed tick has a content hash");
    let batch = ArchiveDirtyBatch::try_new(1, hash, vec![fixed_comparison_input(1, hash)])
        .expect("the authored fixture satisfies the constructor invariants");
    assert_direct_render_failure_leaves_no_publication(&target, &store, hash);
    let first = store
        .materialize_receipt(target.campaign_id, &batch, ArchiveMaterializeMode::Stage)
        .expect("the fixture materializes the receipt");
    let second = store
        .materialize_receipt(target.campaign_id, &batch, ArchiveMaterializeMode::Stage)
        .expect("the fixture materializes the receipt");
    assert!(first.pages()[0].persisted());
    assert!(!second.pages()[0].persisted());
    assert_eq!(first.pages()[0].page(), second.pages()[0].page());
    assert_stored_revision_corruption_refused(
        &target,
        &store,
        &batch,
        first.pages()[0].page().search_text(),
    );
    target.finish();
}

fn assert_direct_render_failure_leaves_no_publication(
    target: &LiveWorkerTarget,
    store: &SemanticArchiveStore,
    hash: [u8; 32],
) {
    let unknown = ArchivePageInput::try_new(
        ArchiveSubject::try_new(
            ArchiveSubjectKind::County,
            "99999".to_owned(),
            "Unknown county".to_owned(),
        )
        .expect("the authored fixture satisfies the constructor invariants"),
        1,
        hash,
        "Who knows this county?".to_owned(),
        Vec::new(),
        Vec::new(),
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let refused = ArchiveDirtyBatch::try_new(1, hash, vec![unknown])
        .expect("the authored fixture satisfies the constructor invariants");
    assert_eq!(
        store.materialize_receipt(
            target.campaign_id,
            &refused,
            ArchiveMaterializeMode::Consume
        ),
        Err(SemanticArchiveError::UnknownSubject)
    );
    assert_no_publication(target);
}

fn assert_stored_revision_corruption_refused(
    target: &LiveWorkerTarget,
    store: &SemanticArchiveStore,
    batch: &ArchiveDirtyBatch,
    original_search_text: &str,
) {
    let mut client = target
        .config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    client.execute(
        "UPDATE babylon_meta.archive_page_revision_v2 SET search_text=search_text || ' forged' WHERE campaign_id=$1",
        &[target.campaign_id.as_uuid()],
    ).expect("the test database applies the setup statement");
    assert!(
        matches!(
            store.materialize_receipt(target.campaign_id, batch, ArchiveMaterializeMode::Consume),
            Err(SemanticArchiveError::ReceiptConflict | SemanticArchiveError::StoredPageMismatch)
        ),
        "matching stored revision digest must not conceal different stored fields"
    );
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        0
    );
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 1);
    client
        .execute(
            "UPDATE babylon_meta.archive_page_revision_v2 SET search_text=$2 WHERE campaign_id=$1",
            &[target.campaign_id.as_uuid(), &original_search_text],
        )
        .expect("the test database applies the setup statement");
    assert!(reverse_grant_membership(&mut client, target.campaign_id, None) > 0);
    assert!(
        store
            .materialize_receipt(target.campaign_id, batch, ArchiveMaterializeMode::Consume)
            .is_err(),
        "same count and digest cannot conceal reordered grant membership"
    );
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        0
    );
    assert!(reverse_grant_membership(&mut client, target.campaign_id, None) > 0);
    client.execute(
        "UPDATE babylon_meta.archive_page_revision_v2 SET body_bytes=body_bytes || decode('00','hex') WHERE campaign_id=$1",
        &[target.campaign_id.as_uuid()],
    ).expect("the test database applies the setup statement");
    assert!(
        store
            .materialize_receipt(target.campaign_id, batch, ArchiveMaterializeMode::Consume)
            .is_err(),
        "noncanonical emission bytes refuse reuse even with the original digest"
    );
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        0
    );
    drop(client);
}

fn reverse_grant_membership(
    client: &mut impl postgres::GenericClient,
    campaign: CampaignId,
    subject_id: Option<&str>,
) -> u64 {
    // Reverse complete parallel arrays: shape, count and reference validity
    // remain intact, so ordered canonical reconciliation must detect the fault.
    client
        .execute(
            "UPDATE babylon_meta.archive_page_revision_v2 SET \
             grant_subject_kinds=ARRAY(SELECT value FROM unnest(grant_subject_kinds) WITH ORDINALITY item(value,position) ORDER BY position DESC), \
             grant_subject_ids=ARRAY(SELECT value FROM unnest(grant_subject_ids) WITH ORDINALITY item(value,position) ORDER BY position DESC), \
             grant_keys=ARRAY(SELECT value FROM unnest(grant_keys) WITH ORDINALITY item(value,position) ORDER BY position DESC), \
             grant_ticks=ARRAY(SELECT value FROM unnest(grant_ticks) WITH ORDINALITY item(value,position) ORDER BY position DESC), \
             grant_provenance_refs=ARRAY(SELECT value FROM unnest(grant_provenance_refs) WITH ORDINALITY item(value,position) ORDER BY position DESC) \
             WHERE campaign_id=$1 AND ($2::text IS NULL OR subject_id=$2) AND grant_count>1",
            &[campaign.as_uuid(), &subject_id],
        )
        .expect("the test database applies the setup statement")
}

fn retained_comparison_input(
    plan: u64,
    tick: u64,
    hash: [u8; 32],
    changed: bool,
) -> ArchivePageInput {
    let base = support::stub_page_input(
        &PendingArchiveReceipt::try_new(plan, hash)
            .expect("the authored fixture satisfies the constructor invariants"),
    );
    ArchivePageInput::try_new(
        base.subject().clone(),
        tick,
        hash,
        if changed {
            "Which changed neighbor should organizers investigate?"
        } else {
            "Which neighbor should organizers investigate?"
        }
        .to_owned(),
        base.signals().to_vec(),
        Vec::new(),
    )
    .expect("the authored fixture satisfies the constructor invariants")
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_publication_reconciles_batch_and_exact_conflicts_with_constant_queries() {
    let target = LiveWorkerTarget::create("batchpublication", 0x34112, 1);
    let store = SemanticArchiveStore::new(&target.config);
    let scope = archive_reader::scope_at(&target.config, target.campaign_id, 1);
    let hash = scope
        .tick_content_hash()
        .expect("the committed tick has a content hash");
    let batch = ArchiveDirtyBatch::try_new(
        1,
        hash,
        (1..=3)
            .map(|plan| retained_comparison_input(plan, 1, hash, false))
            .collect(),
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let head = ArchiveDirtyBatch::try_new(1, hash, vec![batch.pages()[0].clone()])
        .expect("the authored fixture satisfies the constructor invariants");
    let mut query_counts = Vec::new();
    let mut previous: Option<ArchiveMaterializeReport> = None;
    for (input, mode, expected_insertions) in [
        (&head, ArchiveMaterializeMode::Stage, vec![true]),
        (
            &batch,
            ArchiveMaterializeMode::Stage,
            vec![false, true, true],
        ),
        (
            &batch,
            ArchiveMaterializeMode::Stage,
            vec![false, false, false],
        ),
        (
            &batch,
            ArchiveMaterializeMode::Consume,
            vec![false, false, false],
        ),
    ] {
        crate::archive_revision::storage::reset_capture_queries();
        let report = store
            .materialize_receipt(target.campaign_id, input, mode)
            .expect("the fixture materializes the receipt");
        query_counts.push(crate::archive_revision::storage::reset_capture_queries());
        assert_eq!(report.pages().len(), input.pages().len());
        assert_eq!(
            report
                .pages()
                .iter()
                .map(crate::MaterializedArchivePage::persisted)
                .collect::<Vec<_>>(),
            expected_insertions
        );
        for (page, expected) in report.pages().iter().zip(input.pages()) {
            assert_eq!(page.page_ref(), expected.subject().page_ref());
        }
        if let Some(previous) = previous.as_ref() {
            for (page, earlier) in report.pages().iter().zip(previous.pages()) {
                assert_eq!(page.page(), earlier.page());
            }
        }
        assert_eq!(
            receipt_consumption_count(&target.config, target.campaign_id),
            i64::from(mode == ArchiveMaterializeMode::Consume)
        );
        previous = Some(report);
    }
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 3);
    target.finish();
    // One existing-body capture (three when nonempty), then four exact batch
    // authentication queries. Page count and conflict count cannot add queries.
    assert_eq!(query_counts, [5, 7, 7, 7]);
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_batch_tail_corruption_after_prepare_rolls_back_earlier_inserts_and_consumption() {
    let target = LiveWorkerTarget::create("batchtailrefusal", 0x34113, 1);
    let store = SemanticArchiveStore::new(&target.config);
    let scope = archive_reader::scope_at(&target.config, target.campaign_id, 1);
    let hash = scope
        .tick_content_hash()
        .expect("the committed tick has a content hash");
    let batch = ArchiveDirtyBatch::try_new(
        1,
        hash,
        (1..=3)
            .map(|plan| retained_comparison_input(plan, 1, hash, false))
            .collect(),
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let tail = ArchiveDirtyBatch::try_new(1, hash, vec![batch.pages()[2].clone()])
        .expect("the authored fixture satisfies the constructor invariants");
    store
        .materialize_receipt(target.campaign_id, &tail, ArchiveMaterializeMode::Stage)
        .expect("the fixture materializes the receipt");
    let mut client = target
        .config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let original = publication_row_counts(&mut client, target.campaign_id);
    let tail_sql =
        "SELECT row_to_json(revision)::text FROM babylon_meta.archive_page_revision_v2 revision \
                    WHERE campaign_id=$1 AND subject_id='99925' AND effective_tick=1";
    let original_tail: String = client
        .query_one(tail_sql, &[target.campaign_id.as_uuid()])
        .expect("the seeded row is present exactly once")
        .get(0);
    assert_eq!(original[0], 1);
    assert_eq!(original[4], 0);
    for fault in LATE_TAIL_FAULTS {
        crate::archive_revision::publication::with_campaign_lock(
            &mut client,
            target.campaign_id,
            |client| {
                let (prepared, known) = prepare_checked_batch(client, &scope, &batch)?;
                let mut tx = client
                    .build_transaction()
                    .isolation_level(IsolationLevel::Serializable)
                    .start()
                    .expect("the fixture starts the authored period");
                crate::archive_revision::tick_knowledge::pin_prepared(&mut tx, &scope, &known)?;
                // Corruption occurs after detached authentication, inside the
                // atomic write. The conflict is last, after two new pages.
                assert_eq!(
                    tx.execute(
                        &format!(
                            "UPDATE babylon_meta.archive_page_revision_v2 SET {fault} \
                                  WHERE campaign_id=$1 AND subject_id='99925' AND effective_tick=1"
                        ),
                        &[target.campaign_id.as_uuid()],
                    )
                    .expect("the test database applies the setup statement"),
                    1
                );
                let refused = crate::archive_revision::publication::publish(
                    &mut tx,
                    prepared,
                    ArchiveMaterializeMode::Consume,
                );
                assert_eq!(
                    refused,
                    Err(SemanticArchiveError::ReceiptConflict),
                    "{fault}"
                );
                let staged = publication_row_counts(&mut tx, target.campaign_id);
                assert_eq!(
                    staged[0], 3,
                    "earlier pages were inserted before tail refusal"
                );
                assert!(
                    staged[1] > original[1],
                    "earlier atoms were inserted before refusal"
                );
                assert_eq!(staged[4], 0, "consumption must remain last");
                tx.rollback().expect("the open transaction rolls back");
                Ok(())
            },
        )
        .expect("the fixture builder accepts the authored options");
        assert_eq!(
            publication_row_counts(&mut client, target.campaign_id),
            original
        );
        assert_eq!(
            client
                .query_one(tail_sql, &[target.campaign_id.as_uuid()])
                .expect("the seeded row is present exactly once")
                .get::<_, String>(0),
            original_tail,
            "rollback must restore every stored scalar, body byte and membership array"
        );
    }
    drop(client);
    target.finish();
}

fn prepare_checked_batch(
    client: &mut Client,
    scope: &ArchiveReadScope,
    batch: &ArchiveDirtyBatch,
) -> Result<(PreparedPublication, ArchiveKnowledge), SemanticArchiveError> {
    let mut capture = client
        .build_transaction()
        .isolation_level(IsolationLevel::Serializable)
        .read_only(true)
        .start()
        .expect("the fixture starts the authored period");
    let known = crate::archive_revision::tick_knowledge::capture(&mut capture, scope)?;
    capture.commit().expect("the fixture transaction commits");
    let receipt = PendingArchiveReceipt::try_new(
        scope.tick(),
        scope
            .tick_content_hash()
            .expect("the committed tick has a content hash"),
    )?;
    let mut prepared = crate::archive_revision::publication::prepare(
        scope.campaign_id(),
        &receipt,
        batch,
        &known,
    )?;
    crate::archive_revision::publication::authenticate_existing(client, &mut prepared)?;
    Ok((prepared, known))
}

const LATE_TAIL_FAULTS: [&str; 7] = [
    "search_text=search_text || ' forged'",
    "content_sha256=decode(repeat('00',32),'hex')",
    "revision_sha256=decode(repeat('00',32),'hex')",
    "body_bytes=set_byte(body_bytes,0,get_byte(body_bytes,0) # 1)",
    "atom_ids=ARRAY(SELECT value FROM unnest(atom_ids) WITH ORDINALITY item(value,position) ORDER BY position DESC)",
    "grant_subject_kinds=ARRAY(SELECT value FROM unnest(grant_subject_kinds) WITH ORDINALITY item(value,position) ORDER BY position DESC), \
     grant_subject_ids=ARRAY(SELECT value FROM unnest(grant_subject_ids) WITH ORDINALITY item(value,position) ORDER BY position DESC), \
     grant_keys=ARRAY(SELECT value FROM unnest(grant_keys) WITH ORDINALITY item(value,position) ORDER BY position DESC), \
     grant_ticks=ARRAY(SELECT value FROM unnest(grant_ticks) WITH ORDINALITY item(value,position) ORDER BY position DESC), \
     grant_provenance_refs=ARRAY(SELECT value FROM unnest(grant_provenance_refs) WITH ORDINALITY item(value,position) ORDER BY position DESC)",
    "atom_ids[1]=decode(repeat('ff',32),'hex')",
];

fn publication_row_counts(
    client: &mut impl postgres::GenericClient,
    campaign: CampaignId,
) -> [i64; 5] {
    let row = client
        .query_one(
            "SELECT \
         (SELECT count(*) FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1), \
         (SELECT count(*) FROM babylon_meta.archive_atom_witness_v1 WHERE campaign_id=$1), \
         (SELECT count(*) FROM babylon_meta.archive_tick_knowledge_v3 WHERE campaign_id=$1), \
         (SELECT count(*) FROM babylon_meta.archive_knowledge_membership_v3 WHERE campaign_id=$1), \
         (SELECT count(*) FROM babylon_meta.archive_receipt_consumption_v1 WHERE campaign_id=$1)",
            &[campaign.as_uuid()],
        )
        .expect("the seeded row is present exactly once");
    std::array::from_fn(|column| row.get(column))
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_retained_comparison_has_constant_capture_queries_and_audits_beyond_head() {
    let target = LiveWorkerTarget::create("batchcomparison", 0x34111, 2);
    let store = SemanticArchiveStore::new(&target.config);
    let first = archive_reader::scope_at(&target.config, target.campaign_id, 1);
    let hash = first
        .tick_content_hash()
        .expect("the committed tick has a content hash");
    let plans = [ComparisonPlan(1), ComparisonPlan(2), ComparisonPlan(3)]; // Two county subjects and one place, all genuinely granted.
    let batch = ArchiveDirtyBatch::try_new(
        1,
        hash,
        plans
            .iter()
            .map(|plan| retained_comparison_input(plan.0, 1, hash, false))
            .collect(),
    )
    .expect("the authored fixture satisfies the constructor invariants");
    store
        .materialize_receipt(target.campaign_id, &batch, ArchiveMaterializeMode::Consume)
        .expect("the fixture materializes the receipt");
    let scope = archive_reader::scope_at(&target.config, target.campaign_id, 2);
    let receipt = PendingArchiveReceipt::try_new(
        2,
        scope
            .tick_content_hash()
            .expect("the committed tick has a content hash"),
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let mut reader = target
        .config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let known = crate::archive_revision::tick_knowledge::capture(&mut reader, &scope)
        .expect("the fixture captures the authored state");
    crate::archive_revision::storage::reset_capture_queries();
    let quiet = crate::archive_revision::publication::select_dirty_pages(
        &target.config,
        target.campaign_id,
        &receipt,
        &known,
        &plans,
        1,
        |plan, tick, hash| Ok(retained_comparison_input(plan.0, tick, hash, false)),
    )
    .expect("the fixture call `select_dirty_pages` succeeds for the authored inputs");
    assert!(quiet.batch().pages().is_empty());
    assert_eq!(quiet.remaining(), 0);
    let capture_queries = crate::archive_revision::storage::reset_capture_queries();
    let dirty = crate::archive_revision::publication::select_dirty_pages(
        &target.config,
        target.campaign_id,
        &receipt,
        &known,
        &plans,
        1,
        |plan, tick, hash| Ok(retained_comparison_input(plan.0, tick, hash, true)),
    )
    .expect("the fixture call `select_dirty_pages` succeeds for the authored inputs");
    assert_eq!(dirty.batch().pages().len(), 1);
    assert_eq!(
        dirty.batch().pages()[0].subject().page_ref(),
        &support::stub_subject_spec(1).page_ref
    );
    assert_eq!(dirty.remaining(), 2);
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 3);
    // The tail is not published or selected, but every captured membership must
    // still authenticate. Keeping only the head would hide this corruption.
    assert_eq!(
        reverse_grant_membership(&mut reader, target.campaign_id, Some("99925")),
        1
    );
    let refused = crate::archive_revision::publication::select_dirty_pages(
        &target.config,
        target.campaign_id,
        &receipt,
        &known,
        &plans,
        1,
        |plan, tick, hash| Ok(retained_comparison_input(plan.0, tick, hash, true)),
    );
    assert!(
        matches!(refused, Err(SemanticArchiveError::DuplicateGrant)),
        "unordered frozen grants must be refused: {:?}",
        refused.as_ref().err()
    );
    assert_eq!(
        reverse_grant_membership(&mut reader, target.campaign_id, Some("99925")),
        1
    );
    assert_changed_frozen_value_refused(&mut reader, &target, &receipt, &known, &plans);
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 3);
    drop(reader);
    target.finish();
    // Clean the isolated control before the intentional baseline RED assertion.
    assert_eq!(
        capture_queries, 3,
        "retained comparison must use three batched witness captures"
    );
}

fn assert_changed_frozen_value_refused(
    reader: &mut Client,
    target: &LiveWorkerTarget,
    receipt: &PendingArchiveReceipt,
    known: &ArchiveKnowledge,
    plans: &[ComparisonPlan],
) {
    // Preserve order, cardinality, and all valid references while changing one
    // frozen value within its allowed range. Canonical hashing must refuse this
    // independent fault even though the ordering validator accepts the arrays.
    assert_eq!(
        reader
            .execute(
                "UPDATE babylon_meta.archive_page_revision_v2 \
                 SET grant_ticks[1]=CASE WHEN grant_ticks[1]=0 THEN 1 ELSE 0 END \
                 WHERE campaign_id=$1 AND subject_id='99925' AND source_tick=1",
                &[target.campaign_id.as_uuid()],
            )
            .expect("the test database applies the setup statement"),
        1
    );
    let refused = crate::archive_revision::publication::select_dirty_pages(
        &target.config,
        target.campaign_id,
        receipt,
        known,
        plans,
        1,
        |plan, tick, hash| Ok(retained_comparison_input(plan.0, tick, hash, true)),
    );
    assert!(
        matches!(refused, Err(SemanticArchiveError::StoredPageMismatch)),
        "changed frozen grants must be refused: {:?}",
        refused.as_ref().err()
    );
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
#[allow(
    clippy::too_many_lines,
    reason = "`live_packed_archive_body_reconstructs_confined_identity_and_refuses_projection_and_frame` keeps one authored boundary's fixture and assertions together"
)]
fn live_packed_archive_body_reconstructs_confined_identity_and_refuses_projection_and_frame() {
    let target = LiveWorkerTarget::create("packedbody", 0x34341, 1);
    let mut client = target
        .config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let columns: i64 = client.query_one("SELECT count(*) FROM pg_catalog.pg_attribute WHERE attrelid='babylon_meta.archive_page_revision_v2'::regclass AND attname='body_bytes' AND NOT attisdropped", &[]).expect("the seeded row is present exactly once").get(0);
    assert_eq!(
        columns, 1,
        "actual publication must store the one bounded exact body tuple"
    );
    ArchiveWorker::new(&target.config)
        .sweep_once(target.campaign_id, &StubPageProducer)
        .expect("the fixture sweep completes");
    archive_reader::with_reader(&target.config, |reader| {
        let scope = archive_reader::scope_at(&target.config, target.campaign_id, 1);
        let subject = support::stub_subject_spec(1).page_ref;
        let ready = reader
            .dossier_as_of(&scope, &subject, &ArchiveDossierBounds::default())
            .expect("the fixture dossier exists at the authored period");
        let ArchiveDossierState::Ready { page: original, .. } = ready.state else {
            panic!("packed original ready");
        };
        let snapshot = client.query_one("SELECT body_encoding,body_decoded_length,body_decoded_sha256,body_bytes,search_text FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1", &[target.campaign_id.as_uuid()]).expect("the seeded row is present exactly once");
        for mutation in [
            "UPDATE babylon_meta.archive_page_revision_v2 SET body_encoding=2 WHERE campaign_id=$1",
            "UPDATE babylon_meta.archive_page_revision_v2 SET body_decoded_sha256=decode(repeat('00',32),'hex') WHERE campaign_id=$1",
            "UPDATE babylon_meta.archive_page_revision_v2 SET body_bytes=body_bytes || decode('00','hex') WHERE campaign_id=$1",
            "UPDATE babylon_meta.archive_page_revision_v2 SET search_text=search_text || ' forged' WHERE campaign_id=$1",
        ] {
            // Constraints prohibit unsupported encoding; corrupt storage after the
            // fixture drops only page checks, then rollback all DDL with mutation.
            let mut tx = client.transaction().expect("the test database opens a transaction");
            let checks = tx.query("SELECT conname FROM pg_catalog.pg_constraint WHERE conrelid='babylon_meta.archive_page_revision_v2'::regclass AND contype='c' AND pg_catalog.pg_get_constraintdef(oid) LIKE '%body_%'", &[]).expect("the seeded rows are readable");
            for check in checks {
                let name: String = check.get(0);
                tx.batch_execute(&format!("ALTER TABLE babylon_meta.archive_page_revision_v2 DROP CONSTRAINT \"{}\"",name.replace('"', "\"\""))).expect("the test database applies the schema statements");
            }
            tx.execute(mutation, &[target.campaign_id.as_uuid()]).expect("the test database applies the setup statement");
            let row=tx.query_one(&format!("SELECT {} FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1",crate::archive_revision::storage::COLUMNS), &[target.campaign_id.as_uuid()]).expect("the seeded row is present exactly once");
            assert!(crate::archive_revision::storage::capture_record(&mut tx,row,crate::archive_revision::storage::ReadAuthority::Writer).expect("the fixture captures the authored record").admit().is_err());
            tx.rollback().expect("the open transaction rolls back");
        }
        // A refreshed transport checksum cannot authenticate noncanonical emission.
        let row = client
            .query_one(
                &format!(
                    "SELECT {} FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1",
                    crate::archive_revision::storage::COLUMNS
                ),
                &[target.campaign_id.as_uuid()],
            )
            .expect("the seeded row is present exactly once");
        let record = crate::archive_revision::storage::capture_record(
            &mut client,
            row,
            crate::archive_revision::storage::ReadAuthority::Writer,
        )
        .expect("the fixture captures the authored record")
        .admit()
        .expect("the fixture admits the authored value");
        let emission = format!(
            "{} ",
            record
                .emission
                .encode()
                .expect("the fixture value encodes canonically")
        );
        let mut tuple = b"BabylonArchivePageBodyV1\0".to_vec();
        for field in [
            record.title.as_str(),
            record.markdown.as_str(),
            record.search_text.as_str(),
            record.provenance_json.as_str(),
            emission.as_str(),
        ] {
            tuple.extend_from_slice(
                &u32::try_from(field.len())
                    .expect("the fixture value fits the target range")
                    .to_be_bytes(),
            );
            tuple.extend_from_slice(field.as_bytes());
        }
        let frame = crate::storage_compression::compress_exact(&tuple, 11_538_477)
            .expect("the body fits the exact compressed bound");
        let sha = babylon_kernel::content_digest::sha256_of(&tuple);
        let length = i32::try_from(tuple.len()).expect("the fixture value fits the target range");
        let mut tx = client
            .transaction()
            .expect("the test database opens a transaction");
        tx.execute("UPDATE babylon_meta.archive_page_revision_v2 SET body_decoded_length=$2,body_decoded_sha256=$3,body_bytes=$4 WHERE campaign_id=$1", &[target.campaign_id.as_uuid(),&length,&&sha[..],&frame]).expect("the test database applies the setup statement");
        let row = tx
            .query_one(
                &format!(
                    "SELECT {} FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1",
                    crate::archive_revision::storage::COLUMNS
                ),
                &[target.campaign_id.as_uuid()],
            )
            .expect("the seeded row is present exactly once");
        assert!(crate::archive_revision::storage::capture_record(
            &mut tx,
            row,
            crate::archive_revision::storage::ReadAuthority::Writer
        )
        .expect("the fixture captures the authored record")
        .admit()
        .is_err());
        tx.rollback().expect("the open transaction rolls back");
        assert_eq!(snapshot.get::<_, i16>(0), 1);
        let again = reader
            .dossier_as_of(&scope, &subject, &ArchiveDossierBounds::default())
            .expect("the fixture dossier exists at the authored period");
        let ArchiveDossierState::Ready { page: restored, .. } = again.state else {
            panic!("restored packed original ready");
        };
        assert_eq!(restored, original);
    });
    drop(client);
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_alternate_valid_body_retry_preserves_canonical_frame_outside_publication() {
    use crate::archive_revision::body_encoding;
    let target = LiveWorkerTarget::create("bodyretry", 0x34342, 1);
    let scope = archive_reader::scope_at(&target.config, target.campaign_id, 1);
    let hash = scope
        .tick_content_hash()
        .expect("the committed tick has a content hash");
    let batch = ArchiveDirtyBatch::try_new(1, hash, vec![fixed_comparison_input(1, hash)])
        .expect("the authored fixture satisfies the constructor invariants");
    let mut config = target.config.clone();
    let application = format!("per343_body_retry_{}", std::process::id());
    config.application_name(&application);
    let store = SemanticArchiveStore::new(&config);
    body_encoding::reset_decode_counts();
    let staged = store
        .materialize_receipt(target.campaign_id, &batch, ArchiveMaterializeMode::Stage)
        .expect("the fixture materializes the receipt");
    assert_eq!(staged.pages().len(), 1);
    assert!(staged.pages()[0].persisted());
    assert_eq!(
        body_encoding::decode_counts(),
        (0, 0),
        "fresh publication compares prepared physical evidence without decompressing"
    );
    let mut inspector = target
        .config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let original = packed_body_record(&mut inspector, target.campaign_id);
    let digest = original
        .digest()
        .expect("the fixture value has a canonical digest");
    let alternate = install_equivalent_body_frame(&mut inspector, target.campaign_id, &original);
    let restored = packed_body_record(&mut inspector, target.campaign_id);
    assert_eq!(restored, original);
    assert_eq!(
        restored
            .digest()
            .expect("the fixture value has a canonical digest"),
        digest
    );
    body_encoding::reset_decode_counts();
    let (observations, observed) = mpsc::channel();
    let guard = observe_detached_body_replay(&target.config, &application, observations);
    let consumed = store
        .materialize_receipt(target.campaign_id, &batch, ArchiveMaterializeMode::Consume)
        .expect("the fixture materializes the receipt");
    drop(guard);
    assert_eq!(
        consumed.disposition(),
        crate::ArchiveMaterializeDisposition::Applied
    );
    assert_eq!(consumed.pages().len(), 1);
    assert!(!consumed.pages()[0].persisted());
    let (decodes, in_publication) = body_encoding::decode_counts();
    assert!(
        decodes > 0,
        "existing body was actually admitted, not skipped"
    );
    assert_eq!(
        in_publication, 0,
        "publication guard surrounds the real writer path"
    );
    assert_eq!(observed.try_iter().count(), decodes);
    let row=inspector.query_one("SELECT body_bytes,revision_sha256 FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1", &[target.campaign_id.as_uuid()]).expect("the seeded row is present exactly once");
    assert_eq!(
        row.get::<_, Vec<u8>>(0),
        alternate,
        "canonical retry preserves admitted prior frame rather than overwriting"
    );
    assert_eq!(row.get::<_, Vec<u8>>(1), digest);
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        1
    );
    archive_reader::with_reader(&target.config, |reader| {
        let read = reader
            .dossier_as_of(&scope, &original.subject, &ArchiveDossierBounds::default())
            .expect("the fixture dossier exists at the authored period");
        let ArchiveDossierState::Ready { page, .. } = read.state else {
            panic!("exact retried historical publication ready");
        };
        assert_eq!(page.revision_id, digest);
        assert_eq!(page.markdown, original.markdown);
        assert_eq!(page.atoms, original.atoms);
    });
    drop(inspector);
    target.finish();
}

fn packed_body_record(inspector: &mut Client, campaign: CampaignId) -> RevisionRecord {
    use crate::archive_revision::storage;
    let row = inspector
        .query_one(
            &format!(
                "SELECT {} FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1",
                storage::COLUMNS
            ),
            &[campaign.as_uuid()],
        )
        .expect("the seeded row is present exactly once");
    storage::capture_record(inspector, row, storage::ReadAuthority::Writer)
        .expect("the fixture captures the authored record")
        .admit()
        .expect("the fixture admits the authored value")
}

fn install_equivalent_body_frame(
    inspector: &mut Client,
    campaign: CampaignId,
    record: &RevisionRecord,
) -> Vec<u8> {
    use crate::archive_revision::body_encoding;
    let emission = record
        .emission
        .encode()
        .expect("the fixture value encodes canonically");
    let mut tuple = b"BabylonArchivePageBodyV1\0".to_vec();
    for field in [
        record.title.as_str(),
        record.markdown.as_str(),
        record.search_text.as_str(),
        record.provenance_json.as_str(),
        emission.as_str(),
    ] {
        tuple.extend_from_slice(
            &u32::try_from(field.len())
                .expect("the fixture value fits the target range")
                .to_be_bytes(),
        );
        tuple.extend_from_slice(field.as_bytes());
    }
    let stored: Vec<u8> = inspector
        .query_one(
            "SELECT body_bytes FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1",
            &[campaign.as_uuid()],
        )
        .expect("the seeded row is present exactly once")
        .get(0);
    let mut compressor =
        Compressor::new(3).expect("the constructor accepts the authored fixture arguments");
    compressor
        .set_parameter(CParameter::ChecksumFlag(true))
        .expect("the fixture accepts the authored setting");
    let alternate = compressor
        .compress(&tuple)
        .expect("the fixture call `compress` succeeds for the authored inputs");
    assert_ne!(
        alternate, stored,
        "alternate frame must actually exercise physical inequality"
    );
    let tuple_hash = babylon_kernel::content_digest::sha256_of(&tuple);
    assert_eq!(
        crate::storage_compression::decompress_exact(
            &alternate,
            tuple.len(),
            tuple_hash,
            body_encoding::MAX_BODY_BYTES
        )
        .expect("the compressed body decodes"),
        tuple
    );
    inspector
        .execute(
            "UPDATE babylon_meta.archive_page_revision_v2 SET body_bytes=$2 WHERE campaign_id=$1",
            &[campaign.as_uuid(), &alternate],
        )
        .expect("the test database applies the setup statement");
    alternate
}

fn observe_detached_body_replay(
    config: &Config,
    application: &str,
    counter: Sender<()>,
) -> DecodeObservation {
    use crate::archive_revision::body_encoding;
    let observer_config = config.clone();
    let observer_application = application.to_owned();
    body_encoding::observe_decode(move || {
        let mut observer = observer_config
            .connect(NoTls)
            .expect("the test database accepts the connection");
        let state=observer.query_one("SELECT count(*),bool_and(state='idle' AND xact_start IS NULL) FROM pg_catalog.pg_stat_activity WHERE datname=pg_catalog.current_database() AND application_name=$1 AND pid<>pg_catalog.pg_backend_pid()", &[&observer_application]).expect("the seeded row is present exactly once");
        assert_eq!(
            state.get::<_, i64>(0),
            1,
            "observe the actual sole materializer connection"
        );
        assert_eq!(
            state.get::<_, Option<bool>>(1),
            Some(true),
            "replay decompression occurs after capture commits and before writer starts"
        );
        counter.send(()).expect("observation receiver stays live");
    })
}
