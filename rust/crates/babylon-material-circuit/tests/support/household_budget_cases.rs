//! Counted resident budgets can diverge without adding people, stock or money.
use super::*;

fn second_household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([76; 32])
}

fn split_existing_household() -> MaterialCircuitState {
    let mut state = opening();
    let second = second_household();
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: second,
        location: state.final_demand_principals[0].location,
    });
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        unreachable!()
    };
    let recurring = accounts.recurring.as_mut().unwrap();
    recurring.households[0].households = 1;
    recurring.households[0].persons = 3;
    recurring.households.push(HouseholdCohort {
        principal_id: second,
        kind: HouseholdKind::Ordinary,
        households: 1,
        persons: 1,
    });
    recurring.household_stocks[0].quantity = 6;
    recurring.household_stocks.push(HouseholdStock {
        principal_id: second,
        good_id: good(2),
        unit_id: units(),
        quantity: 2,
    });
    let mut need = recurring.household_needs[0].clone();
    need.principal_id = second;
    recurring.household_needs.push(need);
    recurring.household_purchases[0].target_closing_stock = 6;
    recurring.household_purchases[0].maximum_purchase = 3;
    let mut purchase = recurring.household_purchases[0].clone();
    purchase.principal_id = second;
    purchase.target_closing_stock = 2;
    purchase.maximum_purchase = 1;
    recurring.household_purchases.push(purchase);
    let mut snapshot = accounts.book.snapshot();
    snapshot.accounts.push(CashAccount {
        id: AccountId::Household(second),
        cash: money(0),
    });
    accounts.book = MonetaryBook::from_snapshot(snapshot).unwrap();
    let mut stocks = accounts.costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| r.owner == AccountId::Household(household()))
        .unwrap()
        .amount = money(24);
    stocks.push(StockCarryingValue {
        owner: AccountId::Household(second),
        good_id: good(2),
        unit_id: units(),
        amount: money(8),
    });
    accounts.costs =
        HistoricalCostBook::open(&accounts.book, stocks, vec![], vec![], vec![]).unwrap();
    state
}

#[test]
fn a_no_earner_budget_can_exhaust_while_its_neighbor_receives_actual_wages() {
    let mut state = split_existing_household();
    let household_controls = economy(&state)
        .recurring
        .as_ref()
        .unwrap()
        .households
        .clone();
    assert_eq!(household_controls.iter().map(|r| r.persons).sum::<u64>(), 4);
    assert_eq!(
        household_controls.iter().map(|r| r.households).sum::<u64>(),
        2
    );
    assert_eq!(
        economy(&state).book.total_cash_and_reserves().unwrap(),
        money(24)
    );
    let mut result = advance_material_circuit(&state).unwrap();
    for _ in 0..2 {
        state = result.state;
        result = advance_material_circuit(&state).unwrap();
    }
    let deprived = result
        .household_consumption
        .iter()
        .find(|r| r.principal_id == second_household())
        .unwrap();
    let earning = result
        .household_consumption
        .iter()
        .find(|r| r.principal_id == household())
        .unwrap();
    assert_eq!(
        (deprived.consumed_quantity, deprived.unmet_quantity),
        (0, 1)
    );
    assert_eq!((earning.consumed_quantity, earning.unmet_quantity), (3, 0));
    assert!(result
        .wage_accruals
        .iter()
        .any(|r| r.payee == AccountId::Household(household()) && r.amount.micro_units() > 0));
    assert!(result
        .wage_accruals
        .iter()
        .all(|r| r.payee != AccountId::Household(second_household())));
    assert_eq!(
        economy(&result.state)
            .book
            .total_cash_and_reserves()
            .unwrap(),
        money(24)
    );
    assert_eq!(
        economy(&result.state)
            .recurring
            .as_ref()
            .unwrap()
            .households,
        household_controls
    );
}

