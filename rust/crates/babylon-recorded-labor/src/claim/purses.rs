use super::kind::Claim;
use super::mix::Mix;
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, CircuitAccounting, FinalDemandPrincipalId,
    MaterialCircuitState, MoneyLocation, MoneyTransferPurpose, MoneyTransferReceipt,
    OutboundOrderId,
};
use std::collections::BTreeMap;
use std::error::Error;
use std::fmt::{Display, Formatter, Result as FmtResult};

/// What paid for each order this period: the mix that left its reserve by `DeliverySettlement`.
pub type Paid = BTreeMap<OutboundOrderId, Mix>;

/// Why the purses could not follow or match the money.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ClaimError {
    /// An amount left the range of the arithmetic.
    Arithmetic,
    /// The state keeps no money book.
    NotMonetary,
    /// More was drawn than a purse or reserve holds.
    Overdrawn,
    /// Hours to split, and no money that paid for them.
    Unpaid,
    /// Hours reached a household by an order that nothing paid for.
    UnknownOrder(OutboundOrderId),
    /// A household's transfer of a purpose or a side the kinds do not name.
    Unexpected {
        /// The transfer's place in the period's list.
        index: usize,
    },
    /// A household's kinds are not its cash in the book.
    PurseDiffers {
        /// The household.
        principal: FinalDemandPrincipalId,
        /// Millionths held by kind.
        kinds: i128,
        /// Millionths in the book.
        book: i128,
    },
    /// The kinds held for an order are not that purchase's reserve in the book.
    ReserveDiffers {
        /// The order.
        order: OutboundOrderId,
        /// Millionths held by kind.
        kinds: i128,
        /// Millionths in the book.
        book: i128,
    },
}

impl Display for ClaimError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::Arithmetic => write!(f, "an amount left the range of the arithmetic"),
            Self::NotMonetary => write!(f, "the state keeps no money book"),
            Self::Overdrawn => write!(f, "more was drawn than the purse holds"),
            Self::Unpaid => write!(f, "hours to split and no money that paid for them"),
            Self::UnknownOrder(order) => write!(f, "nothing paid for the order {order:?}"),
            Self::Unexpected { index } => {
                write!(f, "the household's transfer {index} is of no kind named")
            }
            Self::PurseDiffers {
                principal,
                kinds,
                book,
            } => write!(
                f,
                "the kinds of {principal:?}'s purse hold {kinds} millionths, the book {book}"
            ),
            Self::ReserveDiffers { order, kinds, book } => write!(
                f,
                "the kinds held for {order:?} are {kinds} millionths, the book's reserve {book}"
            ),
        }
    }
}

impl Error for ClaimError {}

/// Every household's purse by kind, and the money set aside for each of its open orders.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Purses {
    cash: BTreeMap<FinalDemandPrincipalId, Mix>,
    reserves: BTreeMap<OutboundOrderId, (FinalDemandPrincipalId, Mix)>,
}

fn household_of(location: MoneyLocation) -> Option<FinalDemandPrincipalId> {
    match location {
        MoneyLocation::Cash(AccountId::Household(principal)) => Some(principal),
        _ => None,
    }
}

fn kind_of(purpose: CashTransferPurpose) -> Option<Claim> {
    match purpose {
        CashTransferPurpose::OwnershipDistribution => Some(Claim::Owning),
        CashTransferPurpose::PublicTransfer
        | CashTransferPurpose::HouseholdTransfer
        | CashTransferPurpose::MutualAid => Some(Claim::Support),
        _ => None,
    }
}

fn as_amount(micro: i128) -> Result<i128, ClaimError> {
    if micro < 0 {
        Err(ClaimError::Arithmetic)
    } else {
        Ok(micro)
    }
}

impl Purses {
    /// Every household's cash and open reserves at the opening, all `NotRecorded`.
    ///
    /// # Errors
    /// `NotMonetary`; `Arithmetic`.
    pub fn open(state: &MaterialCircuitState) -> Result<Self, ClaimError> {
        let CircuitAccounting::Monetary(circuit) = &state.accounting else {
            return Err(ClaimError::NotMonetary);
        };
        let mut cash = BTreeMap::new();
        for (id, amount) in circuit.book.cash_accounts() {
            if let AccountId::Household(principal) = id {
                let held = Mix::of(Claim::NotRecorded, as_amount(amount.micro_units())?);
                cash.insert(*principal, held);
            }
        }
        let mut reserves = BTreeMap::new();
        for purchase in circuit.book.purchases() {
            if let AccountId::Household(principal) = purchase.buyer {
                let set_aside = purchase
                    .reserved_amount()
                    .map_err(|_| ClaimError::Arithmetic)?;
                let held = Mix::of(Claim::NotRecorded, as_amount(set_aside.micro_units())?);
                if held.total()? > 0 {
                    reserves.insert(purchase.order, (principal, held));
                }
            }
        }
        Ok(Self { cash, reserves })
    }

    /// No purse and no reserve.
    #[cfg(test)]
    pub(super) fn empty() -> Self {
        Self {
            cash: BTreeMap::new(),
            reserves: BTreeMap::new(),
        }
    }

    /// What a household's purse holds by kind.
    #[must_use]
    pub fn cash_of(&self, principal: FinalDemandPrincipalId) -> Mix {
        self.cash.get(&principal).copied().unwrap_or_default()
    }

    /// What is held for an open order by kind.
    #[must_use]
    pub fn reserve_of(&self, order: OutboundOrderId) -> Mix {
        self.reserves
            .get(&order)
            .map(|(_, mix)| *mix)
            .unwrap_or_default()
    }

