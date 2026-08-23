//! Embedded visual assets and their typed Bevy loading surface.

mod catalog;
mod gallery;
mod presentation;

pub use catalog::{
    FrameKind, InterfaceIcon, MarkerIcon, ProvenanceIcon, SurfaceKind, VisualAssetDescriptor,
    VisualAssetId, VISUAL_ASSET_CATALOG,
};
pub use gallery::{GalleryAssetLabel, GalleryScrollRoot, VisualAssetGalleryPlugin};
pub use presentation::{ReadableTitle, StoryBanner, TitleMark, VisualPresentationPlugin};

use bevy::asset::{embedded_asset, load_embedded_asset, AssetApp, Assets, Handle};
use bevy::image::{Image, TextureAtlasLayout};
use bevy::prelude::{App, Plugin, Resource, UVec2};

/// Loads the complete embedded visual-asset family and its atlas layouts.
#[derive(Default)]
pub struct VisualAssetsPlugin;

impl Plugin for VisualAssetsPlugin {
    fn build(&self, app: &mut App) {
        app.init_asset::<TextureAtlasLayout>();

        embedded_asset!(app, "embedded/title-mark.png");
        embedded_asset!(app, "embedded/interface-atlas.png");
        embedded_asset!(app, "embedded/marker-atlas.png");
        embedded_asset!(app, "embedded/provenance-atlas.png");
        embedded_asset!(app, "embedded/frame-atlas.png");
        embedded_asset!(app, "embedded/surface-atlas.png");
        embedded_asset!(app, "embedded/hero-red-apparatus.webp");
        embedded_asset!(app, "embedded/hero-empire-anatomized.webp");
        embedded_asset!(app, "embedded/concept-bunker-oracle.webp");
        embedded_asset!(app, "embedded/concept-living-map.webp");
        embedded_asset!(app, "embedded/concept-carceral-circuit.webp");
        embedded_asset!(app, "embedded/concept-metabolic-rift.webp");
        embedded_asset!(app, "embedded/banner-counties.webp");
        embedded_asset!(app, "embedded/banner-carceral.webp");
        embedded_asset!(app, "embedded/banner-topology.webp");
        embedded_asset!(app, "embedded/banner-collapse.webp");

        let title_mark = load_embedded_asset!(app, "embedded/title-mark.png");
        let interface_atlas = load_embedded_asset!(app, "embedded/interface-atlas.png");
        let marker_atlas = load_embedded_asset!(app, "embedded/marker-atlas.png");
        let provenance_atlas = load_embedded_asset!(app, "embedded/provenance-atlas.png");
        let frame_atlas = load_embedded_asset!(app, "embedded/frame-atlas.png");
        let surface_atlas = load_embedded_asset!(app, "embedded/surface-atlas.png");
        let hero_red_apparatus = load_embedded_asset!(app, "embedded/hero-red-apparatus.webp");
        let hero_empire_anatomized =
            load_embedded_asset!(app, "embedded/hero-empire-anatomized.webp");
        let concept_bunker_oracle =
            load_embedded_asset!(app, "embedded/concept-bunker-oracle.webp");
        let concept_living_map = load_embedded_asset!(app, "embedded/concept-living-map.webp");
        let concept_carceral_circuit =
            load_embedded_asset!(app, "embedded/concept-carceral-circuit.webp");
        let concept_metabolic_rift =
            load_embedded_asset!(app, "embedded/concept-metabolic-rift.webp");
        let banner_counties = load_embedded_asset!(app, "embedded/banner-counties.webp");
        let banner_carceral = load_embedded_asset!(app, "embedded/banner-carceral.webp");
        let banner_topology = load_embedded_asset!(app, "embedded/banner-topology.webp");
        let banner_collapse = load_embedded_asset!(app, "embedded/banner-collapse.webp");

        let (interface_layout, marker_layout, provenance_layout, frame_layout, surface_layout) =
            create_atlas_layouts(app);

        app.insert_resource(VisualAssets {
            hero_red_apparatus,
            hero_empire_anatomized,
            concept_bunker_oracle,
            concept_living_map,
            concept_carceral_circuit,
            concept_metabolic_rift,
            banner_counties,
            banner_carceral,
            banner_topology,
            banner_collapse,
            title_mark,
            interface_atlas,
            marker_atlas,
            provenance_atlas,
            frame_atlas,
            surface_atlas,
            interface_layout,
            marker_layout,
            provenance_layout,
            frame_layout,
            surface_layout,
        });
    }
}

type AtlasLayouts = (
    Handle<TextureAtlasLayout>,
    Handle<TextureAtlasLayout>,
    Handle<TextureAtlasLayout>,
    Handle<TextureAtlasLayout>,
    Handle<TextureAtlasLayout>,
);

