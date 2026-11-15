//! Two-sided elimination of intercompany holdings and reciprocal claims at a single boundary.
use super::carrying::CompanyCarryingLedger;
use super::{CompanyBalance, CompanyStatementsError};
use crate::site_financial_statements::{self, SiteBalanceSheet};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, CompanyBasisAsset, CompanyId, EquipmentAssetId,
    HistoricalCostSnapshot, MaterialCircuitState, SiteId,
};
use std::collections::BTreeMap;

pub(super) fn group(id: AccountId, members: &BTreeMap<SiteId, CompanyId>) -> Option<CompanyId> {
    match id {
        AccountId::Company(c) => Some(c),
        AccountId::Site(site) => members.get(&site).copied(),
        _ => None,
    }
}
#[derive(Default)]
pub(super) struct Endpoint {
    pub parent: CompanyBalance,
    pub subsidiaries: CompanyBalance,
    pub consolidated: CompanyBalance,
    pub holdings: i128,
    pub claims: i128,
    pub unrealized: i128,
}
pub(super) struct Boundary {
    pub groups: BTreeMap<CompanyId, Endpoint>,
    pub legal: BTreeMap<AccountId, SiteBalanceSheet>,
}
impl Boundary {
    pub(super) fn collect(
        state: &MaterialCircuitState,
        members: &BTreeMap<SiteId, CompanyId>,
        carry: &CompanyCarryingLedger,
    ) -> Result<Self, CompanyStatementsError> {
        let CircuitAccounting::Monetary(m) = &state.accounting else {
            return Err(CompanyStatementsError::MonetaryBooksUnavailable);
        };
        let cost = m.costs.snapshot();
        let money = m.book.snapshot();
        let legal = site_financial_statements::collect_selected(
            &money,
            &cost,
            |id| group(id, members).map(|_| id),
            |_, _| Ok(()),
        )
        .map_err(CompanyStatementsError::SiteBooks)?;
        let mut groups = BTreeMap::<CompanyId, Endpoint>::new();
        for (&id, sheet) in &legal {
            let c = group(id, members).ok_or(CompanyStatementsError::ActivityMismatch)?;
            let g = groups.entry(c).or_default();
            let b = CompanyBalance::from_sheet(sheet)?;
            match id {
                AccountId::Company(_) => g.parent = b,
                AccountId::Site(_) => g.subsidiaries.add(&b)?,
                _ => return Err(CompanyStatementsError::ActivityMismatch),
            }
        }
        for row in &cost.equity {
            if let Some(c) =
                group(row.owner, members).filter(|c| members.get(&row.issuer_site_id) == Some(c))
            {
                let g = groups
                    .get_mut(&c)
                    .ok_or(CompanyStatementsError::TreasuryMismatch(c))?;
                g.holdings = g
                    .holdings
                    .checked_add(row.amount.micro_units())
                    .ok_or(CompanyStatementsError::Arithmetic)?;
            }
        }
        for row in &money.shifts {
            if let Some(c) =
                group(row.employer, members).filter(|c| group(row.payee, members) == Some(*c))
            {
                let g = groups
                    .get_mut(&c)
                    .ok_or(CompanyStatementsError::TreasuryMismatch(c))?;
                let amount = row
                    .outstanding_wages()
                    .map_err(|_| CompanyStatementsError::ActivityMismatch)?;
                g.claims = g
                    .claims
                    .checked_add(amount.micro_units())
                    .ok_or(CompanyStatementsError::Arithmetic)?;
            }
        }
        for g in groups.values_mut() {
            let mut b = g.parent.clone();
            b.add(&g.subsidiaries)?;
            let holdings = Currency::from_micro_units(g.holdings);
            let claims = Currency::from_micro_units(g.claims);
            b.investments = b.investments.checked_sub(holdings)?;
            b.receivables = b.receivables.checked_sub(claims)?;
            b.assets = b.assets.checked_sub(holdings)?.checked_sub(claims)?;
            b.equity = b.equity.checked_sub(holdings)?;
            b.liabilities = b.liabilities.checked_sub(claims)?;
            g.consolidated = b;
        }
        eliminate_unrealized_margin(&cost, members, carry, &mut groups)?;
        for (&c, g) in &groups {
            if g.consolidated
                .assets
                .checked_sub(g.consolidated.liabilities)?
                != g.consolidated.equity
            {
                return Err(CompanyStatementsError::TreasuryMismatch(c));
            }
        }
        Ok(Self { groups, legal })
    }
}

fn eliminate_unrealized_margin(
    cost: &HistoricalCostSnapshot,
    members: &BTreeMap<SiteId, CompanyId>,
    carry: &CompanyCarryingLedger,
    groups: &mut BTreeMap<CompanyId, Endpoint>,
) -> Result<(), CompanyStatementsError> {
    if carry.balances.is_empty() {
        return Ok(());
    }
    let mut basis = BTreeMap::new();
    for row in &cost.stocks {
        if let AccountId::Site(s) = row.owner {
            basis.insert(
                CompanyBasisAsset::Stock(s, row.good_id, row.unit_id),
                row.amount,
            );
        }
    }
    for row in &cost.freight {
        if let AccountId::Site(s) = row.owner {
            basis.insert(CompanyBasisAsset::Freight(s, row.lot_id), row.amount);
        }
    }
    for row in &cost.equipment {
        let asset = match row.asset {
            EquipmentAssetId::Installed(id) => CompanyBasisAsset::Equipment(row.owner, id),
            EquipmentAssetId::Installation(id) => CompanyBasisAsset::Installation(row.owner, id),
        };
        basis.insert(asset, row.amount);
    }
    for (&asset, &margin) in &carry.balances {
        let legal = basis
            .get(&asset)
            .ok_or(CompanyStatementsError::BasisMismatch)?;
        if legal.checked_sub(margin)?.micro_units() < 0 {
            return Err(CompanyStatementsError::BasisMismatch);
        }
        let company = members
            .get(&asset.site())
            .ok_or(CompanyStatementsError::BasisMismatch)?;
        let g = groups
            .get_mut(company)
            .ok_or(CompanyStatementsError::BasisMismatch)?;
        let b = &mut g.consolidated;
        let class = match asset {
            CompanyBasisAsset::Stock(..) => &mut b.inventory,
            CompanyBasisAsset::Freight(..) => &mut b.freight,
            CompanyBasisAsset::Equipment(..) | CompanyBasisAsset::Installation(..) => {
                &mut b.equipment
            }
            _ => return Err(CompanyStatementsError::BasisMismatch),
        };
        *class = class.checked_sub(margin)?;
        b.assets = b.assets.checked_sub(margin)?;
        b.equity = b.equity.checked_sub(margin)?;
        b.retained_earnings = b.retained_earnings.checked_sub(margin)?;
        g.unrealized = g
            .unrealized
            .checked_add(margin.micro_units())
            .ok_or(CompanyStatementsError::Arithmetic)?;
    }
    Ok(())
}
