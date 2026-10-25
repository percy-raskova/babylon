//! Independent monetary journal assertions beyond cash conservation.
use babylon_material_circuit::AccountId;
use babylon_material_circuit::IncomeReceipt;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitTransition;
use babylon_material_circuit::MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES;

fn receipt(transition: &MaterialCircuitTransition, account: AccountId) -> &IncomeReceipt {
    transition
        .income
        .iter()
        .find(|row| row.account == account)
        .expect("one income statement per captured account")
}

#[test]
fn historical_cost_eight_period_control_matches_independent_income_and_retained_earnings() {
    let (catalog, mut state) = crate::opening();
    let mut income = [0_i128; 4];
    for period in 1..=8 {
        crate::recurring_mut(&mut state).household_purchases[0].enabled = ![3, 4].contains(&period);
        let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period");
        for (index, account) in [
            AccountId::Site(crate::site(1)),
            AccountId::Site(crate::site(2)),
            AccountId::Site(crate::site(3)),
            AccountId::Household(crate::household()),
        ]
        .into_iter()
        .enumerate()
        {
            let row = receipt(&result, account);
            row.validate()
                .expect("the authored fixture passes validation");
            let expected = [
                0,
                0,
                if period == 3 { -4 } else { 0 },
                [0, 0, 0, -12, 0, -12, -4, 0]
                    [usize::try_from(period - 1).expect("the fixture value fits the target range")],
            ];
            assert_eq!(
                row.net_income.micro_units(),
                expected[index],
                "period {period}, account {index}"
            );
            assert_eq!(row.opening_retained_earnings.micro_units(), income[index]);
            income[index] += row.net_income.micro_units();
            assert_eq!(row.closing_retained_earnings.micro_units(), income[index]);
        }
        if period == 3 {
            assert_eq!(
                receipt(&result, AccountId::Site(crate::site(3)))
                    .statement
                    .idle_labor_expense,
                crate::money(4)
            );
            assert_eq!(
                receipt(&result, AccountId::Site(crate::site(3)))
                    .statement
                    .handling_expense,
                crate::money(0)
            );
        }
        state = result.state;
    }
    assert_eq!(income, [0, 0, -4, -28]);
    let snapshot = crate::economy(&state).costs.snapshot();
    assert_eq!(
        snapshot
            .accounts
            .iter()
            .map(|r| r.opening_capital.micro_units())
            .collect::<Vec<_>>(),
        [4, 16, 20, 32]
    );
    assert_eq!(
        snapshot
            .accounts
            .iter()
            .map(|r| r.retained_earnings.micro_units())
            .collect::<Vec<_>>(),
        income
    );
    assert_eq!(
        snapshot
            .freight
            .iter()
            .map(|r| r.amount.micro_units())
            .sum::<i128>(),
        16
    );
    assert_eq!(
        crate::economy(&state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(24)
    );
}

#[test]
fn historical_cost_unsold_output_and_quote_changes_do_not_create_income_or_revalue_stock() {
    let (catalog, mut state) = crate::opening();
    for period in 1..=3 {
        crate::recurring_mut(&mut state).household_purchases[0].enabled = period != 3;
        state = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period")
            .state;
    }
    let before = crate::economy(&state).costs.snapshot();
    let factory = before
        .stocks
        .iter()
        .find(|r| r.owner == AccountId::Site(crate::site(2)) && r.good_id == crate::good(2))
        .expect("the fixture holds the searched element");
    assert_eq!(factory.amount, crate::money(12));
    for offer in &mut crate::recurring_mut(&mut state).offers {
        offer.unit_price = crate::money(100);
    }
    crate::recurring_mut(&mut state).household_purchases[0].enabled = false;
    let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(
        receipt(&result, AccountId::Site(crate::site(2))).net_income,
        crate::money(0)
    );
    let after = crate::economy(&result.state).costs.snapshot();
    assert_eq!(
        after
            .stocks
            .iter()
            .find(|r| r.owner == AccountId::Site(crate::site(2)) && r.good_id == crate::good(2))
            .expect("the fixture holds the searched element")
            .amount,
        crate::money(12)
    );
}

#[test]
fn historical_cost_lost_seller_owned_transit_is_an_expense_and_restart_preserves_basis() {
    let (mut catalog, state) = crate::opening();
    catalog.route_stages[0].loss_ppm = 500_000;
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(
        receipt(&first, AccountId::Site(crate::site(1)))
            .statement
            .sales,
        crate::money(0)
    );
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &first.state)
        .expect("the canonical material state encodes");
    let restarted = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
        .expect("the canonical material bytes decode");
    let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("the authored material state advances one period");
    assert_eq!(
        second,
        babylon_material_circuit::advance_material_circuit(&catalog, &restarted)
            .expect("the authored material state advances one period")
    );
    let supplier = receipt(&second, AccountId::Site(crate::site(1)));
    assert_eq!(supplier.statement.sales, crate::money(2));
    assert_eq!(supplier.statement.cost_of_goods_sold, crate::money(2));
    assert_eq!(supplier.statement.freight_loss_expense, crate::money(2));
    assert_eq!(supplier.net_income, crate::money(-2));
    assert_eq!(
        crate::economy(&second.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(24)
    );
}

#[test]
fn valuation_wire_refuses_missing_stocks_zero_quantity_cost_and_forged_equity() {
    let (catalog, state) = crate::opening();
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
            .expect("the canonical material bytes decode"),
        state
    );
    let version = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    for length in 0..bytes.len() {
        assert!(babylon_material_circuit::decode_material_circuit_state(
            &catalog,
            &bytes[..length]
        )
        .is_err());
    }
    let mut previous = bytes.clone();
    previous[version..version + 2].copy_from_slice(&7_u16.to_be_bytes());
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &previous),
        Err(MaterialCircuitError::WireVersion)
    );
    let mut trailing = bytes;
    trailing.push(0);
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &trailing),
        Err(MaterialCircuitError::WireTrailing)
    );
}

#[test]
fn valuation_late_close_failure_leaves_costs_income_and_cash_unpublished() {
    let (catalog, mut state) = crate::opening();
    crate::recurring_mut(&mut state).production[0].output_buffer = u64::MAX;
    let captured = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes"),
        captured
    );
    assert_eq!(
        crate::economy(&state)
            .costs
            .snapshot()
            .accounts
            .iter()
            .map(|r| r.retained_earnings.micro_units())
            .collect::<Vec<_>>(),
        [0, 0, 0, 0]
    );
}
