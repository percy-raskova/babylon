use super::*;

fn retained(state: &mut MaterialCircuitState, earnings: i128) {
    let e = economy_mut(state);
    let mut snapshot = e.costs.snapshot();
    let row = snapshot
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(site()))
        .unwrap();
    row.opening_capital = money(row.opening_capital.micro_units() - earnings);
    row.retained_earnings = money(earnings);
    e.costs = HistoricalCostBook::from_snapshot(snapshot).unwrap();
    e.financial.distributions.push(DistributionPolicy {
        issuer_site_id: site(),
        earnings_fraction_bps: 10_000,
        period_cap: money(i128::MAX),
        cash_floor: money(0),
    });
}

#[test]
fn maximum_currency_distribution_conserves_every_remainder_without_multiplication_overflow() {
    let mut state = opening([i128::MAX, 0, 0, 0, 0]);
    retained(&mut state, i128::MAX);
    let t = advance_material_circuit(&state).unwrap();
    let third = i128::MAX / 3;
    assert_eq!(t.distributions[0].paid, money(third + 1));
    assert_eq!(t.distributions[1].paid, money(third * 2));
    assert_eq!(
        economy(&t.state).book.total_cash_and_reserves().unwrap(),
        money(i128::MAX)
    );
    validate_distribution_receipts(&t.distributions).unwrap();
}

#[test]
fn equity_backed_retained_income_cannot_be_distributed_without_cash() {
    let mut state = opening([0, 0, 0, 0, 0]);
    let other = SiteId::from_bytes([2; 32]);
    state.site_logistics_nodes.push(SiteLogisticsNode {
        site_id: other,
        node_id: LogisticsNodeId::from_bytes([2; 32]),
    });
    let e = economy_mut(&mut state);
    let mut cash = e.book.snapshot();
    cash.accounts.push(CashAccount {
        id: AccountId::Site(other),
        cash: money(0),
    });
    e.book = MonetaryBook::from_snapshot(cash).unwrap();
    let mut equity = e.costs.snapshot().equity;
    equity.push(EquityCarryingValue {
        owner: AccountId::Site(site()),
        issuer_site_id: other,
        amount: money(7),
    });
    e.costs = HistoricalCostBook::open(&e.book, vec![], vec![], equity, vec![]).unwrap();
    e.financial.ownership.push(OwnershipClaim {
        issuer_site_id: other,
        beneficiary: AccountId::Site(site()),
        shares: 1,
    });
    retained(&mut state, 7);
    let t = advance_material_circuit(&state).unwrap();
    assert!(t
        .distributions
        .iter()
        .all(|r| r.eligible_earnings == money(7) && r.paid == money(0)));
    assert_eq!(
        economy(&t.state).book.total_cash_and_reserves().unwrap(),
        money(0)
    );
}

#[test]
fn ownership_requires_explicit_claim_and_descriptors_independent_of_foreign_location() {
    let state = opening([0, 0, 0, 0, 0]);
    let t = advance_material_circuit(&state).unwrap();
    assert!(t.taxes.is_empty());
    let mut duplicate = state.clone();
    let f = &mut economy_mut(&mut duplicate).financial;
    f.ownership.push(f.ownership[0].clone());
    assert_eq!(
        advance_material_circuit(&duplicate),
        Err(MaterialCircuitError::DuplicateRow)
    );
    let mut missing = state;
    economy_mut(&mut missing).financial.locations.pop();
    assert_eq!(
        advance_material_circuit(&missing),
        Err(MaterialCircuitError::FinancialInvariant)
    );
}

#[test]
fn financial_state_wire_refuses_old_schema_noncanonical_claims_and_truncation() {
    let state = opening([7, 0, 0, 0, 0]);
    let bytes = encode_material_circuit_state(&state).unwrap();
    let mut old = bytes.clone();
    let version = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    old[version..version + 2].copy_from_slice(&11_u16.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&old),
        Err(MaterialCircuitError::WireVersion)
    );
    // Seven counted financial tables; three 39-byte locations and two 73-byte claims,
    // followed by the finite capacity tag and two empty service counts.
    let locations = bytes.len() - 9 - (7 * 4 + 3 * 39 + 2 * 73) + 4;
    let ownership = locations + 3 * 39 + 4;
    for (start, width) in [(locations, 39), (ownership, 73)] {
        let mut reversed = bytes.clone();
        reversed[start..start + width * 2].rotate_left(width);
        assert_eq!(
            decode_material_circuit_state(&reversed),
            Err(MaterialCircuitError::WireNoncanonical)
        );
    }
    for end in 0..bytes.len() {
        assert!(decode_material_circuit_state(&bytes[..end]).is_err());
    }
}

#[test]
fn incoming_distribution_cannot_fund_another_issuer_until_the_next_period() {
    let mut state = opening([7, 0, 0, 0, 0]);
    let other = SiteId::from_bytes([2; 32]);
    state.site_logistics_nodes.push(SiteLogisticsNode {
        site_id: other,
        node_id: LogisticsNodeId::from_bytes([2; 32]),
    });
    let e = economy_mut(&mut state);
    let mut book = e.book.snapshot();
    book.accounts.push(CashAccount {
        id: AccountId::Site(other),
        cash: money(0),
    });
    e.book = MonetaryBook::from_snapshot(book).unwrap();
    e.financial.ownership = vec![
        OwnershipClaim {
            issuer_site_id: site(),
            beneficiary: AccountId::Site(other),
            shares: 1,
        },
        OwnershipClaim {
            issuer_site_id: other,
            beneficiary: owner(3),
            shares: 1,
        },
    ];
    e.costs = HistoricalCostBook::open(
        &e.book,
        vec![],
        vec![],
        vec![
            EquityCarryingValue {
                owner: AccountId::Site(other),
                issuer_site_id: site(),
                amount: money(0),
            },
            EquityCarryingValue {
                owner: owner(3),
                issuer_site_id: other,
                amount: money(0),
            },
        ],
        vec![],
    )
    .unwrap();
    retained(&mut state, 7);
    economy_mut(&mut state)
        .financial
        .distributions
        .push(DistributionPolicy {
            issuer_site_id: other,
            earnings_fraction_bps: 10_000,
            period_cap: money(100),
            cash_floor: money(0),
        });
    let first = advance_material_circuit(&state).unwrap();
    assert_eq!(first.distributions[0].paid, money(7));
    assert_eq!(first.distributions[1].paid, money(0));
    assert_eq!(economy(&first.state).book.cash(owner(3)).unwrap(), money(0));
    let next = advance_material_circuit(&first.state).unwrap();
    assert_eq!(next.distributions[1].paid, money(7));
    assert_eq!(economy(&next.state).book.cash(owner(3)).unwrap(), money(7));
    assert_eq!(
        economy(&next.state).book.total_cash_and_reserves().unwrap(),
        money(7)
    );
}
