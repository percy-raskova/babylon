//! Agency-paid attendance through the real detached material close.
#[allow(
    dead_code,
    reason = "shared scenario support includes other test controls"
)]
#[path = "support/organizer_funding_control.rs"]
mod control;

use babylon_material_circuit::{
    AccountId, AgencyAttendanceInput, AgencyAttendanceOutcome, AidOutcome, FinalDemandPrincipalId,
    MaterialCatalog, MaterialCircuitState, MaterialCircuitTransition,
};

#[test]
fn selected_funded_attendance_pays_household_and_reduces_available_time() {
    let (catalog, opening) = control::opening();
    let first = control::close(&catalog, &opening, &[], &[control::collection(1)])
        .expect("the authored attendance scenario is valid");
    let (catalog, second) = control::controlled_opening(catalog, first.state);
    let before = babylon_material_circuit::encode_material_circuit_state(&catalog, &second)
        .expect("the authored attendance scenario is valid");
    let residence = second
        .final_demand_principals
        .iter()
        .find(|row| row.id == control::recipient())
        .expect("the authored attendance scenario is valid")
        .location;
    let input = AgencyAttendanceInput {
        intent_id: [61; 32],
        shift_id: babylon_material_circuit::agency_shift_id(2, [61; 32]),
        agency: match control::organization() {
            AccountId::Organization(id) => id,
            _ => unreachable!(),
        },
        principal_id: control::recipient(),
        residence,
        labor_unit_id: control::unit(90),
        due_period: 2,
        hours: 1,
        hourly_rate: control::money(100_000),
    };
    let baseline = control::close(&catalog, &second, &[], &[])
        .expect("the authored attendance scenario is valid");
    let completed = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &second,
        &[],
        &[],
        &[input],
    )
    .expect("the authored attendance scenario is valid")
    .finish_with_workforce(&catalog, control::labor(3), control::members(3))
    .expect("the authored attendance scenario is valid");
    assert_eq!(completed.household_demand, baseline.household_demand);
    assert_eq!(
        completed.agency_attendance[0].outcome,
        AgencyAttendanceOutcome::Paid
    );
    assert_eq!(
        control::cash(&completed.state, control::organization()),
        300_000
    );
    assert_eq!(
        control::cash(&completed.state, AccountId::Household(control::recipient())),
        100_000
    );
    assert_eq!(
        control::remaining(&completed.state, control::recipient()),
        431
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &second)
            .expect("the authored attendance scenario is valid"),
        before
    );
}

#[test]
fn unfunded_selected_shift_does_not_pay_or_consume_household_time() {
    let (catalog, opening) = control::opening();
    let residence = opening
        .final_demand_principals
        .iter()
        .find(|row| row.id == control::recipient())
        .expect("the authored attendance scenario is valid")
        .location;
    let input = AgencyAttendanceInput {
        intent_id: [61; 32],
        shift_id: babylon_material_circuit::agency_shift_id(1, [61; 32]),
        agency: match control::organization() {
            AccountId::Organization(id) => id,
            _ => unreachable!(),
        },
        principal_id: control::recipient(),
        residence,
        labor_unit_id: control::unit(90),
        due_period: 1,
        hours: 1,
        hourly_rate: control::money(100_000),
    };
    let completed = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &opening,
        &[],
        &[],
        &[input],
    )
    .expect("the authored attendance scenario is valid")
    .finish_with_workforce(&catalog, control::labor(2), control::members(2))
    .expect("the authored attendance scenario is valid");
    assert_eq!(
        completed.agency_attendance[0].outcome,
        AgencyAttendanceOutcome::NoFunds
    );
    assert_eq!(completed.agency_attendance[0].attended_hours, 0);
    assert_eq!(control::cash(&completed.state, control::organization()), 0);
    assert_eq!(
        control::remaining(&completed.state, control::recipient()),
        432
    );
}

