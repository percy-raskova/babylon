use super::*;
use crate::michigan_content::MichiganContentPreset;
use crate::state_storage::IdentityKind;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::replay_session::ReplayCommitDisposition;

#[test]
fn actual_two_periods_reload_independently_without_retaining_historic_lookup() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .unwrap();
    let base = foundation.initial_register().clone();
    let opening = OpeningRegister::from_opening(&base).unwrap();
    let original = lookup_identity(opening.lookup()).unwrap();
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
    let mut chain = initial_lookup_chain(&opening).unwrap();
    let mut session = foundation.into_session().unwrap();
    for period in 1..=2 {
        let actions = OrderedPracticeActionBatch::empty(
            session.graph_session().session_identity().clone(),
            period,
        )
        .unwrap();
        let candidate = session.prepare_advance(&actions).unwrap();
        let current = candidate.material().register();
        let receipts = candidate.material().receipt_bytes();
        let encoded = encode(current, receipts, &opening, chain).unwrap();
        assert!(encoded
            .register_storage_bytes
            .starts_with(b"babylon.state-storage.v3\0"));
        assert!(encoded
            .receipt_storage_bytes
            .starts_with(b"BabylonReceiptStorageV2\0"));
        let loaded = read_period_lookup(
            &opening,
            period,
            &encoded.lookup_delta_bytes,
            LookupAnchor::Previous(chain),
        )
        .unwrap();
        assert_eq!(loaded.lookup.entries(), encoded.lookup.entries());
        // Raw-byte tooling admission follows the same final typed encoder.
        let raw_opening = OpeningRegister::from_canonical(base.canonical_bytes()).unwrap();
        let raw_current = MaterialWorldRegister::decode(current.canonical_bytes()).unwrap();
        let mut independent = state_storage::encode_register_with_opening(
            &raw_opening,
            &raw_current,
            raw_opening.lookup(),
        )
        .unwrap();
        independent.bind_lookup_chain(encoded.lookup_chain).unwrap();
        assert_eq!(independent.package, encoded.register_storage_bytes);
        let mut shortened = encoded.register_storage_bytes.clone();
        let offset = b"babylon.state-storage.v3\0".len() + 32 + 32 + 32 + 8;
        shortened[offset..offset + 4].copy_from_slice(&0_u32.to_be_bytes());
        shortened[offset + 4..offset + 36].copy_from_slice(&sha256_of(&[]));
        assert_eq!(
            state_storage::decode_admitted(&opening, &shortened, &loaded.lookup, loaded.chain)
                .unwrap_err(),
            StorageError::ParentMismatch
        );

        assert_eq!(
            decode(
                &opening,
                period,
                &encoded.register_storage_bytes,
                &encoded.receipt_storage_bytes,
                &loaded.lookup,
                loaded.chain,
            )
            .unwrap(),
            (current.canonical_bytes().to_vec(), receipts.to_vec())
        );
        assert_eq!(
            encode(current, receipts, &opening, chain)
                .unwrap()
                .lookup_delta_bytes,
            encoded.lookup_delta_bytes
        );
        assert_eq!(
            read_period_lookup(
                &opening,
                period + 1,
                &encoded.lookup_delta_bytes,
                LookupAnchor::Previous(chain)
            )
            .unwrap_err(),
            Error::Tick
        );
        assert_eq!(lookup_identity(opening.lookup()).unwrap(), original);
        assert!(encode(current, &[255], &opening, chain).is_err());
        assert_eq!(lookup_identity(opening.lookup()).unwrap(), original);
        chain = loaded.chain;
        session
            .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .unwrap();
    }
}

#[test]
fn surviving_identity_repeats_exactly_but_period_only_identity_is_not_retained() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .unwrap();
    let opening = OpeningRegister::from_opening(foundation.initial_register()).unwrap();
    let pending = IdentityEntry {
        kind: IdentityKind::Order,
        bytes: [222; 32],
    };
    let retired = IdentityEntry {
        kind: IdentityKind::Shift,
        bytes: [223; 32],
    };
    let c0 = initial_lookup_chain(&opening).unwrap();
    let (first, c1) = encode_period_lookup(&opening, 1, c0, &[pending, retired]).unwrap();
    let (second, _) = encode_period_lookup(&opening, 2, c1, &[pending]).unwrap();
    let one = read_period_lookup(&opening, 1, &first, LookupAnchor::Previous(c0)).unwrap();
    let two = read_period_lookup(&opening, 2, &second, LookupAnchor::Previous(c1)).unwrap();
    let seed_count = opening.lookup().entries().len();
    assert_eq!(&one.lookup.entries()[seed_count..], &[pending, retired]);
    assert_eq!(&two.lookup.entries()[seed_count..], &[pending]);
    assert_eq!(two.lookup.entries().len(), seed_count + 1);
    // Codec ownership only; this does not authorize economic retirement.
    assert_eq!(
        read_period_lookup(&opening, 2, &first, LookupAnchor::Previous(c1)).unwrap_err(),
        Error::Tick
    );
}

