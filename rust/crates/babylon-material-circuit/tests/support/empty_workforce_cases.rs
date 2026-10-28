//! Inactive workplaces retain finite resources without creating workers or attendance.
use crate::process;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::EmploymentTerms;
use babylon_material_circuit::FinalDemandPrincipal;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdCohort;
use babylon_material_circuit::HouseholdKind;
use babylon_material_circuit::HouseholdStock;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MemberLaborCapacityRow;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::MoneyTransferPurpose;
use babylon_material_circuit::StaffingMemberId;
use babylon_material_circuit::StaffingPolicy;
use babylon_material_circuit::StaffingPoolBinding;
use babylon_material_circuit::StaffingPoolId;
use babylon_material_circuit::StaffingPoolState;
use babylon_material_circuit::StaffingState;
use babylon_material_circuit::StaffingWorkSource;
use babylon_material_circuit::StockCarryingValue;
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
    let recurring = accounts
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow");
    recurring.replenishment.clear();
    for row in &mut recurring.attendance {
        row.planned_hours = 0;
    }
    // Move four existing micro-units to the buyer; total opening money is unchanged.
    let mut snapshot = accounts.book.snapshot();
    for row in &mut snapshot.accounts {
        if row.id == AccountId::Site(crate::site(3))
            || row.id == AccountId::Household(crate::household())
        {
            row.cash = crate::money(4);
        }
    }
    accounts.book =
        MonetaryBook::from_snapshot(snapshot).expect("the snapshot admits the derived value");
    accounts.costs = HistoricalCostBook::open(
        &accounts.book,
        accounts.costs.snapshot().stocks,
        vec![],
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
    state
}

fn assert_zero_attendance(state: &MaterialCircuitState) {
    let accounts = crate::economy(state);
    let rows = &accounts
        .recurring
        .as_ref()
        .expect("the fixture set the optional field before this read")
        .attendance;
    assert_eq!(rows.len(), 3);
    assert_eq!(
        rows.iter()
            .map(|r| (r.site_id, r.unit_id))
            .collect::<BTreeSet<_>>(),
        [1, 2, 3]
            .map(|id| (crate::site(id), crate::hours()))
            .into_iter()
            .collect()
    );
    assert!(rows
        .iter()
        .all(|r| r.period == state.period && r.planned_hours == 0));
    assert!(state.labor.iter().all(|r| r.available == 0));
    assert_eq!(accounts.employment.len(), 0);
    assert_eq!(accounts.member_labor.len(), 0);
}

#[test]
fn empty_workplaces_cannot_turn_stock_and_funded_demand_into_free_work_after_restart() {
    let (catalog, opening) = crate::opening();
    let mut state = empty_workforce(opening);
    let inventory = state.inventory.clone();
    let cash = crate::economy(&state)
        .book
        .total_cash_and_reserves()
        .expect("the fixture book totals without overflow");
    for period in 1..=3 {
        let before = state.clone();
        let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes");
        let restarted = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
            .expect("the canonical material bytes decode");
        let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period");
        assert_eq!(
            result,
            babylon_material_circuit::advance_material_circuit(&catalog, &restarted)
                .expect("the authored material state advances one period")
        );
        assert_eq!(state, before);
        assert_eq!(result.state.period, period + 1);
        assert_eq!(result.state.inventory, inventory);
        assert!(result.production.iter().all(|r| r.produced_batches == 0));
        assert_eq!(result.local_fulfillments.len(), 0);
        assert_eq!(result.dispatches.len(), 0);
        assert_eq!(result.wage_accruals.len(), 0);
        assert_eq!(result.labor_use.len(), 0);
        assert_eq!(result.member_labor_use.len(), 0);
        assert_eq!(result.household_demand[0].admitted_quantity, 1);
        assert_eq!(result.household_demand[0].expired_quantity, 1);
        assert_eq!(result.household_demand[0].fulfilled_quantity, 0);
        assert_eq!(
            crate::economy(&result.state)
                .book
                .cash(AccountId::Household(crate::household()))
                .expect("the fixture book holds the payer account"),
            crate::money(4)
        );
        assert_eq!(
            crate::economy(&result.state)
                .book
                .total_cash_and_reserves()
                .expect("the fixture book totals without overflow"),
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
        crate::economy(&state)
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .household_stocks[0]
            .quantity,
        0
    );
}

#[test]
fn an_empty_shared_producer_and_merchant_can_request_work_without_inventing_people() {
    let (catalog, opening) = crate::producer_retail_opening();
    let mut state = empty_workforce(opening);
    crate::recurring_mut(&mut state).production[0].output_buffer = 4;
    let bindings = [
        (
            1,
            vec![
                StaffingWorkSource::Production(process(1)),
                StaffingWorkSource::MerchantHandling(crate::site(1)),
            ],
        ),
        (2, vec![StaffingWorkSource::Production(process(2))]),
        (
            3,
            vec![StaffingWorkSource::MerchantHandling(crate::site(3))],
        ),
    ]
    .into_iter()
    .map(|(owner, sources)| {
        StaffingPoolBinding::try_new(
            StaffingPoolId::from_bytes([owner; 32]),
            crate::site(owner),
            crate::hours(),
            0,
            StaffingPolicy::one_period(4).expect("the one-period fixture advances"),
            sources,
        )
        .expect("the authored fixture satisfies the constructor invariants")
    })
    .collect::<Vec<_>>();
    let staffing = StaffingState::try_new(
        1,
        bindings
            .iter()
            .map(|b| {
                StaffingPoolState::try_new(b.clone(), 0, 0, 0)
                    .expect("the authored fixture satisfies the constructor invariants")
            })
            .collect(),
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let closed = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes");
    let requests = closed
        .staffing_requests(&catalog, &bindings)
        .expect("the fixture staffing requests are present");
    assert_eq!(requests.len(), 4);
    assert_eq!(
        requests
            .iter()
            .find(|r| r.work_source() == StaffingWorkSource::Production(process(1)))
            .expect("the fixture holds the searched element")
            .hours(),
        4
    );
    let staffed = babylon_material_circuit::advance_staffing(&staffing, &requests)
        .expect("the fixture staffing advances");
    assert!(staffed
        .receipts()
        .iter()
        .all(|r| r.closing_employed() == 0 && r.closing_reserve() == 0 && r.hires() == 0));
    assert!(staffed.next_labor().iter().all(|r| r.available == 0));
    let result = closed
        .finish_with_workforce(&catalog, staffed.next_labor().to_vec(), vec![])
        .expect("the fixture call `finish_with_workforce` succeeds for the authored inputs");
    assert_zero_attendance(&result.state);
    assert_eq!(result.state.production_commitments.len(), 0);
    assert_eq!(result.member_labor_use.len(), 0);
    assert_eq!(result.wage_accruals.len(), 0);
}

#[test]
fn a_memberless_attendance_plan_cannot_claim_positive_hours() {
    let (catalog, opening) = crate::opening();
    let mut state = empty_workforce(opening);
    crate::recurring_mut(&mut state).attendance[2].planned_hours = 1;
    let before = state.clone();
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::PayrollInvariant)
    );
    assert_eq!(state, before);
}