#[test]
fn immediate_aid_can_make_investigator_time_eligible_after_the_preliminary_preview() {
    let (catalog, opening) = control::opening();
    let mut definition = catalog.into_definition();
    let policy = definition
        .household_time_policy
        .iter_mut()
        .find(|row| row.principal_id == control::recipient())
        .expect("the authored attendance scenario is valid");
    policy.hours_per_eligible_person = 116;
    let catalog =
        MaterialCatalog::try_new(definition).expect("the authored attendance scenario is valid");
    let first = control::close(&catalog, &opening, &[], &[control::collection(1)])
        .expect("the authored attendance scenario is valid");
    let (catalog, second) = control::controlled_opening(catalog, first.state);
    let residence = second
        .final_demand_principals
        .iter()
        .find(|row| row.id == control::recipient())
        .expect("the authored attendance scenario is valid")
        .location;
    let input = AgencyAttendanceInput {
        intent_id: [63; 32],
        shift_id: babylon_material_circuit::agency_shift_id(2, [63; 32]),
        agency: match control::organization() {
            AccountId::Organization(id) => id,
            _ => unreachable!(),
        },
        principal_id: control::recipient(),
        residence,
        labor_unit_id: control::unit(90),
        due_period: 2,
        hours: 1,
        hourly_rate: control::money(100_000),
    };
    let completed = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &second,
        &[control::aid(2)],
        &[],
        &[input],
    )
    .expect("the authored attendance scenario is valid")
    .finish_with_workforce(&catalog, control::labor(3), control::members(3))
    .expect("the authored attendance scenario is valid");
    assert!(completed
        .aid
        .iter()
        .any(|row| row.recipient == control::recipient()
            && row.outcome == AidOutcome::Granted
            && row.quantity > 0));
    assert_eq!(
        completed.agency_attendance[0].outcome,
        AgencyAttendanceOutcome::Paid
    );
    assert_eq!(completed.agency_attendance[0].attended_hours, 1);
}

fn input_for(
    state: &MaterialCircuitState,
    principal: FinalDemandPrincipalId,
    rate: i128,
) -> AgencyAttendanceInput {
    AgencyAttendanceInput {
        intent_id: [71; 32],
        shift_id: babylon_material_circuit::agency_shift_id(state.period, [71; 32]),
        agency: match control::organization() {
            AccountId::Organization(id) => id,
            _ => unreachable!(),
        },
        principal_id: principal,
        residence: state
            .final_demand_principals
            .iter()
            .find(|row| row.id == principal)
            .expect("the authored attendance scenario is valid")
            .location,
        labor_unit_id: control::unit(90),
        due_period: state.period,
        hours: 1,
        hourly_rate: control::money(rate),
    }
}

#[test]
fn protected_time_cancels_and_retires_funded_shift_without_payment() {
    let (catalog, opening) = control::opening();
    let mut definition = catalog.into_definition();
    definition
        .household_time_policy
        .iter_mut()
        .find(|r| r.principal_id == control::recipient())
        .expect("the authored attendance scenario is valid")
        .hours_per_eligible_person = 1;
    let catalog =
        MaterialCatalog::try_new(definition).expect("the authored attendance scenario is valid");
    let first = control::close(&catalog, &opening, &[], &[control::collection(1)])
        .expect("the authored attendance scenario is valid");
    let (catalog, second) = control::controlled_opening(catalog, first.state);
    let input = input_for(&second, control::recipient(), 100_000);
    let completed = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &second,
        &[],
        &[],
        std::slice::from_ref(&input),
    )
    .expect("the authored attendance scenario is valid")
    .finish_with_workforce(&catalog, control::labor(3), control::members(3))
    .expect("the authored attendance scenario is valid");
    let receipt = &completed.agency_attendance[0];
    assert_eq!(receipt.outcome, AgencyAttendanceOutcome::InsufficientTime);
    assert_eq!(
        (receipt.reserved, receipt.cancelled, receipt.paid),
        (
            control::money(100_000),
            control::money(100_000),
            control::money(0)
        )
    );
    assert_eq!(receipt.attended_hours, 0);
    assert!(control::economy(&completed.state)
        .book
        .shift(input.shift_id)
        .is_err());
    assert_eq!(
        control::cash(&completed.state, control::organization()),
        400_000
    );
    assert!(!completed
        .wage_accruals
        .iter()
        .any(|row| row.shift == input.shift_id));
}

