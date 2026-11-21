//! The price of a short market.
//!
//! When what a seller's buyers can pay for at the posted price exceeds what is on offer, the price
//! rises to the first level at which the two are equal, every buyer pays that price, and the seller
//! keeps the difference. The rule is one pure function over exact integers.

mod ladder;
mod limit;
mod rule;
mod supply;
mod table;

pub use ladder::{clear_ladder_market, BidRung, LadderBid, LadderOutcome};
pub(crate) use limit::limit_price;
pub use rule::{clear_market, MarketBid, MarketClearingPolicy, MarketOutcome};
pub(crate) use supply::{sale_commitments, Offer};
pub(crate) use table::MarketTable;
pub use table::{MarketClearingReceipt, MarketMoment};
