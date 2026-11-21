//! Households buy the comforts and luxuries that are services in their stage, with the money their
//! needs do not use.

use super::service_support::{self, ServiceFixture, LOCAL, PUBLIC, UTILITY};
use super::support;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, HouseholdServiceReceipt, HouseholdStandard, MarketMoment,
    MaterialCircuitTransition, MoneyTransferPurpose, OrderId, OutboundOrderId,
    ServicePerformanceReceipt, WantTier,
};

fn close(fixture: &ServiceFixture) -> MaterialCircuitTransition {
    let (catalog, state) = fixture.build();
    babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes")
}

fn want_order(index: u8, service: u8, tier: WantTier) -> OrderId {
    babylon_material_circuit::recurring_service_want_order_id(
        1,
        service_support::account(index),
        support::site(service),
        service_support::service_good(service),
        support::units(),
        tier,
    )
}

fn performance_of(
    closed: &MaterialCircuitTransition,
    order: OrderId,
) -> Option<&ServicePerformanceReceipt> {
    closed
        .service_performance
        .iter()
        .find(|row| row.order_id == order)
}

fn rows_of(closed: &MaterialCircuitTransition, service: u8) -> Vec<&ServicePerformanceReceipt> {
    closed
        .service_performance
        .iter()
        .filter(|row| row.good_id == service_support::service_good(service))
        .collect()
}

fn household_rows(
    closed: &MaterialCircuitTransition,
    index: u8,
    service: u8,
) -> Vec<&HouseholdServiceReceipt> {
    closed
        .household_services
        .iter()
        .filter(|row| {
            row.principal_id == service_support::account(index)
                && row.good_id == service_support::service_good(service)
        })
        .collect()
}

fn purse(closed: &MaterialCircuitTransition, index: u8) -> Currency {
    let CircuitAccounting::Monetary(economy) = &closed.state.accounting else {
        panic!("the fixture is monetary")
    };
    economy
        .book
        .cash(AccountId::Household(service_support::account(index)))
        .expect("the account exists")
}

fn standard(closed: &MaterialCircuitTransition, index: u8) -> HouseholdStandard {
    babylon_material_circuit::household_standard(
        service_support::account(index),
        &closed.household_consumption,
        &closed.household_services,
        &closed.household_tiers,
    )
    .expect("the account's tiers are recorded")
}

