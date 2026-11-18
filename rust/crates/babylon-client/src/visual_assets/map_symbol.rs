//! Stable slots for artist-rendered map symbols. Each tile has a centered pivot.
use super::{InterfaceIcon, VisualAssets};
use bevy::prelude::{ImageNode, TextureAtlas};

/// A geographic place, organizer channel, or reported condition.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
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
    /// Food shortage recorded at this close.
    FoodShortage,
    /// Public county hearing docket.
    Hearing,
}

impl MapSymbol {
    /// Sprite width and height in logical UI pixels, independent of map zoom.
    #[must_use]
    pub const fn size(self) -> f32 {
        match self {
            Self::Origin => 46.0,
            Self::FoodShortage => 44.0,
            Self::Utility | Self::LocalAid | Self::Hearing => 42.0,
            Self::Producer | Self::RemoteAid => 38.0,
            Self::Airport | Self::Shop => 34.0,
            Self::Terminal => 30.0,
        }
    }

    /// Build a UI sprite with the same semantic slot in every map and legend.
    #[must_use]
    pub fn image(self, assets: &VisualAssets) -> ImageNode {
        let index = match self {
            Self::Producer => 0,
            Self::Shop => 1,
            Self::Utility => 2,
            Self::Terminal => 3,
            Self::Airport => 4,
            Self::Origin => 5,
            Self::LocalAid => 6,
            Self::RemoteAid => 7,
            Self::Hearing => 8,
            Self::FoodShortage => {
                return ImageNode::from_atlas_image(
                    assets.interface_atlas.clone(),
                    TextureAtlas {
                        layout: assets.interface_layout.clone(),
                        index: InterfaceIcon::Warning.index(),
                    },
                );
            }
        };
        ImageNode::from_atlas_image(
            assets.economic_map_atlas.clone(),
            TextureAtlas {
                layout: assets.economic_map_layout.clone(),
                index,
            },
        )
    }
}
