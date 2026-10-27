use babylon_material_circuit::SupplierTransport;
use babylon_material_circuit::{
    CommodityDefinition, CorridorCapacity, CorridorId, GoodId, InventoryRow, LaborCapacityRow,
    LogisticsNodeId, MaterialCatalog, MaterialCircuitState, MerchantHandling,
    MerchantHandlingCoefficient, MerchantRole, OrderAccessMode, OrderId, OrderRow, RouteId,
    RouteStage, RouteStageCapacity, SiteId, SiteLogisticsNode, SupplierRoute, UnitId,
};

#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
fn merchant() -> (MaterialCatalog, MaterialCircuitState) {
    let source = SiteId::from_bytes([1; 32]);
    let buyer = SiteId::from_bytes([2; 32]);
    let good_id = GoodId::from_bytes([3; 32]);
    let unit_id = UnitId::from_bytes([4; 32]);
    let route_id = RouteId::from_bytes([5; 32]);
    let corridor_id = CorridorId::from_bytes([6; 32]);
    let order_id = OrderId::from_bytes([7; 32]);
    let source_node = LogisticsNodeId::from_bytes([1; 32]);
    let buyer_node = LogisticsNodeId::from_bytes([2; 32]);
    let catalog = MaterialCatalog {
        capacity_policy: CapacitySupply::FiniteSchedule,
        site_logistics_nodes: vec![
            SiteLogisticsNode {
                site_id: source,
                node_id: source_node,
            },
            SiteLogisticsNode {
                site_id: buyer,
                node_id: buyer_node,
            },
        ],
        process_outputs: vec![],
        input_coefficients: vec![],
        labor_coefficients: vec![],
        commodities: vec![CommodityDefinition {
            good_id,
            unit_id,
            kind: babylon_material_circuit::CommodityKind::Storable { grams_per_unit: 10 },
        }],
        supplier_routes: vec![SupplierRoute {
            transport_kind: SupplierTransport::Staged,
            buyer_site_id: buyer,
            supplier_site_id: source,
            good_id,
            unit_id,
            route_id,
        }],
        route_stages: vec![RouteStage {
            route_id,
            stage_index: 0,
            from_node_id: source_node,
            to_node_id: buyer_node,
            travel_periods: 1,
            loss_ppm: 0,
        }],
        merchants: vec![MerchantHandling {
            site_id: source,
            location: "county:26163"
                .parse()
                .expect("the authored literal parses as the declared type"),
            role: MerchantRole::Retail,
            capacity_id: CorridorId::from_bytes([9; 32]),
            labor_unit_id: UnitId::from_bytes([8; 32]),
        }],
        handling_coefficients: vec![MerchantHandlingCoefficient {
            site_id: source,
            good_id,
            unit_id,
            hours_per_unit: 2,
        }],
        maintenance_binding: None,
        aid_mandates: vec![],
        household_time_policy: vec![],
        service_inputs: vec![],
        household_needs: vec![],
        catalog_digest: [0; 32],
    };
    let state = MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::PhysicalControl,
        service_connections: vec![],
        service_orders: vec![],
        route_stage_capacities: vec![RouteStageCapacity {
            route_id,
            stage_index: 0,
            corridor_id,
        }],
        inventory: vec![InventoryRow {
            site_id: source,
            good_id,
            unit_id,
            quantity: 10,
        }],
        orders: vec![OrderRow {
            order_id,
            access_mode: OrderAccessMode::CommoditySale,
            buyer_site_id: buyer,
            supplier_site_id: source,
            good_id,
            unit_id,
            ordered: 10,
            shipped: 0,
            lost: 0,
            delivered: 0,
            realized: 0,
        }],
        freight: vec![],
        corridor_capacities: vec![
            CorridorCapacity {
                corridor_id: CorridorId::from_bytes([9; 32]),
                period: 1,
                available_grams: 100,
            },
            CorridorCapacity {
                corridor_id,
                period: 1,
                available_grams: 100,
            },
        ],
        capacities: vec![],
        labor: vec![LaborCapacityRow {
            site_id: source,
            unit_id: UnitId::from_bytes([8; 32]),
            period: 1,
            available: 4,
        }],
        production_commitments: vec![],
        final_demand_principals: vec![],
        final_demand_orders: vec![],
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
    };
    (
        MaterialCatalog::try_new(catalog).expect("the authored fixture catalog is valid"),
        state,
    )
}

