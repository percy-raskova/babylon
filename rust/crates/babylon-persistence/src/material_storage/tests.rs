use super::receipt_witness::MaterialStorageWitnesses;
use super::register;
use super::register::{
    admitted_count, decode, DecodedMaterial, DecodedPeriodLookup, EncodedMaterial, Error,
    LookupAnchor, LOOKUP_DOMAIN, MAX_LOOKUP_BYTES,
};
use crate::michigan_content::MichiganContentPreset;
use crate::state_storage;
use crate::state_storage::IdentityKind;
use crate::state_storage::{IdentityEntry, OpeningRegister, StorageError, TypedLookup};
use crate::storage_compression;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_kernel::content_digest;
use babylon_material_circuit::MaterialCatalog;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_world::MaterialWorldRegister;
use babylon_tick::replay_session::ReplayCommitDisposition;

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "one storage scenario asserts encoding, reload and refusal together"
)]
fn actual_two_periods_reload_independently_without_retaining_historic_lookup() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let base = foundation.initial_register().clone();
    let opening =
        OpeningRegister::from_opening(&base).expect("the opening register admits its sections");
    let original = register::lookup_identity(opening.lookup())
        .expect("the fixture call `lookup_identity` succeeds for the authored inputs");
    assert_eq!(
        opening.canonical_bytes().as_ptr(),
        base.canonical_bytes().as_ptr()
    );
    let shared = opening.clone();
    assert_eq!(
        shared.canonical_bytes().as_ptr(),
        opening.canonical_bytes().as_ptr()
    );
    assert!(std::ptr::eq(shared.lookup(), opening.lookup()));
    let mut chain = register::initial_lookup_chain(&opening)
        .expect("the opening register builds its first lookup chain");
    let catalog = foundation.material_catalog().clone();
    let mut session = foundation
        .into_session()
        .expect("the fixture opens a session");
    for period in 1..=2 {
        let actions = OrderedPracticeActionBatch::empty(
            session.graph_session().session_identity().clone(),
            period,
        )
        .expect("the empty authored batch constructs");
        let candidate = session
            .prepare_advance(&actions)
            .expect("the session prepares the authored advance");
        let current = candidate.material().register();
        let receipts = candidate.material().receipt_bytes();
        let encoded = register::encode(current, receipts, &opening, chain)
            .expect("the fixture value encodes canonically");
        assert!(encoded
            .register_storage_bytes
            .starts_with(b"babylon.state-storage.v4\0"));
        assert!(encoded
            .receipt_storage_bytes
            .starts_with(b"BabylonReceiptStorageV3\0"));
        let loaded = register::read_period_lookup(
            &opening,
            period,
            &encoded.lookup_delta_bytes,
            LookupAnchor::Previous(chain),
        )
        .expect("the committed lookup table reads");
        assert_eq!(loaded.lookup.entries(), encoded.lookup.entries());
        // Raw-byte tooling admission follows the same final typed encoder.
        let raw_opening = OpeningRegister::from_canonical(&catalog, base.canonical_bytes())
            .expect("the canonical bytes admit the value");
        let raw_current =
            MaterialWorldRegister::decode_external(&catalog, current.canonical_bytes().to_vec())
                .expect("the committed canonical bytes decode");
        let mut independent = state_storage::encode_register_with_opening(
            &raw_opening,
            &raw_current,
            raw_opening.lookup(),
        )
        .expect("the register encodes with its opening");
        independent
            .bind_lookup_chain(encoded.lookup_chain)
            .expect("the authored lookup chain binds");
        assert_eq!(independent.package, encoded.register_storage_bytes);
        let mut shortened = encoded.register_storage_bytes.clone();
        let offset = b"babylon.state-storage.v4\0".len() + 32 + 32 + 32 + 8;
        shortened[offset..offset + 4].copy_from_slice(&0_u32.to_be_bytes());
        shortened[offset + 4..offset + 36].copy_from_slice(&content_digest::sha256_of(&[]));
        assert_eq!(
            state_storage::decode_admitted(
                &catalog,
                &opening,
                &shortened,
                &loaded.lookup,
                loaded.chain
            )
            .expect_err("the malformed admitted bytes are refused"),
            StorageError::ParentMismatch
        );

        assert_eq!(
            decode(
                &catalog,
                &opening,
                period,
                &encoded.register_storage_bytes,
                &encoded.receipt_storage_bytes,
                &loaded.lookup,
                loaded.chain,
            )
            .expect("the committed canonical bytes decode"),
            (current.canonical_bytes().to_vec(), receipts.to_vec())
        );
        assert_eq!(
            register::encode(current, receipts, &opening, chain)
                .expect("the fixture value encodes canonically")
                .lookup_delta_bytes,
            encoded.lookup_delta_bytes
        );
        assert_eq!(
            register::read_period_lookup(
                &opening,
                period + 1,
                &encoded.lookup_delta_bytes,
                LookupAnchor::Previous(chain)
            )
            .expect_err("the malformed lookup request is refused"),
            Error::Tick
        );
        assert_eq!(
            register::lookup_identity(opening.lookup())
                .expect("the fixture call `lookup_identity` succeeds for the authored inputs"),
            original
        );
        assert!(register::encode(current, &[255], &opening, chain).is_err());
        assert_eq!(
            register::lookup_identity(opening.lookup())
                .expect("the fixture call `lookup_identity` succeeds for the authored inputs"),
            original
        );
        chain = loaded.chain;
        session
            .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_, _| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .expect("the prepared period commits");
    }
}

