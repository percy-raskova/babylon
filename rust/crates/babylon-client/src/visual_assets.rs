//! Embedded visual assets and their typed Bevy loading surface.

mod catalog;

mod fonts;

mod gallery;

pub use catalog::{
    FrameKind, InterfaceIcon, MarkerIcon, ProvenanceIcon, SurfaceKind, VisualAssetDescriptor,
    VisualAssetId, VISUAL_ASSET_CATALOG,
};

pub use fonts::ObserverFonts;

pub use gallery::{GalleryAssetLabel, GalleryScrollRoot, VisualAssetGalleryPlugin};

#[path = "visual_assets/plugin.rs"]
mod plugin;

#[allow(unused_imports)]
use plugin::{
    create_atlas_layouts, linear_image_settings, nearest_image_settings, register_visuals,
    AtlasLayouts, EMBEDDED_VISUALS,
};
pub use plugin::{VisualAssets, VisualAssetsPlugin};

#[allow(unused_imports)]
use bevy::asset::io::embedded::EmbeddedAssetRegistry;
#[allow(unused_imports)]
use bevy::asset::{AssetApp, AssetServer, Assets, Handle};
#[allow(unused_imports)]
use bevy::image::{Image, ImageLoaderSettings, ImageSampler, TextureAtlasLayout};
#[allow(unused_imports)]
use bevy::prelude::{App, Plugin, Resource, UVec2};
#[allow(unused_imports)]
use std::path::{Path, PathBuf};
