//! A buying workplace may take one service from several providers: its requirement is shared over its rows by
//! their caps, each share is ordered of its own provider and paid at that provider's price.

use super::service_support::{self, ServiceFixture, UTILITY};
use super::support;
use babylon_material_circuit::{
    AccountId, AdjustmentReceipt, AdjustmentRule, HiringLimit, MaterialCircuitTransition,
    MoneyTransferPurpose, OutboundOrderId, ServicePerformanceReceipt,
};

/// A business that plans `batches` batches of one unit of utility each, with rows of caps 70 and 30 at two
/// providers that can each make `second` and 100 units; prices are not found by clearing.
fn business(batches: u64, second: u64) -> ServiceFixture {
    let mut fixture = ServiceFixture::new(&[], &[]);
    fixture.business = Some(support::dollars(40_000));
    fixture.business_batches = batches;
    fixture.second_utility = Some(second);
    fixture.paying_order = None;
    fixture
}

fn close(fixture: &ServiceFixture) -> MaterialCircuitTransition {
    let (catalog, state) = fixture.build();
    babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes")
}

fn of_business(closed: &MaterialCircuitTransition) -> Vec<&ServicePerformanceReceipt> {
    let mut rows: Vec<_> = closed
        .service_performance
        .iter()
        .filter(|row| matches!(row.buyer, AccountId::Site(site) if site == support::site(service_support::BUSINESS)))
        .collect();
    rows.sort_by_key(|row| row.provider_site_id);
    rows
}

#[test]
fn a_workplace_buys_from_two_providers() {
    let closed = close(&business(50, 100));
    let rows = of_business(&closed);
    let summary: Vec<_> = rows
        .iter()
        .map(|row| {
            (
                row.requested_quantity,
                row.performed_quantity,
                row.unit_price.micro_units(),
            )
        })
        .collect();
    // The first provider is the utility (site 1), the second site 7; each is asked its share, 35 and 15.
    assert_eq!(
        summary,
        vec![
            (35, 35, service_support::posted(UTILITY).micro_units()),
            (15, 15, service_support::second_posted().micro_units()),
        ]
    );
    let settled: i128 = closed
        .money_transfers
        .iter()
        .filter(|row| {
            matches!(
                row.purpose,
                MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::Service(_))
            )
        })
        .map(|row| row.credit.delta.micro_units())
        .sum();
    assert_eq!(settled, 35 * 4_000_000 + 15 * 6_000_000);
}

/// The hiring bound of the business's next period, as the close wrote it.
fn bound_of(closed: &MaterialCircuitTransition) -> Vec<(u64, u64, HiringLimit)> {
    closed
        .adjustments
        .iter()
        .filter_map(|row| match row {
            AdjustmentReceipt::HiringBound(receipt)
                if receipt.site_id == support::site(service_support::BUSINESS) =>
            {
                Some((receipt.asked_hours, receipt.bound_hours, receipt.limit))
            }
            _ => None,
        })
        .collect()
}

#[test]
fn the_hiring_bound_counts_both_providers() {
    let mut fixture = business(50, 100);
    fixture.adjustments = vec![AdjustmentRule::HiringWithinMeans];
    fixture.paying_order = Some(vec![UTILITY]);
    assert_eq!(
        bound_of(&close(&fixture)),
        vec![(50, 50, HiringLimit::None)]
    );
    // The second provider can make 10 units: the requirement it fits is floor(10 x 100 / 30), 33.
    let mut short = business(50, 10);
    short.adjustments = vec![AdjustmentRule::HiringWithinMeans];
    short.paying_order = Some(vec![UTILITY]);
    assert_eq!(
        bound_of(&close(&short)),
        vec![(50, 33, HiringLimit::Inputs)]
    );
    // The second provider can make one unit: the requirement it fits is floor(1 x 100 / 30), 3.
    let mut idle = business(50, 1);
    idle.adjustments = vec![AdjustmentRule::HiringWithinMeans];
    idle.paying_order = Some(vec![UTILITY]);
    assert_eq!(bound_of(&close(&idle)), vec![(50, 3, HiringLimit::Inputs)]);
}
