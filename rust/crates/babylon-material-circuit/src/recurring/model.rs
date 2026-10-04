//! Captured recurring policies and current stocks; quantities retain their units.

use crate::{FinalDemandPrincipalId, GoodId, OrderId, ProcessId, SiteId, UnitId};
use babylon_kernel::currency::Currency;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecurringEconomy {
    pub service_inputs: Vec<crate::ServiceInputPolicy>,
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
    pub kind: HouseholdKind,
    pub principal_id: FinalDemandPrincipalId,
    pub households: u64,
    pub persons: u64,
}

/// Collective residence accounts carry people without inventing households.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum HouseholdKind {
    Ordinary = 1,
    CollectiveResidence = 2,
}
impl HouseholdKind {
    #[must_use]
    pub const fn admits_counts(self, persons: u64, households: u64) -> bool {
        match self {
            Self::Ordinary => households > 0 && persons >= households,
            Self::CollectiveResidence => persons > 0 && households == 0,
        }
    }
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
    pub basis: HouseholdNeedBasis,
    pub units_per_basis: u64,
}

/// Distinct material requirements may depend on residents or occupied households.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum HouseholdNeedBasis {
    Persons = 1,
    Households = 2,
}

impl HouseholdNeed {
    /// Exact recurring requirement; this calculation changes neither count.
    /// # Errors
    /// Refuses the wrong principal, household-based collective needs, zero coefficients and overflow.
    pub fn required_quantity(
        &self,
        cohort: &HouseholdCohort,
    ) -> Result<u64, crate::MaterialCircuitError> {
        if cohort.principal_id != self.principal_id
            || (cohort.kind == HouseholdKind::CollectiveResidence
                && self.basis == HouseholdNeedBasis::Households)
        {
            return Err(crate::MaterialCircuitError::FinalDemandInvariant);
        }
        if self.units_per_basis == 0 {
            return Err(crate::MaterialCircuitError::ZeroQuantity);
        }
        let count = match self.basis {
            HouseholdNeedBasis::Persons => cohort.persons,
            HouseholdNeedBasis::Households => cohort.households,
        };
        count
            .checked_mul(self.units_per_basis)
            .ok_or(crate::MaterialCircuitError::Arithmetic)
    }
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
    ServiceResponsive {
        minimum: Currency,
        maximum: Currency,
        step: Currency,
    },
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
