//! Costs must come from actual current native quantities, not account-wide profit.
use crate::output;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::CorridorCapacity;
use babylon_material_circuit::GoodsPriceCostBasis;
use babylon_material_circuit::GoodsPriceCostEvidence;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialCircuitTransition;
use babylon_material_circuit::MerchantHandling;
use babylon_material_circuit::MerchantHandlingCoefficient;
use babylon_material_circuit::MerchantRole;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::PriceDecision;
use babylon_material_circuit::PricePolicy;
use babylon_material_circuit::PriceReceipt;
use babylon_material_circuit::StaffingMemberId;

fn price(result: &MaterialCircuitTransition, owner: u8) -> &PriceReceipt {
    result
        .prices
        .iter()
        .find(|r| r.site_id == crate::site(owner))
        .expect("the fixture holds the searched element")
}
fn responsive(state: &mut MaterialCircuitState, owner: u8, quote: i128, target: u64) {
    let row = crate::recurring_mut(state)
        .offers
        .iter_mut()
        .find(|r| r.site_id == crate::site(owner))
        .expect("the fixture holds the searched element");
    row.unit_price = crate::money(quote);
    row.pricing = PricePolicy::Responsive {
        minimum: crate::money(1),
        maximum: crate::money(20),
        step: crate::money(1),
        target_stock: target,
    };
}
fn withdraw_orders(state: &mut MaterialCircuitState) {
    let rows = crate::recurring_mut(state);
    rows.household_purchases[0].enabled = false;
    for row in &mut rows.replenishment {
        row.maximum_purchase = 0;
    }
}

#[test]
fn goods_cost_production_uses_inputs_and_actual_wages_without_adding_release_twice() {
    let mut state = crate::opening();
    responsive(&mut state, 2, 2, 0);
    let result = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    let row = price(&result, 2);
    assert_eq!(
        row.cost,
        GoodsPriceCostEvidence {
            basis: GoodsPriceCostBasis::Produced,
            quantity: 4,
            carrying_cost: crate::money(12),
            handling_wages: crate::money(0),
        }
    );
    assert_eq!(
        (row.reason, row.old_price, row.next_price),
        (
            PriceDecision::CostPressure,
            crate::money(2),
            crate::money(3)
        )
    );
    assert_eq!(row.closing_stock, 0);
    let reserve = crate::economy(&result.state)
        .book
        .snapshot()
        .purchases
        .into_iter()
        .find(|r| r.seller == AccountId::Site(crate::site(2)))
        .expect("the fixture holds the searched element");
    assert_eq!(reserve.unit_price, crate::money(2));
    assert_eq!(price(&result, 1).reason, PriceDecision::Fixed);
    assert_eq!(price(&result, 1).cost.carrying_cost, crate::money(4));
    assert_eq!(
        crate::economy(&result.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(24)
    );
    let restored = babylon_material_circuit::decode_material_circuit_state(
        &babylon_material_circuit::encode_material_circuit_state(&result.state)
            .expect("the canonical material state encodes"),
    )
    .expect("the canonical material bytes decode");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&result.state)
            .expect("the authored material state advances one period"),
        babylon_material_circuit::advance_material_circuit(&restored)
            .expect("the authored material state advances one period")
    );
}

#[test]
fn goods_cost_merchant_uses_released_carrying_and_matching_actual_handling_wages() {
    let mut state = crate::opening();
    responsive(&mut state, 3, 3, 0);
    let result = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    let row = price(&result, 3);
    assert_eq!(
        row.cost,
        GoodsPriceCostEvidence {
            basis: GoodsPriceCostBasis::Released,
            quantity: 4,
            carrying_cost: crate::money(12),
            handling_wages: crate::money(4),
        }
    );
    assert_eq!(
        (row.reason, row.next_price),
        (PriceDecision::CostPressure, crate::money(4))
    );
    let income = result
        .income
        .iter()
        .find(|r| r.account == AccountId::Site(crate::site(3)))
        .expect("the fixture holds the searched element");
    assert_eq!(income.statement.cost_of_goods_sold, crate::money(12));
    assert_eq!(income.statement.handling_expense, crate::money(4));
    assert_eq!(income.net_income, crate::money(-4));
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("paid")
    };
    e.employment
        .iter_mut()
        .find(|r| r.site_id == crate::site(3))
        .expect("the fixture holds the searched element")
        .compensation = LaborCompensation::WorkingOwner;
    let owner_work = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    assert_eq!(price(&owner_work, 3).cost.quantity, 4);
    assert_eq!(price(&owner_work, 3).cost.handling_wages, crate::money(0));
    assert_eq!(price(&owner_work, 3).reason, PriceDecision::Hold);
}

