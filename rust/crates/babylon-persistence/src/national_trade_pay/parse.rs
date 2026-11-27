use super::model::{JobsRule, NationalTradePayError as Error, TradePayRow, WageRule};
use crate::national_cohorts::CohortKey;
use crate::national_counties::NationalCountyReference;
use babylon_kernel::economic_identity::{QcewOwnership, TradeSet};
use babylon_kernel::geography::CountyGeoid;

const HEADER: &str = "county_geoid,function_id,ownership_code,jobs,payroll_usd,jobs_rule,wage_rule,wage_jobs,wage_payroll_usd";
const MAX_SOURCE_INTEGER: u64 = i64::MAX as u64;

/// Parse and check every row's shape; `limit` is the most rows the table may hold.
pub(super) fn parse_csv(
    text: &str,
    counties: &NationalCountyReference,
    limit: usize,
) -> Result<Vec<TradePayRow>, Error> {
    if !text.is_ascii() || !text.ends_with('\n') || text.contains('\r') {
        return Err(Error::Header);
    }
    let mut lines = text.split_terminator('\n');
    if lines.next() != Some(HEADER) {
        return Err(Error::Header);
    }
    let mut rows: Vec<TradePayRow> = Vec::with_capacity(limit);
    for line in lines {
        if rows.len() == limit {
            return Err(Error::Bound);
        }
        let row = parse_row(line, counties)?;
        if rows.last().is_some_and(|prior| prior.key >= row.key) {
            return Err(Error::Order);
        }
        rows.push(row);
    }
    Ok(rows)
}

pub(super) fn parse_row(
    line: &str,
    counties: &NationalCountyReference,
) -> Result<TradePayRow, Error> {
    let fields: [&str; 9] = line
        .splitn(10, ',')
        .collect::<Vec<_>>()
        .try_into()
        .map_err(|_| Error::CsvShape)?;
    let county = CountyGeoid::try_from(fields[0]).map_err(|_| Error::CountyIdentity)?;
    counties.county(county).map_err(|_| Error::UnknownCounty)?;
    let function = TradeSet::Twelve
        .from_source_key(fields[1])
        .ok_or(Error::Function)?;
    let ownership = QcewOwnership::from_source_code(fields[2]).ok_or(Error::Ownership)?;
    let row = TradePayRow {
        key: CohortKey {
            county,
            function: Some(function),
            ownership,
        },
        jobs: integer(fields[3])?,
        payroll_usd: integer(fields[4])?,
        jobs_rule: match fields[5] {
            "published" => JobsRule::Published,
            "placed" => JobsRule::Placed,
            "partial" => JobsRule::Partial,
            _ => return Err(Error::Rule),
        },
        wage_rule: match fields[6] {
            "county" => WageRule::County,
            "state" => WageRule::State,
            "nation" => WageRule::Nation,
            "nation_all_ownerships" => WageRule::NationAllOwnerships,
            _ => return Err(Error::Rule),
        },
        wage_jobs: integer(fields[7])?,
        wage_payroll_usd: integer(fields[8])?,
    };
    row.hourly_wage()?;
    if row.wage_rule == WageRule::County
        && (row.jobs_rule == JobsRule::Partial
            || (row.wage_jobs, row.wage_payroll_usd) != (row.jobs, row.payroll_usd))
    {
        return Err(Error::Rule);
    }
    Ok(row)
}

fn integer(text: &str) -> Result<u64, Error> {
    if text.is_empty()
        || !text.bytes().all(|byte| byte.is_ascii_digit())
        || (text.len() > 1 && text.starts_with('0'))
    {
        return Err(Error::NumericValue);
    }
    text.parse::<u64>()
        .ok()
        .filter(|value| *value <= MAX_SOURCE_INTEGER)
        .ok_or(Error::NumericValue)
}
