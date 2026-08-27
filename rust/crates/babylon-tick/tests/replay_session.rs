use std::collections::HashMap;
use std::process::Command;

use babylon_bsl::causal_contract::{AuditReceipt, EffectSignature, EvidenceClass, RuleRole};
use babylon_bsl::evaluator::Value;
use babylon_bsl::rule_pipeline::split_content;
use babylon_bsl::rules_hash_of;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::memory::MemoryGraph;
use babylon_graph::stable_element::StableElementResolverV1;
use babylon_graph::stable_state::encode_stable_graph_state_v1;
use babylon_graph::state_hash::CanonicalState;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_graph::{allocator_state::AllocatorState, working_copy::DetachedCopy};
use babylon_kernel::replay::{ReplaySeed, ReplaySessionIdV1};
use babylon_kernel::tick_content_hash::{
    PreparedEnvironmentDigestV1, RefDigestV1, TickContentPartsV1, TickContentPreimageV1,
};
use babylon_kernel::{sha256_of, ContentDigest};
use babylon_practice_contract::ordered_action_v1::{
    OrderedPracticeActionBatchV1, ORDERED_PRACTICE_ACTION_BATCH_V1_LAYOUT_VERSION,
};
use babylon_practice_contract::{
    input_authority_ledger_v2_digest, ActorOrganizationIdV2, CampaignIdV2, InputAuthorityIdV2,
    PracticeAuthorityKindV2, PracticeIdV2, PracticeInputAuthorityLedgerV2,
    PracticeInputAuthorityV2, PracticeIntentV2, PracticeTargetIdentityV2, PracticeTargetTagV2,
    ProposalNonceV2, ResolvedPracticeBatchItemV2, ResolvedPracticeBatchV2, TaggedPracticeTargetV2,
};
use babylon_tick::replay_identity::{
    encode_stable_world_v1, encode_tick_payload_v1, encode_world_register_set_v1,
    world_register_manifest_v1, ReplayTickIdentityError, STABLE_WORLD_LAYOUT_VERSION_V1,
    TICK_PAYLOAD_LAYOUT_VERSION_V1, WORLD_REGISTER_MANIFEST_LAYOUT_VERSION_V1,
    WORLD_REGISTER_SET_LAYOUT_VERSION_V1,
};
use babylon_tick::replay_session::{ReplayTickError, ReplayTickSession};

const REPLAY_SCENARIO: &str = r"
(scenario demo/rng-two-classes
  (deffield social-class/needs-roll int extensive)
  (deffield social-class/draw coefficient extensive)
  (node class-a NodeType/SOCIAL_CLASS
    (social-class/needs-roll 0))
  (node class-b NodeType/SOCIAL_CLASS
    (social-class/needs-roll 1)))
";
const REPLAY_RULE: &str = r#"
(intrinsic rng-draw :params (int) :returns real :cost 12)
(rule vitality/rng-keyed-draw
  :role mechanic
  :evidence derived
  :material-basis "replay identity test exercises the real seed-aware draw path"
  :fuel 64
  (bindings
    (binding needs-roll :field social-class/needs-roll))
  (when #t)
  (effects
    (update-node self social-class/draw (set (rng-draw 0)))))
"#;
const PROCESS_CHILD_ENV: &str = "BABYLON_PER60_REPLAY_CHILD";
const PROCESS_MARKER: &str = "PER60_REPLAY=";
const FAILURE_SCENARIO: &str = r"
(scenario tick/replay-failure
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/probability probability intensive)
  (node first NodeType/SOCIAL_CLASS (social-class/probability 0.1p))
  (node second NodeType/SOCIAL_CLASS (social-class/probability 0.9p)))
";
const FAILURE_RULE: &str = r#"
(rule vitality/replay-failure
  :role mechanic
  :evidence derived
  :material-basis "one valid event precedes a domain-invalid write in the detached graph"
  :fuel 64
  (bindings (binding probability :field social-class/probability))
  (when (> probability 0.0p))
  (effects
    (emit EventType/REPLAY_FAILURE)
    (update-node self social-class/probability (add 0.4i))))
"#;

fn str32(value: &str) -> Vec<u8> {
    [
        u32::try_from(value.len()).unwrap().to_be_bytes().as_slice(),
        value.as_bytes(),
    ]
    .concat()
}

fn content_for(rule_src: &str) -> ContentDigest {
    let (_, rules) = split_content(rule_src).unwrap();
    let forms = rules.into_iter().map(|(_, form)| form).collect::<Vec<_>>();
    ContentDigest {
        defines_hash: [0x2d; 32],
        rules_hash: rules_hash_of(&forms).unwrap(),
    }
}

