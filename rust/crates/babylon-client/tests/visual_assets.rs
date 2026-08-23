//! Behavioral contracts for the embedded Bevy visual-asset surface.

use bevy::asset::AssetPlugin;
use bevy::image::ImagePlugin;
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

#[test]
fn typed_catalog_declares_all_sixteen_images_and_bounded_atlases() {
    assert_eq!(
        babylon_client::visual_assets::VISUAL_ASSET_CATALOG.len(),
        16
    );
    assert_eq!(babylon_client::visual_assets::InterfaceIcon::COUNT, 16);
    assert_eq!(babylon_client::visual_assets::MarkerIcon::COUNT, 6);
    assert_eq!(babylon_client::visual_assets::ProvenanceIcon::COUNT, 4);
    assert_eq!(babylon_client::visual_assets::FrameKind::COUNT, 4);
    assert_eq!(babylon_client::visual_assets::SurfaceKind::COUNT, 3);
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
