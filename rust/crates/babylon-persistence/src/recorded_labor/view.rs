//! The view of one period that the recorded-labor fold reads: the two states either side of it and the
//! receipts the fold needs, borrowed and in the order of their source.
use babylon_material_circuit::{
    AidReceipt, ArrivalReceipt, CollectionReceipt, EquipmentWearReceipt, FinalDemandPrincipalId,
    FreightLossReceipt, HouseholdConsumptionReceipt, HouseholdServiceReceipt, InstallationReceipt,
    LocalRetailFulfillmentReceipt, LocalTransferReceipt, MaintenanceReceipt, MaterialCircuitState,
    MerchantHandlingReceipt, ProcurementReceipt, ProductionReceipt, RoutedDispatchReceipt,
    ServiceOutputReceipt, ServicePerformanceReceipt, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;

/// One agency observation as hours of one household: what the fold needs of an `AgencyPaidReceipt`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct AgencyHours {
    pub principal_id: FinalDemandPrincipalId,
    pub labor_unit_id: UnitId,
    pub hours: u64,
}

/// The receipts of one period that the fold reads, borrowed; every list in the order of its source.
pub(crate) struct ReceiptView<'a> {
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
pub(crate) struct PeriodView<'a> {
    pub period: u64,
    pub before: &'a MaterialCircuitState,
    pub after: &'a MaterialCircuitState,
    pub receipts: ReceiptView<'a>,
}

/// The agency rows of the tick's receipts as hours by household, in their order.
pub(crate) fn agency_hours(receipts: &MaterialTickReceipts) -> Vec<AgencyHours> {
    receipts
        .agency_paid
        .iter()
        .map(|row| AgencyHours {
            principal_id: row.principal_id,
            labor_unit_id: row.labor_unit_id,
            hours: row.hours,
        })
        .collect()
}

/// The view of the tick's receipts; `agency` is `agency_hours(receipts)`, kept by the caller.
pub(crate) fn receipt_view<'a>(
    receipts: &'a MaterialTickReceipts,
    agency: &'a [AgencyHours],
) -> ReceiptView<'a> {
    ReceiptView {
        aid: &receipts.aid,
        collections: &receipts.collections,
        agency,
        installation: &receipts.installation,
        equipment_wear: &receipts.equipment_wear,
        maintenance: receipts.maintenance.as_ref(),
        production: &receipts.production,
        dispatches: &receipts.dispatches,
        losses: &receipts.losses,
        arrivals: &receipts.arrivals,
        handling: &receipts.handling,
        local_fulfillments: &receipts.local_fulfillments,
        local_transfers: &receipts.local_transfers,
        procurement: &receipts.procurement,
        service_outputs: &receipts.service_outputs,
        service_performance: &receipts.service_performance,
        household_services: &receipts.household_services,
        household_consumption: &receipts.household_consumption,
    }
}
