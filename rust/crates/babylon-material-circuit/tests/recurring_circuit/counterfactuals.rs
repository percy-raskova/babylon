//! Designed paired interventions; no national outcome or recovery date is implied.
use crate::economy;
use crate::integrated_controls;
use crate::integrated_controls::EconomicLocation;
use crate::integrated_controls::ForeignCounterpart;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::FinalDemandPrincipal;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdCohort;
use babylon_material_circuit::HouseholdKind;
use babylon_material_circuit::HouseholdNeed;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::HouseholdPurchasePolicy;
use babylon_material_circuit::HouseholdStock;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialCircuitTransition;
use babylon_material_circuit::MerchantRole;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::MoneyTransferPurpose;
use babylon_material_circuit::OutboundOrderId;
use babylon_material_circuit::StockCarryingValue;

#[derive(Clone, Copy, Debug)]
enum Constraint {
    Freight,
    Labor,
    Inputs,
    Finance,
}

fn recapture_cash(state: &mut MaterialCircuitState, accounts: Vec<CashAccount>) {
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("paid fixture")
    };
    let stocks = e.costs.snapshot().stocks;
    e.book = MonetaryBook::open(accounts).expect("the fixture opens the authored source");
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
}

fn zero_food(state: &mut MaterialCircuitState) {
    state
        .inventory
        .iter_mut()
        .filter(|r| r.good_id == crate::good(2))
        .for_each(|r| r.quantity = 0);
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    e.recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .household_stocks[0]
        .quantity = 0;
    let mut costs = e.costs.snapshot();
    costs
        .stocks
        .iter_mut()
        .filter(|r| r.good_id == crate::good(2))
        .for_each(|r| r.amount = crate::money(0));
    e.costs =
        HistoricalCostBook::from_snapshot(costs).expect("the snapshot admits the derived value");
}
fn input_cut(state: &mut MaterialCircuitState) {
    state.inventory.iter_mut().for_each(|r| r.quantity = 0);
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    let mut costs = e.costs.snapshot();
    costs
        .stocks
        .iter_mut()
        .for_each(|r| r.amount = crate::money(0));
    e.costs =
        HistoricalCostBook::from_snapshot(costs).expect("the snapshot admits the derived value");
}
fn labor_cut(state: &mut MaterialCircuitState) {
    state
        .labor
        .iter_mut()
        .filter(|r| r.site_id == crate::site(2))
        .for_each(|r| r.available = 0);
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    e.member_labor
        .iter_mut()
        .filter(|r| r.member_id.as_bytes() == crate::site(2).as_bytes())
        .for_each(|r| r.available_hours = 0);
}
fn food_opening(cut: Constraint, grams: u64) -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = crate::opening();
    zero_food(&mut state);
    if matches!(cut, Constraint::Inputs) {
        input_cut(&mut state);
    }
    if matches!(cut, Constraint::Labor) {
        labor_cut(&mut state);
    }
    let finance = matches!(cut, Constraint::Finance);
    recapture_cash(
        &mut state,
        [
            (AccountId::Site(crate::site(1)), 4),
            (
                AccountId::Site(crate::site(2)),
                if finance { 0 } else { 32 },
            ),
            (AccountId::Site(crate::site(3)), 32),
            (
                AccountId::Household(crate::household()),
                if finance { 64 } else { 32 },
            ),
        ]
        .into_iter()
        .map(|(id, cash)| CashAccount {
            id,
            cash: crate::money(cash),
        })
        .collect(),
    );
    state
        .corridor_capacities
        .iter_mut()
        .filter(|r| r.corridor_id == crate::corridor(2))
        .for_each(|r| r.available_grams = grams);
    (catalog, state)
}

#[derive(Debug)]
struct FoodTrajectory {
    first_dispatch: u64,
    second_handoff: u64,
    first_unfunded: u64,
    produced: u64,
}