fn nonempty_action_batch(session: ReplaySessionIdV1) -> OrderedPracticeActionBatchV1 {
    let authority = PracticeInputAuthorityV2 {
        schema_version: 2,
        campaign_id: CampaignIdV2::from_bytes([0x10; 16]),
        authority_kind: PracticeAuthorityKindV2::PlayerSeat,
        input_authority_id: InputAuthorityIdV2::from_bytes([0x20; 16]),
        actor_org_id: ActorOrganizationIdV2::from_bytes(7_u64.to_be_bytes()),
        effective_from_tick: 10,
        effective_through_tick_exclusive: 20,
        decision_content_digest: [0x30; 32],
    };
    let ledger = PracticeInputAuthorityLedgerV2 {
        schema_version: 2,
        rows: vec![authority.clone()],
    };
    let intent = PracticeIntentV2 {
        schema_version: 2,
        submit_after_tick: 10,
        resolve_tick: 11,
        input_authority_id: InputAuthorityIdV2::from_bytes([0x20; 16]),
        actor_org_id: ActorOrganizationIdV2::from_bytes(7_u64.to_be_bytes()),
        practice_id: PracticeIdV2::Strike,
        target: TaggedPracticeTargetV2 {
            tag: PracticeTargetTagV2::LaborProcess,
            identity: PracticeTargetIdentityV2::from_bytes([0x50; 32]),
        },
        proposal_nonce: ProposalNonceV2::from_bytes([0x60; 16]),
        quoted_content_digest: [0x30; 32],
        quoted_resource_contract_digest: [0x40; 32],
        parameters: Vec::new(),
        evidence_digests: vec![[0x70; 32]],
    };
    let source = ResolvedPracticeBatchV2 {
        schema_version: 2,
        campaign_id: CampaignIdV2::from_bytes([0x10; 16]),
        resolve_tick: 11,
        authority_ledger_digest: input_authority_ledger_v2_digest(&ledger).unwrap(),
        resource_allocation_contract_digest: [0x40; 32],
        content_digest: [0x30; 32],
        items: vec![ResolvedPracticeBatchItemV2 { authority, intent }],
    };
    OrderedPracticeActionBatchV1::project(session, &source, &ledger).unwrap()
}

#[derive(Debug, PartialEq, Eq)]
struct ReplayRun {
    outer: String,
    prepared: String,
    prior: String,
    result: String,
    payload: String,
    actions: String,
    draw_bits: u64,
}

fn run_replay<G>(seed: i64) -> ReplayRun
where
    G: GraphSubstrate + CanonicalState + AllocatorState + DetachedCopy + Default,
{
    let replay_id = ReplaySessionIdV1::try_from("per60/cross-substrate").unwrap();
    let mut session = ReplayTickSession::new(
        REPLAY_SCENARIO,
        None,
        REPLAY_RULE,
        G::default(),
        replay_id.clone(),
        ReplaySeed::new(seed),
        content_for(REPLAY_RULE),
        RefDigestV1::from_bytes([0x47; 32]),
    )
    .unwrap();
    let actions = OrderedPracticeActionBatchV1::empty(replay_id, 1).unwrap();
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();
    let report = session.advance(&mut sink, &actions).unwrap();
    ReplayRun {
        outer: report.tick_content_hash().to_hex(),
        prepared: report.prepared_environment_digest().to_hex(),
        prior: report.prior_world().digest().to_hex(),
        result: report.result_world().digest().to_hex(),
        payload: report.payload().digest().to_hex(),
        actions: report.action_batch_digest().to_hex(),
        draw_bits: session
            .graph()
            .node_attribute(NodeId(0), "social-class/draw")
            .unwrap()
            .to_bits(),
    }
}

#[test]
fn replay_session_constructor_is_typed_to_v2_identity() {
    let _constructor = ReplayTickSession::<MemoryGraph>::new;
}

