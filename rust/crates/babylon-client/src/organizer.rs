//! Native organizational decisions over the one authoritative runtime connection.

mod draft;

mod editor;

mod evidence;

mod presentation;

pub(crate) mod qualification_input;

pub(crate) mod ui;

#[path = "organizer/client.rs"]
mod client;

#[cfg(test)]
use client::transport;
pub use client::OrganizerPlugin;
use client::RequestKind;
pub(crate) use client::{report_reading, OrganizerClient, OrganizerInspector};

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
mod tests {
    use super::*;
    use babylon_persistence::identity::CampaignId;
    use babylon_persistence::runtime_session::{
        OrganizerAgreement, OrganizerObservation, OrganizerReport, OrganizerStandingWork,
    };

    pub(crate) fn ready() -> (OrganizerClient, ObserverSession) {
        let campaign = uuid::Uuid::from_u128(927);
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

    fn aid_fixture() -> OrganizerMaterialAidPreview {
        OrganizerMaterialAidPreview {
            kind: babylon_persistence::runtime_session::OrganizerAidKind::Local,
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
            receiving_consent: babylon_persistence::runtime_session::OrganizerGiftConsent::Accept,
            time: None,
            transport: babylon_persistence::runtime_session::OrganizerAidTransportPreview::Local,
        }
    }

    #[test]
    fn aid_requires_current_authenticated_preview_offered_consent_and_no_pending_kind() {
        let (mut client, _) = ready();
        client.view.as_mut().unwrap().aid_options.push(
            babylon_persistence::runtime_session::OrganizerAidOption {
                kind: babylon_persistence::runtime_session::OrganizerAidKind::Local,
                partner_actor_id: 95,
                partner_label: "Recipient collective".into(),
                coordination_hours: 3,
                receiving_consent:
                    babylon_persistence::runtime_session::OrganizerGiftConsent::Accept,
            },
        );
        assert!(!client.choice_available(OrganizerChoice::LocalAid));
        client.aid.push(aid_fixture());
        assert!(client.choice_available(OrganizerChoice::LocalAid));
        assert!(!client.choice_available(OrganizerChoice::RemoteAid));
        client.aid[0].period = 2;
        assert!(!client.choice_available(OrganizerChoice::LocalAid));
        client.aid[0].period = 3;
        client.aid[0].receiving_consent =
            babylon_persistence::runtime_session::OrganizerGiftConsent::Refuse;
        assert!(!client.choice_available(OrganizerChoice::LocalAid));
        client.aid[0].receiving_consent =
            babylon_persistence::runtime_session::OrganizerGiftConsent::Accept;
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
            .unwrap();
        client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
        let request_id = client.pending.as_ref().unwrap().id;
        client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
        assert_eq!(client.pending.as_ref().unwrap().id, request_id);
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
            .unwrap();
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
                .unwrap();
            client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
            let request_id = client.pending.as_ref().unwrap().id;
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
            .unwrap()
            .notes
            .insert("Keep this objection.");
        client.draft.as_mut().unwrap().choice = OrganizerChoice::Hold;
        let accepted = OrganizerCommitment {
            command: client
                .make_command(&session, OrganizerChoice::Reinforce)
                .unwrap(),
            resolves_period: 4,
            commitment_id: [4; 32],
        };
        client.queue(&mut session, RequestKind::Status, None);
        let request_id = client.pending.as_ref().unwrap().id;
        assert!(matches!(
            client.outbox.take(),
            Some(RuntimeSessionRequest::OrganizerStatus { .. })
        ));
        client
            .status(
                request_id,
                OrganizerSnapshot {
                    collection: None,
                    collection_resolutions: Vec::new(),
                    aid: Vec::new(),
                    pending_aid: Vec::new(),
                    aid_resolutions: Vec::new(),
                    view: client.view.clone().unwrap(),
                    pending: Some(accepted.clone()),
                    duration: babylon_kernel::clock::CampaignDuration::Finite { final_period: 16 },
                },
                &mut session,
            )
            .unwrap();
        assert_eq!(client.commitment, Some(accepted));
        assert_eq!(client.choice(), OrganizerChoice::Hold);
        assert_eq!(
            client.draft.as_ref().unwrap().notes.text,
            "Keep this objection."
        );
        assert!(!client.available(&session));
        assert!(client.outbox.is_none());
        assert!(client.reviewed_command.is_none());
    }

    #[test]
    fn held_evidence_withholds_later_reports_and_labels_live_agreements() {
        let (mut client, _) = ready();
        let view = client.view.as_mut().unwrap();
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
            let request_id = client.pending.as_ref().unwrap().id;
            client.outbox = None;
            client
                .status(
                    request_id,
                    OrganizerSnapshot {
                        collection: None,
                        collection_resolutions: Vec::new(),
                        aid: Vec::new(),
                        pending_aid: Vec::new(),
                        aid_resolutions: Vec::new(),
                        view: client.view.clone().unwrap(),
                        pending: None,
                        duration: babylon_kernel::clock::CampaignDuration::Finite {
                            final_period: 3,
                        },
                    },
                    &mut session,
                )
                .unwrap();
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
        let period = client.view.as_ref().unwrap().period;
        client.collection = Some(OrganizerCollectionPreview {
            period,
            mandate_id: [8; 32],
            actor_id: client.view.as_ref().unwrap().actor_id,
            contributor_id: 1,
            contributor_label: "Fixture contributor".into(),
            source_hash: [16; 32],
            cash_consent: babylon_persistence::runtime_session::OrganizerGiftConsent::Accept,
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
        unrelated.collection.as_mut().unwrap().actor_id += 1;
        assert!(!unrelated.choice_available(OrganizerChoice::Collect));
        unrelated.collection.as_mut().unwrap().actor_id -= 1;
        unrelated.collection.as_mut().unwrap().source_hash = [0; 32];
        assert!(!unrelated.choice_available(OrganizerChoice::Collect));
        let command = client
            .make_command(&session, OrganizerChoice::Collect)
            .unwrap();
        client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
        assert!(
            matches!(client.outbox.take(),Some(RuntimeSessionRequest::SubmitOrganizer {command:sent,..}) if sent==command)
        );
        let id = client.pending.as_ref().unwrap().id;
        let accepted = OrganizerCommitment {
            command: command.clone(),
            resolves_period: period + 1,
            commitment_id: [9; 32],
        };
        client.accepted(id, accepted.clone(), &mut session).unwrap();
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
        historical.collection.as_mut().unwrap().cash_consent =
            babylon_persistence::runtime_session::OrganizerGiftConsent::Refuse;
        assert!(!historical.choice_available(OrganizerChoice::Collect));
    }
}
