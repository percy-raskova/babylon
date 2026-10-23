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

#[allow(unused_imports)]
pub(crate) use validation::{canonicalize, validate};
#[allow(unused_imports)]
use validation::{
    row_limits, unique, validate_attendance, validate_firm_policies, validate_households,
    validate_offers, Result,
};

#[allow(unused_imports)]
use crate::{
    AccountId, CircuitAccounting, MaterialCircuitError, MaterialCircuitState, MerchantRole,
    MAX_MATERIAL_CIRCUIT_ROWS,
};
#[allow(unused_imports)]
use std::collections::{BTreeMap, BTreeSet};
