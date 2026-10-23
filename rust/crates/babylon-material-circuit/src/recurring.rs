//! Recurring household needs and purchases share the authoritative material close.

pub(crate) mod firms;

pub(crate) mod households;

mod model;

pub(crate) mod prices;

pub use firms::{recurring_procurement_order_id, ProcurementReceipt, ProductionPlanReceipt};

pub use households::recurring_household_order_id;

pub(crate) use households::{
    admit_household_orders, complete_household_orders, consume_household_needs,
};

pub use model::*;

pub use prices::{GoodsPriceCostBasis, GoodsPriceCostEvidence, PriceDecision, PriceReceipt};

#[cfg(test)]
mod households_tests;

#[path = "recurring/validation.rs"]
mod validation;

use validation::Result;
pub(crate) use validation::{canonicalize, validate};
