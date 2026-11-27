//! One closed period of the doubled world, read as hours, goods and payments.
//!
//! Every figure here comes from a receipt of the engine. Hours are `u64` hours, goods are `u64`
//! units and payments are `i128` millionths of a dollar; the three are never added together.

use babylon_circuit_worlds::{Good, Household, MovedBy, PeriodHours, PeriodResult, Workplace};
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, GoodId, MoneyLocation, MoneyTransferPurpose,
    MoneyTransferReceipt, OutboundOrderId, ShiftId,
};
use std::collections::BTreeMap;
use std::fmt::{Debug, Formatter, Result as FmtResult};

/// A holder of hours, goods or money in the doubled world.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Party {
    Workplace(Workplace),
    Household(Household),
    Treasury,
    Fund,
}

impl Party {
    /// The party that holds this account, or `None` for an account of no party of the world.
    #[must_use]
    pub fn from_account(account: AccountId) -> Option<Party> {
        match account {
            AccountId::Site(site) => Workplace::from_site(site).map(Party::Workplace),
            AccountId::Household(id) => Household::from_principal(id).map(Party::Household),
            AccountId::Public(id) if id == babylon_circuit_worlds::treasury() => {
                Some(Party::Treasury)
            }
            AccountId::Public(id) if id == babylon_circuit_worlds::fund() => Some(Party::Fund),
            AccountId::Public(_) | AccountId::Organization(_) | AccountId::Company(_) => None,
        }
    }

    #[must_use]
    pub fn label(self) -> String {
        match self {
            Self::Workplace(w) => w.label(),
            Self::Household(h) => h.label(),
            Self::Treasury => "Treasury".to_string(),
            Self::Fund => "Fund".to_string(),
        }
    }
}

/// The six kinds of payment the world makes.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum PaymentKind {
    Wages,
    Purchases,
    Taxes,
    Benefits,
    Profit,
    /// An owner's money put into a workplace it owns (`CashTransferPurpose::CapitalContribution`).
    Capital,
}

impl PaymentKind {
    pub const ALL: [PaymentKind; 6] = [
        PaymentKind::Wages,
        PaymentKind::Purchases,
        PaymentKind::Taxes,
        PaymentKind::Benefits,
        PaymentKind::Profit,
        PaymentKind::Capital,
    ];

    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::Wages => "wages",
            Self::Purchases => "purchases",
            Self::Taxes => "taxes",
            Self::Benefits => "benefits",
            Self::Profit => "profit",
            Self::Capital => "capital",
        }
    }
}

/// Hours one household gave one workplace in the period.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WorkFlow {
    pub household: Household,
    pub workplace: Workplace,
    /// Production, handling, maintenance and installation hours.
    pub given: u64,
    /// Hours on the clock that were paid and not used.
    pub idle: u64,
}

/// Units of one good that moved from one party to another.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GoodsMove {
    pub good: Good,
    pub from: Party,
    pub to: Party,
    pub quantity: u64,
    /// Units of the move that come from the opening stock, to the nearest whole unit (half up); `None` when
    /// the period has no record of hours.
    pub opening: Option<u64>,
}

/// One payment, counted once.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Payment {
    pub kind: PaymentKind,
    pub payer: Party,
    pub payee: Party,
    pub amount: i128,
}

/// A period as hours, goods and payments, each sorted by its fields' order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PeriodReading {
    pub period: u64,
    pub work: Vec<WorkFlow>,
    pub goods: Vec<GoodsMove>,
    pub payments: Vec<Payment>,
    /// Of every 100 units moved this period, how many come from the opening stock, to the nearest whole
    /// number (half up); `None` without a record of hours.
    pub opening_per_hundred: Option<u64>,
}

