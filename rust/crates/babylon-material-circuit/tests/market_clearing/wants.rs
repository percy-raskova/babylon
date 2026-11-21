//! Households buy their comforts and luxuries in the same markets, at the same price, with the money
//! their needs do not use.

use super::support::{self, Fixture, Shelf};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, HouseholdStandard, HouseholdTierReceipt, HouseholdWantReceipt,
    MaterialCircuitState, MaterialCircuitTransition, MoneyTransferPurpose, OutboundOrderId,
    WantTier,
};

fn three_accounts(stock: u64) -> Fixture {
    Fixture::new(
        stock,
        &[
            support::dollars(400),
            support::dollars(600),
            support::dollars(40_000),
        ],
    )
}

/// `three_accounts` with a second shelf, good 3, that no household needs.
fn with_leisure(food: u64, leisure: u64) -> Fixture {
    let mut fixture = three_accounts(food);
    fixture.shelves.push(Shelf {
        good: 3,
        price: support::dollars(10),
        stock: leisure,
        needed: false,
    });
    fixture.paying_order = Some(vec![2, 3]);
    fixture
}

fn close(fixture: &Fixture) -> (MaterialCircuitState, MaterialCircuitTransition) {
    let (catalog, state) = fixture.build();
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes");
    (state, closed)
}

fn cash(state: &MaterialCircuitState, id: AccountId) -> Currency {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        panic!("the fixture is monetary")
    };
    economy.book.cash(id).expect("the account exists")
}

fn purse(state: &MaterialCircuitState, index: u8) -> i128 {
    cash(state, AccountId::Household(support::account(index))).micro_units()
}

/// What the retailer was paid for goods handed to households, from the money movements.
fn settled(closed: &MaterialCircuitTransition) -> i128 {
    closed
        .money_transfers
        .iter()
        .filter(|row| {
            matches!(
                row.purpose,
                MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::LocalFinalDemand(_))
            )
        })
        .map(|row| row.credit.delta.micro_units())
        .sum()
}

fn want_row(
    closed: &MaterialCircuitTransition,
    index: u8,
    tier: WantTier,
    shelf: u8,
) -> &HouseholdWantReceipt {
    let mut rows = closed.household_wants.iter().filter(|row| {
        row.principal_id == support::account(index)
            && row.tier == tier
            && row.good_id == support::good(shelf)
    });
    let row = rows.next().expect("the want has a row");
    assert!(rows.next().is_none(), "one row per want");
    row
}

fn tier_row(
    closed: &MaterialCircuitTransition,
    index: u8,
    tier: WantTier,
) -> &HouseholdTierReceipt {
    closed
        .household_tiers
        .iter()
        .find(|row| row.principal_id == support::account(index) && row.tier == tier)
        .expect("the account has a row for the tier")
}

fn standard(closed: &MaterialCircuitTransition, index: u8) -> HouseholdStandard {
    babylon_material_circuit::household_standard(
        support::account(index),
        &closed.household_consumption,
        &closed.household_services,
        &closed.household_tiers,
    )
    .expect("the account's tiers are recorded")
}

fn unmet(closed: &MaterialCircuitTransition, index: u8) -> u64 {
    closed
        .household_consumption
        .iter()
        .filter(|row| row.principal_id == support::account(index))
        .map(|row| row.unmet_quantity)
        .sum()
}

/// What the retailer holds of the shelf's good at the close.
fn shelf_left(closed: &MaterialCircuitTransition, shelf: u8) -> u64 {
    closed
        .state
        .inventory
        .iter()
        .find(|row| row.good_id == support::good(shelf))
        .map_or(0, |row| row.quantity)
}

fn m(dollars: i128) -> i128 {
    dollars * 1_000_000
}

