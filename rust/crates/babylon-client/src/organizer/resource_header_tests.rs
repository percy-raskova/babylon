//! Real-font resource readings across workspace, World and modal inspectors.

use crate::observer::ObserverSession;
use crate::observer_io::ObserverSet;
use babylon_persistence::runtime_session::OrganizerSnapshot;
use bevy::prelude::*;

use crate::observer_focus::ObserverFocusTarget;
use crate::observer_ui::ObserverViewport;
use crate::organizer::{OrganizerClient, OrganizerInspector};
use crate::production::PrimaryView;

use super::super::resource_hud::ResourceChip;
use super::tests;
use super::{OrganizerRoot, TextPart};

pub(super) fn chip_entities(app: &App, hud: Entity) -> Vec<Entity> {
    let mut texts = Vec::new();
    for card in app.world().get::<Children>(hud).expect("chip cards") {
        for child in app.world().get::<Children>(*card).expect("chip contents") {
            if app.world().get::<ResourceChip>(*child).is_some() {
                texts.push(*child);
            }
        }
    }
    assert_eq!(
        texts.len(),
        3,
        "every view retains three labeled resource chips"
    );
    texts
}

pub(super) fn resource_text(app: &App, hud: Entity) -> String {
    let mut text = String::new();
    for entity in chip_entities(app, hud) {
        text.push_str(&app.world().get::<Text>(entity).expect("chip label").0);
        for child in app
            .world()
            .get::<Children>(entity)
            .expect("amount and period spans")
        {
            text.push_str(&app.world().get::<TextSpan>(*child).expect("chip span").0);
        }
        text.push('\n');
    }
    text
}

pub(super) fn assert_chip_glyphs_in(app: &App, hud: Entity, bounds: Rect) {
    for chip in chip_entities(app, hud) {
        assert!(
            !tests::glyph_rects(app, chip).is_empty(),
            "each resource chip renders actual glyphs"
        );
        tests::assert_glyphs_in(app, chip, bounds);
        let card = app
            .world()
            .get::<ChildOf>(chip)
            .expect("chip card")
            .parent();
        tests::assert_glyphs_in(app, chip, tests::workspace_rect(app, card));
    }
}

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
        "/../babylon-persistence/tests/fixtures/national_organizer_opening_v19.json"
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
        .get::<TextFont>(chip_entities(&app, means)[0])
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
        assert_chip_glyphs_in(app, inspector_means, tests::workspace_rect(app, shield));
        assert!(
            resource_text(app, inspector_means).contains("Cash  -$170,141"),
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
            assert_chip_glyphs_in(&app, reading, tests::workspace_rect(&app, parent));
            let panel = if view == PrimaryView::Organizer {
                parent
            } else {
                app.world()
                    .get::<ChildOf>(parent)
                    .expect("shared HUD panel")
                    .parent()
            };
            assert_chip_glyphs_in(&app, reading, tests::workspace_rect(&app, panel));
            assert_chip_glyphs_in(
                &app,
                reading,
                Rect::from_corners(Vec2::ZERO, viewport.as_vec2()),
            );
            let text = resource_text(&app, reading);
            assert!(
                text.contains("-$170,141,183,460,469,231,731,687,303,715,884.105728"),
                "exact cash is visible in {view:?}: {text}"
            );
            assert!(
                text.contains("18,446,744,073,709,551,615"),
                "physical hours stay grouped in {view:?}"
            );
            assert!(
                text.contains("closed P3") && text.contains("next period unknown"),
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
            resource_text(&app, shared).contains("Cash  $0.00"),
            "client-only balance updates repaint World/Evidence chrome"
        );
    }
}

