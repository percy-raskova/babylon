use std::collections::{BTreeMap, BTreeSet};

use babylon_kernel::tick_content_hash::TickContentHashV1;
use babylon_persistence::committed_tick_envelope::{
    validate_committed_tick_envelope_bounds_v1, CommittedTickEnvelopeConflictV1,
    CommittedTickEnvelopeErrorV1, CommittedTickEnvelopeRetryV1, CommittedTickEnvelopeV1,
    CommittedTickRowFamiliesV1, CommittedTickRowFamilyV1, CommittedTickRowV1,
    ALL_COMMITTED_TICK_ROW_FAMILIES_V1, MAX_COMMITTED_TICK_ENVELOPE_BYTES_V1,
    MAX_COMMITTED_TICK_ROWS_V1, MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1,
};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::tick_commit_claim::TickCommitClaimConflictV1;
use babylon_persistence::tick_commit_claim::TickCommitClaimV1;
use serde::Deserialize;
use serde_json::Value;
use uuid::Uuid;

const VECTORS: &str =
    include_str!("../../../../contracts/committed_tick_envelope_v1_vectors.jsonl");
const MAX_VECTOR_ROWS: usize = 64;
const MAX_VECTOR_LINE_BYTES: usize = 16_384;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct VectorRow {
    id: String,
    kind: String,
    data: Value,
}

fn vector_rows() -> Vec<VectorRow> {
    let input = VECTORS.strip_suffix('\n').unwrap_or(VECTORS);
    let mut rows = Vec::with_capacity(MAX_VECTOR_ROWS);
    let mut ids = BTreeSet::new();
    for (index, line) in input.split('\n').take(MAX_VECTOR_ROWS + 1).enumerate() {
        assert!(index < MAX_VECTOR_ROWS, "bounded vector row count");
        assert!(!line.is_empty() && line.len() <= MAX_VECTOR_LINE_BYTES);
        let row: VectorRow = serde_json::from_str(line).expect("valid bounded vector row");
        assert!(ids.insert(row.id.clone()), "unique vector id");
        rows.push(row);
    }
    rows
}

fn text<'a>(data: &'a Value, field: &str) -> &'a str {
    data[field].as_str().expect("text field")
}

fn hex_bytes(value: &str) -> Vec<u8> {
    assert!(value.len() <= MAX_VECTOR_LINE_BYTES && value.len().is_multiple_of(2));
    value
        .as_bytes()
        .chunks_exact(2)
        .take(MAX_VECTOR_LINE_BYTES / 2)
        .map(|chunk| {
            let text = std::str::from_utf8(chunk).expect("ASCII hex");
            u8::from_str_radix(text, 16).expect("hex byte")
        })
        .collect()
}

fn hex32(value: &str) -> [u8; 32] {
    hex_bytes(value).try_into().expect("exact digest32")
}

fn vector_claim(data: &Value) -> TickCommitClaimV1 {
    TickCommitClaimV1::compose(
        CampaignId::from_uuid(
            Uuid::parse_str(text(data, "campaign_id")).expect("canonical campaign UUID"),
        ),
        data["resolve_tick"].as_u64().expect("u64 resolve tick"),
        TickContentHashV1::from_bytes(hex32(text(data, "tick_content_hash_hex"))),
    )
}

fn family_rows(
    data: &Value,
    family: &str,
) -> Result<Vec<CommittedTickRowV1>, CommittedTickEnvelopeErrorV1> {
    let rows = data["families"][family]
        .as_array()
        .expect("family row array");
    assert!(rows.len() <= MAX_VECTOR_ROWS);
    rows.iter()
        .take(MAX_VECTOR_ROWS)
        .map(|row| {
            CommittedTickRowV1::compose(
                hex_bytes(text(row, "key_hex")),
                hex_bytes(text(row, "payload_hex")),
            )
        })
        .collect()
}

fn vector_envelope(data: &Value) -> Result<CommittedTickEnvelopeV1, CommittedTickEnvelopeErrorV1> {
    let families = CommittedTickRowFamiliesV1 {
        graph: family_rows(data, "graph")?,
        state: family_rows(data, "state")?,
        event: family_rows(data, "event")?,
        subsystem: family_rows(data, "subsystem")?,
        conservation: family_rows(data, "conservation")?,
        boundary_flow: family_rows(data, "boundary_flow")?,
        checkpoint: family_rows(data, "checkpoint")?,
        archive_dirty_receipt: family_rows(data, "archive_dirty_receipt")?,
    };
    CommittedTickEnvelopeV1::compose(vector_claim(data), families)
}

