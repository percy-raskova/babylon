//! The seller plans from what was wanted: a buyer that was priced out raises the seller's next
//! plan and steps its posted price up, and a short market closes its gap within a few periods.

use super::service_support::{Funded, ServiceFixture, UTILITY};
use super::support::{self, Fixture};
use babylon_material_circuit::{
    MaterialCircuitState, MaterialCircuitTransition, PriceDecision, PricePolicy,
    ServicePriceDecision,
};

fn advance(fixture: &Fixture, state: &MaterialCircuitState) -> MaterialCircuitTransition {
    let (catalog, _) = fixture.build();
    babylon_material_circuit::advance_material_circuit(&catalog, state)
        .expect("the fixture period closes")
}

/// Two households that ask for 100 units each, with money for all of it, at a retailer that makes
/// the good itself from hours and plans nothing for the first period.
fn retailer_that_makes_its_shelf(stock: u64) -> Fixture {
    let mut fixture = Fixture::new(stock, &[support::dollars(40_000), support::dollars(40_000)]);
    fixture.process_batches = Some(1);
    fixture.makes_shelf = true;
    fixture
}

fn responsive() -> PricePolicy {
    PricePolicy::Responsive {
        minimum: support::dollars(1),
        maximum: support::dollars(10),
        step: support::dollars(1),
        target_stock: 10,
    }
}

fn retailer_plan(closed: &MaterialCircuitTransition) -> (u64, u64, u64) {
    let plan = closed
        .production_plans
        .iter()
        .find(|row| row.site_id == support::site(support::RETAILER))
        .expect("the retailer plans its process");
    (
        plan.dispatched_quantity,
        plan.unshipped_quantity,
        plan.planned_batches,
    )
}

#[test]
fn a_priced_out_buyer_raises_next_periods_plan() {
    let fixture = retailer_that_makes_its_shelf(150);
    let (_, state) = fixture.build();
    let closed = advance(&fixture, &state);
    assert_eq!(closed.market_clearings.len(), 1);
    assert_eq!(closed.market_clearings[0].demand_at_quote, 200);
    assert_eq!(closed.market_clearings[0].sold_quantity, 150);
    // 150 went out and 1 batch was made. The 50 that the price kept from buyers were wanted and not
    // served, so the plan covers 150 + 50 less the 1 on the shelf.
    assert_eq!(retailer_plan(&closed), (150, 50, 199));
}

#[test]
fn the_posted_price_steps_up_after_buyers_are_priced_out() {
    let mut fixture = retailer_that_makes_its_shelf(150);
    fixture.pricing = responsive();
    let (_, state) = fixture.build();
    let closed = advance(&fixture, &state);
    let row = closed
        .prices
        .iter()
        .find(|row| row.site_id == support::site(support::RETAILER))
        .expect("the retailer's good is priced");
    assert_eq!(row.reason, PriceDecision::UnservedDemand);
    assert_eq!(row.unserved_quantity, 50);
    assert_eq!(row.next_price, support::dollars(5));
    // A shelf that was enough leaves nothing priced out, and the price holds.
    let mut enough = fixture.clone();
    enough.shelves[0].stock = 200;
    let (_, state) = enough.build();
    let closed = advance(&enough, &state);
    assert_eq!(closed.prices[0].reason, PriceDecision::Hold);
    assert_eq!(closed.prices[0].next_price, support::dollars(4));
}

#[test]
fn a_priced_out_goods_price_stays_inside_its_bounds() {
    // The posted price is the maximum: buyers priced out cannot lift it past its bound.
    let mut fixture = retailer_that_makes_its_shelf(150);
    fixture.pricing = PricePolicy::Responsive {
        minimum: support::dollars(1),
        maximum: support::dollars(4),
        step: support::dollars(1),
        target_stock: 10,
    };
    let (_, state) = fixture.build();
    let closed = advance(&fixture, &state);
    assert_eq!(closed.market_clearings.len(), 1);
    assert_eq!(closed.market_clearings[0].demand_at_quote, 200);
    let row = closed
        .prices
        .iter()
        .find(|row| row.site_id == support::site(support::RETAILER))
        .expect("the retailer's good is priced");
    assert_eq!(row.unserved_quantity, 50);
    assert_eq!(row.old_price, support::dollars(4));
    assert_eq!(row.next_price, support::dollars(4));
}