#[test]
fn goods_cost_pressure_precedes_excess_stock_but_does_not_force_recovery() {
    let mut state = crate::opening();
    withdraw_orders(&mut state);
    responsive(&mut state, 2, 2, 0);
    let result = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    assert_eq!(price(&result, 2).closing_stock, 4);
    assert_eq!(price(&result, 2).reason, PriceDecision::CostPressure);
    assert_eq!(price(&result, 2).next_price, crate::money(3));
    assert_eq!(
        crate::economy(&result.state)
            .costs
            .snapshot()
            .stocks
            .iter()
            .find(|r| r.owner == AccountId::Site(crate::site(2)) && r.good_id == crate::good(2))
            .expect("the fixture holds the searched element")
            .amount,
        crate::money(12)
    );
    responsive(&mut state, 2, 4, 0);
    let result = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    assert_eq!(price(&result, 2).reason, PriceDecision::ExcessStock);
    assert_eq!(price(&result, 2).next_price, crate::money(3));
}

#[test]
fn goods_cost_no_current_activity_is_unavailable_instead_of_zero_cost_or_stale_evidence() {
    let first = babylon_material_circuit::advance_material_circuit(&crate::opening())
        .expect("the authored material state advances one period");
    let mut state = first.state;
    withdraw_orders(&mut state);
    state.production_commitments.clear();
    for row in &mut crate::recurring_mut(&mut state).production {
        row.planned_batches = 0;
    }
    for row in &mut crate::recurring_mut(&mut state).attendance {
        row.planned_hours = 0;
    }
    responsive(&mut state, 3, 4, 4);
    let result = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    for row in &result.prices {
        assert_eq!(
            row.cost,
            GoodsPriceCostEvidence {
                basis: GoodsPriceCostBasis::Unavailable,
                quantity: 0,
                carrying_cost: crate::money(0),
                handling_wages: crate::money(0),
            }
        );
    }
    assert_eq!(price(&result, 3).reason, PriceDecision::Hold);
}

#[test]
fn goods_cost_input_and_employee_wage_changes_reach_the_actual_output_basis() {
    let mut state = crate::opening();
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("paid")
    };
    let mut accounts = e.book.snapshot().accounts;
    accounts
        .iter_mut()
        .find(|r| r.id == AccountId::Site(crate::site(2)))
        .expect("the fixture holds the searched element")
        .cash = crate::money(100);
    e.book = MonetaryBook::open(accounts).expect("the fixture opens the authored source");
    let mut stocks = e.costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| r.owner == AccountId::Site(crate::site(2)))
        .expect("the fixture holds the searched element")
        .amount = crate::money(40);
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
    e.employment
        .iter_mut()
        .find(|r| r.site_id == crate::site(2))
        .expect("the fixture holds the searched element")
        .compensation = LaborCompensation::Wage(crate::money(2));
    responsive(&mut state, 2, 3, 0);
    let result = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    assert_eq!(price(&result, 2).cost.carrying_cost, crate::money(56)); // Four raw units at10 plus eight actual hours at2.
    assert_eq!(price(&result, 2).cost.quantity, 4);
    assert_eq!(price(&result, 2).reason, PriceDecision::CostPressure);
    assert_eq!(price(&result, 2).next_price, crate::money(4)); // Step, not forced break-even14.
}

#[test]
fn goods_cost_unserved_demand_keeps_precedence_over_an_observed_cost_shortfall() {
    let mut state = crate::opening();
    responsive(&mut state, 3, 3, 0);
    state
        .corridor_capacities
        .iter_mut()
        .find(|r| r.corridor_id == crate::corridor(3) && r.period == 1)
        .expect("the fixture holds the searched element")
        .available_grams = 2;
    let result = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    let row = price(&result, 3);
    // Half the funded requests expire; remaining inventory exceeds target0, so
    // the pre-existing demand/inventory guard makes real cost the operative reason.
    assert_eq!(row.unserved_quantity, 2);
    assert_eq!(row.reason, PriceDecision::CostPressure);
    responsive(&mut state, 3, 3, 2);
    let result = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    let row = price(&result, 3);
    assert_eq!(row.reason, PriceDecision::UnservedDemand);
    assert_eq!(row.cost.carrying_cost, crate::money(6));
    assert_eq!(row.cost.handling_wages, crate::money(2));
    assert_eq!(row.cost.quantity, 2);
}