#[test]
fn actual_processing_caption_and_rightmost_advance_fit_both_header_sizes() {
    use crate::observer_progress::OperationProgress;
    use crate::organizer::processing_feedback::ProcessingCaption;
    for (viewport, size, expected_scale) in [
        (UVec2::new(1366, 768), InterfaceSize::Standard, 1.0),
        (UVec2::new(1366, 768), InterfaceSize::Larger, 1.15),
        (UVec2::new(1920, 1080), InterfaceSize::Standard, 1.25),
        (UVec2::new(1920, 1080), InterfaceSize::Larger, 1.4375),
    ] {
        let (mut app, _, _) = measured_resource_board(viewport, size, expected_scale);
        app.init_resource::<OperationProgress>().add_systems(
            Update,
            crate::observer_progress::track.before(ObserverSet::Paint),
        );
        app.world_mut()
            .resource_mut::<ObserverSession>()
            .set_organizer_control_pending(true);
        for view in [
            PrimaryView::Organizer,
            PrimaryView::Map,
            PrimaryView::Production,
        ] {
            *app.world_mut().resource_mut::<PrimaryView>() = view;
            for _ in 0..4 {
                app.update();
            }
            let world = app.world_mut();
            let captions: Vec<_> = world
                .query_filtered::<(Entity, &ComputedNode), With<ProcessingCaption>>()
                .iter(world)
                .filter_map(|(entity, computed)| (computed.size().x > 0.0).then_some(entity))
                .collect();
            assert_eq!(
                captions.len(),
                1,
                "one visible operation caption in {view:?}"
            );
            let caption = captions[0];
            let parent = app
                .world()
                .get::<ChildOf>(caption)
                .expect("progress region")
                .parent();
            tests::assert_glyphs_in(&app, caption, tests::workspace_rect(&app, parent));
            tests::assert_glyphs_in(
                &app,
                caption,
                Rect::from_corners(Vec2::ZERO, viewport.as_vec2()),
            );
            let world = app.world_mut();
            let advance = world
                .query::<(Entity, &Name, &ComputedNode)>()
                .iter(world)
                .find_map(|(entity, name, computed)| {
                    (name.as_str() == "wayne.advance" && computed.size().x > 0.0).then_some(entity)
                })
                .expect("the shared header retains Advance while processing");
            let bounds = tests::workspace_rect(&app, advance);
            assert!(
                bounds.max.x <= viewport.as_vec2().x,
                "rightmost Advance stays in the viewport: {bounds:?}"
            );
            let header = app
                .world()
                .get::<ChildOf>(advance)
                .expect("header action row")
                .parent();
            assert_eq!(
                app.world()
                    .get::<Children>(header)
                    .expect("header actions")
                    .last(),
                Some(&advance),
                "Advance remains the far-right header action"
            );
        }
    }
}

#[test]
fn shared_status_help_and_disabled_reasons_keep_readable_glyphs_in_the_header() {
    use crate::observer_ui::ObserverUiState;
    for (viewport, size, scale) in [
        (UVec2::new(1366, 768), InterfaceSize::Standard, 1.0),
        (UVec2::new(1366, 768), InterfaceSize::Larger, 1.15),
        (UVec2::new(1920, 1080), InterfaceSize::Standard, 1.25),
        (UVec2::new(1920, 1080), InterfaceSize::Larger, 1.4375),
    ] {
        let (mut app, shared, _) = measured_resource_board(viewport, size, scale);
        let status = crate::observer_ui::tests::resource_header_status(&mut app);
        for phase in ["current", "history", "pending", "closing"] {
            prepare_header_status(&mut app, phase);
            for (view, archive) in [
                (PrimaryView::Map, false),
                (PrimaryView::Production, false),
                (PrimaryView::Map, true),
            ] {
                *app.world_mut().resource_mut::<PrimaryView>() = view;
                app.world_mut()
                    .resource_mut::<ObserverUiState>()
                    .archive_open = archive;
                for _ in 0..4 {
                    app.update();
                }
                let expected = crate::observer_controls::turn_presentation(
                    app.world().resource::<ObserverSession>(),
                )
                .status;
                assert_eq!(app.world().get::<Text>(status).expect("complete status copy").0, expected,
                    "layout must retain the full {phase} help/reason in {view:?}, archive={archive}");
                let row = app
                    .world()
                    .get::<ChildOf>(status)
                    .expect("shared resource/status row")
                    .parent();
                let row_bounds = tests::workspace_rect(&app, row);
                tests::assert_glyphs_in(&app, status, row_bounds);
                let status_bounds = tests::workspace_rect(&app, status);
                assert!(status_bounds.width() > status_bounds.height(),
                    "{phase} status must remain a readable block, not a one-character column: {status_bounds:?}");
                assert_chip_glyphs_in(&app, shared, row_bounds);
                assert!(
                    tests::workspace_rect(&app, shared).max.x <= status_bounds.min.x,
                    "status must not overlap exact resource readings"
                );
                let world = app.world().resource::<ObserverViewport>();
                assert!(
                    tests::glyph_rects(&app, status)
                        .iter()
                        .all(|glyph| glyph.max.y < world.0.expect("current world viewport").min.y),
                    "the complete status must stay above the game view"
                );
            }
        }
    }
}

fn prepare_header_status(app: &mut App, phase: &str) {
    let mut session = app.world_mut().resource_mut::<ObserverSession>();
    match phase {
        "current" => {}
        "history" => {
            session.inspect_tick(2);
            let context = session.context();
            assert!(
                session.installed(&context),
                "the historical reading installs before its reason is measured"
            );
        }
        "pending" => {
            let live = session.durable_tick;
            session.inspect_tick(live);
            let context = session.context();
            assert!(
                session.installed(&context),
                "the live reading installs before one advance"
            );
            assert!(
                session.begin_advance().is_some(),
                "the pending reason belongs to an actual accepted client request"
            );
        }
        "closing" => session.quit_requested = true,
        _ => unreachable!("the fixture declares each lifecycle phase explicitly"),
    }
}
