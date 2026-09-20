use babylon_kernel::currency::Currency;
use babylon_material_circuit::*;

fn money(value: i128) -> Currency {
    Currency::from_micro_units(value)
}

fn source() -> SiteId {
    SiteId::from_bytes([1; 32])
}
fn store() -> SiteId {
    SiteId::from_bytes([2; 32])
}
fn household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([3; 32])
}
fn good() -> GoodId {
    GoodId::from_bytes([4; 32])
}
fn unit() -> UnitId {
    UnitId::from_bytes([5; 32])
}
fn hours() -> UnitId {
    UnitId::from_bytes([6; 32])
}

fn opening() -> MaterialCircuitState {
    let route = RouteId::from_bytes([7; 32]);
    let corridor = CorridorId::from_bytes([8; 32]);
    let handling = CorridorId::from_bytes([9; 32]);
    MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::Monetary(MonetaryCircuit {
            book: MonetaryBook::open(vec![
                CashAccount {
                    id: AccountId::Site(source()),
                    cash: money(0),
                },
                CashAccount {
                    id: AccountId::Site(store()),
                    cash: money(8),
                },
                CashAccount {
                    id: AccountId::Household(household()),
                    cash: money(16),
                },
            ])
            .unwrap(),
            employment: vec![EmploymentTerms {
                site_id: store(),
                unit_id: hours(),
                payee: household(),
                hourly_rate: money(1),
            }],
        }),
        site_logistics_nodes: vec![
            SiteLogisticsNode {
                site_id: source(),
                node_id: LogisticsNodeId::from_bytes([1; 32]),
            },
            SiteLogisticsNode {
                site_id: store(),
                node_id: LogisticsNodeId::from_bytes([2; 32]),
            },
        ],
        process_outputs: vec![],
        input_coefficients: vec![],
        labor_coefficients: vec![],
        freight_mass_coefficients: vec![FreightMassCoefficient {
            good_id: good(),
            unit_id: unit(),
            grams_per_unit: 1,
        }],
        supplier_routes: vec![SupplierRoute {
            buyer_site_id: store(),
            supplier_site_id: source(),
            good_id: good(),
            unit_id: unit(),
            route_id: route,
            transport_kind: SupplierTransport::Staged,
        }],
        route_stages: vec![RouteStage {
            route_id: route,
            stage_index: 0,
            from_node_id: LogisticsNodeId::from_bytes([1; 32]),
            to_node_id: LogisticsNodeId::from_bytes([2; 32]),
            travel_periods: 1,
            loss_ppm: 0,
        }],
        route_stage_capacities: vec![RouteStageCapacity {
            route_id: route,
            stage_index: 0,
            corridor_id: corridor,
        }],
        inventory: vec![
            InventoryRow {
                site_id: source(),
                good_id: good(),
                unit_id: unit(),
                quantity: 4,
            },
            InventoryRow {
                site_id: store(),
                good_id: good(),
                unit_id: unit(),
                quantity: 4,
            },
        ],
        orders: vec![],
        backlog: vec![],
        freight: vec![],
        corridor_capacities: vec![
            CorridorCapacity {
                corridor_id: corridor,
                period: 1,
                available_grams: 4,
            },
            CorridorCapacity {
                corridor_id: handling,
                period: 1,
                available_grams: 4,
            },
        ],
        capacities: vec![],
        labor: vec![LaborCapacityRow {
            site_id: store(),
            unit_id: hours(),
            period: 1,
            available: 4,
        }],
        production_commitments: vec![],
        merchants: vec![MerchantHandling {
            site_id: store(),
            county_geoid: *b"26163",
            role: MerchantRole::Retail,
            capacity_id: handling,
            labor_unit_id: hours(),
        }],
        handling_coefficients: vec![MerchantHandlingCoefficient {
            site_id: store(),
            good_id: good(),
            unit_id: unit(),
            hours_per_unit: 1,
        }],
        final_demand_principals: vec![FinalDemandPrincipal {
            id: household(),
            county_geoid: *b"26163",
        }],
        final_demand_orders: vec![],
        maintenance_binding: None,
        maintenance_service: None,
    }
}

fn delivery() -> OrderRow {
    OrderRow {
        order_id: OrderId::from_bytes([10; 32]),
        access_mode: OrderAccessMode::CommoditySale,
        buyer_site_id: store(),
        supplier_site_id: source(),
        good_id: good(),
        unit_id: unit(),
        ordered: 4,
        shipped: 0,
        lost: 0,
        delivered: 0,
        realized: 0,
    }
}

fn retail() -> FinalDemandOrder {
    FinalDemandOrder {
        order_id: OrderId::from_bytes([11; 32]),
        retailer_site_id: store(),
        demand_principal_id: household(),
        good_id: good(),
        unit_id: unit(),
        ordered: 2,
        fulfilled: 0,
    }
}