#[test]
fn a_comfort_buys_with_the_money_needs_do_not_use() {
    let mut wanting = three_accounts(1_000);
    wanting.household_wants = vec![
        (0, WantTier::Comfort, 2, 50),
        (1, WantTier::Comfort, 2, 50),
        (2, WantTier::Comfort, 2, 50),
    ];
    let (opening, closed) = close(&wanting);
    let (_, plain) = close(&three_accounts(1_000));
    let rows: Vec<_> = (0..3)
        .map(|i| {
            let row = want_row(&closed, i, WantTier::Comfort, 2);
            (row.wanted_quantity, row.bought_quantity)
        })
        .collect();
    assert_eq!(rows, vec![(50, 0), (50, 50), (50, 50)]);
    for index in 0..3 {
        assert_eq!(
            want_row(&closed, index, WantTier::Comfort, 2)
                .unit_price
                .micro_units(),
            4_000_000
        );
        let comfort = tier_row(&closed, index, WantTier::Comfort);
        let luxury = tier_row(&closed, index, WantTier::Luxury);
        let bought = if index == 0 { 0 } else { m(200) };
        assert_eq!(
            (
                comfort.wanted_value.micro_units(),
                comfort.bought_value.micro_units()
            ),
            (m(200), bought)
        );
        assert_eq!(
            (
                luxury.wanted_value.micro_units(),
                luxury.bought_value.micro_units()
            ),
            (0, 0)
        );
    }
    assert_eq!(
        (0..3).map(|i| standard(&closed, i)).collect::<Vec<_>>(),
        vec![
            HouseholdStandard::GettingBy,
            HouseholdStandard::Affluent,
            HouseholdStandard::Affluent
        ]
    );
    let paid: i128 = (0..3)
        .map(|i| purse(&opening, i) - purse(&closed.state, i))
        .sum();
    assert_eq!(paid, m(1_600));
    assert_eq!(settled(&closed), paid);
    assert_eq!(closed.household_consumption, plain.household_consumption);
    assert_eq!(purse(&closed.state, 2), m(39_400));
    assert_eq!(closed.state.final_demand_orders.len(), 0);
}

#[test]
fn a_comfort_outbids_a_poorer_need() {
    let mut wanting = three_accounts(240);
    wanting.household_wants = vec![(2, WantTier::Comfort, 2, 100)];
    let (_, closed) = close(&wanting);
    assert!(closed
        .household_demand
        .iter()
        .all(|row| row.unit_price.micro_units() == 24_000_001));
    let admitted: Vec<_> = closed
        .household_demand
        .iter()
        .map(|row| row.admitted_quantity)
        .collect();
    assert_eq!(admitted, vec![16, 24, 100]);
    let want = want_row(&closed, 2, WantTier::Comfort, 2);
    assert_eq!(want.bought_quantity, 100);
    assert_eq!(want.unit_price.micro_units(), 24_000_001);
    assert_eq!((unmet(&closed, 0), unmet(&closed, 1)), (84, 76));
    assert_eq!(
        (0..3).map(|i| standard(&closed, i)).collect::<Vec<_>>(),
        vec![
            HouseholdStandard::GoingWithout,
            HouseholdStandard::GoingWithout,
            HouseholdStandard::Affluent
        ]
    );
    assert_eq!(closed.market_clearings.len(), 1);
    let market = &closed.market_clearings[0];
    assert_eq!(
        (market.supply, market.demand_at_quote, market.bidders),
        (240, 400, 3)
    );
}

#[test]
fn a_want_of_a_good_that_is_not_needed() {
    let mut wanting = with_leisure(1_000, 100);
    wanting.household_wants = vec![(2, WantTier::Luxury, 3, 5)];
    let (opening, closed) = close(&wanting);
    let want = want_row(&closed, 2, WantTier::Luxury, 3);
    assert_eq!((want.wanted_quantity, want.bought_quantity), (5, 5));
    assert_eq!(want.unit_price.micro_units(), m(10));
    assert!(closed
        .household_demand
        .iter()
        .all(|row| row.good_id != support::good(3)));
    let CircuitAccounting::Monetary(economy) = &closed.state.accounting else {
        panic!("the fixture is monetary")
    };
    let recurring = economy.recurring.as_ref().expect("a recurring economy");
    assert!(recurring
        .household_stocks
        .iter()
        .all(|row| row.good_id != support::good(3)));
    assert_eq!(shelf_left(&closed, 3), 95);
    assert_eq!(purse(&opening, 2) - purse(&closed.state, 2), m(400) + m(50));
    assert_eq!(closed.state.final_demand_orders.len(), 0);
}

