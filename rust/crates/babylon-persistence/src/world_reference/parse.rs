use super::{
    CounterpartReference, GoodsTradeReference, PopulationReference, PopulationSource,
    PopulationStatus, PopulationSubtotal, TradeStatus, UsRelationship, WorldMember, WorldReference,
    WorldReferenceError as Error, WorldScope, MEMBER_COUNT,
};
use babylon_kernel::economic_location::{ForeignCounterpart, UsDependency};
use serde::Deserialize;
use std::collections::BTreeSet;

const POPULATION_HEADER: &str = "identity_id,counterpart_id,disposition,status,accounted_in_identity,population_persons,population_evidence,source_kind,source_date,source_sheet,source_row,source_area_name,source_notes,source_population_thousands_raw";
const TRADE_HEADER: &str = "identity_id,identity_kind,population_identity_id,population_aggregation,m49_code,iso_alpha2,area_name,census_code,census_reporter_code,census_area_name,counterpart_id,disposition,us_relationship,trade_row_status,trade_source_name,us_imports_annual_raw,us_imports_status,us_imports_monthly_sum,us_imports_annual_minus_monthly,us_imports_jan_raw,us_imports_feb_raw,us_imports_mar_raw,us_imports_apr_raw,us_imports_may_raw,us_imports_jun_raw,us_imports_jul_raw,us_imports_aug_raw,us_imports_sep_raw,us_imports_oct_raw,us_imports_nov_raw,us_imports_dec_raw,us_exports_annual_raw,us_exports_status,us_exports_monthly_sum,us_exports_annual_minus_monthly,us_exports_jan_raw,us_exports_feb_raw,us_exports_mar_raw,us_exports_apr_raw,us_exports_may_raw,us_exports_jun_raw,us_exports_jul_raw,us_exports_aug_raw,us_exports_sep_raw,us_exports_oct_raw,us_exports_nov_raw,us_exports_dec_raw";

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Membership {
    contract: String,
    evidence_class: String,
    memberships: Vec<MemberPolicy>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct MemberPolicy {
    counterpart_id: String,
    disposition: String,
    identity_id: String,
    us_relationship: String,
}

fn records(text: &str, header: &str, columns: usize) -> Result<Vec<Vec<String>>, Error> {
    if !text.ends_with('\n') || text.contains('\r') {
        return Err(Error::CsvShape);
    }
    let mut lines = text.lines();
    if lines.next() != Some(header) {
        return Err(Error::Header);
    }
    let mut rows: Vec<Vec<String>> = Vec::with_capacity(MEMBER_COUNT);
    for line in lines {
        if rows.len() == MEMBER_COUNT {
            return Err(Error::Bound);
        }
        let row = crate::reference_csv::record(line, columns).map_err(|_| Error::CsvShape)?;
        if rows.last().is_some_and(|prior| prior[0] >= row[0]) {
            return Err(Error::Coverage);
        }
        rows.push(row);
    }
    if rows.len() != MEMBER_COUNT {
        return Err(Error::Coverage);
    }
    Ok(rows)
}

pub(super) fn capture(
    population: &str,
    trade: &str,
    membership: &[u8],
) -> Result<WorldReference, Error> {
    let policy: Membership = serde_json::from_slice(membership).map_err(|_| Error::Membership)?;
    if policy.contract != "InternationalCounterpartMembershipV1"
        || policy.evidence_class != "Designed"
        || policy.memberships.len() != MEMBER_COUNT
    {
        return Err(Error::Membership);
    }
    let population = records(population, POPULATION_HEADER, 14)?;
    let trade = records(trade, TRADE_HEADER, 47)?;
    let mut members = Vec::with_capacity(MEMBER_COUNT);
    for ((population, trade), policy) in population.iter().zip(&trade).zip(&policy.memberships) {
        if population[0] != policy.identity_id
            || trade[0] != policy.identity_id
            || population[1] != policy.counterpart_id
            || trade[10] != policy.counterpart_id
            || population[2] != policy.disposition
            || trade[11] != policy.disposition
            || trade[12] != policy.us_relationship
        {
            return Err(Error::Scope);
        }
        let scope = scope(policy)?;
        members.push(WorldMember {
            identity: policy.identity_id.clone(),
            name: trade[6].clone(),
            scope,
            us_relationship: match policy.us_relationship.as_str() {
                "none" => UsRelationship::None,
                "domestic" => UsRelationship::Domestic,
                "us_dependency" => UsRelationship::Dependency,
                "freely_associated_state" => UsRelationship::FreelyAssociatedState,
                _ => return Err(Error::Scope),
            },
            population: population_row(population)?,
            trade: trade_row(trade)?,
        });
    }
    finish(members)
}

fn scope(policy: &MemberPolicy) -> Result<WorldScope, Error> {
    let identity = &policy.identity_id;
    let m49 = identity
        .strip_prefix("m49:")
        .filter(|code| code.len() == 3 && code.bytes().all(|b| b.is_ascii_digit()));
    let trade_child = matches!(identity.as_str(), "census:5082" | "census:5083");
    if m49.is_none() && !trade_child {
        return Err(Error::Membership);
    }
    match (policy.disposition.as_str(), policy.us_relationship.as_str()) {
        ("counterpart", "freely_associated_state")
            if matches!(identity.as_str(), "m49:583" | "m49:584" | "m49:585")
                && policy.counterpart_id == "remaining_asia_pacific" =>
        {
            Ok(WorldScope::Foreign(
                ForeignCounterpart::RemainingAsiaPacific,
            ))
        }
        ("counterpart", "none") => ForeignCounterpart::from_key(&policy.counterpart_id)
            .map(WorldScope::Foreign)
            .ok_or(Error::Scope),
        ("us_dependency", "us_dependency") if policy.counterpart_id.is_empty() => {
            UsDependency::from_m49(m49.ok_or(Error::Scope)?)
                .map(WorldScope::Dependency)
                .ok_or(Error::Scope)
        }
        ("domestic", "domestic") if identity == "m49:840" && policy.counterpart_id.is_empty() => {
            Ok(WorldScope::DomesticContext)
        }
        ("nonmarket", "none") if identity == "m49:010" && policy.counterpart_id.is_empty() => {
            Ok(WorldScope::Nonmarket)
        }
        _ => Err(Error::Scope),
    }
}

fn integer(token: &str) -> Result<u64, Error> {
    if token.is_empty()
        || !token.bytes().all(|b| b.is_ascii_digit())
        || (token.len() > 1 && token.starts_with('0'))
    {
        return Err(Error::Population);
    }
    token.parse().map_err(|_| Error::Population)
}

// Validate numeric source spelling without converting through binary floating point.
fn decimal(token: &str) -> bool {
    if token.is_empty() || token.len() > 64 {
        return false;
    }
    let mut parts = token.split(['e', 'E']);
    let raw_mantissa = parts.next().unwrap_or_default();
    let mantissa = raw_mantissa.strip_prefix('-').unwrap_or(raw_mantissa);
    let mut decimals = mantissa.split('.');
    let whole = decimals.next().unwrap_or_default();
    if whole.is_empty() || !whole.bytes().all(|b| b.is_ascii_digit()) {
        return false;
    }
    if let Some(fraction) = decimals.next() {
        if fraction.is_empty() || !fraction.bytes().all(|b| b.is_ascii_digit()) {
            return false;
        }
    }
    if decimals.next().is_some() {
        return false;
    }
    if let Some(exponent) = parts.next() {
        let digits = exponent.strip_prefix(['+', '-']).unwrap_or(exponent);
        if digits.is_empty() || !digits.bytes().all(|b| b.is_ascii_digit()) {
            return false;
        }
    }
    parts.next().is_none()
}

pub(super) fn population_row(row: &[String]) -> Result<PopulationReference, Error> {
    if row.len() != 14 {
        return Err(Error::CsvShape);
    }
    let status = match row[3].as_str() {
        "source_projection" => PopulationStatus::SourceProjection,
        "designed_scope_apportionment" => PopulationStatus::DesignedScopeApportionment,
        "included_in_parent" => PopulationStatus::IncludedInParent,
        "not_published" => PopulationStatus::NotPublished,
        "trade_only" => PopulationStatus::TradeOnly,
        _ => return Err(Error::Population),
    };
    let persons = if row[5].is_empty() {
        None
    } else {
        Some(integer(&row[5])?)
    };
    let accounted_in = (!row[4].is_empty()).then(|| row[4].clone());
    match status {
        PopulationStatus::SourceProjection | PopulationStatus::DesignedScopeApportionment => {
            let evidence = if status == PopulationStatus::SourceProjection {
                "Derived"
            } else {
                "Designed"
            };
            if persons.is_none()
                || accounted_in.as_deref() != Some(row[0].as_str())
                || row[6] != evidence
                || (status == PopulationStatus::DesignedScopeApportionment
                    && !matches!(row[0].as_str(), "m49:246" | "m49:248"))
            {
                return Err(Error::Population);
            }
        }
        PopulationStatus::IncludedInParent | PopulationStatus::TradeOnly => {
            if persons.is_some()
                || accounted_in.is_none()
                || accounted_in.as_deref() == Some(row[0].as_str())
                || !row[6].is_empty()
            {
                return Err(Error::Population);
            }
        }
        PopulationStatus::NotPublished => {
            if persons.is_some() || accounted_in.is_some() || !row[6].is_empty() {
                return Err(Error::Population);
            }
        }
    }
    let source = projection_source(row, status)?;
    Ok(PopulationReference {
        status,
        persons,
        accounted_in,
        source,
    })
}

fn projection_source(
    row: &[String],
    status: PopulationStatus,
) -> Result<Option<PopulationSource>, Error> {
    let requires_source = status == PopulationStatus::SourceProjection
        || (status == PopulationStatus::DesignedScopeApportionment && row[0] == "m49:246");
    if !requires_source {
        if row[7..].iter().any(|field| !field.is_empty()) {
            return Err(Error::Population);
        }
        return Ok(None);
    }
    if row[7] != "medium_projection"
        || row[8] != "2024-07-01"
        || row[9] != "Medium variant"
        || row[11].is_empty()
        || !decimal(&row[13])
        || row[13].starts_with('-')
    {
        return Err(Error::Population);
    }
    let source_row = integer(&row[10])?;
    if source_row == 0 {
        return Err(Error::Population);
    }
    Ok(Some(PopulationSource {
        kind: row[7].clone(),
        date: row[8].clone(),
        sheet: row[9].clone(),
        row: source_row,
        area_name: row[11].clone(),
        notes: row[12].clone(),
        thousands_raw: row[13].clone(),
    }))
}

fn annual(
    raw: &str,
    status: &str,
    row_status: &str,
) -> Result<(Option<String>, TradeStatus), Error> {
    match (status, row_status) {
        ("published", "published") if decimal(raw) => {
            Ok((Some(raw.to_owned()), TradeStatus::Published))
        }
        ("missing_cell", "published") if raw.is_empty() => Ok((None, TradeStatus::MissingCell)),
        ("not_published", "not_published") if raw.is_empty() => {
            Ok((None, TradeStatus::NotPublished))
        }
        _ => Err(Error::Trade),
    }
}

pub(super) fn trade_row(row: &[String]) -> Result<GoodsTradeReference, Error> {
    if row.len() != 47 {
        return Err(Error::CsvShape);
    }
    let (imports, imports_status) = annual(&row[15], &row[16], &row[13])?;
    let (exports, exports_status) = annual(&row[31], &row[32], &row[13])?;
    if row[13] == "not_published"
        && row[15..]
            .iter()
            .enumerate()
            .any(|(index, field)| !matches!(index, 1 | 17) && !field.is_empty())
    {
        return Err(Error::Trade);
    }
    Ok(GoodsTradeReference {
        imports,
        exports,
        imports_status,
        exports_status,
        census_code: (!row[7].is_empty()).then(|| row[7].clone()),
    })
}

pub(super) fn finish(members: Vec<WorldMember>) -> Result<WorldReference, Error> {
    let mut known_persons = 0_u64;
    let mut dependencies = BTreeSet::new();
    for member in &members {
        known_persons = known_persons
            .checked_add(member.population.persons.unwrap_or(0))
            .ok_or(Error::Arithmetic)?;
        if let WorldScope::Dependency(id) = member.scope {
            if !dependencies.insert(id) {
                return Err(Error::Coverage);
            }
        }
        if matches!(
            member.population.status,
            PopulationStatus::IncludedInParent | PopulationStatus::TradeOnly
        ) {
            let parent = member
                .population
                .accounted_in
                .as_deref()
                .ok_or(Error::ParentRelation)?;
            let row = members
                .iter()
                .find(|row| row.identity == parent)
                .ok_or(Error::ParentRelation)?;
            if row.population.persons.is_none() || row.scope != member.scope {
                return Err(Error::ParentRelation);
            }
        }
    }
    if dependencies.len() != UsDependency::ALL.len() {
        return Err(Error::Coverage);
    }
    let mut counterparts = Vec::with_capacity(12);
    for id in ForeignCounterpart::ALL {
        let selected: Vec<_> = members
            .iter()
            .filter(|row| row.scope == WorldScope::Foreign(id))
            .collect();
        if selected.is_empty() {
            return Err(Error::Coverage);
        }
        let mut population = PopulationSubtotal {
            known_persons: 0,
            missing: Vec::new(),
        };
        for row in selected {
            population.known_persons = population
                .known_persons
                .checked_add(row.population.persons.unwrap_or(0))
                .ok_or(Error::Arithmetic)?;
            if row.population.status == PopulationStatus::NotPublished {
                population.missing.push(row.identity.clone());
            }
        }
        counterparts.push(CounterpartReference { id, population });
    }
    Ok(WorldReference {
        members,
        counterparts,
        known_persons,
    })
}
