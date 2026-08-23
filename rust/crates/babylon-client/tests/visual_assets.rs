//! Behavioral contracts for the embedded Bevy visual-asset surface.

use bevy::asset::AssetPlugin;
use bevy::image::ImagePlugin;
use bevy::prelude::*;
use bevy::render::texture::TexturePlugin;
use std::time::Duration;

static UNKNOWN_STORY: babylon_client::story::Story = babylon_client::story::Story {
    id: "not-in-catalog",
    title: "Unknown",
    premise: "",
    premise_source: "",
    scenario_src: "",
    rule_srcs: &[],
    session_id: "unknown",
    map_binding: None,
    arc: None,
    validated_horizon: 0,
    delays: &[],
};

fn add_visual_asset_plugins(app: &mut App) {
    app.add_plugins((
        MinimalPlugins,
        AssetPlugin::default(),
        ImagePlugin::default(),
        // Bevy 0.18 registers the concrete image loader in this plugin's finish phase.
        TexturePlugin,
    ));
    app.add_plugins(babylon_client::visual_assets::VisualAssetsPlugin);
}

fn visual_assets_app() -> App {
    let mut app = App::new();
    add_visual_asset_plugins(&mut app);
    app.finish();
    app
}

fn visual_presentation_app(
    story: &'static babylon_client::story::Story,
    story_card_visible: bool,
) -> App {
    let mut app = App::new();
    add_visual_asset_plugins(&mut app);
    app.insert_resource(babylon_client::story::SelectedStory(story));
    app.insert_resource(babylon_client::ui::story_card::StoryCardVisible(
        story_card_visible,
    ));
    app.add_plugins(babylon_client::visual_assets::VisualPresentationPlugin);
    app.finish();
    app.update();
    app
}

fn story_banner_state(app: &mut App) -> (Handle<Image>, Visibility) {
    let world = app.world_mut();
    let mut query = world.query_filtered::<
        (&ImageNode, &Visibility),
        With<babylon_client::visual_assets::StoryBanner>,
    >();
    let (image, visibility) = query
        .single(world)
        .expect("exactly one story banner entity");
    (image.image.clone(), *visibility)
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

#[test]
fn presentation_spawns_the_title_mark_readable_title_and_counties_banner() {
    let mut app = visual_presentation_app(babylon_client::story::counties(), true);

    let title_mark_image = {
        let world = app.world_mut();
        let mut query =
            world.query_filtered::<&ImageNode, With<babylon_client::visual_assets::TitleMark>>();
        query
            .single(world)
            .expect("exactly one title mark entity")
            .image
            .clone()
    };
    let readable_title = {
        let world = app.world_mut();
        let mut query =
            world.query_filtered::<&Text, With<babylon_client::visual_assets::ReadableTitle>>();
        query
            .single(world)
            .expect("exactly one readable title entity")
            .0
            .clone()
    };
    let (banner_image, visibility) = story_banner_state(&mut app);
    let assets = app
        .world()
        .resource::<babylon_client::visual_assets::VisualAssets>();

    assert_eq!(title_mark_image, assets.title_mark);
    assert_eq!(readable_title, "BABYLON");
    assert_eq!(banner_image, assets.banner_counties);
    assert_eq!(visibility, Visibility::Visible);
}

#[test]
fn story_banner_tracks_the_selected_story_and_story_card_visibility() {
    let mut app = visual_presentation_app(babylon_client::story::counties(), true);

    app.world_mut()
        .resource_mut::<babylon_client::story::SelectedStory>()
        .0 = babylon_client::story::carceral();
    app.update();

    let (banner_image, visibility) = story_banner_state(&mut app);
    let assets = app
        .world()
        .resource::<babylon_client::visual_assets::VisualAssets>();
    assert_eq!(banner_image, assets.banner_carceral);
    assert_eq!(visibility, Visibility::Visible);

    app.world_mut()
        .resource_mut::<babylon_client::ui::story_card::StoryCardVisible>()
        .0 = false;
    app.update();

    let (_, visibility) = story_banner_state(&mut app);
    assert_eq!(visibility, Visibility::Hidden);
}

#[test]
#[should_panic(expected = "no visual banner declared for story \"not-in-catalog\"")]
fn presentation_rejects_an_unknown_story_id() {
    let _app = visual_presentation_app(&UNKNOWN_STORY, true);
}
