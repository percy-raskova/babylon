//! Native regressions measured with shipped fonts and the production viewport fit.

use super::super::board::DecisionDeck;
use super::super::scene::OrganizerSubject;
use super::SceneDetail;
use super::TextPart;
use bevy::prelude::*;

use super::super::board::{ChoicePair, ComparisonCard};
use super::super::OrganizerClient;
use super::{tests, SceneRoot};
use crate::observer_ui::{ObserverFontRole, ObserverViewport};
use crate::production::PrimaryView;

const FITS: [(UVec2, bool, f32); 4] = [
    (UVec2::new(1366, 768), false, 1.0),
    (UVec2::new(1366, 768), true, 1.15),
    (UVec2::new(1920, 1080), false, 1.25),
    (UVec2::new(1920, 1080), true, 1.4375),
];

fn measured(viewport: UVec2, larger: bool, long: bool) -> (App, Entity) {
    use bevy::asset::AssetApp as _;
    let mut app = tests::measured_board(viewport, 1.0, larger, long);
    {
        let mut client = app.world_mut().resource_mut::<OrganizerClient>();
        let view = client.view.as_mut().expect("admitted organizer");
        view.available_hours = 16;
        view.contact_hours = 8;
        // Current Michigan fixture labels (organizer_content.rs).
        view.workplace_label = if long {
            "Wayne County repair and maintenance workplace committee serving the eastern industrial district"
        } else {
            "Wayne metal-parts workplace"
        }.into();
        view.workplace_partner_label = if long {
            "Workplace Committee serving the eastern industrial district and its neighboring repair workplaces"
        } else {
            "Wayne Metal-Parts Workplace Committee"
        }.into();
        view.neighborhood_partner_label = "Wayne Neighborhood Contact Group".into();
    }
    app.init_asset::<Image>()
        .init_asset::<TextureAtlasLayout>()
        .add_systems(
            PostUpdate,
            bevy::ui::widget::text_system.after(bevy::ui::ui_layout_system),
        );
    let (body, display) = {
        let world = app.world_mut();
        let fonts = world
            .query::<(&ObserverFontRole, &TextFont)>()
            .iter(world)
            .collect::<Vec<_>>();
        (
            fonts
                .iter()
                .find(|(role, _)| matches!(role, ObserverFontRole::Body))
                .expect("body")
                .1
                .font
                .clone(),
            fonts
                .iter()
                .find(|(role, _)| matches!(role, ObserverFontRole::Display))
                .expect("display")
                .1
                .font
                .clone(),
        )
    };
    let means = crate::observer_ui::tests::install_resource_header_fixture(&mut app, viewport);
    {
        let world = app.world_mut();
        for (role, mut font) in world
            .query::<(&ObserverFontRole, &mut TextFont)>()
            .iter_mut(world)
        {
            if matches!(role, ObserverFontRole::Display) {
                font.weight = FontWeight::SEMIBOLD;
            }
            font.font = match role {
                ObserverFontRole::Display => display.clone(),
                ObserverFontRole::Exact => Handle::default().into(),
                _ => body.clone(),
            };
        }
    }
    for _ in 0..8 {
        app.update();
    }
    (app, means)
}

#[test]
fn rendered_choices_expose_both_actual_terms_at_all_native_fits() {
    for (viewport, larger, scale) in FITS {
        for long in [false, true] {
            let (mut app, _) = measured(viewport, larger, long);
            assert_eq!(app.world().resource::<UiScale>().0, scale);
            let (pair, cards) = {
                let world = app.world_mut();
                let pair = world
                    .query_filtered::<Entity, With<ChoicePair>>()
                    .single(world)
                    .expect("one reading");
                let cards = world
                    .query_filtered::<(Entity, &Children), With<ComparisonCard>>()
                    .iter(world)
                    .map(|(entity, children)| (entity, children.iter().collect::<Vec<_>>()))
                    .collect::<Vec<_>>();
                (pair, cards)
            };
            assert_eq!(cards.len(), 2);
            let deck = app
                .world()
                .get::<ChildOf>(pair)
                .expect("comparison paper")
                .parent();
            let deck_bounds = tests::workspace_rect(&app, deck)
                .intersect(Rect::from_corners(Vec2::ZERO, viewport.as_vec2()));
            let mut descendants = vec![deck];
            while let Some(entity) = descendants.pop() {
                if let Some(children) = app.world().get::<Children>(entity) {
                    descendants.extend(children.iter());
                }
                if app
                    .world()
                    .get::<Text>(entity)
                    .is_some_and(|text| !text.0.is_empty())
                {
                    tests::assert_glyphs_in(&app, entity, deck_bounds);
                }
            }
            let bounds = tests::workspace_rect(&app, pair)
                .intersect(Rect::from_corners(Vec2::ZERO, viewport.as_vec2()));
            let scene = {
                let world = app.world_mut();
                world
                    .query_filtered::<Entity, With<SceneRoot>>()
                    .single(world)
                    .expect("actual scene region")
            };
            let scene = tests::workspace_rect(&app, scene);
            assert!(
                scene.height() > 0.0 && scene.max.y < bounds.min.y,
                "map leaves room for the full decision"
            );
            assert_eq!(
                app.world().resource::<ObserverViewport>().0,
                Some(scene),
                "camera fits the actual scene region"
            );
            for (card, lines) in cards {
                let visible = bounds.intersect(tests::workspace_rect(&app, card));
                assert_eq!(
                    lines.len(),
                    3,
                    "status, actual heading and complete factual terms"
                );
                for line in lines {
                    tests::assert_glyphs_in(&app, line, visible);
                }
            }
            crate::observer_map3d::assert_paper_blocks_navigation(&mut app, bounds.center());
        }
    }
}

