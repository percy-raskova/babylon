//! Counted resident budgets can diverge without adding people, stock or money.
use babylon_material_circuit::AccountId;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::DistributionPolicy;
use babylon_material_circuit::EquityCarryingValue;
use babylon_material_circuit::FinalDemandPrincipal;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdCohort;
use babylon_material_circuit::HouseholdKind;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::HouseholdStock;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::OwnershipClaim;
use babylon_material_circuit::StaffingMemberBinding;
use babylon_material_circuit::StaffingMemberId;
use babylon_material_circuit::StaffingMemberState;
use babylon_material_circuit::StaffingPolicy;
use babylon_material_circuit::StaffingPoolBinding;
use babylon_material_circuit::StaffingPoolId;
use babylon_material_circuit::StaffingPoolState;
use babylon_material_circuit::StaffingState;
use babylon_material_circuit::StaffingWorkRequest;
use babylon_material_circuit::StaffingWorkSource;
use babylon_material_circuit::StockCarryingValue;

fn second_household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([76; 32])
}

fn split_existing_household() -> (MaterialCatalog, MaterialCircuitState) {
    let (mut catalog, mut state) = crate::opening();
    let second = second_household();
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: second,
        location: state.final_demand_principals[0].location,
    });
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        unreachable!()
    };
    let recurring = accounts
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow");
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
        good_id: crate::good(2),
        unit_id: crate::units(),
        quantity: 2,
    });
    let mut need = recurring.household_needs[0].clone();
    need.principal_id = second;
    recurring.household_needs.push(need.clone());
    catalog.household_needs.push(need);
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
        cash: crate::money(0),
    });
    accounts.book =
        MonetaryBook::from_snapshot(snapshot).expect("the snapshot admits the derived value");
    let mut stocks = accounts.costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| r.owner == AccountId::Household(crate::household()))
        .expect("the fixture holds the searched element")
        .amount = crate::money(24);
    stocks.push(StockCarryingValue {
        owner: AccountId::Household(second),
        good_id: crate::good(2),
        unit_id: crate::units(),
        amount: crate::money(8),
    });
    accounts.costs = HistoricalCostBook::open(&accounts.book, stocks, vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    (catalog, state)
}

#[test]
fn a_no_earner_budget_can_exhaust_while_its_neighbor_receives_actual_wages() {
    let (catalog, mut state) = split_existing_household();
    let household_controls = crate::economy(&state)
        .recurring
        .as_ref()
        .expect("the fixture set the optional field before this read")
        .households
        .clone();
    assert_eq!(household_controls.iter().map(|r| r.persons).sum::<u64>(), 4);
    assert_eq!(
        household_controls.iter().map(|r| r.households).sum::<u64>(),
        2
    );
    assert_eq!(
        crate::economy(&state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(24)
    );
    let mut result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    for _ in 0..2 {
        state = result.state;
        result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period");
    }
    let deprived = result
        .household_consumption
        .iter()
        .find(|r| r.principal_id == second_household())
        .expect("the fixture holds the searched element");
    let earning = result
        .household_consumption
        .iter()
        .find(|r| r.principal_id == crate::household())
        .expect("the fixture holds the searched element");
    assert_eq!(
        (deprived.consumed_quantity, deprived.unmet_quantity),
        (0, 1)
    );
    assert_eq!((earning.consumed_quantity, earning.unmet_quantity), (3, 0));
    assert!(
        result
            .wage_accruals
            .iter()
            .any(|r| r.payee == AccountId::Household(crate::household())
                && r.amount.micro_units() > 0)
    );
    assert!(result
        .wage_accruals
        .iter()
        .all(|r| r.payee != AccountId::Household(second_household())));
    assert_eq!(
        crate::economy(&result.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(24)
    );
    assert_eq!(
        crate::economy(&result.state)
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .households,
        household_controls
    );
}

#[test]
fn separate_budget_consumption_and_payroll_survive_canonical_restart() {
    let (catalog, opening) = split_existing_household();
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &first.state)
        .expect("the canonical material state encodes");
    let reopened = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
        .expect("the canonical material bytes decode");
    let live = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("the authored material state advances one period");
    let resumed = babylon_material_circuit::advance_material_circuit(&catalog, &reopened)
        .expect("the authored material state advances one period");
    assert_eq!(live, resumed);
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &live.state)
            .expect("the canonical material state encodes"),
        babylon_material_circuit::encode_material_circuit_state(&catalog, &resumed.state)
            .expect("the canonical material state encodes")
    );
}

#[test]
fn collective_residents_consume_person_based_needs_without_fake_households() {
    let (catalog, mut state) = crate::opening();
    let recurring = crate::recurring_mut(&mut state);
    recurring.households[0].kind = HouseholdKind::CollectiveResidence;
    recurring.households[0].households = 0;
    let encoded = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    let reopened = babylon_material_circuit::decode_material_circuit_state(&catalog, &encoded)
        .expect("the canonical material bytes decode");
    let result = babylon_material_circuit::advance_material_circuit(&catalog, &reopened)
        .expect("the authored material state advances one period");
    assert_eq!(result.household_consumption[0].required_quantity, 4);
    assert_eq!(result.household_consumption[0].consumed_quantity, 4);
    let row = &crate::economy(&result.state)
        .recurring
        .as_ref()
        .expect("the fixture set the optional field before this read")
        .households[0];
    assert_eq!(
        (row.kind, row.persons, row.households),
        (HouseholdKind::CollectiveResidence, 4, 0)
    );
}

