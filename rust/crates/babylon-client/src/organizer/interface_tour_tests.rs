//! Controls exercise the real organizer handlers and shell modal policy.

use std::sync::mpsc::Receiver;

use babylon_persistence::runtime_session::{
    OrganizerAllocation, OrganizerChoice, OrganizerCollectionPreview, OrganizerCommitment,
    OrganizerGiftConsent, RuntimeSessionRequest,
};
use bevy::input::keyboard::{Key, KeyboardInput, NativeKey};
use bevy::input::ButtonState;
use bevy::input::InputPlugin;
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::input_focus::{FocusCause, FocusedInput, InputFocus};
use bevy::prelude::*;
use bevy::text::TextLayoutInfo;
use bevy::ui::UiSystems;
use bevy::window::PrimaryWindow;
use uuid::Uuid;

use super::runtime::{InterfaceTour, TourControl};
use super::view::Highlight;
use super::{preferences, TourRoot};
use crate::atlas::CountyAtlas;
use crate::map::SelectedCounty;
use crate::navigation::NavigationAction;
use crate::observer::{ObserverSession, SessionPhase};
use crate::observer_focus::{
    ObserverFocusPlugin, ObserverFocusPolicy, ObserverFocusTarget, ObserverKeyboardActivate,
    ObserverKeyboardClaim,
};
use crate::observer_io::ObserverSet;
use crate::observer_opening::{OpeningPresentation, OpeningStage};
use crate::observer_ui::ObserverFontRole;
use crate::observer_ui::{ObserverCommand, ObserverUiState};
use crate::organizer::amount_editor::AmountField;
use crate::organizer::ui::TextPart;
use crate::organizer::ui::{OrganizerAction, OrganizerActionRequested};
use crate::organizer::{OrganizerClient, OrganizerInspector, RequestKind};
use crate::production::{PrimaryView, ProductionCommand, ProductionNavigation};
use crate::ui::Interaction;

fn admitted() -> (OrganizerClient, ObserverSession) {
    let (mut client, mut session, request, snapshot) = crate::organizer::tests::status_fixture();
    let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
        panic!("status fixture");
    };
    client
        .status(request_id, snapshot, &mut session)
        .expect("authenticated P3 organizer");
    session.playing = true;
    (client, session)
}

fn fixture() -> (App, Entity, Entity, Receiver<RuntimeSessionRequest>) {
    let (mut app, requests) = crate::observer_io::tests::command_app();
    let (client, session) = admitted();
    app.add_plugins((
        MinimalPlugins,
        InputPlugin,
        ObserverFocusPlugin,
        crate::test_support::HeadlessVisibilityPlugin,
    ))
    .configure_sets(
        Update,
        (
            ObserverSet::Input,
            ObserverSet::Receive,
            ObserverSet::Install,
            ObserverSet::Paint,
        )
            .chain(),
    )
    .insert_resource(client)
    .insert_resource(session)
    .insert_resource(PrimaryView::Organizer)
    .insert_resource(ObserverUiState {
        menu_open: false,
        splash_visible: false,
        ..default()
    })
    .insert_resource(
        CountyAtlas::parse(include_bytes!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../assets/map/county_atlas.bin"
        )))
        .expect("captured atlas"),
    )
    .insert_resource(SelectedCounty(Some(0)));
    app.init_resource::<ProductionNavigation>()
        .add_message::<ProductionCommand>()
        .add_systems(
            Update,
            crate::production::navigation::navigate.in_set(ObserverSet::Input),
        );
    let directory = std::env::temp_dir().join(format!("interface-tour-{}", Uuid::new_v4()));
    app.insert_resource(InterfaceTour {
        preference: Ok(directory.join("interface-tour.json")),
        outcome: None,
        campaign: None,
        step: None,
        replay_requested: false,
        home_requested: false,
        save_error: None,
        return_focus: None,
        restore_focus: false,
    });
    crate::organizer::ui::install(&mut app);
    app.add_plugins(crate::navigation::NavigationPlugin);
    crate::observer_ui::install_shell_focus_policy(&mut app);
    super::install(&mut app);
    let window = app
        .world_mut()
        .spawn((Window::default(), PrimaryWindow))
        .id();
    let parent = app
        .world_mut()
        .spawn((Node::default(), TabGroup::new(1)))
        .id();
    let mut target = ObserverFocusTarget::action(None);
    target.available = true;
    let original = app.world_mut().spawn((Node::default(), target)).id();
    app.world_mut().entity_mut(parent).add_child(original);
    app.world_mut()
        .resource_mut::<InputFocus>()
        .set(original, FocusCause::Navigated);
    app.add_systems(Startup, |mut commands: Commands| {
        commands
            .spawn((Node::default(), TabGroup::new(2)))
            .with_children(super::settings_button);
    });
    (app, window, original, requests)
}