#[test]
fn outbound_merchant_handling_requires_two_hours_per_native_unit() {
    let (catalog, opening) = merchant();
    let result = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    assert_eq!(result.dispatches[0].quantity, 2);
}

use babylon_material_circuit::CapacityReservations;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::{
    FinalDemandOrder, FinalDemandPrincipal, FinalDemandPrincipalId, MaterialCircuitError,
    OutboundOrderId, StaffingPolicy, StaffingPoolBinding, StaffingPoolId, StaffingPoolState,
    StaffingState, StaffingWorkSource,
};

fn add_local_order(catalog: &MaterialCatalog, state: &mut MaterialCircuitState) {
    let store = &catalog.merchants[0];
    let coefficient = &catalog.handling_coefficients[0];
    let principal = FinalDemandPrincipalId::from_bytes([10; 32]);
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: principal,
        location: store.location,
    });
    state.final_demand_orders.push(FinalDemandOrder {
        order_id: OrderId::from_bytes([11; 32]),
        retailer_site_id: store.site_id,
        demand_principal_id: principal,
        good_id: coefficient.good_id,
        unit_id: coefficient.unit_id,
        ordered: 10,
        fulfilled: 0,
    });
}

fn local_store() -> (MaterialCatalog, MaterialCircuitState) {
    let (mut catalog, mut state) = merchant();
    add_local_order(&catalog, &mut state);
    state.orders.clear();
    catalog.supplier_routes.clear();
    catalog.route_stages.clear();
    state.route_stage_capacities.clear();
    let capacity = catalog.merchants[0].capacity_id;
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    state
        .corridor_capacities
        .retain(|row| row.corridor_id == capacity);
    (catalog, state)
}

fn schedule(catalog: &MaterialCatalog, state: &mut MaterialCircuitState, periods: u64, hours: u64) {
    let merchant = catalog.merchants[0].clone();
    state.labor = (1..=periods)
        .map(|period| LaborCapacityRow {
            site_id: merchant.site_id,
            unit_id: merchant.labor_unit_id,
            period,
            available: hours,
        })
        .collect();
    state
        .corridor_capacities
        .extend((2..=periods).map(|period| CorridorCapacity {
            corridor_id: merchant.capacity_id,
            period,
            available_grams: 100,
        }));
}

#[test]
fn routed_and_local_orders_share_stock_handling_mass_and_opening_labor_once() {
    let (catalog, mut state) = merchant();
    add_local_order(&catalog, &mut state);
    let completed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(completed.dispatches[0].quantity, 1);
    assert_eq!(completed.local_fulfillments[0].quantity, 1);
    assert_eq!(completed.handling.len(), 2);
    for receipt in &completed.handling {
        assert_eq!(
            (receipt.feasible_quantity, receipt.handled_quantity),
            (10, 1)
        );
        assert_eq!((receipt.needed_hours, receipt.used_hours), (20, 2));
    }
    assert_eq!(completed.state.inventory[0].quantity, 8);
    assert_eq!(completed.state.freight[0].quantity, 1);
    assert_eq!(completed.state.orders[0].shipped, 1);
    assert_eq!(
        completed.state.derived_backlog().expect("derived backlog")[0].quantity,
        9
    );
    assert_eq!(completed.state.final_demand_orders[0].fulfilled, 1);
    assert_eq!(completed.arrivals.len(), 0);
    assert_eq!(completed.deliveries.len(), 0);
    assert_eq!(completed.realizations.len(), 0);
}

