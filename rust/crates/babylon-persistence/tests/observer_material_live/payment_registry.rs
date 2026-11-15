//! A scoped rebuild releases unused custody references while neighboring periods retain theirs.
use super::{CampaignId, Client};
use postgres::error::SqlState;
use postgres::GenericClient;

const BLOCK_SLOT: &str = "
    SELECT b.block_ordinal,i,b.payer_key[i]
    FROM babylon_state.money_movement_block_v1 b
    CROSS JOIN LATERAL generate_subscripts(b.payer_key,1) AS slot(i)
    WHERE b.campaign_id=$1 AND b.resolve_tick=$2 AND b.payer_key[i] IS NOT NULL
    ORDER BY b.block_ordinal,i LIMIT 1";
const CHANGE_PAYER: &str = "
    UPDATE babylon_state.money_movement_block_v1 SET payer_key[$4]=$5
    WHERE campaign_id=$1 AND resolve_tick=$2 AND block_ordinal=$3";

pub(super) struct Registry {
    surplus: i32,
    periods: Vec<Vec<u8>>,
}

fn periods(owner: &mut Client, campaign: CampaignId) -> Vec<Vec<u8>> {
    let sql = "SELECT sha256(record_send(p) ||
            (SELECT string_agg(sha256(record_send(b)),''::bytea ORDER BY block_ordinal)
             FROM babylon_state.money_movement_block_v1 b WHERE (b.campaign_id,b.resolve_tick)=(p.campaign_id,p.resolve_tick)) ||
            (SELECT string_agg(sha256(record_send(t)),''::bytea ORDER BY purpose)
             FROM babylon_state.money_movement_total_v1 t WHERE (t.campaign_id,t.resolve_tick)=(p.campaign_id,p.resolve_tick)))
        FROM babylon_state.money_journal_period_v1 p WHERE campaign_id=$1 AND resolve_tick IN (1,2) ORDER BY resolve_tick";
    let rows = owner
        .query(sql, &[campaign.as_uuid()])
        .expect("read the two complete period bindings, movements and totals");
    assert_eq!(rows.len(), 2);
    rows.into_iter().map(|r| r.get(0)).collect()
}

fn change_one(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    extra: i32,
) -> (i64, i32, i32) {
    let row = client
        .query_one(BLOCK_SLOT, &[campaign.as_uuid(), &tick])
        .expect("a real cash payer");
    let (block, slot, original) = (
        row.get::<_, i64>(0),
        row.get::<_, i32>(1),
        row.get::<_, i32>(2),
    );
    assert_eq!(
        client
            .execute(
                CHANGE_PAYER,
                &[campaign.as_uuid(), &tick, &block, &slot, &extra]
            )
            .expect("add a valid referenced account to the selected custody block"),
        1
    );
    (block, slot, original)
}

pub(super) fn seed(owner: &mut Client, campaign: CampaignId) -> Registry {
    let periods = periods(owner, campaign);
    let insert = "INSERT INTO babylon_state.economic_flow_account_v1
            (campaign_id,account_key,foundation_sha256,account_kind,account_id)
        SELECT f.campaign_id,(SELECT max(a.account_key)+1 FROM babylon_state.economic_flow_account_v1 a
              WHERE a.campaign_id=f.campaign_id), f.foundation_sha256,'organization_cash',sha256('surplus custody fixture'::bytea)
        FROM babylon_state.material_campaign_foundation_v3 f WHERE f.campaign_id=$1 RETURNING account_key";
    let surplus: i32 = owner
        .query_one(insert, &[campaign.as_uuid()])
        .expect("one extra valid national account")
        .get(0);
    let (block, slot, payer) = change_one(owner, campaign, 2, surplus);
    assert_eq!(
        owner
            .execute(
                CHANGE_PAYER,
                &[campaign.as_uuid(), &2_i64, &block, &slot, &payer]
            )
            .expect("restore the original posted economic payer"),
        1
    );
    let membership = "SELECT count(*) FROM babylon_state.money_movement_account_v1
        WHERE campaign_id=$1 AND account_key=$2 AND resolve_tick=2";
    let row = owner
        .query_one(membership, &[campaign.as_uuid(), &surplus])
        .expect("read stale selected-period reference");
    assert_eq!(row.get::<_, i64>(0), 1);
    let mut probe = owner
        .transaction()
        .expect("rollback-only neighboring-period control");
    let withdraw = "DELETE FROM babylon_state.money_movement_account_v1
        WHERE campaign_id=$1 AND account_key=$2 AND resolve_tick=2";
    assert_eq!(
        probe
            .execute(withdraw, &[campaign.as_uuid(), &surplus])
            .expect("selected period no longer uses the account"),
        1
    );
    change_one(&mut probe, campaign, 1, surplus);
    let delete = "DELETE FROM babylon_state.economic_flow_account_v1 WHERE campaign_id=$1 AND account_key=$2";
    let error = probe
        .execute(delete, &[campaign.as_uuid(), &surplus])
        .expect_err("a different period still actively references the account");
    assert_eq!(error.code(), Some(&SqlState::FOREIGN_KEY_VIOLATION));
    probe
        .rollback()
        .expect("restore unaffected P1 custody and P2 stale membership");
    Registry { surplus, periods }
}

impl Registry {
    pub(super) fn check_repair(self, owner: &mut Client, campaign: CampaignId) {
        assert_eq!(periods(owner, campaign), self.periods);
        let row=owner.query_one("SELECT NOT EXISTS (SELECT FROM babylon_state.economic_flow_account_v1 WHERE campaign_id=$1 AND account_key=$2)
            AND NOT EXISTS (SELECT FROM babylon_state.money_movement_account_v1 WHERE campaign_id=$1 AND account_key=$2)",
            &[campaign.as_uuid(), &self.surplus]).expect("check repaired foundation directory and membership");
        assert!(row.get::<_, bool>(0));
    }
}
