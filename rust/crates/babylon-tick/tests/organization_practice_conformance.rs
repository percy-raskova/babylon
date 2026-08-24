//! Behavioral proof for situated organizational practice over relational territory.

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_kernel::SessionId;
use babylon_tick::TickSession;

const SCENARIO: &str = include_str!("../content/scenarios/organization-foundation.bscn");
const PACK: &str = include_str!("../content/rules/organization.bsl");

const COUNTY_A: NodeId = NodeId(1);
const READING_GROUP: NodeId = NodeId(2);
const PRECINCT: NodeId = NodeId(3);
const COUNTY_B: NodeId = NodeId(6);
const COUNTY_C: NodeId = NodeId(7);
const COUNTY_D: NodeId = NodeId(9);
const PRACTICE_TICKS: usize = 24;

fn attribute(session: &TickSession<HypergraphStore>, node: NodeId, field: &str) -> f64 {
    session
        .graph()
        .node_attribute(node, field)
        .unwrap_or_else(|error| panic!("node {node:?} declares {field}: {error:?}"))
}

fn capacity(session: &TickSession<HypergraphStore>, territory: NodeId) -> f64 {
    attribute(session, territory, "territory/rooted-capacity")
}

fn rooted_work(session: &TickSession<HypergraphStore>, territory: NodeId) -> f64 {
    attribute(session, territory, "territory/rooted-work-inbox")
}

fn membership(session: &TickSession<HypergraphStore>) -> f64 {
    attribute(session, READING_GROUP, "organization/membership-share")
}

#[test]
fn rooted_capacity_moves_one_relational_hop_per_tick() {
    let mut session = TickSession::new(
        SCENARIO,
        PACK,
        HypergraphStore::new(),
        SessionId::new("organization-practice-conformance").expect("literal is non-empty"),
    )
    .expect("the organization practice world loads");
    let mut sink = CollectingSink::default();

    session.advance(&mut sink).expect("tick 1");
    assert!(capacity(&session, COUNTY_A) > 0.0);
    assert!(capacity(&session, COUNTY_B) > 0.0);
    assert_eq!(capacity(&session, COUNTY_C).to_bits(), 0.0_f64.to_bits());
    assert_eq!(
        attribute(&session, READING_GROUP, "organization/action-budget").to_bits(),
        0.0_f64.to_bits()
    );
    assert_eq!(
        attribute(&session, PRECINCT, "organization/action-budget").to_bits(),
        1.0_f64.to_bits()
    );

    session.advance(&mut sink).expect("tick 2");
    assert!(capacity(&session, COUNTY_C) > 0.0);
}

#[test]
fn unique_low_buffer_corridor_relays_more_capacity_than_reroutable_corridor() {
    let mut session = TickSession::new(
        SCENARIO,
        PACK,
        HypergraphStore::new(),
        SessionId::new("organization-circulation-bottleneck").expect("literal is non-empty"),
    )
    .expect("the organization practice world loads");
    let mut sink = CollectingSink::default();

    session
        .advance(&mut sink)
        .expect("circulation comparison tick");

    let unique_corridor_capacity = capacity(&session, COUNTY_B);
    let reroutable_corridor_capacity = capacity(&session, COUNTY_D);
    assert!(reroutable_corridor_capacity > 0.0);
    assert!(
        unique_corridor_capacity > reroutable_corridor_capacity,
        "unique corridor capacity {unique_corridor_capacity} did not exceed reroutable corridor capacity {reroutable_corridor_capacity}"
    );
}

#[test]
fn one_weekly_action_is_divided_across_the_organizations_branches() {
    let mut one_branch = TickSession::new(
        SCENARIO,
        PACK,
        HypergraphStore::new(),
        SessionId::new("organization-one-branch").expect("literal is non-empty"),
    )
    .expect("the one-branch organization world loads");
    let two_branch_scenario = SCENARIO.replace(
        "  (edge EdgeType/SOLIDARITY reading-group precinct 1))",
        "  (edge EdgeType/SOLIDARITY reading-group precinct 1)\n  \
         (edge EdgeType/PRESENCE reading-group county-b 1)\n  \
         (edge-attr EdgeType/PRESENCE reading-group county-b presence/embedding PracticeEmbedding/NEIGHBORHOOD))",
    );
    assert_ne!(
        two_branch_scenario, SCENARIO,
        "the second branch must be inserted"
    );
    let mut two_branches = TickSession::new(
        &two_branch_scenario,
        PACK,
        HypergraphStore::new(),
        SessionId::new("organization-two-branches").expect("literal is non-empty"),
    )
    .expect("the two-branch organization world loads");
    let mut one_branch_sink = CollectingSink::default();
    let mut two_branch_sink = CollectingSink::default();

    one_branch
        .advance(&mut one_branch_sink)
        .expect("one-branch tick");
    two_branches
        .advance(&mut two_branch_sink)
        .expect("two-branch tick");

    let one_branch_work = rooted_work(&one_branch, COUNTY_A);
    let first_branch_work = rooted_work(&two_branches, COUNTY_A);
    let second_branch_work = rooted_work(&two_branches, COUNTY_B);
    assert!(first_branch_work > 0.0);
    assert!(second_branch_work > 0.0);
    assert!(first_branch_work < one_branch_work);
    assert!(first_branch_work + second_branch_work <= one_branch_work);
}

