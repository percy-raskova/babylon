use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CashAccount, FinalDemandPrincipalId, FundedShift, MonetaryBook,
    MonetaryBookSnapshot, MonetaryError, OrderId, OutboundOrderId, PurchaseEscrow, ShiftId, SiteId,
    MAX_MATERIAL_CIRCUIT_ROWS,
};

const FAMILY: usize = MAX_MATERIAL_CIRCUIT_ROWS;
const COMBINED: usize = 5 * FAMILY;

fn identity(index: usize) -> [u8; 32] {
    let mut bytes = [0; 32];
    bytes[..8].copy_from_slice(&u64::try_from(index).unwrap().to_be_bytes());
    bytes
}
fn buyer() -> AccountId {
    AccountId::Household(FinalDemandPrincipalId::from_bytes([1; 32]))
}
fn seller() -> AccountId {
    AccountId::Site(SiteId::from_bytes([2; 32]))
}
fn purchase(index: usize) -> PurchaseEscrow {
    let order = if index < 2 * FAMILY {
        OutboundOrderId::Delivery(OrderId::from_bytes(identity(index)))
    } else if index < 3 * FAMILY {
        OutboundOrderId::LocalFinalDemand(OrderId::from_bytes(identity(index - 2 * FAMILY)))
    } else {
        OutboundOrderId::Service(OrderId::from_bytes(identity(index - 3 * FAMILY)))
    };
    PurchaseEscrow::new(order, buyer(), seller(), 1, Currency::from_micro_units(1)).unwrap()
}
fn snapshot(count: usize) -> MonetaryBookSnapshot {
    MonetaryBookSnapshot {
        aid: vec![],

        accounts: vec![
            CashAccount {
                id: buyer(),
                cash: Currency::from_micro_units(7),
            },
            CashAccount {
                id: seller(),
                cash: Currency::from_micro_units(0),
            },
        ],
        purchases: (0..count).map(purchase).collect(),
        shifts: vec![],
    }
}
#[test]
fn disjoint_purchase_principals_fill_the_combined_bound_without_losing_cash() {
    let mut book = MonetaryBook::from_snapshot(snapshot(COMBINED - 1)).unwrap();
    let before = book.total_cash_and_reserves().unwrap();
    book.reserve_purchase(purchase(COMBINED - 1)).unwrap();
    assert_eq!(book.snapshot().purchases.len(), COMBINED);
    assert_eq!(book.total_cash_and_reserves().unwrap(), before);
    assert_eq!(book.cash(buyer()).unwrap().micro_units(), 6);
    let mut excess = purchase(COMBINED - 1);
    excess.order = OutboundOrderId::Service(OrderId::from_bytes(identity(2 * FAMILY)));
    let unchanged = book.clone();
    assert_eq!(book.reserve_purchase(excess), Err(MonetaryError::RowLimit));
    assert_eq!(book, unchanged);
}
#[test]
fn snapshot_admission_inspects_duplicate_principals_after_the_old_ceiling() {
    let mut rows = snapshot(FAMILY + 2);
    rows.purchases[FAMILY + 1] = rows.purchases[FAMILY].clone();
    assert_eq!(
        MonetaryBook::from_snapshot(rows),
        Err(MonetaryError::DuplicatePurchase)
    );
    assert_eq!(
        MonetaryBook::from_snapshot(snapshot(COMBINED + 1)),
        Err(MonetaryError::RowLimit)
    );
}
#[test]
fn a_larger_purchase_book_does_not_enlarge_funded_shift_capacity() {
    let mut rows = snapshot(0);
    rows.shifts = (0..=FAMILY)
        .map(|index| {
            FundedShift::new(
                ShiftId::from_bytes(identity(index)),
                seller(),
                buyer(),
                1,
                1,
                Currency::from_micro_units(1),
            )
            .unwrap()
        })
        .collect();
    assert_eq!(
        MonetaryBook::from_snapshot(rows),
        Err(MonetaryError::RowLimit)
    );
}
