use babylon_kernel::currency::Currency;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::AidBook;
use babylon_material_circuit::AttendancePlan;
use babylon_material_circuit::CapacityRow;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::CommodityDefinition;
use babylon_material_circuit::CommodityKind;
use babylon_material_circuit::CorridorCapacity;
use babylon_material_circuit::CorridorId;
use babylon_material_circuit::EmploymentTerms;
use babylon_material_circuit::EquipmentBinding;
use babylon_material_circuit::EquipmentDefinition;
use babylon_material_circuit::EquipmentDefinitionId;
use babylon_material_circuit::FinalDemandPrincipal;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::FinancialInstitutions;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::GoodsPriceCostBasis;
use babylon_material_circuit::GoodsPriceCostEvidence;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::InputOutputCoefficient;
use babylon_material_circuit::InstallationInput;
use babylon_material_circuit::InstallationPolicy;
use babylon_material_circuit::InstallationTarget;
use babylon_material_circuit::InventoryRow;
use babylon_material_circuit::InvestmentPolicy;
use babylon_material_circuit::LaborCapacityRow;
use babylon_material_circuit::LaborCoefficient;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::LogisticsNodeId;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialCircuitTransition;
use babylon_material_circuit::MemberLaborCapacityRow;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::MonetaryCircuit;
use babylon_material_circuit::PriceDecision;
use babylon_material_circuit::PricePolicy;
use babylon_material_circuit::ProcessId;
use babylon_material_circuit::ProcessOutput;
use babylon_material_circuit::ProductionDemandPolicy;
use babylon_material_circuit::ProductiveEquipment;
use babylon_material_circuit::RecurringEconomy;
use babylon_material_circuit::RollingCapacitySupply;
use babylon_material_circuit::RollingProcessSupply;
use babylon_material_circuit::RouteId;
use babylon_material_circuit::RouteStage;
use babylon_material_circuit::RouteStageCapacity;
use babylon_material_circuit::SellerOffer;
use babylon_material_circuit::SharedCapacitySupply;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::SiteLogisticsNode;
use babylon_material_circuit::StaffingMemberId;
use babylon_material_circuit::StaffingPolicy;
use babylon_material_circuit::StaffingPoolBinding;
use babylon_material_circuit::StaffingPoolId;
use babylon_material_circuit::StaffingPoolState;
use babylon_material_circuit::StaffingState;
use babylon_material_circuit::StaffingWorkSource;
use babylon_material_circuit::StockCarryingValue;
use babylon_material_circuit::SupplierRoute;
use babylon_material_circuit::SupplierTransport;
use babylon_material_circuit::UnitId;
use babylon_material_circuit::MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES;

include!("support/equipment_fixture.rs");

#[test]
fn arrived_equipment_and_materials_wait_for_actual_work_before_next_period_capacity() {
    let (catalog, opening) = opening();
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    assert_eq!(position(&first.state).pending[0].remaining_hours, 3);
    assert_eq!(position(&first.state).cohorts.len(), 0);
    assert_eq!(first.state.capacities[0].available_batches, 0);
    assert_eq!(equipment_cost(&first.state), money(26));
    let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("the authored material state advances one period");
    assert_eq!(position(&second.state).pending[0].remaining_hours, 1);
    assert_eq!(equipment_cost(&second.state), money(30));
    assert_eq!(second.installation[0].used_hours, 2);
    assert_eq!(second.member_labor_use[0].installation_wages, money(4));
    let restored = babylon_material_circuit::decode_material_circuit_state(
        &catalog,
        &babylon_material_circuit::encode_material_circuit_state(&catalog, &second.state)
            .expect("the canonical material state encodes"),
    )
    .expect("the canonical material bytes decode");
    let third = babylon_material_circuit::advance_material_circuit(&catalog, &second.state)
        .expect("the authored material state advances one period");
    assert_eq!(
        third,
        babylon_material_circuit::advance_material_circuit(&catalog, &restored)
            .expect("the authored material state advances one period")
    );
    assert_eq!(
        third
            .production
            .iter()
            .map(|r| r.produced_batches)
            .sum::<u64>(),
        0
    );
    assert_eq!(position(&third.state).pending.len(), 0);
    assert_eq!(position(&third.state).cohorts[0].usable_from_period, 4);
    assert_eq!(third.state.capacities[0].available_batches, 2);
    assert_eq!(equipment_cost(&third.state), money(32));
}

