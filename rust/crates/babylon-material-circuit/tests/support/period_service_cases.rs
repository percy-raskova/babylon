use babylon_material_circuit::decode_material_circuit_state;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::AttendancePlan;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdCohort;
use babylon_material_circuit::HouseholdNeed;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::HouseholdPurchasePolicy;
use babylon_material_circuit::InventoryRow;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialPurchase;
use babylon_material_circuit::MemberLaborCapacityRow;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::OrderAccessMode;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::OrderRow;
use babylon_material_circuit::OutboundOrderId;
use babylon_material_circuit::PricePolicy;
use babylon_material_circuit::ProductionDemandPolicy;
use babylon_material_circuit::RecurringEconomy;
use babylon_material_circuit::RouteId;
use babylon_material_circuit::SellerOffer;
use babylon_material_circuit::ServiceConnection;
use babylon_material_circuit::ServiceInputPolicy;
use babylon_material_circuit::ServiceOrder;
use babylon_material_circuit::ServicePriceDecision;
use babylon_material_circuit::StaffingMemberId;
use babylon_material_circuit::StockCarryingValue;
use babylon_material_circuit::SupplierRoute;
use babylon_material_circuit::SupplierTransport;
use babylon_material_circuit::MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES;

// These finite fixtures explicitly supply one resident member per employer.
fn sync_member_hours(state: &mut MaterialCircuitState) {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("paid control")
    };
    economy.member_labor = state
        .labor
        .iter()
        .map(|row| MemberLaborCapacityRow {
            member_id: StaffingMemberId::from_bytes(row.site_id.as_bytes()),
            period: row.period,
            available_hours: row.available,
        })
        .collect();
}

#[test]
fn household_service_need_uses_the_selected_basis_at_admission_and_consumption() {
    for (basis, expected) in [
        (HouseholdNeedBasis::Persons, 4),
        (HouseholdNeedBasis::Households, 1),
    ] {
        let mut state = recurring(crate::opening());
        let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
            panic!("the control must pay for actual services");
        };
        let rows = economy.recurring.as_mut().unwrap();
        rows.households[0].persons = 4;
        rows.household_needs[0].basis = basis;
        rows.household_purchases[0].maximum_purchase = 4;
        let close = babylon_material_circuit::advance_material_circuit(&state).unwrap();
        let receipt = &close.household_services[0];
        assert_eq!(receipt.required_quantity, expected);
        assert_eq!(
            receipt.satisfied_quantity + receipt.unmet_quantity,
            expected
        );
        assert_eq!(receipt.satisfied_quantity, 1);
        let request = close
            .service_performance
            .iter()
            .find(|row| row.buyer == AccountId::Household(crate::household()))
            .unwrap();
        assert_eq!(request.requested_quantity, expected);
    }
}

