//! One shared native-unit resource allocator for routed and local outbound work.

mod residual;

#[path = "outbound/orders.rs"]
mod orders;

#[allow(unused_imports)]
pub(crate) use orders::allocate_services;
#[allow(unused_imports)]
use orders::{
    add_aid_requests, add_request, add_route_requests, allocation_matrix, apply_aid_dispatches,
    apply_dispatches, apply_handling, apply_local_fulfillments, apply_local_transfer,
    apply_one_aid_dispatch, canonical_requests, complete_allocations, labor_groups, labor_index,
    limit_allocations, order_allocations, outbound_orders, reserve_route_capacity,
    resource_available, resource_groups, FreightRequest, FreightResourceKey, OutboundOrder,
};
#[allow(unused_imports)]
pub(super) use orders::{
    credit_local_transfers, dispatch_orders, dispatch_orders_with_aid, ensure_resource_group_count,
    AidDispatch, OutboundReceipts, OutboundSelection,
};

#[allow(unused_imports)]
use super::merchant_admission::{hours_per_unit, merchant};
#[allow(unused_imports)]
use super::{
    credit_inventory, debit_inventory, freight_lot_id, grams_per_unit, route_stages,
    stage_capacities, supplier_routes, BTreeMap, CapacityKey, InventoryKey, InventoryLedger,
    MaterialCircuitError, MaterialCircuitState, RouteId, RoutedDispatchReceipt, RoutedFreightLot,
    SiteId, SupplierKey, SupplyPath, UnitId,
};
#[allow(unused_imports)]
use crate::production::proportional_floor;
#[allow(unused_imports)]
use crate::valuation::CostClose;
#[allow(unused_imports)]
use crate::{
    LocalRetailFulfillmentReceipt, LocalTransferReceipt, MerchantHandlingReceipt, OutboundOrderId,
    SupplierTransport, MAX_FREIGHT_RESOURCE_REQUESTS,
};
