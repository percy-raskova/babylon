//! A bounded maintenance dependency conserves parts and hours across period closes.
use babylon_material_circuit::AccountId;
use babylon_material_circuit::AidBook;
use babylon_material_circuit::CapacityReservations;
use babylon_material_circuit::CapacityRow;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::CommodityDefinition;
use babylon_material_circuit::CommodityKind;
use babylon_material_circuit::CorridorCapacity;
use babylon_material_circuit::CorridorId;
use babylon_material_circuit::EmploymentTerms;
use babylon_material_circuit::FinalDemandPrincipal;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::FinancialInstitutions;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_material_circuit::InputOutputCoefficient;
use babylon_material_circuit::InventoryRow;
use babylon_material_circuit::LaborCapacityRow;
use babylon_material_circuit::LaborCoefficient;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::LogisticsNodeId;
use babylon_material_circuit::MaintenanceBinding;
use babylon_material_circuit::MaintenanceService;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCatalogDefinition;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialCircuitTransition;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::MonetaryCircuit;
use babylon_material_circuit::OrderAccessMode;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::OrderRow;
use babylon_material_circuit::ProcessId;
use babylon_material_circuit::ProcessOutput;
use babylon_material_circuit::ProductionCommitment;
use babylon_material_circuit::RouteId;
use babylon_material_circuit::RouteStage;
use babylon_material_circuit::RouteStageCapacity;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::SiteLogisticsNode;
use babylon_material_circuit::StaffingMemberId;
use babylon_material_circuit::StaffingPolicy;
use babylon_material_circuit::StaffingPoolBinding;
use babylon_material_circuit::StaffingPoolId;
use babylon_material_circuit::StaffingPoolState;
use babylon_material_circuit::StaffingState;
use babylon_material_circuit::StaffingTransition;
use babylon_material_circuit::StaffingWorkSource;
use babylon_material_circuit::StockCarryingValue;
use babylon_material_circuit::SupplierRoute;
use babylon_material_circuit::SupplierTransport;
use babylon_material_circuit::UnitId;
use babylon_material_circuit::MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES;

