//! Physical movement references must reject invalid writes and retire with their blocks.
use babylon_persistence::identity::CampaignId;
use postgres::error::SqlState;
use postgres::types::ToSql;
use postgres::Client;

const LABOR: &str = "babylon_state.labor_movement_block_v1";
const MONEY: &str = "babylon_state.money_movement_block_v1";

fn refuse(owner: &mut Client, statement: &str, params: &[&(dyn ToSql + Sync)], code: &SqlState) {
    match owner.execute(statement, params) {
        Ok(changed) => panic!("expected {code:?} from {statement}, changed {changed} rows"),
        Err(error) => assert_eq!(error.code(), Some(code), "{statement}: {error}"),
    }
}

pub(super) fn retained_labor(owner: &mut Client, campaign: CampaignId) {
    let id = campaign.as_uuid();
    let selected = owner.query_one(
        &format!("SELECT block_ordinal, source_node[1]/256 AS parent FROM {LABOR}
          WHERE campaign_id=$1 AND resolve_tick=2 AND cardinality(slots)>=2 ORDER BY block_ordinal LIMIT 1"),
        &[id],
    ).expect("retained Michigan labor movements with at least two slots");
    let block: i64 = selected.get("block_ordinal");
    let parent: i64 = selected.get("parent");
    let scope = "WHERE campaign_id=$1 AND resolve_tick=2 AND block_ordinal=$2";
    for change in [
        "source_node[1]=(SELECT max(last_ordinal)+1 FROM babylon_state.labor_node_block_v1 WHERE campaign_id=$1 AND resolve_tick=2)",
        "resolve_tick=9223372036854775807",
    ] {
        refuse(owner, &format!("UPDATE {LABOR} SET {change} {scope}"), &[id, &block], &SqlState::FOREIGN_KEY_VIOLATION);
    }
    for table in ["labor_movement_roster_v1", "labor_node_block_v1"] {
        refuse(
            owner,
            &format!("DELETE FROM babylon_state.{table} {scope}"),
            &[id, &parent],
            &SqlState::FOREIGN_KEY_VIOLATION,
        );
    }
    for change in ["slots[2]=slots[1]", "unknown_opening[1]=NULL"] {
        refuse(
            owner,
            &format!("UPDATE {LABOR} SET {change} {scope}"),
            &[id, &block],
            &SqlState::CHECK_VIOLATION,
        );
    }
}

pub(super) fn retained_money(owner: &mut Client, campaign: CampaignId) {
    let id = campaign.as_uuid();
    let selected = owner
        .query_one(
            &format!(
                "SELECT block_ordinal, p.i, payer_key[p.i] AS payer FROM {MONEY}
            CROSS JOIN LATERAL generate_subscripts(payer_key,1) p(i)
            WHERE campaign_id=$1 AND resolve_tick=1 AND payer_key[p.i] IS NOT NULL
            ORDER BY block_ordinal,p.i LIMIT 1"
            ),
            &[id],
        )
        .expect("retained national transfer with a recorded payer");
    let block: i64 = selected.get("block_ordinal");
    let index: i32 = selected.get("i");
    let payer: i32 = selected.get("payer");
    let scope = "WHERE campaign_id=$1 AND resolve_tick=1 AND block_ordinal=$2";
    refuse(
        owner,
        &format!("UPDATE {MONEY} SET payer_key[$3]=-1 {scope}"),
        &[id, &block, &index],
        &SqlState::FOREIGN_KEY_VIOLATION,
    );
    refuse(owner, "DELETE FROM babylon_state.money_movement_account_v1 WHERE campaign_id=$1 AND resolve_tick=1 AND account_key=$2", &[id, &payer], &SqlState::FOREIGN_KEY_VIOLATION);
    for change in [
        "reference_id=ARRAY[]::bytea[]",
        "amount_micros[1]=170141183460469231731687303715884105728",
    ] {
        refuse(
            owner,
            &format!("UPDATE {MONEY} SET {change} {scope}"),
            &[id, &block],
            &SqlState::CHECK_VIOLATION,
        );
    }
}

pub(super) fn retired(owner: &mut Client, campaign: CampaignId) {
    for table in [
        "labor_movement_roster_v1",
        "money_movement_account_v1",
        "labor_movement_block_v1",
        "money_movement_block_v1",
    ] {
        let exists: bool = owner.query_one(
            &format!("SELECT EXISTS(SELECT FROM babylon_state.{table} WHERE campaign_id=$1 AND resolve_tick=1)"),
            &[campaign.as_uuid()],
        ).expect("inspect expired movement storage").get(0);
        assert!(!exists, "expired {table} still holds a period-one row");
    }
}
