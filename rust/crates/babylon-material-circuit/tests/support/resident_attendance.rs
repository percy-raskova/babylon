//! Actual handling proves resident payroll and mixed compensation cost attribution.
use crate::book;
use crate::hours;
use crate::household;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::EmploymentTerms;
use babylon_material_circuit::FinalDemandPrincipal;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialPurchase;
use babylon_material_circuit::MemberLaborCapacityRow;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::StaffingMemberId;

fn member(key: u8) -> StaffingMemberId {
    StaffingMemberId::from_bytes([key; 32])
}
fn other_household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([77; 32])
}

fn mixed(second: LaborCompensation) -> MaterialCircuitState {
    let mut state = crate::opening();
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: other_household(),
        location: "county:26099"
            .parse()
            .expect("the authored literal parses as the declared type"),
    });
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let mut snapshot = economy.book.snapshot();
    snapshot.accounts.push(CashAccount {
        id: AccountId::Household(other_household()),
        cash: crate::money(0),
    });
    economy.book =
        MonetaryBook::from_snapshot(snapshot).expect("the snapshot admits the derived value");
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        economy.costs.snapshot().stocks,
        vec![],
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
    economy.employment = vec![
        EmploymentTerms {
            member_id: member(1),
            site_id: crate::store(),
            unit_id: hours(),
            payee: household(),
            compensation: LaborCompensation::Wage(crate::money(1)),
        },
        EmploymentTerms {
            member_id: member(2),
            site_id: crate::store(),
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
    let state = mixed(LaborCompensation::Wage(crate::money(2)));
    let closed = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
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
            .expect("the fixture book holds the payer account"),
        crate::money(18)
    );
    assert_eq!(
        book(&closed.state)
            .cash(AccountId::Household(other_household()))
            .expect("the fixture book holds the payer account"),
        crate::money(4)
    );
    assert_eq!(
        book(&closed.state)
            .cash(AccountId::Site(crate::store()))
            .expect("the fixture book holds the payer account"),
        crate::money(2)
    );
    assert_eq!(closed.member_labor_use.len(), 2);
    assert_eq!(
        book(&closed.state)
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(24)
    );
}

#[test]
fn owner_and_family_hours_do_real_work_without_wages_or_ownership_claims() {
    for mode in [
        LaborCompensation::WorkingOwner,
        LaborCompensation::UnpaidFamily,
    ] {
        let (state, _) = babylon_material_circuit::admit_material_purchase(
            &mixed(mode),
            MaterialPurchase::LocalFinalDemand(crate::retail()),
            crate::money(4),
        )
        .expect("the fixture admits the authored purchase");
        let closed = babylon_material_circuit::advance_material_circuit(&state)
            .expect("the authored material state advances one period");
        assert_eq!(closed.local_fulfillments[0].quantity, 2);
        assert_eq!(closed.wage_accruals.len(), 1);
        assert_eq!(closed.wage_accruals[0].amount, crate::money(2));
        let account = closed
            .income
            .iter()
            .find(|r| r.account == AccountId::Site(crate::store()))
            .expect("the fixture holds the searched element");
        assert_eq!(account.statement.handling_expense, crate::money(1));
        assert_eq!(account.statement.idle_labor_expense, crate::money(1));
        assert_eq!(closed.member_labor_use[0].handling_hours, 1);
        assert_eq!(closed.member_labor_use[1].handling_hours, 1);
        assert_eq!(closed.member_labor_use[1].accrued_wages, crate::money(0));
        assert_eq!(
            book(&closed.state)
                .cash(AccountId::Household(other_household()))
                .expect("the fixture book holds the payer account"),
            crate::money(0)
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
    assert!(babylon_material_circuit::advance_material_circuit(&state).is_err());
    assert_eq!(state, original);
}
