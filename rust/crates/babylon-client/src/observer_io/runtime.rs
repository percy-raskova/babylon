//! Leaf implementation for the parent module; public paths stay on the parent.

#[allow(unused_imports)]
use super::qualification;

use std::io::{BufRead, Read, Write};

use std::sync::{mpsc, Mutex};

use babylon_persistence::{
    observer_reader::ObserverEconomyReader, observer_reader::ObserverEconomySnapshot,
    observer_reader::ObserverVisibility, runtime_session::RuntimeSessionPreset,
    runtime_session::RuntimeSessionRequest, runtime_session::RuntimeSessionResponse,
    runtime_session::RuntimeSessionScope, runtime_session::RuntimeSessionTail,
    runtime_session::RuntimeSessionTarget, runtime_session::RUNTIME_SESSION_MAX_LINE_BYTES,
    runtime_session::RUNTIME_SESSION_PROTOCOL_VERSION,
};

use bevy::ecs::system::SystemParam;

use bevy::prelude::*;

use bevy::tasks::{block_on, AsyncComputeTaskPool, Task};

use crate::observer::{ObservationContext, ObserverSession, Perspective, SessionPhase};

use crate::observer_controls::{availability, ControlAvailability};

use crate::observer_ui::{ObserverCommand, ObserverFeedback, ObserverFrame, ObserverUiState};

use crate::ui::dossier_card::{
    ActiveCountyDossier, DossierCampaignId, DossierFetchState, DossierPageView, DossierRefresh,
};

pub(crate) const LAUNCHER_REQUIRED: &str =
    "This window has no launcher connection. Close it and start Babylon through its launcher.";

// Allows the bounded 120-second storage statement to finish before recovery cleanup.
pub(crate) const SHUTDOWN_TIMEOUT_SECS: f64 = 150.0;

#[derive(SystemSet, Debug, Clone, PartialEq, Eq, Hash)]
pub enum ObserverSet {
    Input,
    Receive,
    Install,
    Paint,
}

#[derive(Resource)]
pub(crate) struct RuntimePipe {
    pub(super) requests: mpsc::SyncSender<RuntimeSessionRequest>,
    pub(super) responses: Mutex<mpsc::Receiver<Result<RuntimeSessionResponse, String>>>,
}

#[derive(Debug)]
pub(crate) enum RuntimeSendError {
    Full,
    Disconnected,
}

impl RuntimePipe {
    pub(crate) fn send_request(
        &self,
        request: RuntimeSessionRequest,
    ) -> Result<(), RuntimeSendError> {
        self.requests
            .try_send(request)
            .map_err(|error| match error {
                mpsc::TrySendError::Full(_) => RuntimeSendError::Full,
                mpsc::TrySendError::Disconnected(_) => RuntimeSendError::Disconnected,
            })
    }
}

#[cfg(test)]
impl RuntimePipe {
    pub(crate) fn detached_fixture() -> Self {
        let (requests, _) = mpsc::sync_channel(1);
        let (_, responses) = mpsc::channel();
        Self {
            requests,
            responses: Mutex::new(responses),
        }
    }
}

#[derive(Resource, Default)]
pub(crate) struct PendingObservation(
    pub(super) Option<(ObservationContext, Task<ObservationRead>)>,
);

pub(crate) struct ObservationRead {
    result: Result<PreparedObservation, String>,
    cursor: Option<babylon_persistence::observer_reader::ObserverMaterialCursor>,
    qualification: Option<qualification::Candidate>,
}

pub(crate) struct PreparedObservation {
    pub(super) snapshot: ObserverEconomySnapshot,
    pub(super) evidence: crate::observer_ui::ProductionEvidenceOutcome,
}

impl PreparedObservation {
    pub(super) fn new(mut snapshot: ObserverEconomySnapshot) -> Self {
        let evidence = snapshot.production_evidence_digest();
        Self { snapshot, evidence }
    }
}

#[derive(Clone, PartialEq, Eq)]
pub(crate) struct ObservationCacheKey {
    pub(super) campaign: babylon_persistence::identity::CampaignId,
    pub(super) epoch: Option<u64>,
    pub(super) perspective: Perspective,
    pub(super) foundation: Option<String>,
    pub(super) qualification: Option<qualification::Configuration>,
}

impl ObservationCacheKey {
    fn from_session(
        session: &ObserverSession,
        qualification: Option<&qualification::NativeAudit>,
    ) -> Self {
        Self {
            campaign: session.campaign,
            epoch: session.runtime_scope().map(|scope| scope.epoch),
            perspective: session.perspective,
            foundation: session.foundation_digest.clone(),
            qualification: qualification.map(qualification::NativeAudit::key),
        }
    }
}

/// Retains one scope's immutable source admission and authenticated read cursor.
#[derive(Resource, Default)]
pub(crate) struct ObservationCache {
    key: Option<ObservationCacheKey>,
    cursor: Option<babylon_persistence::observer_reader::ObserverMaterialCursor>,
    full_reader: Option<ObserverEconomyReader>,
}

impl ObservationCache {
    pub(super) fn reconcile(&mut self, key: ObservationCacheKey) {
        if self.key.as_ref() != Some(&key) {
            *self = Self {
                key: Some(key),
                ..Self::default()
            };
        }
    }

    pub(super) fn reader(
        &mut self,
        visibility: ObserverVisibility,
        connect: impl FnOnce() -> Result<
            ObserverEconomyReader,
            babylon_persistence::observer_reader::ObserverEconomyError,
        >,
    ) -> Result<ObserverEconomyReader, babylon_persistence::observer_reader::ObserverEconomyError>
    {
        if visibility == ObserverVisibility::FullObserver {
            if let Some(reader) = &self.full_reader {
                return Ok(reader.clone());
            }
        }
        let reader = connect()?;
        if reader.visibility() != visibility {
            return Err(babylon_persistence::observer_reader::ObserverEconomyError::Authority);
        }
        if visibility == ObserverVisibility::FullObserver {
            // Clones share only the existing admitted immutable source owner.
            // Each consuming read still authenticates actual stored components
            // and publishes admission only after that read completely succeeds.
            self.full_reader = Some(reader.clone());
        }
        Ok(reader)
    }
}