fn site(id: u8) -> SiteId {
    SiteId::from_bytes([id; 32])
}
fn good(id: u8) -> GoodId {
    GoodId::from_bytes([id; 32])
}
fn unit(id: u8) -> UnitId {
    UnitId::from_bytes([id; 32])
}
fn process() -> ProcessId {
    ProcessId::from_bytes([1; 32])
}
#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
fn opening(parts: u64, provider_hours: u64) -> (MaterialCatalog, MaterialCircuitState) {
    {
        let state = MaterialCircuitState {
            capacity_reservations: CapacityReservations::default(),
            period: 1,
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities: vec![],
            inventory: vec![
                InventoryRow {
                    site_id: site(1),
                    good_id: good(1),
                    unit_id: unit(1),
                    quantity: 2560,
                },
                InventoryRow {
                    site_id: site(2),
                    good_id: good(2),
                    unit_id: unit(1),
                    quantity: parts,
                },
            ],
            orders: vec![],
            freight: vec![],
            corridor_capacities: vec![],
            capacities: (1..=6)
                .map(|period| CapacityRow {
                    process_id: process(),
                    site_id: site(1),
                    period,
                    available_batches: 16,
                })
                .collect(),
            labor: (1..=6)
                .flat_map(|period| {
                    [
                        LaborCapacityRow {
                            site_id: site(1),
                            unit_id: unit(2),
                            period,
                            available: 1280,
                        },
                        LaborCapacityRow {
                            site_id: site(2),
                            unit_id: unit(2),
                            period,
                            available: provider_hours,
                        },
                    ]
                })
                .collect(),
            production_commitments: vec![ProductionCommitment {
                process_id: process(),
                site_id: site(1),
                period: 1,
                planned_batches: 16,
            }],
            final_demand_principals: vec![],
            final_demand_orders: vec![],
            accounting: babylon_material_circuit::CircuitAccounting::PhysicalControl,
            maintenance_service: Some(MaintenanceService {
                period: 1,
                available_batches: 16,
            }),
        };
        (
            MaterialCatalog::try_new(MaterialCatalogDefinition {
                capacity_policy: CapacitySupply::FiniteSchedule,
                site_logistics_nodes: (1..=3)
                    .map(|id| SiteLogisticsNode {
                        site_id: site(id),
                        node_id: LogisticsNodeId::from_bytes([id; 32]),
                    })
                    .collect(),
                process_outputs: vec![ProcessOutput {
                    process_id: process(),
                    site_id: site(1),
                    good_id: good(2),
                    unit_id: unit(1),
                    quantity_per_batch: 60,
                }],
                input_coefficients: vec![InputOutputCoefficient {
                    process_id: process(),
                    good_id: good(1),
                    unit_id: unit(1),
                    quantity_per_batch: 80,
                }],
                labor_coefficients: vec![LaborCoefficient {
                    process_id: process(),
                    unit_id: unit(2),
                    quantity_per_batch: 60,
                }],
                commodities: vec![
                    CommodityDefinition {
                        good_id: good(1),
                        unit_id: unit(1),
                        kind: babylon_material_circuit::CommodityKind::Storable {
                            grams_per_unit: 1000,
                        },
                    },
                    CommodityDefinition {
                        good_id: good(2),
                        unit_id: unit(1),
                        kind: babylon_material_circuit::CommodityKind::Storable {
                            grams_per_unit: 1000,
                        },
                    },
                ],
                supplier_routes: vec![],
                route_stages: vec![],
                merchants: vec![],
                handling_coefficients: vec![],
                maintenance_binding: Some(MaintenanceBinding {
                    provider_site_id: site(2),
                    consumer_process_id: process(),
                    spare_good_id: good(2),
                    spare_unit_id: unit(1),
                    labor_unit_id: unit(2),
                    spare_units_per_job: 1,
                    labor_units_per_job: 10,
                    enabled_batches_per_job: 1,
                    maximum_jobs_per_period: 16,
                }),
                aid_mandates: Vec::new(),
                household_time_policy: Vec::new(),
                service_inputs: Vec::new(),
                household_needs: Vec::new(),
            })
            .expect("the authored fixture catalog is valid"),
            state,
        )
    }
}
fn restock(catalog: &mut MaterialCatalogDefinition, state: &mut MaterialCircuitState) {
    for (id, buyer, quantity) in [(1, 2, 256), (2, 3, 3840)] {
        let order_id = OrderId::from_bytes([id; 32]);
        catalog.supplier_routes.push(SupplierRoute {
            buyer_site_id: site(buyer),
            supplier_site_id: site(1),
            good_id: good(2),
            unit_id: unit(1),
            route_id: RouteId::from_bytes([id; 32]),
            transport_kind: SupplierTransport::Local,
        });
        state.orders.push(OrderRow {
            order_id,
            access_mode: OrderAccessMode::CommoditySale,
            buyer_site_id: site(buyer),
            supplier_site_id: site(1),
            good_id: good(2),
            unit_id: unit(1),
            ordered: quantity,
            shipped: 0,
            lost: 0,
            delivered: 0,
            realized: 0,
        });
    }
}
fn people(provider_employed: u64) -> StaffingState {
    StaffingState::try_new(
        1,
        vec![
            (1, 12, 8, StaffingWorkSource::Production(process())),
            (
                2,
                1,
                provider_employed,
                StaffingWorkSource::Maintenance(site(2)),
            ),
        ]
        .into_iter()
        .map(|(id, total, employed, source)| {
            let binding = StaffingPoolBinding::try_new(
                StaffingPoolId::from_bytes([id; 32]),
                site(id),
                unit(2),
                total,
                StaffingPolicy::one_period(160).expect("the one-period fixture advances"),
                vec![source],
            )
            .expect("the authored fixture satisfies the constructor invariants");
            StaffingPoolState::try_new(binding, employed, total - employed, 0)
                .expect("the authored fixture satisfies the constructor invariants")
        })
        .collect(),
    )
    .expect("the authored fixture satisfies the constructor invariants")
}
fn staffed(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    people: &StaffingState,
) -> (MaterialCircuitTransition, StaffingTransition) {
    let closed = babylon_material_circuit::close_material_period(catalog, state)
        .expect("the material period closes");
    let bindings: Vec<_> = people
        .pools()
        .iter()
        .map(|pool| pool.binding().clone())
        .collect();
    let requests = closed
        .staffing_requests(catalog, &bindings)
        .expect("the fixture staffing requests are present");
    let staffing = babylon_material_circuit::advance_staffing(people, &requests)
        .expect("the fixture staffing advances");
    (
        closed
            .finish_with_labor(catalog, staffing.next_labor().to_vec())
            .expect("the fixture completes with labor"),
        staffing,
    )
}
fn produced(transition: &MaterialCircuitTransition) -> u64 {
    transition
        .production
        .iter()
        .map(|row| row.produced_batches * 60)
        .sum()
}
fn stock(state: &MaterialCircuitState, site_id: SiteId, good_id: GoodId) -> u64 {
    state
        .inventory
        .iter()
        .find(|row| row.site_id == site_id && row.good_id == good_id)
        .map_or(0, |row| row.quantity)
}

