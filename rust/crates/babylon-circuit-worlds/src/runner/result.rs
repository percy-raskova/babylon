//! What one closed period returns.

use crate::doubled::Figures;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CapitalAccount, DistributionReceipt, GoodId, HouseholdCohort,
    HouseholdConsumptionReceipt, HouseholdDemandReceipt, HouseholdServiceReceipt, IncomeReceipt,
    LaborUseReceipt, LocalRetailFulfillmentReceipt, LocalTransferReceipt, MarketClearingReceipt,
    MemberLaborUseReceipt, MerchantHandlingReceipt, MoneyTransferReceipt, OwnershipClaim,
    PriceReceipt, ProcurementReceipt, ProductionReceipt, PublicBudgetReceipt, PublicProgramReceipt,
    ServiceMarketReceipt, ServiceOutputReceipt, ServicePerformanceReceipt, SiteId,
    StaffingMemberReceipt, TaxReceipt, WageAccrualReceipt,
};

/// One closed period.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PeriodResult {
    /// The period that closed.
    pub period: u64,
    /// The catalog's figures this period closed under.
    pub figures: Figures,
    /// The receipts the scene reads.
    pub receipts: PeriodReceipts,
    /// The member receipts of the staffing; the transition's own list is empty.
    pub members: Vec<StaffingMemberReceipt>,
    /// What the next state holds.
    pub closing: Closing,
    /// The measures of the period.
    pub summary: PeriodSummary,
    /// `material_circuit_state_digest` of the catalog this period closed under and the next state.
    pub state_digest: [u8; 32],
}

/// The receipts the scene reads, moved out of the engine's transition.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PeriodReceipts {
    pub member_labor_use: Vec<MemberLaborUseReceipt>,
    pub labor_use: Vec<LaborUseReceipt>,
    pub production: Vec<ProductionReceipt>,
    pub service_outputs: Vec<ServiceOutputReceipt>,
    pub service_performance: Vec<ServicePerformanceReceipt>,
    pub household_services: Vec<HouseholdServiceReceipt>,
    pub handling: Vec<MerchantHandlingReceipt>,
    pub local_transfers: Vec<LocalTransferReceipt>,
    pub local_fulfillments: Vec<LocalRetailFulfillmentReceipt>,
    pub procurement: Vec<ProcurementReceipt>,
    pub household_demand: Vec<HouseholdDemandReceipt>,
    pub household_consumption: Vec<HouseholdConsumptionReceipt>,
    pub money_transfers: Vec<MoneyTransferReceipt>,
    pub wage_accruals: Vec<WageAccrualReceipt>,
    pub taxes: Vec<TaxReceipt>,
    pub public_programs: Vec<PublicProgramReceipt>,
    pub public_budgets: Vec<PublicBudgetReceipt>,
    pub distributions: Vec<DistributionReceipt>,
    pub income: Vec<IncomeReceipt>,
    pub prices: Vec<PriceReceipt>,
    pub service_markets: Vec<ServiceMarketReceipt>,
    pub market_clearings: Vec<MarketClearingReceipt>,
}

/// Read from the next state before it is carried on.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Closing {
    /// Cash by account, in the book's order.
    pub cash: Vec<(AccountId, Currency)>,
    /// The book capital of each account.
    pub capital: Vec<CapitalAccount>,
    /// Who owns which workplace.
    pub ownership: Vec<OwnershipClaim>,
    /// The households' cohorts.
    pub households: Vec<HouseholdCohort>,
    /// Persons at work, by `Workplace::index`.
    pub employed: [u64; 8],
    /// Persons in reserve, by `Workplace::index`.
    pub reserve: [u64; 8],
}

/// The measures by which two periods are called equal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PeriodSummary {
    /// Hours attended, by `Workplace::index`.
    pub hours_attended: [u64; 8],
    /// Units made, by `Workplace::index`.
    pub made: [u64; 8],
    /// Persons employed, by `Workplace::index`.
    pub employed: [u64; 8],
    /// Cash by account, in millionths of a dollar.
    pub cash: Vec<(AccountId, i128)>,
    /// Posted offers at the close, in millionths of a dollar.
    pub prices: Vec<(SiteId, GoodId, i128)>,
    /// All cash and reserves, in millionths of a dollar.
    pub total_money: i128,
    /// Persons of every cohort.
    pub persons: u64,
}
