//! Shared frozen bases must preserve exact history and reject admission corruption.
use super::*;
use crate::archive_revision::{publication, tick_knowledge};
use crate::{ArchiveMaterializeMode, SemanticArchiveReaderError};
use postgres::IsolationLevel;

fn empty_batch(target: &LiveWorkerTarget, tick: u64) -> ArchiveDirtyBatch {
    let scope = scope_at(&target.config, target.campaign_id, tick);
    ArchiveDirtyBatch::try_new(tick, scope.tick_content_hash().unwrap(), Vec::new()).unwrap()
}

fn grant_at(target: &LiveWorkerTarget, key: &str, tick: u64) {
    SemanticArchiveStore::new(&target.config)
        .grant_knowledge(
            target.campaign_id,
            &ArchiveKnowledgeGrant::try_new(
                stub_subject_spec(1).page_ref,
                key.to_owned(),
                tick,
                ArchiveCitation::try_new("checkpoint-proof".to_owned(), format!("{key}@{tick}"))
                    .unwrap(),
            )
            .unwrap(),
        )
        .unwrap();
}

fn consume_through(target: &LiveWorkerTarget, last: u64) {
    let store = SemanticArchiveStore::new(&target.config);
    for tick in 1..=last {
        store
            .materialize_receipt(
                target.campaign_id,
                &empty_batch(target, tick),
                ArchiveMaterializeMode::Consume,
            )
            .unwrap();
    }
}

fn frozen(target: &LiveWorkerTarget, tick: u64) -> crate::ArchiveKnowledge {
    tick_knowledge::load(
        &mut target.config.connect(NoTls).unwrap(),
        &scope_at(&target.config, target.campaign_id, tick),
    )
    .unwrap()
}

