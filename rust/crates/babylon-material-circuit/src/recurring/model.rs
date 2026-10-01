//! Captured recurring policies and current stocks; quantities retain their units.

use crate::{FinalDemandPrincipalId, GoodId, OrderId, ProcessId, SiteId, UnitId};
use babylon_kernel::currency::Currency;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecurringEconomy {
    pub households: Vec<HouseholdCohort>,
    pub household_stocks: Vec<HouseholdStock>,
    pub household_needs: Vec<HouseholdNeed>,
    pub household_purchases: Vec<HouseholdPurchasePolicy>,
    pub offers: Vec<SellerOffer>,
    pub replenishment: Vec<ReplenishmentPolicy>,
    pub production: Vec<ProductionDemandPolicy>,
    pub attendance: Vec<AttendancePlan>,
    /// Both cursors equal the preceding period at a canonical opening.
    pub last_household_admission_period: u64,
    pub last_household_consumption_period: u64,
}

/// Resident persons and household count are independent of workplace jobs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdCohort {
    pub principal_id: FinalDemandPrincipalId,
    pub households: u64,
    pub persons: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdStock {
    pub principal_id: FinalDemandPrincipalId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub quantity: u64,
}

/// Need survives absent purchases and unemployment; no unmet-demand carryover.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdNeed {
    pub principal_id: FinalDemandPrincipalId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub units_per_person: u64,
}

/// One preferred local retailer per resident good/unit requirement.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdPurchasePolicy {
    pub principal_id: FinalDemandPrincipalId,
    pub retailer_site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub target_closing_stock: u64,
    pub maximum_purchase: u64,
    pub enabled: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SellerOffer {
    pub site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub unit_price: Currency,
    pub pricing: PricePolicy,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PricePolicy {
    Fixed,
    Responsive {
        minimum: Currency,
        maximum: Currency,
        step: Currency,
        target_stock: u64,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReplenishmentPolicy {
    pub buyer_site_id: SiteId,
    pub supplier_site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub target_stock: u64,
    pub maximum_purchase: u64,
    pub cash_floor: Currency,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProductionDemandPolicy {
    pub process_id: ProcessId,
    pub site_id: SiteId,
    pub output_buffer: u64,
    pub planned_batches: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AttendancePlan {
    pub site_id: SiteId,
    pub unit_id: UnitId,
    pub period: u64,
    pub planned_hours: u64,
}

/// The quoted order identity exists as evidence even for a zero admission.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdDemandReceipt {
    pub period: u64,
    pub principal_id: FinalDemandPrincipalId,
    pub retailer_site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub order_id: OrderId,
    pub opening_stock: u64,
    pub required_quantity: u64,
    pub desired_quantity: u64,
    pub requested_quantity: u64,
    pub admitted_quantity: u64,
    pub fulfilled_quantity: u64,
    pub expired_quantity: u64,
    pub unit_price: Currency,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdConsumptionReceipt {
    pub period: u64,
    pub principal_id: FinalDemandPrincipalId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub required_quantity: u64,
    pub available_quantity: u64,
    pub consumed_quantity: u64,
    pub unmet_quantity: u64,
    pub closing_quantity: u64,
}
