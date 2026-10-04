use super::*;
use crate::committed_tick_envelope::{
    CommittedTickEnvelopeError, CommittedTickRow, CommittedTickRowFamily,
};

fn row(key: u8, payload: Vec<u8>) -> CommittedTickRow {
    CommittedTickRow::compose(vec![key], payload).unwrap()
}
fn families() -> CommittedTickRowFamilies {
    CommittedTickRowFamilies {
        graph: vec![row(1, vec![0x10, 0, 0xff]), row(2, vec![0x55; 65_537])],
        state: vec![row(3, vec![0x20])],
        event: vec![],
        choice_receipt: vec![row(4, vec![0x30, 0x31])],
        checkpoint: vec![row(5, vec![0; 65_536]), row(6, vec![0x40])],
        archive_dirty_receipt: row(7, vec![0x50]),
    }
}
fn identity(receipts: &[u8]) -> IdentifiedMaterialTick {
    // This module owns opaque row framing. Semantic admission belongs to the
    // producer and authenticated consumer; these rows do not bypass either.
    let mut bytes = b"babylon.material-tick-content.v3\0".to_vec();
    bytes.extend_from_slice(&3_u32.to_be_bytes());
    bytes.extend_from_slice(&7_u64.to_be_bytes());
    for value in 1..=6 {
        bytes.extend_from_slice(&[value; 32]);
    }
    bytes.extend_from_slice(&sha256_of(receipts));
    IdentifiedMaterialTick::decode(&bytes).unwrap()
}
fn campaign() -> CampaignId {
    CampaignId::from_uuid(uuid::Uuid::from_u128(0x1234))
}

#[test]
fn streamed_envelope_matches_independent_v3_bytes_and_digest() {
    let register = vec![0x91; 65_537];
    let receipts = vec![0xa3; 65_535];
    let identity = identity(&receipts);
    let complete = CommittedMaterialTickEnvelope::compose(
        campaign(),
        &identity,
        families(),
        &register,
        &receipts,
    )
    .unwrap();
    let attested = CommittedMaterialTickEnvelope::attest(
        campaign(),
        &identity,
        families(),
        &register,
        &receipts,
    )
    .unwrap();
    // Independently constructed by vector-construction.py: a new conformance
    // control, with no change to the existing format or governed baseline.
    assert_eq!(complete.canonical_bytes().len(), 262_399);
    assert_eq!(
        crate::michigan_economy::digest_hex(&complete.digest()),
        "14685bd2c116676a2c1b021175abfb771cc78414eb3aa5aaf739b4475dc83202"
    );
    assert_eq!(attested.digest(), complete.digest());
    assert_eq!(attested.encoded_bytes(), complete.canonical_bytes().len());
}

