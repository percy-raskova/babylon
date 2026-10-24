use crate::equipment;
use crate::equipment_cost;
use crate::household;
use crate::stock_cost;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::BacklogRow;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CorridorId;
use babylon_material_circuit::EquipmentAssetId;
use babylon_material_circuit::EquipmentCarryingValue;
use babylon_material_circuit::EquipmentCohortId;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::InstallationTarget;
use babylon_material_circuit::InstalledEquipmentCohort;
use babylon_material_circuit::InvestmentPolicy;
use babylon_material_circuit::LogisticsNodeId;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::OrderAccessMode;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::OrderRow;
use babylon_material_circuit::OutboundOrderId;
use babylon_material_circuit::PurchaseEscrow;
use babylon_material_circuit::RouteId;
use babylon_material_circuit::RouteStage;
use babylon_material_circuit::RouteStageCapacity;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::StaffingPolicy;
use babylon_material_circuit::StaffingPoolBinding;
use babylon_material_circuit::StaffingPoolId;
use babylon_material_circuit::StaffingWorkSource;
use babylon_material_circuit::SupplierRoute;
use babylon_material_circuit::SupplierTransport;

fn pledged_opening() -> MaterialCircuitState {
    let mut state = crate::opening();
    crate::configure_investment(&mut state, 100, 0);
    crate::equipment_mut(&mut state).investment_policies.clear();
    state
        .inventory
        .iter_mut()
        .find(|r| r.site_id == crate::site() && r.good_id == crate::good(1))
        .unwrap()
        .quantity = 1;
    let buyer = SiteId::from_bytes([2; 32]);
    state.supplier_routes[0].buyer_site_id = buyer;
    state.supplier_routes[0].supplier_site_id = crate::site();
    state.route_stages[0].from_node_id = LogisticsNodeId::from_bytes([1; 32]);
    state.route_stages[0].to_node_id = LogisticsNodeId::from_bytes([2; 32]);
    let id = OrderId::from_bytes([3; 32]);
    let mut book = MonetaryBook::open(vec![
        CashAccount {
            id: AccountId::Site(crate::site()),
            cash: crate::money(100),
        },
        CashAccount {
            id: AccountId::Site(buyer),
            cash: crate::money(100),
        },
        CashAccount {
            id: AccountId::Household(household()),
            cash: crate::money(0),
        },
    ])
    .unwrap();
    book.reserve_purchase(
        PurchaseEscrow::new(
            OutboundOrderId::Delivery(id),
            AccountId::Site(buyer),
            AccountId::Site(crate::site()),
            1,
            crate::money(20),
        )
        .unwrap(),
    )
    .unwrap();
    let mut stocks = crate::economy(&state).costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| r.owner == AccountId::Site(crate::site()) && r.good_id == crate::good(1))
        .unwrap()
        .amount = crate::money(20);
    let costs = HistoricalCostBook::open(&book, stocks, vec![], vec![], vec![]).unwrap();
    crate::economy_mut(&mut state).book = book;
    crate::economy_mut(&mut state).costs = costs;
    state.orders.push(OrderRow {
        order_id: id,
        access_mode: OrderAccessMode::CommoditySale,
        buyer_site_id: buyer,
        supplier_site_id: crate::site(),
        good_id: crate::good(1),
        unit_id: crate::unit(),
        ordered: 1,
        shipped: 0,
        lost: 0,
        delivered: 0,
        realized: 0,
    });
    state.backlog.push(BacklogRow {
        order_id: id,
        quantity: 1,
    });
    state
}

#[test]
fn installation_choice_preserves_owned_equipment_pledged_to_a_paid_buyer() {
    let state = pledged_opening();
    let closed = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    assert!(
        equipment(&closed.state).pending.is_empty(),
        "sale inventory must not become WIP"
    );
    assert!(closed.installation.is_empty());
    assert_eq!(closed.dispatches.iter().map(|r| r.quantity).sum::<u64>(), 1);
    assert_eq!(closed.state.freight.len(), 1);
    assert_eq!(stock_cost(&closed.state, crate::good(2)), crate::money(6));
}

