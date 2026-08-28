//! Contract for the database-free mapping from a committed envelope to `PostgreSQL` storage.

use babylon_kernel::replay::{ReplaySeed, ReplaySessionIdV1};
use babylon_kernel::tick_content_hash::{RefDigestV1, TickContentHashV1};
use babylon_kernel::ContentDigest;
use babylon_persistence::committed_tick_envelope::{
    CommittedTickEnvelopeV1, CommittedTickRowFamiliesV1, CommittedTickRowFamilyV1,
    CommittedTickRowV1,
};
use babylon_persistence::committed_tick_storage::{
    CampaignStorageRowV1, CommittedTickStorageEnvelopeV1, CommittedTickStorageErrorV1,
    ALL_COMMITTED_TICK_STORAGE_TARGETS_V1, CAMPAIGN_STORAGE_TABLE_V1, TICK_COMMIT_STORAGE_TABLE_V1,
};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::tick_commit_claim::TickCommitClaimV1;
use babylon_persistence::{request_rust_writer_authority, RustWriterAuthorityError};
use uuid::Uuid;

const CAMPAIGN: u128 = 0x0011_2233_4455_6677_8899_aabb_ccdd_eeff;

#[test]
fn all_eight_families_have_one_closed_schema_qualified_storage_target() {
    let expected = [
        (CommittedTickRowFamilyV1::Graph, 0x10, "tick_graph_row"),
        (CommittedTickRowFamilyV1::State, 0x11, "tick_state_row"),
        (CommittedTickRowFamilyV1::Event, 0x12, "tick_event_row"),
        (
            CommittedTickRowFamilyV1::Subsystem,
            0x13,
            "tick_subsystem_row",
        ),
        (
            CommittedTickRowFamilyV1::Conservation,
            0x14,
            "tick_conservation_row",
        ),
        (
            CommittedTickRowFamilyV1::BoundaryFlow,
            0x15,
            "tick_boundary_flow_row",
        ),
        (
            CommittedTickRowFamilyV1::Checkpoint,
            0x16,
            "tick_checkpoint_row",
        ),
        (
            CommittedTickRowFamilyV1::ArchiveDirtyReceipt,
            0x17,
            "tick_archive_dirty_receipt_row",
        ),
    ];

    assert_eq!(ALL_COMMITTED_TICK_STORAGE_TARGETS_V1.len(), expected.len());
    for index in 0..expected.len() {
        let target = ALL_COMMITTED_TICK_STORAGE_TARGETS_V1[index];
        let (family, tag, table) = expected[index];
        assert_eq!(target.family(), family);
        assert_eq!(target.family().tag(), tag);
        assert_eq!(target.table().schema(), "babylon_state");
        assert_eq!(target.table().relation(), table);
        assert_eq!(
            target.table().columns(),
            &[
                "campaign_id",
                "resolve_tick",
                "row_ordinal",
                "row_key",
                "row_payload",
            ]
        );
        assert_eq!(
            target.table().qualified_name(),
            format!("babylon_state.{table}")
        );
    }

    assert_eq!(
        CAMPAIGN_STORAGE_TABLE_V1.qualified_name(),
        "babylon_state.campaign"
    );
    assert_eq!(
        CAMPAIGN_STORAGE_TABLE_V1.columns(),
        &[
            "campaign_id",
            "replay_layout_version",
            "rng_layout_version",
            "replay_session_id",
            "rng_seed",
            "defines_hash",
            "rules_hash",
            "ref_digest",
        ]
    );
    assert_eq!(
        TICK_COMMIT_STORAGE_TABLE_V1.qualified_name(),
        "babylon_state.tick_commit"
    );
    assert_eq!(
        TICK_COMMIT_STORAGE_TABLE_V1.columns(),
        &[
            "campaign_id",
            "resolve_tick",
            "envelope_layout_version",
            "tick_content_hash",
            "envelope_digest",
        ]
    );
}

#[test]
fn campaign_mapping_preserves_each_separate_replay_and_content_identity() {
    let campaign_id = CampaignId::from_uuid(Uuid::from_u128(CAMPAIGN));
    let replay_session_id = ReplaySessionIdV1::try_from("storage-contract-session").unwrap();
    let content = ContentDigest {
        defines_hash: [0x31; 32],
        rules_hash: [0x42; 32],
    };
    let reference = RefDigestV1::from_bytes([0x53; 32]);
    let row = CampaignStorageRowV1::new(
        campaign_id,
        &replay_session_id,
        ReplaySeed::new(-54),
        &content,
        reference,
    );

    assert_eq!(row.campaign_id(), campaign_id);
    assert_eq!(row.replay_layout_version(), 1);
    assert_eq!(row.rng_layout_version(), 2);
    assert_eq!(row.replay_session_bytes(), b"storage-contract-session");
    assert_eq!(row.rng_seed(), -54);
    assert_eq!(row.defines_hash(), &[0x31; 32]);
    assert_eq!(row.rules_hash(), &[0x42; 32]);
    assert_eq!(row.reference(), reference);
}

