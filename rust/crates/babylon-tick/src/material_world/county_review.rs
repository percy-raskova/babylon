//! The county review's section of the material register and the labor facts it is fed.
//!
//! The section holds the county administration's captured configuration and the roster the
//! session rolls forward. It is the City PD's section in shape: one optional frame, canonical
//! bytes, and a check against the world it sits in at every rebuild. The labor facts are read from
//! the receipts of the close that prepared the successor, before any later operation runs.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::{Formatter, Result as FmtResult};

use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, FinalDemandPrincipalId, HouseholdContributionUse, HouseholdKind,
    HouseholdTimeAccounting, LaborCompensation, MaterialCircuitState, MaterialCircuitTransition,
    MonetaryCircuit, PublicAccountId, PublicAllocation, PublicTransferTreatment, SiteId,
    StaffingMemberId, TaxBasis, UnitId,
};
use babylon_practice_contract::{
    CountyReviewConfig, CountyReviewError, CountyReviewGroup, CountyReviewState, CrewPeriodFacts,
    GroupKind, HourCharge, PayMode, SupportLine,
};

use super::register;
use super::MaterialWorldError;

/// The priority of household support lines: after grants and appropriations, which are at 0.
const SUPPORT_PRIORITY: u32 = 1;
/// The domain of the county's frame in a version 9 register.
pub(super) const COUNTY_FRAME_DOMAIN: &[u8] = b"babylon.material-world-register.county-review.v1\0";

/// Why the county's section, or a period's facts for it, was refused.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CountyReviewRegisterError {
    /// The kernel refused the configuration, the roster, the facts or the session.
    Kernel(CountyReviewError),
    /// The world is not a monetary circuit with household cohorts and modeled household time.
    Economy,
    /// The county's public account or its budget is not in the world.
    PublicAccount,
    /// A configured group is not a household cohort of the world, or the households differ.
    Cohort,
    /// A configured crew is not an employment row of its group.
    Employment,
    /// The public account's household support lines are not the lines the section announces.
    Lines,
    /// The roster, the facts or the session stand for another period than the register.
    Period,
    /// A receipt of the close does not belong to the configured crew or group it names.
    Receipt,
    /// The organizer's journal does not hold exactly one coherent review contact.
    Contact,
    /// The section's frame is malformed.
    Framing,
    /// An exact sum left its range.
    Arithmetic,
}

impl std::fmt::Display for CountyReviewRegisterError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        write!(formatter, "county review register refused: {self:?}")
    }
}
impl std::error::Error for CountyReviewRegisterError {}

impl From<CountyReviewError> for CountyReviewRegisterError {
    fn from(error: CountyReviewError) -> Self {
        Self::Kernel(error)
    }
}

impl From<CountyReviewError> for MaterialWorldError {
    fn from(error: CountyReviewError) -> Self {
        Self::CountyReview(CountyReviewRegisterError::Kernel(error))
    }
}

impl From<CountyReviewRegisterError> for MaterialWorldError {
    fn from(error: CountyReviewRegisterError) -> Self {
        Self::CountyReview(error)
    }
}

/// The captured county administration and the roster of its households, bound into the register.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CountyReviewRegister {
    config: CountyReviewConfig,
    state: CountyReviewState,
}

impl CountyReviewRegister {
    /// Bind a configuration to the state that follows it.
    ///
    /// # Errors
    ///
    /// The kernel's refusal of a state that does not follow its configuration.
    pub fn try_new(
        config: CountyReviewConfig,
        state: CountyReviewState,
    ) -> Result<Self, MaterialWorldError> {
        babylon_practice_contract::validate_county_review_state(&config, &state)?;
        Ok(Self { config, state })
    }

    /// The captured configuration.
    #[must_use]
    pub const fn config(&self) -> &CountyReviewConfig {
        &self.config
    }

    /// The roster, the facts of the last close and the last session.
    #[must_use]
    pub const fn state(&self) -> &CountyReviewState {
        &self.state
    }
}

/// One budget group's wage tax, income and households in the period just closed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CountyGroupLabor {
    /// Index of the group in the configuration.
    pub group: u32,
    /// Wages taxed.
    pub taxed_wages_micros: i128,
    /// Wage tax collected.
    pub wage_tax_collected_micros: i128,
    /// Income from ownership.
    pub ownership_income_micros: i128,
    /// Income from county support.
    pub support_income_micros: i128,
    /// Income from mutual aid.
    pub aid_income_micros: i128,
    /// Households after the period.
    pub closing_households: u64,
}

