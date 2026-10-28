//! Independent finite-hour witnesses through the real recurring material close.
use babylon_material_circuit::decode_material_circuit_state;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::FundedShift;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdContributionUse;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_material_circuit::HouseholdTimeBook;
use babylon_material_circuit::HouseholdTimeCommitment;
use babylon_material_circuit::HouseholdTimePolicy;
use babylon_material_circuit::HouseholdUnmetTimeBurden;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::MoneyTransferPurpose;
use babylon_material_circuit::ShiftId;

fn time_opening(food: u64) -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = crate::opening();
    let mut catalog = catalog.into_definition();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the worked control must have monetary accounts");
    };
    let recurring = economy
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow");
    recurring.household_stocks[0].quantity = food;
    recurring.household_purchases[0].enabled = false;
    let policy = HouseholdTimePolicy {
        principal_id: crate::household(),
        labor_unit_id: crate::hours(),
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
            good_id: crate::good(2),
            unit_id: crate::units(),
            hours_per_unmet_unit: 5,
        }],
    };
    catalog.household_time_policy = vec![policy.clone()];
    economy.household_time = HouseholdTimeAccounting::Modeled(HouseholdTimeBook::default());
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    (catalog, state)
}

#[test]
fn actual_attendance_and_consumption_close_one_finite_household_time_account() {
    let (catalog, opening) = time_opening(4);
    let transition = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    assert_eq!(transition.household_time.len(), 1);
    let row = &transition.household_time[0];
    assert_eq!(row.principal_id, crate::household());
    assert_eq!(row.labor_unit_id, crate::hours());
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
    let (catalog, opening) = time_opening(2);
    let transition = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
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
    let (catalog, opening) = time_opening(4);
    let mut state = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period")
        .state;
    let before = state.clone();
    let uses = [
        HouseholdContributionUse {
            use_id: [1; 32],
            principal_id: crate::household(),
            actor_id: 11,
            contributor_id: 21,
            hours: 4,
        },
        HouseholdContributionUse {
            use_id: [2; 32],
            principal_id: crate::household(),
            actor_id: 12,
            contributor_id: 22,
            hours: 3,
        },
    ];
    assert_eq!(
        babylon_material_circuit::consume_household_contributions(&catalog, &mut state, 1, &uses),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
    assert_eq!(state, before);
    let one = &uses[..1];
    let receipt =
        babylon_material_circuit::consume_household_contributions(&catalog, &mut state, 1, one)
            .expect("the fixture consumes the authored contributions");
    let unchanged = state.clone();
    assert_eq!(
        babylon_material_circuit::consume_household_contributions(&catalog, &mut state, 1, one)
            .expect("the fixture consumes the authored contributions"),
        receipt
    );
    assert_eq!(state, unchanged);
    let mut conflicting = uses[0].clone();
    conflicting.hours = 3;
    assert_eq!(
        babylon_material_circuit::consume_household_contributions(
            &catalog,
            &mut state,
            1,
            &[conflicting]
        ),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
    assert_eq!(state, unchanged);
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    assert_eq!(
        decode_material_circuit_state(&catalog, &bytes)
            .expect("the canonical material bytes decode"),
        state
    );
}

#[test]
fn time_endowments_refuse_population_overrun_unaccounted_attendance_and_wrong_units() {
    for invalid in [0, 5] {
        let (catalog, state) = time_opening(4);
        let mut definition = catalog.into_definition();
        definition.household_time_policy[0].eligible_persons = invalid;
        let catalog = MaterialCatalog::try_new(definition).expect("valid definition");
        assert_eq!(
            babylon_material_circuit::advance_material_circuit(&catalog, &state),
            Err(MaterialCircuitError::HouseholdTimeInvariant)
        );
    }
    let (catalog, state) = time_opening(4);
    let mut definition = catalog.into_definition();
    definition.household_time_policy[0].labor_unit_id = crate::units();
    let catalog = MaterialCatalog::try_new(definition).expect("valid definition");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
}

#[test]
fn missing_wage_funding_preserves_needs_and_finite_household_obligations() {
    let (catalog, mut state) = time_opening(2);
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
                r.cash = crate::money(0);
                r
            })
            .collect(),
    )
    .expect("the fixture opens the authored source");
    let costs = economy.costs.snapshot();
    economy.costs =
        HistoricalCostBook::open(&economy.book, costs.stocks, costs.freight, vec![], vec![])
            .expect("the fixture opens the authored source");
    let transition = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
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
    let (catalog, opening) = time_opening(4);
    let mut state = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period")
        .state;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let shift = ShiftId::from_bytes([97; 32]);
    economy
        .book
        .reserve_shift(
            FundedShift::new(
                shift,
                AccountId::Site(crate::site(3)),
                AccountId::Household(crate::household()),
                1,
                2,
                crate::money(1),
            )
            .expect("the constructor accepts the authored fixture arguments"),
        )
        .expect("the fixture shift reservation fits");
    economy
        .book
        .accrue_shift(shift)
        .expect("the fixture accrues the authored shift");
    let costs = economy.costs.snapshot();
    // The controlled continuation captures its existing claim and liability unchanged.
    economy.costs =
        HistoricalCostBook::open(&economy.book, costs.stocks, costs.freight, vec![], vec![])
            .expect("the fixture opens the authored source");
    let transition = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
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
        let (catalog, mut state) = time_opening(4);
        let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
            unreachable!()
        };
        for term in &mut economy.employment {
            term.compensation = compensation;
        }
        let transition = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period");
        assert_eq!(transition.wage_accruals.len(), 0);
        assert!(transition.member_labor_use.iter().any(|r| r.idle_hours > 0));
        assert!(transition
            .member_labor_use
            .iter()
            .all(|r| r.accrued_wages == crate::money(0)));
        assert_eq!(transition.household_time.len(), 1);
        assert_eq!(transition.household_time[0].attended_hours, 16);
        assert_eq!(transition.household_time[0].contribution_available_hours, 6);
    }
}