#[test]
fn four_cases_bind_labor_and_parts_then_rehire_and_recover() {
    for (parts, employed) in [(256, 1), (256, 0), (0, 1), (0, 0)] {
        let (catalog, mut state) = opening(parts, employed * 160);
        let mut definition = catalog.into_definition();
        restock(&mut definition, &mut state);
        let catalog = MaterialCatalog::try_new(definition).expect("valid definitions");
        let original = state.clone();
        let (first, staff1) = staffed(&catalog, &state, &people(employed));
        let receipt = first
            .maintenance
            .as_ref()
            .expect("the fixture set the optional field before this read");
        assert_eq!(produced(&first), 960);
        assert_eq!(receipt.requested_jobs, 16);
        assert_eq!(
            receipt.completed_jobs,
            if parts > 0 && employed > 0 { 16 } else { 0 }
        );
        assert_eq!(
            receipt.available_spare_parts, parts,
            "local credits follow maintenance"
        );
        assert_eq!(
            first
                .local_transfers
                .iter()
                .find(|row| row.buyer_site_id == site(2))
                .expect("the fixture holds the searched element")
                .quantity,
            60
        );
        assert_eq!(
            stock(&first.state, site(2), good(2)),
            parts - receipt.completed_jobs + 60
        );
        assert_eq!(staff1.state().pools()[1].employed(), 1);
        let (second, staff2) = staffed(&catalog, &first.state, staff1.state());
        assert_eq!(
            produced(&second),
            if parts > 0 && employed > 0 { 960 } else { 0 }
        );
        if parts == 0 || employed == 0 {
            assert_eq!(
                second
                    .maintenance
                    .as_ref()
                    .expect("the fixture set the optional field before this read")
                    .completed_jobs,
                16
            );
            let (third, _) = staffed(&catalog, &second.state, staff2.state());
            assert_eq!(produced(&third), 960);
        }
        assert_eq!(state, original, "detached close must not mutate its input");
    }
}

#[test]
fn whole_jobs_debit_exact_inputs_and_expire_unused_service() {
    let (catalog, mut state) = opening(7, 19);
    let mut catalog = catalog.into_definition();
    catalog
        .maintenance_binding
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .spare_units_per_job = 3;
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    state.production_commitments[0].planned_batches = 4;
    let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let receipt = result
        .maintenance
        .expect("the fixture receipt carries its maintenance section");
    assert_eq!(
        (
            receipt.completed_jobs,
            receipt.consumed_spare_parts,
            receipt.consumed_labor_hours
        ),
        (1, 3, 10)
    );
    assert_eq!(
        (
            receipt.opening_service_batches,
            receipt.consumed_service_batches,
            receipt.expired_service_batches
        ),
        (16, 4, 12)
    );
    assert_eq!(
        receipt.next_service,
        MaintenanceService {
            period: 2,
            available_batches: 1
        }
    );
    assert_eq!(stock(&result.state, site(2), good(2)), 4);
    assert_eq!(result.state.production_commitments[0].planned_batches, 1);
}