/// The labor and tax facts of one close, for every configured crew and group, in the
/// configuration's order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CountyLaborFacts {
    /// One entry for each configured crew.
    pub crews: Vec<CrewPeriodFacts>,
    /// One entry for each configured group.
    pub groups: Vec<CountyGroupLabor>,
}

fn index(value: usize) -> Result<u32, CountyReviewRegisterError> {
    u32::try_from(value).map_err(|_| CountyReviewRegisterError::Arithmetic)
}

fn checked_add(a: u64, b: u64) -> Result<u64, CountyReviewRegisterError> {
    a.checked_add(b)
        .ok_or(CountyReviewRegisterError::Arithmetic)
}

fn checked_add_micros(a: i128, b: i128) -> Result<i128, CountyReviewRegisterError> {
    a.checked_add(b)
        .ok_or(CountyReviewRegisterError::Arithmetic)
}

/// The group a crew belongs to.
fn group_of(
    config: &CountyReviewConfig,
    group: u32,
) -> Result<&CountyReviewGroup, CountyReviewRegisterError> {
    usize::try_from(group)
        .ok()
        .and_then(|g| config.groups.get(g))
        .ok_or(CountyReviewRegisterError::Kernel(
            CountyReviewError::UnknownGroup,
        ))
}

/// The canonical bytes of the county's frame: the domain, then the configuration and the state,
/// each length-prefixed.
pub(super) fn encode(register: &CountyReviewRegister) -> Result<Vec<u8>, MaterialWorldError> {
    let config = babylon_practice_contract::encode_county_review_config(&register.config)?;
    let state = babylon_practice_contract::encode_county_review_state(&register.state)?;
    let length = COUNTY_FRAME_DOMAIN
        .len()
        .checked_add(16)
        .and_then(|n| n.checked_add(config.len()))
        .and_then(|n| n.checked_add(state.len()))
        .ok_or(MaterialWorldError::Arithmetic)?;
    let mut bytes = Vec::new();
    bytes
        .try_reserve_exact(length)
        .map_err(|_| MaterialWorldError::Allocation)?;
    bytes.extend_from_slice(COUNTY_FRAME_DOMAIN);
    for part in [&config, &state] {
        bytes.extend_from_slice(
            &u64::try_from(part.len())
                .map_err(|_| MaterialWorldError::Arithmetic)?
                .to_be_bytes(),
        );
        bytes.extend_from_slice(part);
    }
    Ok(bytes)
}

/// Reads the county's frame. The bytes must be exactly the canonical bytes of what they hold.
pub(super) fn decode(frame: &[u8]) -> Result<CountyReviewRegister, MaterialWorldError> {
    let mut rest = frame
        .strip_prefix(COUNTY_FRAME_DOMAIN)
        .ok_or(CountyReviewRegisterError::Framing)?;
    let config = register::take_organizer_section(&mut rest)?;
    let state = register::take_organizer_section(&mut rest)?;
    if !rest.is_empty() {
        return Err(CountyReviewRegisterError::Framing.into());
    }
    let register = CountyReviewRegister::try_new(
        babylon_practice_contract::decode_county_review_config(config)?,
        babylon_practice_contract::decode_county_review_state(state)?,
    )?;
    if encode(&register)? != frame {
        return Err(CountyReviewRegisterError::Framing.into());
    }
    Ok(register)
}

/// The household support allocation for one group's principal, if the account has one.
fn support_row(
    economy: &MonetaryCircuit,
    account: PublicAccountId,
    principal: FinalDemandPrincipalId,
) -> Option<i128> {
    economy
        .financial
        .public_allocations
        .iter()
        .find(|row| {
            row.public_account == account
                && row.treatment == PublicTransferTreatment::HouseholdIncomeSupport
                && row.recipient == AccountId::Household(principal)
        })
        .map(|row| row.amount_per_period.micro_units())
}

/// What the section says a group's household support line is.
enum Announced {
    /// The section has no session for the register's period: it says nothing.
    Unsaid,
    /// The group has no line.
    NoLine,
    /// The group's line, in millionths of a dollar.
    Line(i128),
}

