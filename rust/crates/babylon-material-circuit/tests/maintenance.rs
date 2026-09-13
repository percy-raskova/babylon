//! A bounded maintenance dependency conserves parts and hours across period closes.
use babylon_material_circuit::*;

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
fn opening(parts: u64, provider_hours: u64) -> MaterialCircuitState {
    MaterialCircuitState {
        period: 1,
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
        freight_mass_coefficients: vec![FreightMassCoefficient {
            good_id: good(2),
            unit_id: unit(1),
            grams_per_unit: 1000,
        }],
        supplier_routes: vec![],
        route_stages: vec![],
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
        backlog: vec![],
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
        merchants: vec![],
        handling_coefficients: vec![],
        final_demand_principals: vec![],
        final_demand_orders: vec![],
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
        maintenance_service: Some(MaintenanceService {
            period: 1,
            available_batches: 16,
        }),
    }
}
fn restock(state: &mut MaterialCircuitState) {
    for (id, buyer, quantity) in [(1, 2, 256), (2, 3, 3840)] {
        let order_id = OrderId::from_bytes([id; 32]);
        state.supplier_routes.push(SupplierRoute {
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
        state.backlog.push(BacklogRow { order_id, quantity });
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
                StaffingPolicy::one_period(160).unwrap(),
                vec![source],
            )
            .unwrap();
            StaffingPoolState::try_new(binding, employed, total - employed, 0).unwrap()
        })
        .collect(),
    )
    .unwrap()
}
fn staffed(
    state: &MaterialCircuitState,
    people: &StaffingState,
) -> (MaterialCircuitTransition, StaffingTransition) {
    let closed = close_material_period(state).unwrap();
    let bindings: Vec<_> = people
        .pools()
        .iter()
        .map(|pool| pool.binding().clone())
        .collect();
    let requests = closed.staffing_requests(&bindings).unwrap();
    let staffing = advance_staffing(people, &requests).unwrap();
    (
        closed
            .finish_with_labor(staffing.next_labor().to_vec())
            .unwrap(),
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
        let mut state = opening(parts, employed * 160);
        restock(&mut state);
        let original = state.clone();
        let (first, staff1) = staffed(&state, &people(employed));
        let receipt = first.maintenance.as_ref().unwrap();
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
                .unwrap()
                .quantity,
            60
        );
        assert_eq!(
            stock(&first.state, site(2), good(2)),
            parts - receipt.completed_jobs + 60
        );
        assert_eq!(staff1.state().pools()[1].employed(), 1);
        let (second, staff2) = staffed(&first.state, staff1.state());
        assert_eq!(
            produced(&second),
            if parts > 0 && employed > 0 { 960 } else { 0 }
        );
        if parts == 0 || employed == 0 {
            assert_eq!(second.maintenance.as_ref().unwrap().completed_jobs, 16);
            let (third, _) = staffed(&second.state, staff2.state());
            assert_eq!(produced(&third), 960);
        }
        assert_eq!(state, original, "detached close must not mutate its input");
    }
}

#[test]
fn whole_jobs_debit_exact_inputs_and_expire_unused_service() {
    let mut state = opening(7, 19);
    state
        .maintenance_binding
        .as_mut()
        .unwrap()
        .spare_units_per_job = 3;
    state.production_commitments[0].planned_batches = 4;
    let result = advance_material_circuit(&state).unwrap();
    let receipt = result.maintenance.unwrap();
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
    let mut state = opening(256, 160);
    state
        .maintenance_service
        .as_mut()
        .unwrap()
        .available_batches = 0;
    let first = advance_material_circuit(&state).unwrap();
    assert_eq!(produced(&first), 0);
    assert_eq!(first.maintenance.as_ref().unwrap().requested_jobs, 16);
    assert_eq!(first.maintenance.as_ref().unwrap().completed_jobs, 16);
    assert_eq!(
        produced(&advance_material_circuit(&first.state).unwrap()),
        960
    );

    state.production_commitments.clear();
    state.inventory[0].quantity = 0;
    state
        .maintenance_service
        .as_mut()
        .unwrap()
        .available_batches = 16;
    let result = advance_material_circuit(&state).unwrap();
    let receipt = result.maintenance.unwrap();
    assert_eq!(
        (
            receipt.requested_jobs,
            receipt.completed_jobs,
            receipt.expired_service_batches
        ),
        (0, 0, 16)
    );
    assert_eq!(
        result.state.maintenance_service.unwrap().available_batches,
        0
    );
}

