//! Read-only presentation rows derived from a committed material envelope.
//! These rows report exact stocks and receipts; they never adjudicate a tick.

mod freight_orders;

mod physical_routes;

pub(crate) use freight_orders::FreightOrderRegistry;

pub use freight_orders::{freight_order_identity, FreightOrderError, FreightOrderIndex};

pub use physical_routes::{PhysicalRouteError, PhysicalRouteIndex};

#[path = "production_observation/snapshot.rs"]
mod snapshot;

pub use snapshot::{
    CompletedProductionFinalDemand, CompletedProductionFreightCapacity, CompletedProductionLabor,
    CompletedProductionMaintenance, CompletedProductionMerchantHandling,
    CompletedProductionStaffing, CompletedProductionStaffingMember, DesignedProcessAttribution,
    ObservedKnownSubtotal, ObservedNationalCohortContext, ObservedSectorContext,
    PhysicalRouteDefinition, ProductionAidCapacityOrder, ProductionBusinessSubject,
    ProductionCapacityKind, ProductionDeliveryEvidence, ProductionDeliveryStage, ProductionEvent,
    ProductionFinalDemandAccount, ProductionFinalDemandOrder, ProductionFreight,
    ProductionFreightCapacityAccount, ProductionFreightCapacityOrder,
    ProductionFreightOrderDefinition, ProductionFreightReservation, ProductionHandlingCoefficient,
    ProductionInput, ProductionLabor, ProductionLaborAccount, ProductionLaborCompensation,
    ProductionMaintenanceAccount, ProductionMerchantHandlingAccount,
    ProductionMerchantHandlingOrder, ProductionOutboundKind, ProductionPhysicalEdge,
    ProductionProcess, ProductionRoadSource, ProductionRoute, ProductionRouteStage,
    ProductionRouteTransport, ProductionSite, ProductionSiteRole, ProductionSnapshot,
    ProductionStaffingAccount, ProductionStaffingMemberAccount, ProductionStaffingSubject,
    ProductionStock,
};
