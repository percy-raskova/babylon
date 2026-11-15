//! Exercise durable physical labor within the existing fourteen-period control.
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::{self, JournalError, MoneyJournalWriter};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use postgres::Client;

#[path = "movement_blocks.rs"]
mod movement_blocks;

#[path = "labor_positions.rs"]
mod labor_positions;

pub(super) fn retention_and_repair(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
) {
    labor_positions::check(owner, observer, writer, campaign);
    cold_window(owner, observer, writer, campaign);
    movement_blocks::check(owner, campaign);
    compare_retained_rows(owner, observer, writer, campaign);
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
    money_journal::prune_money_journal_detail(&mut pruning, campaign, 14)
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

fn compare_retained_rows(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
) {
    let id = campaign.as_uuid();
    check_shared_node_repair(owner, observer, writer, campaign);

    let last: i64 = owner
        .query_one(
            "SELECT max(block_ordinal) FROM babylon_state.labor_movement_block_v1
             WHERE campaign_id=$1 AND resolve_tick=2",
            &[id],
        )
        .expect("retained work movements")
        .get(0);
    let shift = "UPDATE babylon_state.labor_movement_block_v1 SET block_ordinal=$3
                 WHERE campaign_id=$1 AND resolve_tick=2 AND block_ordinal=$2";
    let extra = last.checked_add(1).expect("fixture block fits");
    assert_eq!(
        owner
            .execute(shift, &[id, &last, &extra])
            .expect("replace a required movement with an extra key"),
        1
    );
    assert_eq!(
        writer.publish(observer, campaign, 2),
        Err(JournalError::Projection)
    );
    assert_eq!(
        owner
            .execute(shift, &[id, &extra, &last])
            .expect("restore original movement"),
        1
    );
    assert!(
        !writer
            .publish(observer, campaign, 2)
            .expect("admit restored facts")
            .changed
    );
}

/// A moved nullable scalar, with a valid content key and unchanged counts, must fail idempotent
/// verification. Rebuilding the one period must preserve a neighbor using the original identity.
fn check_shared_node_repair(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
) {
    let id = campaign.as_uuid();
    let selected=owner.query_one("SELECT n.node_ordinal,d.descriptor_sha256,
            (SELECT min(peer.resolve_tick) FROM babylon_state.labor_node_v1 peer WHERE
                peer.campaign_id=n.campaign_id AND peer.descriptor_key=n.descriptor_key AND peer.resolve_tick<>2) AS neighbor
        FROM babylon_state.labor_node_v1 n JOIN babylon_state.labor_node_identity_v1 d USING(campaign_id,descriptor_key) WHERE n.campaign_id=$1 AND n.resolve_tick=2
        AND d.kind IN ('site_stock','household_stock','work','household_work','process','equipment')
        AND EXISTS (SELECT FROM babylon_state.labor_node_v1 peer WHERE peer.campaign_id=n.campaign_id
            AND peer.descriptor_key=n.descriptor_key AND peer.resolve_tick<>2) ORDER BY n.node_ordinal LIMIT 1",
        &[id]).expect("one recurring identity used in two retained periods");
    let ordinal: i64 = selected.get(0);
    let original: Vec<u8> = selected.get(1);
    let neighbor: i64 = selected.get(2);
    let snapshot = |db: &mut Client, tick| -> String {
        db.query_one(
            "SELECT to_jsonb(d)::text FROM babylon_state.labor_node_v1 n
            JOIN babylon_state.labor_node_descriptor_v1 d USING(campaign_id,descriptor_key)
            WHERE n.campaign_id=$1 AND n.resolve_tick=$2 AND d.descriptor_sha256=$3 LIMIT 1",
            &[id, &tick, &original],
        )
        .expect("original typed identity")
        .get(0)
    };
    check_physical_reference(owner, campaign, ordinal, &original);
    let before = snapshot(owner, neighbor);
    let corrupt=owner.query_one("WITH changed AS (
          SELECT d AS physical,jsonb_populate_record(f,jsonb_build_object('catchment_key',
              CASE WHEN f.catchment_key IS NULL THEN 'changed' ELSE NULL END)) AS logical
          FROM babylon_state.labor_node_identity_v1 d JOIN babylon_state.labor_node_descriptor_v1 f USING(campaign_id,descriptor_key)
          WHERE d.campaign_id=$1 AND d.descriptor_sha256=$2
        ), keyed AS (
          SELECT jsonb_populate_record(physical,jsonb_build_object(
              'descriptor_key',(SELECT max(descriptor_key)+1 FROM babylon_state.labor_node_identity_v1 WHERE campaign_id=$1),
              'descriptor_sha256',babylon_state.labor_node_fingerprint_v1(logical),'scope_key',NULL,'scope_revision',NULL,
              'point_revision',NULL,'physical_scope',to_jsonb(logical))) AS body FROM changed
        ), staged AS (
          INSERT INTO babylon_state.labor_node_identity_v1 SELECT (body).* FROM keyed
          ON CONFLICT (campaign_id,descriptor_sha256) DO NOTHING
          RETURNING descriptor_key,descriptor_sha256
        ), resolved AS (
          SELECT descriptor_key,descriptor_sha256 FROM staged UNION ALL
          SELECT d.descriptor_key,d.descriptor_sha256 FROM babylon_state.labor_node_identity_v1 d
          JOIN keyed k ON (d.campaign_id,d.descriptor_sha256)=((k.body).campaign_id,(k.body).descriptor_sha256)
        )
        UPDATE babylon_state.labor_node_block_v1 n SET descriptor_keys[(($3::bigint%256)::integer+1)]=k.descriptor_key FROM resolved k
        WHERE n.campaign_id=$1 AND n.resolve_tick=2 AND n.block_ordinal=$3::bigint/256 RETURNING k.descriptor_sha256",
        &[id,&original,&ordinal]).expect("alter only one nullable source field behind a retained reference");
    assert_ne!(corrupt.get::<_, Vec<u8>>(0), original);
    assert_eq!(
        writer.publish(observer, campaign, 2),
        Err(JournalError::Projection)
    );
    writer
        .rebuild(observer, campaign, 2)
        .expect("repair from authenticated node facts");
    assert_eq!(snapshot(owner, neighbor), before);
    assert_eq!(snapshot(owner, 2), before);
    let restored: Vec<u8> = owner
        .query_one(
            "SELECT d.descriptor_sha256 FROM babylon_state.labor_node_v1 n JOIN babylon_state.labor_node_identity_v1 d USING(campaign_id,descriptor_key)
        WHERE n.campaign_id=$1 AND n.resolve_tick=2 AND n.node_ordinal=$2",
            &[id, &ordinal],
        )
        .expect("same original receipt ordinal")
        .get(0);
    assert_eq!(restored, original);
    let orphan: bool = owner
        .query_one(
            "SELECT EXISTS (SELECT FROM babylon_state.labor_node_identity_v1 d
        WHERE d.campaign_id=$1 AND NOT EXISTS (SELECT FROM babylon_state.labor_node_v1 n
          WHERE (n.campaign_id,n.descriptor_key)=(d.campaign_id,d.descriptor_key)))",
            &[id],
        )
        .expect("membership after recovery and thirteen-period retention")
        .get(0);
    assert!(!orphan);
}

