//! Designed historical-cost bookkeeping over the authoritative physical close.
//! No price revaluation, credit, money issuance, or claim to measure surplus value.

mod book;

mod close;

mod equipment;

mod financial;

mod model;

mod prices;

mod validation;

pub(crate) use close::CostClose;

pub(crate) use validation::validate;

pub use book::HistoricalCostBook;

pub use model::*;

#[path = "valuation/arithmetic.rs"]
mod arithmetic;

#[allow(unused_imports)]
pub(crate) use arithmetic::portion;
pub use arithmetic::MAX_CARRYING_STOCKS;
#[allow(unused_imports)]
use arithmetic::{add, amount, sub, zero, Result};

#[allow(unused_imports)]
use crate::MaterialCircuitError;
#[allow(unused_imports)]
use babylon_kernel::currency::Currency;