fn observe_food(closed: &MaterialCircuitTransition, period: u64, facts: &mut FoodTrajectory) {
    let amount = closed
        .production
        .iter()
        .filter(|r| r.process_id == crate::process(2))
        .map(|r| r.produced_batches)
        .sum::<u64>();
    facts.produced = facts
        .produced
        .checked_add(amount)
        .expect("the fixture arithmetic stays in range");
    if period == 1 {
        let admitted = closed
            .procurement
            .iter()
            .find(|r| {
                r.buyer_site_id == crate::site(3)
                    && r.good_id == crate::good(2)
                    && r.unit_id == crate::units()
            })
            .expect("the fixture holds the searched element");
        assert_eq!(
            admitted.admitted_quantity, 4,
            "fixture must isolate physical/work constraint"
        );
        facts.first_dispatch = closed
            .dispatches
            .iter()
            .filter(|r| r.route_id == crate::route(2))
            .map(|r| r.quantity)
            .sum();
        facts.first_unfunded = closed
            .labor_use
            .iter()
            .filter(|r| r.site_id == crate::site(2))
            .map(|r| r.unfunded_hours)
            .sum();
    }
    if period == 2 {
        facts.second_handoff = closed
            .household_demand
            .iter()
            .filter(|r| {
                r.principal_id == crate::household()
                    && r.good_id == crate::good(2)
                    && r.unit_id == crate::units()
            })
            .map(|r| r.fulfilled_quantity)
            .sum();
    }
}
fn food_trajectory(
    (catalog, mut state): (MaterialCatalog, MaterialCircuitState),
) -> FoodTrajectory {
    let original = state.clone();
    let physical = state.inventory.iter().map(|r| r.quantity).sum::<u64>();
    let mut consumed = 0_u64;
    let mut facts = FoodTrajectory {
        first_dispatch: 0,
        second_handoff: 0,
        first_unfunded: 0,
        produced: 0,
    };
    for period in 1..=3 {
        let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period");
        observe_food(&closed, period, &mut facts);
        consumed = consumed
            .checked_add(
                closed
                    .household_consumption
                    .iter()
                    .map(|r| r.consumed_quantity)
                    .sum::<u64>(),
            )
            .expect("the fixture arithmetic stays in range");
        integrated_controls::assert_conservation(&closed.state, consumed, physical, 100);
        let restored = babylon_material_circuit::decode_material_circuit_state(
            &catalog,
            &babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
                .expect("the canonical material state encodes"),
        )
        .expect("the canonical material bytes decode");
        assert_eq!(
            closed,
            babylon_material_circuit::advance_material_circuit(&catalog, &restored)
                .expect("the authored material state advances one period")
        );
        if period == 1 {
            assert_eq!(state, original);
        }
        state = closed.state;
    }
    facts
}

#[test]
fn extra_freight_changes_only_the_freight_bound_paid_food_case() {
    for cut in [
        Constraint::Freight,
        Constraint::Labor,
        Constraint::Inputs,
        Constraint::Finance,
    ] {
        // Designed three-close horizon; exactly 1 gram per native food unit.
        let low = food_trajectory(food_opening(cut, 1));
        let high = food_trajectory(food_opening(cut, 4));
        if matches!(cut, Constraint::Freight) {
            assert_eq!((low.first_dispatch, high.first_dispatch), (1, 4));
            assert_eq!((low.second_handoff, high.second_handoff), (1, 4));
        } else {
            assert_eq!(
                (low.produced, high.produced),
                (0, 0),
                "{cut:?}: {low:?} / {high:?}"
            );
            assert_eq!((low.second_handoff, high.second_handoff), (0, 0));
        }
        if matches!(cut, Constraint::Finance) {
            assert!(low.first_unfunded > 0 && high.first_unfunded > 0);
        }
    }
}

fn foreign_household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([77; 32])
}

fn foreign_need(state: &mut MaterialCircuitState, enabled: bool) {
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    let recurring = e
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow");
    recurring.households.push(HouseholdCohort {
        principal_id: foreign_household(),
        kind: HouseholdKind::Ordinary,
        households: 1,
        persons: 1,
    });
    recurring.household_stocks.push(HouseholdStock {
        principal_id: foreign_household(),
        good_id: crate::good(2),
        unit_id: crate::units(),
        quantity: 0,
    });
    recurring.household_needs.push(HouseholdNeed {
        principal_id: foreign_household(),
        good_id: crate::good(2),
        unit_id: crate::units(),
        basis: HouseholdNeedBasis::Persons,
        units_per_basis: 2,
    });
    recurring.household_purchases.push(HouseholdPurchasePolicy {
        principal_id: foreign_household(),
        retailer_site_id: crate::site(2),
        good_id: crate::good(2),
        unit_id: crate::units(),
        target_closing_stock: 0,
        maximum_purchase: 2,
        enabled,
    });
}