#[test]
fn zero_households_require_explicit_collective_kind_and_no_household_basis_need() {
    let (catalog, mut ordinary) = crate::opening();
    crate::recurring_mut(&mut ordinary).households[0].households = 0;
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &ordinary),
        Err(MaterialCircuitError::FinalDemandInvariant)
    );
    let (catalog, mut collective) = crate::opening();
    let recurring = crate::recurring_mut(&mut collective);
    recurring.households[0].kind = HouseholdKind::CollectiveResidence;
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &collective),
        Err(MaterialCircuitError::FinalDemandInvariant)
    );
    let recurring = crate::recurring_mut(&mut collective);
    recurring.households[0].households = 0;
    recurring.household_needs[0].basis = HouseholdNeedBasis::Households;
    assert!(babylon_material_circuit::advance_material_circuit(&catalog, &collective).is_err());
}

#[test]
fn reserve_hiring_preserves_the_resident_budget_identity_and_counts() {
    let (_catalog, state) = split_existing_household();
    let cohorts = crate::economy(&state)
        .recurring
        .as_ref()
        .expect("the fixture set the optional field before this read")
        .households
        .clone();
    let waiting = StaffingMemberBinding::try_new(
        StaffingMemberId::from_bytes([76; 32]),
        second_household(),
        state.final_demand_principals[0].location,
        1,
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let active = StaffingMemberBinding::try_new(
        StaffingMemberId::from_bytes([1; 32]),
        crate::household(),
        state.final_demand_principals[0].location,
        1,
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let pool = StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([3; 32]),
        crate::site(3),
        crate::hours(),
        2,
        StaffingPolicy::one_period(4).expect("the one-period fixture advances"),
        vec![StaffingWorkSource::MerchantHandling(crate::site(3))],
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let request = StaffingWorkRequest::new(
        1,
        pool.pool_id(),
        pool.work_sources()[0],
        crate::site(3),
        crate::hours(),
        8,
    );
    let workforce = StaffingState::try_new(
        1,
        vec![StaffingPoolState::try_new(pool, 1, 1, 0)
            .expect("the authored fixture satisfies the constructor invariants")],
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let closed = babylon_material_circuit::advance_staffing(&workforce, &[request])
        .expect("the fixture staffing advances");
    let members = [
        StaffingMemberState::try_new(active, 1, 0)
            .expect("the authored fixture satisfies the constructor invariants"),
        StaffingMemberState::try_new(waiting.clone(), 0, 1)
            .expect("the authored fixture satisfies the constructor invariants"),
    ];
    let changes =
        babylon_material_circuit::distribute_staffing_members(&closed.receipts()[0], &members)
            .expect("the fixture distributes the authored members");
    let hired = changes
        .iter()
        .find(|r| r.member.member_id() == waiting.member_id())
        .expect("the fixture holds the searched element");
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
        crate::economy(&state)
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .households,
        cohorts
    );
}

#[test]
fn captured_ownership_pays_its_own_budget_without_becoming_wage_income() {
    let (catalog, mut state) = split_existing_household();
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        unreachable!()
    };
    accounts
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .offers
        .iter_mut()
        .find(|r| r.site_id == crate::site(3))
        .expect("the fixture holds the searched element")
        .unit_price = crate::money(5);
    accounts.financial.ownership.push(OwnershipClaim {
        issuer_site_id: crate::site(3),
        beneficiary: AccountId::Household(second_household()),
        shares: 1,
    });
    accounts.financial.distributions.push(DistributionPolicy {
        issuer_site_id: crate::site(3),
        earnings_fraction_bps: 10_000,
        period_cap: crate::money(100),
        cash_floor: crate::money(0),
    });
    accounts.costs = HistoricalCostBook::open(
        &accounts.book,
        accounts.costs.snapshot().stocks,
        vec![],
        vec![EquityCarryingValue {
            owner: AccountId::Household(second_household()),
            issuer_site_id: crate::site(3),
            amount: crate::money(0),
        }],
        vec![],
    )
    .expect("the fixture opens the authored source");
    let mut paid_to_owner = 0;
    let mut actual_wages = 0;
    for _ in 0..8 {
        let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period");
        assert!(closed
            .wage_accruals
            .iter()
            .all(|r| r.payee == AccountId::Household(crate::household())));
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
            .expect("the fixture holds the searched element");
        assert_eq!(owner_income.statement.wage_income, crate::money(0));
        assert_eq!(
            owner_income.statement.distribution_income,
            crate::money(distributed)
        );
        let wage_income = closed
            .income
            .iter()
            .find(|r| r.account == AccountId::Household(crate::household()))
            .expect("the fixture holds the searched element");
        assert_eq!(wage_income.statement.distribution_income, crate::money(0));
        state = closed.state;
    }
    assert!(actual_wages > 0);
    assert!(paid_to_owner > 0);
    assert_eq!(
        crate::economy(&state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(24)
    );
}

#[test]
fn household_kind_is_explicit_in_canonical_bytes_and_unknown_tags_are_refused() {
    let (catalog, state) = split_existing_household();
    let encoded = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
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
        babylon_material_circuit::decode_material_circuit_state(&catalog, &forged),
        Err(MaterialCircuitError::WireEnum)
    );
    assert!(babylon_material_circuit::decode_material_circuit_state(
        &catalog,
        &encoded[..position + row.len() - 1]
    )
    .is_err());
    let restored = babylon_material_circuit::decode_material_circuit_state(&catalog, &encoded)
        .expect("the canonical material bytes decode");
    assert_eq!(
        crate::economy(&restored)
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .households,
        crate::economy(&state)
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .households
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &restored)
            .expect("the canonical material state encodes"),
        encoded
    );
}
