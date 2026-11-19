//! Eliminate each authenticated parent holding against its wholly owned operating site.
use super::{CompanyBalance, CompanyOpening, CompanyStatementsError, EliminatedMember};
use crate::economic_catalog::CapturedEconomicCatalog;
use crate::national_economy::companies::{CompanyKey, CompanyTreasury};
use crate::site_financial_statements;
use babylon_material_circuit::{AccountId, CircuitAccounting, CompanyId, MaterialCircuitState};
use std::collections::BTreeMap;

/// Project the authenticated founding legal books after the opening treasury sweep.
/// # Errors
/// Refuses missing capture or any mismatch among ownership, funding, legal equity and native cash.
pub fn project_opening(
    capture: &CapturedEconomicCatalog,
    state: &MaterialCircuitState,
) -> Result<Vec<CompanyOpening>, CompanyStatementsError> {
    let roster = capture
        .national_companies()
        .ok_or(CompanyStatementsError::MembershipNotCaptured)?;
    let finances = capture
        .national_company_finances()
        .ok_or(CompanyStatementsError::TreasuryNotCaptured)?;
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(CompanyStatementsError::MonetaryBooksUnavailable);
    };
    let costs = economy.costs.snapshot();
    let mut sheets = site_financial_statements::collect_selected(
        &economy.book.snapshot(),
        &costs,
        |id| matches!(id, AccountId::Company(_) | AccountId::Site(_)).then_some(id),
        |_, _| Ok(()),
    )
    .map_err(CompanyStatementsError::SiteBooks)?;
    let holdings: BTreeMap<_, _> = costs
        .equity
        .iter()
        .map(|row| ((row.owner, row.issuer_site_id), row.amount))
        .collect();
    let mut funding: BTreeMap<_, _> = finances.members.iter().map(|r| (r.site, r)).collect();
    let mut owners = BTreeMap::new();
    for claim in &economy.financial.ownership {
        let row = owners
            .entry(claim.issuer_site_id)
            .or_insert(Some(claim.beneficiary));
        if *row != Some(claim.beneficiary) {
            *row = None;
        }
    }
    let mut members: BTreeMap<CompanyId, Vec<(EliminatedMember, CompanyBalance)>> = BTreeMap::new();
    for member in &roster.members {
        let site = member.site;
        let company = member.company.id();
        let refusal = CompanyStatementsError::MemberMismatch(site);
        let source = funding.remove(&site).ok_or(refusal)?;
        let sheet = sheets.remove(&AccountId::Site(site)).ok_or(refusal)?;
        let owner = AccountId::Company(company);
        let investment = *holdings.get(&(owner, site)).ok_or(refusal)?;
        if owners.get(&site) != Some(&Some(owner))
            || source.company != company
            || sheet.cash != source.remaining_cash
            || sheet.total_equity != source.remaining_capital
            || investment != sheet.total_equity
        {
            return Err(refusal);
        }
        members.entry(company).or_default().push((
            EliminatedMember {
                site,
                cash: sheet.cash,
                investment,
            },
            CompanyBalance::from_sheet(&sheet)?,
        ));
    }
    if let Some((&site, _)) = funding.first_key_value() {
        return Err(CompanyStatementsError::MemberMismatch(site));
    }
    let mut keys: BTreeMap<_, _> = roster
        .companies
        .iter()
        .map(|r| (r.key.id(), r.key))
        .collect();
    let mut reports = Vec::with_capacity(finances.treasuries.len());
    for treasury in &finances.treasuries {
        let company = treasury.company;
        let refusal = CompanyStatementsError::TreasuryMismatch(company);
        let parent = CompanyBalance::from_sheet(
            &sheets.remove(&AccountId::Company(company)).ok_or(refusal)?,
        )?;
        let entries = members.remove(&company).ok_or(refusal)?;
        let key = keys.remove(&company).ok_or(refusal)?;
        reports.push(consolidate(treasury, key, parent, entries)?);
    }
    if let Some((&company, _)) = members.first_key_value() {
        return Err(CompanyStatementsError::TreasuryMismatch(company));
    }
    if let Some((&company, _)) = keys.first_key_value() {
        return Err(CompanyStatementsError::TreasuryMismatch(company));
    }
    Ok(reports)
}

fn consolidate(
    treasury: &CompanyTreasury,
    key: CompanyKey,
    parent: CompanyBalance,
    entries: Vec<(EliminatedMember, CompanyBalance)>,
) -> Result<CompanyOpening, CompanyStatementsError> {
    let company = treasury.company;
    let refusal = CompanyStatementsError::TreasuryMismatch(company);
    let mut rows = Vec::with_capacity(entries.len());
    let mut entries = entries.into_iter();
    let (first, mut subsidiaries) = entries.next().ok_or(refusal)?;
    let mut eliminated = first.investment;
    rows.push(first);
    for (member, sheet) in entries {
        subsidiaries.add(&sheet)?;
        eliminated = eliminated.checked_add(member.investment)?;
        rows.push(member);
    }
    if parent.cash != treasury.cash
        || parent.equity != treasury.original_capital
        || subsidiaries.equity != treasury.subsidiary_capital
        || eliminated != subsidiaries.equity
    {
        return Err(refusal);
    }
    let mut consolidated = parent.clone();
    consolidated.add(&subsidiaries)?;
    consolidated.investments = consolidated.investments.checked_sub(eliminated)?;
    consolidated.assets = consolidated.assets.checked_sub(eliminated)?;
    consolidated.equity = consolidated.equity.checked_sub(eliminated)?;
    if consolidated.assets.checked_sub(consolidated.liabilities)? != consolidated.equity {
        return Err(refusal);
    }
    Ok(CompanyOpening {
        company,
        key,
        parent,
        subsidiaries,
        eliminated_member_investment: eliminated,
        consolidated,
        members: rows,
    })
}