#[test]
fn zero_eligible_persons_can_retain_needs_without_invented_time() {
    let (catalog, mut state) = time_opening(2);
    for labor in &mut state.labor {
        labor.available = 0;
    }
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    for labor in &mut economy.member_labor {
        labor.available_hours = 0;
    }
    for attendance in &mut economy
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .attendance
    {
        attendance.planned_hours = 0;
    }
    let snapshot = economy.book.snapshot();
    economy.book = MonetaryBook::open(
        snapshot
            .accounts
            .into_iter()
            .map(|mut r| {
                r.cash = crate::money(0);
                r
            })
            .collect(),
    )
    .expect("the fixture opens the authored source");
    let costs = economy.costs.snapshot();
    economy.costs =
        HistoricalCostBook::open(&economy.book, costs.stocks, costs.freight, vec![], vec![])
            .expect("the fixture opens the authored source");
    let mut definition = catalog.into_definition();
    definition.household_time_policy[0].eligible_persons = 0;
    let catalog = MaterialCatalog::try_new(definition).expect("valid definition");
    let transition = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
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
    let (catalog, opening) = time_opening(4);
    let mut state = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period")
        .state;
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
        babylon_material_circuit::encode_material_circuit_state(&catalog, &state),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
}

#[test]
fn nonworker_household_requires_an_admitted_hour_unit() {
    let (catalog, mut state) = time_opening(2);
    for row in &mut state.labor {
        row.available = 0;
    }
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    economy.employment.clear();
    economy.member_labor.clear();
    for row in &mut economy
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .attendance
    {
        row.planned_hours = 0;
    }
    let mut definition = catalog.clone().into_definition();
    definition.household_time_policy[0].labor_unit_id = crate::units();
    let invalid_catalog = MaterialCatalog::try_new(definition).expect("valid definition");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&invalid_catalog, &state),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(closed.household_time[0].attended_hours, 0);
    assert_eq!(closed.household_time[0].contribution_available_hours, 12);
}

