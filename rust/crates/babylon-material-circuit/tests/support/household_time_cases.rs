//! Independent finite-hour witnesses through the real recurring material close.
use super::*;

fn time_opening(food: u64) -> MaterialCircuitState {
    let mut state = opening();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the worked control must have monetary accounts");
    };
    let recurring = economy.recurring.as_mut().unwrap();
    recurring.household_stocks[0].quantity = food;
    recurring.household_purchases[0].enabled = false;
    economy.household_time = HouseholdTimeAccounting::Modeled(
        HouseholdTimeBook::new(vec![HouseholdTimePolicy {
            principal_id: household(),
            labor_unit_id: hours(),
            eligible_persons: 4,
            hours_per_eligible_person: 8,
            protected: HouseholdTimeCommitment {
                basis: HouseholdNeedBasis::Households,
                hours_per_basis: 2,
            },
            routine_provisioning: HouseholdTimeCommitment {
                basis: HouseholdNeedBasis::Households,
                hours_per_basis: 3,
            },
            unmet_burdens: vec![HouseholdUnmetTimeBurden {
                good_id: good(2),
                unit_id: units(),
                hours_per_unmet_unit: 5,
            }],
        }])
        .unwrap(),
    );
    state
}

#[test]
fn actual_attendance_and_consumption_close_one_finite_household_time_account() {
    let transition = advance_material_circuit(&time_opening(4)).unwrap();
    assert_eq!(transition.household_time.len(), 1);
    let row = &transition.household_time[0];
    assert_eq!(row.principal_id, household());
    assert_eq!(row.labor_unit_id, hours());
    assert_eq!(row.period, 1);
    assert_eq!(row.endowment_hours, 32);
    assert_eq!(row.attended_hours, 16);
    assert_eq!(row.protected_hours, 4);
    assert_eq!(row.unpaid_requested_hours, 6);
    assert_eq!(row.unpaid_allocated_hours, 6);
    assert_eq!(row.unpaid_unresolved_hours, 0);
    assert_eq!(row.contribution_available_hours, 6);
    assert_eq!(
        row.endowment_hours,
        row.attended_hours
            + row.protected_hours
            + row.unpaid_allocated_hours
            + row.contribution_available_hours
    );
}

#[test]
fn paid_idle_and_unmet_food_do_not_become_voluntary_time() {
    let transition = advance_material_circuit(&time_opening(2)).unwrap();
    assert_eq!(transition.household_consumption[0].unmet_quantity, 2);
    assert!(transition.member_labor_use.iter().any(|r| r.idle_hours > 0));
    let row = &transition.household_time[0];
    assert_eq!(row.attended_hours, 16);
    assert_eq!(row.unpaid_requested_hours, 16);
    assert_eq!(row.unpaid_allocated_hours, 12);
    assert_eq!(row.unpaid_unresolved_hours, 4);
    assert_eq!(row.contribution_available_hours, 0);
}