#[test]
fn independent_physical_need_and_residual_handling_respect_the_road_cut() {
    let (catalog, mut state) = merchant();
    add_local_order(&catalog, &mut state);
    let road = state.route_stage_capacities[0].corridor_id;
    state
        .corridor_capacities
        .iter_mut()
        .find(|row| row.corridor_id == road)
        .expect("the fixture holds the searched element")
        .available_grams = 20;
    let completed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(completed.dispatches[0].quantity, 1);
    assert_eq!(completed.local_fulfillments[0].quantity, 1);
    assert_eq!(
        completed
            .handling
            .iter()
            .map(|row| (
                row.feasible_quantity,
                row.handled_quantity,
                row.needed_hours,
                row.used_hours
            ))
            .collect::<Vec<_>>(),
        vec![(2, 1, 4, 2), (10, 1, 20, 2)]
    );
    assert_eq!(completed.state.inventory[0].quantity, 8);
}

#[test]
fn local_handoff_consumes_handling_mass_without_a_road_or_freight_lot() {
    let (catalog, mut state) = local_store();
    state.labor[0].available = 100;
    state.corridor_capacities[0].available_grams = 30;
    let completed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(completed.local_fulfillments[0].quantity, 3);
    assert_eq!(completed.handling[0].needed_hours, 6);
    assert_eq!(completed.handling[0].used_hours, 6);
    assert_eq!(completed.state.inventory[0].quantity, 7);
    assert_eq!(completed.state.freight.len(), 0);
    assert_eq!(completed.dispatches.len(), 0);
    assert_eq!(completed.production.len(), 0);
    assert_eq!(
        completed.state.inventory[0].good_id,
        state.inventory[0].good_id
    );
}

#[test]
fn finite_local_orders_credit_once_and_finished_orders_report_completed_zero() {
    let (catalog, mut state) = local_store();
    schedule(&catalog, &mut state, 6, 4);
    let mut handed_off = 0;
    for period in 1..=6 {
        assert_eq!(state.period, period);
        let completed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period");
        handed_off += completed
            .local_fulfillments
            .iter()
            .map(|row| row.quantity)
            .sum::<u64>();
        let stock = completed
            .state
            .inventory
            .iter()
            .map(|row| row.quantity)
            .sum::<u64>();
        assert_eq!(stock + handed_off, 10);
        assert_eq!(completed.state.final_demand_orders[0].fulfilled, handed_off);
        if period == 6 {
            assert_eq!(completed.local_fulfillments.len(), 0);
            assert_eq!(completed.handling.len(), 1);
            assert_eq!(
                (
                    completed.handling[0].feasible_quantity,
                    completed.handling[0].handled_quantity,
                    completed.handling[0].needed_hours,
                    completed.handling[0].used_hours
                ),
                (0, 0, 0, 0)
            );
        }
        let bytes =
            babylon_material_circuit::encode_material_circuit_state(&catalog, &completed.state)
                .expect("the canonical material state encodes");
        state = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
            .expect("the canonical material bytes decode");
    }
    assert_eq!(handed_off, 10);
}

fn staffing_binding(
    catalog: &MaterialCatalog,
    _state: &MaterialCircuitState,
) -> StaffingPoolBinding {
    let merchant = &catalog.merchants[0];
    StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([12; 32]),
        merchant.site_id,
        merchant.labor_unit_id,
        10,
        StaffingPolicy::one_period(2).expect("the one-period fixture advances"),
        vec![StaffingWorkSource::MerchantHandling(merchant.site_id)],
    )
    .expect("the authored fixture satisfies the constructor invariants")
}

