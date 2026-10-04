//! Semantic refusals remain visible beneath the outer exact-artifact digest.
use super::{mapping::FunctionMapping, parse::parse_group, NationalCohortReferenceError as Error};
use crate::national_counties::national_county_reference;

fn row(text: &str) -> Result<super::CohortReference, Error> {
    parse_group(
        text,
        &FunctionMapping::load()?,
        national_county_reference().map_err(Error::CountyReference)?,
    )
}

#[test]
fn known_zero_with_unknown_jobs_does_not_admit_a_group() {
    let group = row("01017,food,5,0,1,0,1,0,0,0,0,311~N~0~~~").unwrap();
    assert_eq!(group.establishments().complete_total(), Some(0));
    assert_eq!(group.jobs().complete_total(), None);
    assert!(!group.is_admitted());
    assert_eq!(
        row("01017,food,5,1,1,0,1,0,0,0,0,311~N~0~~~"),
        Err(Error::Admission)
    );
}

#[test]
fn published_jobs_with_rounded_zero_establishments_are_sufficient() {
    let group = row("01017,food,5,1,1,0,1,1,1,7,1,311~P~0~1~7~2").unwrap();
    assert!(group.is_admitted());
    assert_eq!(group.jobs().complete_total(), Some(1));
    assert_eq!(group.members()[0].mean_weekly_wage_usd, Some(2));
}

#[test]
fn row_subtotals_and_disclosure_must_match_members() {
    assert_eq!(
        row("01017,food,5,1,1,0,1,2,1,7,1,311~P~0~1~7~2"),
        Err(Error::Subtotal)
    );
    assert_eq!(
        row("01017,food,5,1,1,2,1,0,0,0,0,311~N~2~0~~"),
        Err(Error::Disclosure)
    );
    assert_eq!(
        row("01017,food,5,1,1,2,0,0,0,0,0,311~N~2~~~"),
        Err(Error::Subtotal)
    );
}

#[test]
fn source_membership_county_and_identity_are_default_deny() {
    assert!(matches!(
        row("26999,food,5,1,1,0,1,1,1,7,1,311~P~0~1~7~2"),
        Err(Error::UnknownCounty(_))
    ));
    assert_eq!(
        row("01017,capital_goods,5,1,1,0,1,1,1,7,1,311~P~0~1~7~2"),
        Err(Error::MemberIdentity)
    );
    assert_eq!(
        row("01017,food,0,1,1,0,1,1,1,7,1,311~P~0~1~7~2"),
        Err(Error::Ownership)
    );
    assert_eq!(
        row("01017,food,5,1,2,0,2,2,2,14,2,311~P~0~1~7~2;311~P~0~1~7~2"),
        Err(Error::MemberOrder)
    );
}

#[test]
fn source_integer_bounds_and_member_count_are_checked() {
    assert_eq!(
        row("01017,food,5,1,1,9223372036854775808,1,1,1,7,1,311~P~0~1~7~2"),
        Err(Error::NumericValue)
    );
    assert_eq!(
        row("01017,food,5,1,2,0,2,1,1,7,1,311~P~0~1~7~2"),
        Err(Error::MemberCount)
    );
}

#[test]
fn unknown_function_and_positive_context_never_get_an_executable_fallback() {
    let group = row("01017,,5,0,1,1,1,2,1,7,1,99~P~1~2~7~2").unwrap();
    assert_eq!(group.key().function, None);
    assert!(!group.is_admitted());
    assert_eq!(
        row("01017,,5,1,1,1,1,2,1,7,1,99~P~1~2~7~2"),
        Err(Error::Admission)
    );
    assert_eq!(
        row("01017,unknown,5,1,1,1,1,2,1,7,1,99~P~1~2~7~2"),
        Err(Error::Function)
    );
}

#[test]
fn aggregate_overflow_and_noncanonical_numbers_are_refused() {
    assert_eq!(
        row("01017,food,5,1,2,1,2,2,2,14,2,111~P~9223372036854775807~1~7~2;311~P~1~1~7~2"),
        Err(Error::NumericValue)
    );
    assert_eq!(
        row("01017,food,5,1,1,0,1,01,1,7,1,311~P~0~1~7~2"),
        Err(Error::NumericValue)
    );
}

#[test]
fn duplicate_groups_are_refused_before_coverage_checks() {
    let original = super::decode_gzip(super::ARTIFACT).unwrap();
    let mut lines = original.lines();
    let header = lines.next().unwrap();
    let first = lines.next().unwrap();
    let duplicate = format!("{header}\n{first}\n{first}\n");
    assert_eq!(
        super::parse::parse_csv(
            &duplicate,
            &FunctionMapping::load().unwrap(),
            national_county_reference().unwrap()
        ),
        Err(Error::GroupOrder)
    );
}
