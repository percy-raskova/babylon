//! Canonical current routed-material state bytes for restart and replay.

mod accounting;

mod aid;

mod capacity;

mod equipment;

mod financial;

mod household_time;

mod recurring;

#[cfg(test)]
mod row_limits_tests;

mod services;

mod valuation;

#[path = "wire/state.rs"]
mod state;

#[allow(unused_imports)]
use state::{
    append_backlog, append_bounded_rows, append_capacities, append_commitments,
    append_corridor_capacities, append_final_demand_orders, append_final_demand_principals,
    append_freight, append_handling_coefficients, append_input_coefficients, append_inventory,
    append_labor, append_labor_coefficients, append_maintenance, append_merchants, append_orders,
    append_process_outputs, append_route_stages, append_rows, append_site_nodes,
    append_stage_capacities, append_supplier_routes, decode_backlog, decode_bounded_rows,
    decode_capacities, decode_commitments, decode_corridor_capacities, decode_final_demand_orders,
    decode_final_demand_principals, decode_freight, decode_handling_coefficients,
    decode_input_coefficients, decode_inventory, decode_labor, decode_labor_coefficients,
    decode_maintenance_binding, decode_maintenance_service, decode_merchants, decode_orders,
    decode_process_outputs, decode_route_stages, decode_rows, decode_site_nodes,
    decode_stage_capacities, decode_supplier_routes, row_count, SCHEMA_VERSION,
};
pub use state::{
    decode_material_circuit_state, encode_material_circuit_state, material_circuit_state_digest,
    MATERIAL_CIRCUIT_SOURCE_SHA256, MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES,
};
#[allow(unused_imports)]
pub(crate) use state::{Cursor, CursorError};

#[allow(unused_imports)]
use crate::transition::canonical_state;
#[allow(unused_imports)]
use crate::SupplierTransport;
#[allow(unused_imports)]
use crate::{
    BacklogRow, CapacityRow, CorridorCapacity, CorridorId, FreightLotId, GoodId,
    InputOutputCoefficient, InventoryRow, LaborCapacityRow, LaborCoefficient, LogisticsNodeId,
    MaterialCircuitError, MaterialCircuitState, OrderAccessMode, OrderId, OrderRow, ProcessId,
    ProcessOutput, ProductionCommitment, RouteId, RouteStage, RouteStageCapacity, RoutedFreightLot,
    SiteId, SiteLogisticsNode, SupplierRoute, UnitId, MAX_MATERIAL_CIRCUIT_ROWS,
};
#[allow(unused_imports)]
use crate::{
    FinalDemandOrder, FinalDemandPrincipal, FinalDemandPrincipalId, MerchantHandling,
    MerchantHandlingCoefficient, MerchantRole,
};
#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use babylon_kernel::economic_location::EconomicLocation;
