//! Committed quote evidence joined to actual native flows; no valuation is rerun.
mod flows;

mod model;

pub use model::{
    CompletedGoodsPrice, GoodsPriceBasis, GoodsPriceReason, ProductionGoodsPriceAccount,
};

#[path = "prices/projection.rs"]
mod projection;

pub(super) use projection::{project_with_labels, validate};
use projection::{Key, Result};

use super::{lifecycle, ProductionProjectionError};
use babylon_material_circuit::{MaterialCircuitState, PriceReceipt};
use babylon_tick::material_world::MaterialTickReceipts;