fn control(app: &mut App, sought: TourControl) -> Entity {
    let world = app.world_mut();
    world
        .query::<(Entity, &TourControl)>()
        .iter(world)
        .find_map(|(entity, value)| (*value == sought).then_some(entity))
        .expect("real tour control")
}

fn press(app: &mut App, sought: TourControl) {
    let entity = control(app, sought);
    *app.world_mut()
        .get_mut::<Interaction>(entity)
        .expect("pressable") = Interaction::Pressed;
    app.update();
    *app.world_mut()
        .get_mut::<Interaction>(entity)
        .expect("pressable") = Interaction::None;
    app.update();
}

fn key(app: &mut App, window: Entity, key_code: KeyCode) {
    for state in [ButtonState::Pressed, ButtonState::Released] {
        app.world_mut().write_message(KeyboardInput {
            key_code,
            logical_key: Key::Unidentified(NativeKey::Unidentified),
            state,
            text: None,
            repeat: false,
            window,
        });
        app.update();
    }
}

fn cleanup(app: &App) {
    let tour = app.world().resource::<InterfaceTour>();
    if let Ok(path) = &tour.preference {
        if let Some(directory) = path.parent() {
            if directory.exists() {
                std::fs::remove_dir_all(directory).expect("remove disposable preference");
            }
        }
    }
}

#[test]
fn first_authenticated_loaded_period_opens_modal_and_pauses_without_game_changes() {
    let (mut app, _, original, requests) = fixture();
    let draft = app.world().resource::<OrganizerClient>().draft.clone();
    let hash = app.world().resource::<ObserverSession>().world_hash.clone();
    app.update();
    assert!(
        app.world()
            .resource::<ObserverUiState>()
            .interface_tour_open
    );
    assert_eq!(app.world().resource::<InterfaceTour>().step, Some(0));
    assert!(app
        .world()
        .resource::<ObserverFocusPolicy>()
        .modal
        .is_some());
    assert_ne!(app.world().resource::<InputFocus>().get(), Some(original));
    assert!(app
        .world()
        .resource::<ObserverKeyboardClaim>()
        .blocks_world_shortcuts());
    let session = app.world().resource::<ObserverSession>();
    assert!(!session.playing);
    assert_eq!(session.durable_tick, 3);
    assert_eq!(session.world_hash, hash);
    assert!(!session.advance_pending());
    let client = app.world().resource::<OrganizerClient>();
    assert_eq!(client.draft, draft);
    assert!(client.outbox.is_none());
    assert!(client.pending.is_none());
    assert!(requests.try_recv().is_err());
    cleanup(&app);
}

