//! Exact money principals for the material circuit, without credit or issuance.
//!
//! Spendable cash excludes purchase and payroll reserves. Every cash movement
//! produces equal opposite postings. Goods, title, physical delivery and work
//! allocation remain the caller's authority; this book neither advances freight
//! nor turns payment into proof of production. It deliberately has no default:
//! a monetary campaign must capture opening accounts explicitly.

use std::collections::BTreeMap;

use babylon_kernel::currency::Currency;

use crate::{FinalDemandPrincipalId, OutboundOrderId, SiteId, MAX_MATERIAL_CIRCUIT_ROWS};

crate::model::identity_type!(OrganizationAccountId);
crate::model::identity_type!(PublicAccountId);
crate::model::identity_type!(ShiftId);

/// Owner namespaces stay distinct even when their underlying bytes coincide.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum AccountId {
    Site(SiteId),
    Household(FinalDemandPrincipalId),
    Organization(OrganizationAccountId),
    Public(PublicAccountId),
}

/// Nonnegative spendable cash; reserves belong only to their separate principal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CashAccount {
    pub id: AccountId,
    pub cash: Currency,
}

/// A price fixed at admission, in micro-currency per native order unit.
///
/// `delivered` and `refunded` are disjoint cumulative quantities. The unconsumed
/// remainder alone is reserved money. No extra account balance duplicates it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PurchaseEscrow {
    pub order: OutboundOrderId,
    pub buyer: AccountId,
    pub seller: AccountId,
    pub quantity: u64,
    pub unit_price: Currency,
    pub delivered: u64,
    pub refunded: u64,
}

impl PurchaseEscrow {
    /// Capture one complete order principal before any settlement or refund.
    /// # Errors
    /// Refuses identical parties, zero quantities, nonpositive prices or overflow.
    pub fn new(
        order: OutboundOrderId,
        buyer: AccountId,
        seller: AccountId,
        quantity: u64,
        unit_price: Currency,
    ) -> Result<Self, MonetaryError> {
        let row = Self {
            order,
            buyer,
            seller,
            quantity,
            unit_price,
            delivered: 0,
            refunded: 0,
        };
        row.validate()?;
        Ok(row)
    }

    /// Exact unspent reserve after disjoint delivery and refund quantities.
    /// # Errors
    /// Refuses invalid public snapshot rows and unrepresentable money amounts.
    pub fn reserved_amount(&self) -> Result<Currency, MonetaryError> {
        self.validate()?;
        let remaining = self
            .quantity
            .checked_sub(self.closed_quantity()?)
            .ok_or(MonetaryError::QuantityExceedsPrincipal)?;
        quantity_amount(remaining, self.unit_price)
    }

    fn closed_quantity(&self) -> Result<u64, MonetaryError> {
        self.delivered
            .checked_add(self.refunded)
            .ok_or(MonetaryError::Arithmetic)
    }

    fn validate(&self) -> Result<(), MonetaryError> {
        distinct_parties(self.buyer, self.seller)?;
        if self.quantity == 0 {
            return Err(MonetaryError::ZeroQuantity);
        }
        positive_amount(self.unit_price)?;
        quantity_amount(self.quantity, self.unit_price)?;
        if self.closed_quantity()? > self.quantity {
            return Err(MonetaryError::QuantityExceedsPrincipal);
        }
        Ok(())
    }
}

/// Attendance obligations do not depend on productive use of the funded hours.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ShiftState {
    Reserved,
    Accrued,
    Paid,
    Cancelled,
}

/// One fully funded attendance commitment; partial attendance is not inferred.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FundedShift {
    pub id: ShiftId,
    pub employer: AccountId,
    pub payee: AccountId,
    pub period: u64,
    pub committed_hours: u64,
    pub hourly_rate: Currency,
    pub state: ShiftState,
}

impl FundedShift {
    /// Capture the wage for all committed hours, including any paid idle time.
    /// # Errors
    /// Refuses identical parties, zero hours, nonpositive rates or overflow.
    pub fn new(
        id: ShiftId,
        employer: AccountId,
        payee: AccountId,
        period: u64,
        committed_hours: u64,
        hourly_rate: Currency,
    ) -> Result<Self, MonetaryError> {
        let row = Self {
            id,
            employer,
            payee,
            period,
            committed_hours,
            hourly_rate,
            state: ShiftState::Reserved,
        };
        row.validate()?;
        Ok(row)
    }