#[test]
fn rendered_focused_period_stays_clear_of_resources_at_all_native_fits() {
    for (viewport, larger, scale) in FITS {
        let (mut app, means) = measured(viewport, larger, false);
        *app.world_mut().resource_mut::<PrimaryView>() = PrimaryView::Map;
        let clock = crate::observer_ui::tests::focus_clock(&mut app);
        for _ in 0..4 {
            app.update();
        }
        let outline = app
            .world()
            .get::<Outline>(clock)
            .expect("actual focus border");
        let (Val::Px(width), Val::Px(offset)) = (outline.width, outline.offset) else {
            panic!("pixel focus border");
        };
        let clock_bounds = tests::workspace_rect(&app, clock).inflate((width + offset) * scale);
        tests::assert_glyphs_in(&app, clock, tests::workspace_rect(&app, clock));
        let resources = tests::glyph_rects(&app, means);
        assert_ne!(resources, []);
        assert!(
            resources
                .iter()
                .all(|glyph| glyph.min.y >= clock_bounds.max.y),
            "focused period {clock_bounds:?} crosses resource glyph {:?}",
            resources
                .iter()
                .find(|glyph| glyph.min.y < clock_bounds.max.y)
        );
        let world = app
            .world()
            .resource::<ObserverViewport>()
            .0
            .expect("fitted world");
        assert!(resources.iter().all(|glyph| glyph.max.y < world.min.y));
    }
}

#[test]
fn national_allocation_fields_and_choices_leave_the_subject_visible_at_all_four_fits() {
    use super::super::amount_editor::AmountField;
    use babylon_persistence::runtime_session::OrganizerChoice;
    for (viewport, larger, scale) in FITS {
        let (mut app, _) = measured(viewport, larger, true);
        tests::install_national_opening(&mut app);
        for choice in [
            OrganizerChoice::Collect,
            OrganizerChoice::LocalAid,
            OrganizerChoice::RemoteAid,
        ] {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.draft.as_mut().expect("draft").choice = choice;
            client.selected_subject = client
                .view
                .as_ref()
                .and_then(|v| v.aid_partners.last())
                .map(|p| OrganizerSubject::AidPartner(p.actor_id));
            for _ in 0..8 {
                app.update();
            }
            assert_eq!(app.world().resource::<UiScale>().0, scale);
            let world = app.world_mut();
            let viewport_bounds = Rect::from_corners(Vec2::ZERO, viewport.as_vec2());
            let fields = world
                .query::<(Entity, &AmountField, &Children, &Node)>()
                .iter(world)
                .filter(|(_, _, _, n)| n.display != Display::None)
                .map(|(e, f, c, _)| (e, *f, c[0]))
                .collect::<Vec<_>>();
            assert_eq!(
                fields.len(),
                if choice == OrganizerChoice::Collect {
                    1
                } else {
                    2
                }
            );
            let deck = world
                .query_filtered::<Entity, With<DecisionDeck>>()
                .single(world)
                .expect("deck");
            let scene = world
                .query_filtered::<Entity, With<SceneRoot>>()
                .single(world)
                .expect("map");
            let cards = world
                .query_filtered::<(Entity, &Children), With<ComparisonCard>>()
                .iter(world)
                .map(|(e, c)| (e, c.iter().collect::<Vec<_>>()))
                .collect::<Vec<_>>();
            let means = world
                .query::<(Entity, &TextPart)>()
                .iter(world)
                .find_map(|(e, p)| matches!(p, TextPart::Means).then_some(e))
                .expect("organization means");
            let subject = world
                .query_filtered::<Entity, With<SceneDetail>>()
                .iter(world)
                .find(|e| {
                    world
                        .get::<Text>(*e)
                        .is_some_and(|t| t.contains("Cook Independent"))
                })
                .expect("selected national group");
            let deck_bounds = tests::workspace_rect(&app, deck).intersect(viewport_bounds);
            tests::assert_glyphs_in(&app, subject, viewport_bounds);
            if let Some(clip) = app.world().get::<CalculatedClip>(subject) {
                assert!(
                    tests::glyph_rects(&app, subject)
                        .iter()
                        .all(|g| clip.contains_point(g.center())),
                    "selected group must remain visible in its scrolling dossier"
                );
            }
            tests::assert_glyphs_in(&app, means, viewport_bounds);
            assert!(app
                .world()
                .get::<Text>(means)
                .expect("treasury")
                .contains("$1.00"));
            for (e, field, text) in fields {
                let bounds = tests::workspace_rect(&app, e).intersect(deck_bounds);
                assert!(field.applies(choice));
                tests::assert_glyphs_in(&app, text, bounds);
                crate::observer_map3d::assert_paper_blocks_navigation(&mut app, bounds.center());
            }
            for (e, lines) in cards {
                let bounds = tests::workspace_rect(&app, e).intersect(deck_bounds);
                for line in lines {
                    tests::assert_glyphs_in(&app, line, bounds);
                }
            }
            let region = tests::workspace_rect(&app, scene);
            assert!(region.height() > 0.0 && region.max.y < deck_bounds.min.y);
            assert_eq!(app.world().resource::<ObserverViewport>().0, Some(region));
        }
    }
}
