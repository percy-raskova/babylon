//! A shop whose handling hours are given for a block of units sells what its hours handle.

use babylon_material_circuit::{
    CapacityReservations, CapacitySupply, CircuitAccounting, CommodityDefinition, CommodityKind,
    CorridorCapacity, CorridorId, FinalDemandOrder, FinalDemandPrincipal, FinalDemandPrincipalId,
    GoodId, InventoryRow, LaborCapacityRow, LogisticsNodeId, MaterialCatalog,
    MaterialCatalogDefinition, MaterialCircuitState, MerchantHandling, MerchantHandlingCoefficient,
    MerchantRole, OrderId, SiteId, SiteLogisticsNode, UnitId,
};

fn site() -> SiteId {
    SiteId::from_bytes([1; 32])
}

fn food() -> GoodId {
    GoodId::from_bytes([2; 32])
}

fn unit() -> UnitId {
    UnitId::from_bytes([3; 32])
}

fn hours() -> UnitId {
    UnitId::from_bytes([4; 32])
}

/// One retailer with 100 units of food in stock and 7 hours of labor, handling 10 units in 1 hour; three
/// households each ask for 30 units.
fn shop() -> (MaterialCatalog, MaterialCircuitState) {
    let store = MerchantHandling {
        site_id: site(),
        location: "county:26163"
            .parse()
            .expect("the authored literal parses as the declared type"),
        role: MerchantRole::Retail,
        capacity_id: CorridorId::from_bytes([5; 32]),
        labor_unit_id: hours(),
    };
    let catalog = MaterialCatalog::try_new(MaterialCatalogDefinition {
        market_clearing: None,
        capacity_policy: CapacitySupply::FiniteSchedule,
        site_logistics_nodes: vec![SiteLogisticsNode {
            site_id: site(),
            node_id: LogisticsNodeId::from_bytes([6; 32]),
        }],
        process_outputs: vec![],
        input_coefficients: vec![],
        labor_coefficients: vec![],
        commodities: vec![CommodityDefinition {
            good_id: food(),
            unit_id: unit(),
            kind: CommodityKind::Storable { grams_per_unit: 1 },
        }],
        supplier_routes: vec![],
        route_stages: vec![],
        merchants: vec![store.clone()],
        handling_coefficients: vec![MerchantHandlingCoefficient {
            site_id: site(),
            good_id: food(),
            unit_id: unit(),
            hours_per_unit: 1,
            units: 10,
        }],
        company_portfolios: None,
        company_payouts: vec![],
        maintenance_binding: None,
        aid_mandates: vec![],
        household_time_policy: vec![],
        service_inputs: vec![],
        household_needs: vec![],
    })
    .expect("the authored fixture catalog is valid");
    let principals: Vec<_> = (0..3_u8)
        .map(|n| FinalDemandPrincipalId::from_bytes([10 + n; 32]))
        .collect();
    let state = MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::PhysicalControl,
        service_connections: vec![],
        service_orders: vec![],
        route_stage_capacities: vec![],
        inventory: vec![InventoryRow {
            site_id: site(),
            good_id: food(),
            unit_id: unit(),
            quantity: 100,
        }],
        orders: vec![],
        freight: vec![],
        corridor_capacities: vec![CorridorCapacity {
            corridor_id: store.capacity_id,
            period: 1,
            available_grams: 1_000,
        }],
        capacities: vec![],
        labor: vec![LaborCapacityRow {
            site_id: site(),
            unit_id: hours(),
            period: 1,
            available: 7,
        }],
        production_commitments: vec![],
        final_demand_principals: principals
            .iter()
            .map(|id| FinalDemandPrincipal {
                id: *id,
                location: store.location,
            })
            .collect(),
        final_demand_orders: principals
            .iter()
            .enumerate()
            .map(|(n, id)| FinalDemandOrder {
                order_id: OrderId::from_bytes([20 + u8::try_from(n).expect("three"); 32]),
                retailer_site_id: site(),
                demand_principal_id: *id,
                good_id: food(),
                unit_id: unit(),
                ordered: 30,
                fulfilled: 0,
            })
            .collect(),
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
    };
    (catalog, state)
}

#[test]
fn a_shop_with_blocks_sells_what_its_hours_handle() {
    let (catalog, state) = shop();
    let completed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let handed: u64 = completed
        .local_fulfillments
        .iter()
        .map(|row| row.quantity)
        .sum();
    assert_eq!(handed, 70);
    assert_eq!(
        completed
            .handling
            .iter()
            .map(|row| row.used_hours)
            .sum::<u64>(),
        7
    );
    assert_eq!(completed.state.inventory[0].quantity, 30);
}
