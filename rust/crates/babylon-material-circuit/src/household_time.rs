//! Finite resident time after actual attendance and necessary provisioning.
//!
//! These accounts measure hours, not political consent. The organizer must admit
//! an independent agreement before consuming a household contribution.

use std::collections::{BTreeMap, BTreeSet};

use crate::{
    CircuitAccounting, FinalDemandPrincipalId, GoodId, HouseholdCohort,
    HouseholdConsumptionReceipt, HouseholdNeed, HouseholdNeedBasis, HouseholdServiceReceipt,
    MaterialCircuitError, MaterialCircuitState, MemberLaborUseReceipt, UnitId,
    MAX_MATERIAL_CIRCUIT_ROWS,
};

type Result<T> = std::result::Result<T, MaterialCircuitError>;
type Cohorts<'a> = BTreeMap<FinalDemandPrincipalId, &'a HouseholdCohort>;
type Needs<'a> = BTreeMap<(FinalDemandPrincipalId, GoodId, UnitId), &'a HouseholdNeed>;
type Policies<'a> = BTreeMap<FinalDemandPrincipalId, &'a HouseholdTimePolicy>;

/// Closed controls explicitly omit this account. Captured campaigns model it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HouseholdTimeAccounting {
    NotModeled,
    Modeled(HouseholdTimeBook),
}

/// A declared requirement in resident or occupied-household hours.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdTimeCommitment {
    pub basis: HouseholdNeedBasis,
    pub hours_per_basis: u64,
}

/// An unmet physical requirement creates a declared time claim, not goods.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdUnmetTimeBurden {
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub hours_per_unmet_unit: u64,
}

/// Eligibility is captured separately from employment and cannot create people.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdTimePolicy {
    pub principal_id: FinalDemandPrincipalId,
    pub labor_unit_id: UnitId,
    pub eligible_persons: u64,
    pub hours_per_eligible_person: u64,
    pub protected: HouseholdTimeCommitment,
    pub routine_provisioning: HouseholdTimeCommitment,
    pub unmet_burdens: Vec<HouseholdUnmetTimeBurden>,
}

/// Last completed period; unpaid claims partition allocated and unresolved hours.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdTimeReceipt {
    pub principal_id: FinalDemandPrincipalId,
    pub period: u64,
    pub labor_unit_id: UnitId,
    pub endowment_hours: u64,
    pub attended_hours: u64,
    pub protected_hours: u64,
    pub protected_unresolved_hours: u64,
    pub unpaid_requested_hours: u64,
    pub unpaid_allocated_hours: u64,
    pub unpaid_unresolved_hours: u64,
    pub contribution_available_hours: u64,
}

impl HouseholdTimeReceipt {
    /// Check exact hour partitions, without interpreting unresolved claims as work.
    /// # Errors
    /// Refuses zero periods, overflow and inconsistent partitions.
    pub fn validate(&self) -> Result<()> {
        sum(&[self.protected_hours, self.protected_unresolved_hours])?;
        if self.period == 0
            || sum(&[
                self.attended_hours,
                self.protected_hours,
                self.unpaid_allocated_hours,
                self.contribution_available_hours,
            ])? != self.endowment_hours
            || sum(&[self.unpaid_allocated_hours, self.unpaid_unresolved_hours])?
                != self.unpaid_requested_hours
            || (self.protected_unresolved_hours != 0
                && (self.unpaid_allocated_hours != 0 || self.contribution_available_hours != 0))
            || (self.unpaid_unresolved_hours != 0 && self.contribution_available_hours != 0)
        {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
        Ok(())
    }
}

/// Several organizational aliases may draw from this one household account.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdContributionUse {
    pub use_id: [u8; 32],
    pub principal_id: FinalDemandPrincipalId,
    pub actor_id: u64,
    pub contributor_id: u64,
    pub hours: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdContributionReceipt {
    pub period: u64,
    pub contribution: HouseholdContributionUse,
}

/// Policies persist; receipts and uses describe exactly the last completed period.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdTimeBook {
    pub policies: Vec<HouseholdTimePolicy>,
    pub receipts: Vec<HouseholdTimeReceipt>,
    pub contributions: Vec<HouseholdContributionReceipt>,
}