/// Why a period cannot be read.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ReadingError {
    /// A receipt names an account, a site or a good that belongs to no party or good of the world.
    UnknownParty(String),
    /// A payment of a shift or an order whose reservation is not in the period.
    UnpairedPayment(String),
    /// A transfer of a purpose the world does not make.
    UnexpectedPayment(String),
    /// A sum overflowed or a receipt's own law does not hold.
    Arithmetic,
}

impl std::fmt::Display for ReadingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::UnknownParty(what) => write!(f, "a receipt of no party of the world: {what}"),
            Self::UnpairedPayment(what) => write!(f, "a payment with no reservation: {what}"),
            Self::UnexpectedPayment(what) => {
                write!(f, "a transfer the world does not make: {what}")
            }
            Self::Arithmetic => write!(f, "a receipt's own sums do not hold"),
        }
    }
}

impl std::error::Error for ReadingError {}

/// Read one closed period.
///
/// # Errors
/// `ReadingError` when a receipt names no party, a payment has no reservation, a transfer is of
/// a purpose the world does not make, or a sum does not hold.
pub fn read_period(result: &PeriodResult) -> Result<PeriodReading, ReadingError> {
    let mut work = read_work(result)?;
    let mut goods = read_goods(result)?;
    let mut payments = read_payments(&result.receipts.money_transfers)?;
    work.sort_by_key(|f| (f.household, f.workplace, f.given, f.idle));
    goods.sort_by_key(|m| (m.good, m.from, m.to, m.quantity, m.opening));
    payments.sort_by_key(|p| (p.kind, p.payer, p.payee, p.amount));
    Ok(PeriodReading {
        period: result.period,
        work,
        goods,
        payments,
        opening_per_hundred: opening_per_hundred(result)?,
    })
}

/// Micro-units in one unit.
const MICRO_UNITS: u128 = 1_000_000;

/// A move's opening units from the record: to the nearest whole unit (half up), at most the move's quantity.
fn opening_units(
    hours: &PeriodHours,
    moved_by: MovedBy,
    receipt: &dyn Debug,
) -> Result<u64, ReadingError> {
    let record = hours
        .of_move(moved_by)
        .ok_or_else(|| ReadingError::UnknownParty(format!("{receipt:?}")))?;
    let rounded = record
        .opening_micro_units
        .checked_add(MICRO_UNITS / 2)
        .ok_or(ReadingError::Arithmetic)?
        / MICRO_UNITS;
    let whole = u64::try_from(rounded).map_err(|_| ReadingError::Arithmetic)?;
    Ok(whole.min(record.quantity))
}

/// Of every 100 units the period's moves carried, how many come from the opening stock (half up).
fn opening_per_hundred(result: &PeriodResult) -> Result<Option<u64>, ReadingError> {
    let Some(hours) = &result.hours else {
        return Ok(None);
    };
    let mut opening: u128 = 0;
    let mut quantity: u128 = 0;
    for record in &hours.moves {
        opening = opening
            .checked_add(record.opening_micro_units)
            .ok_or(ReadingError::Arithmetic)?;
        quantity = quantity
            .checked_add(u128::from(record.quantity))
            .ok_or(ReadingError::Arithmetic)?;
    }
    Ok(Some(share_of_hundred(opening, quantity)?))
}

/// Of every 100 units moved, how many come from the opening stock (half up): `opening` in micro-units of the
/// opening stock, `quantity` in whole units; 0 when nothing moved.
pub(super) fn share_of_hundred(opening: u128, quantity: u128) -> Result<u64, ReadingError> {
    let divisor = quantity
        .checked_mul(MICRO_UNITS)
        .ok_or(ReadingError::Arithmetic)?;
    if divisor == 0 {
        return Ok(0);
    }
    let share = opening
        .checked_mul(100)
        .and_then(|n| n.checked_add(divisor / 2))
        .ok_or(ReadingError::Arithmetic)?
        / divisor;
    u64::try_from(share).map_err(|_| ReadingError::Arithmetic)
}

