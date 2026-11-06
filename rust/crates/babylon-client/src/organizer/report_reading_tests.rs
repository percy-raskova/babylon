//! Selected report identity, real glyphs and reading continuity.
use super::{
    tests, ActionButton, Destination, DispatchDestination, OrganizerAction,
    OrganizerEvidenceRequested, TextPart,
};
use crate::atlas::CountyAtlas;
use crate::map::SelectedCounty;
use crate::observer::ObserverSession;
use crate::observer_io::ObserverSet;
use crate::observer_ui::{ObserverCommand, ObserverFrame};
use crate::organizer::{OrganizerClient, OrganizerInspector};
use crate::production::PrimaryView;
use babylon_persistence::runtime_session::{OrganizerObservation, OrganizerReport};
use bevy::input_focus::InputFocus;
use bevy::prelude::*;

fn reports(client: &mut OrganizerClient) {
    let view = client.view.as_mut().expect("admitted view");
    view.workplace_partner_label = "Workplace Committee serving the eastern industrial district and its neighboring repair workplaces".into();
    view.observations = vec![
        OrganizerObservation {
            observation_id: [31; 32],
            actor_id: view.actor_id,
            subject_id: view.workplace_id,
            source_actor_id: view.workplace_partner_id,
            observed_period: 2,
            acquired_period: 3,
            receipt_id: Some([7; 32]),
            report: OrganizerReport::Work {
                performed_labor_hours: 12345,
                output_kg: 67890,
                previous_labor_hours: None,
                previous_output_kg: None,
            },
        },
        OrganizerObservation {
            observation_id: [32; 32],
            actor_id: view.actor_id,
            subject_id: view.workplace_id,
            source_actor_id: view.workplace_partner_id,
            observed_period: 3,
            acquired_period: 3,
            receipt_id: None,
            report: OrganizerReport::ReducedWork {
                previous_labor_hours: 12345,
                performed_labor_hours: 4567,
            },
        },
    ];
    view.total_observation_count = 2;
}

fn part(app: &mut App, selected: TextPart) -> Entity {
    let world = app.world_mut();
    world
        .query::<(Entity, &TextPart)>()
        .iter(world)
        .find_map(|(entity, part)| {
            (std::mem::discriminant(part) == std::mem::discriminant(&selected)).then_some(entity)
        })
        .expect("painted report part")
}

fn settle(app: &mut App) {
    for _ in 0..4 {
        app.update();
    }
}

#[test]
fn inquiry_dispatch_opens_its_exact_answer_beside_a_newer_automatic_report() {
    let (mut app, draft) = tests::admitted_scene_fixture();
    reports(&mut app.world_mut().resource_mut::<OrganizerClient>());
    settle(&mut app);
    let link = {
        let world = app.world_mut();
        world
            .query::<&ActionButton>()
            .iter(world)
            .find_map(|button| match button.0 {
                OrganizerAction::Follow(link)
                    if link.destination
                        == Destination::Detail(DispatchDestination::Report([31; 32])) =>
                {
                    Some(link)
                }
                _ => None,
            })
            .expect("actual dispatch report action")
    };
    let dispatch = part(&mut app, TextPart::Aftermath);
    let text = &app.world().get::<Text>(dispatch).expect("dispatch").0;
    assert!(
        text.contains("Output: 67,890 kg"),
        "acquired answer belongs in dispatch: {text}"
    );
    app.world_mut().write_message(OrganizerAction::Follow(link));
    settle(&mut app);
    let body = part(&mut app, TextPart::InspectorBody);
    let text = &app.world().get::<Text>(body).expect("report").0;
    assert!(
        text.starts_with("Work performed: 12,345 labor-hours. Output: 67,890 kg."),
        "{text}"
    );
    assert!(
        text.contains("Observed period 2") && text.contains("Received period 3"),
        "{text}"
    );
    assert!(
        text.contains(&"1f".repeat(32)) && text.contains(&"07".repeat(32)),
        "exact report and inquiry citations remain reachable"
    );
    assert!(
        !text.contains("4,567"),
        "newer automatic facts cannot replace requested facts"
    );
    assert_eq!(
        app.world()
            .resource::<OrganizerClient>()
            .selected_evidence_id(3),
        Some([31; 32])
    );
    app.world_mut()
        .write_message(OrganizerAction::CloseInspector);
    settle(&mut app);
    assert_eq!(app.world().resource::<OrganizerClient>().draft, draft);
}

fn assert_return_visible(app: &mut App, bounds: Rect) {
    let label = {
        let world = app.world_mut();
        world
            .query::<(&ActionButton, &Children)>()
            .iter(world)
            .find_map(|(button, children)| {
                (button.0 == OrganizerAction::CloseInspector).then_some(children[0])
            })
            .expect("fixed Return control")
    };
    tests::assert_glyphs_in(app, label, bounds);
}

#[derive(Clone, Copy, Debug)]
enum InterfaceSize {
    Standard,
    Larger,
}

fn measured_report(viewport: UVec2, size: InterfaceSize) -> App {
    use bevy::asset::AssetApp as _;
    let mut app = tests::measured_board(viewport, 1.0, matches!(size, InterfaceSize::Larger), true);
    app.init_asset::<Image>()
        .init_asset::<TextureAtlasLayout>()
        .add_systems(
            PostUpdate,
            bevy::ui::widget::text_system.after(bevy::ui::ui_layout_system),
        );
    crate::observer_ui::tests::install_resource_header_fixture(&mut app, viewport);
    app.add_message::<OrganizerAction>()
        .add_message::<ObserverCommand>()
        .add_systems(Update, super::actions.in_set(ObserverSet::Input))
        .configure_sets(Update, (ObserverSet::Input, ObserverSet::Paint).chain());
    reports(&mut app.world_mut().resource_mut::<OrganizerClient>());
    app.world_mut()
        .resource_mut::<OrganizerClient>()
        .open_evidence_report([31; 32], 3);
    app.world_mut()
        .write_message(OrganizerAction::Inspect(OrganizerInspector::Evidence));
    settle(&mut app);
    app
}