#[test]
fn maintenance_capacity_is_per_period_and_demand_precedes_its_limit() {
    let mut state = opening(256, 1000);
    state.production_commitments.clear();
    state.inventory[0].quantity = 80 * 40;
    state
        .capacities
        .iter_mut()
        .for_each(|row| row.available_batches = 40);
    let result = advance_material_circuit(&state).unwrap();
    let receipt = result.maintenance.unwrap();
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
    let mut state = opening(0, 0);
    state
        .maintenance_service
        .as_mut()
        .unwrap()
        .available_batches = 0;
    for row in &mut state.labor {
        row.available = 0;
    }
    let closed = close_material_period(&state).unwrap();
    let bindings: Vec<_> = people(0)
        .pools()
        .iter()
        .map(|pool| pool.binding().clone())
        .collect();
    let requests = closed.staffing_requests(&bindings).unwrap();
    assert_eq!(requests[0].hours(), 960);
    assert_eq!(requests[1].hours(), 160);
}

#[test]
fn canonical_replay_and_restart_preserve_maintenance_and_reject_old_version() {
    let mut state = opening(256, 160);
    restock(&mut state);
    let expected = advance_material_circuit(&state).unwrap();
    state.inventory.reverse();
    state.labor.reverse();
    state.capacities.reverse();
    state.orders.reverse();
    state.backlog.reverse();
    state.supplier_routes.reverse();
    assert_eq!(advance_material_circuit(&state).unwrap(), expected);
    let bytes = encode_material_circuit_state(&expected.state).unwrap();
    let restored = decode_material_circuit_state(&bytes).unwrap();
    assert_eq!(
        advance_material_circuit(&restored),
        advance_material_circuit(&expected.state)
    );
    let mut obsolete = bytes;
    let offset = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    obsolete[offset..offset + 2].copy_from_slice(&3_u16.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&obsolete),
        Err(MaterialCircuitError::WireVersion)
    );
}

#[test]
fn invalid_maintenance_bindings_and_overflow_refuse_atomically() {
    let state = opening(256, 160);
    for mutate in [
        |row: &mut MaterialCircuitState| row.maintenance_service = None,
        |row: &mut MaterialCircuitState| row.maintenance_binding = None,
        |row: &mut MaterialCircuitState| row.maintenance_service.as_mut().unwrap().period = 2,
        |row: &mut MaterialCircuitState| {
            row.maintenance_binding.as_mut().unwrap().provider_site_id = site(1)
        },
        |row: &mut MaterialCircuitState| {
            row.maintenance_binding
                .as_mut()
                .unwrap()
                .consumer_process_id = ProcessId::from_bytes([9; 32])
        },
        |row: &mut MaterialCircuitState| {
            row.maintenance_binding
                .as_mut()
                .unwrap()
                .spare_units_per_job = 0
        },
        |row: &mut MaterialCircuitState| {
            row.maintenance_binding
                .as_mut()
                .unwrap()
                .labor_units_per_job = 0
        },
        |row: &mut MaterialCircuitState| {
            row.maintenance_binding
                .as_mut()
                .unwrap()
                .enabled_batches_per_job = 0
        },
        |row: &mut MaterialCircuitState| {
            row.maintenance_binding
                .as_mut()
                .unwrap()
                .maximum_jobs_per_period = 0
        },
    ] {
        let mut invalid = state.clone();
        mutate(&mut invalid);
        let original = invalid.clone();
        assert_eq!(
            advance_material_circuit(&invalid),
            Err(MaterialCircuitError::MaintenanceInvariant)
        );
        assert_eq!(invalid, original);
    }
    let mut overflow = state;
    overflow
        .maintenance_binding
        .as_mut()
        .unwrap()
        .enabled_batches_per_job = u64::MAX;
    assert_eq!(
        advance_material_circuit(&overflow),
        Err(MaterialCircuitError::Arithmetic)
    );
}