#[test]
fn partial_cash_and_duplicate_input_are_refused_without_mutating_the_opening() {
    let (catalog, opening) = control::opening();
    let first = control::close(&catalog, &opening, &[], &[control::collection(1)])
        .expect("the authored attendance scenario is valid");
    let (catalog, second) = control::controlled_opening(catalog, first.state);
    let before = babylon_material_circuit::encode_material_circuit_state(&catalog, &second)
        .expect("the authored attendance scenario is valid");
    let input = input_for(&second, control::recipient(), 500_000);
    let completed = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &second,
        &[],
        &[],
        std::slice::from_ref(&input),
    )
    .expect("the authored attendance scenario is valid")
    .finish_with_workforce(&catalog, control::labor(3), control::members(3))
    .expect("the authored attendance scenario is valid");
    assert_eq!(
        completed.agency_attendance[0].outcome,
        AgencyAttendanceOutcome::NoFunds
    );
    assert_eq!(
        completed.agency_attendance[0].shortfall,
        control::money(100_000)
    );
    assert_eq!(completed.agency_attendance[0].reserved, control::money(0));
    assert!(
        babylon_material_circuit::close_material_period_with_support(
            &catalog,
            &second,
            &[],
            &[],
            &[input.clone(), input.clone()]
        )
        .is_err()
    );
    let mut wrong_period = input.clone();
    wrong_period.due_period += 1;
    assert!(
        babylon_material_circuit::close_material_period_with_support(
            &catalog,
            &second,
            &[],
            &[],
            &[wrong_period]
        )
        .is_err()
    );
    let mut wrong_shift = input;
    wrong_shift.shift_id =
        babylon_material_circuit::agency_shift_id(second.period + 1, wrong_shift.intent_id);
    assert!(
        babylon_material_circuit::close_material_period_with_support(
            &catalog,
            &second,
            &[],
            &[],
            &[wrong_shift]
        )
        .is_err()
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &second)
            .expect("the authored attendance scenario is valid"),
        before
    );
}

#[test]
fn agency_wage_and_voluntary_aid_share_one_time_and_cash_book() {
    let (catalog, opening) = control::opening();
    let first = control::close(&catalog, &opening, &[], &[control::collection(1)])
        .expect("the authored attendance scenario is valid");
    let (catalog, second) = control::controlled_opening(catalog, first.state);
    let input = input_for(&second, control::donor(), 100_000);
    let total = control::economy(&second)
        .book
        .total_cash_and_reserves()
        .expect("the authored attendance scenario is valid");
    let completed = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &second,
        &[control::aid(2)],
        &[],
        std::slice::from_ref(&input),
    )
    .expect("the authored attendance scenario is valid")
    .finish_with_workforce(&catalog, control::labor(3), control::members(3))
    .expect("the authored attendance scenario is valid");
    let receipt = &completed.agency_attendance[0];
    assert_eq!(receipt.outcome, AgencyAttendanceOutcome::Paid);
    assert_eq!(receipt.attended_hours, 1);
    let time = completed
        .household_time
        .iter()
        .find(|r| r.principal_id == control::donor())
        .expect("the authored attendance scenario is valid");
    assert_eq!(time.attended_hours, 641);
    let aid_hours: u64 = completed
        .aid
        .iter()
        .filter(|r| r.donor == control::donor())
        .map(|r| r.contribution_hours)
        .sum();
    // Four selected food units each need two hours; the agency's cash payment
    // reduces only the independent cash leg from400000 to300000 micros.
    assert_eq!(aid_hours, 8);
    assert!(completed.aid.iter().any(|row| row.outcome
        == babylon_material_circuit::AidOutcome::CashGranted
        && row.cash_amount == control::money(300_000)));
    assert!(completed.aid.iter().any(|row| row.outcome
        == babylon_material_circuit::AidOutcome::Granted
        && row.quantity == 4
        && row.cash_amount == control::money(0)));
    assert_eq!(
        control::remaining(&completed.state, control::donor()),
        time.contribution_available_hours - aid_hours
    );
    let employer = completed
        .income
        .iter()
        .find(|r| r.account == control::organization())
        .expect("the authored attendance scenario is valid");
    let household = completed
        .income
        .iter()
        .find(|r| r.account == AccountId::Household(control::donor()))
        .expect("the authored attendance scenario is valid");
    assert_eq!(
        employer.statement.agency_observation_labor_expense,
        control::money(100_000)
    );
    assert_eq!(
        household.statement.wage_income,
        control::money(15_360_100_000)
    );
    let tax = completed
        .taxes
        .iter()
        .find(|r| r.payer == AccountId::Household(control::donor()))
        .expect("the authored attendance scenario is valid");
    assert_eq!(tax.taxable_amount, household.statement.wage_income);
    assert_eq!(tax.assessed, control::money(2_304_015_000));
    assert_eq!(
        control::economy(&completed.state)
            .book
            .total_cash_and_reserves()
            .expect("the authored attendance scenario is valid"),
        total
    );
    assert!(control::economy(&completed.state)
        .book
        .shift(input.shift_id)
        .is_err());
}