#[test]
fn separate_budget_consumption_and_payroll_survive_canonical_restart() {
    let first = advance_material_circuit(&split_existing_household()).unwrap();
    let bytes = encode_material_circuit_state(&first.state).unwrap();
    let reopened = decode_material_circuit_state(&bytes).unwrap();
    let live = advance_material_circuit(&first.state).unwrap();
    let resumed = advance_material_circuit(&reopened).unwrap();
    assert_eq!(live, resumed);
    assert_eq!(
        encode_material_circuit_state(&live.state).unwrap(),
        encode_material_circuit_state(&resumed.state).unwrap()
    );
}

#[test]
fn collective_residents_consume_person_based_needs_without_fake_households() {
    let mut state = opening();
    let recurring = recurring_mut(&mut state);
    recurring.households[0].kind = HouseholdKind::CollectiveResidence;
    recurring.households[0].households = 0;
    let encoded = encode_material_circuit_state(&state).unwrap();
    let reopened = decode_material_circuit_state(&encoded).unwrap();
    let result = advance_material_circuit(&reopened).unwrap();
    assert_eq!(result.household_consumption[0].required_quantity, 4);
    assert_eq!(result.household_consumption[0].consumed_quantity, 4);
    let row = &economy(&result.state)
        .recurring
        .as_ref()
        .unwrap()
        .households[0];
    assert_eq!(
        (row.kind, row.persons, row.households),
        (HouseholdKind::CollectiveResidence, 4, 0)
    );
}

#[test]
fn zero_households_require_explicit_collective_kind_and_no_household_basis_need() {
    let mut ordinary = opening();
    recurring_mut(&mut ordinary).households[0].households = 0;
    assert_eq!(
        advance_material_circuit(&ordinary),
        Err(MaterialCircuitError::FinalDemandInvariant)
    );
    let mut collective = opening();
    let recurring = recurring_mut(&mut collective);
    recurring.households[0].kind = HouseholdKind::CollectiveResidence;
    assert_eq!(
        advance_material_circuit(&collective),
        Err(MaterialCircuitError::FinalDemandInvariant)
    );
    let recurring = recurring_mut(&mut collective);
    recurring.households[0].households = 0;
    recurring.household_needs[0].basis = HouseholdNeedBasis::Households;
    assert!(advance_material_circuit(&collective).is_err());
}

#[test]
fn reserve_hiring_preserves_the_resident_budget_identity_and_counts() {
    let state = split_existing_household();
    let cohorts = economy(&state)
        .recurring
        .as_ref()
        .unwrap()
        .households
        .clone();
    let waiting = StaffingMemberBinding::try_new(
        StaffingMemberId::from_bytes([76; 32]),
        second_household(),
        state.final_demand_principals[0].location,
        1,
    )
    .unwrap();
    let active = StaffingMemberBinding::try_new(
        StaffingMemberId::from_bytes([1; 32]),
        household(),
        state.final_demand_principals[0].location,
        1,
    )
    .unwrap();
    let pool = StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([3; 32]),
        site(3),
        hours(),
        2,
        StaffingPolicy::one_period(4).unwrap(),
        vec![StaffingWorkSource::MerchantHandling(site(3))],
    )
    .unwrap();
    let request = StaffingWorkRequest::new(
        1,
        pool.pool_id(),
        pool.work_sources()[0],
        site(3),
        hours(),
        8,
    );
    let workforce =
        StaffingState::try_new(1, vec![StaffingPoolState::try_new(pool, 1, 1, 0).unwrap()])
            .unwrap();
    let closed = advance_staffing(&workforce, &[request]).unwrap();
    let members = [
        StaffingMemberState::try_new(active, 1, 0).unwrap(),
        StaffingMemberState::try_new(waiting.clone(), 0, 1).unwrap(),
    ];
    let changes = distribute_staffing_members(&closed.receipts()[0], &members).unwrap();
    let hired = changes
        .iter()
        .find(|r| r.member.member_id() == waiting.member_id())
        .unwrap();
    assert_eq!(hired.member, waiting);
    assert_eq!(hired.member.household_id(), second_household());
    assert_eq!(
        (
            hired.opening_employed,
            hired.opening_reserve,
            hired.hires,
            hired.closing_employed,
            hired.closing_reserve
        ),
        (0, 1, 1, 1, 0)
    );
    assert_eq!(hired.next_opening_hours, 4);
    assert_eq!(
        changes
            .iter()
            .map(|r| r.closing_employed + r.closing_reserve)
            .sum::<u64>(),
        2
    );
    assert_eq!(
        economy(&state).recurring.as_ref().unwrap().households,
        cohorts
    );
}