#[test]
fn checked_mapping_preserves_claim_digests_and_every_exact_family_row() {
    let campaign_id = CampaignId::from_uuid(Uuid::from_u128(CAMPAIGN));
    let tick_content_hash = TickContentHashV1::from_bytes([0x11; 32]);
    let claim = TickCommitClaimV1::compose(campaign_id, 42, tick_content_hash);
    let envelope = CommittedTickEnvelopeV1::compose(
        claim,
        CommittedTickRowFamiliesV1 {
            graph: rows(0x01, 0xa1),
            state: rows(0x02, 0xa2),
            event: rows(0x03, 0xa3),
            subsystem: rows(0x04, 0xa4),
            conservation: rows(0x05, 0xa5),
            boundary_flow: rows(0x06, 0xa6),
            checkpoint: rows(0x07, 0xa7),
            archive_dirty_receipt: rows(0x08, 0xa8),
        },
    )
    .unwrap();

    let storage = CommittedTickStorageEnvelopeV1::try_from(&envelope).unwrap();
    assert_eq!(storage.marker().campaign_id(), campaign_id);
    assert_eq!(storage.marker().resolve_tick(), 42_i64);
    assert_eq!(storage.marker().envelope_layout_version(), 1_i16);
    assert_eq!(storage.marker().tick_content_hash(), tick_content_hash);
    assert_eq!(storage.marker().envelope_digest(), envelope.digest());
    assert_eq!(storage.batches().len(), 8);

    for (index, (batch, target)) in storage
        .batches()
        .iter()
        .zip(ALL_COMMITTED_TICK_STORAGE_TARGETS_V1.iter())
        .enumerate()
        .take(8)
    {
        assert_eq!(batch.target(), *target);
        assert_eq!(batch.campaign_id(), campaign_id);
        assert_eq!(batch.resolve_tick(), 42_i64);
        assert_eq!(batch.row_count(), 1);
        let row = batch.storage_row(0).unwrap();
        assert_eq!(row.campaign_id(), campaign_id);
        assert_eq!(row.resolve_tick(), 42_i64);
        assert_eq!(row.row_ordinal(), 0_i32);
        assert_eq!(row.key(), &[u8::try_from(index + 1).unwrap()]);
        assert_eq!(row.payload(), &[0xa1 + u8::try_from(index).unwrap()]);
        assert!(batch.storage_row(1).is_none());
    }
}

#[test]
fn storage_ordinals_preserve_checked_canonical_order_without_indexing_opaque_keys() {
    let claim = TickCommitClaimV1::compose(
        CampaignId::from_uuid(Uuid::from_u128(CAMPAIGN)),
        43,
        TickContentHashV1::from_bytes([0x12; 32]),
    );
    let envelope = CommittedTickEnvelopeV1::compose(
        claim,
        CommittedTickRowFamiliesV1 {
            graph: vec![
                CommittedTickRowV1::compose(vec![0x01; 4_096], vec![0xa1]).unwrap(),
                CommittedTickRowV1::compose(vec![0x02; 4_096], vec![0xa2]).unwrap(),
            ],
            ..CommittedTickRowFamiliesV1::default()
        },
    )
    .unwrap();

    let storage = CommittedTickStorageEnvelopeV1::try_from(&envelope).unwrap();
    let graph = &storage.batches()[0];
    assert_eq!(graph.row_count(), 2);
    let first = graph.storage_row(0).unwrap();
    let second = graph.storage_row(1).unwrap();
    assert_eq!(first.row_ordinal(), 0_i32);
    assert_eq!(second.row_ordinal(), 1_i32);
    assert_eq!(first.key(), &[0x01; 4_096]);
    assert_eq!(second.key(), &[0x02; 4_096]);
}

#[test]
fn mapping_refuses_a_tick_outside_postgresql_bigint() {
    let claim = TickCommitClaimV1::compose(
        CampaignId::from_uuid(Uuid::from_u128(CAMPAIGN)),
        u64::MAX,
        TickContentHashV1::from_bytes([0x22; 32]),
    );
    let envelope =
        CommittedTickEnvelopeV1::compose(claim, CommittedTickRowFamiliesV1::default()).unwrap();

    assert_eq!(
        CommittedTickStorageEnvelopeV1::try_from(&envelope),
        Err(CommittedTickStorageErrorV1::ResolveTickOutOfRange {
            actual: u64::MAX,
            maximum: i64::MAX as u64,
        })
    );
}

#[test]
fn storage_mapping_does_not_activate_rust_writer_authority() {
    assert!(matches!(
        request_rust_writer_authority(),
        Err(RustWriterAuthorityError::PythonAuthorityActive)
    ));
}

fn rows(key: u8, payload: u8) -> Vec<CommittedTickRowV1> {
    vec![CommittedTickRowV1::compose(vec![key], vec![payload]).unwrap()]
}
