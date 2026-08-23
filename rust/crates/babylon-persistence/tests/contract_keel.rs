//! Public contracts that prevent persistence identity and hash-name collapse.

use babylon_kernel::{seed_for, ContentDigest, SessionId};
use babylon_persistence::{
    CampaignId, GraphStateHash, PersistenceError, PersistenceFailureKind, RefDigest,
    ReplayIdentityHash, TickContentHash,
};
use std::any::TypeId;
use uuid::Uuid;

#[test]
fn campaign_uuid_is_not_an_rng_input() {
    let first = CampaignId::from_uuid(Uuid::from_u128(1));
    let second = CampaignId::from_uuid(Uuid::from_u128(2));
    let session = SessionId::new("contract-keel").expect("literal is non-empty");
    assert_ne!(first, second);
    assert_eq!(
        seed_for(&session, 7, "contract", "carrier"),
        seed_for(&session, 7, "contract", "carrier")
    );
    assert_eq!(first.as_uuid(), &Uuid::from_u128(1));
}

#[test]
fn honest_hashes_are_nominally_distinct() {
    assert_ne!(
        TypeId::of::<ReplayIdentityHash>(),
        TypeId::of::<GraphStateHash>()
    );
    assert_ne!(
        TypeId::of::<GraphStateHash>(),
        TypeId::of::<TickContentHash>()
    );
    assert_ne!(TypeId::of::<TickContentHash>(), TypeId::of::<RefDigest>());
    let bytes = [0x07; 32];
    assert_eq!(GraphStateHash::from_bytes(bytes).as_bytes(), &bytes);
    assert_eq!(RefDigest::from_bytes(bytes).to_hex(), "07".repeat(32));
}

#[test]
fn content_digest_remains_the_kernel_pair() {
    let digest = ContentDigest {
        defines_hash: [1; 32],
        rules_hash: [2; 32],
    };
    assert_ne!(digest.defines_hash, digest.rules_hash);
}

#[test]
fn failures_keep_five_distinct_stages() {
    let cases = [
        (
            PersistenceError::connection("connect"),
            PersistenceFailureKind::Connection,
        ),
        (
            PersistenceError::migration("adopt"),
            PersistenceFailureKind::Migration,
        ),
        (
            PersistenceError::serialization("encode"),
            PersistenceFailureKind::Serialization,
        ),
        (
            PersistenceError::constraint("foreign key"),
            PersistenceFailureKind::Constraint,
        ),
        (
            PersistenceError::commit("commit"),
            PersistenceFailureKind::Commit,
        ),
    ];
    for (error, expected) in cases {
        assert_eq!(error.kind(), expected);
        assert!(!error.to_string().is_empty());
    }
}
