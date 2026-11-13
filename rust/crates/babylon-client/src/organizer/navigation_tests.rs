//! Shared navigation regressions through native organizer and production handlers.

use bevy::input_focus::InputFocus;
use bevy::prelude::*;

use crate::navigation::{self, NavigationAction, NavigationButton, NavigationHistory};
use crate::observer::ObserverSession;
use crate::observer_io::ObserverSet;
use crate::observer_ui::{ObserverFeedback, ObserverFrame};
use crate::production::{PrimaryView, ProductionCommand, ProductionNavigation};
use crate::ui::dossier_card::DossierRefresh;
use crate::ui::Interaction;

use super::super::ui;
use super::super::{OrganizerClient, OrganizerInspector};

fn app() -> App {
    let (mut app, _, _) = ui::tests::dossier_navigation_fixture();
    app.init_resource::<ProductionNavigation>()
        .init_resource::<ObserverFrame>()
        .init_resource::<ObserverFeedback>()
        .init_resource::<DossierRefresh>()
        .init_resource::<crate::observer_focus::ObserverFocusPolicy>()
        .add_message::<ProductionCommand>()
        .add_systems(
            Update,
            crate::production::navigation::navigate.in_set(ObserverSet::Input),
        );
    // This focused fixture installs organizer UI, so supply the connected shell's native
    // controls as well. Their ordinary pointer/focus admission and handler remain unchanged.
    app.world_mut()
        .commands()
        .spawn((
            Node::default(),
            bevy::input_focus::tab_navigation::TabGroup::new(0),
        ))
        .with_children(navigation::spawn);
    app.world_mut().flush();
    app.update();
    app
}

fn press(app: &mut App, action: NavigationAction) {
    let entity = {
        let world = app.world_mut();
        let mut query = world.query::<(Entity, &NavigationButton)>();
        query
            .iter(world)
            .find_map(|(entity, button)| {
                (button.0 == action && visible(world, entity)).then_some(entity)
            })
            .expect("the native navigation button was spawned")
    };
    *app.world_mut()
        .get_mut::<Interaction>(entity)
        .expect("native pressable control") = Interaction::Pressed;
    app.update();
    *app.world_mut()
        .get_mut::<Interaction>(entity)
        .expect("native pressable survives navigation") = Interaction::None;
    app.update();
}

fn visible(world: &World, entity: Entity) -> bool {
    let modal = world
        .resource::<crate::observer_focus::ObserverFocusPolicy>()
        .modal;
    let mut inside_modal = modal.is_none();
    let mut cursor = Some(entity);
    while let Some(current) = cursor {
        if world
            .get::<Node>(current)
            .is_some_and(|node| node.display == Display::None)
        {
            return false;
        }
        inside_modal |= modal == Some(current);
        cursor = world.get::<ChildOf>(current).map(ChildOf::parent);
    }
    inside_modal
}

#[test]
fn world_back_and_home_return_through_the_native_handlers_without_draft_changes() {
    let mut app = app();
    let draft = ui::tests::draft_debug(&app);
    app.world_mut().write_message(ProductionCommand::Map);
    app.update();
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Map,
        "World opens through production navigation"
    );
    press(&mut app, NavigationAction::Back);
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Organizer,
        "Back restores the prior decision screen"
    );
    assert!(
        !app.world().resource::<NavigationHistory>().can_go_back(),
        "Back must not record itself"
    );
    app.world_mut().write_message(ProductionCommand::Map);
    app.update();
    press(&mut app, NavigationAction::Home);
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Organizer,
        "Home reaches organizing"
    );
    press(&mut app, NavigationAction::Back);
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Map,
        "Home records its origin"
    );
    assert_eq!(
        ui::tests::draft_debug(&app),
        draft,
        "navigation cannot rewrite the personal draft"
    );
}

#[test]
fn evidence_back_closes_the_top_panel_before_returning_to_world() {
    let mut app = app();
    app.world_mut().write_message(ProductionCommand::Map);
    app.update();
    app.world_mut().write_message(ProductionCommand::Open);
    app.update();
    assert_eq!(
        app.world().resource::<OrganizerClient>().inspector,
        OrganizerInspector::Evidence,
        "organizer campaigns use earned evidence"
    );
    press(&mut app, NavigationAction::Back);
    assert_eq!(
        app.world().resource::<OrganizerClient>().inspector,
        OrganizerInspector::Closed,
        "Back closes only the topmost detail first"
    );
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Organizer,
        "closing the inspector does not skip the parent"
    );
    press(&mut app, NavigationAction::Back);
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Map,
        "the next Back consumes the prior screen visit"
    );
}

