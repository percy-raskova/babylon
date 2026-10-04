//! Trade markets, domestic counties and dependencies cannot alias one another.

use babylon_kernel::{
    economic_location::{EconomicLocation, ForeignCounterpart, UsDependency},
    geography::CountyGeoid,
};
use std::collections::BTreeSet;

#[test]
fn approved_world_scopes_have_disjoint_stable_identities() {
    let county = CountyGeoid::try_from("26163").unwrap();
    let mut locations = vec![EconomicLocation::domestic_county(county).unwrap()];
    locations.extend(ForeignCounterpart::ALL.map(EconomicLocation::Foreign));
    locations.extend(UsDependency::ALL.map(EconomicLocation::Dependency));
    assert_eq!(locations.len(), 19);
    assert_eq!(
        locations[0].canonical_bytes(),
        [0, b'2', b'6', b'1', b'6', b'3']
    );
    assert_eq!(
        EconomicLocation::Foreign(ForeignCounterpart::Canada).canonical_bytes(),
        [1, 1, 0, 0, 0, 0]
    );
    assert_eq!(
        EconomicLocation::Dependency(UsDependency::Guam).canonical_bytes(),
        [2, 2, 0, 0, 0, 0]
    );
    assert_eq!(
        locations
            .iter()
            .map(|v| v.canonical_bytes())
            .collect::<BTreeSet<_>>()
            .len(),
        19
    );
    for location in locations {
        assert_eq!(
            EconomicLocation::from_canonical_bytes(location.canonical_bytes()).unwrap(),
            location
        );
    }
    assert_eq!(
        ForeignCounterpart::ALL.map(ForeignCounterpart::as_str),
        [
            "canada",
            "mexico",
            "china",
            "russia",
            "india",
            "japan",
            "european_union",
            "remaining_europe",
            "latin_america_caribbean",
            "west_asia_north_africa",
            "sub_saharan_africa",
            "remaining_asia_pacific",
        ]
    );
}

#[test]
fn county_syntax_cannot_reclassify_a_dependency_or_unknown_jurisdiction() {
    for text in [
        "60010", "66010", "69085", "72001", "74050", "78010", "99001",
    ] {
        let county = CountyGeoid::try_from(text).unwrap();
        assert!(EconomicLocation::domestic_county(county).is_err(), "{text}");
    }
    for text in ["02013", "15005", "11001", "09110"] {
        assert!(EconomicLocation::domestic_county(CountyGeoid::try_from(text).unwrap()).is_ok());
    }
}

#[test]
fn source_relationship_and_game_market_are_explicit_and_closed() {
    assert_eq!(
        UsDependency::from_m49("630"),
        Some(UsDependency::PuertoRico)
    );
    assert_eq!(
        UsDependency::from_m49("581"),
        Some(UsDependency::MinorOutlyingIslands)
    );
    for freely_associated in ["583", "584", "585"] {
        assert_eq!(UsDependency::from_m49(freely_associated), None);
    }
    assert_eq!(
        ForeignCounterpart::from_key("china"),
        Some(ForeignCounterpart::China)
    );
    for invalid in ["China", "russia ", "us", "taiwan", "630", "eu"] {
        assert_eq!(ForeignCounterpart::from_key(invalid), None);
    }
}

#[test]
fn encoded_scope_refuses_unknown_tags_and_noncanonical_padding() {
    assert!(EconomicLocation::from_canonical_bytes([255; 6]).is_err());
    for bytes in [
        [1, 0, 0, 0, 0, 0],
        [1, 13, 0, 0, 0, 0],
        [2, 0, 0, 0, 0, 0],
        [2, 7, 0, 0, 0, 0],
    ] {
        assert!(EconomicLocation::from_canonical_bytes(bytes).is_err());
    }
    let mut foreign = EconomicLocation::Foreign(ForeignCounterpart::Canada).canonical_bytes();
    foreign[5] = 1;
    assert!(EconomicLocation::from_canonical_bytes(foreign).is_err());
    let mut dependency = EconomicLocation::Dependency(UsDependency::Guam).canonical_bytes();
    dependency[2] = 1;
    assert!(EconomicLocation::from_canonical_bytes(dependency).is_err());
    assert!(EconomicLocation::from_canonical_bytes([0, b'7', b'2', b'0', b'0', b'1']).is_err());
}
