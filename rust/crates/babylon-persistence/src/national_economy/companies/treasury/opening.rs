//! Conversion of the native opening capital, cash and original site claims.
use super::model::Result;
use super::{claims, CompanyFinances, MemberFunding, TreasuryError};
use crate::economic_catalog::EconomicOpening;
use crate::national_economy::companies::CompanyCapture;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CashAccount, CompanyPayoutPolicy, EquityCarryingValue, OwnershipClaim,
};
use std::collections::{BTreeMap, BTreeSet};
pub(in crate::national_economy) fn fund(
    opening: &mut EconomicOpening,
    capture: &CompanyCapture,
    sweep_bps: u16,
    earnings_bps: u16,
) -> Result<CompanyFinances> {
    let capital = opening
        .opening_capital()
        .map_err(|_| TreasuryError::OpeningBook)?;
    let mut parents: BTreeMap<_, _> = capture
        .members
        .iter()
        .map(|r| (r.site, r.company.id()))
        .collect();
    let floors: BTreeMap<_, _> = opening
        .institutions
        .distributions
        .iter()
        .map(|r| (r.issuer_site_id, r.cash_floor))
        .collect();
    let mut members = Vec::with_capacity(parents.len());
    for site in &mut opening.sites {
        let Some(company) = parents.remove(&site.site_id) else {
            continue;
        };
        let original_capital = *capital
            .get(&AccountId::Site(site.site_id))
            .ok_or(TreasuryError::MissingSite(site.site_id))?;
        let cash_floor = *floors
            .get(&site.site_id)
            .ok_or(TreasuryError::MissingFloor(site.site_id))?;
        let original_cash = site.opening_cash;
        let swept = sweep(original_cash, cash_floor, sweep_bps)?;
        let remaining_capital = subtract(original_capital, swept)?;
        if remaining_capital.micro_units() < 0 {
            return Err(TreasuryError::InvalidBasis(site.site_id));
        }
        site.opening_cash = subtract(original_cash, swept)?;
        members.push(MemberFunding {
            site: site.site_id,
            company,
            original_cash,
            cash_floor,
            swept,
            remaining_cash: site.opening_cash,
            original_capital,
            remaining_capital,
        });
    }
    if let Some((&site, _)) = parents.first_key_value() {
        return Err(TreasuryError::MissingSite(site));
    }
    let sites: BTreeSet<_> = members.iter().map(|r| r.site).collect();
    let sources = claims::original(opening, &members)?;
    let (treasuries, claims) = claims::combine(&members, &sources)?;
    opening
        .institutions
        .ownership
        .retain(|r| !sites.contains(&r.issuer_site_id));
    opening
        .equity
        .retain(|r| !sites.contains(&r.issuer_site_id));
    for row in &members {
        let beneficiary = AccountId::Company(row.company);
        opening.institutions.ownership.push(OwnershipClaim {
            issuer_site_id: row.site,
            beneficiary,
            shares: 1,
        });
        opening.equity.push(EquityCarryingValue {
            issuer_site_id: row.site,
            owner: beneficiary,
            amount: row.remaining_capital,
        });
    }
    opening
        .institutional_cash
        .extend(treasuries.iter().map(|r| CashAccount {
            id: AccountId::Company(r.company),
            cash: r.cash,
        }));
    let mut owners = BTreeMap::<_, Vec<_>>::new();
    for row in &claims {
        if row.weight > 0 {
            owners
                .entry(row.company)
                .or_default()
                .push((row.beneficiary, row.weight));
        }
    }
    opening.policies.company_payouts = owners
        .into_iter()
        .map(|(company, claims)| CompanyPayoutPolicy {
            company,
            claims,
            earnings_bps,
        })
        .collect();
    Ok(CompanyFinances {
        sweep_bps,
        members,
        sources,
        claims,
        treasuries,
    })
}

/// Floor only at disbursement. Decomposing the product avoids rejecting a representable result.
pub(super) fn sweep(cash: Currency, floor: Currency, bps: u16) -> Result<Currency> {
    if bps > 10_000 || cash.micro_units() < 0 || floor.micro_units() < 0 {
        return Err(TreasuryError::InvalidRate);
    }
    let excess = (cash.micro_units() - floor.micro_units()).max(0);
    let rate = i128::from(bps);
    Ok(Currency::from_micro_units(
        excess / 10_000 * rate + excess % 10_000 * rate / 10_000,
    ))
}
fn subtract(left: Currency, right: Currency) -> Result<Currency> {
    left.checked_sub(right)
        .map_err(|_| TreasuryError::Arithmetic)
}
pub(super) fn add(left: Currency, right: Currency) -> Result<Currency> {
    left.checked_add(right)
        .map_err(|_| TreasuryError::Arithmetic)
}
