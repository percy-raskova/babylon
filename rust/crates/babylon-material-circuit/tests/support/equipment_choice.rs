use crate::equipment_cost;
use crate::household;
use crate::stock_cost;
use babylon_material_circuit::AccountId;
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
use babylon_material_circuit::MaterialCatalog;
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

fn pledged_opening() -> (MaterialCatalog, MaterialCircuitState) {
    let (mut catalog, mut state) = crate::opening();
    crate::configure_investment(&mut catalog, &mut state, 100, 0);
    catalog = crate::rebuild(&catalog, |content| content.investment_policies.clear());
    state
        .inventory
        .iter_mut()
        .find(|r| r.site_id == crate::site() && r.good_id == crate::good(1))
        .expect("the fixture holds the searched element")
        .quantity = 1;
    let buyer = SiteId::from_bytes([2; 32]);
    catalog.supplier_routes[0].buyer_site_id = buyer;
    catalog.supplier_routes[0].supplier_site_id = crate::site();
    catalog.route_stages[0].from_node_id = LogisticsNodeId::from_bytes([1; 32]);
    catalog.route_stages[0].to_node_id = LogisticsNodeId::from_bytes([2; 32]);
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
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
    .expect("the fixture opens the authored source");
    book.reserve_purchase(
        PurchaseEscrow::new(
            OutboundOrderId::Delivery(id),
            AccountId::Site(buyer),
            AccountId::Site(crate::site()),
            1,
            crate::money(20),
        )
        .expect("the constructor accepts the authored fixture arguments"),
    )
    .expect("the fixture reserve admits the purchase");
    let mut stocks = crate::economy(&state).costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| r.owner == AccountId::Site(crate::site()) && r.good_id == crate::good(1))
        .expect("the fixture holds the searched element")
        .amount = crate::money(20);
    let costs = HistoricalCostBook::open(&book, stocks, vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
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
    (catalog, state)
}

#[test]
fn installation_choice_preserves_owned_equipment_pledged_to_a_paid_buyer() {
    let (catalog, state) = pledged_opening();
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert!(
        crate::position(&closed.state).pending.is_empty(),
        "sale inventory must not become WIP"
    );
    assert_eq!(closed.installation.len(), 0);
    assert_eq!(closed.dispatches.iter().map(|r| r.quantity).sum::<u64>(), 1);
    assert_eq!(closed.state.freight.len(), 1);
    assert_eq!(stock_cost(&closed.state, crate::good(2)), crate::money(6));
}

#[test]
fn installation_choice_does_not_expand_a_process_already_at_its_captured_target() {
    let (catalog, mut state) = crate::opening();
    let id = EquipmentCohortId::from_bytes([20; 32]);
    crate::position_mut(&mut state)
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
        .expect("the fixture holds the searched element")
        .opening_capital = crate::money(142);
    crate::economy_mut(&mut state).costs =
        HistoricalCostBook::from_snapshot(snapshot).expect("the snapshot admits the derived value");
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert!(
        crate::position(&closed.state).pending.is_empty(),
        "owned spare stock is not automatic expansion"
    );
    assert_eq!(crate::position(&closed.state).cohorts.len(), 1);
    assert_eq!(stock_cost(&closed.state, crate::good(1)), crate::money(20));
}

#[test]
fn installation_choice_lowered_target_keeps_existing_wip_and_exact_restart() {
    let (catalog, opening) = crate::opening();
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    let state = first.state;
    let catalog = crate::rebuild(&catalog, |content| {
        content.installation_policies[0].target = InstallationTarget::FixedUnits(0);
    });
    let second = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(second.installation_decisions[0].target_units, 0);
    assert_eq!(second.installation_decisions[0].pending_units, 1);
    assert_eq!(second.installation_decisions[0].requested_units, 0);
    assert_eq!(second.installation_decisions[0].started_units, 0);
    assert_eq!(second.installation[0].used_hours, 2);
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
    assert_eq!(crate::position(&third.state).cohorts[0].units, 1);
    assert_eq!(equipment_cost(&third.state), crate::money(32));
}

#[test]
fn installation_choice_owned_equipment_can_install_above_the_purchase_ceiling() {
    let (mut catalog, mut state) = crate::opening();
    crate::configure_investment(&mut catalog, &mut state, 100, 0);
    state
        .inventory
        .iter_mut()
        .find(|r| r.site_id == crate::site() && r.good_id == crate::good(1))
        .expect("the fixture holds the searched element")
        .quantity = 2;
    state
        .inventory
        .iter_mut()
        .find(|r| r.site_id == crate::site() && r.good_id == crate::good(2))
        .expect("the fixture holds the searched element")
        .quantity = 4;
    let mut stocks = crate::economy(&state).costs.snapshot().stocks;
    stocks
        .iter_mut()
        .find(|r| r.owner == AccountId::Site(crate::site()) && r.good_id == crate::good(1))
        .expect("the fixture holds the searched element")
        .amount = crate::money(20);
    let costs =
        HistoricalCostBook::open(&crate::economy(&state).book, stocks, vec![], vec![], vec![])
            .expect("the fixture opens the authored source");
    crate::economy_mut(&mut state).costs = costs;
    let catalog = crate::rebuild(&catalog, |content| {
        content.installation_policies[0].target = InstallationTarget::FixedUnits(2);
        content.installation_policies[0].maximum_started_units_per_period = 2;
        content.investment_policies[0].maximum_installed_units = 1;
    });
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(closed.installation_decisions[0].target_units, 2);
    assert_eq!(closed.installation_decisions[0].started_units, 2);
    assert_eq!(crate::position(&closed.state).pending[0].units, 2);
    assert_eq!(closed.investment[0].admitted_units, 0);
}

