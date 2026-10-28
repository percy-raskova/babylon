//! Rolling capacity is physical service, not a lifetime endowment or cash balance.
use crate::inventory;
use crate::money;
use crate::output;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::CorridorCapacity;
use babylon_material_circuit::FutureCapacityReservation;
use babylon_material_circuit::InstalledProcessCapacity;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialCircuitTransition;
use babylon_material_circuit::MemberLaborCapacityRow;
use babylon_material_circuit::OrderAccessMode;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::OrderRow;
use babylon_material_circuit::RollingCapacitySupply;
use babylon_material_circuit::RollingProcessSupply;
use babylon_material_circuit::RouteStage;
use babylon_material_circuit::RouteStageCapacity;
use babylon_material_circuit::SharedCapacitySupply;
use babylon_material_circuit::SiteLogisticsNode;
use babylon_material_circuit::StaffingMemberId;
use babylon_material_circuit::StaffingPolicy;
use babylon_material_circuit::StaffingPoolBinding;
use babylon_material_circuit::StaffingPoolId;
use babylon_material_circuit::StaffingPoolState;
use babylon_material_circuit::StaffingState;
use babylon_material_circuit::StaffingWorkSource;
use babylon_material_circuit::SupplierRoute;
use babylon_material_circuit::SupplierTransport;
use babylon_material_circuit::MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES;
use babylon_material_circuit::MAX_MATERIAL_CIRCUIT_ROWS;

fn rolling(catalog: &mut MaterialCatalog, mut state: MaterialCircuitState) -> MaterialCircuitState {
    state.capacities.retain(|row| row.period == state.period);
    state
        .corridor_capacities
        .retain(|row| row.period == state.period);
    let mut definition = catalog.clone().into_definition();
    definition.capacity_policy = CapacitySupply::Rolling(Box::new(RollingCapacitySupply {
        processes: RollingProcessSupply::CapturedNameplate(
            state
                .capacities
                .iter()
                .map(|row| InstalledProcessCapacity {
                    process_id: row.process_id,
                    site_id: row.site_id,
                    batches_per_period: row.available_batches,
                })
                .collect(),
        ),
        shared: state
            .corridor_capacities
            .iter()
            .map(|row| SharedCapacitySupply {
                corridor_id: row.corridor_id,
                grams_per_period: row.available_grams,
            })
            .collect(),
    }));
    *catalog = MaterialCatalog::try_new(definition).expect("the fixture catalog stays valid");
    state
}

fn staffing() -> StaffingState {
    let pools = [(1, 1), (2, 2), (3, 1)]
        .into_iter()
        .map(|(owner, persons)| {
            let source = if owner == 3 {
                StaffingWorkSource::MerchantHandling(crate::site(owner))
            } else {
                StaffingWorkSource::Production(crate::process(owner))
            };
            let binding = StaffingPoolBinding::try_new(
                StaffingPoolId::from_bytes([owner; 32]),
                crate::site(owner),
                crate::hours(),
                persons,
                StaffingPolicy::one_period(4).expect("the one-period fixture advances"),
                vec![source],
            )
            .expect("the authored fixture satisfies the constructor invariants");
            StaffingPoolState::try_new(binding, persons, 0, persons * 4)
                .expect("the authored fixture satisfies the constructor invariants")
        })
        .collect();
    StaffingState::try_new(1, pools)
        .expect("the authored fixture satisfies the constructor invariants")
}

fn staffed_close(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    people: &StaffingState,
) -> (MaterialCircuitTransition, StaffingState) {
    let closed = babylon_material_circuit::close_material_period(catalog, state)
        .expect("the material period closes");
    let bindings = people
        .pools()
        .iter()
        .map(|pool| pool.binding().clone())
        .collect::<Vec<_>>();
    let requests = closed
        .staffing_requests(catalog, &bindings)
        .expect("the fixture staffing requests are present");
    let staffing = babylon_material_circuit::advance_staffing(people, &requests)
        .expect("the fixture staffing advances");
    let member_hours = staffing
        .next_labor()
        .iter()
        .map(|row| MemberLaborCapacityRow {
            member_id: StaffingMemberId::from_bytes(row.site_id.as_bytes()),
            period: row.period,
            available_hours: row.available,
        })
        .collect();
    let result = closed
        .finish_with_workforce(catalog, staffing.next_labor().to_vec(), member_hours)
        .expect("the fixture call `finish_with_workforce` succeeds for the authored inputs");
    (result, staffing.state().clone())
}

