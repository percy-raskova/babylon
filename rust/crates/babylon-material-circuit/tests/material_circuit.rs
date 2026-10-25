use babylon_material_circuit::CapacityReservations;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::UNSEALED_CATALOG_DIGEST;
use babylon_material_circuit::{
    CapacityRow, CommodityDefinition, CorridorCapacity, CorridorId, GoodId, InputOutputCoefficient,
    InventoryRow, LaborCapacityRow, LaborCoefficient, LogisticsNodeId, MaterialCatalog,
    MaterialCircuitError, MaterialCircuitState, OrderAccessMode, OrderId, OrderRow, ProcessId,
    ProcessOutput, ProductionCommitment, RouteId, RouteStage, RouteStageCapacity, SiteId,
    SiteLogisticsNode, SupplierRoute, SupplierTransport, UnitId, MAX_MATERIAL_CIRCUIT_ROWS,
};

fn site(byte: u8) -> SiteId {
    SiteId::from_bytes([byte; 32])
}

fn good(byte: u8) -> GoodId {
    GoodId::from_bytes([byte; 32])
}

fn unit(byte: u8) -> UnitId {
    UnitId::from_bytes([byte; 32])
}

fn process(byte: u8) -> ProcessId {
    ProcessId::from_bytes([byte; 32])
}

fn order(byte: u8) -> OrderId {
    OrderId::from_bytes([byte; 32])
}

fn numbered_site(index: usize) -> SiteId {
    let mut bytes = [0_u8; 32];
    let number = u64::try_from(index).expect("material row ceiling fits u64");
    bytes[24..].copy_from_slice(&number.to_be_bytes());
    SiteId::from_bytes(bytes)
}

const SUPPLIER: u8 = 1;
const FACTORY: u8 = 2;
const GRAIN: u8 = 3;
const BREAD: u8 = 4;
const GOODS_UNIT: u8 = 5;
const LABOR_UNIT: u8 = 6;
const BAKERY: u8 = 7;
const GRAIN_ORDER: u8 = 8;
fn capacity_rows() -> Vec<CapacityRow> {
    [1, 2, 3]
        .into_iter()
        .map(|period| CapacityRow {
            process_id: process(BAKERY),
            site_id: site(FACTORY),
            period,
            available_batches: 3,
        })
        .collect()
}

fn labor_rows() -> Vec<LaborCapacityRow> {
    [1, 2, 3]
        .into_iter()
        .map(|period| LaborCapacityRow {
            site_id: site(FACTORY),
            unit_id: unit(LABOR_UNIT),
            period,
            available: 12,
        })
        .collect()
}