#[derive(Resource, Default)]
pub(crate) struct PlaybackClock {
    pub(super) elapsed: f64,
}

#[derive(Resource, Default)]
pub(crate) struct ShutdownProgress {
    started_at: Option<f64>,
    pub(super) stop_sent: bool,
    exit_sent: bool,
}

#[derive(Resource)]
pub(crate) struct ContinuationPreference(pub(super) std::path::PathBuf);

pub(crate) fn start_pipe(mut commands: Commands, mut state: ResMut<ObserverSession>) {
    if std::env::var("BABYLON_SESSION_STDIO").as_deref() != Ok("1") {
        state.fail("Open this campaign with mise run play to connect its durable runtime.".into());
        return;
    }
    match crate::campaign_browser::preference_path() {
        Ok(path) => {
            commands.insert_resource(ContinuationPreference(path));
        }
        Err(error) => {
            state.fail(error);
            return;
        }
    }
    let (request_tx, request_rx) = mpsc::sync_channel::<RuntimeSessionRequest>(1);
    let (response_tx, response_rx) =
        mpsc::sync_channel::<Result<RuntimeSessionResponse, String>>(8);
    let errors = response_tx.clone();
    let writer = std::thread::Builder::new()
        .name("observer-control-writer".into())
        .spawn(move || {
            let mut output = std::io::stdout().lock();
            while let Ok(request) = request_rx.recv() {
                let result = serde_json::to_vec(&request)
                    .map_err(|error| error.to_string())
                    .and_then(|mut bytes| {
                        if bytes.len() >= RUNTIME_SESSION_MAX_LINE_BYTES {
                            return Err("Runtime request exceeds protocol bound".into());
                        }
                        bytes.push(b'\n');
                        output
                            .write_all(&bytes)
                            .and_then(|()| output.flush())
                            .map_err(|error| error.to_string())
                    });
                if let Err(error) = result {
                    let _ = errors.send(Err(error));
                    break;
                }
            }
        });
    if let Err(error) = writer {
        state.fail(format!("Cannot start control writer: {error}"));
        return;
    }
    let reader = std::thread::Builder::new()
        .name("observer-control-reader".into())
        .spawn(move || {
            let mut input = std::io::stdin().lock();
            loop {
                let mut line = Vec::new();
                let result = (&mut input)
                    .take((RUNTIME_SESSION_MAX_LINE_BYTES + 1) as u64)
                    .read_until(b'\n', &mut line);
                match result {
                    Ok(0) => {
                        let _ = response_tx.send(Err(
                            "Runtime disconnected; reopen to reconcile the committed campaign."
                                .into(),
                        ));
                        break;
                    }
                    Ok(size) if size <= RUNTIME_SESSION_MAX_LINE_BYTES && line.ends_with(b"\n") => {
                        let response = serde_json::from_slice(&line)
                            .map_err(|error| format!("Invalid runtime response: {error}"));
                        if response_tx.send(response).is_err() {
                            break;
                        }
                    }
                    Ok(_) => {
                        let _ =
                            response_tx.send(Err("Runtime response exceeds protocol bound".into()));
                        break;
                    }
                    Err(error) => {
                        let _ = response_tx.send(Err(error.to_string()));
                        break;
                    }
                }
            }
        });
    if let Err(error) = reader {
        state.fail(format!("Cannot start control reader: {error}"));
        return;
    }
    commands.insert_resource(RuntimePipe {
        requests: request_tx,
        responses: Mutex::new(response_rx),
    });
}

pub(crate) fn send_advance(
    pipe: &RuntimePipe,
    state: &mut ObserverSession,
    qualification: Option<&mut qualification::NativeAudit>,
) {
    let Some(request_id) = state.begin_advance() else {
        return;
    };
    let request = RuntimeSessionRequest::Advance {
        protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
        scope: state
            .runtime_scope()
            .expect("admitted runtime scope")
            .clone(),
        request_id,
        expected_tail: RuntimeSessionTail {
            resolve_tick: state.durable_tick,
            tick_content_hash: state.content_hash.clone(),
        },
    };
    let timing = match qualification
        .as_deref()
        .map(|audit| audit.prepare_advance(state, &request))
        .transpose()
    {
        Ok(timing) => timing,
        Err(error) => {
            state.fail(error);
            return;
        }
    };
    match pipe.requests.try_send(request) {
        Ok(()) => {
            if let (Some(audit), Some(timing)) = (qualification, timing) {
                audit.advance_sent(timing);
            }
        }
        Err(error) => state.fail(format!("Cannot request next period: {error}")),
    }
}

pub(crate) fn next_response(
    receiver: &mpsc::Receiver<Result<RuntimeSessionResponse, String>>,
) -> Result<Option<RuntimeSessionResponse>, String> {
    match receiver.try_recv() {
        Ok(response) => response.map(Some),
        Err(mpsc::TryRecvError::Disconnected) => {
            Err("Runtime disconnected; reopen to reconcile committed progress.".into())
        }
        Err(mpsc::TryRecvError::Empty) => Ok(None),
    }
}

#[derive(SystemParam)]
pub(crate) struct CampaignReset<'w> {
    preference: Option<Res<'w, ContinuationPreference>>,
    organizer: Option<ResMut<'w, crate::organizer::OrganizerClient>>,
    primary: Option<ResMut<'w, crate::production::PrimaryView>>,
    atlas: Option<Res<'w, crate::atlas::CountyAtlas>>,
    selected: Option<ResMut<'w, crate::map::SelectedCounty>>,
    frame: Option<ResMut<'w, ObserverFrame>>,
    pending: Option<ResMut<'w, PendingObservation>>,
    campaign: Option<ResMut<'w, DossierCampaignId>>,
    dossier: Option<ResMut<'w, ActiveCountyDossier>>,
    fetch: Option<ResMut<'w, DossierFetchState>>,
    view: Option<ResMut<'w, DossierPageView>>,
    ui: Option<ResMut<'w, ObserverUiState>>,
    qualification: Option<ResMut<'w, qualification::NativeAudit>>,
}

