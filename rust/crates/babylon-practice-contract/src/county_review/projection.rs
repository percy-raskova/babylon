//! What the player sees of the county: the ledger, the roll, the list and the positions.
//!
//! The fog rule (ADR182 R2): the list's order, the units paid and unpaid, the roll and the counts
//! of who works in each band are public. A position's dollar figures, its households, the
//! households reached and the reasons its households stayed home are earned by contact, and are
//! filled in only for a position in `contacted`.
use serde::{Deserialize, Serialize};

use super::codec;
use super::codec::CountyReviewState;
use super::place;
use super::roster;
use super::session::{ContactOutcome, SessionRow};
use super::types::{
    Band, BandCount, CountyReviewConfig, CountyReviewCrew, CountyReviewError, GroupKind, PayMode,
    PositionKey, RosterRow,
};

/// The kind of a line of the county's ledger.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LedgerLineKind {
    /// A grant to a public workplace.
    PublicWorkplace,
    /// The City PD's payroll, named inside its workplace's grant.
    CityPdPayroll,
    /// The City PD's visits.
    CityPdVisits,
    /// Relief for a household group.
    HouseholdSupport,
    /// Relief for a collective residence.
    CollectiveResidence,
}

/// One line of the county's ledger.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LedgerLine {
    /// What the line is for.
    pub kind: LedgerLineKind,
    /// The name shown to the player.
    pub label: String,
    /// The amount, in millionths of a dollar.
    #[serde(with = "super::decimal")]
    pub amount_micros: i128,
    /// Whether the line is paid before relief.
    pub first_class: bool,
}

/// The engine's ledger as the county's account stands.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LedgerInput {
    /// The county's cash.
    pub cash_micros: i128,
    /// The spending limit.
    pub spending_limit_micros: i128,
    /// The engine's lines in pay order, before the payroll is named.
    pub lines: Vec<LedgerLine>,
    /// The City PD's workplace label, its positions and its payroll.
    pub city_pd_payroll: Option<(String, u64, i128)>,
}

/// A position's earned figures: shown only where the player has made a contact.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PositionEarned {
    /// Households in the position.
    pub households: u64,
    /// Of those, the households reached.
    pub reached: u64,
    /// The wage of one household's people at work, rounded down, at the last close's pay.
    #[serde(with = "super::decimal")]
    pub wage_micros_per_household: i128,
    /// The wage tax on one household's wage, rounded down. It is never used to rank.
    #[serde(with = "super::decimal")]
    pub wage_tax_micros_per_household: i128,
    /// What one household stands to gain or lose: its units, or one unit if it holds none.
    #[serde(with = "super::decimal")]
    pub stake_micros: i128,
    /// The group's ownership income at the last close. A total for the group, not a household's.
    #[serde(with = "super::decimal")]
    pub group_ownership_income_micros: i128,
    /// The group's county support at the last close. A total for the group.
    #[serde(with = "super::decimal")]
    pub group_support_income_micros: i128,
    /// The group's mutual aid at the last close. A total for the group.
    #[serde(with = "super::decimal")]
    pub group_aid_income_micros: i128,
    /// Households that asked for a unit at the last session.
    pub asked: u64,
    /// Of those, households the county could not reach with its money.
    pub asked_no_place: u64,
    /// Reached households that wanted to ask and had no hours.
    pub asked_no_time: u64,
    /// Reached households that would have come from the roll and had no hours.
    pub roll_no_time: u64,
    /// Reached households that hold a unit and lose none.
    pub nothing_at_stake: u64,
    /// Reached households whose stake was below the floor.
    pub not_worth_time: u64,
    /// Households brought, reached from the next session.
    pub brought: u64,
}

/// One position, as the player sees it. The list's figures are those of the last session.
#[allow(
    clippy::struct_excessive_bools,
    reason = "the four sources of income and the contact are independent facts the interface fixes"
)]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PositionView {
    /// The position.
    pub key: PositionKey,
    /// Its budget group's name.
    pub group_label: String,
    /// Its workplace's name, if its people have one.
    pub workplace_label: Option<String>,
    /// How its people are paid, if they have a workplace.
    pub pay_mode: Option<PayMode>,
    /// Its rank at the last session, if the list held it.
    pub rank: Option<u32>,
    /// Whether any of its people are at work for a wage.
    pub has_wages: bool,
    /// Whether its budget group draws ownership income.
    pub has_ownership_income: bool,
    /// Whether it holds a unit on the roll.
    pub has_support: bool,
    /// Whether its budget group receives mutual aid.
    pub has_mutual_aid: bool,
    /// Units it held on the list at the last session.
    pub units_listed: u64,
    /// Of those, the units the county paid.
    pub units_paid: u64,
    /// Of those, the units the county did not pay.
    pub units_unpaid: u64,
    /// Households that asked and were paid at the last session.
    pub asked_paid: u64,
    /// Households that came because a unit they hold was not paid.
    pub came_from_roll: u64,
    /// Whether the player has made a contact here.
    pub contacted: bool,
    /// Its earned figures, for a contacted position only.
    pub earned: Option<PositionEarned>,
}