fn book(state: &MaterialCircuitState) -> &MonetaryBook {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        panic!("monetary control")
    };
    &economy.book
}

#[test]
fn dispatch_keeps_escrow_and_restart_settles_only_actual_arrival() {
    let (state, reservation) =
        admit_material_purchase(&opening(), MaterialPurchase::Delivery(delivery()), money(1))
            .unwrap();
    assert_eq!(reservation.debit.delta, money(-4));
    let closed = advance_material_circuit(&state).unwrap();
    assert_eq!(closed.dispatches[0].quantity, 4);
    assert_eq!(
        book(&closed.state).cash(AccountId::Site(source())).unwrap(),
        money(0)
    );
    assert_eq!(
        book(&closed.state)
            .purchase(OutboundOrderId::Delivery(delivery().order_id))
            .unwrap()
            .reserved_amount()
            .unwrap(),
        money(4)
    );
    assert_eq!(closed.labor_use[0].funded_hours, 4);
    assert_eq!(closed.labor_use[0].used_hours, 0);
    assert_eq!(closed.labor_use[0].paid_idle_hours, 4);
    let restored =
        decode_material_circuit_state(&encode_material_circuit_state(&closed.state).unwrap())
            .unwrap();
    let arrived = advance_material_circuit(&restored).unwrap();
    assert_eq!(arrived, advance_material_circuit(&closed.state).unwrap());
    assert_eq!(arrived.arrivals[0].quantity, 4);
    assert_eq!(
        book(&arrived.state)
            .cash(AccountId::Site(source()))
            .unwrap(),
        money(4)
    );
    assert_eq!(
        book(&arrived.state).total_cash_and_reserves().unwrap(),
        money(24)
    );
}

#[test]
fn actual_local_handoff_pays_seller_and_reports_paid_idle_separately() {
    let (state, _) = admit_material_purchase(
        &opening(),
        MaterialPurchase::LocalFinalDemand(retail()),
        money(4),
    )
    .unwrap();
    let closed = advance_material_circuit(&state).unwrap();
    assert_eq!(closed.local_fulfillments[0].quantity, 2);
    assert_eq!(closed.wage_accruals[0].obligated_hours, 4);
    assert_eq!(closed.wage_accruals[0].amount, money(4));
    assert_eq!(closed.labor_use[0].used_hours, 2);
    assert_eq!(closed.labor_use[0].paid_idle_hours, 2);
    assert_eq!(
        book(&closed.state).cash(AccountId::Site(store())).unwrap(),
        money(12)
    );
    assert_eq!(
        book(&closed.state)
            .cash(AccountId::Household(household()))
            .unwrap(),
        money(12)
    );
    assert_eq!(
        book(&closed.state).total_cash_and_reserves().unwrap(),
        money(24)
    );
}

#[test]
fn missing_or_wrong_beneficiary_escrow_refuses_the_whole_material_close() {
    let mut unfunded = opening();
    unfunded.orders.push(delivery());
    unfunded.backlog.push(BacklogRow {
        order_id: delivery().order_id,
        quantity: 4,
    });
    let unchanged = unfunded.clone();
    assert_eq!(
        advance_material_circuit(&unfunded),
        Err(MaterialCircuitError::PurchaseInvariant)
    );
    assert_eq!(unfunded, unchanged);
    let (mut wrong, _) =
        admit_material_purchase(&opening(), MaterialPurchase::Delivery(delivery()), money(1))
            .unwrap();
    let CircuitAccounting::Monetary(economy) = &mut wrong.accounting else {
        unreachable!()
    };
    let mut snapshot = economy.book.snapshot();
    snapshot.purchases[0].seller = AccountId::Household(household());
    economy.book = MonetaryBook::from_snapshot(snapshot).unwrap();
    assert_eq!(
        advance_material_circuit(&wrong),
        Err(MaterialCircuitError::PurchaseInvariant)
    );
}

#[test]
fn purchase_admission_cannot_spend_the_same_cash_twice_or_leave_an_order_behind() {
    let state = opening();
    let unchanged = state.clone();
    assert_eq!(
        admit_material_purchase(&state, MaterialPurchase::Delivery(delivery()), money(3)),
        Err(MaterialCircuitError::MonetaryInvariant)
    );
    assert_eq!(state, unchanged);
    let (funded, _) =
        admit_material_purchase(&state, MaterialPurchase::Delivery(delivery()), money(2)).unwrap();
    let closed = advance_material_circuit(&funded).unwrap();
    assert!(closed.wage_accruals.is_empty());
    assert_eq!(closed.labor_use[0].funded_hours, 0);
    assert_eq!(closed.labor_use[0].unfunded_hours, 4);
    assert_eq!(
        book(&closed.state)
            .cash(AccountId::Household(household()))
            .unwrap(),
        money(16)
    );
}