#[test]
fn replay_session_publishes_exact_identity_and_retains_static_bytes_once() {
    let replay_id = ReplaySessionIdV1::try_from("per60/session-a").unwrap();
    let seed = ReplaySeed::new(-71);
    let content = content_for(REPLAY_RULE);
    let reference = RefDigestV1::from_bytes([0x6e; 32]);
    let mut session = ReplayTickSession::new(
        REPLAY_SCENARIO,
        None,
        REPLAY_RULE,
        HypergraphStore::new(),
        replay_id.clone(),
        seed,
        content.clone(),
        reference,
    )
    .unwrap();
    let resolver_storage = session.resolver_manifest_bytes().as_ptr();
    let register_storage = session.register_manifest_bytes().as_ptr();
    let prepared_storage = session.prepared_environment_bytes().as_ptr();
    let prepared_digest =
        PreparedEnvironmentDigestV1::from_bytes(sha256_of(session.prepared_environment_bytes()));
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();
    let actions = OrderedPracticeActionBatchV1::empty(replay_id.clone(), 1).unwrap();
    let identified = session.advance(&mut sink, &actions).unwrap();

    assert_eq!(session.completed_tick(), 1);
    assert_eq!(identified.action_batch_bytes(), actions.canonical_bytes());
    assert_eq!(
        identified.action_batch_layout_version(),
        ORDERED_PRACTICE_ACTION_BATCH_V1_LAYOUT_VERSION
    );
    assert_eq!(identified.action_batch_digest(), actions.digest());
    assert_eq!(identified.prior_registers().completed_tick(), 0);
    assert_eq!(identified.result_registers().completed_tick(), 1);
    assert_eq!(identified.prepared_environment_digest(), prepared_digest);
    assert_eq!(
        identified.tick_content_hash(),
        identified.outer_preimage().digest()
    );
    assert_eq!(identified.report().fired, 2);

    let independently_composed = TickContentPreimageV1::compose(&TickContentPartsV1 {
        session: &replay_id,
        resolve_tick: 1,
        seed,
        content: &content,
        reference,
        prepared: prepared_digest,
        prior_world: identified.prior_world().digest(),
        actions: actions.digest(),
        result_world: identified.result_world().digest(),
        payload: identified.payload().digest(),
    })
    .unwrap();
    assert_eq!(
        identified.outer_preimage().as_bytes(),
        independently_composed.as_bytes()
    );

    let next_actions = OrderedPracticeActionBatchV1::empty(replay_id, 2).unwrap();
    let second = session.advance(&mut sink, &next_actions).unwrap();
    assert_eq!(second.prior_registers().completed_tick(), 1);
    assert_eq!(second.result_registers().completed_tick(), 2);
    assert_eq!(session.resolver_manifest_bytes().as_ptr(), resolver_storage);
    assert_eq!(session.register_manifest_bytes().as_ptr(), register_storage);
    assert_eq!(
        session.prepared_environment_bytes().as_ptr(),
        prepared_storage
    );
}

#[test]
fn replay_identity_agrees_across_substrates_and_seed_moves_real_draws() {
    let memory = run_replay::<MemoryGraph>(811);
    let hypergraph = run_replay::<HypergraphStore>(811);
    assert_eq!(memory, hypergraph);

    let changed_seed = run_replay::<HypergraphStore>(812);
    assert_eq!(hypergraph.prepared, changed_seed.prepared);
    assert_eq!(hypergraph.prior, changed_seed.prior);
    assert_eq!(hypergraph.actions, changed_seed.actions);
    assert_eq!(hypergraph.payload, changed_seed.payload);
    assert_ne!(hypergraph.draw_bits, changed_seed.draw_bits);
    assert_ne!(hypergraph.result, changed_seed.result);
    assert_ne!(hypergraph.outer, changed_seed.outer);
}

#[test]
fn replay_identity_is_exact_across_fresh_processes() {
    if std::env::var_os(PROCESS_CHILD_ENV).is_some() {
        println!("{PROCESS_MARKER}{:?}", run_replay::<HypergraphStore>(811));
        return;
    }
    let executable = std::env::current_exe().unwrap();
    let run_child = || {
        let output = Command::new(&executable)
            .args([
                "--exact",
                "replay_identity_is_exact_across_fresh_processes",
                "--nocapture",
            ])
            .env(PROCESS_CHILD_ENV, "1")
            .output()
            .unwrap();
        assert!(output.status.success(), "{output:?}");
        String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .find_map(|line| line.strip_prefix(PROCESS_MARKER).map(str::to_owned))
            .unwrap()
    };
    assert_eq!(run_child(), run_child());
}

