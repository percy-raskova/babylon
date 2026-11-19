//! Preserve exact original claims through whole-site incorporation.
use super::model::Result;
use super::{
    opening, BeneficiaryClaim, CompanyTreasury, MemberFunding, OriginalClaim, TreasuryError,
};
use crate::economic_catalog::EconomicOpening;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{AccountId, CompanyId};
use std::collections::BTreeMap;

pub(super) fn original(
    opening: &EconomicOpening,
    members: &[MemberFunding],
) -> Result<Vec<OriginalClaim>> {
    let sites: BTreeMap<_, _> = members.iter().map(|r| (r.site, r)).collect();
    let mut equity: BTreeMap<_, _> = opening
        .equity
        .iter()
        .filter(|r| sites.contains_key(&r.issuer_site_id))
        .map(|r| ((r.issuer_site_id, r.owner), r.amount))
        .collect();
    let mut totals = BTreeMap::new();
    let mut sources = Vec::new();
    for claim in &opening.institutions.ownership {
        let Some(member) = sites.get(&claim.issuer_site_id) else {
            continue;
        };
        let site = member.site;
        let basis = equity
            .remove(&(site, claim.beneficiary))
            .ok_or(TreasuryError::InvalidClaims(site))?;
        // The national generator authors zero historical cost for beneficiary holdings.
        // A nonzero cost needs a parent-issuer carrying position at conversion.
        if basis.micro_units() != 0 || claim.shares == 0 {
            return Err(TreasuryError::InvalidBasis(site));
        }
        let total = totals.entry(site).or_insert(0_u64);
        *total = total
            .checked_add(claim.shares)
            .ok_or(TreasuryError::Arithmetic)?;
        sources.push(OriginalClaim {
            site,
            company: member.company,
            beneficiary: claim.beneficiary,
            capital: member.original_capital,
            original_shares: claim.shares,
            site_total_shares: 0,
            original_carrying_value: basis,
        });
    }
    if let Some(((site, _), _)) = equity.first_key_value() {
        return Err(TreasuryError::InvalidClaims(*site));
    }
    for member in members {
        if !totals.contains_key(&member.site) {
            return Err(TreasuryError::InvalidClaims(member.site));
        }
    }
    for source in &mut sources {
        source.site_total_shares = totals[&source.site];
    }
    sources.sort_unstable_by_key(|r| (r.site, r.beneficiary));
    Ok(sources)
}

pub(super) fn combine(
    members: &[MemberFunding],
    sources: &[OriginalClaim],
) -> Result<(Vec<CompanyTreasury>, Vec<BeneficiaryClaim>)> {
    let mut companies = BTreeMap::new();
    let zero = Currency::from_micro_units(0);
    for member in members {
        let treasury = companies.entry(member.company).or_insert(CompanyTreasury {
            company: member.company,
            cash: zero,
            original_capital: zero,
            subsidiary_capital: zero,
            common_denominator: 1,
            total_weight: 0,
        });
        treasury.cash = opening::add(treasury.cash, member.swept)?;
        treasury.original_capital =
            opening::add(treasury.original_capital, member.original_capital)?;
        treasury.subsidiary_capital =
            opening::add(treasury.subsidiary_capital, member.remaining_capital)?;
    }
    for row in sources {
        let company = companies
            .get_mut(&row.company)
            .ok_or(TreasuryError::InvalidClaims(row.site))?;
        company.common_denominator = lcm(company.common_denominator, row.site_total_shares)?;
    }
    let mut weights = BTreeMap::<(CompanyId, AccountId), u128>::new();
    for row in sources {
        let company = companies
            .get_mut(&row.company)
            .ok_or(TreasuryError::InvalidClaims(row.site))?;
        let factor = company.common_denominator / u128::from(row.site_total_shares);
        let capital = u128::try_from(row.capital.micro_units())
            .map_err(|_| TreasuryError::InvalidBasis(row.site))?;
        let weight = capital
            .checked_mul(u128::from(row.original_shares))
            .and_then(|w| w.checked_mul(factor))
            .ok_or(TreasuryError::Arithmetic)?;
        let held = weights.entry((row.company, row.beneficiary)).or_default();
        *held = held.checked_add(weight).ok_or(TreasuryError::Arithmetic)?;
        company.total_weight = company
            .total_weight
            .checked_add(weight)
            .ok_or(TreasuryError::Arithmetic)?;
    }
    for company in companies.values() {
        let capital = u128::try_from(company.original_capital.micro_units())
            .map_err(|_| TreasuryError::UnrepresentedCapital(company.company))?;
        if capital == 0
            || capital.checked_mul(company.common_denominator) != Some(company.total_weight)
            || opening::add(company.cash, company.subsidiary_capital)? != company.original_capital
        {
            return Err(TreasuryError::UnrepresentedCapital(company.company));
        }
    }
    let claims = weights
        .into_iter()
        .map(|((company, beneficiary), weight)| BeneficiaryClaim {
            company,
            beneficiary,
            weight,
        })
        .collect();
    Ok((companies.into_values().collect(), claims))
}
fn lcm(left: u128, right: u64) -> Result<u128> {
    let right = u128::from(right);
    let (mut a, mut b) = (left, right);
    while b != 0 {
        (a, b) = (b, a % b);
    }
    (left / a)
        .checked_mul(right)
        .filter(|&n| n > 0)
        .ok_or(TreasuryError::Arithmetic)
}