    /// Follow the period's transfers in their order; what paid for each order. The purses are unchanged on an
    /// error.
    ///
    /// # Errors
    /// `Unexpected { index }` for a household's transfer of a purpose no kind is named for; `Overdrawn`;
    /// `Arithmetic`.
    pub fn follow(&mut self, transfers: &[MoneyTransferReceipt]) -> Result<Paid, ClaimError> {
        let mut next = self.clone();
        let mut paid = Paid::new();
        for (index, transfer) in transfers.iter().enumerate() {
            next.apply(transfer, &mut paid)
                .map_err(|error| match error {
                    ClaimError::Unexpected { .. } => ClaimError::Unexpected { index },
                    other => other,
                })?;
        }
        *self = next;
        Ok(paid)
    }

    fn apply(
        &mut self,
        transfer: &MoneyTransferReceipt,
        paid: &mut Paid,
    ) -> Result<(), ClaimError> {
        let amount = as_amount(transfer.credit.delta.micro_units())?;
        let from = household_of(transfer.debit.location);
        let to = household_of(transfer.credit.location);
        let unexpected = ClaimError::Unexpected { index: 0 };
        match transfer.purpose {
            MoneyTransferPurpose::PurchaseReservation(order) => {
                if to.is_some() {
                    return Err(unexpected);
                }
                if let Some(principal) = from {
                    let taken = self.draw_cash(principal, amount)?;
                    self.put_reserve(order, principal, taken)?;
                }
            }
            MoneyTransferPurpose::DeliverySettlement(order) => {
                if to.is_some() {
                    return Err(unexpected);
                }
                if self.reserves.contains_key(&order) {
                    let taken = self.draw_reserve(order, amount)?;
                    paid.entry(order).or_default().add(taken)?;
                }
            }
            MoneyTransferPurpose::PurchaseRefund(order) => {
                if let Some((principal, _)) = self.reserves.get(&order).copied() {
                    let taken = self.draw_reserve(order, amount)?;
                    self.put_cash(principal, taken)?;
                }
            }
            MoneyTransferPurpose::ShiftReservation(_)
            | MoneyTransferPurpose::ShiftCancellation(_) => {
                if from.is_some() || to.is_some() {
                    return Err(unexpected);
                }
            }
            MoneyTransferPurpose::WagePayment(_) => {
                if from.is_some() {
                    return Err(unexpected);
                }
                if let Some(principal) = to {
                    self.put_cash(principal, Mix::of(Claim::Work, amount))?;
                }
            }
            MoneyTransferPurpose::Cash(purpose) => {
                if let Some(principal) = from {
                    self.draw_cash(principal, amount)?;
                }
                if let Some(principal) = to {
                    let claim = kind_of(purpose).ok_or(unexpected)?;
                    self.put_cash(principal, Mix::of(claim, amount))?;
                }
            }
        }
        Ok(())
    }

    fn draw_cash(
        &mut self,
        principal: FinalDemandPrincipalId,
        amount: i128,
    ) -> Result<Mix, ClaimError> {
        self.cash
            .get_mut(&principal)
            .ok_or(ClaimError::Overdrawn)?
            .draw(amount)
    }

    fn put_cash(&mut self, principal: FinalDemandPrincipalId, mix: Mix) -> Result<(), ClaimError> {
        self.cash.entry(principal).or_default().add(mix)
    }

    fn put_reserve(
        &mut self,
        order: OutboundOrderId,
        principal: FinalDemandPrincipalId,
        mix: Mix,
    ) -> Result<(), ClaimError> {
        self.reserves
            .entry(order)
            .or_insert_with(|| (principal, Mix::default()))
            .1
            .add(mix)
    }

    fn draw_reserve(&mut self, order: OutboundOrderId, amount: i128) -> Result<Mix, ClaimError> {
        let (_, held) = self.reserves.get_mut(&order).ok_or(ClaimError::Overdrawn)?;
        let taken = held.draw(amount)?;
        if held.total()? == 0 {
            self.reserves.remove(&order);
        }
        Ok(taken)
    }

    /// Each household's kinds equal its cash in the book; the kinds held for each open order equal that
    /// purchase's reserve.
    ///
    /// # Errors
    /// `NotMonetary`; `PurseDiffers`; `ReserveDiffers`; `Arithmetic`.
    pub fn check(&self, state: &MaterialCircuitState) -> Result<(), ClaimError> {
        let CircuitAccounting::Monetary(circuit) = &state.accounting else {
            return Err(ClaimError::NotMonetary);
        };
        let mut book_cash: BTreeMap<FinalDemandPrincipalId, i128> = BTreeMap::new();
        for (id, amount) in circuit.book.cash_accounts() {
            if let AccountId::Household(principal) = id {
                book_cash.insert(*principal, amount.micro_units());
            }
        }
        for principal in book_cash.keys().chain(self.cash.keys()) {
            let book = book_cash.get(principal).copied().unwrap_or(0);
            let kinds = self.cash_of(*principal).total()?;
            if kinds != book {
                return Err(ClaimError::PurseDiffers {
                    principal: *principal,
                    kinds,
                    book,
                });
            }
        }
        let mut book_reserves: BTreeMap<OutboundOrderId, i128> = BTreeMap::new();
        for purchase in circuit.book.purchases() {
            if matches!(purchase.buyer, AccountId::Household(_)) {
                let set_aside = purchase
                    .reserved_amount()
                    .map_err(|_| ClaimError::Arithmetic)?;
                book_reserves.insert(purchase.order, set_aside.micro_units());
            }
        }
        for order in book_reserves.keys().chain(self.reserves.keys()) {
            let book = book_reserves.get(order).copied().unwrap_or(0);
            let kinds = self.reserve_of(*order).total()?;
            if kinds != book {
                return Err(ClaimError::ReserveDiffers {
                    order: *order,
                    kinds,
                    book,
                });
            }
        }
        Ok(())
    }
}