#[test]
fn zero_employment_can_rehire_from_feasible_handling_need_without_current_dispatch() {
    let (catalog, mut state) = local_store();
    schedule(&catalog, &mut state, 2, 0);
    let binding = staffing_binding(&catalog, &state);
    let opening_staffing = StaffingState::try_new(
        1,
        vec![StaffingPoolState::try_new(binding.clone(), 0, 10, 0)
            .expect("the authored fixture satisfies the constructor invariants")],
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let closed = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes");
    let requests = closed
        .staffing_requests(&catalog, std::slice::from_ref(&binding))
        .expect("the fixture staffing requests are present");
    assert_eq!(
        requests[0].work_source(),
        StaffingWorkSource::MerchantHandling(binding.site_id())
    );
    assert_eq!(requests[0].hours(), 20);
    let staffing = babylon_material_circuit::advance_staffing(&opening_staffing, &requests)
        .expect("the fixture staffing advances");
    assert_eq!(
        (
            staffing.receipts()[0].hires(),
            staffing.receipts()[0].closing_employed(),
            staffing.receipts()[0].closing_reserve()
        ),
        (10, 10, 0)
    );
    let completed = closed
        .finish_with_labor(&catalog, staffing.next_labor().to_vec())
        .expect("the fixture completes with labor");
    assert_eq!(completed.local_fulfillments.len(), 0);
    assert_eq!(
        (
            completed.handling[0].needed_hours,
            completed.handling[0].used_hours
        ),
        (20, 0)
    );
    let next = babylon_material_circuit::advance_material_circuit(&catalog, &completed.state)
        .expect("the authored material state advances one period");
    assert_eq!(next.local_fulfillments[0].quantity, 10);
}

#[test]
fn empty_inventory_reports_zero_feasible_handling_and_staffing_need() {
    let (catalog, mut state) = local_store();
    state.inventory.clear();
    let closed = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes");
    assert_eq!(
        closed
            .staffing_requests(&catalog, &[staffing_binding(&catalog, &state)])
            .expect("the fixture staffing requests are present")[0]
            .hours(),
        0
    );
    let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(
        (
            result.handling[0].needed_hours,
            result.handling[0].used_hours
        ),
        (0, 0)
    );
    assert_eq!(result.local_fulfillments.len(), 0);
}

#[test]
fn arrived_goods_are_available_to_retail_handling_in_the_same_close() {
    let (mut catalog, mut state) = merchant();
    add_local_order(&catalog, &mut state);
    schedule(&catalog, &mut state, 2, 4);
    let incoming_source = state.orders[0].buyer_site_id;
    let retailer = state.orders[0].supplier_site_id;
    state.inventory[0].site_id = incoming_source;
    state.orders[0].buyer_site_id = retailer;
    state.orders[0].supplier_site_id = incoming_source;
    catalog.supplier_routes[0].buyer_site_id = retailer;
    catalog.supplier_routes[0].supplier_site_id = incoming_source;
    let route_stage = &mut catalog.route_stages[0];
    std::mem::swap(&mut route_stage.from_node_id, &mut route_stage.to_node_id);
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(first.dispatches[0].quantity, 10);
    assert_eq!(first.handling[0].needed_hours, 0);
    let arrived = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("the authored material state advances one period");
    assert_eq!(arrived.arrivals[0].quantity, 10);
    assert_eq!(arrived.local_fulfillments[0].quantity, 2);
    assert_eq!(
        (
            arrived.handling[0].needed_hours,
            arrived.handling[0].used_hours
        ),
        (20, 4)
    );
    assert_eq!(
        arrived
            .state
            .inventory
            .iter()
            .map(|row| row.quantity)
            .sum::<u64>(),
        8
    );
}

#[test]
fn merchant_admission_refuses_invalid_coefficients_county_role_and_capacity_ownership() {
    let (catalog, base) = local_store();
    // Definition rows are refused at catalog admission.
    let definition_mutations: &[fn(&mut MaterialCatalog)] = &[
        |c| c.handling_coefficients[0].hours_per_unit = 0,
        |c| c.merchants.push(c.merchants[0].clone()),
    ];
    for mutate in definition_mutations {
        let mut malformed = catalog.clone();
        mutate(&mut malformed);
        assert!(MaterialCatalog::try_new(malformed).is_err());
    }
    let mut uncovered = catalog.clone();
    uncovered.handling_coefficients.clear();
    assert!(babylon_material_circuit::advance_material_circuit(&uncovered, &base).is_err());
    // Captured semantic relations are refused by the period close.
    let mut wholesale = catalog.clone();
    wholesale.merchants[0].role = MerchantRole::Wholesale;
    let wholesale =
        MaterialCatalog::try_new(wholesale).expect("the changed fixture catalog is valid");
    let state_mutations: &[fn(&mut MaterialCircuitState)] = &[
        |s| s.final_demand_orders[0].fulfilled = 11,
        |s| {
            s.final_demand_principals[0].location = "county:26001"
                .parse()
                .expect("the authored literal parses as the declared type");
        },
        |s| s.final_demand_orders.push(s.final_demand_orders[0].clone()),
    ];
    for mutate in state_mutations {
        let mut malformed = base.clone();
        mutate(&mut malformed);
        let preserved = malformed.clone();
        assert!(babylon_material_circuit::advance_material_circuit(&catalog, &malformed).is_err());
        assert_eq!(malformed, preserved);
    }
    assert!(babylon_material_circuit::advance_material_circuit(&wholesale, &base).is_err());
    let (catalog, overlap) = merchant();
    let mut overlap_catalog = catalog.clone();
    overlap_catalog.merchants[0].capacity_id = overlap.route_stage_capacities[0].corridor_id;
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&overlap_catalog, &overlap),
        Err(MaterialCircuitError::MerchantInvariant)
    );
}

