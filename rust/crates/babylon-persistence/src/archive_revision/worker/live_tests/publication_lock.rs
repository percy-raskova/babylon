//! Archive deletion protection must coexist with authoritative tick publication.

use super::*;
use crate::archive_revision::{publication, tick_knowledge};
use crate::{ArchiveMaterializeDisposition, ArchiveMaterializeMode};
use babylon_tick::material_replay::IdentifiedMaterialTick;
use postgres::{error::SqlState, IsolationLevel, Transaction};
use std::sync::mpsc;

// The real publication has finished its writes but retains every transaction
// lock until this work returns. Read its staged revision while waiting so the
// normal five-second idle timeout cannot accidentally release the tested lock.
// There is no sleep, elapsed-time assertion, or timeout override.
fn with_publication_held<T: Send>(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    staged_digest: &[u8],
    work: impl FnOnce() -> T + Send,
) -> T {
    std::thread::scope(|scope| {
        let (completed, completion) = mpsc::sync_channel(1);
        let task = scope.spawn(move || {
            let result = work();
            let _ = completed.send(());
            result
        });
        loop {
            match completion.try_recv() {
                Ok(()) | Err(mpsc::TryRecvError::Disconnected) => break,
                Err(mpsc::TryRecvError::Empty) => {
                    let retained: Vec<u8> = tx
                        .query_one(
                            "SELECT revision_sha256 FROM babylon_meta.archive_page_revision_v2 \
                             WHERE campaign_id=$1 AND effective_tick=1",
                            &[campaign.as_uuid()],
                        )
                        .expect("publication retains its staged revision and campaign lock")
                        .get(0);
                    assert_eq!(retained, staged_digest);
                }
            }
        }
        task.join().expect("concurrent operation did not panic")
    })
}

fn commit_authoritative_tick(
    target: &LiveWorkerTarget,
) -> Result<(IdentifiedMaterialTick, IdentifiedMaterialTick), material_runtime::MaterialRuntimeError>
{
    let campaign = target.campaign_id;
    let mut runtime = DurableMaterialRuntime::open(
        &target.config,
        campaign,
        current_material::foundation().digest(),
    )?;
    let actions = OrderedPracticeActionBatch::empty(
        runtime.session().graph_session().session_identity().clone(),
        2,
    )
    .expect("second exact action batch");
    let expected = *runtime.session().prepare_advance(&actions)?.identity();
    let committed = runtime.advance_and_commit(&mut CollectingSink::default(), &actions)?;
    assert_eq!(committed.tick_content_hash(), expected.tick_content_hash());
    assert_eq!(
        runtime.session().current_world_hash()?,
        expected.result_world_hash()
    );
    let actions = OrderedPracticeActionBatch::empty(
        runtime.session().graph_session().session_identity().clone(),
        3,
    )
    .expect("third exact action batch");
    let next_identity = *runtime.session().prepare_advance(&actions)?.identity();
    Ok((expected, next_identity))
}