#[test]
fn surviving_identity_repeats_exactly_but_period_only_identity_is_not_retained() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let opening = OpeningRegister::from_opening(foundation.initial_register())
        .expect("the opening register admits its sections");
    let pending = IdentityEntry {
        kind: IdentityKind::Order,
        bytes: [222; 32],
    };
    let retired = IdentityEntry {
        kind: IdentityKind::Shift,
        bytes: [223; 32],
    };
    let c0 = register::initial_lookup_chain(&opening)
        .expect("the opening register builds its first lookup chain");
    let (first, c1) = register::encode_period_lookup(&opening, 1, c0, &[pending, retired])
        .expect("the authored lookup table encodes");
    let (second, _) = register::encode_period_lookup(&opening, 2, c1, &[pending])
        .expect("the authored lookup table encodes");
    let one = register::read_period_lookup(&opening, 1, &first, LookupAnchor::Previous(c0))
        .expect("the committed lookup table reads");
    let two = register::read_period_lookup(&opening, 2, &second, LookupAnchor::Previous(c1))
        .expect("the committed lookup table reads");
    let seed_count = opening.lookup().entries().len();
    assert_eq!(&one.lookup.entries()[seed_count..], &[pending, retired]);
    assert_eq!(&two.lookup.entries()[seed_count..], &[pending]);
    assert_eq!(two.lookup.entries().len(), seed_count + 1);
    // Codec ownership only; this does not authorize economic retirement.
    assert_eq!(
        register::read_period_lookup(&opening, 2, &first, LookupAnchor::Previous(c1))
            .expect_err("the malformed lookup request is refused"),
        Error::Tick
    );
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`malformed_and_wrong_context_period_tables_refuse_without_seed_mutation` keeps one authored boundary's fixture and assertions together"
)]
fn malformed_and_wrong_context_period_tables_refuse_without_seed_mutation() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let opening = OpeningRegister::from_opening(foundation.initial_register())
        .expect("the opening register admits its sections");
    let original = register::lookup_identity(opening.lookup())
        .expect("the fixture call `lookup_identity` succeeds for the authored inputs");
    let extra = IdentityEntry {
        kind: IdentityKind::Site,
        bytes: [254; 32],
    };
    let c0 = register::initial_lookup_chain(&opening)
        .expect("the opening register builds its first lookup chain");
    let (good, _) = register::encode_period_lookup(&opening, 52, c0, &[extra])
        .expect("the authored lookup table encodes");
    assert_eq!(
        register::read_period_lookup(&opening, 0, &good, LookupAnchor::Previous(c0))
            .expect_err("the malformed lookup request is refused"),
        Error::Tick
    );
    assert_eq!(
        register::read_period_lookup(&opening, 51, &good, LookupAnchor::Previous(c0))
            .expect_err("the malformed lookup request is refused"),
        Error::Tick
    );
    let (duplicate, _) = register::encode_period_lookup(&opening, 52, c0, &[extra, extra])
        .expect("the authored lookup table encodes");
    assert!(
        register::read_period_lookup(&opening, 52, &duplicate, LookupAnchor::Previous(c0)).is_err()
    );
    let (seed_duplicate, _) =
        register::encode_period_lookup(&opening, 52, c0, &opening.lookup().entries()[..1])
            .expect("the authored lookup table encodes");
    assert!(register::read_period_lookup(
        &opening,
        52,
        &seed_duplicate,
        LookupAnchor::Previous(c0)
    )
    .is_err());
    let mut other_opening = good.clone();
    other_opening[LOOKUP_DOMAIN.len() + 2] ^= 1;
    assert_eq!(
        register::read_period_lookup(&opening, 52, &other_opening, LookupAnchor::Previous(c0))
            .expect_err("the malformed lookup request is refused"),
        Error::Opening
    );
    let mut version = good.clone();
    version[LOOKUP_DOMAIN.len() + 1] = 99;
    assert_eq!(
        register::read_period_lookup(&opening, 52, &version, LookupAnchor::Previous(c0))
            .expect_err("the malformed lookup request is refused"),
        Error::Version
    );
    let mut oversized = good.clone();
    let offset = LOOKUP_DOMAIN.len() + 2 + 32 + 8 + 32;
    oversized[offset..offset + 8].copy_from_slice(&(MAX_LOOKUP_BYTES as u64 + 1).to_be_bytes());
    assert_eq!(
        register::read_period_lookup(&opening, 52, &oversized, LookupAnchor::Previous(c0))
            .expect_err("the malformed lookup request is refused"),
        Error::Bounds
    );
    let mut unknown_kind = good[..LOOKUP_DOMAIN.len() + 2 + 32 + 8 + 32].to_vec();
    let mut packed = 1_u32.to_be_bytes().to_vec();
    packed.push(21);
    packed.extend_from_slice(&[0; 32]);
    let compressed = storage_compression::compress_exact(&packed, MAX_LOOKUP_BYTES)
        .expect("the body fits the exact compressed bound");
    unknown_kind.extend_from_slice(&(packed.len() as u64).to_be_bytes());
    unknown_kind.extend_from_slice(&content_digest::sha256_of(&packed));
    unknown_kind.extend_from_slice(&(packed.len() as u64).to_be_bytes());
    unknown_kind.extend_from_slice(&content_digest::sha256_of(&packed));
    unknown_kind.extend_from_slice(&(compressed.len() as u64).to_be_bytes());
    unknown_kind.extend_from_slice(&compressed);
    assert_eq!(
        register::read_period_lookup(&opening, 52, &unknown_kind, LookupAnchor::Previous(c0))
            .expect_err("the malformed lookup request is refused"),
        Error::State(StorageError::IdentityKind)
    );
    let mut damaged = good.clone();
    *damaged
        .last_mut()
        .expect("the fixture sequence is non-empty") ^= 1;
    assert!(
        register::read_period_lookup(&opening, 52, &damaged, LookupAnchor::Previous(c0)).is_err()
    );
    let mut trailing = good.clone();
    trailing.push(0);
    assert_eq!(
        register::read_period_lookup(&opening, 52, &trailing, LookupAnchor::Previous(c0))
            .expect_err("the malformed lookup request is refused"),
        Error::Trailing
    );
    assert!(register::read_period_lookup(
        &opening,
        52,
        &good[..good.len() - 1],
        LookupAnchor::Previous(c0)
    )
    .is_err());
    assert_eq!(
        register::lookup_identity(opening.lookup())
            .expect("the fixture call `lookup_identity` succeeds for the authored inputs"),
        original
    );
}

