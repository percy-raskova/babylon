//! Households' wants are admitted with the catalog and the state. Until a tier buys them they
//! change nothing.

use super::support::{self, Fixture, Shelf};
use babylon_material_circuit::{
    CircuitAccounting, MaterialCircuitState, MaterialCircuitTransition, WantTier,
};

fn shelves() -> Fixture {
    let mut fixture = Fixture::new(
        240,
        &[
            support::dollars(400),
            support::dollars(600),
            support::dollars(40_000),
        ],
    );
    fixture.shelves.push(Shelf {
        good: 3,
        price: support::dollars(10),
        stock: 50,
        needed: false,
    });
    fixture.paying_order = Some(vec![2, 3]);
    fixture
}

fn close(fixture: &Fixture) -> MaterialCircuitTransition {
    let (catalog, state) = fixture.build();
    babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes")
}

/// The closed state without its purchase rows for products no account needs.
fn without_want_rows(mut state: MaterialCircuitState) -> MaterialCircuitState {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the fixture is monetary")
    };
    let recurring = economy.recurring.as_mut().expect("a recurring economy");
    let stocked: Vec<_> = recurring
        .household_stocks
        .iter()
        .map(|row| (row.principal_id, row.good_id, row.unit_id))
        .collect();
    recurring
        .household_purchases
        .retain(|row| stocked.contains(&(row.principal_id, row.good_id, row.unit_id)));
    state
}

#[test]
fn declared_wants_change_nothing_yet() {
    let plain = close(&shelves());
    let mut wanting = shelves();
    wanting.household_wants = vec![
        (0, WantTier::Comfort, 2, 3),
        (1, WantTier::Comfort, 2, 2),
        (2, WantTier::Comfort, 3, 4),
    ];
    let wanted = close(&wanting);
    assert_eq!(plain.household_demand.len(), 3);
    assert_eq!(wanted.household_demand, plain.household_demand);
    assert_eq!(wanted.household_consumption, plain.household_consumption);
    assert_eq!(wanted.market_clearings, plain.market_clearings);
    assert_eq!(wanted.money_transfers, plain.money_transfers);
    assert_eq!(wanted.prices, plain.prices);
    assert_eq!(wanted.local_fulfillments, plain.local_fulfillments);
    assert_eq!(wanted.handling, plain.handling);
    assert_eq!(wanted.deliveries, plain.deliveries);
    assert_eq!(without_want_rows(wanted.state), plain.state);
}
