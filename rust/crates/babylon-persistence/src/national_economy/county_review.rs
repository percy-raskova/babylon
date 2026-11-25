//! Designed national county review capture, bound to the opening's household cohorts, staffing and
//! household-support lines.
//!
//! The configuration names the county's household groups and their crews; the opening roster places
//! every household of every ordinary group by the people its crews have at the opening. Nothing
//! here reads the City PD's capture: only cohorts, staffing, employment, ownership and the
//! household-support lines, which `city_pd::add_opening` leaves as they were.

use std::collections::{BTreeMap, BTreeSet};

use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::content_digest;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    AccountId, EmploymentTerms, FinalDemandPrincipalId, HouseholdKind, LaborCompensation,
    PublicAccountId, PublicTransferTreatment, StaffingMemberId,
};
use babylon_practice_contract::{
    Band, CityPdConfig, CountyReviewConfig, CountyReviewCrew, CountyReviewError, CountyReviewGroup,
    CountyReviewState, GroupKind, OpeningCrew, OrganizerHearingConfig, PayMode,
    COUNTY_REVIEW_SCHEMA_VERSION,
};

use crate::economic_catalog::{EconomicCatalogError, EconomicOpening};
use crate::national_economy::{
    NationalAidCapture, NationalGamePolicy, NationalOpeningError, NationalSupportClaimant,
    NATIONAL_SCENARIO_ID,
};
use crate::national_household_allocation::HouseholdBudgetKey;

use std::result::Result as StdResult;

type Result<T> = StdResult<T, EconomicCatalogError>;

/// Why the county review could not be captured from the opening.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CountyReviewCaptureError {
    /// The kernel refused the configuration or the opening roster.
    Kernel(CountyReviewError),
    /// The policy's review county is not the county the opening's cohorts are in.
    County,
    /// The policy's names differ from the hearing's or from the opening's own.
    Names,
    /// A group's household-support line is not a whole number of units.
    SupportNotWholeUnits {
        /// The group's name.
        group: String,
    },
    /// A member who has people has no employment terms at its workplace.
    NoEmploymentTerms {
        /// The group the member belongs to.
        group: String,
    },
    /// One member has two employment rows.
    DuplicateEmployment,
    /// A cohort of the county has no budget key, so no name.
    UnnamedGroup,
    /// The City PD's payroll site employs no crew of the county's households, so the ledger could
    /// not name its payroll.
    PayrollSiteWithoutCrew,
    /// The band a rule of thirds needs more households for than the opening can place there.
    BandShort {
        /// The band that is short.
        band: Band,
        /// Households the band needs.
        needed: u64,
        /// Households the opening has that can fill it.
        found: u64,
    },
}

impl From<CountyReviewCaptureError> for EconomicCatalogError {
    fn from(error: CountyReviewCaptureError) -> Self {
        Self::CountyReview(error)
    }
}

impl From<CountyReviewError> for EconomicCatalogError {
    fn from(error: CountyReviewError) -> Self {
        Self::CountyReview(CountyReviewCaptureError::Kernel(error))
    }
}

/// The captured county administration and the roster it opens with.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct CountyReviewOpening {
    pub config: CountyReviewConfig,
    pub state: CountyReviewState,
}

/// The captures the county's groups and names are read from.
pub(crate) struct CountyReviewCapture<'a> {
    pub opening: &'a EconomicOpening,
    pub policy: &'a NationalGamePolicy,
    pub aid: &'a NationalAidCapture,
    pub claimant: &'a NationalSupportClaimant,
    pub household_keys: &'a BTreeMap<FinalDemandPrincipalId, HouseholdBudgetKey>,
    pub hearing: &'a OrganizerHearingConfig,
}

fn actor_key() -> StableElementKey {
    StableElementKey::Node {
        scenario: NATIONAL_SCENARIO_ID.into(),
        local_name: "wayne-county-administration".into(),
    }
}

fn actor_id() -> Result<u64> {
    super::city_pd::actor_id_of(&actor_key())
}

fn authority_id(campaign: [u8; 16], actor_id: u64) -> [u8; 16] {
    let mut preimage = b"babylon.county-review-authority.v1\0".to_vec();
    preimage.extend_from_slice(&campaign);
    preimage.extend_from_slice(&actor_id.to_be_bytes());
    let mut id = [0; 16];
    id.copy_from_slice(&content_digest::sha256_of(&preimage)[..16]);
    id
}