#[test]
fn expired_or_absent_service_never_enables_current_production_or_suppresses_demand() {
    let (catalog, mut state) = opening(256, 160);
    state
        .maintenance_service
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .available_batches = 0;
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(produced(&first), 0);
    assert_eq!(
        first
            .maintenance
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .requested_jobs,
        16
    );
    assert_eq!(
        first
            .maintenance
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .completed_jobs,
        16
    );
    assert_eq!(
        produced(
            &babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
                .expect("the authored material state advances one period")
        ),
        960
    );

    state.production_commitments.clear();
    state.inventory[0].quantity = 0;
    state
        .maintenance_service
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .available_batches = 16;
    let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let receipt = result
        .maintenance
        .expect("the fixture receipt carries its maintenance section");
    assert_eq!(
        (
            receipt.requested_jobs,
            receipt.completed_jobs,
            receipt.expired_service_batches
        ),
        (0, 0, 16)
    );
    assert_eq!(
        result
            .state
            .maintenance_service
            .expect("the fixture state carries its maintenance service")
            .available_batches,
        0
    );
}

#[test]
fn maintenance_capacity_is_per_period_and_demand_precedes_its_limit() {
    let (catalog, mut state) = opening(256, 1000);
    state.production_commitments.clear();
    state.inventory[0].quantity = 80 * 40;
    state
        .capacities
        .iter_mut()
        .for_each(|row| row.available_batches = 40);
    let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let receipt = result
        .maintenance
        .expect("the fixture receipt carries its maintenance section");
    assert_eq!(
        (
            receipt.prospective_batches,
            receipt.requested_jobs,
            receipt.completed_jobs
        ),
        (40, 40, 16)
    );
    assert_eq!(receipt.next_service.available_batches, 16);
}

#[test]
fn zero_service_and_zero_employment_preserve_both_staffing_requests() {
    let (catalog, mut state) = opening(0, 0);
    state
        .maintenance_service
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .available_batches = 0;
    for row in &mut state.labor {
        row.available = 0;
    }
    let closed = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes");
    let bindings: Vec<_> = people(0)
        .pools()
        .iter()
        .map(|pool| pool.binding().clone())
        .collect();
    let requests = closed
        .staffing_requests(&catalog, &bindings)
        .expect("the fixture staffing requests are present");
    assert_eq!(requests[0].hours(), 960);
    assert_eq!(requests[1].hours(), 160);
}

#[test]
fn canonical_replay_and_restart_preserve_maintenance_and_reject_old_version() {
    let (catalog, mut state) = opening(256, 160);
    let mut catalog = catalog.into_definition();
    restock(&mut catalog, &mut state);
    let expected_catalog = MaterialCatalog::try_new(catalog.clone()).expect("valid definitions");
    let expected = babylon_material_circuit::advance_material_circuit(&expected_catalog, &state)
        .expect("the authored material state advances one period");
    state.inventory.reverse();
    state.labor.reverse();
    state.capacities.reverse();
    state.orders.reverse();
    catalog.supplier_routes.reverse();
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period"),
        expected
    );
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &expected.state)
        .expect("the canonical material state encodes");
    let restored = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
        .expect("the canonical material bytes decode");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &restored),
        babylon_material_circuit::advance_material_circuit(&catalog, &expected.state)
    );
    let mut obsolete = bytes;
    let offset = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    obsolete[offset..offset + 2].copy_from_slice(&3_u16.to_be_bytes());
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &obsolete),
        Err(MaterialCircuitError::WireVersion)
    );
}

