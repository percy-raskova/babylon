use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CashAccount, CashTransferPurpose, FinalDemandPrincipalId, FundedShift, MonetaryBook,
    MonetaryError, OrderId, OutboundOrderId, PurchaseEscrow, ShiftId, ShiftState, SiteId,
};

fn money(micro: i128) -> Currency {
    Currency::from_micro_units(micro)
}

fn supplier() -> AccountId {
    AccountId::Site(SiteId::from_bytes([1; 32]))
}

fn buyer() -> AccountId {
    AccountId::Household(FinalDemandPrincipalId::from_bytes([1; 32]))
}

fn order() -> OutboundOrderId {
    OutboundOrderId::Delivery(OrderId::from_bytes([3; 32]))
}

fn shift() -> ShiftId {
    ShiftId::from_bytes([4; 32])
}

fn book() -> MonetaryBook {
    MonetaryBook::open(vec![
        CashAccount {
            id: supplier(),
            cash: money(40),
        },
        CashAccount {
            id: buyer(),
            cash: money(100),
        },
    ])
    .unwrap()
}

fn purchase(quantity: u64, price: i128) -> PurchaseEscrow {
    PurchaseEscrow::new(order(), buyer(), supplier(), quantity, money(price)).unwrap()
}

#[test]
fn reservation_is_one_principal_and_arrival_is_the_payment_boundary() {
    let mut ledger = book();
    let receipt = ledger.reserve_purchase(purchase(10, 3)).unwrap();
    assert_eq!(receipt.debit.delta, money(-30));
    assert_eq!(receipt.credit.delta, money(30));
    assert_eq!(ledger.cash(buyer()).unwrap(), money(70));
    assert_eq!(ledger.cash(supplier()).unwrap(), money(40));
    assert_eq!(ledger.total_cash_and_reserves().unwrap(), money(140));
    let reserved = ledger.clone();
    assert_eq!(
        ledger.reserve_purchase(purchase(10, 3)),
        Err(MonetaryError::DuplicatePurchase)
    );
    assert_eq!(ledger, reserved);

    let receipt = ledger.settle_purchase(order(), 4).unwrap();
    assert_eq!(receipt.quantity, 4);
    assert_eq!(receipt.transfer.credit.delta, money(12));
    assert_eq!(ledger.cash(supplier()).unwrap(), money(52));
    let settled = ledger.clone();
    assert_eq!(
        ledger.settle_purchase(order(), 4),
        Err(MonetaryError::NonIncreasingQuantity)
    );
    assert_eq!(
        ledger.settle_purchase(order(), 3),
        Err(MonetaryError::NonIncreasingQuantity)
    );
    assert_eq!(ledger, settled);
}

#[test]
fn partial_loss_delivery_and_cancellation_conserve_cash() {
    let mut ledger = book();
    ledger.reserve_purchase(purchase(10, 3)).unwrap();
    ledger.refund_purchase(order(), 2).unwrap();
    ledger.settle_purchase(order(), 4).unwrap();
    ledger.settle_purchase(order(), 7).unwrap();
    ledger.refund_purchase(order(), 3).unwrap();
    assert_eq!(ledger.cash(buyer()).unwrap(), money(79));
    assert_eq!(ledger.cash(supplier()).unwrap(), money(61));
    assert_eq!(ledger.total_cash_and_reserves().unwrap(), money(140));
    assert_eq!(
        ledger.purchase(order()).unwrap().reserved_amount().unwrap(),
        money(0)
    );
    let closed = ledger.clone();
    assert_eq!(
        ledger.settle_purchase(order(), 8),
        Err(MonetaryError::QuantityExceedsPrincipal)
    );
    assert_eq!(
        ledger.refund_purchase(order(), 3),
        Err(MonetaryError::NonIncreasingQuantity)
    );
    assert_eq!(ledger, closed);
    ledger.retire_purchase(order()).unwrap();
    assert_eq!(
        ledger.purchase(order()),
        Err(MonetaryError::UnknownPurchase)
    );
}

#[test]
fn insufficient_cash_and_overflow_leave_the_book_unchanged() {
    let mut ledger = book();
    let before = ledger.clone();
    assert_eq!(
        ledger.reserve_purchase(purchase(34, 3)),
        Err(MonetaryError::InsufficientCash)
    );
    assert_eq!(ledger, before);
    assert_eq!(
        PurchaseEscrow::new(order(), buyer(), supplier(), 2, money(i128::MAX)),
        Err(MonetaryError::Arithmetic)
    );
    assert_eq!(ledger, before);
    assert_eq!(
        ledger.transfer_cash(
            buyer(),
            supplier(),
            money(101),
            CashTransferPurpose::MutualAid
        ),
        Err(MonetaryError::InsufficientCash)
    );
    assert_eq!(ledger, before);

    let mut huge = MonetaryBook::open(vec![
        CashAccount {
            id: buyer(),
            cash: money(10),
        },
        CashAccount {
            id: supplier(),
            cash: money(i128::MAX),
        },
    ])
    .unwrap();
    huge.reserve_purchase(purchase(1, 1)).unwrap();
    let before = huge.clone();
    assert_eq!(
        huge.settle_purchase(order(), 1),
        Err(MonetaryError::Arithmetic)
    );
    assert_eq!(huge, before);
    assert_eq!(
        huge.total_cash_and_reserves(),
        Err(MonetaryError::Arithmetic)
    );
}

