//! Standalone evidence for actual installation, wear and contingent purchase decisions.
use super::{EquipmentCohortId, InstallationId, Result};
use crate::{MaterialCircuitError, OrderId, ProcessId, SiteId};
use babylon_kernel::currency::Currency;
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstallationReceipt {
    pub period: u64,
    pub id: InstallationId,
    pub process_id: ProcessId,
    pub site_id: SiteId,
    pub units: u64,
    pub started: bool,
    pub opening_hours: u64,
    pub used_hours: u64,
    pub remaining_hours: u64,
    pub usable_from_period: u64,
    pub opening_carrying: Currency,
    pub materials_capitalized: Currency,
    pub wages_capitalized: Currency,
    pub closing_carrying: Currency,
}
impl InstallationReceipt {
    /// # Errors
    /// Refuses inconsistent work, timing, or historical carrying amounts.
    pub fn validate(&self) -> Result<()> {
        let next = self
            .period
            .checked_add(1)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        if self.period == 0
            || self.units == 0
            || self.opening_hours == 0
            || self.used_hours.checked_add(self.remaining_hours) != Some(self.opening_hours)
            || self.usable_from_period != if self.remaining_hours == 0 { next } else { 0 }
            || (self.used_hours == 0 && self.wages_capitalized.micro_units() != 0)
            || (!self.started && self.materials_capitalized.micro_units() != 0)
            || (self.started && self.opening_carrying.micro_units() != 0)
            || [
                self.opening_carrying,
                self.materials_capitalized,
                self.wages_capitalized,
                self.closing_carrying,
            ]
            .iter()
            .any(|v| v.micro_units() < 0)
            || self
                .opening_carrying
                .checked_add(self.materials_capitalized)
                .and_then(|v| v.checked_add(self.wages_capitalized))
                .map_err(|_| MaterialCircuitError::Arithmetic)?
                != self.closing_carrying
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
        Ok(())
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EquipmentWearReceipt {
    pub period: u64,
    pub cohort_id: EquipmentCohortId,
    pub process_id: ProcessId,
    pub site_id: SiteId,
    pub opening_service_batches: u64,
    pub used_batches: u64,
    pub remaining_service_batches: u64,
    pub opening_carrying: Currency,
    pub carried_to_output: Currency,
    pub closing_carrying: Currency,
}
impl EquipmentWearReceipt {
    /// # Errors
    /// Refuses inconsistent productive use or transferred cost.
    pub fn validate(&self) -> Result<()> {
        if self.period == 0
            || self.used_batches == 0
            || self
                .used_batches
                .checked_add(self.remaining_service_batches)
                != Some(self.opening_service_batches)
            || [
                self.opening_carrying,
                self.carried_to_output,
                self.closing_carrying,
            ]
            .iter()
            .any(|v| v.micro_units() < 0)
            || self
                .carried_to_output
                .checked_add(self.closing_carrying)
                .map_err(|_| MaterialCircuitError::Arithmetic)?
                != self.opening_carrying
            || (self.remaining_service_batches == 0 && self.closing_carrying.micro_units() != 0)
            || crate::valuation::portion(
                self.opening_carrying,
                self.opening_service_batches,
                self.used_batches,
            )? != self.carried_to_output
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
        Ok(())
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InvestmentReceipt {
    pub period: u64,
    pub order_id: OrderId,
    pub process_id: ProcessId,
    pub site_id: SiteId,
    pub supplier_site_id: SiteId,
    pub installed_units: u64,
    pub pending_units: u64,
    pub on_hand_units: u64,
    pub outstanding_inbound_units: u64,
    pub captured_plan_batches: u64,
    /// Outstanding goods commitments at this close; completed service sales are absent.
    pub accepted_output_orders: u64,
    pub output_stock: u64,
    pub output_buffer: u64,
    pub replacement_requested_units: u64,
    pub expansion_requested_units: u64,
    pub admitted_units: u64,
    pub unit_price: Currency,
    pub free_cash: Currency,
    pub earnings_budget: Currency,
}
impl InvestmentReceipt {
    /// # Errors
    /// Refuses unfunded admission or negative evidence; intent is not delivered capacity.
    pub fn validate(&self) -> Result<()> {
        let requested = self
            .replacement_requested_units
            .checked_add(self.expansion_requested_units)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let amount = self
            .unit_price
            .micro_units()
            .checked_mul(i128::from(self.admitted_units))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let expansion_cost = self
            .unit_price
            .micro_units()
            .checked_mul(i128::from(
                self.admitted_units
                    .saturating_sub(self.replacement_requested_units),
            ))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        if self.period == 0
            || self.site_id == self.supplier_site_id
            || expansion_cost > self.earnings_budget.micro_units()
            || self.unit_price.micro_units() <= 0
            || self.free_cash.micro_units() < 0
            || self.earnings_budget.micro_units() < 0
            || self.admitted_units > requested
            || amount > self.free_cash.micro_units()
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
        Ok(())
    }
}

/// Target evidence at installation admission, after actual current productive wear.
/// Captured plans express a decision, not a claim that demand will clear.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstallationDecisionReceipt {
    pub period: u64,
    pub process_id: ProcessId,
    pub site_id: SiteId,
    pub captured_plan_batches: u64,
    pub target_units: u64,
    pub installed_units: u64,
    pub pending_units: u64,
    pub requested_units: u64,
    pub started_units: u64,
}
impl InstallationDecisionReceipt {
    /// # Errors
    /// Refuses inconsistent position, requested deficit or actual starts.
    pub fn validate(&self) -> Result<()> {
        let position = self
            .installed_units
            .checked_add(self.pending_units)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        if self.period == 0
            || self.requested_units != self.target_units.saturating_sub(position)
            || self.started_units > self.requested_units
        {
            return Err(MaterialCircuitError::EquipmentInvariant);
        }
        Ok(())
    }
}
