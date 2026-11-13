//! Historical organizer status responses retain their current navigation context.

use super::tests;
use super::OrganizerAction;
use crate::observer::{ObserverSession, SessionPhase};
use crate::observer_io::ObserverSet;
use crate::organizer::scene::{OrganizerSceneMode, OrganizerSubject};
use crate::organizer::OrganizerClient;
use babylon_persistence::runtime_session::{
    OrganizerChoice, RuntimeSessionRequest, RuntimeSessionResponse,
};
use bevy::input_focus::InputFocus;
use bevy::prelude::*;

#[test]
fn historical_navigation_reconciles_stale_status_without_disconnecting() {
    let (mut app, focus, draft) = tests::organizer_navigation();
    let (mut client, session, request, snapshot) = crate::organizer::tests::status_fixture();
    client.draft = Some(draft.clone());
    let command = client
        .make_command(&session, OrganizerChoice::Hold)
        .expect("fixture command");
    client.preview = Some(tests::preview_for(&command));
    client.reviewed_command = Some(command);
    client.review_context = Some(session.context());
    app.insert_resource(client).insert_resource(session);
    let (requests, replies) = crate::observer_io::tests::install_status_pipe(&mut app);
    app.add_systems(
        Update,
        super::super::transport
            .after(ObserverSet::Receive)
            .before(ObserverSet::Paint),
    );
    let RuntimeSessionRequest::OrganizerStatus {
        scope, request_id, ..
    } = request
    else {
        panic!("expected status request");
    };
    {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        session.inspect_tick(1);
        let context = session.context();
        assert!(session.installed(&context));
    }
    replies
        .send(Ok(RuntimeSessionResponse::OrganizerStatus {
            scope: scope.clone(),
            request_id,
            snapshot: Box::new(snapshot.clone()),
        }))
        .expect("response receiver remains open");
    app.update();
    let session = app.world().resource::<ObserverSession>();
    assert!(
        !session.runtime_disconnected(),
        "local navigation must not disconnect the runtime"
    );
    assert_ne!(session.phase, SessionPhase::Failed);
    let client = app.world().resource::<OrganizerClient>();
    assert_eq!(
        client
            .view
            .as_ref()
            .expect("original view")
            .organization_label,
        "Fixture collective"
    );
    assert_eq!(client.city_pd_encounters.len(), 0);
    assert_eq!(client.draft.as_ref(), Some(&draft));
    assert!(client.reviewed_command.is_none());
    assert_eq!(app.world().resource::<InputFocus>().get(), Some(focus));
    let RuntimeSessionRequest::OrganizerStatus {
        request_id: retry_id,
        scope: retry_scope,
        ..
    } = requests.try_recv().expect("fresh status requested")
    else {
        panic!("expected fresh status");
    };
    assert_ne!(retry_id, request_id);
    assert_eq!(retry_scope, scope);
    replies
        .send(Ok(RuntimeSessionResponse::OrganizerStatus {
            scope: retry_scope,
            request_id: retry_id,
            snapshot: Box::new(snapshot),
        }))
        .expect("response receiver remains open");
    app.update();
    let client = app.world().resource::<OrganizerClient>();
    assert_eq!(
        client
            .view
            .as_ref()
            .expect("updated view")
            .organization_label,
        "Updated collective"
    );
    assert_eq!(client.city_pd_encounters.len(), 1);
    assert_eq!(client.draft.as_ref(), Some(&draft));
    assert!(client.reviewed_command.is_none());
    assert_eq!(app.world().resource::<InputFocus>().get(), Some(focus));
    assert!(!app
        .world()
        .resource::<ObserverSession>()
        .runtime_disconnected());
}