#[test]
fn actual_use_transfers_the_complete_carrying_remainder_to_unsold_output_without_cash_credit() {
    let (catalog, mut state) = opening();
    for _ in 0..3 {
        state = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period")
            .state;
    }
    let fourth = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(fourth.production[0].produced_batches, 2);
    assert_eq!(fourth.equipment_wear[0].carried_to_output, money(21));
    assert_eq!(equipment_cost(&fourth.state), money(11));
    assert_eq!(stock_cost(&fourth.state, good(4)), money(29));
    let fifth = babylon_material_circuit::advance_material_circuit(&catalog, &fourth.state)
        .expect("the authored material state advances one period");
    assert_eq!(fifth.production[0].produced_batches, 1);
    assert_eq!(fifth.equipment_wear[0].carried_to_output, money(11));
    assert_eq!(position(&fifth.state).cohorts.len(), 0);
    assert_eq!(equipment_cost(&fifth.state), money(0));
    assert_eq!(stock_cost(&fifth.state, good(4)), money(44));
    assert_eq!(
        economy(&fifth.state)
            .book
            .cash(AccountId::Site(site()))
            .expect("the fixture book holds the payer account"),
        money(88)
    );
    assert_eq!(
        fifth
            .income
            .iter()
            .find(|r| r.account == AccountId::Site(site()))
            .expect("the fixture holds the searched element")
            .net_income,
        money(0)
    );
}

#[test]
fn unpaid_owner_installation_performs_real_work_without_creating_wage_cost_or_ownership() {
    let (catalog, mut state) = opening();
    economy_mut(&mut state).employment[0].compensation = LaborCompensation::WorkingOwner;
    for _ in 0..3 {
        state = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period")
            .state;
    }
    assert_eq!(equipment_cost(&state), money(26));
    assert_eq!(position(&state).cohorts[0].units, 1);
    assert_eq!(
        economy(&state)
            .book
            .cash(AccountId::Household(household()))
            .expect("the fixture book holds the payer account"),
        money(0)
    );
    assert_eq!(economy(&state).financial.ownership.len(), 0);
}

#[test]
fn missing_complements_and_hoarding_do_not_turn_stocked_equipment_into_capacity() {
    let (catalog, mut missing) = opening();
    missing
        .inventory
        .iter_mut()
        .find(|r| r.good_id == good(2))
        .expect("the fixture holds the searched element")
        .quantity = 0;
    let mut snapshot = economy(&missing).costs.snapshot();
    snapshot
        .stocks
        .iter_mut()
        .find(|r| r.good_id == good(2))
        .expect("the fixture holds the searched element")
        .amount = money(0);
    snapshot
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(site()))
        .expect("the fixture holds the searched element")
        .opening_capital = money(126);
    economy_mut(&mut missing).costs =
        HistoricalCostBook::from_snapshot(snapshot).expect("the snapshot admits the derived value");
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &missing)
        .expect("the authored material state advances one period");
    assert_eq!(position(&closed.state).pending.len(), 0);
    assert_eq!(closed.state.capacities[0].available_batches, 0);
    let (catalog, hoarded) = opening();
    let hoarded_catalog = rebuild(&catalog, |content| content.installation_policies.clear());
    let closed = babylon_material_circuit::advance_material_circuit(&hoarded_catalog, &hoarded)
        .expect("the authored material state advances one period");
    assert_eq!(position(&closed.state).pending.len(), 0);
    assert_eq!(
        closed
            .state
            .inventory
            .iter()
            .find(|r| r.good_id == good(1))
            .expect("the fixture holds the searched element")
            .quantity,
        1
    );
    assert_eq!(closed.state.capacities[0].available_batches, 0);
}

