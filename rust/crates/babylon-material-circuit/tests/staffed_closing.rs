//! The staffing seam reads one real close and plans against authoritative new hours.

use babylon_material_circuit::CapacityReservations;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::UNSEALED_CATALOG_DIGEST;
use babylon_material_circuit::{
    advance_staffing, close_material_period, CapacityRow, CommodityDefinition, CorridorCapacity,
    CorridorId, GoodId, InputOutputCoefficient, InventoryRow, LaborCapacityRow, LaborCoefficient,
    LogisticsNodeId, MaterialCircuitError, MaterialCircuitState, OrderAccessMode, OrderId,
    OrderRow, ProcessId, ProcessOutput, ProductionCommitment, RouteId, RouteStage,
    RouteStageCapacity, SiteId, SiteLogisticsNode, StaffingPolicy, StaffingPoolBinding,
    StaffingPoolId, StaffingPoolState, StaffingState, StaffingWorkSource, SupplierRoute,
    SupplierTransport, UnitId,
};

fn site(value: u8) -> SiteId {
    SiteId::from_bytes([value; 32])
}

fn process(value: u8) -> ProcessId {
    ProcessId::from_bytes([value; 32])
}

fn good(value: u8) -> GoodId {
    GoodId::from_bytes([value; 32])
}

fn unit(value: u8) -> UnitId {
    UnitId::from_bytes([value; 32])
}

fn labor(period: u64, available: u64) -> LaborCapacityRow {
    LaborCapacityRow {
        site_id: site(1),
        unit_id: unit(1),
        period,
        available,
    }
}

fn binding(processes: &[u8]) -> StaffingPoolBinding {
    StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([1; 32]),
        site(1),
        unit(1),
        2,
        StaffingPolicy::one_period(40).expect("the one-period fixture advances"),
        processes
            .iter()
            .copied()
            .map(|id| StaffingWorkSource::Production(process(id)))
            .collect(),
    )
    .expect("the authored fixture satisfies the constructor invariants")
}

fn opening() -> (MaterialCatalog, MaterialCircuitState) {
    {
        let state = MaterialCircuitState {
            capacity_reservations: CapacityReservations::default(),
            final_demand_principals: vec![],
            final_demand_orders: vec![],
            accounting: CircuitAccounting::PhysicalControl,
            maintenance_service: None,
            period: 1,
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities: Vec::new(),
            inventory: vec![InventoryRow {
                site_id: site(1),
                good_id: good(1),
                unit_id: unit(2),
                quantity: 12,
            }],
            orders: Vec::new(),
            freight: Vec::new(),
            corridor_capacities: Vec::new(),
            capacities: vec![CapacityRow {
                process_id: process(1),
                site_id: site(1),
                period: 2,
                available_batches: 4,
            }],
            labor: vec![labor(1, 0)],
            production_commitments: Vec::new(),
        };
        (
            MaterialCatalog::try_new(MaterialCatalog {
                capacity_policy: CapacitySupply::FiniteSchedule,
                merchants: vec![],
                handling_coefficients: vec![],
                maintenance_binding: None,
                site_logistics_nodes: Vec::new(),
                process_outputs: vec![ProcessOutput {
                    process_id: process(1),
                    site_id: site(1),
                    good_id: good(2),
                    unit_id: unit(2),
                    quantity_per_batch: 5,
                }],
                input_coefficients: vec![InputOutputCoefficient {
                    process_id: process(1),
                    good_id: good(1),
                    unit_id: unit(2),
                    quantity_per_batch: 2,
                }],
                labor_coefficients: vec![LaborCoefficient {
                    process_id: process(1),
                    unit_id: unit(1),
                    quantity_per_batch: 10,
                }],
                supplier_routes: Vec::new(),
                commodities: vec![
                    CommodityDefinition {
                        good_id: good(1),
                        unit_id: unit(2),
                        kind: babylon_material_circuit::CommodityKind::Storable {
                            grams_per_unit: 1,
                        },
                    },
                    CommodityDefinition {
                        good_id: good(2),
                        unit_id: unit(2),
                        kind: babylon_material_circuit::CommodityKind::Storable {
                            grams_per_unit: 1,
                        },
                    },
                ],
                route_stages: Vec::new(),
                aid_mandates: Vec::new(),
                household_time_policy: Vec::new(),
                service_inputs: Vec::new(),
                household_needs: Vec::new(),
                catalog_digest: UNSEALED_CATALOG_DIGEST,
            })
            .expect("the authored fixture catalog is valid"),
            state,
        )
    }
}

