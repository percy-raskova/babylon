use super::lists::{HouseholdLists, ListItem};
use crate::tiers::{self, HouseholdStandard, HouseholdTierReceipt};
use crate::{FinalDemandPrincipalId, GoodId, OrderId, SiteId, UnitId, WantTier};
use crate::{HouseholdConsumptionReceipt, HouseholdServiceReceipt, MaterialCircuitError};
use babylon_kernel::currency::Currency;

fn money(dollars: i128) -> Currency {
    Currency::from_micro_units(dollars * 1_000_000)
}
fn account() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([1; 32])
}
fn good(n: u8) -> GoodId {
    GoodId::from_bytes([n; 32])
}
fn unit() -> UnitId {
    UnitId::from_bytes([7; 32])
}
fn order(n: u8) -> OrderId {
    OrderId::from_bytes([n; 32])
}
fn item(good_n: u8, tier: u8, order_n: u8, posted: i128, wanted: u64, place: usize) -> ListItem {
    ListItem::new(
        (account(), good(good_n), unit()),
        tier,
        place,
        SiteId::from_bytes([5; 32]),
        order(order_n),
        money(posted),
        wanted,
    )
}
const FOOD: u8 = 1;
const UTILITY: u8 = 2;

/// One account: food need 10 at $4, utility need 10 at $2, a tier 2 want of 5 utility and a tier 3
/// want of 5 food.
fn list() -> HouseholdLists {
    HouseholdLists::from_items(vec![
        item(FOOD, 1, 10, 4, 10, 0),
        item(UTILITY, 1, 11, 2, 10, 1),
        item(UTILITY, 2, 12, 2, 5, 1),
        item(FOOD, 3, 13, 4, 5, 0),
    ])
}
fn reserves(lists: &HouseholdLists, good_n: u8, need: u64) -> Vec<i128> {
    lists
        .rungs(account(), good(good_n), unit(), need)
        .expect("the account has the product")
        .iter()
        .map(|r| r.rung.reserve.micro_units() / 1_000_000)
        .collect()
}

#[test]
fn the_reserve_counts_what_is_ahead_and_still_to_buy() {
    let mut lists = list();
    assert_eq!(reserves(&lists, FOOD, 10), vec![0, 30]);
    assert_eq!(reserves(&lists, UTILITY, 10), vec![0, 40]);
    lists
        .settle(
            account(),
            good(UTILITY),
            unit(),
            &[(order(11), 10), (order(12), 0)],
            money(2),
        )
        .expect("the market settles");
    assert_eq!(reserves(&lists, FOOD, 10), vec![0, 0]);
}

#[test]
fn an_unmet_need_keeps_its_reserve_and_a_want_does_not() {
    let mut lists = list();
    lists
        .settle(
            account(),
            good(UTILITY),
            unit(),
            &[(order(11), 4), (order(12), 0)],
            money(2),
        )
        .expect("the market settles");
    assert_eq!(reserves(&lists, FOOD, 10), vec![0, 12]);
}

#[test]
fn reserves_never_fall_along_a_bid() {
    let more = HouseholdLists::from_items(vec![
        item(FOOD, 1, 10, 4, 10, 0),
        item(UTILITY, 1, 11, 2, 10, 1),
        item(UTILITY, 2, 12, 2, 5, 1),
        item(UTILITY, 3, 14, 2, 3, 1),
        item(FOOD, 2, 15, 4, 2, 0),
        item(FOOD, 3, 13, 4, 5, 0),
    ]);
    for lists in [list(), more] {
        for good_n in [FOOD, UTILITY] {
            let r = reserves(&lists, good_n, 10);
            assert!(r.windows(2).all(|w| w[0] <= w[1]), "{r:?}");
        }
    }
}

#[test]
fn receipts_sum_each_tier_at_posted_prices() {
    let mut lists = list();
    lists
        .settle(
            account(),
            good(FOOD),
            unit(),
            &[(order(10), 10), (order(13), 2)],
            money(5),
        )
        .expect("food settles");
    lists
        .settle(
            account(),
            good(UTILITY),
            unit(),
            &[(order(11), 10), (order(12), 5)],
            money(2),
        )
        .expect("utility settles");
    let (wants, tiers) = lists.receipts(3).expect("the records hold together");
    assert_eq!(wants.len(), 2);
    assert_eq!(wants[0].tier, WantTier::Comfort);
    assert_eq!((wants[0].wanted_quantity, wants[0].bought_quantity), (5, 5));
    assert_eq!(wants[1].tier, WantTier::Luxury);
    assert_eq!(wants[1].unit_price, money(5));
    assert_eq!(wants[1].posted_price, money(4));
    assert_eq!(tiers.len(), 2);
    assert_eq!(
        (tiers[0].wanted_value, tiers[0].bought_value),
        (money(10), money(10))
    );
    assert_eq!(
        (tiers[1].wanted_value, tiers[1].bought_value),
        (money(20), money(8))
    );
    // A product never reached shows bought 0 at its posted price.
    let (wants, _) = list().receipts(3).expect("records of an untouched list");
    assert!(wants
        .iter()
        .all(|w| w.bought_quantity == 0 && w.unit_price == w.posted_price));
}