#[test]
fn agency_hour_takes_priority_over_competing_voluntary_donor_hours() {
    let (catalog, opening) = control::opening_with_agency(500_000);
    let mut definition = catalog.into_definition();
    definition
        .household_time_policy
        .iter_mut()
        .find(|r| r.principal_id == control::donor())
        .expect("the authored attendance scenario is valid")
        .hours_per_eligible_person = 129;
    let catalog =
        MaterialCatalog::try_new(definition).expect("the authored attendance scenario is valid");
    let baseline = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &opening,
        &[control::aid(1)],
        &[],
        &[],
    )
    .expect("the authored attendance scenario is valid")
    .finish_with_workforce(&catalog, control::labor(2), control::members(2))
    .expect("the authored attendance scenario is valid");
    let input = input_for(&opening, control::donor(), 100_000);
    let paid = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &opening,
        &[control::aid(1)],
        &[],
        &[input],
    )
    .expect("the authored attendance scenario is valid")
    .finish_with_workforce(&catalog, control::labor(2), control::members(2))
    .expect("the authored attendance scenario is valid");
    let granted = |transition: &MaterialCircuitTransition| {
        transition
            .aid
            .iter()
            .filter(|row| row.outcome == AidOutcome::Granted)
            .map(|row| row.quantity)
            .sum::<u64>()
    };
    assert_eq!(granted(&baseline), 4);
    assert_eq!(granted(&paid), 3);
    assert_eq!(
        paid.agency_attendance[0].outcome,
        AgencyAttendanceOutcome::Paid
    );
    let time = paid
        .household_time
        .iter()
        .find(|r| r.principal_id == control::donor())
        .expect("the authored attendance scenario is valid");
    assert_eq!(time.attended_hours, 641);
    assert_eq!(time.contribution_available_hours, 7);
    assert_eq!(control::remaining(&paid.state, control::donor()), 1);
}

#[test]
fn only_prior_committed_public_appropriation_can_fund_the_agency_shift() {
    use babylon_material_circuit::{
        CircuitAccounting, PublicAllocation, PublicBudget, PublicTransferTreatment,
    };
    let (catalog, mut opening) = control::opening_with_cash(0, 100_000);
    let CircuitAccounting::Monetary(economy) = &mut opening.accounting else {
        unreachable!()
    };
    let AccountId::Public(public_id) = control::public() else {
        unreachable!()
    };
    economy.financial.public_budgets.push(PublicBudget {
        public_account: public_id,
        period_cap: control::money(100_000),
        cash_floor: control::money(0),
    });
    economy.financial.public_allocations.push(PublicAllocation {
        public_account: public_id,
        recipient: control::organization(),
        treatment: PublicTransferTreatment::AgencyAppropriation,
        priority: 0,
        amount_per_period: control::money(100_000),
    });
    let total = control::economy(&opening)
        .book
        .total_cash_and_reserves()
        .expect("the authored attendance scenario is valid");
    let first_input = input_for(&opening, control::recipient(), 100_000);
    let first = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &opening,
        &[],
        &[],
        &[first_input],
    )
    .expect("the authored attendance scenario is valid")
    .finish_with_workforce(&catalog, control::labor(2), control::members(2))
    .expect("the authored attendance scenario is valid");
    assert_eq!(
        first.agency_attendance[0].outcome,
        AgencyAttendanceOutcome::NoFunds
    );
    assert_eq!(first.public_budgets[0].paid, control::money(100_000));
    assert_eq!(
        control::cash(&first.state, control::organization()),
        100_000
    );
    assert_eq!(
        control::economy(&first.state)
            .book
            .total_cash_and_reserves()
            .expect("the authored attendance scenario is valid"),
        total
    );
    let (catalog, second) = control::controlled_opening(catalog, first.state);
    let second_input = input_for(&second, control::recipient(), 100_000);
    let second = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &second,
        &[],
        &[],
        &[second_input],
    )
    .expect("the authored attendance scenario is valid")
    .finish_with_workforce(&catalog, control::labor(3), control::members(3))
    .expect("the authored attendance scenario is valid");
    assert_eq!(
        second.agency_attendance[0].outcome,
        AgencyAttendanceOutcome::Paid
    );
    assert_eq!(second.agency_attendance[0].paid, control::money(100_000));
    assert_eq!(
        control::cash(&second.state, AccountId::Household(control::recipient())),
        100_000
    );
    assert_eq!(
        control::economy(&second.state)
            .book
            .total_cash_and_reserves()
            .expect("the authored attendance scenario is valid"),
        total
    );
}

