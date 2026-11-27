//! One period of the county review: the session after the organizer's practice, the roster rolled
//! forward, and the lines and hours written into the closed state.

use babylon_graph::stable_element::StableElementResolver;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, FinalDemandPrincipalId, HouseholdTimeAccounting, MaterialCatalog,
    MaterialCircuitState, PublicAccountId, PublicTransferTreatment,
};
use babylon_practice_contract::{
    CountyPeriodFacts, CountyReviewConfig, CountyReviewState, GroupPeriodFacts, OrganizerChoice,
    OrganizerOutcome, OrganizerPeriodJournalEntries, PositionKey, SessionOutcome,
    COUNTY_REVIEW_SCHEMA_VERSION,
};

use super::county_review::{CountyLaborFacts, CountyReviewRegisterError};
use super::{MaterialWorldError, PreparedMaterialWorld};

/// What one period of the county leaves: the state to keep and the session, if one was held.
#[derive(Debug, PartialEq, Eq)]
pub(super) struct HeldPeriod {
    pub(super) next: CountyReviewState,
    pub(super) session: Option<SessionOutcome>,
}

/// Runs the county's period on the closed, detached world.
///
/// It starts from the section as the period opened, so a second call on the same candidate reads
/// the same facts and writes the same bytes: the hours it charged are left out of the free hours
/// it reads.
pub(crate) fn resolve(
    candidate: &mut PreparedMaterialWorld,
    catalog: &MaterialCatalog,
    resolver: &StableElementResolver,
) -> Result<(), MaterialWorldError> {
    let opening = candidate
        .county_review_opening()
        .cloned()
        .ok_or(CountyReviewRegisterError::Economy)?;
    let labor = candidate
        .county_labor_facts()
        .cloned()
        .ok_or(CountyReviewRegisterError::Economy)?;
    let register = candidate.register();
    let period = register.completed_tick();
    let facts = period_facts(opening.config(), &labor, register.state(), period)?;
    let contact = review_contact(
        register
            .organizer_journal()
            .and_then(|journal| journal.latest()),
        period,
    )?;
    let held = hold_period(opening.config(), opening.state(), &facts, contact)?;
    candidate.set_county_review(catalog, held.next, held.session.as_ref(), resolver)
}

/// The period's facts: the labor facts of the close, and the county's money and its households'
/// free hours from the closed state.
///
/// Free hours are a group's contribution hours of the period less the hours already given to
/// anyone but the county, so the county's own charge is never counted against itself. A group with
/// no time receipt has none.
pub(super) fn period_facts(
    config: &CountyReviewConfig,
    labor: &CountyLaborFacts,
    state: &MaterialCircuitState,
    period: u64,
) -> Result<CountyPeriodFacts, MaterialWorldError> {
    use CountyReviewRegisterError as E;
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(E::Economy.into());
    };
    let HouseholdTimeAccounting::Modeled(time) = &economy.household_time else {
        return Err(E::Economy.into());
    };
    let account = PublicAccountId::from_bytes(config.public_account_id);
    let budget = economy
        .financial
        .public_budgets
        .iter()
        .find(|budget| budget.public_account == account)
        .ok_or(E::PublicAccount)?;
    let cash = economy
        .book
        .cash(AccountId::Public(account))
        .map_err(|_| E::PublicAccount)?;
    let mut first_class = 0_i128;
    for row in &economy.financial.public_allocations {
        if row.public_account == account
            && row.treatment != PublicTransferTreatment::HouseholdIncomeSupport
        {
            first_class = first_class
                .checked_add(row.amount_per_period.micro_units())
                .ok_or(E::Arithmetic)?;
        }
    }
    let mut groups = Vec::with_capacity(labor.groups.len());
    for (group, configured) in labor.groups.iter().zip(&config.groups) {
        let principal = FinalDemandPrincipalId::from_bytes(configured.group_id);
        let available = time
            .receipts
            .iter()
            .filter(|row| row.principal_id == principal && row.period == period)
            .try_fold(0_u64, |total, row| {
                total.checked_add(row.contribution_available_hours)
            })
            .ok_or(E::Arithmetic)?;
        let given = time
            .contributions
            .iter()
            .filter(|row| {
                row.contribution.principal_id == principal
                    && row.period == period
                    && row.contribution.actor_id != config.actor_id
            })
            .try_fold(0_u64, |total, row| {
                total.checked_add(row.contribution.hours)
            })
            .ok_or(E::Arithmetic)?;
        groups.push(GroupPeriodFacts {
            group: group.group,
            taxed_wages_micros: group.taxed_wages_micros,
            wage_tax_collected_micros: group.wage_tax_collected_micros,
            ownership_income_micros: group.ownership_income_micros,
            support_income_micros: group.support_income_micros,
            aid_income_micros: group.aid_income_micros,
            free_hours: available.checked_sub(given).ok_or(E::Arithmetic)?,
            closing_households: group.closing_households,
        });
    }
    Ok(CountyPeriodFacts {
        period,
        crews: labor.crews.clone(),
        groups,
        cash_micros: cash.micro_units(),
        cash_floor_micros: budget.cash_floor.micro_units(),
        spending_limit_micros: budget.period_cap.micro_units(),
        first_class_micros: first_class,
    })
}

/// The position the organizer reached this period, if the journal holds a review contact.
pub(super) fn review_contact(
    entries: Option<&OrganizerPeriodJournalEntries>,
    period: u64,
) -> Result<Option<PositionKey>, MaterialWorldError> {
    let entries = entries.ok_or(CountyReviewRegisterError::Contact)?;
    if entries.period != period {
        return Err(CountyReviewRegisterError::Contact.into());
    }
    let mut contacts = entries
        .receipts
        .iter()
        .filter(|receipt| receipt.outcome == OrganizerOutcome::ReviewContactMade);
    let contact = match contacts.next() {
        None => None,
        Some(receipt) => match receipt.choice {
            OrganizerChoice::ReviewContact(key) => Some(key),
            _ => return Err(CountyReviewRegisterError::Contact.into()),
        },
    };
    if contacts.next().is_some() {
        return Err(CountyReviewRegisterError::Contact.into());
    }
    Ok(contact)
}

/// The county's period on its own: before the first session only the roster moves; from the first
/// session on the session is held on the roster as it stood, and the roster it leaves moves.
/// Both keep the facts. A period with no session keeps the last session as it was.
pub(super) fn hold_period(
    config: &CountyReviewConfig,
    state: &CountyReviewState,
    facts: &CountyPeriodFacts,
    contact: Option<PositionKey>,
) -> Result<HeldPeriod, MaterialWorldError> {
    if facts.period < config.first_session_period {
        if contact.is_some() {
            return Err(CountyReviewRegisterError::Contact.into());
        }
        return Ok(HeldPeriod {
            next: CountyReviewState {
                schema_version: COUNTY_REVIEW_SCHEMA_VERSION,
                roster: babylon_practice_contract::roll_forward(config, &state.roster, facts)?,
                last_facts: Some(facts.clone()),
                last_session: state.last_session.clone(),
            },
            session: None,
        });
    }
    let outcome = babylon_practice_contract::hold_session(config, &state.roster, facts, contact)?;
    let roster = babylon_practice_contract::roll_forward(config, &outcome.roster, facts)?;
    Ok(HeldPeriod {
        next: CountyReviewState {
            schema_version: COUNTY_REVIEW_SCHEMA_VERSION,
            roster,
            last_facts: Some(facts.clone()),
            last_session: Some(outcome.record.clone()),
        },
        session: Some(outcome),
    })
}