#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
pub(super) fn recurring(mut state: MaterialCircuitState) -> MaterialCircuitState {
    state.inventory[0].quantity = 3;
    state.capacities[0].available_batches = 4;
    state.capacities[1].available_batches = 3;
    state.labor[0].available = 3;
    state.labor[1].available = 2;
    state.production_commitments[0].planned_batches = 3;
    state.production_commitments[1].planned_batches = 2;
    state.service_connections.push(ServiceConnection {
        provider_site_id: crate::site(2),
        buyer: AccountId::Household(crate::household()),
        good_id: crate::good(2),
        unit_id: crate::unit(2),
    });
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!()
    };
    e.recurring = Some(Box::new(RecurringEconomy {
        service_inputs: vec![
            ServiceInputPolicy {
                buyer_site_id: crate::site(2),
                provider_site_id: crate::site(1),
                good_id: crate::good(1),
                unit_id: crate::unit(1),
                quantity_per_period: 2,
                maximum_purchase: 2,
                cash_floor: crate::money(0),
            },
            ServiceInputPolicy {
                buyer_site_id: crate::site(3),
                provider_site_id: crate::site(1),
                good_id: crate::good(1),
                unit_id: crate::unit(1),
                quantity_per_period: 1,
                maximum_purchase: 1,
                cash_floor: crate::money(0),
            },
            ServiceInputPolicy {
                buyer_site_id: crate::site(3),
                provider_site_id: crate::site(2),
                good_id: crate::good(2),
                unit_id: crate::unit(2),
                quantity_per_period: 1,
                maximum_purchase: 1,
                cash_floor: crate::money(0),
            },
        ],
        households: vec![HouseholdCohort {
            kind: babylon_material_circuit::HouseholdKind::Ordinary,
            principal_id: crate::household(),
            households: 1,
            persons: 1,
        }],
        household_stocks: vec![],
        household_needs: vec![HouseholdNeed {
            principal_id: crate::household(),
            good_id: crate::good(2),
            unit_id: crate::unit(2),
            basis: babylon_material_circuit::HouseholdNeedBasis::Persons,
            units_per_basis: 1,
        }],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: crate::household(),
            retailer_site_id: crate::site(2),
            good_id: crate::good(2),
            unit_id: crate::unit(2),
            target_closing_stock: 0,
            maximum_purchase: 1,
            enabled: true,
        }],
        offers: (1..=3)
            .map(|n| SellerOffer {
                site_id: crate::site(n),
                good_id: crate::good(n),
                unit_id: crate::unit(n),
                unit_price: crate::money(if n == 1 { 2 } else { 4 }),
                pricing: if n == 3 {
                    PricePolicy::Fixed
                } else {
                    PricePolicy::ServiceResponsive {
                        minimum: crate::money(1),
                        maximum: crate::money(10),
                        step: crate::money(1),
                    }
                },
            })
            .collect(),
        replenishment: vec![],
        production: (1..=3)
            .map(|n| ProductionDemandPolicy {
                process_id: crate::process(n),
                site_id: crate::site(n),
                output_buffer: 0,
                planned_batches: if n == 1 {
                    3
                } else if n == 2 {
                    2
                } else {
                    1
                },
            })
            .collect(),
        attendance: (1..=3)
            .map(|n| AttendancePlan {
                site_id: crate::site(n),
                unit_id: crate::unit(9),
                period: 1,
                planned_hours: if n == 1 {
                    3
                } else if n == 2 {
                    2
                } else {
                    1
                },
            })
            .collect(),
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }));
    sync_member_hours(&mut state);
    state
}
#[test]
fn service_household_satisfaction_has_no_pantry_or_retailer_requirement() {
    let closed =
        babylon_material_circuit::advance_material_circuit(&recurring(crate::opening())).unwrap();
    assert!(closed.household_consumption.is_empty());
    assert!(closed.household_demand.is_empty());
    assert_eq!(closed.household_services.len(), 1);
    let h = &closed.household_services[0];
    assert_eq!(
        (
            h.required_quantity,
            h.satisfied_quantity,
            h.unmet_quantity,
            h.unused_quantity
        ),
        (1, 1, 0, 0)
    );
    let CircuitAccounting::Monetary(e) = &closed.state.accounting else {
        panic!()
    };
    assert!(e.recurring.as_ref().unwrap().household_stocks.is_empty());
    assert_eq!(
        closed
            .income
            .iter()
            .find(|r| r.account == AccountId::Household(crate::household()))
            .unwrap()
            .statement
            .consumption_expense,
        crate::money(4)
    );
}
#[test]
fn service_quotes_distinguish_funded_unmet_cost_pressure_and_spare_capacity() {
    let base = recurring(crate::opening());
    let spare = babylon_material_circuit::advance_material_circuit(&base).unwrap();
    let u = &spare.service_markets[0];
    assert_eq!(
        (
            u.admitted_quantity,
            u.performed_quantity,
            u.available_capacity
        ),
        (3, 3, 4)
    );
    assert_eq!(
        (u.old_price, u.next_price, u.reason),
        (
            crate::money(2),
            crate::money(1),
            ServicePriceDecision::SpareCapacity
        )
    );
    let mut scarce = base.clone();
    scarce.inventory[0].quantity = 2;
    let closed = babylon_material_circuit::advance_material_circuit(&scarce).unwrap();
    let u = &closed.service_markets[0];
    assert!(u.admitted_quantity > u.performed_quantity);
    assert_eq!(
        (u.next_price, u.reason),
        (crate::money(3), ServicePriceDecision::FundedUnmet)
    );
    let mut costly = base;
    let CircuitAccounting::Monetary(e) = &mut costly.accounting else {
        panic!()
    };
    e.employment[0].compensation = LaborCompensation::Wage(crate::money(3));
    let closed = babylon_material_circuit::advance_material_circuit(&costly).unwrap();
    let u = &closed.service_markets[0];
    assert_eq!(
        (u.direct_cost, u.next_price, u.reason),
        (
            crate::money(9),
            crate::money(3),
            ServicePriceDecision::CostPressure
        )
    );
}
#[test]
fn future_service_reserve_retains_accepted_quote_through_current_price_change_and_restart() {
    let state = recurring(crate::opening());
    let id = OrderId::from_bytes([99; 32]);
    let (state, _) = babylon_material_circuit::admit_material_purchase(
        &state,
        MaterialPurchase::Service(ServiceOrder {
            order_id: id,
            performance_period: 2,
            provider_site_id: crate::site(1),
            buyer: AccountId::Site(crate::site(3)),
            good_id: crate::good(1),
            unit_id: crate::unit(1),
            quantity: 1,
        }),
        crate::money(2),
    )
    .unwrap();
    let closed = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    let CircuitAccounting::Monetary(e) = &closed.state.accounting else {
        panic!()
    };
    assert_eq!(
        e.book
            .purchase(OutboundOrderId::Service(id))
            .unwrap()
            .unit_price,
        crate::money(2)
    );
    assert_eq!(
        e.recurring.as_ref().unwrap().offers[0].unit_price,
        crate::money(1)
    );
    assert_eq!(closed.state.service_orders.len(), 1);
    let bytes = babylon_material_circuit::encode_material_circuit_state(&closed.state).unwrap();
    assert_eq!(decode_material_circuit_state(&bytes).unwrap(), closed.state);
}
#[test]
fn purchased_unused_service_is_expensed_and_unsold_provider_capacity_does_not_work() {
    let mut state = crate::opening();
    state.inventory[0].quantity = 2;
    state
        .production_commitments
        .retain(|r| r.process_id != crate::process(3));
    let closed = babylon_material_circuit::advance_material_circuit(&crate::funded(state)).unwrap();
    let f = closed
        .income
        .iter()
        .find(|r| r.account == AccountId::Site(crate::site(3)))
        .unwrap();
    assert_eq!(f.statement.unused_service_expense, crate::money(5));
    assert_eq!(f.statement.idle_labor_expense, crate::money(1));
    assert!(closed
        .service_performance
        .iter()
        .filter(|r| r.buyer == AccountId::Site(crate::site(3)))
        .all(|r| r.used_quantity == 0 && r.unused_quantity == 1));
    let closed = babylon_material_circuit::advance_material_circuit(&crate::opening()).unwrap();
    assert!(closed.production.iter().all(|r| r.produced_batches == 0));
    assert!(closed.labor_use.iter().all(|r| r.used_hours == 0));
    assert!(closed
        .income
        .iter()
        .all(|r| r.statement.productive_labor_capitalized == crate::money(0)));
}
#[test]
fn service_wire_refuses_old_version_and_late_planning_overflow_is_atomic() {
    let mut state = recurring(crate::opening());
    let before = babylon_material_circuit::encode_material_circuit_state(&state).unwrap();
    let mut old = before.clone();
    let version = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    old[version..version + 2].copy_from_slice(&8_u16.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&old),
        Err(MaterialCircuitError::WireVersion)
    );
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!()
    };
    e.recurring.as_mut().unwrap().production[2].output_buffer = u64::MAX;
    state.supplier_routes.push(SupplierRoute {
        buyer_site_id: crate::site(1),
        supplier_site_id: crate::site(3),
        good_id: crate::good(3),
        unit_id: crate::unit(3),
        route_id: RouteId::from_bytes([99; 32]),
        transport_kind: SupplierTransport::Local,
    });
    state = babylon_material_circuit::admit_material_purchase(
        &state,
        MaterialPurchase::Delivery(OrderRow {
            order_id: OrderId::from_bytes([88; 32]),
            access_mode: OrderAccessMode::CommoditySale,
            buyer_site_id: crate::site(1),
            supplier_site_id: crate::site(3),
            good_id: crate::good(3),
            unit_id: crate::unit(3),
            ordered: 1,
            shipped: 0,
            lost: 0,
            delivered: 0,
            realized: 0,
        }),
        crate::money(1),
    )
    .unwrap()
    .0;
    // The goods planner overflows only after service work and settlement have run detached.
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

