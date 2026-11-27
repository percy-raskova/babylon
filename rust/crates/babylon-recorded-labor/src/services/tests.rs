//! A household may buy a service beyond its need (a want of a tier): the fold reads that purchase.
use super::close;
use crate::book::{Book, Carry, Frame};
use crate::model::{
    LaborBasis, LaborDisposition, LaborNode, LaborReceiptFamily, RecordedLaborError,
};
use crate::view::{PeriodView, ReceiptView};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CapacityReservations, CircuitAccounting, FinalDemandPrincipalId, GoodId,
    HouseholdServiceReceipt, HouseholdWantReceipt, MaterialCircuitState, OrderId,
    ServicePerformanceReceipt, SiteId, UnitId, WantTier,
};

const PERIOD: u64 = 3;

fn ids() -> (FinalDemandPrincipalId, GoodId, UnitId, SiteId) {
    (
        FinalDemandPrincipalId::from_bytes([0x16; 32]),
        GoodId::from_bytes([2; 32]),
        UnitId::from_bytes([3; 32]),
        SiteId::from_bytes([4; 32]),
    )
}

fn state() -> MaterialCircuitState {
    MaterialCircuitState {
        period: PERIOD,
        accounting: CircuitAccounting::PhysicalControl,
        service_connections: vec![],
        service_orders: vec![],
        route_stage_capacities: vec![],
        inventory: vec![],
        orders: vec![],
        freight: vec![],
        corridor_capacities: vec![],
        capacities: vec![],
        labor: vec![],
        production_commitments: vec![],
        final_demand_principals: vec![],
        final_demand_orders: vec![],
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
    }
}

fn performance(order: u8, performed: u64, used: u64) -> ServicePerformanceReceipt {
    let (principal, good, unit, site) = ids();
    ServicePerformanceReceipt {
        period: PERIOD,
        order_id: OrderId::from_bytes([order; 32]),
        provider_site_id: site,
        buyer: AccountId::Household(principal),
        good_id: good,
        unit_id: unit,
        requested_quantity: performed,
        admitted_quantity: performed,
        performed_quantity: performed,
        used_quantity: used,
        unused_quantity: performed - used,
        expired_quantity: 0,
        unit_price: Currency::from_micro_units(1),
    }
}

fn need(performed: u64) -> HouseholdServiceReceipt {
    let (principal, good, unit, _) = ids();
    HouseholdServiceReceipt {
        period: PERIOD,
        principal_id: principal,
        good_id: good,
        unit_id: unit,
        required_quantity: 8,
        performed_quantity: performed,
        satisfied_quantity: performed,
        unmet_quantity: 0,
        unused_quantity: 0,
    }
}

fn want(order: u8, bought: u64) -> HouseholdWantReceipt {
    let (principal, good, unit, site) = ids();
    HouseholdWantReceipt {
        period: PERIOD,
        principal_id: principal,
        tier: WantTier::Comfort,
        seller_site_id: site,
        good_id: good,
        unit_id: unit,
        order_id: OrderId::from_bytes([order; 32]),
        wanted_quantity: 8,
        bought_quantity: bought,
        posted_price: Currency::from_micro_units(1),
        unit_price: Currency::from_micro_units(1),
    }
}

/// Run `finish` on a household holding `held` units (one million micro-hours each).
fn run(
    carry: Carry,
    held: u64,
    performances: &[ServicePerformanceReceipt],
    needs: &[HouseholdServiceReceipt],
    wants: &[HouseholdWantReceipt],
) -> (Result<(), RecordedLaborError>, Frame) {
    let (principal, good, unit, _) = ids();
    let node = LaborNode::household(principal, good, unit);
    let micros = match carry {
        Carry::Hours => u128::from(held) * 1_000_000,
        Carry::OpeningUnits => u128::from(held) * 500_000,
    };
    let mut frame = Frame::carrying(Book::new(), carry);
    frame
        .credit(
            node,
            held,
            LaborBasis {
                recorded_micro_hours: micros,
                unknown_opening: false,
            },
        )
        .expect("the household's stock");
    let state = state();
    let view = PeriodView {
        period: PERIOD,
        before: &state,
        after: &state,
        receipts: ReceiptView {
            aid: &[],
            collections: &[],
            agency: &[],
            installation: &[],
            equipment_wear: &[],
            maintenance: None,
            production: &[],
            dispatches: &[],
            losses: &[],
            arrivals: &[],
            handling: &[],
            local_fulfillments: &[],
            local_transfers: &[],
            procurement: &[],
            service_outputs: &[],
            service_performance: performances,
            household_services: needs,
            household_wants: wants,
            household_consumption: &[],
        },
    };
    let result = close::finish(&mut frame, &view);
    (result, frame)
}