#[test]
fn same_period_grant_cannot_replace_prior_cash_spent_on_an_earlier_contribution() {
    use babylon_material_circuit::{
        CapitalContributionOrder, CircuitAccounting, ContributionId, EquityCarryingValue,
        HistoricalCostBook, OwnershipClaim, PublicAllocation, PublicBudget,
        PublicTransferTreatment,
    };
    let (catalog, mut opening) = control::opening_with_cash(10, 20);
    let CircuitAccounting::Monetary(economy) = &mut opening.accounting else {
        unreachable!()
    };
    let AccountId::Public(public_id) = control::public() else {
        unreachable!()
    };
    economy.financial.ownership.push(OwnershipClaim {
        issuer_site_id: control::site(1),
        beneficiary: control::organization(),
        shares: 1,
    });
    economy
        .financial
        .contributions
        .push(CapitalContributionOrder {
            id: ContributionId::from_bytes([90; 32]),
            due_period: 1,
            contributor: control::organization(),
            issuer_site_id: control::site(1),
            amount: control::money(10),
        });
    let mut snapshot = economy.costs.snapshot();
    snapshot.equity.push(EquityCarryingValue {
        owner: control::organization(),
        issuer_site_id: control::site(1),
        amount: control::money(0),
    });
    economy.costs = HistoricalCostBook::from_snapshot(snapshot)
        .expect("the authored attendance scenario is valid");
    economy.financial.public_budgets.push(PublicBudget {
        public_account: public_id,
        period_cap: control::money(20),
        cash_floor: control::money(0),
    });
    economy.financial.public_allocations.push(PublicAllocation {
        public_account: public_id,
        recipient: control::organization(),
        treatment: PublicTransferTreatment::AgencyAppropriation,
        priority: 0,
        amount_per_period: control::money(20),
    });
    let input = input_for(&opening, control::recipient(), 10);
    let completed = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &opening,
        &[],
        &[],
        std::slice::from_ref(&input),
    )
    .expect("the authored attendance scenario is valid")
    .finish_with_workforce(&catalog, control::labor(2), control::members(2))
    .expect("the authored attendance scenario is valid");
    assert_eq!(completed.contributions[0].paid, control::money(10));
    assert_eq!(completed.public_budgets[0].paid, control::money(20));
    assert_eq!(
        completed.agency_attendance[0].outcome,
        AgencyAttendanceOutcome::NoFunds
    );
    assert_eq!(completed.agency_attendance[0].shortfall, control::money(10));
    assert_eq!(control::cash(&completed.state, control::organization()), 20);
    assert!(!completed
        .wage_accruals
        .iter()
        .any(|r| r.shift == input.shift_id));
}

#[test]
fn exact_zero_and_one_residual_hours_control_paid_attendance() {
    for (available, expected) in [
        (0, AgencyAttendanceOutcome::InsufficientTime),
        (1, AgencyAttendanceOutcome::Paid),
    ] {
        let (catalog, opening) = control::opening_with_agency(500_000);
        let mut definition = catalog.into_definition();
        let policy = definition
            .household_time_policy
            .iter_mut()
            .find(|row| row.principal_id == control::recipient())
            .expect("recipient has a time policy");
        policy.eligible_persons = 1;
        policy.hours_per_eligible_person = 4 + available;
        policy.protected.hours_per_basis = 1;
        policy.routine_provisioning.hours_per_basis = 0;
        policy.unmet_burdens.clear();
        let catalog = MaterialCatalog::try_new(definition).expect("time policy is valid");
        let input = input_for(&opening, control::recipient(), 100_000);
        let result = babylon_material_circuit::close_material_period_with_support(
            &catalog,
            &opening,
            &[],
            &[],
            &[input],
        )
        .expect("close begins")
        .finish_with_workforce(&catalog, control::labor(2), control::members(2))
        .expect("close finishes");
        let time = result
            .household_time
            .iter()
            .find(|row| row.principal_id == control::recipient())
            .expect("recipient time is present");
        assert_eq!(time.protected_unresolved_hours, 0);
        assert_eq!(time.unpaid_unresolved_hours, 0);
        assert_eq!(result.agency_attendance[0].outcome, expected);
        assert_eq!(result.agency_attendance[0].attended_hours, available);
        assert_eq!(time.contribution_available_hours, 0);
    }
}