fn envelopes(rows: &[VectorRow]) -> BTreeMap<&str, CommittedTickEnvelopeV1> {
    rows.iter()
        .take(MAX_VECTOR_ROWS)
        .filter(|row| row.kind == "envelope")
        .map(|row| {
            (
                row.id.as_str(),
                vector_envelope(&row.data).expect("valid shared envelope"),
            )
        })
        .collect()
}

fn envelope_error_code(error: &CommittedTickEnvelopeErrorV1) -> &'static str {
    match error {
        CommittedTickEnvelopeErrorV1::EmptyRowKey => "invalid_row_hex",
        CommittedTickEnvelopeErrorV1::DuplicateRowKey { .. } => "duplicate_row_key",
        CommittedTickEnvelopeErrorV1::RowOrder { .. } => "row_order",
        CommittedTickEnvelopeErrorV1::BatchBytes { .. } => "batch_bytes",
        CommittedTickEnvelopeErrorV1::AggregateRows { .. } => "aggregate_rows",
        CommittedTickEnvelopeErrorV1::BatchShape { .. } => "batch_shape",
        CommittedTickEnvelopeErrorV1::EnvelopeBytes { .. } => "envelope_bytes",
        CommittedTickEnvelopeErrorV1::CapacityOverflow { .. } => "capacity_overflow",
        CommittedTickEnvelopeErrorV1::IntegerConversion { .. } => "integer_conversion",
        CommittedTickEnvelopeErrorV1::Allocation { .. } => "allocation",
        CommittedTickEnvelopeErrorV1::CanonicalLength { .. } => "canonical_length",
    }
}

fn usize_array(data: &Value, field: &str) -> [usize; 8] {
    data[field]
        .as_array()
        .expect("bound array")
        .iter()
        .take(8)
        .map(|value| usize::try_from(value.as_u64().expect("bound u64")).expect("bound usize"))
        .collect::<Vec<_>>()
        .try_into()
        .expect("exact eight bounds")
}

fn claim(campaign: u128, tick: u64, content: u8) -> TickCommitClaimV1 {
    TickCommitClaimV1::compose(
        CampaignId::from_uuid(Uuid::from_u128(campaign)),
        tick,
        TickContentHashV1::from_bytes([content; 32]),
    )
}

fn row(key: u8, payload: u8) -> CommittedTickRowV1 {
    CommittedTickRowV1::compose(vec![key], vec![payload]).expect("bounded canonical row")
}

fn singleton_families(payload: u8) -> CommittedTickRowFamiliesV1 {
    CommittedTickRowFamiliesV1 {
        graph: vec![row(0x01, payload)],
        state: vec![row(0x02, payload)],
        event: vec![row(0x03, payload)],
        subsystem: vec![row(0x04, payload)],
        conservation: vec![row(0x05, payload)],
        boundary_flow: vec![row(0x06, payload)],
        checkpoint: vec![row(0x07, payload)],
        archive_dirty_receipt: vec![row(0x08, payload)],
    }
}

fn mutate_family(families: &mut CommittedTickRowFamiliesV1, family: CommittedTickRowFamilyV1) {
    let replacement = vec![row(0x01, 0xff)];
    match family {
        CommittedTickRowFamilyV1::Graph => families.graph = replacement,
        CommittedTickRowFamilyV1::State => families.state = replacement,
        CommittedTickRowFamilyV1::Event => families.event = replacement,
        CommittedTickRowFamilyV1::Subsystem => families.subsystem = replacement,
        CommittedTickRowFamilyV1::Conservation => families.conservation = replacement,
        CommittedTickRowFamilyV1::BoundaryFlow => families.boundary_flow = replacement,
        CommittedTickRowFamilyV1::Checkpoint => families.checkpoint = replacement,
        CommittedTickRowFamilyV1::ArchiveDirtyReceipt => {
            families.archive_dirty_receipt = replacement;
        }
    }
}

#[test]
fn zero_row_tick_still_has_a_complete_eight_family_envelope() {
    let envelope = CommittedTickEnvelopeV1::compose(
        claim(0x0011_2233_4455_6677_8899_aabb_ccdd_eeff, 42, 0x11),
        CommittedTickRowFamiliesV1::default(),
    )
    .expect("zero-row envelope");

    assert_eq!(envelope.total_rows(), 0);
    assert_eq!(envelope.row_families().len(), 8);
    assert!(envelope.canonical_bytes().len() < MAX_COMMITTED_TICK_ENVELOPE_BYTES_V1);
}