    /// Unspent payroll principal, whether attendance is reserved or already owed.
    /// # Errors
    /// Refuses invalid snapshot rows or an unrepresentable commitment.
    pub fn reserved_amount(&self) -> Result<Currency, MonetaryError> {
        self.validate()?;
        match self.state {
            ShiftState::Reserved | ShiftState::Accrued => self.amount(),
            ShiftState::Paid | ShiftState::Cancelled => Ok(zero()),
        }
    }

    /// Employer payable and worker receivable share this one exact obligation.
    /// # Errors
    /// Refuses invalid snapshot rows or an unrepresentable commitment.
    pub fn outstanding_wages(&self) -> Result<Currency, MonetaryError> {
        self.validate()?;
        if self.state == ShiftState::Accrued {
            self.amount()
        } else {
            Ok(zero())
        }
    }

    fn amount(&self) -> Result<Currency, MonetaryError> {
        quantity_amount(self.committed_hours, self.hourly_rate)
    }

    fn validate(&self) -> Result<(), MonetaryError> {
        distinct_parties(self.employer, self.payee)?;
        if self.committed_hours == 0 {
            return Err(MonetaryError::ZeroQuantity);
        }
        positive_amount(self.hourly_rate)?;
        self.amount()?;
        Ok(())
    }
}

/// Finite transfer purposes; the caller must adjudicate their eligibility.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CashTransferPurpose {
    Tax,
    PublicTransfer,
    HouseholdTransfer,
    OwnershipDistribution,
    CapitalContribution,
    TransportService,
    MutualAid,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MoneyLocation {
    Cash(AccountId),
    PurchaseReserve(OutboundOrderId),
    PayrollReserve(ShiftId),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MoneyTransferPurpose {
    PurchaseReservation(OutboundOrderId),
    DeliverySettlement(OutboundOrderId),
    PurchaseRefund(OutboundOrderId),
    ShiftReservation(ShiftId),
    WagePayment(ShiftId),
    ShiftCancellation(ShiftId),
    Cash(CashTransferPurpose),
}

/// Signed cash or reserve delta. One transfer always has two opposite postings.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MoneyPosting {
    pub location: MoneyLocation,
    pub delta: Currency,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MoneyTransferReceipt {
    pub purpose: MoneyTransferPurpose,
    pub debit: MoneyPosting,
    pub credit: MoneyPosting,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PurchaseMovementReceipt {
    pub order: OutboundOrderId,
    pub quantity: u64,
    pub cumulative_quantity: u64,
    pub transfer: MoneyTransferReceipt,
}

/// A payable/receivable pair, without a cash movement or a claim about new value.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WageAccrualReceipt {
    pub shift: ShiftId,
    pub employer: AccountId,
    pub payee: AccountId,
    pub period: u64,
    pub obligated_hours: u64,
    pub amount: Currency,
}

/// Complete current state for canonical wire encoding; no historical journal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MonetaryBookSnapshot {
    pub accounts: Vec<CashAccount>,
    pub purchases: Vec<PurchaseEscrow>,
    pub shifts: Vec<FundedShift>,
}

/// A bounded current book; every operation validates before any mutation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MonetaryBook {
    accounts: BTreeMap<AccountId, Currency>,
    purchases: BTreeMap<OutboundOrderId, PurchaseEscrow>,
    shifts: BTreeMap<ShiftId, FundedShift>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MonetaryError {
    RowLimit,
    DuplicateAccount,
    UnknownAccount,
    NegativeCash,
    NonPositiveAmount,
    IdenticalParties,
    ZeroQuantity,
    Arithmetic,
    InsufficientCash,
    DuplicatePurchase,
    UnknownPurchase,
    NonOpeningPurchase,
    NonIncreasingQuantity,
    QuantityExceedsPrincipal,
    DuplicateShift,
    UnknownShift,
    ShiftNotReserved,
    ShiftNotAccrued,
    OpenPrincipal,
}