fn short_utility(provider_hours: u64) -> ServiceFixture {
    let mut fixture = ServiceFixture::new(
        &[support::dollars(400), support::dollars(600)],
        &[vec![(UTILITY, 100)], vec![(UTILITY, 100)]],
    );
    fixture.utility_capacity = 1_000;
    fixture.utility_hours = Some(provider_hours);
    fixture.utility_pricing = PricePolicy::ServiceResponsive {
        minimum: support::dollars(1),
        maximum: support::dollars(10),
        step: support::dollars(1),
    };
    fixture
}

fn utility_market(closed: &MaterialCircuitTransition) -> (ServicePriceDecision, i128, i128) {
    let row = closed
        .service_markets
        .iter()
        .find(|row| row.good_id == support::good(UTILITY))
        .expect("the utility has a market receipt");
    (
        row.reason,
        row.old_price.micro_units(),
        row.next_price.micro_units(),
    )
}

#[test]
fn a_priced_out_service_buyer_steps_the_utility_up_even_with_spare_capacity() {
    let (catalog, state) = short_utility(150).build();
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes");
    assert_eq!(closed.market_clearings.len(), 1);
    let row = &closed.service_markets[0];
    assert!(row.performed_quantity < row.available_capacity);
    assert_eq!(row.admitted_quantity, row.performed_quantity);
    assert_eq!(
        utility_market(&closed),
        (ServicePriceDecision::PricedOut, 4_000_000, 5_000_000)
    );
    // Enough hands for everyone: nobody is priced out and the spare capacity steps the price down.
    let (catalog, state) = short_utility(1_000).build();
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes");
    assert_eq!(closed.market_clearings.len(), 0);
    assert_eq!(
        utility_market(&closed),
        (ServicePriceDecision::SpareCapacity, 4_000_000, 3_000_000)
    );
}

#[test]
fn a_priced_out_service_price_stays_inside_its_bounds() {
    let mut fixture = short_utility(150);
    fixture.utility_pricing = PricePolicy::ServiceResponsive {
        minimum: support::dollars(1),
        maximum: support::money(4_500_000),
        step: support::dollars(1),
    };
    let (catalog, state) = fixture.build();
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes");
    assert_eq!(
        utility_market(&closed),
        (ServicePriceDecision::PricedOut, 4_000_000, 4_500_000)
    );
}

#[test]
fn a_run_of_three_periods_closes_the_gap() {
    // The retailer keeps 200 ready beyond what it sold, and made 200 in the first period.
    let mut fixture = retailer_that_makes_its_shelf(150);
    fixture.process_batches = Some(200);
    fixture.output_buffer = 200;
    let (_, opening) = fixture.build();
    let first = advance(&fixture, &opening);
    assert_eq!(first.market_clearings.len(), 1);
    assert_eq!(first.market_clearings[0].demand_at_quote, 200);
    // 150 sent, 50 priced out and 200 ready, less the 200 on the shelf at the close: the second
    // period makes 200. Counting only what was sent it would make 150.
    assert_eq!(retailer_plan(&first), (150, 50, 200));
    let second = advance(&fixture, &first.state);
    assert_eq!(second.market_clearings.len(), 0);
    let third = advance(&fixture, &second.state);
    assert_eq!(third.market_clearings.len(), 0);
    // The households spent what they had at the market's price in the first period, so the third
    // is limited by their purses, not by the shelf: it holds all 200 and sells at the posted price.
    assert!(second
        .household_demand
        .iter()
        .all(|row| row.unit_price == support::dollars(4) && row.fulfilled_quantity == 100));
    let shelf = |state: &MaterialCircuitState| {
        state
            .inventory
            .iter()
            .find(|row| row.good_id == support::good(2))
            .map(|row| row.quantity)
    };
    assert_eq!(shelf(&second.state), Some(200));
    assert!(third
        .household_demand
        .iter()
        .all(|row| row.unit_price == support::dollars(4) && row.fulfilled_quantity > 0));
}