#[test]
fn staffed_recurring_eighty_periods_and_restart_preserve_goods_money_and_capacity() {
    let (mut catalog, opening) = crate::opening();
    let mut state = rolling(&mut catalog, opening);
    state.inventory[0].quantity = 400; // Finite material resource, not regenerated by capacity.
    state.labor.retain(|row| row.period == 1);
    let CircuitAccounting::Monetary(opening_economy) = &mut state.accounting else {
        panic!("paid control")
    };
    opening_economy.member_labor.retain(|row| row.period == 1);
    let mut people = staffing();
    let mut consumed = 0;
    let mut fork = None;
    for period in 1..=80 {
        if period == 52 {
            let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
                .expect("the canonical material state encodes");
            fork = Some((
                babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
                    .expect("the canonical material bytes decode"),
                people.clone(),
            ));
        }
        let (closed, next_people) = staffed_close(&catalog, &state, &people);
        if let Some((restart, restart_people)) = &mut fork {
            let (replayed, replayed_people) = staffed_close(&catalog, restart, restart_people);
            assert_eq!(closed, replayed, "restart period {period}");
            assert_eq!(next_people, replayed_people);
            *restart = replayed.state;
            *restart_people = replayed_people;
        }
        consumed += closed.household_consumption[0].consumed_quantity;
        assert_eq!(
            crate::economy(&closed.state)
                .book
                .total_cash_and_reserves()
                .expect("the fixture book totals without overflow"),
            money(24)
        );
        let physical = closed
            .state
            .inventory
            .iter()
            .map(|r| r.quantity)
            .sum::<u64>()
            + closed.state.freight.iter().map(|r| r.quantity).sum::<u64>()
            + crate::economy(&closed.state)
                .recurring
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .household_stocks[0]
                .quantity;
        assert_eq!(physical + consumed, 416);
        assert_eq!(closed.state.capacities.len(), 2);
        assert_eq!(closed.state.corridor_capacities.len(), 3);
        assert!(closed
            .state
            .capacities
            .iter()
            .all(|r| r.period == period + 1));
        assert!(closed
            .state
            .corridor_capacities
            .iter()
            .all(|r| r.period == period + 1));
        assert_eq!(closed.state.labor.len(), 3);
        if period > 52 {
            assert_eq!(closed.household_consumption[0].consumed_quantity, 4);
            assert_eq!(output(&closed, 1), 4);
            assert_eq!(output(&closed, 2), 4);
        }
        people = next_people;
        state = closed.state;
    }
}

#[test]
fn finite_controls_do_not_extrapolate_missing_capacity() {
    let (catalog, mut state) = crate::opening();
    state.capacities.retain(|row| row.period == 1);
    state.corridor_capacities.retain(|row| row.period == 1);
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(first.state.capacities.len(), 0);
    assert_eq!(first.state.corridor_capacities.len(), 0);
    assert_eq!(first.state.production_commitments.len(), 0);
    let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("the authored material state advances one period");
    assert_eq!(second.dispatches.len(), 0);
    assert_eq!(second.household_demand[0].fulfilled_quantity, 0);
}

fn add_order(state: &mut MaterialCircuitState, buyer: u8, quantity: u64) {
    let id = OrderId::from_bytes([buyer; 32]);
    state.orders.push(OrderRow {
        order_id: id,
        access_mode: OrderAccessMode::CommoditySale,
        supplier_site_id: crate::site(1),
        buyer_site_id: crate::site(buyer),
        good_id: crate::good(1),
        unit_id: crate::units(),
        ordered: quantity,
        shipped: 0,
        delivered: 0,
        realized: 0,
        lost: 0,
    });
}