#[test]
fn goods_cost_exact_ceiling_and_unavailable_shape_refuse_invalid_or_overflowing_claims() {
    let evidence = GoodsPriceCostEvidence {
        basis: GoodsPriceCostBasis::Produced,
        quantity: 4,
        carrying_cost: crate::money(13),
        handling_wages: crate::money(0),
    };
    assert_eq!(
        evidence
            .unit_cost()
            .expect("the fixture account carries its authored unit cost"),
        Some(crate::money(4))
    );
    let mut large = evidence;
    large.carrying_cost = crate::money(i128::MAX);
    large.quantity = 1;
    assert_eq!(
        large
            .unit_cost()
            .expect("the fixture account carries its authored unit cost"),
        Some(crate::money(i128::MAX))
    );
    large.quantity = u64::MAX;
    assert!(
        large
            .unit_cost()
            .expect("the fixture account carries its authored unit cost")
            .expect("the nested fixture result is present")
            > crate::money(0)
    );
    large.basis = GoodsPriceCostBasis::Released;
    large.handling_wages = crate::money(1);
    assert_eq!(large.unit_cost(), Err(MaterialCircuitError::Arithmetic));
    for basis in [
        GoodsPriceCostBasis::Unavailable,
        GoodsPriceCostBasis::Produced,
        GoodsPriceCostBasis::Released,
    ] {
        let invalid = GoodsPriceCostEvidence {
            basis,
            quantity: 0,
            carrying_cost: crate::money(1),
            handling_wages: crate::money(0),
        };
        assert!(invalid.unit_cost().is_err());
    }
    let mut invalid = GoodsPriceCostEvidence {
        basis: GoodsPriceCostBasis::Produced,
        quantity: 1,
        carrying_cost: crate::money(0),
        handling_wages: crate::money(1),
    };
    assert!(invalid.unit_cost().is_err());
    invalid.handling_wages = crate::money(0);
    assert_eq!(
        invalid
            .unit_cost()
            .expect("the fixture account carries its authored unit cost"),
        Some(crate::money(0))
    ); // Observed free output differs from no activity.
    invalid.carrying_cost = crate::money(-1);
    assert!(invalid.unit_cost().is_err());
}

#[test]
fn goods_cost_same_site_production_and_merchant_release_use_one_quantity_basis() {
    let mut state = crate::opening();
    responsive(&mut state, 2, 2, 0);
    state.merchants.push(MerchantHandling {
        site_id: crate::site(2),
        location: "county:26163"
            .parse()
            .expect("the authored literal parses as the declared type"),
        role: MerchantRole::Wholesale,
        capacity_id: crate::corridor(4),
        labor_unit_id: crate::hours(),
    });
    state
        .handling_coefficients
        .push(MerchantHandlingCoefficient {
            site_id: crate::site(2),
            good_id: crate::good(2),
            unit_id: crate::units(),
            hours_per_unit: 1,
        });
    state
        .corridor_capacities
        .extend((1..=9).map(|period| CorridorCapacity {
            corridor_id: crate::corridor(4),
            period,
            available_grams: 4,
        }));
    state
        .labor
        .iter_mut()
        .find(|r| r.site_id == crate::site(2) && r.period == 1)
        .expect("the fixture holds the searched element")
        .available = 12;
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("paid")
    };
    e.member_labor
        .iter_mut()
        .find(|r| {
            r.member_id == StaffingMemberId::from_bytes(crate::site(2).as_bytes()) && r.period == 1
        })
        .expect("the fixture holds the searched element")
        .available_hours = 12;
    e.recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .attendance
        .iter_mut()
        .find(|r| r.site_id == crate::site(2))
        .expect("the fixture holds the searched element")
        .planned_hours = 12;
    let result = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    assert_eq!(output(&result, 2), 4);
    assert_eq!(
        price(&result, 2).cost,
        GoodsPriceCostEvidence {
            basis: GoodsPriceCostBasis::Released,
            quantity: 4,
            carrying_cost: crate::money(12),
            handling_wages: crate::money(4),
        }
    );
    assert_eq!(
        price(&result, 2)
            .cost
            .unit_cost()
            .expect("the fixture account carries its authored unit cost"),
        Some(crate::money(4))
    );
    assert_eq!(price(&result, 2).next_price, crate::money(3));
    let income = result
        .income
        .iter()
        .find(|r| r.account == AccountId::Site(crate::site(2)))
        .expect("the fixture holds the searched element");
    assert_eq!(income.statement.cost_of_goods_sold, crate::money(0)); // Seller-owned transit is not yet a sale.
    assert_eq!(income.statement.handling_expense, crate::money(4));
}