#[test]
fn accepted_loaded_commitment_survives_every_callout_and_completion_unchanged() {
    let (mut app, _, _, requests) = fixture();
    let commitment = {
        let client = app.world().resource::<OrganizerClient>();
        let session = app.world().resource::<ObserverSession>();
        OrganizerCommitment {
            command: client
                .make_command(session, OrganizerChoice::Reinforce)
                .expect("captured command"),
            resolves_period: 4,
            commitment_id: [4; 32],
        }
    };
    let expected = serde_json::to_value(&commitment).expect("commitment snapshot");
    app.world_mut().resource_mut::<OrganizerClient>().commitment = Some(commitment);
    let draft = app.world().resource::<OrganizerClient>().draft.clone();
    let hash = app.world().resource::<ObserverSession>().world_hash.clone();
    app.update();
    assert!(
        app.world()
            .resource::<ObserverUiState>()
            .interface_tour_open
    );
    for _ in 0..super::view::STEP_COUNT {
        press(&mut app, TourControl::Next);
    }
    let client = app.world().resource::<OrganizerClient>();
    assert_eq!(
        serde_json::to_value(
            client
                .commitment
                .as_ref()
                .expect("accepted command retained")
        )
        .expect("commitment snapshot"),
        expected
    );
    assert_eq!(client.draft, draft);
    assert!(client.pending.is_none());
    assert!(client.outbox.is_none());
    let session = app.world().resource::<ObserverSession>();
    assert_eq!(session.durable_tick, 3);
    assert_eq!(session.world_hash, hash);
    assert!(!session.advance_pending());
    assert!(requests.try_recv().is_err());
    cleanup(&app);
}

#[test]
fn first_ready_gate_waits_for_current_body_controls_and_unobstructed_organizer() {
    for gate in [
        "body",
        "stale",
        "status",
        "outbox",
        "controls",
        "advance",
        "menu",
        "comparison",
        "inspector",
        "map",
        "loading",
        "historical",
        "opening",
    ] {
        let (mut app, _, _, _) = fixture();
        match gate {
            "body" => {
                app.world_mut()
                    .resource_mut::<OrganizerClient>()
                    .body_context = None;
            }
            "stale" => {
                app.world_mut()
                    .resource_mut::<OrganizerClient>()
                    .body_world_hash = Some("stale".into());
            }
            "status" => app.world_mut().resource_mut::<OrganizerClient>().status_due = true,
            "outbox" => {
                let (mut client, mut session) = admitted();
                client.queue(&mut session, RequestKind::Status, None);
                app.insert_resource(client).insert_resource(session);
            }
            "controls" => app
                .world_mut()
                .resource_mut::<ObserverSession>()
                .set_organizer_control_pending(true),
            "advance" => {
                app.world_mut().resource_mut::<ObserverSession>().phase = SessionPhase::Advancing;
            }
            "menu" => app.world_mut().resource_mut::<ObserverUiState>().menu_open = true,
            "comparison" => {
                app.world_mut()
                    .resource_mut::<ObserverUiState>()
                    .comparison_open = true;
            }
            "inspector" => {
                app.world_mut().resource_mut::<OrganizerClient>().inspector =
                    OrganizerInspector::Review;
            }
            "map" => *app.world_mut().resource_mut::<PrimaryView>() = PrimaryView::Map,
            "loading" => {
                app.world_mut().resource_mut::<ObserverSession>().phase = SessionPhase::Loading;
            }
            "historical" => {
                app.world_mut()
                    .resource_mut::<ObserverSession>()
                    .viewed_tick = 2;
            }
            "opening" => {
                app.insert_resource(OpeningPresentation {
                    stage: OpeningStage::Title,
                    ..default()
                });
            }
            _ => unreachable!("authored case"),
        }
        app.update();
        assert!(
            !app.world()
                .resource::<ObserverUiState>()
                .interface_tour_open,
            "{gate}"
        );
        let (client, session) = admitted();
        app.world_mut().remove_resource::<OpeningPresentation>();
        app.insert_resource(client)
            .insert_resource(session)
            .insert_resource(PrimaryView::Organizer)
            .insert_resource(ObserverUiState {
                menu_open: false,
                splash_visible: false,
                ..default()
            });
        app.update();
        assert!(
            app.world()
                .resource::<ObserverUiState>()
                .interface_tour_open,
            "{gate} ready"
        );
        cleanup(&app);
    }
}

