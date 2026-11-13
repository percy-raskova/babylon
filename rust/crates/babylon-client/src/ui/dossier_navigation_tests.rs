//! History reacquires Archive links through the same native control admission.

use super::tests::{chip_app, frame, installed, page_mut};
use super::*;
use crate::navigation::{NavigationAction, NavigationPlugin};
use crate::observer_focus::ObserverKeyboardClaim;
use crate::production::PrimaryView;
use bevy::input_focus::InputFocus;

fn history_app() -> (App, Entity, SubjectPageRequest) {
    let (mut app, chip, request) = chip_app();
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .organizer_enabled = true;
    app.init_resource::<navigation::ArchiveNavigation>()
        .init_resource::<OrganizerClient>()
        .init_resource::<InputFocus>()
        .init_resource::<ObserverFocusPolicy>()
        .init_resource::<ObserverKeyboardClaim>()
        .init_resource::<ButtonInput<KeyCode>>()
        .insert_resource(PrimaryView::Map)
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
        .add_systems(
            Update,
            navigation::restore
                .after(ObserverSet::Install)
                .before(ArchiveEvidenceApplied),
        )
        .add_plugins(NavigationPlugin);
    app.update();
    (app, chip, request)
}

fn open_chip(app: &mut App, entity: Entity, request: &SubjectPageRequest) {
    app.world_mut().trigger(ObserverKeyboardActivate {
        entity,
        context: request.scope.observer.clone(),
    });
    app.update();
    assert!(
        matches!(
            *app.world().resource::<DossierPageView>(),
            DossierPageView::Subject(_)
        ),
        "the native chip handler admitted its current disclosed link"
    );
}

fn route(app: &App) -> navigation::ArchiveRoute {
    app.world()
        .resource::<navigation::ArchiveNavigation>()
        .capture(
            app.world().resource::<DossierPageView>(),
            app.world().resource::<DossierPresentation>(),
        )
}

#[test]
fn archive_history_reacquires_the_subject_under_the_new_observation_scope() {
    let (mut app, chip, request) = history_app();
    open_chip(&mut app, chip, &request);
    let saved = route(&app);
    {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        session.ready(2, Some("c".repeat(64)));
        session.inspect_tick(1);
        let context = session.context();
        assert!(
            session.installed(&context),
            "the fixture installs the replacement historical observation"
        );
    }
    let session = app.world().resource::<ObserverSession>();
    let next_frame = frame(session, &"b".repeat(64));
    let current_county = installed(session, &"b".repeat(64));
    app.insert_resource(next_frame);
    app.world_mut()
        .resource_mut::<navigation::ArchiveNavigation>()
        .begin(saved);
    app.update();
    app.world_mut().resource_mut::<ActiveCountyDossier>().0 = Some(current_county);
    app.update();
    let DossierPageView::Subject(current) = app.world().resource::<DossierPageView>() else {
        panic!("the fresh county page disclosed the target")
    };
    assert_eq!(
        current.id, request.id,
        "history returns the requested subject identity"
    );
    assert_eq!(
        current.scope.observer,
        Some(app.world().resource::<ObserverSession>().context()),
        "history reacquires current observation admission"
    );
    assert_ne!(
        current.scope.observer, request.scope.observer,
        "the obsolete link scope was not restored"
    );
    assert!(
        app.world().resource::<ActiveCountyDossier>().0.is_none(),
        "the subject must be read again rather than reviving the old page"
    );
}

#[test]
fn missing_archive_link_stays_on_the_admitted_parent_with_clear_feedback() {
    let (mut app, chip, request) = history_app();
    open_chip(&mut app, chip, &request);
    let saved = route(&app);
    app.world_mut()
        .resource_mut::<navigation::ArchiveNavigation>()
        .begin(saved);
    app.update();
    let mut county = installed(app.world().resource::<ObserverSession>(), &"a".repeat(64));
    page_mut(&mut county).links.clear();
    app.world_mut().resource_mut::<ActiveCountyDossier>().0 = Some(county);
    app.update();
    assert_eq!(
        *app.world().resource::<DossierPageView>(),
        DossierPageView::Card,
        "an absent current link cannot authorize the old subject"
    );
    assert!(
        !app.world()
            .resource::<navigation::ArchiveNavigation>()
            .is_restoring(),
        "fallback terminates restoration"
    );
    assert!(
        app.world()
            .resource::<ObserverFeedback>()
            .message
            .is_some_and(|message| message.contains("available parent")),
        "fallback explains the available parent"
    );
}

#[test]
fn failed_archive_subject_read_returns_to_county_and_ends_restoration() {
    let (mut app, chip, request) = history_app();
    open_chip(&mut app, chip, &request);
    let saved = route(&app);
    app.world_mut()
        .resource_mut::<navigation::ArchiveNavigation>()
        .begin(saved);
    app.update();
    let county = installed(app.world().resource::<ObserverSession>(), &"a".repeat(64));
    app.world_mut().resource_mut::<ActiveCountyDossier>().0 = Some(county);
    app.update();
    assert!(
        matches!(
            *app.world().resource::<DossierPageView>(),
            DossierPageView::Subject(_)
        ),
        "the current parent admitted the subject read"
    );
    *app.world_mut().resource_mut::<DossierFetchState>() = DossierFetchState::Failed(
        DossierFetchError::ReaderAbsent("Fixture reader unavailable".into()),
    );
    app.update();
    assert_eq!(
        *app.world().resource::<DossierPageView>(),
        DossierPageView::Card,
        "failed subject restoration lands on a safe county parent"
    );
    assert!(
        !app.world()
            .resource::<navigation::ArchiveNavigation>()
            .is_restoring(),
        "failed reads do not keep restoration pending indefinitely"
    );
}

#[test]
fn shared_back_closes_one_archive_detail_level_and_home_cancels_a_pending_read() {
    let (mut app, _, request) = history_app();
    app.world_mut()
        .write_message(DossierControl::Details(request.scope.clone()));
    app.update();
    app.world_mut()
        .write_message(DossierControl::Technical(request.scope));
    app.update();
    assert!(
        app.world().resource::<DossierPresentation>().technical_open,
        "native controls opened both detail levels"
    );
    app.world_mut().write_message(NavigationAction::Back);
    app.update();
    let presentation = app.world().resource::<DossierPresentation>();
    assert!(
        presentation.details_open && !presentation.technical_open,
        "first Back closes only technical detail"
    );
    app.world_mut().write_message(NavigationAction::Back);
    app.update();
    assert!(
        !app.world().resource::<DossierPresentation>().details_open,
        "second Back closes ordinary details"
    );
    let saved = route(&app);
    app.world_mut()
        .resource_mut::<navigation::ArchiveNavigation>()
        .begin(saved);
    app.world_mut().write_message(NavigationAction::Home);
    app.update();
    assert!(
        !app.world()
            .resource::<navigation::ArchiveNavigation>()
            .is_restoring(),
        "Home cancels unfinished Archive restoration"
    );
    assert!(
        !app.world().resource::<ObserverUiState>().archive_open,
        "Home closes the Archive"
    );
    assert_eq!(
        *app.world().resource::<PrimaryView>(),
        PrimaryView::Organizer,
        "Home returns to organizing without a runtime command"
    );
}
