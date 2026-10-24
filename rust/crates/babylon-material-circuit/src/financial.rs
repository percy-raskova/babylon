//! Designed, cash-funded public/ownership policy in the existing atomic close.
mod close;

mod model;

mod receipts;

mod validation;

pub(crate) use close::FinancialClose;

pub use model::*;

pub use receipts::validate_distribution_receipts;

pub(crate) use validation::{canonicalize, validate};

#[path = "financial/arithmetic.rs"]
mod arithmetic;

use arithmetic::{add, available, fraction, sub, zero, Result};
