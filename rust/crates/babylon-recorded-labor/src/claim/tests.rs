use super::split;
use super::{Claim, ClaimError, ClaimHours, Mix, Paid, Purses};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, FinalDemandPrincipalId, MoneyLocation, MoneyPosting,
    MoneyTransferPurpose, MoneyTransferReceipt, OrderId, OutboundOrderId, ShiftId, SiteId,
};
use std::error::Error;

type TestResult = Result<(), Box<dyn Error>>;

const DOLLAR: i128 = 1_000_000;

fn mix(work: i128, owning: i128, support: i128, not_recorded: i128) -> Result<Mix, ClaimError> {
    let mut mix = Mix::of(Claim::Work, work);
    mix.add(Mix::of(Claim::Owning, owning))?;
    mix.add(Mix::of(Claim::Support, support))?;
    mix.add(Mix::of(Claim::NotRecorded, not_recorded))?;
    Ok(mix)
}

fn amounts(mix: &Mix) -> [i128; 4] {
    Claim::ALL.map(|claim| mix.amount(claim))
}

fn household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([7; 32])
}

fn order() -> OutboundOrderId {
    OutboundOrderId::LocalFinalDemand(OrderId::from_bytes([9; 32]))
}

fn transfer(
    purpose: MoneyTransferPurpose,
    from: MoneyLocation,
    to: MoneyLocation,
    amount: i128,
) -> MoneyTransferReceipt {
    MoneyTransferReceipt {
        purpose,
        debit: MoneyPosting {
            location: from,
            delta: Currency::from_micro_units(-amount),
        },
        credit: MoneyPosting {
            location: to,
            delta: Currency::from_micro_units(amount),
        },
    }
}

fn mine() -> MoneyLocation {
    MoneyLocation::Cash(AccountId::Household(household()))
}

fn a_site() -> MoneyLocation {
    MoneyLocation::Cash(AccountId::Site(SiteId::from_bytes([3; 32])))
}

fn shift_reserve() -> MoneyLocation {
    MoneyLocation::PayrollReserve(ShiftId::from_bytes([4; 32]))
}

fn wages(amount: i128) -> MoneyTransferReceipt {
    transfer(
        MoneyTransferPurpose::WagePayment(ShiftId::from_bytes([4; 32])),
        shift_reserve(),
        mine(),
        amount,
    )
}

fn cash_in(purpose: CashTransferPurpose, amount: i128) -> MoneyTransferReceipt {
    transfer(
        MoneyTransferPurpose::Cash(purpose),
        a_site(),
        mine(),
        amount,
    )
}

#[test]
fn a_draw_takes_floor_shares_then_the_rest_in_order() -> TestResult {
    let mut held = mix(1, 1, 0, 0)?;
    let taken = held.draw(1)?;
    assert_eq!(amounts(&taken), [1, 0, 0, 0]);
    assert_eq!(amounts(&held), [0, 1, 0, 0]);
    let mut held = mix(3, 0, 5, 0)?;
    let taken = held.draw(4)?;
    assert_eq!(amounts(&taken), [2, 0, 2, 0]);
    assert_eq!(amounts(&held), [1, 0, 3, 0]);
    Ok(())
}

#[test]
fn a_whole_draw_takes_every_kind() -> TestResult {
    let mut held = mix(7, 0, 2, 9)?;
    let taken = held.draw(18)?;
    assert_eq!(amounts(&taken), [7, 0, 2, 9]);
    assert_eq!(amounts(&held), [0; 4]);
    Ok(())
}

#[test]
fn a_split_of_hours_adds_up_and_skips_an_empty_kind() -> TestResult {
    let paid = mix(1, 0, 2, 0)?;
    let split = split::split_hours(10_000_000, &paid)?;
    assert_eq!(
        split,
        ClaimHours {
            work: 3_333_333,
            owning: 0,
            support: 6_666_667,
            not_recorded: 0
        }
    );
    assert_eq!(split.total()?, 10_000_000);
    assert_eq!(
        split::split_hours(5, &Mix::default()),
        Err(ClaimError::Unpaid)
    );
    assert_eq!(
        split::split_hours(0, &Mix::default())?,
        ClaimHours::default(),
        "no hours need no money"
    );
    Ok(())
}