impl std::fmt::Display for MonetaryError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "monetary book refused: {self:?}")
    }
}

impl std::error::Error for MonetaryError {}

impl MonetaryBook {
    /// Capture explicit opening balances. This is the only issuance boundary.
    /// # Errors
    /// Refuses duplicate accounts, negative cash or an exceeded row bound.
    pub fn open(accounts: Vec<CashAccount>) -> Result<Self, MonetaryError> {
        Self::from_snapshot(MonetaryBookSnapshot {
            accounts,
            purchases: vec![],
            shifts: vec![],
        })
    }

    /// Validate a complete snapshot; output iteration is canonical identity order.
    ///
    /// Cash rows already exclude all reserves. Reconstruction does not subtract
    /// them again. Cross-checks against physical orders belong to the host codec.
    /// # Errors
    /// Refuses row overflow, duplicate principals, absent owners or invalid rows.
    pub fn from_snapshot(snapshot: MonetaryBookSnapshot) -> Result<Self, MonetaryError> {
        row_limit(snapshot.accounts.len())?;
        row_limit(snapshot.purchases.len())?;
        row_limit(snapshot.shifts.len())?;
        let mut book = Self {
            accounts: BTreeMap::new(),
            purchases: BTreeMap::new(),
            shifts: BTreeMap::new(),
        };
        for row in snapshot.accounts {
            if row.cash.micro_units() < 0 {
                return Err(MonetaryError::NegativeCash);
            }
            if book.accounts.insert(row.id, row.cash).is_some() {
                return Err(MonetaryError::DuplicateAccount);
            }
        }
        for row in snapshot.purchases {
            row.validate()?;
            book.cash(row.buyer)?;
            book.cash(row.seller)?;
            if book.purchases.insert(row.order, row).is_some() {
                return Err(MonetaryError::DuplicatePurchase);
            }
        }
        for row in snapshot.shifts {
            row.validate()?;
            book.cash(row.employer)?;
            book.cash(row.payee)?;
            if book.shifts.insert(row.id, row).is_some() {
                return Err(MonetaryError::DuplicateShift);
            }
        }
        Ok(book)
    }

    /// Snapshot rows always appear in canonical identity order.
    #[must_use]
    pub fn snapshot(&self) -> MonetaryBookSnapshot {
        MonetaryBookSnapshot {
            accounts: self
                .accounts
                .iter()
                .map(|(&id, &cash)| CashAccount { id, cash })
                .collect(),
            purchases: self.purchases.values().cloned().collect(),
            shifts: self.shifts.values().cloned().collect(),
        }
    }

    /// # Errors
    /// Refuses an account absent from the captured book.
    pub fn cash(&self, account: AccountId) -> Result<Currency, MonetaryError> {
        self.accounts
            .get(&account)
            .copied()
            .ok_or(MonetaryError::UnknownAccount)
    }

    /// # Errors
    /// Refuses an absent or explicitly retired order principal.
    pub fn purchase(&self, order: OutboundOrderId) -> Result<&PurchaseEscrow, MonetaryError> {
        self.purchases
            .get(&order)
            .ok_or(MonetaryError::UnknownPurchase)
    }

    /// # Errors
    /// Refuses an absent or explicitly retired shift principal.
    pub fn shift(&self, id: ShiftId) -> Result<&FundedShift, MonetaryError> {
        self.shifts.get(&id).ok_or(MonetaryError::UnknownShift)
    }

    /// Sum each cash principal exactly once; wage claims are not extra money.
    /// # Errors
    /// Refuses an aggregate outside the exact currency range.
    pub fn total_cash_and_reserves(&self) -> Result<Currency, MonetaryError> {
        let mut total = zero();
        for cash in self.accounts.values() {
            total = add(total, *cash)?;
        }
        for purchase in self.purchases.values() {
            total = add(total, purchase.reserved_amount()?)?;
        }
        for shift in self.shifts.values() {
            total = add(total, shift.reserved_amount()?)?;
        }
        Ok(total)
    }

