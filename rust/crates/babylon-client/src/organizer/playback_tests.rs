//! Continuous playback through the real commit, status and observation consumers.

use super::client;
use super::tests;
use super::OrganizerClient;
use super::RequestKind;
use crate::observer::ObserverSession;
use crate::observer_io::tests as transport_tests;
use crate::observer_io::ObserverSet;
use crate::observer_ui::ObserverCommand;
use babylon_persistence::runtime_session::RuntimeSessionResponse;
use babylon_persistence::runtime_session::RuntimeSessionTail;
use babylon_persistence::runtime_session::{
    OrganizerChoice, OrganizerCommitment, OrganizerSnapshot, RuntimeSessionRequest,
};
use bevy::prelude::*;
use std::sync::mpsc::{Receiver, Sender};
use std::time::Duration;

fn playback_app() -> (
    App,
    Receiver<RuntimeSessionRequest>,
    Sender<Result<RuntimeSessionResponse, String>>,
) {
    let (mut client, mut session) = tests::ready();
    client.draft.as_mut().expect("retained draft").choice = OrganizerChoice::Reinforce;
    client.commitment = Some(OrganizerCommitment {
        command: client
            .make_command(&session, OrganizerChoice::Reinforce)
            .expect("reviewed one-off"),
        resolves_period: 4,
        commitment_id: [6; 32],
    });
    session.playing = true;
    let (mut app, _) = transport_tests::command_app();
    app.insert_resource(client).insert_resource(session);
    let (requests, replies) = transport_tests::install_status_pipe(&mut app);
    transport_tests::install_playback(&mut app);
    app.add_systems(
        Update,
        client::transport
            .after(ObserverSet::Receive)
            .before(ObserverSet::Install),
    );
    app.world_mut()
        .resource_mut::<Time>()
        .advance_by(Duration::from_secs(1));
    (app, requests, replies)
}

fn acknowledge(
    app: &App,
    replies: &Sender<Result<RuntimeSessionResponse, String>>,
    request_id: u64,
    period: u64,
) {
    let scope = app
        .world()
        .resource::<ObserverSession>()
        .runtime_scope()
        .cloned()
        .expect("connected scope");
    replies
        .send(Ok(RuntimeSessionResponse::Committed {
            request_id,
            scope,
            tail: RuntimeSessionTail {
                resolve_tick: period,
                tick_content_hash: None,
                world_hash: None,
            },
        }))
        .expect("live fixture receiver");
}

fn next_snapshot(app: &App) -> OrganizerSnapshot {
    let (_, _, _, mut snapshot) = tests::status_fixture();
    let period = app.world().resource::<ObserverSession>().durable_tick;
    snapshot.view.period = period;
    snapshot.body_scope.period = period;
    snapshot.city_pd_encounters.clear();
    snapshot
        .view
        .observations
        .push(babylon_persistence::runtime_session::OrganizerObservation {
            observation_id: [u8::try_from(period).expect("fixture period fits"); 32],
            actor_id: 90,
            subject_id: 91,
            source_actor_id: 92,
            observed_period: period - 1,
            acquired_period: period,
            receipt_id: Some([7; 32]),
            report: babylon_persistence::runtime_session::OrganizerReport::Work {
                performed_labor_hours: 2,
                output_kg: 777,
                previous_labor_hours: None,
                previous_output_kg: None,
            },
        });
    snapshot
}

fn send_status(
    app: &App,
    replies: &Sender<Result<RuntimeSessionResponse, String>>,
    request: RuntimeSessionRequest,
) {
    let RuntimeSessionRequest::OrganizerStatus {
        request_id, scope, ..
    } = request
    else {
        panic!("automatic refresh must only request Status");
    };
    replies
        .send(Ok(RuntimeSessionResponse::OrganizerStatus {
            request_id,
            scope,
            snapshot: Box::new(next_snapshot(app)),
        }))
        .expect("live fixture receiver");
}

fn install_observation(app: &mut App) {
    let mut session = app.world_mut().resource_mut::<ObserverSession>();
    let context = session.context();
    assert!(
        session.installed(&context),
        "only exact committed observation installs"
    );
}

