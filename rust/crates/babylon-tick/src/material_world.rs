//! Exact successor world-register ownership for the routed material circuit.
//!
//! An active register contains the complete current opening state, never an economic
//! summary or a second inventory ledger. The graph-only digest stays unchanged.

mod aid_receipt;

mod collection_receipt;

mod equipment_receipt;

mod financial_receipt;

mod household_time_receipt;

#[cfg(test)]
mod household_time_tests;

mod income_receipt;

mod installation_decision;

mod maintenance_receipt;

mod monetary_receipt;

pub(crate) mod organizer_collection;

mod organizer_support;

mod organizer_time;

mod recurring_receipt;

mod service_receipt;

mod workforce_receipt;

#[cfg(test)]
mod tests;

#[path = "material_world/register.rs"]
mod register;

#[allow(unused_imports)]
use register::{
    bounded_bytes, encode_bound_organizer, encode_handling_receipts, encode_material_receipts,
    maximum_material_receipt_bytes, organizer_workplace_facts, take_organizer_section,
    ReceiptCursor, NOMINAL_DOMAIN, RECEIPT_DOMAIN, REGISTER_DOMAIN,
};
pub use register::{
    decode_material_receipts, nominal_material_world_hash, receipt_row_limit,
    validate_retained_collection, MaterialTickReceipts, MaterialWorldError, MaterialWorldRegister,
    PreparedMaterialWorld, MAX_MATERIAL_TICK_RECEIPT_BYTES, MAX_MATERIAL_WORLD_REGISTER_BYTES,
    RECEIPT_FAMILY_COUNT, RECEIPT_ROW_BYTES,
};

#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use babylon_material_circuit::ArrivalReceipt;
#[allow(unused_imports)]
use babylon_material_circuit::DeliveryReceipt;
#[allow(unused_imports)]
use babylon_material_circuit::FinalDemandPrincipalId;
#[allow(unused_imports)]
use babylon_material_circuit::FreightLossReceipt;
#[allow(unused_imports)]
use babylon_material_circuit::FreightLotId;
#[allow(unused_imports)]
use babylon_material_circuit::GoodId;
#[allow(unused_imports)]
use babylon_material_circuit::LocalRetailFulfillmentReceipt;
#[allow(unused_imports)]
use babylon_material_circuit::LocalTransferReceipt;
#[allow(unused_imports)]
use babylon_material_circuit::MerchantHandlingReceipt;
#[allow(unused_imports)]
use babylon_material_circuit::OrderId;
#[allow(unused_imports)]
use babylon_material_circuit::OutboundOrderId;
#[allow(unused_imports)]
use babylon_material_circuit::ProcessId;
#[allow(unused_imports)]
use babylon_material_circuit::ProductionReceipt;
#[allow(unused_imports)]
use babylon_material_circuit::RealizationReceipt;
#[allow(unused_imports)]
use babylon_material_circuit::RouteId;
#[allow(unused_imports)]
use babylon_material_circuit::RoutedDispatchReceipt;
#[allow(unused_imports)]
use babylon_material_circuit::SiteId;
#[allow(unused_imports)]
use babylon_material_circuit::UnitId;
#[allow(unused_imports)]
use babylon_material_circuit::MAX_ROUTE_STAGES_PER_ROUTE;
#[allow(unused_imports)]
use babylon_material_circuit::{
    advance_material_circuit, decode_material_circuit_state, encode_material_circuit_state,
    MaterialCircuitError, MaterialCircuitState, MaterialCircuitTransition,
};
#[allow(unused_imports)]
use babylon_practice_contract::{
    decode_organizer_config, decode_organizer_state, encode_organizer_config,
    encode_organizer_state, OrganizerConfig, OrganizerError, OrganizerState,
    OrganizerWorkplaceFacts,
};