fn county_location(policy: &NationalGamePolicy) -> Result<EconomicLocation> {
    let terms = policy
        .county_review
        .as_ref()
        .ok_or(EconomicCatalogError::Opening(
            "the county review needs a national policy that carries [county_review]",
        ))?;
    EconomicLocation::domestic_county(terms.county).map_err(|_| EconomicCatalogError::Identity)
}

/// A group's name: its budget key's label, with the role of a cohort carved out of a budget group
/// added where the carving would otherwise repeat the label.
fn group_label(
    capture: &CountyReviewCapture<'_>,
    principal: FinalDemandPrincipalId,
) -> Result<String> {
    let key = capture
        .household_keys
        .get(&principal)
        .ok_or(CountyReviewCaptureError::UnnamedGroup)?;
    let role = if principal == capture.claimant.principal {
        Some("claimants")
    } else {
        capture
            .aid
            .children
            .iter()
            .enumerate()
            .find_map(|(at, child)| {
                (child.principal == principal).then_some(match at {
                    0 => "aid donors",
                    1 => "aid partners",
                    _ => "remote aid partners",
                })
            })
    };
    Ok(role.map_or_else(
        || key.label().to_owned(),
        |role| format!("{} ({role})", key.label()),
    ))
}

/// The groups of the county: its household cohorts, in principal order.
fn groups(
    capture: &CountyReviewCapture<'_>,
    county: EconomicLocation,
    public: PublicAccountId,
    unit_price: i128,
) -> Result<Vec<CountyReviewGroup>> {
    let opening = capture.opening;
    let owners: BTreeSet<FinalDemandPrincipalId> = opening
        .institutions
        .ownership
        .iter()
        .filter(|claim| claim.shares > 0)
        .filter_map(|claim| match claim.beneficiary {
            AccountId::Household(principal) => Some(principal),
            _ => None,
        })
        .collect();
    let partners = capture
        .aid
        .children
        .get(1)
        .ok_or(EconomicCatalogError::Identity)?
        .principal;
    let mut groups = Vec::new();
    for seed in opening
        .households
        .iter()
        .filter(|seed| seed.location == county)
    {
        let label = group_label(capture, seed.principal_id)?;
        let mut support = 0_i128;
        for line in &opening.institutions.public_allocations {
            if line.treatment == PublicTransferTreatment::HouseholdIncomeSupport
                && line.recipient == AccountId::Household(seed.principal_id)
            {
                if line.public_account != public {
                    return Err(EconomicCatalogError::Identity);
                }
                support = support
                    .checked_add(line.amount_per_period.micro_units())
                    .ok_or(EconomicCatalogError::Arithmetic)?;
            }
        }
        if support % unit_price != 0 {
            return Err(CountyReviewCaptureError::SupportNotWholeUnits { group: label }.into());
        }
        let roll_units =
            u64::try_from(support / unit_price).map_err(|_| EconomicCatalogError::Arithmetic)?;
        let (kind, opening_households) = match seed.kind {
            HouseholdKind::Ordinary => (GroupKind::Ordinary, seed.households),
            HouseholdKind::CollectiveResidence => (GroupKind::CollectiveResidence, 0),
        };
        groups.push(CountyReviewGroup {
            group_id: seed.principal_id.as_bytes(),
            label,
            kind,
            opening_households,
            roll_units,
            has_ownership_income: owners.contains(&seed.principal_id),
            receives_mutual_aid: seed.principal_id == partners,
        });
    }
    groups.sort_by_key(|group| group.group_id);
    Ok(groups)
}