#[test]
fn pending_advance_keeps_navigation_live_without_sending_another_operation() {
    let mut app = app();
    let (client, session) = super::super::tests::ready();
    app.insert_resource(client).insert_resource(session);
    app.update();
    let draft = ui::tests::draft_debug(&app);
    let request = app
        .world_mut()
        .resource_mut::<ObserverSession>()
        .begin_advance()
        .expect("the ready fixture admits one advance");
    app.world_mut().write_message(ProductionCommand::Map);
    app.update();
    press(&mut app, NavigationAction::Home);
    press(&mut app, NavigationAction::Back);
    let session = app.world().resource::<ObserverSession>();
    assert_eq!(
        session.pending_advance_request(),
        Some(request),
        "navigation must preserve the in-flight operation identity"
    );
    assert_eq!(
        session.durable_tick, 3,
        "navigation does not advance gameplay"
    );
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Map,
        "Back remains usable during advance"
    );
    assert_eq!(
        ui::tests::draft_debug(&app),
        draft,
        "busy navigation preserves draft edits"
    );
    assert!(
        app.world().resource::<OrganizerClient>().outbox.is_none(),
        "navigation never sends organizer commands"
    );
}

#[test]
fn historical_home_invalidates_review_and_back_reacquires_the_period() {
    let mut app = app();
    let (mut client, mut session) = super::super::tests::ready();
    let command = client
        .make_command(&session, client.choice())
        .expect("the ready fixture has a draft command");
    client.reviewed_command = Some(command.clone());
    client.review_context = Some(session.context());
    client.commitment = Some(babylon_persistence::runtime_session::OrganizerCommitment {
        command,
        resolves_period: 4,
        commitment_id: [44; 32],
    });
    session.inspect_tick(2);
    assert!(
        session.installed(&session.context()),
        "fixture historical observation is installed"
    );
    app.insert_resource(client).insert_resource(session);
    app.update();
    let draft = ui::tests::draft_debug(&app);
    let accepted = app.world().resource::<OrganizerClient>().commitment.clone();
    press(&mut app, NavigationAction::Home);
    assert_eq!(
        app.world().resource::<ObserverSession>().viewed_tick,
        3,
        "Home requests the live period"
    );
    assert!(
        app.world()
            .resource::<OrganizerClient>()
            .reviewed_command
            .is_none(),
        "historical return requires fresh review"
    );
    {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        let context = session.context();
        assert!(
            session.installed(&context),
            "replacement live observation installs normally"
        );
    }
    press(&mut app, NavigationAction::Back);
    assert_eq!(
        app.world().resource::<ObserverSession>().viewed_tick,
        2,
        "Back re-enters history through session inspection"
    );
    assert_eq!(
        ui::tests::draft_debug(&app),
        draft,
        "period navigation preserves the draft"
    );
    assert_eq!(
        app.world().resource::<OrganizerClient>().commitment,
        accepted,
        "period navigation preserves the accepted ruling"
    );
}

#[test]
fn perspective_reset_and_observer_only_campaigns_cannot_reuse_organizing_history() {
    let mut app = app();
    app.world_mut().write_message(ProductionCommand::Map);
    app.update();
    assert!(
        app.world().resource::<NavigationHistory>().can_go_back(),
        "the fixture first creates a visit"
    );
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .set_perspective(crate::observer::Perspective::PlayerKnowledge);
    app.update();
    assert!(
        !app.world().resource::<NavigationHistory>().can_go_back(),
        "perspective changes discard old capabilities and visits"
    );
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .organizer_enabled = false;
    let focus = app.world().resource::<InputFocus>().get();
    press(&mut app, NavigationAction::Home);
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Map,
        "Home cannot grant organizing authority"
    );
    assert_eq!(
        app.world().resource::<InputFocus>().get(),
        focus,
        "a refused Home leaves focus alone"
    );
}

#[test]
fn automatic_live_period_refresh_does_not_add_a_visit_or_roll_back_gameplay() {
    let mut app = app();
    app.world_mut().write_message(ProductionCommand::Map);
    app.update();
    {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        session.ready(1, None);
        let context = session.context();
        assert!(
            session.installed(&context),
            "the next committed observation installs normally"
        );
    }
    app.update();
    press(&mut app, NavigationAction::Back);
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Organizer,
        "automatic refresh did not insert another World visit"
    );
    assert_eq!(
        app.world().resource::<ObserverSession>().viewed_tick,
        1,
        "a live descriptor resolves the current durable period"
    );
    assert!(
        !app.world().resource::<NavigationHistory>().can_go_back(),
        "one intentional route produces exactly one return"
    );
}

