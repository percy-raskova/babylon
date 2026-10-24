//! Leaf implementation for the parent module; public paths stay on the parent.

use super::{draft, evidence, presentation, ui};

use babylon_persistence::runtime_session::{
    OrganizerAidPending, OrganizerAidResolution, OrganizerChoice, OrganizerCollectionPreview,
    OrganizerCollectionResolution, OrganizerCommand, OrganizerCommitment,
    OrganizerMaterialAidPreview, OrganizerPreview, OrganizerSnapshot, OrganizerView,
    RuntimeSessionRequest, RUNTIME_SESSION_PROTOCOL_VERSION,
};

use bevy::prelude::*;

use crate::observer::{ObservationContext, ObserverSession, SessionPhase};

use crate::observer_io::{ObserverSet, RuntimePipe, RuntimeSendError};

use super::draft::OrganizerDraft;
use crate::observer_io::qualification::NativeAudit;
use babylon_persistence::runtime_session::OrganizerAidKind;
use babylon_persistence::runtime_session::OrganizerGiftConsent;
use babylon_persistence::runtime_session::OrganizerObservation;
use evidence::EvidenceInspection;
use uuid::Uuid;

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
pub(crate) enum RequestKind {
    Status,
    Preview,
    Submit,
}

pub(crate) struct PendingRequest {
    pub(super) id: u64,
    pub(super) kind: RequestKind,
    pub(super) command: Option<OrganizerCommand>,
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
    pub(super) draft: Option<OrganizerDraft>,
    pub(super) campaign: Option<Uuid>,
    pub(super) reviewed_command: Option<OrganizerCommand>,
    pub(super) review_context: Option<ObservationContext>,
    pub(super) pending: Option<PendingRequest>,
    pub(super) outbox: Option<RuntimeSessionRequest>,
    pub(super) status_due: bool,
    pub(super) draft_dirty: bool,
    pub(super) draft_changed_at: f64,
    pub(super) draft_writable: bool,
    pub(super) draft_save_error: Option<String>,
    pub(super) return_focus: Option<Entity>,
    pub(super) evidence: EvidenceInspection,
}

impl OrganizerClient {
    pub(crate) fn reset(&mut self) {
        self.save_draft();
        *self = Self::default();
    }

    pub(crate) fn admitted(&mut self, campaign: Uuid) {
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

    pub(crate) fn require_status(&mut self, session: &mut ObserverSession) {
        self.status_due = true;
        session.set_organizer_control_pending(true);
    }

    pub(super) fn clear_review(&mut self) {
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

    pub(super) fn save_draft(&mut self) {
        if !self.draft_dirty || !self.draft_writable {
            return;
        }
        if let (Some(campaign), Some(draft)) = (self.campaign, &self.draft) {
            let result = draft::save(campaign, draft);
            self.draft_saved(result);
        }
    }

    pub(super) fn draft_saved(&mut self, result: Result<(), String>) {
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

    pub(super) fn dirty(&mut self, now: f64) {
        self.draft_dirty = true;
        self.draft_changed_at = now;
    }

    pub(super) fn choice(&self) -> OrganizerChoice {
        self.draft
            .as_ref()
            .map_or(OrganizerChoice::Hold, |draft| draft.choice)
    }

    pub(super) fn available(&self, session: &ObserverSession) -> bool {
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

    pub(super) fn aid_preview(
        &self,
        choice: OrganizerChoice,
    ) -> Option<&OrganizerMaterialAidPreview> {
        let kind = match choice {
            OrganizerChoice::LocalAid => OrganizerAidKind::Local,
            OrganizerChoice::RemoteAid => OrganizerAidKind::Remote,
            _ => return None,
        };
        let view = self.view.as_ref()?;
        self.aid
            .iter()
            .find(|row| row.kind == kind && row.period == view.period)
    }

    pub(super) fn collection_preview(&self) -> Option<&OrganizerCollectionPreview> {
        let view = self.view.as_ref()?;
        self.collection.as_ref().filter(|terms| {
            terms.period == view.period
                && terms.actor_id == view.actor_id
                && terms.contributor_id > 0
                && !terms.contributor_label.is_empty()
                && terms.source_hash != [0; 32]
        })
    }

    pub(super) fn choice_available(&self, choice: OrganizerChoice) -> bool {
        if choice == OrganizerChoice::Collect {
            return self
                .collection_preview()
                .is_some_and(|terms| terms.cash_consent == OrganizerGiftConsent::Accept);
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
                    && option.receiving_consent == OrganizerGiftConsent::Accept
            })
        }) && preview.receiving_consent == OrganizerGiftConsent::Accept
            && !self.pending_aid.iter().any(|row| row.kind == preview.kind)
    }

    pub(super) fn make_command(
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
            nonce: *Uuid::new_v4().as_bytes(),
            choice,
        })
    }

    pub(super) fn queue(
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

pub(crate) fn transport(
    mut organizer: ResMut<OrganizerClient>,
    mut session: ResMut<ObserverSession>,
    pipe: Option<Res<RuntimePipe>>,
    time: Res<Time>,
    mut qualification: Option<ResMut<NativeAudit>>,
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
        if let Err(error) = qualification
            .as_deref_mut()
            .map(|audit| audit.stage(&session, &request, organizer.preview.as_ref()))
            .transpose()
        {
            session.fail(error);
            return;
        }
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
    observation: &OrganizerObservation,
    period: u64,
) -> String {
    presentation::observation(view, observation, period)
}
