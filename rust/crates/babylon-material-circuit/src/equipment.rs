//! Actual productive equipment; money alone supplies no productive capacity.
mod choice;

mod installation;

mod investment;

mod model;

mod receipts;

mod validation;

pub use installation::equipment_installation_id;

pub(crate) use installation::{install, work_requests};

pub use investment::equipment_purchase_order_id;

pub(crate) use investment::invest;

pub use model::*;

pub use receipts::*;

pub(crate) use validation::{canonicalize, row_limits, validate};

#[path = "equipment/lookup.rs"]
mod lookup;

use lookup::Result;
pub(crate) use lookup::{get, get_mut};

use crate::{MaterialCircuitError, MaterialCircuitState, ProcessId};
