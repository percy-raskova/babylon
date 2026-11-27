//! Semantic refusals and figures on hand-written rows.
use super::model::{
    NationalTradePayError as Error, NationalTradePayReference, TradePayRow, WageRule,
};
use super::parse;
use crate::national_counties;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_kernel::geography::CountyGeoid;

const HEADER: &str = "county_geoid,function_id,ownership_code,jobs,payroll_usd,jobs_rule,wage_rule,wage_jobs,wage_payroll_usd";
const OWN: &str = "26163,consumer_goods,5,60000,6000000000,published,county,60000,6000000000";
const SERVICES: &str =
    "26163,household_services,5,100000,5200000000,published,county,100000,5200000000";
const WITHHELD: &str = "26163,leisure_hospitality,2,0,0,partial,state,48138,4997065672";

fn geoid(text: &str) -> CountyGeoid {
    CountyGeoid::try_from(text).expect("the fixture geoid is five digits")
}

fn table(lines: &[&str]) -> Result<Vec<TradePayRow>, Error> {
    let counties = national_counties::national_county_reference().expect("the county table loads");
    let mut text = format!("{HEADER}\n");
    for line in lines {
        text.push_str(line);
        text.push('\n');
    }
    parse::parse_csv(&text, counties, 100)
}

fn reference(lines: &[&str]) -> NationalTradePayReference {
    NationalTradePayReference::from_rows(
        table(lines).expect("the fixture rows are well formed"),
        [0; 32],
    )
    .expect("the fixture rows hold jobs")
}

fn first_row(line: &str) -> TradePayRow {
    table(&[line]).expect("the fixture row parses")[0]
}

#[test]
fn a_county_row_pays_its_own_wage() {
    let row = first_row(OWN);
    assert_eq!(row.wage_rule, WageRule::County);
    assert_eq!(row.hourly_wage().expect("a wage").micro_units(), 48_076_923);
    assert_eq!(
        first_row(SERVICES)
            .hourly_wage()
            .expect("a wage")
            .micro_units(),
        25_000_000
    );
}

#[test]
fn a_withheld_row_takes_the_state_pair() {
    assert_eq!(
        first_row(WITHHELD)
            .hourly_wage()
            .expect("a wage")
            .micro_units(),
        49_907_254
    );
}

#[test]
fn the_county_average_counts_its_own_jobs() {
    let pay = reference(&[OWN, SERVICES, WITHHELD]);
    assert_eq!(pay.county_average(geoid("26163")).micro_units(), 33_653_846);
}

#[test]
fn a_county_without_rows_takes_the_state_average() {
    let pay = reference(&[OWN, SERVICES, WITHHELD]);
    // Another county of state 26, and counties of states with no rows at all.
    assert_eq!(pay.county_average(geoid("26001")).micro_units(), 33_653_846);
    assert_eq!(pay.county_average(geoid("15005")).micro_units(), 33_653_846);
    // A state with rows of its own keeps its own figure; the nation's is over all rows.
    let two = reference(&[
        "01001,household_services,5,1000,26000000,published,county,1000,26000000",
        OWN,
        SERVICES,
    ]);
    assert_eq!(two.county_average(geoid("01003")).micro_units(), 12_500_000);
    assert_eq!(two.county_average(geoid("26001")).micro_units(), 33_653_846);
    assert_eq!(two.county_average(geoid("15005")).micro_units(), 33_522_455);
}

#[test]
fn a_county_whose_rows_hold_no_jobs_takes_its_states_figure() {
    let pay = reference(&[
        "26001,leisure_hospitality,2,0,0,partial,state,48138,4997065672",
        OWN,
    ]);
    assert_eq!(pay.county_average(geoid("26001")).micro_units(), 48_076_923);
}

#[test]
fn national_wage_sums_every_place() {
    let pay = reference(&[OWN]);
    assert_eq!(
        pay.national_wage(EconomicFunction::ConsumerGoods)
            .micro_units(),
        48_076_923
    );
}

#[test]
fn bad_rows_are_refused() {
    let counties = national_counties::national_county_reference().expect("the county table loads");
    let with =
        |header: &str, line: &str| parse::parse_csv(&format!("{header}\n{line}\n"), counties, 10);
    assert_eq!(with("county_geoid,function_id", OWN), Err(Error::Header));
    assert_eq!(
        with(
            HEADER,
            "26163,consumer_goods,5,60000,6000000000,published,county,60000"
        ),
        Err(Error::CsvShape)
    );
    let bad = |line: &str| table(&[line]).map(|_| ());
    assert_eq!(
        bad("26163,consumer_goods,5,0042,6000000000,published,county,60000,6000000000"),
        Err(Error::NumericValue)
    );
    assert_eq!(
        bad("26163,consumer_goods,5,60000,6000000000,mixed,county,60000,6000000000"),
        Err(Error::Rule)
    );
    assert_eq!(
        bad("26163,consumer_goods,5,60000,6000000000,published,county,0,6000000000"),
        Err(Error::Wage)
    );
    assert_eq!(
        bad("26163,consumer_goods,5,60000,6000000000,published,state,60000,0"),
        Err(Error::Wage)
    );
    assert_eq!(table(&[SERVICES, OWN]).map(|_| ()), Err(Error::Order));
    assert_eq!(table(&[OWN, OWN]).map(|_| ()), Err(Error::Order));
    assert_eq!(
        bad("26163,consumer_goods,5,60000,6000000000,published,county,60000,6000000001"),
        Err(Error::Rule)
    );
    assert_eq!(
        bad("26163,quarrying,5,60000,6000000000,published,county,60000,6000000000"),
        Err(Error::Function)
    );
}

#[test]
fn a_table_with_one_row_removed_is_refused_as_coverage() {
    let counties = national_counties::national_county_reference().expect("the county table loads");
    let cohorts = crate::national_cohorts::national_cohort_reference_v2()
        .expect("the twelve-trade cohort table loads");
    let rows = parse::parse_csv(
        &super::artifact::decode_gzip(super::artifact::ARTIFACT).expect("the table inflates"),
        counties,
        65_065,
    )
    .expect("the committed rows parse");
    assert_eq!(super::artifact::check_coverage(&rows, cohorts), Ok(()));
    let mut short = rows.clone();
    short.remove(1_000);
    assert_eq!(
        super::artifact::check_coverage(&short, cohorts),
        Err(Error::Coverage)
    );
    // The ten-trade table is no cover for the twelve-trade rows.
    let ten =
        crate::national_cohorts::national_cohort_reference().expect("the ten-trade table loads");
    assert_eq!(
        super::artifact::check_coverage(&rows, ten),
        Err(Error::Coverage)
    );
}

#[test]
fn an_empty_table_is_refused_before_any_zero_wage_is_built() {
    assert_eq!(
        NationalTradePayReference::from_rows(Vec::new(), [0; 32]),
        Err(Error::EmptyTable)
    );
}