#[test]
fn local_chunk_and_reference_boundaries_are_checked_without_large_allocations() {
    let maximum = (MAX_LOOKUP_BYTES - 4) / 33;
    assert_eq!(
        admitted_count(0, maximum)
            .expect("the fixture call `admitted_count` succeeds for the authored inputs"),
        maximum
    );
    assert_eq!(
        admitted_count(0, maximum + 1)
            .expect_err("the fixture call `admitted_count` fails for the authored inputs"),
        Error::Bounds
    );
    let last_count = u32::MAX as usize;
    assert_eq!(
        admitted_count(last_count, 0)
            .expect("the fixture call `admitted_count` succeeds for the authored inputs"),
        last_count
    );
    assert_eq!(
        admitted_count(last_count, 1)
            .expect_err("the fixture call `admitted_count` fails for the authored inputs"),
        Error::Bounds
    );
    assert_eq!(
        admitted_count(usize::MAX, 1)
            .expect_err("the fixture call `admitted_count` fails for the authored inputs"),
        Error::Bounds
    );
}

#[test]
fn self_consistent_older_table_tamper_cannot_retain_later_chain_or_tail_anchor() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let opening = OpeningRegister::from_opening(foundation.initial_register())
        .expect("the opening register admits its sections");
    let c0 = register::initial_lookup_chain(&opening)
        .expect("the opening register builds its first lookup chain");
    let old = IdentityEntry {
        kind: IdentityKind::Order,
        bytes: [222; 32],
    };
    let changed = IdentityEntry {
        kind: IdentityKind::Order,
        bytes: [223; 32],
    };
    let later = IdentityEntry {
        kind: IdentityKind::Shift,
        bytes: [224; 32],
    };
    let (first, c1) = register::encode_period_lookup(&opening, 1, c0, &[old])
        .expect("the authored lookup table encodes");
    let (second, c2) = register::encode_period_lookup(&opening, 2, c1, &[later])
        .expect("the authored lookup table encodes");
    let (tampered, changed_c1) = register::encode_period_lookup(&opening, 1, c0, &[changed])
        .expect("the authored lookup table encodes");
    // Both old and changed chunks are independently well-framed, typed, checksummed.
    assert!(register::read_period_lookup(&opening, 1, &first, LookupAnchor::Previous(c0)).is_ok());
    assert!(
        register::read_period_lookup(&opening, 1, &tampered, LookupAnchor::Previous(c0)).is_ok()
    );
    assert_ne!(changed_c1, c1);
    assert_eq!(
        register::read_period_lookup(&opening, 2, &second, LookupAnchor::Previous(changed_c1))
            .expect_err("the malformed lookup request is refused"),
        Error::LookupChain
    );
    // Rewriting the later predecessor link still cannot retain the original tail anchor.
    let (rewritten, changed_c2) = register::encode_period_lookup(&opening, 2, changed_c1, &[later])
        .expect("the authored lookup table encodes");
    assert_ne!(changed_c2, c2);
    assert_eq!(
        register::read_period_lookup(&opening, 2, &rewritten, LookupAnchor::Current(c2))
            .expect_err("the malformed lookup request is refused"),
        Error::LookupChain
    );
}

