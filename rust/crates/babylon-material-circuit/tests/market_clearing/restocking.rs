//! Businesses restock at the price of the market: each business bids for a short input up to the
//! price at which its own product stops paying, and what the route cannot carry is cancelled.

use super::restock_support::{self, Buyer, Restock, Supplier, Use, INPUT, WAGE};
use super::support;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, MarketMoment, MaterialCircuitState, MaterialCircuitTransition,
    MoneyTransferPurpose, OutboundOrderId, SiteId,
};

fn close(fixture: &Restock) -> (MaterialCircuitState, MaterialCircuitTransition) {
    let (catalog, state) = fixture.build();
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes");
    (state, closed)
}

fn cash(state: &MaterialCircuitState, site: SiteId) -> i128 {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        panic!("the fixture is monetary")
    };
    economy
        .book
        .cash(AccountId::Site(site))
        .expect("the account exists")
        .micro_units()
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

/// What each buyer bought and at what price, in the order of the buyers.
fn bought(closed: &MaterialCircuitTransition) -> Vec<(u64, i128)> {
    closed
        .procurement
        .iter()
        .map(|row| (row.admitted_quantity, row.unit_price.micro_units()))
        .collect()
}

fn reserved(closed: &MaterialCircuitTransition) -> i128 {
    closed
        .money_transfers
        .iter()
        .filter(|row| {
            matches!(
                row.purpose,
                MoneyTransferPurpose::PurchaseReservation(OutboundOrderId::Delivery(_))
            )
        })
        .map(|row| row.credit.delta.micro_units())
        .sum()
}

fn refunded(closed: &MaterialCircuitTransition) -> i128 {
    closed
        .money_transfers
        .iter()
        .filter(|row| {
            matches!(
                row.purpose,
                MoneyTransferPurpose::PurchaseRefund(OutboundOrderId::Delivery(_))
            )
        })
        .map(|row| row.credit.delta.micro_units())
        .sum()
}

fn supplier(stock: u64) -> Supplier {
    Supplier {
        stock,
        price: support::dollars(100),
    }
}

#[test]
fn a_maker_stops_bidding_at_its_cost_price() {
    // One batch of the first maker's product earns $250 less $5 of wages: it pays up to $245. The
    // second earns $111 less $5: up to $106. The posted price is $100 and 80 units are on offer.
    let fixture = Restock::new(
        vec![supplier(80)],
        vec![
            Buyer::maker(support::dollars(15_000), support::dollars(250), 100),
            Buyer::maker(support::dollars(1_000_000), support::dollars(111), 100),
        ],
    );
    let (opening, closed) = close(&fixture);
    // The first maker's purse is its cash less the wages of its ten hours.
    let purse = support::dollars(15_000).micro_units() - 10 * WAGE * 1_000_000;
    // The least price at which it can no longer pay for more than 80 units.
    let price = purse / 81 + 1;
    assert_eq!(bought(&closed), vec![(80, price), (0, 100_000_000)]);
    assert!(price > 106_000_000 && price <= 245_000_000);
    assert_eq!(closed.state.orders.len(), 1);
    assert_eq!(
        closed.state.orders[0].buyer_site_id,
        restock_support::buyer_site(0)
    );
    assert_eq!(reserved(&closed), 80 * price);
    assert_eq!(total(&opening), total(&closed.state));
    assert_eq!(closed.market_clearings.len(), 1);
    let market = &closed.market_clearings[0];
    assert_eq!(market.moment, MarketMoment::Restocking);
    assert_eq!(
        (
            market.site_id,
            market.supply,
            market.demand_at_quote,
            market.sold_quantity,
            market.bidders,
            market.served_bidders
        ),
        (restock_support::supplier_site(0), 80, 200, 80, 2, 1)
    );
    assert_eq!(market.good_id, support::good(INPUT));
    assert_eq!(market.unit_id, support::units());
}

#[test]
fn a_maker_below_its_cost_buys_at_the_posted_price_only() {
    // Both earn $80 less $5 of wages: under the posted $100, so neither outbids it.
    let fixture = Restock::new(
        vec![supplier(120)],
        vec![
            Buyer::maker(support::dollars(1_000_000), support::dollars(80), 100),
            Buyer::maker(support::dollars(1_000_000), support::dollars(80), 100),
        ],
    );
    let (opening, closed) = close(&fixture);
    assert_eq!(bought(&closed), vec![(60, 100_000_000), (60, 100_000_000)]);
    assert_eq!(
        closed.market_clearings[0].clearing_price,
        support::dollars(100)
    );
    assert_eq!(total(&opening), total(&closed.state));
}

#[test]
fn a_merchant_stops_at_its_own_price_less_handling() {
    // The merchant sells the input at $130 and pays $5 of wages to hand a unit over: it pays up to
    // $125. The maker pays up to $128. With 150 units on offer the merchant drops out above $125,
    // and the price stays at its limit; without the handling wage it would have gone to $128.
    let merchant = Buyer {
        cash: support::dollars(1_000_000),
        uses: Use::Sells(support::dollars(130)),
        wanted: 100,
        hours: 10,
        route_units: 1_000_000,
    };
    let maker = Buyer::maker(support::dollars(1_000_000), support::dollars(133), 100);
    let fixture = Restock::new(vec![supplier(150)], vec![merchant, maker]);
    let (opening, closed) = close(&fixture);
    assert_eq!(bought(&closed), vec![(50, 125_000_000), (100, 125_000_000)]);
    assert_eq!(total(&opening), total(&closed.state));
}

