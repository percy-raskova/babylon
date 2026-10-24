use babylon_kernel::geography::CountyGeoid;
use babylon_persistence::national_counties;
use babylon_persistence::national_counties::{
    NationalCountyReference, NationalCountyReferenceError, ObservationStatus,
};

const ARTIFACT: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../src/babylon/data/reference/economy/national_county_reference_2024.csv.gz"
));
fn id(value: &str) -> CountyGeoid {
    CountyGeoid::try_from(value).expect("the fixture value fits the target range")
}

#[test]
fn captures_complete_domestic_roster_and_preserves_source_meaning() {
    let captured =
        national_counties::national_county_reference().expect("the county reference fixture loads");
    assert_eq!(captured.counties().len(), 3144);
    for (state, expected) in [
        (*b"09", 9),
        (*b"02", 30),
        (*b"15", 5),
        (*b"11", 1),
        (*b"26", 83),
    ] {
        assert_eq!(
            captured
                .counties()
                .iter()
                .filter(|row| row.geoid().state_fips() == state)
                .count(),
            expected
        );
    }
    let autauga = captured
        .county(id("01001"))
        .expect("the fixture catalog holds the addressed county");
    assert_eq!(
        autauga.residents().population_persons.estimate.value(),
        Some(59947)
    );
    assert_eq!(autauga.residents().households.estimate.value(), Some(22917));
    assert_eq!(
        autauga
            .residents()
            .civilian_employed_persons
            .estimate
            .value(),
        Some(26122)
    );
    assert_eq!(autauga.workplaces().jobs.value(), Some(12383));
    assert_eq!(
        autauga
            .residents()
            .population_persons
            .margin_of_error
            .value(),
        None
    );
    assert_eq!(
        autauga
            .residents()
            .population_persons
            .margin_of_error
            .status(),
        ObservationStatus::ControlledEstimate
    );
    assert_eq!(
        autauga.residents().population_persons.margin_of_error.raw(),
        "-555555555"
    );
    assert_eq!(autauga.internal_point().latitude(), "+32.5322367");
    assert_eq!(autauga.internal_point().longitude(), "-086.6464395");
    assert_eq!(
        captured.artifact_sha256(),
        babylon_kernel::content_digest::sha256_of(ARTIFACT)
    );
}

#[test]
fn missing_workplace_row_does_not_erase_kalawao_residents_or_become_zero() {
    let captured =
        national_counties::national_county_reference().expect("the county reference fixture loads");
    let kalawao = captured
        .county(id("15005"))
        .expect("the fixture catalog holds the addressed county");
    assert!(kalawao
        .residents()
        .population_persons
        .estimate
        .value()
        .is_some());
    assert_eq!(
        kalawao.workplaces().status(),
        ObservationStatus::NotPublished
    );
    assert_eq!(kalawao.workplaces().jobs.value(), None);
    assert_eq!(kalawao.workplaces().jobs.raw(), "");
    assert_eq!(
        kalawao.workplaces().jobs.status(),
        ObservationStatus::NotPublished
    );
    for unknown in ["72001", "01000", "99999"] {
        assert_eq!(
            captured
                .county(id(unknown))
                .expect_err("the fixture call `county` fails for the authored inputs"),
            NationalCountyReferenceError::UnknownCounty(id(unknown))
        );
    }
}

#[test]
fn refuses_corrupted_truncated_and_extra_artifact_bytes() {
    let mut corrupted = ARTIFACT.to_vec();
    corrupted[100] ^= 1;
    assert_eq!(
        NationalCountyReference::decode_pinned(&corrupted)
            .expect_err("`decode_pinned` rejects the malformed bytes"),
        NationalCountyReferenceError::ArtifactDigest
    );
    assert!(NationalCountyReference::decode_pinned(&ARTIFACT[..100]).is_err());
    let mut trailing = ARTIFACT.to_vec();
    trailing.push(0);
    assert!(NationalCountyReference::decode_pinned(&trailing).is_err());
}