#[test]
fn skip_and_escape_restore_focus_save_seen_and_never_resume_playback() {
    for escape in [false, true] {
        let (mut app, window, original, _) = fixture();
        app.update();
        press(&mut app, TourControl::Next);
        if escape {
            key(&mut app, window, KeyCode::Escape);
        } else {
            press(&mut app, TourControl::Skip);
        }
        app.update();
        assert!(
            !app.world()
                .resource::<ObserverUiState>()
                .interface_tour_open
        );
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(original));
        assert!(!app.world().resource::<ObserverSession>().playing);
        let tour = app.world().resource::<InterfaceTour>();
        assert_eq!(tour.outcome, Some(preferences::Outcome::Skipped));
        assert_eq!(
            preferences::read(tour.preference.as_ref().expect("path")).expect("saved skip"),
            tour.outcome
        );
        app.world_mut().resource_mut::<ObserverUiState>().menu_open = true;
        app.update();
        app.world_mut().resource_mut::<ObserverUiState>().menu_open = false;
        app.update();
        assert!(
            !app.world()
                .resource::<ObserverUiState>()
                .interface_tour_open
        );
        cleanup(&app);
    }
}

#[test]
fn physical_tab_and_enter_stay_inside_tour_and_escape_restores_world_focus() {
    let (mut app, window, _, requests) = fixture();
    app.world_mut()
        .resource_mut::<InputFocus>()
        .set(window, FocusCause::Navigated);
    app.update();
    let next = control(&mut app, TourControl::Next);
    assert_eq!(app.world().resource::<InputFocus>().get(), Some(next));
    key(&mut app, window, KeyCode::Enter);
    assert_eq!(app.world().resource::<InterfaceTour>().step, Some(1));
    for _ in 0..6 {
        key(&mut app, window, KeyCode::Tab);
        let focused = app
            .world()
            .resource::<InputFocus>()
            .get()
            .expect("modal focus");
        assert!(
            app.world().get::<TourControl>(focused).is_some(),
            "Tab never reaches a background action"
        );
    }
    key(&mut app, window, KeyCode::Escape);
    app.update();
    assert_eq!(app.world().resource::<InputFocus>().get(), Some(window));
    assert!(!app.world().resource::<ObserverSession>().advance_pending());
    assert!(requests.try_recv().is_err());
    cleanup(&app);
}

#[test]
fn previous_complete_replay_and_menu_round_trip_use_real_controls() {
    let (mut app, _, _, _) = fixture();
    app.update();
    press(&mut app, TourControl::Next);
    press(&mut app, TourControl::Next);
    press(&mut app, TourControl::Previous);
    assert_eq!(app.world().resource::<InterfaceTour>().step, Some(1));
    app.world_mut().resource_mut::<ObserverUiState>().menu_open = true;
    app.update();
    assert!(
        !app.world()
            .resource::<ObserverUiState>()
            .interface_tour_open
    );
    assert_eq!(app.world().resource::<InterfaceTour>().step, Some(1));
    app.world_mut().resource_mut::<ObserverUiState>().menu_open = false;
    app.update();
    assert!(
        app.world()
            .resource::<ObserverUiState>()
            .interface_tour_open
    );
    for _ in 1..super::view::STEP_COUNT {
        press(&mut app, TourControl::Next);
    }
    assert_eq!(
        app.world().resource::<InterfaceTour>().outcome,
        Some(preferences::Outcome::Completed)
    );
    app.world_mut().resource_mut::<ObserverUiState>().menu_open = true;
    app.update();
    let replay = control(&mut app, TourControl::Replay);
    let context = app.world().resource::<ObserverSession>().context();
    app.world_mut().trigger(ObserverKeyboardActivate {
        entity: replay,
        context: Some(context),
    });
    app.update();
    assert_eq!(app.world().resource::<InterfaceTour>().step, Some(0));
    assert!(
        app.world()
            .resource::<ObserverUiState>()
            .interface_tour_open
    );
    cleanup(&app);
}