impl CampaignReset<'_> {
    fn switching(
        &mut self,
        state: &mut ObserverSession,
        refresh: &mut DossierRefresh,
        request_id: u64,
        previous: &RuntimeSessionScope,
        scope: RuntimeSessionScope,
    ) -> Result<(), String> {
        let leaving_organizer = state.organizer_enabled;
        state.switching(request_id, previous, scope)?;
        if let Some(audit) = &mut self.qualification {
            audit.switching(
                request_id,
                previous,
                state
                    .runtime_scope()
                    .ok_or("native recovery switched scope absent")?,
            )?;
        }
        if leaving_organizer {
            state.set_perspective(Perspective::FullObserver);
        }
        self.clear(state);
        refresh.bump();
        Ok(())
    }
    fn organizer(&mut self) -> Result<&mut crate::organizer::OrganizerClient, String> {
        self.organizer
            .as_deref_mut()
            .ok_or_else(|| "Organizer interface is not installed".into())
    }

    fn organizer_status(
        &mut self,
        state: &mut ObserverSession,
        request_id: u64,
        snapshot: babylon_persistence::runtime_session::OrganizerSnapshot,
    ) -> Result<(), String> {
        let original = self.qualification.is_some().then(|| snapshot.clone());
        self.organizer()?.status(request_id, snapshot, state)?;
        if let (Some(audit), Some(original)) = (&mut self.qualification, original) {
            audit.status(state, original)?;
        }
        Ok(())
    }

    fn organizer_accepted(
        &mut self,
        state: &mut ObserverSession,
        request_id: u64,
        commitment: babylon_persistence::runtime_session::OrganizerCommitment,
    ) -> Result<(), String> {
        self.organizer()?
            .accepted(request_id, commitment.clone(), state)?;
        if let Some(audit) = &mut self.qualification {
            audit.accepted(state, request_id, &commitment)?;
            // Recovery must capture actual status including the pending ruling.
            // The ordinary status request also prevents a second action meanwhile.
            self.organizer()?.require_status(state);
        }
        Ok(())
    }

    fn clear(&mut self, state: &ObserverSession) {
        if let Some(organizer) = &mut self.organizer {
            organizer.reset();
        }
        if let Some(primary) = &mut self.primary {
            **primary = crate::production::PrimaryView::Map;
        }
        if let Some(frame) = &mut self.frame {
            **frame = ObserverFrame::default();
        }
        if let Some(pending) = &mut self.pending {
            pending.0 = None;
        }
        if let Some(campaign) = &mut self.campaign {
            campaign.0 = state.campaign;
        }
        if let Some(dossier) = &mut self.dossier {
            dossier.0 = None;
        }
        if let Some(fetch) = &mut self.fetch {
            **fetch = DossierFetchState::WaitingForObservation;
        }
        if let Some(view) = &mut self.view {
            **view = DossierPageView::Card;
        }
        if let Some(ui) = &mut self.ui {
            ui.comparison_open = false;
        }
    }
}

pub(crate) fn receive(
    pipe: Option<Res<RuntimePipe>>,
    mut state: ResMut<ObserverSession>,
    mut refresh: ResMut<DossierRefresh>,
    mut reset: CampaignReset,
    mut progress: Option<ResMut<crate::observer_progress::OperationProgress>>,
    time: Res<Time<Real>>,
) {
    if state.phase == SessionPhase::Closed || state.runtime_disconnected() {
        return;
    }
    let Some(pipe) = pipe else {
        return;
    };
    let Ok(receiver) = pipe.responses.lock() else {
        state.disconnect("Runtime response lock failed".into());
        return;
    };
    for _ in 0..8 {
        let response = match next_response(&receiver) {
            Ok(Some(response)) => response,
            Ok(None) => break,
            Err(error) => {
                state.disconnect(error);
                break;
            }
        };
        if let RuntimeSessionResponse::AdvanceProgress {
            request_id,
            resolve_tick,
            stage,
            ..
        } = &response
        {
            let result = admits_response_scope(&response, &state).and_then(|admitted| {
                if !admitted {
                    return Ok(());
                }
                progress
                    .as_deref_mut()
                    .ok_or_else(|| "Advance progress presentation is not installed".to_owned())?
                    .report_stage(&state, *request_id, *resolve_tick, *stage, time.elapsed())
            });
            if let Err(error) = result {
                state.disconnect(error);
                break;
            }
            continue;
        }
        if let Err(error) = apply_response(response, &mut state, &mut refresh, &mut reset) {
            state.disconnect(error);
            break;
        }
        if state.phase == SessionPhase::Closed {
            break;
        }
    }
}

pub(crate) fn response_scope(response: &RuntimeSessionResponse) -> &RuntimeSessionScope {
    match response {
        RuntimeSessionResponse::Hello { scope, .. }
        | RuntimeSessionResponse::Switching { scope, .. }
        | RuntimeSessionResponse::Ready { scope, .. }
        | RuntimeSessionResponse::AdvanceProgress { scope, .. }
        | RuntimeSessionResponse::Committed { scope, .. }
        | RuntimeSessionResponse::ArchiveProgress { scope, .. }
        | RuntimeSessionResponse::Error { scope, .. }
        | RuntimeSessionResponse::Stopped { scope, .. }
        | RuntimeSessionResponse::OrganizerPreview { scope, .. }
        | RuntimeSessionResponse::OrganizerAccepted { scope, .. }
        | RuntimeSessionResponse::OrganizerStatus { scope, .. } => scope,
    }
}

