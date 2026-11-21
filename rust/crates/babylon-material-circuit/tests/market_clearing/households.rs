//! Households buy goods at the market's price and take them home.

use super::support::{self, Fixture, Shelf};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, MaterialCircuitState, MaterialCircuitTransition, MoneyLocation,
    MoneyTransferPurpose, OutboundOrderId,
};

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

fn total(state: &MaterialCircuitState) -> Currency {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        panic!("the fixture is monetary")
    };
    economy
        .book
        .total_cash_and_reserves()
        .expect("the book totals")
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

#[test]
fn a_short_shelf_raises_the_price_for_everyone() {
    let (opening, closed) = close(&three_accounts(240));
    let rows: Vec<_> = closed
        .household_demand
        .iter()
        .map(|row| (row.unit_price.micro_units(), row.admitted_quantity))
        .collect();
    assert_eq!(
        rows,
        vec![(7_058_824, 56), (7_058_824, 84), (7_058_824, 100)]
    );
    for row in &closed.household_demand {
        assert_eq!(row.fulfilled_quantity, row.admitted_quantity);
        assert_eq!(row.expired_quantity, 0);
    }
    let paid: i128 = closed
        .household_demand
        .iter()
        .map(|row| row.unit_price.micro_units() * i128::from(row.admitted_quantity))
        .sum();
    assert_eq!(settled(&closed), paid);
    for (index, row) in closed.household_demand.iter().enumerate() {
        let id = AccountId::Household(support::account(u8::try_from(index).expect("few accounts")));
        assert_eq!(
            cash(&opening, id).micro_units() - cash(&closed.state, id).micro_units(),
            row.unit_price.micro_units() * i128::from(row.admitted_quantity)
        );
    }
    assert_eq!(total(&opening), total(&closed.state));
    let retailer = AccountId::Site(support::site(support::RETAILER));
    let into_retailer: i128 = closed
        .money_transfers
        .iter()
        .filter(|row| row.credit.location == MoneyLocation::Cash(retailer))
        .map(|row| row.credit.delta.micro_units())
        .sum();
    let out_of_retailer: i128 = closed
        .money_transfers
        .iter()
        .filter(|row| row.debit.location == MoneyLocation::Cash(retailer))
        .map(|row| row.debit.delta.micro_units().abs())
        .sum();
    assert_eq!(
        cash(&closed.state, retailer).micro_units() - cash(&opening, retailer).micro_units(),
        into_retailer - out_of_retailer
    );
    assert!(into_retailer >= settled(&closed));
    assert!(closed.money_transfers.iter().all(|row| !matches!(
        row.purpose,
        MoneyTransferPurpose::PurchaseRefund(OutboundOrderId::LocalFinalDemand(_))
    )));
    assert_eq!(closed.market_clearings.len(), 1);
    let market = &closed.market_clearings[0];
    assert_eq!(
        (
            market.site_id,
            market.good_id,
            market.supply,
            market.demand_at_quote,
            market.sold_quantity,
            market.bidders,
            market.served_bidders
        ),
        (
            support::site(support::RETAILER),
            support::good(2),
            240,
            300,
            240,
            3,
            3
        )
    );
    assert_eq!(market.quote_price, support::dollars(4));
    assert_eq!(market.clearing_price.micro_units(), 7_058_824);
}

#[test]
fn a_full_shelf_sells_at_the_posted_price() {
    let (_, closed) = close(&three_accounts(300));
    let rows: Vec<_> = closed
        .household_demand
        .iter()
        .map(|row| {
            (
                row.unit_price,
                row.admitted_quantity,
                row.fulfilled_quantity,
            )
        })
        .collect();
    assert_eq!(rows, vec![(support::dollars(4), 100, 100); 3]);
    assert_eq!(closed.market_clearings.len(), 0);
}