#[test]
fn replay_from_archive_uses_shared_home_and_keeps_back_origin_and_draft() {
    let (mut app, _, _, requests) = fixture();
    app.update();
    press(&mut app, TourControl::Skip);
    let draft = app.world().resource::<OrganizerClient>().draft.clone();
    *app.world_mut().resource_mut::<PrimaryView>() = PrimaryView::Map;
    app.world_mut()
        .resource_mut::<ObserverUiState>()
        .archive_open = true;
    app.update();
    app.world_mut().resource_mut::<ObserverUiState>().menu_open = true;
    app.update();
    press(&mut app, TourControl::Replay);
    for _ in 0..4 {
        app.update();
        if app
            .world()
            .resource::<ObserverUiState>()
            .interface_tour_open
        {
            let focus = app
                .world()
                .resource::<InputFocus>()
                .get()
                .expect("tour focus");
            assert!(
                app.world().get::<TourControl>(focus).is_some(),
                "Home restoration never takes focus out of the tour"
            );
        }
    }
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Organizer
    );
    assert!(!app.world().resource::<ObserverUiState>().archive_open);
    assert!(
        app.world()
            .resource::<ObserverUiState>()
            .interface_tour_open
    );
    assert_eq!(app.world().resource::<InterfaceTour>().step, Some(0));
    assert_eq!(app.world().resource::<OrganizerClient>().draft, draft);
    press(&mut app, TourControl::Skip);
    app.world_mut().write_message(NavigationAction::Back);
    app.update();
    assert_eq!(*app.world().resource::<PrimaryView>(), PrimaryView::Map);
    assert!(app.world().resource::<ObserverUiState>().archive_open);
    assert_eq!(app.world().resource::<OrganizerClient>().draft, draft);
    assert!(requests.try_recv().is_err());
    cleanup(&app);
}

#[test]
fn shield_rejects_actual_background_organizer_and_queued_observer_actions() {
    let (mut app, _, _, requests) = fixture();
    app.update();
    let draft = app.world().resource::<OrganizerClient>().draft.clone();
    let hashes = {
        let session = app.world().resource::<ObserverSession>();
        (
            session.durable_tick,
            session.world_hash.clone(),
            session.content_hash.clone(),
        )
    };
    for action in [
        OrganizerAction::Choose(OrganizerChoice::Hold),
        OrganizerAction::Review,
        OrganizerAction::Confirm,
        OrganizerAction::Advance,
        OrganizerAction::Inspect(OrganizerInspector::Notes),
    ] {
        app.world_mut().trigger(OrganizerActionRequested(action));
    }
    app.world_mut().write_message(ObserverCommand::Step);
    app.world_mut().write_message(ObserverCommand::TogglePlay);
    app.world_mut().write_message(ProductionCommand::Map);
    app.world_mut().write_message(ProductionCommand::Open);
    app.world_mut().write_message(NavigationAction::Back);
    app.world_mut().write_message(NavigationAction::Home);
    app.update();
    let client = app.world().resource::<OrganizerClient>();
    assert_eq!(client.draft, draft);
    assert!(client.pending.is_none());
    assert!(client.outbox.is_none());
    assert_eq!(client.inspector, OrganizerInspector::Closed);
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Organizer
    );
    let session = app.world().resource::<ObserverSession>();
    assert_eq!(
        (
            session.durable_tick,
            session.world_hash.clone(),
            session.content_hash.clone()
        ),
        hashes
    );
    assert!(!session.advance_pending());
    assert!(!session.playing);
    assert!(requests.try_recv().is_err());
    cleanup(&app);
}