#[test]
fn settled_scene_refreshes_after_history_and_return_live() {
    use babylon_persistence::runtime_session::RuntimeSessionErrorCode;
    let (mut client, mut session, request, snapshot) = super::super::tests::status_fixture();
    let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
        panic!("initial status request");
    };
    client
        .status(request_id, snapshot.clone(), &mut session)
        .expect("settled live status");
    client.scene_mode = OrganizerSceneMode::Relationships;
    let (mut app, _, draft) = tests::organizer_navigation();
    client.draft = Some(draft.clone());
    app.insert_resource(client).insert_resource(session);
    let (requests, replies) = crate::observer_io::tests::install_status_pipe(&mut app);
    app.add_systems(
        Update,
        super::super::transport
            .after(ObserverSet::Receive)
            .before(ObserverSet::Paint),
    );
    app.update();
    let neighborhood = OrganizerSubject::NeighborhoodGroup(93);
    app.world_mut()
        .write_message(OrganizerAction::SelectSubject(neighborhood));
    app.update();
    assert!(tests::scene_text(&mut app).contains("Collective structure unknown"));
    assert!(requests.try_recv().is_err());
    tests::inspect_period(&mut app, 2);
    app.update();
    let RuntimeSessionRequest::OrganizerStatus {
        scope, request_id, ..
    } = requests.try_recv().expect("history status requested")
    else {
        panic!("history status request");
    };
    assert!(tests::scene_text(&mut app).contains("Loading organizer scene"));
    assert!(!tests::scene_text(&mut app).contains("Fixture workplace"));
    replies
        .send(Ok(RuntimeSessionResponse::Error {
            scope,
            request_id: Some(request_id),
            code: RuntimeSessionErrorCode::StorageRefused,
            tail: None,
        }))
        .expect("history refusal");
    app.update();
    assert!(tests::scene_text(&mut app).contains("StorageRefused"));
    app.update();
    assert!(
        requests.try_recv().is_err(),
        "a matching refusal must not retry"
    );
    {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        session.return_live();
        let context = session.context();
        assert!(session.installed(&context));
    }
    app.update();
    let RuntimeSessionRequest::OrganizerStatus {
        scope, request_id, ..
    } = requests.try_recv().expect("returned live status requested")
    else {
        panic!("returned live status request");
    };
    assert!(tests::scene_text(&mut app).contains("Loading organizer scene"));
    replies
        .send(Ok(RuntimeSessionResponse::OrganizerStatus {
            scope,
            request_id,
            snapshot: Box::new(snapshot),
        }))
        .expect("validated live status");
    app.update();
    assert!(tests::scene_text(&mut app).contains("Collective structure unknown"));
    let client = app.world().resource::<OrganizerClient>();
    assert_eq!(client.selected_subject, Some(neighborhood));
    assert_eq!(client.draft.as_ref(), Some(&draft));
    assert!(client
        .scene_for(app.world().resource::<ObserverSession>())
        .is_some());
    app.update();
    assert!(
        requests.try_recv().is_err(),
        "settled context must not retry"
    );
}

#[test]
fn stale_status_refusal_requeues_the_returned_live_context() {
    use babylon_persistence::runtime_session::RuntimeSessionErrorCode;
    let (client, session, request, snapshot) = super::super::tests::status_fixture();
    let RuntimeSessionRequest::OrganizerStatus {
        scope, request_id, ..
    } = request
    else {
        panic!("status request")
    };
    let (mut app, _, _) = tests::organizer_navigation();
    app.insert_resource(client).insert_resource(session);
    let (requests, replies) = crate::observer_io::tests::install_status_pipe(&mut app);
    app.add_systems(
        Update,
        super::super::transport
            .after(ObserverSet::Receive)
            .before(ObserverSet::Paint),
    );
    tests::inspect_period(&mut app, 2);
    tests::inspect_period(&mut app, 3);
    replies
        .send(Ok(RuntimeSessionResponse::Error {
            scope: scope.clone(),
            request_id: Some(request_id),
            code: RuntimeSessionErrorCode::StorageRefused,
            tail: None,
        }))
        .expect("refusal delivered");
    app.update();
    let RuntimeSessionRequest::OrganizerStatus {
        request_id: retry_id,
        scope: retry_scope,
        ..
    } = requests.try_recv().expect("fresh status requested")
    else {
        panic!("replacement status")
    };
    assert_ne!(retry_id, request_id);
    assert_eq!(retry_scope, scope);
    assert!(tests::scene_text(&mut app).contains("Loading organizer scene"));
    assert!(!tests::scene_text(&mut app).contains("StorageRefused"));
    replies
        .send(Ok(RuntimeSessionResponse::OrganizerStatus {
            scope: retry_scope,
            request_id: retry_id,
            snapshot: Box::new(snapshot),
        }))
        .expect("replacement delivered");
    app.update();
    let client = app.world().resource::<OrganizerClient>();
    let session = app.world().resource::<ObserverSession>();
    assert!(!client.status_due);
    assert!(client.pending.is_none());
    assert!(client.scene_for(session).is_some());
    assert!(!session.runtime_disconnected());
}
