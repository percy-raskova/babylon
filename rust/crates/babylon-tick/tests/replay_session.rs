use std::collections::HashMap;

use babylon_bsl::causal_contract::{AuditReceipt, EffectSignature, EvidenceClass, RuleRole};
use babylon_bsl::evaluator::Value;
use babylon_graph::memory::MemoryGraph;
use babylon_graph::stable_element::StableElementResolverV1;
use babylon_graph::stable_state::encode_stable_graph_state_v1;
use babylon_graph::substrate::GraphSubstrate;
use babylon_tick::replay_identity::{
    encode_stable_world_v1, encode_tick_payload_v1, encode_world_register_set_v1,
    world_register_manifest_v1, ReplayTickIdentityError, STABLE_WORLD_LAYOUT_VERSION_V1,
    TICK_PAYLOAD_LAYOUT_VERSION_V1, WORLD_REGISTER_MANIFEST_LAYOUT_VERSION_V1,
    WORLD_REGISTER_SET_LAYOUT_VERSION_V1,
};

fn str32(value: &str) -> Vec<u8> {
    [
        u32::try_from(value.len()).unwrap().to_be_bytes().as_slice(),
        value.as_bytes(),
    ]
    .concat()
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