#[test]
fn skip_keeps_background_commands_blocked_for_the_entire_closing_input_frame() {
    let (mut app, _, _, requests) = fixture();
    app.update();
    app.world_mut().write_message(ObserverCommand::Step);
    app.world_mut().write_message(OrganizerAction::Advance);
    app.world_mut().write_message(ProductionCommand::Map);
    app.world_mut().write_message(NavigationAction::Home);
    press(&mut app, TourControl::Skip);
    assert!(
        !app.world()
            .resource::<ObserverUiState>()
            .interface_tour_open
    );
    assert!(!app.world().resource::<ObserverSession>().advance_pending());
    assert!(app.world().resource::<OrganizerClient>().outbox.is_none());
    assert!(requests.try_recv().is_err());
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Organizer
    );
    cleanup(&app);
}

#[test]
fn stale_editor_events_cannot_change_amounts_or_notes_behind_tour() {
    let (mut app, window, _, requests) = fixture();
    let mut client = app
        .world_mut()
        .remove_resource::<OrganizerClient>()
        .expect("organizer");
    let mut session = app
        .world_mut()
        .remove_resource::<ObserverSession>()
        .expect("session");
    let (_, _, _, mut snapshot) = crate::organizer::tests::status_fixture();
    snapshot.collection = Some(OrganizerCollectionPreview {
        period: 3,
        mandate_id: [8; 32],
        actor_id: snapshot.view.actor_id,
        contributor_id: 1,
        contributor_label: "Disclosed contributor".into(),
        source_hash: [16; 32],
        cash_consent: OrganizerGiftConsent::Accept,
        initial_cash_micros: 280_000_000,
        maximum_cash_micros: 1_450_000_000,
        protected_cash_floor_micros: 0,
        collection_hours: 2,
        organization_cash_micros: 1_000_000,
    });
    client.queue(&mut session, RequestKind::Status, None);
    let RuntimeSessionRequest::OrganizerStatus { request_id, .. } =
        client.outbox.take().expect("status request")
    else {
        panic!("status request")
    };
    client
        .status(request_id, snapshot, &mut session)
        .expect("authenticated amount terms");
    let draft = client.draft.as_mut().expect("draft");
    draft.choice = OrganizerChoice::Collect;
    draft.collection_allocation = OrganizerAllocation::Collection {
        target_cash_micros: 280_000_000,
    };
    client.draft_writable = true;
    let original = draft.clone();
    let message = client.message.clone();
    app.insert_resource(client).insert_resource(session);
    app.update();
    assert!(
        app.world()
            .resource::<ObserverUiState>()
            .interface_tour_open
    );
    let (amount, notes) = {
        let world = app.world_mut();
        let amount = world
            .query::<(Entity, &AmountField)>()
            .iter(world)
            .find_map(|(entity, field)| (*field == AmountField::Contribution).then_some(entity))
            .expect("actual amount field");
        let notes = world
            .query::<(&TextPart, &ChildOf)>()
            .iter(world)
            .find_map(|(part, parent)| matches!(part, TextPart::Notes).then(|| parent.parent()))
            .expect("actual notes field");
        (amount, notes)
    };
    for entity in [amount, notes] {
        app.world_mut()
            .resource_mut::<InputFocus>()
            .set(entity, FocusCause::Navigated);
        app.world_mut()
            .get_mut::<ObserverFocusTarget>(entity)
            .expect("real editor target")
            .available = true;
        app.world_mut().trigger(FocusedInput::new(
            entity,
            KeyboardInput {
                key_code: KeyCode::Digit9,
                logical_key: Key::Character("9".into()),
                state: ButtonState::Pressed,
                text: Some("9".into()),
                repeat: false,
                window,
            },
            window,
        ));
    }
    app.update();
    let client = app.world().resource::<OrganizerClient>();
    assert_eq!(client.draft.as_ref(), Some(&original));
    assert_eq!(client.message, message);
    assert!(!client.draft_dirty);
    assert!(client.pending.is_none());
    assert!(client.outbox.is_none());
    assert!(!app.world().resource::<ObserverSession>().advance_pending());
    assert!(requests.try_recv().is_err());
    cleanup(&app);
}