#[test]
fn captured_ownership_pays_its_own_budget_without_becoming_wage_income() {
    let mut state = split_existing_household();
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        unreachable!()
    };
    accounts
        .recurring
        .as_mut()
        .unwrap()
        .offers
        .iter_mut()
        .find(|r| r.site_id == site(3))
        .unwrap()
        .unit_price = money(5);
    accounts.financial.ownership.push(OwnershipClaim {
        issuer_site_id: site(3),
        beneficiary: AccountId::Household(second_household()),
        shares: 1,
    });
    accounts.financial.distributions.push(DistributionPolicy {
        issuer_site_id: site(3),
        earnings_fraction_bps: 10_000,
        period_cap: money(100),
        cash_floor: money(0),
    });
    accounts.costs = HistoricalCostBook::open(
        &accounts.book,
        accounts.costs.snapshot().stocks,
        vec![],
        vec![EquityCarryingValue {
            owner: AccountId::Household(second_household()),
            issuer_site_id: site(3),
            amount: money(0),
        }],
        vec![],
    )
    .unwrap();
    let mut paid_to_owner = 0;
    let mut actual_wages = 0;
    for _ in 0..8 {
        let closed = advance_material_circuit(&state).unwrap();
        assert!(closed
            .wage_accruals
            .iter()
            .all(|r| r.payee == AccountId::Household(household())));
        actual_wages += closed
            .wage_accruals
            .iter()
            .map(|r| r.amount.micro_units())
            .sum::<i128>();
        assert!(closed
            .distributions
            .iter()
            .all(|r| r.beneficiary == AccountId::Household(second_household())));
        let distributed = closed
            .distributions
            .iter()
            .map(|r| r.paid.micro_units())
            .sum::<i128>();
        paid_to_owner += distributed;
        let owner_income = closed
            .income
            .iter()
            .find(|r| r.account == AccountId::Household(second_household()))
            .unwrap();
        assert_eq!(owner_income.statement.wage_income, money(0));
        assert_eq!(
            owner_income.statement.distribution_income,
            money(distributed)
        );
        let wage_income = closed
            .income
            .iter()
            .find(|r| r.account == AccountId::Household(household()))
            .unwrap();
        assert_eq!(wage_income.statement.distribution_income, money(0));
        state = closed.state;
    }
    assert!(actual_wages > 0);
    assert!(paid_to_owner > 0);
    assert_eq!(
        economy(&state).book.total_cash_and_reserves().unwrap(),
        money(24)
    );
}

#[test]
fn household_kind_is_explicit_in_canonical_bytes_and_unknown_tags_are_refused() {
    let state = split_existing_household();
    let encoded = encode_material_circuit_state(&state).unwrap();
    let mut row = vec![1]; // current Ordinary tag, followed by the exact counted principal
    row.extend_from_slice(&second_household().as_bytes());
    row.extend_from_slice(&1_u64.to_be_bytes());
    row.extend_from_slice(&1_u64.to_be_bytes());
    let positions: Vec<_> = encoded
        .windows(row.len())
        .enumerate()
        .filter_map(|(i, candidate)| (candidate == row).then_some(i))
        .collect();
    assert_eq!(positions.len(), 1);
    let position = positions[0];
    let mut forged = encoded.clone();
    forged[position] = 255;
    assert_eq!(
        decode_material_circuit_state(&forged),
        Err(MaterialCircuitError::WireEnum)
    );
    assert!(decode_material_circuit_state(&encoded[..position + row.len() - 1]).is_err());
    let restored = decode_material_circuit_state(&encoded).unwrap();
    assert_eq!(
        economy(&restored).recurring.as_ref().unwrap().households,
        economy(&state).recurring.as_ref().unwrap().households
    );
    assert_eq!(encode_material_circuit_state(&restored).unwrap(), encoded);
}