    /// Fund the original order exactly once; this records no sale or title change.
    /// # Errors
    /// Refuses malformed or duplicate orders, unknown parties, or insufficient cash.
    pub fn reserve_purchase(
        &mut self,
        row: PurchaseEscrow,
    ) -> Result<MoneyTransferReceipt, MonetaryError> {
        row.validate()?;
        if row.delivered != 0 || row.refunded != 0 {
            return Err(MonetaryError::NonOpeningPurchase);
        }
        if self.purchases.contains_key(&row.order) {
            return Err(MonetaryError::DuplicatePurchase);
        }
        insertion_limit(self.purchases.len())?;
        self.cash(row.seller)?;
        let amount = row.reserved_amount()?;
        let cash = self.cash_after_debit(row.buyer, amount)?;
        let receipt = transfer_receipt(
            MoneyTransferPurpose::PurchaseReservation(row.order),
            MoneyLocation::Cash(row.buyer),
            MoneyLocation::PurchaseReserve(row.order),
            amount,
        )?;
        self.accounts.insert(row.buyer, cash);
        self.purchases.insert(row.order, row);
        Ok(receipt)
    }

    /// Settle only newly accepted arrival or local-handoff quantity.
    ///
    /// The host must supply the physical order's cumulative delivered quantity,
    /// never its dispatched quantity. A repeated or decreasing total is refused.
    /// # Errors
    /// Refuses missing principals, duplicate delivery, excess quantities or overflow.
    pub fn settle_purchase(
        &mut self,
        order: OutboundOrderId,
        cumulative_delivered: u64,
    ) -> Result<PurchaseMovementReceipt, MonetaryError> {
        self.resolve_purchase(order, cumulative_delivered, PurchaseResolution::Delivered)
    }

    /// Refund newly lost or cancelled units, without paying the seller.
    /// # Errors
    /// Refuses missing principals, duplicate refunds, excess quantities or overflow.
    pub fn refund_purchase(
        &mut self,
        order: OutboundOrderId,
        cumulative_refunded: u64,
    ) -> Result<PurchaseMovementReceipt, MonetaryError> {
        self.resolve_purchase(order, cumulative_refunded, PurchaseResolution::Refunded)
    }

    fn resolve_purchase(
        &mut self,
        order: OutboundOrderId,
        cumulative: u64,
        resolution: PurchaseResolution,
    ) -> Result<PurchaseMovementReceipt, MonetaryError> {
        let mut row = self.purchase(order)?.clone();
        let (previous, recipient, purpose) = match resolution {
            PurchaseResolution::Delivered => (
                row.delivered,
                row.seller,
                MoneyTransferPurpose::DeliverySettlement(order),
            ),
            PurchaseResolution::Refunded => (
                row.refunded,
                row.buyer,
                MoneyTransferPurpose::PurchaseRefund(order),
            ),
        };
        if cumulative <= previous {
            return Err(MonetaryError::NonIncreasingQuantity);
        }
        let quantity = cumulative
            .checked_sub(previous)
            .ok_or(MonetaryError::Arithmetic)?;
        match resolution {
            PurchaseResolution::Delivered => row.delivered = cumulative,
            PurchaseResolution::Refunded => row.refunded = cumulative,
        }
        row.validate()?;
        let amount = quantity_amount(quantity, row.unit_price)?;
        let cash = add(self.cash(recipient)?, amount)?;
        let transfer = transfer_receipt(
            purpose,
            MoneyLocation::PurchaseReserve(order),
            MoneyLocation::Cash(recipient),
            amount,
        )?;
        self.accounts.insert(recipient, cash);
        self.purchases.insert(order, row);
        Ok(PurchaseMovementReceipt {
            order,
            quantity,
            cumulative_quantity: cumulative,
            transfer,
        })
    }

    /// Retire a closed financial principal alongside its physical order.
    ///
    /// The host must never reuse retired order identities. Completed evidence
    /// belongs in committed receipts, not an ever-growing live tombstone table.
    /// # Errors
    /// Refuses unknown orders or any remaining reserved money.
    pub fn retire_purchase(
        &mut self,
        order: OutboundOrderId,
    ) -> Result<PurchaseEscrow, MonetaryError> {
        if self.purchase(order)?.reserved_amount()? != zero() {
            return Err(MonetaryError::OpenPrincipal);
        }
        self.purchases
            .remove(&order)
            .ok_or(MonetaryError::UnknownPurchase)
    }

