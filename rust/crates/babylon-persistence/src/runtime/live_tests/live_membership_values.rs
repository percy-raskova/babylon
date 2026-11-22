//! A saved world keeps the values its memberships carry (AG clause i, #653).
use super::{CampaignId, NoTls, TestDatabase};
use crate::material_runtime::DurableMaterialRuntime;
use crate::michigan_content::MichiganContentPreset;
use crate::runtime::session;
use crate::stored_tick::{CapturedGraphState, StoredTickReadSource};
use babylon_graph::stable_state::{self, StableGraphState, StableGraphStateRowsInput};
use uuid::Uuid;

const SCOPE: &str = "membership/proof";
const TICK: i64 = 9_001;

/// Two nations over the same two groups, a value on three of the four memberships.
fn nations_with_values() -> StableGraphState {
    let members = vec!["group-a".to_owned(), "group-b".to_owned()];
    stable_state::compose_stable_graph_state_from_rows(
        SCOPE,
        StableGraphStateRowsInput {
            nodes: vec![
                ("group-a".to_owned(), "group".to_owned()),
                ("group-b".to_owned(), "group".to_owned()),
            ],
            node_f64: Vec::new(),
            edges: Vec::new(),
            hyperedges: vec![
                ("nation-1".to_owned(), "nation".to_owned(), members.clone()),
                ("nation-2".to_owned(), "nation".to_owned(), members),
            ],
            edge_f64: Vec::new(),
            node_currency: Vec::new(),
            hyperedge_f64: Vec::new(),
            membership_f64: [
                ("nation-1", "group-a", 3.0_f64),
                ("nation-1", "group-b", -0.5),
                ("nation-2", "group-a", 7.0),
            ]
            .into_iter()
            .map(|(edge, member, value)| {
                (
                    edge.to_owned(),
                    member.to_owned(),
                    "nation/households".to_owned(),
                    value.to_bits(),
                )
            })
            .collect(),
        },
    )
    .expect("the authored rows compose a stable graph state")
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn a_campaign_with_membership_values_restores_them() {
    let base = super::validated_base_config();
    let database = TestDatabase::create_from_template(
        &base,
        &super::validated_template_name(),
        "membervalues",
    );
    let config = database.config(&base);
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x653_0a01));
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation_for_campaign(&crate::test_support::catalog(), campaign)
        .expect("the authored catalog builds the campaign foundation");
    drop(
        DurableMaterialRuntime::create(&config, campaign, foundation)
            .expect("the test database creates the fixture campaign"),
    );
    let written = nations_with_values();
    assert_eq!(written.rows().membership_f64().len(), 3);

    // The whole exchange stays inside one transaction that is rolled back: the
    // graph rows' marker constraints are deferred, and no tick is committed here.
    let mut client = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let mut tx = client
        .transaction()
        .expect("the test database opens a transaction");
    session::insert_typed_graph_rows(&mut tx, campaign, TICK, &written)
        .expect("the fixture graph writes its typed rows");

    // Reload: the hyperedges and every value come back exactly. Nodes are not
    // compared: their chunked rows are read through a committed tick's marker,
    // and this transaction commits none.
    let reloaded = reload(&mut tx, campaign);
    assert_eq!(reloaded.rows().hyperedges(), written.rows().hyperedges());
    assert_eq!(
        reloaded.rows().membership_f64(),
        written.rows().membership_f64()
    );

    // A value for a pair that is not a membership is refused by the table itself.
    let mut attempt = tx
        .transaction()
        .expect("the open transaction opens a savepoint");
    let refused = attempt
        .execute(
            "INSERT INTO babylon_state.graph_hyperedge_member_f64_v1 \
             (campaign_id, resolve_tick, local_name, member, qname, value_bits) \
             VALUES ($1::uuid, $2, 'nation-1', 'group-zzz', 'nation/households', 0)",
            &[campaign.as_uuid(), &TICK],
        )
        .expect_err("the foreign key refuses a value for a non-member");
    assert_eq!(
        refused.code(),
        Some(&postgres::error::SqlState::FOREIGN_KEY_VIOLATION)
    );
    attempt.rollback().expect("the savepoint rolls back");

    // A lost value row changes the reloaded state, so the checkpoint's section
    // hash would refuse the load rather than quietly read zero.
    tx.execute(
        "DELETE FROM babylon_state.graph_hyperedge_member_f64_v1 \
         WHERE campaign_id = $1::uuid AND resolve_tick = $2 AND local_name = 'nation-2'",
        &[campaign.as_uuid(), &TICK],
    )
    .expect("the test database applies the setup statement");
    let shrunk = reload(&mut tx, campaign);
    assert_eq!(shrunk.rows().membership_f64().len(), 2);
    assert_ne!(
        shrunk.rows().membership_f64(),
        written.rows().membership_f64()
    );
    tx.rollback().expect("the open transaction rolls back");
    drop(client);
    database.cleanup();
}

fn reload(client: &mut impl postgres::GenericClient, campaign: CampaignId) -> StableGraphState {
    CapturedGraphState::capture(client, StoredTickReadSource::Runtime, campaign, TICK)
        .expect("the stored rows are readable")
        .admit(SCOPE)
        .expect("the stored rows admit as a stable graph state")
}