fn full_cohort(
    client: &mut impl postgres::GenericClient,
    campaign: CampaignId,
    tick: i64,
) -> (i64, Vec<u8>) {
    let row = client
        .query_one(
            "SELECT grant_count,knowledge_sha256 FROM babylon_meta.archive_knowledge_cohort_v3 \
         WHERE campaign_id=$1 AND resolve_tick=$2 AND NOT admitted_only",
            &[campaign.as_uuid(), &tick],
        )
        .unwrap();
    (row.get(0), row.get(1))
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_shared_membership_preserves_checkpoint_boundary_and_historical_reads() {
    assert_eq!(tick_knowledge::ARCHIVE_KNOWLEDGE_CHECKPOINT_PERIODS, 13);
    let target = LiveWorkerTarget::create("checkpointboundary", 0x34301, 14);
    grant_at(&target, "checkpoint-proof", 2);
    consume_through(&target, 14);
    let first = frozen(&target, 1);
    let second = frozen(&target, 2);
    assert_eq!(second.rows().count(), first.rows().count() + 1);
    assert_eq!(frozen(&target, 13), second);
    assert_eq!(frozen(&target, 14), second);
    assert!(first
        .grant(&stub_subject_spec(1).page_ref, "checkpoint-proof")
        .is_none());
    let mut client = target.config.connect(NoTls).unwrap();
    let rows = client.query(
        "SELECT resolve_tick,checkpoint_tick,admitted_count FROM babylon_meta.archive_tick_knowledge_v3 \
         WHERE campaign_id=$1 ORDER BY resolve_tick", &[target.campaign_id.as_uuid()],
    ).unwrap();
    assert_eq!(rows.len(), 14);
    for row in rows {
        let tick: i64 = row.get(0);
        assert_eq!(row.get::<_, i64>(1), if tick == 14 { 14 } else { 1 });
        let count = match tick {
            1 => first.rows().count(),
            2 => 1,
            14 => second.rows().count(),
            _ => 0,
        };
        assert_eq!(usize::try_from(row.get::<_, i32>(2)).unwrap(), count);
    }
    let count: i64 = client.query_one(
        "SELECT count(*) FROM babylon_meta.archive_knowledge_membership_v3 WHERE campaign_id=$1",
        &[target.campaign_id.as_uuid()],
    ).unwrap().get(0);
    assert_eq!(
        usize::try_from(count).unwrap(),
        first.rows().count() + 1 + second.rows().count()
    );
    with_reader(&target.config, |reader| {
        for tick in [1, 2, 13, 14] {
            assert!(reader
                .search_as_of(
                    &scope_at(&target.config, target.campaign_id, tick),
                    "checkpoint",
                    10
                )
                .unwrap()
                .hits
                .is_empty());
        }
    });
    let mut transaction = client.transaction().unwrap();
    transaction.execute(
        "UPDATE babylon_meta.archive_tick_knowledge_v3 SET admitted_sha256=decode(repeat('ab',32),'hex') \
         WHERE campaign_id=$1 AND resolve_tick=2", &[target.campaign_id.as_uuid()],
    ).unwrap();
    assert_eq!(
        tick_knowledge::load(
            &mut transaction,
            &scope_at(&target.config, target.campaign_id, 13)
        ),
        Err(SemanticArchiveError::StoredPageMismatch)
    );
    assert_eq!(
        tick_knowledge::load(
            &mut transaction,
            &scope_at(&target.config, target.campaign_id, 14)
        )
        .unwrap(),
        second
    );
    transaction.rollback().unwrap();
    drop(client);
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_changed_admission_refuses_even_when_later_full_set_is_unchanged() {
    let target = LiveWorkerTarget::create("admissionmove", 0x34302, 3);
    grant_at(&target, "checkpoint-proof", 2);
    consume_through(&target, 3);
    let scope = scope_at(&target.config, target.campaign_id, 3);
    let expected = frozen(&target, 3);
    let mut client = target.config.connect(NoTls).unwrap();
    let before = full_cohort(&mut client, target.campaign_id, 3);
    assert_eq!(
        client
            .execute(
                "UPDATE babylon_meta.archive_knowledge_membership_v3 SET admitted_at_tick=3 \
         WHERE campaign_id=$1 AND checkpoint_tick=1 AND grant_key='checkpoint-proof'",
                &[target.campaign_id.as_uuid()],
            )
            .unwrap(),
        1
    );
    assert_eq!(full_cohort(&mut client, target.campaign_id, 3), before);
    assert_eq!(
        tick_knowledge::load(&mut client, &scope),
        Err(SemanticArchiveError::StoredPageMismatch)
    );
    with_reader(&target.config, |reader| {
        assert_eq!(
            reader.search_as_of(&scope, "checkpoint", 10),
            Err(SemanticArchiveReaderError::Archive(
                SemanticArchiveError::StoredPageMismatch
            ))
        );
    });
    assert_eq!(
        client
            .execute(
                "UPDATE babylon_meta.archive_knowledge_membership_v3 SET admitted_at_tick=2 \
         WHERE campaign_id=$1 AND checkpoint_tick=1 AND grant_key='checkpoint-proof'",
                &[target.campaign_id.as_uuid()],
            )
            .unwrap(),
        1
    );
    assert_eq!(tick_knowledge::load(&mut client, &scope).unwrap(), expected);
    drop(client);
    target.finish();
}

fn assert_corruption_refused(target: &LiveWorkerTarget, statement: &str) {
    let scope = scope_at(&target.config, target.campaign_id, 3);
    let mut client = target.config.connect(NoTls).unwrap();
    let expected = tick_knowledge::load(&mut client, &scope).unwrap();
    let mut tx = client.transaction().unwrap();
    assert_eq!(
        tx.execute(statement, &[target.campaign_id.as_uuid()])
            .unwrap(),
        1
    );
    assert_eq!(
        tick_knowledge::load(&mut tx, &scope),
        Err(SemanticArchiveError::StoredPageMismatch)
    );
    tx.rollback().unwrap();
    assert_eq!(tick_knowledge::load(&mut client, &scope).unwrap(), expected);
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_frozen_membership_refuses_missing_extra_base_reference_and_delta_corruption() {
    let target = LiveWorkerTarget::create("checkpointcorrupt", 0x34303, 3);
    grant_at(&target, "checkpoint-proof", 2);
    consume_through(&target, 3);
    let original = frozen(&target, 1);
    grant_at(&target, "unadmitted-proof", 0);
    assert_eq!(
        frozen(&target, 1),
        original,
        "backdated arrival cannot alter the shared historical base"
    );
    for statement in [
        "DELETE FROM babylon_meta.archive_knowledge_membership_v3 WHERE campaign_id=$1 AND checkpoint_tick=1 AND subject_kind='county' AND subject_id='99963' AND grant_key='employment'",
        "INSERT INTO babylon_meta.archive_knowledge_membership_v3 (campaign_id,checkpoint_tick,admitted_at_tick,subject_kind,subject_id,grant_key) VALUES($1,1,3,'county','99963','unadmitted-proof')",
        "UPDATE babylon_meta.archive_tick_knowledge_v3 SET knowledge_sha256=decode(repeat('ab',32),'hex'),admitted_sha256=decode(repeat('ab',32),'hex') WHERE campaign_id=$1 AND resolve_tick=1",
        "UPDATE babylon_meta.archive_tick_knowledge_v3 SET checkpoint_tick=2 WHERE campaign_id=$1 AND resolve_tick=3",
        "UPDATE babylon_meta.archive_tick_knowledge_v3 SET admitted_sha256=decode(repeat('ab',32),'hex') WHERE campaign_id=$1 AND resolve_tick=2",
        "UPDATE babylon_meta.archive_tick_knowledge_v3 SET admitted_count=0 WHERE campaign_id=$1 AND resolve_tick=2",
    ] {
        assert_corruption_refused(&target, statement);
    }
    target.finish();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_checkpoint_page_failure_rolls_back_new_base_without_disturbing_history() {
    let target = LiveWorkerTarget::create("checkpointrollback", 0x34304, 14);
    consume_through(&target, 13);
    let original = frozen(&target, 13);
    let scope = scope_at(&target.config, target.campaign_id, 14);
    let receipt = PendingArchiveReceipt::try_new(14, scope.tick_content_hash().unwrap()).unwrap();
    let batch = ArchiveDirtyBatch::try_new(
        14,
        *receipt.tick_content_hash(),
        vec![stub_page_input(&receipt)],
    )
    .unwrap();
    let store = SemanticArchiveStore::new(&target.config);
    let mut client = store.connect("checkpoint rollback control").unwrap();
    publication::with_campaign_lock(&mut client, target.campaign_id, |client| {
        let known = tick_knowledge::capture(client, &scope)?;
        let mut prepared = publication::prepare(target.campaign_id, &receipt, &batch, &known)?;
        publication::authenticate_existing(client, &mut prepared)?;
        let mut tx = client.build_transaction().isolation_level(IsolationLevel::Serializable).read_only(false).start().unwrap();
        crate::current_schema::require_current_schema(&mut tx).unwrap();
        tick_knowledge::pin_prepared(&mut tx, &scope, &known)?;
        let count: i64 = tx.query_one(
            "SELECT count(*) FROM babylon_meta.archive_knowledge_membership_v3 WHERE campaign_id=$1 AND checkpoint_tick=14",
            &[target.campaign_id.as_uuid()],
        ).unwrap().get(0);
        assert_eq!(usize::try_from(count).unwrap(), known.rows().count());
        tx.batch_execute("ALTER TABLE babylon_meta.archive_page_revision_v2 ADD CONSTRAINT refuse_checkpoint_page CHECK (subject_id <> '9990001')").unwrap();
        let Err(SemanticArchiveError::Database { diagnostic, .. }) =
            publication::publish(&mut tx, prepared, ArchiveMaterializeMode::Consume)
        else {
            panic!("the injected page constraint must refuse publication")
        };
        assert_eq!(diagnostic.sqlstate(), Some("23514"));
        drop(tx); // An actual failed insert rolls back header, base, atoms, DDL and claim.
        Ok(())
    }).unwrap();
    assert_eq!(frozen(&target, 13), original);
    for query in [
        "SELECT count(*) FROM babylon_meta.archive_tick_knowledge_v3 WHERE campaign_id=$1 AND resolve_tick=14",
        "SELECT count(*) FROM babylon_meta.archive_knowledge_membership_v3 WHERE campaign_id=$1 AND checkpoint_tick=14",
        "SELECT count(*) FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1 AND effective_tick=14",
        "SELECT count(*) FROM babylon_meta.archive_receipt_consumption_v1 WHERE campaign_id=$1 AND resolve_tick=14",
    ] {
        assert_eq!(client.query_one(query, &[target.campaign_id.as_uuid()]).unwrap().get::<_, i64>(0), 0);
    }
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        13
    );
    drop(client);
    target.finish();
}