#[test]
fn current_production_withdrawal_removes_b2b_service_requests() {
    let mut state = recurring(crate::opening());
    state
        .production_commitments
        .retain(|r| r.process_id != crate::process(3));
    let closed = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    let firm_requests: Vec<_> = closed
        .service_performance
        .iter()
        .filter(|r| r.buyer == AccountId::Site(crate::site(3)))
        .collect();
    assert_eq!(firm_requests.len(), 2);
    assert!(firm_requests.iter().all(|r| r.requested_quantity == 0
        && r.admitted_quantity == 0
        && r.performed_quantity == 0));
}
#[test]
fn utility_and_goods_stages_share_the_same_site_labor_residual() {
    let mut state = crate::opening();
    state.process_outputs[2].site_id = crate::site(1);
    state.capacities[2].site_id = crate::site(1);
    state.production_commitments[2].site_id = crate::site(1);
    state
        .input_coefficients
        .retain(|r| !(r.process_id == crate::process(3) && r.good_id == crate::good(1)));
    state.labor.retain(|r| r.site_id != crate::site(3));
    state.labor[0].available = 1;
    state.inventory[1].site_id = crate::site(1);
    state.service_connections = vec![
        ServiceConnection {
            provider_site_id: crate::site(1),
            buyer: AccountId::Site(crate::site(2)),
            good_id: crate::good(1),
            unit_id: crate::unit(1),
        },
        ServiceConnection {
            provider_site_id: crate::site(2),
            buyer: AccountId::Site(crate::site(1)),
            good_id: crate::good(2),
            unit_id: crate::unit(2),
        },
    ];
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!()
    };
    e.employment.retain(|r| r.site_id != crate::site(3));
    let mut captured = e.costs.snapshot();
    captured
        .stocks
        .iter_mut()
        .find(|r| r.good_id == crate::good(3))
        .unwrap()
        .owner = AccountId::Site(crate::site(1));
    e.costs = HistoricalCostBook::from_snapshot(captured).unwrap();
    sync_member_hours(&mut state);
    for (id, provider, buyer, commodity, price) in [(11, 1, 2, 1, 1), (12, 2, 1, 2, 2)] {
        state = babylon_material_circuit::admit_material_purchase(
            &state,
            MaterialPurchase::Service(ServiceOrder {
                order_id: OrderId::from_bytes([id; 32]),
                performance_period: 1,
                provider_site_id: crate::site(provider),
                buyer: AccountId::Site(crate::site(buyer)),
                good_id: crate::good(commodity),
                unit_id: crate::unit(commodity),
                quantity: 1,
            }),
            crate::money(price),
        )
        .unwrap()
        .0;
    }
    let closed = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    assert_eq!(
        closed
            .production
            .iter()
            .find(|r| r.process_id == crate::process(1))
            .unwrap()
            .produced_batches,
        1
    );
    assert_eq!(
        closed
            .production
            .iter()
            .find(|r| r.process_id == crate::process(3))
            .unwrap()
            .produced_batches,
        0
    );
    assert_eq!(
        closed
            .labor_use
            .iter()
            .find(|r| r.site_id == crate::site(1))
            .unwrap()
            .used_hours,
        1
    );
    state.labor[0].available = 2;
    sync_member_hours(&mut state);
    let closed = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    assert_eq!(
        closed
            .production
            .iter()
            .find(|r| r.process_id == crate::process(3))
            .unwrap()
            .produced_batches,
        1
    );
}

