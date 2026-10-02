//! Exact conserved production, inventory, order, and realization transitions.
//!
//! One transition closes one four-week period. Period ordinals advance by one;
//! explicit finite schedules or installed capacity supply each interval; staffing owns labor.
//! Inventories, people, order principals and per-batch recipes retain their units.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

mod accounts;
mod capacity;
mod financial;
mod inventory;
mod maintenance;
mod model;
mod payments;
mod production;
mod recurring;
mod services;
mod staffing;
mod transition;
mod valuation;
mod wire;

pub use accounts::{
    AccountId, CashAccount, CashTransferPurpose, FundedShift, MonetaryBook, MonetaryBookSnapshot,
    MonetaryError, MoneyLocation, MoneyPosting, MoneyTransferPurpose, MoneyTransferReceipt,
    OrganizationAccountId, PublicAccountId, PurchaseEscrow, PurchaseMovementReceipt, ShiftId,
    ShiftState, WageAccrualReceipt,
};
pub use financial::{
    validate_distribution_receipts, CapitalContributionOrder, CapitalContributionReceipt,
    ContributionId, DistributionPolicy, DistributionReceipt, FinancialInstitutions,
    InstitutionLocation, OwnershipClaim, PublicAllocation, PublicBudget, PublicBudgetReceipt,
    PublicTransferTreatment, TaxBasis, TaxPolicy, TaxReceipt,
};
pub use model::*;
pub use payments::{
    admit_material_purchase, member_shift_id, CircuitAccounting, EmploymentTerms,
    LaborCompensation, LaborUseReceipt, MaterialPurchase, MemberLaborUseReceipt, MonetaryCircuit,
    MAX_MONEY_TRANSFERS_PER_PERIOD,
};
pub use recurring::*;
pub use services::{
    recurring_service_order_id, CommodityDefinition, CommodityKind, HouseholdServiceReceipt,
    ServiceConnection, ServiceInputPolicy, ServiceMarketReceipt, ServiceOrder,
    ServiceOutputReceipt, ServicePerformanceReceipt, ServicePriceDecision, ServiceStage,
    MAX_SERVICE_RECEIPTS_PER_PERIOD,
};
pub use staffing::{
    advance_staffing, distribute_staffing_members, MemberLaborCapacityRow, StaffingError,
    StaffingMemberBinding, StaffingMemberId, StaffingMemberReceipt, StaffingMemberState,
    StaffingPolicy, StaffingPoolBinding, StaffingPoolId, StaffingPoolState, StaffingReceipt,
    StaffingState, StaffingTransition, StaffingWorkRequest, StaffingWorkSource,
    MAX_STAFFING_MEMBERS,
};
pub use valuation::{
    CapitalAccount, EquityCarryingValue, FreightCarryingValue, HistoricalCostBook,
    HistoricalCostSnapshot, IncomeReceipt, IncomeStatement, StockCarryingValue,
    MAX_CARRYING_STOCKS,
};

pub use transition::{advance_material_circuit, close_material_period, ClosedMaterialPeriod};
pub use wire::{
    decode_material_circuit_state, encode_material_circuit_state, material_circuit_state_digest,
    MATERIAL_CIRCUIT_SOURCE_SHA256, MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES,
};