#[test]
fn invalid_maintenance_bindings_and_overflow_refuse_atomically() {
    let (catalog, state) = opening(256, 160);
    let definition_mutations: &[fn(&mut MaterialCatalogDefinition)] = &[
        |c| {
            c.maintenance_binding
                .as_mut()
                .expect("the fixture set the optional field before this borrow")
                .spare_units_per_job = 0;
        },
        |c| {
            c.maintenance_binding
                .as_mut()
                .expect("the fixture set the optional field before this borrow")
                .labor_units_per_job = 0;
        },
        |c| {
            c.maintenance_binding
                .as_mut()
                .expect("the fixture set the optional field before this borrow")
                .enabled_batches_per_job = 0;
        },
        |c| {
            c.maintenance_binding
                .as_mut()
                .expect("the fixture set the optional field before this borrow")
                .maximum_jobs_per_period = 0;
        },
    ];
    for mutate in definition_mutations {
        let mut invalid = catalog.clone().into_definition();
        mutate(&mut invalid);
        assert_eq!(
            MaterialCatalog::try_new(invalid),
            Err(MaterialCircuitError::MaintenanceInvariant)
        );
    }
    let mut overflow = catalog.clone().into_definition();
    overflow
        .maintenance_binding
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .enabled_batches_per_job = u64::MAX;
    assert_eq!(
        MaterialCatalog::try_new(overflow),
        Err(MaterialCircuitError::Arithmetic)
    );
    let mut unbound = catalog.clone().into_definition();
    unbound.maintenance_binding = None;
    let unbound = MaterialCatalog::try_new(unbound).expect("valid definitions");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&unbound, &state),
        Err(MaterialCircuitError::MaintenanceInvariant)
    );
    let relational_mutations: &[fn(&mut MaterialCatalogDefinition)] = &[
        |c| {
            c.maintenance_binding
                .as_mut()
                .expect("the fixture set the optional field before this borrow")
                .provider_site_id = site(1);
        },
        |c| {
            c.maintenance_binding
                .as_mut()
                .expect("the fixture set the optional field before this borrow")
                .consumer_process_id = ProcessId::from_bytes([9; 32]);
        },
    ];
    for mutate in relational_mutations {
        let mut invalid = catalog.clone().into_definition();
        mutate(&mut invalid);
        let invalid = MaterialCatalog::try_new(invalid).expect("the changed catalog is valid");
        assert_eq!(
            babylon_material_circuit::advance_material_circuit(&invalid, &state),
            Err(MaterialCircuitError::MaintenanceInvariant)
        );
    }
    let mut state_service = state.clone();
    state_service.maintenance_service = None;
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state_service),
        Err(MaterialCircuitError::MaintenanceInvariant)
    );
    let mut late_service = state;
    late_service
        .maintenance_service
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .period = 2;
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &late_service),
        Err(MaterialCircuitError::MaintenanceInvariant)
    );
}

