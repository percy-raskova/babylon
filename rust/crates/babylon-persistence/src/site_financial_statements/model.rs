//! Typed statement outputs, independent of persistence journals and SQL totals.
use crate::identity::CampaignId;
use crate::observer_reader::ObserverEconomyError;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{IncomeReceipt, MoneyTransferReceipt, OwnershipClaim, SiteId};
use std::fmt::Result as FmtResult;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SiteStatementsError {
    Read(ObserverEconomyError),
    SiteAbsent,
    MonetaryBooksUnavailable,
    Arithmetic,
    BalanceSheetMismatch,
    IncomeReceiptMismatch,
    InvestmentReceiptMismatch,
    EquityBridgeMismatch,
    InvalidTransfer,
    CashReconciliationMismatch,
    PeriodMismatch,
}
impl From<ObserverEconomyError> for SiteStatementsError {
    fn from(value: ObserverEconomyError) -> Self {
        Self::Read(value)
    }
}
impl Display for SiteStatementsError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "site financial statements refused: {self:?}")
    }
}
impl std::error::Error for SiteStatementsError {}

/// No ownership share, workplace location, or cash receipt proves planning control.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlanningControl {
    NotCaptured,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SiteFinancialStatements {
    pub campaign_id: CampaignId,
    pub site_id: SiteId,
    pub resolve_tick: u64,
    pub foundation_digest: [u8; 32],
    pub nominal_world_hash: Option<[u8; 32]>,
    pub tick_content_hash: Option<[u8; 32]>,
    pub receipt_digest: Option<[u8; 32]>,
    pub books: SiteBookStatements,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SiteBookStatements {
    /// None only for the foundation: it has no predecessor or period flow.
    pub opening: Option<SiteBalanceSheet>,
    pub closing: SiteBalanceSheet,
    pub activity: Option<SitePeriodActivity>,
    pub ownership_claims: Vec<OwnershipClaim>,
    pub planning_control: PlanningControl,
}

/// No liabilities are inferred from unpaid tax assessments or purchase promises.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SiteBalanceSheet {
    pub cash: Currency,
    pub purchase_reserves: Currency,
    pub payroll_reserves: Currency,
    pub wage_receivables: Currency,
    pub inventory: Currency,
    pub freight: Currency,
    pub equity_investments: Currency,
    pub equipment: Currency,
    pub total_assets: Currency,
    pub wage_payables: Currency,
    pub total_liabilities: Currency,
    pub opening_capital: Currency,
    pub contributed_capital: Currency,
    pub retained_earnings: Currency,
    pub total_equity: Currency,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SitePeriodActivity {
    /// Complete receipt, including all costs, transfers and capitalization disclosures.
    pub income: IncomeReceipt,
    pub change_in_equity: Currency,
    pub cash_flow: CashFlowStatement,
}

/// Spendable cash excludes purchase/payroll reserves. Moving cash to a reserve
/// changes liquidity before a purchase settles or attendance becomes an expense.
/// Purchase reservations joined exactly to this period's admitted investment
/// receipts are investing cash outflows. Other reserve movements are proved and
/// reported separately, without guessing the principal's operating/investing use.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CashFlowStatement {
    pub operating: Currency,
    pub investing: Currency,
    pub financing: Currency,
    pub reserve_reclassification: Currency,
    pub net_change_in_cash: Currency,
    pub opening_cash: Currency,
    pub closing_cash: Currency,
    pub change_in_purchase_reserves: Currency,
    pub change_in_payroll_reserves: Currency,
    pub transfers: Vec<CashFlowTransfer>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CashFlowCategory {
    Operating,
    Investing,
    Financing,
    ReserveReclassification,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CashFlowTransfer {
    /// Position in this exact committed receipt family's `money_transfers` register.
    pub receipt_index: usize,
    pub category: CashFlowCategory,
    pub transfer: MoneyTransferReceipt,
}