#[test]
fn streamed_envelope_covers_buffer_boundaries_and_every_family() {
    for length in [0, 1, 63, 64, 65_535, 65_536, 65_537, 130_000] {
        let register = vec![0x91; length];
        let receipts = vec![0xa3; length];
        let identity = identity(&receipts);
        let complete = CommittedMaterialTickEnvelope::compose(
            campaign(),
            &identity,
            families(),
            &register,
            &receipts,
        )
        .unwrap();
        let attested = CommittedMaterialTickEnvelope::attest(
            campaign(),
            &identity,
            families(),
            &register,
            &receipts,
        )
        .unwrap();
        assert_eq!(attested.digest(), complete.digest(), "length={length}");
        assert_eq!(attested.encoded_bytes(), complete.canonical_bytes().len());
    }
    let register = vec![0x91; 65_537];
    let receipts = vec![0xa3; 65_535];
    let identity = identity(&receipts);
    let expected = CommittedMaterialTickEnvelope::attest(
        campaign(),
        &identity,
        families(),
        &register,
        &receipts,
    )
    .unwrap()
    .digest();
    for family in 0..8 {
        let mut families = families();
        let mut register = register.clone();
        let mut receipts = receipts.clone();
        match family {
            0 => families.graph[0] = row(1, vec![0x11, 0, 0xff]),
            1 => families.state[0] = row(3, vec![0x21]),
            2 => families.event.push(row(8, vec![0x22])),
            3 => families.choice_receipt[0] = row(4, vec![0x32, 0x31]),
            4 => families.checkpoint[1] = row(6, vec![0x41]),
            5 => families.archive_dirty_receipt = row(7, vec![0x51]),
            6 => register[0] ^= 1,
            7 => receipts[0] ^= 1,
            _ => unreachable!(),
        }
        let identity = if family == 7 {
            self::identity(&receipts)
        } else {
            identity
        };
        let changed = CommittedMaterialTickEnvelope::attest(
            campaign(),
            &identity,
            families,
            &register,
            &receipts,
        )
        .unwrap();
        assert_ne!(changed.digest(), expected, "family={family}");
    }
    assert_ne!(
        CommittedMaterialTickEnvelope::attest(
            CampaignId::from_uuid(uuid::Uuid::from_u128(0x1235)),
            &identity,
            families(),
            &register,
            &receipts,
        )
        .unwrap()
        .digest(),
        expected
    );
    let mut alternate = identity.canonical_bytes().to_vec();
    let offset = b"babylon.material-tick-content.v3\0".len() + 4;
    alternate[offset..offset + 8].copy_from_slice(&8_u64.to_be_bytes());
    let alternate = IdentifiedMaterialTick::decode(&alternate).unwrap();
    assert_ne!(
        CommittedMaterialTickEnvelope::attest(
            campaign(),
            &alternate,
            families(),
            &register,
            &receipts,
        )
        .unwrap()
        .digest(),
        expected
    );
}

#[test]
fn streamed_envelope_covers_empty_optional_families() {
    let empty = CommittedTickRowFamilies {
        graph: vec![],
        state: vec![],
        event: vec![],
        choice_receipt: vec![],
        checkpoint: vec![],
        archive_dirty_receipt: row(1, vec![]),
    };
    let identity = self::identity(&[]);
    let complete =
        CommittedMaterialTickEnvelope::compose(campaign(), &identity, empty, &[], &[]).unwrap();
    let empty = CommittedTickRowFamilies {
        graph: vec![],
        state: vec![],
        event: vec![],
        choice_receipt: vec![],
        checkpoint: vec![],
        archive_dirty_receipt: row(1, vec![]),
    };
    let attested =
        CommittedMaterialTickEnvelope::attest(campaign(), &identity, empty, &[], &[]).unwrap();
    assert_eq!(attested.digest(), complete.digest());
    assert_eq!(attested.encoded_bytes(), complete.canonical_bytes().len());
}

#[test]
fn streamed_envelope_retains_receipt_binding_and_row_order_refusals() {
    let register = vec![0x91; 32];
    let receipts = vec![0xa3; 32];
    let identity = identity(&receipts);
    let mut changed = receipts.clone();
    changed[0] ^= 1;
    assert!(matches!(
        CommittedMaterialTickEnvelope::compose(
            campaign(),
            &identity,
            families(),
            &register,
            &changed,
        ),
        Err(RustPersistenceRuntimeError::CampaignConflict)
    ));
    assert!(matches!(
        CommittedMaterialTickEnvelope::attest(
            campaign(),
            &identity,
            families(),
            &register,
            &changed,
        ),
        Err(RustPersistenceRuntimeError::CampaignConflict)
    ));
    for duplicate in [false, true] {
        let changed = || {
            let mut families = families();
            if duplicate {
                families.graph[1] = row(1, vec![0x12]);
            } else {
                families.graph.swap(0, 1);
            }
            families
        };
        let complete = CommittedMaterialTickEnvelope::compose(
            campaign(),
            &identity,
            changed(),
            &register,
            &receipts,
        )
        .unwrap_err();
        let error = CommittedMaterialTickEnvelope::attest(
            campaign(),
            &identity,
            changed(),
            &register,
            &receipts,
        )
        .unwrap_err();
        let (
            RustPersistenceRuntimeError::SemanticEnvelope(complete),
            RustPersistenceRuntimeError::SemanticEnvelope(error),
        ) = (complete, error)
        else {
            panic!("both sinks must preserve the specific row refusal");
        };
        assert_eq!(complete, error);
        assert!(matches!(
            (duplicate, error),
            (
                true,
                CommittedTickEnvelopeError::DuplicateRowKey {
                    family: CommittedTickRowFamily::Graph,
                    index: 1
                }
            ) | (
                false,
                CommittedTickEnvelopeError::RowOrder {
                    family: CommittedTickRowFamily::Graph,
                    index: 1
                }
            )
        ));
    }
}

