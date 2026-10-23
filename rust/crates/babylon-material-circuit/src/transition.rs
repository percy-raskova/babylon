//! Pure per-period transition for the exact routed material circuit.

mod merchant_admission;

pub(crate) mod outbound;

#[path = "transition/state.rs"]
mod state;

pub use state::{
    advance_material_circuit, advance_material_circuit_with_aid, close_material_period,
    close_material_period_with_aid, close_material_period_with_support, ClosedMaterialPeriod,
};
pub(crate) use state::{canonical_state, check_order_principal_limits, has_duplicate};
use state::{
    freight_lot_id, grams_per_unit, route_stages, site_node, stage_capacities, supplier_routes,
    CapacityKey, SupplierKey, SupplyPath,
};

use crate::inventory::{credit_inventory, debit_inventory, InventoryKey, InventoryLedger};
use crate::{
    MaterialCircuitError, MaterialCircuitState, RouteId, RoutedDispatchReceipt, RoutedFreightLot,
    SiteId, UnitId,
};
use std::collections::{BTreeMap, BTreeSet};
