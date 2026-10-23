//! Committed quote evidence joined to actual native flows; no valuation is rerun.
mod flows;

mod model;

pub use model::{
    CompletedGoodsPrice, GoodsPriceBasis, GoodsPriceReason, ProductionGoodsPriceAccount,
};

#[path = "prices/projection.rs"]
mod projection;

#[allow(unused_imports)]
use projection::{offers, validate_reason, Key, Result};
#[allow(unused_imports)]
pub(super) use projection::{project_with_labels, validate};

#[allow(unused_imports)]
use super::{lifecycle, ProductionProjectionError};
#[allow(unused_imports)]
use babylon_material_circuit::{
    CommodityKind, GoodId, MaterialCircuitState, PriceDecision, PricePolicy, PriceReceipt,
    SellerOffer, SiteId, UnitId,
};
#[allow(unused_imports)]
use babylon_tick::material_world::MaterialTickReceipts;
#[allow(unused_imports)]
use std::collections::BTreeMap;
