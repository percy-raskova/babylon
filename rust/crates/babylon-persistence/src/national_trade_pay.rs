//! The pay of each trade by place (rule O2), read from stage 1's pay table.
//!
//! The table sets pay and nothing else: where residents work stays the cohort
//! table's weights. A row's wage is its own `wage_payroll_usd` over its
//! `wage_jobs` at 2,080 hours a year; the reader never re-derives a withheld
//! wage, and no average is taken over a place whose rows hold no jobs.

mod model;

mod parse;

#[cfg(test)]
mod tests;

pub use model::{
    JobsRule, NationalTradePayError, NationalTradePayReference, TradePayRow, WageRule,
};

#[path = "national_trade_pay/artifact.rs"]
mod artifact;

pub use artifact::national_trade_pay_reference;
