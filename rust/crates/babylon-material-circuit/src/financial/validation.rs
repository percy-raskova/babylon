use super::{FinancialInstitutions, PublicTransferTreatment, Result};
use crate::{
    AccountId, CircuitAccounting, MaterialCircuitError, MaterialCircuitState,
    MAX_MATERIAL_CIRCUIT_ROWS,
};
use std::collections::{BTreeMap, BTreeSet};

pub(crate) fn canonicalize(f: &mut FinancialInstitutions) {
    f.locations.sort_by_key(|r| r.account);
    f.ownership
        .sort_by_key(|r| (r.issuer_site_id, r.beneficiary));
    f.distributions.sort_by_key(|r| r.issuer_site_id);
    f.taxes.sort_by_key(|r| r.payer);
    f.public_budgets.sort_by_key(|r| r.public_account);
    f.public_allocations
        .sort_by_key(|r| (r.public_account, r.priority, r.recipient, r.treatment));
    f.contributions.sort_by_key(|r| r.id);
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
    bounded_unique(&f.taxes, crate::MAX_MONETARY_ACCOUNTS, |r| r.payer)?;
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
fn validate_public(f: &FinancialInstitutions, book: &crate::MonetaryBook) -> Result<()> {
    let mut budgets = BTreeSet::new();
    for r in &f.public_budgets {
        book.cash(AccountId::Public(r.public_account))?;
        if r.period_cap.micro_units() < 0 || r.cash_floor.micro_units() < 0 {
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
