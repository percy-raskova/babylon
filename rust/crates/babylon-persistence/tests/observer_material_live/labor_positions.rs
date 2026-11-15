//! Paired physical rows project the original two logical endpoint disclosures.
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::{JournalError, MoneyJournalWriter};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use postgres::error::SqlState;
use postgres::types::ToSql;
use postgres::{Client, GenericClient};

const TABLE: &str = "babylon_state.labor_node_v1";
const VIEW: &str = "public.v_observer_labor_position_v1";

pub(super) fn check(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
) {
    let id = campaign.as_uuid();
    let projected = owner
        .query_one(
            "SELECT position_count, (SELECT count(*) FROM public.v_observer_labor_position_v1
             WHERE campaign_id=$1 AND resolve_tick=2)
         FROM public.v_observer_labor_period_v1 WHERE campaign_id=$1 AND resolve_tick=2",
            &[id],
        )
        .expect("actual logical period coverage");
    let endpoints: i64 = projected.get(0);
    assert_eq!(endpoints, projected.get::<_, i64>(1));
    let physical = owner
        .query_one(
            "SELECT count(*) FILTER (WHERE opening_quantity IS NOT NULL OR closing_quantity IS NOT NULL),
             min(node_ordinal) FILTER (WHERE opening_quantity IS NOT NULL
             AND closing_quantity IS NOT NULL) FROM babylon_state.labor_node_v1
         WHERE campaign_id=$1 AND resolve_tick=2",
            &[id],
        )
        .expect("physical period positions");
    assert!(physical.get::<_, i64>(0) < endpoints);
    let node: i64 = physical.get(1);
    let before = logical(owner, campaign, node);
    assert_eq!(before.len(), 2);
    check_sparse_sides(owner, campaign, node);
    let update = format!(
        "UPDATE {TABLE} SET closing_unknown_opening = NOT closing_unknown_opening
        WHERE campaign_id=$1 AND resolve_tick=2 AND node_ordinal=$2"
    );
    assert_eq!(
        owner
            .execute(&update, &[id, &node])
            .expect("change just one closing disclosure"),
        1
    );
    assert_eq!(
        writer.publish(observer, campaign, 2),
        Err(JournalError::Projection)
    );
    writer
        .rebuild(observer, campaign, 2)
        .expect("reconstruct logical positions from canonical receipts");
    assert_eq!(logical(owner, campaign, node), before);
}

type Endpoint = (String, String, String, bool);

fn logical(client: &mut impl GenericClient, campaign: CampaignId, node: i64) -> Vec<Endpoint> {
    let query = format!(
        "SELECT side,quantity::text,recorded_micro_hours::text,unknown_opening
        FROM {VIEW} WHERE campaign_id=$1 AND resolve_tick=2 AND node_ordinal=$2 ORDER BY side"
    );
    client
        .query(&query, &[campaign.as_uuid(), &node])
        .expect("logical side projection")
        .iter()
        .map(|r| (r.get(0), r.get(1), r.get(2), r.get(3)))
        .collect()
}

fn check_sparse_sides(owner: &mut Client, campaign: CampaignId, node: i64) {
    let mut tx = owner
        .transaction()
        .expect("uncommitted synthetic boundary values");
    let scope = "WHERE campaign_id=$1 AND resolve_tick=2 AND node_ordinal=$2";
    let opening = format!("UPDATE {TABLE}
        SET opening_quantity=1, opening_recorded_micro_hours=0, opening_unknown_opening=false,
            closing_quantity=NULL, closing_recorded_micro_hours=NULL, closing_unknown_opening=NULL {scope}");
    let params: &[&(dyn ToSql + Sync)] = &[campaign.as_uuid(), &node];
    assert_eq!(
        tx.execute(&opening, params)
            .expect("opening-only known zero hours"),
        1
    );
    assert_eq!(
        logical(&mut tx, campaign, node),
        [("opening".into(), "1".into(), "0".into(), false)]
    );
    let closing = format!(
        "UPDATE {TABLE}
        SET closing_quantity=18446744073709551615,
            closing_recorded_micro_hours=340282366920938463463374607431768211455,
            closing_unknown_opening=true, opening_quantity=NULL, opening_recorded_micro_hours=NULL,
            opening_unknown_opening=NULL {scope}"
    );
    assert_eq!(
        tx.execute(&closing, params)
            .expect("closing-only maximum values"),
        1
    );
    assert_eq!(
        logical(&mut tx, campaign, node),
        [(
            "closing".into(),
            u64::MAX.to_string(),
            u128::MAX.to_string(),
            true
        )]
    );
    for damage in [
        "closing_recorded_micro_hours=NULL",
        "closing_quantity=0",
        "closing_quantity=18446744073709551616",
        "closing_recorded_micro_hours=340282366920938463463374607431768211456",
        "closing_recorded_micro_hours=0.5",
    ] {
        let mut probe = tx
            .transaction()
            .expect("savepoint for individual constraint");
        let update = format!("UPDATE {TABLE} SET {damage} {scope}");
        let err = probe
            .execute(&update, params)
            .expect_err("physical basis rejects malformed endpoint");
        assert_eq!(err.code(), Some(&SqlState::CHECK_VIOLATION));
        probe.rollback().expect("preserve prior valid boundary");
    }
    let unknown_zero =
        format!("UPDATE {TABLE} SET closing_quantity=1, closing_recorded_micro_hours=0 {scope}");
    assert_eq!(
        tx.execute(&unknown_zero, params)
            .expect("unknown prior hours with no recorded work"),
        1
    );
    assert_eq!(
        logical(&mut tx, campaign, node),
        [("closing".into(), "1".into(), "0".into(), true)]
    );
    let clear = format!(
        "UPDATE {TABLE} SET closing_quantity=NULL, closing_recorded_micro_hours=NULL,
                         closing_unknown_opening=NULL {scope}"
    );
    assert_eq!(
        tx.execute(&clear, params).expect("clear the last holding"),
        1
    );
    assert_eq!(logical(&mut tx, campaign, node), [] as [Endpoint; 0]);
    let class = format!("SELECT count(*) FROM public.v_observer_labor_node_v1 {scope}");
    let count: i64 = tx
        .query_one(&class, params)
        .expect("retain the movement endpoint")
        .get(0);
    assert_eq!(count, 1);
    tx.rollback()
        .expect("retain the authentic source-derived cells");
}
