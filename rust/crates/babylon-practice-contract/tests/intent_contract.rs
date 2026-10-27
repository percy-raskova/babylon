use babylon_practice_contract::ActorOrganizationId;
use babylon_practice_contract::{
    decode_practice_intent, encode_practice_intent, fixed_practice_target_digest,
    practice_intent_digest, practice_parameter_bytes_digest, InputAuthorityId, PracticeId,
    PracticeIntent, PracticeIntentError, PracticeTargetIdentity, PracticeTargetTag, ProposalNonce,
    TaggedPracticeTarget, PRACTICE_INTENT_SOURCE_SHA256,
};
use serde_json::Value;

const SCHEMA: &[u8] = include_bytes!("../../../../contracts/practice_intent.yaml");
const VECTORS: &str = include_str!("../../../../contracts/practice_intent_vectors.jsonl");

fn actor_id(value: u64) -> ActorOrganizationId {
    ActorOrganizationId::from_bytes(value.to_be_bytes())
}

fn hex_bytes(value: &str) -> Vec<u8> {
    assert_eq!(value.len() % 2, 0);
    value
        .as_bytes()
        .as_chunks::<2>()
        .0
        .iter()
        .map(|chunk| {
            let text = std::str::from_utf8(chunk).expect("hex fixture is ASCII");
            u8::from_str_radix(text, 16).expect("hex fixture is valid")
        })
        .collect()
}

