use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::SupplierTransport;
use babylon_material_circuit::{
    BacklogRow, CommodityDefinition, CommodityKind, CorridorCapacity, CorridorId, GoodId,
    InventoryRow, LogisticsNodeId, MaterialCircuitError, MaterialCircuitState, OrderAccessMode,
    OrderId, OrderRow, RouteId, RouteStage, RouteStageCapacity, SiteId, SiteLogisticsNode,
    SupplierRoute, UnitId,
};

fn opening() -> MaterialCircuitState {
    let mut state = empty();
    for (identity, quantity) in [(1_u8, 10), (2_u8, 100)] {
        add_order(&mut state, identity, quantity);
    }
    state.corridor_capacities.push(CorridorCapacity {
        corridor_id: CorridorId::from_bytes([90; 32]),
        period: 1,
        available_grams: 60,
    });
    state
}

fn empty() -> MaterialCircuitState {
    MaterialCircuitState {
        capacity_supply: CapacitySupply::FiniteSchedule,
        merchants: vec![],
        handling_coefficients: vec![],
        final_demand_principals: vec![],
        final_demand_orders: vec![],
        accounting: CircuitAccounting::PhysicalControl,
        maintenance_binding: None,
        maintenance_service: None,
        period: 1,
        site_logistics_nodes: Vec::new(),
        process_outputs: Vec::new(),
        input_coefficients: Vec::new(),
        labor_coefficients: Vec::new(),
        supplier_routes: Vec::new(),
        service_connections: vec![],
        service_orders: vec![],
        commodities: Vec::new(),
        route_stage_capacities: Vec::new(),
        route_stages: Vec::new(),
        inventory: Vec::new(),
        orders: Vec::new(),
        backlog: Vec::new(),
        freight: Vec::new(),
        corridor_capacities: Vec::new(),
        capacities: Vec::new(),
        labor: Vec::new(),
        production_commitments: Vec::new(),
    }
}

fn add_order(state: &mut MaterialCircuitState, identity: u8, quantity: u64) {
    let source = SiteId::from_bytes([identity; 32]);
    let buyer = SiteId::from_bytes([identity + 10; 32]);
    let source_node = LogisticsNodeId::from_bytes([identity; 32]);
    let buyer_node = LogisticsNodeId::from_bytes([identity + 10; 32]);
    let good = GoodId::from_bytes([identity; 32]);
    let unit = UnitId::from_bytes([identity; 32]);
    let route = RouteId::from_bytes([identity; 32]);
    let order = OrderId::from_bytes([identity; 32]);
    state.site_logistics_nodes.extend([
        SiteLogisticsNode {
            site_id: source,
            node_id: source_node,
        },
        SiteLogisticsNode {
            site_id: buyer,
            node_id: buyer_node,
        },
    ]);
    state.supplier_routes.push(SupplierRoute {
        transport_kind: SupplierTransport::Staged,
        buyer_site_id: buyer,
        supplier_site_id: source,
        good_id: good,
        unit_id: unit,
        route_id: route,
    });
    state.route_stages.push(RouteStage {
        route_id: route,
        stage_index: 0,
        from_node_id: source_node,
        to_node_id: buyer_node,
        travel_periods: 1,
        loss_ppm: 0,
    });
    state.inventory.push(InventoryRow {
        site_id: source,
        good_id: good,
        unit_id: unit,
        quantity,
    });
    state.orders.push(OrderRow {
        order_id: order,
        access_mode: OrderAccessMode::CommoditySale,
        buyer_site_id: buyer,
        supplier_site_id: source,
        good_id: good,
        unit_id: unit,
        ordered: quantity,
        shipped: 0,
        lost: 0,
        delivered: 0,
        realized: 0,
    });
    state.backlog.push(BacklogRow {
        order_id: order,
        quantity,
    });
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id: route,
        stage_index: 0,
        corridor_id: CorridorId::from_bytes([90; 32]),
    });
    state.commodities.push(CommodityDefinition {
        good_id: good,
        unit_id: unit,
        kind: babylon_material_circuit::CommodityKind::Storable {
            grams_per_unit: if identity == 1 { 10 } else { 1 },
        },
    });
}

fn constrained() -> MaterialCircuitState {
    let mut state = opening();
    for row in &mut state.orders {
        row.ordered = 2;
    }
    for row in &mut state.backlog {
        row.quantity = 2;
    }
    state.commodities[0].kind = CommodityKind::Storable { grams_per_unit: 6 };
    state.corridor_capacities[0].available_grams = 10;
    state
}
fn quantities(state: &MaterialCircuitState) -> Vec<u64> {
    babylon_material_circuit::advance_material_circuit(state)
        .unwrap()
        .state
        .orders
        .iter()
        .map(|r| r.shipped)
        .collect()
}
#[test]
fn residual_capacity_serves_remaining_feasible_commercial_native_unit() {
    let state = constrained();
    assert_eq!(quantities(&state), [1, 2]);
    assert_eq!(state.orders.iter().map(|r| r.shipped).sum::<u64>(), 0);
}
#[test]
fn residual_policy_is_independent_of_input_row_order() {
    let state = constrained();
    let mut reversed = state.clone();
    reversed.orders.reverse();
    reversed.backlog.reverse();
    reversed.inventory.reverse();
    reversed.route_stages.reverse();
    reversed.route_stage_capacities.reverse();
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&state),
        babylon_material_circuit::advance_material_circuit(&reversed)
    );
    assert_eq!(quantities(&reversed), [1, 2]);
}
#[test]
fn residual_respects_a_future_departure_capacity() {
    let mut state = constrained();
    let first = state.route_stages[1].clone();
    let intermediate = LogisticsNodeId::from_bytes([77; 32]);
    state.route_stages[1].to_node_id = intermediate;
    state.route_stages.push(RouteStage {
        stage_index: 1,
        from_node_id: intermediate,
        ..first
    });
    let corridor = CorridorId::from_bytes([99; 32]);
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id: state.route_stages[1].route_id,
        stage_index: 1,
        corridor_id: corridor,
    });
    state.corridor_capacities.push(CorridorCapacity {
        period: 2,
        corridor_id: corridor,
        available_grams: 1,
    });
    assert_eq!(quantities(&state), [1, 1]);
}

#[test]
fn summed_resource_request_overflow_refuses_atomically() {
    let mut state = constrained();
    for row in &mut state.orders {
        row.ordered = u64::MAX;
    }
    for row in &mut state.backlog {
        row.quantity = u64::MAX;
    }
    for row in &mut state.commodities {
        row.kind = CommodityKind::Storable {
            grams_per_unit: u64::MAX,
        };
    }
    let before = babylon_material_circuit::encode_material_circuit_state(&state).unwrap();
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&state).unwrap(),
        before
    );
}