#[test]
fn shared_household_aliases_cannot_duplicate_contribution_time() {
    let mut state = advance_material_circuit(&time_opening(4)).unwrap().state;
    let before = state.clone();
    let uses = [
        HouseholdContributionUse {
            use_id: [1; 32],
            principal_id: household(),
            actor_id: 11,
            contributor_id: 21,
            hours: 4,
        },
        HouseholdContributionUse {
            use_id: [2; 32],
            principal_id: household(),
            actor_id: 12,
            contributor_id: 22,
            hours: 3,
        },
    ];
    assert_eq!(
        consume_household_contributions(&mut state, 1, &uses),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
    assert_eq!(state, before);
    let one = &uses[..1];
    let receipt = consume_household_contributions(&mut state, 1, one).unwrap();
    let once = state.clone();
    assert_eq!(
        consume_household_contributions(&mut state, 1, one).unwrap(),
        receipt
    );
    assert_eq!(state, once);
    let mut conflicting = uses[0].clone();
    conflicting.hours = 3;
    assert_eq!(
        consume_household_contributions(&mut state, 1, &[conflicting]),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
    assert_eq!(state, once);
    let bytes = encode_material_circuit_state(&state).unwrap();
    assert_eq!(decode_material_circuit_state(&bytes).unwrap(), state);
}

#[test]
fn time_endowments_refuse_population_overrun_unaccounted_attendance_and_wrong_units() {
    for invalid in [0, 5] {
        let mut state = time_opening(4);
        let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
            unreachable!()
        };
        let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time else {
            unreachable!()
        };
        book.policies[0].eligible_persons = invalid;
        assert_eq!(
            advance_material_circuit(&state),
            Err(MaterialCircuitError::HouseholdTimeInvariant)
        );
    }
    let mut state = time_opening(4);
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time else {
        unreachable!()
    };
    book.policies[0].labor_unit_id = units();
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
}

#[test]
fn missing_wage_funding_preserves_needs_and_finite_household_obligations() {
    let mut state = time_opening(2);
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    // Capture a different closed monetary opening, rather than erase earned wages.
    let snapshot = economy.book.snapshot();
    economy.book = MonetaryBook::open(
        snapshot
            .accounts
            .into_iter()
            .map(|mut r| {
                r.cash = money(0);
                r
            })
            .collect(),
    )
    .unwrap();
    let costs = economy.costs.snapshot();
    economy.costs =
        HistoricalCostBook::open(&economy.book, costs.stocks, costs.freight, vec![], vec![])
            .unwrap();
    let transition = advance_material_circuit(&state).unwrap();
    assert_eq!(transition.household_consumption[0].required_quantity, 4);
    assert_eq!(transition.household_consumption[0].unmet_quantity, 2);
    let row = &transition.household_time[0];
    assert_eq!(row.endowment_hours, 32);
    assert_eq!(row.attended_hours, 0);
    assert_eq!(row.protected_hours, 4);
    assert_eq!(row.unpaid_requested_hours, 16);
    assert_eq!(row.unpaid_allocated_hours, 16);
    assert_eq!(row.contribution_available_hours, 12);
}

#[test]
fn payment_of_an_earlier_wage_claim_does_not_charge_attendance_twice() {
    let mut state = advance_material_circuit(&time_opening(4)).unwrap().state;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let shift = ShiftId::from_bytes([97; 32]);
    economy
        .book
        .reserve_shift(
            FundedShift::new(
                shift,
                AccountId::Site(site(3)),
                AccountId::Household(household()),
                1,
                2,
                money(1),
            )
            .unwrap(),
        )
        .unwrap();
    economy.book.accrue_shift(shift).unwrap();
    let costs = economy.costs.snapshot();
    // The controlled continuation captures its existing claim and liability once.
    economy.costs =
        HistoricalCostBook::open(&economy.book, costs.stocks, costs.freight, vec![], vec![])
            .unwrap();
    let transition = advance_material_circuit(&state).unwrap();
    assert_eq!(
        transition
            .money_transfers
            .iter()
            .filter(|r| r.purpose == MoneyTransferPurpose::WagePayment(shift))
            .count(),
        1
    );
    assert_eq!(
        transition.household_time[0].attended_hours,
        transition
            .member_labor_use
            .iter()
            .map(|r| r.attended_hours)
            .sum::<u64>()
    );
    assert!(transition.household_time.iter().all(|r| r.period == 2));
}

#[test]
fn nonwage_attendance_and_idle_use_the_same_finite_household_time() {
    for compensation in [
        LaborCompensation::WorkingOwner,
        LaborCompensation::UnpaidFamily,
    ] {
        let mut state = time_opening(4);
        let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
            unreachable!()
        };
        for term in &mut economy.employment {
            term.compensation = compensation;
        }
        let transition = advance_material_circuit(&state).unwrap();
        assert!(transition.wage_accruals.is_empty());
        assert!(transition.member_labor_use.iter().any(|r| r.idle_hours > 0));
        assert!(transition
            .member_labor_use
            .iter()
            .all(|r| r.accrued_wages == money(0)));
        assert_eq!(transition.household_time.len(), 1);
        assert_eq!(transition.household_time[0].attended_hours, 16);
        assert_eq!(transition.household_time[0].contribution_available_hours, 6);
    }
}

