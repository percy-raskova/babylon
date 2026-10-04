//! Current service claims and native-unit performance; no durable service stock.
use crate::{AccountId, GoodId, OrderId, ProcessId, SiteId, UnitId};
use babylon_kernel::currency::Currency;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum ServiceStage {
    UtilityProvision = 1,
    LocalServiceProvision = 2,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum CommodityKind {
    Storable { grams_per_unit: u64 },
    PeriodService { stage: ServiceStage },
}
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct CommodityDefinition {
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub kind: CommodityKind,
}

/// Captured technical reach; geographic eligibility belongs to source compilation.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct ServiceConnection {
    pub provider_site_id: SiteId,
    pub buyer: AccountId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
}
/// A funded claim for exactly one period. No performance is carried at an opening.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct ServiceOrder {
    pub order_id: OrderId,
    pub performance_period: u64,
    pub provider_site_id: SiteId,
    pub buyer: AccountId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub quantity: u64,
}
/// Captured bounds on recipe-derived current service requirements.
/// `quantity_per_period` is a cap; absent committed production requests nothing.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ServiceInputPolicy {
    pub buyer_site_id: SiteId,
    pub provider_site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub quantity_per_period: u64,
    pub maximum_purchase: u64,
    pub cash_floor: Currency,
}
/// Used and unused partition performance; performance and expiry partition admission.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ServicePerformanceReceipt {
    pub period: u64,
    pub order_id: OrderId,
    pub provider_site_id: SiteId,
    pub buyer: AccountId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub requested_quantity: u64,
    pub admitted_quantity: u64,
    pub performed_quantity: u64,
    pub used_quantity: u64,
    pub unused_quantity: u64,
    pub expired_quantity: u64,
    pub unit_price: Currency,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdServiceReceipt {
    pub period: u64,
    pub principal_id: crate::FinalDemandPrincipalId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub required_quantity: u64,
    pub performed_quantity: u64,
    pub satisfied_quantity: u64,
    pub unmet_quantity: u64,
    pub unused_quantity: u64,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum ServicePriceDecision {
    Fixed = 1,
    Hold = 2,
    FundedUnmet = 3,
    CostPressure = 4,
    SpareCapacity = 5,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ServiceMarketReceipt {
    pub period: u64,
    pub next_period: u64,
    pub process_id: ProcessId,
    pub site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub requested_quantity: u64,
    pub admitted_quantity: u64,
    pub performed_quantity: u64,
    pub available_capacity: u64,
    pub direct_cost: Currency,
    pub old_price: Currency,
    pub next_price: Currency,
    pub reason: ServicePriceDecision,
    pub planned_quantity: u64,
}
/// Complete produced batches partition into acquired grants and unallocated expiry.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ServiceOutputReceipt {
    pub period: u64,
    pub process_id: ProcessId,
    pub site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub produced_quantity: u64,
    pub allocated_quantity: u64,
    pub expired_quantity: u64,
    pub direct_cost: Currency,
    pub expired_cost: Currency,
}
impl ServiceOutputReceipt {
    /// Validate the native output and historical-cost partitions.
    /// # Errors
    /// Refuses nonpositive periods, negative costs or inconsistent expiry.
    pub fn validate(&self) -> Result<(), crate::MaterialCircuitError> {
        if self.period == 0
            || self.allocated_quantity.checked_add(self.expired_quantity)
                != Some(self.produced_quantity)
            || self.direct_cost.micro_units() < 0
            || self.expired_cost.micro_units() < 0
            || self.expired_cost > self.direct_cost
            || (self.produced_quantity == 0 && self.direct_cost.micro_units() != 0)
            || (self.expired_quantity == 0 && self.expired_cost.micro_units() != 0)
            || (self.allocated_quantity == 0 && self.expired_cost != self.direct_cost)
        {
            return Err(crate::MaterialCircuitError::ServiceInvariant);
        }
        Ok(())
    }
}
/// Independent close ceiling, including captured orders and zero-admission requests.
pub const MAX_SERVICE_RECEIPTS_PER_PERIOD: usize = 3 * crate::MAX_MATERIAL_CIRCUIT_ROWS;

impl ServicePerformanceReceipt {
    /// Check quantity partitions without claiming knowledge of absent production state.
    /// # Errors
    /// Refuses nonpositive periods/prices, identical parties and inconsistent partitions.
    pub fn validate(&self) -> Result<(), crate::MaterialCircuitError> {
        if self.period == 0
            || self.unit_price.micro_units() <= 0
            || self.buyer == AccountId::Site(self.provider_site_id)
            || !matches!(self.buyer, AccountId::Site(_) | AccountId::Household(_))
            || self
                .unit_price
                .micro_units()
                .checked_mul(i128::from(self.admitted_quantity))
                .is_none()
            || self.admitted_quantity > self.requested_quantity
            || self.performed_quantity.checked_add(self.expired_quantity)
                != Some(self.admitted_quantity)
            || self.used_quantity.checked_add(self.unused_quantity) != Some(self.performed_quantity)
        {
            return Err(crate::MaterialCircuitError::ServiceInvariant);
        }
        Ok(())
    }
}
impl HouseholdServiceReceipt {
    /// Check current satisfaction and unmet need independently of stored consumption.
    /// # Errors
    /// Refuses impossible or unpartitioned current-period quantities.
    pub fn validate(&self) -> Result<(), crate::MaterialCircuitError> {
        if self.period == 0
            || self.required_quantity == 0
            || self.satisfied_quantity != self.required_quantity.min(self.performed_quantity)
            || self.satisfied_quantity.checked_add(self.unmet_quantity)
                != Some(self.required_quantity)
            || self.satisfied_quantity.checked_add(self.unused_quantity)
                != Some(self.performed_quantity)
        {
            return Err(crate::MaterialCircuitError::ServiceInvariant);
        }
        Ok(())
    }
}
impl ServiceMarketReceipt {
    /// Validate standalone market direction and finite production evidence.
    /// # Errors
    /// Refuses invalid bounds, periods, money or unexplained direction.
    pub fn validate(&self) -> Result<(), crate::MaterialCircuitError> {
        use crate::MaterialCircuitError::ServiceInvariant;
        if self.period == 0
            || self.period.checked_add(1) != Some(self.next_period)
            || self.old_price.micro_units() <= 0
            || self.next_price.micro_units() <= 0
            || self.direct_cost.micro_units() < 0
            || self.performed_quantity > self.admitted_quantity
            || self.admitted_quantity > self.requested_quantity
            || self.performed_quantity > self.available_capacity
            || self.planned_quantity < self.requested_quantity
        {
            return Err(ServiceInvariant);
        }
        let comparison = self
            .old_price
            .micro_units()
            .checked_mul(i128::from(self.performed_quantity))
            .ok_or(crate::MaterialCircuitError::Arithmetic)?;
        let valid = match self.reason {
            ServicePriceDecision::Fixed | ServicePriceDecision::Hold => {
                self.next_price == self.old_price
            }
            ServicePriceDecision::FundedUnmet => {
                self.admitted_quantity > self.performed_quantity
                    && self.next_price >= self.old_price
            }
            ServicePriceDecision::CostPressure => {
                self.admitted_quantity == self.performed_quantity
                    && self.performed_quantity > 0
                    && self.direct_cost.micro_units() > comparison
                    && self.next_price >= self.old_price
            }
            ServicePriceDecision::SpareCapacity => {
                self.admitted_quantity == self.performed_quantity
                    && self.performed_quantity < self.available_capacity
                    && (self.performed_quantity == 0 || self.direct_cost.micro_units() < comparison)
                    && self.next_price <= self.old_price
            }
        };
        if !valid {
            return Err(ServiceInvariant);
        }
        Ok(())
    }
}