#[test]
fn unpaid_obligation_alone_refuses_a_funded_agency_hour() {
    let (catalog, opening) = control::opening_with_agency(500_000);
    let mut definition = catalog.into_definition();
    let policy = definition
        .household_time_policy
        .iter_mut()
        .find(|row| row.principal_id == control::recipient())
        .expect("recipient has a time policy");
    policy.eligible_persons = 1;
    policy.hours_per_eligible_person = 3;
    policy.protected.hours_per_basis = 0;
    policy.routine_provisioning.hours_per_basis = 1;
    policy.unmet_burdens.clear();
    let catalog = MaterialCatalog::try_new(definition).expect("time policy is valid");
    let input = input_for(&opening, control::recipient(), 100_000);
    let result = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &opening,
        &[],
        &[],
        &[input],
    )
    .expect("close begins")
    .finish_with_workforce(&catalog, control::labor(2), control::members(2))
    .expect("close finishes");
    let time = result
        .household_time
        .iter()
        .find(|row| row.principal_id == control::recipient())
        .expect("recipient time is present");
    assert_eq!(time.protected_unresolved_hours, 0);
    assert_eq!(time.unpaid_unresolved_hours, 1);
    assert_eq!(
        result.agency_attendance[0].outcome,
        AgencyAttendanceOutcome::InsufficientTime
    );
    assert_eq!(result.agency_attendance[0].paid, control::money(0));
}

#[test]
fn duplicate_entitlement_and_existing_shift_are_refused() {
    use babylon_material_circuit::CircuitAccounting;
    use babylon_material_circuit::FundedShift;

    let (catalog, mut opening) = control::opening_with_agency(500_000);
    let mut definition = catalog.clone().into_definition();
    let duplicate = definition
        .household_time_policy
        .iter()
        .find(|row| row.principal_id == control::recipient())
        .expect("recipient policy")
        .clone();
    definition.household_time_policy.push(duplicate);
    assert!(MaterialCatalog::try_new(definition).is_err());
    let input = input_for(&opening, control::recipient(), 100_000);
    let CircuitAccounting::Monetary(economy) = &mut opening.accounting else {
        unreachable!()
    };
    economy
        .book
        .reserve_shift(
            FundedShift::new(
                input.shift_id,
                AccountId::Organization(input.agency),
                AccountId::Household(input.principal_id),
                input.due_period,
                input.hours,
                input.hourly_rate,
            )
            .expect("shift terms are valid"),
        )
        .expect("agency has the funds");
    // A current-period reservation is deliberately not an admissible opening;
    // compare the full supplied value rather than asking the codec to admit it.
    let before = opening.clone();
    assert!(
        babylon_material_circuit::close_material_period_with_support(
            &catalog,
            &opening,
            &[],
            &[],
            &[input],
        )
        .is_err()
    );
    assert_eq!(opening, before);
}

#[test]
fn duplicate_aid_refusal_after_funding_preserves_opening_bytes() {
    let (catalog, opening) = control::opening_with_agency(500_000);
    let before = babylon_material_circuit::encode_material_circuit_state(&catalog, &opening)
        .expect("opening encodes");
    let input = input_for(&opening, control::recipient(), 100_000);
    let aid = control::aid(1);
    assert!(
        babylon_material_circuit::close_material_period_with_support(
            &catalog,
            &opening,
            &[aid.clone(), aid],
            &[],
            &[input],
        )
        .is_err()
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &opening)
            .expect("unchanged opening encodes"),
        before
    );
}

#[test]
fn authored_time_policy_permutation_preserves_paid_result() {
    let (catalog, opening) = control::opening_with_agency(500_000);
    let mut definition = catalog.clone().into_definition();
    definition.household_time_policy.reverse();
    let permuted = MaterialCatalog::try_new(definition).expect("permuted definitions are valid");
    let input = input_for(&opening, control::recipient(), 100_000);
    let close = |catalog: &MaterialCatalog| {
        babylon_material_circuit::close_material_period_with_support(
            catalog,
            &opening,
            &[],
            &[],
            std::slice::from_ref(&input),
        )
        .expect("close begins")
        .finish_with_workforce(catalog, control::labor(2), control::members(2))
        .expect("close finishes")
    };
    let first = close(&catalog);
    let second = close(&permuted);
    assert_eq!(first.agency_attendance, second.agency_attendance);
    assert_eq!(first.household_time, second.household_time);
    assert_eq!(first.money_transfers, second.money_transfers);
    assert_eq!(first.wage_accruals, second.wage_accruals);
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &first.state)
            .expect("first state encodes"),
        babylon_material_circuit::encode_material_circuit_state(&permuted, &second.state)
            .expect("permuted state encodes")
    );
}
