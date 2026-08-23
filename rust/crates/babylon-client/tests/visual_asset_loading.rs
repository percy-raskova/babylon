//! Isolated loading contract for embedded Bevy visual assets.

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