fn batch_opening(mut state: MaterialCircuitState) -> MaterialCircuitState {
    state.inventory[0].quantity = 1;
    state.process_outputs[0].quantity_per_batch = 4;
    state.labor[0].available = 1;
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!()
    };
    let mut stocks = e.costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| r.good_id == crate::good(4))
        .unwrap()
        .amount = crate::money(9);
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![]).unwrap();
    if let Some(r) = &mut e.recurring {
        r.household_purchases[0].enabled = false;
        r.attendance[0].planned_hours = 1;
        r.attendance[1].planned_hours = 1;
        state.labor[1].available = 1;
        state.production_commitments[1].planned_batches = 1;
    }
    sync_member_hours(&mut state);
    state
}
#[test]
fn service_batches_expire_unallocated_output_at_exact_remaining_cost() {
    let closed = babylon_material_circuit::advance_material_circuit(&crate::funded(batch_opening(
        crate::opening(),
    )))
    .unwrap();
    assert_eq!(closed.production[0].produced_batches, 1);
    let output = &closed.service_outputs[0];
    assert_eq!(
        (
            output.produced_quantity,
            output.allocated_quantity,
            output.expired_quantity,
            output.direct_cost,
            output.expired_cost
        ),
        (4, 2, 2, crate::money(10), crate::money(6))
    );
    let u = closed
        .income
        .iter()
        .find(|r| r.account == AccountId::Site(crate::site(1)))
        .unwrap();
    assert_eq!(
        (
            u.statement.sales,
            u.statement.cost_of_goods_sold,
            u.statement.unused_service_expense,
            u.net_income
        ),
        (
            crate::money(4),
            crate::money(4),
            crate::money(6),
            crate::money(-6)
        )
    );
    assert!(closed
        .state
        .inventory
        .iter()
        .all(|r| r.good_id != crate::good(1) && r.good_id != crate::good(2)));
    assert!(closed.state.freight.is_empty());
    let bytes = babylon_material_circuit::encode_material_circuit_state(&closed.state).unwrap();
    assert_eq!(decode_material_circuit_state(&bytes).unwrap(), closed.state);
}
#[test]
fn service_quote_cost_evidence_includes_unallocated_batch_output() {
    let closed = babylon_material_circuit::advance_material_circuit(&batch_opening(recurring(
        crate::opening(),
    )))
    .unwrap();
    let u = &closed.service_markets[0];
    assert_eq!(
        (u.performed_quantity, u.direct_cost, u.next_price, u.reason),
        (
            2,
            crate::money(10),
            crate::money(3),
            ServicePriceDecision::CostPressure
        )
    );
}

