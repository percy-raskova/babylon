//! Costs must come from actual current native quantities, not account-wide profit.
use super::*;

fn price(result: &MaterialCircuitTransition, owner: u8) -> &PriceReceipt {
    result
        .prices
        .iter()
        .find(|r| r.site_id == site(owner))
        .unwrap()
}
fn responsive(state: &mut MaterialCircuitState, owner: u8, quote: i128, target: u64) {
    let row = recurring_mut(state)
        .offers
        .iter_mut()
        .find(|r| r.site_id == site(owner))
        .unwrap();
    row.unit_price = money(quote);
    row.pricing = PricePolicy::Responsive {
        minimum: money(1),
        maximum: money(20),
        step: money(1),
        target_stock: target,
    };
}
fn withdraw_orders(state: &mut MaterialCircuitState) {
    let rows = recurring_mut(state);
    rows.household_purchases[0].enabled = false;
    for row in &mut rows.replenishment {
        row.maximum_purchase = 0;
    }
}

#[test]
fn goods_cost_production_uses_inputs_and_actual_wages_without_adding_release_twice() {
    let mut state = opening();
    responsive(&mut state, 2, 2, 0);
    let result = advance_material_circuit(&state).unwrap();
    let row = price(&result, 2);
    assert_eq!(
        row.cost,
        GoodsPriceCostEvidence {
            basis: GoodsPriceCostBasis::Produced,
            quantity: 4,
            carrying_cost: money(12),
            handling_wages: money(0),
        }
    );
    assert_eq!(
        (row.reason, row.old_price, row.next_price),
        (PriceDecision::CostPressure, money(2), money(3))
    );
    assert_eq!(row.closing_stock, 0);
    let reserve = economy(&result.state)
        .book
        .snapshot()
        .purchases
        .into_iter()
        .find(|r| r.seller == AccountId::Site(site(2)))
        .unwrap();
    assert_eq!(reserve.unit_price, money(2));
    assert_eq!(price(&result, 1).reason, PriceDecision::Fixed);
    assert_eq!(price(&result, 1).cost.carrying_cost, money(4));
    assert_eq!(
        economy(&result.state)
            .book
            .total_cash_and_reserves()
            .unwrap(),
        money(24)
    );
    let restored =
        decode_material_circuit_state(&encode_material_circuit_state(&result.state).unwrap())
            .unwrap();
    assert_eq!(
        advance_material_circuit(&result.state).unwrap(),
        advance_material_circuit(&restored).unwrap()
    );
}

#[test]
fn goods_cost_merchant_uses_released_carrying_and_matching_actual_handling_wages() {
    let mut state = opening();
    responsive(&mut state, 3, 3, 0);
    let result = advance_material_circuit(&state).unwrap();
    let row = price(&result, 3);
    assert_eq!(
        row.cost,
        GoodsPriceCostEvidence {
            basis: GoodsPriceCostBasis::Released,
            quantity: 4,
            carrying_cost: money(12),
            handling_wages: money(4),
        }
    );
    assert_eq!(
        (row.reason, row.next_price),
        (PriceDecision::CostPressure, money(4))
    );
    let income = result
        .income
        .iter()
        .find(|r| r.account == AccountId::Site(site(3)))
        .unwrap();
    assert_eq!(income.statement.cost_of_goods_sold, money(12));
    assert_eq!(income.statement.handling_expense, money(4));
    assert_eq!(income.net_income, money(-4));
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("paid")
    };
    e.employment
        .iter_mut()
        .find(|r| r.site_id == site(3))
        .unwrap()
        .compensation = LaborCompensation::WorkingOwner;
    let owner_work = advance_material_circuit(&state).unwrap();
    assert_eq!(price(&owner_work, 3).cost.quantity, 4);
    assert_eq!(price(&owner_work, 3).cost.handling_wages, money(0));
    assert_eq!(price(&owner_work, 3).reason, PriceDecision::Hold);
}

