//! The keys of the rebuilt opening (schema 8): wants, handling blocks, the fund, the programs,
//! luxury scales, place services and the map's basis. Each key is refused under schema 7 and
//! earlier, and each is required under schema 8 unless the plan names it optional.
use super::{
    GameCommodity, GameFundPolicy, GameHandling, GameLuxuryScale, GameMapBasis, GameNeed,
    GamePlaceGrant, GameProgram, GameProgramRecipients, GameProgramTerms, GameWant,
    NationalGamePolicyError, MAX_GAME_PROGRAM_SHARE_BPS,
};
use crate::national_household_allocation::HouseholdBudgetKey;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::TradeSet;
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart, UsDependency};
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::{CommodityKind, HouseholdNeedBasis, WantTier};
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet};

type Error = NationalGamePolicyError;

/// Every budget key, for reading a label back.
const BUDGET_KEYS: [HouseholdBudgetKey; 8] = [
    HouseholdBudgetKey::EarningNonowner,
    HouseholdBudgetKey::EarningOwner,
    HouseholdBudgetKey::NoEarnerNonowner,
    HouseholdBudgetKey::NoEarnerOwner,
    HouseholdBudgetKey::CollectiveResidence,
    HouseholdBudgetKey::PooledExternal,
    HouseholdBudgetKey::EarningLowerPaidHalf,
    HouseholdBudgetKey::EarningBetterPaidForty,
];

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct RawWant {
    good: String,
    tier: String,
    basis: String,
    units_per_basis: u64,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct RawFund {
    evidence_class: String,
    wage_tax_share_bps: u16,
    operating_income_tax_share_bps: u16,
    reserve_periods: u64,
    share_by_part: Option<BTreeMap<String, u16>>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct RawPlaceGrant {
    part: String,
    amount_per_period_micros: i128,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct RawProgram {
    key: String,
    kind: String,
    rank: u32,
    wage_share_bps: Option<u16>,
    half_periods: Option<u16>,
    amount_per_person_micros: Option<i128>,
    share_bps: Option<u32>,
    recipients: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct RawLuxuryScale {
    by_account: BTreeMap<String, u32>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct RawMapBasis {
    #[serde(rename = "food_labor_hours_per_batch")]
    labor_hours_per_batch: u64,
    #[serde(rename = "food_output_units_per_batch")]
    output_units_per_batch: u64,
    #[serde(rename = "food_units_per_person")]
    units_per_person: u64,
    #[serde(rename = "food_grams_per_unit")]
    grams_per_unit: u64,
}

/// The handling figures as written, by commodity key: hours and units, each optional.
pub(super) type RawHandling = BTreeMap<String, (Option<u64>, Option<u64>)>;

/// Every raw piece of the rebuilt opening's keys.
pub(super) struct RawKeys {
    pub(super) handling: RawHandling,
    pub(super) wants: Option<Vec<RawWant>>,
    pub(super) fund: Option<RawFund>,
    pub(super) programs: Option<Vec<RawProgram>>,
    pub(super) luxury_scale: Option<RawLuxuryScale>,
    pub(super) basis: Option<RawMapBasis>,
    pub(super) place_services: Option<Vec<String>>,
    pub(super) country_services: Option<Vec<String>>,
    pub(super) place_grants: Option<Vec<RawPlaceGrant>>,
}

/// The admitted keys.
pub(super) struct BuilderKeys {
    pub(super) wants: Vec<GameWant>,
    pub(super) fund: Option<GameFundPolicy>,
    pub(super) programs: Vec<GameProgram>,
    pub(super) luxury_scales: Vec<GameLuxuryScale>,
    pub(super) place_services: Vec<String>,
    pub(super) country_services: Vec<String>,
    pub(super) place_grants: Vec<GamePlaceGrant>,
    pub(super) map_basis: Option<GameMapBasis>,
}

/// Admit every key of the rebuilt opening, and set the handling of the shop goods.
pub(super) fn admit(
    raw: RawKeys,
    trades: TradeSet,
    goods: &mut BTreeMap<String, GameCommodity>,
    needs: &[GameNeed],
    paying_order: Option<&[String]>,
) -> Result<BuilderKeys, Error> {
    let schema_8 = trades == TradeSet::Twelve;
    let wants = wants(raw.wants, schema_8, goods, paying_order)?;
    handling(goods, &raw.handling, schema_8, needs, &wants)?;
    let place_services = service_list(raw.place_services, schema_8, goods, &[], "place_services")?;
    let country_services = service_list(
        raw.country_services,
        schema_8,
        goods,
        &place_services,
        "country_services",
    )?;
    Ok(BuilderKeys {
        place_services,
        country_services,
        place_grants: place_grants(raw.place_grants, schema_8)?,
        fund: fund(raw.fund, schema_8)?,
        programs: programs(raw.programs, schema_8)?,
        luxury_scales: luxury_scales(raw.luxury_scale, schema_8)?,
        map_basis: map_basis(raw.basis, schema_8)?,
        wants,
    })
}

fn storable(goods: &BTreeMap<String, GameCommodity>, key: &str) -> bool {
    goods
        .get(key)
        .is_some_and(|g| matches!(g.kind, CommodityKind::Storable { .. }))
}

fn wants(
    raw: Option<Vec<RawWant>>,
    schema_8: bool,
    goods: &BTreeMap<String, GameCommodity>,
    paying_order: Option<&[String]>,
) -> Result<Vec<GameWant>, Error> {
    let rows = match (schema_8, raw) {
        (false, None) => return Ok(Vec::new()),
        (true, rows) => rows.unwrap_or_default(),
        (false, Some(_)) => return Err(Error::Shape),
    };
    let order = paying_order.unwrap_or_default();
    let mut seen = BTreeSet::new();
    let mut result = Vec::new();
    for row in rows {
        let fail = || Error::HouseholdNeed(row.good.clone());
        let tier = match row.tier.as_str() {
            "comfort" => WantTier::Comfort,
            "luxury" => WantTier::Luxury,
            _ => return Err(fail()),
        };
        let basis = match row.basis.as_str() {
            "persons" => HouseholdNeedBasis::Persons,
            "households" => HouseholdNeedBasis::Households,
            _ => return Err(fail()),
        };
        if row.units_per_basis == 0
            || goods.get(&row.good).is_none_or(|g| g.price.is_none())
            || !order.contains(&row.good)
            || !seen.insert((tier, row.good.clone()))
        {
            return Err(fail());
        }
        result.push(GameWant {
            key: row.good,
            tier,
            basis,
            units_per_basis: row.units_per_basis,
        });
    }
    result.sort_by(|a, b| (a.tier, &a.key).cmp(&(b.tier, &b.key)));
    Ok(result)
}

/// A storable good that a need or a want names has a handling row, and no other commodity has one.
fn handling(
    goods: &mut BTreeMap<String, GameCommodity>,
    raw: &RawHandling,
    schema_8: bool,
    needs: &[GameNeed],
    wants: &[GameWant],
) -> Result<(), Error> {
    let named: BTreeSet<&str> = needs
        .iter()
        .map(|n| n.key.as_str())
        .chain(wants.iter().map(|w| w.key.as_str()))
        .collect();
    let rows: Vec<(String, Option<GameHandling>)> = raw
        .iter()
        .map(|(key, written)| {
            let wanted = schema_8 && storable(goods, key) && named.contains(key.as_str());
            let row = match *written {
                (None, None) if !wanted => None,
                (Some(hours), Some(units)) if wanted => {
                    if hours == 0 || units == 0 {
                        return Err(Error::Profile("handling".to_owned()));
                    }
                    Some(GameHandling { hours, units })
                }
                _ => return Err(Error::Shape),
            };
            Ok((key.clone(), row))
        })
        .collect::<Result<_, Error>>()?;
    for (key, row) in rows {
        if let Some(good) = goods.get_mut(&key) {
            good.handling = row;
        }
    }
    Ok(())
}

/// K1 and K2 (and the place services): a sorted list of period services of the scenario, each once, none of
/// them in `excluded`. `name` is the key's own name, for the refusal `Profile(name)`.
pub(super) fn service_list(
    raw: Option<Vec<String>>,
    schema_8: bool,
    goods: &BTreeMap<String, GameCommodity>,
    excluded: &[String],
    name: &str,
) -> Result<Vec<String>, Error> {
    let mut rows = match (schema_8, raw) {
        (_, None) => return Ok(Vec::new()),
        (true, Some(rows)) => rows,
        (false, Some(_)) => return Err(Error::Shape),
    };
    let fail = || Error::Profile(name.to_owned());
    let mut seen = BTreeSet::new();
    for key in &rows {
        let service = goods
            .get(key)
            .is_some_and(|g| matches!(g.kind, CommodityKind::PeriodService { .. }));
        if !service || excluded.contains(key) || !seen.insert(key.clone()) {
            return Err(fail());
        }
    }
    rows.sort();
    Ok(rows)
}

fn fund(raw: Option<RawFund>, schema_8: bool) -> Result<Option<GameFundPolicy>, Error> {
    let raw = match (schema_8, raw) {
        (false, None) => return Ok(None),
        (true, Some(raw)) => raw,
        _ => return Err(Error::Shape),
    };
    if raw.evidence_class != "Designed" {
        return Err(Error::Evidence);
    }
    if raw.wage_tax_share_bps > 10_000
        || raw.operating_income_tax_share_bps > 10_000
        || !(1..=16).contains(&raw.reserve_periods)
    {
        return Err(Error::Profile("fund".to_owned()));
    }
    let share_by_part = raw.share_by_part.unwrap_or_default();
    for (part, bps) in &share_by_part {
        if !domestic_part_label_ok(part) {
            return Err(Error::Location);
        }
        if *bps > 10_000 {
            return Err(Error::Profile("fund".to_owned()));
        }
    }
    Ok(Some(GameFundPolicy {
        wage_tax_share_bps: raw.wage_tax_share_bps,
        operating_income_tax_share_bps: raw.operating_income_tax_share_bps,
        reserve_periods: raw.reserve_periods,
        share_by_part,
    }))
}

/// K5: the fund's grants to a part's funded public providers, sorted by part.
fn place_grants(
    raw: Option<Vec<RawPlaceGrant>>,
    schema_8: bool,
) -> Result<Vec<GamePlaceGrant>, Error> {
    let rows = match (schema_8, raw) {
        (_, None) => return Ok(Vec::new()),
        (true, Some(rows)) => rows,
        (false, Some(_)) => return Err(Error::Shape),
    };
    let mut seen = BTreeSet::new();
    let mut result = Vec::new();
    for row in rows {
        if !domestic_part_label_ok(&row.part) {
            return Err(Error::Location);
        }
        if row.amount_per_period_micros <= 0 || !seen.insert(row.part.clone()) {
            return Err(Error::Profile("place_grants".to_owned()));
        }
        result.push(GamePlaceGrant {
            part: row.part,
            amount_per_period: Currency::from_micro_units(row.amount_per_period_micros),
        });
    }
    result.sort_by(|a, b| a.part.cmp(&b.part));
    Ok(result)
}

/// A domestic part's label: `<hub geoid>` or `<hub geoid>/<none|below|at|above>`, the hub a county that
/// `EconomicLocation::domestic_county` admits.
fn domestic_part_label_ok(place: &str) -> bool {
    match place.split_once('/') {
        Some((hub, position)) => {
            matches!(position, "none" | "below" | "at" | "above") && domestic_county(hub).is_ok()
        }
        None => domestic_county(place).is_ok(),
    }
}

fn domestic_county(text: &str) -> Result<CountyGeoid, Error> {
    let county = CountyGeoid::try_from(text).map_err(|_| Error::Location)?;
    EconomicLocation::domestic_county(county).map_err(|_| Error::Location)?;
    Ok(county)
}

fn programs(raw: Option<Vec<RawProgram>>, schema_8: bool) -> Result<Vec<GameProgram>, Error> {
    let rows = match (schema_8, raw) {
        (false, None) => return Ok(Vec::new()),
        (true, Some(rows)) if (2..=3).contains(&rows.len()) => rows,
        _ => return Err(Error::Shape),
    };
    let mut seen = BTreeSet::new();
    let mut result = Vec::new();
    for row in rows {
        if !seen.insert(row.key.clone()) {
            return Err(Error::Profile("program".to_owned()));
        }
        result.push(program(row)?);
    }
    if !seen.contains("laid_off") || !seen.contains("no_earner") {
        return Err(Error::Shape);
    }
    result.sort_by(|a, b| a.key.cmp(&b.key));
    Ok(result)
}

/// A program's own recipients and the kinds its key may take.
fn program_kinds(
    key: &str,
) -> Option<(&'static [&'static str], &'static str, GameProgramRecipients)> {
    match key {
        "laid_off" => Some((
            &["after_layoff"],
            "earning_or_residence_at_opening",
            GameProgramRecipients::EarningOrResidenceAtOpening,
        )),
        "no_earner" => Some((
            &["per_person", "own_needs"],
            "no_earner_at_opening",
            GameProgramRecipients::NoEarnerAtOpening,
        )),
        "residence" => Some((
            &["own_needs"],
            "collective_residence_at_opening",
            GameProgramRecipients::CollectiveResidenceAtOpening,
        )),
        _ => None,
    }
}

fn program(row: RawProgram) -> Result<GameProgram, Error> {
    let fail = || Error::Profile("program".to_owned());
    let (kinds, recipients_text, recipients) = program_kinds(&row.key).ok_or_else(fail)?;
    if !kinds.contains(&row.kind.as_str()) || row.recipients != recipients_text || row.rank > 255 {
        return Err(fail());
    }
    let terms = match (
        row.kind.as_str(),
        row.wage_share_bps,
        row.half_periods,
        row.amount_per_person_micros,
        row.share_bps,
    ) {
        ("after_layoff", Some(wage_share_bps), Some(half_periods), None, None) => {
            if !(1..=10_000).contains(&wage_share_bps) || !(1..=26).contains(&half_periods) {
                return Err(fail());
            }
            GameProgramTerms::AfterLayoff {
                wage_share_bps,
                half_periods,
            }
        }
        ("per_person", None, None, Some(amount), None) => {
            if amount <= 0 {
                return Err(fail());
            }
            GameProgramTerms::PerPerson {
                amount_per_person: Currency::from_micro_units(amount),
            }
        }
        ("own_needs", None, None, None, Some(share_bps)) => {
            if !(1..=MAX_GAME_PROGRAM_SHARE_BPS).contains(&share_bps) {
                return Err(fail());
            }
            GameProgramTerms::OwnNeeds { share_bps }
        }
        _ => return Err(Error::Shape),
    };
    Ok(GameProgram {
        key: row.key,
        rank: row.rank,
        terms,
        recipients,
    })
}

/// A domestic part's label, a counterpart's key or a dependency's code.
fn place_label_ok(place: &str) -> bool {
    match place.split_once('/') {
        Some((hub, position)) => {
            matches!(position, "none" | "below" | "at" | "above") && domestic_county(hub).is_ok()
        }
        None => {
            domestic_county(place).is_ok()
                || ForeignCounterpart::from_key(place).is_some()
                || UsDependency::from_m49(place).is_some()
        }
    }
}

fn luxury_scales(
    raw: Option<RawLuxuryScale>,
    schema_8: bool,
) -> Result<Vec<GameLuxuryScale>, Error> {
    let raw = match (schema_8, raw) {
        (_, None) => return Ok(Vec::new()),
        (true, Some(raw)) => raw,
        (false, Some(_)) => return Err(Error::Shape),
    };
    let mut seen = BTreeSet::new();
    let mut result = Vec::new();
    for (account, bps) in raw.by_account {
        let (place, label) = account.rsplit_once(':').ok_or(Error::Location)?;
        let key = BUDGET_KEYS
            .into_iter()
            .find(|key| key.label() == label)
            .ok_or(Error::Location)?;
        if !place_label_ok(place) {
            return Err(Error::Location);
        }
        if bps <= 10_000 || bps > 1_000_000 || !seen.insert((place.to_owned(), key as u8)) {
            return Err(Error::Profile("luxury_scale".to_owned()));
        }
        result.push(GameLuxuryScale {
            place: place.to_owned(),
            key,
            bps,
        });
    }
    result.sort_by(|a, b| (&a.place, a.key as u8).cmp(&(&b.place, b.key as u8)));
    Ok(result)
}

fn map_basis(raw: Option<RawMapBasis>, schema_8: bool) -> Result<Option<GameMapBasis>, Error> {
    let raw = match (schema_8, raw) {
        (false, None) => return Ok(None),
        (true, Some(raw)) => raw,
        _ => return Err(Error::Shape),
    };
    if [
        raw.labor_hours_per_batch,
        raw.output_units_per_batch,
        raw.units_per_person,
        raw.grams_per_unit,
    ]
    .contains(&0)
    {
        return Err(Error::Profile("grain basis".to_owned()));
    }
    Ok(Some(GameMapBasis {
        food_labor_hours_per_batch: raw.labor_hours_per_batch,
        food_output_units_per_batch: raw.output_units_per_batch,
        food_units_per_person: raw.units_per_person,
        food_grams_per_unit: raw.grams_per_unit,
    }))
}