/// The crews of the ordinary groups, and the people each has at the opening, in crew order.
fn crews(
    opening: &EconomicOpening,
    groups: &[CountyReviewGroup],
) -> Result<(Vec<CountyReviewCrew>, Vec<OpeningCrew>)> {
    let position: BTreeMap<[u8; 32], usize> = groups
        .iter()
        .enumerate()
        .filter(|(_, group)| group.kind == GroupKind::Ordinary)
        .map(|(at, group)| (group.group_id, at))
        .collect();
    let mut terms: BTreeMap<StaffingMemberId, &EmploymentTerms> = BTreeMap::new();
    for row in &opening.employment {
        if terms.insert(row.member_id, row).is_some() {
            return Err(CountyReviewCaptureError::DuplicateEmployment.into());
        }
    }
    let labels: BTreeMap<_, _> = opening
        .sites
        .iter()
        .map(|site| (site.site_id, site.label.as_str()))
        .collect();
    let mut found: Vec<(CountyReviewCrew, OpeningCrew)> = Vec::new();
    for pool in &opening.staffing {
        for member in &pool.members {
            let Some(group) = position.get(&member.member.household_id().as_bytes()) else {
                continue;
            };
            let people = member
                .employed
                .checked_add(member.reserve)
                .ok_or(EconomicCatalogError::Arithmetic)?;
            let Some(row) = terms.get(&member.member.member_id()) else {
                if people == 0 {
                    continue;
                }
                return Err(CountyReviewCaptureError::NoEmploymentTerms {
                    group: groups[*group].label.clone(),
                }
                .into());
            };
            let pay_mode = match row.compensation {
                LaborCompensation::Wage(_) => PayMode::Wage,
                LaborCompensation::WorkingOwner => PayMode::WorkingOwner,
                LaborCompensation::UnpaidFamily => PayMode::UnpaidFamily,
            };
            let workplace_label = labels
                .get(&row.site_id)
                .ok_or(EconomicCatalogError::Identity)?;
            found.push((
                CountyReviewCrew {
                    crew_id: member.member.member_id().as_bytes(),
                    group: u32::try_from(*group).map_err(|_| EconomicCatalogError::Arithmetic)?,
                    site_id: row.site_id.as_bytes(),
                    unit_id: row.unit_id.as_bytes(),
                    workplace_label: (*workplace_label).to_owned(),
                    pay_mode,
                },
                OpeningCrew {
                    crew: 0,
                    at_work: member.employed,
                    seeking: member.reserve,
                },
            ));
        }
    }
    found.sort_by_key(|(crew, _)| crew.crew_id);
    let mut configured = Vec::with_capacity(found.len());
    let mut people = Vec::with_capacity(found.len());
    for (at, (crew, opening_crew)) in found.into_iter().enumerate() {
        configured.push(crew);
        people.push(OpeningCrew {
            crew: u32::try_from(at).map_err(|_| EconomicCatalogError::Arithmetic)?,
            ..opening_crew
        });
    }
    Ok((configured, people))
}

/// Turns the kernel's two band refusals into capture errors that say how many households were
/// needed and how many there were.
fn band_refusal(
    config: &CountyReviewConfig,
    people: &[OpeningCrew],
    error: CountyReviewError,
) -> EconomicCatalogError {
    let short = |band: Band, owners: bool| -> EconomicCatalogError {
        let total: u64 = config
            .groups
            .iter()
            .filter(|group| {
                group.kind == GroupKind::Ordinary && group.has_ownership_income == owners
            })
            .map(|group| group.opening_households)
            .sum();
        let ratio = if owners { (1, 9) } else { (4, 5) };
        let Ok((needed, _)) = babylon_practice_contract::ratio_split(total, ratio.0, ratio.1)
        else {
            return error.into();
        };
        let Ok(placed) = babylon_practice_contract::opening_placement(config, people) else {
            return error.into();
        };
        let found = placed
            .iter()
            .filter(|row| {
                usize::try_from(row.group)
                    .ok()
                    .and_then(|group| config.groups.get(group))
                    .is_some_and(|group| group.has_ownership_income == owners)
                    && row.crew.is_none() == owners
            })
            .map(|row| row.households)
            .sum();
        CountyReviewCaptureError::BandShort {
            band,
            needed,
            found,
        }
        .into()
    };
    match error {
        CountyReviewError::TopBandInLaborForce => short(Band::Top1, true),
        CountyReviewError::WageBandOutsideLaborForce => short(Band::Next40, false),
        other => other.into(),
    }
}