fn service_use_edges(frame: &Frame) -> Vec<(u64, u128, LaborReceiptFamily, usize)> {
    frame
        .edges
        .iter()
        .filter(|e| e.destination == LaborNode::sink(LaborDisposition::HouseholdServiceUse))
        .map(|e| {
            (
                e.quantity,
                e.basis.recorded_micro_hours,
                e.receipt.family,
                e.receipt.ordinal,
            )
        })
        .collect()
}

#[test]
fn a_need_of_eight_and_a_want_of_one_fold_and_all_nine_leave_to_service_use() {
    let rows = [performance(1, 8, 8), performance(2, 1, 1)];
    let (hours, hours_frame) = run(Carry::Hours, 9, &rows, &[need(8)], &[want(2, 1)]);
    hours.expect("a want beyond the need folds");
    assert!(hours_frame.book.is_empty());
    assert_eq!(hours_frame.released_micro_hours, 9_000_000);
    let edges = service_use_edges(&hours_frame);
    assert_eq!(edges.iter().map(|e| e.0).sum::<u64>(), 9);
    assert!(edges
        .iter()
        .any(|e| e.2 == LaborReceiptFamily::ServicePerformance && e.3 == 1 && e.0 == 1));
    let (units, units_frame) = run(Carry::OpeningUnits, 9, &rows, &[need(8)], &[want(2, 1)]);
    units.expect("the second run folds too");
    assert!(units_frame.book.is_empty());
    let moves = |edges: Vec<(u64, u128, LaborReceiptFamily, usize)>| {
        edges
            .into_iter()
            .map(|e| (e.0, e.2, e.3))
            .collect::<Vec<_>>()
    };
    assert_eq!(moves(edges), moves(service_use_edges(&units_frame)));
}

#[test]
fn a_want_s_row_that_is_not_wholly_used_is_refused() {
    let rows = [performance(1, 8, 8), performance(2, 1, 0)];
    let (result, _) = run(Carry::Hours, 9, &rows, &[need(8)], &[want(2, 1)]);
    assert_eq!(
        result,
        Err(RecordedLaborError::ReceiptMismatch("service use"))
    );
}

#[test]
fn a_want_s_performance_that_differs_from_what_was_bought_is_refused() {
    let rows = [performance(1, 8, 8), performance(2, 2, 2)];
    let (result, _) = run(Carry::Hours, 10, &rows, &[need(8)], &[want(2, 1)]);
    assert_eq!(
        result,
        Err(RecordedLaborError::ReceiptMismatch("service use"))
    );
}

#[test]
fn with_no_wants_the_nine_units_still_disagree_with_the_need() {
    let rows = [performance(1, 8, 8), performance(2, 1, 1)];
    let (result, _) = run(Carry::Hours, 9, &rows, &[need(8)], &[]);
    assert_eq!(
        result,
        Err(RecordedLaborError::ReceiptMismatch("service use"))
    );
}

#[test]
fn with_no_wants_a_need_alone_folds_as_before() {
    let rows = [performance(1, 8, 8)];
    let (result, frame) = run(Carry::Hours, 8, &rows, &[need(8)], &[]);
    result.expect("the need alone");
    assert!(frame.book.is_empty());
    assert_eq!(frame.released_micro_hours, 8_000_000);
}

#[test]
fn a_want_that_bought_nothing_is_not_a_want() {
    let rows = [performance(1, 8, 8), performance(2, 1, 1)];
    let (result, _) = run(Carry::Hours, 9, &rows, &[need(8)], &[want(2, 0)]);
    assert_eq!(
        result,
        Err(RecordedLaborError::ReceiptMismatch("service use"))
    );
}