fn check_physical_reference(
    owner: &mut Client,
    campaign: CampaignId,
    ordinal: i64,
    original: &[u8],
) {
    let id = campaign.as_uuid();
    let mut broken = owner.transaction().expect("exercise physical reference");
    broken
        .execute(
            "UPDATE babylon_state.labor_node_block_v1 SET descriptor_keys[(($2::bigint%256)::integer+1)]=
                 (SELECT max(descriptor_key)+1 FROM babylon_state.labor_node_identity_v1 WHERE campaign_id=$1)
             WHERE campaign_id=$1 AND resolve_tick=2 AND block_ordinal=$2::bigint/256",
            &[id, &ordinal],
        )
        .expect("stage missing physical descriptor");
    assert_eq!(
        broken
            .commit()
            .expect_err("deferred link must resolve")
            .code(),
        Some(&postgres::error::SqlState::FOREIGN_KEY_VIOLATION)
    );
    let collision = owner.execute(
        "UPDATE babylon_state.labor_node_identity_v1 SET location_key=coalesce(location_key,'')||'!'
         WHERE campaign_id=$1 AND descriptor_sha256=$2",
        &[id, &original],
    );
    assert_eq!(
        collision
            .expect_err("a physical key cannot authorize changed content")
            .code(),
        Some(&postgres::error::SqlState::CHECK_VIOLATION)
    );
}