fn freight_opening() -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = crate::opening();
    let mut catalog = catalog.into_definition();
    state.period = 50;
    state.accounting = CircuitAccounting::PhysicalControl;
    catalog.household_needs.clear();
    catalog.process_outputs.clear();
    catalog.input_coefficients.clear();
    catalog.labor_coefficients.clear();
    state.production_commitments.clear();
    state.capacities.clear();
    state.labor.clear();
    catalog.merchants.clear();
    catalog.handling_coefficients.clear();
    state.final_demand_principals.clear();
    state.inventory = vec![inventory(1, 1, 20)];
    catalog.site_logistics_nodes.push(SiteLogisticsNode {
        site_id: crate::site(4),
        node_id: crate::node(4),
    });
    catalog.supplier_routes = [2, 3, 4]
        .into_iter()
        .map(|buyer| SupplierRoute {
            supplier_site_id: crate::site(1),
            buyer_site_id: crate::site(buyer),
            good_id: crate::good(1),
            unit_id: crate::units(),
            route_id: crate::route(buyer),
            transport_kind: SupplierTransport::Staged,
        })
        .collect();
    catalog.route_stages = [
        (2, 0, 1, 5, 1, 1_000_000),
        (2, 1, 5, 6, 1, 0),
        (2, 2, 6, 2, 1, 0),
        (3, 0, 1, 3, 1, 0),
        (4, 0, 1, 5, 1, 0),
        (4, 1, 5, 4, 1, 0),
    ]
    .into_iter()
    .map(
        |(id, stage_index, from, to, travel_periods, loss_ppm)| RouteStage {
            route_id: crate::route(id),
            stage_index,
            from_node_id: crate::node(from),
            to_node_id: crate::node(to),
            travel_periods,
            loss_ppm,
        },
    )
    .collect();
    state.route_stage_capacities = [
        (2, 0, 1),
        (2, 1, 1),
        (2, 2, 2),
        (3, 0, 2),
        (4, 0, 3),
        (4, 1, 2),
    ]
    .into_iter()
    .map(|(r, stage_index, c)| RouteStageCapacity {
        route_id: crate::route(r),
        stage_index,
        corridor_id: crate::corridor(c),
    })
    .collect();
    state.corridor_capacities = [1, 2, 3]
        .into_iter()
        .map(|c| CorridorCapacity {
            corridor_id: crate::corridor(c),
            period: 50,
            available_grams: 10,
        })
        .collect();
    add_order(&mut state, 2, 7);
    let mut catalog = MaterialCatalog::try_new(catalog).expect("valid definitions");
    let state = rolling(&mut catalog, state);
    (catalog, state)
}

#[test]
fn future_departures_remain_reserved_after_total_loss_and_checkpoint_restart() {
    let (catalog, opening) = freight_opening();
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    assert_eq!(first.dispatches[0].quantity, 7);
    let mut state = first.state;
    add_order(&mut state, 4, 8);
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    let restarted = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
        .expect("the canonical material bytes decode");
    let second = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(
        second,
        babylon_material_circuit::advance_material_circuit(&catalog, &restarted)
            .expect("the authored material state advances one period")
    );
    assert_eq!(second.dispatches[0].quantity, 3);
    let mut state = second.state;
    assert_eq!(state.period, 52);
    assert_eq!(
        state
            .corridor_capacities
            .iter()
            .find(|r| r.corridor_id == crate::corridor(2))
            .expect("the fixture holds the searched element")
            .available_grams,
        0
    );
    add_order(&mut state, 3, 1);
    let third = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(second.losses.iter().map(|r| r.quantity).sum::<u64>(), 7);
    assert_eq!(third.losses.len(), 0);
    assert!(!third
        .state
        .freight
        .iter()
        .any(|r| r.order_id == OrderId::from_bytes([2; 32])));
    assert!(!third
        .dispatches
        .iter()
        .any(|r| r.order_id == OrderId::from_bytes([3; 32])));
    assert_eq!(
        third
            .state
            .inventory
            .iter()
            .map(|r| r.quantity)
            .sum::<u64>()
            + third.state.freight.iter().map(|r| r.quantity).sum::<u64>()
            + 7,
        20
    );
    // The second order's five still-unshipped units now book departure 53.
    assert_eq!(
        third
            .dispatches
            .iter()
            .find(|row| row.order_id == OrderId::from_bytes([4; 32]))
            .expect("the fixture holds the searched element")
            .quantity,
        5
    );
    assert_eq!(
        third
            .state
            .corridor_capacities
            .iter()
            .find(|r| r.corridor_id == crate::corridor(2))
            .expect("the fixture holds the searched element")
            .available_grams,
        5
    );
}

