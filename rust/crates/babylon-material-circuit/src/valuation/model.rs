//! Historical transaction costs, distinct from money and physical quantities.

use crate::{AccountId, FreightLotId, GoodId, SiteId, UnitId};
use babylon_kernel::currency::Currency;

/// One explicit carrying amount for an existing physical stock, including zero.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StockCarryingValue {
    pub owner: AccountId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub amount: Currency,
}

/// Seller-owned cost follows a lot independently of buyer purchase escrow.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FreightCarryingValue {
    pub lot_id: FreightLotId,
    pub owner: SiteId,
    pub amount: Currency,
}

/// Historical acquisition of a captured ownership claim, never marked to market.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EquityCarryingValue {
    pub owner: AccountId,
    pub issuer_site_id: SiteId,
    pub amount: Currency,
}

/// Opening book capital is captured once; earnings can be negative.
/// Existing installed equipment without a captured monetary carrying amount is
/// outside this book. This is not total social capital or a value-theory measure.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CapitalAccount {
    pub account: AccountId,
    pub opening_capital: Currency,
    pub contributed_capital: Currency,
    pub retained_earnings: Currency,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HistoricalCostSnapshot {
    pub accounts: Vec<CapitalAccount>,
    pub stocks: Vec<StockCarryingValue>,
    pub freight: Vec<FreightCarryingValue>,
    pub equity: Vec<EquityCarryingValue>,
}

/// Nonnegative period flows; capitalization is disclosed but is not an expense.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IncomeStatement {
    pub sales: Currency,
    pub wage_income: Currency,
    pub cost_of_goods_sold: Currency,
    pub productive_labor_capitalized: Currency,
    pub idle_labor_expense: Currency,
    pub handling_expense: Currency,
    pub maintenance_labor_expense: Currency,
    pub maintenance_material_expense: Currency,
    pub freight_loss_expense: Currency,
    pub consumption_expense: Currency,
    pub final_demand_outlay: Currency,
    pub unused_service_expense: Currency,
    pub tax_income: Currency,
    pub tax_expense: Currency,
    pub public_transfer_income: Currency,
    pub public_transfer_expense: Currency,
    pub distribution_income: Currency,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IncomeReceipt {
    pub account: AccountId,
    pub period: u64,
    pub opening_capital: Currency,
    pub opening_retained_earnings: Currency,
    pub opening_contributed_capital: Currency,
    pub contributions_received: Currency,
    pub closing_contributed_capital: Currency,
    pub distributions_paid: Currency,
    pub statement: IncomeStatement,
    pub net_income: Currency,
    pub closing_retained_earnings: Currency,
}
