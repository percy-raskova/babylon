//! Exercise durable physical labor within the existing fourteen-period control.
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::{
    JournalError, MoneyJournalWriter, MONEY_DETAIL_RETENTION_SQL,
};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use postgres::Client;

pub(super) fn retention_and_repair(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
) {
    cold_window(owner, observer, writer, campaign);
    let id = campaign.as_uuid();
    let source = observer
        .recorded_labor_window(campaign, 1, 1)
        .expect("first period source")
        .next()
        .expect("requested close")
        .expect("authenticated labor");
    let coverage=owner.query_one("SELECT movement_count,direct_micro_hours::text,detail_retained FROM public.v_observer_labor_period_v1 WHERE campaign_id=$1 AND resolve_tick=1",&[id]).expect("historical coverage");
    assert_eq!(
        coverage.get::<_, i64>(0),
        i64::try_from(source.labor.edges.len()).expect("edge count")
    );
    assert_eq!(
        coverage.get::<_, String>(1),
        source.labor.direct_micro_hours.to_string()
    );
    assert!(!coverage.get::<_, bool>(2));
    assert!(
        source.labor.direct_micro_hours > 0,
        "physical productive hours survive without a cash movement"
    );
    let detail=owner.query_one("SELECT (SELECT count(*) FROM babylon_state.labor_movement_v1 WHERE campaign_id=$1 AND resolve_tick=1),(SELECT count(*) FROM public.v_observer_labor_period_v1 WHERE campaign_id=$1),(SELECT count(*) FROM public.v_observer_labor_checkpoint_v1 WHERE campaign_id=$1)",&[id]).expect("retention and coverage");
    assert_eq!(
        (
            detail.get::<_, i64>(0),
            detail.get::<_, i64>(1),
            detail.get::<_, i64>(2)
        ),
        (0, 14, 13)
    );
    // A cash/physical publication cannot commit with a missing labor coverage record.
    let mut tx = owner.transaction().expect("broken publication");
    tx.execute(
        "DELETE FROM babylon_state.labor_period_v1 WHERE campaign_id=$1 AND resolve_tick=14",
        &[id],
    )
    .expect("temporarily remove labor");
    let error = tx
        .commit()
        .expect_err("deferred coverage reference rejects partial publication");
    assert_eq!(
        error.code().map(postgres::error::SqlState::code),
        Some("23503")
    );
    writer
        .publish(observer, campaign, 14)
        .expect("prior complete reporting survived that rollback");
    // A corrupt mutable cache can be discarded independently of immutable source evidence.
    owner.execute("WITH original AS (SELECT set_byte(checkpoint_bytes,0,get_byte(checkpoint_bytes,0) # 1) AS bad FROM babylon_state.labor_checkpoint_v1 WHERE campaign_id=$1 AND resolve_tick=13) UPDATE babylon_state.labor_checkpoint_v1 c SET checkpoint_bytes=o.bad,sha256=pg_catalog.sha256(o.bad) FROM original o WHERE c.campaign_id=$1 AND c.resolve_tick=13", &[id]).expect("damage one disposable cache");
    assert!(matches!(
        writer.publish(observer, campaign, 13),
        Err(JournalError::Projection)
    ));
    writer
        .publish(observer, campaign, 14)
        .expect("skip damaged anchor and reproduce the following exact facts");
    writer
        .rebuild(observer, campaign, 13)
        .expect("repair cache from its authenticated source");
    let mut pruning = owner
        .transaction()
        .expect("exercise expired sparse checkpoint");
    pruning
        .execute(MONEY_DETAIL_RETENTION_SQL, &[id, &14_i64])
        .expect("old detail cutoff");
    let kept:Vec<i64>=pruning.query("SELECT resolve_tick FROM public.v_observer_labor_checkpoint_v1 WHERE campaign_id=$1 ORDER BY resolve_tick",&[id]).expect("sparse checkpoints").iter().map(|row|row.get(0)).collect();
    assert_eq!(kept, [13]);
    pruning
        .rollback()
        .expect("retain the existing suite's configured cutoff");
}

fn cold_window(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
) {
    let mut full = observer
        .recorded_labor_window(campaign, 1, 4)
        .expect("full replay");
    let result = full
        .by_ref()
        .last()
        .expect("close four")
        .expect("source from foundation");
    let expected = serde_json::to_vec(&result).expect("complete canonical report");
    assert_eq!(full.restored_checkpoint_period(), None);
    let read = |anchor| {
        let mut cold = observer
            .recorded_labor_window(campaign, 4, 4)
            .expect("observer cold window");
        let result = cold
            .next()
            .expect("one requested close")
            .expect("committed source");
        assert_eq!(cold.restored_checkpoint_period(), Some(anchor));
        assert_eq!(
            serde_json::to_vec(&result).expect("complete restored report"),
            expected
        );
        assert!(cold.next().is_none());
    };
    read(3);
    // Supply period two's authentic cache as period three's, with matching local hashes.
    // Only comparison to the independently authenticated boundary can reject this substitution.
    let id = campaign.as_uuid();
    let bad = owner.query_one("SELECT checkpoint_bytes,sha256 FROM babylon_state.labor_checkpoint_v1 WHERE campaign_id=$1 AND resolve_tick=2", &[id]).expect("older authentic cache");
    let bytes: Vec<u8> = bad.get(0);
    let hash: Vec<u8> = bad.get(1);
    let mut tx = owner
        .transaction()
        .expect("exercise incorrect cache binding");
    tx.execute("UPDATE babylon_state.labor_checkpoint_v1 SET checkpoint_bytes=$2,sha256=$3 WHERE campaign_id=$1 AND resolve_tick=3",&[id,&bytes,&hash]).expect("move cache");
    tx.execute("UPDATE babylon_state.labor_period_v1 SET checkpoint_sha256=$2 WHERE campaign_id=$1 AND resolve_tick=3",&[id,&hash]).expect("bind wrong cache");
    tx.commit()
        .expect("owner deliberately replaced a derived cache");
    read(2);
    writer
        .rebuild(observer, campaign, 3)
        .expect("restore disposable cache from unchanged source");
}
