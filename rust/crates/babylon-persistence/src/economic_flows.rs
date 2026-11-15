//! Economic counterparties and their captured geographic scope.
mod accounts;
mod model;
mod payments;
mod principals;
#[cfg(test)]
mod tests;

pub use model::{
    CountyInternalPoint, EconomicFlowError, EconomicPaymentPeriod, FlowAccount, Settlement,
};
pub(crate) use payments::project;
