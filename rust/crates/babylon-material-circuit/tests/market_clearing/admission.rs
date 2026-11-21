//! A product that clears by price has no seller with a fixed price (P12).

use super::service_support::{ServiceFixture, LOCAL, UTILITY};
use super::support::{self, Fixture};
use babylon_material_circuit::{
    MaterialCatalog, MaterialCircuitError, MaterialCircuitState, MaterialCircuitTransition,
};

fn close(
    built: &(MaterialCatalog, MaterialCircuitState),
) -> Result<MaterialCircuitTransition, MaterialCircuitError> {
    babylon_material_circuit::advance_material_circuit(&built.0, &built.1)
}

fn goods() -> Fixture {
    Fixture::new(
        240,
        &[
            support::dollars(400),
            support::dollars(600),
            support::dollars(40_000),
        ],
    )
}

fn services() -> ServiceFixture {
    let wants = vec![vec![(LOCAL, 50)], vec![(LOCAL, 50)]];
    ServiceFixture::new(&[support::dollars(400), support::dollars(600)], &wants)
}

#[test]
fn a_fixed_price_seller_of_a_priced_good_is_refused() {
    let mut fixture = goods();
    fixture.keep_fixed = true;
    assert_eq!(
        close(&fixture.build()).err(),
        Some(MaterialCircuitError::MarketClearingInvariant)
    );
}

#[test]
fn a_fixed_price_provider_of_a_priced_service_is_refused() {
    let mut fixture = services();
    fixture.keep_fixed = true;
    assert_eq!(
        close(&fixture.build()).err(),
        Some(MaterialCircuitError::MarketClearingInvariant)
    );
}

#[test]
fn a_fixed_price_is_admitted_for_a_service_left_out_of_the_order() {
    let mut with = services();
    with.paying_order = Some(vec![UTILITY]);
    with.utility_pricing = support::pinned(super::service_support::posted(UTILITY), true);
    with.keep_fixed = true;
    let mut without = with.clone();
    without.paying_order = None;
    let with = close(&with.build()).expect("the period closes");
    let without = close(&without.build()).expect("the period closes");
    assert_eq!(with.service_markets, without.service_markets);
    assert_eq!(with.service_performance, without.service_performance);
    assert_eq!(with.household_demand, without.household_demand);
}

#[test]
fn without_a_market_policy_a_fixed_price_is_admitted() {
    let mut fixture = goods();
    fixture.paying_order = None;
    fixture.keep_fixed = true;
    let closed = close(&fixture.build()).expect("the period closes");
    assert_eq!(closed.market_clearings.len(), 0);
}