fn read_work(result: &PeriodResult) -> Result<Vec<WorkFlow>, ReadingError> {
    let mut work = Vec::new();
    for receipt in &result.receipts.member_labor_use {
        let household = Household::from_principal(receipt.payee)
            .ok_or_else(|| ReadingError::UnknownParty(format!("{receipt:?}")))?;
        let workplace = Workplace::from_site(receipt.site_id)
            .ok_or_else(|| ReadingError::UnknownParty(format!("{receipt:?}")))?;
        // A pair member holds nobody until people move: its receipt of no hours is no flow.
        if household != workplace.workers() && receipt.attended_hours == 0 {
            continue;
        }
        let given = receipt
            .production_hours
            .checked_add(receipt.handling_hours)
            .and_then(|n| n.checked_add(receipt.maintenance_hours))
            .and_then(|n| n.checked_add(receipt.installation_hours))
            .ok_or(ReadingError::Arithmetic)?;
        if given.checked_add(receipt.idle_hours) != Some(receipt.attended_hours) {
            return Err(ReadingError::Arithmetic);
        }
        work.push(WorkFlow {
            household,
            workplace,
            given,
            idle: receipt.idle_hours,
        });
    }
    Ok(work)
}

fn party_of(account: AccountId, receipt: &dyn Debug) -> Result<Party, ReadingError> {
    Party::from_account(account).ok_or_else(|| ReadingError::UnknownParty(format!("{receipt:?}")))
}

fn good_of(id: GoodId, receipt: &dyn Debug) -> Result<Good, ReadingError> {
    Good::from_good(id).ok_or_else(|| ReadingError::UnknownParty(format!("{receipt:?}")))
}

fn read_goods(result: &PeriodResult) -> Result<Vec<GoodsMove>, ReadingError> {
    let receipts = &result.receipts;
    let hours = result.hours.as_ref();
    // The record holds a hand-over only for a move that moved something: a receipt of no unit is dropped below,
    // so it needs no opening.
    let opening = |moved_by: MovedBy,
                   quantity: u64,
                   receipt: &dyn Debug|
     -> Result<Option<u64>, ReadingError> {
        match (hours, quantity) {
            (None, _) => Ok(None),
            (Some(_), 0) => Ok(Some(0)),
            (Some(record), _) => opening_units(record, moved_by, receipt).map(Some),
        }
    };
    let mut goods = Vec::new();
    for (index, r) in receipts.service_performance.iter().enumerate() {
        goods.push(GoodsMove {
            good: good_of(r.good_id, r)?,
            from: party_of(AccountId::Site(r.provider_site_id), r)?,
            to: party_of(r.buyer, r)?,
            quantity: r.performed_quantity,
            opening: opening(MovedBy::ServicePerformance(index), r.performed_quantity, r)?,
        });
    }
    for (index, r) in receipts.local_transfers.iter().enumerate() {
        goods.push(GoodsMove {
            good: good_of(r.good_id, r)?,
            from: party_of(AccountId::Site(r.supplier_site_id), r)?,
            to: party_of(AccountId::Site(r.buyer_site_id), r)?,
            quantity: r.quantity,
            opening: opening(MovedBy::LocalTransfer(index), r.quantity, r)?,
        });
    }
    for (index, r) in receipts.local_fulfillments.iter().enumerate() {
        goods.push(GoodsMove {
            good: good_of(r.good_id, r)?,
            from: party_of(AccountId::Site(r.retailer_site_id), r)?,
            to: party_of(AccountId::Household(r.demand_principal_id), r)?,
            quantity: r.quantity,
            opening: opening(MovedBy::LocalFulfillment(index), r.quantity, r)?,
        });
    }
    goods.retain(|m| m.quantity > 0);
    Ok(goods)
}

/// The cash account at one end of a transfer.
fn cash_of(
    location: MoneyLocation,
    transfer: &MoneyTransferReceipt,
) -> Result<Party, ReadingError> {
    match location {
        MoneyLocation::Cash(account) => party_of(account, transfer),
        MoneyLocation::PurchaseReserve(_) | MoneyLocation::PayrollReserve(_) => {
            Err(ReadingError::UnexpectedPayment(format!("{transfer:?}")))
        }
    }
}

