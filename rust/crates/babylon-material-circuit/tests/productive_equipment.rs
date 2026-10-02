use babylon_kernel::currency::Currency;
use babylon_material_circuit::*;

include!("support/equipment_fixture.rs");

#[test]
fn arrived_equipment_and_materials_wait_for_actual_work_before_next_period_capacity() {
    let first = advance_material_circuit(&opening()).unwrap();
    assert_eq!(equipment(&first.state).pending[0].remaining_hours, 3);
    assert!(equipment(&first.state).cohorts.is_empty());
    assert_eq!(first.state.capacities[0].available_batches, 0);
    assert_eq!(equipment_cost(&first.state), money(26));
    let second = advance_material_circuit(&first.state).unwrap();
    assert_eq!(equipment(&second.state).pending[0].remaining_hours, 1);
    assert_eq!(equipment_cost(&second.state), money(30));
    assert_eq!(second.installation[0].used_hours, 2);
    assert_eq!(second.member_labor_use[0].installation_wages, money(4));
    let restored =
        decode_material_circuit_state(&encode_material_circuit_state(&second.state).unwrap())
            .unwrap();
    let third = advance_material_circuit(&second.state).unwrap();
    assert_eq!(third, advance_material_circuit(&restored).unwrap());
    assert_eq!(
        third
            .production
            .iter()
            .map(|r| r.produced_batches)
            .sum::<u64>(),
        0
    );
    assert!(equipment(&third.state).pending.is_empty());
    assert_eq!(equipment(&third.state).cohorts[0].usable_from_period, 4);
    assert_eq!(third.state.capacities[0].available_batches, 2);
    assert_eq!(equipment_cost(&third.state), money(32));
}

#[test]
fn actual_use_transfers_the_complete_carrying_remainder_to_unsold_output_without_cash_credit() {
    let mut state = opening();
    for _ in 0..3 {
        state = advance_material_circuit(&state).unwrap().state;
    }
    let fourth = advance_material_circuit(&state).unwrap();
    assert_eq!(fourth.production[0].produced_batches, 2);
    assert_eq!(fourth.equipment_wear[0].carried_to_output, money(21));
    assert_eq!(equipment_cost(&fourth.state), money(11));
    assert_eq!(stock_cost(&fourth.state, good(4)), money(29));
    let fifth = advance_material_circuit(&fourth.state).unwrap();
    assert_eq!(fifth.production[0].produced_batches, 1);
    assert_eq!(fifth.equipment_wear[0].carried_to_output, money(11));
    assert!(equipment(&fifth.state).cohorts.is_empty());
    assert_eq!(equipment_cost(&fifth.state), money(0));
    assert_eq!(stock_cost(&fifth.state, good(4)), money(44));
    assert_eq!(
        economy(&fifth.state)
            .book
            .cash(AccountId::Site(site()))
            .unwrap(),
        money(88)
    );
    assert_eq!(
        fifth
            .income
            .iter()
            .find(|r| r.account == AccountId::Site(site()))
            .unwrap()
            .net_income,
        money(0)
    );
}

#[test]
fn unpaid_owner_installation_performs_real_work_without_creating_wage_cost_or_ownership() {
    let mut state = opening();
    economy_mut(&mut state).employment[0].compensation = LaborCompensation::WorkingOwner;
    for _ in 0..3 {
        state = advance_material_circuit(&state).unwrap().state;
    }
    assert_eq!(equipment_cost(&state), money(26));
    assert_eq!(equipment(&state).cohorts[0].units, 1);
    assert_eq!(
        economy(&state)
            .book
            .cash(AccountId::Household(household()))
            .unwrap(),
        money(0)
    );
    assert!(economy(&state).financial.ownership.is_empty());
}

#[test]
fn missing_complements_and_hoarding_do_not_turn_stocked_equipment_into_capacity() {
    let mut missing = opening();
    missing
        .inventory
        .iter_mut()
        .find(|r| r.good_id == good(2))
        .unwrap()
        .quantity = 0;
    let mut snapshot = economy(&missing).costs.snapshot();
    snapshot
        .stocks
        .iter_mut()
        .find(|r| r.good_id == good(2))
        .unwrap()
        .amount = money(0);
    snapshot
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(site()))
        .unwrap()
        .opening_capital = money(126);
    economy_mut(&mut missing).costs = HistoricalCostBook::from_snapshot(snapshot).unwrap();
    let closed = advance_material_circuit(&missing).unwrap();
    assert!(equipment(&closed.state).pending.is_empty());
    assert_eq!(closed.state.capacities[0].available_batches, 0);
    let mut hoarded = opening();
    equipment_mut(&mut hoarded).installation_policies.clear();
    let closed = advance_material_circuit(&hoarded).unwrap();
    assert!(equipment(&closed.state).pending.is_empty());
    assert_eq!(
        closed
            .state
            .inventory
            .iter()
            .find(|r| r.good_id == good(1))
            .unwrap()
            .quantity,
        1
    );
    assert_eq!(closed.state.capacities[0].available_batches, 0);
}

