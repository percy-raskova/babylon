//! A concurrent owner commit cannot give one journal period two material snapshots.
use crate::{
    CampaignId, DisposableTarget, DurableMaterialRuntime, MichiganContentPreset, NoTls,
    ObserverEconomyError, ObserverEconomyReader, ObserverVisibility, Uuid,
};
use babylon_persistence::money_journal::{JournalError, MoneyJournalWriter};
use postgres::Transaction;
use std::thread;
use std::time::{Duration, Instant};

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn journal_endpoint_reads_share_one_concurrent_snapshot() {
    let mut target = DisposableTarget::create();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x739a));
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("authored Michigan foundation");
    let mut runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation)
        .expect("create isolated campaign");
    crate::provision_observer_role(&target.writer).expect("full observer role");
    let observer = ObserverEconomyReader::connect(
        &target.login("babylon_observer", "snapshots"),
        ObserverVisibility::FullObserver,
    )
    .expect("bounded observer");
    let writer = MoneyJournalWriter::connect(&target.writer).expect("bounded journal writer");
    for period in 1..=2 {
        crate::advance_material_period(&mut runtime);
        assert!(
            writer
                .publish(&observer, campaign, period)
                .expect("initial period")
                .changed
        );
    }
    let mut owner = target
        .writer
        .connect(NoTls)
        .expect("disposable campaign owner");
    let mut guard = owner.transaction().expect("concurrent perturbation");
    // The prior journal checkpoint view never reads campaign. The canonical
    // foundation read does, after the repeatable-read transaction takes its snapshot.
    guard
        .batch_execute("LOCK TABLE babylon_state.campaign IN ACCESS EXCLUSIVE MODE")
        .expect("pause the canonical reader before it can export its snapshot");
    let original: Vec<u8> = guard
        .query_one(
            "SELECT receipt_storage_bytes FROM babylon_state.material_tick_v3
         WHERE campaign_id=$1 AND resolve_tick=2",
            &[campaign.as_uuid()],
        )
        .expect("original receipt package")
        .get(0);
    let (reached, concurrent) = thread::scope(|scope| {
        let publication = scope.spawn(|| writer.publish(&observer, campaign, 2));
        let reached = reader_has_snapshot(&mut guard, || publication.is_finished());
        if reached {
            let damaged: &[u8] = &[0];
            set_receipt(&mut guard, campaign, damaged);
            guard
                .commit()
                .expect("commit while original observer snapshot is live");
        } else {
            guard.rollback().expect("release the reader on failure");
        }
        (reached, publication.join().expect("publisher completes"))
    });
    assert!(
        reached,
        "the authenticated reader waited with an assigned snapshot"
    );
    let fresh = writer.publish(&observer, campaign, 2);
    let mut restore = owner.transaction().expect("restore original bytes");
    set_receipt(&mut restore, campaign, &original);
    restore
        .commit()
        .expect("restore disposable campaign source");
    assert!(
        !concurrent
            .expect("both endpoints see the original complete close")
            .changed
    );
    assert_eq!(
        fresh,
        Err(JournalError::Observer(
            ObserverEconomyError::InvalidProjection
        ))
    );
    assert!(
        !writer
            .publish(&observer, campaign, 2)
            .expect("exact source restoration")
            .changed
    );
}

fn reader_has_snapshot(guard: &mut Transaction<'_>, finished: impl Fn() -> bool) -> bool {
    let until = Instant::now() + Duration::from_secs(25);
    loop {
        // A catalog statistics snapshot otherwise persists until the owner's
        // transaction ends. Wait for the real lock request and assigned xmin.
        guard
            .query_one("SELECT pg_catalog.pg_stat_clear_snapshot()", &[])
            .expect("refresh backend activity");
        let blocked: bool = guard
            .query_one(
                "SELECT EXISTS (
                 SELECT 1 FROM pg_catalog.pg_locks l
                 JOIN pg_catalog.pg_stat_activity a ON a.pid = l.pid
                 WHERE l.relation = 'babylon_state.campaign'::regclass
                   AND NOT l.granted AND l.mode = 'AccessShareLock'
                   AND a.datname = current_database() AND a.backend_xmin IS NOT NULL
                   AND pg_catalog.pg_backend_pid() = ANY(pg_catalog.pg_blocking_pids(l.pid))
             )",
                &[],
            )
            .expect("read real snapshot and lock state")
            .get(0);
        if blocked || finished() || Instant::now() >= until {
            return blocked;
        }
        thread::sleep(Duration::from_millis(10));
    }
}

fn set_receipt(tx: &mut Transaction<'_>, campaign: CampaignId, bytes: &[u8]) {
    assert_eq!(
        tx.execute(
            "UPDATE babylon_state.material_tick_v3 SET receipt_storage_bytes=$2
         WHERE campaign_id=$1 AND resolve_tick=2",
            &[campaign.as_uuid(), &bytes],
        )
        .expect("replace one disposable receipt package"),
        1
    );
}
