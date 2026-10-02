//! Inactive workplaces retain finite resources without creating workers or attendance.
use super::*;
use std::collections::BTreeSet;

fn empty_workforce(mut state: MaterialCircuitState) -> MaterialCircuitState {
    for row in &mut state.labor {
        row.available = 0;
    }
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        unreachable!()
    };
    accounts.employment.clear();
    accounts.member_labor.clear();
    let recurring = accounts.recurring.as_mut().unwrap();
    recurring.replenishment.clear();
    for row in &mut recurring.attendance {
        row.planned_hours = 0;
    }
    // Move four existing micro-units to the buyer; total opening money is unchanged.
    let mut snapshot = accounts.book.snapshot();
    for row in &mut snapshot.accounts {
        if row.id == AccountId::Site(site(3)) || row.id == AccountId::Household(household()) {
            row.cash = money(4);
        }
    }
    accounts.book = MonetaryBook::from_snapshot(snapshot).unwrap();
    accounts.costs = HistoricalCostBook::open(
        &accounts.book,
        accounts.costs.snapshot().stocks,
        vec![],
        vec![],
        vec![],
    )
    .unwrap();
    state
}

fn assert_zero_attendance(state: &MaterialCircuitState) {
    let accounts = economy(state);
    let rows = &accounts.recurring.as_ref().unwrap().attendance;
    assert_eq!(rows.len(), 3);
    assert_eq!(
        rows.iter()
            .map(|r| (r.site_id, r.unit_id))
            .collect::<BTreeSet<_>>(),
        [1, 2, 3]
            .map(|id| (site(id), hours()))
            .into_iter()
            .collect()
    );
    assert!(rows
        .iter()
        .all(|r| r.period == state.period && r.planned_hours == 0));
    assert!(state.labor.iter().all(|r| r.available == 0));
    assert!(accounts.employment.is_empty());
    assert!(accounts.member_labor.is_empty());
}

#[test]
fn empty_workplaces_cannot_turn_stock_and_funded_demand_into_free_work_after_restart() {
    let mut state = empty_workforce(opening());
    let inventory = state.inventory.clone();
    let cash = economy(&state).book.total_cash_and_reserves().unwrap();
    for period in 1..=3 {
        let before = state.clone();
        let bytes = encode_material_circuit_state(&state).unwrap();
        let restarted = decode_material_circuit_state(&bytes).unwrap();
        let result = advance_material_circuit(&state).unwrap();
        assert_eq!(result, advance_material_circuit(&restarted).unwrap());
        assert_eq!(state, before);
        assert_eq!(result.state.period, period + 1);
        assert_eq!(result.state.inventory, inventory);
        assert!(result.production.iter().all(|r| r.produced_batches == 0));
        assert!(result.local_fulfillments.is_empty());
        assert!(result.dispatches.is_empty());
        assert!(result.wage_accruals.is_empty());
        assert!(result.labor_use.is_empty());
        assert!(result.member_labor_use.is_empty());
        assert_eq!(result.household_demand[0].admitted_quantity, 1);
        assert_eq!(result.household_demand[0].expired_quantity, 1);
        assert_eq!(result.household_demand[0].fulfilled_quantity, 0);
        assert_eq!(
            economy(&result.state)
                .book
                .cash(AccountId::Household(household()))
                .unwrap(),
            money(4)
        );
        assert_eq!(
            economy(&result.state)
                .book
                .total_cash_and_reserves()
                .unwrap(),
            cash
        );
        assert!(result
            .money_transfers
            .iter()
            .all(|r| !matches!(r.purpose, MoneyTransferPurpose::WagePayment(_))));
        assert_zero_attendance(&result.state);
        state = result.state;
    }
    assert_eq!(
        economy(&state).recurring.as_ref().unwrap().household_stocks[0].quantity,
        0
    );
}

#[test]
fn an_empty_shared_producer_and_merchant_can_request_work_without_inventing_people() {
    let mut state = empty_workforce(producer_retail_opening());
    recurring_mut(&mut state).production[0].output_buffer = 4;
    let bindings = [
        (
            1,
            vec![
                StaffingWorkSource::Production(process(1)),
                StaffingWorkSource::MerchantHandling(site(1)),
            ],
        ),
        (2, vec![StaffingWorkSource::Production(process(2))]),
        (3, vec![StaffingWorkSource::MerchantHandling(site(3))]),
    ]
    .into_iter()
    .map(|(owner, sources)| {
        StaffingPoolBinding::try_new(
            StaffingPoolId::from_bytes([owner; 32]),
            site(owner),
            hours(),
            0,
            StaffingPolicy::one_period(4).unwrap(),
            sources,
        )
        .unwrap()
    })
    .collect::<Vec<_>>();
    let staffing = StaffingState::try_new(
        1,
        bindings
            .iter()
            .map(|b| StaffingPoolState::try_new(b.clone(), 0, 0, 0).unwrap())
            .collect(),
    )
    .unwrap();
    let closed = close_material_period(&state).unwrap();
    let requests = closed.staffing_requests(&bindings).unwrap();
    assert_eq!(requests.len(), 4);
    assert_eq!(
        requests
            .iter()
            .find(|r| r.work_source() == StaffingWorkSource::Production(process(1)))
            .unwrap()
            .hours(),
        4
    );
    let staffed = advance_staffing(&staffing, &requests).unwrap();
    assert!(staffed
        .receipts()
        .iter()
        .all(|r| r.closing_employed() == 0 && r.closing_reserve() == 0 && r.hires() == 0));
    assert!(staffed.next_labor().iter().all(|r| r.available == 0));
    let result = closed
        .finish_with_workforce(staffed.next_labor().to_vec(), vec![])
        .unwrap();
    assert_zero_attendance(&result.state);
    assert!(result.state.production_commitments.is_empty());
    assert!(result.member_labor_use.is_empty());
    assert!(result.wage_accruals.is_empty());
}