#[test]
fn practice_requires_presence_with_the_matching_material_embedding() {
    let workplace_practice = SCENARIO.replace(
        "(organization/practice-embedding PracticeEmbedding/NEIGHBORHOOD)",
        "(organization/practice-embedding PracticeEmbedding/WORKPLACE)",
    );
    assert_ne!(
        workplace_practice, SCENARIO,
        "the organization must select workplace practice"
    );
    let matched_workplace = workplace_practice.replace(
        "county presence/embedding PracticeEmbedding/NEIGHBORHOOD)",
        "county presence/embedding PracticeEmbedding/WORKPLACE)",
    );
    assert_ne!(
        matched_workplace, workplace_practice,
        "the presence relation must become a workplace embedding"
    );
    let mut mismatched = TickSession::new(
        &workplace_practice,
        PACK,
        HypergraphStore::new(),
        SessionId::new("organization-mismatched-embedding").expect("literal is non-empty"),
    )
    .expect("the mismatched-embedding world loads");
    let mut matched = TickSession::new(
        &matched_workplace,
        PACK,
        HypergraphStore::new(),
        SessionId::new("organization-matched-embedding").expect("literal is non-empty"),
    )
    .expect("the matched-embedding world loads");
    let mut mismatched_sink = CollectingSink::default();
    let mut matched_sink = CollectingSink::default();

    mismatched
        .advance(&mut mismatched_sink)
        .expect("mismatched-embedding tick");
    matched
        .advance(&mut matched_sink)
        .expect("matched-embedding tick");

    assert_eq!(
        rooted_work(&mismatched, COUNTY_A).to_bits(),
        0.0_f64.to_bits()
    );
    assert_eq!(
        attribute(&mismatched, COUNTY_A, "territory/reproduction-pressure").to_bits(),
        0.9_f64.to_bits()
    );
    assert!(rooted_work(&matched, COUNTY_A) > 0.0);
    assert!(attribute(&matched, COUNTY_A, "territory/reproduction-pressure") < 0.9);
}

#[test]
fn recruitment_emerges_as_slow_fast_slow_growth() {
    let mut session = TickSession::new(
        SCENARIO,
        PACK,
        HypergraphStore::new(),
        SessionId::new("organization-recruitment-emergence").expect("literal is non-empty"),
    )
    .expect("the organization practice world loads");
    let mut sink = CollectingSink::default();
    let mut trajectory = [0.0_f64; PRACTICE_TICKS];

    for membership_share in &mut trajectory {
        session.advance(&mut sink).expect("bounded emergence tick");
        *membership_share = membership(&session);
    }

    let early_gain = trajectory[3] - trajectory[0];
    let middle_gain = trajectory[11] - trajectory[8];
    let late_gain = trajectory[23] - trajectory[20];

    assert!(trajectory.windows(2).all(|pair| pair[1] >= pair[0]));
    assert!(early_gain > 0.0, "early gain was {early_gain}");
    assert!(
        middle_gain > early_gain,
        "middle gain {middle_gain} did not exceed early gain {early_gain}"
    );
    assert!(
        (0.0..middle_gain).contains(&late_gain),
        "late gain {late_gain} did not decelerate from {middle_gain}"
    );
    assert!(trajectory[23] < 1.0);
    assert!(
        attribute(&session, COUNTY_A, "territory/command-pressure") > 0.0,
        "rooted organization should provoke a territorial command response"
    );
    assert!(
        attribute(&session, COUNTY_A, "territory/reproduction-pressure") < 0.9,
        "organized care should ease the pressure that initially conditioned recruitment"
    );
}