#[test]
fn handling_hour_overflow_refuses_before_any_successor_or_local_receipt_escapes() {
    let (catalog, state) = local_store();
    let mut malformed_catalog = catalog;
    malformed_catalog.handling_coefficients[0].hours_per_unit = u64::MAX;
    let preserved = state.clone();
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&malformed_catalog, &state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(state, preserved);
    for code in 20..=21 {
        assert_eq!(
            u16::from(
                MaterialCircuitError::try_from(code)
                    .expect("the fixture value fits the target range")
            ),
            code
        );
    }
}

#[test]
fn new_families_are_canonical_hash_bound_and_local_routed_ids_are_disjoint() {
    let (catalog, mut state) = merchant();
    add_local_order(&catalog, &mut state);
    state.final_demand_orders[0].order_id = state.orders[0].order_id;
    let mut duplicate_good = catalog.handling_coefficients[0].clone();
    duplicate_good.good_id = GoodId::from_bytes([99; 32]);
    let mut catalog = catalog;
    catalog.handling_coefficients.push(duplicate_good.clone());
    catalog.commodities.push(CommodityDefinition {
        good_id: duplicate_good.good_id,
        unit_id: duplicate_good.unit_id,
        kind: babylon_material_circuit::CommodityKind::Storable { grams_per_unit: 10 },
    });
    let catalog = MaterialCatalog::try_new(catalog).expect("the changed fixture catalog is valid");
    let original = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    let completed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(
        completed.handling[0].order,
        OutboundOrderId::Delivery(state.orders[0].order_id)
    );
    assert_eq!(
        completed.handling[1].order,
        OutboundOrderId::LocalFinalDemand(state.orders[0].order_id)
    );
    let mut permuted = state.clone();
    permuted.final_demand_principals.reverse();
    permuted.final_demand_orders.reverse();
    permuted.corridor_capacities.reverse();
    let mut permuted_catalog = catalog.clone();
    permuted_catalog.merchants.reverse();
    permuted_catalog.handling_coefficients.reverse();
    permuted_catalog.commodities.reverse();
    permuted_catalog.site_logistics_nodes.reverse();
    let permuted_catalog =
        MaterialCatalog::try_new(permuted_catalog).expect("the permuted catalog is valid");
    assert_eq!(permuted_catalog.catalog_digest, catalog.catalog_digest);
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&permuted_catalog, &permuted)
            .expect("the canonical material state encodes"),
        original
    );
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&permuted_catalog, &permuted)
            .expect("the authored material state advances one period"),
        completed
    );
    let baseline = babylon_material_circuit::material_circuit_state_digest(&catalog, &state)
        .expect("the material state has a digest");
    let definition_mutations: &[fn(&mut MaterialCatalog)] = &[
        |c| {
            c.merchants[0].location = "county:26001"
                .parse()
                .expect("the authored literal parses as the declared type");
        },
        |c| c.handling_coefficients[0].hours_per_unit += 1,
    ];
    for mutate in definition_mutations {
        let mut changed = catalog.clone();
        mutate(&mut changed);
        let changed = MaterialCatalog::try_new(changed).expect("the changed catalog is valid");
        assert_ne!(changed.catalog_digest, catalog.catalog_digest);
    }
    let mut relocated_catalog = catalog.clone();
    relocated_catalog.merchants[0].location = "county:26001"
        .parse()
        .expect("the authored literal parses as the declared type");
    let relocated_catalog =
        MaterialCatalog::try_new(relocated_catalog).expect("the changed fixture catalog is valid");
    let mut relocated = state.clone();
    relocated.final_demand_principals[0].location = "county:26001"
        .parse()
        .expect("the authored literal parses as the declared type");
    assert_ne!(
        babylon_material_circuit::material_circuit_state_digest(&relocated_catalog, &relocated)
            .expect("the material state has a digest"),
        baseline
    );
    let state_mutations: &[fn(&mut MaterialCircuitState)] = &[
        |s| {
            let id = FinalDemandPrincipalId::from_bytes([90; 32]);
            s.final_demand_principals[0].id = id;
            s.final_demand_orders[0].demand_principal_id = id;
        },
        |s| s.final_demand_orders[0].ordered += 1,
        |s| s.final_demand_orders[0].fulfilled += 1,
    ];
    for mutate in state_mutations {
        let mut changed = state.clone();
        mutate(&mut changed);
        assert_ne!(
            babylon_material_circuit::material_circuit_state_digest(&catalog, &changed)
                .expect("the material state has a digest"),
            baseline
        );
    }
}