#[test]
fn continuous_organizer_play_waits_for_both_responses_and_never_resubmits_draft() {
    let (mut app, requests, replies) = playback_app();
    let draft = app.world().resource::<OrganizerClient>().draft.clone();
    for period in [4, 5] {
        app.update();
        let RuntimeSessionRequest::Advance {
            request_id,
            expected_tail,
            ..
        } = requests.try_recv().expect("next ready period")
        else {
            panic!("only Advance may run routine work");
        };
        assert_eq!(expected_tail.resolve_tick, period - 1);
        app.update();
        assert!(
            requests.try_recv().is_err(),
            "one outstanding atomic advance"
        );
        acknowledge(&app, &replies, request_id, period);
        app.update();
        assert!(
            app.world().resource::<ObserverSession>().playing,
            "a normal commit must keep Play running"
        );
        let status = requests.try_recv().expect("automatic status refresh");
        if period == 4 {
            install_observation(&mut app);
            app.update();
            assert!(
                requests.try_recv().is_err(),
                "observation alone cannot bypass pending Status"
            );
            send_status(&app, &replies, status);
        } else {
            send_status(&app, &replies, status);
            app.update();
            assert!(
                requests.try_recv().is_err(),
                "Status alone cannot bypass missing observation"
            );
            install_observation(&mut app);
        }
        if period == 5 {
            assert!(
                app.world()
                    .resource::<OrganizerClient>()
                    .commitment
                    .is_none(),
                "consumed one-off stays consumed"
            );
        }
        assert_eq!(
            app.world().resource::<OrganizerClient>().draft,
            draft,
            "draft persists without becoming a submission"
        );
    }
    transport_tests::dispatch(&mut app, &[ObserverCommand::TogglePlay]);
    assert!(!app.world().resource::<ObserverSession>().playing);
    assert!(
        requests.try_recv().is_err(),
        "Pause prevents the next request"
    );
}

#[test]
fn pause_while_status_is_pending_stays_paused_after_settlement_and_step_is_one_period() {
    let (mut app, requests, replies) = playback_app();
    app.update();
    let RuntimeSessionRequest::Advance { request_id, .. } =
        requests.try_recv().expect("first period")
    else {
        panic!("advance");
    };
    acknowledge(&app, &replies, request_id, 4);
    app.update();
    let status = requests.try_recv().expect("status");
    // The manual Pause must remain enabled during the automatic status refresh.
    app.world_mut().resource_mut::<ObserverSession>().playing = true;
    transport_tests::dispatch(&mut app, &[ObserverCommand::TogglePlay]);
    assert!(
        !app.world().resource::<ObserverSession>().playing,
        "Pause is available while Status is pending"
    );
    send_status(&app, &replies, status);
    install_observation(&mut app);
    app.update();
    app.update();
    assert!(
        requests.try_recv().is_err(),
        "settlement must never restart Play"
    );
    transport_tests::dispatch(&mut app, &[ObserverCommand::Speed]);
    assert!(
        requests.try_recv().is_err(),
        "Speed changes pace without advancing or confirming"
    );
    transport_tests::dispatch(&mut app, &[ObserverCommand::Step]);
    let RuntimeSessionRequest::Advance { request_id, .. } =
        requests.try_recv().expect("one manual period")
    else {
        panic!("advance");
    };
    assert!(!app.world().resource::<ObserverSession>().playing);
    acknowledge(&app, &replies, request_id, 5);
    app.update();
    send_status(&app, &replies, requests.try_recv().expect("step status"));
    install_observation(&mut app);
    app.update();
    app.update();
    assert!(
        requests.try_recv().is_err(),
        "Step cannot become continuous Play"
    );
}

#[test]
fn only_a_new_admitted_current_city_pd_notice_pauses_play() {
    for case in ["new", "repeated", "old", "hidden", "foreign", "stale"] {
        let (mut client, mut session, request, mut snapshot) = tests::status_fixture();
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
            panic!("status");
        };
        snapshot.city_pd_encounters[0].resolve_period = 3;
        match case {
            "repeated" => client.city_pd_encounters = snapshot.city_pd_encounters.clone(),
            "old" => snapshot.city_pd_encounters[0].resolve_period = 2,
            "hidden" => snapshot.city_pd_encounters.clear(),
            "foreign" => snapshot.city_pd_encounters[0].controlled_actor_id += 1,
            "stale" => session.generation += 1,
            "new" => {}
            _ => unreachable!(),
        }
        session.playing = true;
        let result = client.status(request_id, snapshot, &mut session);
        assert_eq!(session.playing, case != "new", "{case}");
        if case == "new" {
            assert!(
                client.message.contains("City PD") && client.message.contains("paused"),
                "readable development reason: {}",
                client.message
            );
        }
        assert_eq!(result.is_err(), case == "foreign", "{case}");
    }
}

