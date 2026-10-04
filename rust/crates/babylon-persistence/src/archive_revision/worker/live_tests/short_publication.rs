//! Prepared inputs must survive only as owned Rust values during production.
use super::*;
use crate::ArchiveWorkerCancellation;

struct DuringProduce<F>(F);
impl<F: Fn() -> Result<(), SemanticArchiveError>> ArchiveDossierProducer for DuringProduce<F> {
    fn produce(
        &self,
        campaign: Uuid,
        receipt: &PendingArchiveReceipt,
        knowledge: &crate::ArchiveKnowledge,
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
    let mut client = target.config.connect(NoTls).unwrap();
    for relation in [
        "archive_tick_knowledge_v3",
        "archive_knowledge_membership_v3",
    ] {
        let count: i64 = client
            .query_one(
                &format!("SELECT count(*) FROM babylon_meta.{relation} WHERE campaign_id=$1"),
                &[target.campaign_id.as_uuid()],
            )
            .unwrap()
            .get(0);
        assert_eq!(count, 0, "no prepared pin survives in {relation}");
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_slow_producer_has_no_outer_transaction_at_short_idle_timeout() {
    let target = LiveWorkerTarget::create("shortpublication", 0x34101, 1);
    let store = SemanticArchiveStore::new(&target.config);
    let mut client = store.connect("short publication proof").unwrap();
    client
        .batch_execute("SET idle_in_transaction_session_timeout='100ms'")
        .unwrap();
    let pid: i32 = client
        .query_one("SELECT pg_backend_pid()", &[])
        .unwrap()
        .get(0);
    let producer = DuringProduce(|| {
        let mut observer = target.config.connect(NoTls).unwrap();
        let row = observer
            .query_one(
                "SELECT state,xact_start IS NULL FROM pg_stat_activity WHERE pid=$1",
                &[&pid],
            )
            .unwrap();
        assert_eq!(row.get::<_, String>(0), "idle");
        assert!(
            row.get::<_, bool>(1),
            "producer must own no outer SQL snapshot"
        );
        assert_no_publication(&target);
        std::thread::sleep(std::time::Duration::from_millis(250));
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
            result.unwrap_err(),
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
            let mut writer = target.config.connect(NoTls).unwrap();
            if grant {
                writer
                    .execute(
                        "UPDATE babylon_meta.archive_knowledge_grant_v1 \
                    SET provenance_locator='changed-after-prepare' WHERE campaign_id=$1 \
                    AND subject_kind='county' AND subject_id='99963' AND grant_key='subject'",
                        &[target.campaign_id.as_uuid()],
                    )
                    .unwrap();
            } else {
                writer
                    .execute(
                        "UPDATE babylon_state.archive_dirty_receipt_v1 \
                    SET tick_content_hash=$2 WHERE campaign_id=$1 AND resolve_tick=1",
                        &[target.campaign_id.as_uuid(), &&[0xab_u8; 32][..]],
                    )
                    .unwrap();
            }
            Ok(())
        });
        let error = ArchiveWorker::new(&target.config)
            .sweep_once(target.campaign_id, &producer)
            .unwrap_err();
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
        .unwrap()
        .batch_execute(
            "ALTER TABLE babylon_meta.archive_page_revision_v2 \
         ADD CONSTRAINT refuse_proof_page CHECK (subject_id <> '99963')",
        )
        .unwrap();
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
        target.config.connect(NoTls).unwrap().execute(
            "INSERT INTO babylon_meta.archive_knowledge_grant_v1 \
             (campaign_id,subject_kind,subject_id,grant_key,granted_tick,provenance_source_id,provenance_locator) \
             VALUES($1,'county','99963','identity',0,'late-proof','backdated')",
            &[target.campaign_id.as_uuid()],
        ).unwrap();
        Ok(())
    });
    assert_eq!(
        ArchiveWorker::new(&target.config)
            .sweep_once(target.campaign_id, &producer)
            .unwrap_err(),
        SemanticArchiveError::ReceiptConflict
    );
    assert_no_publication(&target);
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_prepared_publication_preserves_historical_receipt_identity() {
    let target = LiveWorkerTarget::create("preparehistorical", 0x34108, 2);
    let original = scope_at(&target.config, target.campaign_id, 1);
    let store = SemanticArchiveStore::new(&target.config);
    let mut client = store.connect("historical preparation proof").unwrap();
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
    .unwrap();
    assert_eq!(report.verified_tick(), 1);
    assert_eq!(report.durable_tick(), 2);
    let row = target.config.connect(NoTls).unwrap().query_one(
        "SELECT resolve_tick,tick_content_hash FROM babylon_meta.archive_receipt_consumption_v1 \
         WHERE campaign_id=$1", &[target.campaign_id.as_uuid()],
    ).unwrap();
    assert_eq!(row.get::<_, i64>(0), 1);
    assert_eq!(
        row.get::<_, Vec<u8>>(1),
        original.tick_content_hash().unwrap()
    );
    assert_eq!(scope_at(&target.config, target.campaign_id, 1), original);
    drop(client);
    target.finish();
}

fn fixed_comparison_input(tick: u64, hash: [u8; 32]) -> ArchivePageInput {
    let base = stub_page_input(&PendingArchiveReceipt::try_new(1, hash).unwrap());
    ArchivePageInput::try_new(
        base.subject().clone(),
        tick,
        hash,
        "Which neighbor should organizers investigate?".to_owned(),
        base.signals().to_vec(),
        Vec::new(),
    )
    .unwrap()
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_dirty_comparison_renders_after_capture_commit() {
    let target = LiveWorkerTarget::create("detachedcomparison", 0x34109, 2);
    let store = SemanticArchiveStore::new(&target.config);
    let first_scope = scope_at(&target.config, target.campaign_id, 1);
    let first_hash = first_scope.tick_content_hash().unwrap();
    let first =
        ArchiveDirtyBatch::try_new(1, first_hash, vec![fixed_comparison_input(1, first_hash)])
            .unwrap();
    store
        .materialize_receipt(
            target.campaign_id,
            &first,
            crate::ArchiveMaterializeMode::Consume,
        )
        .unwrap();
    let scope = scope_at(&target.config, target.campaign_id, 2);
    let receipt = PendingArchiveReceipt::try_new(2, scope.tick_content_hash().unwrap()).unwrap();
    let mut reader = target.config.connect(NoTls).unwrap();
    let known = crate::archive_revision::tick_knowledge::capture(&mut reader, &scope).unwrap();
    let mut config = target.config.clone();
    config.application_name("per341-detached-comparison");
    let historical_calls = std::cell::Cell::new(0);
    let outcome = crate::archive_revision::publication::select_dirty_pages(
        &config,
        target.campaign_id,
        &receipt,
        &known,
        &[()],
        1,
        |(), tick, hash| {
            if tick == 1 {
                historical_calls.set(historical_calls.get() + 1);
                let mut observer = target.config.connect(NoTls).unwrap();
                let row = observer
                    .query_one(
                        "SELECT count(*),bool_and(state='idle' AND xact_start IS NULL) \
                     FROM pg_stat_activity WHERE application_name='per341-detached-comparison'",
                        &[],
                    )
                    .unwrap();
                assert_eq!(row.get::<_, i64>(0), 1);
                assert_eq!(
                    row.get::<_, Option<bool>>(1),
                    Some(true),
                    "historical composition/rendering must be detached"
                );
                std::thread::sleep(std::time::Duration::from_millis(250));
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
    let scope = scope_at(&target.config, target.campaign_id, 1);
    let hash = scope.tick_content_hash().unwrap();
    let batch = ArchiveDirtyBatch::try_new(1, hash, vec![fixed_comparison_input(1, hash)]).unwrap();
    assert_direct_render_failure_leaves_no_publication(&target, &store, hash);
    let first = store
        .materialize_receipt(
            target.campaign_id,
            &batch,
            crate::ArchiveMaterializeMode::Stage,
        )
        .unwrap();
    let second = store
        .materialize_receipt(
            target.campaign_id,
            &batch,
            crate::ArchiveMaterializeMode::Stage,
        )
        .unwrap();
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
        .unwrap(),
        1,
        hash,
        "Who knows this county?".to_owned(),
        Vec::new(),
        Vec::new(),
    )
    .unwrap();
    let refused = ArchiveDirtyBatch::try_new(1, hash, vec![unknown]).unwrap();
    assert_eq!(
        store.materialize_receipt(
            target.campaign_id,
            &refused,
            crate::ArchiveMaterializeMode::Consume
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
    let mut client = target.config.connect(NoTls).unwrap();
    client.execute(
        "UPDATE babylon_meta.archive_page_revision_v2 SET search_text=search_text || ' forged' WHERE campaign_id=$1",
        &[target.campaign_id.as_uuid()],
    ).unwrap();
    assert!(
        matches!(
            store.materialize_receipt(
                target.campaign_id,
                batch,
                crate::ArchiveMaterializeMode::Consume
            ),
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
        .unwrap();
    client.execute(
        "UPDATE babylon_meta.archive_revision_grant_v2 SET position=512 WHERE campaign_id=$1 AND position=0",
        &[target.campaign_id.as_uuid()],
    ).unwrap();
    assert!(
        store
            .materialize_receipt(
                target.campaign_id,
                batch,
                crate::ArchiveMaterializeMode::Consume
            )
            .is_err(),
        "same count and digest cannot conceal reordered grant membership"
    );
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        0
    );
    client.execute(
        "UPDATE babylon_meta.archive_revision_grant_v2 SET position=0 WHERE campaign_id=$1 AND position=512",
        &[target.campaign_id.as_uuid()],
    ).unwrap();
    client.execute(
        "UPDATE babylon_meta.archive_page_revision_v2 SET body_bytes=body_bytes || decode('00','hex') WHERE campaign_id=$1",
        &[target.campaign_id.as_uuid()],
    ).unwrap();
    assert!(
        store
            .materialize_receipt(
                target.campaign_id,
                batch,
                crate::ArchiveMaterializeMode::Consume
            )
            .is_err(),
        "noncanonical emission bytes refuse reuse even with the original digest"
    );
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        0
    );
    drop(client);
}

fn retained_comparison_input(
    plan: u64,
    tick: u64,
    hash: [u8; 32],
    changed: bool,
) -> ArchivePageInput {
    let base = stub_page_input(&PendingArchiveReceipt::try_new(plan, hash).unwrap());
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
    .unwrap()
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_retained_comparison_has_constant_capture_queries_and_audits_beyond_head() {
    let target = LiveWorkerTarget::create("batchcomparison", 0x34111, 2);
    let store = SemanticArchiveStore::new(&target.config);
    let first = scope_at(&target.config, target.campaign_id, 1);
    let hash = first.tick_content_hash().unwrap();
    let plans = [1_u64, 2, 3]; // Two county subjects and one place, all genuinely granted.
    let batch = ArchiveDirtyBatch::try_new(
        1,
        hash,
        plans
            .iter()
            .map(|plan| retained_comparison_input(*plan, 1, hash, false))
            .collect(),
    )
    .unwrap();
    store
        .materialize_receipt(
            target.campaign_id,
            &batch,
            crate::ArchiveMaterializeMode::Consume,
        )
        .unwrap();
    let scope = scope_at(&target.config, target.campaign_id, 2);
    let receipt = PendingArchiveReceipt::try_new(2, scope.tick_content_hash().unwrap()).unwrap();
    let mut reader = target.config.connect(NoTls).unwrap();
    let known = crate::archive_revision::tick_knowledge::capture(&mut reader, &scope).unwrap();
    crate::archive_revision::storage::reset_capture_queries();
    let quiet = crate::archive_revision::publication::select_dirty_pages(
        &target.config,
        target.campaign_id,
        &receipt,
        &known,
        &plans,
        1,
        |plan, tick, hash| Ok(retained_comparison_input(*plan, tick, hash, false)),
    )
    .unwrap();
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
        |plan, tick, hash| Ok(retained_comparison_input(*plan, tick, hash, true)),
    )
    .unwrap();
    assert_eq!(dirty.batch().pages().len(), 1);
    assert_eq!(
        dirty.batch().pages()[0].subject().page_ref(),
        &stub_subject_spec(1).page_ref
    );
    assert_eq!(dirty.remaining(), 2);
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 3);
    // The tail is not published or selected, but every captured membership must
    // still authenticate. Keeping only the head would hide this corruption.
    assert_eq!(
        reader
            .execute(
                "UPDATE babylon_meta.archive_revision_grant_v2 \
        SET position=512 WHERE campaign_id=$1 AND subject_kind='county' \
        AND subject_id='99925' AND effective_tick=1 AND position=0",
                &[target.campaign_id.as_uuid()]
            )
            .unwrap(),
        1
    );
    let refused = crate::archive_revision::publication::select_dirty_pages(
        &target.config,
        target.campaign_id,
        &receipt,
        &known,
        &plans,
        1,
        |plan, tick, hash| Ok(retained_comparison_input(*plan, tick, hash, true)),
    );
    assert!(matches!(
        refused,
        Err(SemanticArchiveError::StoredPageMismatch)
    ));
    assert_eq!(archive_page_count(&target.config, target.campaign_id), 3);
    drop(reader);
    target.finish();
    // Clean the isolated control before the intentional baseline RED assertion.
    assert_eq!(
        capture_queries, 3,
        "retained comparison must use three batched witness captures"
    );
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_packed_archive_body_reconstructs_confined_identity_and_refuses_projection_and_frame() {
    let target = LiveWorkerTarget::create("packedbody", 0x34341, 1);
    let mut client = target.config.connect(NoTls).unwrap();
    let columns: i64 = client.query_one("SELECT count(*) FROM pg_catalog.pg_attribute WHERE attrelid='babylon_meta.archive_page_revision_v2'::regclass AND attname='body_bytes' AND NOT attisdropped", &[]).unwrap().get(0);
    assert_eq!(
        columns, 1,
        "actual publication must store the one bounded exact body tuple"
    );
    ArchiveWorker::new(&target.config)
        .sweep_once(target.campaign_id, &StubPageProducer)
        .unwrap();
    with_reader(&target.config, |reader| {
        let scope = scope_at(&target.config, target.campaign_id, 1);
        let subject = stub_subject_spec(1).page_ref;
        let ready = reader
            .dossier_as_of(&scope, &subject, &ArchiveDossierBounds::default())
            .unwrap();
        let ArchiveDossierState::Ready { page: original, .. } = ready.state else {
            panic!("packed original ready");
        };
        let snapshot = client.query_one("SELECT body_encoding,body_decoded_length,body_decoded_sha256,body_bytes,search_text FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1", &[target.campaign_id.as_uuid()]).unwrap();
        for mutation in [
            "UPDATE babylon_meta.archive_page_revision_v2 SET body_encoding=2 WHERE campaign_id=$1",
            "UPDATE babylon_meta.archive_page_revision_v2 SET body_decoded_sha256=decode(repeat('00',32),'hex') WHERE campaign_id=$1",
            "UPDATE babylon_meta.archive_page_revision_v2 SET body_bytes=body_bytes || decode('00','hex') WHERE campaign_id=$1",
            "UPDATE babylon_meta.archive_page_revision_v2 SET search_text=search_text || ' forged' WHERE campaign_id=$1",
        ] {
            // Constraints prohibit unsupported encoding; corrupt storage after the
            // fixture drops only page checks, then rollback all DDL with mutation.
            let mut tx = client.transaction().unwrap();
            let checks = tx.query("SELECT conname FROM pg_catalog.pg_constraint WHERE conrelid='babylon_meta.archive_page_revision_v2'::regclass AND contype='c' AND pg_catalog.pg_get_constraintdef(oid) LIKE '%body_%'", &[]).unwrap();
            for check in checks {
                let name: String = check.get(0);
                tx.batch_execute(&format!("ALTER TABLE babylon_meta.archive_page_revision_v2 DROP CONSTRAINT \"{}\"",name.replace('"', "\"\""))).unwrap();
            }
            tx.execute(mutation, &[target.campaign_id.as_uuid()]).unwrap();
            let row=tx.query_one(&format!("SELECT {} FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1",crate::archive_revision::storage::COLUMNS), &[target.campaign_id.as_uuid()]).unwrap();
            assert!(crate::archive_revision::storage::capture_record(&mut tx,row,crate::archive_revision::storage::ReadAuthority::Writer).unwrap().admit().is_err());
            tx.rollback().unwrap();
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
            .unwrap();
        let record = crate::archive_revision::storage::capture_record(
            &mut client,
            row,
            crate::archive_revision::storage::ReadAuthority::Writer,
        )
        .unwrap()
        .admit()
        .unwrap();
        let emission = format!("{} ", record.emission.encode().unwrap());
        let mut tuple = b"BabylonArchivePageBodyV1\0".to_vec();
        for field in [
            record.title.as_str(),
            record.markdown.as_str(),
            record.search_text.as_str(),
            record.provenance_json.as_str(),
            emission.as_str(),
        ] {
            tuple.extend_from_slice(&u32::try_from(field.len()).unwrap().to_be_bytes());
            tuple.extend_from_slice(field.as_bytes());
        }
        let frame = crate::storage_compression::compress_exact(&tuple, 11_538_477).unwrap();
        let sha = babylon_kernel::content_digest::sha256_of(&tuple);
        let length = i32::try_from(tuple.len()).unwrap();
        let mut tx = client.transaction().unwrap();
        tx.execute("UPDATE babylon_meta.archive_page_revision_v2 SET body_decoded_length=$2,body_decoded_sha256=$3,body_bytes=$4 WHERE campaign_id=$1", &[target.campaign_id.as_uuid(),&length,&&sha[..],&frame]).unwrap();
        let row = tx
            .query_one(
                &format!(
                    "SELECT {} FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1",
                    crate::archive_revision::storage::COLUMNS
                ),
                &[target.campaign_id.as_uuid()],
            )
            .unwrap();
        assert!(crate::archive_revision::storage::capture_record(
            &mut tx,
            row,
            crate::archive_revision::storage::ReadAuthority::Writer
        )
        .unwrap()
        .admit()
        .is_err());
        tx.rollback().unwrap();
        assert_eq!(snapshot.get::<_, i16>(0), 1);
        let again = reader
            .dossier_as_of(&scope, &subject, &ArchiveDossierBounds::default())
            .unwrap();
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
    let scope = scope_at(&target.config, target.campaign_id, 1);
    let hash = scope.tick_content_hash().unwrap();
    let batch = ArchiveDirtyBatch::try_new(1, hash, vec![fixed_comparison_input(1, hash)]).unwrap();
    let mut config = target.config.clone();
    let application = format!("per343_body_retry_{}", std::process::id());
    config.application_name(&application);
    let store = SemanticArchiveStore::new(&config);
    body_encoding::reset_decode_counts();
    let staged = store
        .materialize_receipt(
            target.campaign_id,
            &batch,
            crate::ArchiveMaterializeMode::Stage,
        )
        .unwrap();
    assert_eq!(staged.pages().len(), 1);
    assert!(staged.pages()[0].persisted());
    assert_eq!(
        body_encoding::decode_counts(),
        (0, 0),
        "fresh publication compares prepared physical evidence without decompressing"
    );
    let mut inspector = target.config.connect(NoTls).unwrap();
    let original = packed_body_record(&mut inspector, target.campaign_id);
    let digest = original.digest().unwrap();
    let alternate = install_equivalent_body_frame(&mut inspector, target.campaign_id, &original);
    let restored = packed_body_record(&mut inspector, target.campaign_id);
    assert_eq!(restored, original);
    assert_eq!(restored.digest().unwrap(), digest);
    body_encoding::reset_decode_counts();
    let observations = std::rc::Rc::new(std::cell::Cell::new(0_usize));
    let guard = observe_detached_body_replay(&target.config, &application, observations.clone());
    let consumed = store
        .materialize_receipt(
            target.campaign_id,
            &batch,
            crate::ArchiveMaterializeMode::Consume,
        )
        .unwrap();
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
    assert_eq!(observations.get(), decodes);
    let row=inspector.query_one("SELECT body_bytes,revision_sha256 FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1", &[target.campaign_id.as_uuid()]).unwrap();
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
    with_reader(&target.config, |reader| {
        let read = reader
            .dossier_as_of(&scope, &original.subject, &ArchiveDossierBounds::default())
            .unwrap();
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

fn packed_body_record(
    inspector: &mut postgres::Client,
    campaign: CampaignId,
) -> crate::archive_revision::record::RevisionRecord {
    use crate::archive_revision::storage;
    let row = inspector
        .query_one(
            &format!(
                "SELECT {} FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1",
                storage::COLUMNS
            ),
            &[campaign.as_uuid()],
        )
        .unwrap();
    storage::capture_record(inspector, row, storage::ReadAuthority::Writer)
        .unwrap()
        .admit()
        .unwrap()
}

fn install_equivalent_body_frame(
    inspector: &mut postgres::Client,
    campaign: CampaignId,
    record: &crate::archive_revision::record::RevisionRecord,
) -> Vec<u8> {
    use crate::archive_revision::body_encoding;
    let emission = record.emission.encode().unwrap();
    let mut tuple = b"BabylonArchivePageBodyV1\0".to_vec();
    for field in [
        record.title.as_str(),
        record.markdown.as_str(),
        record.search_text.as_str(),
        record.provenance_json.as_str(),
        emission.as_str(),
    ] {
        tuple.extend_from_slice(&u32::try_from(field.len()).unwrap().to_be_bytes());
        tuple.extend_from_slice(field.as_bytes());
    }
    let stored: Vec<u8> = inspector
        .query_one(
            "SELECT body_bytes FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1",
            &[campaign.as_uuid()],
        )
        .unwrap()
        .get(0);
    let mut compressor = zstd::bulk::Compressor::new(3).unwrap();
    compressor
        .set_parameter(zstd::zstd_safe::CParameter::ChecksumFlag(true))
        .unwrap();
    let alternate = compressor.compress(&tuple).unwrap();
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
        .unwrap(),
        tuple
    );
    inspector
        .execute(
            "UPDATE babylon_meta.archive_page_revision_v2 SET body_bytes=$2 WHERE campaign_id=$1",
            &[campaign.as_uuid(), &alternate],
        )
        .unwrap();
    alternate
}

fn observe_detached_body_replay(
    config: &Config,
    application: &str,
    counter: std::rc::Rc<std::cell::Cell<usize>>,
) -> crate::archive_revision::body_encoding::DecodeObservation {
    use crate::archive_revision::body_encoding;
    let observer_config = config.clone();
    let observer_application = application.to_owned();
    body_encoding::observe_decode(move || {
        let mut observer = observer_config.connect(NoTls).unwrap();
        let state=observer.query_one("SELECT count(*),bool_and(state='idle' AND xact_start IS NULL) FROM pg_catalog.pg_stat_activity WHERE datname=pg_catalog.current_database() AND application_name=$1 AND pid<>pg_catalog.pg_backend_pid()", &[&observer_application]).unwrap();
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
        counter.set(counter.get().checked_add(1).unwrap());
    })
}
