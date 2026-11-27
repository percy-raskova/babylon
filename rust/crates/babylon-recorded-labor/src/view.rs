//! The view of one period that the recorded-labor fold reads: the two states either side of it and the
//! receipts the fold needs, borrowed and in the order of their source.
use crate::model::RecordedLaborError;
use babylon_material_circuit::{
    AidReceipt, ArrivalReceipt, CollectionReceipt, EquipmentWearReceipt, FinalDemandPrincipalId,
    FreightLossReceipt, HouseholdConsumptionReceipt, HouseholdServiceReceipt, HouseholdWantReceipt,
    InstallationReceipt, LocalRetailFulfillmentReceipt, LocalTransferReceipt, MaintenanceReceipt,
    MaterialCircuitState, MerchantHandlingReceipt, OrderId, ProcurementReceipt, ProductionReceipt,
    RoutedDispatchReceipt, ServiceOutputReceipt, ServicePerformanceReceipt, UnitId,
};
use std::collections::BTreeMap;

/// One agency observation as hours of one household: what the fold needs of an `AgencyPaidReceipt`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct AgencyHours {
    pub principal_id: FinalDemandPrincipalId,
    pub labor_unit_id: UnitId,
    pub hours: u64,
}

/// The receipts of one period that the fold reads, borrowed; every list in the order of its source.
pub struct ReceiptView<'a> {
    pub aid: &'a [AidReceipt],
    pub collections: &'a [CollectionReceipt],
    pub agency: &'a [AgencyHours],
    pub installation: &'a [InstallationReceipt],
    pub equipment_wear: &'a [EquipmentWearReceipt],
    pub maintenance: Option<&'a MaintenanceReceipt>,
    pub production: &'a [ProductionReceipt],
    pub dispatches: &'a [RoutedDispatchReceipt],
    pub losses: &'a [FreightLossReceipt],
    pub arrivals: &'a [ArrivalReceipt],
    pub handling: &'a [MerchantHandlingReceipt],
    pub local_fulfillments: &'a [LocalRetailFulfillmentReceipt],
    pub local_transfers: &'a [LocalTransferReceipt],
    pub procurement: &'a [ProcurementReceipt],
    pub service_outputs: &'a [ServiceOutputReceipt],
    pub service_performance: &'a [ServicePerformanceReceipt],
    pub household_services: &'a [HouseholdServiceReceipt],
    /// What each household wanted and bought beyond its need, by tier.
    pub household_wants: &'a [HouseholdWantReceipt],
    pub household_consumption: &'a [HouseholdConsumptionReceipt],
}

/// One period: the number it closes, the states either side of it, and its receipts.
pub struct PeriodView<'a> {
    pub period: u64,
    pub before: &'a MaterialCircuitState,
    pub after: &'a MaterialCircuitState,
    pub receipts: ReceiptView<'a>,
}

impl PeriodView<'_> {
    /// The wants of the period that bought something, by the order each was placed under.
    ///
    /// # Errors
    /// Two such wants under one order: `RecordedLaborError`.
    pub(crate) fn bought_wants(
        &self,
    ) -> Result<BTreeMap<OrderId, &HouseholdWantReceipt>, RecordedLaborError> {
        let mut wants = BTreeMap::new();
        for want in self.receipts.household_wants {
            if want.period == self.period
                && want.bought_quantity > 0
                && wants.insert(want.order_id, want).is_some()
            {
                return Err(RecordedLaborError::ReceiptMismatch("household wants"));
            }
        }
        Ok(wants)
    }
}