pub(crate) fn admits_response_scope(
    response: &RuntimeSessionResponse,
    state: &ObserverSession,
) -> Result<bool, String> {
    let scope = response_scope(response);
    if let Some(current) = state.runtime_scope() {
        if scope.epoch < current.epoch && !matches!(response, RuntimeSessionResponse::Hello { .. })
        {
            log::debug!("Discarded an earlier runtime lifecycle response");
            return Ok(false);
        }
        if !matches!(response, RuntimeSessionResponse::Switching { .. }) && scope != current {
            return Err("Runtime response lifecycle identity mismatch".into());
        }
    } else if !matches!(response, RuntimeSessionResponse::Hello { .. }) {
        return Err("Runtime did not begin with Hello".into());
    }
    Ok(true)
}

pub(crate) struct CampaignAdmission {
    request_id: u64,
    foundation_digest: String,
    tail: RuntimeSessionTail,
    organizer: bool,
    duration: babylon_kernel::clock::CampaignDuration,
}

pub(crate) fn admit_campaign(
    state: &mut ObserverSession,
    refresh: &mut DossierRefresh,
    reset: &mut CampaignReset,
    admission: CampaignAdmission,
) -> Result<(), String> {
    let CampaignAdmission {
        request_id,
        foundation_digest,
        tail,
        organizer,
        duration,
    } = admission;
    if !duration.contains(tail.resolve_tick) {
        return Err("Runtime supplied an invalid campaign duration".into());
    }
    state.admitted(request_id, foundation_digest, tail)?;
    state.duration = Some(duration);
    state.organizer_enabled = organizer;
    state.set_organizer_control_pending(organizer);
    if organizer {
        state.set_perspective(Perspective::PlayerKnowledge);
        if let (Some(atlas), Some(selected)) = (&reset.atlas, &mut reset.selected) {
            selected.0 = atlas.index_of_fips("26163");
        }
        reset.organizer()?.admitted(*state.campaign.as_uuid());
        if let Some(primary) = &mut reset.primary {
            **primary = crate::production::PrimaryView::Organizer;
        }
        if let Some(ui) = &mut reset.ui {
            ui.archive_open = false;
            ui.history_open = false;
        }
    }
    if let Some(audit) = &mut reset.qualification {
        audit.reopened_ready(state, request_id)?;
    }
    refresh.bump();
    if let Some(preference) = &reset.preference {
        if let Err(error) = crate::campaign_browser::write_preference(
            &preference.0,
            state.campaign,
            state.generation,
        ) {
            log::warn!(
                "Campaign opened, but its continuation preference could not be saved: {error}"
            );
        }
    }
    Ok(())
}

pub(crate) fn refuse_runtime_request(
    state: &mut ObserverSession,
    reset: &mut CampaignReset,
    request_id: Option<u64>,
    code: babylon_persistence::runtime_session::RuntimeSessionErrorCode,
    tail: Option<&RuntimeSessionTail>,
) -> Result<(), String> {
    let complete = code
        == babylon_persistence::runtime_session::RuntimeSessionErrorCode::HorizonComplete
        && state
            .duration
            .is_some_and(|duration| duration.complete(state.durable_tick))
        && tail.is_some_and(|tail| {
            tail.resolve_tick == state.durable_tick && tail.tick_content_hash == state.content_hash
        });
    log::warn!("Runtime campaign request was refused: {code}");
    let organizer_refused = reset.organizer.as_mut().is_some_and(|organizer| {
        organizer.refused(
            request_id,
            format!(
                "Runtime refused the organizer request: {code}. Refresh or reopen to reconcile."
            ),
            state,
        )
    });
    if let (Some(audit), Some(request_id)) = (
        reset
            .qualification
            .as_deref_mut()
            .filter(|_| organizer_refused),
        request_id,
    ) {
        audit.refused(state, request_id);
    }
    if !organizer_refused && !state.refuse_request(request_id, code) {
        return Err("Runtime refusal did not match an outstanding request".into());
    }
    if complete {
        state.complete();
    }
    Ok(())
}

pub(crate) fn apply_archive_progress(
    state: &mut ObserverSession,
    refresh: &mut DossierRefresh,
    durable_tick: u64,
    verified_tick: u64,
) -> Result<(), String> {
    if state.foundation_digest.is_none()
        || durable_tick != state.durable_tick
        || verified_tick > durable_tick
        || verified_tick < state.archive_verified_tick
    {
        return Err("Archive progress did not match the acknowledged campaign tail".into());
    }
    if state.archive_verified_tick != verified_tick {
        state.archive_verified_tick = verified_tick;
    }
    refresh.bump();
    Ok(())
}

pub(crate) fn apply_response(
    response: RuntimeSessionResponse,
    state: &mut ObserverSession,
    refresh: &mut DossierRefresh,
    reset: &mut CampaignReset,
) -> Result<(), String> {
    if !admits_response_scope(&response, state)? {
        return Ok(());
    }
    match response {
        RuntimeSessionResponse::Hello {
            protocol_version,
            scope,
        } => {
            if protocol_version != RUNTIME_SESSION_PROTOCOL_VERSION {
                return Err("Runtime protocol version mismatch".into());
            }
            state.hello(scope)?;
        }
        RuntimeSessionResponse::Switching {
            request_id,
            previous_scope,
            scope,
        } => {
            reset.switching(state, refresh, request_id, &previous_scope, scope)?;
        }
        RuntimeSessionResponse::Ready {
            request_id,
            foundation_digest,
            tail,
            duration,
            organizer,
            ..
        } => {
            admit_campaign(
                state,
                refresh,
                reset,
                CampaignAdmission {
                    request_id,
                    foundation_digest,
                    tail,
                    organizer,
                    duration,
                },
            )?;
        }
        RuntimeSessionResponse::AdvanceProgress { .. } => {
            return Err("Advance progress must use its readonly presentation admission".into());
        }
        RuntimeSessionResponse::Committed {
            request_id, tail, ..
        } => {
            apply_committed_response(state, refresh, reset, request_id, tail)?;
        }
        RuntimeSessionResponse::OrganizerStatus {
            request_id,
            snapshot,
            ..
        } => {
            reset.organizer_status(state, request_id, *snapshot)?;
        }
        RuntimeSessionResponse::OrganizerPreview {
            request_id,
            preview,
            ..
        } => {
            reset.organizer()?.previewed(request_id, preview, state)?;
        }
        RuntimeSessionResponse::OrganizerAccepted {
            request_id,
            commitment,
            ..
        } => {
            reset.organizer_accepted(state, request_id, commitment)?;
        }
        RuntimeSessionResponse::ArchiveProgress {
            durable_tick,
            verified_tick,
            ..
        } => {
            apply_archive_progress(state, refresh, durable_tick, verified_tick)?;
            if let Some(audit) = reset.qualification.as_deref_mut() {
                audit.advance_archive_progress(state)?;
            }
        }
        RuntimeSessionResponse::Error {
            request_id,
            code,
            tail,
            ..
        } => {
            refuse_runtime_request(state, reset, request_id, code, tail.as_ref())?;
        }
        RuntimeSessionResponse::Stopped { request_id, .. } => {
            if !state.stopped(request_id) {
                return Err("Unexpected shutdown acknowledgement; reopen the campaign.".into());
            }
        }
    }
    Ok(())
}

