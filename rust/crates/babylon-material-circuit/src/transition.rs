//! Pure per-period transition for the exact routed material circuit.

mod merchant_admission;

pub(crate) mod outbound;

#[path = "transition/state.rs"]
mod state;

pub use state::{
    advance_material_circuit, advance_material_circuit_with_aid, close_material_period,
    close_material_period_with_aid, close_material_period_with_support, ClosedMaterialPeriod,
};
#[allow(unused_imports)]
use state::{
    begin_close, canonicalize_outbound_receipts, canonicalize_rows, check_row_limits,
    close_due_aid, close_due_freight, close_funded_production, close_household_finance,
    close_household_reproduction, dispatch_and_replenish, execute_production_stages,
    expected_stage_arrival, finish_close_accounting, following_period, freight_lot_id,
    freight_step, grams_per_unit, loss_quantity, next_plans, order_index, process_due_freight,
    rebuild_backlog, recurring_merchant_hours, refund_lost_aid, route_stages, site_node,
    staffing_work_owners, stage_capacities, supplier_routes, validate_next_labor,
    validate_orders_and_freight, validate_route_stages, validate_routes, validate_unique_rows,
    AidResolve, CapacityKey, CloseOpening, DueFreightReceipts, FinalAccountingReceipts,
    FreightStep, FundedProductionReceipts, HouseholdCloseReceipts, HouseholdSupportInputs,
    NextPlans, ProductionStageReceipts, SupplierKey, SupplyPath,
};
#[allow(unused_imports)]
pub(crate) use state::{canonical_state, check_order_principal_limits, has_duplicate};

#[allow(unused_imports)]
use crate::inventory::{
    credit_inventory, debit_inventory, publish_inventory, take_inventory, InventoryKey,
    InventoryLedger,
};
#[allow(unused_imports)]
use crate::production::{
    derive_shared_labor_requests, derive_shared_production, execute_shared_production,
};
#[allow(unused_imports)]
use crate::valuation::CostClose;
#[allow(unused_imports)]
use crate::{
    ArrivalReceipt, BacklogRow, CorridorId, DeliveryReceipt, FreightLossReceipt, FreightLotId,
    GoodId, InventoryRow, LaborCapacityRow, MaterialCircuitError, MaterialCircuitState,
    MaterialCircuitTransition, OrderId, RealizationReceipt, RouteId, RouteStage,
    RoutedDispatchReceipt, RoutedFreightLot, SiteId, StaffingPoolBinding, StaffingWorkRequest,
    UnitId, FREIGHT_LOSS_PARTS_PER_MILLION, MAX_MATERIAL_CIRCUIT_ROWS, MAX_ROUTE_STAGES_PER_ROUTE,
};
#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