#[test]
fn replacement_can_use_cash_at_a_loss_while_positive_retained_income_cannot_replace_missing_cash() {
    let (mut catalog, mut loss) = opening();
    configure_investment(&mut catalog, &mut loss, 100, -10);
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &loss)
        .expect("the authored material state advances one period");
    assert_eq!(first.investment[0].replacement_requested_units, 1);
    assert_eq!(first.investment[0].admitted_units, 1);
    assert_eq!(first.state.orders.len(), 1);
    assert_eq!(first.state.capacities[0].available_batches, 0);
    assert_eq!(position(&first.state).cohorts.len(), 0);
    assert_eq!(
        economy(&first.state)
            .book
            .cash(AccountId::Site(site()))
            .expect("the fixture book holds the payer account"),
        money(80)
    );
    let (mut catalog, mut cash_poor) = opening();
    configure_investment(&mut catalog, &mut cash_poor, 0, 10);
    economy_mut(&mut cash_poor)
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .offers[0]
        .unit_price = money(5);
    catalog = rebuild(&catalog, |content| {
        content.investment_policies[0].replacement_target_units = 0;
    });
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &cash_poor)
        .expect("the authored material state advances one period");
    assert_eq!(closed.investment[0].expansion_requested_units, 1);
    assert_eq!(closed.investment[0].admitted_units, 0);
    assert_eq!(closed.state.orders.len(), 0);
}

#[test]
fn funded_undelivered_equipment_is_not_repurchased_or_installed() {
    let (mut catalog, mut state) = opening();
    configure_investment(&mut catalog, &mut state, 100, -10);
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("the authored material state advances one period");
    assert_eq!(second.investment[0].outstanding_inbound_units, 1);
    assert_eq!(second.investment[0].admitted_units, 0);
    assert_eq!(second.state.freight.len(), 1);
    assert_eq!(second.state.capacities[0].available_batches, 0);
    assert_eq!(position(&second.state).pending.len(), 0);
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &second.state)
        .expect("the canonical material state encodes");
    let restored = babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
        .expect("the canonical material bytes decode");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &second.state)
            .expect("the authored material state advances one period"),
        babylon_material_circuit::advance_material_circuit(&catalog, &restored)
            .expect("the authored material state advances one period")
    );
}

#[test]
fn inactive_managed_process_keeps_its_checked_binding_without_assets_or_policies() {
    let (mut catalog, mut state) = opening();
    catalog = rebuild(&catalog, |content| content.installation_policies.clear());
    for row in &mut state.labor {
        row.available = 0;
    }
    let e = economy_mut(&mut state);
    for row in &mut e.member_labor {
        row.available_hours = 0;
    }
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(equipment(&catalog).bindings.len(), 1);
    assert_eq!(position(&closed.state).cohorts.len(), 0);
    assert_eq!(position(&closed.state).pending.len(), 0);
    assert_eq!(closed.state.capacities[0].available_batches, 0);
    assert_eq!(closed.installation.len(), 0);
}

#[test]
fn installation_overflow_after_attendance_discards_every_detached_change() {
    let (mut catalog, mut state) = opening();
    state.labor[0].available = 1;
    economy_mut(&mut state).member_labor[0].available_hours = 1;
    state
        .inventory
        .iter_mut()
        .find(|r| r.good_id == good(1))
        .expect("the fixture holds the searched element")
        .quantity = 2;
    state
        .inventory
        .iter_mut()
        .find(|r| r.good_id == good(2))
        .expect("the fixture holds the searched element")
        .quantity = 4;
    catalog = rebuild(&catalog, |content| {
        content.installation_policies[0].maximum_started_units_per_period = 2;
        content.installation_policies[0].target = InstallationTarget::FixedUnits(2);
        content.definitions[0].installation_hours_per_unit = u64::MAX;
    });
    let before = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes"),
        before
    );
    assert_eq!(
        economy(&state)
            .book
            .cash(AccountId::Site(site()))
            .expect("the fixture book holds the payer account"),
        money(100)
    );
}

