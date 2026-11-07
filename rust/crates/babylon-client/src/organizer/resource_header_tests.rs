//! Real-font resource readings across workspace, World and modal inspectors.

use babylon_persistence::runtime_session::OrganizerSnapshot;
use bevy::prelude::*;

use crate::observer_focus::ObserverFocusTarget;
use crate::organizer::{OrganizerClient, OrganizerInspector};
use crate::production::PrimaryView;

use super::tests;
use super::{OrganizerRoot, TextPart};

#[derive(Clone, Copy)]
enum InterfaceSize {
    Standard,
    Larger,
}

fn measured_resource_board(
    viewport: UVec2,
    size: InterfaceSize,
    expected_scale: f32,
) -> (App, Entity, Entity) {
    use bevy::asset::AssetApp as _;
    let mut app =
        tests::measured_board(viewport, 1.0, matches!(size, InterfaceSize::Larger), false);
    // The base fixture measures layout; glyph checks also need Bevy's text renderer,
    // as in the existing relationship glyph fixture.
    app.init_asset::<Image>()
        .init_asset::<TextureAtlasLayout>()
        .add_systems(
            PostUpdate,
            bevy::ui::widget::text_system.after(bevy::ui::ui_layout_system),
        );
    let captured: OrganizerSnapshot = serde_json::from_str(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../babylon-persistence/tests/fixtures/national_organizer_opening_v18.json"
    )))
    .expect("captured national resources");
    {
        let mut client = app.world_mut().resource_mut::<OrganizerClient>();
        let view = client.view.as_mut().expect("admitted view");
        view.available_hours = u64::MAX;
        let actor = view.actor_id;
        let period = view.period;
        let mut collection = captured.collection.expect("captured collective account");
        collection.actor_id = actor;
        collection.period = period;
        collection.organization_cash_micros = i128::MIN;
        client.collection = Some(collection);
        client.aid = captured.aid;
        for row in &mut client.aid {
            row.period = period;
            let food = row.food.as_mut().expect("national food offer");
            food.time = Some(babylon_persistence::runtime_session::OrganizerAidTime {
                period,
                labor_unit_id: food.labor_unit_id,
                remaining_hours: u64::MAX,
            });
        }
    }
    let shared = crate::observer_ui::tests::install_resource_header_fixture(&mut app, viewport);
    let means = {
        let world = app.world_mut();
        world
            .query::<(Entity, &TextPart)>()
            .iter(world)
            .find_map(|(entity, part)| matches!(part, TextPart::Means).then_some(entity))
            .expect("organizer resource header")
    };
    let body_font = app
        .world()
        .get::<TextFont>(means)
        .expect("real body font")
        .font
        .clone();
    {
        let world = app.world_mut();
        for mut font in world.query::<&mut TextFont>().iter_mut(world) {
            font.font = body_font.clone();
        }
    }
    for _ in 0..4 {
        app.update();
    }
    assert_eq!(
        app.world().resource::<UiScale>().0.to_bits(),
        expected_scale.to_bits(),
        "actual viewport fitting applies the Larger setting once"
    );
    (app, shared, means)
}

fn assert_inspector_resources(app: &mut App, inspector_means: Entity) {
    for inspector in [OrganizerInspector::Evidence, OrganizerInspector::Review] {
        app.world_mut().resource_mut::<OrganizerClient>().inspector = inspector;
        for _ in 0..4 {
            app.update();
        }
        let shield = app
            .world()
            .get::<ChildOf>(inspector_means)
            .expect("modal shield")
            .parent();
        tests::assert_glyphs_in(app, inspector_means, tests::workspace_rect(app, shield));
        assert!(
            app.world()
                .get::<Text>(inspector_means)
                .expect("inspector resources")
                .0
                .contains("Collective cash -$170,141"),
            "current resources stay visible in {inspector:?}"
        );
        let root = {
            let world = app.world_mut();
            world
                .query_filtered::<&Node, With<OrganizerRoot>>()
                .single(world)
                .expect("one workspace")
        };
        assert_eq!(
            root.display,
            Display::None,
            "workspace controls stay hidden behind the existing modal"
        );
        assert!(
            app.world()
                .get::<ObserverFocusTarget>(inspector_means)
                .is_none(),
            "resource copy cannot become an extra modal control"
        );
    }
}

