//! The committed pay table, read against the committed twelve-trade cohort table.
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership};
use babylon_kernel::geography::CountyGeoid;
use babylon_persistence::national_cohorts::{self, CohortKey};
use babylon_persistence::national_counties;
use babylon_persistence::national_trade_pay::{
    self, NationalTradePayError, NationalTradePayReference, WageRule,
};

#[test]
fn the_committed_pay_table() {
    let pay = national_trade_pay::national_trade_pay_reference().expect("the pay table loads");
    let cohorts =
        national_cohorts::national_cohort_reference_v2().expect("the twelve-trade cohorts load");
    let counties = national_counties::national_county_reference().expect("the county table loads");
    assert_eq!(pay.rows().len(), 65_065);
    assert_eq!(cohorts.admitted_cohorts().count(), 65_065);
    for group in cohorts.admitted_cohorts() {
        assert!(pay.row(group.key()).is_some(), "{:?}", group.key());
    }
    let wayne = CohortKey {
        county: CountyGeoid::try_from("26163").expect("a geoid"),
        function: Some(EconomicFunction::ConsumerGoods),
        ownership: QcewOwnership::Private,
    };
    let row = pay.row(wayne).expect("Wayne has consumer goods");
    assert!(row.jobs >= 53_000, "{}", row.jobs);
    assert_eq!(row.wage_rule, WageRule::County);
    assert_eq!(counties.counties().len(), 3_144);
    for county in counties.counties() {
        assert!(pay.county_average(county.geoid()).micro_units() > 0);
    }
    assert_eq!(pay.artifact_sha256().len(), 32);
}

#[test]
fn altered_bytes_are_refused() {
    let cohorts =
        national_cohorts::national_cohort_reference_v2().expect("the twelve-trade cohorts load");
    let counties = national_counties::national_county_reference().expect("the county table loads");
    assert_eq!(
        NationalTradePayReference::decode_captured(&[0x1f, 0x8b, 0], cohorts, counties),
        Err(NationalTradePayError::ArtifactDigest)
    );
}