fn create_atlas_layouts(app: &mut App) -> AtlasLayouts {
    let mut layouts = app.world_mut().resource_mut::<Assets<TextureAtlasLayout>>();
    let interface_layout = layouts.add(TextureAtlasLayout::from_grid(
        UVec2::new(128, 128),
        4,
        4,
        None,
        None,
    ));
    let marker_layout = layouts.add(TextureAtlasLayout::from_grid(
        UVec2::new(128, 128),
        3,
        2,
        None,
        None,
    ));
    let provenance_layout = layouts.add(TextureAtlasLayout::from_grid(
        UVec2::new(128, 128),
        2,
        2,
        None,
        None,
    ));
    let frame_layout = layouts.add(TextureAtlasLayout::from_grid(
        UVec2::new(64, 64),
        4,
        1,
        None,
        None,
    ));
    let surface_layout = layouts.add(TextureAtlasLayout::from_grid(
        UVec2::new(128, 128),
        3,
        1,
        None,
        None,
    ));
    (
        interface_layout,
        marker_layout,
        provenance_layout,
        frame_layout,
        surface_layout,
    )
}

/// Named image and layout handles for the complete visual-asset family.
#[derive(Clone, Resource)]
pub struct VisualAssets {
    /// The Red Apparatus hero illustration.
    pub hero_red_apparatus: Handle<Image>,
    /// The Empire Anatomized hero illustration.
    pub hero_empire_anatomized: Handle<Image>,
    /// The Bunker Oracle concept illustration.
    pub concept_bunker_oracle: Handle<Image>,
    /// The Living Map concept illustration.
    pub concept_living_map: Handle<Image>,
    /// The Carceral Circuit concept illustration.
    pub concept_carceral_circuit: Handle<Image>,
    /// The Metabolic Rift concept illustration.
    pub concept_metabolic_rift: Handle<Image>,
    /// The counties-story banner.
    pub banner_counties: Handle<Image>,
    /// The carceral-story banner.
    pub banner_carceral: Handle<Image>,
    /// The topology-story banner.
    pub banner_topology: Handle<Image>,
    /// The collapse-story banner.
    pub banner_collapse: Handle<Image>,
    /// The Babylon title mark.
    pub title_mark: Handle<Image>,
    /// The sixteen-cell interface icon atlas.
    pub interface_atlas: Handle<Image>,
    /// The six-cell map-marker atlas.
    pub marker_atlas: Handle<Image>,
    /// The four-cell projection-provenance atlas.
    pub provenance_atlas: Handle<Image>,
    /// The four-cell frame atlas.
    pub frame_atlas: Handle<Image>,
    /// The three-cell surface-texture atlas.
    pub surface_atlas: Handle<Image>,
    /// The sixteen-cell interface icon layout.
    pub interface_layout: Handle<TextureAtlasLayout>,
    /// The six-cell map-marker layout.
    pub marker_layout: Handle<TextureAtlasLayout>,
    /// The four-cell projection-provenance layout.
    pub provenance_layout: Handle<TextureAtlasLayout>,
    /// The four-cell frame layout.
    pub frame_layout: Handle<TextureAtlasLayout>,
    /// The three-cell surface-texture layout.
    pub surface_layout: Handle<TextureAtlasLayout>,
}

impl VisualAssets {
    /// Returns a clone of the image handle for `id`.
    #[must_use]
    pub fn image(&self, id: VisualAssetId) -> Handle<Image> {
        match id {
            VisualAssetId::TitleMark => self.title_mark.clone(),
            VisualAssetId::InterfaceAtlas => self.interface_atlas.clone(),
            VisualAssetId::MarkerAtlas => self.marker_atlas.clone(),
            VisualAssetId::ProvenanceAtlas => self.provenance_atlas.clone(),
            VisualAssetId::FrameAtlas => self.frame_atlas.clone(),
            VisualAssetId::SurfaceAtlas => self.surface_atlas.clone(),
            VisualAssetId::HeroRedApparatus => self.hero_red_apparatus.clone(),
            VisualAssetId::HeroEmpireAnatomized => self.hero_empire_anatomized.clone(),
            VisualAssetId::ConceptBunkerOracle => self.concept_bunker_oracle.clone(),
            VisualAssetId::ConceptLivingMap => self.concept_living_map.clone(),
            VisualAssetId::ConceptCarceralCircuit => self.concept_carceral_circuit.clone(),
            VisualAssetId::ConceptMetabolicRift => self.concept_metabolic_rift.clone(),
            VisualAssetId::BannerCounties => self.banner_counties.clone(),
            VisualAssetId::BannerCarceral => self.banner_carceral.clone(),
            VisualAssetId::BannerTopology => self.banner_topology.clone(),
            VisualAssetId::BannerCollapse => self.banner_collapse.clone(),
        }
    }
}