#[test]
fn rolling_wire_refuses_obsolete_noncanonical_and_invalid_bookings() {
    let (mut catalog, opening) = crate::opening();
    let state = rolling(&mut catalog, opening);
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
            .expect("the canonical material bytes decode"),
        state
    );
    let version = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    let mut obsolete = bytes.clone();
    obsolete[version..version + 2].copy_from_slice(&6_u16.to_be_bytes());
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &obsolete),
        Err(MaterialCircuitError::WireVersion)
    );
    for end in 0..bytes.len() {
        assert!(
            babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes[..end])
                .is_err()
        );
    }
    for (departure_period, c, reserved_grams) in [
        (49, 2, 1),
        (50, 2, 1),
        (53, 2, 1),
        (52, 3, 1),
        (52, 2, 0),
        (52, 2, 11),
    ] {
        let (catalog, mut invalid) = freight_opening();
        invalid
            .capacity_reservations
            .future
            .push(FutureCapacityReservation {
                departure_period,
                corridor_id: crate::corridor(c),
                reserved_grams,
            });
        assert_eq!(
            babylon_material_circuit::encode_material_circuit_state(&catalog, &invalid),
            Err(MaterialCircuitError::CapacityInvariant)
        );
    }
    // The authored policy is sealed once; an overbound policy is refused at admission.
    let (mut catalog, opening) = crate::opening();
    let state = rolling(&mut catalog, opening);
    let CapacitySupply::Rolling(rows) = &catalog.capacity_policy else {
        unreachable!()
    };
    let mut excessive = catalog.clone().into_definition();
    let CapacitySupply::Rolling(excessive_rows) = &mut excessive.capacity_policy else {
        unreachable!()
    };
    excessive_rows.shared = vec![rows.shared[0].clone(); MAX_MATERIAL_CIRCUIT_ROWS + 1];
    assert_eq!(
        MaterialCatalog::try_new(excessive),
        Err(MaterialCircuitError::RowLimit)
    );
    assert_eq!(state.period, 1);
}

#[test]
fn date_overflow_and_late_planning_failure_publish_no_capacity_or_money_changes() {
    let (catalog, mut state) = freight_opening();
    state.period = u64::MAX;
    for row in &mut state.corridor_capacities {
        row.period = state.period;
    }
    let before = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes"),
        before
    );

    let (mut catalog, opening) = crate::opening();
    let mut state = rolling(&mut catalog, opening);
    let mut catalog = catalog.into_definition();
    crate::recurring_mut(&mut state).production[0].output_buffer = u64::MAX;
    catalog.route_stages[0].to_node_id = crate::node(9);
    catalog.route_stages.push(RouteStage {
        route_id: crate::route(1),
        stage_index: 1,
        from_node_id: crate::node(9),
        to_node_id: crate::node(2),
        travel_periods: 1,
        loss_ppm: 0,
    });
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id: crate::route(1),
        stage_index: 1,
        corridor_id: crate::corridor(1),
    });
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let before = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    // Payroll, retail settlement and a newly reserved future departure precede
    // overflow of dispatched_quantity + output_buffer in production planning.
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes"),
        before
    );
}