/// The utility's receipt of the period: what was asked, and what it plans for the next.
fn utility_plan(closed: &MaterialCircuitTransition) -> (u64, u64, ServicePriceDecision) {
    let row = closed
        .service_markets
        .iter()
        .find(|row| row.good_id == support::good(UTILITY))
        .expect("the utility has a market receipt");
    (row.requested_quantity, row.planned_quantity, row.reason)
}

fn close_service(fixture: &ServiceFixture) -> MaterialCircuitTransition {
    let (catalog, state) = fixture.build();
    babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes")
}

/// One household that asks for 40 units of utility at $4 with money for 25 of them.
fn buyers_who_can_pay_for_25() -> ServiceFixture {
    ServiceFixture::new(&[support::dollars(100)], &[vec![(UTILITY, 40)]])
}

#[test]
fn a_service_staffs_for_what_buyers_could_pay_for() {
    let closed = close_service(&buyers_who_can_pay_for_25());
    let (requested, planned, _) = utility_plan(&closed);
    // What was asked stays on the receipt; the plan is what the buyers could pay for.
    assert_eq!((requested, planned), (40, 25));
}

#[test]
fn an_order_funded_earlier_counts_in_the_plan() {
    // One account needs 20 and holds a funded order for 10; with the $40 it has left it can pay for
    // the other 10. Another asks for 40 and can pay for 15. The buyers could pay for 25 new units
    // and 10 are owed, so the plan is 35.
    let mut fixture = ServiceFixture::new(
        &[support::dollars(80), support::dollars(60)],
        &[vec![(UTILITY, 20)], vec![(UTILITY, 40)]],
    );
    fixture.funded = vec![Funded {
        buyer: 0,
        service: UTILITY,
        quantity: 10,
        price: support::dollars(4),
        order: 7,
    }];
    let closed = close_service(&fixture);
    let (_, planned, _) = utility_plan(&closed);
    assert_eq!(planned, 35);
}

#[test]
fn buyers_who_return_are_planned_for_after_one_period() {
    // Period 1: nobody has money, so nobody bids and the provider plans nothing.
    let mut broke = buyers_who_can_pay_for_25();
    broke.purses = vec![support::dollars(0)];
    let (requested, planned, _) = utility_plan(&close_service(&broke));
    assert_eq!((requested, planned), (40, 0));
    // Period 2: the provider has no hands, the buyers can pay for 30, so they are priced out of an
    // empty market with the reason `PricedOut` and the plan for the next period is 30.
    let mut returned = ServiceFixture::new(&[support::dollars(120)], &[vec![(UTILITY, 40)]]);
    returned.utility_hours = Some(0);
    returned.utility_pricing = PricePolicy::ServiceResponsive {
        minimum: support::dollars(1),
        maximum: support::dollars(10),
        step: support::dollars(1),
    };
    let closed = close_service(&returned);
    assert_eq!(closed.market_clearings.len(), 1);
    assert_eq!(closed.market_clearings[0].supply, 0);
    let (_, planned, reason) = utility_plan(&closed);
    assert_eq!((planned, reason), (30, ServicePriceDecision::PricedOut));
}

#[test]
fn without_a_market_policy_a_service_plans_for_what_was_asked() {
    let mut fixture = buyers_who_can_pay_for_25();
    fixture.paying_order = None;
    let (requested, planned, _) = utility_plan(&close_service(&fixture));
    assert_eq!((requested, planned), (40, 40));
}
