use babylon_practice_contract::{
    decode_input_authority, encode_resolved_practice_batch, resolved_practice_batch_digest,
    PracticeBatchError, PracticeInputAuthorityLedger, ResolvedPracticeBatchError,
    RESOLVED_PRACTICE_BATCH_FIELD_ORDER, RESOLVED_PRACTICE_BATCH_SOURCE_SHA256,
};
use serde_json::Value;

const SCHEMA: &[u8] = include_bytes!("../../../../contracts/resolved_practice_batch.yaml");
const VECTORS: &str = include_str!("../../../../contracts/resolved_practice_batch_vectors.jsonl");
const AUTHORITY_VECTORS: &str =
    include_str!("../../../../contracts/practice_input_authority_vectors.jsonl");

fn hex_bytes(value: &str) -> Vec<u8> {
    assert_eq!(value.len() % 2, 0);
    value
        .as_bytes()
        .chunks_exact(2)
        .map(|chunk| {
            let text = std::str::from_utf8(chunk).expect("hex fixture is ASCII");
            u8::from_str_radix(text, 16).expect("hex fixture is valid")
        })
        .collect()
}

fn parse_cases(source: &str) -> Vec<Value> {
    source
        .lines()
        .take(65)
        .map(|line| {
            assert!(line.len() <= 65_536);
            serde_json::from_str(line).expect("the authored JSON matches the declared schema")
        })
        .collect()
}

fn authority_ledger() -> PracticeInputAuthorityLedger {
    let cases = parse_cases(AUTHORITY_VECTORS);
    let row = cases
        .iter()
        .find(|case| case["case_id"] == "authority-player")
        .expect("the fixture holds the searched element");
    PracticeInputAuthorityLedger {
        schema_version: 2,
        rows: vec![decode_input_authority(&hex_bytes(
            row["data"]["canonical_hex"]
                .as_str()
                .expect("the JSON fixture field is a string"),
        ))
        .expect("the canonical bytes decode into the declared type")],
    }
}

#[test]
fn resolved_batch_schema_and_vectors_drive_the_rust_boundary() {
    assert_eq!(
        babylon_kernel::content_digest::sha256_of(SCHEMA),
        RESOLVED_PRACTICE_BATCH_SOURCE_SHA256
    );
    let cases = parse_cases(VECTORS);
    assert_eq!(cases.len(), 14);

    let manifest = cases
        .iter()
        .find(|case| case["case_id"] == "manifest")
        .expect("the fixture holds the searched element");
    let valid = cases
        .iter()
        .find(|case| case["case_id"] == "batch-one")
        .expect("the fixture holds the searched element");
    let canonical = hex_bytes(
        valid["data"]["canonical_hex"]
            .as_str()
            .expect("the JSON fixture field is a string"),
    );
    let ledger = authority_ledger();
    let batch = babylon_practice_contract::decode_resolved_practice_batch(&canonical, &ledger)
        .expect("the canonical bytes decode into the declared type");

    assert_eq!(manifest["data"]["canonical_example_bytes"], canonical.len());
    assert_eq!(manifest["data"]["max_items"], 4_096);
    assert_eq!(manifest["data"]["authority_row_bytes"], 127);
    assert_eq!(manifest["data"]["max_batch_bytes"], 67_645_599);
    assert_eq!(
        encode_resolved_practice_batch(&batch, &ledger)
            .expect("the fixture value encodes to its canonical bytes"),
        canonical
    );
    assert_eq!(
        resolved_practice_batch_digest(&batch, &ledger)
            .expect("the fixture call `resolved_practice_batch_digest` succeeds for the authored inputs")
            .to_vec(),
        hex_bytes(valid["data"]["digest_hex"].as_str().expect("the JSON fixture field is a string"))
    );

    for case in cases.iter().filter(|case| case["kind"] == "invalid_wire") {
        let payload = hex_bytes(
            case["data"]["payload_hex"]
                .as_str()
                .expect("the JSON fixture field is a string"),
        );
        let expected = PracticeBatchError::try_from(
            u16::try_from(
                case["data"]["error"]
                    .as_u64()
                    .expect("the JSON fixture field is an unsigned integer"),
            )
            .expect("the fixture value fits the target range"),
        )
        .expect("the fixture value fits the target range");
        assert_eq!(
            babylon_practice_contract::decode_resolved_practice_batch(&payload, &ledger)
                .map(|_| ()),
            Err(ResolvedPracticeBatchError::Batch(expected))
        );
    }
}

#[test]
fn resolved_batch_digest_is_derived_and_absent_from_its_preimage() {
    let cases = parse_cases(VECTORS);
    let valid = cases
        .iter()
        .find(|case| case["case_id"] == "batch-one")
        .expect("the fixture holds the searched element");
    let canonical = hex_bytes(
        valid["data"]["canonical_hex"]
            .as_str()
            .expect("the JSON fixture field is a string"),
    );
    let digest = hex_bytes(
        valid["data"]["digest_hex"]
            .as_str()
            .expect("the JSON fixture field is a string"),
    );

    assert_eq!(digest.len(), 32);
    assert_eq!(
        babylon_kernel::content_digest::sha256_of(&canonical).to_vec(),
        digest
    );
    assert!(!RESOLVED_PRACTICE_BATCH_FIELD_ORDER.contains(&"batch_digest"));
}