pub(crate) fn apply_committed_response(
    state: &mut ObserverSession,
    refresh: &mut DossierRefresh,
    reset: &mut CampaignReset,
    request_id: u64,
    tail: RuntimeSessionTail,
) -> Result<(), String> {
    if !state.acknowledge(request_id, tail.resolve_tick, tail.tick_content_hash) {
        return Err("Unexpected committed acknowledgement; reopen the campaign.".into());
    }
    if let Some(audit) = reset.qualification.as_deref_mut() {
        audit.advance_committed(state, request_id)?;
    }
    if state.organizer_enabled {
        state.pause_playback();
        state.set_organizer_control_pending(true);
        reset.organizer()?.committed();
    }
    refresh.bump();
    Ok(())
}

#[derive(SystemParam)]
pub(crate) struct CommandContext<'w> {
    qualification: Option<ResMut<'w, qualification::NativeAudit>>,
    opening: Option<ResMut<'w, crate::observer_opening::OpeningPresentation>>,
    state: ResMut<'w, ObserverSession>,
    ui: ResMut<'w, ObserverUiState>,
    pipe: Option<Res<'w, RuntimePipe>>,
    frame: Res<'w, ObserverFrame>,
    refresh: ResMut<'w, DossierRefresh>,
    audio: ResMut<'w, crate::observer_audio::ObserverAudioSettings>,
    feedback: ResMut<'w, ObserverFeedback>,
    time: Res<'w, Time>,
}

pub(crate) fn handle_commands(
    mut commands: MessageReader<ObserverCommand>,
    mut context: CommandContext,
    mut qualification: Option<ResMut<crate::organizer::qualification_input::HandlerReceipt>>,
) {
    for (command, message_id) in commands.read_with_id() {
        let command = *command;
        if context.ui.splash_visible {
            if command != ObserverCommand::Quit {
                if let Some(receipt) = qualification.as_deref_mut() {
                    receipt.observer_finished(
                        message_id,
                        false,
                        context.state.pending_advance_request(),
                        &context.state,
                    );
                }
                continue;
            }
        } else if context.ui.comparison_open {
            if let Some(receipt) = qualification.as_deref_mut() {
                receipt.observer_finished(
                    message_id,
                    false,
                    context.state.pending_advance_request(),
                    &context.state,
                );
            }
            continue;
        }
        if let ControlAvailability::Disabled(reason) = availability(command, &context.state) {
            if let Some(receipt) = qualification.as_deref_mut() {
                receipt.observer_finished(
                    message_id,
                    false,
                    context.state.pending_advance_request(),
                    &context.state,
                );
            }
            let now = context.time.elapsed_secs_f64();
            context.feedback.reject(reason, now);
            continue;
        }
        context.feedback.message = None;
        let before = context.state.pending_advance_request();
        apply_command(command, &mut context);
        if let Some(receipt) = qualification.as_deref_mut() {
            receipt.observer_finished(message_id, true, before, &context.state);
        }
    }
}

pub(crate) fn apply_command(command: ObserverCommand, context: &mut CommandContext) {
    let CommandContext {
        qualification,
        state,
        ui,
        pipe,
        refresh,
        feedback,
        time,
        ..
    } = context;
    match command {
        ObserverCommand::Quit => {
            state.pause_playback();
            state.quit_requested = true;
            ui.menu_open = true;
            ui.disclosure = None;
        }
        ObserverCommand::TogglePlay => {
            if state.playing {
                state.pause_playback();
            } else if !state.start_playback() {
                feedback.reject(
                    "Cannot start playback; reopen to reconcile progress.",
                    time.elapsed_secs_f64(),
                );
            }
        }
        ObserverCommand::Step => {
            state.pause_playback();
            if let Some(pipe) = pipe {
                send_advance(pipe, state, qualification.as_deref_mut());
            } else {
                feedback.reject(
                    "No campaign connection. Reopen the campaign from Menu.",
                    time.elapsed_secs_f64(),
                );
            }
        }
        ObserverCommand::Speed => {
            state.periods_per_second = match state.periods_per_second {
                1.0 => 2.0,
                2.0 => 5.0,
                _ => 1.0,
            }
        }
        ObserverCommand::Perspective => {
            let perspective = match state.perspective {
                Perspective::FullObserver => Perspective::PlayerKnowledge,
                Perspective::PlayerKnowledge => Perspective::FullObserver,
            };
            state.set_perspective(perspective);
            ui.disclosure = None;
            ui.evidence_open = false;
            refresh.bump();
        }
        ObserverCommand::PreviousPeriod | ObserverCommand::NextPeriod | ObserverCommand::Live => {
            let tick = match command {
                ObserverCommand::PreviousPeriod => state.viewed_tick.saturating_sub(1),
                ObserverCommand::NextPeriod => state.viewed_tick.saturating_add(1),
                _ => state.durable_tick,
            };
            state.inspect_tick(tick);
            refresh.bump();
        }
        command
            if command == ObserverCommand::ReopenCampaign || campaign_preset(command).is_some() =>
        {
            queue_menu_campaign(command, context);
        }
        _ => apply_presentation_command(command, context),
    }
}