#[test]
fn original_canonical_state_does_not_admit_a_changed_storage_chain() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let opening = OpeningRegister::from_opening(foundation.initial_register())
        .expect("the opening register admits its sections");
    let catalog = foundation.material_catalog().clone();
    let session = foundation
        .into_session()
        .expect("the fixture opens a session");
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .expect("the empty authored batch constructs");
    let candidate = session
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance");
    let encoded = register::encode(
        candidate.material().register(),
        candidate.material().receipt_bytes(),
        &opening,
        register::initial_lookup_chain(&opening)
            .expect("the opening register builds its first lookup chain"),
    )
    .expect("the fixture value encodes canonically");
    let mut wrong = encoded.lookup_chain;
    wrong[0] ^= 1;
    assert_eq!(
        decode(
            &catalog,
            &opening,
            1,
            &encoded.register_storage_bytes,
            &encoded.receipt_storage_bytes,
            &encoded.lookup,
            wrong
        )
        .expect_err("the malformed bytes are refused"),
        Error::State(StorageError::DigestMismatch)
    );
    assert_eq!(
        decode(
            &catalog,
            &opening,
            1,
            &encoded.register_storage_bytes,
            &encoded.receipt_storage_bytes,
            &encoded.lookup,
            encoded.lookup_chain
        )
        .expect("the committed canonical bytes decode")
        .0,
        candidate.material().register().canonical_bytes()
    );
    // No economic re-execution or changed canonical framing is used by this proof.
}

#[test]
fn encode_refuses_independently_valid_receipt_from_another_tick() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let opening = OpeningRegister::from_opening(foundation.initial_register())
        .expect("the opening register admits its sections");
    let chain = register::initial_lookup_chain(&opening)
        .expect("the opening register builds its first lookup chain");
    let original_seed = register::lookup_identity(opening.lookup())
        .expect("the fixture call `lookup_identity` succeeds for the authored inputs");
    let mut session = foundation
        .into_session()
        .expect("the fixture opens a session");
    let first_actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .expect("the empty authored batch constructs");
    let first = session
        .prepare_advance(&first_actions)
        .expect("the session prepares the authored advance");
    let previous_receipts = first.material().receipt_bytes().to_vec();
    babylon_tick::material_world::decode_material_receipts(&previous_receipts)
        .expect("the canonical bytes decode into the declared type");
    session
        .commit_prepared_and_publish(&mut CollectingSink::default(), first, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("the prepared period commits");
    let second_actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 2)
            .expect("the empty authored batch constructs");
    let second = session
        .prepare_advance(&second_actions)
        .expect("the session prepares the authored advance");
    assert_eq!(
        register::encode(
            second.material().register(),
            &previous_receipts,
            &opening,
            chain
        )
        .expect_err("the fixture call `encode` fails for the authored inputs"),
        Error::Tick
    );
    assert_eq!(
        register::lookup_identity(opening.lookup())
            .expect("the fixture call `lookup_identity` succeeds for the authored inputs"),
        original_seed
    );
    assert!(register::encode(
        second.material().register(),
        second.material().receipt_bytes(),
        &opening,
        chain
    )
    .is_ok());
}

