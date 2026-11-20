//! The county's session rule crosses the real BSL/tick boundary.

// Shared fixture modules contain helpers used by other integration targets.
#[allow(
    dead_code,
    reason = "the shared fixture module serves other integration targets"
)]
#[path = "../../babylon-persistence/src/michigan_dynamic_hex_foundation.rs"]
mod michigan_dynamic_hex_foundation;
#[allow(
    dead_code,
    reason = "the shared fixture module serves other integration targets"
)]
#[path = "support/organizer_aid_fixture.rs"]
mod organizer_aid_fixture;

use crate::organizer_aid_fixture::{MATERIAL, PRACTICE, PRODUCTS};

const COUNTY_REVIEW: &str =
    include_str!("../../../../content/scenarios/national/county-review-cycle.bsl");

#[test]
fn a_campaign_with_the_rule_and_no_county_section_is_refused_by_name() {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("the Michigan hex foundation builds");
    let error = organizer_aid_fixture::try_session(
        foundation,
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}\n{COUNTY_REVIEW}"),
        organizer_aid_fixture::opening(),
        organizer_aid_fixture::config(),
    )
    .err()
    .expect("the county's rule without a county section refuses before gameplay");
    assert!(
        error
            .to_string()
            .contains("County review needs a captured county administration"),
        "{error}"
    );
}

#[test]
fn the_same_campaign_without_the_rule_opens() {
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .expect("the Michigan hex foundation builds");
    organizer_aid_fixture::try_session(
        foundation,
        &format!("{MATERIAL}\n{PRODUCTS}\n{PRACTICE}"),
        organizer_aid_fixture::opening(),
        organizer_aid_fixture::config(),
    )
    .expect("the fixture opens a session");
}