#[test]
fn native_resource_headers_keep_long_current_values_visible_across_views() {
    for (viewport, size, expected_scale) in [
        (UVec2::new(1366, 768), InterfaceSize::Standard, 1.0),
        (UVec2::new(1366, 768), InterfaceSize::Larger, 1.15),
        (UVec2::new(1920, 1080), InterfaceSize::Standard, 1.25),
        (UVec2::new(1920, 1080), InterfaceSize::Larger, 1.4375),
    ] {
        let (mut app, shared, means) = measured_resource_board(viewport, size, expected_scale);
        for view in [
            PrimaryView::Organizer,
            PrimaryView::Map,
            PrimaryView::Production,
        ] {
            *app.world_mut().resource_mut::<PrimaryView>() = view;
            for _ in 0..4 {
                app.update();
            }
            let reading = if view == PrimaryView::Organizer {
                means
            } else {
                shared
            };
            let parent = app
                .world()
                .get::<ChildOf>(reading)
                .expect("resource row")
                .parent();
            assert!(!tests::glyph_rects(&app, reading).is_empty(), "resource header in {view:?} must render glyphs; text {:?}; computed {:?}; parent {:?}", app.world().get::<Text>(reading), app.world().get::<ComputedNode>(reading), app.world().get::<ComputedNode>(parent));
            tests::assert_glyphs_in(&app, reading, tests::workspace_rect(&app, parent));
            let panel = if view == PrimaryView::Organizer {
                parent
            } else {
                app.world()
                    .get::<ChildOf>(parent)
                    .expect("shared HUD panel")
                    .parent()
            };
            tests::assert_glyphs_in(&app, reading, tests::workspace_rect(&app, panel));
            tests::assert_glyphs_in(
                &app,
                reading,
                Rect::from_corners(Vec2::ZERO, viewport.as_vec2()),
            );
            let text = app
                .world()
                .get::<Text>(reading)
                .expect("painted authoritative resources");
            assert!(
                text.0
                    .contains("-$170,141,183,460,469,231,731,687,303,715,884.105728"),
                "exact cash is visible in {view:?}: {}",
                text.0
            );
            assert!(
                text.0.contains("18,446,744,073,709,551,615"),
                "physical hours stay grouped in {view:?}"
            );
            assert!(
                text.0.contains("closed P3") && text.0.contains("next period unknown"),
                "past supply never becomes future capacity"
            );
        }
        *app.world_mut().resource_mut::<PrimaryView>() = PrimaryView::Organizer;
        let inspector_means = {
            let world = app.world_mut();
            world
                .query::<(Entity, &TextPart)>()
                .iter(world)
                .find_map(|(entity, part)| {
                    matches!(part, TextPart::InspectorMeans).then_some(entity)
                })
                .expect("resource reading belongs to the existing modal shield")
        };
        assert_inspector_resources(&mut app, inspector_means);
        app.world_mut().resource_mut::<OrganizerClient>().inspector = OrganizerInspector::Closed;
        *app.world_mut().resource_mut::<PrimaryView>() = PrimaryView::Production;
        for _ in 0..4 {
            app.update();
        }
        // Only the organizer resource changes: shared shell must repaint without a session change.
        app.world_mut()
            .resource_mut::<OrganizerClient>()
            .collection
            .as_mut()
            .expect("owned account")
            .organization_cash_micros = 0;
        app.update();
        app.update();
        assert!(
            app.world()
                .get::<Text>(shared)
                .expect("repainted shared reading")
                .0
                .contains("Collective cash $0.00"),
            "client-only balance updates repaint World/Evidence chrome"
        );
    }
}