#[test]
fn nothing_is_ordered_from_an_empty_supplier() {
    let fixture = Restock::new(
        vec![supplier(0)],
        vec![
            Buyer::maker(support::dollars(1_000_000), support::dollars(250), 100),
            Buyer::maker(support::dollars(1_000_000), support::dollars(250), 100),
        ],
    );
    let (opening, closed) = close(&fixture);
    assert_eq!(closed.state.orders.len(), 0);
    assert_eq!(reserved(&closed), 0);
    assert_eq!(bought(&closed), vec![(0, 100_000_000), (0, 100_000_000)]);
    assert_eq!(closed.market_clearings.len(), 1);
    let market = &closed.market_clearings[0];
    assert_eq!(
        (market.supply, market.sold_quantity, market.demand_at_quote),
        (0, 0, 200)
    );
    assert_eq!(market.clearing_price, market.quote_price);
    assert_eq!(market.quote_price, support::dollars(100));
    assert_eq!(total(&opening), total(&closed.state));
}

#[test]
fn goods_owed_to_an_earlier_order_are_not_sold_twice() {
    // The supplier holds 100 and owes 70 to an order made earlier, whose route is closed this
    // period, so 30 are on offer.
    let mut fixture = Restock::new(
        vec![supplier(100)],
        vec![
            Buyer::maker(support::dollars(1_000_000), support::dollars(250), 100),
            Buyer::maker(support::dollars(1_000_000), support::dollars(250), 100),
        ],
    );
    fixture.owed = 70;
    let (opening, closed) = close(&fixture);
    let market = &closed.market_clearings[0];
    assert_eq!(
        (market.supply, market.sold_quantity, market.demand_at_quote),
        (30, 30, 200)
    );
    let earlier: Vec<_> = closed
        .state
        .orders
        .iter()
        .filter(|row| row.buyer_site_id == super::support::site(90))
        .collect();
    assert_eq!(earlier.len(), 1);
    assert_eq!((earlier[0].ordered, earlier[0].shipped), (70, 0));
    assert_eq!(total(&opening), total(&closed.state));
}

#[test]
fn what_the_route_cannot_carry_is_cancelled_and_refunded() {
    let mut buyer = Buyer::maker(support::dollars(100_000), support::dollars(250), 100);
    buyer.hours = 0;
    buyer.route_units = 40;
    let fixture = Restock::new(vec![supplier(100)], vec![buyer]);
    let (catalog, opening) = fixture.build();
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the fixture period closes");
    assert_eq!(bought(&closed), vec![(100, 100_000_000)]);
    assert_eq!(closed.state.orders.len(), 1);
    let order = &closed.state.orders[0];
    assert_eq!((order.ordered, order.shipped), (40, 40));
    assert_eq!(
        cash(&opening, restock_support::buyer_site(0))
            - cash(&closed.state, restock_support::buyer_site(0)),
        40 * 100_000_000
    );
    assert_eq!(reserved(&closed), 100 * 100_000_000);
    assert_eq!(refunded(&closed), 60 * 100_000_000);
    let held = closed
        .state
        .inventory
        .iter()
        .find(|row| row.site_id == restock_support::supplier_site(0))
        .expect("the supplier keeps a row");
    assert_eq!(held.quantity, 60);
    assert_eq!(total(&opening), total(&closed.state));
    // Next period only what is in transit counts as arriving.
    let next = babylon_material_circuit::advance_material_circuit(&catalog, &closed.state)
        .expect("the next period closes");
    assert!(next.procurement[0].outstanding_inbound <= 40);
}

#[test]
fn an_order_nothing_of_which_moved_leaves_no_row() {
    let mut buyer = Buyer::maker(support::dollars(100_000), support::dollars(250), 100);
    buyer.hours = 0;
    buyer.route_units = 0;
    let fixture = Restock::new(vec![supplier(100)], vec![buyer]);
    let (opening, closed) = close(&fixture);
    assert_eq!(bought(&closed), vec![(100, 100_000_000)]);
    assert_eq!(closed.state.orders.len(), 0);
    assert_eq!(
        cash(&opening, restock_support::buyer_site(0)),
        cash(&closed.state, restock_support::buyer_site(0))
    );
    assert_eq!(reserved(&closed), refunded(&closed));
    let CircuitAccounting::Monetary(economy) = &closed.state.accounting else {
        panic!("the fixture is monetary")
    };
    assert_eq!(
        economy.book.snapshot().purchases.len(),
        0,
        "no principal is left open"
    );
    assert_eq!(total(&opening), total(&closed.state));
}

#[test]
fn a_second_supplier_sees_what_the_first_sold() {
    let mut buyer = Buyer::maker(support::dollars(1_000_000), support::dollars(250), 100);
    buyer.hours = 0;
    let fixture = Restock::new(vec![supplier(60), supplier(60)], vec![buyer]);
    let (opening, closed) = close(&fixture);
    let rows: Vec<_> = closed
        .procurement
        .iter()
        .map(|row| {
            (
                row.supplier_site_id,
                row.desired_quantity,
                row.outstanding_inbound,
                row.admitted_quantity,
            )
        })
        .collect();
    assert_eq!(
        rows,
        vec![
            (restock_support::supplier_site(0), 100, 0, 60),
            (restock_support::supplier_site(1), 40, 60, 40)
        ]
    );
    assert_eq!(total(&opening), total(&closed.state));
}
