//! Shared atlas and county selection for the durable observer's geographic views.

mod scope;

pub(crate) use scope::CountyMapScope;

#[path = "map/layer.rs"]
mod layer;

#[allow(unused_imports)]
pub(crate) use layer::MapScopeSet;
pub use layer::{load_county_atlas, HoveredCounty, MapPlugin, SelectedCounty};

#[allow(unused_imports)]
use crate::atlas::CountyAtlas;
#[allow(unused_imports)]
use bevy::input::InputPlugin;

#[allow(unused_imports)]
use bevy::prelude::*;
