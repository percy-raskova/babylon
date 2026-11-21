//! The moments at which a market is priced, the market's receipt, and the period's table of markets.

use super::rule::MarketOutcome;
use crate::{GoodId, MaterialCircuitError, SiteId, UnitId};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;

/// The moments of a period at which a market is priced.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum MarketMoment {
    HouseholdGoods = 1,
    Utility = 2,
    LocalService = 3,
    Restocking = 4,
}

/// What one short market cleared at.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MarketClearingReceipt {
    pub period: u64,
    pub moment: MarketMoment,
    /// The seller.
    pub site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub quote_price: Currency,
    pub clearing_price: Currency,
    /// On offer to new buyers.
    pub supply: u64,
    pub demand_at_quote: u64,
    pub sold_quantity: u64,
    pub bidders: u32,
    pub served_bidders: u32,
}

impl MarketClearingReceipt {
    /// # Errors
    /// `MarketClearingInvariant` unless the period is positive, the quote is positive, the clearing
    /// price is at least the quote, the demand at the quote exceeds the supply, everything on offer
    /// was sold, no more buyers were served than bid, and the price is the quote when nothing was
    /// on offer.
    pub fn validate(&self) -> Result<(), MaterialCircuitError> {
        if self.period == 0
            || self.quote_price.micro_units() <= 0
            || self.clearing_price < self.quote_price
            || self.demand_at_quote <= self.supply
            || self.sold_quantity != self.supply
            || self.served_bidders > self.bidders
            || (self.supply == 0 && self.clearing_price != self.quote_price)
        {
            return Err(MaterialCircuitError::MarketClearingInvariant);
        }
        Ok(())
    }
}

type MarketKey = (MarketMoment, SiteId, GoodId, UnitId);

#[derive(Debug)]
struct MarketRow {
    key: MarketKey,
    price: Currency,
    /// What the buyers could pay for at the posted price, `None` when no buyer bid.
    demand: Option<u64>,
    priced_out: u64,
    receipt: Option<MarketClearingReceipt>,
}

/// The markets of one close, in the order they cleared.
#[derive(Debug, Default)]
pub(crate) struct MarketTable {
    rows: Vec<MarketRow>,
    /// The place in `rows` of each market, by its key.
    by_key: BTreeMap<MarketKey, usize>,
    /// What buyers were priced out of at each seller's product, over every moment.
    priced_out_by_product: BTreeMap<(SiteId, GoodId, UnitId), u64>,
}

impl MarketTable {
    /// Record one market: always its price, and a receipt when it was short.
    #[allow(
        clippy::too_many_arguments,
        reason = "the plan fixes this signature; later tasks call it at four moments"
    )]
    pub(crate) fn record(
        &mut self,
        period: u64,
        moment: MarketMoment,
        seller: (SiteId, GoodId, UnitId),
        quote: Currency,
        supply: u64,
        bids: usize,
        outcome: &MarketOutcome,
    ) -> Result<(), MaterialCircuitError> {
        let key = (moment, seller.0, seller.1, seller.2);
        if self.has_row(moment, seller.0, seller.1, seller.2) {
            return Err(MaterialCircuitError::MarketClearingInvariant);
        }
        let sold = outcome
            .quantities
            .iter()
            .try_fold(0_u64, |sum, &quantity| sum.checked_add(quantity))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let mut priced_out = 0;
        let mut receipt = None;
        if outcome.demand_at_quote > supply {
            let count = |n: usize| u32::try_from(n).map_err(|_| MaterialCircuitError::Arithmetic);
            let row = MarketClearingReceipt {
                period,
                moment,
                site_id: seller.0,
                good_id: seller.1,
                unit_id: seller.2,
                quote_price: quote,
                clearing_price: outcome.price,
                supply,
                demand_at_quote: outcome.demand_at_quote,
                sold_quantity: sold,
                bidders: count(bids)?,
                served_bidders: count(outcome.quantities.iter().filter(|&&q| q > 0).count())?,
            };
            row.validate()?;
            priced_out = outcome.demand_at_quote.saturating_sub(sold);
            receipt = Some(row);
        }
        let total = self
            .priced_out_by_product
            .entry((seller.0, seller.1, seller.2))
            .or_insert(0);
        *total = total
            .checked_add(priced_out)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        self.by_key.insert(key, self.rows.len());
        self.rows.push(MarketRow {
            key,
            price: outcome.price,
            demand: (bids > 0).then_some(outcome.demand_at_quote),
            priced_out,
            receipt,
        });
        Ok(())
    }

    /// What buyers could pay for at the posted price and did not get, at this seller's product.
    pub(crate) fn priced_out(&self, site: SiteId, good: GoodId, unit: UnitId) -> u64 {
        self.priced_out_by_product
            .get(&(site, good, unit))
            .copied()
            .unwrap_or(0)
    }

    /// What this market's buyers could pay for at the posted price this period, short or not.
    /// `None` when no buyer bid in it.
    pub(crate) fn demand_at_quote(
        &self,
        moment: MarketMoment,
        site: SiteId,
        good: GoodId,
        unit: UnitId,
    ) -> Option<u64> {
        self.row(moment, site, good, unit)
            .and_then(|row| row.demand)
    }

    /// What goods buyers were priced out of, by seller and product, for the seller's next plan.
    /// Services are left out: without a market policy they are planned from what was asked, and
    /// under one from the demand at the quote (rule P14).
    pub(crate) fn priced_out_goods(
        &self,
    ) -> impl Iterator<Item = ((SiteId, GoodId, UnitId), u64)> + '_ {
        self.rows
            .iter()
            .filter(|row| {
                matches!(
                    row.key.0,
                    MarketMoment::HouseholdGoods | MarketMoment::Restocking
                ) && row.priced_out > 0
            })
            .map(|row| ((row.key.1, row.key.2, row.key.3), row.priced_out))
    }

    fn row(
        &self,
        moment: MarketMoment,
        site: SiteId,
        good: GoodId,
        unit: UnitId,
    ) -> Option<&MarketRow> {
        self.by_key
            .get(&(moment, site, good, unit))
            .map(|&at| &self.rows[at])
    }

    pub(crate) fn has_row(
        &self,
        moment: MarketMoment,
        site: SiteId,
        good: GoodId,
        unit: UnitId,
    ) -> bool {
        self.by_key.contains_key(&(moment, site, good, unit))
    }

    /// The price paid at one market of this close, if it cleared.
    #[allow(dead_code, reason = "later moments and the stored records read it")]
    pub(crate) fn price(
        &self,
        moment: MarketMoment,
        site: SiteId,
        good: GoodId,
        unit: UnitId,
    ) -> Option<Currency> {
        self.row(moment, site, good, unit).map(|row| row.price)
    }

    /// Sorted by (moment, site, good, unit).
    pub(crate) fn into_receipts(self) -> Vec<MarketClearingReceipt> {
        let mut receipts: Vec<_> = self
            .rows
            .into_iter()
            .filter_map(|row| row.receipt)
            .collect();
        receipts.sort_by_key(|row| (row.moment, row.site_id, row.good_id, row.unit_id));
        receipts
    }
}
