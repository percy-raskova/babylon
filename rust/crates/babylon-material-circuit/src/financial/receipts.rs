use super::{
    add, fraction, zero, CapitalContributionReceipt, DistributionReceipt, PublicBudgetReceipt,
    PublicTransferTreatment, Result, TaxReceipt,
};
use crate::{AccountId, MaterialCircuitError};
use babylon_kernel::currency::Currency;
fn partition(period: u64, requested: Currency, paid: Currency, unfunded: Currency) -> Result<()> {
    if period == 0
        || requested.micro_units() <= 0
        || paid.micro_units() < 0
        || unfunded.micro_units() < 0
        || requested != add(paid, unfunded)?
    {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    Ok(())
}
impl PublicBudgetReceipt {
    /// Check the partition this standalone receipt proves, without absent policy state.
    /// # Errors
    /// Refuses invalid parties, treatment, period or funding amounts.
    pub fn validate(&self) -> Result<()> {
        partition(self.period, self.requested, self.paid, self.unfunded)?;
        if !matches!(
            (self.treatment, self.recipient),
            (
                PublicTransferTreatment::HouseholdIncomeSupport,
                AccountId::Household(_)
            ) | (
                PublicTransferTreatment::ProviderOperatingGrant,
                AccountId::Site(_)
            )
        ) {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        Ok(())
    }
}
impl CapitalContributionReceipt {
    /// # Errors
    /// Refuses self-contribution or a malformed finite funding partition.
    pub fn validate(&self) -> Result<()> {
        partition(self.period, self.requested, self.paid, self.unfunded)?;
        if self.contributor == AccountId::Site(self.issuer_site_id) {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        Ok(())
    }
}
impl TaxReceipt {
    /// # Errors
    /// Refuses invalid assessment arithmetic, parties, rates or cash partition.
    pub fn validate(&self) -> Result<()> {
        if self.period == 0
            || self.payer == AccountId::Public(self.public_recipient)
            || self.rate_bps > 10_000
            || self.taxable_amount < zero()
            || self.collected < zero()
            || self.uncollected < zero()
            || self.assessed != add(self.collected, self.uncollected)?
            || self.assessed != fraction(self.taxable_amount, u64::from(self.rate_bps), 10_000)?
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        Ok(())
    }
}
impl DistributionReceipt {
    /// # Errors
    /// Refuses malformed shares, negative money or payment above declared earnings.
    pub fn validate(&self) -> Result<()> {
        if self.period == 0
            || self.beneficiary == AccountId::Site(self.issuer_site_id)
            || self.shares == 0
            || self.shares > self.total_shares
            || self.eligible_earnings < zero()
            || self.declared_total < zero()
            || self.declared_total > self.eligible_earnings
            || self.paid < zero()
            || self.paid > self.declared_total
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        Ok(())
    }
}
/// Validate complete canonical issuer groups and exact stable remainder allocation.
/// # Errors
/// Refuses duplicate keys, inconsistent group totals, or an incorrect share split.
pub fn validate_distribution_receipts(rows: &[DistributionReceipt]) -> Result<()> {
    if rows
        .windows(2)
        .any(|r| (r[0].issuer_site_id, r[0].beneficiary) >= (r[1].issuer_site_id, r[1].beneficiary))
    {
        return Err(MaterialCircuitError::WireNoncanonical);
    }
    let mut start = 0;
    while start < rows.len() {
        let first = &rows[start];
        let end =
            start + rows[start..].partition_point(|r| r.issuer_site_id == first.issuer_site_id);
        let group = &rows[start..end];
        let mut shares = 0_u64;
        let mut floors = zero();
        for r in group {
            r.validate()?;
            if (
                r.period,
                r.total_shares,
                r.eligible_earnings,
                r.declared_total,
            ) != (
                first.period,
                first.total_shares,
                first.eligible_earnings,
                first.declared_total,
            ) {
                return Err(MaterialCircuitError::FinancialInvariant);
            }
            shares = shares
                .checked_add(r.shares)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            floors = add(
                floors,
                fraction(r.declared_total, r.shares, r.total_shares)?,
            )?;
        }
        if shares != first.total_shares {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        let mut remainder = super::sub(first.declared_total, floors)?.micro_units();
        for r in group {
            let extra = i128::from(remainder > 0);
            remainder -= extra;
            let expected = add(
                fraction(r.declared_total, r.shares, r.total_shares)?,
                Currency::from_micro_units(extra),
            )?;
            if r.paid != expected {
                return Err(MaterialCircuitError::FinancialInvariant);
            }
        }
        if remainder != 0 {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        start = end;
    }
    Ok(())
}