    /// Reserve the full attendance wage before admitting the shift.
    /// # Errors
    /// Refuses duplicate or nonopening shifts, invalid rows or insufficient cash.
    pub fn reserve_shift(
        &mut self,
        row: FundedShift,
    ) -> Result<MoneyTransferReceipt, MonetaryError> {
        row.validate()?;
        if row.state != ShiftState::Reserved {
            return Err(MonetaryError::ShiftNotReserved);
        }
        if self.shifts.contains_key(&row.id) {
            return Err(MonetaryError::DuplicateShift);
        }
        insertion_limit(self.shifts.len())?;
        self.cash(row.payee)?;
        let amount = row.amount()?;
        let cash = self.cash_after_debit(row.employer, amount)?;
        let receipt = transfer_receipt(
            MoneyTransferPurpose::ShiftReservation(row.id),
            MoneyLocation::Cash(row.employer),
            MoneyLocation::PayrollReserve(row.id),
            amount,
        )?;
        self.accounts.insert(row.employer, cash);
        self.shifts.insert(row.id, row);
        Ok(receipt)
    }

    /// Accrue all committed attendance independently of its productive use.
    ///
    /// This records an employer payable and matching worker receivable without
    /// paying cash. It needs no prediction of later work: wage-funded household
    /// purchases can determine handling work after payment. Utilization and paid
    /// idle hours belong to the host's separate labor-use receipt.
    /// # Errors
    /// Refuses unknown or already accrued shifts.
    pub fn accrue_shift(&mut self, id: ShiftId) -> Result<WageAccrualReceipt, MonetaryError> {
        let mut row = self.shift(id)?.clone();
        if row.state != ShiftState::Reserved {
            return Err(MonetaryError::ShiftNotReserved);
        }
        let receipt = WageAccrualReceipt {
            shift: id,
            employer: row.employer,
            payee: row.payee,
            period: row.period,
            obligated_hours: row.committed_hours,
            amount: row.amount()?,
        };
        row.state = ShiftState::Accrued;
        self.shifts.insert(id, row);
        Ok(receipt)
    }

    /// Pay an accrued obligation from its reserve and extinguish that claim.
    /// # Errors
    /// Refuses an unaccrued or already paid shift, or recipient cash overflow.
    pub fn pay_shift(&mut self, id: ShiftId) -> Result<MoneyTransferReceipt, MonetaryError> {
        let mut row = self.shift(id)?.clone();
        if row.state != ShiftState::Accrued {
            return Err(MonetaryError::ShiftNotAccrued);
        }
        let amount = row.amount()?;
        let cash = add(self.cash(row.payee)?, amount)?;
        let receipt = transfer_receipt(
            MoneyTransferPurpose::WagePayment(id),
            MoneyLocation::PayrollReserve(id),
            MoneyLocation::Cash(row.payee),
            amount,
        )?;
        row.state = ShiftState::Paid;
        self.accounts.insert(row.payee, cash);
        self.shifts.insert(id, row);
        Ok(receipt)
    }

    /// Refund a cancelled commitment only before attendance earned its wage.
    /// # Errors
    /// Refuses accrued/paid/cancelled shifts, or recipient cash overflow.
    pub fn cancel_unearned_shift(
        &mut self,
        id: ShiftId,
    ) -> Result<MoneyTransferReceipt, MonetaryError> {
        let mut row = self.shift(id)?.clone();
        if row.state != ShiftState::Reserved {
            return Err(MonetaryError::ShiftNotReserved);
        }
        let amount = row.amount()?;
        let cash = add(self.cash(row.employer)?, amount)?;
        let receipt = transfer_receipt(
            MoneyTransferPurpose::ShiftCancellation(id),
            MoneyLocation::PayrollReserve(id),
            MoneyLocation::Cash(row.employer),
            amount,
        )?;
        row.state = ShiftState::Cancelled;
        self.accounts.insert(row.employer, cash);
        self.shifts.insert(id, row);
        Ok(receipt)
    }

