//! Finite native services in the same resource and monetary authority as goods.
mod admission;

mod close;

mod market;

mod model;

mod validation;

pub use admission::{recurring_service_order_id, recurring_service_topup_order_id};

pub(crate) use close::ServiceClose;

pub use model::*;

pub(crate) use validation::{canonicalize, validate};

#[path = "services/requirements.rs"]
mod requirements;

pub(crate) use requirements::{
    input_requirements, is_service, kind, planning_grants, required_input, stage, Result,
};

use crate::{GoodId, MaterialCircuitError, MaterialCircuitState, UnitId};