#[test]
fn due_freight_supplies_jobs_before_local_outbound_credits() {
    let mut state = opening(0, 160);
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
    state.backlog.push(BacklogRow {
        order_id,
        quantity: 17,
    });
    state.supplier_routes.push(SupplierRoute {
        buyer_site_id: site(2),
        supplier_site_id: site(3),
        good_id: good(2),
        unit_id: unit(1),
        route_id,
        transport_kind: SupplierTransport::Staged,
    });
    state.route_stages.push(RouteStage {
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
    let first = advance_material_circuit(&state).unwrap();
    assert_eq!(first.maintenance.as_ref().unwrap().completed_jobs, 0);
    assert_eq!(first.dispatches[0].quantity, 17);
    let second = advance_material_circuit(&first.state).unwrap();
    let receipt = second.maintenance.as_ref().unwrap();
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
        produced(&advance_material_circuit(&second.state).unwrap()),
        960
    );
}

#[test]
fn resource_sharing_is_refused_instead_of_imposing_hidden_priority() {
    let state = opening(256, 160);
    let mut shared_process = state.clone();
    let other = ProcessId::from_bytes([9; 32]);
    shared_process.process_outputs.push(ProcessOutput {
        process_id: other,
        site_id: site(1),
        good_id: good(3),
        unit_id: unit(1),
        quantity_per_batch: 1,
    });
    shared_process.labor_coefficients.push(LaborCoefficient {
        process_id: other,
        unit_id: unit(2),
        quantity_per_batch: 1,
    });
    assert_eq!(
        advance_material_circuit(&shared_process),
        Err(MaterialCircuitError::MaintenanceInvariant)
    );
    for (supplier, material) in [(site(2), good(2)), (site(1), good(1))] {
        let mut shared_order = state.clone();
        if material == good(1) {
            shared_order
                .freight_mass_coefficients
                .push(FreightMassCoefficient {
                    good_id: material,
                    unit_id: unit(1),
                    grams_per_unit: 1000,
                });
        }
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
        shared_order.backlog.push(BacklogRow {
            order_id,
            quantity: 1,
        });
        assert_eq!(
            advance_material_circuit(&shared_order),
            Err(MaterialCircuitError::MaintenanceInvariant)
        );
    }
}

#[test]
fn failed_later_outbound_credit_publishes_no_maintenance_or_debits() {
    let mut state = opening(u64::MAX, 160);
    restock(&mut state);
    let original = state.clone();
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(state, original);
}

#[test]
fn unrepresentable_maintenance_demand_does_not_disappear_with_zero_resources() {
    let mut state = opening(0, 0);
    state
        .maintenance_service
        .as_mut()
        .unwrap()
        .available_batches = 0;
    state.production_commitments.clear();
    state.inventory[0].quantity = u64::MAX;
    state.input_coefficients[0].quantity_per_batch = 1;
    state.labor_coefficients[0].quantity_per_batch = 1;
    for row in &mut state.capacities {
        row.available_batches = u64::MAX;
    }
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::Arithmetic)
    );
}

#[test]
fn idle_consumer_and_provider_rehire_after_later_material_arrival() {
    let mut state = opening(256, 160);
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
    state
        .freight_mass_coefficients
        .push(FreightMassCoefficient {
            good_id: good(1),
            unit_id: unit(1),
            grams_per_unit: 1000,
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
    state.backlog.push(BacklogRow {
        order_id,
        quantity: 1280,
    });
    state.supplier_routes.push(SupplierRoute {
        buyer_site_id: site(1),
        supplier_site_id: site(3),
        good_id: good(1),
        unit_id: unit(1),
        route_id,
        transport_kind: SupplierTransport::Staged,
    });
    state.route_stages.push(RouteStage {
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
    let mut staff = people(1);
    let mut output = Vec::new();
    let mut jobs = Vec::new();
    let mut employment = Vec::new();
    for _ in 1..=7 {
        let (transition, next_staff) = staffed(&state, &staff);
        output.push(produced(&transition));
        jobs.push(transition.maintenance.as_ref().unwrap().completed_jobs);
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
    let mut state = opening(256, 160);
    state.maintenance_binding.as_mut().unwrap().labor_unit_id = unit(1);
    for row in &mut state.labor {
        if row.site_id == site(2) {
            row.unit_id = unit(1);
        }
    }
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::MaintenanceInvariant)
    );
}

#[test]
fn spare_parts_independently_limit_positive_whole_jobs() {
    let mut state = opening(7, 160);
    state
        .maintenance_binding
        .as_mut()
        .unwrap()
        .spare_units_per_job = 3;
    let result = advance_material_circuit(&state).unwrap();
    let receipt = result.maintenance.as_ref().unwrap();
    assert_eq!(receipt.requested_jobs, 16);
    assert_eq!(receipt.available_labor_hours, 160);
    assert_eq!(receipt.completed_jobs, 2);
    assert_eq!(receipt.consumed_spare_parts, 6);
    assert_eq!(receipt.consumed_labor_hours, 20);
    assert_eq!(stock(&result.state, site(2), good(2)), 1);
    assert_eq!(receipt.next_service.available_batches, 2);
    assert_eq!(result.state.production_commitments[0].planned_batches, 2);
}