pub(crate) fn queue_menu_campaign(command: ObserverCommand, context: &mut CommandContext) {
    let CommandContext {
        state,
        pipe,
        feedback,
        time,
        opening,
        ..
    } = context;
    if pipe.is_none() {
        feedback.reject(LAUNCHER_REQUIRED, time.elapsed_secs_f64());
        return;
    }
    state.pause_playback();
    let target = if command == ObserverCommand::ReopenCampaign {
        RuntimeSessionTarget::Open {
            campaign_id: state.campaign.as_uuid().to_string(),
        }
    } else {
        let Some(preset) = campaign_preset(command) else {
            feedback.reject(
                "This command does not select a new campaign.",
                time.elapsed_secs_f64(),
            );
            return;
        };
        RuntimeSessionTarget::New {
            campaign_id: uuid::Uuid::new_v4().to_string(),
            preset,
        }
    };
    if let Err(error) = state.queue_campaign(target) {
        state.fail(error);
    } else if let Some(opening) = opening {
        opening.launch_pending = true;
    }
}

pub(crate) fn campaign_preset(command: ObserverCommand) -> Option<RuntimeSessionPreset> {
    Some(match command {
        ObserverCommand::NewNationalCampaign => RuntimeSessionPreset::NationalWorld,
        ObserverCommand::NewCampaign => RuntimeSessionPreset::Standard,
        ObserverCommand::NewOrganizerCampaign => RuntimeSessionPreset::OrganizeInWayne,
        ObserverCommand::NewStatewideMaintenanceBaselineCampaign => {
            RuntimeSessionPreset::StatewideMaintenanceBaseline
        }
        ObserverCommand::NewStatewideMaintenanceLaborShortageCampaign => {
            RuntimeSessionPreset::StatewideMaintenanceLaborShortage
        }
        ObserverCommand::NewStatewideMaintenancePartsShortageCampaign => {
            RuntimeSessionPreset::StatewideMaintenancePartsShortage
        }
        ObserverCommand::NewStatewideMaintenanceBothCampaign => {
            RuntimeSessionPreset::StatewideMaintenanceBoth
        }
        ObserverCommand::NewStatewideBaselineCampaign => RuntimeSessionPreset::StatewideBaseline,
        ObserverCommand::NewStatewideFreightConstraintCampaign => {
            RuntimeSessionPreset::StatewideFreightConstraint
        }
        ObserverCommand::NewStatewidePackagingShortageCampaign => {
            RuntimeSessionPreset::StatewidePackagingShortage
        }
        ObserverCommand::NewStatewideBothCampaign => RuntimeSessionPreset::StatewideBoth,

        ObserverCommand::NewSharedFreightAmpleCampaign => RuntimeSessionPreset::SharedFreightAmple,
        ObserverCommand::NewSharedFreightConstrainedCampaign => {
            RuntimeSessionPreset::SharedFreightConstrained
        }
        ObserverCommand::NewDelayedCampaign => RuntimeSessionPreset::Delayed,
        _ => return None,
    })
}

pub(crate) fn apply_presentation_command(command: ObserverCommand, context: &mut CommandContext) {
    let CommandContext {
        state,
        ui,
        frame,
        audio,
        ..
    } = context;
    match command {
        ObserverCommand::Relationships => {
            ui.lens = crate::map_economy_lens::MapLens::Relationships;
            ui.disclosure = None;
        }
        ObserverCommand::NetworkSector(sector) => {
            ui.network_sector = sector;
            ui.road_layer = crate::observer_ui::RoadLayer::EconomyNetwork;
            ui.disclosure = None;
        }
        ObserverCommand::RoadLayer(layer) => {
            ui.road_layer = layer;
            ui.disclosure = None;
        }
        ObserverCommand::EconomicDetails => ui.economic_details_open = !ui.economic_details_open,
        ObserverCommand::Workforce(metric) => {
            ui.lens = crate::map_economy_lens::MapLens::Workforce(metric);
            ui.disclosure = None;
        }
        ObserverCommand::Lens(metric) => {
            ui.economic_details_open = true;
            ui.lens = crate::map_economy_lens::MapLens::Qcew(metric);
            ui.disclosure = None;
        }
        ObserverCommand::MaterialLens(kind) => {
            ui.economic_details_open = true;
            let good = match &ui.lens {
                crate::map_economy_lens::MapLens::Material { good, .. } => good.clone(),
                crate::map_economy_lens::MapLens::Relationships
                | crate::map_economy_lens::MapLens::Qcew(_)
                | crate::map_economy_lens::MapLens::Workforce(_) => None,
            };
            ui.lens = crate::map_economy_lens::MapLens::Material { kind, good };
            ui.lens.reconcile(frame.for_session(state), false);
            ui.disclosure = None;
        }
        ObserverCommand::CycleGood(backwards) => {
            ui.lens.cycle_good(frame.for_session(state), backwards);
        }
        ObserverCommand::Archive => ui.archive_open = !ui.archive_open,
        ObserverCommand::Menu => {
            if ui.menu_open && !crate::observer_title::can_continue(state) {
                return;
            }
            ui.menu_open = !ui.menu_open;
            ui.disclosure = None;
            state.pause_playback();
        }
        ObserverCommand::UiScale => ui.larger_interface = !ui.larger_interface,
        ObserverCommand::ReducedMotion => ui.reduced_motion = !ui.reduced_motion,
        ObserverCommand::MusicVolume => {
            audio.music_volume = if audio.music_volume < 1.0 {
                (audio.music_volume + 0.25).min(1.0)
            } else {
                0.0
            }
        }
        ObserverCommand::EffectsVolume => {
            audio.effects_volume = if audio.effects_volume < 0.2 {
                0.4
            } else if audio.effects_volume < 0.6 {
                0.75
            } else {
                0.0
            }
        }
        ObserverCommand::MusicTrack => audio.next_track(),
        ObserverCommand::History => {
            ui.history_open = !ui.history_open;
            if ui.history_open {
                ui.archive_open = false;
                ui.disclosure = None;
                state.pause_playback();
            }
        }
        ObserverCommand::StopOnDelivery => ui.stop_on_delivery = !ui.stop_on_delivery,
        ObserverCommand::Disclosure(disclosure) => {
            ui.disclosure = if ui.disclosure == Some(disclosure) {
                None
            } else {
                Some(disclosure)
            }
        }
        ObserverCommand::Evidence => ui.evidence_open = !ui.evidence_open,
        _ => unreachable!("transport commands are applied before presentation dispatch"),
    }
}