#[test]
fn a_memberless_attendance_plan_cannot_claim_positive_hours() {
    let mut state = empty_workforce(opening());
    recurring_mut(&mut state).attendance[2].planned_hours = 1;
    let before = state.clone();
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::PayrollInvariant)
    );
    assert_eq!(state, before);
}

#[test]
fn a_memberless_attendance_plan_requires_its_explicit_current_zero_budget() {
    let mut state = empty_workforce(opening());
    state
        .labor
        .retain(|r| !(r.site_id == site(3) && r.period == 1));
    let before = state.clone();
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::PayrollInvariant)
    );
    assert_eq!(state, before);
}

fn split_retail_members() -> MaterialCircuitState {
    let mut state = opening();
    let second = FinalDemandPrincipalId::from_bytes([77; 32]);
    let member = StaffingMemberId::from_bytes([77; 32]);
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: second,
        location: "county:26163".parse().unwrap(),
    });
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        unreachable!()
    };
    let recurring = accounts.recurring.as_mut().unwrap();
    recurring.households[0].households = 1;
    recurring.households[0].persons = 3;
    recurring.households.push(HouseholdCohort {
        kind: babylon_material_circuit::HouseholdKind::Ordinary,
        principal_id: second,
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
    accounts.employment.push(EmploymentTerms {
        member_id: member,
        site_id: site(3),
        unit_id: hours(),
        payee: second,
        compensation: LaborCompensation::Wage(money(2)),
    });
    for row in &mut accounts.member_labor {
        if row.member_id == StaffingMemberId::from_bytes(site(3).as_bytes()) {
            row.available_hours = 2;
        }
    }
    accounts
        .member_labor
        .extend((1..=9).map(|period| MemberLaborCapacityRow {
            member_id: member,
            period,
            available_hours: 2,
        }));
    let mut snapshot = accounts.book.snapshot();
    snapshot.accounts.push(CashAccount {
        id: AccountId::Household(second),
        cash: money(0),
    });
    accounts.book = MonetaryBook::from_snapshot(snapshot).unwrap();
    let mut stock = accounts.costs.snapshot().stocks;
    stock
        .iter_mut()
        .find(|r| r.owner == AccountId::Household(household()))
        .unwrap()
        .amount = money(24);
    stock.push(StockCarryingValue {
        owner: AccountId::Household(second),
        good_id: good(2),
        unit_id: units(),
        amount: money(8),
    });
    accounts.costs =
        HistoricalCostBook::open(&accounts.book, stock, vec![], vec![], vec![]).unwrap();
    state
}

#[test]
fn multiple_resident_members_share_one_workplace_plan_and_keep_their_own_wages() {
    let mut state = split_retail_members();
    let opening_cash = economy(&state).book.total_cash_and_reserves().unwrap();
    for period in 1..=2 {
        let bytes = encode_material_circuit_state(&state).unwrap();
        let result = advance_material_circuit(&state).unwrap();
        assert_eq!(
            result,
            advance_material_circuit(&decode_material_circuit_state(&bytes).unwrap()).unwrap()
        );
        let rows = &economy(&result.state)
            .recurring
            .as_ref()
            .unwrap()
            .attendance;
        assert_eq!(rows.len(), 3);
        assert_eq!(
            rows.iter()
                .map(|r| (r.site_id, r.unit_id))
                .collect::<BTreeSet<_>>()
                .len(),
            3
        );
        assert!(rows.iter().all(|r| r.period == period + 1));
        let members = result
            .member_labor_use
            .iter()
            .filter(|r| r.site_id == site(3))
            .collect::<Vec<_>>();
        assert_eq!(members.len(), 2);
        assert_eq!(members.iter().map(|r| r.available_hours).sum::<u64>(), 4);
        if period == 1 {
            assert_eq!(
                (
                    members[0].payee,
                    members[0].attended_hours,
                    members[0].accrued_wages
                ),
                (household(), 2, money(2))
            );
            assert_eq!(
                (
                    members[1].payee,
                    members[1].attended_hours,
                    members[1].accrued_wages
                ),
                (FinalDemandPrincipalId::from_bytes([77; 32]), 2, money(4))
            );
        }
        let cohorts = &economy(&result.state)
            .recurring
            .as_ref()
            .unwrap()
            .households;
        assert_eq!(cohorts.iter().map(|r| r.persons).sum::<u64>(), 4);
        assert_eq!(cohorts.iter().map(|r| r.households).sum::<u64>(), 2);
        assert_eq!(
            economy(&result.state)
                .book
                .total_cash_and_reserves()
                .unwrap(),
            opening_cash
        );
        state = result.state;
    }
}
