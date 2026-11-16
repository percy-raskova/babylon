//! Stable slots for artist-rendered map symbols. Each tile has a centered pivot.
use super::VisualAssets;
use bevy::prelude::{ImageNode, TextureAtlas};

/// Row-major slots in the transparent, four-column economic map sheet.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
#[repr(usize)]
pub enum MapSymbol {
    /// Workplace or producing cohort.
    Producer,
    /// Retail seller.
    Shop,
    /// Energy or utility provider.
    Utility,
    /// County freight endpoint.
    Terminal,
    /// Observed FAA facility.
    Airport,
    /// Freight comparison origin.
    Origin,
    /// Local aid channel disclosed to the organizer.
    LocalAid,
    /// Remote aid channel disclosed to the organizer.
    RemoteAid,
}

impl MapSymbol {
    /// Sprite width and height in logical UI pixels, independent of map zoom.
    #[must_use]
    pub const fn size(self) -> f32 {
        match self {
            Self::Origin => 46.0,
            Self::Utility | Self::LocalAid => 42.0,
            Self::Producer | Self::RemoteAid => 38.0,
            Self::Airport | Self::Shop => 34.0,
            Self::Terminal => 30.0,
        }
    }

    /// Build a UI sprite with the same semantic slot in every map and legend.
    #[must_use]
    pub fn image(self, assets: &VisualAssets) -> ImageNode {
        ImageNode::from_atlas_image(
            assets.economic_map_atlas.clone(),
            TextureAtlas {
                layout: assets.economic_map_layout.clone(),
                index: self as usize,
            },
        )
    }
}
