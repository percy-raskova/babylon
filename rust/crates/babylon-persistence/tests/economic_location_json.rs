//! Captured content cannot bypass the domestic jurisdiction check through Serde.

use babylon_kernel::{
    economic_location::{EconomicLocation, ForeignCounterpart, UsDependency},
    geography::CountyGeoid,
};

#[test]
fn captured_locations_keep_readable_disjoint_namespaces_and_exact_wire_identity() {
    let county =
        EconomicLocation::domestic_county(CountyGeoid::try_from("01001").unwrap()).unwrap();
    let mut cases = vec![(county, "county:01001".to_owned())];
    cases.extend(ForeignCounterpart::ALL.into_iter().map(|id| {
        (
            EconomicLocation::Foreign(id),
            format!("foreign:{}", id.as_str()),
        )
    }));
    cases.extend(UsDependency::ALL.into_iter().map(|id| {
        (
            EconomicLocation::Dependency(id),
            format!("dependency:{}", id.m49()),
        )
    }));
    for (location, key) in cases {
        let encoded = serde_json::to_string(&location).unwrap();
        assert_eq!(encoded, serde_json::to_string(&key).unwrap());
        let restored: EconomicLocation = serde_json::from_str(&encoded).unwrap();
        assert_eq!(restored.canonical_bytes(), location.canonical_bytes());
    }
}

#[test]
fn captured_locations_refuse_aliases_territorial_counties_and_unchecked_object_shapes() {
    for value in [
        r#""county:72001""#,
        r#""county:0101""#,
        r#""county:00001""#,
        r#""county:01001 ""#,
        r#""foreign:Canada""#,
        r#""foreign:puerto_rico""#,
        r#""dependency:583""#,
        r#""dependency:72""#,
        r#""01001""#,
        r#"{"County":"72001"}"#,
        r"[0,55,50,48,48,49]",
    ] {
        assert!(
            serde_json::from_str::<EconomicLocation>(value).is_err(),
            "{value}"
        );
    }
}