impl HouseholdTimeBook {
    /// Construct a policy book before its first close.
    /// # Errors
    /// Refuses duplicate identities, zero endowment or burden rates, excessive
    /// rows or overflow. Explicit zero protected/provisioning controls are valid.
    pub fn new(policies: Vec<HouseholdTimePolicy>) -> Result<Self> {
        let mut book = Self {
            policies,
            receipts: Vec::new(),
            contributions: Vec::new(),
        };
        canonicalize_book(&mut book);
        validate_structure(&book)?;
        Ok(book)
    }
}

fn sum(values: &[u64]) -> Result<u64> {
    values.iter().try_fold(0_u64, |n, value| {
        n.checked_add(*value)
            .ok_or(MaterialCircuitError::Arithmetic)
    })
}

fn multiply(left: u64, right: u64) -> Result<u64> {
    left.checked_mul(right)
        .ok_or(MaterialCircuitError::Arithmetic)
}

fn requirement(commitment: &HouseholdTimeCommitment, cohort: &HouseholdCohort) -> Result<u64> {
    multiply(
        match commitment.basis {
            HouseholdNeedBasis::Persons => cohort.persons,
            HouseholdNeedBasis::Households => cohort.households,
        },
        commitment.hours_per_basis,
    )
}

fn canonicalize_book(book: &mut HouseholdTimeBook) {
    book.policies.sort_by_key(|row| row.principal_id);
    for policy in &mut book.policies {
        policy
            .unmet_burdens
            .sort_by_key(|row| (row.good_id, row.unit_id));
    }
    book.receipts.sort_by_key(|row| row.principal_id);
    book.contributions
        .sort_by_key(|row| row.contribution.use_id);
}

pub(crate) fn canonicalize(accounting: &mut HouseholdTimeAccounting) {
    if let HouseholdTimeAccounting::Modeled(book) = accounting {
        canonicalize_book(book);
    }
}

pub(crate) fn validate_structure(book: &HouseholdTimeBook) -> Result<()> {
    if [
        book.policies.len(),
        book.receipts.len(),
        book.contributions.len(),
    ]
    .into_iter()
    .any(|length| length > MAX_MATERIAL_CIRCUIT_ROWS)
    {
        return Err(MaterialCircuitError::RowLimit);
    }
    let mut policies = BTreeSet::new();
    let mut burden_count = 0_usize;
    for row in &book.policies {
        if !policies.insert(row.principal_id) || row.hours_per_eligible_person == 0 {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
        multiply(row.eligible_persons, row.hours_per_eligible_person)?;
        burden_count = burden_count
            .checked_add(row.unmet_burdens.len())
            .ok_or(MaterialCircuitError::Arithmetic)?;
        if burden_count > MAX_MATERIAL_CIRCUIT_ROWS {
            return Err(MaterialCircuitError::RowLimit);
        }
        let mut needs = BTreeSet::new();
        for need in &row.unmet_burdens {
            if need.hours_per_unmet_unit == 0 || !needs.insert((need.good_id, need.unit_id)) {
                return Err(MaterialCircuitError::HouseholdTimeInvariant);
            }
        }
    }
    let mut receipts = BTreeMap::new();
    for row in &book.receipts {
        row.validate()?;
        if !policies.contains(&row.principal_id) || receipts.insert(row.principal_id, row).is_some()
        {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
    }
    let mut identities = BTreeSet::new();
    let mut consumed = BTreeMap::<_, u64>::new();
    for row in &book.contributions {
        let usage = &row.contribution;
        let receipt = receipts
            .get(&usage.principal_id)
            .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
        if row.period != receipt.period
            || usage.hours == 0
            || usage.actor_id == 0
            || usage.contributor_id == 0
            || usage.use_id == [0; 32]
            || !identities.insert(usage.use_id)
        {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
        let used = consumed.entry(usage.principal_id).or_default();
        *used = sum(&[*used, usage.hours])?;
        if *used > receipt.contribution_available_hours {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
    }
    Ok(())
}

pub(crate) fn validate(state: &MaterialCircuitState) -> Result<()> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(());
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        return Ok(());
    };
    validate_structure(book)?;
    let recurring = economy
        .recurring
        .as_ref()
        .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
    let cohorts: Cohorts<'_> = recurring
        .households
        .iter()
        .map(|r| (r.principal_id, r))
        .collect();
    if book.policies.len() != cohorts.len() {
        return Err(MaterialCircuitError::HouseholdTimeInvariant);
    }
    let needs: Needs<'_> = recurring
        .household_needs
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r))
        .collect();
    let policies: Policies<'_> = book.policies.iter().map(|r| (r.principal_id, r)).collect();
    if cohorts.len() != recurring.households.len() || needs.len() != recurring.household_needs.len()
    {
        return Err(MaterialCircuitError::HouseholdTimeInvariant);
    }
    validate_policies(state, economy, book, &cohorts, &needs, &policies)?;
    validate_receipts(state.period, book, &cohorts, &needs, &policies)
}