#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
fn base_state() -> (MaterialCatalog, MaterialCircuitState) {
    {
        let state = MaterialCircuitState {
            capacity_reservations: CapacityReservations::default(),
            period: 1,
            final_demand_principals: vec![],
            final_demand_orders: vec![],
            accounting: CircuitAccounting::PhysicalControl,
            maintenance_service: None,
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities: vec![RouteStageCapacity {
                route_id: RouteId::from_bytes([GRAIN_ORDER; 32]),
                stage_index: 0,
                corridor_id: CorridorId::from_bytes([9; 32]),
            }],
            corridor_capacities: (1..=3)
                .map(|period| CorridorCapacity {
                    corridor_id: CorridorId::from_bytes([9; 32]),
                    period,
                    available_grams: u64::MAX,
                })
                .collect(),
            inventory: vec![
                InventoryRow {
                    site_id: site(SUPPLIER),
                    good_id: good(GRAIN),
                    unit_id: unit(GOODS_UNIT),
                    quantity: 10,
                },
                InventoryRow {
                    site_id: site(FACTORY),
                    good_id: good(GRAIN),
                    unit_id: unit(GOODS_UNIT),
                    quantity: 0,
                },
                InventoryRow {
                    site_id: site(FACTORY),
                    good_id: good(BREAD),
                    unit_id: unit(GOODS_UNIT),
                    quantity: 0,
                },
            ],
            orders: vec![OrderRow {
                order_id: order(GRAIN_ORDER),
                access_mode: OrderAccessMode::CommoditySale,
                buyer_site_id: site(FACTORY),
                supplier_site_id: site(SUPPLIER),
                good_id: good(GRAIN),
                unit_id: unit(GOODS_UNIT),
                ordered: 6,
                shipped: 0,
                lost: 0,
                delivered: 0,
                realized: 0,
            }],
            freight: Vec::new(),
            capacities: capacity_rows(),
            labor: labor_rows(),
            production_commitments: Vec::new(),
        };
        (
            MaterialCatalog::try_new(MaterialCatalog {
                capacity_policy: CapacitySupply::FiniteSchedule,
                merchants: vec![],
                handling_coefficients: vec![],
                maintenance_binding: None,
                site_logistics_nodes: vec![
                    SiteLogisticsNode {
                        site_id: site(SUPPLIER),
                        node_id: LogisticsNodeId::from_bytes([SUPPLIER; 32]),
                    },
                    SiteLogisticsNode {
                        site_id: site(FACTORY),
                        node_id: LogisticsNodeId::from_bytes([FACTORY; 32]),
                    },
                ],
                commodities: vec![
                    CommodityDefinition {
                        good_id: good(GRAIN),
                        unit_id: unit(GOODS_UNIT),
                        kind: babylon_material_circuit::CommodityKind::Storable {
                            grams_per_unit: 1,
                        },
                    },
                    CommodityDefinition {
                        good_id: good(BREAD),
                        unit_id: unit(GOODS_UNIT),
                        kind: babylon_material_circuit::CommodityKind::Storable {
                            grams_per_unit: 1,
                        },
                    },
                ],
                route_stages: vec![RouteStage {
                    route_id: RouteId::from_bytes([GRAIN_ORDER; 32]),
                    stage_index: 0,
                    from_node_id: LogisticsNodeId::from_bytes([SUPPLIER; 32]),
                    to_node_id: LogisticsNodeId::from_bytes([FACTORY; 32]),
                    travel_periods: 1,
                    loss_ppm: 0,
                }],
                process_outputs: vec![ProcessOutput {
                    process_id: process(BAKERY),
                    site_id: site(FACTORY),
                    good_id: good(BREAD),
                    unit_id: unit(GOODS_UNIT),
                    quantity_per_batch: 2,
                }],
                input_coefficients: vec![InputOutputCoefficient {
                    process_id: process(BAKERY),
                    good_id: good(GRAIN),
                    unit_id: unit(GOODS_UNIT),
                    quantity_per_batch: 3,
                }],
                labor_coefficients: vec![LaborCoefficient {
                    process_id: process(BAKERY),
                    unit_id: unit(LABOR_UNIT),
                    quantity_per_batch: 4,
                }],
                supplier_routes: vec![SupplierRoute {
                    buyer_site_id: site(FACTORY),
                    supplier_site_id: site(SUPPLIER),
                    good_id: good(GRAIN),
                    unit_id: unit(GOODS_UNIT),
                    transport_kind: SupplierTransport::Staged,
                    route_id: RouteId::from_bytes([GRAIN_ORDER; 32]),
                }],
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

fn inventory_quantity(state: &MaterialCircuitState, site_byte: u8, good_byte: u8) -> u64 {
    state
        .inventory
        .iter()
        .take(babylon_material_circuit::MAX_MATERIAL_CIRCUIT_ROWS + 1)
        .find(|row| row.site_id == site(site_byte) && row.good_id == good(good_byte))
        .map_or(0, |row| row.quantity)
}

#[test]
fn shipment_precedes_arrival_and_realization() {
    let (catalog, opening) = base_state();
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("period one must close");
    assert_eq!(first.state.period, 2);
    assert_eq!(first.dispatches.len(), 1);
    assert!(first.arrivals.is_empty());
    assert!(first.realizations.is_empty());
    assert_eq!(first.state.orders[0].shipped, 6);
    assert_eq!(first.state.orders[0].delivered, 0);
    assert_eq!(first.state.orders[0].realized, 0);
    assert_eq!(
        first.state.derived_backlog().expect("derived backlog")[0].quantity,
        0
    );
    assert_eq!(inventory_quantity(&first.state, SUPPLIER, GRAIN), 4);
    assert_eq!(inventory_quantity(&first.state, FACTORY, GRAIN), 0);

    let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("period two must close");
    assert_eq!(second.state.period, 3);
    assert_eq!(second.arrivals.len(), 1);
    assert_eq!(second.deliveries.len(), 1);
    assert_eq!(second.realizations.len(), 1);
    assert_eq!(second.state.orders[0].delivered, 6);
    assert_eq!(second.state.orders[0].realized, 6);
    assert_eq!(inventory_quantity(&second.state, FACTORY, GRAIN), 6);
    assert_eq!(second.state.production_commitments[0].period, 3);
    assert_eq!(second.state.production_commitments[0].planned_batches, 2);
}

#[test]
fn delivered_inputs_feed_the_following_period_not_the_arrival_period() {
    let (catalog, opening) = base_state();
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("period one must close");
    assert!(first.state.production_commitments.is_empty());

    let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("period two must close");
    assert_eq!(second.state.production_commitments[0].planned_batches, 2);
    assert!(second.production.is_empty());

    let third = babylon_material_circuit::advance_material_circuit(&catalog, &second.state)
        .expect("period three must close");
    assert_eq!(third.production[0].planned_batches, 2);
    assert_eq!(third.production[0].produced_batches, 2);
    assert_eq!(inventory_quantity(&third.state, FACTORY, GRAIN), 0);
    assert_eq!(inventory_quantity(&third.state, FACTORY, BREAD), 4);
}

#[test]
fn severed_supplier_relation_causes_backlog_without_creating_goods() {
    let (mut catalog, state) = base_state();
    catalog.supplier_routes.clear();
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");

    let first = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("missing supply is a material outcome");
    assert!(first.dispatches.is_empty());
    assert_eq!(first.state.orders[0].shipped, 0);
    assert_eq!(
        first.state.derived_backlog().expect("derived backlog")[0].quantity,
        6
    );
    assert_eq!(inventory_quantity(&first.state, SUPPLIER, GRAIN), 10);

    let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("period two must close");
    assert!(second.arrivals.is_empty());
    assert!(second.state.production_commitments.is_empty());
}

#[test]
fn missing_stock_and_labor_are_material_shortages_not_engine_errors() {
    let (catalog, mut state) = base_state();
    state.inventory.remove(0);
    state.labor = state
        .labor
        .into_iter()
        .take(babylon_material_circuit::MAX_MATERIAL_CIRCUIT_ROWS + 1)
        .filter(|row| row.period != 1)
        .collect();
    state.production_commitments = vec![ProductionCommitment {
        process_id: process(BAKERY),
        site_id: site(FACTORY),
        period: 1,
        planned_batches: 3,
    }];

    let outcome = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("zero supply must still close");
    assert_eq!(outcome.production[0].produced_batches, 0);
    assert!(outcome.dispatches.is_empty());
    assert_eq!(
        outcome.state.derived_backlog().expect("derived backlog")[0].quantity,
        6
    );
    assert_eq!(inventory_quantity(&outcome.state, FACTORY, BREAD), 0);
}

#[test]
fn leontief_output_is_bounded_by_labor_capacity_and_inputs() {
    let (catalog, mut state) = base_state();
    state.orders.clear();
    state.inventory[1].quantity = 30;
    state.capacities[0].available_batches = 4;
    state.labor[0].available = 10;
    state.production_commitments = vec![ProductionCommitment {
        process_id: process(BAKERY),
        site_id: site(FACTORY),
        period: 1,
        planned_batches: 10,
    }];

    let outcome = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("bounded production must close");
    assert_eq!(outcome.production[0].planned_batches, 10);
    assert_eq!(outcome.production[0].produced_batches, 2);
    assert_eq!(inventory_quantity(&outcome.state, FACTORY, GRAIN), 24);
    assert_eq!(inventory_quantity(&outcome.state, FACTORY, BREAD), 4);
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
fn production_debits_all_inputs_before_crediting_any_output() {
    let producer = process(1);
    let consumer = process(2);
    let shared_good = good(3);
    let consumer_output = good(4);
    let production_site = site(5);
    let goods_unit = unit(6);
    let labor_unit = unit(7);
    let (catalog, state) = {
        let state = MaterialCircuitState {
            capacity_reservations: CapacityReservations::default(),
            period: 1,
            final_demand_principals: vec![],
            final_demand_orders: vec![],
            accounting: CircuitAccounting::PhysicalControl,
            maintenance_service: None,
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities: vec![],
            corridor_capacities: vec![],
            inventory: vec![InventoryRow {
                site_id: production_site,
                good_id: shared_good,
                unit_id: goods_unit,
                quantity: u64::MAX,
            }],
            orders: Vec::new(),
            freight: Vec::new(),
            capacities: vec![
                CapacityRow {
                    process_id: producer,
                    site_id: production_site,
                    period: 1,
                    available_batches: 1,
                },
                CapacityRow {
                    process_id: consumer,
                    site_id: production_site,
                    period: 1,
                    available_batches: 1,
                },
            ],
            labor: vec![LaborCapacityRow {
                site_id: production_site,
                unit_id: labor_unit,
                period: 1,
                available: 2,
            }],
            production_commitments: vec![
                ProductionCommitment {
                    process_id: producer,
                    site_id: production_site,
                    period: 1,
                    planned_batches: 1,
                },
                ProductionCommitment {
                    process_id: consumer,
                    site_id: production_site,
                    period: 1,
                    planned_batches: 1,
                },
            ],
        };
        (
            MaterialCatalog::try_new(MaterialCatalog {
                capacity_policy: CapacitySupply::FiniteSchedule,
                merchants: vec![],
                handling_coefficients: vec![],
                maintenance_binding: None,
                site_logistics_nodes: vec![],
                commodities: vec![
                    CommodityDefinition {
                        good_id: shared_good,
                        unit_id: goods_unit,
                        kind: babylon_material_circuit::CommodityKind::Storable {
                            grams_per_unit: 1,
                        },
                    },
                    CommodityDefinition {
                        good_id: consumer_output,
                        unit_id: goods_unit,
                        kind: babylon_material_circuit::CommodityKind::Storable {
                            grams_per_unit: 1,
                        },
                    },
                ],
                route_stages: vec![],
                process_outputs: vec![
                    ProcessOutput {
                        process_id: producer,
                        site_id: production_site,
                        good_id: shared_good,
                        unit_id: goods_unit,
                        quantity_per_batch: 1,
                    },
                    ProcessOutput {
                        process_id: consumer,
                        site_id: production_site,
                        good_id: consumer_output,
                        unit_id: goods_unit,
                        quantity_per_batch: 1,
                    },
                ],
                input_coefficients: vec![InputOutputCoefficient {
                    process_id: consumer,
                    good_id: shared_good,
                    unit_id: goods_unit,
                    quantity_per_batch: 1,
                }],
                labor_coefficients: vec![
                    LaborCoefficient {
                        process_id: producer,
                        unit_id: labor_unit,
                        quantity_per_batch: 1,
                    },
                    LaborCoefficient {
                        process_id: consumer,
                        unit_id: labor_unit,
                        quantity_per_batch: 1,
                    },
                ],
                supplier_routes: Vec::new(),
                aid_mandates: Vec::new(),
                household_time_policy: Vec::new(),
                service_inputs: Vec::new(),
                household_needs: Vec::new(),
                catalog_digest: UNSEALED_CATALOG_DIGEST,
            })
            .expect("the authored fixture catalog is valid"),
            state,
        )
    };

    let outcome = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("net-conserved production must close");
    assert_eq!(
        inventory_quantity(&outcome.state, 5, 3),
        u64::MAX,
        "the shared inventory must be debited before its output is credited"
    );
    assert_eq!(inventory_quantity(&outcome.state, 5, 4), 1);
}

#[test]
fn proportional_production_uses_u128_for_unbounded_requested_units() {
    let (catalog, mut state) = production_state_for_numeric_boundary();
    state.production_commitments[0].planned_batches = u64::MAX;
    state.capacities[0].available_batches = u64::MAX;
    state.labor[0].available = u64::MAX;

    let outcome = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("scarcity must bound an intermediate request larger than u64");
    assert_eq!(outcome.production[0].produced_batches, 1);
    assert_eq!(inventory_quantity(&outcome.state, 1, 2), 0);
    assert_eq!(inventory_quantity(&outcome.state, 1, 3), 1);
}

fn production_state_for_numeric_boundary() -> (MaterialCatalog, MaterialCircuitState) {
    let production_site = site(1);
    let input_good = good(2);
    let output_good = good(3);
    let goods_unit = unit(4);
    let labor_unit = unit(5);
    let process_id = process(6);
    {
        let state = MaterialCircuitState {
            capacity_reservations: CapacityReservations::default(),
            period: 1,
            final_demand_principals: vec![],
            final_demand_orders: vec![],
            accounting: CircuitAccounting::PhysicalControl,
            maintenance_service: None,
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities: vec![],
            corridor_capacities: vec![],
            inventory: vec![
                InventoryRow {
                    site_id: production_site,
                    good_id: input_good,
                    unit_id: goods_unit,
                    quantity: 2,
                },
                InventoryRow {
                    site_id: production_site,
                    good_id: output_good,
                    unit_id: goods_unit,
                    quantity: 0,
                },
            ],
            orders: Vec::new(),
            freight: Vec::new(),
            capacities: vec![CapacityRow {
                process_id,
                site_id: production_site,
                period: 1,
                available_batches: 1,
            }],
            labor: vec![LaborCapacityRow {
                site_id: production_site,
                unit_id: labor_unit,
                period: 1,
                available: 1,
            }],
            production_commitments: vec![ProductionCommitment {
                process_id,
                site_id: production_site,
                period: 1,
                planned_batches: 1,
            }],
        };
        (
            numeric_boundary_catalog(
                production_site,
                input_good,
                output_good,
                goods_unit,
                labor_unit,
                process_id,
            ),
            state,
        )
    }
}

fn numeric_boundary_catalog(
    production_site: SiteId,
    input_good: GoodId,
    output_good: GoodId,
    goods_unit: UnitId,
    labor_unit: UnitId,
    process_id: ProcessId,
) -> MaterialCatalog {
    MaterialCatalog::try_new(MaterialCatalog {
        capacity_policy: CapacitySupply::FiniteSchedule,
        merchants: vec![],
        handling_coefficients: vec![],
        maintenance_binding: None,
        site_logistics_nodes: vec![],
        commodities: vec![
            CommodityDefinition {
                good_id: input_good,
                unit_id: goods_unit,
                kind: babylon_material_circuit::CommodityKind::Storable { grams_per_unit: 1 },
            },
            CommodityDefinition {
                good_id: output_good,
                unit_id: goods_unit,
                kind: babylon_material_circuit::CommodityKind::Storable { grams_per_unit: 1 },
            },
        ],
        route_stages: vec![],
        process_outputs: vec![ProcessOutput {
            process_id,
            site_id: production_site,
            good_id: output_good,
            unit_id: goods_unit,
            quantity_per_batch: 1,
        }],
        input_coefficients: vec![InputOutputCoefficient {
            process_id,
            good_id: input_good,
            unit_id: goods_unit,
            quantity_per_batch: 2,
        }],
        labor_coefficients: vec![LaborCoefficient {
            process_id,
            unit_id: labor_unit,
            quantity_per_batch: 1,
        }],
        supplier_routes: Vec::new(),
        aid_mandates: Vec::new(),
        household_time_policy: Vec::new(),
        service_inputs: Vec::new(),
        household_needs: Vec::new(),
        catalog_digest: UNSEALED_CATALOG_DIGEST,
    })
    .expect("the authored fixture catalog is valid")
}

#[test]
fn zero_production_does_not_create_an_empty_inventory_row() {
    let production_site = site(1);
    let output_good = GoodId::from_bytes([0xff; 32]);
    let goods_unit = unit(2);
    let labor_unit = unit(3);
    let process_id = process(4);
    let inventory = (0..MAX_MATERIAL_CIRCUIT_ROWS)
        .map(|index| InventoryRow {
            site_id: numbered_site(index),
            good_id: good(0),
            unit_id: goods_unit,
            quantity: 1,
        })
        .collect();
    let (catalog, state) = {
        let state = MaterialCircuitState {
            capacity_reservations: CapacityReservations::default(),
            period: 1,
            final_demand_principals: vec![],
            final_demand_orders: vec![],
            accounting: CircuitAccounting::PhysicalControl,
            maintenance_service: None,
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities: vec![],
            corridor_capacities: vec![],
            inventory,
            orders: Vec::new(),
            freight: Vec::new(),
            capacities: Vec::new(),
            labor: Vec::new(),
            production_commitments: vec![ProductionCommitment {
                process_id,
                site_id: production_site,
                period: 1,
                planned_batches: 1,
            }],
        };
        (
            MaterialCatalog::try_new(MaterialCatalog {
                capacity_policy: CapacitySupply::FiniteSchedule,
                merchants: vec![],
                handling_coefficients: vec![],
                maintenance_binding: None,
                site_logistics_nodes: vec![],
                commodities: vec![
                    CommodityDefinition {
                        good_id: good(0),
                        unit_id: goods_unit,
                        kind: babylon_material_circuit::CommodityKind::Storable {
                            grams_per_unit: 1,
                        },
                    },
                    CommodityDefinition {
                        good_id: output_good,
                        unit_id: goods_unit,
                        kind: babylon_material_circuit::CommodityKind::Storable {
                            grams_per_unit: 1,
                        },
                    },
                ],
                route_stages: vec![],
                process_outputs: vec![ProcessOutput {
                    process_id,
                    site_id: production_site,
                    good_id: output_good,
                    unit_id: goods_unit,
                    quantity_per_batch: 1,
                }],
                input_coefficients: Vec::new(),
                labor_coefficients: vec![LaborCoefficient {
                    process_id,
                    unit_id: labor_unit,
                    quantity_per_batch: 1,
                }],
                supplier_routes: Vec::new(),
                aid_mandates: Vec::new(),
                household_time_policy: Vec::new(),
                service_inputs: Vec::new(),
                household_needs: Vec::new(),
                catalog_digest: UNSEALED_CATALOG_DIGEST,
            })
            .expect("the authored fixture catalog is valid"),
            state,
        )
    };

    let outcome = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("zero production is a valid outcome");
    assert_eq!(outcome.production[0].produced_batches, 0);
    assert_eq!(outcome.state.inventory.len(), MAX_MATERIAL_CIRCUIT_ROWS);
    assert!(outcome
        .state
        .inventory
        .iter()
        .all(|row| row.good_id != output_good));
}

#[test]
fn proportional_base_and_canonical_residual_are_row_order_independent() {
    let (mut catalog, mut state) = base_state();
    catalog.process_outputs.clear();
    catalog.input_coefficients.clear();
    catalog.labor_coefficients.clear();
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    state.capacities.clear();
    state.labor.clear();
    state.inventory[0].quantity = 4;
    state.orders = vec![
        OrderRow {
            ordered: 4,
            ..state.orders[0].clone()
        },
        OrderRow {
            order_id: order(9),
            ordered: 6,
            ..state.orders[0].clone()
        },
    ];
    let mut reversed = state.clone();
    reversed.orders.reverse();

    let a = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("allocation must close");
    let b = babylon_material_circuit::advance_material_circuit(&catalog, &reversed)
        .expect("permuted allocation must close");
    assert_eq!(a.state.orders[0].shipped, 2);
    assert_eq!(a.state.orders[1].shipped, 2);
    assert_eq!(inventory_quantity(&a.state, SUPPLIER, GRAIN), 0);
    assert_eq!(
        babylon_material_circuit::material_circuit_state_digest(&catalog, &a.state),
        babylon_material_circuit::material_circuit_state_digest(&catalog, &b.state)
    );
}

#[test]
fn arithmetic_refusal_does_not_publish_a_partial_state() {
    let (catalog, opening) = base_state();
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    let mut state = first.state;
    state
        .inventory
        .iter_mut()
        .find(|row| row.site_id == site(FACTORY) && row.good_id == good(GRAIN))
        .expect("the fixture holds the searched element")
        .quantity = u64::MAX;
    let before = babylon_material_circuit::material_circuit_state_digest(&catalog, &state)
        .expect("the material state has a digest");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(
        babylon_material_circuit::material_circuit_state_digest(&catalog, &state)
            .expect("the material state has a digest"),
        before
    );
}

#[test]
fn duplicate_dispatch_identity_is_rejected_even_when_arrival_periods_differ() {
    let (catalog, opening) = base_state();
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    let mut state = first.state;
    let mut duplicate = state.freight[0].clone();
    duplicate.stage_arrival_period += 1;
    state.freight.push(duplicate);
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::DuplicateRow)
    );
}
