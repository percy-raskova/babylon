//! Logical framing is checked before allocation and before resolving bad recipes.
use super::*;
use crate::state_storage::IdentityKind as K;
fn opening() -> OpeningRegister {
    let session = crate::organizer_aid_fixture::authored_session(
        crate::michigan_dynamic_hex_foundation().unwrap(),
        crate::organizer_aid_fixture::config(),
        false,
        false,
    );
    OpeningRegister::from_opening(session.material()).unwrap()
}
fn checked_body(package: &[u8], body: &[u8]) -> Vec<u8> {
    let offset = LOOKUP_DOMAIN.len() + 2 + 32 + 8 + 32 + 8 + 32;
    let compressed = compress_exact(body, MAX_LOOKUP_BYTES).unwrap();
    let mut changed = package[..offset].to_vec();
    changed.extend_from_slice(&(body.len() as u64).to_be_bytes());
    changed.extend_from_slice(&sha256_of(body));
    changed.extend_from_slice(&(compressed.len() as u64).to_be_bytes());
    changed.extend_from_slice(&compressed);
    changed
}
#[test]
fn logical_length_and_count_refuse_before_out_of_range_recipe_resolution() {
    let opening = opening();
    let previous = initial_lookup_chain(&opening).unwrap();
    let entry = IdentityEntry {
        kind: K::Site,
        bytes: [241; 32],
    };
    let (package, _) = encode_period_lookup(&opening, 1, previous, &[entry]).unwrap();
    let mut body = 1u32.to_be_bytes().to_vec();
    body.push(128);
    body.extend_from_slice(&u32::MAX.to_be_bytes());
    body.extend_from_slice(&1u64.to_be_bytes());
    let broken_row = checked_body(&package, &body);
    assert_eq!(
        read_period_lookup(&opening, 1, &broken_row, LookupAnchor::Previous(previous)).unwrap_err(),
        Error::Descriptor(DescriptorError::Row)
    );
    let offset = LOOKUP_DOMAIN.len() + 2 + 32 + 8 + 32;
    for length in [3u64, 38] {
        let mut changed = broken_row.clone();
        changed[offset..offset + 8].copy_from_slice(&length.to_be_bytes());
        assert_eq!(
            read_period_lookup(&opening, 1, &changed, LookupAnchor::Previous(previous))
                .unwrap_err(),
            Error::State(StorageError::Framing)
        );
    }
    // Structurally valid two-entry logical length versus one descriptor. Body SHA
    // and compressed frame are valid; count rejection must precede invalid row.
    let mut changed = broken_row.clone();
    changed[offset..offset + 8].copy_from_slice(&70u64.to_be_bytes());
    assert_eq!(
        read_period_lookup(&opening, 1, &changed, LookupAnchor::Previous(previous)).unwrap_err(),
        Error::Descriptor(DescriptorError::Framing)
    );
    body[..4].copy_from_slice(&u32::MAX.to_be_bytes());
    let huge_count = checked_body(&package, &body);
    assert_eq!(
        read_period_lookup(&opening, 1, &huge_count, LookupAnchor::Previous(previous)).unwrap_err(),
        Error::Descriptor(DescriptorError::Framing)
    );
    let mut oversized = broken_row;
    oversized[offset..offset + 8].copy_from_slice(&(MAX_LOOKUP_BYTES as u64 + 1).to_be_bytes());
    assert_eq!(
        read_period_lookup(&opening, 1, &oversized, LookupAnchor::Previous(previous)).unwrap_err(),
        Error::Bounds
    );
}
#[test]
fn empty_and_nonrecipe_kinds_keep_exact_logical_tables() {
    let opening = opening();
    let previous = initial_lookup_chain(&opening).unwrap();
    for entries in [
        vec![],
        vec![IdentityEntry {
            kind: K::Site,
            bytes: [243; 32],
        }],
    ] {
        let (package, chain) = encode_period_lookup(&opening, 1, previous, &entries).unwrap();
        let loaded =
            read_period_lookup(&opening, 1, &package, LookupAnchor::Previous(previous)).unwrap();
        assert_eq!(
            &loaded.lookup.entries()[opening.lookup().entries().len()..],
            entries
        );
        assert_eq!(loaded.chain, chain);
        let offset = LOOKUP_DOMAIN.len() + 2 + 32 + 8 + 32;
        assert_eq!(
            u64::from_be_bytes(package[offset..offset + 8].try_into().unwrap()),
            u64::from_be_bytes(package[offset + 40..offset + 48].try_into().unwrap())
        );
        assert_eq!(
            &package[offset + 8..offset + 40],
            &package[offset + 48..offset + 80]
        );
    }
}

#[test]
fn descriptor_length_cannot_exceed_its_logical_table_before_decompression() {
    let opening = opening();
    let previous = initial_lookup_chain(&opening).unwrap();
    let (mut package, _) = encode_period_lookup(&opening, 1, previous, &[]).unwrap();
    let offset = LOOKUP_DOMAIN.len() + 2 + 32 + 8 + 32 + 8 + 32;
    // The closed grammar can encode zero additions in exactly four bytes.
    // Keep the valid four-byte compressed frame but declare five. Refusal must
    // happen at descriptor admission, before the decompressor sees the frame.
    for declared in [5_u64, MAX_LOOKUP_BYTES as u64] {
        package[offset..offset + 8].copy_from_slice(&declared.to_be_bytes());
        assert_eq!(
            read_period_lookup(&opening, 1, &package, LookupAnchor::Previous(previous))
                .unwrap_err(),
            Error::Descriptor(DescriptorError::Framing)
        );
    }
}