#[test]
fn every_mandatory_row_family_moves_whole_payload_identity() {
    let base = CommittedTickEnvelopeV1::compose(claim(1, 42, 0x11), singleton_families(0xaa))
        .expect("base envelope");

    for family in ALL_COMMITTED_TICK_ROW_FAMILIES_V1.iter().take(8).copied() {
        let mut mutated_rows = singleton_families(0xaa);
        mutate_family(&mut mutated_rows, family);
        let mutated = CommittedTickEnvelopeV1::compose(claim(1, 42, 0x11), mutated_rows)
            .expect("mutated envelope");
        assert_ne!(
            base.canonical_bytes(),
            mutated.canonical_bytes(),
            "{family:?}"
        );
        assert_ne!(base.digest(), mutated.digest(), "{family:?}");
    }
}

#[test]
fn retry_requires_exact_whole_payload_bytes() {
    let existing = CommittedTickEnvelopeV1::compose(claim(1, 42, 0x11), singleton_families(0xaa))
        .expect("existing envelope");
    let identical = CommittedTickEnvelopeV1::compose(claim(1, 42, 0x11), singleton_families(0xaa))
        .expect("identical retry");
    let payload_conflict =
        CommittedTickEnvelopeV1::compose(claim(1, 42, 0x11), singleton_families(0xbb))
            .expect("payload conflict");
    let content_conflict =
        CommittedTickEnvelopeV1::compose(claim(1, 42, 0x22), singleton_families(0xaa))
            .expect("content conflict");
    let key_conflict =
        CommittedTickEnvelopeV1::compose(claim(1, 43, 0x11), singleton_families(0xaa))
            .expect("key conflict");

    assert_eq!(
        identical.classify_retry_against(&existing),
        Ok(CommittedTickEnvelopeRetryV1::Idempotent)
    );
    assert!(matches!(
        payload_conflict.classify_retry_against(&existing),
        Err(CommittedTickEnvelopeConflictV1::WholePayloadMismatch { .. })
    ));
    assert!(matches!(
        content_conflict.classify_retry_against(&existing),
        Err(CommittedTickEnvelopeConflictV1::Claim(_))
    ));
    assert!(matches!(
        key_conflict.classify_retry_against(&existing),
        Err(CommittedTickEnvelopeConflictV1::Claim(_))
    ));
}

#[test]
fn row_keys_are_nonempty_unique_and_strictly_ordered() {
    assert!(matches!(
        CommittedTickRowV1::compose(Vec::new(), vec![1]),
        Err(CommittedTickEnvelopeErrorV1::EmptyRowKey)
    ));

    let duplicate = CommittedTickRowFamiliesV1 {
        graph: vec![row(1, 1), row(1, 2)],
        ..CommittedTickRowFamiliesV1::default()
    };
    assert!(matches!(
        CommittedTickEnvelopeV1::compose(claim(1, 1, 1), duplicate),
        Err(CommittedTickEnvelopeErrorV1::DuplicateRowKey { .. })
    ));

    let descending = CommittedTickRowFamiliesV1 {
        graph: vec![row(2, 1), row(1, 2)],
        ..CommittedTickRowFamiliesV1::default()
    };
    assert!(matches!(
        CommittedTickEnvelopeV1::compose(claim(1, 1, 1), descending),
        Err(CommittedTickEnvelopeErrorV1::RowOrder { .. })
    ));
}

