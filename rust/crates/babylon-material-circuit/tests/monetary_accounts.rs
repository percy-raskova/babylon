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
    .expect("the fixture opens the authored source")
}

fn purchase(quantity: u64, price: i128) -> PurchaseEscrow {
    PurchaseEscrow::new(order(), buyer(), supplier(), quantity, money(price))
        .expect("the constructor accepts the authored fixture arguments")
}

#[test]
fn reservation_is_one_principal_and_arrival_is_the_payment_boundary() {
    let mut ledger = book();
    let receipt = ledger
        .reserve_purchase(purchase(10, 3))
        .expect("the fixture reserve admits the purchase");
    assert_eq!(receipt.debit.delta, money(-30));
    assert_eq!(receipt.credit.delta, money(30));
    assert_eq!(
        ledger
            .cash(buyer())
            .expect("the fixture book holds the payer account"),
        money(70)
    );
    assert_eq!(
        ledger
            .cash(supplier())
            .expect("the fixture book holds the payer account"),
        money(40)
    );
    assert_eq!(
        ledger
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(140)
    );
    let reserved = ledger.clone();
    assert_eq!(
        ledger.reserve_purchase(purchase(10, 3)),
        Err(MonetaryError::DuplicatePurchase)
    );
    assert_eq!(ledger, reserved);

    let receipt = ledger
        .settle_purchase(order(), 4)
        .expect("the fixture settles the authored purchase");
    assert_eq!(receipt.quantity, 4);
    assert_eq!(receipt.transfer.credit.delta, money(12));
    assert_eq!(
        ledger
            .cash(supplier())
            .expect("the fixture book holds the payer account"),
        money(52)
    );
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
    ledger
        .reserve_purchase(purchase(10, 3))
        .expect("the fixture reserve admits the purchase");
    ledger
        .refund_purchase(order(), 2)
        .expect("the fixture refunds the authored purchase");
    ledger
        .settle_purchase(order(), 4)
        .expect("the fixture settles the authored purchase");
    ledger
        .settle_purchase(order(), 7)
        .expect("the fixture settles the authored purchase");
    ledger
        .refund_purchase(order(), 3)
        .expect("the fixture refunds the authored purchase");
    assert_eq!(
        ledger
            .cash(buyer())
            .expect("the fixture book holds the payer account"),
        money(79)
    );
    assert_eq!(
        ledger
            .cash(supplier())
            .expect("the fixture book holds the payer account"),
        money(61)
    );
    assert_eq!(
        ledger
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(140)
    );
    assert_eq!(
        ledger
            .purchase(order())
            .expect("the fixture purchase is present")
            .reserved_amount()
            .expect("the fixture reservation exists"),
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
    ledger
        .retire_purchase(order())
        .expect("the fixture retires the authored purchase");
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
    .expect("the fixture opens the authored source");
    huge.reserve_purchase(purchase(1, 1))
        .expect("the fixture reserve admits the purchase");
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
#[allow(
    clippy::too_many_lines,
    reason = "`funded_idle_attendance_creates_an_obligation_before_payment` keeps one authored boundary's fixture and assertions together"
)]
fn funded_idle_attendance_creates_an_obligation_before_payment() {
    let mut ledger = book();
    let commitment = FundedShift::new(shift(), supplier(), buyer(), 7, 4, money(3))
        .expect("the constructor accepts the authored fixture arguments");
    ledger
        .reserve_shift(commitment)
        .expect("the fixture shift reservation fits");
    assert_eq!(
        ledger
            .cash(supplier())
            .expect("the fixture book holds the payer account"),
        money(28)
    );
    assert_eq!(
        ledger
            .cash(buyer())
            .expect("the fixture book holds the payer account"),
        money(100)
    );
    assert_eq!(
        ledger
            .shift(shift())
            .expect("the fixture call `shift` succeeds for the authored inputs")
            .outstanding_wages()
            .expect("the fixture payroll carries its authored wages"),
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
    let accrued = ledger
        .accrue_shift(shift())
        .expect("the fixture accrues the authored shift");
    assert_eq!(accrued.obligated_hours, 4);
    assert_eq!(accrued.amount, money(12));
    assert_eq!(
        ledger
            .shift(shift())
            .expect("the fixture call `shift` succeeds for the authored inputs")
            .state,
        ShiftState::Accrued
    );
    assert_eq!(
        ledger
            .shift(shift())
            .expect("the fixture call `shift` succeeds for the authored inputs")
            .outstanding_wages()
            .expect("the fixture payroll carries its authored wages"),
        money(12)
    );
    assert_eq!(
        ledger
            .cash(buyer())
            .expect("the fixture book holds the payer account"),
        money(100)
    );
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

    ledger
        .pay_shift(shift())
        .expect("the fixture pays the authored shift");
    assert_eq!(
        ledger
            .shift(shift())
            .expect("the fixture call `shift` succeeds for the authored inputs")
            .state,
        ShiftState::Paid
    );
    assert_eq!(
        ledger
            .cash(buyer())
            .expect("the fixture book holds the payer account"),
        money(112)
    );
    assert_eq!(
        ledger
            .shift(shift())
            .expect("the fixture call `shift` succeeds for the authored inputs")
            .outstanding_wages()
            .expect("the fixture payroll carries its authored wages"),
        money(0)
    );
    assert_eq!(
        ledger
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(140)
    );
    let paid = ledger.clone();
    assert_eq!(
        ledger.pay_shift(shift()),
        Err(MonetaryError::ShiftNotAccrued)
    );
    assert_eq!(ledger, paid);
    ledger
        .retire_shift(shift())
        .expect("the fixture retires the authored shift");
}

#[test]
fn unearned_shift_can_be_refunded_but_live_principals_cannot_be_retired() {
    let mut ledger = book();
    let commitment = FundedShift::new(shift(), supplier(), buyer(), 7, 4, money(3))
        .expect("the constructor accepts the authored fixture arguments");
    ledger
        .reserve_shift(commitment.clone())
        .expect("the fixture shift reservation fits");
    ledger
        .reserve_purchase(purchase(10, 3))
        .expect("the fixture reserve admits the purchase");
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
    ledger
        .cancel_unearned_shift(shift())
        .expect("the fixture cancels the unearned shift");
    assert_eq!(
        ledger
            .cash(supplier())
            .expect("the fixture book holds the payer account"),
        money(40)
    );
    assert_eq!(
        ledger
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(140)
    );
}

#[test]
fn canonical_snapshot_preserves_pending_escrow_and_unpaid_obligations() {
    let mut ledger = book();
    ledger
        .reserve_purchase(purchase(10, 3))
        .expect("the fixture reserve admits the purchase");
    ledger
        .settle_purchase(order(), 4)
        .expect("the fixture settles the authored purchase");
    ledger
        .refund_purchase(order(), 2)
        .expect("the fixture refunds the authored purchase");
    ledger
        .reserve_shift(
            FundedShift::new(shift(), supplier(), buyer(), 2, 4, money(3))
                .expect("the constructor accepts the authored fixture arguments"),
        )
        .expect("the fixture shift reservation fits");
    ledger
        .accrue_shift(shift())
        .expect("the fixture accrues the authored shift");
    let snapshot = ledger.snapshot();
    assert_eq!(
        MonetaryBook::from_snapshot(snapshot.clone())
            .expect("the snapshot admits the derived value"),
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
        .expect("the fixture transfer stays funded");
    assert_eq!(
        receipt
            .debit
            .delta
            .checked_add(receipt.credit.delta)
            .expect("the fixture arithmetic stays in range"),
        money(0)
    );
    assert_eq!(
        ledger
            .cash(supplier())
            .expect("the fixture book holds the payer account"),
        money(33)
    );
    assert_eq!(
        ledger
            .cash(buyer())
            .expect("the fixture book holds the payer account"),
        money(107)
    );
    assert_eq!(
        ledger
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(140)
    );
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
    .expect("the fixture opens the authored source");
    ledger
        .reserve_shift(
            FundedShift::new(shift(), supplier(), buyer(), 1, 1, money(1))
                .expect("the constructor accepts the authored fixture arguments"),
        )
        .expect("the fixture shift reservation fits");
    ledger
        .accrue_shift(shift())
        .expect("the fixture accrues the authored shift");
    let before = ledger.clone();
    assert_eq!(ledger.pay_shift(shift()), Err(MonetaryError::Arithmetic));
    assert_eq!(ledger, before);
    assert_eq!(
        ledger
            .shift(shift())
            .expect("the fixture call `shift` succeeds for the authored inputs")
            .outstanding_wages()
            .expect("the fixture payroll carries its authored wages"),
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
    let unaffordable = FundedShift::new(shift(), supplier(), buyer(), 1, 41, money(1))
        .expect("the constructor accepts the authored fixture arguments");
    assert_eq!(
        ledger.reserve_shift(unaffordable),
        Err(MonetaryError::InsufficientCash)
    );
    assert_eq!(ledger, before);
}

#[test]
fn immutable_money_views_match_canonical_identity_order() {
    let mut ledger = MonetaryBook::open(vec![
        CashAccount {
            id: buyer(),
            cash: money(100),
        },
        CashAccount {
            id: supplier(),
            cash: money(40),
        },
    ])
    .expect("the fixture opens the authored source");
    let service = OutboundOrderId::Service(OrderId::from_bytes([2; 32]));
    ledger
        .reserve_purchase(
            PurchaseEscrow::new(service, buyer(), supplier(), 2, money(3))
                .expect("the constructor accepts the authored fixture arguments"),
        )
        .expect("the fixture reserve admits the purchase");
    ledger
        .reserve_purchase(purchase(10, 3))
        .expect("the fixture reserve admits the purchase");
    ledger
        .reserve_shift(
            FundedShift::new(shift(), supplier(), buyer(), 2, 4, money(3))
                .expect("the constructor accepts the authored fixture arguments"),
        )
        .expect("the fixture shift reservation fits");
    let snapshot = ledger.snapshot();
    assert_eq!(ledger.cash_accounts().len(), snapshot.accounts.len());
    let accounts: Vec<_> = ledger
        .cash_accounts()
        .map(|(&id, &cash)| CashAccount { id, cash })
        .collect();
    assert_eq!(accounts, snapshot.accounts);
    // Same identity bytes in different owner namespaces remain separate principals.
    assert_eq!(accounts.len(), 2);
    assert_ne!(accounts[0].id, accounts[1].id);
    assert_eq!(ledger.purchases().len(), snapshot.purchases.len());
    assert_eq!(
        ledger.purchases().cloned().collect::<Vec<_>>(),
        snapshot.purchases
    );
    for principal in ledger.purchases() {
        assert!(std::ptr::eq(
            principal,
            ledger
                .purchase(principal.order)
                .expect("the fixture purchase is present")
        ));
    }
    assert_eq!(ledger.snapshot(), snapshot);
    assert_eq!(
        MonetaryBook::from_snapshot(snapshot).expect("the snapshot admits the derived value"),
        ledger
    );
}

#[test]
fn purchase_view_preserves_partial_settlement_and_retirement() {
    let mut ledger = book();
    assert!(ledger.purchases().next().is_none());
    ledger
        .reserve_purchase(purchase(10, 3))
        .expect("the fixture reserve admits the purchase");
    ledger
        .settle_purchase(order(), 4)
        .expect("the fixture settles the authored purchase");
    ledger
        .refund_purchase(order(), 2)
        .expect("the fixture refunds the authored purchase");
    let snapshot = ledger.snapshot();
    let principal = ledger
        .purchases()
        .next()
        .expect("the fixture iterator yields its authored rows");
    assert_eq!(principal, &snapshot.purchases[0]);
    assert_eq!((principal.delivered, principal.refunded), (4, 2));
    assert!(std::ptr::eq(
        principal,
        ledger
            .purchase(order())
            .expect("the fixture purchase is present")
    ));
    assert_eq!(
        ledger.retire_purchase(order()),
        Err(MonetaryError::OpenPrincipal)
    );
    assert_eq!(ledger.snapshot(), snapshot);
    ledger
        .settle_purchase(order(), 8)
        .expect("the fixture settles the authored purchase");
    ledger
        .retire_purchase(order())
        .expect("the fixture retires the authored purchase");
    assert!(ledger.purchases().next().is_none());
    assert_eq!(ledger.snapshot().purchases.len(), 0);
    assert_eq!(ledger.cash_accounts().len(), 2);
    assert_eq!(
        ledger
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        money(140)
    );
}
