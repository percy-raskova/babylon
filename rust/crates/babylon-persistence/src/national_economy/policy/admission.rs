use super::{
    GameCommodity, GameDependencyProfile, GameEquipmentPolicy, GameFinancialPolicy,
    GameHouseholdLifecyclePolicy, GameHouseholdPolicy, GameHouseholdTimePolicy, GameJourneyTiming,
    GameMarketPolicy, GameNeed, GamePrice, GameProfile, GameProfileWage, GameRecipe,
    GameServiceReach, GameWages, InitialAgeDistribution, NationalGamePolicy,
    NationalGamePolicyError,
};
use crate::national_economy::grain::NationalGrainError;
use crate::national_economy::grain::NationalGrainGeneration;
use crate::national_economy::grain::NationalGrainPolicy;
use crate::national_transport::CargoClass;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, TradeSet};
use babylon_kernel::economic_location::ForeignCounterpart;
use babylon_material_circuit::{CompanyConditionOrder, CompanyPortfolioPolicy};

use super::GameOrganizerPolicy;
use super::{
    GameAidPolicy, GameCityPdPolicy, GameCountyReviewPolicy, GameHouseholdSupportClaimant,
};
use crate::national_economy::companies::{
    CompanyCaptureError, CompanyPolicy, ExperimentalPopulation,
};
use babylon_kernel::content_digest;
use babylon_material_circuit::{CommodityKind, HouseholdNeedBasis, ServiceStage, UnitId};
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet};