#[test]
fn funded_idle_attendance_creates_an_obligation_before_payment() {
    let mut ledger = book();
    let commitment = FundedShift::new(shift(), supplier(), buyer(), 7, 4, money(3)).unwrap();
    ledger.reserve_shift(commitment).unwrap();
    assert_eq!(ledger.cash(supplier()).unwrap(), money(28));
    assert_eq!(ledger.cash(buyer()).unwrap(), money(100));
    assert_eq!(
        ledger.shift(shift()).unwrap().outstanding_wages().unwrap(),
        money(0)
    );
    let before = ledger.clone();
    assert_eq!(
        ledger.pay_shift(shift()),
        Err(MonetaryError::ShiftNotAccrued)
    );
    assert_eq!(ledger, before);

    // Attendance is owed before household purchases determine merchant work.
    // Productive use is deliberately absent from wage accrual and payment.
    let accrued = ledger.accrue_shift(shift()).unwrap();
    assert_eq!(accrued.obligated_hours, 4);
    assert_eq!(accrued.amount, money(12));
    assert_eq!(ledger.shift(shift()).unwrap().state, ShiftState::Accrued);
    assert_eq!(
        ledger.shift(shift()).unwrap().outstanding_wages().unwrap(),
        money(12)
    );
    assert_eq!(ledger.cash(buyer()).unwrap(), money(100));
    let before = ledger.clone();
    assert_eq!(
        ledger.accrue_shift(shift()),
        Err(MonetaryError::ShiftNotReserved)
    );
    assert_eq!(
        ledger.cancel_unearned_shift(shift()),
        Err(MonetaryError::ShiftNotReserved)
    );
    assert_eq!(ledger, before);

    ledger.pay_shift(shift()).unwrap();
    assert_eq!(ledger.shift(shift()).unwrap().state, ShiftState::Paid);
    assert_eq!(ledger.cash(buyer()).unwrap(), money(112));
    assert_eq!(
        ledger.shift(shift()).unwrap().outstanding_wages().unwrap(),
        money(0)
    );
    assert_eq!(ledger.total_cash_and_reserves().unwrap(), money(140));
    let paid = ledger.clone();
    assert_eq!(
        ledger.pay_shift(shift()),
        Err(MonetaryError::ShiftNotAccrued)
    );
    assert_eq!(ledger, paid);
    ledger.retire_shift(shift()).unwrap();
}

#[test]
fn unearned_shift_can_be_refunded_but_live_principals_cannot_be_retired() {
    let mut ledger = book();
    let commitment = FundedShift::new(shift(), supplier(), buyer(), 7, 4, money(3)).unwrap();
    ledger.reserve_shift(commitment.clone()).unwrap();
    ledger.reserve_purchase(purchase(10, 3)).unwrap();
    let before = ledger.clone();
    assert_eq!(
        ledger.reserve_shift(commitment),
        Err(MonetaryError::DuplicateShift)
    );
    assert_eq!(
        ledger.retire_shift(shift()),
        Err(MonetaryError::OpenPrincipal)
    );
    assert_eq!(
        ledger.retire_purchase(order()),
        Err(MonetaryError::OpenPrincipal)
    );
    assert_eq!(ledger, before);
    ledger.cancel_unearned_shift(shift()).unwrap();
    assert_eq!(ledger.cash(supplier()).unwrap(), money(40));
    assert_eq!(ledger.total_cash_and_reserves().unwrap(), money(140));
}