fn want_receipt(
    closed: &MaterialCircuitTransition,
    index: u8,
    service: u8,
    tier: WantTier,
) -> (u64, u64) {
    let row = closed
        .household_wants
        .iter()
        .find(|row| {
            row.principal_id == service_support::account(index)
                && row.good_id == service_support::service_good(service)
                && row.tier == tier
        })
        .expect("the want has a row");
    (row.wanted_quantity, row.bought_quantity)
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
fn a_utility_comfort_keeps_the_money_for_a_local_need() {
    let mut fixture = ServiceFixture::new(&[support::dollars(500)], &[vec![(LOCAL, 100)]]);
    fixture.household_wants = vec![(0, WantTier::Comfort, UTILITY, 100)];
    let closed = close(&fixture);
    let row = performance_of(&closed, want_order(0, UTILITY, WantTier::Comfort))
        .expect("a want that money reaches has a performance row");
    assert_eq!(
        (
            row.requested_quantity,
            row.admitted_quantity,
            row.performed_quantity,
            row.unit_price.micro_units(),
            row.used_quantity,
            row.unused_quantity
        ),
        (50, 50, 50, 4_000_000, 50, 0)
    );
    let output = closed
        .service_outputs
        .iter()
        .find(|row| row.good_id == service_support::service_good(UTILITY))
        .expect("the utility produced");
    assert_eq!(output.produced_quantity, 50);
    let local = household_rows(&closed, 0, LOCAL);
    assert_eq!(local.len(), 1);
    assert_eq!(
        (
            local[0].satisfied_quantity,
            local[0].unmet_quantity,
            local[0].unused_quantity
        ),
        (100, 0, 0)
    );
    assert!(
        household_rows(&closed, 0, UTILITY).is_empty(),
        "a want is a use, not a need"
    );
    assert_eq!(
        want_receipt(&closed, 0, UTILITY, WantTier::Comfort),
        (100, 50)
    );
    assert_eq!(purse(&closed, 0).micro_units(), 0);
    assert_eq!(standard(&closed, 0), HouseholdStandard::GettingBy);
}

#[test]
fn a_short_local_service_sells_a_comfort_before_a_poor_need() {
    let mut fixture = ServiceFixture::new(
        &[support::dollars(150), support::dollars(10_000)],
        &[vec![(LOCAL, 100)], vec![(LOCAL, 50)]],
    );
    fixture.local_capacity = 100;
    fixture.household_wants = vec![(1, WantTier::Comfort, LOCAL, 100)];
    let closed = close(&fixture);
    let rows = rows_of(&closed, LOCAL);
    assert_eq!(rows.len(), 3);
    for row in &rows {
        assert_eq!(row.unit_price.micro_units(), 100_000_001);
    }
    let need = |index: u8| -> &ServicePerformanceReceipt {
        let order = babylon_material_circuit::recurring_service_order_id(
            1,
            AccountId::Household(service_support::account(index)),
            support::site(LOCAL),
            service_support::service_good(LOCAL),
            support::units(),
        );
        performance_of(&closed, order).expect("the need has a row")
    };
    assert_eq!(need(0).admitted_quantity, 1);
    assert_eq!(household_rows(&closed, 0, LOCAL)[0].unmet_quantity, 99);
    assert_eq!(need(1).admitted_quantity, 50);
    let comfort = performance_of(&closed, want_order(1, LOCAL, WantTier::Comfort))
        .expect("the comfort has a row");
    assert_eq!(comfort.admitted_quantity, 49);
    assert_eq!(closed.market_clearings.len(), 1);
    let market = &closed.market_clearings[0];
    assert_eq!(market.moment, MarketMoment::LocalService);
    assert_eq!(market.demand_at_quote, 200);
    assert_eq!(settled(&closed), paid(&rows));
}

#[test]
fn an_unfunded_want_leaves_the_plan_as_it_was() {
    let mut fixture = ServiceFixture::new(&[support::dollars(300)], &[vec![(LOCAL, 100)]]);
    fixture.household_wants = vec![(0, WantTier::Comfort, UTILITY, 100)];
    let closed = close(&fixture);
    assert!(
        performance_of(&closed, want_order(0, UTILITY, WantTier::Comfort)).is_none(),
        "money that cannot reach a want leaves no row"
    );
    let local = closed
        .service_markets
        .iter()
        .find(|row| row.good_id == service_support::service_good(LOCAL))
        .expect("the local service has a market row");
    assert_eq!(
        (local.requested_quantity, local.planned_quantity),
        (100, 100)
    );
    let utility = closed
        .service_markets
        .iter()
        .find(|row| row.good_id == service_support::service_good(UTILITY))
        .expect("the utility has a market row");
    assert_eq!(
        (utility.requested_quantity, utility.planned_quantity),
        (0, 0)
    );
    assert_eq!(
        want_receipt(&closed, 0, UTILITY, WantTier::Comfort),
        (100, 0)
    );
}

#[test]
fn a_public_need_bought_stops_reserving() {
    // The account has $100, needs 10 of the public service ($30) and wants 60 of the local service in
    // tier 3. The local market comes first, so its want still holds back the public need's $30 and
    // buys 23 of 60. The public need is then bought in full, out of exactly what was held back.
    let mut fixture = ServiceFixture::new(&[support::dollars(100)], &[vec![(PUBLIC, 10)]]);
    fixture.household_wants = vec![(0, WantTier::Luxury, LOCAL, 60)];
    let closed = close(&fixture);
    assert_eq!(want_receipt(&closed, 0, LOCAL, WantTier::Luxury), (60, 23));
    let need = household_rows(&closed, 0, PUBLIC);
    assert_eq!(need.len(), 1);
    assert_eq!(
        (need[0].satisfied_quantity, need[0].unmet_quantity),
        (10, 0)
    );
    assert_eq!(purse(&closed, 0).micro_units(), 1_000_000);
    let public = rows_of(&closed, PUBLIC);
    assert_eq!(public.len(), 1);
    assert_eq!(
        settled(&closed),
        paid(&rows_of(&closed, LOCAL)) + paid(&public)
    );
}

#[test]
fn without_wants_the_stage_is_unchanged() {
    let mut fixture = ServiceFixture::new(
        &[support::dollars(400), support::dollars(600)],
        &[vec![(UTILITY, 100)], vec![(UTILITY, 100)]],
    );
    fixture.utility_capacity = 240;
    fixture.business = Some(support::dollars(40_000));
    let closed = close(&fixture);
    let mut summary: Vec<_> = rows_of(&closed, UTILITY)
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
    assert!(closed.household_wants.is_empty() && closed.household_tiers.is_empty());
}