#[test]
fn same_stage_peer_acquisition_cannot_mix_into_unsold_provider_cost() {
    let mut state = batch_opening(crate::opening());
    state.process_outputs[1].good_id = crate::good(1);
    state.process_outputs[1].unit_id = crate::unit(1);
    state.process_outputs[1].quantity_per_batch = 4;
    state.input_coefficients[1].good_id = crate::good(4);
    state.input_coefficients[1].unit_id = crate::unit(4);
    state
        .production_commitments
        .retain(|r| r.process_id != crate::process(3));
    state.labor[2].available = 0;
    sync_member_hours(&mut state);
    state.inventory.push(InventoryRow {
        site_id: crate::site(2),
        good_id: crate::good(4),
        unit_id: crate::unit(4),
        quantity: 1,
    });
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!()
    };
    let mut stocks = e.costs.snapshot().stocks;
    stocks.push(StockCarryingValue {
        owner: AccountId::Site(crate::site(2)),
        good_id: crate::good(4),
        unit_id: crate::unit(4),
        amount: crate::money(19),
    });
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![]).unwrap();
    state.service_connections = (1..=2)
        .map(|provider| ServiceConnection {
            provider_site_id: crate::site(provider),
            buyer: AccountId::Site(crate::site(3 - provider)),
            good_id: crate::good(1),
            unit_id: crate::unit(1),
        })
        .collect();
    for (provider, price) in [(1, 2), (2, 3)] {
        state = babylon_material_circuit::admit_material_purchase(
            &state,
            MaterialPurchase::Service(ServiceOrder {
                order_id: OrderId::from_bytes([provider; 32]),
                performance_period: 1,
                provider_site_id: crate::site(provider),
                buyer: AccountId::Site(crate::site(3 - provider)),
                good_id: crate::good(1),
                unit_id: crate::unit(1),
                quantity: 1,
            }),
            crate::money(price),
        )
        .unwrap()
        .0;
    }
    let closed = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    assert_eq!(
        closed
            .service_outputs
            .iter()
            .map(|r| (r.direct_cost, r.expired_cost))
            .collect::<Vec<_>>(),
        [
            (crate::money(10), crate::money(8)),
            (crate::money(20), crate::money(15))
        ]
    );
    for (owner, expense, income) in [(1, 11, -11), (2, 17, -19)] {
        let r = closed
            .income
            .iter()
            .find(|r| r.account == AccountId::Site(crate::site(owner)))
            .unwrap();
        assert_eq!(
            (r.statement.unused_service_expense, r.net_income),
            (crate::money(expense), crate::money(income))
        );
    }
}