#[test]
fn an_empty_shelf_sells_nothing_and_moves_no_money() {
    let (opening, closed) = close(&three_accounts(0));
    assert!(closed
        .household_demand
        .iter()
        .all(|row| row.admitted_quantity == 0 && row.fulfilled_quantity == 0));
    assert!(closed.money_transfers.iter().all(|row| !matches!(
        row.purpose,
        MoneyTransferPurpose::PurchaseReservation(OutboundOrderId::LocalFinalDemand(_))
            | MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::LocalFinalDemand(_))
            | MoneyTransferPurpose::PurchaseRefund(OutboundOrderId::LocalFinalDemand(_))
    )));
    for index in 0..3 {
        let id = AccountId::Household(support::account(index));
        assert_eq!(cash(&opening, id), cash(&closed.state, id));
    }
    assert_eq!(closed.market_clearings.len(), 1);
    let market = &closed.market_clearings[0];
    assert_eq!((market.supply, market.sold_quantity), (0, 0));
    assert_eq!(market.clearing_price, market.quote_price);
    assert_eq!(market.demand_at_quote, 300);
}

#[test]
fn a_shelf_with_no_inventory_row_sells_nothing_and_closes() {
    let mut fixture = three_accounts(0);
    fixture.no_stock_rows = true;
    let (state, closed) = close(&fixture);
    assert_eq!(state.inventory.len(), 0);
    assert!(closed
        .household_demand
        .iter()
        .all(|row| row.fulfilled_quantity == 0));
    assert_eq!(total(&state), total(&closed.state));
    assert_eq!(closed.market_clearings[0].sold_quantity, 0);
}

#[test]
fn a_household_pays_for_food_before_materials() {
    let mut fixture = Fixture::new(50, &[support::dollars(400)]);
    fixture.shelves.push(Shelf {
        good: 3,
        price: support::dollars(10),
        stock: 50,
        needed: true,
    });
    fixture.paying_order = Some(vec![2, 3]);
    let (_, closed) = close(&fixture);
    let by_good = |id: u8| {
        closed
            .household_demand
            .iter()
            .find(|row| row.good_id == support::good(id))
            .expect("the household has a row for the good")
    };
    assert_eq!(by_good(2).admitted_quantity, 50);
    // The least price at which $400 buys no more than 50 units is just above $400 / 51.
    assert_eq!(by_good(2).unit_price.micro_units(), 7_843_138);
    assert_eq!(by_good(3).admitted_quantity, 0);
    assert_eq!(closed.market_clearings.len(), 1);
    assert_eq!(closed.market_clearings[0].good_id, support::good(2));
}

#[test]
fn without_a_market_policy_the_shelf_is_shared_in_proportion() {
    let mut fixture = three_accounts(240);
    fixture.paying_order = None;
    let (_, closed) = close(&fixture);
    let rows: Vec<_> = closed
        .household_demand
        .iter()
        .map(|row| {
            (
                row.unit_price,
                row.admitted_quantity,
                row.fulfilled_quantity,
            )
        })
        .collect();
    assert_eq!(
        rows,
        vec![
            (support::dollars(4), 100, 80),
            (support::dollars(4), 100, 80),
            (support::dollars(4), 100, 80)
        ]
    );
    assert_eq!(closed.market_clearings.len(), 0);
}

#[test]
fn goods_already_owed_are_not_on_offer() {
    let mut fixture = three_accounts(240);
    fixture.owed = 100;
    let (_, closed) = close(&fixture);
    assert_eq!(closed.market_clearings.len(), 1);
    assert_eq!(closed.market_clearings[0].supply, 140);
    let sold: u64 = closed
        .household_demand
        .iter()
        .map(|row| row.fulfilled_quantity)
        .sum();
    assert_eq!(sold, 140);
}

#[test]
fn a_shelf_that_feeds_the_sellers_own_production_is_sold_first() {
    let mut fixture = Fixture::new(300, &[support::dollars(40_000), support::dollars(40_000)]);
    fixture.process_batches = Some(300);
    let (_, closed) = close(&fixture);
    assert!(closed
        .household_demand
        .iter()
        .all(|row| row.fulfilled_quantity == 100 && row.unit_price == support::dollars(4)));
    let produced = closed
        .production
        .iter()
        .find(|row| row.site_id == support::site(support::RETAILER))
        .expect("the retailer runs the process")
        .produced_batches;
    assert_eq!(produced, 100);
}

#[test]
fn too_few_hands_make_a_short_market() {
    let mut fixture = three_accounts(300);
    fixture.hours = 240;
    let (_, closed) = close(&fixture);
    assert_eq!(closed.market_clearings.len(), 1);
    assert_eq!(closed.market_clearings[0].supply, 240);
    assert!(closed.market_clearings[0].clearing_price > support::dollars(4));
}
