//! The bid with rungs.
//!
//! A buyer's bid in one market is a list of rungs, one for the need and one for each want of the
//! product, each with a reserve: the money that rung may not touch. The market prices the bids'
//! totals as `clear_market` does, so there is one price for every buyer and every rung.

use super::rule::{self, MarketOutcome};
use crate::MaterialCircuitError;
use babylon_kernel::currency::Currency;

/// One rung of a bid: a quantity and the money the rung may not touch.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BidRung {
    pub wanted: u64,
    pub reserve: Currency,
}

/// One buyer's bid in one market, rungs in its list's order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LadderBid {
    pub rungs: Vec<BidRung>,
    pub purse: Currency,
    pub limit: Option<Currency>,
}

/// The price of a market and what each rung of each bid gets at it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LadderOutcome {
    /// The price every buyer pays.
    pub price: Currency,
    /// For each bid, in the bids' order, one quantity per rung.
    pub quantities: Vec<Vec<u64>>,
    /// What the buyers could pay for at the posted price, every rung counted.
    pub demand_at_quote: u64,
}

impl LadderOutcome {
    /// One quantity per bid, the sum of its rungs, for `MarketTable::record`.
    ///
    /// # Errors
    /// `Arithmetic` when a bid's rungs do not add within `u64`.
    pub fn totals(&self) -> Result<MarketOutcome, MaterialCircuitError> {
        let quantities = self
            .quantities
            .iter()
            .map(|rungs| sum_units(rungs))
            .collect::<Result<Vec<u64>, _>>()?;
        Ok(MarketOutcome {
            price: self.price,
            quantities,
            demand_at_quote: self.demand_at_quote,
        })
    }
}

fn sum_units(rungs: &[u64]) -> Result<u64, MaterialCircuitError> {
    rungs.iter().try_fold(0_u64, |sum, &quantity| {
        sum.checked_add(quantity)
            .ok_or(MaterialCircuitError::Arithmetic)
    })
}

/// A bid read in micro-units, its limit read against the quote.
struct Reading {
    rungs: Vec<(u64, i128)>,
    purse: i128,
    limit: Option<i128>,
}

impl Reading {
    /// The quantity of each rung at price `p` (positive micro-units).
    fn rungs_at(&self, p: i128) -> Result<Vec<u64>, MaterialCircuitError> {
        if self.limit.is_some_and(|limit| p > limit) {
            return Ok(vec![0; self.rungs.len()]);
        }
        let mut spent = 0_i128;
        let mut quantities = Vec::with_capacity(self.rungs.len());
        for &(wanted, reserve) in &self.rungs {
            let room = self
                .purse
                .checked_sub(reserve)
                .and_then(|left| left.checked_sub(spent))
                .ok_or(MaterialCircuitError::Arithmetic)?;
            let quantity = if room <= 0 {
                0
            } else {
                u64::try_from((room / p).min(i128::from(wanted)))
                    .map_err(|_| MaterialCircuitError::Arithmetic)?
            };
            // `quantity x p` is at most `room`, so it cannot overflow.
            spent += i128::from(quantity) * p;
            quantities.push(quantity);
        }
        Ok(quantities)
    }

    fn total_at(&self, p: i128) -> Result<u64, MaterialCircuitError> {
        sum_units(&self.rungs_at(p)?)
    }
}

fn read_bids(quote: i128, bids: &[LadderBid]) -> Result<Vec<Reading>, MaterialCircuitError> {
    bids.iter()
        .map(|bid| {
            let purse = bid.purse.micro_units();
            if purse < 0 || bid.rungs.is_empty() {
                return Err(MaterialCircuitError::MarketClearingInvariant);
            }
            let mut rungs = Vec::with_capacity(bid.rungs.len());
            let mut last = 0_i128;
            for rung in &bid.rungs {
                let reserve = rung.reserve.micro_units();
                if reserve < last {
                    return Err(MaterialCircuitError::MarketClearingInvariant);
                }
                last = reserve;
                rungs.push((rung.wanted, reserve));
            }
            Ok(Reading {
                rungs,
                purse,
                limit: bid.limit.map(|limit| limit.micro_units().max(quote)),
            })
        })
        .collect()
}

fn demand(readings: &[Reading], p: i128) -> Result<u128, MaterialCircuitError> {
    readings.iter().try_fold(0_u128, |sum, reading| {
        sum.checked_add(u128::from(reading.total_at(p)?))
            .ok_or(MaterialCircuitError::Arithmetic)
    })
}