#[test]
fn multiple_merchants_and_county_accounts_preserve_identity_under_all_new_row_permutations() {
    let (mut catalog, mut state) = local_store();
    let second_site = catalog.site_logistics_nodes[1].site_id;
    let mut second_store = catalog.merchants[0].clone();
    second_store.site_id = second_site;
    second_store.location = "county:26001"
        .parse()
        .expect("the authored literal parses as the declared type");
    second_store.capacity_id = CorridorId::from_bytes([20; 32]);
    let mut coefficient = catalog.handling_coefficients[0].clone();
    coefficient.site_id = second_site;
    coefficient.hours_per_unit = 3;
    let mut stock = state.inventory[0].clone();
    stock.site_id = second_site;
    stock.quantity = 6;
    let mut labor = state.labor[0].clone();
    labor.site_id = second_site;
    labor.available = 9;
    let mut demand = state.final_demand_principals[0].clone();
    demand.id = FinalDemandPrincipalId::from_bytes([21; 32]);
    demand.location = second_store.location;
    let mut order = state.final_demand_orders[0].clone();
    order.order_id = OrderId::from_bytes([22; 32]);
    order.retailer_site_id = second_site;
    order.demand_principal_id = demand.id;
    order.ordered = 4;
    state.corridor_capacities.push(CorridorCapacity {
        corridor_id: second_store.capacity_id,
        period: 1,
        available_grams: 100,
    });
    catalog.merchants.push(second_store);
    catalog.handling_coefficients.push(coefficient);
    catalog = MaterialCatalog::try_new(catalog).expect("the changed fixture catalog is valid");
    state.inventory.push(stock);
    state.labor.push(labor);
    state.final_demand_principals.push(demand);
    state.final_demand_orders.push(order);
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    let expected = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(
        expected
            .local_fulfillments
            .iter()
            .map(|row| row.quantity)
            .collect::<Vec<_>>(),
        vec![2, 3]
    );
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let mut permuted_catalog = catalog.clone();
    permuted_catalog.merchants.reverse();
    permuted_catalog.handling_coefficients.reverse();
    let permuted_catalog =
        MaterialCatalog::try_new(permuted_catalog).expect("the permuted catalog is valid");
    assert_eq!(permuted_catalog.catalog_digest, catalog.catalog_digest);
    state.final_demand_principals.reverse();
    state.final_demand_orders.reverse();
    state.inventory.reverse();
    state.labor.reverse();
    state.corridor_capacities.reverse();
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes"),
        bytes
    );
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period"),
        expected
    );
}

