//! Canonical financial institutions, eligibility, finite instructions and budgets.
use super::accounting;
use super::Cursor;
use crate::{
    CapitalContributionOrder, ContributionId, DistributionPolicy, FinalDemandPrincipalId,
    FinancialInstitutions, InstitutionLocation, LayoffRecord, MaterialCircuitError, OwnershipClaim,
    PublicAccountId, PublicAllocation, PublicBudget, PublicProgram, PublicProgramKey,
    PublicProgramTerms, PublicSpendingRule, PublicTransferTreatment, SiteId, StaffingMemberId,
    TaxBasis, TaxPolicy, MAX_LAYOFF_PERIODS,
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
    if f.has_public_program_extension() {
        append_tail(out, f)?;
    }
    Ok(())
}
/// `extended` is true only under state versions 25 and 26, which carry the tail.
pub(super) fn decode(c: &mut Cursor<'_>, extended: bool) -> Result<FinancialInstitutions> {
    let mut f = FinancialInstitutions {
        locations: decode_locations(c)?,
        ownership: decode_ownership(c)?,
        distributions: decode_distributions(c)?,
        taxes: decode_taxes(c)?,
        public_budgets: decode_public_budgets(c)?,
        public_allocations: decode_public_allocations(c)?,
        contributions: decode_contributions(c)?,
        programs: vec![],
        layoffs: vec![],
    };
    if extended {
        decode_tail(c, &mut f)?;
    }
    Ok(f)
}
/// The tail after the financial rows: one `u32` count equal to the budgets' and one `u8` rule for each
/// budget in its order; then the programs and the layoff records, each a `u32` count.
fn append_tail(out: &mut Vec<u8>, f: &FinancialInstitutions) -> Result<()> {
    super::append_rows(out, &f.public_budgets, |b, r| b.push(r.rule as u8))?;
    append_programs(out, &f.programs)?;
    append_layoffs(out, &f.layoffs)
}
fn decode_tail(c: &mut Cursor<'_>, f: &mut FinancialInstitutions) -> Result<()> {
    let rules = super::decode_rows(c, |b| match b.u8()? {
        1 => Ok(PublicSpendingRule::CappedInOrder),
        2 => Ok(PublicSpendingRule::CashInProportion),
        _ => Err(MaterialCircuitError::WireEnum),
    })?;
    if rules.len() != f.public_budgets.len() {
        return Err(MaterialCircuitError::WireNoncanonical);
    }
    for (budget, rule) in f.public_budgets.iter_mut().zip(rules) {
        budget.rule = rule;
    }
    f.programs = decode_programs(c)?;
    f.layoffs = decode_layoffs(c)?;
    Ok(())
}
/// Per record: the member 32 bytes, the hours of the job lost `u64`, a `u8` count of cohorts and each
/// cohort `u64`, newest first.
fn append_layoffs(out: &mut Vec<u8>, rows: &[LayoffRecord]) -> Result<()> {
    super::try_append_bounded_rows(out, rows, crate::MAX_STAFFING_MEMBERS, |b, r| {
        b.extend_from_slice(&r.member_id.as_bytes());
        b.extend_from_slice(&r.hours_per_person.to_be_bytes());
        b.push(u8::try_from(r.cohorts.len()).map_err(|_| MaterialCircuitError::WireLimit)?);
        for cohort in &r.cohorts {
            b.extend_from_slice(&cohort.to_be_bytes());
        }
        Ok(())
    })
}
fn decode_layoffs(c: &mut Cursor<'_>) -> Result<Vec<LayoffRecord>> {
    let rows = super::decode_bounded_rows(c, crate::MAX_STAFFING_MEMBERS, |b| {
        let member_id = StaffingMemberId::from_bytes(b.array()?);
        let hours_per_person = b.u64()?;
        let count = usize::from(b.u8()?);
        let mut cohorts = Vec::with_capacity(count.min(MAX_LAYOFF_PERIODS));
        for _ in 0..count {
            cohorts.push(b.u64()?);
        }
        Ok(LayoffRecord {
            member_id,
            hours_per_person,
            cohorts,
        })
    })?;
    accounting::ordered_rows(&rows, |r| r.member_id)?;
    Ok(rows)
}
/// Per program: key length `u8` and its bytes, payer, rank `u32`, a tag `u8`, the terms, then a `u32`
/// count of recipients and 32 bytes each. Terms: tag 1 the amount per person, tag 2 the wage share
/// `u16` and the half periods `u16`, tag 3 the share `u32`; under tag 3 only, each recipient's own
/// amount as `i128` follows the recipients, in their order and with no count of its own.
fn append_programs(out: &mut Vec<u8>, rows: &[PublicProgram]) -> Result<()> {
    super::try_append_bounded_rows(out, rows, crate::MAX_PUBLIC_PROGRAMS, |b, r| {
        let key = r.key.as_str().as_bytes();
        b.push(u8::try_from(key.len()).map_err(|_| MaterialCircuitError::WireLimit)?);
        b.extend_from_slice(key);
        b.extend_from_slice(&r.payer.as_bytes());
        b.extend_from_slice(&r.rank.to_be_bytes());
        match r.terms {
            PublicProgramTerms::PerPerson { amount_per_person } => {
                b.push(1);
                b.extend_from_slice(&amount_per_person.micro_units().to_be_bytes());
            }
            PublicProgramTerms::AfterLayoff {
                wage_share_bps,
                half_periods,
            } => {
                b.push(2);
                b.extend_from_slice(&wage_share_bps.to_be_bytes());
                b.extend_from_slice(&half_periods.to_be_bytes());
            }
            PublicProgramTerms::PerPersonOwn { share_bps } => {
                b.push(3);
                b.extend_from_slice(&share_bps.to_be_bytes());
            }
        }
        b.extend_from_slice(
            &u32::try_from(r.recipients.len())
                .map_err(|_| MaterialCircuitError::WireLimit)?
                .to_be_bytes(),
        );
        for recipient in &r.recipients {
            b.extend_from_slice(&recipient.as_bytes());
        }
        if matches!(r.terms, PublicProgramTerms::PerPersonOwn { .. }) {
            for amount in &r.own_amounts {
                b.extend_from_slice(&amount.micro_units().to_be_bytes());
            }
        }
        Ok(())
    })
}
fn decode_programs(c: &mut Cursor<'_>) -> Result<Vec<PublicProgram>> {
    let rows = super::decode_bounded_rows(c, crate::MAX_PUBLIC_PROGRAMS, |b| {
        let length = usize::from(b.u8()?);
        let text = std::str::from_utf8(b.take(length)?)
            .map_err(|_| MaterialCircuitError::WireNoncanonical)?;
        let key =
            PublicProgramKey::new(text).map_err(|_| MaterialCircuitError::WireNoncanonical)?;
        let payer = PublicAccountId::from_bytes(b.array()?);
        let rank = b.u32()?;
        let terms = match b.u8()? {
            1 => PublicProgramTerms::PerPerson {
                amount_per_person: accounting::decode_currency(b)?,
            },
            2 => PublicProgramTerms::AfterLayoff {
                wage_share_bps: b.u16()?,
                half_periods: b.u16()?,
            },
            3 => PublicProgramTerms::PerPersonOwn {
                share_bps: b.u32()?,
            },
            _ => return Err(MaterialCircuitError::WireEnum),
        };
        let recipients =
            super::decode_rows(b, |b| Ok(FinalDemandPrincipalId::from_bytes(b.array()?)))?;
        accounting::ordered_rows(&recipients, |r| *r)?;
        let mut own_amounts = Vec::new();
        if matches!(terms, PublicProgramTerms::PerPersonOwn { .. }) {
            for _ in &recipients {
                let amount = accounting::decode_currency(b)?;
                if amount.micro_units() <= 0 {
                    return Err(MaterialCircuitError::WireNoncanonical);
                }
                own_amounts.push(amount);
            }
        }
        Ok(PublicProgram {
            key,
            payer,
            rank,
            terms,
            recipients,
            own_amounts,
        })
    })?;
    accounting::ordered_rows(&rows, |r| r.key.clone())?;
    Ok(rows)
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
    super::append_bounded_rows(out, rows, crate::MAX_TAX_POLICIES, |b, r| {
        accounting::append_account(b, r.payer);
        b.extend_from_slice(&r.public_recipient.as_bytes());
        b.push(r.basis as u8);
        b.extend_from_slice(&r.rate_bps.to_be_bytes());
        b.extend_from_slice(&r.cash_floor.micro_units().to_be_bytes());
    })
}
fn decode_taxes(c: &mut Cursor<'_>) -> Result<Vec<TaxPolicy>> {
    let rows = super::decode_bounded_rows(c, crate::MAX_TAX_POLICIES, |b| {
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
    accounting::ordered_rows(&rows, |r| (r.payer, r.basis, r.public_recipient))?;
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
            rule: PublicSpendingRule::CappedInOrder,
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
                3 => PublicTransferTreatment::AgencyAppropriation,
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

#[cfg(test)]
mod tests {
    use super::{append_layoffs, append_programs, decode_programs};
    use crate::wire::Cursor;
    use crate::{
        FinalDemandPrincipalId, LayoffRecord, MaterialCircuitError, PublicAccountId, PublicProgram,
        PublicProgramKey, PublicProgramTerms, StaffingMemberId,
    };
    use babylon_kernel::currency::Currency;

    fn own_program(amounts: [i128; 2]) -> PublicProgram {
        PublicProgram {
            key: PublicProgramKey::new("p").expect("a key"),
            payer: PublicAccountId::from_bytes([9; 32]),
            rank: 2,
            terms: PublicProgramTerms::PerPersonOwn { share_bps: 10_000 },
            recipients: vec![
                FinalDemandPrincipalId::from_bytes([1; 32]),
                FinalDemandPrincipalId::from_bytes([2; 32]),
            ],
            own_amounts: amounts.map(Currency::from_micro_units).to_vec(),
        }
    }

    #[test]
    fn a_program_of_own_amounts_round_trips() {
        let program = own_program([5, 7]);
        let mut out = vec![];
        append_programs(&mut out, std::slice::from_ref(&program)).expect("written");
        let mut expected = 1_u32.to_be_bytes().to_vec();
        expected.push(1);
        expected.extend_from_slice(b"p");
        expected.extend_from_slice(&[9; 32]);
        expected.extend_from_slice(&2_u32.to_be_bytes());
        expected.push(3);
        expected.extend_from_slice(&10_000_u32.to_be_bytes());
        expected.extend_from_slice(&2_u32.to_be_bytes());
        expected.extend_from_slice(&[1; 32]);
        expected.extend_from_slice(&[2; 32]);
        expected.extend_from_slice(&5_i128.to_be_bytes());
        expected.extend_from_slice(&7_i128.to_be_bytes());
        assert_eq!(out, expected);
        assert_eq!(
            decode_programs(&mut Cursor::new(&out)).expect("decoded"),
            vec![program]
        );
        let tag_at = 4 + 1 + 1 + 32 + 4;
        let mut bad_tag = out.clone();
        bad_tag[tag_at] = 4;
        assert_eq!(
            decode_programs(&mut Cursor::new(&bad_tag)).err(),
            Some(MaterialCircuitError::WireEnum)
        );
        let mut zero = vec![];
        append_programs(&mut zero, &[own_program([0, 7])]).expect("written");
        assert_eq!(
            decode_programs(&mut Cursor::new(&zero)).err(),
            Some(MaterialCircuitError::WireNoncanonical)
        );
    }

    /// A record of more cohorts than the byte count holds is refused, never clamped to 255.
    #[test]
    fn a_record_of_too_many_cohorts_is_a_wire_limit() {
        let record = LayoffRecord {
            member_id: StaffingMemberId::from_bytes([1; 32]),
            hours_per_person: 1,
            cohorts: vec![1; 256],
        };
        let mut out = vec![];
        assert_eq!(
            append_layoffs(&mut out, &[record]),
            Err(MaterialCircuitError::WireLimit)
        );
    }

    /// An ill-formed key in the bytes is a fault of the bytes, not of a program.
    #[test]
    fn an_ill_formed_key_in_the_bytes_is_noncanonical() {
        let mut bytes = 1_u32.to_be_bytes().to_vec();
        bytes.push(9);
        bytes.extend_from_slice(b"No-earner");
        assert_eq!(
            decode_programs(&mut Cursor::new(&bytes)).err(),
            Some(MaterialCircuitError::WireNoncanonical)
        );
    }
}
