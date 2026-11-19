//! Compact period rows derived from the authenticated predecessor, close and receipts.
use super::{balances, projection};
use super::{
    SiteAccountingPeriod, SiteBalanceSheet, SiteCashFlowTotals, SiteStatementSummary,
    SiteStatementsError, SiteStockBalance, SiteStockPosition,
};
use babylon_material_circuit::{
    AccountId, CircuitAccounting, GoodId, MaterialCircuitState, MoneyLocation, SiteId, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::BTreeMap;

type StockKey = (SiteId, GoodId, UnitId);
type SiteBalances = BTreeMap<SiteId, SiteBalanceSheet>;

struct Endpoint {
    balances: Option<SiteBalances>,
    stocks: BTreeMap<StockKey, SiteStockPosition>,
}

impl Endpoint {
    fn collect(state: &MaterialCircuitState) -> Result<Self, SiteStatementsError> {
        let mut stocks = BTreeMap::new();
        for row in &state.inventory {
            let key = (row.site_id, row.good_id, row.unit_id);
            let position = SiteStockPosition {
                quantity: row.quantity,
                carrying_cost: None,
            };
            if stocks.insert(key, position).is_some() {
                return Err(SiteStatementsError::StockBasisMismatch);
            }
        }
        let balances = match &state.accounting {
            CircuitAccounting::PhysicalControl => None,
            CircuitAccounting::Monetary(economy) => {
                let balances = balances::collect(
                    &economy.book.snapshot(),
                    &economy.costs.snapshot(),
                    None,
                    |site, basis| {
                        let key = (site, basis.good_id, basis.unit_id);
                        let row = stocks
                            .get_mut(&key)
                            .ok_or(SiteStatementsError::StockBasisMismatch)?;
                        if (row.quantity == 0 && basis.amount.micro_units() != 0)
                            || row.carrying_cost.replace(basis.amount).is_some()
                        {
                            return Err(SiteStatementsError::StockBasisMismatch);
                        }
                        Ok(())
                    },
                )?;
                if stocks.values().any(|row| row.carrying_cost.is_none()) {
                    return Err(SiteStatementsError::StockBasisMismatch);
                }
                Some(balances)
            }
        };
        Ok(Self { balances, stocks })
    }
}

/// Project all site financial summaries and exact native-unit stock positions for
/// one completed period. Each transfer is attributed only to its site cash postings.
/// The caller authenticates both registers and the exact committed receipt identity.
///
/// # Errors
/// Refuses inconsistent period, accounting mode, stock basis, missing principals, or
/// unreconciled site assets, equity, income and cash movements.
pub fn project_period(
    opening: &MaterialCircuitState,
    closing: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
) -> Result<SiteAccountingPeriod, SiteStatementsError> {
    if receipts.resolve_tick == 0
        || receipts.resolve_tick != opening.period
        || opening.period.checked_add(1) != Some(closing.period)
    {
        return Err(SiteStatementsError::PeriodMismatch);
    }
    let before = Endpoint::collect(opening)?;
    let after = Endpoint::collect(closing)?;
    let statements = match (before.balances, after.balances) {
        (Some(before), Some(after)) => Some(statements(before, after, receipts)?),
        (None, None)
            if receipts.income.is_empty()
                && receipts.money_transfers.is_empty()
                && receipts.investment.is_empty() =>
        {
            None
        }
        _ => return Err(SiteStatementsError::PeriodMismatch),
    };
    let mut stocks = BTreeMap::new();
    for (key, point) in before.stocks {
        stocks.insert(key, (Some(point), None));
    }
    for (key, point) in after.stocks {
        stocks.entry(key).or_default().1 = Some(point);
    }
    let stocks = stocks
        .into_iter()
        .map(
            |((site_id, good_id, unit_id), (opening, closing))| SiteStockBalance {
                site_id,
                good_id,
                unit_id,
                opening,
                closing,
            },
        )
        .collect();
    Ok(SiteAccountingPeriod {
        resolve_tick: receipts.resolve_tick,
        statements,
        stocks,
    })
}

fn statements(
    opening: SiteBalances,
    closing: SiteBalances,
    receipts: &MaterialTickReceipts,
) -> Result<Vec<SiteStatementSummary>, SiteStatementsError> {
    if !opening.keys().eq(closing.keys()) {
        return Err(SiteStatementsError::BalanceSheetMismatch);
    }
    let mut cash: BTreeMap<_, _> = opening
        .keys()
        .map(|&site| (site, SiteCashFlowTotals::empty()))
        .collect();
    let investments = projection::investment_reservations(None, receipts)?;
    for transfer in &receipts.money_transfers {
        for posting in [&transfer.debit, &transfer.credit] {
            if let MoneyLocation::Cash(AccountId::Site(site)) = posting.location {
                cash.get_mut(&site)
                    .ok_or(SiteStatementsError::InvalidTransfer)?
                    .record(site, transfer, &investments)?;
            }
        }
    }
    let mut incomes = BTreeMap::new();
    for income in &receipts.income {
        if let AccountId::Site(site) = income.account {
            if !opening.contains_key(&site) || incomes.insert(site, income).is_some() {
                return Err(SiteStatementsError::IncomeReceiptMismatch);
            }
        }
    }
    let mut summaries = Vec::with_capacity(opening.len());
    for (((site_id, opening), closing), cash_flow) in opening
        .into_iter()
        .zip(closing.into_values())
        .zip(cash.into_values())
    {
        let income = incomes
            .remove(&site_id)
            .ok_or(SiteStatementsError::IncomeReceiptMismatch)?;
        let change_in_equity =
            projection::equity_change(&opening, &closing, income, receipts.resolve_tick)?;
        cash_flow.reconcile(projection::sub(closing.cash, opening.cash)?)?;
        summaries.push(SiteStatementSummary {
            site_id,
            opening,
            closing,
            income: income.clone(),
            change_in_equity,
            cash_flow,
        });
    }
    Ok(summaries)
}