#[test]
fn current_equipment_wire_refuses_previous_schema_and_inconsistent_physical_cost_owners() {
    let (catalog, opening) = opening();
    let state = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period")
        .state;
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    let mut old = bytes.clone();
    let offset = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    old[offset..offset + 2].copy_from_slice(&14_u16.to_be_bytes());
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &old),
        Err(MaterialCircuitError::WireVersion)
    );
    for length in [0, offset, bytes.len() / 2, bytes.len() - 1] {
        assert!(babylon_material_circuit::decode_material_circuit_state(
            &catalog,
            &bytes[..length]
        )
        .is_err());
    }
    let mut absent = state.clone();
    let mut book = economy(&absent).costs.snapshot();
    book.equipment.clear();
    economy_mut(&mut absent).costs =
        HistoricalCostBook::from_snapshot(book).expect("the snapshot admits the derived value");
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &absent),
        Err(MaterialCircuitError::ValuationInvariant)
    );
    let mut invalid = state;
    position_mut(&mut invalid).pending[0].remaining_hours = 0;
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &invalid),
        Err(MaterialCircuitError::EquipmentInvariant)
    );
}

fn staffed_equipment_close(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    people: &StaffingState,
) -> (MaterialCircuitTransition, StaffingState) {
    let closed = babylon_material_circuit::close_material_period(catalog, state)
        .expect("the material period closes");
    let bindings = people
        .pools()
        .iter()
        .map(|r| r.binding().clone())
        .collect::<Vec<_>>();
    let requests = closed
        .staffing_requests(catalog, &bindings)
        .expect("the fixture staffing requests are present");
    let next = babylon_material_circuit::advance_staffing(people, &requests)
        .expect("the fixture staffing advances");
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
        .finish_with_workforce(catalog, next.next_labor().to_vec(), members)
        .expect("the fixture call `finish_with_workforce` succeeds for the authored inputs");
    (result, next.state().clone())
}