#[test]
fn installation_choice_does_not_expand_a_process_already_at_its_captured_target() {
    let mut state = crate::opening();
    let id = EquipmentCohortId::from_bytes([20; 32]);
    crate::equipment_mut(&mut state)
        .cohorts
        .push(InstalledEquipmentCohort {
            id,
            process_id: crate::process(),
            units: 1,
            remaining_service_batches: 3,
            usable_from_period: 1,
        });
    state.capacities[0].available_batches = 2;
    let mut snapshot = crate::economy(&state).costs.snapshot();
    snapshot.equipment.push(EquipmentCarryingValue {
        asset: EquipmentAssetId::Installed(id),
        owner: crate::site(),
        amount: crate::money(10),
    });
    snapshot
        .accounts
        .iter_mut()
        .find(|r| r.account == AccountId::Site(crate::site()))
        .unwrap()
        .opening_capital = crate::money(142);
    crate::economy_mut(&mut state).costs = HistoricalCostBook::from_snapshot(snapshot).unwrap();
    let closed = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    assert!(
        equipment(&closed.state).pending.is_empty(),
        "owned spare stock is not automatic expansion"
    );
    assert_eq!(equipment(&closed.state).cohorts.len(), 1);
    assert_eq!(stock_cost(&closed.state, crate::good(1)), crate::money(20));
}

#[test]
fn installation_choice_lowered_target_keeps_existing_wip_and_exact_restart() {
    let first = babylon_material_circuit::advance_material_circuit(&crate::opening()).unwrap();
    let mut state = first.state;
    crate::equipment_mut(&mut state).installation_policies[0].target =
        InstallationTarget::FixedUnits(0);
    let second = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    assert_eq!(second.installation_decisions[0].target_units, 0);
    assert_eq!(second.installation_decisions[0].pending_units, 1);
    assert_eq!(second.installation_decisions[0].requested_units, 0);
    assert_eq!(second.installation_decisions[0].started_units, 0);
    assert_eq!(second.installation[0].used_hours, 2);
    let restored = babylon_material_circuit::decode_material_circuit_state(
        &babylon_material_circuit::encode_material_circuit_state(&second.state).unwrap(),
    )
    .unwrap();
    let third = babylon_material_circuit::advance_material_circuit(&second.state).unwrap();
    assert_eq!(
        third,
        babylon_material_circuit::advance_material_circuit(&restored).unwrap()
    );
    assert_eq!(equipment(&third.state).cohorts[0].units, 1);
    assert_eq!(equipment_cost(&third.state), crate::money(32));
}

#[test]
fn installation_choice_owned_equipment_can_install_above_the_purchase_ceiling() {
    let mut state = crate::opening();
    crate::configure_investment(&mut state, 100, 0);
    state
        .inventory
        .iter_mut()
        .find(|r| r.site_id == crate::site() && r.good_id == crate::good(1))
        .unwrap()
        .quantity = 2;
    state
        .inventory
        .iter_mut()
        .find(|r| r.site_id == crate::site() && r.good_id == crate::good(2))
        .unwrap()
        .quantity = 4;
    let mut stocks = crate::economy(&state).costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| r.owner == AccountId::Site(crate::site()) && r.good_id == crate::good(1))
        .unwrap()
        .amount = crate::money(20);
    let costs =
        HistoricalCostBook::open(&crate::economy(&state).book, stocks, vec![], vec![], vec![])
            .unwrap();
    crate::economy_mut(&mut state).costs = costs;
    let e = crate::equipment_mut(&mut state);
    e.installation_policies[0].target = InstallationTarget::FixedUnits(2);
    e.installation_policies[0].maximum_started_units_per_period = 2;
    e.investment_policies[0].maximum_installed_units = 1;
    let closed = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    assert_eq!(closed.installation_decisions[0].target_units, 2);
    assert_eq!(closed.installation_decisions[0].started_units, 2);
    assert_eq!(equipment(&closed.state).pending[0].units, 2);
    assert_eq!(closed.investment[0].admitted_units, 0);
}

