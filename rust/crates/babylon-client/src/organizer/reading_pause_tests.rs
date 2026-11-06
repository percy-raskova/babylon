//! Focused reading stops scheduling while an already detached tick settles once.

use super::tests;
use super::{OrganizerAction, OrganizerEvidenceRequested};
use crate::observer::ObserverSession;
use crate::observer_io::tests as transport_tests;
use crate::observer_io::ObserverSet;
use crate::organizer::draft::OrganizerDraft;
use crate::organizer::scene::OrganizerSubject;
use crate::organizer::workspace_copy::{DatedLink, Destination};
use crate::organizer::{OrganizerClient, OrganizerInspector};
use babylon_persistence::runtime_session::{
    RuntimeSessionRequest, RuntimeSessionResponse, RuntimeSessionTail,
};
use bevy::prelude::*;
use bevy::time::TimeUpdateStrategy;
use std::time::Duration;

fn reading_app(action: Option<OrganizerAction>) -> (App, Option<OrganizerDraft>) {
    let (mut app, draft) = tests::admitted_scene_fixture();
    if action == Some(OrganizerAction::OpenReferences) {
        app.world_mut().resource_mut::<OrganizerClient>().inspector = OrganizerInspector::Notes;
    }
    if action == Some(OrganizerAction::ArchiveOrganization) {
        app.world_mut().resource_mut::<OrganizerClient>().inspector = OrganizerInspector::Receipts;
    }
    transport_tests::install_playback(&mut app);
    app.add_systems(
        Update,
        super::super::client::transport
            .after(ObserverSet::Receive)
            .before(ObserverSet::Install),
    );
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs(1)));
    (app, draft)
}

#[test]
fn accepted_detail_navigation_pauses_and_settles_one_pending_period_without_restarting() {
    for action in [
        Some(OrganizerAction::Inspect(OrganizerInspector::Evidence)),
        Some(OrganizerAction::OpenReferences),
        Some(OrganizerAction::ArchiveWorkplace),
        Some(OrganizerAction::ArchiveOrganization),
        None,
    ] {
        let (mut app, draft) = reading_app(action);
        let (requests, replies) = transport_tests::install_status_pipe(&mut app);
        let (request_id, scope) = {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.playing = true;
            let scope = session.runtime_scope().cloned().expect("connected scope");
            (session.begin_advance().expect("one detached period"), scope)
        };
        if let Some(action) = action {
            app.world_mut().write_message(action);
        } else {
            app.world_mut().trigger(OrganizerEvidenceRequested);
        }
        app.update();
        let session = app.world().resource::<ObserverSession>();
        assert!(!session.playing, "accepted {action:?} pauses scheduling");
        assert_eq!(session.durable_tick, 3, "reading cannot speculate a commit");
        assert_eq!(
            session.pending_advance_request(),
            Some(request_id),
            "reading cannot cancel an atomic tick"
        );
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.draft, draft);
        assert_eq!(
            client
                .view
                .as_ref()
                .expect("retained view")
                .observations
                .last()
                .expect("retained report")
                .observation_id,
            [3; 32],
            "report identity survives navigation"
        );
        assert!(
            requests.try_recv().is_err(),
            "reading does not send another advance"
        );
        replies
            .send(Ok(RuntimeSessionResponse::Committed {
                request_id,
                scope: scope.clone(),
                tail: RuntimeSessionTail {
                    resolve_tick: 4,
                    tick_content_hash: None,
                    world_hash: None,
                },
            }))
            .expect("live receiver");
        app.update();
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } =
            requests.try_recv().expect("settle Status")
        else {
            panic!("only Status after commit");
        };
        let (_, _, _, mut snapshot) = super::super::tests::status_fixture();
        snapshot.view.period = 4;
        snapshot.body_scope.period = 4;
        snapshot.city_pd_encounters.clear();
        replies
            .send(Ok(RuntimeSessionResponse::OrganizerStatus {
                request_id,
                scope,
                snapshot: Box::new(snapshot),
            }))
            .expect("live receiver");
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            let context = session.context();
            assert!(session.installed(&context));
        }
        app.update();
        app.world_mut()
            .write_message(OrganizerAction::CloseInspector);
        app.update();
        app.update();
        assert!(!app.world().resource::<ObserverSession>().playing);
        assert_eq!(app.world().resource::<ObserverSession>().durable_tick, 4);
        assert_eq!(app.world().resource::<OrganizerClient>().draft, draft);
        assert!(
            requests.try_recv().is_err(),
            "settlement or closing detail cannot resume Play"
        );
    }
}

#[test]
fn plain_subject_selection_and_accepted_subject_links_leave_play_running() {
    for follow in [false, true] {
        let (mut app, draft) = tests::admitted_scene_fixture();
        let subject = OrganizerSubject::NeighborhoodGroup(93);
        let action = if follow {
            let session = app.world().resource::<ObserverSession>();
            OrganizerAction::Follow(DatedLink::new(
                session,
                session.viewed_tick,
                Destination::Subject(subject),
            ))
        } else {
            OrganizerAction::SelectSubject(subject)
        };
        app.world_mut().resource_mut::<ObserverSession>().playing = true;
        app.world_mut().write_message(action);
        app.update();
        assert!(app.world().resource::<ObserverSession>().playing);
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.selected_subject, Some(subject));
        assert_eq!(client.draft, draft);
    }
}
