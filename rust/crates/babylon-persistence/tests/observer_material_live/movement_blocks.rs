//! Physical movement blocks must preserve referential behavior through retention.
use babylon_persistence::identity::CampaignId;
use postgres::error::SqlState;
use postgres::Client;

pub(super) fn check(owner: &mut Client, campaign: CampaignId) {
    let id = campaign.as_uuid();
    let labor = "babylon_state.labor_movement_block_v1";
    let money = "babylon_state.money_movement_block_v1";
    let scope = "WHERE campaign_id=$1 AND resolve_tick=2 AND block_ordinal=0";
    for statement in [
        format!("UPDATE {labor} SET source_node[1]=(SELECT max(last_ordinal)+1 FROM babylon_state.labor_node_block_v1 WHERE campaign_id=$1 AND resolve_tick=2) {scope}"),
        format!("UPDATE {labor} SET resolve_tick=9223372036854775807 {scope}"),
        format!("UPDATE {money} SET payer_key[1]=-1 {scope}"),
        "DELETE FROM babylon_state.labor_movement_roster_v1 WHERE campaign_id=$1 AND resolve_tick=2".to_owned(),
        "DELETE FROM babylon_state.money_movement_account_v1 WHERE campaign_id=$1 AND resolve_tick=2".to_owned(),
        "DELETE FROM babylon_state.labor_node_block_v1 WHERE campaign_id=$1 AND resolve_tick=2".to_owned(),
    ] {
        let error = owner.execute(&statement, &[id]).expect_err("retained endpoint must exist in the same scope");
        assert_eq!(error.code(), Some(&SqlState::FOREIGN_KEY_VIOLATION), "{statement}");
    }
    for statement in [
        format!("UPDATE {labor} SET slots[2]=slots[1] {scope}"),
        format!("UPDATE {labor} SET unknown_opening[1]=NULL {scope}"),
        format!("UPDATE {money} SET reference_id=ARRAY[]::bytea[] {scope}"),
        format!(
            "UPDATE {money} SET amount_micros[1]=170141183460469231731687303715884105728 {scope}"
        ),
    ] {
        let error = owner
            .execute(&statement, &[id])
            .expect_err("a malformed block cannot commit");
        assert_eq!(
            error.code(),
            Some(&SqlState::CHECK_VIOLATION),
            "{statement}"
        );
    }
    let retired = owner.query_one(
        "SELECT EXISTS(SELECT FROM babylon_state.labor_movement_roster_v1 WHERE campaign_id=$1 AND resolve_tick=1)
             OR EXISTS(SELECT FROM babylon_state.money_movement_account_v1 WHERE campaign_id=$1 AND resolve_tick=1)", &[id])
        .expect("retired movement storage");
    assert!(!retired.get::<_, bool>(0));
}