#[test]
fn a_matched_status_refusal_pauses_but_an_unrelated_response_cannot_change_play() {
    for matched in [false, true] {
        let (mut client, mut session, request, _) = tests::status_fixture();
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
            panic!("status fixture");
        };
        session.playing = true;
        assert_eq!(
            client.refused(
                Some(if matched { request_id } else { request_id + 1 }),
                "Refresh refused".into(),
                &mut session
            ),
            matched,
            "only the outstanding request can be refused"
        );
        assert_eq!(
            session.playing, !matched,
            "a real failure stops future scheduling"
        );
        if matched {
            assert_eq!(
                client.message, "Refresh refused",
                "actionable failure stays visible"
            );
        }
    }
}

use babylon_persistence::runtime_session::{
    OrganizerAidResolution, OrganizerBodyDisclosure, OrganizerBodyScope,
    OrganizerCollectionResolution, OrganizerView,
};

#[derive(serde::Deserialize)]
struct DevelopmentPeriod {
    view: OrganizerView,
    collection_resolutions: Vec<OrganizerCollectionResolution>,
    aid_resolutions: Vec<OrganizerAidResolution>,
}

#[test]
fn new_national_developments_pause_with_short_feedback_and_retain_full_dated_facts() {
    let periods: Vec<DevelopmentPeriod> = serde_json::from_str(include_str!(
        "../../tests/fixtures/wayne_public_developments_v19.json"
    ))
    .expect("captured national collection, payment and shortfalls");
    let opening: OrganizerSnapshot = serde_json::from_str(include_str!(
        "../../../babylon-persistence/tests/fixtures/national_organizer_opening_v19.json"
    ))
    .expect("actual opening seeds existing notices");
    let (mut client, mut session) = tests::ready();
    client.developments.install(&opening.view, &[], &[]);
    for row in periods {
        let period = row.view.period;
        session.ready(period, None);
        assert!(session.installed(&session.context()));
        client.view = None;
        client.queue(&mut session, RequestKind::Status, None);
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } =
            client.outbox.take().expect("status")
        else {
            panic!("only Status requested");
        };
        let body_scope = OrganizerBodyScope {
            campaign_id: *session.campaign.canonical_bytes(),
            actor_id: row.view.actor_id,
            period,
            content_digest: row.view.content_digest,
            source: None,
        };
        let snapshot = OrganizerSnapshot {
            view: row.view,
            collection_resolutions: row.collection_resolutions,
            aid_resolutions: row.aid_resolutions,
            body: OrganizerBodyDisclosure::Unavailable,
            body_scope,
            duration: opening.duration,
            pending: None,
            collection: None,
            aid: vec![],
            pending_aid: vec![],
            city_pd_encounters: vec![],
        };
        session.playing = true;
        client
            .status(request_id, snapshot, &mut session)
            .expect("admitted factual status");
        assert!(!session.playing, "new P{period} development pauses Play");
        assert!(
            client.message.contains(&format!("P{period} dispatch"))
                && client.message.contains("Read"),
            "dated acknowledgement points to existing reading: {}",
            client.message
        );
        assert!(
            !client.message.contains("unmet") && !client.message.contains("Requested $"),
            "full result belongs to dispatch/report, not persistent decision feedback: {}",
            client.message
        );
        let view = client.view.as_ref().expect("admitted view");
        let dispatch = super::workspace::dispatch(&client, period).expect("dated dispatch");
        let practices = super::presentation::dispatch_practices(&dispatch);
        let reports = view
            .observations
            .iter()
            .filter(|row| row.acquired_period == period)
            .map(|row| {
                format!(
                    "{} {}",
                    super::presentation::report_caption(row),
                    super::presentation::report(&row.report)
                )
            })
            .collect::<Vec<_>>()
            .join("\n");
        if period == 1 {
            assert!(
                practices.contains("$1,450.00") && practices.contains("2 shared material hours"),
                "{practices}"
            );
        }
        if period == 2 {
            let support = super::developments::current_support(&client.aid_resolutions, period);
            assert!(
                support.contains("$1,450.00") && support.contains("P2 partner response"),
                "{support}"
            );
        }
        assert!(
            reports.contains("unmet") && reports.contains(&format!("{period}")),
            "exact current reports remain: {reports}"
        );
    }
}