#[test]
fn admitted_current_receipt_is_not_typed_decoded_again_for_endpoint_framing() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let catalog = foundation.material_catalog().clone();
    let session = foundation
        .into_session()
        .expect("the fixture opens a session");
    let opening = OpeningRegister::from_opening(session.material())
        .expect("the opening register admits its sections");
    let chain = register::initial_lookup_chain(&opening)
        .expect("the opening register builds its first lookup chain");
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .expect("the empty authored batch constructs");
    let candidate = session
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance");
    let encoded = register::encode(
        candidate.material().register(),
        candidate.material().receipt_bytes(),
        &opening,
        chain,
    )
    .expect("the fixture value encodes canonically");
    let loaded = register::read_period_lookup(
        &opening,
        1,
        &encoded.lookup_delta_bytes,
        LookupAnchor::Previous(chain),
    )
    .expect("the committed lookup table reads");
    let before = crate::receipt_storage::typed_admission_count();
    let history = register::decode_typed(
        &catalog,
        &opening,
        1,
        &encoded.register_storage_bytes,
        &encoded.receipt_storage_bytes,
        &loaded.lookup,
        loaded.chain,
    )
    .expect("the canonical bytes decode into the declared type");
    let endpoint = register::decode_typed_with_witness(
        &catalog,
        &opening,
        1,
        &encoded.register_storage_bytes,
        &encoded.receipt_storage_bytes,
        &loaded.lookup,
        loaded.chain,
        MaterialStorageWitnesses {
            register: Some(&history.register),
            receipt: Some(&history.receipt_witness),
        },
    )
    .expect("the canonical bytes decode into the declared type");
    assert_eq!(endpoint.receipt_bytes, candidate.material().receipt_bytes());
    assert!(endpoint.receipts.shares_allocation(&history.receipts));
    assert_eq!(endpoint.receipts, history.receipts);
    assert_eq!(
        crate::receipt_storage::typed_admission_count() - before,
        1,
        "the complete reader must reuse the already admitted current typed receipt"
    );
    assert_receipt_witness_refusals(&catalog, &opening, &encoded, &loaded, &history);
    let cold = register::decode_typed(
        &catalog,
        &opening,
        1,
        &encoded.register_storage_bytes,
        &encoded.receipt_storage_bytes,
        &loaded.lookup,
        loaded.chain,
    )
    .expect("the canonical bytes decode into the declared type");
    assert_eq!(cold.receipt_bytes, endpoint.receipt_bytes);
    assert_eq!(cold.receipts, endpoint.receipts);
    assert!(!cold.receipts.shares_allocation(&endpoint.receipts));
    assert_eq!(crate::receipt_storage::typed_admission_count() - before, 2);
}

fn assert_receipt_witness_refusals(
    catalog: &MaterialCatalog,
    opening: &OpeningRegister,
    encoded: &EncodedMaterial,
    loaded: &DecodedPeriodLookup,
    history: &DecodedMaterial,
) {
    let unchanged = history.receipts.clone();
    let witness = MaterialStorageWitnesses {
        register: Some(&history.register),
        receipt: Some(&history.receipt_witness),
    };
    let restored = |tick, package: &[u8], chain| {
        register::decode_typed_with_witness(
            catalog,
            opening,
            tick,
            &encoded.register_storage_bytes,
            package,
            &loaded.lookup,
            chain,
            witness,
        )
    };
    let mut changed_package = encoded.receipt_storage_bytes.clone();
    changed_package.push(0);
    assert_eq!(
        restored(1, &changed_package, loaded.chain).err(),
        Some(Error::ReceiptWitness)
    );
    assert_eq!(
        history
            .receipt_witness
            .restore(
                2,
                &encoded.receipt_storage_bytes,
                &loaded.lookup,
                loaded.chain
            )
            .err(),
        Some(Error::Tick)
    );
    // A register's chain also refuses this input; exercise the receipt's own bound proof independently.
    assert_eq!(
        history
            .receipt_witness
            .restore(1, &encoded.receipt_storage_bytes, &loaded.lookup, [99; 32])
            .err(),
        Some(Error::LookupChain)
    );
    assert_eq!(
        history
            .receipt_witness
            .restore(
                1,
                &encoded.receipt_storage_bytes,
                &TypedLookup::default(),
                loaded.chain
            )
            .err(),
        Some(Error::LookupChain)
    );
    assert!(unchanged.shares_allocation(&history.receipts));
}
