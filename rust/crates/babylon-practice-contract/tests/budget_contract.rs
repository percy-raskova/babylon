use babylon_practice_contract::{
    budget_delta_digest, decode_budget_delta, encode_budget_delta, OrganizationBudgetDelta,
    PracticeContractError, PracticeId, VerbMode, VerbStem, PRACTICE_BUDGET_TOPOLOGY_SOURCE_SHA256,
};
use serde_json::Value;

const SCHEMA: &[u8] = include_bytes!("../../../../contracts/practice_budget_topology.yaml");
const VECTORS: &str = include_str!("../../../../contracts/practice_budget_topology_vectors.jsonl");

fn hex_bytes(value: &str) -> Vec<u8> {
    assert_eq!(value.len() % 2, 0);
    value
        .as_bytes()
        .as_chunks::<2>()
        .0
        .iter()
        .map(|pair| {
            u8::from_str_radix(
                std::str::from_utf8(pair).expect("the fixture bytes came from a UTF-8 string"),
                16,
            )
            .expect("the authored digits parse as the declared type")
        })
        .collect()
}

#[test]
fn retained_budget_bytes_and_refusals_match_the_independent_contract() {
    assert_eq!(
        babylon_kernel::content_digest::sha256_of(SCHEMA),
        PRACTICE_BUDGET_TOPOLOGY_SOURCE_SHA256
    );
    let delta = OrganizationBudgetDelta {
        schema_version: 1,
        tick: 11,
        actor_node_id: 7,
        pre_action_world_hash: [0x33; 32],
        budget_before: 1,
        governed_cost: 1,
        footprint_count: 2,
        raw_credit: 2,
        credited_credit: 1,
        ceiling_bound: false,
        budget_after: 1,
    };
    let cases: Vec<Value> = VECTORS
        .lines()
        .map(|line| {
            serde_json::from_str(line).expect("the authored JSON matches the declared schema")
        })
        .collect();
    let case = cases
        .iter()
        .find(|case| case["case_id"] == "budget-delta")
        .expect("the fixture holds the searched element");
    let bytes = hex_bytes(
        case["data"]["canonical_hex"]
            .as_str()
            .expect("the JSON fixture field is a string"),
    );
    assert_eq!(
        encode_budget_delta(&delta).expect("the fixture value encodes to its canonical bytes"),
        bytes
    );
    assert_eq!(
        decode_budget_delta(&bytes).expect("the canonical bytes decode into the declared type"),
        delta
    );
    assert_eq!(
        budget_delta_digest(&delta)
            .expect("the fixture call `budget_delta_digest` succeeds for the authored inputs")
            .as_slice(),
        hex_bytes(
            case["data"]["digest_hex"]
                .as_str()
                .expect("the JSON fixture field is a string")
        )
    );
    for end in 0..bytes.len() {
        assert!(decode_budget_delta(&bytes[..end]).is_err());
    }
    let mut trailing = bytes.clone();
    trailing.push(0);
    assert_eq!(
        decode_budget_delta(&trailing),
        Err(PracticeContractError::PracticeTrailingBytes)
    );
    let case = cases
        .iter()
        .find(|case| case["case_id"] == "budget-boolean")
        .expect("the fixture holds the searched element");
    assert_eq!(
        decode_budget_delta(&hex_bytes(
            case["data"]["payload_hex"]
                .as_str()
                .expect("the JSON fixture field is a string")
        )),
        Err(PracticeContractError::PracticeBoolean)
    );
}

#[test]
fn machine_verbs_exist_only_for_the_declared_material_mappings() {
    let organize = babylon_practice_contract::practice_machine_verb(PracticeId::Organize)
        .expect("the fixture call `practice_machine_verb` succeeds for the authored inputs");
    let agitate = babylon_practice_contract::practice_machine_verb(PracticeId::Agitate)
        .expect("the fixture call `practice_machine_verb` succeeds for the authored inputs");
    let aid = babylon_practice_contract::practice_machine_verb(PracticeId::MutualAid)
        .expect("the fixture call `practice_machine_verb` succeeds for the authored inputs");
    assert_eq!(
        (organize.stem, organize.mode),
        (VerbStem::Mobilize, Some(VerbMode::Canvass))
    );
    assert_eq!(
        (agitate.stem, agitate.mode),
        (VerbStem::Mobilize, Some(VerbMode::Agitate))
    );
    assert_eq!((aid.stem, aid.mode), (VerbStem::Aid, None));
    for practice in [
        PracticeId::Strike,
        PracticeId::Blockade,
        PracticeId::Occupation,
        PracticeId::Damage,
        PracticeId::CapitalStrike,
    ] {
        assert_eq!(
            babylon_practice_contract::practice_machine_verb(practice),
            None
        );
    }
}