/// The digest of the designed inputs the configuration is built from.
fn content_identity(
    campaign: [u8; 16],
    actor_id: u64,
    public_account_id: [u8; 32],
    unit_price: i128,
    policy: &NationalGamePolicy,
    going_wage: i128,
) -> [u8; 32] {
    let mut content = b"babylon.county-review-national-policy.v1\0".to_vec();
    content.extend_from_slice(&campaign);
    content.extend_from_slice(&actor_id.to_be_bytes());
    content.extend_from_slice(&public_account_id);
    content.extend_from_slice(&unit_price.to_be_bytes());
    content.extend_from_slice(&going_wage.to_be_bytes());
    if let Some(terms) = &policy.county_review {
        content.extend_from_slice(&terms.first_session_period.to_be_bytes());
        content.extend_from_slice(&terms.session_hours.to_be_bytes());
        content.extend_from_slice(&terms.bring_hours.to_be_bytes());
        for label in [
            &terms.administration_label,
            &terms.claimants_body_label,
            &terms.aid_body_label,
        ] {
            content.extend_from_slice(label.as_bytes());
            content.push(0);
        }
    }
    content_digest::sha256_of(&content)
}

/// The households each hearing delegation authorizes, placed on its body's group: the claimants'
/// on the claimant group and the aid partners' on the local aid recipients.
fn opening_reach(
    config: &CountyReviewConfig,
    capture: &CountyReviewCapture<'_>,
) -> Result<[(u32, u64); 2]> {
    let reach_of = |principal: FinalDemandPrincipalId, households: u64| {
        config
            .groups
            .iter()
            .position(|group| group.group_id == principal.as_bytes())
            .and_then(|at| u32::try_from(at).ok())
            .map(|at| (at, households))
            .ok_or(EconomicCatalogError::Identity)
    };
    let partners = capture
        .aid
        .children
        .get(1)
        .ok_or(EconomicCatalogError::Identity)?;
    Ok([
        reach_of(
            capture.claimant.principal,
            capture.hearing.claimant_delegation.authorizing_households,
        )?,
        reach_of(
            partners.principal,
            capture.hearing.partner_delegation.authorizing_households,
        )?,
    ])
}

/// The City PD's payroll is named inside its workplace's grant, so some crew of the county's
/// households must work at that site.
///
/// # Errors
///
/// `PayrollSiteWithoutCrew` when no configured crew works at the payroll site.
pub(crate) fn check_payroll_site(
    config: &CountyReviewConfig,
    city_pd: &CityPdConfig,
) -> Result<()> {
    if config
        .crews
        .iter()
        .any(|crew| crew.site_id == city_pd.payroll_site_account_id)
    {
        Ok(())
    } else {
        Err(CountyReviewCaptureError::PayrollSiteWithoutCrew.into())
    }
}

