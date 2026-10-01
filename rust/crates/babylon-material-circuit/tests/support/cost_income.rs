//! Independent monetary journal assertions beyond cash conservation.
use super::*;

fn receipt(transition: &MaterialCircuitTransition, account: AccountId) -> &IncomeReceipt {
    transition
        .income
        .iter()
        .find(|row| row.account == account)
        .expect("one income statement per captured account")
}

#[test]
fn historical_cost_eight_period_control_matches_independent_income_and_retained_earnings() {
    let mut state = opening();
    let mut income = [0_i128; 4];
    for period in 1..=8 {
        recurring_mut(&mut state).household_purchases[0].enabled = ![3, 4].contains(&period);
        let result = advance_material_circuit(&state).unwrap();
        for (index, account) in [
            AccountId::Site(site(1)),
            AccountId::Site(site(2)),
            AccountId::Site(site(3)),
            AccountId::Household(household()),
        ]
        .into_iter()
        .enumerate()
        {
            let row = receipt(&result, account);
            row.validate().unwrap();
            let expected = [
                0,
                0,
                if period == 3 { -4 } else { 0 },
                [0, 0, 0, -12, 0, -12, -4, 0][usize::try_from(period - 1).unwrap()],
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
                receipt(&result, AccountId::Site(site(3)))
                    .statement
                    .idle_labor_expense,
                money(4)
            );
            assert_eq!(
                receipt(&result, AccountId::Site(site(3)))
                    .statement
                    .handling_expense,
                money(0)
            );
        }
        state = result.state;
    }
    assert_eq!(income, [0, 0, -4, -28]);
    let snapshot = economy(&state).costs.snapshot();
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
        economy(&state).book.total_cash_and_reserves().unwrap(),
        money(24)
    );
}

#[test]
fn historical_cost_unsold_output_and_quote_changes_do_not_create_income_or_revalue_stock() {
    let mut state = opening();
    for period in 1..=3 {
        recurring_mut(&mut state).household_purchases[0].enabled = period != 3;
        state = advance_material_circuit(&state).unwrap().state;
    }
    let before = economy(&state).costs.snapshot();
    let factory = before
        .stocks
        .iter()
        .find(|r| r.owner == AccountId::Site(site(2)) && r.good_id == good(2))
        .unwrap();
    assert_eq!(factory.amount, money(12));
    for offer in &mut recurring_mut(&mut state).offers {
        offer.unit_price = money(100);
    }
    recurring_mut(&mut state).household_purchases[0].enabled = false;
    let result = advance_material_circuit(&state).unwrap();
    assert_eq!(
        receipt(&result, AccountId::Site(site(2))).net_income,
        money(0)
    );
    let after = economy(&result.state).costs.snapshot();
    assert_eq!(
        after
            .stocks
            .iter()
            .find(|r| r.owner == AccountId::Site(site(2)) && r.good_id == good(2))
            .unwrap()
            .amount,
        money(12)
    );
}

#[test]
fn historical_cost_lost_seller_owned_transit_is_an_expense_and_restart_preserves_basis() {
    let mut state = opening();
    state.route_stages[0].loss_ppm = 500_000;
    let first = advance_material_circuit(&state).unwrap();
    assert_eq!(
        receipt(&first, AccountId::Site(site(1))).statement.sales,
        money(0)
    );
    let bytes = encode_material_circuit_state(&first.state).unwrap();
    let restarted = decode_material_circuit_state(&bytes).unwrap();
    let second = advance_material_circuit(&first.state).unwrap();
    assert_eq!(second, advance_material_circuit(&restarted).unwrap());
    let supplier = receipt(&second, AccountId::Site(site(1)));
    assert_eq!(supplier.statement.sales, money(2));
    assert_eq!(supplier.statement.cost_of_goods_sold, money(2));
    assert_eq!(supplier.statement.freight_loss_expense, money(2));
    assert_eq!(supplier.net_income, money(-2));
    assert_eq!(
        economy(&second.state)
            .book
            .total_cash_and_reserves()
            .unwrap(),
        money(24)
    );
}

#[test]
fn valuation_wire_refuses_missing_stocks_zero_quantity_cost_and_forged_equity() {
    let state = opening();
    let bytes = encode_material_circuit_state(&state).unwrap();
    assert_eq!(decode_material_circuit_state(&bytes).unwrap(), state);
    let snapshot = economy(&state).costs.snapshot();
    let width = 12
        + 65 * snapshot.accounts.len()
        + 113 * snapshot.stocks.len()
        + 80 * snapshot.freight.len();
    let start = bytes.len() - 9 - width; // Finite capacity tag and two empty service row counts follow accounting.
    for length in start..bytes.len() {
        assert!(decode_material_circuit_state(&bytes[..length]).is_err());
    }
    let mut previous = bytes.clone();
    let version = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    previous[version..version + 2].copy_from_slice(&7_u16.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&previous),
        Err(MaterialCircuitError::WireVersion)
    );
    let stock_start = start + 4 + 65 * snapshot.accounts.len();
    let mut reordered = bytes.clone();
    let first = stock_start + 4;
    let left = reordered[first..first + 113].to_vec();
    let right = reordered[first + 113..first + 226].to_vec();
    reordered[first..first + 113].copy_from_slice(&right);
    reordered[first + 113..first + 226].copy_from_slice(&left);
    assert_eq!(
        decode_material_circuit_state(&reordered),
        Err(MaterialCircuitError::WireNoncanonical)
    );
    let mut oversized = bytes.clone();
    oversized[stock_start..stock_start + 4].copy_from_slice(
        &u32::try_from(MAX_CARRYING_STOCKS + 1)
            .unwrap()
            .to_be_bytes(),
    );
    assert_eq!(
        decode_material_circuit_state(&oversized),
        Err(MaterialCircuitError::WireLimit)
    );
    for mode in 0..3 {
        let mut changed = state.clone();
        let CircuitAccounting::Monetary(book) = &mut changed.accounting else {
            panic!("paid control");
        };
        let mut rows = book.costs.snapshot();
        match mode {
            0 => {
                rows.stocks.pop();
            }
            1 => {
                rows.accounts[0].retained_earnings = money(1);
            }
            _ => {
                changed.inventory[1].quantity = 0;
            }
        }
        book.costs = HistoricalCostBook::from_snapshot(rows).unwrap();
        assert_eq!(
            encode_material_circuit_state(&changed),
            Err(MaterialCircuitError::ValuationInvariant)
        );
    }
}

#[test]
fn valuation_late_close_failure_leaves_costs_income_and_cash_unpublished() {
    let mut state = opening();
    recurring_mut(&mut state).production[0].output_buffer = u64::MAX;
    let captured = encode_material_circuit_state(&state).unwrap();
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(encode_material_circuit_state(&state).unwrap(), captured);
    assert_eq!(
        economy(&state)
            .costs
            .snapshot()
            .accounts
            .iter()
            .map(|r| r.retained_earnings.micro_units())
            .collect::<Vec<_>>(),
        [0, 0, 0, 0]
    );
}