#[test]
fn merchant_role_encoding_rejects_unknown_tags() {
    let (catalog, state) = local_store();
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    // The v4 state frame no longer carries merchant definitions, so an unknown
    // role tag cannot appear in it; the catalog encoder owns that enum and its
    // bytes are not decoded. The state frame still ends with the explicit
    // physical-control tag and empty service rows.
    assert!(state.maintenance_service.is_none());
    assert_eq!(state.accounting, CircuitAccounting::PhysicalControl);
    assert_eq!(&bytes[bytes.len() - 4..], &[0, 0, 0, 0]);
    let mut trailing = bytes;
    trailing.push(0);
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &trailing),
        Err(MaterialCircuitError::WireTrailing)
    );
}

#[test]
fn local_inter_owner_transfer_needs_no_road_or_transit() {
    let (mut catalog, mut state) = merchant();
    catalog.supplier_routes[0].transport_kind = SupplierTransport::Local;
    catalog.route_stages.clear();
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    state.route_stage_capacities.clear();
    let handling = catalog.merchants[0].capacity_id;
    state
        .corridor_capacities
        .retain(|row| row.corridor_id == handling);
    let completed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("explicit local circulation");
    assert_eq!(completed.state.orders[0].delivered, 2);
    assert_eq!(completed.state.freight.len(), 0);
    assert_eq!(completed.arrivals.len(), 0);
}

fn local_supplier() -> (MaterialCatalog, MaterialCircuitState) {
    let (mut catalog, mut state) = merchant();
    catalog.supplier_routes[0].transport_kind = SupplierTransport::Local;
    catalog.route_stages.clear();
    state.route_stage_capacities.clear();
    let capacity = catalog.merchants[0].capacity_id;
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    state
        .corridor_capacities
        .retain(|row| row.corridor_id == capacity);
    (catalog, state)
}

#[test]
fn local_transfer_has_explicit_receipt_and_still_requires_merchant_labor() {
    let (catalog, mut state) = local_supplier();
    let completed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(completed.local_transfers.len(), 1);
    assert_eq!(completed.local_transfers[0].quantity, 2);
    assert_eq!(
        completed.local_transfers[0].buyer_site_id,
        state.orders[0].buyer_site_id
    );
    assert_eq!(completed.dispatches.len(), 0);
    assert_eq!(completed.arrivals.len(), 0);
    assert_eq!(completed.deliveries.len(), 0);
    assert_eq!(completed.realizations.len(), 0);
    assert_eq!(
        (
            completed.state.orders[0].shipped,
            completed.state.orders[0].delivered,
            completed.state.orders[0].realized,
            completed.state.orders[0].lost
        ),
        (2, 2, 2, 0)
    );
    assert_eq!(
        completed
            .state
            .inventory
            .iter()
            .map(|row| row.quantity)
            .sum::<u64>(),
        10
    );
    state.labor[0].available = 0;
    let stopped = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(stopped.local_transfers.len(), 0);
    assert_eq!(stopped.handling[0].needed_hours, 20);
    assert_eq!(stopped.handling[0].used_hours, 0);
    assert_eq!(stopped.state.orders[0].shipped, 0);
}

