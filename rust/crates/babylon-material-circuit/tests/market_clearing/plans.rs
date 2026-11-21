//! The seller plans from what was wanted: a buyer that was priced out raises the seller's next
//! plan and steps its posted price up, and a short market closes its gap within a few periods.

use super::service_support::{ServiceFixture, UTILITY};
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
