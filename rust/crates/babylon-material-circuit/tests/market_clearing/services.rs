//! Services clear in their stage: the price is found when the stage's output is known, and an order
//! that was funded earlier for the period keeps its price and is served first.

use super::service_support::{self, Funded, ServiceFixture, LOCAL, PUBLIC, UTILITY};
use super::support;
use babylon_material_circuit::{
    AccountId, MarketMoment, MaterialCircuitTransition, MoneyTransferPurpose, OrderId,
    OutboundOrderId, ServicePerformanceReceipt,
};

fn close(fixture: &ServiceFixture) -> MaterialCircuitTransition {
    let (catalog, state) = fixture.build();
    babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes")
}

fn rows_of(closed: &MaterialCircuitTransition, service: u8) -> Vec<&ServicePerformanceReceipt> {
    closed
        .service_performance
        .iter()
        .filter(|row| row.good_id == service_support::service_good(service))
        .collect()
}

/// What providers were paid for services performed, from the money movements.
fn settled(closed: &MaterialCircuitTransition) -> i128 {
    closed
        .money_transfers
        .iter()
        .filter(|row| {
            matches!(
                row.purpose,
                MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::Service(_))
            )
        })
        .map(|row| row.credit.delta.micro_units())
        .sum()
}

fn paid(rows: &[&ServicePerformanceReceipt]) -> i128 {
    rows.iter()
        .map(|row| row.unit_price.micro_units() * i128::from(row.performed_quantity))
        .sum()
}

#[test]
fn a_short_utility_is_priced_in_its_stage() {
    let mut fixture = ServiceFixture::new(
        &[support::dollars(400), support::dollars(600)],
        &[vec![(UTILITY, 100)], vec![(UTILITY, 100)]],
    );
    fixture.utility_capacity = 240;
    fixture.business = Some(support::dollars(40_000));
    let closed = close(&fixture);
    let rows = rows_of(&closed, UTILITY);
    let mut summary: Vec<_> = rows
        .iter()
        .map(|row| {
            (
                matches!(row.buyer, AccountId::Site(_)),
                row.unit_price.micro_units(),
                row.admitted_quantity,
            )
        })
        .collect();
    summary.sort_unstable();
    assert_eq!(
        summary,
        vec![
            (false, 7_058_824, 56),
            (false, 7_058_824, 84),
            (true, 7_058_824, 100)
        ]
    );
    for row in &rows {
        assert_eq!(row.performed_quantity, row.admitted_quantity);
        assert_eq!(row.expired_quantity, 0);
        assert_eq!(row.requested_quantity, 100);
    }
    assert_eq!(settled(&closed), paid(&rows));
    assert_eq!(closed.market_clearings.len(), 1);
    let market = &closed.market_clearings[0];
    assert_eq!(market.moment, MarketMoment::Utility);
    assert_eq!(
        (market.supply, market.demand_at_quote, market.sold_quantity),
        (240, 300, 240)
    );
    assert_eq!((market.bidders, market.served_bidders), (3, 3));
}

#[test]
fn utility_is_paid_before_the_local_service() {
    let mut fixture = ServiceFixture::new(
        &[support::dollars(500), support::dollars(10_000)],
        &[
            vec![(UTILITY, 100), (LOCAL, 100)],
            vec![(UTILITY, 100), (LOCAL, 100)],
        ],
    );
    fixture.utility_capacity = 100;
    let closed = close(&fixture);
    let first = |service: u8| -> Vec<(i128, u64)> {
        rows_of(&closed, service)
            .iter()
            .map(|row| (row.unit_price.micro_units(), row.admitted_quantity))
            .collect()
    };
    let mut utility = first(UTILITY);
    utility.sort_unstable();
    assert_eq!(utility, vec![(103_092_784, 4), (103_092_784, 96)]);
    // Each account paid the higher price for the utility it got; what is left of its cash buys fewer
    // units of the ample local service than it wanted, at the posted price.
    let mut local = first(LOCAL);
    local.sort_unstable();
    assert_eq!(local, vec![(3_000_000, 29), (3_000_000, 34)]);
    assert_eq!(closed.market_clearings.len(), 1);
    assert_eq!(closed.market_clearings[0].moment, MarketMoment::Utility);
}

