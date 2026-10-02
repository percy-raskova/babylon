//! Authenticated public/ownership evidence and matched cash postings.
use super::{
    monetary_receipt::{account, account_parts},
    MaterialWorldError, ReceiptCursor,
};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    validate_distribution_receipts, AccountId, CapitalContributionReceipt, CashTransferPurpose,
    ContributionId, DistributionReceipt, MoneyLocation, MoneyTransferPurpose, MoneyTransferReceipt,
    PublicAccountId, PublicBudgetReceipt, PublicTransferTreatment, SiteId, TaxBasis, TaxReceipt,
};
use std::collections::{BTreeMap, BTreeSet};
type Result<T> = std::result::Result<T, MaterialWorldError>;
fn write_account(out: &mut Vec<u8>, id: AccountId) {
    let (tag, bytes) = account_parts(id);
    out.push(tag);
    out.extend_from_slice(&bytes);
}
fn read_account(c: &mut ReceiptCursor<'_>) -> Result<AccountId> {
    let [tag] = c.take()?;
    account(tag, c.take()?)
}
fn money(c: &mut ReceiptCursor<'_>) -> Result<Currency> {
    Ok(Currency::from_micro_units(i128::from_be_bytes(c.take()?)))
}

pub(super) const PUBLIC_BUDGETS_BYTES: usize = 126;
pub(super) fn encode_public_budgets(
    rows: &[PublicBudgetReceipt],
    tick: u64,
    out: &mut Vec<u8>,
) -> Result<()> {
    for r in rows {
        r.validate().map_err(|_| MaterialWorldError::Wire)?;
        if r.period != tick {
            return Err(MaterialWorldError::Wire);
        }
        out.extend_from_slice(&r.period.to_be_bytes());
        out.extend_from_slice(&r.public_account.as_bytes());
        write_account(out, r.recipient);
        out.push(r.treatment as u8);
        out.extend_from_slice(&r.priority.to_be_bytes());
        out.extend_from_slice(&r.requested.micro_units().to_be_bytes());
        out.extend_from_slice(&r.paid.micro_units().to_be_bytes());
        out.extend_from_slice(&r.unfunded.micro_units().to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode_public_budgets(
    c: &mut ReceiptCursor<'_>,
    tick: u64,
) -> Result<PublicBudgetReceipt> {
    let r = PublicBudgetReceipt {
        period: c.u64()?,
        public_account: PublicAccountId::from_bytes(c.take()?),
        recipient: read_account(c)?,
        treatment: match c.take::<1>()? {
            [1] => PublicTransferTreatment::HouseholdIncomeSupport,
            [2] => PublicTransferTreatment::ProviderOperatingGrant,
            _ => return Err(MaterialWorldError::Wire),
        },
        priority: u32::from_be_bytes(c.take()?),
        requested: money(c)?,
        paid: money(c)?,
        unfunded: money(c)?,
    };
    r.validate().map_err(|_| MaterialWorldError::Wire)?;
    if r.period != tick {
        return Err(MaterialWorldError::Wire);
    }
    Ok(r)
}
pub(super) const TAXES_BYTES: usize = 140;
pub(super) fn encode_taxes(rows: &[TaxReceipt], tick: u64, out: &mut Vec<u8>) -> Result<()> {
    for r in rows {
        r.validate().map_err(|_| MaterialWorldError::Wire)?;
        if r.period != tick {
            return Err(MaterialWorldError::Wire);
        }
        out.extend_from_slice(&r.period.to_be_bytes());
        write_account(out, r.payer);
        out.extend_from_slice(&r.public_recipient.as_bytes());
        out.push(r.basis as u8);
        out.extend_from_slice(&r.rate_bps.to_be_bytes());
        out.extend_from_slice(&r.taxable_amount.micro_units().to_be_bytes());
        out.extend_from_slice(&r.assessed.micro_units().to_be_bytes());
        out.extend_from_slice(&r.collected.micro_units().to_be_bytes());
        out.extend_from_slice(&r.uncollected.micro_units().to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode_taxes(c: &mut ReceiptCursor<'_>, tick: u64) -> Result<TaxReceipt> {
    let r = TaxReceipt {
        period: c.u64()?,
        payer: read_account(c)?,
        public_recipient: PublicAccountId::from_bytes(c.take()?),
        basis: match c.take::<1>()? {
            [1] => TaxBasis::WageIncome,
            [2] => TaxBasis::PositiveOperatingIncome,
            _ => return Err(MaterialWorldError::Wire),
        },
        rate_bps: u16::from_be_bytes(c.take()?),
        taxable_amount: money(c)?,
        assessed: money(c)?,
        collected: money(c)?,
        uncollected: money(c)?,
    };
    r.validate().map_err(|_| MaterialWorldError::Wire)?;
    if r.period != tick {
        return Err(MaterialWorldError::Wire);
    }
    Ok(r)
}
pub(super) const DISTRIBUTIONS_BYTES: usize = 137;
pub(super) fn encode_distributions(
    rows: &[DistributionReceipt],
    tick: u64,
    out: &mut Vec<u8>,
) -> Result<()> {
    for r in rows {
        r.validate().map_err(|_| MaterialWorldError::Wire)?;
        if r.period != tick {
            return Err(MaterialWorldError::Wire);
        }
        out.extend_from_slice(&r.period.to_be_bytes());
        out.extend_from_slice(&r.issuer_site_id.as_bytes());
        write_account(out, r.beneficiary);
        out.extend_from_slice(&r.shares.to_be_bytes());
        out.extend_from_slice(&r.total_shares.to_be_bytes());
        out.extend_from_slice(&r.eligible_earnings.micro_units().to_be_bytes());
        out.extend_from_slice(&r.declared_total.micro_units().to_be_bytes());
        out.extend_from_slice(&r.paid.micro_units().to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode_distributions(
    c: &mut ReceiptCursor<'_>,
    tick: u64,
) -> Result<DistributionReceipt> {
    let r = DistributionReceipt {
        period: c.u64()?,
        issuer_site_id: SiteId::from_bytes(c.take()?),
        beneficiary: read_account(c)?,
        shares: c.u64()?,
        total_shares: c.u64()?,
        eligible_earnings: money(c)?,
        declared_total: money(c)?,
        paid: money(c)?,
    };
    r.validate().map_err(|_| MaterialWorldError::Wire)?;
    if r.period != tick {
        return Err(MaterialWorldError::Wire);
    }
    Ok(r)
}
pub(super) const CONTRIBUTIONS_BYTES: usize = 153;
pub(super) fn encode_contributions(
    rows: &[CapitalContributionReceipt],
    tick: u64,
    out: &mut Vec<u8>,
) -> Result<()> {
    for r in rows {
        r.validate().map_err(|_| MaterialWorldError::Wire)?;
        if r.period != tick {
            return Err(MaterialWorldError::Wire);
        }
        out.extend_from_slice(&r.period.to_be_bytes());
        out.extend_from_slice(&r.id.as_bytes());
        write_account(out, r.contributor);
        out.extend_from_slice(&r.issuer_site_id.as_bytes());
        out.extend_from_slice(&r.requested.micro_units().to_be_bytes());
        out.extend_from_slice(&r.paid.micro_units().to_be_bytes());
        out.extend_from_slice(&r.unfunded.micro_units().to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode_contributions(
    c: &mut ReceiptCursor<'_>,
    tick: u64,
) -> Result<CapitalContributionReceipt> {
    let r = CapitalContributionReceipt {
        period: c.u64()?,
        id: ContributionId::from_bytes(c.take()?),
        contributor: read_account(c)?,
        issuer_site_id: SiteId::from_bytes(c.take()?),
        requested: money(c)?,
        paid: money(c)?,
        unfunded: money(c)?,
    };
    r.validate().map_err(|_| MaterialWorldError::Wire)?;
    if r.period != tick {
        return Err(MaterialWorldError::Wire);
    }
    Ok(r)
}

fn ordered<T, K: Ord>(rows: &[T], key: impl Fn(&T) -> K) -> Result<()> {
    if rows.windows(2).any(|r| key(&r[0]) >= key(&r[1])) {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}
type PostingTotals = BTreeMap<(u8, AccountId, AccountId), Currency>;
fn accumulate(
    totals: &mut PostingTotals,
    key: (u8, AccountId, AccountId),
    amount: Currency,
) -> Result<()> {
    if amount.micro_units() == 0 {
        return Ok(());
    }
    if amount.micro_units() < 0 {
        return Err(MaterialWorldError::Wire);
    }
    let entry = totals.entry(key).or_insert(Currency::from_micro_units(0));
    *entry = entry
        .checked_add(amount)
        .map_err(|_| MaterialWorldError::Wire)?;
    Ok(())
}
pub(super) fn validate(
    public: &[PublicBudgetReceipt],
    taxes: &[TaxReceipt],
    distributions: &[DistributionReceipt],
    contributions: &[CapitalContributionReceipt],
    money: &[MoneyTransferReceipt],
) -> Result<()> {
    ordered(public, |r| {
        (r.public_account, r.priority, r.recipient, r.treatment)
    })?;
    let mut identities = BTreeSet::new();
    if public
        .iter()
        .any(|r| !identities.insert((r.public_account, r.recipient, r.treatment)))
    {
        return Err(MaterialWorldError::Wire);
    }
    ordered(taxes, |r| r.payer)?;
    ordered(contributions, |r| r.id)?;
    validate_distribution_receipts(distributions).map_err(|_| MaterialWorldError::Wire)?;
    let mut expected = PostingTotals::new();
    for r in public {
        accumulate(
            &mut expected,
            (1, AccountId::Public(r.public_account), r.recipient),
            r.paid,
        )?;
    }
    for r in taxes {
        accumulate(
            &mut expected,
            (2, r.payer, AccountId::Public(r.public_recipient)),
            r.collected,
        )?;
    }
    for r in distributions {
        accumulate(
            &mut expected,
            (3, AccountId::Site(r.issuer_site_id), r.beneficiary),
            r.paid,
        )?;
    }
    for r in contributions {
        accumulate(
            &mut expected,
            (4, r.contributor, AccountId::Site(r.issuer_site_id)),
            r.paid,
        )?;
    }
    let actual = actual_postings(money)?;
    if actual != expected {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}
fn actual_postings(money: &[MoneyTransferReceipt]) -> Result<PostingTotals> {
    let mut actual = PostingTotals::new();
    for r in money {
        let tag = match r.purpose {
            MoneyTransferPurpose::Cash(CashTransferPurpose::PublicTransfer) => 1,
            MoneyTransferPurpose::Cash(CashTransferPurpose::Tax) => 2,
            MoneyTransferPurpose::Cash(CashTransferPurpose::OwnershipDistribution) => 3,
            MoneyTransferPurpose::Cash(CashTransferPurpose::CapitalContribution) => 4,
            _ => continue,
        };
        let (MoneyLocation::Cash(payer), MoneyLocation::Cash(recipient)) =
            (r.debit.location, r.credit.location)
        else {
            return Err(MaterialWorldError::Wire);
        };
        if r.debit
            .delta
            .checked_add(r.credit.delta)
            .map_err(|_| MaterialWorldError::Wire)?
            .micro_units()
            != 0
        {
            return Err(MaterialWorldError::Wire);
        }
        accumulate(&mut actual, (tag, payer, recipient), r.credit.delta)?;
    }
    Ok(actual)
}