/// The lines the section announces for a group: the session's lines once it has held one for the
/// register's period, otherwise the opening roll at the unit price.
fn announced_line(
    register: &CountyReviewRegister,
    completed_tick: u64,
    group: u32,
) -> Result<Announced, CountyReviewRegisterError> {
    let config = &register.config;
    let configured = group_of(config, group)?;
    if completed_tick < config.first_session_period {
        let units = i128::from(configured.roll_units);
        let amount = units
            .checked_mul(config.unit_price_micros)
            .ok_or(CountyReviewRegisterError::Arithmetic)?;
        return Ok(if amount > 0 {
            Announced::Line(amount)
        } else {
            Announced::NoLine
        });
    }
    let Some(session) = register
        .state
        .last_session
        .as_ref()
        .filter(|session| session.period == completed_tick)
    else {
        return Ok(Announced::Unsaid);
    };
    let line = session
        .lines
        .iter()
        .chain(&session.collective_lines)
        .find(|line| line.group == group);
    Ok(line.map_or(Announced::NoLine, |line| {
        Announced::Line(line.amount_micros)
    }))
}

/// Checks the section against the world it is bound into.
///
/// Every configured group is a household cohort with the roster's households, every crew is an
/// employment row of its group, the public account and its budget exist, the roster, the facts and
/// the session stand for the register's period, and the account's household support lines are the
/// ones the section announces.
pub(super) fn validate_world(
    register: &CountyReviewRegister,
    state: &MaterialCircuitState,
    completed_tick: u64,
) -> Result<(), MaterialWorldError> {
    use CountyReviewRegisterError as E;
    let config = &register.config;
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(E::Economy.into());
    };
    let cohorts = &economy.recurring.as_ref().ok_or(E::Economy)?.households;
    if !matches!(economy.household_time, HouseholdTimeAccounting::Modeled(_)) {
        return Err(E::Economy.into());
    }
    let account = PublicAccountId::from_bytes(config.public_account_id);
    economy
        .book
        .cash(AccountId::Public(account))
        .map_err(|_| E::PublicAccount)?;
    if !economy
        .financial
        .public_budgets
        .iter()
        .any(|budget| budget.public_account == account)
    {
        return Err(E::PublicAccount.into());
    }
    let roster = &register.state.roster;
    for (position, group) in config.groups.iter().enumerate() {
        let principal = FinalDemandPrincipalId::from_bytes(group.group_id);
        let cohort = cohorts
            .iter()
            .find(|cohort| cohort.principal_id == principal)
            .ok_or(E::Cohort)?;
        let kind = match group.kind {
            GroupKind::Ordinary => HouseholdKind::Ordinary,
            GroupKind::CollectiveResidence => HouseholdKind::CollectiveResidence,
        };
        let households = roster.groups.get(position).ok_or(E::Cohort)?.households;
        if cohort.kind != kind || cohort.households != households {
            return Err(E::Cohort.into());
        }
    }
    for crew in &config.crews {
        let principal = FinalDemandPrincipalId::from_bytes(group_of(config, crew.group)?.group_id);
        let paid = economy.employment.iter().any(|row| {
            row.member_id == StaffingMemberId::from_bytes(crew.crew_id)
                && row.site_id == SiteId::from_bytes(crew.site_id)
                && row.unit_id == UnitId::from_bytes(crew.unit_id)
                && row.payee == principal
                && matches!(
                    (crew.pay_mode, row.compensation),
                    (PayMode::Wage, LaborCompensation::Wage(_))
                        | (PayMode::WorkingOwner, LaborCompensation::WorkingOwner)
                        | (PayMode::UnpaidFamily, LaborCompensation::UnpaidFamily)
                )
        });
        if !paid {
            return Err(E::Employment.into());
        }
    }
    let content = &register.state;
    if roster.period != completed_tick
        || content
            .last_facts
            .as_ref()
            .is_some_and(|facts| facts.period != completed_tick)
        || content
            .last_session
            .as_ref()
            .is_some_and(|session| session.period > completed_tick)
    {
        return Err(E::Period.into());
    }
    for (position, group) in config.groups.iter().enumerate() {
        let principal = FinalDemandPrincipalId::from_bytes(group.group_id);
        let held = support_row(economy, account, principal);
        let agrees = match announced_line(register, completed_tick, index(position)?)? {
            Announced::Unsaid => true,
            Announced::NoLine => held.is_none(),
            Announced::Line(amount) => held == Some(amount),
        };
        if !agrees {
            return Err(E::Lines.into());
        }
    }
    Ok(())
}