#[test]
fn due_freight_supplies_jobs_before_local_outbound_credits() {
    let (catalog, mut state) = opening(0, 160);
    let mut catalog = catalog.into_definition();
    let order_id = OrderId::from_bytes([4; 32]);
    let route_id = RouteId::from_bytes([4; 32]);
    let corridor_id = CorridorId::from_bytes([4; 32]);
    state.inventory.push(InventoryRow {
        site_id: site(3),
        good_id: good(2),
        unit_id: unit(1),
        quantity: 17,
    });
    state.orders.push(OrderRow {
        order_id,
        access_mode: OrderAccessMode::CommoditySale,
        buyer_site_id: site(2),
        supplier_site_id: site(3),
        good_id: good(2),
        unit_id: unit(1),
        ordered: 17,
        shipped: 0,
        lost: 0,
        delivered: 0,
        realized: 0,
    });
    catalog.supplier_routes.push(SupplierRoute {
        buyer_site_id: site(2),
        supplier_site_id: site(3),
        good_id: good(2),
        unit_id: unit(1),
        route_id,
        transport_kind: SupplierTransport::Staged,
    });
    catalog.route_stages.push(RouteStage {
        route_id,
        stage_index: 0,
        from_node_id: LogisticsNodeId::from_bytes([3; 32]),
        to_node_id: LogisticsNodeId::from_bytes([2; 32]),
        travel_periods: 1,
        loss_ppm: 0,
    });
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id,
        stage_index: 0,
        corridor_id,
    });
    state.corridor_capacities.push(CorridorCapacity {
        corridor_id,
        period: 1,
        available_grams: 17_000,
    });
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(
        first
            .maintenance
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .completed_jobs,
        0
    );
    assert_eq!(first.dispatches[0].quantity, 17);
    let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("the authored material state advances one period");
    let receipt = second
        .maintenance
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(produced(&second), 0);
    assert_eq!(
        (
            receipt.opening_spare_parts,
            receipt.arrived_spare_parts,
            receipt.available_spare_parts
        ),
        (0, 17, 17)
    );
    assert_eq!(
        (receipt.completed_jobs, receipt.consumed_spare_parts),
        (16, 16)
    );
    assert_eq!(stock(&second.state, site(2), good(2)), 1);
    assert_eq!(
        produced(
            &babylon_material_circuit::advance_material_circuit(&catalog, &second.state)
                .expect("the authored material state advances one period")
        ),
        960
    );
}

#[test]
fn resource_sharing_is_refused_instead_of_imposing_hidden_priority() {
    let (catalog, state) = opening(256, 160);
    let catalog = catalog.into_definition();
    let mut shared_process = catalog.clone();
    let other = ProcessId::from_bytes([9; 32]);
    shared_process.process_outputs.push(ProcessOutput {
        process_id: other,
        site_id: site(1),
        good_id: good(3),
        unit_id: unit(1),
        quantity_per_batch: 1,
    });
    shared_process.commodities.push(CommodityDefinition {
        good_id: good(3),
        unit_id: unit(1),
        kind: CommodityKind::Storable {
            grams_per_unit: 1000,
        },
    });
    shared_process.labor_coefficients.push(LaborCoefficient {
        process_id: other,
        unit_id: unit(2),
        quantity_per_batch: 1,
    });
    let shared_process = MaterialCatalog::try_new(shared_process).expect("valid definitions");
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&shared_process, &state),
        Err(MaterialCircuitError::MaintenanceInvariant)
    );
    for (supplier, material) in [(site(2), good(2)), (site(1), good(1))] {
        let mut shared_order = state.clone();
        let order_id = OrderId::from_bytes([9; 32]);
        shared_order.orders.push(OrderRow {
            order_id,
            access_mode: OrderAccessMode::CommoditySale,
            buyer_site_id: site(3),
            supplier_site_id: supplier,
            good_id: material,
            unit_id: unit(1),
            ordered: 1,
            shipped: 0,
            lost: 0,
            delivered: 0,
            realized: 0,
        });
        assert_eq!(
            babylon_material_circuit::advance_material_circuit(&catalog, &shared_order),
            Err(MaterialCircuitError::MaintenanceInvariant)
        );
    }
}

#[test]
fn failed_later_outbound_credit_publishes_no_maintenance_or_debits() {
    let (catalog, mut state) = opening(u64::MAX, 160);
    let mut definition = catalog.into_definition();
    restock(&mut definition, &mut state);
    let catalog = MaterialCatalog::try_new(definition).expect("valid definitions");
    let original = state.clone();
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(state, original);
}

#[test]
fn unrepresentable_maintenance_demand_does_not_disappear_with_zero_resources() {
    let (catalog, mut state) = opening(0, 0);
    let mut catalog = catalog.into_definition();
    state
        .maintenance_service
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .available_batches = 0;
    state.production_commitments.clear();
    state.inventory[0].quantity = u64::MAX;
    catalog.input_coefficients[0].quantity_per_batch = 1;
    catalog.labor_coefficients[0].quantity_per_batch = 1;
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    for row in &mut state.capacities {
        row.available_batches = u64::MAX;
    }
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::Arithmetic)
    );
}

