//! Isolated loading contract for embedded Bevy visual assets.

use bevy::asset::AssetPlugin;
use bevy::image::{ImagePlugin, ImageSampler};
use bevy::prelude::*;
use bevy::render::texture::TexturePlugin;
use std::time::Duration;

fn visual_assets_app() -> App {
    let mut app = App::new();
    app.add_plugins((
        MinimalPlugins,
        AssetPlugin::default(),
        ImagePlugin::default(),
        // Bevy 0.18 registers the concrete image loader in this plugin's finish phase.
        TexturePlugin,
    ));
    app.add_plugins(babylon_client::visual_assets::VisualAssetsPlugin);
    app.finish();
    app
}

fn assert_loaded_sampler_contract(app: &App) {
    let world = app.world();
    let assets = world.resource::<babylon_client::visual_assets::VisualAssets>();
    let images = world.resource::<Assets<Image>>();
    let nearest_images = [
        ("title-mark", &assets.title_mark),
        ("interface-atlas", &assets.interface_atlas),
        ("marker-atlas", &assets.marker_atlas),
        ("provenance-atlas", &assets.provenance_atlas),
        ("frame-atlas", &assets.frame_atlas),
        ("surface-atlas", &assets.surface_atlas),
    ];
    for (id, handle) in nearest_images {
        let image = images
            .get(handle)
            .unwrap_or_else(|| panic!("loaded image {id:?} is absent from Assets<Image>"));
        assert_eq!(
            image.sampler,
            ImageSampler::nearest(),
            "interface image {id:?} must use nearest sampling"
        );
    }

    let linear_images = [
        ("hero-red-apparatus", &assets.hero_red_apparatus),
        ("hero-empire-anatomized", &assets.hero_empire_anatomized),
        ("concept-bunker-oracle", &assets.concept_bunker_oracle),
        ("concept-living-map", &assets.concept_living_map),
        ("concept-carceral-circuit", &assets.concept_carceral_circuit),
        ("concept-metabolic-rift", &assets.concept_metabolic_rift),
        ("banner-counties", &assets.banner_counties),
        ("banner-carceral", &assets.banner_carceral),
        ("banner-topology", &assets.banner_topology),
        ("banner-collapse", &assets.banner_collapse),
    ];
    for (id, handle) in linear_images {
        let image = images
            .get(handle)
            .unwrap_or_else(|| panic!("loaded image {id:?} is absent from Assets<Image>"));
        assert_eq!(
            image.sampler,
            ImageSampler::linear(),
            "illustration {id:?} must use linear sampling"
        );
    }
}

#[test]
fn every_typed_embedded_image_loads_within_sixty_four_updates() {
    let mut app = visual_assets_app();

    for _ in 0..64 {
        app.update();
        std::thread::sleep(Duration::from_millis(100));
        let asset_server = app.world().resource::<AssetServer>();
        let assets = app
            .world()
            .resource::<babylon_client::visual_assets::VisualAssets>();
        if babylon_client::visual_assets::VISUAL_ASSET_CATALOG
            .iter()
            .all(|descriptor| {
                asset_server.is_loaded_with_dependencies(assets.image(descriptor.id).id())
            })
        {
            assert_loaded_sampler_contract(&app);
            return;
        }
    }

    let asset_server = app.world().resource::<AssetServer>();
    let assets = app
        .world()
        .resource::<babylon_client::visual_assets::VisualAssets>();
    let unloaded: Vec<_> = babylon_client::visual_assets::VISUAL_ASSET_CATALOG
        .iter()
        .filter(|descriptor| {
            !asset_server.is_loaded_with_dependencies(assets.image(descriptor.id).id())
        })
        .map(|descriptor| descriptor.id)
        .collect();
    assert!(
        unloaded.is_empty(),
        "embedded images did not load within 64 updates: {unloaded:?}"
    );
}