#[test]
fn prebooked_services_cover_recurring_need_before_any_new_purchase() {
    for (buyer, prebooked_id) in [
        (3, OrderId::from_bytes([99; 32])),
        (
            3,
            babylon_material_circuit::recurring_service_order_id(
                1,
                AccountId::Site(crate::site(3)),
                crate::site(1),
                crate::good(1),
                crate::unit(1),
            ),
        ),
        (
            2,
            babylon_material_circuit::recurring_service_order_id(
                1,
                AccountId::Site(crate::site(2)),
                crate::site(1),
                crate::good(1),
                crate::unit(1),
            ),
        ),
    ] {
        let (state, _) = babylon_material_circuit::admit_material_purchase(
            &recurring(crate::opening()),
            MaterialPurchase::Service(ServiceOrder {
                order_id: prebooked_id,
                performance_period: 1,
                provider_site_id: crate::site(1),
                buyer: AccountId::Site(crate::site(buyer)),
                good_id: crate::good(1),
                unit_id: crate::unit(1),
                quantity: 1,
            }),
            crate::money(1),
        )
        .unwrap();
        let closed = babylon_material_circuit::advance_material_circuit(&state).unwrap();
        let rows: Vec<_> = closed
            .service_performance
            .iter()
            .filter(|r| {
                r.buyer == AccountId::Site(crate::site(buyer)) && r.good_id == crate::good(1)
            })
            .collect();
        assert_eq!(
            rows.iter().map(|r| r.admitted_quantity).sum::<u64>(),
            if buyer == 2 { 2 } else { 1 }
        );
        let old = rows.iter().find(|r| r.order_id == prebooked_id).unwrap();
        assert_eq!(
            (old.admitted_quantity, old.unit_price),
            (1, crate::money(1))
        );
        if buyer == 2 {
            let topup = rows.iter().find(|r| r.order_id != prebooked_id).unwrap();
            assert_eq!(
                (topup.admitted_quantity, topup.unit_price),
                (1, crate::money(2))
            );
        }
    }
}

#[test]
fn prebooked_household_service_retains_its_price_and_is_not_purchased_twice() {
    let mut state = recurring(crate::opening());
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!()
    };
    let mut accounts = e.book.snapshot().accounts;
    accounts
        .iter_mut()
        .find(|r| r.id == AccountId::Site(crate::site(3)))
        .unwrap()
        .cash = crate::money(8);
    accounts
        .iter_mut()
        .find(|r| r.id == AccountId::Household(crate::household()))
        .unwrap()
        .cash = crate::money(2);
    e.book = MonetaryBook::open(accounts).unwrap();
    e.costs = HistoricalCostBook::open(&e.book, e.costs.snapshot().stocks, vec![], vec![], vec![])
        .unwrap();
    let id = babylon_material_circuit::recurring_service_order_id(
        1,
        AccountId::Household(crate::household()),
        crate::site(2),
        crate::good(2),
        crate::unit(2),
    );
    let (state, _) = babylon_material_circuit::admit_material_purchase(
        &state,
        MaterialPurchase::Service(ServiceOrder {
            order_id: id,
            performance_period: 1,
            provider_site_id: crate::site(2),
            buyer: AccountId::Household(crate::household()),
            good_id: crate::good(2),
            unit_id: crate::unit(2),
            quantity: 1,
        }),
        crate::money(1),
    )
    .unwrap();
    let closed = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    let rows: Vec<_> = closed
        .service_performance
        .iter()
        .filter(|r| r.buyer == AccountId::Household(crate::household()))
        .collect();
    assert_eq!(rows.iter().map(|r| r.admitted_quantity).sum::<u64>(), 1);
    assert_eq!(
        rows.iter().find(|r| r.order_id == id).unwrap().unit_price,
        crate::money(1)
    );
    assert_eq!(closed.household_services[0].satisfied_quantity, 1);
    assert_eq!(
        closed
            .income
            .iter()
            .find(|r| r.account == AccountId::Household(crate::household()))
            .unwrap()
            .statement
            .consumption_expense,
        crate::money(1)
    );
}