#[test]
fn a_reserve_keeps_its_mix_until_paid_or_refunded() -> TestResult {
    let mut purses = Purses::empty();
    purses.follow(&[wages(10 * DOLLAR)])?;
    purses.follow(&[cash_in(CashTransferPurpose::PublicTransfer, 10 * DOLLAR)])?;
    let reserve = MoneyLocation::PurchaseReserve(order());
    let paid = purses.follow(&[transfer(
        MoneyTransferPurpose::PurchaseReservation(order()),
        mine(),
        reserve,
        8 * DOLLAR,
    )])?;
    assert!(paid.is_empty());
    assert_eq!(
        amounts(&purses.reserve_of(order())),
        [4 * DOLLAR, 0, 4 * DOLLAR, 0]
    );
    let paid = purses.follow(&[transfer(
        MoneyTransferPurpose::DeliverySettlement(order()),
        reserve,
        a_site(),
        6 * DOLLAR,
    )])?;
    assert_eq!(
        paid.get(&order()).map(amounts),
        Some([3 * DOLLAR, 0, 3 * DOLLAR, 0])
    );
    purses.follow(&[transfer(
        MoneyTransferPurpose::PurchaseRefund(order()),
        reserve,
        mine(),
        2 * DOLLAR,
    )])?;
    assert_eq!(
        amounts(&purses.cash_of(household())),
        [7 * DOLLAR, 0, 7 * DOLLAR, 0]
    );
    assert_eq!(amounts(&purses.reserve_of(order())), [0; 4]);
    assert_eq!(purses, {
        let mut again = Purses::empty();
        again.follow(&[wages(7 * DOLLAR)])?;
        again.follow(&[cash_in(CashTransferPurpose::PublicTransfer, 7 * DOLLAR)])?;
        again
    });
    Ok(())
}

#[test]
fn each_purpose_enters_as_its_kind() -> TestResult {
    let enters = [
        (wages(5), [5, 0, 0, 0]),
        (
            cash_in(CashTransferPurpose::OwnershipDistribution, 5),
            [0, 5, 0, 0],
        ),
        (
            cash_in(CashTransferPurpose::PublicTransfer, 5),
            [0, 0, 5, 0],
        ),
        (
            cash_in(CashTransferPurpose::HouseholdTransfer, 5),
            [0, 0, 5, 0],
        ),
        (cash_in(CashTransferPurpose::MutualAid, 5), [0, 0, 5, 0]),
    ];
    for (receipt, kinds) in enters {
        let mut purses = Purses::empty();
        purses.follow(&[receipt])?;
        assert_eq!(amounts(&purses.cash_of(household())), kinds);
    }
    let mut purses = Purses::empty();
    let other = cash_in(CashTransferPurpose::Tax, 5);
    assert_eq!(
        purses.follow(&[wages(5), other]),
        Err(ClaimError::Unexpected { index: 1 })
    );
    assert_eq!(purses, Purses::empty(), "a refusal changes nothing");
    Ok(())
}

#[test]
fn a_tax_and_a_contribution_draw_the_mix() -> TestResult {
    let mut purses = Purses::empty();
    purses.follow(&[
        wages(30),
        cash_in(CashTransferPurpose::OwnershipDistribution, 10),
    ])?;
    let tax = transfer(
        MoneyTransferPurpose::Cash(CashTransferPurpose::Tax),
        mine(),
        a_site(),
        8,
    );
    purses.follow(&[tax])?;
    assert_eq!(amounts(&purses.cash_of(household())), [24, 8, 0, 0]);
    let contribution = transfer(
        MoneyTransferPurpose::Cash(CashTransferPurpose::CapitalContribution),
        mine(),
        a_site(),
        16,
    );
    purses.follow(&[contribution])?;
    assert_eq!(amounts(&purses.cash_of(household())), [12, 4, 0, 0]);
    Ok(())
}

#[test]
fn an_overdraft_is_refused() -> TestResult {
    let mut purses = Purses::empty();
    purses.follow(&[wages(10)])?;
    let before = purses.clone();
    let tax = transfer(
        MoneyTransferPurpose::Cash(CashTransferPurpose::Tax),
        mine(),
        a_site(),
        11,
    );
    assert_eq!(purses.follow(&[tax]), Err(ClaimError::Overdrawn));
    assert_eq!(purses, before);
    let mut held = mix(1, 0, 0, 0)?;
    assert_eq!(held.draw(2), Err(ClaimError::Overdrawn));
    assert_eq!(held.draw(-1), Err(ClaimError::Overdrawn));
    assert_eq!(amounts(&held), [1, 0, 0, 0]);
    let none: Paid = Paid::new();
    assert!(none.is_empty());
    Ok(())
}
