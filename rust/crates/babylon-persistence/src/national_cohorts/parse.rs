use super::{
    mapping::FunctionMapping, CohortKey, CohortReference, KnownSubtotal,
    NationalCohortReferenceError as Error, QcewDisclosure, SourceMember, ADMITTED_COUNT,
    GROUP_COUNT, MEMBER_COUNT,
};
use crate::national_counties::NationalCountyReference;
use babylon_kernel::{
    economic_identity::{EconomicFunction, QcewOwnership},
    geography::CountyGeoid,
};

const HEADER: &str = "county_geoid,function_id,ownership_code,admitted,member_count,establishments_known,establishments_published_members,jobs_known,jobs_published_members,payroll_known,payroll_published_members,members";
const MAX_GROUP_MEMBERS: usize = 15;
const MAX_SOURCE_INTEGER: u64 = i64::MAX as u64;

pub(super) fn parse_csv(
    text: &str,
    mapping: &FunctionMapping,
    counties: &NationalCountyReference,
) -> Result<Vec<CohortReference>, Error> {
    if !text.is_ascii() || !text.ends_with('\n') || text.contains('\r') {
        return Err(Error::Header);
    }
    let mut lines = text.split_terminator('\n');
    if lines.next() != Some(HEADER) {
        return Err(Error::Header);
    }
    let mut groups: Vec<CohortReference> = Vec::with_capacity(GROUP_COUNT);
    let mut member_count = 0;
    for line in lines {
        if groups.len() == GROUP_COUNT {
            return Err(Error::Bound);
        }
        let group = parse_group(line, mapping, counties)?;
        if groups
            .last()
            .is_some_and(|prior| prior.key() >= group.key())
        {
            return Err(Error::GroupOrder);
        }
        member_count += group.members().len();
        if member_count > MEMBER_COUNT {
            return Err(Error::Bound);
        }
        groups.push(group);
    }
    if groups.len() != GROUP_COUNT
        || member_count != MEMBER_COUNT
        || groups.iter().filter(|row| row.is_admitted()).count() != ADMITTED_COUNT
    {
        return Err(Error::Coverage);
    }
    Ok(groups)
}

pub(super) fn parse_group(
    line: &str,
    mapping: &FunctionMapping,
    counties: &NationalCountyReference,
) -> Result<CohortReference, Error> {
    let fields: [&str; 12] = line
        .splitn(13, ',')
        .collect::<Vec<_>>()
        .try_into()
        .map_err(|_| Error::CsvShape)?;
    let county = CountyGeoid::try_from(fields[0]).map_err(Error::CountyIdentity)?;
    counties
        .county(county)
        .map_err(|_| Error::UnknownCounty(county))?;
    let function = if fields[1].is_empty() {
        None
    } else {
        Some(EconomicFunction::from_source_key(fields[1]).ok_or(Error::Function)?)
    };
    let ownership = QcewOwnership::from_source_code(fields[2]).ok_or(Error::Ownership)?;
    let key = CohortKey {
        county,
        function,
        ownership,
    };
    let admitted = match fields[3] {
        "0" => false,
        "1" => true,
        _ => return Err(Error::Admission),
    };
    let member_count = bounded_count(fields[4])?;
    if member_count == 0 {
        return Err(Error::MemberCount);
    }
    let members = parse_members(fields[11], key, mapping)?;
    if members.len() != member_count {
        return Err(Error::MemberCount);
    }
    let establishments = verified_subtotal(
        fields[5],
        fields[6],
        members
            .iter()
            .map(|row| Some(row.annual_average_establishments)),
    )?;
    let jobs = verified_subtotal(
        fields[7],
        fields[8],
        members.iter().map(|row| row.annual_average_jobs),
    )?;
    let annual_payroll_usd = verified_subtotal(
        fields[9],
        fields[10],
        members.iter().map(|row| row.annual_payroll_usd),
    )?;
    let positive = [establishments, jobs, annual_payroll_usd]
        .iter()
        .any(|value| value.known_subtotal() > 0);
    if admitted != (function.is_some() && positive) {
        return Err(Error::Admission);
    }
    Ok(CohortReference {
        key,
        admitted,
        establishments,
        jobs,
        annual_payroll_usd,
        members: members.into_boxed_slice(),
    })
}

fn parse_members(
    text: &str,
    key: CohortKey,
    mapping: &FunctionMapping,
) -> Result<Vec<SourceMember>, Error> {
    let mut members: Vec<SourceMember> = Vec::new();
    for text in text.split(';') {
        if members.len() == MAX_GROUP_MEMBERS {
            return Err(Error::Bound);
        }
        let member = parse_member(text, key, mapping)?;
        if members
            .last()
            .is_some_and(|prior| prior.naics_code >= member.naics_code)
        {
            return Err(Error::MemberOrder);
        }
        members.push(member);
    }
    Ok(members)
}
fn parse_member(
    text: &str,
    key: CohortKey,
    mapping: &FunctionMapping,
) -> Result<SourceMember, Error> {
    let fields: [&str; 6] = text
        .splitn(7, '~')
        .collect::<Vec<_>>()
        .try_into()
        .map_err(|_| Error::CsvShape)?;
    if !mapping.admits(fields[0], key.function) {
        return Err(Error::MemberIdentity);
    }
    let disclosure = match fields[1] {
        "P" => QcewDisclosure::Published,
        "N" => QcewDisclosure::Suppressed,
        _ => return Err(Error::Disclosure),
    };
    let annual_average_establishments = integer(fields[2])?;
    let values = match disclosure {
        QcewDisclosure::Published => {
            if fields[3..].iter().any(|field| field.is_empty()) {
                return Err(Error::Disclosure);
            }
            [
                Some(integer(fields[3])?),
                Some(integer(fields[4])?),
                Some(integer(fields[5])?),
            ]
        }
        QcewDisclosure::Suppressed => {
            if fields[3..].iter().any(|field| !field.is_empty()) {
                return Err(Error::Disclosure);
            }
            [None; 3]
        }
    };
    Ok(SourceMember {
        naics_code: fields[0].to_owned(),
        disclosure,
        annual_average_establishments,
        annual_average_jobs: values[0],
        annual_payroll_usd: values[1],
        mean_weekly_wage_usd: values[2],
    })
}
fn verified_subtotal(
    declared_sum: &str,
    declared_published: &str,
    values: impl Iterator<Item = Option<u64>>,
) -> Result<KnownSubtotal, Error> {
    let expected_sum = integer(declared_sum)?;
    let expected_published = bounded_count(declared_published)?;
    let mut subtotal = KnownSubtotal {
        known_sum: 0,
        published_members: 0,
        member_count: 0,
    };
    for value in values {
        subtotal.member_count += 1;
        if let Some(value) = value {
            subtotal.known_sum = subtotal
                .known_sum
                .checked_add(value)
                .filter(|total| *total <= MAX_SOURCE_INTEGER)
                .ok_or(Error::NumericValue)?;
            subtotal.published_members += 1;
        }
    }
    if subtotal.known_sum != expected_sum || subtotal.published_members != expected_published {
        return Err(Error::Subtotal);
    }
    Ok(subtotal)
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
fn bounded_count(text: &str) -> Result<usize, Error> {
    let count = usize::try_from(integer(text)?).map_err(|_| Error::Bound)?;
    if count > MAX_GROUP_MEMBERS {
        return Err(Error::Bound);
    }
    Ok(count)
}