#[test]
fn goods_cost_pressure_precedes_excess_stock_but_does_not_force_recovery() {
    let mut state = opening();
    withdraw_orders(&mut state);
    responsive(&mut state, 2, 2, 0);
    let result = advance_material_circuit(&state).unwrap();
    assert_eq!(price(&result, 2).closing_stock, 4);
    assert_eq!(price(&result, 2).reason, PriceDecision::CostPressure);
    assert_eq!(price(&result, 2).next_price, money(3));
    assert_eq!(
        economy(&result.state)
            .costs
            .snapshot()
            .stocks
            .iter()
            .find(|r| r.owner == AccountId::Site(site(2)) && r.good_id == good(2))
            .unwrap()
            .amount,
        money(12)
    );
    responsive(&mut state, 2, 4, 0);
    let result = advance_material_circuit(&state).unwrap();
    assert_eq!(price(&result, 2).reason, PriceDecision::ExcessStock);
    assert_eq!(price(&result, 2).next_price, money(3));
}

#[test]
fn goods_cost_no_current_activity_is_unavailable_instead_of_zero_cost_or_stale_evidence() {
    let first = advance_material_circuit(&opening()).unwrap();
    let mut state = first.state;
    withdraw_orders(&mut state);
    state.production_commitments.clear();
    for row in &mut recurring_mut(&mut state).production {
        row.planned_batches = 0;
    }
    for row in &mut recurring_mut(&mut state).attendance {
        row.planned_hours = 0;
    }
    responsive(&mut state, 3, 4, 4);
    let result = advance_material_circuit(&state).unwrap();
    for row in &result.prices {
        assert_eq!(
            row.cost,
            GoodsPriceCostEvidence {
                basis: GoodsPriceCostBasis::Unavailable,
                quantity: 0,
                carrying_cost: money(0),
                handling_wages: money(0),
            }
        );
    }
    assert_eq!(price(&result, 3).reason, PriceDecision::Hold);
}

#[test]
fn goods_cost_input_and_employee_wage_changes_reach_the_actual_output_basis() {
    let mut state = opening();
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("paid")
    };
    let mut accounts = e.book.snapshot().accounts;
    accounts
        .iter_mut()
        .find(|r| r.id == AccountId::Site(site(2)))
        .unwrap()
        .cash = money(100);
    e.book = MonetaryBook::open(accounts).unwrap();
    let mut stocks = e.costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| r.owner == AccountId::Site(site(2)))
        .unwrap()
        .amount = money(40);
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![]).unwrap();
    e.employment
        .iter_mut()
        .find(|r| r.site_id == site(2))
        .unwrap()
        .compensation = LaborCompensation::Wage(money(2));
    responsive(&mut state, 2, 3, 0);
    let result = advance_material_circuit(&state).unwrap();
    assert_eq!(price(&result, 2).cost.carrying_cost, money(56)); // Four raw units at10 plus eight actual hours at2.
    assert_eq!(price(&result, 2).cost.quantity, 4);
    assert_eq!(price(&result, 2).reason, PriceDecision::CostPressure);
    assert_eq!(price(&result, 2).next_price, money(4)); // Step, not forced break-even14.
}

#[test]
fn goods_cost_unserved_demand_keeps_precedence_over_an_observed_cost_shortfall() {
    let mut state = opening();
    responsive(&mut state, 3, 3, 0);
    state
        .corridor_capacities
        .iter_mut()
        .find(|r| r.corridor_id == corridor(3) && r.period == 1)
        .unwrap()
        .available_grams = 2;
    let result = advance_material_circuit(&state).unwrap();
    let row = price(&result, 3);
    // Half the funded requests expire; remaining inventory exceeds target0, so
    // the pre-existing demand/inventory guard makes real cost the operative reason.
    assert_eq!(row.unserved_quantity, 2);
    assert_eq!(row.reason, PriceDecision::CostPressure);
    responsive(&mut state, 3, 3, 2);
    let result = advance_material_circuit(&state).unwrap();
    let row = price(&result, 3);
    assert_eq!(row.reason, PriceDecision::UnservedDemand);
    assert_eq!(row.cost.carrying_cost, money(6));
    assert_eq!(row.cost.handling_wages, money(2));
    assert_eq!(row.cost.quantity, 2);
}

