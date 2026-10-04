//! Independent product framing/identity controls, written before the V3 encoder.
use super::*;
use crate::state_storage::IdentityKind as K;
use babylon_material_circuit::{
    aid_commitment_id, recurring_household_order_id, CircuitAccounting,
};
fn fixture() -> (OpeningRegister, IdentityEntry, IdentityEntry) {
    let session = crate::organizer_aid_fixture::authored_session(
        crate::michigan_dynamic_hex_foundation().unwrap(),
        crate::organizer_aid_fixture::config(),
        false,
        false,
    );
    let opening = OpeningRegister::from_opening(session.material()).unwrap();
    let CircuitAccounting::Monetary(economy) = &session.material().state().accounting else {
        panic!("monetary fixture");
    };
    let need = &economy.recurring.as_ref().unwrap().household_needs[0];
    let make = |period| IdentityEntry {
        kind: K::Order,
        bytes: recurring_household_order_id(
            period,
            (need.principal_id, need.good_id, need.unit_id),
        )
        .as_bytes(),
    };
    (opening, make(2), make(1))
}
fn descriptor_body(package: &[u8]) -> Vec<u8> {
    assert_eq!(
        &package[..b"BabylonPeriodLookupV3\0".len()],
        b"BabylonPeriodLookupV3\0"
    );
    let start = b"BabylonPeriodLookupV3\0".len() + 2 + 32 + 8 + 32 + 8 + 32;
    let length = usize::try_from(u64::from_be_bytes(
        package[start..start + 8].try_into().unwrap(),
    ))
    .unwrap();
    let digest = package[start + 8..start + 40].try_into().unwrap();
    let encoded_length = usize::try_from(u64::from_be_bytes(
        package[start + 40..start + 48].try_into().unwrap(),
    ))
    .unwrap();
    assert_eq!(start + 48 + encoded_length, package.len());
    decompress_exact(&package[start + 48..], length, digest, MAX_LOOKUP_BYTES).unwrap()
}
#[test]
fn current_generated_table_is_compact_and_exact_without_prior_period_dependency() {
    let (opening, generated, survivor) = fixture();
    let same_bytes = IdentityEntry {
        kind: K::Good,
        bytes: generated.bytes,
    };
    let authored = IdentityEntry {
        kind: K::Site,
        bytes: [247; 32],
    };
    let aid = IdentityEntry {
        kind: K::Order,
        bytes: aid_commitment_id([246; 32], 2).as_bytes(),
    };
    let mandate = IdentityEntry {
        kind: K::AidMandate,
        bytes: aid.bytes,
    };
    let entries = [generated, same_bytes, authored, survivor, aid, mandate];
    let previous = [221; 32];
    let (package, chain) = encode_period_lookup(&opening, 2, previous, &entries).unwrap();
    let body = descriptor_body(&package);
    let logical = state_storage::encode_lookup(&entries).unwrap();
    assert_eq!(body.len(), 4 + 13 + 5 * 33);
    assert!(body.len() < logical.len());
    assert_eq!(body[17], K::Good as u8);
    assert_eq!(body[50], K::Site as u8);
    assert_eq!(body[83], K::Order as u8); // old-period survivor remains literal
    assert_eq!(body[116], K::Order as u8); // aid commitment has its own domain
    assert_eq!(body[149], K::AidMandate as u8);
    // First exact household recipe: tag128, opening row ordinal, explicit period2.
    assert_eq!(body[4], 128);
    assert_eq!(u64::from_be_bytes(body[9..17].try_into().unwrap()), 2);
    let reconstructed =
        read_period_lookup(&opening, 2, &package, LookupAnchor::Previous(previous)).unwrap();
    assert_eq!(
        &reconstructed.lookup.entries()[opening.lookup().entries().len()..],
        &entries
    );
    assert_eq!(
        chain,
        period_lookup_chain(&opening, 2, previous, sha256_of(&logical))
    );
    assert_eq!(
        read_period_lookup(&opening, 2, &package, LookupAnchor::Current(chain))
            .unwrap()
            .chain,
        chain
    );
    // Old wrapper2 is refused rather than silently interpreted as descriptor bytes.
    let mut old = package.clone();
    old[b"BabylonPeriodLookupV3\0".len() + 1] = 2;
    assert_eq!(
        read_period_lookup(&opening, 2, &old, LookupAnchor::Previous(previous)).unwrap_err(),
        Error::Version
    );
}
fn replace_descriptor_body(package: &[u8], body: &[u8]) -> Vec<u8> {
    let start = b"BabylonPeriodLookupV3\0".len() + 2 + 32 + 8 + 32 + 8 + 32;
    let compressed = compress_exact(body, MAX_LOOKUP_BYTES).unwrap();
    let mut changed = package[..start].to_vec();
    changed.extend_from_slice(&(body.len() as u64).to_be_bytes());
    changed.extend_from_slice(&sha256_of(body));
    changed.extend_from_slice(&(compressed.len() as u64).to_be_bytes());
    changed.extend_from_slice(&compressed);
    changed
}
#[test]
fn checked_recipe_substitution_cannot_change_unchanged_logical_anchor() {
    let (opening, generated, _) = fixture();
    let previous = [222; 32];
    let (package, _) = encode_period_lookup(&opening, 2, previous, &[generated]).unwrap();
    let mut body = descriptor_body(&package);
    body[9..17].copy_from_slice(&1u64.to_be_bytes());
    let changed = replace_descriptor_body(&package, &body);
    assert_eq!(
        read_period_lookup(&opening, 2, &changed, LookupAnchor::Previous(previous)).unwrap_err(),
        Error::State(StorageError::DigestMismatch)
    );
}
