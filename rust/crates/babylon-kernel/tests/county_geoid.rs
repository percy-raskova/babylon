use babylon_kernel::geography::{CountyGeoid, CountyGeoidError, CountyJurisdiction};

#[test]
fn exact_geoid_keeps_leading_zeros_without_granting_membership() {
    let county = CountyGeoid::try_from("01001").unwrap();
    assert_eq!(county.as_bytes(), *b"01001");
    assert_eq!(county.as_str(), "01001");
    assert_eq!(county.state_fips(), *b"01");
    assert_eq!(county.county_fips(), *b"001");
    assert_eq!(county.jurisdiction(), CountyJurisdiction::State);
    assert_eq!(
        CountyGeoid::try_from("11001").unwrap().jurisdiction(),
        CountyJurisdiction::DistrictOfColumbia
    );
    assert_eq!(
        CountyGeoid::try_from("72001").unwrap().jurisdiction(),
        CountyJurisdiction::Dependency
    );
    assert_eq!(
        CountyGeoid::try_from("99999").unwrap().jurisdiction(),
        CountyJurisdiction::Unknown
    );
    assert_eq!(CountyGeoid::try_from("01000").unwrap().as_str(), "01000");
}

#[test]
fn refuses_lossy_or_nonnumeric_identities() {
    assert_eq!(
        CountyGeoid::try_from("1001"),
        Err(CountyGeoidError::Length { actual: 4 })
    );
    assert_eq!(
        CountyGeoid::try_from("010011"),
        Err(CountyGeoidError::Length { actual: 6 })
    );
    for invalid in ["01a01", "01 01", "+1001", "０00"] {
        assert!(CountyGeoid::try_from(invalid).is_err(), "{invalid}");
    }
    assert_eq!(
        CountyGeoid::try_from(*b"01a01"),
        Err(CountyGeoidError::NonDecimal)
    );
}
