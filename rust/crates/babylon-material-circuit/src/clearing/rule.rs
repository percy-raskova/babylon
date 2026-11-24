//! The price of a short market.
//!
//! When what a seller's buyers can pay for at the posted price exceeds what is on offer, the price
//! rises to the first level at which the two are equal, every buyer pays that price, and the seller
//! keeps the difference. The rule is one pure function over exact integers.

use crate::{
    AdjustmentRule, FinalDemandPrincipalId, GoodId, HouseholdWant, MaterialCircuitError, UnitId,
};
use babylon_kernel::currency::Currency;

/// The products that clear by price, in the order in which a buyer's purse reaches them.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MarketClearingPolicy {
    pub paying_order: Vec<(GoodId, UnitId)>,
    /// What household accounts buy after their needs, in canonical order (empty without wants).
    pub household_wants: Vec<HouseholdWant>,
    /// Rule A6 (ADR314): a workplace with more money than one period of what it pays out plans for
    /// what was asked of it, as far as that money carries. `false` keeps today's plans and bytes.
    pub plans_from_spare_money: bool,
    /// The rules of ADR314 this policy asks for, in the order of `AdjustmentRule`, each once.
    /// Empty keeps today's behaviour and bytes.
    pub adjustments: Vec<AdjustmentRule>,
}

impl MarketClearingPolicy {
    /// The product's place in the order, or `None` when it does not clear by price.
    #[must_use]
    pub fn place(&self, good: GoodId, unit: UnitId) -> Option<usize> {
        self.paying_order
            .iter()
            .position(|&(g, u)| g == good && u == unit)
    }

    /// One account's wants, in canonical order.
    ///
    /// It reads an admitted catalog, whose wants are in canonical order (sorted by account), so
    /// the account's rows are one contiguous run found by binary search. On a catalog that was not
    /// admitted the run is not defined.
    #[must_use]
    pub fn wants_of(&self, principal: FinalDemandPrincipalId) -> &[HouseholdWant] {
        let start = self
            .household_wants
            .partition_point(|row| row.principal_id < principal);
        let end = self
            .household_wants
            .partition_point(|row| row.principal_id <= principal);
        &self.household_wants[start..end]
    }
}

/// One buyer's bid in one market.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MarketBid {
    /// What the buyer asks for at the posted price, before any cash limit.
    pub wanted: u64,
    /// The money the buyer can commit now. Never negative.
    pub purse: Currency,
    /// The highest price a business pays. `None` for a household.
    pub limit: Option<Currency>,
}

/// The price of a market and what each buyer gets at it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MarketOutcome {
    /// The price every buyer pays.
    pub price: Currency,
    /// One quantity for each bid, in the bids' order.
    pub quantities: Vec<u64>,
    /// What the buyers could pay for at the posted price.
    pub demand_at_quote: u64,
}

/// A bid with its limit read against the quote, in micro-units.
#[derive(Clone, Copy)]
struct Reading {
    wanted: u64,
    purse: i128,
    limit: Option<i128>,
}

impl Reading {
    /// What the buyer can pay for at price `p` (positive micro-units).
    fn can_pay(self, p: i128) -> Result<u64, MaterialCircuitError> {
        if self.limit.is_some_and(|limit| p > limit) {
            return Ok(0);
        }
        let by_purse = self.purse / p;
        u64::try_from(by_purse.min(i128::from(self.wanted)))
            .map_err(|_| MaterialCircuitError::Arithmetic)
    }
}

fn demand(readings: &[Reading], p: i128) -> Result<u128, MaterialCircuitError> {
    readings.iter().try_fold(0_u128, |sum, reading| {
        sum.checked_add(u128::from(reading.can_pay(p)?))
            .ok_or(MaterialCircuitError::Arithmetic)
    })
}

fn quantities_at(readings: &[Reading], p: i128) -> Result<Vec<u64>, MaterialCircuitError> {
    readings.iter().map(|reading| reading.can_pay(p)).collect()
}