#[test]
fn an_order_funded_earlier_is_served_first() {
    let mut fixture = ServiceFixture::new(
        &[support::dollars(1_000), support::dollars(1_000)],
        &[vec![(UTILITY, 100)], vec![(UTILITY, 50)]],
    );
    fixture.utility_capacity = 60;
    fixture.funded = vec![Funded {
        buyer: 0,
        service: UTILITY,
        quantity: 50,
        price: support::dollars(4),
        order: 7,
    }];
    let closed = close(&fixture);
    let rows = rows_of(&closed, UTILITY);
    let funded = rows
        .iter()
        .find(|row| row.order_id == OrderId::from_bytes([7; 32]))
        .expect("the funded order is in the close");
    assert_eq!(
        (
            funded.admitted_quantity,
            funded.performed_quantity,
            funded.unit_price
        ),
        (50, 50, support::dollars(4))
    );
    assert_eq!(closed.market_clearings.len(), 1);
    let market = &closed.market_clearings[0];
    assert_eq!((market.supply, market.sold_quantity), (10, 10));
    assert_eq!(market.clearing_price.micro_units(), 160_000_001);
    // The household that holds the funded order has less cash left, so it buys fewer of the rest.
    let mut fresh: Vec<_> = rows
        .iter()
        .filter(|row| row.order_id != funded.order_id)
        .map(|row| {
            (
                row.unit_price.micro_units(),
                row.admitted_quantity,
                row.expired_quantity,
            )
        })
        .collect();
    fresh.sort_unstable_by_key(|row| row.1);
    assert_eq!(fresh, vec![(160_000_001, 4, 0), (160_000_001, 6, 0)]);
    assert_eq!(settled(&closed), paid(&rows));
    let sorted: Vec<_> = closed
        .service_performance
        .iter()
        .map(|row| row.order_id)
        .collect();
    assert!(sorted.windows(2).all(|pair| pair[0] < pair[1]));
}

#[test]
fn public_provision_is_still_shared() {
    let mut fixture = ServiceFixture::new(
        &[support::dollars(1_000), support::dollars(1_000)],
        &[vec![(PUBLIC, 100)], vec![(PUBLIC, 100)]],
    );
    fixture.public_capacity = 60;
    let closed = close(&fixture);
    let rows = rows_of(&closed, PUBLIC);
    assert_eq!(rows.len(), 2);
    for row in &rows {
        assert_eq!(row.unit_price, service_support::posted(PUBLIC));
        assert_eq!(
            (
                row.admitted_quantity,
                row.performed_quantity,
                row.expired_quantity
            ),
            (100, 30, 70)
        );
    }
    assert_eq!(closed.market_clearings, vec![]);
}

#[test]
fn a_stage_two_order_does_not_appear_in_stage_one() {
    let mut fixture = ServiceFixture::new(
        &[support::dollars(1_000)],
        &[vec![(UTILITY, 10), (LOCAL, 10)]],
    );
    fixture.funded = vec![
        Funded {
            buyer: 0,
            service: UTILITY,
            quantity: 10,
            price: support::dollars(4),
            order: 7,
        },
        Funded {
            buyer: 0,
            service: LOCAL,
            quantity: 10,
            price: support::dollars(3),
            order: 8,
        },
    ];
    let closed = close(&fixture);
    for id in [7_u8, 8] {
        let count = closed
            .service_performance
            .iter()
            .filter(|row| row.order_id == OrderId::from_bytes([id; 32]))
            .count();
        assert_eq!(count, 1, "order {id} appears once");
    }
    assert!(closed
        .service_performance
        .iter()
        .all(|row| row.performed_quantity == row.admitted_quantity));
}

#[test]
fn without_a_market_policy_services_are_admitted_at_the_start() {
    let mut fixture = ServiceFixture::new(
        &[support::dollars(400), support::dollars(600)],
        &[vec![(UTILITY, 100)], vec![(UTILITY, 100)]],
    );
    fixture.utility_capacity = 240;
    fixture.business = Some(support::dollars(40_000));
    fixture.paying_order = None;
    let closed = close(&fixture);
    let rows = rows_of(&closed, UTILITY);
    assert_eq!(rows.len(), 3);
    for row in &rows {
        assert_eq!(row.unit_price, service_support::posted(UTILITY));
        assert_eq!(
            (
                row.admitted_quantity,
                row.performed_quantity,
                row.expired_quantity
            ),
            (100, 80, 20)
        );
    }
    assert_eq!(closed.market_clearings, vec![]);
    let _ = support::units();
}