#[test]
fn replacement_can_use_cash_at_a_loss_while_positive_retained_income_cannot_replace_missing_cash() {
    let mut loss = opening();
    configure_investment(&mut loss, 100, -10);
    let first = advance_material_circuit(&loss).unwrap();
    assert_eq!(first.investment[0].replacement_requested_units, 1);
    assert_eq!(first.investment[0].admitted_units, 1);
    assert_eq!(first.state.orders.len(), 1);
    assert_eq!(first.state.capacities[0].available_batches, 0);
    assert!(equipment(&first.state).cohorts.is_empty());
    assert_eq!(
        economy(&first.state)
            .book
            .cash(AccountId::Site(site()))
            .unwrap(),
        money(80)
    );
    let mut cash_poor = opening();
    configure_investment(&mut cash_poor, 0, 10);
    economy_mut(&mut cash_poor)
        .recurring
        .as_mut()
        .unwrap()
        .offers[0]
        .unit_price = money(5);
    equipment_mut(&mut cash_poor).investment_policies[0].replacement_target_units = 0;
    let closed = advance_material_circuit(&cash_poor).unwrap();
    assert_eq!(closed.investment[0].expansion_requested_units, 1);
    assert_eq!(closed.investment[0].admitted_units, 0);
    assert!(closed.state.orders.is_empty());
}

#[test]
fn funded_undelivered_equipment_is_not_repurchased_or_installed() {
    let mut state = opening();
    configure_investment(&mut state, 100, -10);
    let first = advance_material_circuit(&state).unwrap();
    let second = advance_material_circuit(&first.state).unwrap();
    assert_eq!(second.investment[0].outstanding_inbound_units, 1);
    assert_eq!(second.investment[0].admitted_units, 0);
    assert_eq!(second.state.freight.len(), 1);
    assert_eq!(second.state.capacities[0].available_batches, 0);
    assert!(equipment(&second.state).pending.is_empty());
    let bytes = encode_material_circuit_state(&second.state).unwrap();
    let restored = decode_material_circuit_state(&bytes).unwrap();
    assert_eq!(
        advance_material_circuit(&second.state).unwrap(),
        advance_material_circuit(&restored).unwrap()
    );
}

#[test]
fn inactive_managed_process_keeps_its_checked_binding_without_assets_or_policies() {
    let mut state = opening();
    equipment_mut(&mut state).installation_policies.clear();
    for row in &mut state.labor {
        row.available = 0;
    }
    let e = economy_mut(&mut state);
    for row in &mut e.member_labor {
        row.available_hours = 0;
    }
    let closed = advance_material_circuit(&state).unwrap();
    assert_eq!(equipment(&closed.state).bindings.len(), 1);
    assert!(equipment(&closed.state).cohorts.is_empty());
    assert!(equipment(&closed.state).pending.is_empty());
    assert_eq!(closed.state.capacities[0].available_batches, 0);
    assert!(closed.installation.is_empty());
}

#[test]
fn installation_overflow_after_attendance_discards_every_detached_change() {
    let mut state = opening();
    state.labor[0].available = 1;
    economy_mut(&mut state).member_labor[0].available_hours = 1;
    state
        .inventory
        .iter_mut()
        .find(|r| r.good_id == good(1))
        .unwrap()
        .quantity = 2;
    state
        .inventory
        .iter_mut()
        .find(|r| r.good_id == good(2))
        .unwrap()
        .quantity = 4;
    equipment_mut(&mut state).installation_policies[0].maximum_started_units_per_period = 2;
    equipment_mut(&mut state).definitions[0].installation_hours_per_unit = u64::MAX;
    let before = encode_material_circuit_state(&state).unwrap();
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(encode_material_circuit_state(&state).unwrap(), before);
    assert_eq!(
        economy(&state).book.cash(AccountId::Site(site())).unwrap(),
        money(100)
    );
}

#[test]
fn current_equipment_wire_refuses_previous_schema_and_inconsistent_physical_cost_owners() {
    let state = advance_material_circuit(&opening()).unwrap().state;
    let bytes = encode_material_circuit_state(&state).unwrap();
    let mut old = bytes.clone();
    let offset = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    old[offset..offset + 2].copy_from_slice(&13_u16.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&old),
        Err(MaterialCircuitError::WireVersion)
    );
    for length in [0, offset, bytes.len() / 2, bytes.len() - 1] {
        assert!(decode_material_circuit_state(&bytes[..length]).is_err());
    }
    let mut absent = state.clone();
    let mut book = economy(&absent).costs.snapshot();
    book.equipment.clear();
    economy_mut(&mut absent).costs = HistoricalCostBook::from_snapshot(book).unwrap();
    assert_eq!(
        encode_material_circuit_state(&absent),
        Err(MaterialCircuitError::ValuationInvariant)
    );
    let mut invalid = state;
    equipment_mut(&mut invalid).pending[0].remaining_hours = 0;
    assert_eq!(
        encode_material_circuit_state(&invalid),
        Err(MaterialCircuitError::EquipmentInvariant)
    );
}

