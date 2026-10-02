//! Actual handling proves resident payroll and mixed compensation cost attribution.
use super::*;

fn member(key: u8) -> StaffingMemberId {
    StaffingMemberId::from_bytes([key; 32])
}
fn other_household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([77; 32])
}

fn mixed(second: LaborCompensation) -> MaterialCircuitState {
    let mut state = opening();
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: other_household(),
        location: "county:26099".parse().unwrap(),
    });
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let mut snapshot = economy.book.snapshot();
    snapshot.accounts.push(CashAccount {
        id: AccountId::Household(other_household()),
        cash: money(0),
    });
    economy.book = MonetaryBook::from_snapshot(snapshot).unwrap();
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        economy.costs.snapshot().stocks,
        vec![],
        vec![],
        vec![],
    )
    .unwrap();
    economy.employment = vec![
        EmploymentTerms {
            member_id: member(1),
            site_id: store(),
            unit_id: hours(),
            payee: household(),
            compensation: LaborCompensation::Wage(money(1)),
        },
        EmploymentTerms {
            member_id: member(2),
            site_id: store(),
            unit_id: hours(),
            payee: other_household(),
            compensation: second,
        },
    ];
    economy.member_labor = vec![
        MemberLaborCapacityRow {
            member_id: member(1),
            period: 1,
            available_hours: 2,
        },
        MemberLaborCapacityRow {
            member_id: member(2),
            period: 1,
            available_hours: 2,
        },
    ];
    state
}

#[test]
fn two_resident_payees_receive_only_their_own_funded_attendance() {
    let state = mixed(LaborCompensation::Wage(money(2)));
    let closed = advance_material_circuit(&state).unwrap();
    assert_eq!(
        closed
            .wage_accruals
            .iter()
            .map(|r| r.amount.micro_units())
            .collect::<Vec<_>>(),
        [2, 4]
    );
    assert_eq!(
        book(&closed.state)
            .cash(AccountId::Household(household()))
            .unwrap(),
        money(18)
    );
    assert_eq!(
        book(&closed.state)
            .cash(AccountId::Household(other_household()))
            .unwrap(),
        money(4)
    );
    assert_eq!(
        book(&closed.state).cash(AccountId::Site(store())).unwrap(),
        money(2)
    );
    assert_eq!(closed.member_labor_use.len(), 2);
    assert_eq!(
        book(&closed.state).total_cash_and_reserves().unwrap(),
        money(24)
    );
}

#[test]
fn owner_and_family_hours_do_real_work_without_wages_or_ownership_claims() {
    for mode in [
        LaborCompensation::WorkingOwner,
        LaborCompensation::UnpaidFamily,
    ] {
        let (state, _) = admit_material_purchase(
            &mixed(mode),
            MaterialPurchase::LocalFinalDemand(retail()),
            money(4),
        )
        .unwrap();
        let closed = advance_material_circuit(&state).unwrap();
        assert_eq!(closed.local_fulfillments[0].quantity, 2);
        assert_eq!(closed.wage_accruals.len(), 1);
        assert_eq!(closed.wage_accruals[0].amount, money(2));
        let account = closed
            .income
            .iter()
            .find(|r| r.account == AccountId::Site(store()))
            .unwrap();
        assert_eq!(account.statement.handling_expense, money(1));
        assert_eq!(account.statement.idle_labor_expense, money(1));
        assert_eq!(closed.member_labor_use[0].handling_hours, 1);
        assert_eq!(closed.member_labor_use[1].handling_hours, 1);
        assert_eq!(closed.member_labor_use[1].accrued_wages, money(0));
        assert_eq!(
            book(&closed.state)
                .cash(AccountId::Household(other_household()))
                .unwrap(),
            money(0)
        );
        assert_eq!(closed.labor_use[0].non_wage_hours, 2);
        assert_eq!(closed.labor_use[0].unpaid_idle_hours, 1);
    }
}

#[test]
fn conflicting_member_hours_refuse_before_payroll_or_goods_change() {
    let mut state = mixed(LaborCompensation::WorkingOwner);
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    economy.member_labor[1].available_hours += 1;
    let original = state.clone();
    assert!(advance_material_circuit(&state).is_err());
    assert_eq!(state, original);
}