#[test]
fn installation_choice_plan_withdrawal_and_explicit_replacement_are_distinct() {
    let (catalog, mut state) = crate::opening();
    crate::configure_output_quote(&mut state);
    crate::economy_mut(&mut state)
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .production[0]
        .planned_batches = 0;
    let catalog = crate::rebuild(&catalog, |content| {
        content.installation_policies[0].target = InstallationTarget::ProductionPlan {
            replacement_units: 0,
        };
    });
    let held = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(held.installation_decisions[0].captured_plan_batches, 0);
    assert_eq!(held.installation_decisions[0].target_units, 0);
    assert_eq!(held.installation_decisions[0].started_units, 0);
    assert_eq!(crate::position(&held.state).pending.len(), 0);
    let catalog = crate::rebuild(&catalog, |content| {
        content.installation_policies[0].target = InstallationTarget::ProductionPlan {
            replacement_units: 1,
        };
    });
    let replacement = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(replacement.installation_decisions[0].target_units, 1);
    assert_eq!(replacement.installation_decisions[0].started_units, 1);
    assert_eq!(
        crate::position(&replacement.state).pending[0].remaining_hours,
        3
    );
}

#[test]
fn installation_choice_staffing_does_not_request_work_for_sale_inventory() {
    let (catalog, mut state) = pledged_opening();
    state.corridor_capacities[0].available_grams = 0;
    let closed = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes");
    let binding = StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([1; 32]),
        crate::site(),
        crate::hours(),
        1,
        StaffingPolicy::one_period(1).expect("the one-period fixture advances"),
        vec![
            StaffingWorkSource::Production(crate::process()),
            StaffingWorkSource::Installation(crate::process()),
        ],
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let requests = closed
        .staffing_requests(&catalog, &[binding])
        .expect("the fixture staffing requests are present");
    let installation = requests
        .iter()
        .find(|r| r.work_source() == StaffingWorkSource::Installation(crate::process()))
        .expect("the fixture holds the searched element");
    assert_eq!(installation.hours(), 0);
}

#[test]
fn installation_choice_pledged_stock_does_not_suppress_a_real_replacement_purchase() {
    let (mut catalog, mut state) = pledged_opening();
    state.corridor_capacities[0].available_grams = 0;
    let supplier = SiteId::from_bytes([2; 32]);
    let route = RouteId::from_bytes([4; 32]);
    catalog.supplier_routes.push(SupplierRoute {
        buyer_site_id: crate::site(),
        supplier_site_id: supplier,
        good_id: crate::good(1),
        unit_id: crate::unit(),
        route_id: route,
        transport_kind: SupplierTransport::Staged,
    });
    catalog.route_stages.push(RouteStage {
        route_id: route,
        stage_index: 0,
        from_node_id: LogisticsNodeId::from_bytes([2; 32]),
        to_node_id: LogisticsNodeId::from_bytes([1; 32]),
        travel_periods: 1,
        loss_ppm: 0,
    });
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    state.route_stage_capacities.push(RouteStageCapacity {
        route_id: route,
        stage_index: 0,
        corridor_id: CorridorId::from_bytes([2; 32]),
    });
    catalog = crate::rebuild(&catalog, |content| {
        content.investment_policies.push(InvestmentPolicy {
            process_id: crate::process(),
            supplier_site_id: supplier,
            replacement_target_units: 1,
            maximum_installed_units: 2,
            maximum_purchase_per_period: 1,
            expansion_earnings_fraction_bps: 0,
            cash_floor: crate::money(0),
        });
    });
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(closed.installation.len(), 0);
    assert_eq!(closed.investment[0].on_hand_units, 0);
    assert_eq!(closed.investment[0].replacement_requested_units, 1);
    assert_eq!(closed.investment[0].admitted_units, 1);
    assert_eq!(closed.state.orders.len(), 2);
    assert_eq!(stock_cost(&closed.state, crate::good(1)), crate::money(20));
}

#[test]
fn installation_choice_wire_refuses_an_absent_plan_without_defaulting() {
    let (catalog, state) = crate::opening();
    let absent = crate::rebuild(&catalog, |content| {
        content.installation_policies[0].target = InstallationTarget::ProductionPlan {
            replacement_units: 1,
        };
    });
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&absent, &state),
        Err(MaterialCircuitError::EquipmentInvariant)
    );
}