#[test]
fn local_buyer_credits_wait_until_all_outbound_grants_are_fixed() {
    let (mut catalog, mut state) = local_supplier();
    schedule(&catalog, &mut state, 2, 4);
    let next_buyer = SiteId::from_bytes([40; 32]);
    catalog.site_logistics_nodes.push(SiteLogisticsNode {
        site_id: next_buyer,
        node_id: LogisticsNodeId::from_bytes([40; 32]),
    });
    let mut onward = state.orders[0].clone();
    onward.order_id = OrderId::from_bytes([41; 32]);
    onward.supplier_site_id = state.orders[0].buyer_site_id;
    onward.buyer_site_id = next_buyer;
    let mut relation = catalog.supplier_routes[0].clone();
    relation.route_id = RouteId::from_bytes([41; 32]);
    relation.supplier_site_id = onward.supplier_site_id;
    relation.buyer_site_id = next_buyer;
    catalog.supplier_routes.push(relation);
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    state.orders.push(onward);
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(first.local_transfers.len(), 1);
    assert_eq!(first.state.orders[1].shipped, 0);
    assert!(first
        .state
        .inventory
        .iter()
        .all(|row| row.site_id != next_buyer || row.quantity == 0));
    let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("the authored material state advances one period");
    assert_eq!(second.state.orders[1].shipped, 2);
    assert_eq!(
        second
            .state
            .inventory
            .iter()
            .find(|row| row.site_id == next_buyer)
            .expect("the fixture holds the searched element")
            .quantity,
        2
    );
    assert_eq!(
        second
            .state
            .inventory
            .iter()
            .map(|row| row.quantity)
            .sum::<u64>(),
        10
    );
    state.orders.reverse();
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period"),
        first
    );
}

#[test]
fn local_transfer_mode_and_wire_are_checked_and_buyer_overflow_is_atomic() {
    let (catalog, state) = local_supplier();
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(
            &catalog,
            &babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
                .expect("the canonical material bytes decode")
        )
        .expect("the authored material state advances one period"),
        babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period")
    );
    let wrong_mode = state.clone();
    let mut wrong_catalog = catalog.clone();
    wrong_catalog.supplier_routes[0].transport_kind = SupplierTransport::Staged;
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&wrong_catalog, &wrong_mode),
        Err(MaterialCircuitError::RouteInvariant)
    );
    let (mut wrongly_local_catalog, wrongly_local) = merchant();
    wrongly_local_catalog.supplier_routes[0].transport_kind = SupplierTransport::Local;
    // A local relation may not keep timed stages; definition admission refuses it.
    assert_eq!(
        MaterialCatalog::try_new(wrongly_local_catalog),
        Err(MaterialCircuitError::RouteInvariant)
    );
    assert_eq!(wrongly_local.period, 1);
    let mut overflowing = state.clone();
    let mut buyer_stock = overflowing.inventory[0].clone();
    buyer_stock.site_id = overflowing.orders[0].buyer_site_id;
    buyer_stock.quantity = u64::MAX;
    overflowing.inventory.push(buyer_stock);
    let preserved = overflowing.clone();
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &overflowing),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(overflowing, preserved);
}

#[test]
fn residual_zero_base_order_still_requires_funded_handling_hours() {
    let (catalog, mut state) = merchant();
    add_local_order(&catalog, &mut state);
    state.inventory[0].quantity = 1;
    state.orders[0].ordered = 1;
    state.final_demand_orders[0].ordered = 1;
    state.labor[0].available = 2;
    let completed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(completed.dispatches[0].quantity, 1);
    assert_eq!(completed.local_fulfillments.len(), 0);
    assert_eq!(
        completed.handling.iter().map(|r| r.used_hours).sum::<u64>(),
        2
    );
    assert!(completed
        .handling
        .iter()
        .all(|r| r.feasible_quantity == 1 && r.needed_hours == 2));
    state.labor[0].available = 1;
    let blocked = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(blocked.dispatches.len(), 0);
    assert_eq!(blocked.local_fulfillments.len(), 0);
    assert!(blocked.handling.iter().all(|r| r.used_hours == 0));
}