/// The least price in `[lo, hi]` at which the demand no longer exceeds `supply`.
fn least_price_within(
    readings: &[Reading],
    supply: u128,
    mut lo: i128,
    mut hi: i128,
) -> Result<i128, MaterialCircuitError> {
    while lo < hi {
        let mid = lo + (hi - lo) / 2;
        if demand(readings, mid)? <= supply {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    Ok(lo)
}

/// Shares what is left among the buyers who fall away at a step, by their margins, and gives the
/// last indivisible units to the buyers in order.
fn share_step(
    readings: &[Reading],
    supply: u64,
    stop: i128,
) -> Result<Vec<u64>, MaterialCircuitError> {
    let below = quantities_at(
        readings,
        stop.checked_sub(1)
            .ok_or(MaterialCircuitError::Arithmetic)?,
    )?;
    let base = quantities_at(readings, stop)?;
    share_margins(&base, &below, supply)
}

/// Gives each buyer its quantity at the stop (`base`), then shares the `supply` left among the
/// buyers by the margin between their quantity just below the stop and at it.
pub(super) fn share_margins(
    base: &[u64],
    below: &[u64],
    supply: u64,
) -> Result<Vec<u64>, MaterialCircuitError> {
    let base_sum: u128 = base.iter().map(|&q| u128::from(q)).sum();
    let rest = u128::from(supply)
        .checked_sub(base_sum)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let margins: Vec<u128> = below
        .iter()
        .zip(base)
        .map(|(&high, &low)| u128::from(high.saturating_sub(low)))
        .collect();
    let total: u128 = margins.iter().sum();
    if total == 0 {
        return Ok(base.to_vec());
    }
    let mut shares = Vec::with_capacity(margins.len());
    for &margin in &margins {
        let product = rest
            .checked_mul(margin)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        shares.push(product / total);
    }
    let mut left = rest - shares.iter().sum::<u128>();
    let mut grants = Vec::with_capacity(base.len());
    for ((&low, &margin), share) in base.iter().zip(&margins).zip(shares) {
        let extra = (margin - share).min(left);
        left -= extra;
        grants.push(add_units(low, share + extra)?);
    }
    Ok(grants)
}

fn add_units(quantity: u64, units: u128) -> Result<u64, MaterialCircuitError> {
    u64::try_from(u128::from(quantity) + units).map_err(|_| MaterialCircuitError::Arithmetic)
}

fn read_bids(quote: i128, bids: &[MarketBid]) -> Result<Vec<Reading>, MaterialCircuitError> {
    bids.iter()
        .map(|bid| {
            let purse = bid.purse.micro_units();
            if purse < 0 {
                return Err(MaterialCircuitError::MarketClearingInvariant);
            }
            Ok(Reading {
                wanted: bid.wanted,
                purse,
                limit: bid.limit.map(|limit| limit.micro_units().max(quote)),
            })
        })
        .collect()
}

/// Finds the price of one market and each buyer's quantity.
///
/// # Errors
/// `MarketClearingInvariant` for a quote that is not positive or a negative purse;
/// `Arithmetic` on overflow, or when the demand at the quote does not fit `u64`.
pub fn clear_market(
    supply: u64,
    quote: Currency,
    bids: &[MarketBid],
) -> Result<MarketOutcome, MaterialCircuitError> {
    let quote_micro = quote.micro_units();
    if quote_micro <= 0 {
        return Err(MaterialCircuitError::MarketClearingInvariant);
    }
    let readings = read_bids(quote_micro, bids)?;
    let at_quote = demand(&readings, quote_micro)?;
    let demand_at_quote = u64::try_from(at_quote).map_err(|_| MaterialCircuitError::Arithmetic)?;
    let sold_at = |price: i128, quantities: Vec<u64>| MarketOutcome {
        price: Currency::from_micro_units(price),
        quantities,
        demand_at_quote,
    };
    if at_quote <= u128::from(supply) {
        return Ok(sold_at(quote_micro, quantities_at(&readings, quote_micro)?));
    }
    if supply == 0 {
        return Ok(sold_at(quote_micro, vec![0; readings.len()]));
    }
    let deepest = readings
        .iter()
        .map(|reading| reading.purse.min(reading.limit.unwrap_or(i128::MAX)))
        .max()
        .unwrap_or(0);
    let ceiling = deepest
        .checked_add(1)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let above_quote = quote_micro
        .checked_add(1)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let stop = least_price_within(
        &readings,
        u128::from(supply),
        above_quote,
        ceiling.max(above_quote),
    )?;
    if demand(&readings, stop)? == u128::from(supply) {
        return Ok(sold_at(stop, quantities_at(&readings, stop)?));
    }
    let below_stop = stop
        .checked_sub(1)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(sold_at(below_stop, share_step(&readings, supply, stop)?))
}

#[cfg(test)]
mod tests {
    use super::*;

    const DEEP: i128 = 1_000_000_000_000_000;

    fn bid(wanted: u64, purse: i128, limit: Option<i128>) -> MarketBid {
        MarketBid {
            wanted,
            purse: Currency::from_micro_units(purse),
            limit: limit.map(Currency::from_micro_units),
        }
    }

    fn run(supply: u64, quote: i128, bids: &[MarketBid]) -> (i128, Vec<u64>, u64) {
        let outcome = clear_market(supply, Currency::from_micro_units(quote), bids)
            .expect("the market clears");
        (
            outcome.price.micro_units(),
            outcome.quantities,
            outcome.demand_at_quote,
        )
    }

    fn three() -> Vec<MarketBid> {
        vec![
            bid(100, 7_500_000_000, None),
            bid(100, 11_250_000_000, None),
            bid(100, DEEP, None),
        ]
    }

    #[test]
    fn enough_for_all_sells_at_the_quote() {
        assert_eq!(
            run(300, 75_000_000, &three()),
            (75_000_000, vec![100, 100, 100], 300)
        );
    }

    #[test]
    fn a_fifth_short() {
        assert_eq!(
            run(240, 75_000_000, &three()),
            (132_352_942, vec![56, 84, 100], 300)
        );
    }

    #[test]
    fn half_short() {
        assert_eq!(
            run(150, 75_000_000, &three()),
            (362_903_226, vec![20, 30, 100], 300)
        );
    }

    #[test]
    fn equal_purses_share() {
        let bids = vec![bid(4, 300_000_000, None); 3];
        assert_eq!(run(5, 75_000_000, &bids), (150_000_000, vec![2, 2, 1], 12));
    }

    #[test]
    fn nothing_on_offer_sells_nothing() {
        let bids = vec![bid(100, 7_500_000_000, None), bid(100, DEEP, None)];
        assert_eq!(run(0, 75_000_000, &bids), (75_000_000, vec![0, 0], 200));
    }

    fn limited() -> Vec<MarketBid> {
        vec![
            bid(100, DEEP, Some(106_000_000)),
            bid(100, DEEP, Some(245_000_000)),
            bid(50, 5_000_000_000, None),
        ]
    }

    #[test]
    fn a_business_stops_at_its_limit() {
        assert_eq!(
            run(120, 100_000_000, &limited()),
            (238_095_239, vec![0, 100, 20], 250)
        );
    }

    #[test]
    fn businesses_below_cost_share_at_the_quote() {
        let bids = vec![bid(100, DEEP, Some(40_000_000)); 2];
        assert_eq!(
            run(60, 100_000_000, &bids),
            (100_000_000, vec![30, 30], 200)
        );
    }

    fn stepped() -> Vec<MarketBid> {
        vec![
            bid(10, 1_000_000_000_000, Some(100_000_000)),
            bid(10, 1_000_000_000_000, Some(100_000_000)),
            bid(4, 400_000_000, None),
        ]
    }

    #[test]
    fn a_step_at_the_quote_shares_what_is_left() {
        assert_eq!(
            run(7, 100_000_000, &stepped()),
            (100_000_000, vec![3, 1, 3], 24)
        );
    }

    #[test]
    fn a_limit_under_the_quote_never_outbids() {
        let bids = vec![
            bid(10, 1_000_000_000_000, Some(40_000_000)),
            bid(10, 1_000_000_000_000, Some(150_000_000)),
        ];
        assert_eq!(run(4, 100_000_000, &bids), (150_000_000, vec![0, 4], 20));
    }

    #[test]
    fn one_unit_and_three_purses() {
        let bids = vec![
            bid(1000, 3_000_000_000, None),
            bid(1000, 9_000_000_000, None),
            bid(1000, 500_000_000, None),
        ];
        assert_eq!(
            run(1, 280_000_000, &bids),
            (4_500_000_001, vec![0, 1, 0], 43)
        );
    }

    #[test]
    fn one_buyer_wants_more_than_there_is() {
        let bids = vec![bid(1000, 9_000_000_000, None)];
        assert_eq!(run(10, 280_000_000, &bids), (818_181_819, vec![10], 32));
    }

    #[test]
    fn an_empty_purse_does_not_bid() {
        let bids = vec![
            bid(5, 0, None),
            bid(5, 1_400_000_000, None),
            bid(5, 560_000_000, None),
        ];
        assert_eq!(run(3, 280_000_000, &bids), (466_666_667, vec![0, 2, 1], 7));
    }

    #[test]
    fn food_at_the_scale_of_wayne() {
        let bids = vec![
            bid(456_528, 127_827_840_000_000, None),
            bid(50_726, 56_813_120_000_000, None),
            bid(173_993, 24_359_020_000_000, None),
            bid(19_334, 16_240_560_000_000, None),
        ];
        assert_eq!(
            run(400_000, 280_000_000, &bids),
            (461_254_209, vec![277_130, 50_726, 52_810, 19_334], 613_584)
        );
    }

    #[test]
    fn a_very_deep_purse_does_not_overflow() {
        let bids = vec![
            bid(2_000_000, 1_000_000_000_000_000_000_000_000, None),
            bid(2_000_000, 150_000_000_000_000, None),
        ];
        assert_eq!(
            run(1_000_000, 75_000_000, &bids),
            (999_999_000_001_000_000, vec![1_000_000, 0], 4_000_000)
        );
    }

    #[test]
    fn the_laws_hold_on_every_small_market() {
        let markets: [(i128, Vec<MarketBid>); 3] = [
            (100_000_000, limited()),
            (75_000_000, vec![bid(4, 300_000_000, None); 3]),
            (100_000_000, stepped()),
        ];
        for (quote, bids) in &markets {
            let at_quote = run(0, *quote, bids).2;
            let mut previous_price = 0;
            for supply in 0..=at_quote + 2 {
                let (price, quantities, _) = run(supply, *quote, bids);
                assert_eq!(
                    quantities.iter().sum::<u64>(),
                    supply.min(at_quote),
                    "everything on offer is sold"
                );
                assert!(price >= *quote);
                for (bid, &quantity) in bids.iter().zip(&quantities) {
                    assert!(quantity <= bid.wanted);
                    assert!(i128::from(quantity) * price <= bid.purse.micro_units());
                    if quantity > 0 {
                        assert!(bid
                            .limit
                            .is_none_or(|l| l.micro_units().max(*quote) >= price));
                    }
                }
                if supply >= 2 {
                    assert!(
                        price <= previous_price,
                        "more supply never raises the price"
                    );
                }
                previous_price = price;
            }
        }
    }

    #[test]
    fn a_bad_quote_or_purse_is_refused() {
        let bids = vec![bid(1, 10, None)];
        assert_eq!(
            clear_market(1, Currency::from_micro_units(0), &bids),
            Err(MaterialCircuitError::MarketClearingInvariant)
        );
        let negative = vec![bid(1, -1, None)];
        assert_eq!(
            clear_market(1, Currency::from_micro_units(5), &negative),
            Err(MaterialCircuitError::MarketClearingInvariant)
        );
    }

    #[test]
    fn wants_beyond_u64_are_refused_not_wrapped() {
        let bids = vec![bid(u64::MAX, DEEP * DEEP, None); 2];
        assert_eq!(
            clear_market(1, Currency::from_micro_units(1), &bids),
            Err(MaterialCircuitError::Arithmetic)
        );
    }

    #[test]
    fn a_quote_at_the_top_of_the_range_is_refused_not_panicked() {
        let bids = vec![bid(1, i128::MAX, None); 2];
        assert_eq!(
            clear_market(1, Currency::from_micro_units(i128::MAX), &bids),
            Err(MaterialCircuitError::Arithmetic)
        );
    }
}