#[test]
fn unsupported_observer_mode_hides_replay_and_failed_save_does_not_block_play() {
    let (mut app, _, _, _) = fixture();
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .organizer_enabled = false;
    app.update();
    assert!(
        !app.world()
            .resource::<ObserverUiState>()
            .interface_tour_open
    );
    let replay = control(&mut app, TourControl::Replay);
    assert_eq!(
        app.world().get::<Node>(replay).expect("replay").display,
        Display::None
    );
    assert!(
        !app.world()
            .get::<ObserverFocusTarget>(replay)
            .expect("replay focus")
            .available
    );
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .organizer_enabled = true;
    app.world_mut().resource_mut::<InterfaceTour>().preference =
        Err("No personal directory".into());
    app.update();
    press(&mut app, TourControl::Skip);
    assert!(
        !app.world()
            .resource::<ObserverUiState>()
            .interface_tour_open
    );
    assert!(app.world().resource::<InterfaceTour>().save_error.is_some());
    app.world_mut().write_message(ObserverCommand::TogglePlay);
    app.update();
    assert!(app.world().resource::<ObserverSession>().playing);
}

#[test]
fn unfinished_progress_is_memory_only_and_completed_preference_suppresses_autostart() {
    let (mut app, _, _, _) = fixture();
    app.update();
    press(&mut app, TourControl::Next);
    press(&mut app, TourControl::Next);
    let path = app
        .world()
        .resource::<InterfaceTour>()
        .preference
        .as_ref()
        .expect("path")
        .clone();
    assert!(
        !path.exists(),
        "opening and advancing explanations must not mark a tour seen"
    );
    // A new process has only the preference, never the unfinished step.
    assert_eq!(preferences::read(&path).expect("unseen preference"), None);
    press(&mut app, TourControl::Skip);
    let (mut reopened, _, _, _) = fixture();
    reopened.world_mut().resource_mut::<InterfaceTour>().outcome =
        preferences::read(&path).expect("saved seen state");
    reopened.update();
    assert!(
        !reopened
            .world()
            .resource::<ObserverUiState>()
            .interface_tour_open
    );
    cleanup(&app);
    cleanup(&reopened);
}

fn measured_tour(viewport: UVec2, scale: f32, ui_state: &ObserverUiState) -> App {
    use bevy::asset::AssetApp as _;
    use bevy::ecs::system::RunSystemOnce as _;

    let mut app = crate::organizer::ui::tests::measured_board(
        viewport,
        scale,
        ui_state.larger_interface,
        false,
    );
    let font = {
        let world = app.world_mut();
        world
            .query::<(&ObserverFontRole, &TextFont)>()
            .iter(world)
            .find_map(|(role, font)| {
                matches!(role, ObserverFontRole::Body).then(|| font.font.clone())
            })
            .expect("shipped body font")
    };
    {
        let mut ui = app.world_mut().resource_mut::<ObserverUiState>();
        ui.interface_tour_open = true;
        ui.reduced_motion = ui_state.reduced_motion;
    }
    app.init_asset::<Image>()
        .init_asset::<TextureAtlasLayout>()
        .insert_resource(InterfaceTour {
            preference: Err("geometry fixture has no personal storage".into()),
            outcome: None,
            campaign: None,
            step: Some(0),
            replay_requested: false,
            home_requested: false,
            save_error: None,
            return_focus: None,
            restore_focus: false,
        })
        .add_systems(Update, super::view::paint)
        .add_systems(
            PostUpdate,
            (
                bevy::ui::widget::text_system.after(bevy::ui::ui_layout_system),
                super::view::position.after(UiSystems::Layout),
            ),
        );
    app.world_mut()
        .run_system_once(super::view::spawn)
        .expect("spawn actual tour");
    app.update();
    {
        let world = app.world_mut();
        for mut text in world.query::<&mut TextFont>().iter_mut(world) {
            text.font = font.clone();
        }
        let mut roots = world.query_filtered::<&mut Node, With<TourRoot>>();
        roots.single_mut(world).expect("actual tour shield").display = Display::Flex;
    }
    app
}

