//! Exercise publication failure after staging nonzero cash facts in an owned database.
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::material_runtime::DurableMaterialRuntime;
use babylon_persistence::money_journal::{JournalError, MoneyJournalWriter};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use babylon_tick::material_replay::IdentifiedMaterialTick;
use postgres::{Client, Config, Transaction};
use std::thread;
use std::time::{Duration, Instant};

pub(super) fn next_without_projection(runtime: &DurableMaterialRuntime) -> IdentifiedMaterialTick {
    let actions = runtime.next_action_batch().expect("same ordinary actions");
    *runtime
        .session()
        .prepare_advance(&actions)
        .expect("unpublished analytics control")
        .identity()
}

pub(super) fn commit_after_projection(
    config: &Config,
    campaign: CampaignId,
    expected: &IdentifiedMaterialTick,
) {
    let mut reopened = DurableMaterialRuntime::open(config, campaign, expected.foundation_digest())
        .expect("reopen the recorded campaign with period-one analytics installed");
    let actions = reopened
        .next_action_batch()
        .expect("ordinary actions after reopening");
    let actual = reopened
        .advance_and_commit(&mut CollectingSink::default(), &actions)
        .expect("commit the next period with analytics present");
    assert_eq!(
        &actual, expected,
        "foundation, graph, receipts, and world identities must match"
    );
}

// Wait for this owner's other connection to request a write on the locked summary
// table. A process in another database or one blocked by a different lock is ineligible.
fn cancel_blocked_summary_insert(lock: &mut Transaction<'_>) -> bool {
    let deadline = Instant::now() + Duration::from_secs(45);
    while Instant::now() < deadline {
        let cancelled = lock.query_opt(
            "SELECT pg_catalog.pg_cancel_backend(l.pid)
               FROM pg_catalog.pg_locks l
              WHERE l.locktype = 'relation' AND NOT l.granted AND l.mode = 'RowExclusiveLock'
                AND l.relation = 'babylon_state.money_movement_total_v1'::regclass
                AND l.database = (SELECT oid FROM pg_catalog.pg_database WHERE datname = current_database())
                AND pg_catalog.pg_backend_pid() = ANY(pg_catalog.pg_blocking_pids(l.pid))",
            &[],
        ).expect("inspect only the controlled publication lock");
        if let Some(row) = cancelled {
            return row.get(0);
        }
        thread::sleep(Duration::from_millis(20));
    }
    false
}

pub(super) fn interrupt_and_retry(
    owner: &mut Client,
    writer: &MoneyJournalWriter,
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
) {
    let mut lock = owner.transaction().expect("start interruption control");
    lock.batch_execute("LOCK TABLE babylon_state.money_movement_total_v1 IN SHARE MODE")
        .expect("block the summary after the detail insert");
    let (cancelled, publication) = thread::scope(|scope| {
        let attempt = scope.spawn(|| writer.publish(observer, campaign, 2));
        let cancelled = cancel_blocked_summary_insert(&mut lock);
        if !cancelled {
            lock.rollback().expect("release the controlled lock");
        }
        (cancelled, attempt.join().expect("publisher exits"))
    });
    assert!(cancelled, "observed the publisher staging period two");
    assert_eq!(publication, Err(JournalError::Database));
    let counts = owner.query_one(
        "SELECT (SELECT count(*) FROM babylon_state.money_movement_v1 WHERE campaign_id=$1 AND resolve_tick=2),
                (SELECT count(*) FROM babylon_state.money_movement_total_v1 WHERE campaign_id=$1 AND resolve_tick=2),
                (SELECT count(*) FROM babylon_state.money_journal_period_v1 WHERE campaign_id=$1 AND resolve_tick=2),
                (SELECT count(*) FROM babylon_state.economic_payment_v1 WHERE campaign_id=$1 AND resolve_tick=2),
                (SELECT count(*) FROM babylon_state.company_statement_balance_v1 WHERE campaign_id=$1 AND resolve_tick=2),
                (SELECT count(*) FROM babylon_state.company_accounting_checkpoint_v1 WHERE campaign_id=$1 AND resolve_tick=2)",
        &[campaign.as_uuid()],
    ).expect("inspect rolled-back rows from another connection");
    for column in 0..6 {
        assert_eq!(
            counts.get::<_, i64>(column),
            0,
            "no partial publication is visible"
        );
    }
    assert_eq!(
        observer.money_movements(campaign, 2),
        Err(JournalError::CoverageAbsent)
    );
    let retry = writer
        .publish(observer, campaign, 2)
        .expect("retry interrupted period");
    let source = observer
        .committed_material_receipts(campaign, 2)
        .expect("independent retry source");
    assert!(retry.changed && retry.movement_count > 0);
    assert_eq!(
        usize::try_from(retry.movement_count).expect("bounded receipt count"),
        source.receipts.money_transfers.len()
    );
}
