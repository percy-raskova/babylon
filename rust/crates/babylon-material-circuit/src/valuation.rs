//! Designed historical-cost bookkeeping over the authoritative physical close.
//! No price revaluation, credit, money issuance, or claim to measure surplus value.

mod book;

mod close;
mod company_basis;
pub use company_basis::{
    CompanyBasisAsset, CompanyBasisMovement, CompanySale, MAX_COMPANY_BASIS_MOVEMENTS,
};

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

pub(crate) use arithmetic::portion;
pub use arithmetic::MAX_CARRYING_STOCKS;
use arithmetic::{add, amount, sub, zero, Result};
