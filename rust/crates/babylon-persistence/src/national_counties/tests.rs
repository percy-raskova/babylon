use super::artifact;
use super::artifact::{NationalCountyReferenceError, ObservationStatus, ARTIFACT};
use super::parse;
use super::parse::{acs_cell, parse_csv};
use babylon_kernel::geography::CountyGeoid;

fn source() -> String {
    artifact::decode_gzip(ARTIFACT).expect("the gzipped body decodes")
}

#[test]
fn duplicate_and_nonroster_rows_are_refused_before_capture() {
    let text = source();
    let mut lines: Vec<_> = text.lines().map(str::to_owned).collect();
    lines[2] = lines[1].clone();
    assert_eq!(
        parse_csv(&(lines.join("\n") + "\n")).expect_err("the malformed CSV is refused"),
        NationalCountyReferenceError::DuplicateCounty(
            CountyGeoid::try_from("01001").expect("the fixture value fits the target range")
        )
    );
    let mut lines: Vec<_> = text.lines().map(str::to_owned).collect();
    lines[1] = lines[1].replacen("01001,01,001,", "01000,01,000,", 1);
    assert_eq!(
        parse_csv(&(lines.join("\n") + "\n")).expect_err("the malformed CSV is refused"),
        NationalCountyReferenceError::RosterDigest
    );
    lines[1] = lines[1].replacen("01000,01,000,", "72001,72,001,", 1);
    assert_eq!(
        parse_csv(&(lines.join("\n") + "\n")).expect_err("the malformed CSV is refused"),
        NationalCountyReferenceError::OutsideDomesticScope(
            CountyGeoid::try_from("72001").expect("the fixture value fits the target range")
        )
    );
}

#[test]
fn county_order_and_column_shape_are_canonical() {
    let text = source();
    let mut lines: Vec<_> = text.lines().map(str::to_owned).collect();
    lines.swap(1, 2);
    assert_eq!(
        parse_csv(&(lines.join("\n") + "\n")).expect_err("the malformed CSV is refused"),
        NationalCountyReferenceError::CountyOrder
    );
    assert_eq!(
        parse_csv(&text.replacen("county_geoid", "county_id", 1))
            .expect_err("the malformed CSV is refused"),
        NationalCountyReferenceError::Header
    );
    assert!(parse_csv(&text.replacen("Autauga County", "\"Autauga\" County", 1)).is_err());
}

#[test]
fn sentinel_and_status_cannot_contradict_the_usable_value() {
    assert_eq!(
        acs_cell(&["", "-555555555", "controlled_estimate"])
            .expect("the fixture call `acs_cell` succeeds for the authored inputs")
            .status(),
        ObservationStatus::ControlledEstimate
    );
    assert_eq!(
        acs_cell(&["0", "-555555555", "controlled_estimate"])
            .expect_err("the fixture call `acs_cell` fails for the authored inputs"),
        NationalCountyReferenceError::Observation
    );
    assert_eq!(
        acs_cell(&["", "0", "published"])
            .expect_err("the fixture call `acs_cell` fails for the authored inputs"),
        NationalCountyReferenceError::Observation
    );
    assert_eq!(
        acs_cell(&["1", "2", "published"])
            .expect_err("the fixture call `acs_cell` fails for the authored inputs"),
        NationalCountyReferenceError::Observation
    );
    assert_eq!(
        acs_cell(&["9223372036854775808", "9223372036854775808", "published"])
            .expect_err("the fixture call `acs_cell` fails for the authored inputs"),
        NationalCountyReferenceError::NumericValue
    );
}

#[test]
fn qcew_suppression_retains_establishments_and_never_creates_zero_jobs() {
    let fields = [
        "suppressed",
        "N",
        "7",
        "7",
        "published",
        "",
        "0",
        "suppressed",
        "",
        "0",
        "suppressed",
        "",
        "0",
        "suppressed",
    ];
    let row =
        parse::qcew(&fields).expect("the fixture call `qcew` succeeds for the authored inputs");
    assert_eq!(row.establishments.value(), Some(7));
    assert_eq!(row.jobs.value(), None);
    assert_eq!(row.jobs.raw(), "0");
    assert_eq!(row.jobs.status(), ObservationStatus::Suppressed);
    let mut wrong = fields;
    wrong[6] = "1";
    assert_eq!(
        parse::qcew(&wrong).expect_err("the fixture call `qcew` fails for the authored inputs"),
        NationalCountyReferenceError::Observation
    );
    let mut wrong = fields;
    wrong[1] = "";
    assert_eq!(
        parse::qcew(&wrong).expect_err("the fixture call `qcew` fails for the authored inputs"),
        NationalCountyReferenceError::Observation
    );
}