type Error = NationalGamePolicyError;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawPolicy {
    companies: Option<RawCompanies>,
    grain: RawGrain,
    schema_version: u16,
    evidence_class: String,
    period_days: u64,
    work_hours_per_person: u64,
    default_wage_micros_per_hour: Option<i128>,
    opening_pantry_periods: u64,
    opening_input_periods: u64,
    working_capital_periods: u64,
    retailer_buffer_periods: u64,
    resource_reserve_output_periods: u64,
    handling_hours_per_unit: u64,
    missing_peer_weight_per_establishment: u64,
    household_enterprise_function: String,
    financial: RawFinancial,
    households: RawHouseholds,
    household_time: RawHouseholdTime,
    household_lifecycle: Option<RawHouseholdLifecycle>,
    aid: GameAidPolicy,
    household_support_claimant: Option<RawHouseholdSupportClaimant>,
    city_pd: Option<RawCityPd>,
    county_review: Option<RawCountyReview>,
    organizer: GameOrganizerPolicy,
    markets: RawMarkets,
    equipment: RawEquipment,
    commodity: BTreeMap<String, RawCommodity>,
    process: BTreeMap<String, RawRecipe>,
    household_needs: Vec<RawNeed>,
    counterpart: BTreeMap<String, RawProfile>,
    dependency: RawDependency,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawHouseholdSupportClaimant {
    evidence_class: String,
    county: String,
    households: u64,
    reserve_persons: u64,
}

impl RawHouseholdSupportClaimant {
    fn admit(self) -> Result<GameHouseholdSupportClaimant, Error> {
        if self.evidence_class != "Designed" {
            return Err(Error::Evidence);
        }
        if self.county != "26163" || self.households == 0 || self.households > self.reserve_persons
        {
            return Err(Error::Profile("Wayne household support claimant".into()));
        }
        Ok(GameHouseholdSupportClaimant {
            county: babylon_kernel::geography::CountyGeoid::try_from(self.county.as_str())
                .map_err(|_| Error::Location)?,
            households: self.households,
            reserve_persons: self.reserve_persons,
        })
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawCityPd {
    evidence_class: String,
    positions: u64,
    positions_source: String,
    visits_per_period: u64,
    visit_hours: u64,
}

impl RawCityPd {
    fn admit(self) -> Result<GameCityPdPolicy, Error> {
        if self.evidence_class != "Designed" {
            return Err(Error::Evidence);
        }
        if self.positions == 0
            || self.visits_per_period == 0
            || self.visit_hours == 0
            || self.positions_source.trim().is_empty()
        {
            return Err(Error::Profile("City PD positions, source or visits".into()));
        }
        Ok(GameCityPdPolicy {
            positions: self.positions,
            positions_source: self.positions_source,
            visits_per_period: self.visits_per_period,
            visit_hours: self.visit_hours,
        })
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawCountyReview {
    evidence_class: String,
    county: String,
    first_session_period: u64,
    session_hours: u64,
    bring_hours: u64,
    administration_label: String,
    claimants_body_label: String,
    aid_body_label: String,
}

impl RawCountyReview {
    fn admit(self) -> Result<GameCountyReviewPolicy, Error> {
        if self.evidence_class != "Designed" {
            return Err(Error::Evidence);
        }
        let invalid_text =
            |text: &String| text.trim().is_empty() || text.len() > 128 || text.contains('\0');
        if self.first_session_period == 0
            || self.session_hours == 0
            || self.bring_hours == 0
            || [
                &self.administration_label,
                &self.claimants_body_label,
                &self.aid_body_label,
            ]
            .into_iter()
            .any(invalid_text)
        {
            return Err(Error::Profile("county review terms".into()));
        }
        Ok(GameCountyReviewPolicy {
            county: babylon_kernel::geography::CountyGeoid::try_from(self.county.as_str())
                .map_err(|_| Error::Location)?,
            first_session_period: self.first_session_period,
            session_hours: self.session_hours,
            bring_hours: self.bring_hours,
            administration_label: self.administration_label,
            claimants_body_label: self.claimants_body_label,
            aid_body_label: self.aid_body_label,
        })
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawHouseholdLifecycle {
    initial_age_distribution: InitialAgeDistribution,
    births_per_million_working_age_per_period: u32,
    deaths_per_million_per_period: [u32; 4],
    external_eligible_age_bps: [u16; 3],
}

impl RawHouseholdLifecycle {
    fn admit(self) -> Result<GameHouseholdLifecyclePolicy, Error> {
        if self
            .external_eligible_age_bps
            .into_iter()
            .map(u32::from)
            .sum::<u32>()
            != 10_000
            || self.births_per_million_working_age_per_period > 1_000_000
            || self
                .deaths_per_million_per_period
                .iter()
                .any(|rate| *rate > 1_000_000)
        {
            return Err(Error::Profile(
                "household lifecycle rates or external age mix".into(),
            ));
        }
        Ok(GameHouseholdLifecyclePolicy {
            initial_age_distribution: self.initial_age_distribution,
            rates: babylon_material_circuit::HouseholdLifecycleRates {
                births_per_million_working_age_per_period: self
                    .births_per_million_working_age_per_period,
                deaths_per_million_per_period: self.deaths_per_million_per_period,
            },
            external_eligible_age_bps: self.external_eligible_age_bps,
        })
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawCompanies {
    experiment_controller_count: Option<u16>,
    inherited_grain_policy_sha256: [u8; 32],
    opening_employment_bps: [u16; 3],
    opening_treasury_bps: u16,
    portfolio_weights: [[u16; 4]; 4],
    high_utilization_bps: u16,
    history_periods: u8,
    modest_expansion_bps: u16,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawCommodity {
    label: String,
    unit_label: String,
    kind: String,
    grams_per_unit: u64,
    cargo_class: Option<String>,
    opening_price_micros: Option<i128>,
    minimum_price_micros: Option<i128>,
    maximum_price_micros: Option<i128>,
    price_step_micros: Option<i128>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawRecipe {
    output: String,
    output_units_per_batch: u64,
    labor_hours_per_batch: u64,
    inputs: BTreeMap<String, u64>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawNeed {
    good: String,
    basis: String,
    units_per_basis: u64,
}
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct RawProfile {
    participation_bps: u16,
    opening_employment_bps: u16,
    persons_per_household: u64,
    wage_micros_per_hour: Option<i128>,
    wage_fraction_bps: Option<u16>,
    price_scale_bps: u16,
    function_weights_bps: Vec<u16>,
}
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct RawDependency {
    participation_bps: u16,
    opening_employment_bps: u16,
    persons_per_household: u64,
    wage_micros_per_hour: Option<i128>,
    wage_fraction_bps: Option<u16>,
    price_scale_bps: u16,
    function_weights_bps: Vec<u16>,
    missing_population_game_persons: u64,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawHouseholds {
    private_owner_households_bps: u16,
    next_forty_households_bps: Option<u16>,
}

#[derive(Clone, Copy, Deserialize)]
#[serde(deny_unknown_fields)]
struct RawFinancial {
    wage_tax_bps: u16,
    operating_income_tax_bps: u16,
    private_distribution_bps: u16,
    reserve_food_support_periods: u64,
    cross_border_ownership_bps: u16,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawHouseholdTime {
    hours_per_eligible_person: u64,
    ordinary_protected_hours_per_household: u64,
    ordinary_provisioning_hours_per_household: u64,
    collective_protected_hours_per_person: u64,
    collective_provisioning_hours_per_person: u64,
    external_eligible_persons_bps: u16,
    unmet_hours_per_unit: BTreeMap<String, u64>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawEquipment {
    batches_per_unit_per_period: u64,
    service_batches_per_unit: u64,
    installation_hours_per_unit: u64,
    installation_inputs: BTreeMap<String, u64>,
    installation_workforce_hours_bps: u16,
    expansion_earnings_fraction_bps: u16,
    opening_remaining_service_bps: [u16; 4],
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawMarkets {
    foreign_procurement_bps: u16,
    journey_timing: String,
    service_reach: String,
    paying_order: Option<Vec<String>>,
}

pub(super) fn parse(source: &str) -> Result<NationalGamePolicy, Error> {
    if source.len() > 65_536 {
        return Err(Error::Bounds);
    }
    let raw: RawPolicy = toml::from_str(source).map_err(|_| Error::Syntax)?;
    validate_globals(&raw)?;
    let trades = if raw.schema_version >= 8 {
        TradeSet::Twelve
    } else {
        TradeSet::Ten
    };
    let wages = wages(&raw, trades)?;
    let grain = grain(&raw.grain)?;
    validate_organizer(&raw.organizer)?;
    let county_review_terms = raw.county_review.map(RawCountyReview::admit).transpose()?;
    if let Some(terms) = &county_review_terms {
        validate_county_review(terms, &raw.organizer)?;
    }
    validate_aid(&raw.aid)?;
    let households = households(&raw.households, trades)?;
    let commodities = commodities(raw.commodity, trades)?;
    let recipes = recipes(raw.process, &commodities, trades)?;
    let household_needs = needs(raw.household_needs, &commodities)?;
    let counterparts = counterparts(raw.counterpart, trades)?;
    let dependency = dependency(raw.dependency, trades)?;
    let financial = financial(raw.financial)?;
    let household_time = household_time(
        raw.household_time,
        raw.period_days,
        raw.work_hours_per_person,
        &household_needs,
    )?;
    let markets = markets(&raw.markets, trades, &commodities, &household_needs)?;
    let equipment = equipment(raw.equipment, &commodities)?;
    let source_digest = content_digest::sha256_of(source.as_bytes());
    let grain_identity_policy_digest = raw
        .companies
        .as_ref()
        .map_or(source_digest, |c| c.inherited_grain_policy_sha256);
    if grain_identity_policy_digest == [0; 32] {
        return Err(Error::Shape);
    }
    let companies = companies(raw.companies, raw.schema_version)?;
    Ok(NationalGamePolicy {
        companies,
        grain,
        source_digest,
        grain_identity_policy_digest,
        period_days: raw.period_days,
        work_hours_per_person: raw.work_hours_per_person,
        trades,
        wages,
        opening_pantry_periods: raw.opening_pantry_periods,
        opening_input_periods: raw.opening_input_periods,
        working_capital_periods: raw.working_capital_periods,
        retailer_buffer_periods: raw.retailer_buffer_periods,
        resource_reserve_output_periods: raw.resource_reserve_output_periods,
        handling_hours_per_unit: raw.handling_hours_per_unit,
        missing_peer_weight_per_establishment: raw.missing_peer_weight_per_establishment,
        household_enterprise_function: EconomicFunction::HouseholdServices,
        aid: raw.aid,
        household_support_claimant: raw
            .household_support_claimant
            .map(RawHouseholdSupportClaimant::admit)
            .transpose()?,
        city_pd: raw.city_pd.map(RawCityPd::admit).transpose()?,
        county_review: county_review_terms,
        organizer: raw.organizer,
        financial,
        households,
        household_time,
        household_lifecycle: raw
            .household_lifecycle
            .map(RawHouseholdLifecycle::admit)
            .transpose()?,
        markets,
        equipment,
        commodities,
        recipes,
        household_needs,
        counterparts,
        dependency,
    })
}

/// Admit the optional company policy; schema 3 orders high demand before spare capacity.
fn companies(
    companies: Option<RawCompanies>,
    schema_version: u16,
) -> Result<Option<CompanyPolicy>, Error> {
    companies
        .map(|c| {
            let mut terms = CompanyPolicy::try_new(
                c.opening_employment_bps,
                c.opening_treasury_bps,
                CompanyPortfolioPolicy {
                    condition_order: if schema_version == 3 {
                        CompanyConditionOrder::HighDemandBeforeSpare
                    } else {
                        CompanyConditionOrder::FirstApplicable
                    },
                    rows: c.portfolio_weights,
                    high_utilization_bps: c.high_utilization_bps,
                    history_periods: c.history_periods,
                    modest_expansion_bps: c.modest_expansion_bps,
                },
            )?;
            terms.experiment = c
                .experiment_controller_count
                .map(|n| {
                    ExperimentalPopulation::from_count(n).ok_or(CompanyCaptureError::InvalidTargets)
                })
                .transpose()?;
            Ok::<_, CompanyCaptureError>(terms)
        })
        .transpose()
        .map_err(|_| Error::Shape)
}

/// The review's county and its two body labels repeat the hearing's and the local partner's; the
/// capture reads the names from those, so a table that disagrees with them is refused here.
fn validate_county_review(
    terms: &GameCountyReviewPolicy,
    organizer: &GameOrganizerPolicy,
) -> Result<(), Error> {
    let hearing = organizer
        .hearing
        .as_ref()
        .ok_or_else(|| Error::Profile("county review needs the relief hearing".into()))?;
    if hearing.county_geoid != terms.county.as_str()
        || hearing.claimant_label != terms.claimants_body_label
        || organizer.local_partner_label != terms.aid_body_label
    {
        return Err(Error::Profile(
            "county review names differ from the hearing's".into(),
        ));
    }
    Ok(())
}

fn validate_organizer(organizer: &GameOrganizerPolicy) -> Result<(), Error> {
    if let Some(hearing) = &organizer.hearing {
        if hearing.evidence_class != "Designed"
            || babylon_kernel::geography::CountyGeoid::try_from(hearing.county_geoid.as_str())
                .is_err()
            || hearing.period == 0
            || hearing.period.checked_add(1) != Some(hearing.review_period)
            || !(1..=organizer.contributor_hours_cap).contains(&hearing.attendance_hours)
            || [
                &hearing.claimant_label,
                &hearing.claimant_claim,
                &hearing.partner_claim,
            ]
            .iter()
            .any(|text| text.trim().is_empty() || text.len() > 128 || text.contains('\0'))
        {
            return Err(Error::Profile("Wayne relief hearing terms".into()));
        }
    }
    if organizer.collection_maximum_cash_micros <= 0
        || organizer.collection_initial_cash_micros <= 0
        || organizer.collection_initial_cash_micros > organizer.collection_maximum_cash_micros
        || organizer.collection_protected_cash_floor_micros < 0
        || organizer
            .collection_maximum_cash_micros
            .checked_add(organizer.collection_protected_cash_floor_micros)
            .is_none()
        || organizer.collection_hours == 0
        || organizer.collection_hours > organizer.contributor_hours_cap
        || organizer.evidence_class != "Designed"
        || [
            &organizer.organization_label,
            &organizer.workplace_partner_label,
            &organizer.neighborhood_partner_label,
            &organizer.local_partner_label,
            &organizer.remote_partner_label,
        ]
        .iter()
        .any(|label| label.is_empty() || label.len() > 128 || label.contains('\0'))
        || [
            organizer.contributor_hours_cap,
            organizer.inquiry_hours,
            organizer.contact_hours,
            organizer.partner_response_hours,
            organizer.aid_coordination_hours,
            organizer.initial_agreement_through_period,
            organizer.contact_renewal_periods,
        ]
        .iter()
        .any(|n| !(1..=224).contains(n))
        || organizer
            .contact_hours
            .checked_add(organizer.partner_response_hours)
            .is_none_or(|hours| hours > organizer.contributor_hours_cap)
    {
        return Err(Error::Shape);
    }

    Ok(())
}

fn validate_aid(aid: &GameAidPolicy) -> Result<(), Error> {
    let actors = [
        aid.donor_actor,
        aid.local_recipient_actor,
        aid.remote_recipient_actor,
    ];
    let contributors = [
        aid.donor_contributor_id,
        aid.local_recipient_contributor_id,
        aid.remote_recipient_contributor_id,
    ];
    if aid.evidence_class != "Designed"
        || actors.contains(&0)
        || contributors.contains(&0)
        || actors.into_iter().collect::<BTreeSet<_>>().len() != 3
        || contributors.into_iter().collect::<BTreeSet<_>>().len() != 3
        || aid.organization_opening_cash_micros <= 0
        || aid.maximum_cash_micros <= 0
        || aid.maximum_cash_micros > 1_450_000_000
        || aid.initial_cash_micros < 0
        || aid.initial_cash_micros > aid.maximum_cash_micros
        || aid.initial_food_quantity > aid.maximum_quantity
        || (aid.initial_food_quantity == 0 && aid.initial_cash_micros == 0)
        || aid.fulfillment_hours_per_unit == 0
        || !(1..=4).contains(&aid.maximum_quantity)
    {
        return Err(Error::Shape);
    }
    Ok(())
}

fn equipment(
    raw: RawEquipment,
    goods: &BTreeMap<String, GameCommodity>,
) -> Result<GameEquipmentPolicy, Error> {
    if raw.batches_per_unit_per_period == 0
        || raw.service_batches_per_unit == 0
        || raw.installation_hours_per_unit == 0
        || !(1..=10_000).contains(&raw.installation_workforce_hours_bps)
        || raw.expansion_earnings_fraction_bps > 10_000
        || raw
            .opening_remaining_service_bps
            .iter()
            .any(|n| !(1..=10_000).contains(n))
        || raw.installation_inputs.is_empty()
        || raw.installation_inputs.iter().any(|(key, quantity)| {
            *quantity == 0
                || goods.get(key).is_none_or(|g| {
                    !matches!(g.kind, CommodityKind::Storable { .. }) || g.price.is_none()
                })
        })
    {
        return Err(Error::Profile("equipment policy".to_owned()));
    }
    Ok(GameEquipmentPolicy {
        batches_per_unit_per_period: raw.batches_per_unit_per_period,
        service_batches_per_unit: raw.service_batches_per_unit,
        installation_hours_per_unit: raw.installation_hours_per_unit,
        installation_inputs: raw.installation_inputs,
        installation_workforce_hours_bps: raw.installation_workforce_hours_bps,
        expansion_earnings_fraction_bps: raw.expansion_earnings_fraction_bps,
        opening_remaining_service_bps: raw.opening_remaining_service_bps,
    })
}

fn financial(raw: RawFinancial) -> Result<GameFinancialPolicy, Error> {
    if [
        raw.wage_tax_bps,
        raw.operating_income_tax_bps,
        raw.private_distribution_bps,
        raw.cross_border_ownership_bps,
    ]
    .into_iter()
    .any(|n| n > 10_000)
        || raw.reserve_food_support_periods > 16
    {
        return Err(Error::Profile("financial policy".to_owned()));
    }
    Ok(GameFinancialPolicy {
        wage_tax_bps: raw.wage_tax_bps,
        operating_income_tax_bps: raw.operating_income_tax_bps,
        private_distribution_bps: raw.private_distribution_bps,
        reserve_food_support_periods: raw.reserve_food_support_periods,
        cross_border_ownership_bps: raw.cross_border_ownership_bps,
    })
}

fn household_time(
    raw: RawHouseholdTime,
    period_days: u64,
    work_hours: u64,
    needs: &[GameNeed],
) -> Result<GameHouseholdTimePolicy, Error> {
    let maximum = period_days.checked_mul(24).ok_or(Error::Arithmetic)?;
    if raw.hours_per_eligible_person < work_hours
        || raw.hours_per_eligible_person > maximum
        || [
            raw.ordinary_protected_hours_per_household,
            raw.ordinary_provisioning_hours_per_household,
            raw.collective_protected_hours_per_person,
            raw.collective_provisioning_hours_per_person,
        ]
        .into_iter()
        .any(|hours| !(1..=maximum).contains(&hours))
        || !(1..=10_000).contains(&raw.external_eligible_persons_bps)
        || raw.unmet_hours_per_unit.is_empty()
        || raw
            .unmet_hours_per_unit
            .iter()
            .any(|(key, hours)| *hours == 0 || !needs.iter().any(|need| need.key == *key))
    {
        return Err(Error::Profile("household time policy".to_owned()));
    }
    Ok(GameHouseholdTimePolicy {
        hours_per_eligible_person: raw.hours_per_eligible_person,
        ordinary_protected_hours_per_household: raw.ordinary_protected_hours_per_household,
        ordinary_provisioning_hours_per_household: raw.ordinary_provisioning_hours_per_household,
        collective_protected_hours_per_person: raw.collective_protected_hours_per_person,
        collective_provisioning_hours_per_person: raw.collective_provisioning_hours_per_person,
        external_eligible_persons_bps: raw.external_eligible_persons_bps,
        unmet_hours_per_unit: raw.unmet_hours_per_unit,
    })
}

fn validate_globals(raw: &RawPolicy) -> Result<(), Error> {
    if raw.evidence_class != "Designed" {
        return Err(Error::Evidence);
    }
    if !matches!(
        (
            raw.schema_version,
            raw.companies.is_some(),
            raw.household_lifecycle.is_some(),
            raw.household_support_claimant.is_some(),
            raw.city_pd.is_some(),
            raw.county_review.is_some()
        ),
        (2, false, false, false, false, false)
            | (3 | 4, true, false, false, false, false)
            | (5, true, true, false, false, false)
            | (6, true, true, true, false, false)
            | (7 | 8, true, true, true, true, true)
    ) || raw.period_days != 28
        || !(1..=672).contains(&raw.work_hours_per_person)
        || raw.household_enterprise_function != "household_services"
        || [
            raw.opening_pantry_periods,
            raw.opening_input_periods,
            raw.working_capital_periods,
            raw.retailer_buffer_periods,
        ]
        .into_iter()
        .any(|n| !(1..=16).contains(&n))
        || raw.resource_reserve_output_periods == 0
        || raw.handling_hours_per_unit == 0
        || raw.missing_peer_weight_per_establishment == 0
    {
        return Err(Error::Shape);
    }
    Ok(())
}

fn commodities(
    raw: BTreeMap<String, RawCommodity>,
    trades: TradeSet,
) -> Result<BTreeMap<String, GameCommodity>, Error> {
    let mut expected: BTreeSet<_> = [
        "food",
        "resources",
        "materials",
        "equipment",
        "utility",
        "housing",
        "household_services",
        "business_services",
        "public_provision",
        "resource_deposit",
    ]
    .into_iter()
    .collect();
    if trades == TradeSet::Twelve {
        expected.extend(["consumer_goods", "leisure"]);
    }
    if raw.keys().map(String::as_str).collect::<BTreeSet<_>>() != expected {
        return Err(Error::Shape);
    }
    raw.into_iter()
        .map(|(key, raw)| {
            let row = commodity(&key, raw)?;
            Ok((key, row))
        })
        .collect()
}
fn commodity(key: &str, raw: RawCommodity) -> Result<GameCommodity, Error> {
    let fail = || Error::Commodity(key.to_owned());
    if raw.label.is_empty()
        || raw.label.len() > 256
        || raw.unit_label.is_empty()
        || raw.unit_label.len() > 128
        || raw.label.trim() != raw.label
        || raw.unit_label.trim() != raw.unit_label
        || raw.label.chars().any(char::is_control)
        || raw.unit_label.chars().any(char::is_control)
    {
        return Err(fail());
    }
    let kind = match (raw.kind.as_str(), raw.grams_per_unit) {
        ("storable", grams) if grams > 0 => CommodityKind::Storable {
            grams_per_unit: grams,
        },
        ("utility", 0) => CommodityKind::PeriodService {
            stage: ServiceStage::UtilityProvision,
        },
        ("service", 0) => CommodityKind::PeriodService {
            stage: ServiceStage::LocalServiceProvision,
        },
        _ => return Err(fail()),
    };
    let price = price(key, &raw)?;
    if (key == "resource_deposit") != price.is_none() {
        return Err(fail());
    }
    let cargo = match raw.cargo_class.as_deref() {
        None => None,
        Some("general") => Some(CargoClass::General),
        Some("dry_bulk") => Some(CargoClass::DryBulk),
        Some("crude_oil") => Some(CargoClass::CrudeOil),
        Some("refined_liquid") => Some(CargoClass::RefinedLiquid),
        _ => return Err(fail()),
    };
    if cargo.is_some() != (matches!(kind, CommodityKind::Storable { .. }) && price.is_some()) {
        return Err(fail());
    }
    let mut unit_bytes = b"NationalUnitV1\0".to_vec();
    unit_bytes.extend_from_slice(raw.unit_label.as_bytes());
    Ok(GameCommodity {
        good_id: crate::national_economy::commodity_good_id(key),
        unit_id: UnitId::from_bytes(content_digest::sha256_of(&unit_bytes)),
        label: raw.label,
        unit_label: raw.unit_label,
        kind,
        cargo,
        price,
    })
}
fn price(key: &str, raw: &RawCommodity) -> Result<Option<GamePrice>, Error> {
    match (
        raw.opening_price_micros,
        raw.minimum_price_micros,
        raw.maximum_price_micros,
        raw.price_step_micros,
    ) {
        (None, None, None, None) => Ok(None),
        (Some(opening), Some(minimum), Some(maximum), Some(step))
            if minimum > 0
                && step > 0
                && opening >= minimum
                && opening <= maximum
                && maximum.checked_mul(i128::from(u16::MAX)).is_some() =>
        {
            Ok(Some(GamePrice {
                opening: Currency::from_micro_units(opening),
                minimum: Currency::from_micro_units(minimum),
                maximum: Currency::from_micro_units(maximum),
                step: Currency::from_micro_units(step),
            }))
        }
        _ => Err(Error::Commodity(key.to_owned())),
    }
}

fn recipes(
    raw: BTreeMap<String, RawRecipe>,
    goods: &BTreeMap<String, GameCommodity>,
    trades: TradeSet,
) -> Result<BTreeMap<EconomicFunction, GameRecipe>, Error> {
    // One recipe for each trade of the set but distribution.
    if raw.len() + 1 != trades.functions().len() {
        return Err(Error::Shape);
    }
    raw.into_iter()
        .map(|(key, row)| {
            let function = trades
                .from_source_key(&key)
                .ok_or_else(|| Error::Recipe(key.clone()))?;
            if function == EconomicFunction::DistributionTransport {
                return Err(Error::Recipe(key));
            }
            validate_recipe(&key, &row, goods)?;
            Ok((
                function,
                GameRecipe {
                    output: row.output,
                    output_units_per_batch: row.output_units_per_batch,
                    labor_hours_per_batch: row.labor_hours_per_batch,
                    inputs: row.inputs,
                },
            ))
        })
        .collect()
}
fn validate_recipe(
    key: &str,
    row: &RawRecipe,
    goods: &BTreeMap<String, GameCommodity>,
) -> Result<(), Error> {
    let fail = || Error::Recipe(key.to_owned());
    let output = goods.get(&row.output).ok_or_else(fail)?;
    if row.output_units_per_batch == 0
        || row.labor_hours_per_batch == 0
        || row.inputs.is_empty()
        || row.inputs.contains_key(&row.output)
        || output.price.is_none()
    {
        return Err(fail());
    }
    let price = output.price.as_ref().ok_or_else(fail)?;
    price
        .maximum
        .micro_units()
        .checked_mul(i128::from(row.output_units_per_batch))
        .ok_or(Error::Arithmetic)?;
    for (input, coefficient) in &row.inputs {
        let input = goods.get(input).ok_or_else(fail)?;
        if *coefficient == 0 {
            return Err(fail());
        }
        if let (
            CommodityKind::PeriodService { stage: output },
            CommodityKind::PeriodService { stage: input },
        ) = (output.kind, input.kind)
        {
            if input >= output {
                return Err(fail());
            }
        }
    }
    Ok(())
}

fn needs(
    raw: Vec<RawNeed>,
    goods: &BTreeMap<String, GameCommodity>,
) -> Result<Vec<GameNeed>, Error> {
    if raw.len() != 6 {
        return Err(Error::Shape);
    }
    let mut seen = BTreeSet::new();
    let mut result = Vec::new();
    for row in raw {
        if !seen.insert(row.good.clone())
            || row.units_per_basis == 0
            || goods.get(&row.good).is_none_or(|g| g.price.is_none())
        {
            return Err(Error::HouseholdNeed(row.good));
        }
        let basis = match row.basis.as_str() {
            "persons" => HouseholdNeedBasis::Persons,
            "households" => HouseholdNeedBasis::Households,
            _ => return Err(Error::HouseholdNeed(row.good)),
        };
        result.push(GameNeed {
            key: row.good,
            basis,
            units_per_basis: row.units_per_basis,
        });
    }
    result.sort_by(|a, b| a.key.cmp(&b.key));
    Ok(result)
}
fn profile_wage(key: &str, raw: &RawProfile, trades: TradeSet) -> Result<GameProfileWage, Error> {
    let fail = || Error::Profile(key.to_owned());
    match (trades, raw.wage_micros_per_hour, raw.wage_fraction_bps) {
        (TradeSet::Ten, Some(wage), None) if wage > 0 && wage.checked_mul(672).is_some() => {
            Ok(GameProfileWage::PerHour(Currency::from_micro_units(wage)))
        }
        (TradeSet::Twelve, None, Some(bps)) if (1..=10_000).contains(&bps) => {
            Ok(GameProfileWage::FractionOfUnitedStates { bps })
        }
        // A wage key of the other schema, or the schema's own key missing, is a
        // shape fault; a present key with a bad value stays a profile fault.
        (TradeSet::Ten, None, _)
        | (TradeSet::Ten, _, Some(_))
        | (TradeSet::Twelve, _, None)
        | (TradeSet::Twelve, Some(_), _) => Err(Error::Shape),
        _ => Err(fail()),
    }
}
fn profile(key: &str, raw: RawProfile, trades: TradeSet) -> Result<GameProfile, Error> {
    let wage = profile_wage(key, &raw, trades)?;
    if !(1..=10_000).contains(&raw.participation_bps)
        || raw.opening_employment_bps > 10_000
        || raw.persons_per_household == 0
        || raw.price_scale_bps == 0
        || raw.function_weights_bps.len() != trades.functions().len()
        || raw
            .function_weights_bps
            .iter()
            .map(|n| u64::from(*n))
            .sum::<u64>()
            != 10_000
        || raw.function_weights_bps.contains(&0)
    {
        return Err(Error::Profile(key.to_owned()));
    }
    Ok(GameProfile {
        participation_bps: raw.participation_bps,
        opening_employment_bps: raw.opening_employment_bps,
        persons_per_household: raw.persons_per_household,
        wage,
        price_scale_bps: raw.price_scale_bps,
        function_weights_bps: raw.function_weights_bps,
    })
}
fn counterparts(
    raw: BTreeMap<String, RawProfile>,
    trades: TradeSet,
) -> Result<BTreeMap<ForeignCounterpart, GameProfile>, Error> {
    if raw.len() != 12 {
        return Err(Error::Shape);
    }
    raw.into_iter()
        .map(|(key, row)| {
            let counterpart =
                ForeignCounterpart::from_key(&key).ok_or_else(|| Error::Profile(key.clone()))?;
            Ok((counterpart, profile(&key, row, trades)?))
        })
        .collect()
}
fn dependency(raw: RawDependency, trades: TradeSet) -> Result<GameDependencyProfile, Error> {
    if raw.missing_population_game_persons == 0 {
        return Err(Error::Profile("missing dependency population".to_owned()));
    }
    Ok(GameDependencyProfile {
        missing_population_game_persons: raw.missing_population_game_persons,
        profile: profile(
            "dependency",
            RawProfile {
                participation_bps: raw.participation_bps,
                opening_employment_bps: raw.opening_employment_bps,
                persons_per_household: raw.persons_per_household,
                wage_micros_per_hour: raw.wage_micros_per_hour,
                wage_fraction_bps: raw.wage_fraction_bps,
                price_scale_bps: raw.price_scale_bps,
                function_weights_bps: raw.function_weights_bps,
            },
            trades,
        )?,
    })
}

fn wages(raw: &RawPolicy, trades: TradeSet) -> Result<GameWages, Error> {
    match (trades, raw.default_wage_micros_per_hour) {
        (TradeSet::Ten, Some(wage))
            if wage > 0
                && wage
                    .checked_mul(i128::from(raw.work_hours_per_person))
                    .is_some() =>
        {
            Ok(GameWages::Single(Currency::from_micro_units(wage)))
        }
        (TradeSet::Twelve, None) => Ok(GameWages::Observed),
        _ => Err(Error::Shape),
    }
}

fn households(raw: &RawHouseholds, trades: TradeSet) -> Result<GameHouseholdPolicy, Error> {
    if !(1..=10_000).contains(&raw.private_owner_households_bps) {
        return Err(Error::Profile("private owner household fraction".into()));
    }
    let next_forty_households_bps = match (trades, raw.next_forty_households_bps) {
        (TradeSet::Ten, None) => None,
        (TradeSet::Twelve, Some(bps)) => {
            // The bottom half must exist.
            if !(1..=10_000).contains(&bps)
                || u32::from(raw.private_owner_households_bps) + u32::from(bps) >= 10_000
            {
                return Err(Error::Profile("household bands need a bottom half".into()));
            }
            Some(bps)
        }
        _ => return Err(Error::Shape),
    };
    Ok(GameHouseholdPolicy {
        private_owner_households_bps: raw.private_owner_households_bps,
        next_forty_households_bps,
    })
}

/// The order of paying: each name a priced product once; every storable household need, and only
/// then the services, with utility before every local service.
fn paying_order(
    order: &[String],
    goods: &BTreeMap<String, GameCommodity>,
    needs: &[GameNeed],
) -> Result<(), Error> {
    let fail = || Error::Profile("paying order".to_owned());
    let mut seen = BTreeSet::new();
    let mut first_service = None;
    let mut utility = None;
    let mut first_local_service = None;
    for (index, key) in order.iter().enumerate() {
        let good = goods.get(key).ok_or_else(fail)?;
        if good.price.is_none() || !seen.insert(key.as_str()) {
            return Err(fail());
        }
        match good.kind {
            CommodityKind::Storable { .. } => {}
            CommodityKind::PeriodService { stage } => {
                first_service.get_or_insert(index);
                if stage == ServiceStage::UtilityProvision {
                    utility = Some(index);
                } else {
                    first_local_service.get_or_insert(index);
                }
            }
        }
    }
    for need in needs {
        let good = goods.get(&need.key).ok_or_else(fail)?;
        if matches!(good.kind, CommodityKind::Storable { .. }) {
            let at = order
                .iter()
                .position(|key| *key == need.key)
                .ok_or_else(fail)?;
            if first_service.is_some_and(|service| at > service) {
                return Err(fail());
            }
        }
    }
    if let (Some(utility), Some(local)) = (utility, first_local_service) {
        if utility > local {
            return Err(fail());
        }
    }
    Ok(())
}

fn markets(
    raw: &RawMarkets,
    trades: TradeSet,
    goods: &BTreeMap<String, GameCommodity>,
    needs: &[GameNeed],
) -> Result<GameMarketPolicy, Error> {
    let paying_order = match (trades, &raw.paying_order) {
        (TradeSet::Ten, None) => None,
        (TradeSet::Twelve, Some(order)) => {
            paying_order(order, goods, needs)?;
            Some(order.clone())
        }
        _ => return Err(Error::Shape),
    };
    if raw.foreign_procurement_bps > 10_000
        || raw.journey_timing != "slowest_profile"
        || raw.service_reach != "same_state_or_own_counterpart"
    {
        return Err(Error::Profile("market scope".to_owned()));
    }
    Ok(GameMarketPolicy {
        foreign_procurement_bps: raw.foreign_procurement_bps,
        paying_order,
        journey_timing: GameJourneyTiming::SlowestProfile,
        service_reach: GameServiceReach::SameStateOrOwnCounterpart,
    })
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawGrain {
    evidence_class: String,
    generation: String,
    protected_counties: Vec<String>,
    hub_selection: String,
    access_capacity: String,
    capacity_refinement: String,
}
fn grain(raw: &RawGrain) -> Result<NationalGrainPolicy, Error> {
    use babylon_kernel::geography::CountyGeoid;
    if raw.generation != "state_faf_reserve_positions" {
        return Err(Error::Grain(NationalGrainError::UnsupportedGeneration));
    }
    if raw.evidence_class != "Designed"
        || raw.hub_selection != "largest_observed_population_then_geoid"
        || raw.access_capacity != "captured_hub_lane"
        || raw.capacity_refinement != "essential_food_lower_bound_first_fit"
    {
        return Err(Error::Profile("national grain".into()));
    }
    let protected_counties: BTreeSet<_> = raw
        .protected_counties
        .iter()
        .map(|c| CountyGeoid::try_from(c.as_str()).map_err(|_| Error::Location))
        .collect::<Result<_, _>>()?;
    if protected_counties.len() != raw.protected_counties.len()
        || !["17031", "26163"].into_iter().all(|c| {
            protected_counties
                .iter()
                .any(|p| p.as_bytes() == *c.as_bytes())
        })
    {
        return Err(Error::Profile("protected national counties".into()));
    }
    Ok(NationalGrainPolicy {
        generation: NationalGrainGeneration::StateFafReservePositions,
        protected_counties,
    })
}