#[test]
fn a_prior_period_contribution_cannot_be_replayed_after_rollover() {
    let (catalog, opening) = time_opening(4);
    let mut state = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period")
        .state;
    let usage = HouseholdContributionUse {
        use_id: [9; 32],
        principal_id: crate::household(),
        actor_id: 11,
        contributor_id: 21,
        hours: 4,
    };
    babylon_material_circuit::consume_household_contributions(
        &catalog,
        &mut state,
        1,
        std::slice::from_ref(&usage),
    )
    .expect("the fixture consumes the authored contributions");
    state = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period")
        .state;
    let before = state.clone();
    assert_eq!(
        babylon_material_circuit::consume_household_contributions(
            &catalog,
            &mut state,
            1,
            &[usage]
        ),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
    assert_eq!(state, before);
}

#[test]
fn authored_time_policy_is_canonical_and_refuses_invalid_definitions() {
    let (catalog, _) = time_opening(4);
    let mut definition = catalog.clone().into_definition();
    let second = HouseholdUnmetTimeBurden {
        good_id: crate::good(1),
        unit_id: crate::units(),
        hours_per_unmet_unit: 2,
    };
    definition.household_time_policy[0]
        .unmet_burdens
        .push(second);
    let admitted = MaterialCatalog::try_new(definition.clone()).expect("valid authored policies");
    definition.household_time_policy[0].unmet_burdens.reverse();
    assert_eq!(
        admitted,
        MaterialCatalog::try_new(definition.clone()).expect("same policy")
    );
    definition.household_time_policy[0].unmet_burdens[0].hours_per_unmet_unit = 0;
    assert_eq!(
        MaterialCatalog::try_new(definition),
        Err(MaterialCircuitError::HouseholdTimeInvariant)
    );
    let mut overflow = catalog.into_definition();
    overflow.household_time_policy[0].eligible_persons = u64::MAX;
    assert_eq!(
        MaterialCatalog::try_new(overflow),
        Err(MaterialCircuitError::Arithmetic)
    );
}

#[test]
fn unmodeled_and_physical_accounts_refuse_authored_time_policies() {
    let (catalog, mut monetary) = time_opening(4);
    let CircuitAccounting::Monetary(economy) = &mut monetary.accounting else {
        unreachable!()
    };
    economy.household_time = HouseholdTimeAccounting::NotModeled;
    let mut physical = monetary.clone();
    physical.accounting = CircuitAccounting::PhysicalControl;
    let errors: Vec<_> = [&monetary, &physical]
        .into_iter()
        .map(|state| babylon_material_circuit::encode_material_circuit_state(&catalog, state).err())
        .collect();
    assert_eq!(
        errors,
        vec![Some(MaterialCircuitError::HouseholdTimeInvariant); 2]
    );
    for state in [&monetary, &physical] {
        assert_eq!(
            babylon_material_circuit::advance_material_circuit(&catalog, state).err(),
            Some(MaterialCircuitError::HouseholdTimeInvariant)
        );
        assert_eq!(
            babylon_material_circuit::close_material_period(&catalog, state).err(),
            Some(MaterialCircuitError::HouseholdTimeInvariant)
        );
    }
    let mut definition = catalog.into_definition();
    definition.household_time_policy.clear();
    let empty = MaterialCatalog::try_new(definition).expect("empty time definition is valid");
    assert!(babylon_material_circuit::encode_material_circuit_state(&empty, &monetary).is_ok());
    let mut physical_definition = empty.into_definition();
    physical_definition.household_needs.clear();
    let physical_catalog =
        MaterialCatalog::try_new(physical_definition).expect("empty policies are valid");
    assert!(
        babylon_material_circuit::encode_material_circuit_state(&physical_catalog, &physical)
            .is_ok()
    );
}

#[test]
fn inactive_recurring_modes_refuse_authored_needs() {
    let (catalog, mut missing) = crate::opening();
    let CircuitAccounting::Monetary(economy) = &mut missing.accounting else {
        unreachable!()
    };
    economy.recurring = None;
    let mut physical = missing.clone();
    physical.accounting = CircuitAccounting::PhysicalControl;
    for state in [&missing, &physical] {
        assert_eq!(
            babylon_material_circuit::encode_material_circuit_state(&catalog, state).err(),
            Some(MaterialCircuitError::PurchaseInvariant)
        );
        assert_eq!(
            babylon_material_circuit::close_material_period(&catalog, state).err(),
            Some(MaterialCircuitError::PurchaseInvariant)
        );
    }
}