#[test]
fn malformed_and_wrong_context_period_tables_refuse_without_seed_mutation() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .unwrap();
    let opening = OpeningRegister::from_opening(foundation.initial_register()).unwrap();
    let original = lookup_identity(opening.lookup()).unwrap();
    let extra = IdentityEntry {
        kind: IdentityKind::Site,
        bytes: [254; 32],
    };
    let c0 = initial_lookup_chain(&opening).unwrap();
    let (good, _) = encode_period_lookup(&opening, 52, c0, &[extra]).unwrap();
    assert_eq!(
        read_period_lookup(&opening, 0, &good, LookupAnchor::Previous(c0)).unwrap_err(),
        Error::Tick
    );
    assert_eq!(
        read_period_lookup(&opening, 51, &good, LookupAnchor::Previous(c0)).unwrap_err(),
        Error::Tick
    );
    let (duplicate, _) = encode_period_lookup(&opening, 52, c0, &[extra, extra]).unwrap();
    assert!(read_period_lookup(&opening, 52, &duplicate, LookupAnchor::Previous(c0)).is_err());
    let (seed_duplicate, _) =
        encode_period_lookup(&opening, 52, c0, &opening.lookup().entries()[..1]).unwrap();
    assert!(read_period_lookup(&opening, 52, &seed_duplicate, LookupAnchor::Previous(c0)).is_err());
    let mut other_opening = good.clone();
    other_opening[LOOKUP_DOMAIN.len() + 2] ^= 1;
    assert_eq!(
        read_period_lookup(&opening, 52, &other_opening, LookupAnchor::Previous(c0)).unwrap_err(),
        Error::Opening
    );
    let mut version = good.clone();
    version[LOOKUP_DOMAIN.len() + 1] = 99;
    assert_eq!(
        read_period_lookup(&opening, 52, &version, LookupAnchor::Previous(c0)).unwrap_err(),
        Error::Version
    );
    let mut oversized = good.clone();
    let offset = LOOKUP_DOMAIN.len() + 2 + 32 + 8 + 32;
    oversized[offset..offset + 8].copy_from_slice(&(MAX_LOOKUP_BYTES as u64 + 1).to_be_bytes());
    assert_eq!(
        read_period_lookup(&opening, 52, &oversized, LookupAnchor::Previous(c0)).unwrap_err(),
        Error::Bounds
    );
    let mut unknown_kind = good[..LOOKUP_DOMAIN.len() + 2 + 32 + 8 + 32].to_vec();
    let mut packed = 1_u32.to_be_bytes().to_vec();
    packed.push(21);
    packed.extend_from_slice(&[0; 32]);
    let compressed = compress_exact(&packed, MAX_LOOKUP_BYTES).unwrap();
    unknown_kind.extend_from_slice(&(packed.len() as u64).to_be_bytes());
    unknown_kind.extend_from_slice(&sha256_of(&packed));
    unknown_kind.extend_from_slice(&(packed.len() as u64).to_be_bytes());
    unknown_kind.extend_from_slice(&sha256_of(&packed));
    unknown_kind.extend_from_slice(&(compressed.len() as u64).to_be_bytes());
    unknown_kind.extend_from_slice(&compressed);
    assert_eq!(
        read_period_lookup(&opening, 52, &unknown_kind, LookupAnchor::Previous(c0)).unwrap_err(),
        Error::State(StorageError::IdentityKind)
    );
    let mut damaged = good.clone();
    *damaged.last_mut().unwrap() ^= 1;
    assert!(read_period_lookup(&opening, 52, &damaged, LookupAnchor::Previous(c0)).is_err());
    let mut trailing = good.clone();
    trailing.push(0);
    assert_eq!(
        read_period_lookup(&opening, 52, &trailing, LookupAnchor::Previous(c0)).unwrap_err(),
        Error::Trailing
    );
    assert!(read_period_lookup(
        &opening,
        52,
        &good[..good.len() - 1],
        LookupAnchor::Previous(c0)
    )
    .is_err());
    assert_eq!(lookup_identity(opening.lookup()).unwrap(), original);
}