#[test]
fn idle_consumer_and_provider_rehire_after_later_material_arrival() {
    let (catalog, mut state) = opening(256, 160);
    let mut catalog = catalog.into_definition();
    for period in [7, 8] {
        state.capacities.push(CapacityRow {
            process_id: process(),
            site_id: site(1),
            period,
            available_batches: 16,
        });
    }
    let order_id = OrderId::from_bytes([5; 32]);
    let route_id = RouteId::from_bytes([5; 32]);
    let corridor_id = CorridorId::from_bytes([5; 32]);
    state.inventory.push(InventoryRow {
        site_id: site(3),
        good_id: good(1),
        unit_id: unit(1),
        quantity: 1280,
    });
    state.orders.push(OrderRow {
        order_id,
        access_mode: OrderAccessMode::CommoditySale,
        buyer_site_id: site(1),
        supplier_site_id: site(3),
        good_id: good(1),
        unit_id: unit(1),
        ordered: 1280,
        shipped: 0,
        lost: 0,
        delivered: 0,
        realized: 0,
    });
    catalog.supplier_routes.push(SupplierRoute {
        buyer_site_id: site(1),
        supplier_site_id: site(3),
        good_id: good(1),
        unit_id: unit(1),
        route_id,
        transport_kind: SupplierTransport::Staged,
    });
    catalog.route_stages.push(RouteStage {
        route_id,
        stage_index: 0,
        from_node_id: LogisticsNodeId::from_bytes([3; 32]),
        to_node_id: LogisticsNodeId::from_bytes([1; 32]),
        travel_periods: 4,
        loss_ppm: 0,
    });
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id,
        stage_index: 0,
        corridor_id,
    });
    state.corridor_capacities.push(CorridorCapacity {
        corridor_id,
        period: 1,
        available_grams: 1_280_000,
    });
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let mut staff = people(1);
    let mut output = Vec::new();
    let mut jobs = Vec::new();
    let mut employment = Vec::new();
    for _ in 1..=7 {
        let (transition, next_staff) = staffed(&catalog, &state, &staff);
        output.push(produced(&transition));
        jobs.push(
            transition
                .maintenance
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .completed_jobs,
        );
        employment.push((
            next_staff.state().pools()[0].employed(),
            next_staff.state().pools()[1].employed(),
        ));
        state = transition.state;
        staff = next_staff.into_state();
    }
    assert_eq!(output, [960, 960, 0, 0, 0, 0, 960]);
    assert_eq!(jobs, [16, 0, 0, 0, 0, 16, 0]);
    assert_eq!(
        employment,
        [(6, 1), (6, 1), (0, 0), (0, 0), (6, 1), (6, 1), (6, 1)]
    );
}

#[test]
fn spare_quantity_and_labor_time_cannot_share_a_unit() {
    let (catalog, mut state) = opening(256, 160);
    let mut shared_unit = catalog.clone().into_definition();
    shared_unit
        .maintenance_binding
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .labor_unit_id = unit(1);
    assert_eq!(
        MaterialCatalog::try_new(shared_unit),
        Err(MaterialCircuitError::MaintenanceInvariant)
    );
    for row in &mut state.labor {
        if row.site_id == site(2) {
            row.unit_id = unit(1);
        }
    }
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::MaintenanceInvariant)
    );
}

#[test]
fn spare_parts_independently_limit_positive_whole_jobs() {
    let (catalog, state) = opening(7, 160);
    let mut catalog = catalog.into_definition();
    catalog
        .maintenance_binding
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .spare_units_per_job = 3;
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let receipt = result
        .maintenance
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(receipt.requested_jobs, 16);
    assert_eq!(receipt.available_labor_hours, 160);
    assert_eq!(receipt.completed_jobs, 2);
    assert_eq!(receipt.consumed_spare_parts, 6);
    assert_eq!(receipt.consumed_labor_hours, 20);
    assert_eq!(stock(&result.state, site(2), good(2)), 1);
    assert_eq!(receipt.next_service.available_batches, 2);
    assert_eq!(result.state.production_commitments[0].planned_batches, 2);
}

