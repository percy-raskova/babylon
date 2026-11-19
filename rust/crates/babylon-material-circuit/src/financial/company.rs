//! Frozen parent budgets and exact ultimate distributions.
use super::{CompanyDistributionReceipt, CompanyPayoutPolicy, Result};
use crate::valuation::CostClose;
use crate::{
    AccountId, CashTransferPurpose, CompanyId, MaterialCatalog, MaterialCircuitError,
    MonetaryCircuit, MoneyTransferReceipt,
};
use babylon_kernel::currency::Currency;
use std::collections::{BTreeMap, BTreeSet};

pub(crate) fn validate_company_policy(rows: &[CompanyPayoutPolicy]) -> Result<()> {
    let mut count = 0_usize;
    if rows.windows(2).any(|p| p[0].company >= p[1].company) {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    for row in rows {
        count = count
            .checked_add(row.claims.len())
            .ok_or(MaterialCircuitError::RowLimit)?;
        if count > crate::MAX_OWNERSHIP_CLAIMS
            || row.claims.is_empty()
            || row.earnings_bps > 10_000
            || row.claims.windows(2).any(|p| p[0].0 >= p[1].0)
            || row
                .claims
                .iter()
                .any(|&(id, w)| w == 0 || matches!(id, AccountId::Company(_)))
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        total_weight(&row.claims)?;
    }
    Ok(())
}
fn total_weight(claims: &[(AccountId, u128)]) -> Result<u128> {
    claims.iter().try_fold(0_u128, |acc, (_, weight)| {
        acc.checked_add(*weight)
            .ok_or(MaterialCircuitError::Arithmetic)
    })
}
pub(crate) fn validate_company_accounts(
    catalog: &MaterialCatalog,
    e: &MonetaryCircuit,
) -> Result<()> {
    let expected: BTreeSet<_> = catalog.company_payouts.iter().map(|r| r.company).collect();
    let actual: BTreeSet<_> = e
        .book
        .cash_accounts()
        .filter_map(|(&id, _)| match id {
            AccountId::Company(c) => Some(c),
            _ => None,
        })
        .collect();
    if expected != actual {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    for terms in &catalog.company_payouts {
        for &(owner, _) in &terms.claims {
            e.book.cash(owner)?;
        }
    }
    Ok(())
}
pub(super) fn pay(
    catalog: &MaterialCatalog,
    period: u64,
    e: &mut MonetaryCircuit,
    costs: &mut CostClose,
    movements: &mut Vec<MoneyTransferReceipt>,
) -> Result<Vec<CompanyDistributionReceipt>> {
    if catalog.company_payouts.is_empty() {
        return Ok(Vec::new());
    }
    let mut commitments = BTreeMap::<CompanyId, Currency>::new();
    for order in &e.financial.contributions {
        if let AccountId::Company(id) = order.contributor {
            let reserved = commitments.entry(id).or_insert_with(super::zero);
            *reserved = super::add(*reserved, order.amount)?;
        }
    }
    let mut receipts = Vec::new();
    // Take every issuer's budget before either tier credits a beneficiary.
    for policy in &catalog.company_payouts {
        let payer = AccountId::Company(policy.company);
        let eligible = costs.eligible_earnings(payer)?;
        let protected = commitments
            .get(&policy.company)
            .copied()
            .unwrap_or_else(super::zero);
        let declared = super::fraction(eligible, u64::from(policy.earnings_bps), 10_000)?
            .min(super::available(e.book.cash(payer)?, protected)?);
        let total = total_weight(&policy.claims)?;
        let start = receipts.len();
        let mut unallocated = declared;
        for &(beneficiary, weight) in &policy.claims {
            let paid = declared
                .floor_weighted_share(weight, total)
                .ok_or(MaterialCircuitError::FinancialInvariant)?;
            unallocated = super::sub(unallocated, paid)?;
            receipts.push(CompanyDistributionReceipt {
                period,
                company: policy.company,
                beneficiary,
                weight,
                total_weight: total,
                eligible_earnings: eligible,
                protected_contributions: protected,
                declared,
                paid,
            });
        }
        let residual = usize::try_from(unallocated.micro_units())
            .map_err(|_| MaterialCircuitError::Arithmetic)?;
        for row in receipts[start..]
            .get_mut(..residual)
            .ok_or(MaterialCircuitError::FinancialInvariant)?
        {
            row.paid = super::add(row.paid, Currency::from_micro_units(1))?;
        }
    }
    for row in &receipts {
        if row.paid.micro_units() > 0 {
            let payer = AccountId::Company(row.company);
            movements.push(e.book.transfer_cash(
                payer,
                row.beneficiary,
                row.paid,
                CashTransferPurpose::OwnershipDistribution,
            )?);
            costs.distribution(payer, row.beneficiary, row.paid)?;
        }
    }
    Ok(receipts)
}

/// Authenticate canonical company group totals and the exact stable micro-unit residual.
/// # Errors
/// Refuses duplicate beneficiaries, inconsistent issuer budgets or altered weights or amounts.
pub fn validate_company_distributions(rows: &[CompanyDistributionReceipt]) -> Result<()> {
    if rows.len() > crate::MAX_OWNERSHIP_CLAIMS
        || rows
            .windows(2)
            .any(|p| (p[0].company, p[0].beneficiary) >= (p[1].company, p[1].beneficiary))
    {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    for group in rows.chunk_by(|a, b| a.company == b.company) {
        let first = &group[0];
        if first.period == 0
            || first.declared.micro_units() < 0
            || first.eligible_earnings < first.declared
            || first.protected_contributions.micro_units() < 0
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        let mut weight = 0_u128;
        let mut rest = first.declared;
        let mut floors = Vec::with_capacity(group.len());
        for row in group {
            if (
                row.period,
                row.eligible_earnings,
                row.protected_contributions,
                row.declared,
                row.total_weight,
            ) != (
                first.period,
                first.eligible_earnings,
                first.protected_contributions,
                first.declared,
                first.total_weight,
            ) || row.weight == 0
                || matches!(row.beneficiary, AccountId::Company(_))
            {
                return Err(MaterialCircuitError::FinancialInvariant);
            }
            weight = weight
                .checked_add(row.weight)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            let floor = first
                .declared
                .floor_weighted_share(row.weight, first.total_weight)
                .ok_or(MaterialCircuitError::FinancialInvariant)?;
            rest = super::sub(rest, floor)?;
            floors.push(floor);
        }
        let residual = usize::try_from(rest.micro_units())
            .map_err(|_| MaterialCircuitError::FinancialInvariant)?;
        if weight != first.total_weight || residual >= group.len() {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        for (index, (row, floor)) in group.iter().zip(floors).enumerate() {
            if row.paid
                != super::add(
                    floor,
                    Currency::from_micro_units(i128::from(index < residual)),
                )?
            {
                return Err(MaterialCircuitError::FinancialInvariant);
            }
        }
    }
    Ok(())
}