fn read_payments(transfers: &[MoneyTransferReceipt]) -> Result<Vec<Payment>, ReadingError> {
    let mut shifts: BTreeMap<ShiftId, &MoneyTransferReceipt> = BTreeMap::new();
    let mut orders: BTreeMap<OutboundOrderId, &MoneyTransferReceipt> = BTreeMap::new();
    for transfer in transfers {
        match transfer.purpose {
            MoneyTransferPurpose::ShiftReservation(shift) => {
                shifts.insert(shift, transfer);
            }
            MoneyTransferPurpose::PurchaseReservation(order) => {
                orders.insert(order, transfer);
            }
            MoneyTransferPurpose::DeliverySettlement(_)
            | MoneyTransferPurpose::PurchaseRefund(_)
            | MoneyTransferPurpose::WagePayment(_)
            | MoneyTransferPurpose::ShiftCancellation(_)
            | MoneyTransferPurpose::Cash(_) => {}
        }
    }
    let mut payments = Vec::new();
    for transfer in transfers {
        let amount = transfer.credit.delta.micro_units();
        let (kind, payer) = match transfer.purpose {
            MoneyTransferPurpose::WagePayment(shift) => {
                let reservation = shifts
                    .get(&shift)
                    .ok_or_else(|| ReadingError::UnpairedPayment(format!("{transfer:?}")))?;
                (
                    PaymentKind::Wages,
                    cash_of(reservation.debit.location, reservation)?,
                )
            }
            MoneyTransferPurpose::DeliverySettlement(order) => {
                let reservation = orders
                    .get(&order)
                    .ok_or_else(|| ReadingError::UnpairedPayment(format!("{transfer:?}")))?;
                (
                    PaymentKind::Purchases,
                    cash_of(reservation.debit.location, reservation)?,
                )
            }
            MoneyTransferPurpose::Cash(purpose) => {
                let kind = match purpose {
                    CashTransferPurpose::Tax => PaymentKind::Taxes,
                    CashTransferPurpose::PublicTransfer => PaymentKind::Benefits,
                    CashTransferPurpose::OwnershipDistribution => PaymentKind::Profit,
                    CashTransferPurpose::CapitalContribution => PaymentKind::Capital,
                    CashTransferPurpose::HouseholdTransfer
                    | CashTransferPurpose::TransportService
                    | CashTransferPurpose::MutualAid => {
                        return Err(ReadingError::UnexpectedPayment(format!("{transfer:?}")));
                    }
                };
                (kind, cash_of(transfer.debit.location, transfer)?)
            }
            MoneyTransferPurpose::PurchaseReservation(_)
            | MoneyTransferPurpose::PurchaseRefund(_)
            | MoneyTransferPurpose::ShiftReservation(_)
            | MoneyTransferPurpose::ShiftCancellation(_) => continue,
        };
        payments.push(Payment {
            kind,
            payer,
            payee: cash_of(transfer.credit.location, transfer)?,
            amount,
        });
    }
    Ok(payments)
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_circuit_worlds::{Kind, Place, Runner};
    use babylon_material_circuit::FinalDemandPrincipalId;
    use std::error::Error;

    type TestResult = Result<(), Box<dyn Error>>;

    fn first_period() -> Result<PeriodResult, Box<dyn Error>> {
        let mut runner = Runner::open()?;
        Ok(runner.step()?.clone())
    }

    fn total(reading: &PeriodReading, kind: PaymentKind) -> i128 {
        reading
            .payments
            .iter()
            .filter(|p| p.kind == kind)
            .map(|p| p.amount)
            .sum()
    }

    fn count(reading: &PeriodReading, kind: PaymentKind) -> usize {
        reading.payments.iter().filter(|p| p.kind == kind).count()
    }

    #[test]
    fn every_payment_of_the_quiet_period_is_read_once() -> TestResult {
        let reading = read_period(&first_period()?)?;
        assert_eq!(count(&reading, PaymentKind::Wages), 8);
        assert_eq!(total(&reading, PaymentKind::Wages), 4_800_000_000);
        assert_eq!(total(&reading, PaymentKind::Purchases), 10_320_000_000);
        assert_eq!(total(&reading, PaymentKind::Taxes), 1_280_000_000);
        assert_eq!(total(&reading, PaymentKind::Benefits), 1_280_000_000);
        assert_eq!(total(&reading, PaymentKind::Profit), 1_280_000_000);
        Ok(())
    }

    #[test]
    fn a_capital_contribution_is_read_as_capital() -> TestResult {
        let mut result = first_period()?;
        let transfer = result
            .receipts
            .money_transfers
            .iter_mut()
            .find(|t| {
                t.purpose == MoneyTransferPurpose::Cash(CashTransferPurpose::OwnershipDistribution)
            })
            .ok_or("a profit transfer")?;
        let amount = transfer.credit.delta.micro_units();
        transfer.purpose = MoneyTransferPurpose::Cash(CashTransferPurpose::CapitalContribution);
        std::mem::swap(&mut transfer.debit.location, &mut transfer.credit.location);
        let party = |location: MoneyLocation| match location {
            MoneyLocation::Cash(account) => Party::from_account(account),
            MoneyLocation::PurchaseReserve(_) | MoneyLocation::PayrollReserve(_) => None,
        };
        let from = party(transfer.debit.location).ok_or("the owner")?;
        let to = party(transfer.credit.location).ok_or("the site")?;
        assert!(matches!(from, Party::Household(_)));
        assert!(matches!(to, Party::Workplace(_)));
        let before = read_period(&first_period()?)?;
        let reading = read_period(&result)?;
        let capital: Vec<&Payment> = reading
            .payments
            .iter()
            .filter(|p| p.kind == PaymentKind::Capital)
            .collect();
        assert_eq!(capital.len(), 1);
        assert_eq!(
            (capital[0].payer, capital[0].payee, capital[0].amount),
            (from, to, amount)
        );
        assert_eq!(
            total(&reading, PaymentKind::Profit),
            total(&before, PaymentKind::Profit) - amount
        );
        for kind in [
            PaymentKind::Wages,
            PaymentKind::Purchases,
            PaymentKind::Taxes,
            PaymentKind::Benefits,
        ] {
            assert_eq!(total(&reading, kind), total(&before, kind));
        }
        Ok(())
    }

    #[test]
    fn the_quiet_period_gives_480_hours_and_no_idle_hour() -> TestResult {
        let reading = read_period(&first_period()?)?;
        assert_eq!(reading.work.len(), 8);
        let given_in = |place: Place| -> u64 {
            reading
                .work
                .iter()
                .filter(|f| f.workplace.place == place)
                .map(|f| f.given)
                .sum()
        };
        assert_eq!(given_in(Place::A), 240);
        assert_eq!(given_in(Place::B), 240);
        let by_kind = |kind: Kind| -> Vec<u64> {
            Workplace::ALL
                .iter()
                .filter(|w| w.kind == kind)
                .map(|w| {
                    reading
                        .work
                        .iter()
                        .filter(|f| f.workplace == *w)
                        .map(|f| f.given)
                        .sum()
                })
                .collect()
        };
        assert_eq!(by_kind(Kind::Utility), [120, 120]);
        assert_eq!(by_kind(Kind::Farm), [40, 40]);
        assert_eq!(by_kind(Kind::Clinic), [40, 40]);
        assert_eq!(by_kind(Kind::Shop), [40, 40]);
        assert!(reading.work.iter().all(|f| f.idle == 0));
        Ok(())
    }

    #[test]
    fn goods_move_along_their_own_paths() -> TestResult {
        let reading = read_period(&first_period()?)?;
        let of = |good: Good| -> Vec<&GoodsMove> {
            reading.goods.iter().filter(|m| m.good == good).collect()
        };
        let power = of(Good::Power);
        assert_eq!(power.len(), 16);
        assert_eq!(power.iter().map(|m| m.quantity).sum::<u64>(), 240);
        for place in Place::ALL {
            let utility = Party::Workplace(Workplace {
                place,
                kind: Kind::Utility,
            });
            for kind in [Kind::Farm, Kind::Clinic] {
                let own = Party::Workplace(Workplace { place, kind });
                assert!(
                    power
                        .iter()
                        .any(|m| m.from == utility && m.to == own && m.quantity == 40),
                    "{place:?} {kind:?}"
                );
            }
        }
        for household in Household::ALL {
            let to_it: Vec<u64> = power
                .iter()
                .filter(|m| m.to == Party::Household(household))
                .map(|m| m.quantity)
                .collect();
            assert_eq!(to_it, [household.opening_persons()], "{household:?}");
        }
        let care = of(Good::Care);
        assert_eq!(care.len(), 12);
        assert_eq!(care.iter().map(|m| m.quantity).sum::<u64>(), 80);
        let food = of(Good::Food);
        assert_eq!(food.len(), 14);
        assert_eq!(food.iter().map(|m| m.quantity).sum::<u64>(), 160);
        let result = first_period()?;
        for place in Place::ALL {
            let transfers = result
                .receipts
                .local_transfers
                .iter()
                .filter(|r| Workplace::from_site(r.buyer_site_id).is_some_and(|w| w.place == place))
                .filter(|r| Good::from_good(r.good_id) == Some(Good::Food))
                .count();
            assert_eq!(transfers, 1, "{place:?}");
        }
        let to_shop: Vec<u64> = food
            .iter()
            .filter(|m| matches!(m.to, Party::Workplace(w) if w.kind == Kind::Shop))
            .map(|m| m.quantity)
            .collect();
        assert_eq!(to_shop, [40, 40]);
        for place in Place::ALL {
            let mut to_households: Vec<u64> = food
                .iter()
                .filter(|m| matches!(m.to, Party::Household(h) if h.place() == place))
                .map(|m| m.quantity)
                .collect();
            to_households.sort_unstable();
            assert_eq!(to_households, [4, 4, 4, 8, 8, 12], "{place:?}");
        }
        for m in &reading.goods {
            let place_of = |party: Party| match party {
                Party::Workplace(w) => Some(w.place),
                Party::Household(h) => Some(h.place()),
                Party::Treasury | Party::Fund => None,
            };
            assert_eq!(place_of(m.from), place_of(m.to), "{m:?}");
        }
        Ok(())
    }

    #[test]
    fn a_receipt_of_no_party_is_refused() -> TestResult {
        let result = first_period()?;
        let wage = result
            .receipts
            .money_transfers
            .iter()
            .position(|t| matches!(t.purpose, MoneyTransferPurpose::WagePayment(_)))
            .ok_or("no wage payment")?;

        let mut unknown = result.clone();
        unknown.receipts.money_transfers[wage].credit.location = MoneyLocation::Cash(
            AccountId::Household(FinalDemandPrincipalId::from_bytes([99; 32])),
        );
        let error = read_period(&unknown).err().ok_or("read an unknown party")?;
        assert!(matches!(error, ReadingError::UnknownParty(_)), "{error:?}");
        assert!(error.to_string().contains("WagePayment"), "{error}");

        let mut unexpected = result;
        unexpected.receipts.money_transfers[wage].purpose =
            MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid);
        let error = read_period(&unexpected)
            .err()
            .ok_or("read an unexpected payment")?;
        assert!(
            matches!(error, ReadingError::UnexpectedPayment(_)),
            "{error:?}"
        );
        Ok(())
    }
}