fn paid_maintenance_opening() -> (MaterialCatalog, MaterialCircuitState) {
    use babylon_kernel::currency::Currency;
    let money = Currency::from_micro_units;
    let (catalog, mut state) = opening(2, 20);
    let payee = FinalDemandPrincipalId::from_bytes([7; 32]);
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: payee,
        location: "county:26163"
            .parse()
            .expect("the authored literal parses as the declared type"),
    });
    let book = MonetaryBook::open(vec![
        CashAccount {
            id: AccountId::Site(site(1)),
            cash: money(1280),
        },
        CashAccount {
            id: AccountId::Site(site(2)),
            cash: money(20),
        },
        CashAccount {
            id: AccountId::Site(site(3)),
            cash: money(0),
        },
        CashAccount {
            id: AccountId::Household(payee),
            cash: money(0),
        },
    ])
    .expect("the fixture opens the authored source");
    let costs = HistoricalCostBook::open(
        &book,
        vec![
            StockCarryingValue {
                owner: AccountId::Site(site(1)),
                good_id: good(1),
                unit_id: unit(1),
                amount: money(2560),
            },
            StockCarryingValue {
                owner: AccountId::Site(site(2)),
                good_id: good(2),
                unit_id: unit(1),
                amount: money(6),
            },
        ],
        vec![],
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
    state.accounting = CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
        aid: AidBook::default(),

        household_time: HouseholdTimeAccounting::NotModeled,
        financial: FinancialInstitutions::empty(),
        member_labor: state
            .labor
            .iter()
            .map(|row| babylon_material_circuit::MemberLaborCapacityRow {
                member_id: StaffingMemberId::from_bytes(row.site_id.as_bytes()),
                period: row.period,
                available_hours: row.available,
            })
            .collect(),
        book,
        costs,
        employment: [1, 2]
            .into_iter()
            .map(|id| EmploymentTerms {
                member_id: StaffingMemberId::from_bytes((site(id)).as_bytes()),
                site_id: site(id),
                unit_id: unit(2),
                payee,
                compensation: LaborCompensation::Wage(money(1)),
            })
            .collect(),
        recurring: None,
    }));
    (catalog, state)
}

#[test]
fn historical_cost_maintenance_and_idle_work_are_expenses_not_output_assets() {
    use babylon_kernel::currency::Currency;
    let money = Currency::from_micro_units;
    let (catalog, state) = paid_maintenance_opening();
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let producer = &closed
        .income
        .iter()
        .find(|row| row.account == AccountId::Site(site(1)))
        .expect("the fixture holds the searched element")
        .statement;
    assert_eq!(producer.productive_labor_capitalized, money(960));
    assert_eq!(producer.idle_labor_expense, money(320));
    assert_eq!(
        producer.net_income().expect("the fixture book balances"),
        money(-320)
    );
    let provider = &closed
        .income
        .iter()
        .find(|row| row.account == AccountId::Site(site(2)))
        .expect("the fixture holds the searched element")
        .statement;
    assert_eq!(provider.maintenance_material_expense, money(6));
    assert_eq!(provider.maintenance_labor_expense, money(20));
    assert_eq!(
        provider.net_income().expect("the fixture book balances"),
        money(-26)
    );
    let CircuitAccounting::Monetary(economy) = &closed.state.accounting else {
        unreachable!()
    };
    assert_eq!(
        economy
            .costs
            .snapshot()
            .stocks
            .iter()
            .find(|row| row.owner == AccountId::Site(site(1)) && row.good_id == good(2))
            .expect("the fixture holds the searched element")
            .amount,
        money(2240)
    );
    assert_eq!(
        economy
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(1300)
    );
}