fn staffed_equipment_close(
    state: &MaterialCircuitState,
    people: &StaffingState,
) -> (MaterialCircuitTransition, StaffingState) {
    let closed = close_material_period(state).unwrap();
    let bindings = people
        .pools()
        .iter()
        .map(|r| r.binding().clone())
        .collect::<Vec<_>>();
    let requests = closed.staffing_requests(&bindings).unwrap();
    let next = advance_staffing(people, &requests).unwrap();
    let members = next
        .next_labor()
        .iter()
        .map(|r| MemberLaborCapacityRow {
            member_id: StaffingMemberId::from_bytes([1; 32]),
            period: r.period,
            available_hours: r.available,
        })
        .collect();
    let result = closed
        .finish_with_workforce(next.next_labor().to_vec(), members)
        .unwrap();
    (result, next.state().clone())
}

#[test]
fn eighty_staffed_periods_preserve_unfinished_installation_after_horizon_and_exact_restart_cost() {
    let mut state = opening();
    state.labor.retain(|r| r.period == 1);
    let e = economy_mut(&mut state);
    e.member_labor.retain(|r| r.period == 1);
    e.employment[0].compensation = LaborCompensation::Wage(money(1));
    equipment_mut(&mut state).definitions[0].installation_hours_per_unit = 60;
    equipment_mut(&mut state).installation_policies[0].maximum_hours_per_period = 1;
    let binding = StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([1; 32]),
        site(),
        hours(),
        1,
        StaffingPolicy::one_period(1).unwrap(),
        vec![
            StaffingWorkSource::Production(process()),
            StaffingWorkSource::Installation(process()),
        ],
    )
    .unwrap();
    let mut people = StaffingState::try_new(
        1,
        vec![StaffingPoolState::try_new(binding, 0, 1, 0).unwrap()],
    )
    .unwrap();
    let mut fork = None;
    let mut installed_hours = 0;
    let mut paid_idle_hours = 0;
    let mut wear = money(0);
    for period in 1..=80 {
        if period == 52 {
            assert_eq!(state.capacities[0].available_batches, 0);
            assert_eq!(equipment(&state).pending[0].remaining_hours, 10);
            fork = Some((
                decode_material_circuit_state(&encode_material_circuit_state(&state).unwrap())
                    .unwrap(),
                people.clone(),
            ));
        }
        let (closed, next) = staffed_equipment_close(&state, &people);
        if let Some((restored, restored_people)) = &mut fork {
            let (replayed, replayed_people) = staffed_equipment_close(restored, restored_people);
            assert_eq!(closed, replayed, "period {period}");
            assert_eq!(next, replayed_people);
            *restored = replayed.state;
            *restored_people = replayed_people;
        }
        paid_idle_hours += closed
            .labor_use
            .iter()
            .map(|r| r.paid_idle_hours)
            .sum::<u64>();
        installed_hours += closed
            .installation
            .iter()
            .map(|r| r.used_hours)
            .sum::<u64>();
        for r in &closed.equipment_wear {
            wear = wear.checked_add(r.carried_to_output).unwrap();
        }
        state = closed.state;
        people = next;
    }
    assert_eq!(installed_hours, 60);
    // The captured next-period roster retains one paid idle hour as equipment exhausts.
    assert_eq!(paid_idle_hours, 1);
    assert_eq!(wear, money(86));
    assert!(equipment(&state).pending.is_empty());
    assert!(equipment(&state).cohorts.is_empty());
    assert_eq!(stock_cost(&state, good(4)), money(95));
    assert_eq!(
        economy(&state).book.cash(AccountId::Site(site())).unwrap(),
        money(36)
    );
    assert_eq!(
        economy(&state)
            .book
            .cash(AccountId::Household(household()))
            .unwrap(),
        money(64)
    );
    assert_eq!(
        people.pools()[0].employed() + people.pools()[0].reserve(),
        1
    );
}

#[test]
fn installed_capacity_cannot_replace_missing_inputs_or_avoid_paid_idle_loss() {
    let mut state = opening();
    state
        .inventory
        .iter_mut()
        .find(|r| r.good_id == good(3))
        .unwrap()
        .quantity = 0;
    let mut book = economy(&state).costs.snapshot();
    book.stocks
        .iter_mut()
        .find(|r| r.good_id == good(3))
        .unwrap()
        .amount = money(0);
    book.accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(site()))
        .unwrap()
        .opening_capital = money(126);
    economy_mut(&mut state).costs = HistoricalCostBook::from_snapshot(book).unwrap();
    for _ in 0..3 {
        state = advance_material_circuit(&state).unwrap().state;
    }
    assert_eq!(state.capacities[0].available_batches, 2);
    let closed = advance_material_circuit(&state).unwrap();
    assert_eq!(
        closed
            .production
            .iter()
            .map(|r| r.produced_batches)
            .sum::<u64>(),
        0
    );
    assert!(closed.equipment_wear.is_empty());
    assert_eq!(equipment_cost(&closed.state), money(32));
    let income = closed
        .income
        .iter()
        .find(|r| r.account == AccountId::Site(site()))
        .unwrap();
    assert_eq!(income.statement.idle_labor_expense, money(4));
    assert_eq!(income.net_income, money(-4));
}