/// The use of one group's hours the session charges: the SHA-256 of the campaign, the period and
/// the group.
pub(super) fn hours_use_id(
    config: &CountyReviewConfig,
    period: u64,
    group_id: [u8; 32],
) -> [u8; 32] {
    let mut identity = b"babylon.county-review-hours.v1\0".to_vec();
    identity.extend_from_slice(&config.campaign_id);
    identity.extend_from_slice(&period.to_be_bytes());
    identity.extend_from_slice(&group_id);
    content_digest::sha256_of(&identity)
}

/// The single row of a receipt family for one member, if there is one.
fn only<'a, T>(
    rows: impl Iterator<Item = &'a T>,
) -> Result<Option<&'a T>, CountyReviewRegisterError> {
    let mut rows = rows;
    let first = rows.next();
    if rows.next().is_some() {
        return Err(CountyReviewRegisterError::Receipt);
    }
    Ok(first)
}

/// One crew's facts. The engine removes people before it hires or lays off, so a staffing
/// receipt's opening counts are the counts after the removal: the kernel's opening counts are
/// those plus the people removed. A crew with no staffing receipt in the period keeps the roster's
/// counts; its wages are still read from its labor-use receipt (zero when it has none).
fn crew_facts(
    register: &CountyReviewRegister,
    transition: &MaterialCircuitTransition,
    position: usize,
) -> Result<CrewPeriodFacts, CountyReviewRegisterError> {
    use CountyReviewRegisterError as E;
    let config = &register.config;
    let crew = config.crews.get(position).ok_or(E::Receipt)?;
    let id = StaffingMemberId::from_bytes(crew.crew_id);
    let at = index(position)?;
    let principal = FinalDemandPrincipalId::from_bytes(group_of(config, crew.group)?.group_id);
    let (site, unit) = (
        SiteId::from_bytes(crew.site_id),
        UnitId::from_bytes(crew.unit_id),
    );
    let staffing = only(
        transition
            .staffing_members
            .iter()
            .filter(|row| row.member.member_id() == id),
    )?;
    let attrition = only(
        transition
            .resident_workforce_attrition
            .iter()
            .filter(|row| row.member_id == id),
    )?;
    let labor = only(
        transition
            .member_labor_use
            .iter()
            .filter(|row| row.member_id == id),
    )?;
    let wages = match labor {
        Some(row) if row.site_id != site || row.unit_id != unit || row.payee != principal => {
            return Err(E::Receipt)
        }
        Some(row) => row.accrued_wages.micro_units(),
        None => 0,
    };
    match (staffing, attrition) {
        (Some(row), removed) => {
            if row.member.household_id() != principal || row.site_id != site || row.unit_id != unit
            {
                return Err(E::Receipt);
            }
            let (left_at_work, left_seeking) =
                removed.map_or((0, 0), |r| (r.employed_removed, r.reserve_removed));
            Ok(CrewPeriodFacts {
                crew: at,
                accrued_wages_micros: wages,
                opening_at_work: checked_add(row.opening_employed, left_at_work)?,
                opening_seeking: checked_add(row.opening_reserve, left_seeking)?,
                left_at_work,
                left_seeking,
                hires: row.hires,
                separations: row.separations,
                closing_at_work: row.closing_employed,
                closing_seeking: row.closing_reserve,
            })
        }
        (None, None) => {
            let at_work = register.state.roster.crew_at_work(at);
            let seeking = register.state.roster.crew_seeking(at);
            Ok(CrewPeriodFacts {
                crew: at,
                accrued_wages_micros: wages,
                opening_at_work: at_work,
                opening_seeking: seeking,
                left_at_work: 0,
                left_seeking: 0,
                hires: 0,
                separations: 0,
                closing_at_work: at_work,
                closing_seeking: seeking,
            })
        }
        (None, Some(_)) => Err(E::Receipt),
    }
}