pub(crate) fn start_observation(
    mut state: ResMut<ObserverSession>,
    mut pending: ResMut<PendingObservation>,
    mut cache: ResMut<ObservationCache>,
    mut frame: ResMut<ObserverFrame>,
    mut qualification: Option<ResMut<qualification::NativeAudit>>,
) {
    let key = ObservationCacheKey::from_session(&state, qualification.as_deref());
    cache.reconcile(key);
    if state.quit_requested {
        pending.0 = None;
        *cache = ObservationCache::default();
        return;
    }
    if let Some((context, _)) = &pending.0 {
        if !state.accepts(context) {
            *frame = ObserverFrame::default();
            // A blocking database reconstruction cannot be cancelled at an await
            // point. Drain it before launching another large qualified read.
            // collect_observation discards its stale result without publication.
            if qualification.is_some() {
                return;
            }
            pending.0 = None;
        }
    }
    if state.phase != SessionPhase::Loading || pending.0.is_some() {
        return;
    }
    if qualification::awaiting_archive(&state, qualification.is_some()) {
        return;
    }
    if qualification
        .as_ref()
        .is_some_and(|audit| audit.awaiting_recovery_status())
    {
        return;
    }
    let audit_work = match qualification
        .as_deref_mut()
        .map(|audit| audit.begin(&state))
        .transpose()
    {
        Ok(work) => work.flatten(),
        Err(error) => {
            state.fail(error);
            return;
        }
    };
    *frame = ObserverFrame::default();
    let context = state.context();
    let requested = context.clone();
    let qualified = qualification.is_some();
    let reader = match (audit_work.is_some(), requested.perspective) {
        (true, _) | (_, Perspective::FullObserver) => cache.reader(
            ObserverVisibility::FullObserver,
            ObserverEconomyReader::from_observer_env,
        ),
        (false, Perspective::PlayerKnowledge) => cache.reader(
            ObserverVisibility::KnownPreview,
            ObserverEconomyReader::from_known_env,
        ),
    };
    let mut cursor = cache.cursor.take();
    let task = AsyncComputeTaskPool::get().spawn(async move {
        let started = std::time::Instant::now();
        let resumed_after = cursor
            .as_ref()
            .map(babylon_persistence::observer_reader::ObserverMaterialCursor::completed_tick);
        let mut qualification = None;
        let result = (|| {
            let reader = reader.map_err(|error| error.to_string())?;
            if let Some(work) = audit_work {
                let (prepared, candidate) = work.read(reader, &requested, &mut cursor)?;
                qualification = Some(candidate);
                return Ok(prepared);
            }
            // A known-only refresh has no material cursor. Preserve the private
            // authenticated cursor for the next qualification boundary.
            let snapshot = if qualified && requested.perspective == Perspective::PlayerKnowledge {
                reader.snapshot(requested.campaign, requested.tick)
            } else {
                reader.snapshot_with_cursor(requested.campaign, requested.tick, &mut cursor)
            };
            snapshot
                .map(PreparedObservation::new)
                .map_err(|error| error.to_string())
        })();
        bevy::log::info!(target: "babylon_client::timing",
            stage = "authenticated_observer_read",
            resumed_after = ?resumed_after,
            campaign = %requested.campaign.as_uuid(),
            tick = requested.tick,
            generation = requested.generation,
            perspective = ?requested.perspective,
            elapsed_us = started.elapsed().as_micros(),
            success = result.is_ok(),
            "observer read completed");
        ObservationRead {
            result,
            cursor,
            qualification,
        }
    });
    pending.0 = Some((context, task));
}

pub(crate) fn collect_observation(
    mut state: ResMut<ObserverSession>,
    mut pending: ResMut<PendingObservation>,
    mut cache: ResMut<ObservationCache>,
    mut frame: ResMut<ObserverFrame>,
    ui: Res<ObserverUiState>,
    mut qualification: Option<ResMut<qualification::NativeAudit>>,
) {
    let Some((context, task)) = &mut pending.0 else {
        return;
    };
    let Some(result) = block_on(bevy::tasks::futures_lite::future::poll_once(task)) else {
        return;
    };
    let context = context.clone();
    pending.0 = None;
    if !state.accepts(&context) {
        return;
    }
    match result.result {
        Ok(snapshot) => {
            let installed = install_observation(
                &mut state,
                &context,
                snapshot,
                &mut frame,
                ui.stop_on_delivery,
            );
            if installed {
                if let Some(candidate) = result.qualification {
                    let published = qualification
                        .as_deref_mut()
                        .ok_or_else(|| "native audit publication capability absent".to_string())
                        .and_then(|audit| audit.commit(&state, candidate));
                    if let Err(error) = published {
                        state.fail(error);
                        return;
                    }
                }
                cache.cursor = result.cursor;
            }
        }
        Err(error) => {
            // Reader failures leave the previously authenticated cursor intact.
            cache.cursor = result.cursor;
            bevy::log::error!(target: "babylon_client::timing",
                campaign = %context.campaign.as_uuid(),
                tick = context.tick,
                generation = context.generation,
                perspective = ?context.perspective,
                reason = %error,
                "authenticated observer read refused");
            state.fail(error);
        }
    }
}