/// Full scopes in the national source share the authenticated cash directory and
/// county points. PostgreSQL protects retained identities before another writer
/// can change a parent's typed payload or remove the row.
pub(super) fn national_descriptor_sources(owner: &mut Client, campaign: CampaignId) {
    use postgres::error::SqlState;
    let id = campaign.as_uuid();
    let row = owner
        .query_one(
            "SELECT scope_key,location_key,product_key FROM babylon_state.labor_node_identity_v1
             WHERE campaign_id=$1 AND scope_key IS NOT NULL AND point_revision IS NOT NULL AND product_key IS NOT NULL LIMIT 1",
            &[id],
        )
        .expect("a located national stock uses all three shared parents");
    let account: i32 = row.get(0);
    let point: String = row.get(1);
    let product: i32 = row.get(2);
    let change = owner
        .execute(
            "UPDATE babylon_state.economic_flow_account_v1 SET catchment_key=coalesce(catchment_key,'')||'!'
             WHERE campaign_id=$1 AND account_key=$2",
            &[id, &account],
        )
        .expect_err("a retained scope pins its nullable classification");
    assert_eq!(change.code(), Some(&SqlState::FOREIGN_KEY_VIOLATION));
    let change = owner
        .execute(
            "UPDATE babylon_state.economic_flow_location_v1 SET longitude=longitude + ('0.'||repeat('0',scale(longitude)+1))::numeric
             WHERE campaign_id=$1 AND location_key=$2",
            &[id, &point],
        )
        .expect_err("numeric scale is part of the binary location descriptor");
    assert_eq!(change.code(), Some(&SqlState::FOREIGN_KEY_VIOLATION));
    let remove = owner
        .execute(
            "DELETE FROM babylon_state.economic_flow_location_v1 WHERE campaign_id=$1 AND location_key=$2",
            &[id, &point],
        )
        .expect_err("a retained coordinate pair requires its county point");
    assert_eq!(remove.code(), Some(&SqlState::FOREIGN_KEY_VIOLATION));
    let change = owner
        .execute(
            "UPDATE babylon_state.labor_product_v1 SET unit_id=sha256(unit_id) WHERE campaign_id=$1 AND product_key=$2",
            &[id, &product],
        )
        .expect_err("a retained unit cannot change under its compact key");
    assert_eq!(change.code(), Some(&SqlState::CHECK_VIOLATION));
    let wrong = owner.execute(
        "INSERT INTO babylon_state.labor_node_identity_v1
         SELECT (jsonb_populate_record(d,jsonb_build_object('descriptor_key',(SELECT max(descriptor_key)+1 FROM babylon_state.labor_node_identity_v1 WHERE campaign_id=$1),
             'descriptor_sha256',sha256(d.descriptor_sha256)))).*
         FROM babylon_state.labor_node_identity_v1 d WHERE campaign_id=$1 AND scope_key=$2 LIMIT 1",
        &[id, &account],
    ).expect_err("a newly inserted identity must match the recomputed full descriptor SHA");
    assert_eq!(wrong.code(), Some(&SqlState::CHECK_VIOLATION));
}