#[test]
fn same_campaign_reopen_discards_the_old_history_epoch() {
    use babylon_persistence::runtime_session::{
        RuntimeSessionRequest, RuntimeSessionScope, RuntimeSessionTail, RuntimeSessionTarget,
    };
    let mut app = app();
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .connected_fixture();
    app.update();
    app.world_mut().write_message(ProductionCommand::Map);
    app.update();
    assert!(
        app.world().resource::<NavigationHistory>().can_go_back(),
        "the fixture has a visit before reopen"
    );
    {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        let campaign_id = session.campaign.as_uuid().to_string();
        session
            .queue_campaign(RuntimeSessionTarget::Open {
                campaign_id: campaign_id.clone(),
            })
            .expect("same campaign reopen is admitted");
        let RuntimeSessionRequest::Switch {
            request_id, scope, ..
        } = session
            .pending_switch_request()
            .expect("queued reopen request")
        else {
            panic!("reopen produces a Switch request")
        };
        session.switch_sent();
        session
            .switching(
                request_id,
                &scope,
                RuntimeSessionScope {
                    epoch: scope.epoch + 1,
                    campaign_id: Some(campaign_id),
                },
            )
            .expect("the exact reopen acknowledgement is admitted");
        session
            .admitted(
                request_id,
                "fixture".into(),
                RuntimeSessionTail {
                    resolve_tick: 0,
                    tick_content_hash: None,
                    world_hash: None,
                },
            )
            .expect("same campaign returns ready under the new epoch");
        session.organizer_enabled = true;
    }
    app.update();
    assert!(
        !app.world().resource::<NavigationHistory>().can_go_back(),
        "history cannot cross a same-campaign lifecycle reset"
    );
}

#[test]
fn draft_edits_and_refused_review_do_not_create_navigation_history() {
    let mut app = app();
    app.world_mut()
        .resource_mut::<OrganizerClient>()
        .draft
        .as_mut()
        .expect("fixture draft")
        .notes
        .insert("A local note.");
    app.update();
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .begin_advance()
        .expect("the fixture starts one pending advance before review");
    app.world_mut().write_message(ui::OrganizerAction::Review);
    app.update();
    assert_eq!(
        app.world().resource::<OrganizerClient>().inspector,
        OrganizerInspector::Closed,
        "the unsupported review is refused"
    );
    assert!(
        !app.world().resource::<NavigationHistory>().can_go_back(),
        "draft mutations and refused actions never push visits"
    );
}

#[test]
fn failed_advance_cancels_a_deferred_historical_return_without_replacing_the_request() {
    let mut app = app();
    let (client, mut session) = super::super::tests::ready();
    session.inspect_tick(2);
    assert!(
        session.installed(&session.context()),
        "fixture history is admitted"
    );
    app.insert_resource(client).insert_resource(session);
    app.update();
    press(&mut app, NavigationAction::Home);
    let request = {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        let context = session.context();
        assert!(session.installed(&context), "live replacement is admitted");
        session.begin_advance().expect("one advance begins")
    };
    press(&mut app, NavigationAction::Back);
    assert_eq!(
        app.world().resource::<ObserverSession>().viewed_tick,
        3,
        "period inspection waits while advance owns the request"
    );
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .fail("Storage acknowledgement is uncertain.".into());
    app.update();
    assert!(
        app.world()
            .resource::<NavigationHistory>()
            .restore
            .is_none(),
        "terminal failure ends deferred restoration"
    );
    assert_eq!(
        app.world()
            .resource::<ObserverSession>()
            .pending_advance_request(),
        Some(request),
        "failure navigation must preserve the uncertain operation for reconciliation"
    );
    assert!(
        app.world()
            .resource::<OrganizerClient>()
            .message
            .contains("reconciled"),
        "the safe parent explains why history could not reopen"
    );
}

fn key(app: &mut App, window: Entity, key_code: KeyCode) {
    app.world_mut()
        .write_message(bevy::input::keyboard::KeyboardInput {
            key_code,
            logical_key: bevy::input::keyboard::Key::Character("".into()),
            state: bevy::input::ButtonState::Pressed,
            text: None,
            repeat: false,
            window,
        });
    app.update();
}

#[test]
fn alt_left_uses_history_but_text_editor_arrow_and_backspace_remain_edits() {
    let mut app = app();
    app.add_plugins((
        bevy::input::InputPlugin,
        crate::observer_focus::ObserverFocusPlugin,
    ));
    let window = app
        .world_mut()
        .spawn((Window::default(), bevy::window::PrimaryWindow))
        .id();
    app.world_mut().write_message(ProductionCommand::Map);
    app.update();
    key(&mut app, window, KeyCode::AltLeft);
    key(&mut app, window, KeyCode::ArrowLeft);
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Organizer,
        "Alt+Left returns through the shared Back handler"
    );

    let (mut editor, window, focus) = ui::tests::focused_notes_navigation();
    let before = editor
        .world()
        .resource::<OrganizerClient>()
        .draft
        .as_ref()
        .expect("notes draft")
        .notes
        .text
        .len();
    key(&mut editor, window, KeyCode::AltLeft);
    key(&mut editor, window, KeyCode::ArrowLeft);
    key(&mut editor, window, KeyCode::Backspace);
    assert_eq!(
        editor.world().resource::<OrganizerClient>().inspector,
        OrganizerInspector::Notes,
        "text-editor keys do not leave the Notes panel"
    );
    assert_eq!(
        editor.world().resource::<InputFocus>().get(),
        Some(focus),
        "editing retains its actual focus target"
    );
    assert_eq!(
        editor
            .world()
            .resource::<OrganizerClient>()
            .draft
            .as_ref()
            .expect("notes draft")
            .notes
            .text
            .len(),
        before - 1,
        "Backspace still edits the note"
    );
}