    /// Remove a paid or cancelled shift after its receipt is committed.
    /// The host must never reuse retired shift identities.
    /// # Errors
    /// Refuses unknown shifts, live reserves or unpaid obligations.
    pub fn retire_shift(&mut self, id: ShiftId) -> Result<FundedShift, MonetaryError> {
        if self.shift(id)?.reserved_amount()? != zero() {
            return Err(MonetaryError::OpenPrincipal);
        }
        self.shifts.remove(&id).ok_or(MonetaryError::UnknownShift)
    }

    /// An exact funded cash transfer, with an explicit material purpose.
    /// # Errors
    /// Refuses identical or missing parties, nonpositive amounts, insufficient
    /// cash or overflow. Neither party is changed on failure.
    pub fn transfer_cash(
        &mut self,
        sender: AccountId,
        recipient: AccountId,
        amount: Currency,
        purpose: CashTransferPurpose,
    ) -> Result<MoneyTransferReceipt, MonetaryError> {
        distinct_parties(sender, recipient)?;
        positive_amount(amount)?;
        let debited_cash = self.cash_after_debit(sender, amount)?;
        let credited_cash = add(self.cash(recipient)?, amount)?;
        let receipt = transfer_receipt(
            MoneyTransferPurpose::Cash(purpose),
            MoneyLocation::Cash(sender),
            MoneyLocation::Cash(recipient),
            amount,
        )?;
        self.accounts.insert(sender, debited_cash);
        self.accounts.insert(recipient, credited_cash);
        Ok(receipt)
    }

    fn cash_after_debit(
        &self,
        account: AccountId,
        amount: Currency,
    ) -> Result<Currency, MonetaryError> {
        let cash = self.cash(account)?;
        if cash < amount {
            return Err(MonetaryError::InsufficientCash);
        }
        cash.checked_sub(amount)
            .map_err(|_| MonetaryError::Arithmetic)
    }
}

#[derive(Clone, Copy)]
enum PurchaseResolution {
    Delivered,
    Refunded,
}

fn zero() -> Currency {
    Currency::from_micro_units(0)
}

fn add(left: Currency, right: Currency) -> Result<Currency, MonetaryError> {
    left.checked_add(right)
        .map_err(|_| MonetaryError::Arithmetic)
}

fn quantity_amount(quantity: u64, unit_price: Currency) -> Result<Currency, MonetaryError> {
    unit_price
        .micro_units()
        .checked_mul(i128::from(quantity))
        .map(Currency::from_micro_units)
        .ok_or(MonetaryError::Arithmetic)
}

fn positive_amount(amount: Currency) -> Result<(), MonetaryError> {
    if amount.micro_units() <= 0 {
        Err(MonetaryError::NonPositiveAmount)
    } else {
        Ok(())
    }
}

fn distinct_parties(left: AccountId, right: AccountId) -> Result<(), MonetaryError> {
    if left == right {
        Err(MonetaryError::IdenticalParties)
    } else {
        Ok(())
    }
}

fn row_limit(length: usize) -> Result<(), MonetaryError> {
    if length > MAX_MATERIAL_CIRCUIT_ROWS {
        Err(MonetaryError::RowLimit)
    } else {
        Ok(())
    }
}

fn insertion_limit(length: usize) -> Result<(), MonetaryError> {
    row_limit(length.checked_add(1).ok_or(MonetaryError::Arithmetic)?)
}

fn transfer_receipt(
    purpose: MoneyTransferPurpose,
    from: MoneyLocation,
    to: MoneyLocation,
    amount: Currency,
) -> Result<MoneyTransferReceipt, MonetaryError> {
    positive_amount(amount)?;
    let debit = zero()
        .checked_sub(amount)
        .map_err(|_| MonetaryError::Arithmetic)?;
    Ok(MoneyTransferReceipt {
        purpose,
        debit: MoneyPosting {
            location: from,
            delta: debit,
        },
        credit: MoneyPosting {
            location: to,
            delta: amount,
        },
    })
}