#[test]
fn replay_action_guards_and_rules_hash_refuse_without_publication() {
    let replay_id = ReplaySessionIdV1::try_from("per60/guarded").unwrap();
    let mut bad_content = content_for(REPLAY_RULE);
    bad_content.rules_hash = [0xff; 32];
    assert!(matches!(
        ReplayTickSession::new(
            REPLAY_SCENARIO,
            None,
            REPLAY_RULE,
            MemoryGraph::new(),
            replay_id.clone(),
            ReplaySeed::new(9),
            bad_content,
            RefDigestV1::from_bytes([0x11; 32]),
        ),
        Err(ReplayTickError::Identity(
            ReplayTickIdentityError::RulesHashMismatch { .. }
        ))
    ));

    let mut session = ReplayTickSession::new(
        REPLAY_SCENARIO,
        None,
        REPLAY_RULE,
        MemoryGraph::new(),
        replay_id.clone(),
        ReplaySeed::new(9),
        content_for(REPLAY_RULE),
        RefDigestV1::from_bytes([0x11; 32]),
    )
    .unwrap();
    let before = session.graph().encode_state().unwrap().as_bytes().to_vec();
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();

    let structural = nonempty_action_batch(replay_id.clone());
    assert!(matches!(
        session.advance(&mut sink, &structural),
        Err(ReplayTickError::NonEmptyActionBatch { count: 1 })
    ));

    let other_session = ReplaySessionIdV1::try_from("per60/other").unwrap();
    let wrong_session = OrderedPracticeActionBatchV1::empty(other_session, 1).unwrap();
    assert!(matches!(
        session.advance(&mut sink, &wrong_session),
        Err(ReplayTickError::ActionSessionMismatch)
    ));
    let wrong_tick = OrderedPracticeActionBatchV1::empty(replay_id, 2).unwrap();
    assert!(matches!(
        session.advance(&mut sink, &wrong_tick),
        Err(ReplayTickError::ActionTickMismatch {
            expected: 1,
            actual: 2,
        })
    ));
    assert_eq!(session.completed_tick(), 0);
    assert!(sink.events.is_empty());
    assert_eq!(session.graph().encode_state().unwrap().as_bytes(), before);
}

#[test]
fn replay_rule_failure_discards_detached_writes_events_and_identity() {
    let replay_id = ReplaySessionIdV1::try_from("per60/rule-failure").unwrap();
    let mut session = ReplayTickSession::new(
        FAILURE_SCENARIO,
        None,
        FAILURE_RULE,
        MemoryGraph::new(),
        replay_id.clone(),
        ReplaySeed::new(13),
        content_for(FAILURE_RULE),
        RefDigestV1::from_bytes([0x91; 32]),
    )
    .unwrap();
    let before = session.graph().encode_state().unwrap().as_bytes().to_vec();
    let actions = OrderedPracticeActionBatchV1::empty(replay_id, 1).unwrap();
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();

    assert!(matches!(
        session.advance(&mut sink, &actions),
        Err(ReplayTickError::Execution { .. })
    ));
    assert_eq!(session.completed_tick(), 0);
    assert!(sink.events.is_empty());
    assert_eq!(session.graph().encode_state().unwrap().as_bytes(), before);
}

#[test]
fn register_manifest_set_and_stable_world_bytes_are_exact() {
    let manifest = world_register_manifest_v1().unwrap();
    assert_eq!(
        manifest.canonical_bytes(),
        [
            b"babylon.world-register-manifest\0".as_slice(),
            &WORLD_REGISTER_MANIFEST_LAYOUT_VERSION_V1.to_be_bytes(),
            &1_u32.to_be_bytes(),
            &str32("world/completed-tick"),
            &1_u32.to_be_bytes(),
        ]
        .concat()
    );
    let registers = encode_world_register_set_v1(&manifest, 0).unwrap();
    assert_eq!(
        registers.canonical_bytes(),
        [
            b"babylon.world-register-set\0".as_slice(),
            &WORLD_REGISTER_SET_LAYOUT_VERSION_V1.to_be_bytes(),
            &[0x01],
            &WORLD_REGISTER_MANIFEST_LAYOUT_VERSION_V1.to_be_bytes(),
            manifest.digest().as_slice(),
            &[0x02],
            &1_u32.to_be_bytes(),
            &str32("world/completed-tick"),
            &1_u32.to_be_bytes(),
            &8_u32.to_be_bytes(),
            &0_i64.to_be_bytes(),
        ]
        .concat()
    );

    let mut graph = MemoryGraph::new();
    let node = graph.add_node("class").unwrap();
    let resolver = StableElementResolverV1::seal(
        &graph,
        "demo/world",
        &HashMap::from([(node, "workers".to_owned())]),
        &HashMap::new(),
    )
    .unwrap();
    let stable_graph = encode_stable_graph_state_v1(&graph, &resolver).unwrap();
    let world = encode_stable_world_v1(&stable_graph, &registers).unwrap();
    assert_eq!(
        world.canonical_bytes(),
        [
            b"babylon.stable-world\0".as_slice(),
            &STABLE_WORLD_LAYOUT_VERSION_V1.to_be_bytes(),
            &[0x01],
            &1_u32.to_be_bytes(),
            stable_graph.digest().as_bytes(),
            &[0x02],
            &WORLD_REGISTER_SET_LAYOUT_VERSION_V1.to_be_bytes(),
            registers.digest().as_slice(),
        ]
        .concat()
    );
}

