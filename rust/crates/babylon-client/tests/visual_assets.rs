//! Behavioral contracts for the embedded Bevy visual-asset surface.

use bevy::asset::AssetPlugin;
use bevy::image::ImagePlugin;
use bevy::input::mouse::{AccumulatedMouseScroll, MouseScrollUnit};
use bevy::prelude::*;
use bevy::render::texture::TexturePlugin;
use std::sync::{Mutex, MutexGuard};

static BEVY_APP_TEST_MUTEX: Mutex<()> = Mutex::new(());

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

fn bevy_app_test_guard() -> MutexGuard<'static, ()> {
    match BEVY_APP_TEST_MUTEX.lock() {
        Ok(guard) => guard,
        // `presentation_rejects_an_unknown_story_id` deliberately panics while holding this
        // guard, so later app tests must recover the mutex rather than conceal the assertion.
        Err(poisoned) => poisoned.into_inner(),
    }
}

fn visual_asset_gallery_app() -> App {
    let mut app = App::new();
    add_visual_asset_plugins(&mut app);
    app.add_plugins(babylon_client::visual_assets::VisualAssetGalleryPlugin);
    app.finish();
    app.update();
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
    app.add_systems(Startup, babylon_client::ui::story_card::spawn_story_card);
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
fn gallery_labels_match_the_fixed_visual_asset_catalog() {
    let _guard = bevy_app_test_guard();
    let mut app = visual_asset_gallery_app();
    let world = app.world_mut();
    let mut labels =
        world.query_filtered::<&Text, With<babylon_client::visual_assets::GalleryAssetLabel>>();
    let actual: Vec<_> = labels
        .iter(world)
        .take(17)
        .map(|text| text.0.clone())
        .collect();
    let expected: Vec<_> = babylon_client::visual_assets::VISUAL_ASSET_CATALOG
        .iter()
        .map(|descriptor| descriptor.label.to_owned())
        .collect();

    assert_eq!(actual.len(), 16);
    assert_eq!(actual, expected);
}

#[test]
fn gallery_scroll_position_changes_from_injected_line_input() {
    let _guard = bevy_app_test_guard();
    let mut app = visual_asset_gallery_app();
    let root = {
        let world = app.world_mut();
        let mut roots = world
            .query_filtered::<Entity, With<babylon_client::visual_assets::GalleryScrollRoot>>();
        roots
            .single(world)
            .expect("exactly one gallery scroll root")
    };
    app.world_mut().entity_mut(root).insert(ComputedNode {
        size: Vec2::new(100.0, 100.0),
        content_size: Vec2::new(100.0, 300.0),
        ..ComputedNode::DEFAULT
    });
    app.insert_resource(AccumulatedMouseScroll {
        unit: MouseScrollUnit::Line,
        delta: Vec2::new(0.0, -1.0),
    });

    app.update();

    let scroll_position = app
        .world()
        .entity(root)
        .get::<ScrollPosition>()
        .expect("gallery root retains its scroll position");
    assert!(
        (scroll_position.y - 20.0).abs() < f32::EPSILON,
        "one line of input must move the gallery by 20 logical pixels"
    );
}

#[test]
fn presentation_spawns_the_title_mark_readable_title_and_counties_banner() {
    let _guard = bevy_app_test_guard();
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
    let _guard = bevy_app_test_guard();
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
fn story_banner_is_globally_below_the_readable_story_card_layer() {
    let _guard = bevy_app_test_guard();
    let mut app = visual_presentation_app(babylon_client::story::counties(), true);
    let world = app.world_mut();
    let mut banner_query =
        world.query_filtered::<&GlobalZIndex, With<babylon_client::visual_assets::StoryBanner>>();
    let banner_z = banner_query
        .single(world)
        .expect("story banner must declare an explicit global z-index")
        .0;
    let mut story_card_query = world.query_filtered::<
        Option<&GlobalZIndex>,
        With<babylon_client::ui::story_card::StoryCardText>,
    >();
    let story_card_z = story_card_query
        .single(world)
        .expect("exactly one readable story-card layer")
        .map_or(0, |z_index| z_index.0);

    assert!(
        banner_z < story_card_z,
        "story banner z-index {banner_z} must remain below story-card z-index {story_card_z}"
    );
}

#[test]
#[should_panic(expected = "no visual banner declared for story \"not-in-catalog\"")]
fn presentation_rejects_an_unknown_story_id() {
    let _guard = bevy_app_test_guard();
    let _app = visual_presentation_app(&UNKNOWN_STORY, true);
}