#[test]
fn a_memberless_attendance_plan_requires_its_explicit_current_zero_budget() {
    let (catalog, opening) = crate::opening();
    let mut state = empty_workforce(opening);
    state
        .labor
        .retain(|r| !(r.site_id == crate::site(3) && r.period == 1));
    let before = state.clone();
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::PayrollInvariant)
    );
    assert_eq!(state, before);
}

fn split_retail_members() -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = crate::opening();
    let second = FinalDemandPrincipalId::from_bytes([77; 32]);
    let member = StaffingMemberId::from_bytes([77; 32]);
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: second,
        location: "county:26163"
            .parse()
            .expect("the authored literal parses as the declared type"),
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
        kind: HouseholdKind::Ordinary,
        principal_id: second,
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
        site_id: crate::site(3),
        unit_id: crate::hours(),
        payee: second,
        compensation: LaborCompensation::Wage(crate::money(2)),
    });
    for row in &mut accounts.member_labor {
        if row.member_id == StaffingMemberId::from_bytes(crate::site(3).as_bytes()) {
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
        cash: crate::money(0),
    });
    accounts.book =
        MonetaryBook::from_snapshot(snapshot).expect("the snapshot admits the derived value");
    let mut stock = accounts.costs.snapshot().stocks;
    stock
        .iter_mut()
        .find(|r| r.owner == AccountId::Household(crate::household()))
        .expect("the fixture holds the searched element")
        .amount = crate::money(24);
    stock.push(StockCarryingValue {
        owner: AccountId::Household(second),
        good_id: crate::good(2),
        unit_id: crate::units(),
        amount: crate::money(8),
    });
    accounts.costs = HistoricalCostBook::open(&accounts.book, stock, vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
    (catalog, state)
}

#[test]
fn multiple_resident_members_share_one_workplace_plan_and_keep_their_own_wages() {
    let (catalog, mut state) = split_retail_members();
    let opening_cash = crate::economy(&state)
        .book
        .total_cash_and_reserves()
        .expect("the fixture book totals without overflow");
    for period in 1..=2 {
        let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes");
        let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period");
        assert_eq!(
            result,
            babylon_material_circuit::advance_material_circuit(
                &catalog,
                &babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
                    .expect("the canonical material bytes decode")
            )
            .expect("the authored material state advances one period")
        );
        let rows = &crate::economy(&result.state)
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
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
            .filter(|r| r.site_id == crate::site(3))
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
                (crate::household(), 2, crate::money(2))
            );
            assert_eq!(
                (
                    members[1].payee,
                    members[1].attended_hours,
                    members[1].accrued_wages
                ),
                (
                    FinalDemandPrincipalId::from_bytes([77; 32]),
                    2,
                    crate::money(4)
                )
            );
        }
        let cohorts = &crate::economy(&result.state)
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .households;
        assert_eq!(cohorts.iter().map(|r| r.persons).sum::<u64>(), 4);
        assert_eq!(cohorts.iter().map(|r| r.households).sum::<u64>(), 2);
        assert_eq!(
            crate::economy(&result.state)
                .book
                .total_cash_and_reserves()
                .expect("the fixture book totals without overflow"),
            opening_cash
        );
        state = result.state;
    }
}
