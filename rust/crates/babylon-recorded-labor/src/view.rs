//! The view of one period that the recorded-labor fold reads: the two states either side of it and the
//! receipts the fold needs, borrowed and in the order of their source.
use babylon_material_circuit::{
    AidReceipt, ArrivalReceipt, CollectionReceipt, EquipmentWearReceipt, FinalDemandPrincipalId,
    FreightLossReceipt, HouseholdConsumptionReceipt, HouseholdServiceReceipt, InstallationReceipt,
    LocalRetailFulfillmentReceipt, LocalTransferReceipt, MaintenanceReceipt, MaterialCircuitState,
    MerchantHandlingReceipt, ProcurementReceipt, ProductionReceipt, RoutedDispatchReceipt,
    ServiceOutputReceipt, ServicePerformanceReceipt, UnitId,
};

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
    pub household_consumption: &'a [HouseholdConsumptionReceipt],
}

/// One period: the number it closes, the states either side of it, and its receipts.
pub struct PeriodView<'a> {
    pub period: u64,
    pub before: &'a MaterialCircuitState,
    pub after: &'a MaterialCircuitState,
    pub receipts: ReceiptView<'a>,
}
