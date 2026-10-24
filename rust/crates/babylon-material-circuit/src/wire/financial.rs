//! Canonical financial institutions, eligibility, finite instructions and budgets.
use super::accounting;
use super::Cursor;
use crate::{
    CapitalContributionOrder, ContributionId, DistributionPolicy, FinancialInstitutions,
    InstitutionLocation, MaterialCircuitError, OwnershipClaim, PublicAccountId, PublicAllocation,
    PublicBudget, PublicTransferTreatment, SiteId, TaxBasis, TaxPolicy,
};
use babylon_kernel::economic_location::EconomicLocation;
use std::result::Result as StdResult;
type Result<T> = StdResult<T, MaterialCircuitError>;

pub(super) fn append(out: &mut Vec<u8>, f: &FinancialInstitutions) -> Result<()> {
    append_locations(out, &f.locations)?;
    append_ownership(out, &f.ownership)?;
    append_distributions(out, &f.distributions)?;
    append_taxes(out, &f.taxes)?;
    append_public_budgets(out, &f.public_budgets)?;
    append_public_allocations(out, &f.public_allocations)?;
    append_contributions(out, &f.contributions)?;
    Ok(())
}
pub(super) fn decode(c: &mut Cursor<'_>) -> Result<FinancialInstitutions> {
    Ok(FinancialInstitutions {
        locations: decode_locations(c)?,
        ownership: decode_ownership(c)?,
        distributions: decode_distributions(c)?,
        taxes: decode_taxes(c)?,
        public_budgets: decode_public_budgets(c)?,
        public_allocations: decode_public_allocations(c)?,
        contributions: decode_contributions(c)?,
    })
}
fn append_locations(out: &mut Vec<u8>, rows: &[InstitutionLocation]) -> Result<()> {
    super::append_rows(out, rows, |b, r| {
        accounting::append_account(b, r.account);
        b.extend_from_slice(&r.location.canonical_bytes());
    })
}
fn decode_locations(c: &mut Cursor<'_>) -> Result<Vec<InstitutionLocation>> {
    let rows = super::decode_rows(c, |b| {
        Ok(InstitutionLocation {
            account: accounting::decode_account(b)?,
            location: EconomicLocation::from_canonical_bytes(b.array()?)
                .map_err(|_| MaterialCircuitError::WireEnum)?,
        })
    })?;
    accounting::ordered_rows(&rows, |r| r.account)?;
    Ok(rows)
}
fn append_ownership(out: &mut Vec<u8>, rows: &[OwnershipClaim]) -> Result<()> {
    super::append_bounded_rows(out, rows, crate::MAX_OWNERSHIP_CLAIMS, |b, r| {
        b.extend_from_slice(&r.issuer_site_id.as_bytes());
        accounting::append_account(b, r.beneficiary);
        b.extend_from_slice(&r.shares.to_be_bytes());
    })
}
fn decode_ownership(c: &mut Cursor<'_>) -> Result<Vec<OwnershipClaim>> {
    let rows = super::decode_bounded_rows(c, crate::MAX_OWNERSHIP_CLAIMS, |b| {
        Ok(OwnershipClaim {
            issuer_site_id: SiteId::from_bytes(b.array()?),
            beneficiary: accounting::decode_account(b)?,
            shares: b.u64()?,
        })
    })?;
    accounting::ordered_rows(&rows, |r| (r.issuer_site_id, r.beneficiary))?;
    Ok(rows)
}
fn append_distributions(out: &mut Vec<u8>, rows: &[DistributionPolicy]) -> Result<()> {
    super::append_rows(out, rows, |b, r| {
        b.extend_from_slice(&r.issuer_site_id.as_bytes());
        b.extend_from_slice(&r.earnings_fraction_bps.to_be_bytes());
        b.extend_from_slice(&r.period_cap.micro_units().to_be_bytes());
        b.extend_from_slice(&r.cash_floor.micro_units().to_be_bytes());
    })
}
fn decode_distributions(c: &mut Cursor<'_>) -> Result<Vec<DistributionPolicy>> {
    let rows = super::decode_rows(c, |b| {
        Ok(DistributionPolicy {
            issuer_site_id: SiteId::from_bytes(b.array()?),
            earnings_fraction_bps: b.u16()?,
            period_cap: accounting::decode_currency(b)?,
            cash_floor: accounting::decode_currency(b)?,
        })
    })?;
    accounting::ordered_rows(&rows, |r| r.issuer_site_id)?;
    Ok(rows)
}
fn append_taxes(out: &mut Vec<u8>, rows: &[TaxPolicy]) -> Result<()> {
    super::append_bounded_rows(out, rows, crate::MAX_MONETARY_ACCOUNTS, |b, r| {
        accounting::append_account(b, r.payer);
        b.extend_from_slice(&r.public_recipient.as_bytes());
        b.push(r.basis as u8);
        b.extend_from_slice(&r.rate_bps.to_be_bytes());
        b.extend_from_slice(&r.cash_floor.micro_units().to_be_bytes());
    })
}
fn decode_taxes(c: &mut Cursor<'_>) -> Result<Vec<TaxPolicy>> {
    let rows = super::decode_bounded_rows(c, crate::MAX_MONETARY_ACCOUNTS, |b| {
        Ok(TaxPolicy {
            payer: accounting::decode_account(b)?,
            public_recipient: PublicAccountId::from_bytes(b.array()?),
            basis: match b.u8()? {
                1 => TaxBasis::WageIncome,
                2 => TaxBasis::PositiveOperatingIncome,
                _ => return Err(MaterialCircuitError::WireEnum),
            },
            rate_bps: b.u16()?,
            cash_floor: accounting::decode_currency(b)?,
        })
    })?;
    accounting::ordered_rows(&rows, |r| r.payer)?;
    Ok(rows)
}
fn append_public_budgets(out: &mut Vec<u8>, rows: &[PublicBudget]) -> Result<()> {
    super::append_rows(out, rows, |b, r| {
        b.extend_from_slice(&r.public_account.as_bytes());
        b.extend_from_slice(&r.period_cap.micro_units().to_be_bytes());
        b.extend_from_slice(&r.cash_floor.micro_units().to_be_bytes());
    })
}
fn decode_public_budgets(c: &mut Cursor<'_>) -> Result<Vec<PublicBudget>> {
    let rows = super::decode_rows(c, |b| {
        Ok(PublicBudget {
            public_account: PublicAccountId::from_bytes(b.array()?),
            period_cap: accounting::decode_currency(b)?,
            cash_floor: accounting::decode_currency(b)?,
        })
    })?;
    accounting::ordered_rows(&rows, |r| r.public_account)?;
    Ok(rows)
}
fn append_public_allocations(out: &mut Vec<u8>, rows: &[PublicAllocation]) -> Result<()> {
    super::append_rows(out, rows, |b, r| {
        b.extend_from_slice(&r.public_account.as_bytes());
        accounting::append_account(b, r.recipient);
        b.push(r.treatment as u8);
        b.extend_from_slice(&r.priority.to_be_bytes());
        b.extend_from_slice(&r.amount_per_period.micro_units().to_be_bytes());
    })
}
fn decode_public_allocations(c: &mut Cursor<'_>) -> Result<Vec<PublicAllocation>> {
    let rows = super::decode_rows(c, |b| {
        Ok(PublicAllocation {
            public_account: PublicAccountId::from_bytes(b.array()?),
            recipient: accounting::decode_account(b)?,
            treatment: match b.u8()? {
                1 => PublicTransferTreatment::HouseholdIncomeSupport,
                2 => PublicTransferTreatment::ProviderOperatingGrant,
                _ => return Err(MaterialCircuitError::WireEnum),
            },
            priority: b.u32()?,
            amount_per_period: accounting::decode_currency(b)?,
        })
    })?;
    accounting::ordered_rows(&rows, |r| {
        (r.public_account, r.priority, r.recipient, r.treatment)
    })?;
    Ok(rows)
}
fn append_contributions(out: &mut Vec<u8>, rows: &[CapitalContributionOrder]) -> Result<()> {
    super::append_rows(out, rows, |b, r| {
        b.extend_from_slice(&r.id.as_bytes());
        b.extend_from_slice(&r.due_period.to_be_bytes());
        accounting::append_account(b, r.contributor);
        b.extend_from_slice(&r.issuer_site_id.as_bytes());
        b.extend_from_slice(&r.amount.micro_units().to_be_bytes());
    })
}
fn decode_contributions(c: &mut Cursor<'_>) -> Result<Vec<CapitalContributionOrder>> {
    let rows = super::decode_rows(c, |b| {
        Ok(CapitalContributionOrder {
            id: ContributionId::from_bytes(b.array()?),
            due_period: b.u64()?,
            contributor: accounting::decode_account(b)?,
            issuer_site_id: SiteId::from_bytes(b.array()?),
            amount: accounting::decode_currency(b)?,
        })
    })?;
    accounting::ordered_rows(&rows, |r| r.id)?;
    Ok(rows)
}