fn validate_policies(
    state: &MaterialCircuitState,
    economy: &crate::MonetaryCircuit,
    book: &HouseholdTimeBook,
    cohorts: &Cohorts<'_>,
    needs: &Needs<'_>,
    policies: &Policies<'_>,
) -> Result<()> {
    let terms: BTreeMap<_, _> = economy
        .employment
        .iter()
        .map(|r| (r.member_id, r))
        .collect();
    let time_units: BTreeSet<_> = state
        .labor
        .iter()
        .map(|r| r.unit_id)
        .chain(state.labor_coefficients.iter().map(|r| r.unit_id))
        .chain(state.merchants.iter().map(|r| r.labor_unit_id))
        .chain(state.maintenance_binding.iter().map(|r| r.labor_unit_id))
        .collect();
    let mut capacities = BTreeMap::<_, u64>::new();
    for row in &economy.member_labor {
        if row.period != state.period {
            continue;
        }
        let term = terms
            .get(&row.member_id)
            .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
        let policy = policies
            .get(&term.payee)
            .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
        if term.unit_id != policy.labor_unit_id {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
        let available = capacities.entry(term.payee).or_default();
        *available = sum(&[*available, row.available_hours])?;
    }
    for policy in &book.policies {
        let cohort = cohorts
            .get(&policy.principal_id)
            .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
        if policy.eligible_persons > cohort.persons
            || !time_units.contains(&policy.labor_unit_id)
            || capacities.get(&policy.principal_id).copied().unwrap_or(0)
                > multiply(policy.eligible_persons, policy.hours_per_eligible_person)?
            || policy
                .unmet_burdens
                .iter()
                .any(|r| !needs.contains_key(&(policy.principal_id, r.good_id, r.unit_id)))
        {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
        requirement(&policy.protected, cohort)?;
        requirement(&policy.routine_provisioning, cohort)?;
    }
    Ok(())
}

fn validate_receipts(
    period: u64,
    book: &HouseholdTimeBook,
    cohorts: &Cohorts<'_>,
    needs: &Needs<'_>,
    policies: &Policies<'_>,
) -> Result<()> {
    let previous = period
        .checked_sub(1)
        .ok_or(MaterialCircuitError::PeriodInvariant)?;
    if (previous == 0 && (!book.receipts.is_empty() || !book.contributions.is_empty()))
        || (previous != 0 && book.receipts.len() != book.policies.len())
    {
        return Err(MaterialCircuitError::HouseholdTimeInvariant);
    }
    for row in &book.receipts {
        let policy = policies
            .get(&row.principal_id)
            .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
        let cohort = cohorts
            .get(&row.principal_id)
            .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
        let after_attendance = row
            .endowment_hours
            .checked_sub(row.attended_hours)
            .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
        let protected_request = requirement(&policy.protected, cohort)?;
        let after_protected = after_attendance
            .checked_sub(row.protected_hours)
            .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
        let mut maximum_unpaid = requirement(&policy.routine_provisioning, cohort)?;
        for burden in &policy.unmet_burdens {
            let need = needs
                .get(&(policy.principal_id, burden.good_id, burden.unit_id))
                .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
            maximum_unpaid = sum(&[
                maximum_unpaid,
                multiply(need.required_quantity(cohort)?, burden.hours_per_unmet_unit)?,
            ])?;
        }
        if row.period != previous
            || row.labor_unit_id != policy.labor_unit_id
            || row.endowment_hours
                != multiply(policy.eligible_persons, policy.hours_per_eligible_person)?
            || sum(&[row.protected_hours, row.protected_unresolved_hours])? != protected_request
            || row.protected_hours != protected_request.min(after_attendance)
            || row.unpaid_allocated_hours != row.unpaid_requested_hours.min(after_protected)
            || row.unpaid_requested_hours < requirement(&policy.routine_provisioning, cohort)?
            || row.unpaid_requested_hours > maximum_unpaid
        {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
    }
    Ok(())
}

pub(crate) fn close(
    state: &mut MaterialCircuitState,
    attendance: &[MemberLaborUseReceipt],
    consumption: &[HouseholdConsumptionReceipt],
    services: &[HouseholdServiceReceipt],
) -> Result<Vec<HouseholdTimeReceipt>> {
    let result = preview(state, attendance, consumption, services)?;
    if let CircuitAccounting::Monetary(economy) = &mut state.accounting {
        if let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time {
            book.receipts.clone_from(&result);
            book.contributions.clear();
        }
    }
    Ok(result)
}

pub(crate) fn preview(
    state: &MaterialCircuitState,
    attendance: &[MemberLaborUseReceipt],
    consumption: &[HouseholdConsumptionReceipt],
    services: &[HouseholdServiceReceipt],
) -> Result<Vec<HouseholdTimeReceipt>> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(Vec::new());
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        return Ok(Vec::new());
    };
    let recurring = economy
        .recurring
        .as_ref()
        .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
    let cohorts: BTreeMap<_, _> = recurring
        .households
        .iter()
        .map(|r| (r.principal_id, r))
        .collect();
    let mut attended = BTreeMap::<_, (UnitId, u64)>::new();
    let mut members = BTreeSet::new();
    for row in attendance {
        row.validate()?;
        if row.period != state.period || !members.insert(row.member_id) {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
        let entry = attended.entry(row.payee).or_insert((row.unit_id, 0));
        if entry.0 != row.unit_id {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
        entry.1 = sum(&[entry.1, row.attended_hours])?;
    }
    let mut unmet = BTreeMap::new();
    for (period, principal, good, unit, quantity) in consumption
        .iter()
        .map(|r| {
            (
                r.period,
                r.principal_id,
                r.good_id,
                r.unit_id,
                r.unmet_quantity,
            )
        })
        .chain(services.iter().map(|r| {
            (
                r.period,
                r.principal_id,
                r.good_id,
                r.unit_id,
                r.unmet_quantity,
            )
        }))
    {
        if period != state.period || unmet.insert((principal, good, unit), quantity).is_some() {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
    }
    let mut result = Vec::with_capacity(book.policies.len());
    for policy in &book.policies {
        let cohort = cohorts
            .get(&policy.principal_id)
            .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
        let attendance = attended
            .remove(&policy.principal_id)
            .unwrap_or((policy.labor_unit_id, 0));
        let receipt = close_household(policy, cohort, state.period, attendance, &unmet)?;
        result.push(receipt);
    }
    if !attended.is_empty() {
        return Err(MaterialCircuitError::HouseholdTimeInvariant);
    }
    Ok(result)
}

fn close_household(
    policy: &HouseholdTimePolicy,
    cohort: &HouseholdCohort,
    period: u64,
    (unit, attendance): (UnitId, u64),
    unmet: &BTreeMap<(FinalDemandPrincipalId, GoodId, UnitId), u64>,
) -> Result<HouseholdTimeReceipt> {
    let endowment = multiply(policy.eligible_persons, policy.hours_per_eligible_person)?;
    if unit != policy.labor_unit_id {
        return Err(MaterialCircuitError::HouseholdTimeInvariant);
    }
    let mut available = endowment
        .checked_sub(attendance)
        .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
    let protected = requirement(&policy.protected, cohort)?;
    let protected_allocated = protected.min(available);
    available -= protected_allocated;
    let mut unpaid = requirement(&policy.routine_provisioning, cohort)?;
    for burden in &policy.unmet_burdens {
        let missing = unmet
            .get(&(policy.principal_id, burden.good_id, burden.unit_id))
            .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
        unpaid = sum(&[unpaid, multiply(*missing, burden.hours_per_unmet_unit)?])?;
    }
    let unpaid_allocated = unpaid.min(available);
    available -= unpaid_allocated;
    let receipt = HouseholdTimeReceipt {
        principal_id: policy.principal_id,
        period,
        labor_unit_id: policy.labor_unit_id,
        endowment_hours: endowment,
        attended_hours: attendance,
        protected_hours: protected_allocated,
        protected_unresolved_hours: protected - protected_allocated,
        unpaid_requested_hours: unpaid,
        unpaid_allocated_hours: unpaid_allocated,
        unpaid_unresolved_hours: unpaid - unpaid_allocated,
        contribution_available_hours: available,
    };
    receipt.validate()?;
    Ok(receipt)
}

/// Debit authorized contributions atomically from the last close. Exact retries
/// return the same receipts; shared aliases cannot spend the same hours twice.
/// # Errors
/// Refuses stale periods, missing modeled accounts, reused IDs with changed terms,
/// duplicate admission rows, overdraw, unsupported quantities or overflow.
pub fn consume_household_contributions(
    state: &mut MaterialCircuitState,
    period: u64,
    uses: &[HouseholdContributionUse],
) -> Result<Vec<HouseholdContributionReceipt>> {
    validate(state)?;
    if period.checked_add(1) != Some(state.period) || uses.len() > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::HouseholdTimeInvariant);
    }
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Err(MaterialCircuitError::HouseholdTimeInvariant);
    };
    let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time else {
        return Err(MaterialCircuitError::HouseholdTimeInvariant);
    };
    let mut candidate = book.clone();
    let mut ledger: BTreeMap<_, _> = candidate
        .contributions
        .into_iter()
        .map(|r| (r.contribution.use_id, r))
        .collect();
    let mut seen = BTreeSet::new();
    let mut result = Vec::with_capacity(uses.len());
    for usage in uses {
        if !seen.insert(usage.use_id) {
            return Err(MaterialCircuitError::HouseholdTimeInvariant);
        }
        let receipt = HouseholdContributionReceipt {
            period,
            contribution: usage.clone(),
        };
        match ledger.get(&usage.use_id) {
            Some(existing) if *existing == receipt => {}
            Some(_) => return Err(MaterialCircuitError::HouseholdTimeInvariant),
            None => {
                ledger.insert(usage.use_id, receipt.clone());
            }
        }
        result.push(receipt);
    }
    candidate.contributions = ledger.into_values().collect();
    validate_structure(&candidate)?;
    *book = candidate;
    Ok(result)
}