#[test]
fn goods_cost_exact_ceiling_and_unavailable_shape_refuse_invalid_or_overflowing_claims() {
    let evidence = GoodsPriceCostEvidence {
        basis: GoodsPriceCostBasis::Produced,
        quantity: 4,
        carrying_cost: money(13),
        handling_wages: money(0),
    };
    assert_eq!(evidence.unit_cost().unwrap(), Some(money(4)));
    let mut large = evidence;
    large.carrying_cost = money(i128::MAX);
    large.quantity = 1;
    assert_eq!(large.unit_cost().unwrap(), Some(money(i128::MAX)));
    large.quantity = u64::MAX;
    assert!(large.unit_cost().unwrap().unwrap() > money(0));
    large.basis = GoodsPriceCostBasis::Released;
    large.handling_wages = money(1);
    assert_eq!(large.unit_cost(), Err(MaterialCircuitError::Arithmetic));
    for basis in [
        GoodsPriceCostBasis::Unavailable,
        GoodsPriceCostBasis::Produced,
        GoodsPriceCostBasis::Released,
    ] {
        let invalid = GoodsPriceCostEvidence {
            basis,
            quantity: 0,
            carrying_cost: money(1),
            handling_wages: money(0),
        };
        assert!(invalid.unit_cost().is_err());
    }
    let mut invalid = GoodsPriceCostEvidence {
        basis: GoodsPriceCostBasis::Produced,
        quantity: 1,
        carrying_cost: money(0),
        handling_wages: money(1),
    };
    assert!(invalid.unit_cost().is_err());
    invalid.handling_wages = money(0);
    assert_eq!(invalid.unit_cost().unwrap(), Some(money(0))); // Observed free output differs from no activity.
    invalid.carrying_cost = money(-1);
    assert!(invalid.unit_cost().is_err());
}

#[test]
fn goods_cost_same_site_production_and_merchant_release_use_one_quantity_basis() {
    let mut state = opening();
    responsive(&mut state, 2, 2, 0);
    state.merchants.push(MerchantHandling {
        site_id: site(2),
        location: "county:26163".parse().unwrap(),
        role: MerchantRole::Wholesale,
        capacity_id: corridor(4),
        labor_unit_id: hours(),
    });
    state
        .handling_coefficients
        .push(MerchantHandlingCoefficient {
            site_id: site(2),
            good_id: good(2),
            unit_id: units(),
            hours_per_unit: 1,
        });
    state
        .corridor_capacities
        .extend((1..=9).map(|period| CorridorCapacity {
            corridor_id: corridor(4),
            period,
            available_grams: 4,
        }));
    state
        .labor
        .iter_mut()
        .find(|r| r.site_id == site(2) && r.period == 1)
        .unwrap()
        .available = 12;
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("paid")
    };
    e.member_labor
        .iter_mut()
        .find(|r| r.member_id == StaffingMemberId::from_bytes(site(2).as_bytes()) && r.period == 1)
        .unwrap()
        .available_hours = 12;
    e.recurring
        .as_mut()
        .unwrap()
        .attendance
        .iter_mut()
        .find(|r| r.site_id == site(2))
        .unwrap()
        .planned_hours = 12;
    let result = advance_material_circuit(&state).unwrap();
    assert_eq!(output(&result, 2), 4);
    assert_eq!(
        price(&result, 2).cost,
        GoodsPriceCostEvidence {
            basis: GoodsPriceCostBasis::Released,
            quantity: 4,
            carrying_cost: money(12),
            handling_wages: money(4),
        }
    );
    assert_eq!(price(&result, 2).cost.unit_cost().unwrap(), Some(money(4)));
    assert_eq!(price(&result, 2).next_price, money(3));
    let income = result
        .income
        .iter()
        .find(|r| r.account == AccountId::Site(site(2)))
        .unwrap();
    assert_eq!(income.statement.cost_of_goods_sold, money(0)); // Seller-owned transit is not yet a sale.
    assert_eq!(income.statement.handling_expense, money(4));
}
