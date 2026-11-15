//! The transfer price stays on subsidiary books until an actual outside disposition.
use super::carrying::CompanyCarryingLedger;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::FreightLotId;
use babylon_material_circuit::{
    AccountId, CompanyBasisAsset, CompanyBasisMovement, CompanyId, CompanySale, GoodId, OrderId,
    OutboundOrderId, SiteId, UnitId,
};
use std::collections::BTreeMap;

#[test]
fn a_partial_external_sale_releases_group_cost_and_leaves_the_rounding_residual() {
    let site = |n| SiteId::from_bytes([n; 32]);
    let group = CompanyId::from_bytes([4; 32]);
    let g = GoodId::from_bytes([5; 32]);
    let u = UnitId::from_bytes([6; 32]);
    let stock = |n| CompanyBasisAsset::Stock(site(n), g, u);
    let micros = Currency::from_micro_units;
    let sale = |from, to, available, quantity, opening, price| CompanyBasisMovement {
        source: stock(from),
        destination: Some(stock(to)),
        sale: Some(CompanySale {
            order: OutboundOrderId::Delivery(OrderId::from_bytes([from; 32])),
            buyer: AccountId::Site(site(to)),
            proceeds: micros(price),
        }),
        available,
        quantity,
        opening: micros(opening),
    };
    let members = BTreeMap::from([(site(1), group), (site(2), group)]);
    let mut ledger = CompanyCarryingLedger::default();
    let first = ledger
        .close(&members, &[sale(1, 2, 3, 3, 5, 10)])
        .expect("internal handoff");
    assert_eq!(first[&group].internal_sales, micros(10));
    assert_eq!(first[&group].new_internal_margin, micros(5));
    assert_eq!(ledger.margin(stock(2)), micros(5));
    // One preexisting unit at 3 plus three transferred units at 10 legal / 5 group cost.
    let second = ledger
        .close(&members, &[sale(2, 3, 4, 1, 13, 8)])
        .expect("outside sale");
    assert_eq!(second[&group].realized_margin, micros(1));
    assert_eq!(ledger.margin(stock(2)), micros(4));
    let third = ledger
        .close(&members, &[sale(2, 3, 3, 3, 10, 15)])
        .expect("final depletion");
    assert_eq!(third[&group].realized_margin, micros(4));
    assert_eq!(ledger.margin(stock(2)), micros(0));
}

#[test]
fn an_internal_discount_is_carried_through_freight_loss_and_external_sale() {
    let s = SiteId::from_bytes([1; 32]);
    let b = SiteId::from_bytes([2; 32]);
    let group = CompanyId::from_bytes([3; 32]);
    let members = BTreeMap::from([(s, group), (b, group)]);
    let g = GoodId::from_bytes([4; 32]);
    let u = UnitId::from_bytes([5; 32]);
    let stock = CompanyBasisAsset::Stock(b, g, u);
    let lot = CompanyBasisAsset::Freight(b, FreightLotId::from_bytes([6; 32]));
    let id = OutboundOrderId::Delivery(OrderId::from_bytes([7; 32]));
    let micros = Currency::from_micro_units;
    let mut ledger = CompanyCarryingLedger::default();
    let sale = CompanyBasisMovement {
        source: CompanyBasisAsset::Stock(s, g, u),
        destination: Some(stock),
        sale: Some(CompanySale {
            order: id,
            buyer: AccountId::Site(b),
            proceeds: micros(5),
        }),
        opening: micros(10),
        available: 3,
        quantity: 3,
    };
    let dispatch = CompanyBasisMovement {
        source: stock,
        destination: Some(lot),
        sale: None,
        opening: micros(5),
        available: 3,
        quantity: 3,
    };
    ledger
        .close(&members, &[sale, dispatch])
        .expect("below-cost transfer dispatched");
    assert_eq!(ledger.margin(lot), micros(-5));
    let loss = CompanyBasisMovement {
        source: lot,
        destination: None,
        sale: None,
        opening: micros(5),
        available: 3,
        quantity: 1,
    };
    let outside = SiteId::from_bytes([8; 32]);
    let external = CompanyBasisMovement {
        source: lot,
        destination: Some(CompanyBasisAsset::Stock(outside, g, u)),
        sale: Some(CompanySale {
            order: id,
            buyer: AccountId::Site(outside),
            proceeds: micros(12),
        }),
        opening: micros(4),
        available: 2,
        quantity: 2,
    };
    let result = ledger
        .close(&members, &[loss, external])
        .expect("loss then actual delivery");
    assert_eq!(result[&group].realized_margin, micros(-5));
    assert_eq!(result[&group].realized_on_sales, micros(-3));
    assert_eq!(ledger.margin(lot), micros(0));
}