/// The county as the player sees it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CountyReviewProjection {
    /// The county's FIPS code.
    pub county: [u8; 5],
    /// The administration's name.
    pub administration_label: String,
    /// The Claimants' Assembly's name.
    pub claimants_body_label: String,
    /// The aid partners' name.
    pub aid_body_label: String,
    /// The period the roster stands for.
    pub roster_period: u64,
    /// The first period with a session.
    pub first_session_period: u64,
    /// The period of the last session held.
    pub session_period: Option<u64>,
    /// One unit of relief.
    #[serde(with = "super::decimal")]
    pub unit_price_micros: i128,
    /// The county's cash.
    #[serde(with = "super::decimal")]
    pub cash_micros: i128,
    /// The spending limit.
    #[serde(with = "super::decimal")]
    pub spending_limit_micros: i128,
    /// The ledger's lines in pay order, with the City PD's payroll named.
    pub ledger: Vec<LedgerLine>,
    /// The lines paid before relief.
    #[serde(with = "super::decimal")]
    pub first_class_micros: i128,
    /// The money for relief at the last session.
    #[serde(with = "super::decimal::option")]
    pub relief_micros: Option<i128>,
    /// Household units the county could pay at the last session.
    pub household_units_payable: Option<u64>,
    /// Units an exact tie left unpaid at the last session.
    pub kept_back_units: Option<u64>,
    /// Units on the roll by group: the group's name and its units.
    pub roll: Vec<(String, u64)>,
    /// Who works in each band, top first. Public county totals.
    pub bands: Vec<BandCount>,
    /// Households that came from the roll at the last session.
    pub claimants_roll_households: Option<u64>,
    /// Households that asked and were paid at the last session.
    pub aid_roll_households: Option<u64>,
    /// The last session's contact and what came of it.
    pub contact: Option<(PositionKey, ContactOutcome)>,
    /// The roster's positions, in the order of the list and then by key.
    pub positions: Vec<PositionView>,
}

fn checked_total(mut amounts: impl Iterator<Item = i128>) -> Result<i128, CountyReviewError> {
    amounts.try_fold(0_i128, |total, amount| {
        total
            .checked_add(amount)
            .ok_or(CountyReviewError::Arithmetic)
    })
}

/// The ledger with the City PD's payroll named: the workplace line is reduced by the payroll and a
/// payroll line of the same amount follows it.
fn name_payroll(input: &LedgerInput) -> Result<Vec<LedgerLine>, CountyReviewError> {
    if input.lines.iter().any(|line| line.amount_micros < 0) {
        return Err(CountyReviewError::Arithmetic);
    }
    let Some((label, _positions, payroll)) = &input.city_pd_payroll else {
        return Ok(input.lines.clone());
    };
    let mut lines = Vec::with_capacity(input.lines.len().saturating_add(1));
    let mut named = false;
    for line in &input.lines {
        let is_workplace = line.kind == LedgerLineKind::PublicWorkplace && line.label == *label;
        if !is_workplace || named {
            lines.push(line.clone());
            continue;
        }
        let rest = line
            .amount_micros
            .checked_sub(*payroll)
            .filter(|rest| *rest >= 0 && *payroll >= 0)
            .ok_or(CountyReviewError::LedgerPayrollNotInWorkplace)?;
        lines.push(LedgerLine {
            amount_micros: rest,
            ..line.clone()
        });
        lines.push(LedgerLine {
            kind: LedgerLineKind::CityPdPayroll,
            label: "City PD payroll".to_owned(),
            amount_micros: *payroll,
            first_class: line.first_class,
        });
        named = true;
    }
    if named {
        Ok(lines)
    } else {
        Err(CountyReviewError::LedgerPayrollNotInWorkplace)
    }
}

fn index(value: u32) -> Result<usize, CountyReviewError> {
    usize::try_from(value).map_err(|_| CountyReviewError::Arithmetic)
}

/// The wage of a household's people at work, from the crew's wages and people at work, rounded
/// down.
fn wage_per_household(
    at_work: u16,
    wages_micros: i128,
    crew_at_work: u64,
) -> Result<i128, CountyReviewError> {
    if wages_micros < 0 {
        return Err(CountyReviewError::Arithmetic);
    }
    if at_work == 0 || crew_at_work == 0 {
        return Ok(0);
    }
    Ok(wages_micros
        .checked_mul(i128::from(at_work))
        .ok_or(CountyReviewError::Arithmetic)?
        / i128::from(crew_at_work))
}