#[test]
fn cumulative_bounds_accept_exact_maxima_and_refuse_maximum_plus_one() {
    assert_eq!(
        validate_committed_tick_envelope_bounds_v1(
            [1; 8],
            [MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1; 8],
        )
        .expect("exact byte maximum"),
        MAX_COMMITTED_TICK_ENVELOPE_BYTES_V1
    );
    assert!(matches!(
        validate_committed_tick_envelope_bounds_v1(
            [1; 8],
            [MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1 + 1; 8],
        ),
        Err(CommittedTickEnvelopeErrorV1::BatchBytes { .. })
    ));

    let mut maximum_rows = [0_usize; 8];
    maximum_rows[0] = MAX_COMMITTED_TICK_ROWS_V1;
    let mut minimum_bodies = [0_usize; 8];
    minimum_bodies[0] = MAX_COMMITTED_TICK_ROWS_V1 * 9;
    assert!(validate_committed_tick_envelope_bounds_v1(maximum_rows, minimum_bodies).is_ok());
    maximum_rows[0] += 1;
    minimum_bodies[0] += 9;
    assert!(matches!(
        validate_committed_tick_envelope_bounds_v1(maximum_rows, minimum_bodies),
        Err(CommittedTickEnvelopeErrorV1::AggregateRows { .. })
    ));

    assert!(matches!(
        validate_committed_tick_envelope_bounds_v1(
            [2, 0, 0, 0, 0, 0, 0, 0],
            [9, 0, 0, 0, 0, 0, 0, 0]
        ),
        Err(CommittedTickEnvelopeErrorV1::BatchShape { .. })
    ));
}

#[test]
fn production_envelope_reconstructs_every_shared_golden() {
    let rows = vector_rows();
    let kinds: BTreeSet<&str> = rows.iter().map(|row| row.kind.as_str()).collect();
    assert_eq!(
        kinds,
        BTreeSet::from(["bound", "envelope", "mutation", "refusal", "retry"])
    );
    for row in rows
        .iter()
        .take(MAX_VECTOR_ROWS)
        .filter(|row| row.kind == "envelope")
    {
        let envelope = vector_envelope(&row.data).expect("shared envelope");
        assert_eq!(
            envelope.canonical_bytes(),
            hex_bytes(text(&row.data, "canonical_hex")),
            "{}",
            row.id
        );
        assert_eq!(
            envelope.digest().as_bytes(),
            &hex32(text(&row.data, "sha256_hex")),
            "{}",
            row.id
        );
    }
}

#[test]
fn production_mutations_and_retries_match_the_shared_contract() {
    let rows = vector_rows();
    let envelopes = envelopes(&rows);
    for row in rows.iter().take(MAX_VECTOR_ROWS) {
        if row.kind == "mutation" {
            let base = &envelopes[text(&row.data, "base_id")];
            let mutated = &envelopes[text(&row.data, "mutated_id")];
            assert_ne!(
                base.canonical_bytes(),
                mutated.canonical_bytes(),
                "{}",
                row.id
            );
        }
        if row.kind == "retry" {
            let requested = &envelopes[text(&row.data, "requested_id")];
            let existing = &envelopes[text(&row.data, "existing_id")];
            let result = requested.classify_retry_against(existing);
            match text(&row.data, "expected") {
                "idempotent" => assert_eq!(result, Ok(CommittedTickEnvelopeRetryV1::Idempotent)),
                "key_mismatch" => assert!(matches!(
                    result,
                    Err(CommittedTickEnvelopeConflictV1::Claim(
                        TickCommitClaimConflictV1::KeyMismatch { .. }
                    ))
                )),
                "content_identity_mismatch" => assert!(matches!(
                    result,
                    Err(CommittedTickEnvelopeConflictV1::Claim(
                        TickCommitClaimConflictV1::ContentIdentityMismatch { .. }
                    ))
                )),
                "whole_payload_mismatch" => assert!(matches!(
                    result,
                    Err(CommittedTickEnvelopeConflictV1::WholePayloadMismatch { .. })
                )),
                unexpected => panic!("unknown retry outcome: {unexpected}"),
            }
        }
    }
}

#[test]
fn production_refusal_and_bound_operations_match_the_shared_contract() {
    let rows = vector_rows();
    for row in rows.iter().take(MAX_VECTOR_ROWS) {
        if row.kind == "refusal" {
            let error = vector_envelope(&row.data).expect_err("shared refusal");
            assert_eq!(
                envelope_error_code(&error),
                text(&row.data, "expected_code"),
                "{}",
                row.id
            );
        }
        if row.kind == "bound" {
            let result = validate_committed_tick_envelope_bounds_v1(
                usize_array(&row.data, "row_counts"),
                usize_array(&row.data, "batch_body_bytes"),
            );
            if let Some(expected) = row.data.get("expected_code") {
                let error = result.expect_err("shared bound refusal");
                assert_eq!(envelope_error_code(&error), expected.as_str().unwrap());
            } else {
                assert_eq!(
                    result.expect("shared accepted bound"),
                    usize::try_from(row.data["expected_bytes"].as_u64().unwrap()).unwrap()
                );
            }
        }
    }
}
