//! The map of the tick's receipts into the view of one period that the fold reads.
use babylon_recorded_labor::{AgencyHours, ReceiptView};
use babylon_tick::material_world::MaterialTickReceipts;

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
