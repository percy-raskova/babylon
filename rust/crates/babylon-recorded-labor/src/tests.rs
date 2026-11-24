//! Frame-level tests of the fold's carrying: hand-built nodes, no stored records.
use crate::circulation::{Handling, Handoff};
use crate::fold;
use crate::{
    Book, Carry, Frame, Handed, LaborBasis, LaborNode, LaborReceiptFamily, Position, ReceiptRef,
    MICROS_PER_UNIT,
};
use babylon_material_circuit::{
    GoodId, MerchantHandlingReceipt, OrderId, OutboundOrderId, SiteId, UnitId,
};
use std::collections::BTreeMap;

fn node(site: u8) -> LaborNode {
    LaborNode::site(
        SiteId::from_bytes([site; 32]),
        GoodId::from_bytes([3; 32]),
        UnitId::from_bytes([4; 32]),
    )
}

fn work(site: u8) -> LaborNode {
    LaborNode::work(SiteId::from_bytes([site; 32]), UnitId::from_bytes([5; 32]))
}

fn receipt() -> ReceiptRef {
    ReceiptRef::new(LaborReceiptFamily::Production, 0)
}

/// Two opening units plus one unit of output, taken apart one unit at a time.
fn shares(carry: Carry, opening: u128) -> Vec<u128> {
    let source = node(1);
    let mut frame = Frame::carrying(Book::new(), carry);
    frame
        .credit(
            source,
            2,
            LaborBasis {
                recorded_micro_hours: opening,
                unknown_opening: true,
            },
        )
        .expect("two opening units");
    let output = frame
        .direct(work(1), source, 1, receipt())
        .expect("one hour of output");
    frame.credit(source, 1, output).expect("mixed in");
    (0..3)
        .map(|_| {
            frame
                .take(source, 1)
                .expect("one unit")
                .recorded_micro_hours
        })
        .collect()
}

#[test]
fn opening_units_take_the_same_floor_shares_as_hours() {
    // Hours: 3 units hold 1_000_000. Units: 3 units hold 2 * MICROS_PER_UNIT.
    // Each take is the floor share of what the pool holds; the last unit carries the rest.
    assert_eq!(shares(Carry::Hours, 0), [333_333, 333_333, 333_334]);
    assert_eq!(
        shares(Carry::OpeningUnits, 2 * MICROS_PER_UNIT),
        [666_666, 666_667, 666_667]
    );
    let hours: u128 = shares(Carry::Hours, 0).iter().sum();
    let units: u128 = shares(Carry::OpeningUnits, 2 * MICROS_PER_UNIT)
        .iter()
        .sum();
    assert_eq!((hours, units), (1_000_000, 2_000_000));
}

#[test]
fn direct_work_adds_nothing_to_opening_units() {
    let to = node(1);
    let mut units = Frame::carrying(Book::new(), Carry::OpeningUnits);
    let basis = units.direct(work(1), to, 10, receipt()).expect("posted");
    assert_eq!(basis, LaborBasis::default());
    assert_eq!(units.direct_micro_hours, 0);
    assert_eq!(units.edges.len(), 1);
    assert_eq!(units.edges[0].quantity, 10);
    let mut hours = Frame::new(Book::new());
    let basis = hours.direct(work(1), to, 10, receipt()).expect("posted");
    assert_eq!(basis.recorded_micro_hours, 10_000_000);
    assert_eq!(hours.direct_micro_hours, 10_000_000);
    assert_eq!(hours.edges.len(), 1);
}

#[test]
fn the_opening_book_carries_a_unit_as_a_million() {
    let positions = BTreeMap::from([(node(1), 40_u64)]);
    let expected = |micro| {
        Book::from([(
            node(1),
            Position {
                quantity: 40,
                basis: LaborBasis {
                    recorded_micro_hours: micro,
                    unknown_opening: true,
                },
            },
        )])
    };
    assert_eq!(
        fold::book_of(positions.clone(), Carry::Hours).expect("book"),
        expected(0)
    );
    assert_eq!(
        fold::book_of(positions, Carry::OpeningUnits).expect("book"),
        expected(40_000_000)
    );
}

#[test]
fn a_hand_over_is_recorded_with_its_handling() {
    let (supplier, buyer) = (node(1), node(2));
    let site = SiteId::from_bytes([1; 32]);
    let order = OutboundOrderId::Delivery(OrderId::from_bytes([7; 32]));
    let row = MerchantHandlingReceipt {
        site_id: site,
        order,
        feasible_quantity: 4,
        handled_quantity: 4,
        needed_hours: 4,
        used_hours: 4,
    };
    let mut handling = Handling {
        units: BTreeMap::from([(site, UnitId::from_bytes([5; 32]))]),
        rows: BTreeMap::from([(order, (0, &row))]),
    };
    let mut frame = Frame::new(Book::from([(
        supplier,
        Position {
            quantity: 8,
            basis: LaborBasis {
                recorded_micro_hours: 8_000_000,
                unknown_opening: false,
            },
        },
    )]));
    let reference = ReceiptRef::new(LaborReceiptFamily::LocalTransfers, 0);
    let basis = Handoff {
        order,
        site,
        from: supplier,
        to: buyer,
        receiver: buyer,
        qty: 4,
        reference,
    }
    .debit(&mut frame, &mut handling)
    .expect("handed over");
    assert_eq!(basis.recorded_micro_hours, 8_000_000);
    assert_eq!(
        frame.handed,
        [Handed {
            receipt: reference,
            from: supplier,
            to: buyer,
            quantity: 4,
            basis,
        }]
    );
}