#[test]
fn a_luxury_waits_for_a_comfort_still_to_buy() {
    let mut wanting = with_leisure(1_000, 1_000);
    wanting.household_wants = vec![(1, WantTier::Luxury, 2, 50), (1, WantTier::Comfort, 3, 10)];
    let (_, closed) = close(&wanting);
    let luxury = want_row(&closed, 1, WantTier::Luxury, 2);
    assert_eq!((luxury.wanted_quantity, luxury.bought_quantity), (50, 25));
    let comfort = want_row(&closed, 1, WantTier::Comfort, 3);
    assert_eq!((comfort.wanted_quantity, comfort.bought_quantity), (10, 10));
    assert_eq!(purse(&closed.state, 1), 0);
    assert_eq!(standard(&closed, 1), HouseholdStandard::Comfortable);
}

#[test]
fn a_household_short_of_food_buys_no_leisure_with_its_money() {
    let mut wanting = with_leisure(0, 1_000);
    wanting.household_wants = vec![(0, WantTier::Luxury, 3, 30), (1, WantTier::Luxury, 3, 30)];
    let (_, closed) = close(&wanting);
    let first = want_row(&closed, 0, WantTier::Luxury, 3);
    let second = want_row(&closed, 1, WantTier::Luxury, 3);
    assert_eq!(first.bought_quantity, 0);
    assert_eq!(second.bought_quantity, 20);
    assert_eq!(purse(&closed.state, 0), m(400));
    assert_eq!(purse(&closed.state, 1), m(400));
    assert_eq!(standard(&closed, 0), HouseholdStandard::GoingWithout);
    assert_eq!(standard(&closed, 1), HouseholdStandard::GoingWithout);
    assert_eq!((unmet(&closed, 0), unmet(&closed, 1)), (100, 100));
}

#[test]
fn an_empty_shelf_leaves_a_want_unbought() {
    let mut wanting = with_leisure(1_000, 0);
    wanting.household_wants = vec![(2, WantTier::Luxury, 3, 5)];
    let (opening, closed) = close(&wanting);
    let want = want_row(&closed, 2, WantTier::Luxury, 3);
    assert_eq!((want.wanted_quantity, want.bought_quantity), (5, 0));
    assert_eq!(want.unit_price.micro_units(), m(10));
    let order = babylon_material_circuit::recurring_household_want_order_id(
        1,
        (support::account(2), support::good(3), support::units()),
        WantTier::Luxury,
    );
    assert!(closed
        .local_fulfillments
        .iter()
        .all(|row| row.order_id != order));
    assert!(closed.money_transfers.iter().all(|row| !matches!(
        row.purpose,
        MoneyTransferPurpose::PurchaseReservation(OutboundOrderId::LocalFinalDemand(id))
            | MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::LocalFinalDemand(id))
            | MoneyTransferPurpose::PurchaseRefund(OutboundOrderId::LocalFinalDemand(id))
            if id == order
    )));
    assert_eq!(
        purse(&opening, 2) - purse(&closed.state, 2),
        m(400),
        "only the need is paid"
    );
}

#[test]
fn a_disabled_purchase_wants_nothing() {
    let mut wanting = with_leisure(1_000, 1_000);
    wanting.household_wants = vec![(2, WantTier::Luxury, 3, 5)];
    let (catalog, mut state) = wanting.build();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the fixture is monetary")
    };
    let recurring = economy.recurring.as_mut().expect("a recurring economy");
    for row in &mut recurring.household_purchases {
        if row.good_id == support::good(3) {
            row.enabled = false;
        }
    }
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the period closes");
    let want = want_row(&closed, 2, WantTier::Luxury, 3);
    assert_eq!((want.wanted_quantity, want.bought_quantity), (0, 0));
    let luxury = tier_row(&closed, 2, WantTier::Luxury);
    assert_eq!(
        (
            luxury.wanted_value.micro_units(),
            luxury.bought_value.micro_units()
        ),
        (0, 0)
    );
    assert_eq!(
        tier_row(&closed, 2, WantTier::Comfort)
            .wanted_value
            .micro_units(),
        0
    );
    assert_eq!(standard(&closed, 2), HouseholdStandard::Affluent);
}

#[test]
fn a_market_policy_without_wants_writes_no_tier_rows() {
    let (_, closed) = close(&three_accounts(240));
    assert_eq!(closed.household_demand.len(), 3);
    assert_eq!(closed.household_wants.len(), 0);
    assert_eq!(closed.household_tiers.len(), 0);
}