fn earned_for(
    config: &CountyReviewConfig,
    state: &CountyReviewState,
    row: &RosterRow,
    listed: Option<&SessionRow>,
) -> Result<Option<PositionEarned>, CountyReviewError> {
    let Some(facts) = &state.last_facts else {
        return Ok(None);
    };
    let key = row.key;
    let group = facts
        .groups
        .get(index(key.group)?)
        .ok_or(CountyReviewError::UnknownGroup)?;
    let (wage, wage_tax) = match key.crew {
        None => (0, 0),
        Some(crew) => {
            let crew_facts = facts
                .crews
                .get(index(crew)?)
                .ok_or(CountyReviewError::UnknownCrew)?;
            let people = crew_facts.opening_at_work;
            let wage = wage_per_household(key.at_work, crew_facts.accrued_wages_micros, people)?;
            let tax = place::place(
                key.at_work,
                crew_facts.accrued_wages_micros,
                people,
                group.wage_tax_collected_micros,
                group.taxed_wages_micros,
            )?
            .floor_micros()?;
            (wage, tax)
        }
    };
    let units = i128::from(key.units.max(1));
    let stake_micros = units
        .checked_mul(config.unit_price_micros)
        .ok_or(CountyReviewError::Arithmetic)?;
    let count = |figure: fn(&SessionRow) -> u64| listed.map_or(0, figure);
    Ok(Some(PositionEarned {
        households: row.households,
        reached: row.reached,
        wage_micros_per_household: wage,
        wage_tax_micros_per_household: wage_tax,
        stake_micros,
        group_ownership_income_micros: group.ownership_income_micros,
        group_support_income_micros: group.support_income_micros,
        group_aid_income_micros: group.aid_income_micros,
        asked: count(|r| r.asked),
        asked_no_place: count(|r| r.asked_no_place),
        asked_no_time: count(|r| r.asked_no_time),
        roll_no_time: count(|r| r.roll_no_time),
        nothing_at_stake: count(|r| r.nothing_at_stake),
        not_worth_time: count(|r| r.not_worth_time),
        brought: count(|r| r.brought),
    }))
}

/// A band's name, as the player reads it.
#[must_use]
pub const fn band_label(band: Band) -> &'static str {
    match band {
        Band::Top1 => "Top 1%",
        Band::Next9 => "Next 9%",
        Band::Next40 => "Next 40%",
        Band::Bottom50 => "Bottom 50%",
    }
}

/// How a crew is paid, in the player's words.
#[must_use]
pub const fn pay_mode_text(mode: PayMode) -> &'static str {
    match mode {
        PayMode::Wage => "wage",
        PayMode::WorkingOwner => "working owner",
        PayMode::UnpaidFamily => "unpaid family work",
    }
}

/// Where a position's people work, in the player's words: the workplace and how it pays, or that
/// nobody in the position is in the labor force.
#[must_use]
pub fn workplace_text(workplace_label: Option<&str>, pay_mode: Option<PayMode>) -> String {
    match (workplace_label, pay_mode) {
        (Some(label), Some(mode)) => format!("{label} ({})", pay_mode_text(mode)),
        (Some(label), None) => label.to_owned(),
        (None, _) => "no wage · no one in the labor force".to_owned(),
    }
}

/// The public structure that names a position: its band, its budget group and its workplace. The
/// interface and the Archive both name a position with these words.
#[must_use]
pub fn position_name(
    band: Band,
    group_label: &str,
    workplace_label: Option<&str>,
    pay_mode: Option<PayMode>,
) -> String {
    format!(
        "{} · {group_label} · {}",
        band_label(band),
        workplace_text(workplace_label, pay_mode)
    )
}

/// The name of a position of the county's configuration.
///
/// # Errors
///
/// `UnknownGroup` or `UnknownCrew` for a key the configuration does not hold.
pub fn position_name_in(
    config: &CountyReviewConfig,
    key: PositionKey,
) -> Result<String, CountyReviewError> {
    let group = config
        .groups
        .get(index(key.group)?)
        .ok_or(CountyReviewError::UnknownGroup)?;
    let crew = match key.crew {
        None => None,
        Some(crew) => Some(
            config
                .crews
                .get(index(crew)?)
                .ok_or(CountyReviewError::UnknownCrew)?,
        ),
    };
    Ok(position_name(
        key.band,
        &group.label,
        crew.map(|c| c.workplace_label.as_str()),
        crew.map(|c| c.pay_mode),
    ))
}