fn assert_callout(app: &mut App, viewport: UVec2, scale: f32, step: usize) {
    {
        let world = app.world_mut();
        let (node, computed) = world
            .query_filtered::<(&Node, &ComputedNode), With<Highlight>>()
            .single(world)
            .expect("target highlight");
        assert_eq!(
            node.display,
            Display::Flex,
            "step {step} has a visible real HUD anchor"
        );
        assert!(
            computed.size().min_element() > 0.0,
            "step {step} target outline has geometry"
        );
    }
    let (callout, texts) = {
        let world = app.world_mut();
        let mut roots = world.query_filtered::<&Children, With<TourRoot>>();
        let callout = roots
            .single(world)
            .expect("tour shield")
            .iter()
            .find(|entity| world.get::<Children>(*entity).is_some())
            .expect("actual callout panel");
        let mut descendants = vec![callout];
        let mut texts = Vec::new();
        while let Some(entity) = descendants.pop() {
            if let Some(children) = world.get::<Children>(entity) {
                descendants.extend(children.iter());
            }
            if world
                .get::<Text>(entity)
                .is_some_and(|text| !text.0.is_empty())
            {
                texts.push(entity);
            }
        }
        (callout, texts)
    };
    let panel = app
        .world()
        .get::<ComputedNode>(callout)
        .expect("computed callout");
    let transform = app
        .world()
        .get::<UiGlobalTransform>(callout)
        .expect("positioned callout");
    let bounds = Rect::from_center_size(transform.translation, panel.size());
    let viewport_rect = Rect::from_corners(Vec2::ZERO, viewport.as_vec2());
    assert!(
        (bounds.intersect(viewport_rect).size() - bounds.size())
            .abs()
            .max_element()
            <= 1.1,
        "callout fits {viewport:?} scale {scale} step {step}: {bounds:?}"
    );
    for entity in texts {
        let node = app
            .world()
            .get::<ComputedNode>(entity)
            .expect("text layout");
        let transform = app
            .world()
            .get::<UiGlobalTransform>(entity)
            .expect("text position")
            .affine();
        let layout = app
            .world()
            .get::<TextLayoutInfo>(entity)
            .expect("shipped font glyphs");
        assert!(!layout.glyphs.is_empty(), "tour text is actually rendered");
        for glyph in &layout.glyphs {
            if glyph.atlas_info.rect.size().min_element() <= 0.0 {
                continue;
            }
            let local = node.content_box().min + glyph.position;
            let half = glyph.atlas_info.rect.size() * 0.5;
            let rect = Rect::from_corners(
                transform.transform_point2(local - half),
                transform.transform_point2(local + half),
            );
            assert!(
                (rect.intersect(bounds).size() - rect.size())
                    .abs()
                    .max_element()
                    <= 1.1,
                "tour glyph fits its panel at {viewport:?} scale {scale}, step {step}"
            );
        }
    }
}

#[test]
fn callout_text_and_controls_fit_shipped_fonts_at_native_sizes_and_scales() {
    for (viewport, scale, larger) in [
        (UVec2::new(1366, 768), 1.0, false),
        (UVec2::new(1366, 768), 1.15, true),
        (UVec2::new(1920, 1080), 1.25, false),
        (UVec2::new(1920, 1080), 1.4375, true),
    ] {
        for reduced_motion in [false, true] {
            let mut app = measured_tour(
                viewport,
                scale,
                &ObserverUiState {
                    larger_interface: larger,
                    reduced_motion,
                    ..default()
                },
            );
            for step in 0..super::view::STEP_COUNT {
                app.world_mut().resource_mut::<InterfaceTour>().step = Some(step);
                for _ in 0..5 {
                    app.update();
                }
                assert_callout(&mut app, viewport, scale, step);
            }
        }
    }
}