fn tier(tier: WantTier, wanted: i128, bought: i128) -> HouseholdTierReceipt {
    HouseholdTierReceipt {
        period: 1,
        principal_id: account(),
        tier,
        wanted_value: money(wanted),
        bought_value: money(bought),
    }
}
fn consumption(unmet: u64) -> HouseholdConsumptionReceipt {
    HouseholdConsumptionReceipt {
        period: 1,
        principal_id: account(),
        good_id: good(FOOD),
        unit_id: unit(),
        required_quantity: 10,
        available_quantity: 10 - unmet,
        consumed_quantity: 10 - unmet,
        unmet_quantity: unmet,
        closing_quantity: 0,
    }
}
fn service(unmet: u64) -> HouseholdServiceReceipt {
    HouseholdServiceReceipt {
        period: 1,
        principal_id: account(),
        good_id: good(UTILITY),
        unit_id: unit(),
        required_quantity: 10,
        performed_quantity: 10 - unmet,
        satisfied_quantity: 10 - unmet,
        unmet_quantity: unmet,
        unused_quantity: 0,
    }
}

#[test]
fn each_standard_is_read_from_the_records() {
    let full = [
        tier(WantTier::Comfort, 10, 10),
        tier(WantTier::Luxury, 20, 20),
    ];
    let read =
        |c: &[HouseholdConsumptionReceipt],
         s: &[HouseholdServiceReceipt],
         t: &[HouseholdTierReceipt]| tiers::household_standard(account(), c, s, t);
    assert_eq!(
        read(&[consumption(0)], &[service(0)], &full),
        Ok(HouseholdStandard::Affluent)
    );
    assert_eq!(
        read(
            &[consumption(0)],
            &[service(0)],
            &[
                tier(WantTier::Comfort, 10, 10),
                tier(WantTier::Luxury, 20, 8)
            ]
        ),
        Ok(HouseholdStandard::Comfortable)
    );
    assert_eq!(
        read(
            &[consumption(0)],
            &[service(0)],
            &[
                tier(WantTier::Comfort, 10, 4),
                tier(WantTier::Luxury, 20, 0)
            ]
        ),
        Ok(HouseholdStandard::GettingBy)
    );
    assert_eq!(
        read(&[consumption(3)], &[service(0)], &full),
        Ok(HouseholdStandard::GoingWithout)
    );
    assert_eq!(
        read(&[consumption(0)], &[service(1)], &full),
        Ok(HouseholdStandard::GoingWithout)
    );
    assert!(HouseholdStandard::GoingWithout < HouseholdStandard::Affluent);
}

#[test]
fn a_missing_tier_row_is_refused() {
    let missing = [tier(WantTier::Comfort, 10, 10)];
    let twice = [
        tier(WantTier::Comfort, 10, 10),
        tier(WantTier::Luxury, 20, 20),
        tier(WantTier::Luxury, 20, 20),
    ];
    for rows in [&missing[..], &twice[..], &[]] {
        assert_eq!(
            tiers::household_standard(account(), &[consumption(0)], &[], rows),
            Err(MaterialCircuitError::MarketClearingInvariant)
        );
    }
}

#[test]
fn want_order_ids_differ_by_tier_and_from_the_need() {
    let key = (account(), good(FOOD), unit());
    let comfort = tiers::recurring_household_want_order_id(1, key, WantTier::Comfort);
    let luxury = tiers::recurring_household_want_order_id(1, key, WantTier::Luxury);
    assert_ne!(comfort, luxury);
    assert_ne!(comfort, crate::recurring_household_order_id(1, key));
    assert_ne!(
        comfort,
        tiers::recurring_household_want_order_id(2, key, WantTier::Comfort)
    );
    let site = SiteId::from_bytes([5; 32]);
    let a = tiers::recurring_service_want_order_id(
        1,
        account(),
        site,
        good(FOOD),
        unit(),
        WantTier::Comfort,
    );
    let b = tiers::recurring_service_want_order_id(
        1,
        account(),
        site,
        good(FOOD),
        unit(),
        WantTier::Luxury,
    );
    assert_ne!(a, b);
    assert_ne!(a, comfort);
}
