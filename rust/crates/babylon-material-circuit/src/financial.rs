//! Designed, cash-funded public/ownership policy in the existing atomic close.
mod close;
mod company;
mod cut;
pub use company::validate_company_distributions;
pub(crate) use company::{validate_company_accounts, validate_company_policy};

mod layoffs;

mod model;

mod programs;

mod receipts;

mod validation;

pub(crate) use close::FinancialClose;

pub(crate) use layoffs::{
    advance_layoffs, advance_records, holds_after_layoff_program, program_window,
};

pub use model::*;

pub use receipts::validate_distribution_receipts;

pub(crate) use validation::{canonicalize, validate};

#[path = "financial/arithmetic.rs"]
mod arithmetic;

pub(crate) use arithmetic::fraction;
use arithmetic::{add, available, sub, zero, Result};
