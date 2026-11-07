//! Selected report identity, real glyphs and reading continuity.
use super::Scope;
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
        !text.contains(&"1f".repeat(32)) && !text.contains(&"07".repeat(32)),
        "technical locators stay out of the report reading"
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
            .find_map(|(entity, text)| text.0.starts_with("Earned reports").then_some(entity))
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

#[derive(Resource, Default)]
struct Requested(Option<u64>);

#[test]
fn disclosed_partner_report_routes_to_that_organization_and_withholding_keeps_scene_nodes() {
    use crate::organizer::scene::{OrganizerScene, OrganizerSubject};
    use crate::organizer::ui::{OrganizerArchiveRequested, OrganizerArchiveTarget};
    use babylon_persistence::runtime_session::OrganizerSnapshot;
    let captured: OrganizerSnapshot = serde_json::from_str(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../babylon-persistence/tests/fixtures/national_organizer_pending_v18.json"
    )))
    .expect("actual pending national disclosure");
    let actor = captured.view.aid_partners[1].actor_id;
    let mut report = captured
        .view
        .observations
        .iter()
        .find(|r| r.subject_id == actor && r.observed_period == 1)
        .expect("real shared report")
        .clone();
    let scene = OrganizerScene::from_disclosure(&captured.view, &captured.body);
    let mut withheld = captured.view.clone();
    withheld.observations.retain(|r| r.subject_id != actor);
    withheld.total_observation_count =
        u32::try_from(withheld.observations.len()).expect("bounded observations");
    let private = OrganizerScene::from_disclosure(&withheld, &captured.body);
    assert_eq!(scene, private);
    assert_eq!(
        scene
            .nodes
            .iter()
            .filter(|n| n.subject == OrganizerSubject::AidPartner(actor))
            .count(),
        1
    );
    let (mut app, _) = tests::admitted_scene_fixture();
    app.init_resource::<Requested>().add_observer(
        |event: On<OrganizerArchiveRequested>, mut request: ResMut<Requested>| {
            if let OrganizerArchiveTarget::PartnerOrganization(id) = event.target {
                request.0 = Some(id);
            }
        },
    );
    {
        let mut client = app.world_mut().resource_mut::<OrganizerClient>();
        let view = client.view.as_mut().expect("admitted identity");
        report.actor_id = view.actor_id;
        view.aid_partners = captured.view.aid_partners;
        view.observations.push(report.clone());
        assert!(client.lawful_evidence(report.observation_id, 0).is_none());
        assert!(client.open_evidence_report(report.observation_id, 3));
        client.inspector = OrganizerInspector::Evidence;
    }
    app.world_mut()
        .write_message(OrganizerAction::ArchiveReport);
    settle(&mut app);
    assert_eq!(app.world().resource::<Requested>().0, Some(actor));
}

#[test]
fn partner_comparison_requires_a_prior_acquired_topic_for_the_same_reader() {
    use babylon_persistence::runtime_session::{
        OrganizerPartnerFacts, OrganizerReport, OrganizerSnapshot,
    };
    let snapshot: OrganizerSnapshot = serde_json::from_str(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../babylon-persistence/tests/fixtures/national_organizer_pending_v18.json"
    )))
    .expect("actual national disclosure");
    let mut view = snapshot.view;
    let prior = view
        .observations
        .iter()
        .find(|r| {
            matches!(
                r.report,
                OrganizerReport::Partner {
                    facts: OrganizerPartnerFacts::FoodProvision { .. },
                    ..
                }
            )
        })
        .expect("first completed food report")
        .clone();
    assert!(super::presentation::observation(&view, &prior, 1)
        .contains("Earlier comparable report unknown"));
    let mut current = prior.clone();
    current.observed_period = 2;
    current.acquired_period = 2;
    let detail = |view: &_| super::presentation::observation(view, &current, 2);
    view.observations = vec![prior.clone()];
    assert!(detail(&view).contains("Earlier shared report P1"));
    view.observations[0].acquired_period = 3;
    assert!(detail(&view).contains("Earlier comparable report unknown"));
    view.observations[0] = prior;
    view.observations[0].actor_id += 1;
    assert!(detail(&view).contains("Earlier comparable report unknown"));
}

#[test]
fn scoped_opening_dossier_selects_only_the_known_subject_and_world_names_its_scope() {
    use crate::organizer::scene::OrganizerSubject;
    use babylon_persistence::runtime_session::OrganizerSnapshot;
    use bevy::ecs::system::RunSystemOnce;
    let captured: OrganizerSnapshot = serde_json::from_str(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../babylon-persistence/tests/fixtures/national_organizer_opening_v18.json"
    )))
    .expect("actual opening disclosure");
    let partners = captured.view.aid_partners.clone();
    let workplace = captured.view.workplace_id;
    let committee = captured.view.workplace_partner_id;
    let (mut app, _) = tests::admitted_scene_fixture();
    let mut session = app.world_mut().resource_mut::<ObserverSession>();
    session.viewed_tick = 0;
    session.durable_tick = 0;
    let context = session.context();
    let campaign = *session.campaign.as_uuid().as_bytes();
    let mut client = app.world_mut().resource_mut::<OrganizerClient>();
    client.view = Some(captured.view);
    client.body_durable_tick = Some(0);
    client.body_context = Some(context);
    let mut scope = captured.body_scope;
    scope.campaign_id = campaign;
    client.body_scope = Some(scope);
    for subject in [
        OrganizerSubject::Workplace(workplace),
        OrganizerSubject::WorkplaceCommittee(committee),
        OrganizerSubject::AidPartner(partners[0].actor_id),
        OrganizerSubject::AidPartner(partners[1].actor_id),
    ] {
        app.world_mut()
            .resource_mut::<OrganizerClient>()
            .selected_subject = Some(subject);
        let reading = app
            .world_mut()
            .run_system_once(|scope: Scope| super::board::subject_reading(&scope))
            .expect("visible subject reading");
        app.world_mut().resource_mut::<OrganizerClient>().inspector = OrganizerInspector::Closed;
        app.world_mut()
            .write_message(OrganizerAction::InspectSubjectEvidence);
        app.update();
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.inspector, OrganizerInspector::Evidence);
        let visible = client.evidence_ids(0);
        if let OrganizerSubject::AidPartner(id) = subject {
            let expected = partners
                .iter()
                .find(|p| p.actor_id == id)
                .expect("known partner");
            assert_eq!(visible.len(), 1);
            assert_eq!(
                client
                    .lawful_evidence(visible[0], 0)
                    .expect("selected partner report")
                    .subject_id,
                id
            );
            assert!(
                reading.contains("Opening food assessment") && reading.contains(&expected.label),
                "{reading}"
            );
            assert!(!reading.contains(
                &partners
                    .iter()
                    .find(|p| p.actor_id != id)
                    .expect("other partner")
                    .label
            ));
        } else {
            assert_eq!(visible.len(), 0);
            assert!(!reading.contains("Opening food assessment"), "{reading}");
        }
    }
    let world = super::copy::world_reports(
        app.world().resource::<OrganizerClient>(),
        app.world().resource::<ObserverSession>(),
    )
    .expect("earned World summary");
    assert!(partners.iter().all(|p| world.contains(&p.label)));
    assert!(!world.contains("This is workplace report scope"));
}