fn arrival_opening() -> (MaterialCatalog, MaterialCircuitState) {
    let (mut catalog, mut state) = opening();
    state.inventory[0].site_id = site(2);
    state.inventory[0].quantity = 4;
    state.capacities[0].period = 3;
    state.capacities[0].available_batches = 2;
    catalog.labor_coefficients[0].quantity_per_batch = 20;
    catalog.site_logistics_nodes = [1, 2]
        .map(|value| SiteLogisticsNode {
            site_id: site(value),
            node_id: LogisticsNodeId::from_bytes([value; 32]),
        })
        .to_vec();
    catalog.supplier_routes.push(SupplierRoute {
        transport_kind: SupplierTransport::Staged,
        buyer_site_id: site(1),
        supplier_site_id: site(2),
        good_id: good(1),
        unit_id: unit(2),
        route_id: RouteId::from_bytes([1; 32]),
    });
    catalog.route_stages.push(RouteStage {
        route_id: RouteId::from_bytes([1; 32]),
        stage_index: 0,
        from_node_id: LogisticsNodeId::from_bytes([2; 32]),
        to_node_id: LogisticsNodeId::from_bytes([1; 32]),
        travel_periods: 1,
        loss_ppm: 0,
    });
    state.orders.push(OrderRow {
        order_id: OrderId::from_bytes([1; 32]),
        access_mode: OrderAccessMode::CommoditySale,
        buyer_site_id: site(1),
        supplier_site_id: site(2),
        good_id: good(1),
        unit_id: unit(2),
        ordered: 4,
        shipped: 0,
        lost: 0,
        delivered: 0,
        realized: 0,
    });
    state.corridor_capacities.push(CorridorCapacity {
        corridor_id: CorridorId::from_bytes([1; 32]),
        period: 1,
        available_grams: 4,
    });
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id: RouteId::from_bytes([1; 32]),
        stage_index: 0,
        corridor_id: CorridorId::from_bytes([1; 32]),
    });
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    (catalog, state)
}