#[test]
fn streamed_envelope_preserves_actual_family_body_ceiling_refusals() {
    let maximum = CommittedTickRowFamily::State.maximum_body_bytes();
    let families = || CommittedTickRowFamilies {
        graph: vec![],
        state: vec![row(1, vec![0; maximum - 8])],
        event: vec![],
        choice_receipt: vec![],
        checkpoint: vec![],
        archive_dirty_receipt: row(1, vec![]),
    };
    let identity = identity(&[]);
    let complete =
        CommittedMaterialTickEnvelope::compose(campaign(), &identity, families(), &[], &[])
            .unwrap_err();
    let attested =
        CommittedMaterialTickEnvelope::attest(campaign(), &identity, families(), &[], &[])
            .unwrap_err();
    let (
        RustPersistenceRuntimeError::SemanticEnvelope(complete),
        RustPersistenceRuntimeError::SemanticEnvelope(attested),
    ) = (complete, attested)
    else {
        panic!("both sinks must preserve the specific body bound refusal");
    };
    assert_eq!(complete, attested);
    assert_eq!(
        attested,
        CommittedTickEnvelopeError::BatchBytes {
            family: CommittedTickRowFamily::State,
            actual: maximum + 1,
            maximum,
        }
    );
}

#[test]
fn streamed_envelope_refuses_incomplete_or_excess_framing() {
    let mut short = BoundedSink::new(BufferedDigest::new().unwrap(), 3);
    short.append(&[1, 2]).unwrap();
    assert!(matches!(
        short.finish(),
        Err(RustPersistenceRuntimeError::CampaignConflict)
    ));
    let mut long = BoundedSink::new(BufferedDigest::new().unwrap(), 1);
    assert!(matches!(
        long.append(&[1, 2]),
        Err(RustPersistenceRuntimeError::CampaignConflict)
    ));
    assert!(matches!(
        long.finish(),
        Err(RustPersistenceRuntimeError::CampaignConflict)
    ));
    let mut overrun = BoundedSink::new(BufferedDigest::new().unwrap(), 1);
    overrun.append(&[1]).unwrap();
    assert!(matches!(
        overrun.append(&[2]),
        Err(RustPersistenceRuntimeError::CampaignConflict)
    ));
    assert!(matches!(
        overrun.finish(),
        Err(RustPersistenceRuntimeError::CampaignConflict)
    ));
    let mut exact = BoundedSink::new(BufferedDigest::new().unwrap(), 3);
    exact.append(&[1]).unwrap();
    exact.append(&[2, 3]).unwrap();
    assert_eq!(exact.finish().unwrap(), sha256_of(&[1, 2, 3]));
}

#[test]
fn streamed_envelope_chunk_partitions_preserve_concat_and_bound_scratch() {
    let bytes: Vec<u8> = (0_u8..=255).cycle().take(262_145).collect();
    for chunk_bytes in [1, 3, 63, 64, 65_535, 65_536, 65_537, 130_000, 262_145] {
        let mut sink = BoundedSink::new(BufferedDigest::new().unwrap(), bytes.len());
        for chunk in bytes.chunks(chunk_bytes) {
            sink.append(chunk).unwrap();
            assert!(sink.inner.buffer.len() <= HASH_BUFFER_BYTES);
        }
        assert_eq!(
            sink.finish().unwrap(),
            sha256_of(&bytes),
            "chunk_bytes={chunk_bytes}"
        );
    }
}
