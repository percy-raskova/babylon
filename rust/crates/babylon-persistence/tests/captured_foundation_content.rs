//! Independent framing witnesses for the singular current foundation content blob.
use babylon_persistence::{FoundationContentBundle, FoundationContentKind};

const DOMAIN: &[u8] = b"babylon.campaign-foundation-content.v3\0";
const SCENARIO: &str = "(scenario paper (defvocabulary NodeType (HOUSEHOLD)))";

fn blob(bytes: &mut Vec<u8>, tag: u8, value: &[u8]) {
    bytes.push(tag);
    bytes.extend_from_slice(&u32::try_from(value.len()).unwrap().to_be_bytes());
    bytes.extend_from_slice(value);
}
fn authored(prelude: Option<&[u8]>) -> Vec<u8> {
    let mut bytes = DOMAIN.to_vec();
    bytes.extend_from_slice(&3_u32.to_be_bytes());
    bytes.push(1); // Explicit authored BSCN source disposition.
    blob(&mut bytes, 1, SCENARIO.as_bytes());
    bytes.push(2);
    match prelude {
        None => bytes.push(0),
        Some(value) => {
            bytes.push(1);
            bytes.extend_from_slice(&u32::try_from(value.len()).unwrap().to_be_bytes());
            bytes.extend_from_slice(value);
        }
    }
    blob(&mut bytes, 3, b"");
    blob(&mut bytes, 4, b"defined policy");
    blob(&mut bytes, 5, b"captured reference");
    bytes
}

#[test]
fn independent_authored_vector_round_trips_as_one_tagged_content_blob() {
    let raw = authored(None);
    let bundle = FoundationContentBundle::decode(&raw).unwrap();
    assert_eq!(bundle.kind(), FoundationContentKind::AuthoredBscn);
    assert_eq!(bundle.canonical_bytes(), raw);
    assert_eq!(bundle.scenario_source_bytes(), SCENARIO.as_bytes());
    assert_eq!(bundle.defines_bytes(), b"defined policy");
    assert_eq!(
        bundle.reference_bundle_manifest_bytes(),
        b"captured reference"
    );
    let created = FoundationContentBundle::try_new(
        SCENARIO,
        None,
        "",
        b"defined policy",
        b"captured reference",
    )
    .unwrap();
    assert_eq!(created, bundle);
    let empty_prelude = FoundationContentBundle::decode(&authored(Some(b""))).unwrap();
    assert_ne!(empty_prelude.canonical_bytes(), bundle.canonical_bytes());
    assert_eq!(empty_prelude.prelude_source_bytes(), Some(b"".as_slice()));
}

#[test]
fn unsupported_tags_versions_lengths_and_trailing_bytes_are_not_dispatched_by_prefix() {
    let raw = authored(None);
    for length in [0, DOMAIN.len(), DOMAIN.len() + 4, raw.len() - 1] {
        assert!(FoundationContentBundle::decode(&raw[..length]).is_err());
    }
    let mut old = b"babylon.campaign-foundation-content.v2\0".to_vec();
    old.extend_from_slice(&2_u32.to_be_bytes());
    old.extend_from_slice(&raw[DOMAIN.len() + 5..]);
    assert!(FoundationContentBundle::decode(&old).is_err());
    let mut unknown_kind = raw.clone();
    unknown_kind[DOMAIN.len() + 4] = 3;
    assert!(FoundationContentBundle::decode(&unknown_kind).is_err());
    let mut wrong_first_field = raw.clone();
    wrong_first_field[DOMAIN.len() + 5] = 2;
    assert!(FoundationContentBundle::decode(&wrong_first_field).is_err());
    let mut excess_source = raw.clone();
    excess_source[DOMAIN.len() + 6..DOMAIN.len() + 10]
        .copy_from_slice(&1_048_577_u32.to_be_bytes());
    assert!(FoundationContentBundle::decode(&excess_source).is_err());
    let mut invalid_utf8 = raw.clone();
    invalid_utf8[DOMAIN.len() + 10] = 0xff;
    assert!(FoundationContentBundle::decode(&invalid_utf8).is_err());
    let mut embedded_nul = raw.clone();
    embedded_nul[DOMAIN.len() + 10] = 0;
    assert!(FoundationContentBundle::decode(&embedded_nul).is_err());
    let mut unknown_option = raw.clone();
    unknown_option[DOMAIN.len() + 11 + SCENARIO.len()] = 2;
    assert!(FoundationContentBundle::decode(&unknown_option).is_err());
    let mut trailing = raw;
    trailing.push(0);
    assert!(FoundationContentBundle::decode(&trailing).is_err());
}
