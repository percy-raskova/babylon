use super::FinancialInstitutions;
use super::PublicProgramTerms;
use super::PublicSpendingRule;
use super::PublicTransferTreatment;
use super::Result;
use super::{MAX_LAYOFF_HALF_PERIODS, MAX_LAYOFF_PERIODS};
use crate::MonetaryBook;
use crate::{
    AccountId, CircuitAccounting, LaborCompensation, MaterialCircuitError, MaterialCircuitState,
    MonetaryCircuit, MAX_MATERIAL_CIRCUIT_ROWS, MAX_PUBLIC_PROGRAMS, MAX_STAFFING_MEMBERS,
};
use std::collections::{BTreeMap, BTreeSet};

pub(crate) fn canonicalize(f: &mut FinancialInstitutions) {
    f.locations.sort_by_key(|r| r.account);
    f.ownership
        .sort_by_key(|r| (r.issuer_site_id, r.beneficiary));
    f.distributions.sort_by_key(|r| r.issuer_site_id);
    f.taxes
        .sort_by_key(|r| (r.payer, r.basis, r.public_recipient));
    f.public_budgets.sort_by_key(|r| r.public_account);
    f.public_allocations
        .sort_by_key(|r| (r.public_account, r.priority, r.recipient, r.treatment));
    f.contributions.sort_by_key(|r| r.id);
    f.programs.sort_by(|a, b| a.key.cmp(&b.key));
    f.layoffs.sort_by_key(|r| r.member_id);
    for program in &mut f.programs {
        program.recipients.sort();
    }
}
fn unique<T, K: Ord>(rows: &[T], key: impl Fn(&T) -> K) -> Result<()> {
    bounded_unique(rows, MAX_MATERIAL_CIRCUIT_ROWS, key)
}
fn bounded_unique<T, K: Ord>(rows: &[T], limit: usize, key: impl Fn(&T) -> K) -> Result<()> {
    if rows.len() > limit {
        return Err(MaterialCircuitError::RowLimit);
    }
    let mut keys = BTreeSet::new();
    if rows.iter().any(|r| !keys.insert(key(r))) {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    Ok(())
}
fn structure(f: &FinancialInstitutions) -> Result<()> {
    unique(&f.locations, |r| r.account)?;
    bounded_unique(&f.ownership, crate::MAX_OWNERSHIP_CLAIMS, |r| {
        (r.issuer_site_id, r.beneficiary)
    })?;
    unique(&f.distributions, |r| r.issuer_site_id)?;
    bounded_unique(&f.taxes, crate::MAX_TAX_POLICIES, |r| {
        (r.payer, r.basis, r.public_recipient)
    })?;
    unique(&f.public_budgets, |r| r.public_account)?;
    unique(&f.public_allocations, |r| {
        (r.public_account, r.recipient, r.treatment)
    })?;
    unique(&f.contributions, |r| r.id)
}
pub(crate) fn validate(state: &MaterialCircuitState) -> Result<()> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(());
    };
    let f = &e.financial;
    structure(f)?;
    let snapshot = e.book.snapshot();
    let institutions: BTreeSet<_> = snapshot
        .accounts
        .iter()
        .filter_map(|r| {
            matches!(r.id, AccountId::Organization(_) | AccountId::Public(_)).then_some(r.id)
        })
        .collect();
    if institutions != f.locations.iter().map(|r| r.account).collect() {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    let mut shares = BTreeMap::new();
    let mut claims = BTreeSet::new();
    for r in &f.ownership {
        e.book.cash(AccountId::Site(r.issuer_site_id))?;
        e.book.cash(r.beneficiary)?;
        if r.shares == 0 || r.beneficiary == AccountId::Site(r.issuer_site_id) {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        let total = shares.entry(r.issuer_site_id).or_insert(0_u64);
        *total = total
            .checked_add(r.shares)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        claims.insert((r.beneficiary, r.issuer_site_id));
    }
    let companies: BTreeSet<_> = snapshot
        .accounts
        .iter()
        .filter_map(|r| match r.id {
            AccountId::Company(id) => Some(id),
            _ => None,
        })
        .collect();
    let mut subsidiaries = BTreeSet::new();
    let mut parents = BTreeSet::new();
    for claim in &f.ownership {
        if let AccountId::Company(id) = claim.beneficiary {
            if shares[&claim.issuer_site_id] != claim.shares
                || !subsidiaries.insert(claim.issuer_site_id)
            {
                return Err(MaterialCircuitError::FinancialInvariant);
            }
            parents.insert(id);
        }
    }
    if parents != companies {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    if claims
        != e.costs
            .snapshot()
            .equity
            .iter()
            .map(|r| (r.owner, r.issuer_site_id))
            .collect()
    {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    for r in &f.distributions {
        if !shares.contains_key(&r.issuer_site_id)
            || r.earnings_fraction_bps > 10_000
            || r.period_cap.micro_units() < 0
            || r.cash_floor.micro_units() < 0
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
    }
    validate_public(f, &e.book)?;
    validate_programs(state, f)?;
    for r in &f.contributions {
        if r.due_period < state.period
            || r.amount.micro_units() <= 0
            || !claims.contains(&(r.contributor, r.issuer_site_id))
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
    }
    Ok(())
}
fn validate_public(f: &FinancialInstitutions, book: &MonetaryBook) -> Result<()> {
    let mut budgets = BTreeSet::new();
    for r in &f.public_budgets {
        book.cash(AccountId::Public(r.public_account))?;
        // A budget in proportion does not read its cap, so a cap is refused, never ignored.
        if r.period_cap.micro_units() < 0
            || r.cash_floor.micro_units() < 0
            || (r.rule == PublicSpendingRule::CashInProportion && r.period_cap.micro_units() != 0)
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        budgets.insert(r.public_account);
    }
    for r in &f.public_allocations {
        book.cash(r.recipient)?;
        let valid = matches!(
            (r.treatment, r.recipient),
            (
                PublicTransferTreatment::HouseholdIncomeSupport,
                AccountId::Household(_)
            ) | (
                PublicTransferTreatment::ProviderOperatingGrant,
                AccountId::Site(_)
            ) | (
                PublicTransferTreatment::AgencyAppropriation,
                AccountId::Organization(_)
            )
        );
        if !valid || !budgets.contains(&r.public_account) || r.amount_per_period.micro_units() <= 0
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
    }
    for r in &f.taxes {
        book.cash(r.payer)?;
        book.cash(AccountId::Public(r.public_recipient))?;
        if r.payer == AccountId::Public(r.public_recipient)
            || r.rate_bps > 10_000
            || r.cash_floor.micro_units() < 0
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
    }
    Ok(())
}
/// Keys unique, payer in proportion, recipients household accounts; per person, each with a cohort.
fn validate_programs(state: &MaterialCircuitState, f: &FinancialInstitutions) -> Result<()> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(());
    };
    let invalid = MaterialCircuitError::PublicProgramInvariant;
    if f.programs.len() > MAX_PUBLIC_PROGRAMS {
        return Err(invalid);
    }
    let mut keys = BTreeSet::new();
    let mut after_layoff = BTreeSet::new();
    let mut recipients = 0_usize;
    for program in &f.programs {
        let in_proportion = f.public_budgets.iter().any(|b| {
            b.public_account == program.payer && b.rule == PublicSpendingRule::CashInProportion
        });
        let mut seen = BTreeSet::new();
        recipients = recipients.saturating_add(program.recipients.len());
        if !keys.insert(&program.key)
            || !in_proportion
            || program.recipients.is_empty()
            || program.recipients.iter().any(|r| !seen.insert(*r))
            || program
                .recipients
                .iter()
                .any(|r| e.book.cash(AccountId::Household(*r)).is_err())
        {
            return Err(invalid);
        }
        match program.terms {
            PublicProgramTerms::PerPerson { amount_per_person } => {
                let cohorts = e.recurring.as_ref().map(|r| &r.households);
                if amount_per_person.micro_units() <= 0
                    || program
                        .recipients
                        .iter()
                        .any(|r| !cohorts.is_some_and(|c| c.iter().any(|h| h.principal_id == *r)))
                {
                    return Err(invalid);
                }
            }
            PublicProgramTerms::AfterLayoff {
                wage_share_bps,
                half_periods,
            } => {
                // A household is a recipient of at most one program of this kind.
                if !(1..=10_000).contains(&wage_share_bps)
                    || !(1..=MAX_LAYOFF_HALF_PERIODS).contains(&half_periods)
                    || program.recipients.iter().any(|r| !after_layoff.insert(*r))
                {
                    return Err(invalid);
                }
            }
        }
    }
    if recipients > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(invalid);
    }
    validate_layoffs(e, f)
}
/// Records unique and sorted by member, each of a member with a wage: a schedule, one to thirteen
/// cohorts, the last not 0. A record whose payee is no longer a recipient is valid and owed nothing,
/// so a change of programs never makes the state unreadable.
fn validate_layoffs(e: &MonetaryCircuit, f: &FinancialInstitutions) -> Result<()> {
    let invalid = MaterialCircuitError::PublicProgramInvariant;
    if f.layoffs.len() > MAX_STAFFING_MEMBERS {
        return Err(invalid);
    }
    let mut members = BTreeSet::new();
    for record in &f.layoffs {
        let paid = e.employment.iter().any(|t| {
            t.member_id == record.member_id && matches!(t.compensation, LaborCompensation::Wage(_))
        });
        if !paid
            || record.hours_per_person == 0
            || !(1..=MAX_LAYOFF_PERIODS).contains(&record.cohorts.len())
            || record.cohorts.last() == Some(&0)
            || !members.insert(record.member_id)
        {
            return Err(invalid);
        }
    }
    if f.layoffs
        .windows(2)
        .any(|w| w[0].member_id > w[1].member_id)
    {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    Ok(())
}