fn position_view(
    config: &CountyReviewConfig,
    state: &CountyReviewState,
    row: &RosterRow,
    contacted: &[PositionKey],
) -> Result<PositionView, CountyReviewError> {
    let key = row.key;
    let group = config
        .groups
        .get(index(key.group)?)
        .ok_or(CountyReviewError::UnknownGroup)?;
    let crew: Option<&CountyReviewCrew> = match key.crew {
        None => None,
        Some(crew) => Some(
            config
                .crews
                .get(index(crew)?)
                .ok_or(CountyReviewError::UnknownCrew)?,
        ),
    };
    let listed = state.last_session.as_ref().and_then(|session| {
        session
            .rows
            .binary_search_by_key(&key, |r| r.key)
            .ok()
            .and_then(|at| session.rows.get(at))
    });
    let is_contacted = contacted.contains(&key);
    let earned = if is_contacted {
        earned_for(config, state, row, listed)?
    } else {
        None
    };
    Ok(PositionView {
        key,
        group_label: group.label.clone(),
        workplace_label: crew.map(|c| c.workplace_label.clone()),
        pay_mode: crew.map(|c| c.pay_mode),
        rank: listed.map(|r| r.rank),
        has_wages: crew.is_some_and(|c| c.pay_mode == PayMode::Wage) && key.at_work >= 1,
        has_ownership_income: group.has_ownership_income,
        has_support: key.units > 0,
        has_mutual_aid: group.receives_mutual_aid,
        units_listed: listed.map_or(0, |r| r.units_listed),
        units_paid: listed.map_or(0, |r| r.units_paid),
        units_unpaid: listed.map_or(0, |r| r.units_unpaid),
        asked_paid: listed.map_or(0, |r| r.asked_paid),
        came_from_roll: listed.map_or(0, |r| r.came_from_roll),
        contacted: is_contacted,
        earned,
    })
}

fn roll_by_group(
    config: &CountyReviewConfig,
    state: &CountyReviewState,
) -> Result<Vec<(String, u64)>, CountyReviewError> {
    config
        .groups
        .iter()
        .enumerate()
        .map(|(at, group)| {
            let units = match group.kind {
                GroupKind::Ordinary => {
                    let at = u32::try_from(at).map_err(|_| CountyReviewError::Arithmetic)?;
                    state.roster.group_units(at)
                }
                GroupKind::CollectiveResidence => group.roll_units,
            };
            Ok((group.label.clone(), units))
        })
        .collect()
}

/// Makes the player's view of the county.
///
/// `ledger` is the engine's lines as they stand; the City PD's payroll is named inside its
/// workplace's grant. A position is `contacted` when `contacted` holds its key, and only then are
/// its earned figures filled in. The order of `positions` is the last session's list, by rank, and
/// then by key; positions the last session did not list come last.
///
/// # Errors
///
/// The refusals of `validate_county_review_state`, `LedgerPayrollNotInWorkplace` when the payroll
/// names no workplace line that can hold it, and `Arithmetic` for a negative ledger amount or a
/// sum that leaves its range.
pub fn project(
    config: &CountyReviewConfig,
    state: &CountyReviewState,
    ledger: &LedgerInput,
    contacted: &[PositionKey],
) -> Result<CountyReviewProjection, CountyReviewError> {
    codec::validate_county_review_state(config, state)?;
    roster::validate_roster(config, &state.roster)?;
    let lines = name_payroll(ledger)?;
    let first_class_micros = checked_total(
        lines
            .iter()
            .filter(|line| line.first_class)
            .map(|line| line.amount_micros),
    )?;
    let mut positions = state
        .roster
        .rows
        .iter()
        .map(|row| position_view(config, state, row, contacted))
        .collect::<Result<Vec<_>, _>>()?;
    positions.sort_by_key(|view| (view.rank.unwrap_or(u32::MAX), view.key));
    let session = state.last_session.as_ref();
    Ok(CountyReviewProjection {
        county: config.county,
        administration_label: config.administration_label.clone(),
        claimants_body_label: config.claimants_body_label.clone(),
        aid_body_label: config.aid_body_label.clone(),
        roster_period: state.roster.period,
        first_session_period: config.first_session_period,
        session_period: session.map(|s| s.period),
        unit_price_micros: config.unit_price_micros,
        cash_micros: ledger.cash_micros,
        spending_limit_micros: ledger.spending_limit_micros,
        ledger: lines,
        first_class_micros,
        relief_micros: session.map(|s| s.relief_micros),
        household_units_payable: session.map(|s| s.household_units_payable),
        kept_back_units: session.map(|s| s.kept_back_units),
        roll: roll_by_group(config, state)?,
        bands: state.roster.band_counts(),
        claimants_roll_households: session.map(|s| s.claimants_roll_households),
        aid_roll_households: session.map(|s| s.aid_roll_households),
        contact: session.and_then(|s| s.contact),
        positions,
    })
}