pub(crate) fn install_observation(
    state: &mut ObserverSession,
    context: &ObservationContext,
    prepared: PreparedObservation,
    frame: &mut ObserverFrame,
    stop_on_delivery: bool,
) -> bool {
    if !state.accepts(context) {
        return false;
    }
    let PreparedObservation { snapshot, evidence } = prepared;
    let visibility = match context.perspective {
        Perspective::FullObserver => ObserverVisibility::FullObserver,
        Perspective::PlayerKnowledge => ObserverVisibility::KnownPreview,
    };
    if snapshot.campaign_id != context.campaign.as_uuid().to_string()
        || snapshot.resolve_tick != context.tick
        || snapshot.visibility != visibility
        || state.foundation_digest.as_deref() != Some(snapshot.foundation_digest.as_str())
        || (context.tick == state.durable_tick && snapshot.tick_content_hash != state.content_hash)
    {
        state.fail(
            "Observation identity mismatch; the last committed campaign was preserved.".into(),
        );
        return false;
    }
    if let Some(production) = &snapshot.production {
        if !production.duration.contains(snapshot.resolve_tick)
            || state
                .duration
                .is_some_and(|duration| duration != production.duration)
        {
            state.fail("Observation duration differs from the admitted campaign.".into());
            return false;
        }
        state.duration = Some(production.duration);
    }
    if state.installed(context) {
        // Only newly installed, disclosed events from this committed period can
        // interrupt transport. Historical and hidden material cannot pause it.
        if state.playing
            && state.viewed_tick == state.durable_tick
            && snapshot.production.as_ref().is_some_and(|production| {
                production.events.iter().any(|event| {
                    event.period == snapshot.resolve_tick
                        && (event.kind == "freight loss"
                            || (stop_on_delivery && event.kind == "delivery"))
                })
            })
        {
            state.pause_playback();
        }
        *frame = ObserverFrame(Some(snapshot), Some(evidence));
        return true;
    }
    false
}

pub(crate) fn playback(
    time: Res<Time>,
    ui: Res<ObserverUiState>,
    pipe: Option<Res<RuntimePipe>>,
    mut clock: ResMut<PlaybackClock>,
    mut state: ResMut<ObserverSession>,
    mut qualification: Option<ResMut<qualification::NativeAudit>>,
) {
    if state.quit_requested {
        return;
    }
    let Some(pipe) = pipe else {
        return;
    };
    if ui.splash_visible {
        if state.playing {
            state.pause_playback();
        }
        clock.elapsed = 0.0;
    }
    if !ui.splash_visible && state.playback_due() {
        clock.elapsed += time.delta_secs_f64();
        if clock.elapsed >= state.periods_per_second.recip() {
            clock.elapsed = 0.0;
            send_advance(&pipe, &mut state, qualification.as_deref_mut());
        }
    } else {
        clock.elapsed = 0.0;
    }
}

pub(crate) fn send_campaign_switch(
    pipe: Option<Res<RuntimePipe>>,
    mut state: ResMut<ObserverSession>,
    mut qualification: Option<ResMut<qualification::NativeAudit>>,
) {
    let Some(pipe) = pipe else {
        return;
    };
    if !state.switch_send_due() {
        return;
    }
    let Some(request) = state.pending_switch_request() else {
        return;
    };
    if let Some(audit) = qualification.as_deref_mut() {
        if let Err(error) = audit.stage_reopen(&state, &request) {
            state.fail(error);
            return;
        }
    }
    match pipe.requests.try_send(request) {
        Ok(()) => state.switch_sent(),
        Err(mpsc::TrySendError::Full(_)) => {}
        Err(mpsc::TrySendError::Disconnected(_)) => {
            state.disconnect("Runtime disconnected; close and relaunch Babylon.".into());
        }
    }
}

pub(crate) fn finish_shutdown(
    pipe: Option<Res<RuntimePipe>>,
    mut state: ResMut<ObserverSession>,
    mut shutdown: ResMut<ShutdownProgress>,
    time: Res<Time<Real>>,
    mut exits: MessageWriter<AppExit>,
) {
    if !state.quit_requested || shutdown.exit_sent {
        return;
    }
    if state.playing {
        state.playing = false;
    }
    let started = *shutdown.started_at.get_or_insert(time.elapsed_secs_f64());
    if time.elapsed_secs_f64() - started >= SHUTDOWN_TIMEOUT_SECS {
        state.disconnect(
            "Runtime shutdown timed out; reopen to reconcile committed progress.".into(),
        );
    }
    if pipe.is_none() || state.runtime_disconnected() || state.phase == SessionPhase::Closed {
        shutdown.exit_sent = true;
        exits.write(AppExit::Success);
        return;
    }
    if shutdown.stop_sent {
        return;
    }
    let Some(request) = state.pending_stop_request() else {
        return;
    };
    match pipe
        .expect("connection checked above")
        .requests
        .try_send(request)
    {
        Ok(()) => {
            state.stop_sent();
            shutdown.stop_sent = true;
        }
        Err(mpsc::TrySendError::Full(_)) => {}
        Err(mpsc::TrySendError::Disconnected(_)) => {
            state.disconnect("Runtime disconnected during shutdown; reopen to reconcile.".into());
            shutdown.exit_sent = true;
            exits.write(AppExit::Success);
        }
    }
}

pub struct ObserverIoPlugin;

impl Plugin for ObserverIoPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<crate::observer_progress::OperationProgress>()
            .add_systems(
                Update,
                crate::observer_progress::track
                    .after(ObserverSet::Install)
                    .before(ObserverSet::Paint),
            )
            .init_resource::<PendingObservation>()
            .init_resource::<ObservationCache>()
            .init_resource::<PlaybackClock>()
            .init_resource::<ShutdownProgress>()
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
            .add_systems(Startup, start_pipe)
            .add_systems(
                Update,
                (
                    receive,
                    handle_commands,
                    send_campaign_switch,
                    finish_shutdown,
                )
                    .chain()
                    .in_set(ObserverSet::Receive),
            )
            .add_systems(
                Update,
                (start_observation, collect_observation, playback)
                    .chain()
                    .in_set(ObserverSet::Install),
            );
    }
}