#[allow(
    clippy::too_many_lines,
    reason = "`intent_from_vector` keeps one authored boundary's fixture and assertions together"
)]
fn intent_from_vector(data: &Value) -> PracticeIntent {
    PracticeIntent {
        schema_version: 2,
        submit_after_tick: data["submit_after_tick"]
            .as_u64()
            .expect("the JSON fixture field is an unsigned integer"),
        resolve_tick: data["resolve_tick"]
            .as_u64()
            .expect("the JSON fixture field is an unsigned integer"),
        input_authority_id: InputAuthorityId::from_bytes(
            hex_bytes(
                data["input_authority_id_hex"]
                    .as_str()
                    .expect("the JSON fixture field is a string"),
            )
            .try_into()
            .expect("the fixture slice has the target length"),
        ),
        actor_org_id: actor_id(
            data["actor_org_id"]
                .as_u64()
                .expect("the JSON fixture field is an unsigned integer"),
        ),
        practice_id: PracticeId::try_from(
            u8::try_from(
                data["practice_id"]
                    .as_u64()
                    .expect("the JSON fixture field is an unsigned integer"),
            )
            .expect("the fixture value fits the target range"),
        )
        .expect("the fixture value fits the target range"),
        target: TaggedPracticeTarget {
            tag: PracticeTargetTag::try_from(
                u8::try_from(
                    data["target_tag"]
                        .as_u64()
                        .expect("the JSON fixture field is an unsigned integer"),
                )
                .expect("the fixture value fits the target range"),
            )
            .expect("the fixture value fits the target range"),
            identity: PracticeTargetIdentity::from_bytes(
                hex_bytes(
                    data["target_identity_hex"]
                        .as_str()
                        .expect("the JSON fixture field is a string"),
                )
                .try_into()
                .expect("the fixture slice has the target length"),
            ),
        },
        proposal_nonce: ProposalNonce::from_bytes(
            hex_bytes(
                data["proposal_nonce_hex"]
                    .as_str()
                    .expect("the JSON fixture field is a string"),
            )
            .try_into()
            .expect("the fixture slice has the target length"),
        ),
        quoted_content_digest: hex_bytes(
            data["quoted_content_digest_hex"]
                .as_str()
                .expect("the JSON fixture field is a string"),
        )
        .try_into()
        .expect("the fixture slice has the target length"),
        quoted_resource_contract_digest: hex_bytes(
            data["quoted_resource_contract_digest_hex"]
                .as_str()
                .expect("the JSON fixture field is a string"),
        )
        .try_into()
        .expect("the fixture slice has the target length"),
        parameters: data["parameters"]
            .as_array()
            .expect("the JSON fixture field is an array")
            .iter()
            .map(|parameter| babylon_practice_contract::PracticeParameter {
                key_u8: u8::try_from(
                    parameter["key_u8"]
                        .as_u64()
                        .expect("the JSON fixture field is an unsigned integer"),
                )
                .expect("the fixture value fits the target range"),
                value_kind_u8: u8::try_from(
                    parameter["value_kind_u8"]
                        .as_u64()
                        .expect("the JSON fixture field is an unsigned integer"),
                )
                .expect("the fixture value fits the target range"),
                value_length_u16: u16::try_from(
                    parameter["value_length_u16"]
                        .as_u64()
                        .expect("the JSON fixture field is an unsigned integer"),
                )
                .expect("the fixture value fits the target range"),
                value_bytes: parameter["value_bytes"]
                    .as_array()
                    .expect("the JSON fixture field is an array")
                    .iter()
                    .map(|value| {
                        u8::try_from(
                            value
                                .as_u64()
                                .expect("the JSON fixture field is an unsigned integer"),
                        )
                        .expect("the fixture value fits the target range")
                    })
                    .collect(),
            })
            .collect(),
        evidence_digests: data["evidence_digests_hex"]
            .as_array()
            .expect("the JSON fixture field is an array")
            .iter()
            .take(65)
            .map(|digest| {
                hex_bytes(digest.as_str().expect("the JSON fixture field is a string"))
                    .try_into()
                    .expect("the fixture slice has the target length")
            })
            .collect(),
    }
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`intent_schema_and_vectors_drive_the_rust_boundary` keeps one authored boundary's fixture and assertions together"
)]
fn intent_schema_and_vectors_drive_the_rust_boundary() {
    assert_eq!(
        babylon_kernel::content_digest::sha256_of(SCHEMA),
        PRACTICE_INTENT_SOURCE_SHA256
    );
    let cases: Vec<Value> = VECTORS
        .lines()
        .take(65)
        .map(|line| {
            assert!(line.len() <= 4_096);
            serde_json::from_str(line).expect("the authored JSON matches the declared schema")
        })
        .collect();
    assert_eq!(cases.len(), 17);

    let intent_case = cases
        .iter()
        .find(|case| case["case_id"] == "intent-strike")
        .expect("the fixture holds the searched element");
    let intent = intent_from_vector(&intent_case["data"]);
    let canonical = hex_bytes(
        intent_case["data"]["canonical_hex"]
            .as_str()
            .expect("the JSON fixture field is a string"),
    );
    assert_eq!(canonical.len(), 251);
    assert_eq!(
        encode_practice_intent(&intent).expect("the practice intent encodes canonically"),
        canonical
    );
    assert_eq!(
        decode_practice_intent(&canonical).expect("the practice intent bytes decode"),
        intent
    );
    assert_eq!(
        practice_intent_digest(&intent)
            .expect("the practice intent has a digest")
            .to_vec(),
        hex_bytes(
            intent_case["data"]["digest_hex"]
                .as_str()
                .expect("the JSON fixture field is a string")
        )
    );

    assert_eq!(
        practice_parameter_bytes_digest(&intent)
            .expect("the parameter bytes have a digest")
            .as_slice(),
        hex_bytes(
            intent_case["data"]["parameter_digest_hex"]
                .as_str()
                .expect("the JSON fixture field is a string")
        )
    );
    assert_eq!(
        fixed_practice_target_digest(intent.target.tag, intent.target.identity).as_slice(),
        hex_bytes(
            intent_case["data"]["fixed_target_digest_hex"]
                .as_str()
                .expect("the JSON fixture field is a string")
        )
    );
    let mut unsupported_domain = canonical.clone();
    unsupported_domain[babylon_practice_contract::PRACTICE_INTENT_DOMAIN_BYTES.len() - 1] = b'1';
    assert_eq!(
        decode_practice_intent(&unsupported_domain),
        Err(PracticeIntentError::IntentDomain)
    );

    for case in cases.iter().filter(|case| case["kind"] == "intent") {
        let value = intent_from_vector(&case["data"]);
        let bytes = hex_bytes(
            case["data"]["canonical_hex"]
                .as_str()
                .expect("the JSON fixture field is a string"),
        );
        assert_eq!(
            encode_practice_intent(&value).expect("the practice intent encodes canonically"),
            bytes
        );
        assert_eq!(
            decode_practice_intent(&bytes).expect("the practice intent bytes decode"),
            value
        );
        assert_eq!(
            practice_intent_digest(&value)
                .expect("the practice intent has a digest")
                .as_slice(),
            hex_bytes(
                case["data"]["digest_hex"]
                    .as_str()
                    .expect("the JSON fixture field is a string")
            )
        );
        assert_eq!(
            practice_parameter_bytes_digest(&value)
                .expect("the parameter bytes have a digest")
                .as_slice(),
            hex_bytes(
                case["data"]["parameter_digest_hex"]
                    .as_str()
                    .expect("the JSON fixture field is a string")
            )
        );
        assert_eq!(
            fixed_practice_target_digest(value.target.tag, value.target.identity).as_slice(),
            hex_bytes(
                case["data"]["fixed_target_digest_hex"]
                    .as_str()
                    .expect("the JSON fixture field is a string")
            )
        );
    }

    for case in cases.iter().filter(|case| case["kind"] == "invalid_wire") {
        let payload = hex_bytes(
            case["data"]["payload_hex"]
                .as_str()
                .expect("the JSON fixture field is a string"),
        );
        let expected = PracticeIntentError::try_from(
            u16::try_from(
                case["data"]["error"]
                    .as_u64()
                    .expect("the JSON fixture field is an unsigned integer"),
            )
            .expect("the fixture value fits the target range"),
        )
        .expect("the fixture value fits the target range");
        assert_eq!(decode_practice_intent(&payload).map(|_| ()), Err(expected));
    }
}
