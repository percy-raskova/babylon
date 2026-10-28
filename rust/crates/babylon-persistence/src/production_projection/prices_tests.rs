//! Prices are committed consequences of the actual close, not reader-side plans.
use super::{lifecycle, recurring_fixture, ProductionProjectionError};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{MaterialCatalog, MaterialCircuitState};
use babylon_tick::material_world;
use babylon_tick::material_world::{MaterialTickReceipts, MaterialWorldRegister};

type Pair = (
    MaterialCircuitState,
    MaterialCircuitState,
    MaterialTickReceipts,
    MaterialCatalog,
);

fn actual_close() -> Pair {
    let (catalog, state) = recurring_fixture::materials();
    let prior = MaterialWorldRegister::try_new(&catalog, 0, state)
        .expect("the authored fixture satisfies the constructor invariants");
    let next = prior
        .prepare_next(&catalog)
        .expect("the fixture prepares the authored state");
    (
        prior.state().clone(),
        next.register().state().clone(),
        material_world::decode_material_receipts(next.receipt_bytes())
            .expect("the canonical bytes decode into the declared type"),
        catalog,
    )
}

#[test]
fn committed_goods_quotes_require_each_captured_offer_and_actual_prior_price() {
    let (prior, current, receipt, catalog) = actual_close();
    assert_eq!(receipt.prices.len(), 3);
    lifecycle::validate_period(&catalog, &prior, &current, &receipt)
        .expect("the authored fixture satisfies the rule");
    let mut missing = receipt.clone();
    missing.prices.pop();
    assert!(matches!(
        lifecycle::validate_period(&catalog, &prior, &current, &missing),
        Err(ProductionProjectionError::State)
    ));
    let mut altered = receipt.clone();
    altered.prices[0].old_price = Currency::from_micro_units(77);
    assert!(matches!(
        lifecycle::validate_period(&catalog, &prior, &current, &altered),
        Err(ProductionProjectionError::State)
    ));
    let mut duplicated = receipt.clone();
    duplicated.prices.push(receipt.prices[0].clone());
    assert!(matches!(
        lifecycle::validate_period(&catalog, &prior, &current, &duplicated),
        Err(ProductionProjectionError::State)
    ));
}

#[test]
fn actual_direct_cost_quote_joins_produced_and_released_quantities() {
    use babylon_material_circuit::{
        CircuitAccounting, GoodsPriceCostBasis, PriceDecision, PricePolicy, SiteId,
    };
    let (catalog, mut state) = recurring_fixture::materials();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("paid control")
    };
    let offer = economy
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .offers
        .iter_mut()
        .find(|r| r.site_id == SiteId::from_bytes([2; 32]))
        .expect("the fixture holds the searched element");
    offer.unit_price = Currency::from_micro_units(2);
    offer.pricing = PricePolicy::Responsive {
        minimum: Currency::from_micro_units(1),
        maximum: Currency::from_micro_units(8),
        step: Currency::from_micro_units(1),
        target_stock: 100,
    };
    let prior = MaterialWorldRegister::try_new(&catalog, 0, state)
        .expect("the authored fixture satisfies the constructor invariants");
    let next = prior
        .prepare_next(&catalog)
        .expect("the fixture prepares the authored state");
    let receipt = material_world::decode_material_receipts(next.receipt_bytes())
        .expect("the canonical bytes decode into the declared type");
    lifecycle::validate_period(&catalog, prior.state(), next.register().state(), &receipt)
        .expect("the authored fixture satisfies the rule");
    let producer = receipt
        .prices
        .iter()
        .find(|r| r.site_id == SiteId::from_bytes([2; 32]))
        .expect("the fixture holds the searched element");
    assert_eq!(producer.reason, PriceDecision::CostPressure);
    assert_eq!(
        (
            producer.old_price.micro_units(),
            producer.next_price.micro_units()
        ),
        (2, 3)
    );
    assert_eq!(producer.cost.basis, GoodsPriceCostBasis::Produced);
    assert_eq!(
        (
            producer.cost.quantity,
            producer.cost.carrying_cost.micro_units()
        ),
        (4, 12)
    );
    let retailer = receipt
        .prices
        .iter()
        .find(|r| r.site_id == SiteId::from_bytes([3; 32]))
        .expect("the fixture holds the searched element");
    assert_eq!(retailer.cost.basis, GoodsPriceCostBasis::Released);
    assert_eq!(
        (
            retailer.cost.quantity,
            retailer.cost.handling_wages.micro_units()
        ),
        (4, 4)
    );
    let accounts = super::prices::project_with_labels(
        &catalog,
        next.register().state(),
        Some(prior.state()),
        Some(&receipt),
        |_, _| Some(("good".to_owned(), "units".to_owned())),
    )
    .expect("the fixture projection accepts the authored input");
    assert_eq!(accounts.len(), 3);
    assert_eq!(
        accounts[1]
            .completed
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .unit_cost_micro,
        Some(3)
    );
    for mutation in 0..3 {
        let mut changed = receipt.clone();
        match mutation {
            0 => changed.prices[1].cost.quantity += 1,
            1 => changed.prices[1].cost.basis = GoodsPriceCostBasis::Released,
            _ => changed.prices[2].cost.handling_wages = Currency::from_micro_units(5),
        }
        assert!(matches!(
            lifecycle::validate_period(&catalog, prior.state(), next.register().state(), &changed),
            Err(ProductionProjectionError::State)
        ));
    }
}