fn domestic_competition(enabled: bool) -> (MaterialCatalog, MaterialCircuitState) {
    let (mut catalog, mut state) = integrated_controls::foreign_trade_opening();
    let foreign = EconomicLocation::Foreign(ForeignCounterpart::Canada);
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: foreign_household(),
        location: foreign,
    });
    catalog
        .merchants
        .iter_mut()
        .find(|r| r.site_id == crate::site(2))
        .expect("the fixture holds the searched element")
        .role = MerchantRole::Retail;
    state
        .inventory
        .iter_mut()
        .find(|r| r.site_id == crate::site(2) && r.good_id == crate::good(2))
        .expect("the fixture holds the searched element")
        .quantity = 2;
    foreign_need(&mut state, enabled);
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    let mut accounts = e.book.snapshot().accounts;
    accounts.push(CashAccount {
        id: AccountId::Household(foreign_household()),
        cash: crate::money(2),
    });
    let mut stocks = e.costs.snapshot().stocks;
    stocks.push(StockCarryingValue {
        owner: AccountId::Household(foreign_household()),
        good_id: crate::good(2),
        unit_id: crate::units(),
        amount: crate::money(0),
    });
    e.book = MonetaryBook::open(accounts).expect("the fixture opens the authored source");
    e.costs = HistoricalCostBook::open(&e.book, stocks, vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
    catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    (catalog, state)
}

fn direction_dispatch(closed: &MaterialCircuitTransition, identity: u8) -> u64 {
    closed
        .dispatches
        .iter()
        .filter(|r| r.route_id == crate::route(identity))
        .map(|r| r.quantity)
        .sum()
}

#[test]
fn counterpart_domestic_paid_need_competes_with_finite_import_supply() {
    let (catalog, absent) = domestic_competition(false);
    let (_present_catalog, present) = domestic_competition(true);
    let low = babylon_material_circuit::advance_material_circuit(&catalog, &absent)
        .expect("the authored material state advances one period");
    let high = babylon_material_circuit::advance_material_circuit(&catalog, &present)
        .expect("the authored material state advances one period");
    let local = high
        .household_demand
        .iter()
        .find(|r| r.principal_id == foreign_household())
        .expect("the fixture holds the searched element");
    assert_eq!(
        (local.good_id, local.unit_id, local.admitted_quantity),
        (crate::good(2), crate::units(), 2)
    );
    assert_eq!(
        (direction_dispatch(&low, 2), direction_dispatch(&high, 2)),
        (2, 0)
    );
    assert_eq!(local.fulfilled_quantity, 2);
    let consumption = high
        .household_consumption
        .iter()
        .find(|r| r.principal_id == foreign_household())
        .expect("the fixture holds the searched element");
    assert_eq!(
        (consumption.consumed_quantity, consumption.unmet_quantity),
        (2, 0)
    );
    // Existing household orders close before newly admitted replenishment dispatch.
    // The counterpart consumes both finite units; no partial shared-pass grant is implied.
    for (first, expected_import) in [(low, 2_u64), (high, 0_u64)] {
        let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
            .expect("the authored material state advances one period");
        let mut delivered = [0; 2];
        let mut paid = [0; 2];
        integrated_controls::record_trade_settlement(
            &first.state,
            &second,
            &mut delivered,
            &mut paid,
        );
        assert_eq!(paid[1], i128::from(delivered[1]));
        assert_eq!(delivered[1], expected_import);
        let first_consumed = first
            .household_consumption
            .iter()
            .map(|r| r.consumed_quantity)
            .try_fold(0_u64, u64::checked_add)
            .expect("the fixture input satisfies the fallible conversion");
        let all_consumed = second
            .household_consumption
            .iter()
            .map(|r| r.consumed_quantity)
            .try_fold(first_consumed, u64::checked_add)
            .expect("the fixture input satisfies the fallible conversion");
        integrated_controls::assert_conservation(&first.state, first_consumed, 14, 202);
        integrated_controls::assert_conservation(&second.state, all_consumed, 14, 202);
        let reopened = babylon_material_circuit::decode_material_circuit_state(
            &catalog,
            &babylon_material_circuit::encode_material_circuit_state(&catalog, &first.state)
                .expect("the canonical material state encodes"),
        )
        .expect("the canonical material bytes decode");
        assert_eq!(
            second,
            babylon_material_circuit::advance_material_circuit(&catalog, &reopened)
                .expect("the authored material state advances one period")
        );
    }
}