#[test]
fn freight_loss_refunds_buyer_and_never_becomes_seller_income() {
    let mut state = opening();
    state.route_stages[0].loss_ppm = 500_000;
    let (state, _) =
        admit_material_purchase(&state, MaterialPurchase::Delivery(delivery()), money(1)).unwrap();
    let dispatched = advance_material_circuit(&state).unwrap();
    let arrived = advance_material_circuit(&dispatched.state).unwrap();
    assert_eq!(arrived.losses[0].quantity, 2);
    assert_eq!(arrived.arrivals[0].quantity, 2);
    assert_eq!(
        book(&arrived.state)
            .cash(AccountId::Site(source()))
            .unwrap(),
        money(2)
    );
    assert_eq!(
        book(&arrived.state).cash(AccountId::Site(store())).unwrap(),
        money(2)
    );
    assert_eq!(
        book(&arrived.state).total_cash_and_reserves().unwrap(),
        money(24)
    );
}

#[test]
fn previously_earned_wages_survive_restart_and_payment_does_not_accrue_them_again() {
    let mut state = opening();
    state.period = 2;
    for row in &mut state.labor {
        row.period = 2;
    }
    for row in &mut state.corridor_capacities {
        row.period = 2;
    }
    let previous_shift = ShiftId::from_bytes([12; 32]);
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    economy
        .book
        .reserve_shift(
            FundedShift::new(
                previous_shift,
                AccountId::Site(store()),
                AccountId::Household(household()),
                1,
                3,
                money(1),
            )
            .unwrap(),
        )
        .unwrap();
    economy.book.accrue_shift(previous_shift).unwrap();
    assert_eq!(
        economy
            .book
            .shift(previous_shift)
            .unwrap()
            .outstanding_wages()
            .unwrap(),
        money(3)
    );
    let restored =
        decode_material_circuit_state(&encode_material_circuit_state(&state).unwrap()).unwrap();
    let closed = advance_material_circuit(&restored).unwrap();
    assert_eq!(closed.wage_accruals.len(), 1);
    assert_eq!(closed.wage_accruals[0].period, 2);
    assert_eq!(closed.wage_accruals[0].amount, money(4));
    assert_eq!(
        closed
            .money_transfers
            .iter()
            .filter(|row| row.purpose == MoneyTransferPurpose::WagePayment(previous_shift))
            .count(),
        1
    );
    assert_eq!(
        book(&closed.state)
            .cash(AccountId::Household(household()))
            .unwrap(),
        money(23)
    );
    assert!(book(&closed.state).snapshot().shifts.is_empty());
    assert_eq!(
        book(&closed.state).total_cash_and_reserves().unwrap(),
        money(24)
    );
}

#[test]
fn goods_and_a_funded_buyer_do_not_substitute_for_employer_working_cash() {
    let (state, _) =
        admit_material_purchase(&opening(), MaterialPurchase::Delivery(delivery()), money(2))
            .unwrap();
    let (state, _) = admit_material_purchase(
        &state,
        MaterialPurchase::LocalFinalDemand(retail()),
        money(4),
    )
    .unwrap();
    let closed = advance_material_circuit(&state).unwrap();
    assert!(closed.local_fulfillments.is_empty());
    assert_eq!(closed.state.final_demand_orders[0].fulfilled, 0);
    assert_eq!(closed.labor_use[0].unfunded_hours, 4);
    assert_eq!(
        closed
            .state
            .inventory
            .iter()
            .find(|row| row.site_id == store())
            .unwrap()
            .quantity,
        4
    );
    assert_eq!(
        book(&closed.state)
            .purchase(OutboundOrderId::LocalFinalDemand(retail().order_id))
            .unwrap()
            .reserved_amount()
            .unwrap(),
        money(8)
    );
    assert_eq!(
        book(&closed.state).total_cash_and_reserves().unwrap(),
        money(24)
    );
}

#[test]
fn a_failure_after_attendance_cannot_publish_wages_or_cash() {
    let mut state = opening();
    state.period = u64::MAX;
    for row in &mut state.labor {
        row.period = u64::MAX;
    }
    for row in &mut state.corridor_capacities {
        row.period = u64::MAX;
    }
    let before = state.clone();
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(state, before);
    assert_eq!(
        book(&state)
            .cash(AccountId::Household(household()))
            .unwrap(),
        money(16)
    );
}

#[test]
fn paid_delivery_cannot_reopen_as_an_unrealized_physical_quantity() {
    let (state, _) =
        admit_material_purchase(&opening(), MaterialPurchase::Delivery(delivery()), money(1))
            .unwrap();
    let dispatched = advance_material_circuit(&state).unwrap();
    let mut arrived = advance_material_circuit(&dispatched.state).unwrap().state;
    assert_eq!(arrived.orders[0].realized, 4);
    arrived.orders[0].realized = 0;
    assert_eq!(
        encode_material_circuit_state(&arrived),
        Err(MaterialCircuitError::PurchaseInvariant)
    );
}