#[test]
fn canonical_snapshot_preserves_pending_escrow_and_unpaid_obligations() {
    let mut ledger = book();
    ledger.reserve_purchase(purchase(10, 3)).unwrap();
    ledger.settle_purchase(order(), 4).unwrap();
    ledger.refund_purchase(order(), 2).unwrap();
    ledger
        .reserve_shift(FundedShift::new(shift(), supplier(), buyer(), 2, 4, money(3)).unwrap())
        .unwrap();
    ledger.accrue_shift(shift()).unwrap();
    let snapshot = ledger.snapshot();
    assert_eq!(
        MonetaryBook::from_snapshot(snapshot.clone()).unwrap(),
        ledger
    );
    let mut duplicate = snapshot.clone();
    duplicate.purchases.push(duplicate.purchases[0].clone());
    assert_eq!(
        MonetaryBook::from_snapshot(duplicate),
        Err(MonetaryError::DuplicatePurchase)
    );
    let mut negative = snapshot.clone();
    negative.accounts[0].cash = money(-1);
    assert_eq!(
        MonetaryBook::from_snapshot(negative),
        Err(MonetaryError::NegativeCash)
    );
    let mut missing = snapshot;
    missing.accounts.retain(|account| account.id != buyer());
    assert_eq!(
        MonetaryBook::from_snapshot(missing),
        Err(MonetaryError::UnknownAccount)
    );
    let mut excessive = ledger.snapshot();
    excessive.purchases[0].refunded = 7;
    assert_eq!(
        MonetaryBook::from_snapshot(excessive),
        Err(MonetaryError::QuantityExceedsPrincipal)
    );
    let mut invalid_shift = ledger.snapshot();
    invalid_shift.shifts[0].committed_hours = 0;
    assert_eq!(
        MonetaryBook::from_snapshot(invalid_shift),
        Err(MonetaryError::ZeroQuantity)
    );
}

#[test]
fn transfers_have_distinct_owners_and_no_issuance() {
    let mut ledger = book();
    assert_ne!(supplier(), buyer());
    let receipt = ledger
        .transfer_cash(
            supplier(),
            buyer(),
            money(7),
            CashTransferPurpose::OwnershipDistribution,
        )
        .unwrap();
    assert_eq!(
        receipt
            .debit
            .delta
            .checked_add(receipt.credit.delta)
            .unwrap(),
        money(0)
    );
    assert_eq!(ledger.cash(supplier()).unwrap(), money(33));
    assert_eq!(ledger.cash(buyer()).unwrap(), money(107));
    assert_eq!(ledger.total_cash_and_reserves().unwrap(), money(140));
    let before = ledger.clone();
    assert_eq!(
        ledger.transfer_cash(buyer(), buyer(), money(1), CashTransferPurpose::MutualAid),
        Err(MonetaryError::IdenticalParties)
    );
    assert_eq!(
        ledger.transfer_cash(buyer(), supplier(), money(-1), CashTransferPurpose::Tax),
        Err(MonetaryError::NonPositiveAmount)
    );
    assert_eq!(ledger, before);
}

#[test]
fn payment_overflow_preserves_both_the_wage_obligation_and_reserve() {
    let mut ledger = MonetaryBook::open(vec![
        CashAccount {
            id: supplier(),
            cash: money(10),
        },
        CashAccount {
            id: buyer(),
            cash: money(i128::MAX),
        },
    ])
    .unwrap();
    ledger
        .reserve_shift(FundedShift::new(shift(), supplier(), buyer(), 1, 1, money(1)).unwrap())
        .unwrap();
    ledger.accrue_shift(shift()).unwrap();
    let before = ledger.clone();
    assert_eq!(ledger.pay_shift(shift()), Err(MonetaryError::Arithmetic));
    assert_eq!(ledger, before);
    assert_eq!(
        ledger.shift(shift()).unwrap().outstanding_wages().unwrap(),
        money(1)
    );
}

#[test]
fn purchase_and_shift_admission_refuse_invalid_principals() {
    assert_eq!(
        PurchaseEscrow::new(order(), buyer(), supplier(), 0, money(1)),
        Err(MonetaryError::ZeroQuantity)
    );
    assert_eq!(
        PurchaseEscrow::new(order(), buyer(), supplier(), 1, money(0)),
        Err(MonetaryError::NonPositiveAmount)
    );
    assert_eq!(
        PurchaseEscrow::new(order(), buyer(), buyer(), 1, money(1)),
        Err(MonetaryError::IdenticalParties)
    );
    assert_eq!(
        FundedShift::new(shift(), supplier(), buyer(), 1, 0, money(1)),
        Err(MonetaryError::ZeroQuantity)
    );
    let mut ledger = book();
    let before = ledger.clone();
    let mut unknown = purchase(1, 1);
    unknown.seller = AccountId::Site(SiteId::from_bytes([9; 32]));
    assert_eq!(
        ledger.reserve_purchase(unknown),
        Err(MonetaryError::UnknownAccount)
    );
    assert_eq!(ledger, before);
    let unaffordable = FundedShift::new(shift(), supplier(), buyer(), 1, 41, money(1)).unwrap();
    assert_eq!(
        ledger.reserve_shift(unaffordable),
        Err(MonetaryError::InsufficientCash)
    );
    assert_eq!(ledger, before);
}