fn rungs_at_all(readings: &[Reading], p: i128) -> Result<Vec<Vec<u64>>, MaterialCircuitError> {
    readings.iter().map(|reading| reading.rungs_at(p)).collect()
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

/// Shares the supply at a step as `clear_market` does, on each bid's total, then fills each bid's
/// rungs in order, each up to its quantity just below the stop.
fn share_step(
    readings: &[Reading],
    supply: u64,
    stop: i128,
) -> Result<Vec<Vec<u64>>, MaterialCircuitError> {
    let below_stop = stop
        .checked_sub(1)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let caps = rungs_at_all(readings, below_stop)?;
    let below = caps
        .iter()
        .map(|rungs| sum_units(rungs))
        .collect::<Result<Vec<u64>, _>>()?;
    let base = readings
        .iter()
        .map(|reading| reading.total_at(stop))
        .collect::<Result<Vec<u64>, _>>()?;
    let grants = rule::share_margins(&base, &below, supply)?;
    Ok(caps
        .iter()
        .zip(grants)
        .map(|(cap, grant)| {
            let mut left = grant;
            cap.iter()
                .map(|&room| {
                    let taken = room.min(left);
                    left -= taken;
                    taken
                })
                .collect()
        })
        .collect())
}

/// Finds the price of one market of bids with rungs, and each rung's quantity.
///
/// The price is `clear_market`'s on the bids' totals. Reserves that never fall along a bid make
/// each total fall or stay as the price rises, so the search is sound.
///
/// # Errors
/// `MarketClearingInvariant` for a quote that is not positive, a negative purse or reserve, a bid
/// with no rung, or reserves that fall along a bid's rungs; `Arithmetic` on overflow.
pub fn clear_ladder_market(
    supply: u64,
    quote: Currency,
    bids: &[LadderBid],
) -> Result<LadderOutcome, MaterialCircuitError> {
    let quote_micro = quote.micro_units();
    if quote_micro <= 0 {
        return Err(MaterialCircuitError::MarketClearingInvariant);
    }
    let readings = read_bids(quote_micro, bids)?;
    let at_quote = demand(&readings, quote_micro)?;
    let demand_at_quote = u64::try_from(at_quote).map_err(|_| MaterialCircuitError::Arithmetic)?;
    let sold_at = |price: i128, quantities: Vec<Vec<u64>>| LadderOutcome {
        price: Currency::from_micro_units(price),
        quantities,
        demand_at_quote,
    };
    if at_quote <= u128::from(supply) {
        return Ok(sold_at(quote_micro, rungs_at_all(&readings, quote_micro)?));
    }
    if supply == 0 {
        let none = readings
            .iter()
            .map(|reading| vec![0; reading.rungs.len()])
            .collect();
        return Ok(sold_at(quote_micro, none));
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
        return Ok(sold_at(stop, rungs_at_all(&readings, stop)?));
    }
    let below_stop = stop
        .checked_sub(1)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(sold_at(below_stop, share_step(&readings, supply, stop)?))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::clearing::{self, MarketBid};

    const M: i128 = 1_000_000;

    fn bid(purse: i128, limit: Option<i128>, rungs: &[(u64, i128)]) -> LadderBid {
        LadderBid {
            rungs: rungs
                .iter()
                .map(|&(wanted, reserve)| BidRung {
                    wanted,
                    reserve: Currency::from_micro_units(reserve),
                })
                .collect(),
            purse: Currency::from_micro_units(purse),
            limit: limit.map(Currency::from_micro_units),
        }
    }

    fn run(supply: u64, quote: i128, bids: &[LadderBid]) -> (i128, Vec<Vec<u64>>, u64) {
        let outcome = clear_ladder_market(supply, Currency::from_micro_units(quote), bids)
            .expect("the market clears");
        (
            outcome.price.micro_units(),
            outcome.quantities,
            outcome.demand_at_quote,
        )
    }

    #[test]
    fn a_comfort_waits_for_the_money_its_needs_do_not_use() {
        let bids = [bid(100 * M, None, &[(5, 0), (5, 30 * M)])];
        assert_eq!(run(100, 10 * M, &bids), (10 * M, vec![vec![5, 2]], 7));
    }

    #[test]
    fn a_reserve_above_the_purse_bids_nothing() {
        let bids = [bid(100 * M, None, &[(5, 0), (5, 200 * M)])];
        assert_eq!(run(100, 10 * M, &bids), (10 * M, vec![vec![5, 0]], 5));
    }

    #[test]
    fn a_luxury_bids_after_its_comfort() {
        let bids = [bid(200 * M, None, &[(4, 0), (4, 40 * M), (10, 60 * M)])];
        assert_eq!(run(100, 10 * M, &bids), (10 * M, vec![vec![4, 4, 6]], 14));
    }

    #[test]
    fn a_comfort_outbids_a_poorer_need() {
        let bids = [
            bid(1_000 * M, None, &[(5, 0), (10, 0)]),
            bid(60 * M, None, &[(6, 0)]),
        ];
        assert_eq!(
            run(10, 10 * M, &bids),
            (90_909_091, vec![vec![5, 5], vec![0]], 21)
        );
    }

    #[test]
    fn a_short_market_drops_the_luxury_first() {
        let bids = [
            bid(200 * M, None, &[(4, 0), (4, 40 * M), (10, 60 * M)]),
            bid(90 * M, None, &[(6, 0)]),
        ];
        assert_eq!(
            run(12, 10 * M, &bids),
            (18_000_001, vec![vec![4, 4, 0], vec![4]], 20)
        );
    }

    #[test]
    fn a_step_fills_each_bids_rungs_in_order() {
        let bids = vec![bid(300 * M, None, &[(1, 0), (3, 0)]); 3];
        assert_eq!(
            run(7, 75 * M, &bids),
            (100 * M, vec![vec![1, 2], vec![1, 1], vec![1, 1]], 12)
        );
    }

    #[test]
    fn a_step_with_reserves() {
        let bids = vec![bid(1_000 * M, None, &[(2, 0), (2, 100 * M)]); 2];
        assert_eq!(
            run(5, 100 * M, &bids),
            (300 * M, vec![vec![2, 1], vec![2, 0]], 8)
        );
    }

    #[test]
    fn a_business_beside_a_household_ladder() {
        let bids = [
            bid(10_i128.pow(15), Some(245 * M), &[(100, 0)]),
            bid(5_000 * M, None, &[(20, 0), (30, 1_000 * M)]),
        ];
        assert_eq!(
            run(120, 100 * M, &bids),
            (190_476_191, vec![vec![100], vec![20, 0]], 140)
        );
    }

    /// A bid as `(wanted, purse, limit)`.
    type FlatBid = (u64, i128, Option<i128>);

    /// Every market of `clearing::rule`'s tests, as `(quote, bids as (wanted, purse, limit))`.
    fn clearing_markets() -> Vec<(i128, Vec<FlatBid>)> {
        const DEEP: i128 = 1_000_000_000_000_000;
        vec![
            (
                75 * M,
                vec![
                    (100, 7_500 * M, None),
                    (100, 11_250 * M, None),
                    (100, DEEP, None),
                ],
            ),
            (75 * M, vec![(4, 300 * M, None); 3]),
            (
                100 * M,
                vec![
                    (100, DEEP, Some(106 * M)),
                    (100, DEEP, Some(245 * M)),
                    (50, 5_000 * M, None),
                ],
            ),
            (100 * M, vec![(100, DEEP, Some(40 * M)); 2]),
            (
                100 * M,
                vec![
                    (10, 1_000_000 * M, Some(100 * M)),
                    (10, 1_000_000 * M, Some(100 * M)),
                    (4, 400 * M, None),
                ],
            ),
            (
                100 * M,
                vec![
                    (10, 1_000_000 * M, Some(40 * M)),
                    (10, 1_000_000 * M, Some(150 * M)),
                ],
            ),
            (
                280 * M,
                vec![
                    (1000, 3_000 * M, None),
                    (1000, 9_000 * M, None),
                    (1000, 500 * M, None),
                ],
            ),
            (280 * M, vec![(1000, 9_000 * M, None)]),
            (
                280 * M,
                vec![(5, 0, None), (5, 1_400 * M, None), (5, 560 * M, None)],
            ),
            (
                280 * M,
                vec![
                    (456_528, 127_827_840_000_000, None),
                    (50_726, 56_813_120_000_000, None),
                    (173_993, 24_359_020_000_000, None),
                    (19_334, 16_240_560_000_000, None),
                ],
            ),
        ]
    }

    #[test]
    fn a_one_rung_ladder_is_clear_market() {
        for (quote, bids) in clearing_markets() {
            let flat: Vec<MarketBid> = bids
                .iter()
                .map(|&(wanted, purse, limit)| MarketBid {
                    wanted,
                    purse: Currency::from_micro_units(purse),
                    limit: limit.map(Currency::from_micro_units),
                })
                .collect();
            let ladders: Vec<LadderBid> = bids
                .iter()
                .map(|&(wanted, purse, limit)| bid(purse, limit, &[(wanted, 0)]))
                .collect();
            let at_quote = clearing::clear_market(0, Currency::from_micro_units(quote), &flat)
                .expect("clears")
                .demand_at_quote;
            for supply in
                (0..=at_quote + 2).step_by(usize::try_from(at_quote / 40 + 1).expect("small"))
            {
                let expected =
                    clearing::clear_market(supply, Currency::from_micro_units(quote), &flat)
                        .expect("clears");
                let (price, quantities, demand) = run(supply, quote, &ladders);
                assert_eq!(price, expected.price.micro_units(), "price at {supply}");
                let single: Vec<u64> = quantities.iter().map(|rungs| rungs[0]).collect();
                assert_eq!(single, expected.quantities, "quantities at {supply}");
                assert_eq!(demand, expected.demand_at_quote);
            }
        }
    }

    #[test]
    fn the_laws_hold_for_ladders() {
        let markets: [(i128, Vec<LadderBid>); 3] = [
            (
                10 * M,
                vec![
                    bid(200 * M, None, &[(4, 0), (4, 40 * M), (10, 60 * M)]),
                    bid(90 * M, None, &[(6, 0)]),
                ],
            ),
            (75 * M, vec![bid(300 * M, None, &[(1, 0), (3, 0)]); 3]),
            (
                100 * M,
                vec![
                    bid(10_i128.pow(15), Some(245 * M), &[(100, 0)]),
                    bid(5_000 * M, None, &[(20, 0), (30, 1_000 * M)]),
                ],
            ),
        ];
        for (quote, bids) in &markets {
            let at_quote = run(0, *quote, bids).2;
            let mut previous = None;
            for supply in 0..=at_quote + 2 {
                let (price, quantities, demand) = run(supply, *quote, bids);
                assert_eq!(demand, at_quote);
                let sold: u64 = quantities.iter().flatten().sum();
                assert_eq!(
                    sold,
                    supply.min(at_quote),
                    "all on offer is sold at {supply}"
                );
                assert!(price >= *quote);
                for (bid, rungs) in bids.iter().zip(&quantities) {
                    let mut taken = 0_u64;
                    for (k, (&got, rung)) in rungs.iter().zip(&bid.rungs).enumerate() {
                        assert!(got <= rung.wanted);
                        taken += got;
                        if got > 0 {
                            assert!(
                                i128::from(taken) * price + rung.reserve.micro_units()
                                    <= bid.purse.micro_units(),
                                "rung {k} pays for itself at {supply}"
                            );
                            assert!(bid
                                .limit
                                .is_none_or(|l| l.micro_units().max(*quote) >= price));
                        }
                    }
                }
                if supply >= 2 {
                    assert!(
                        price <= previous.expect("set"),
                        "more supply never raises the price"
                    );
                }
                previous = Some(price);
            }
        }
    }

    #[test]
    fn a_bad_ladder_is_refused() {
        let refused = |quote: i128, bids: &[LadderBid]| {
            clear_ladder_market(5, Currency::from_micro_units(quote), bids)
        };
        let bad = Err(MaterialCircuitError::MarketClearingInvariant);
        assert_eq!(refused(0, &[bid(10, None, &[(1, 0)])]), bad);
        assert_eq!(refused(5, &[bid(-1, None, &[(1, 0)])]), bad);
        assert_eq!(refused(5, &[bid(10, None, &[(1, -1)])]), bad);
        assert_eq!(refused(5, &[bid(10, None, &[])]), bad);
        assert_eq!(
            refused(5, &[bid(100, None, &[(1, 0), (1, 50), (1, 10)])]),
            bad
        );
    }

    #[test]
    fn totals_add_each_bids_rungs() {
        let bids = [bid(200 * M, None, &[(4, 0), (4, 40 * M), (10, 60 * M)])];
        let outcome =
            clear_ladder_market(100, Currency::from_micro_units(10 * M), &bids).expect("clears");
        let totals = outcome.totals().expect("fits");
        assert_eq!(totals.quantities, vec![14]);
        assert_eq!(totals.price, outcome.price);
        assert_eq!(totals.demand_at_quote, 14);
    }
}
