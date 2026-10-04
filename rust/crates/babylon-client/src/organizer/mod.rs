//! Native organizational decisions over the one authoritative runtime connection.

mod draft;
mod editor;
mod evidence;
mod presentation;
pub(crate) mod ui;

use babylon_persistence::runtime_session::{
    OrganizerAidPending, OrganizerAidResolution, OrganizerChoice, OrganizerCollectionPreview,
    OrganizerCollectionResolution, OrganizerCommand, OrganizerCommitment,
    OrganizerMaterialAidPreview, OrganizerPreview, OrganizerSnapshot, OrganizerView,
    RuntimeSessionRequest, RUNTIME_SESSION_PROTOCOL_VERSION,
};
use bevy::prelude::*;

use crate::observer::{ObservationContext, ObserverSession, SessionPhase};
use crate::observer_io::{ObserverSet, RuntimePipe, RuntimeSendError};

use draft::OrganizerDraft;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum OrganizerInspector {
    #[default]
    Closed,
    Evidence,
    Relationships,
    Direction,
    Receipts,
    Notes,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum RequestKind {
    Status,
    Preview,
    Submit,
}

struct PendingRequest {
    id: u64,
    kind: RequestKind,
    command: Option<OrganizerCommand>,
}

/// Cached lawful projection and local presentation. No authoritative state is owned here.
#[derive(Resource, Default)]
pub(crate) struct OrganizerClient {
    pub view: Option<OrganizerView>,
    pub commitment: Option<OrganizerCommitment>,
    pub preview: Option<OrganizerPreview>,
    pub aid: Vec<OrganizerMaterialAidPreview>,
    pub pending_aid: Vec<OrganizerAidPending>,
    pub aid_resolutions: Vec<OrganizerAidResolution>,
    pub collection: Option<OrganizerCollectionPreview>,
    pub collection_resolutions: Vec<OrganizerCollectionResolution>,
    pub inspector: OrganizerInspector,
    pub message: String,
    draft: Option<OrganizerDraft>,
    campaign: Option<uuid::Uuid>,
    reviewed_command: Option<OrganizerCommand>,
    review_context: Option<ObservationContext>,
    pending: Option<PendingRequest>,
    outbox: Option<RuntimeSessionRequest>,
    status_due: bool,
    draft_dirty: bool,
    draft_changed_at: f64,
    draft_writable: bool,
    draft_save_error: Option<String>,
    return_focus: Option<Entity>,
    evidence: evidence::EvidenceInspection,
}

impl OrganizerClient {
    pub(crate) fn reset(&mut self) {
        self.save_draft();
        *self = Self::default();
    }

    pub(crate) fn admitted(&mut self, campaign: uuid::Uuid) {
        self.reset();
        self.campaign = Some(campaign);
        self.status_due = true;
        self.message = "Opening the organization's committed situation…".into();
    }

    pub(crate) fn committed(&mut self) {
        self.clear_review();
        self.status_due = true;
        self.message = "Period committed. Reading its practice receipts…".into();
    }

    fn clear_review(&mut self) {
        self.preview = None;
        self.reviewed_command = None;
        self.review_context = None;
    }

    fn invalidate_review(&mut self, session: &ObserverSession) {
        if self
            .review_context
            .as_ref()
            .is_some_and(|context| *context != session.context())
        {
            self.clear_review();
            self.message =
                "Inspection changed. Return Live and review the selected approach again.".into();
        }
    }

    fn save_draft(&mut self) {
        if !self.draft_dirty || !self.draft_writable {
            return;
        }
        if let (Some(campaign), Some(draft)) = (self.campaign, &self.draft) {
            let result = draft::save(campaign, draft);
            self.draft_saved(result);
        }
    }

    fn draft_saved(&mut self, result: Result<(), String>) {
        if let Err(error) = result {
            self.draft_save_error = Some(error.clone());
            self.message = error;
        } else {
            self.draft_dirty = false;
            if self
                .draft_save_error
                .take()
                .is_some_and(|error| self.message == error)
            {
                self.message.clear();
            }
        }
    }

    fn dirty(&mut self, now: f64) {
        self.draft_dirty = true;
        self.draft_changed_at = now;
    }

    fn choice(&self) -> OrganizerChoice {
        self.draft
            .as_ref()
            .map_or(OrganizerChoice::Hold, |draft| draft.choice)
    }

    fn available(&self, session: &ObserverSession) -> bool {
        session.organizer_enabled
            && session.phase == SessionPhase::Ready
            && session.viewed_tick == session.durable_tick
            && !session.quit_requested
            && !session.lifecycle_pending()
            && !session.advance_pending()
            && !session.organizer_control_pending()
            && self.pending.is_none()
            && self.commitment.is_none()
            && self
                .view
                .as_ref()
                .is_some_and(|view| view.period == session.durable_tick)
    }

    fn aid_preview(&self, choice: OrganizerChoice) -> Option<&OrganizerMaterialAidPreview> {
        let kind = match choice {
            OrganizerChoice::LocalAid => {
                babylon_persistence::runtime_session::OrganizerAidKind::Local
            }
            OrganizerChoice::RemoteAid => {
                babylon_persistence::runtime_session::OrganizerAidKind::Remote
            }
            _ => return None,
        };
        let view = self.view.as_ref()?;
        self.aid
            .iter()
            .find(|row| row.kind == kind && row.period == view.period)
    }

    fn choice_available(&self, choice: OrganizerChoice) -> bool {
        if choice == OrganizerChoice::Collect {
            return self.view.as_ref().is_some_and(|view| {
                self.collection.as_ref().is_some_and(|m| {
                    m.period == view.period
                        && m.cash_consent
                            == babylon_persistence::runtime_session::OrganizerGiftConsent::Accept
                })
            });
        }
        if !matches!(
            choice,
            OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
        ) {
            return true;
        }
        let Some(preview) = self.aid_preview(choice) else {
            return false;
        };
        self.view.as_ref().is_some_and(|view| {
            view.aid_options.iter().any(|option| {
                option.kind == preview.kind
                    && option.receiving_consent
                        == babylon_persistence::runtime_session::OrganizerGiftConsent::Accept
            })
        }) && preview.receiving_consent
            == babylon_persistence::runtime_session::OrganizerGiftConsent::Accept
            && !self.pending_aid.iter().any(|row| row.kind == preview.kind)
    }

    fn make_command(
        &self,
        session: &ObserverSession,
        choice: OrganizerChoice,
    ) -> Option<OrganizerCommand> {
        let view = self.view.as_ref()?;
        Some(OrganizerCommand {
            campaign_id: *session.campaign.as_uuid().as_bytes(),
            actor_id: view.actor_id,
            authority_id: view.authority_id,
            expected_period: view.period,
            content_digest: view.content_digest,
            resource_digest: view.resource_digest,
            nonce: *uuid::Uuid::new_v4().as_bytes(),
            choice,
        })
    }

    fn queue(
        &mut self,
        session: &mut ObserverSession,
        kind: RequestKind,
        command: Option<OrganizerCommand>,
    ) {
        if self.pending.is_some() {
            return;
        }
        let Some(scope) = session.runtime_scope().cloned() else {
            return;
        };
        let Some(request_id) = session.next_control_request() else {
            return;
        };
        if kind == RequestKind::Preview {
            self.clear_review();
            self.review_context = Some(session.context());
        }
        let request = match kind {
            RequestKind::Status => RuntimeSessionRequest::OrganizerStatus {
                protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
                request_id,
                scope,
            },
            RequestKind::Preview => RuntimeSessionRequest::PreviewOrganizer {
                protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
                request_id,
                scope,
                command: command
                    .clone()
                    .expect("preview requires a reviewed command"),
            },
            RequestKind::Submit => {
                let command = command
                    .clone()
                    .expect("submission requires a reviewed command");
                if matches!(
                    command.choice,
                    OrganizerChoice::PauseStanding | OrganizerChoice::ResumeStanding
                ) {
                    RuntimeSessionRequest::ConfigureOrganizerStanding {
                        protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
                        request_id,
                        scope,
                        command,
                    }
                } else {
                    RuntimeSessionRequest::SubmitOrganizer {
                        protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
                        request_id,
                        scope,
                        command,
                    }
                }
            }
        };
        self.pending = Some(PendingRequest {
            id: request_id,
            kind,
            command,
        });
        self.outbox = Some(request);
        session.set_organizer_control_pending(true);
        session.pause_playback();
    }

    fn take_response(
        &mut self,
        request_id: u64,
        kind: RequestKind,
    ) -> Result<PendingRequest, String> {
        if !self
            .pending
            .as_ref()
            .is_some_and(|pending| pending.id == request_id && pending.kind == kind)
        {
            return Err(
                "Organizer response did not match its pending request; reopen to reconcile.".into(),
            );
        }
        self.pending
            .take()
            .ok_or_else(|| "Organizer request disappeared.".into())
    }

    pub(crate) fn status(
        &mut self,
        request_id: u64,
        snapshot: OrganizerSnapshot,
        session: &mut ObserverSession,
    ) -> Result<(), String> {
        self.take_response(request_id, RequestKind::Status)?;
        if snapshot.view.period != session.durable_tick
            || !snapshot.duration.contains(snapshot.view.period)
            || self.campaign != Some(*session.campaign.as_uuid())
        {
            return Err(
                "Organizer situation did not match this campaign's committed period.".into(),
            );
        }
        if snapshot.pending.as_ref().is_some_and(|pending| {
            pending.command.campaign_id != *session.campaign.as_uuid().as_bytes()
                || pending.command.actor_id != snapshot.view.actor_id
                || pending.command.authority_id != snapshot.view.authority_id
                || pending.command.content_digest != snapshot.view.content_digest
                || pending.command.resource_digest != snapshot.view.resource_digest
                || pending.command.expected_period != snapshot.view.period
                || snapshot.view.period.checked_add(1) != Some(pending.resolves_period)
                || !snapshot.duration.contains(pending.resolves_period)
        }) {
            return Err("Pending organizer ruling does not match the opened campaign's authority and period.".into());
        }
        if self.draft.is_none() {
            match draft::load(*session.campaign.as_uuid(), snapshot.view.workplace_id) {
                Ok(value) => {
                    self.draft = Some(value);
                    self.draft_writable = true;
                }
                Err(error) => {
                    self.message = error;
                    self.draft = Some(OrganizerDraft::new(snapshot.view.workplace_id));
                    self.draft_writable = false;
                }
            }
        }
        self.clear_review();
        session.duration = Some(snapshot.duration);
        if session.phase == SessionPhase::Ready && snapshot.duration.complete(session.viewed_tick) {
            session.complete();
        }
        self.collection = snapshot.collection;
        self.collection_resolutions = snapshot.collection_resolutions;
        self.aid = snapshot.aid;
        self.pending_aid = snapshot.pending_aid;
        self.aid_resolutions = snapshot.aid_resolutions;
        self.view = Some(snapshot.view);
        self.commitment = snapshot.pending;
        self.status_due = false;
        session.set_organizer_control_pending(false);
        if self.draft_writable {
            // The fixed decision footer renders the acknowledged state. Keep
            // the message line for pending operations and actionable failures.
            self.message.clear();
        }
        Ok(())
    }

    pub(crate) fn previewed(
        &mut self,
        request_id: u64,
        preview: OrganizerPreview,
        session: &mut ObserverSession,
    ) -> Result<(), String> {
        let pending = self.take_response(request_id, RequestKind::Preview)?;
        let command = pending.command.ok_or("Organizer preview had no command.")?;
        if preview.choice != command.choice
            || preview.current_period != command.expected_period
            || preview.resolves_period
                != command
                    .expected_period
                    .checked_add(1)
                    .ok_or("Organizer period overflow")?
        {
            return Err("Organizer preview did not match the requested ruling.".into());
        }
        self.invalidate_review(session);
        if self.review_context.is_none() {
            session.set_organizer_control_pending(false);
            return Ok(());
        }
        self.reviewed_command = Some(command);
        self.message.clear();
        self.preview = Some(preview);
        session.set_organizer_control_pending(false);
        Ok(())
    }

    pub(crate) fn accepted(
        &mut self,
        request_id: u64,
        commitment: OrganizerCommitment,
        session: &mut ObserverSession,
    ) -> Result<(), String> {
        let pending = self.take_response(request_id, RequestKind::Submit)?;
        if pending.command.as_ref() != Some(&commitment.command)
            || commitment.command.expected_period.checked_add(1) != Some(commitment.resolves_period)
        {
            return Err("Accepted organizer ruling differs from the reviewed command.".into());
        }
        self.commitment = Some(commitment);
        self.clear_review();
        self.message.clear();
        session.set_organizer_control_pending(false);
        Ok(())
    }

    pub(crate) fn refused(
        &mut self,
        request_id: Option<u64>,
        message: String,
        session: &mut ObserverSession,
    ) -> bool {
        if self
            .pending
            .as_ref()
            .is_none_or(|pending| Some(pending.id) != request_id)
        {
            return false;
        }
        self.pending = None;
        self.status_due = false;
        self.outbox = None;
        self.clear_review();
        self.message = message;
        session.set_organizer_control_pending(false);
        true
    }
}

fn transport(
    mut organizer: ResMut<OrganizerClient>,
    mut session: ResMut<ObserverSession>,
    pipe: Option<Res<RuntimePipe>>,
    time: Res<Time>,
) {
    if organizer
        .review_context
        .as_ref()
        .is_some_and(|context| *context != session.context())
    {
        organizer.invalidate_review(&session);
    }
    if session.quit_requested || session.lifecycle_pending() {
        organizer.save_draft();
    }
    if organizer.draft_dirty && time.elapsed_secs_f64() - organizer.draft_changed_at >= 0.5 {
        organizer.save_draft();
    }
    if !session.organizer_enabled || session.quit_requested || session.runtime_disconnected() {
        return;
    }
    if organizer.status_due
        && organizer.pending.is_none()
        && !session.advance_pending()
        && !session.lifecycle_pending()
    {
        organizer.queue(&mut session, RequestKind::Status, None);
    }
    if let (Some(pipe), Some(request)) = (pipe, organizer.outbox.clone()) {
        match pipe.send_request(request) {
            Ok(()) => organizer.outbox = None,
            Err(RuntimeSendError::Full) => {}
            Err(RuntimeSendError::Disconnected) => session.disconnect(
                "Organizer connection lost; reopen to reconcile the accepted ruling.".into(),
            ),
        }
    }
}

pub struct OrganizerPlugin;
impl Plugin for OrganizerPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<OrganizerClient>().add_systems(
            Update,
            transport
                .after(ObserverSet::Receive)
                .before(ObserverSet::Install),
        );
        ui::install(app);
    }
}

/// Shared history uses the same earned report wording and provenance as Circuit.
pub(crate) fn report_reading(
    view: &OrganizerView,
    observation: &babylon_persistence::runtime_session::OrganizerObservation,
    period: u64,
) -> String {
    presentation::observation(view, observation, period)
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::identity::CampaignId;
    use babylon_persistence::runtime_session::{
        OrganizerAgreement, OrganizerObservation, OrganizerReport, OrganizerStandingWork,
    };

    fn ready() -> (OrganizerClient, ObserverSession) {
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
            cash_consent: babylon_persistence::runtime_session::OrganizerGiftConsent::Accept,
            maximum_cash_micros: 400_000,
            protected_cash_floor_micros: 0,
            collection_hours: 2,
            organization_cash_micros: 1_000_000,
        });
        assert!(client.choice_available(OrganizerChoice::Collect));
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