#[test]
fn installation_choice_plan_withdrawal_and_explicit_replacement_are_distinct() {
    let mut state = crate::opening();
    crate::configure_output_quote(&mut state);
    crate::economy_mut(&mut state)
        .recurring
        .as_mut()
        .unwrap()
        .production[0]
        .planned_batches = 0;
    crate::equipment_mut(&mut state).installation_policies[0].target =
        InstallationTarget::ProductionPlan {
            replacement_units: 0,
        };
    let held = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    assert_eq!(held.installation_decisions[0].captured_plan_batches, 0);
    assert_eq!(held.installation_decisions[0].target_units, 0);
    assert_eq!(held.installation_decisions[0].started_units, 0);
    assert!(equipment(&held.state).pending.is_empty());
    crate::equipment_mut(&mut state).installation_policies[0].target =
        InstallationTarget::ProductionPlan {
            replacement_units: 1,
        };
    let replacement = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    assert_eq!(replacement.installation_decisions[0].target_units, 1);
    assert_eq!(replacement.installation_decisions[0].started_units, 1);
    assert_eq!(equipment(&replacement.state).pending[0].remaining_hours, 3);
}

#[test]
fn installation_choice_staffing_does_not_request_work_for_sale_inventory() {
    let mut state = pledged_opening();
    state.corridor_capacities[0].available_grams = 0;
    let closed = babylon_material_circuit::close_material_period(&state).unwrap();
    let binding = StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([1; 32]),
        crate::site(),
        crate::hours(),
        1,
        StaffingPolicy::one_period(1).unwrap(),
        vec![
            StaffingWorkSource::Production(crate::process()),
            StaffingWorkSource::Installation(crate::process()),
        ],
    )
    .unwrap();
    let requests = closed.staffing_requests(&[binding]).unwrap();
    let installation = requests
        .iter()
        .find(|r| r.work_source() == StaffingWorkSource::Installation(crate::process()))
        .unwrap();
    assert_eq!(installation.hours(), 0);
}

#[test]
fn installation_choice_pledged_stock_does_not_suppress_a_real_replacement_purchase() {
    let mut state = pledged_opening();
    state.corridor_capacities[0].available_grams = 0;
    let supplier = SiteId::from_bytes([2; 32]);
    let route = RouteId::from_bytes([4; 32]);
    state.supplier_routes.push(SupplierRoute {
        buyer_site_id: crate::site(),
        supplier_site_id: supplier,
        good_id: crate::good(1),
        unit_id: crate::unit(),
        route_id: route,
        transport_kind: SupplierTransport::Staged,
    });
    state.route_stages.push(RouteStage {
        route_id: route,
        stage_index: 0,
        from_node_id: LogisticsNodeId::from_bytes([2; 32]),
        to_node_id: LogisticsNodeId::from_bytes([1; 32]),
        travel_periods: 1,
        loss_ppm: 0,
    });
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id: route,
        stage_index: 0,
        corridor_id: CorridorId::from_bytes([2; 32]),
    });
    crate::equipment_mut(&mut state)
        .investment_policies
        .push(InvestmentPolicy {
            process_id: crate::process(),
            supplier_site_id: supplier,
            replacement_target_units: 1,
            maximum_installed_units: 2,
            maximum_purchase_per_period: 1,
            expansion_earnings_fraction_bps: 0,
            cash_floor: crate::money(0),
        });
    let closed = babylon_material_circuit::advance_material_circuit(&state).unwrap();
    assert!(closed.installation.is_empty());
    assert_eq!(closed.investment[0].on_hand_units, 0);
    assert_eq!(closed.investment[0].replacement_requested_units, 1);
    assert_eq!(closed.investment[0].admitted_units, 1);
    assert_eq!(closed.state.orders.len(), 2);
    assert_eq!(stock_cost(&closed.state, crate::good(1)), crate::money(20));
}

#[test]
fn installation_choice_wire_refuses_an_unknown_target_and_absent_plan_without_defaulting() {
    let state = crate::opening();
    let bytes = babylon_material_circuit::encode_material_circuit_state(&state).unwrap();
    let mut policy = crate::process().as_bytes().to_vec();
    policy.push(1);
    for value in [1_u64, 1, 2] {
        policy.extend_from_slice(&value.to_be_bytes());
    }
    let positions = bytes
        .windows(policy.len())
        .enumerate()
        .filter_map(|(i, row)| (row == policy).then_some(i))
        .collect::<Vec<_>>();
    assert_eq!(positions.len(), 1);
    let mut malformed = bytes;
    malformed[positions[0] + 32] = 3;
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&malformed),
        Err(MaterialCircuitError::WireEnum)
    );
    let mut absent = state;
    crate::equipment_mut(&mut absent).installation_policies[0].target =
        InstallationTarget::ProductionPlan {
            replacement_units: 1,
        };
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&absent),
        Err(MaterialCircuitError::EquipmentInvariant)
    );
}