#[test]
fn local_chunk_and_reference_boundaries_are_checked_without_large_allocations() {
    let maximum = (MAX_LOOKUP_BYTES - 4) / 33;
    assert_eq!(admitted_count(0, maximum).unwrap(), maximum);
    assert_eq!(admitted_count(0, maximum + 1).unwrap_err(), Error::Bounds);
    let last_count = u32::MAX as usize;
    assert_eq!(admitted_count(last_count, 0).unwrap(), last_count);
    assert_eq!(admitted_count(last_count, 1).unwrap_err(), Error::Bounds);
    assert_eq!(admitted_count(usize::MAX, 1).unwrap_err(), Error::Bounds);
}

#[test]
fn self_consistent_older_table_tamper_cannot_retain_later_chain_or_tail_anchor() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .unwrap();
    let opening = OpeningRegister::from_opening(foundation.initial_register()).unwrap();
    let c0 = initial_lookup_chain(&opening).unwrap();
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
    let (first, c1) = encode_period_lookup(&opening, 1, c0, &[old]).unwrap();
    let (second, c2) = encode_period_lookup(&opening, 2, c1, &[later]).unwrap();
    let (tampered, changed_c1) = encode_period_lookup(&opening, 1, c0, &[changed]).unwrap();
    // Both old and changed chunks are independently well-framed, typed, checksummed.
    assert!(read_period_lookup(&opening, 1, &first, LookupAnchor::Previous(c0)).is_ok());
    assert!(read_period_lookup(&opening, 1, &tampered, LookupAnchor::Previous(c0)).is_ok());
    assert_ne!(changed_c1, c1);
    assert_eq!(
        read_period_lookup(&opening, 2, &second, LookupAnchor::Previous(changed_c1)).unwrap_err(),
        Error::LookupChain
    );
    // Rewriting the later predecessor link still cannot retain the original tail anchor.
    let (rewritten, changed_c2) = encode_period_lookup(&opening, 2, changed_c1, &[later]).unwrap();
    assert_ne!(changed_c2, c2);
    assert_eq!(
        read_period_lookup(&opening, 2, &rewritten, LookupAnchor::Current(c2)).unwrap_err(),
        Error::LookupChain
    );
}

#[test]
fn original_canonical_state_does_not_admit_a_changed_storage_chain() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .unwrap();
    let opening = OpeningRegister::from_opening(foundation.initial_register()).unwrap();
    let session = foundation.into_session().unwrap();
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .unwrap();
    let candidate = session.prepare_advance(&actions).unwrap();
    let encoded = encode(
        candidate.material().register(),
        candidate.material().receipt_bytes(),
        &opening,
        initial_lookup_chain(&opening).unwrap(),
    )
    .unwrap();
    let mut wrong = encoded.lookup_chain;
    wrong[0] ^= 1;
    assert_eq!(
        decode(
            &opening,
            1,
            &encoded.register_storage_bytes,
            &encoded.receipt_storage_bytes,
            &encoded.lookup,
            wrong
        )
        .unwrap_err(),
        Error::State(StorageError::DigestMismatch)
    );
    assert_eq!(
        decode(
            &opening,
            1,
            &encoded.register_storage_bytes,
            &encoded.receipt_storage_bytes,
            &encoded.lookup,
            encoded.lookup_chain
        )
        .unwrap()
        .0,
        candidate.material().register().canonical_bytes()
    );
    // No economic re-execution or changed canonical framing is used by this proof.
}

#[test]
fn encode_refuses_independently_valid_receipt_from_another_tick() {
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .unwrap();
    let opening = OpeningRegister::from_opening(foundation.initial_register()).unwrap();
    let chain = initial_lookup_chain(&opening).unwrap();
    let original_seed = lookup_identity(opening.lookup()).unwrap();
    let mut session = foundation.into_session().unwrap();
    let first_actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .unwrap();
    let first = session.prepare_advance(&first_actions).unwrap();
    let previous_receipts = first.material().receipt_bytes().to_vec();
    babylon_tick::material_world::decode_material_receipts(&previous_receipts).unwrap();
    session
        .commit_prepared_and_publish(&mut CollectingSink::default(), first, |_| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .unwrap();
    let second_actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 2)
            .unwrap();
    let second = session.prepare_advance(&second_actions).unwrap();
    assert_eq!(
        encode(
            second.material().register(),
            &previous_receipts,
            &opening,
            chain
        )
        .unwrap_err(),
        Error::Tick
    );
    assert_eq!(lookup_identity(opening.lookup()).unwrap(), original_seed);
    assert!(encode(
        second.material().register(),
        second.material().receipt_bytes(),
        &opening,
        chain
    )
    .is_ok());
}