#[test]
fn zero_eligible_persons_can_retain_needs_without_invented_time() {
    let mut state = time_opening(2);
    for labor in &mut state.labor {
        labor.available = 0;
    }
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    for labor in &mut economy.member_labor {
        labor.available_hours = 0;
    }
    for attendance in &mut economy.recurring.as_mut().unwrap().attendance {
        attendance.planned_hours = 0;
    }
    let snapshot = economy.book.snapshot();
    economy.book = MonetaryBook::open(
        snapshot
            .accounts
            .into_iter()
            .map(|mut r| {
                r.cash = money(0);
                r
            })
            .collect(),
    )
    .unwrap();
    let costs = economy.costs.snapshot();
    economy.costs =
        HistoricalCostBook::open(&economy.book, costs.stocks, costs.freight, vec![], vec![])
            .unwrap();
    let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time else {
        unreachable!()
    };
    book.policies[0].eligible_persons = 0;
    let transition = advance_material_circuit(&state).unwrap();
    assert_eq!(transition.household_consumption[0].required_quantity, 4);
    assert_eq!(transition.household_consumption[0].unmet_quantity, 2);
    let row = &transition.household_time[0];
    assert_eq!(row.endowment_hours, 0);
    assert_eq!(row.attended_hours, 0);
    assert_eq!(row.protected_hours, 0);
    assert_eq!(row.protected_unresolved_hours, 4);
    assert_eq!(row.unpaid_allocated_hours, 0);
    assert_eq!(row.unpaid_unresolved_hours, 16);
    assert_eq!(row.contribution_available_hours, 0);
}

#[test]
fn persisted_unpaid_claim_cannot_exceed_all_captured_material_needs() {
    let mut state = advance_material_circuit(&time_opening(2)).unwrap().state;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time else {
        unreachable!()
    };
    let row = &mut book.receipts[0];
    // The local equation balances, but routine6 + maximum food4*5 is only26.
    row.unpaid_requested_hours = 27;
    row.unpaid_unresolved_hours = 15;
    assert_eq!(
        encode_material_circuit_state(&state),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
}

#[test]
fn nonworker_household_requires_an_admitted_hour_unit() {
    let mut state = time_opening(2);
    for row in &mut state.labor {
        row.available = 0;
    }
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    economy.employment.clear();
    economy.member_labor.clear();
    for row in &mut economy.recurring.as_mut().unwrap().attendance {
        row.planned_hours = 0;
    }
    let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time else {
        unreachable!()
    };
    book.policies[0].labor_unit_id = units();
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time else {
        unreachable!()
    };
    book.policies[0].labor_unit_id = hours();
    let closed = advance_material_circuit(&state).unwrap();
    assert_eq!(closed.household_time[0].attended_hours, 0);
    assert_eq!(closed.household_time[0].contribution_available_hours, 12);
}

#[test]
fn a_prior_period_contribution_cannot_be_replayed_after_rollover() {
    let mut state = advance_material_circuit(&time_opening(4)).unwrap().state;
    let usage = HouseholdContributionUse {
        use_id: [9; 32],
        principal_id: household(),
        actor_id: 11,
        contributor_id: 21,
        hours: 4,
    };
    consume_household_contributions(&mut state, 1, std::slice::from_ref(&usage)).unwrap();
    state = advance_material_circuit(&state).unwrap().state;
    let before = state.clone();
    assert_eq!(
        consume_household_contributions(&mut state, 1, &[usage]),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
    assert_eq!(state, before);
}
