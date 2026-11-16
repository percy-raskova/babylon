//! Embedded visual assets and their typed Bevy loading surface.

mod catalog;

mod fonts;
mod map_art;
mod map_symbol;
pub use map_symbol::MapSymbol;

mod gallery;

pub use catalog::{
    FrameKind, InterfaceIcon, MarkerIcon, ProvenanceIcon, SurfaceKind, VisualAssetDescriptor,
    VisualAssetId, VISUAL_ASSET_CATALOG,
};

pub use fonts::ObserverFonts;

pub use gallery::{GalleryAssetLabel, GalleryScrollRoot, VisualAssetGalleryPlugin};

#[path = "visual_assets/plugin.rs"]
mod plugin;

pub use plugin::{VisualAssets, VisualAssetsPlugin};

#[cfg(test)]
pub(crate) use plugin::install_test_assets;