fn assert_restart_and_retained_evidence(
    target: &LiveWorkerTarget,
    scope: &ArchiveReadScope,
    committed: &IdentifiedMaterialTick,
    next_identity: &IdentifiedMaterialTick,
    page_markdown: &str,
    revision_digest: &[u8],
) {
    let campaign = target.campaign_id;
    let original_hash = scope.tick_content_hash().expect("first committed hash");
    let runtime = DurableMaterialRuntime::open(
        &target.config,
        campaign,
        current_material::foundation().digest(),
    )
    .expect("restart authenticates the concurrent commit");
    assert_eq!(runtime.session().completed_tick(), 2);
    assert_eq!(
        runtime.session().current_world_hash().unwrap(),
        committed.result_world_hash()
    );
    let actions = OrderedPracticeActionBatch::empty(
        runtime.session().graph_session().session_identity().clone(),
        3,
    )
    .expect("restarted third action batch");
    assert_eq!(
        *runtime
            .session()
            .prepare_advance(&actions)
            .unwrap()
            .identity(),
        *next_identity
    );
    drop(runtime);
    assert_eq!(&scope_at(&target.config, campaign, 1), scope);
    assert_eq!(receipt_consumption_count(&target.config, campaign), 1);
    let mut observer = target
        .config
        .connect(NoTls)
        .expect("committed evidence reader");
    let rows = observer
        .query(
            "SELECT marker.resolve_tick, marker.tick_content_hash, dirty.tick_content_hash \
         FROM babylon_state.tick_commit marker JOIN babylon_state.archive_dirty_receipt_v1 dirty \
         USING(campaign_id,resolve_tick) WHERE campaign_id=$1 ORDER BY resolve_tick",
            &[campaign.as_uuid()],
        )
        .expect("both real committed dirty receipts survive");
    assert_eq!(rows.len(), 2);
    for (row, (tick, hash)) in rows.iter().zip([
        (1_i64, original_hash),
        (2, *committed.tick_content_hash().as_bytes()),
    ]) {
        assert_eq!(row.get::<_, i64>(0), tick);
        assert_eq!(row.get::<_, Vec<u8>>(1), hash);
        assert_eq!(row.get::<_, Vec<u8>>(2), hash);
    }
    let retained: Vec<u8> = observer
        .query_one(
            "SELECT revision_sha256 FROM babylon_meta.archive_page_revision_v2 \
         WHERE campaign_id=$1 AND effective_tick=1",
            &[campaign.as_uuid()],
        )
        .expect("committed original revision")
        .get(0);
    assert_eq!(retained, revision_digest);
    drop(observer);
    with_reader(&target.config, |reader| {
        let read = reader
            .dossier_as_of(
                scope,
                &stub_subject_spec(1).page_ref,
                &ArchiveDossierBounds::default(),
            )
            .expect("original dated Archive observation");
        let ArchiveDossierState::Ready { page: retained, .. } = read.state else {
            panic!("concurrent tick cannot invalidate the captured publication");
        };
        assert_eq!(&retained.content_source, scope);
        assert_eq!(retained.markdown, page_markdown);
    });
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_publication_protects_deletion_without_blocking_authoritative_tick() {
    let target = LiveWorkerTarget::create(
        "publicationlock",
        0x2200_0000_0000_0000_0000_0000_0000_00d5,
        1,
    );
    let campaign = target.campaign_id;
    let scope = scope_at(&target.config, campaign, 1);
    let original_hash = scope.tick_content_hash().expect("first committed hash");
    let receipt = PendingArchiveReceipt::try_new(1, original_hash).expect("first receipt");
    let store = SemanticArchiveStore::new(&target.config);
    let mut client = store
        .connect("concurrent publication proof")
        .expect("Archive connection");
    let (committed, next_identity, page, revision_digest) =
        publication::with_campaign_lock(&mut client, campaign, |client| {
            let mut tx = client
                .build_transaction()
                .isolation_level(IsolationLevel::Serializable)
                .read_only(false)
                .start()
                .expect("actual Archive transaction isolation");
            crate::current_schema::require_current_schema(&mut tx)
                .expect("current schema before publication");
            let knowledge = tick_knowledge::pin(&mut tx, &scope).expect("receipt-pinned knowledge");
            let outcome = StubPageProducer
                .produce(*campaign.as_uuid(), &receipt, &knowledge, 1)
                .expect("one real Archive page");
            let report = publication::publish(
                &mut tx,
                campaign,
                &receipt,
                outcome.batch(),
                ArchiveMaterializeMode::Consume,
                &knowledge,
            )
            .expect("actual publication acquires the campaign lock");
            assert_eq!(report.disposition(), ArchiveMaterializeDisposition::Applied);
            let page = report.pages()[0].page().clone();
            let revision_digest: Vec<u8> = tx
                .query_one(
                    "SELECT revision_sha256 FROM babylon_meta.archive_page_revision_v2 \
                     WHERE campaign_id=$1 AND effective_tick=1",
                    &[campaign.as_uuid()],
                )
                .expect("staged immutable revision")
                .get(0);

            let (committed, next_identity) =
                with_publication_held(&mut tx, campaign, &revision_digest, || {
                    commit_authoritative_tick(&target)
                })
                .expect("authoritative tick commits while the Archive publication lock is held");

            let deletion = with_publication_held(&mut tx, campaign, &revision_digest, || {
                let bounded = material_runtime::bounded_material_writer_config(&target.config)
                    .expect("unchanged bounded writer settings");
                let mut writer = bounded.connect(NoTls).expect("campaign deletion writer");
                writer.execute(
                    "DELETE FROM babylon_meta.campaign WHERE campaign_id=$1",
                    &[campaign.as_uuid()],
                )
            })
            .expect_err("publication still protects campaign deletion");
            assert_eq!(deletion.code(), Some(&SqlState::LOCK_NOT_AVAILABLE));
            assert_eq!(
                tick_knowledge::load(&mut tx, &scope).expect("unchanged knowledge"),
                knowledge
            );
            tx.commit()
                .expect("Archive commits its original pinned revision");
            Ok((committed, next_identity, page, revision_digest))
        })
        .expect("ordered Archive publication completes");
    drop(client);

    assert_restart_and_retained_evidence(
        &target,
        &scope,
        &committed,
        &next_identity,
        page.markdown(),
        &revision_digest,
    );
    target.finish();
}
