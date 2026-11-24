//! Exact conserved production, inventory, order, and realization transitions.
//!
//! One transition closes one four-week period. Period ordinals advance by one;
//! explicit finite schedules or installed capacity supply each interval; staffing owns labor.
//! Inventories, people, order principals and per-batch recipes retain their units.

mod accounts;
mod adjustment;
pub use adjustment::AdjustmentRule;
mod agency_attendance;
pub use agency_attendance::{
    agency_shift_id, AgencyAttendanceInput, AgencyAttendanceOutcome,
    AgencyObservationFundingReceipt, CityPdAttendance, MAX_AGENCY_ATTENDANCE_PER_PERIOD,
};
mod aid;
pub use aid::*;
mod collection;
mod collection_funding;
pub use collection::{
    collection_contribution_id, CollectionOutcome, CollectionReceipt, CollectionResolveInput,
};
mod capacity;
mod catalog;
mod clearing;
mod equipment;
mod financial;
mod household_lifecycle;
mod household_time;
pub use household_lifecycle::{
    reconcile_resident_workforce, HouseholdLifecycleBook, HouseholdLifecyclePosition,
    HouseholdLifecycleRates, HouseholdLifecycleReceipt, ResidentAges, ResidentWorkforceAttrition,
};
mod inventory;
mod maintenance;
mod model;
mod payments;
mod production;
mod recurring;
mod services;
mod staffing;
mod tiers;
mod transition;
mod valuation;
mod wire;

pub use accounts::{
    AccountId, CashAccount, CashTransferPurpose, CompanyId, FundedShift, MonetaryBook,
    MonetaryBookSnapshot, MonetaryError, MoneyLocation, MoneyPosting, MoneyTransferPurpose,
    MoneyTransferReceipt, OrganizationAccountId, PublicAccountId, PurchaseEscrow,
    PurchaseMovementReceipt, ShiftId, ShiftState, WageAccrualReceipt,
};
pub use catalog::{MaterialCatalog, MaterialCatalogDefinition};
pub use clearing::{
    clear_ladder_market, clear_market, BidRung, LadderBid, LadderOutcome, MarketBid,
    MarketClearingPolicy, MarketClearingReceipt, MarketMoment, MarketOutcome,
};
pub use equipment::{
    equipment_installation_id, equipment_purchase_order_id, EquipmentAssetId, EquipmentBinding,
    EquipmentCarryingValue, EquipmentCohortId, EquipmentDefinition, EquipmentDefinitionId,
    EquipmentPosition, EquipmentWearReceipt, InstallationDecisionReceipt, InstallationId,
    InstallationInput, InstallationPolicy, InstallationReceipt, InstallationTarget,
    InstalledEquipmentCohort, InvestmentPolicy, InvestmentReceipt, PendingInstallation,
    ProductiveEquipment, RollingProcessSupply,
};
mod portfolio;
pub use financial::{
    validate_company_distributions, validate_distribution_receipts, CapitalContributionOrder,
    CapitalContributionReceipt, CompanyDistributionReceipt, CompanyPayoutPolicy, ContributionId,
    DistributionPolicy, DistributionReceipt, FinancialInstitutions, InstitutionLocation,
    LayoffRecord, OwnershipClaim, PublicAllocation, PublicBudget, PublicBudgetReceipt,
    PublicProgram, PublicProgramKey, PublicProgramReceipt, PublicProgramTerms, PublicSpendingRule,
    PublicTransferTreatment, TaxBasis, TaxPolicy, TaxReceipt, MAX_LAYOFF_HALF_PERIODS,
    MAX_LAYOFF_PERIODS,
};
pub use household_time::{
    consume_household_contributions, HouseholdContributionReceipt, HouseholdContributionUse,
    HouseholdTimeAccounting, HouseholdTimeBook, HouseholdTimeCommitment, HouseholdTimePolicy,
    HouseholdTimeReceipt, HouseholdUnmetTimeBurden,
};
pub use model::*;
pub use payments::{
    admit_material_purchase, member_shift_id, CircuitAccounting, EmploymentTerms,
    LaborCompensation, LaborUseReceipt, MaterialPurchase, MemberLaborUseReceipt, MonetaryCircuit,
    MAX_MONEY_TRANSFERS_PER_PERIOD,
};
pub use portfolio::{
    CompanyCondition, CompanyConditionOrder, CompanyPortfolio, CompanyPortfolioEvidence,
    CompanyPortfolioPolicy, CompanyPortfolioRegister, CompanyPortfolioSelection,
    CompanyProcessEvidence, CompanyProcessPlan, COMPANY_PORTFOLIO_DOMAIN,
};
pub use recurring::*;
pub use services::{
    recurring_service_order_id, recurring_service_topup_order_id, CommodityDefinition,
    CommodityKind, HouseholdServiceReceipt, ServiceConnection, ServiceInputPolicy,
    ServiceMarketReceipt, ServiceOrder, ServiceOutputReceipt, ServicePerformanceReceipt,
    ServicePriceDecision, ServiceStage, MAX_SERVICE_RECEIPTS_PER_PERIOD,
};
pub use staffing::{
    advance_staffing, distribute_staffing_members, MemberLaborCapacityRow, StaffingError,
    StaffingMemberBinding, StaffingMemberId, StaffingMemberReceipt, StaffingMemberState,
    StaffingPolicy, StaffingPoolBinding, StaffingPoolId, StaffingPoolState, StaffingReceipt,
    StaffingState, StaffingTransition, StaffingWorkRequest, StaffingWorkSource,
    MAX_STAFFING_MEMBERS,
};
pub use valuation::{
    CapitalAccount, CompanyBasisAsset, CompanyBasisMovement, CompanySale, EquityCarryingValue,
    FreightCarryingValue, HistoricalCostBook, HistoricalCostSnapshot, IncomeReceipt,
    IncomeStatement, StockCarryingValue, MAX_CARRYING_STOCKS, MAX_COMPANY_BASIS_MOVEMENTS,
};

pub use tiers::{
    household_standard, recurring_household_want_order_id, recurring_service_want_order_id,
    HouseholdStandard, HouseholdTierReceipt, HouseholdWantReceipt,
};
pub use transition::{
    advance_material_circuit, advance_material_circuit_with_aid, close_material_period,
    close_material_period_with_aid, close_material_period_with_portfolios,
    close_material_period_with_support, ClosedMaterialPeriod,
};
pub use wire::{
    decode_material_circuit_state, decode_material_circuit_state_for_encoding,
    encode_material_circuit_state, material_circuit_state_digest, DecodedMaterialCircuitState,
    MATERIAL_CIRCUIT_LIFECYCLE_PUBLIC_PROGRAMS_STATE_SCHEMA_VERSION,
    MATERIAL_CIRCUIT_LIFECYCLE_STATE_SCHEMA_VERSION,
    MATERIAL_CIRCUIT_PUBLIC_PROGRAMS_STATE_SCHEMA_VERSION, MATERIAL_CIRCUIT_SOURCE_SHA256,
    MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES, MATERIAL_CIRCUIT_STATE_SCHEMA_VERSION,
};