#[test]
fn eighty_staffed_periods_preserve_unfinished_installation_after_horizon_and_exact_restart_cost() {
    let (mut catalog, mut state) = opening();
    state.labor.retain(|r| r.period == 1);
    let e = economy_mut(&mut state);
    e.member_labor.retain(|r| r.period == 1);
    e.employment[0].compensation = LaborCompensation::Wage(money(1));
    catalog = rebuild(&catalog, |content| {
        content.definitions[0].installation_hours_per_unit = 60;
        content.installation_policies[0].maximum_hours_per_period = 1;
    });
    let binding = StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([1; 32]),
        site(),
        hours(),
        1,
        StaffingPolicy::one_period(1).expect("the one-period fixture advances"),
        vec![
            StaffingWorkSource::Production(process()),
            StaffingWorkSource::Installation(process()),
        ],
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let mut people = StaffingState::try_new(
        1,
        vec![StaffingPoolState::try_new(binding, 0, 1, 0)
            .expect("the authored fixture satisfies the constructor invariants")],
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let mut fork = None;
    let mut installed_hours = 0;
    let mut paid_idle_hours = 0;
    let mut wear = money(0);
    for period in 1..=80 {
        if period == 52 {
            assert_eq!(state.capacities[0].available_batches, 0);
            assert_eq!(position(&state).pending[0].remaining_hours, 10);
            fork = Some((
                babylon_material_circuit::decode_material_circuit_state(
                    &catalog,
                    &babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
                        .expect("the canonical material state encodes"),
                )
                .expect("the canonical material bytes decode"),
                people.clone(),
            ));
        }
        let (closed, next) = staffed_equipment_close(&catalog, &state, &people);
        if let Some((restored, restored_people)) = &mut fork {
            let (replayed, replayed_people) =
                staffed_equipment_close(&catalog, restored, restored_people);
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
            wear = wear
                .checked_add(r.carried_to_output)
                .expect("the fixture arithmetic stays in range");
        }
        state = closed.state;
        people = next;
    }
    assert_eq!(installed_hours, 60);
    // The captured next-period roster retains one paid idle hour as equipment exhausts.
    assert_eq!(paid_idle_hours, 1);
    assert_eq!(wear, money(86));
    assert_eq!(position(&state).pending.len(), 0);
    assert_eq!(position(&state).cohorts.len(), 0);
    assert_eq!(stock_cost(&state, good(4)), money(95));
    assert_eq!(
        economy(&state)
            .book
            .cash(AccountId::Site(site()))
            .expect("the fixture book holds the payer account"),
        money(36)
    );
    assert_eq!(
        economy(&state)
            .book
            .cash(AccountId::Household(household()))
            .expect("the fixture book holds the payer account"),
        money(64)
    );
    assert_eq!(
        people.pools()[0].employed() + people.pools()[0].reserve(),
        1
    );
}

#[test]
fn installed_capacity_cannot_replace_missing_inputs_or_avoid_paid_idle_loss() {
    let (catalog, mut state) = opening();
    state
        .inventory
        .iter_mut()
        .find(|r| r.good_id == good(3))
        .expect("the fixture holds the searched element")
        .quantity = 0;
    let mut book = economy(&state).costs.snapshot();
    book.stocks
        .iter_mut()
        .find(|r| r.good_id == good(3))
        .expect("the fixture holds the searched element")
        .amount = money(0);
    book.accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(site()))
        .expect("the fixture holds the searched element")
        .opening_capital = money(126);
    economy_mut(&mut state).costs =
        HistoricalCostBook::from_snapshot(book).expect("the snapshot admits the derived value");
    for _ in 0..3 {
        state = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period")
            .state;
    }
    assert_eq!(state.capacities[0].available_batches, 2);
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(
        closed
            .production
            .iter()
            .map(|r| r.produced_batches)
            .sum::<u64>(),
        0
    );
    assert_eq!(closed.equipment_wear.len(), 0);
    assert_eq!(equipment_cost(&closed.state), money(32));
    let income = closed
        .income
        .iter()
        .find(|r| r.account == AccountId::Site(site()))
        .expect("the fixture holds the searched element");
    assert_eq!(income.statement.idle_labor_expense, money(4));
    assert_eq!(income.net_income, money(-4));
}

#[test]
fn goods_cost_actual_wear_inputs_and_wages_are_one_produced_basis_without_revaluation() {
    let (catalog, mut state) = opening();
    for _ in 0..3 {
        state = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period")
            .state;
    }
    configure_output_quote(&mut state);
    let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let row = &result.prices[0];
    assert_eq!(
        row.cost,
        GoodsPriceCostEvidence {
            basis: GoodsPriceCostBasis::Produced,
            quantity: 2,
            carrying_cost: money(29),
            handling_wages: money(0),
        }
    ); // Four inputs + four productive wages +21 wear.
    assert_eq!(
        (row.reason, row.next_price),
        (PriceDecision::CostPressure, money(4))
    );
    assert_eq!(stock_cost(&result.state, good(4)), money(29));
    assert_eq!(equipment_cost(&result.state), money(11));
    let restored = babylon_material_circuit::decode_material_circuit_state(
        &catalog,
        &babylon_material_circuit::encode_material_circuit_state(&catalog, &result.state)
            .expect("the canonical material state encodes"),
    )
    .expect("the canonical material bytes decode");
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &result.state)
            .expect("the authored material state advances one period"),
        babylon_material_circuit::advance_material_circuit(&catalog, &restored)
            .expect("the authored material state advances one period")
    );
}

#[path = "support/equipment_choice.rs"]
mod equipment_choice;