/// One group's wage tax, income and households. A group with no receipt of a kind has zero for
/// that figure.
fn group_facts(
    config: &CountyReviewConfig,
    transition: &MaterialCircuitTransition,
    cohorts: &BTreeMap<FinalDemandPrincipalId, u64>,
    position: usize,
) -> Result<CountyGroupLabor, CountyReviewRegisterError> {
    let group = config
        .groups
        .get(position)
        .ok_or(CountyReviewRegisterError::Receipt)?;
    let principal = FinalDemandPrincipalId::from_bytes(group.group_id);
    let (mut taxed, mut collected) = (0_i128, 0_i128);
    for tax in transition.taxes.iter().filter(|tax| {
        tax.payer == AccountId::Household(principal) && tax.basis == TaxBasis::WageIncome
    }) {
        taxed = checked_add_micros(taxed, tax.taxable_amount.micro_units())?;
        collected = checked_add_micros(collected, tax.collected.micro_units())?;
    }
    let income = only(
        transition
            .income
            .iter()
            .filter(|row| row.account == AccountId::Household(principal)),
    )?;
    let closing_households = match only(
        transition
            .household_lifecycle
            .iter()
            .filter(|row| row.principal_id == principal),
    )? {
        Some(row) => row.closing_households,
        None => *cohorts
            .get(&principal)
            .ok_or(CountyReviewRegisterError::Cohort)?,
    };
    Ok(CountyGroupLabor {
        group: index(position)?,
        taxed_wages_micros: taxed,
        wage_tax_collected_micros: collected,
        ownership_income_micros: income
            .map_or(0, |row| row.statement.distribution_income.micro_units()),
        support_income_micros: income
            .map_or(0, |row| row.statement.public_transfer_income.micro_units()),
        aid_income_micros: income.map_or(0, |row| row.statement.gift_income.micro_units()),
        closing_households,
    })
}

/// Reads the labor and tax facts of the close from its receipts, for every configured crew and
/// group in the configuration's order.
pub(super) fn labor_facts(
    register: &CountyReviewRegister,
    transition: &MaterialCircuitTransition,
) -> Result<CountyLaborFacts, MaterialWorldError> {
    let cohorts: BTreeMap<_, _> = match &transition.state.accounting {
        CircuitAccounting::Monetary(economy) => economy
            .recurring
            .as_ref()
            .ok_or(CountyReviewRegisterError::Economy)?
            .households
            .iter()
            .map(|cohort| (cohort.principal_id, cohort.households))
            .collect(),
        CircuitAccounting::PhysicalControl => return Err(CountyReviewRegisterError::Economy.into()),
    };
    let crews = (0..register.config.crews.len())
        .map(|position| crew_facts(register, transition, position))
        .collect::<Result<_, _>>()?;
    let groups = (0..register.config.groups.len())
        .map(|position| group_facts(&register.config, transition, &cohorts, position))
        .collect::<Result<_, _>>()?;
    Ok(CountyLaborFacts { crews, groups })
}

/// Replaces the household support rows of the configured groups with the session's lines, at
/// priority 1. A group with no line has no row. No other row changes.
pub(super) fn write_support_lines(
    config: &CountyReviewConfig,
    state: &mut MaterialCircuitState,
    lines: &[SupportLine],
    collective_lines: &[SupportLine],
) -> Result<(), MaterialWorldError> {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Err(CountyReviewRegisterError::Economy.into());
    };
    let account = PublicAccountId::from_bytes(config.public_account_id);
    let recipients: BTreeSet<AccountId> = config
        .groups
        .iter()
        .map(|group| AccountId::Household(FinalDemandPrincipalId::from_bytes(group.group_id)))
        .collect();
    let allocations = &mut economy.financial.public_allocations;
    allocations.retain(|row| {
        !(row.public_account == account
            && row.treatment == PublicTransferTreatment::HouseholdIncomeSupport
            && recipients.contains(&row.recipient))
    });
    for line in lines.iter().chain(collective_lines) {
        let group = group_of(config, line.group)?;
        allocations.push(PublicAllocation {
            public_account: account,
            recipient: AccountId::Household(FinalDemandPrincipalId::from_bytes(group.group_id)),
            treatment: PublicTransferTreatment::HouseholdIncomeSupport,
            priority: SUPPORT_PRIORITY,
            amount_per_period: Currency::from_micro_units(line.amount_micros),
        });
    }
    allocations.sort_by_key(|row| {
        (
            row.public_account,
            row.priority,
            row.recipient,
            row.treatment,
        )
    });
    Ok(())
}

/// One use of a group's household hours for each charge, under the county's actor.
pub(super) fn hour_uses(
    config: &CountyReviewConfig,
    period: u64,
    charges: &[HourCharge],
) -> Result<Vec<HouseholdContributionUse>, MaterialWorldError> {
    charges
        .iter()
        .map(|charge| {
            let group = group_of(config, charge.group)?;
            Ok(HouseholdContributionUse {
                use_id: hours_use_id(config, period, group.group_id),
                principal_id: FinalDemandPrincipalId::from_bytes(group.group_id),
                actor_id: config.actor_id,
                contributor_id: u64::from(charge.group)
                    .checked_add(1)
                    .ok_or(CountyReviewRegisterError::Arithmetic)?,
                hours: charge.hours,
            })
        })
        .collect()
}
