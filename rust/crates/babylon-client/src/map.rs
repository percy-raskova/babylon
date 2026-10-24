//! Shared atlas and county selection for the durable observer's geographic views.

mod scope;

pub(crate) use scope::CountyMapScope;

#[path = "map/layer.rs"]
mod layer;

pub(crate) use layer::MapScopeSet;
pub use layer::{load_county_atlas, HoveredCounty, MapPlugin, SelectedCounty};