/// Assembles the county review's configuration and its opening roster.
///
/// # Errors
///
/// A refusal of the policy or the opening: a policy with no `[county_review]`, a county, a name or
/// a support line that does not agree with the opening, a crew with no employment terms, and the
/// kernel's refusals of the configuration and of the roster, with the two band refusals naming the
/// households needed and found.
pub(crate) fn assemble(
    campaign: [u8; 16],
    capture: &CountyReviewCapture<'_>,
) -> Result<CountyReviewOpening> {
    if campaign == [0; 16] {
        return Err(EconomicCatalogError::Identity);
    }
    let policy = capture.policy;
    let terms = policy
        .county_review
        .as_ref()
        .ok_or(EconomicCatalogError::Opening(
            "the county review needs a national policy that carries [county_review]",
        ))?;
    let county = county_location(policy)?;
    let hearing = capture.hearing;
    if hearing.county_geoid != terms.county.as_str()
        || capture.claimant.location != county
        || capture
            .aid
            .children
            .get(1)
            .ok_or(EconomicCatalogError::Identity)?
            .location
            != county
    {
        return Err(CountyReviewCaptureError::County.into());
    }
    if hearing.claimant_label != terms.claimants_body_label
        || policy.organizer.local_partner_label != terms.aid_body_label
    {
        return Err(CountyReviewCaptureError::Names.into());
    }
    let unit_price = super::opening::financial::county_support_unit_price(policy)
        .map_err(EconomicCatalogError::NationalOpening)?
        .micro_units();
    if unit_price <= 0 {
        return Err(EconomicCatalogError::Identity);
    }
    let public_account_id = super::city_pd::public_account_id(county);
    let groups = groups(
        capture,
        county,
        PublicAccountId::from_bytes(public_account_id),
        unit_price,
    )?;
    let (crews, people) = crews(capture.opening, &groups)?;
    let actor_id = actor_id()?;
    // Until the County Review reads the observed going wage (Task 8), only a single wage serves.
    let going_wage = policy
        .wages
        .single()
        .ok_or(EconomicCatalogError::NationalOpening(
            NationalOpeningError::Policy,
        ))?
        .micro_units();
    let content = content_identity(
        campaign,
        actor_id,
        public_account_id,
        unit_price,
        policy,
        going_wage,
    );
    let config = CountyReviewConfig {
        schema_version: COUNTY_REVIEW_SCHEMA_VERSION,
        campaign_id: campaign,
        actor_id,
        authority_id: authority_id(campaign, actor_id),
        county: terms.county.as_bytes(),
        administration_label: terms.administration_label.clone(),
        claimants_body_label: terms.claimants_body_label.clone(),
        aid_body_label: terms.aid_body_label.clone(),
        public_account_id,
        unit_price_micros: unit_price,
        going_wage_micros: going_wage,
        session_hours: terms.session_hours,
        bring_hours: terms.bring_hours,
        first_session_period: terms.first_session_period,
        groups,
        crews,
        content_digest: content,
        policy_source_digest: policy.source_digest,
    };
    babylon_practice_contract::validate_county_review_config(&config)?;
    let reach = opening_reach(&config, capture)?;
    let roster = babylon_practice_contract::opening_roster(&config, &people, &reach)
        .map_err(|error| band_refusal(&config, &people, error))?;
    let state = CountyReviewState {
        schema_version: COUNTY_REVIEW_SCHEMA_VERSION,
        roster,
        last_facts: None,
        last_session: None,
    };
    babylon_practice_contract::validate_county_review_state(&config, &state)?;
    Ok(CountyReviewOpening { config, state })
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_practice_contract::CountyReviewCrew;

    fn config(crew_sites: &[u8]) -> CountyReviewConfig {
        CountyReviewConfig {
            schema_version: COUNTY_REVIEW_SCHEMA_VERSION,
            campaign_id: [1; 16],
            actor_id: 2,
            authority_id: [3; 16],
            county: *b"26163",
            administration_label: "Administration".into(),
            claimants_body_label: "Claimants".into(),
            aid_body_label: "Aid".into(),
            public_account_id: [4; 32],
            unit_price_micros: 280_000_000,
            going_wage_micros: 24_000_000,
            session_hours: 2,
            bring_hours: 2,
            first_session_period: 4,
            groups: vec![],
            crews: crew_sites
                .iter()
                .map(|site| CountyReviewCrew {
                    crew_id: [*site; 32],
                    group: 0,
                    site_id: [*site; 32],
                    unit_id: [9; 32],
                    workplace_label: "Workplace".into(),
                    pay_mode: PayMode::Wage,
                })
                .collect(),
            content_digest: [5; 32],
            policy_source_digest: [6; 32],
        }
    }

    fn city_pd(payroll_site: u8) -> CityPdConfig {
        CityPdConfig {
            schema_version: babylon_practice_contract::CITY_PD_SCHEMA_VERSION,
            campaign_id: [1; 16],
            actor_id: 7,
            authority_id: [8; 16],
            county: *b"26163",
            public_account_id: [4; 32],
            agency_account_id: [10; 32],
            investigator_household_account_id: [11; 32],
            investigator_entitlement_id: [12; 32],
            labor_unit_id: [13; 32],
            visit_hours: 1,
            hourly_wage_micros: 24_000_000,
            visit_cost_micros: 24_000_000,
            appropriation_micros: 24_000_000,
            appropriation_priority: 0,
            payroll_site_account_id: [payroll_site; 32],
            payroll_positions: 1,
            payroll_hours_per_position: 160,
            payroll_micros: 3_840_000_000,
            visits_per_period: 1,
            content_digest: [14; 32],
            policy_source_digest: [15; 32],
        }
    }

    #[test]
    fn the_payroll_site_must_employ_a_crew_of_the_county() {
        assert_eq!(check_payroll_site(&config(&[1, 2]), &city_pd(2)), Ok(()));
        assert_eq!(
            check_payroll_site(&config(&[1, 3]), &city_pd(2)),
            Err(CountyReviewCaptureError::PayrollSiteWithoutCrew.into())
        );
        assert_eq!(
            check_payroll_site(&config(&[]), &city_pd(2)),
            Err(CountyReviewCaptureError::PayrollSiteWithoutCrew.into())
        );
    }
}