#[test]
fn register_tick_domain_is_checked() {
    let manifest = world_register_manifest_v1().unwrap();
    assert!(encode_world_register_set_v1(&manifest, i64::MAX).is_ok());
    assert_eq!(
        encode_world_register_set_v1(&manifest, -1),
        Err(ReplayTickIdentityError::NegativeCompletedTick { value: -1 })
    );
}

#[test]
fn tick_payload_is_exact_and_order_sensitive_without_reencoding_fired() {
    let mut graph = MemoryGraph::new();
    let node = graph.add_node("class").unwrap();
    let resolver = StableElementResolverV1::seal(
        &graph,
        "demo/world",
        &HashMap::from([(node, "workers".to_owned())]),
        &HashMap::new(),
    )
    .unwrap();
    let order = vec!["demo/a".to_owned(), "demo/b".to_owned()];
    let outcomes = vec![("demo/a".to_owned(), 1), ("demo/b".to_owned(), 2)];
    let events = vec![
        (
            "FIRST".to_owned(),
            vec![
                ("value".to_owned(), Value::Int(1)),
                ("value".to_owned(), Value::Int(2)),
            ],
        ),
        (
            "SECOND".to_owned(),
            vec![("value".to_owned(), Value::Int(3))],
        ),
    ];
    let receipts = vec![
        AuditReceipt {
            rule_id: "demo/a".to_owned(),
            role: RuleRole::Mechanic,
            evidence: EvidenceClass::Derived,
            ordinal: 0,
            effect: EffectSignature::NodeField("class/value".to_owned()),
        },
        AuditReceipt {
            rule_id: "demo/b".to_owned(),
            role: RuleRole::Mechanic,
            evidence: EvidenceClass::Derived,
            ordinal: 1,
            effect: EffectSignature::Event("SECOND".to_owned()),
        },
    ];
    let payload =
        encode_tick_payload_v1(&order, &outcomes, 3, &events, &receipts, &resolver).unwrap();
    assert!(payload.canonical_bytes().starts_with(
        &[
            b"babylon.tick-payload\0".as_slice(),
            &TICK_PAYLOAD_LAYOUT_VERSION_V1.to_be_bytes(),
            &[0x01],
        ]
        .concat()
    ));
    assert_eq!(payload.canonical_bytes().last(), Some(&0));
    let reversed = encode_tick_payload_v1(
        &order,
        &outcomes,
        3,
        &events.iter().cloned().rev().collect::<Vec<_>>(),
        &receipts,
        &resolver,
    )
    .unwrap();
    assert_ne!(payload.digest(), reversed.digest());
    let reversed_pairs = vec![
        ("value".to_owned(), Value::Int(2)),
        ("value".to_owned(), Value::Int(1)),
    ];
    let pair_reordered_events = vec![("FIRST".to_owned(), reversed_pairs), events[1].clone()];
    let pair_reordered = encode_tick_payload_v1(
        &order,
        &outcomes,
        3,
        &pair_reordered_events,
        &receipts,
        &resolver,
    )
    .unwrap();
    assert_ne!(payload.digest(), pair_reordered.digest());
    let receipt_reordered = encode_tick_payload_v1(
        &order,
        &outcomes,
        3,
        &events,
        &receipts.iter().cloned().rev().collect::<Vec<_>>(),
        &resolver,
    )
    .unwrap();
    assert_ne!(payload.digest(), receipt_reordered.digest());
    assert!(matches!(
        encode_tick_payload_v1(&order, &outcomes, 4, &events, &receipts, &resolver),
        Err(ReplayTickIdentityError::FiredTotalMismatch { .. })
    ));
    assert!(matches!(
        encode_tick_payload_v1(
            &["demo/b".to_owned(), "demo/a".to_owned()],
            &outcomes,
            3,
            &events,
            &receipts,
            &resolver,
        ),
        Err(ReplayTickIdentityError::RuleOutcomeOrder)
    ));
}
