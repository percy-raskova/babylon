use super::{
    GameCommodity, GameDependencyProfile, GameEquipmentPolicy, GameFinancialPolicy,
    GameJourneyTiming, GameMarketPolicy, GameNeed, GamePrice, GameProfile, GameRecipe,
    GameServiceReach, NationalGamePolicy, NationalGamePolicyError,
};
use crate::national_transport::CargoClass;
use babylon_kernel::{
    content_digest::sha256_of, currency::Currency, economic_identity::EconomicFunction,
    economic_location::ForeignCounterpart,
};
use babylon_material_circuit::{CommodityKind, GoodId, HouseholdNeedBasis, ServiceStage, UnitId};
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet};

type Error = NationalGamePolicyError;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawPolicy {
    schema_version: u16,
    evidence_class: String,
    period_days: u64,
    work_hours_per_person: u64,
    default_wage_micros_per_hour: i128,
    opening_pantry_periods: u64,
    opening_input_periods: u64,
    working_capital_periods: u64,
    retailer_buffer_periods: u64,
    resource_reserve_output_periods: u64,
    handling_hours_per_unit: u64,
    missing_peer_weight_per_establishment: u64,
    household_enterprise_function: String,
    financial: RawFinancial,
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
#[derive(Clone, Copy, Deserialize)]
#[serde(deny_unknown_fields)]
struct RawProfile {
    participation_bps: u16,
    opening_employment_bps: u16,
    persons_per_household: u64,
    wage_micros_per_hour: i128,
    price_scale_bps: u16,
    function_weights_bps: [u16; 10],
}
#[derive(Clone, Copy, Deserialize)]
#[serde(deny_unknown_fields)]
struct RawDependency {
    participation_bps: u16,
    opening_employment_bps: u16,
    persons_per_household: u64,
    wage_micros_per_hour: i128,
    price_scale_bps: u16,
    function_weights_bps: [u16; 10],
    missing_population_game_persons: u64,
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
}

pub(super) fn parse(source: &str) -> Result<NationalGamePolicy, Error> {
    if source.len() > 65_536 {
        return Err(Error::Bounds);
    }
    let raw: RawPolicy = toml::from_str(source).map_err(|_| Error::Syntax)?;
    validate_globals(&raw)?;
    let commodities = commodities(raw.commodity)?;
    let recipes = recipes(raw.process, &commodities)?;
    let household_needs = needs(raw.household_needs, &commodities)?;
    let counterparts = counterparts(raw.counterpart)?;
    let dependency = dependency(raw.dependency)?;
    let financial = financial(raw.financial)?;
    let markets = markets(&raw.markets)?;
    let equipment = equipment(raw.equipment, &commodities)?;
    Ok(NationalGamePolicy {
        period_days: raw.period_days,
        work_hours_per_person: raw.work_hours_per_person,
        default_wage: Currency::from_micro_units(raw.default_wage_micros_per_hour),
        opening_pantry_periods: raw.opening_pantry_periods,
        opening_input_periods: raw.opening_input_periods,
        working_capital_periods: raw.working_capital_periods,
        retailer_buffer_periods: raw.retailer_buffer_periods,
        resource_reserve_output_periods: raw.resource_reserve_output_periods,
        handling_hours_per_unit: raw.handling_hours_per_unit,
        missing_peer_weight_per_establishment: raw.missing_peer_weight_per_establishment,
        household_enterprise_function: EconomicFunction::HouseholdServices,
        financial,
        markets,
        equipment,
        commodities,
        recipes,
        household_needs,
        counterparts,
        dependency,
    })
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

fn validate_globals(raw: &RawPolicy) -> Result<(), Error> {
    if raw.evidence_class != "Designed" {
        return Err(Error::Evidence);
    }
    if raw.schema_version != 1
        || raw.period_days != 28
        || !(1..=672).contains(&raw.work_hours_per_person)
        || raw.default_wage_micros_per_hour <= 0
        || raw
            .default_wage_micros_per_hour
            .checked_mul(i128::from(raw.work_hours_per_person))
            .is_none()
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
) -> Result<BTreeMap<String, GameCommodity>, Error> {
    let expected: BTreeSet<_> = [
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
    let mut good_bytes = b"NationalGoodV1\0".to_vec();
    good_bytes.extend_from_slice(key.as_bytes());
    let mut unit_bytes = b"NationalUnitV1\0".to_vec();
    unit_bytes.extend_from_slice(raw.unit_label.as_bytes());
    Ok(GameCommodity {
        good_id: GoodId::from_bytes(sha256_of(&good_bytes)),
        unit_id: UnitId::from_bytes(sha256_of(&unit_bytes)),
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
) -> Result<BTreeMap<EconomicFunction, GameRecipe>, Error> {
    if raw.len() != 9 {
        return Err(Error::Shape);
    }
    raw.into_iter()
        .map(|(key, row)| {
            let function = EconomicFunction::from_source_key(&key)
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
fn profile(key: &str, raw: RawProfile) -> Result<GameProfile, Error> {
    if !(1..=10_000).contains(&raw.participation_bps)
        || raw.opening_employment_bps > 10_000
        || raw.persons_per_household == 0
        || raw.wage_micros_per_hour <= 0
        || raw.price_scale_bps == 0
        || raw.wage_micros_per_hour.checked_mul(672).is_none()
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
        wage_per_hour: Currency::from_micro_units(raw.wage_micros_per_hour),
        price_scale_bps: raw.price_scale_bps,
        function_weights_bps: raw.function_weights_bps,
    })
}
fn counterparts(
    raw: BTreeMap<String, RawProfile>,
) -> Result<BTreeMap<ForeignCounterpart, GameProfile>, Error> {
    if raw.len() != 12 {
        return Err(Error::Shape);
    }
    raw.into_iter()
        .map(|(key, row)| {
            let counterpart =
                ForeignCounterpart::from_key(&key).ok_or_else(|| Error::Profile(key.clone()))?;
            Ok((counterpart, profile(&key, row)?))
        })
        .collect()
}
fn dependency(raw: RawDependency) -> Result<GameDependencyProfile, Error> {
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
                price_scale_bps: raw.price_scale_bps,
                function_weights_bps: raw.function_weights_bps,
            },
        )?,
    })
}

fn markets(raw: &RawMarkets) -> Result<GameMarketPolicy, Error> {
    if raw.foreign_procurement_bps > 10_000
        || raw.journey_timing != "slowest_profile"
        || raw.service_reach != "same_state_or_own_counterpart"
    {
        return Err(Error::Profile("market scope".to_owned()));
    }
    Ok(GameMarketPolicy {
        foreign_procurement_bps: raw.foreign_procurement_bps,
        journey_timing: GameJourneyTiming::SlowestProfile,
        service_reach: GameServiceReach::SameStateOrOwnCounterpart,
    })
}