#[test]
fn real_arrival_requests_work_with_zero_employment_then_plans_next_period() {
    let (catalog, opening) = arrival_opening();
    let original = opening.clone();
    let binding = binding(&[1]);
    let dispatched = babylon_material_circuit::close_material_period(&catalog, &opening)
        .expect("the material period closes")
        .finish_with_labor(&catalog, vec![labor(2, 0)])
        .expect("the fixture completes with labor");
    assert_eq!(dispatched.dispatches.len(), 1);
    assert!(dispatched.state.production_commitments.is_empty());
    assert_eq!(opening, original);

    let closed = babylon_material_circuit::close_material_period(&catalog, &dispatched.state)
        .expect("the material period closes");
    assert_eq!((closed.closing_period(), closed.next_period()), (2, 3));
    assert_eq!(closed.inventory()[0].quantity, 4);
    let requests = closed
        .staffing_requests(&catalog, std::slice::from_ref(&binding))
        .expect("the fixture staffing requests are present");
    assert_eq!(requests.len(), 1);
    assert_eq!(requests[0].period(), 2);
    assert_eq!(requests[0].hours(), 40);
    let people = StaffingState::try_new(
        2,
        vec![StaffingPoolState::try_new(binding, 0, 2, 0)
            .expect("the authored fixture satisfies the constructor invariants")],
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let staffing = babylon_material_circuit::advance_staffing(&people, &requests)
        .expect("the fixture staffing advances");
    assert_eq!(staffing.receipts()[0].hires(), 1);
    let arrival = closed
        .finish_with_labor(&catalog, staffing.next_labor().to_vec())
        .expect("the fixture completes with labor");
    assert_eq!(arrival.arrivals.len(), 1);
    assert!(arrival.production.is_empty());
    assert_eq!(arrival.state.production_commitments[0].planned_batches, 2);
    assert_eq!(arrival.state.labor, vec![labor(3, 40)]);
    let production = babylon_material_circuit::close_material_period(&catalog, &arrival.state)
        .expect("the material period closes")
        .finish_with_labor(&catalog, vec![labor(4, 0)])
        .expect("the fixture completes with labor");
    assert_eq!(production.production[0].produced_batches, 2);
    // Debiting preserves existing zero rows, including the emptied supplier.
    assert_eq!(
        production.state.inventory,
        vec![
            InventoryRow {
                site_id: site(1),
                good_id: good(1),
                unit_id: unit(2),
                quantity: 0,
            },
            InventoryRow {
                site_id: site(1),
                good_id: good(2),
                unit_id: unit(2),
                quantity: 10,
            },
            InventoryRow {
                site_id: site(2),
                good_id: good(1),
                unit_id: unit(2),
                quantity: 0,
            },
        ],
    );
}

fn shared_opening() -> (MaterialCatalog, MaterialCircuitState) {
    let (mut catalog, mut state) = opening();
    for id in [2, 3] {
        let mut output = catalog.process_outputs[0].clone();
        output.process_id = process(id);
        output.good_id = good(id + 1);
        catalog.process_outputs.push(output);
        catalog.commodities.push(CommodityDefinition {
            good_id: good(id + 1),
            unit_id: unit(2),
            kind: babylon_material_circuit::CommodityKind::Storable { grams_per_unit: 1 },
        });
        let mut input = catalog.input_coefficients[0].clone();
        input.process_id = process(id);
        catalog.input_coefficients.push(input);
        let mut coefficient = catalog.labor_coefficients[0].clone();
        coefficient.process_id = process(id);
        catalog.labor_coefficients.push(coefficient);
        let mut capacity = state.capacities[0].clone();
        capacity.process_id = process(id);
        capacity.available_batches = if id == 2 { 4 } else { 0 };
        state.capacities.push(capacity);
    }
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    (catalog, state)
}

#[test]
fn requests_share_inputs_preserve_zero_processes_and_ignore_labor_under_permutations() {
    let (catalog, mut state) = shared_opening();
    state.labor.extend([labor(2, u64::MAX), labor(3, u64::MAX)]);
    let mut twin = state.clone();
    twin.capacities.reverse();
    twin.labor = vec![labor(1, 0)];
    let bindings = [binding(&[3, 1, 2])];
    let closed = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes");
    let requests = closed
        .staffing_requests(&catalog, &bindings)
        .expect("the fixture staffing requests are present");
    let permuted = babylon_material_circuit::close_material_period(&catalog, &twin)
        .expect("the material period closes");
    assert_eq!(
        requests,
        permuted
            .staffing_requests(&catalog, &bindings)
            .expect("the fixture staffing requests are present")
    );
    assert_eq!(
        requests.iter().map(|row| row.hours()).collect::<Vec<_>>(),
        [30, 30, 0]
    );
    assert_eq!(closed.inventory(), state.inventory);
    // The final planner must use the real small replacement, not request-mode grants
    // or either preseeded future schedule. Shared labor allows one batch each.
    let actual = closed
        .finish_with_labor(&catalog, vec![labor(2, 20)])
        .expect("the fixture completes with labor");
    let twin = permuted
        .finish_with_labor(&catalog, vec![labor(2, 20)])
        .expect("the fixture completes with labor");
    assert_eq!(actual, twin);
    assert_eq!(actual.state.labor, vec![labor(2, 20)]);
    assert_eq!(actual.state.production_commitments.len(), 2);
    assert!(actual
        .state
        .production_commitments
        .iter()
        .all(|row| row.planned_batches == 1));
    assert_eq!(actual.state.inventory, state.inventory);
    assert!(actual.production.is_empty());
}

#[test]
fn staffing_requests_refuse_incomplete_duplicate_and_foreign_bindings() {
    let (catalog, state) = shared_opening();
    let closed = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes");
    for bindings in [vec![], vec![binding(&[1, 2])], vec![binding(&[1, 2, 4])]] {
        assert_eq!(
            closed.staffing_requests(&catalog, &bindings),
            Err(MaterialCircuitError::ProcessInvariant)
        );
    }
    assert_eq!(
        closed.staffing_requests(&catalog, &[binding(&[1, 2, 3]), binding(&[1])]),
        Err(MaterialCircuitError::DuplicateRow),
    );
    for (owner, labor_unit) in [(site(9), unit(1)), (site(1), unit(9))] {
        let foreign = StaffingPoolBinding::try_new(
            StaffingPoolId::from_bytes([1; 32]),
            owner,
            labor_unit,
            2,
            StaffingPolicy::one_period(40).expect("the one-period fixture advances"),
            vec![1, 2, 3]
                .into_iter()
                .map(|id| StaffingWorkSource::Production(process(id)))
                .collect(),
        )
        .expect("the authored fixture satisfies the constructor invariants");
        assert_eq!(
            closed.staffing_requests(&catalog, &[foreign]),
            Err(MaterialCircuitError::ProcessInvariant)
        );
    }
    assert_eq!(
        closed
            .staffing_requests(&catalog, &[binding(&[1, 2, 3])])
            .expect("the fixture staffing requests are present")
            .len(),
        3
    );
}

#[test]
fn invalid_next_labor_refuses_without_mutating_opening_or_publishing_a_partial_close() {
    let (catalog, state) = opening();
    let original = state.clone();
    let mut unknown = labor(2, 40);
    unknown.unit_id = unit(9);
    for (rows, expected) in [
        (vec![], MaterialCircuitError::CapacityInvariant),
        (vec![labor(1, 40)], MaterialCircuitError::PeriodInvariant),
        (vec![labor(3, 40)], MaterialCircuitError::PeriodInvariant),
        (vec![unknown], MaterialCircuitError::CapacityInvariant),
        (
            vec![labor(2, 20), labor(2, 20)],
            MaterialCircuitError::DuplicateRow,
        ),
    ] {
        assert_eq!(
            babylon_material_circuit::close_material_period(&catalog, &state)
                .expect("the material period closes")
                .finish_with_labor(&catalog, rows),
            Err(expected)
        );
        assert_eq!(state, original);
    }
    let finished = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes")
        .finish_with_labor(&catalog, vec![labor(2, 0)])
        .expect("the fixture completes with labor");
    assert!(finished.state.production_commitments.is_empty());
    assert_eq!(finished.state.labor, vec![labor(2, 0)]);
}

#[test]
fn request_hour_overflow_and_closing_period_overflow_refuse_atomically() {
    let (mut catalog, mut state) = opening();
    catalog.input_coefficients.clear();
    state.capacities[0].available_batches = 2;
    catalog.labor_coefficients[0].quantity_per_batch = u64::MAX;
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let original = state.clone();
    let closed = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes");
    assert_eq!(
        closed.staffing_requests(&catalog, &[binding(&[1])]),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(state, original);
    assert_eq!(closed.inventory(), original.inventory);

    state.period = u64::MAX;
    state.capacities[0].period = u64::MAX;
    state.labor[0].period = u64::MAX;
    let original = state.clone();
    assert!(matches!(
        babylon_material_circuit::close_material_period(&catalog, &state),
        Err(MaterialCircuitError::Arithmetic)
    ));
    assert_eq!(state, original);
}

#[test]
fn supplied_schedule_and_one_shot_use_identical_execution_and_planning() {
    let (catalog, mut state) = opening();
    state.labor.push(labor(2, 20));
    let one_shot = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let split = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes")
        .finish_with_labor(&catalog, vec![labor(2, 20)])
        .expect("the fixture completes with labor");
    assert_eq!(split, one_shot);
}

#[test]
fn zero_current_labor_still_blocks_execution_before_unconstrained_next_period_requests() {
    let (catalog, mut state) = opening();
    let mut current = state.capacities[0].clone();
    current.period = 1;
    state.capacities.push(current);
    state.production_commitments.push(ProductionCommitment {
        process_id: process(1),
        site_id: site(1),
        period: 1,
        planned_batches: 4,
    });
    let closed = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes");
    assert_eq!(closed.inventory(), state.inventory);
    assert_eq!(
        closed
            .staffing_requests(&catalog, &[binding(&[1])])
            .expect("the fixture staffing requests are present")[0]
            .hours(),
        40
    );
    let next = closed
        .finish_with_labor(&catalog, vec![labor(2, 40)])
        .expect("the fixture completes with labor");
    assert_eq!(next.production[0].produced_batches, 0);
    assert_eq!(next.state.production_commitments[0].planned_batches, 4);
    assert_eq!(next.state.inventory, state.inventory);
}

#[test]
fn replacement_labor_is_sorted_before_the_planner_searches_multiple_principals() {
    let (mut catalog, mut state) = opening();
    let mut output = catalog.process_outputs[0].clone();
    output.process_id = process(2);
    output.site_id = site(2);
    catalog.process_outputs.push(output);
    let mut input = catalog.input_coefficients[0].clone();
    input.process_id = process(2);
    catalog.input_coefficients.push(input);
    let mut coefficient = catalog.labor_coefficients[0].clone();
    coefficient.process_id = process(2);
    catalog.labor_coefficients.push(coefficient);
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let mut inventory = state.inventory[0].clone();
    inventory.site_id = site(2);
    state.inventory.push(inventory);
    let mut capacity = state.capacities[0].clone();
    capacity.process_id = process(2);
    capacity.site_id = site(2);
    state.capacities.push(capacity);
    let mut second = labor(2, 20);
    second.site_id = site(2);
    let next = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes")
        .finish_with_labor(&catalog, vec![second.clone(), labor(2, 10)])
        .expect("the fixture completes with labor");
    assert_eq!(next.state.labor, [labor(2, 10), second]);
    assert_eq!(next.state.production_commitments[0].planned_batches, 1);
    assert_eq!(next.state.production_commitments[1].planned_batches, 2);
}

#[path = "support/family_bound_cases.rs"]
mod family_bound_cases;