#[test]
fn report_answers_render_initially_and_last_evidence_is_reachable_at_actual_interface_sizes() {
    for (viewport, size, scale) in [
        (UVec2::new(1366, 768), InterfaceSize::Standard, 1.0_f32),
        (UVec2::new(1366, 768), InterfaceSize::Larger, 1.15),
        (UVec2::new(1920, 1080), InterfaceSize::Standard, 1.25),
        (UVec2::new(1920, 1080), InterfaceSize::Larger, 1.4375),
    ] {
        let mut app = measured_report(viewport, size);
        assert_eq!(
            app.world().resource::<UiScale>().0.to_bits(),
            scale.to_bits()
        );
        let title = part(&mut app, TextPart::InspectorTitle);
        let body = part(&mut app, TextPart::InspectorBody);
        let reading = app
            .world()
            .get::<ChildOf>(body)
            .expect("reading region")
            .parent();
        let title_text = &app.world().get::<Text>(title).expect("title").0;
        assert!(
            title_text.contains("Work and output"),
            "selected kind: {title_text}"
        );
        let text = &app.world().get::<Text>(body).expect("answer").0;
        assert!(
            text.starts_with("Work performed: 12,345 labor-hours. Output: 67,890 kg."),
            "{text}"
        );
        let viewport_rect = Rect::from_corners(Vec2::ZERO, viewport.as_vec2());
        tests::assert_glyphs_in(&app, title, viewport_rect);
        let bounds = tests::workspace_rect(&app, reading).intersect(viewport_rect);
        let glyphs = tests::glyph_rects(&app, body);
        assert!(
            !glyphs.is_empty(),
            "the numerical answer renders real glyphs"
        );
        for glyph in glyphs.iter().take(53) {
            assert!(
                (glyph.intersect(bounds).size() - glyph.size())
                    .abs()
                    .max_element()
                    < 1.1,
                "initial answer clipped at {viewport:?}, size={size:?}: {glyph:?}, {bounds:?}"
            );
        }
        app.world_mut()
            .get_mut::<ScrollPosition>(reading)
            .expect("scroll")
            .0
            .y = f32::MAX;
        settle(&mut app);
        let last = tests::glyph_rects(&app, body)
            .last()
            .copied()
            .expect("final evidence glyph");
        assert!(
            (last.intersect(bounds).size() - last.size())
                .abs()
                .max_element()
                < 1.1,
            "final evidence unreachable: {last:?} in {bounds:?}"
        );
        assert_return_visible(&mut app, viewport_rect);
        app.world_mut()
            .write_message(OrganizerAction::PreviousEvidence);
        settle(&mut app);
        assert_eq!(
            app.world()
                .resource::<OrganizerClient>()
                .selected_evidence_id(3),
            Some([32; 32])
        );
        assert_eq!(
            app.world()
                .get::<ScrollPosition>(reading)
                .expect("reset reading")
                .0
                .y,
            0.0
        );
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(body));
    }
}

#[test]
fn world_earned_report_summary_opens_the_ordinary_evidence_reader_and_hides_stale_facts() {
    let mut app = tests::measured_board(UVec2::new(1366, 768), 1.0, false, false);
    crate::observer_ui::tests::install_world_report_fixture(&mut app, UVec2::new(1366, 768));
    app.add_observer(super::open_evidence);
    reports(&mut app.world_mut().resource_mut::<OrganizerClient>());
    *app.world_mut().resource_mut::<PrimaryView>() = PrimaryView::Map;
    let county = app.world().resource::<CountyAtlas>().index_of_fips("26163");
    app.world_mut().resource_mut::<SelectedCounty>().0 = county;
    settle(&mut app);
    let summary = {
        let world = app.world_mut();
        world
            .query::<(Entity, &Text)>()
            .iter(world)
            .find_map(|(entity, text)| {
                text.0
                    .starts_with("Earned workplace reports")
                    .then_some(entity)
            })
            .expect("actual World development text reads earned organizer knowledge")
    };
    let text = &app.world().get::<Text>(summary).expect("World summary").0;
    assert!(text.contains("Work and output · observed P2, received P3 · Requested inquiry"));
    assert!(text.contains("Reduced work · observed P3, received P3 · Automatic report"));
    assert!(text.contains("67,890 kg") && text.contains("4,567 labor-hours"));
    assert!(text.contains("Source: Workplace Committee"));
    assert!(
        app.world().resource::<ObserverFrame>().0.is_none(),
        "no broad production source needed"
    );
    let draft = app.world().resource::<OrganizerClient>().draft.clone();
    app.world_mut().resource_mut::<ObserverSession>().playing = true;
    app.world_mut().trigger(OrganizerEvidenceRequested);
    settle(&mut app);
    assert!(!app.world().resource::<ObserverSession>().playing);
    assert_eq!(
        app.world().resource::<OrganizerClient>().inspector,
        OrganizerInspector::Evidence
    );
    assert_eq!(app.world().resource::<OrganizerClient>().draft, draft);
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .viewed_tick = 2;
    settle(&mut app);
    let text = &app.world().get::<Text>(summary).expect("World summary").0;
    assert!(
        !text.contains("67,890") && !text.contains("4,567"),
        "current knowledge cannot leak to historical World: {text}"
    );
}