#[test]
fn counterpart_procurement_budget_cut_keeps_import_handling_funded() {
    let (catalog, funded) = integrated_controls::foreign_trade_opening();
    let mut protected = funded.clone();
    crate::recurring_mut(&mut protected)
        .replenishment
        .iter_mut()
        .find(|r| r.buyer_site_id == crate::site(2) && r.good_id == crate::good(1))
        .expect("the fixture holds the searched element")
        .cash_floor = crate::money(100);
    let baseline = babylon_material_circuit::advance_material_circuit(&catalog, &funded)
        .expect("the authored material state advances one period");
    let cut = babylon_material_circuit::advance_material_circuit(&catalog, &protected)
        .expect("the authored material state advances one period");
    let admission = cut
        .procurement
        .iter()
        .find(|r| r.buyer_site_id == crate::site(2) && r.good_id == crate::good(1))
        .expect("the fixture holds the searched element");
    assert_eq!(
        (admission.desired_quantity, admission.admitted_quantity),
        (2, 0)
    );
    assert_eq!(direction_dispatch(&baseline, 1), 2);
    assert_eq!(direction_dispatch(&cut, 1), 0);
    assert_eq!(
        direction_dispatch(&cut, 2),
        direction_dispatch(&baseline, 2)
    );
    assert!(!cut
        .state
        .orders
        .iter()
        .any(|r| r.order_id == admission.order_id));
    assert!(!cut.money_transfers.iter().any(|r| matches!(r.purpose,
        MoneyTransferPurpose::PurchaseReservation(OutboundOrderId::Delivery(id)) if id == admission.order_id)));
    let second = babylon_material_circuit::advance_material_circuit(&catalog, &cut.state)
        .expect("the authored material state advances one period");
    let mut delivered = [0; 2];
    let mut paid = [0; 2];
    integrated_controls::record_trade_settlement(&cut.state, &second, &mut delivered, &mut paid);
    assert_eq!(delivered, [0, 2]);
    assert_eq!(paid, [0, 2]);
    assert_eq!(
        economy(&cut.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(200)
    );
}

fn gateway(available: u64) -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = integrated_controls::foreign_trade_opening();
    state
        .route_stage_capacities
        .iter_mut()
        .for_each(|r| r.corridor_id = crate::corridor(1));
    state
        .corridor_capacities
        .retain(|r| r.corridor_id != crate::corridor(2));
    state
        .corridor_capacities
        .iter_mut()
        .filter(|r| r.corridor_id == crate::corridor(1))
        .for_each(|r| r.available_grams = available);
    (catalog, state)
}

#[test]
fn severed_shared_gateway_blocks_both_funded_trade_directions() {
    let (catalog, open_gateway) = gateway(4);
    let (cut_catalog, severed_gateway) = gateway(0);
    let baseline = babylon_material_circuit::advance_material_circuit(&catalog, &open_gateway)
        .expect("the authored material state advances one period");
    let cut = babylon_material_circuit::advance_material_circuit(&cut_catalog, &severed_gateway)
        .expect("the authored material state advances one period");
    assert_eq!(
        (
            direction_dispatch(&baseline, 1),
            direction_dispatch(&baseline, 2)
        ),
        (2, 2)
    );
    assert!(cut.dispatches.is_empty() && cut.state.freight.is_empty());
    assert_eq!(cut.state.orders.len(), 2);
    assert!(cut.state.orders.iter().all(|r| r.shipped == 0));
    let second = babylon_material_circuit::advance_material_circuit(&cut_catalog, &cut.state)
        .expect("the authored material state advances one period");
    assert!(
        second.arrivals.is_empty()
            && second.deliveries.is_empty()
            && second.realizations.is_empty()
    );
    assert!(!second.money_transfers.iter().any(|r| matches!(
        r.purpose,
        MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::Delivery(_))
    )));
    assert_eq!(
        economy(&second.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(200)
    );
    let reopened = babylon_material_circuit::decode_material_circuit_state(
        &catalog,
        &babylon_material_circuit::encode_material_circuit_state(&catalog, &cut.state)
            .expect("the canonical material state encodes"),
    )
    .expect("the canonical material bytes decode");
    assert_eq!(
        second,
        babylon_material_circuit::advance_material_circuit(&catalog, &reopened)
            .expect("the authored material state advances one period")
    );
}
