//! Native organizational decisions over the one authoritative runtime connection.

#[cfg(test)]
use crate::observer::Perspective;
#[cfg(test)]
use babylon_persistence::ArchiveEvidenceClass;
mod draft;

mod editor;

mod evidence;

mod presentation;

mod scene;

mod board;
mod workspace;
pub(crate) use board::Overlay as OrganizerOverlay;
mod workspace_copy;

pub(crate) mod qualification_input;

pub(crate) mod ui;

#[path = "organizer/client.rs"]
mod client;

#[cfg(test)]
use client::transport;
pub use client::OrganizerPlugin;
use client::RequestKind;
pub(crate) use client::{report_reading, OrganizerClient, OrganizerInspector, StatusDisposition};

#[cfg(test)]
use crate::observer::{ObserverSession, SessionPhase};
#[cfg(test)]
use babylon_persistence::runtime_session::{
    OrganizerAidPending, OrganizerChoice, OrganizerCollectionPreview, OrganizerCommand,
    OrganizerCommitment, OrganizerMaterialAidPreview, OrganizerPreview, OrganizerSnapshot,
    OrganizerView, RuntimeSessionRequest,
};
#[cfg(test)]
use draft::OrganizerDraft;

#[cfg(test)]
use bevy::prelude::*;

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use babylon_persistence::identity::CampaignId;
    use babylon_persistence::runtime_session::OrganizerAidKind;
    use babylon_persistence::runtime_session::OrganizerAidTransportPreview;
    use babylon_persistence::runtime_session::OrganizerGiftConsent;
    use babylon_persistence::runtime_session::{
        CityPdEncounter, OrganizerAgreement, OrganizerBodyDisclosure, OrganizerBodyPart,
        OrganizerBodyScope, OrganizerBodySource, OrganizerObservation, OrganizerPosition,
        OrganizerReport, OrganizerStandingWork, CITY_PD_ENCOUNTER_SCHEMA_VERSION,
    };
    use uuid::Uuid;

    pub(crate) fn body_scope() -> OrganizerBodyScope {
        OrganizerBodyScope {
            campaign_id: *Uuid::from_u128(927).as_bytes(),
            actor_id: 90,
            period: 3,
            content_digest: [2; 32],
            source: None,
        }
    }

    pub(crate) fn ready() -> (OrganizerClient, ObserverSession) {
        let campaign = Uuid::from_u128(927);
        let mut session = ObserverSession::new(CampaignId::from_uuid(campaign));
        session.connected_fixture();
        session.ready(3, None);
        assert!(session.installed(&session.context()));
        session.organizer_enabled = true;
        let view = OrganizerView {
            period: 3,
            actor_id: 90,
            authority_id: [1; 16],
            organization_label: "Fixture collective".into(),
            workplace_id: 91,
            workplace_label: "Fixture workplace".into(),
            workplace_partner_id: 92,
            workplace_partner_label: "Fixture workplace contacts".into(),
            neighborhood_partner_id: 93,
            neighborhood_partner_label: "Fixture neighborhood contacts".into(),
            available_hours: 16,
            inquiry_hours: 12,
            contact_hours: 8,
            public_workplace_contact: false,
            content_digest: [2; 32],
            resource_digest: [3; 32],
            standing: OrganizerStandingWork {
                partner_actor_id: 93,
                authorized: true,
                paused_reason: None,
            },
            agreements: Vec::new(),
            total_observation_count: 0,
            observations: Vec::new(),
            total_receipt_count: 0,
            receipts: Vec::new(),
            positions: Vec::new(),
            aid_options: Vec::new(),
        };
        (
            OrganizerClient {
                campaign: Some(campaign),
                draft: Some(OrganizerDraft::new(91)),
                view: Some(view),
                ..default()
            },
            session,
        )
    }

    pub(crate) fn status_fixture() -> (
        OrganizerClient,
        ObserverSession,
        RuntimeSessionRequest,
        OrganizerSnapshot,
    ) {
        let (mut client, mut session) = ready();
        client.queue(&mut session, RequestKind::Status, None);
        let request = client.outbox.take().expect("status request queued");
        let mut view = client.view.clone().expect("fixture view");
        view.organization_label = "Updated collective".into();
        let snapshot = OrganizerSnapshot {
            body: OrganizerBodyDisclosure::Unavailable,
            body_scope: body_scope(),
            collection: None,
            collection_resolutions: Vec::new(),
            aid: Vec::new(),
            pending_aid: Vec::new(),
            aid_resolutions: Vec::new(),
            city_pd_encounters: vec![encounter_fixture()],
            view,
            pending: None,
            duration: babylon_kernel::clock::CampaignDuration::Finite { final_period: 16 },
        };
        (client, session, request, snapshot)
    }

    pub(crate) fn encounter_fixture() -> CityPdEncounter {
        CityPdEncounter {
            schema_version: CITY_PD_ENCOUNTER_SCHEMA_VERSION,
            campaign_id: *Uuid::from_u128(927).as_bytes(),
            controlled_actor_id: 90,
            authority_id: [1; 16],
            content_digest: [2; 32],
            resource_digest: [3; 32],
            subject_id: 91,
            resolve_period: 2,
            visitor_actor_id: 94,
            receipt_id: [4; 32],
            venue_source_id: [5; 32],
            visit_core_id: [6; 32],
            access_evidence_id: [7; 32],
        }
    }

    #[test]
    fn organizer_body_scope_refuses_stale_and_foreign() {
        let (mut client, mut session, request, snapshot) = status_fixture();
        session.inspect_tick(2);
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
            panic!("fixture queues organizer status");
        };
        let previous = client.view.clone();
        assert_eq!(
            client.status(request_id, snapshot, &mut session),
            Ok(StatusDisposition::Superseded),
            "a response captured before history navigation is superseded"
        );
        assert_eq!(
            client.view, previous,
            "superseded status preserves the view"
        );

        client.queue(&mut session, RequestKind::Status, None);
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } =
            client.outbox.take().expect("history status queued")
        else {
            panic!("fixture queues organizer status");
        };
        let (_, _, _, snapshot) = status_fixture();
        assert_eq!(
            client.status(request_id, snapshot, &mut session),
            Ok(StatusDisposition::Installed),
            "the existing period-filtered view remains available"
        );
        let (body, scope) = client.body_for(&session).expect("historical availability");
        assert_eq!(*body, OrganizerBodyDisclosure::Unavailable);
        assert_eq!(scope.period, 2);
        assert_eq!(scope.source, None);
    }

    #[test]
    fn organizer_body_scope_refuses_foreign_metadata() {
        for field in ["campaign", "actor", "period", "content", "missing_source"] {
            let (mut client, mut session, request, mut snapshot) = status_fixture();
            let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
                panic!("initial status request")
            };
            assert_eq!(
                client.status(request_id, snapshot.clone(), &mut session),
                Ok(StatusDisposition::Installed)
            );
            let previous_body = client
                .body_for(&session)
                .map(|(body, scope)| (body.clone(), scope.clone()));
            client.queue(&mut session, RequestKind::Status, None);
            let request = client.outbox.take().expect("second status request");
            match field {
                "campaign" => snapshot.body_scope.campaign_id = [8; 16],
                "actor" => snapshot.body_scope.actor_id += 1,
                "period" => snapshot.body_scope.period += 1,
                "content" => snapshot.body_scope.content_digest = [9; 32],
                "missing_source" => snapshot.body = OrganizerBodyDisclosure::KnownAbsent,
                _ => unreachable!(),
            }
            let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
                panic!("status request")
            };
            let previous = client.view.clone();
            assert!(
                client.status(request_id, snapshot, &mut session).is_err(),
                "refuse {field}"
            );
            assert_eq!(
                client.view, previous,
                "refusal preserves prior view for {field}"
            );
            assert_eq!(
                client
                    .body_for(&session)
                    .map(|(body, scope)| (body.clone(), scope.clone())),
                previous_body,
                "refusal preserves admitted body for {field}"
            );
        }
    }

    #[test]
    fn organizer_body_scope_refuses_stale_context() {
        for field in [
            "perspective",
            "generation",
            "viewed",
            "freshness",
            "tail_hash",
            "world_hash",
            "foundation",
        ] {
            let (mut client, mut session, request, snapshot) = status_fixture();
            let previous = client.view.clone();
            match field {
                "perspective" => {
                    session.set_perspective(Perspective::PlayerKnowledge);
                }
                "generation" => session.generation += 1,
                "viewed" => session.inspect_tick(2),
                "freshness" => session.durable_tick += 1,
                "tail_hash" => session.content_hash = Some("04".repeat(32)),
                "world_hash" => session.world_hash = Some("05".repeat(32)),
                "foundation" => session.foundation_digest = Some("05".repeat(32)),
                _ => unreachable!(),
            }
            let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
                panic!("status request")
            };
            assert_ne!(
                client.status(request_id, snapshot, &mut session),
                Ok(StatusDisposition::Installed),
                "stale {field} cannot install"
            );
            assert_eq!(client.view, previous, "stale {field} preserves prior view");
        }
    }

    fn populate_partial_body(snapshot: &mut OrganizerSnapshot) {
        snapshot.view.positions = [101, 102]
            .into_iter()
            .map(|contributor_id| OrganizerPosition {
                contributor_id,
                label: "Known".into(),
                promised_hours: 1,
                concern: String::new(),
                objection: String::new(),
                review_condition: String::new(),
            })
            .collect();
        snapshot.body = OrganizerBodyDisclosure::Partial(OrganizerBodyPart {
            runtime_hyperedge_id: 7,
            scenario: "economy/national-world".into(),
            local_name: "organizer-participant-body-90".into(),
            contributors: vec![101, 102],
            evidence_class: ArchiveEvidenceClass::Designed,
        });
    }

    #[test]
    fn organizer_body_scope_validates_committed_disclosure() {
        for field in [
            "valid",
            "known_absent",
            "foreign_hash",
            "foreign_world_hash",
            "hidden_contributor",
            "unordered",
            "unattributed",
        ] {
            let (mut client, mut session, _, mut snapshot) = status_fixture();
            client.pending = None;
            client.outbox = None;
            session.content_hash = Some("04".repeat(32));
            session.world_hash = Some("05".repeat(32));
            client.queue(&mut session, RequestKind::Status, None);
            let request = client.outbox.take().expect("status request");
            snapshot.body_scope.source = Some(OrganizerBodySource::Committed {
                tick_content_hash: [4; 32],
                world_hash: [5; 32],
            });
            populate_partial_body(&mut snapshot);
            match field {
                "foreign_hash" => {
                    snapshot.body_scope.source = Some(OrganizerBodySource::Committed {
                        tick_content_hash: [6; 32],
                        world_hash: [5; 32],
                    });
                }
                "foreign_world_hash" => {
                    snapshot.body_scope.source = Some(OrganizerBodySource::Committed {
                        tick_content_hash: [4; 32],
                        world_hash: [6; 32],
                    });
                }
                "hidden_contributor" => {
                    if let OrganizerBodyDisclosure::Partial(part) = &mut snapshot.body {
                        part.contributors.push(103);
                    }
                }
                "unordered" => {
                    if let OrganizerBodyDisclosure::Partial(part) = &mut snapshot.body {
                        part.contributors.reverse();
                    }
                }
                "unattributed" => {
                    if let OrganizerBodyDisclosure::Partial(part) = &mut snapshot.body {
                        part.evidence_class = ArchiveEvidenceClass::Observed;
                    }
                }
                "known_absent" => snapshot.body = OrganizerBodyDisclosure::KnownAbsent,
                "valid" => {}
                _ => unreachable!(),
            }
            let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
                panic!("status request")
            };
            let prior = client.view.clone();
            let result = client.status(request_id, snapshot, &mut session);
            if field == "valid" || field == "known_absent" {
                assert_eq!(result, Ok(StatusDisposition::Installed));
                if field == "valid" {
                    assert!(matches!(
                        client.body_for(&session),
                        Some((OrganizerBodyDisclosure::Partial(_), _))
                    ));
                    session.world_hash = Some("06".repeat(32));
                    assert!(
                        client.body_for(&session).is_none(),
                        "changed admitted world invalidates body"
                    );
                    session.world_hash = Some("05".repeat(32));
                } else {
                    assert!(matches!(
                        client.body_for(&session),
                        Some((OrganizerBodyDisclosure::KnownAbsent, _))
                    ));
                }
                session.durable_tick += 1;
                assert!(
                    client.body_for(&session).is_none(),
                    "advance invalidates admitted body"
                );
            } else {
                assert!(result.is_err(), "refuse {field}");
                assert_eq!(client.view, prior, "refusal preserves prior view");
            }
        }
    }

    #[test]
    fn organizer_body_foundation_source_requires_admitted_digest() {
        let (mut client, mut session, _, mut snapshot) = status_fixture();
        client.pending = None;
        client.outbox = None;
        session.ready(0, None);
        assert!(session.installed(&session.context()));
        session.foundation_digest = Some("04".repeat(32));
        snapshot.view.period = 0;
        snapshot.city_pd_encounters.clear();
        snapshot.body = OrganizerBodyDisclosure::KnownAbsent;
        snapshot.body_scope.period = 0;
        snapshot.body_scope.source = Some(OrganizerBodySource::Foundation {
            foundation_digest: [4; 32],
        });
        client.queue(&mut session, RequestKind::Status, None);
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } =
            client.outbox.take().expect("status request")
        else {
            panic!("status request")
        };
        assert_eq!(
            client.status(request_id, snapshot.clone(), &mut session),
            Ok(StatusDisposition::Installed)
        );
        let prior = client.view.clone();
        client.queue(&mut session, RequestKind::Status, None);
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } =
            client.outbox.take().expect("second request")
        else {
            panic!("status request")
        };
        snapshot.body_scope.source = Some(OrganizerBodySource::Foundation {
            foundation_digest: [5; 32],
        });
        assert!(client.status(request_id, snapshot, &mut session).is_err());
        assert_eq!(
            client.view, prior,
            "foreign foundation cannot replace admitted view"
        );
    }

    fn aid_fixture() -> OrganizerMaterialAidPreview {
        OrganizerMaterialAidPreview {
            kind: OrganizerAidKind::Local,
            mandate_id: [4; 32],
            period: 3,
            donor_id: [5; 32],
            recipient_id: [6; 32],
            good_id: [7; 32],
            unit_id: [8; 32],
            donor_stock: 12,
            own_need: 4,
            grams_per_unit: 1000,
            payer_cash: 120,
            gift_cash_per_unit: 10,
            ordinary_offer: None,
            maximum_quantity: 8,
            labor_unit_id: [9; 32],
            fulfillment_hours_per_unit: 2,
            coordination_hours: 3,
            receiving_consent: OrganizerGiftConsent::Accept,
            time: None,
            transport: OrganizerAidTransportPreview::Local,
        }
    }

    #[test]
    fn aid_requires_current_authenticated_preview_offered_consent_and_no_pending_kind() {
        let (mut client, _) = ready();
        client
            .view
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .aid_options
            .push(babylon_persistence::runtime_session::OrganizerAidOption {
                kind: OrganizerAidKind::Local,
                partner_actor_id: 95,
                partner_label: "Recipient collective".into(),
                coordination_hours: 3,
                receiving_consent: OrganizerGiftConsent::Accept,
            });
        assert!(!client.choice_available(OrganizerChoice::LocalAid));
        client.aid.push(aid_fixture());
        assert!(client.choice_available(OrganizerChoice::LocalAid));
        assert!(!client.choice_available(OrganizerChoice::RemoteAid));
        client.aid[0].period = 2;
        assert!(!client.choice_available(OrganizerChoice::LocalAid));
        client.aid[0].period = 3;
        client.aid[0].receiving_consent = OrganizerGiftConsent::Refuse;
        assert!(!client.choice_available(OrganizerChoice::LocalAid));
        client.aid[0].receiving_consent = OrganizerGiftConsent::Accept;
        client.pending_aid.push(OrganizerAidPending {
            kind: client.aid[0].kind,
            original_commitment_id: [10; 32],
            material_commitment_id: [11; 32],
            mandate_id: [4; 32],
            admitted_period: 1,
            dispatch_period: 2,
            good_id: [7; 32],
            unit_id: [8; 32],
        });
        assert!(!client.choice_available(OrganizerChoice::LocalAid));
        assert!(client.choice_available(OrganizerChoice::Hold));
    }

    #[test]
    fn submission_is_one_reviewed_command_and_history_cannot_act() {
        let (mut client, mut session) = ready();
        assert!(client.available(&session));
        session.inspect_tick(2);
        assert!(session.installed(&session.context()));
        assert!(!client.available(&session));
        session.inspect_tick(3);
        assert!(session.installed(&session.context()));
        let command = client
            .make_command(&session, OrganizerChoice::Reinforce)
            .expect("the fixture command builds");
        client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
        let request_id = client
            .pending
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .id;
        client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
        assert_eq!(
            client
                .pending
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .id,
            request_id
        );
        assert!(session.begin_advance().is_none());
        assert!(!session.start_playback());
        assert!(
            matches!(client.outbox.take(), Some(RuntimeSessionRequest::SubmitOrganizer { command: sent, .. }) if sent == command)
        );
        client
            .accepted(
                request_id,
                OrganizerCommitment {
                    command,
                    resolves_period: 4,
                    commitment_id: [4; 32],
                },
                &mut session,
            )
            .expect("the fixture call `accepted` succeeds for the authored inputs");
        assert!(!client.available(&session));
        assert!(!session.organizer_control_pending());
        assert!(session.begin_advance().is_some());
    }

    #[test]
    fn acceptance_rejects_an_unreviewed_nonce_or_resolving_period() {
        for wrong_nonce in [false, true] {
            let (mut client, mut session) = ready();
            let command = client
                .make_command(&session, OrganizerChoice::Hold)
                .expect("the fixture command builds");
            client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
            let request_id = client
                .pending
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .id;
            let mut commitment = OrganizerCommitment {
                command,
                resolves_period: 4,
                commitment_id: [4; 32],
            };
            if wrong_nonce {
                commitment.command.nonce = [9; 16];
            } else {
                commitment.resolves_period = 5;
            }
            assert!(client
                .accepted(request_id, commitment, &mut session)
                .is_err());
            assert!(client.commitment.is_none());
        }
    }

    #[test]
    fn restored_pending_ruling_is_status_and_preserves_the_presentation_draft() {
        let (mut client, mut session) = ready();
        client
            .draft
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .notes
            .insert("Keep this objection.");
        client
            .draft
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .choice = OrganizerChoice::Hold;
        let accepted = OrganizerCommitment {
            command: client
                .make_command(&session, OrganizerChoice::Reinforce)
                .expect("the fixture command builds"),
            resolves_period: 4,
            commitment_id: [4; 32],
        };
        client.queue(&mut session, RequestKind::Status, None);
        let request_id = client
            .pending
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .id;
        assert!(matches!(
            client.outbox.take(),
            Some(RuntimeSessionRequest::OrganizerStatus { .. })
        ));
        client
            .status(
                request_id,
                OrganizerSnapshot {
                    body: OrganizerBodyDisclosure::Unavailable,
                    body_scope: body_scope(),
                    collection: None,
                    collection_resolutions: Vec::new(),
                    aid: Vec::new(),
                    pending_aid: Vec::new(),
                    aid_resolutions: Vec::new(),
                    city_pd_encounters: Vec::new(),
                    view: client.view.clone().expect("the fixture value clones"),
                    pending: Some(accepted.clone()),
                    duration: babylon_kernel::clock::CampaignDuration::Finite { final_period: 16 },
                },
                &mut session,
            )
            .expect("the fixture command reports its status");
        assert_eq!(client.commitment, Some(accepted));
        assert_eq!(client.choice(), OrganizerChoice::Hold);
        assert_eq!(
            client
                .draft
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .notes
                .text,
            "Keep this objection."
        );
        assert!(!client.available(&session));
        assert!(client.outbox.is_none());
        assert!(client.reviewed_command.is_none());
    }

    #[test]
    fn status_with_new_disclosure_invalidates_review() {
        let (mut client, mut session, request, mut snapshot) = status_fixture();
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
            panic!("expected status request");
        };
        snapshot.view = client.view.clone().expect("fixture view");
        session.duration = Some(snapshot.duration);
        let command = client
            .make_command(&session, OrganizerChoice::Hold)
            .expect("fixture command");
        client.review_context = Some(session.context());
        client.reviewed_command = Some(command.clone());
        client.preview = Some(OrganizerPreview {
            choice: command.choice,
            current_period: command.expected_period,
            resolves_period: command.expected_period + 1,
            available_hours: 16,
            required_hours: 8,
            replaces_standing_work: true,
            refusal: None,
            observations: Vec::new(),
        });
        client
            .status(request_id, snapshot, &mut session)
            .expect("coherent status");
        assert!(client.reviewed_command.is_none());
        assert!(client.preview.is_none());
    }

    #[test]
    fn held_evidence_withholds_later_reports_and_labels_live_agreements() {
        let (mut client, _) = ready();
        let view = client
            .view
            .as_mut()
            .expect("the fixture set the optional field before this borrow");
        view.observations.push(OrganizerObservation {
            observation_id: [1; 32],
            actor_id: view.actor_id,
            subject_id: view.workplace_id,
            source_actor_id: view.workplace_partner_id,
            observed_period: 1,
            acquired_period: 3,
            receipt_id: Some([5; 32]),
            report: OrganizerReport::Work {
                performed_labor_hours: 888,
                output_kg: 999,
                previous_labor_hours: None,
                previous_output_kg: None,
            },
        });
        view.agreements.push(OrganizerAgreement {
            actor_id: view.actor_id,
            partner_actor_id: view.workplace_partner_id,
            valid_from_period: 3,
            valid_through_period: 5,
            source_product_id: Some([6; 32]),
        });
        client.inspector = OrganizerInspector::Evidence;
        let (_, held) = presentation::inspector(&client, 2);
        assert!(!held.contains("999"));
        let (_, current) = presentation::inspector(&client, 3);
        assert!(current.contains("999 kg"));
        assert!(current.contains("Acquired period 3"));
        assert!(current.contains("HISTORICAL REPORT"));
        client.inspector = OrganizerInspector::Relationships;
        let (_, held_relationships) = presentation::inspector(&client, 2);
        assert!(
            held_relationships.contains("CURRENT COMMUNICATION AGREEMENTS · committed period 3")
        );
        assert!(held_relationships.contains("Held history is period 2"));
        assert!(held_relationships.contains("periods 3"));
        assert!(presentation::inspector(&client, 3).1.contains("periods 3"));
    }
    #[test]
    fn completed_status_keeps_the_final_observation_load_and_then_closes_decisions() {
        for already_loaded in [false, true] {
            let (mut client, mut session) = ready();
            if !already_loaded {
                session.phase = SessionPhase::Loading;
            }
            client.queue(&mut session, RequestKind::Status, None);
            let request_id = client
                .pending
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .id;
            client.outbox = None;
            client
                .status(
                    request_id,
                    OrganizerSnapshot {
                        body: OrganizerBodyDisclosure::Unavailable,
                        body_scope: body_scope(),
                        collection: None,
                        collection_resolutions: Vec::new(),
                        aid: Vec::new(),
                        pending_aid: Vec::new(),
                        aid_resolutions: Vec::new(),
                        city_pd_encounters: Vec::new(),
                        view: client.view.clone().expect("the fixture value clones"),
                        pending: None,
                        duration: babylon_kernel::clock::CampaignDuration::Finite {
                            final_period: 3,
                        },
                    },
                    &mut session,
                )
                .expect("the fixture command reports its status");
            assert_eq!(
                session.duration,
                Some(babylon_kernel::clock::CampaignDuration::Finite { final_period: 3 })
            );
            if !already_loaded {
                assert_eq!(session.phase, SessionPhase::Loading);
                assert!(session.installed(&session.context()));
            }
            assert_eq!(session.phase, SessionPhase::Complete);
            assert!(!client.available(&session));
            assert!(session.begin_advance().is_none());
        }
    }
    #[test]
    fn collection_original_command_uses_actual_runtime_queue_and_blocks_historical_actions() {
        let (mut client, mut session) = ready();
        let period = client
            .view
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .period;
        client.collection = Some(OrganizerCollectionPreview {
            period,
            mandate_id: [8; 32],
            actor_id: client
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .actor_id,
            contributor_id: 1,
            contributor_label: "Fixture contributor".into(),
            source_hash: [16; 32],
            cash_consent: OrganizerGiftConsent::Accept,
            maximum_cash_micros: 400_000,
            protected_cash_floor_micros: 0,
            collection_hours: 2,
            organization_cash_micros: 1_000_000,
        });
        assert!(client.choice_available(OrganizerChoice::Collect));
        let mut unrelated = OrganizerClient {
            view: client.view.clone(),
            collection: client.collection.clone(),
            ..OrganizerClient::default()
        };
        unrelated
            .collection
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .actor_id += 1;
        assert!(!unrelated.choice_available(OrganizerChoice::Collect));
        unrelated
            .collection
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .actor_id -= 1;
        unrelated
            .collection
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .source_hash = [0; 32];
        assert!(!unrelated.choice_available(OrganizerChoice::Collect));
        let command = client
            .make_command(&session, OrganizerChoice::Collect)
            .expect("the fixture command builds");
        client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
        assert!(
            matches!(client.outbox.take(),Some(RuntimeSessionRequest::SubmitOrganizer {command:sent,..}) if sent==command)
        );
        let id = client
            .pending
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .id;
        let accepted = OrganizerCommitment {
            command: command.clone(),
            resolves_period: period + 1,
            commitment_id: [9; 32],
        };
        client
            .accepted(id, accepted.clone(), &mut session)
            .expect("the fixture call `accepted` succeeds for the authored inputs");
        assert_eq!(client.commitment, Some(accepted));
        assert_eq!(command.choice, OrganizerChoice::Collect);
        assert_eq!(command.expected_period, period);
        assert!(presentation::review(&client, false, false, false).contains("no standing fallback"));
        assert!(!client.available(&session));
        assert!(session.begin_advance().is_some());
        let (mut historical, mut session) = ready();
        session.inspect_tick(2);
        assert!(session.installed(&session.context()));
        assert!(!historical.available(&session));
        assert!(!historical.choice_available(OrganizerChoice::Collect));
        historical.collection = client.collection;
        historical
            .collection
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .cash_consent = OrganizerGiftConsent::Refuse;
        assert!(!historical.choice_available(OrganizerChoice::Collect));
    }
}
