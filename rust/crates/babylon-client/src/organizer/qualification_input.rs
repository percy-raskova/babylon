//! Opt-in bounded inputs to the real windowed controls. This adapter owns no
//! runtime requests, material effects, authoritative time, or qualification result.

use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::Shutdown;
use std::os::unix::fs::{FileTypeExt, MetadataExt};
use std::os::unix::net::UnixStream;
use std::path::Path;
use std::sync::{mpsc, Mutex};
use std::thread;
use std::time::Duration;

use bevy::ecs::message::MessageId;
use bevy::prelude::*;
use serde::Deserialize;
use serde_json::{json, Value};

use super::{ui, OrganizerClient, OrganizerInspector, RequestKind};
use crate::observer::{ObservationContext, ObserverSession, SessionPhase};
use crate::observer_controls::ControlAvailability;
use crate::observer_io::{ObserverSet, RuntimePipe};
use crate::observer_opening::MenuPage;
use crate::observer_opening::{OpeningPresentation, OpeningStage};
use crate::observer_ui::{ObserverCommand, ObserverUiState};
use crate::observer_warning::ContinueWarning;
use crate::production::PrimaryView;
use babylon_persistence::runtime_session::{
    OrganizerChoice, OrganizerCommand, RuntimeSessionScope,
};
use mpsc::Receiver;
use mpsc::SyncSender;
use mpsc::TryRecvError;
use thread::Builder;
use ui::OrganizerAction;
use uuid::Uuid;

// Designed bounds for instrumentation, independent of the captured game policy.
const INPUT_BYTES: u64 = 4096;
const OUTPUT_BYTES: usize = 32_768;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct StartupAdmission {
    version: u32,
    campaign_id: String,
    phase: StartupPhase,
}

#[derive(Deserialize)]
#[serde(rename_all = "snake_case")]
enum StartupPhase {
    CaptureReady,
}

fn read_startup(reader: &mut impl BufRead, campaign: &str) -> Result<(), &'static str> {
    let mut bytes = Vec::new();
    let count = reader
        .take(INPUT_BYTES + 1)
        .read_until(b'\n', &mut bytes)
        .map_err(|_| "capture_startup_read_failed")?;
    if u64::try_from(count).map_err(|_| "capture_startup_frame_overflow")? > INPUT_BYTES
        || bytes.last() != Some(&b'\n')
    {
        return Err("capture_startup_not_bounded");
    }
    let admission: StartupAdmission =
        serde_json::from_slice(&bytes).map_err(|_| "capture_startup_frame_invalid")?;
    if admission.version != 2 || admission.campaign_id != campaign {
        return Err("capture_startup_identity_invalid");
    }
    let StartupPhase::CaptureReady = admission.phase;
    Ok(())
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
enum Action {
    Status,
    ContinueWarning,
    ContinueTitle,
    OpenOrganizer,
    OpenDirection,
    CloseInspector,
    ChooseRemoteAid,
    ChooseLocalAid,
    ChoosePauseStanding,
    ChooseResumeStanding,
    Review,
    Confirm,
    Step,
    Reopen,
    Refresh,
    Quit,
}

impl Action {
    fn organizer(self) -> Option<OrganizerAction> {
        use ui::OrganizerAction as O;
        Some(match self {
            Self::OpenOrganizer => O::Open,
            Self::OpenDirection => O::Inspect(OrganizerInspector::Direction),
            Self::CloseInspector => O::CloseInspector,
            Self::ChooseRemoteAid => O::Choose(OrganizerChoice::RemoteAid),
            Self::ChooseLocalAid => O::Choose(OrganizerChoice::LocalAid),
            Self::ChoosePauseStanding => O::Choose(OrganizerChoice::PauseStanding),
            Self::ChooseResumeStanding => O::Choose(OrganizerChoice::ResumeStanding),
            Self::Review => O::Review,
            Self::Confirm => O::Confirm,
            Self::Refresh => O::Refresh,
            _ => return None,
        })
    }
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    version: u32,
    sequence: u64,
    campaign_id: String,
    #[serde(deserialize_with = "required_scope")]
    scope_epoch: Option<u64>,
    expected_tick: u64,
    expected_generation: u64,
    action: Action,
}

fn required_scope<'de, D: serde::Deserializer<'de>>(
    deserializer: D,
) -> Result<Option<u64>, D::Error> {
    Option::<u64>::deserialize(deserializer)
}

fn read_input(reader: &mut impl BufRead) -> Result<Option<Input>, &'static str> {
    let mut bytes = Vec::new();
    let count = reader
        .take(INPUT_BYTES + 1)
        .read_until(b'\n', &mut bytes)
        .map_err(|_| "control_read_failed")?;
    if count == 0 {
        return Ok(None);
    }
    if u64::try_from(count).map_err(|_| "control_frame_overflow")? > INPUT_BYTES
        || bytes.last() != Some(&b'\n')
    {
        return Err("control_frame_not_bounded");
    }
    let input: Input = serde_json::from_slice(&bytes).map_err(|_| "control_frame_invalid")?;
    if input.version != 2 || input.sequence == 0 {
        return Err("control_version_or_sequence_invalid");
    }
    Ok(Some(input))
}

enum Incoming {
    Input(Input),
    Closed,
    Failed(&'static str),
}

#[derive(Resource)]
pub(crate) struct Transport {
    incoming: Mutex<Receiver<Incoming>>,
    outgoing: SyncSender<Vec<u8>>,
    socket: UnixStream,
}

impl Transport {
    pub(crate) fn connect(path: &Path, campaign: &str) -> Result<Self, String> {
        let identity = Uuid::parse_str(campaign).map_err(|_| "capture_startup_campaign_invalid")?;
        if identity.is_nil() || identity.to_string() != campaign {
            return Err("capture_startup_campaign_invalid".into());
        }
        let parent = path.parent().ok_or("qualification socket has no parent")?;
        let owner = fs::metadata("/proc/self")
            .map_err(|_| "cannot verify qualification owner")?
            .uid();
        let directory =
            fs::symlink_metadata(parent).map_err(|_| "cannot verify qualification directory")?;
        let endpoint =
            fs::symlink_metadata(path).map_err(|_| "cannot verify qualification socket")?;
        if !path.is_absolute()
            || parent.canonicalize().ok().as_deref() != Some(parent)
            || !directory.is_dir()
            || directory.uid() != owner
            || directory.mode() & 0o777 != 0o700
            || !endpoint.file_type().is_socket()
            || endpoint.uid() != owner
            || endpoint.mode() & 0o777 != 0o600
        {
            return Err("qualification socket must be private, owned, and free of symlinks".into());
        }
        let socket =
            UnixStream::connect(path).map_err(|_| "cannot connect qualification socket")?;
        Self::from_stream(socket, campaign)
    }

    fn from_stream(socket: UnixStream, campaign: &str) -> Result<Self, String> {
        let read = socket
            .try_clone()
            .map_err(|_| "cannot own qualification input")?;
        let mut write = socket
            .try_clone()
            .map_err(|_| "cannot own qualification output")?;
        write
            .set_write_timeout(Some(Duration::from_secs(5)))
            .map_err(|_| "cannot bound qualification output")?;
        // App construction has not installed the runtime pipe yet. Only this
        // private harness admission releases the queued initial New/Open.
        read.set_read_timeout(Some(Duration::from_secs(30)))
            .map_err(|_| "cannot bound capture startup")?;
        let mut reader = BufReader::new(read);
        read_startup(&mut reader, campaign)?;
        reader
            .get_ref()
            .set_read_timeout(None)
            .map_err(|_| "cannot restore qualification input after capture startup")?;
        let (incoming_tx, incoming) = mpsc::sync_channel(1);
        let (outgoing, outgoing_rx) = mpsc::sync_channel::<Vec<u8>>(1);
        Builder::new()
            .name("qualification-input".into())
            .spawn(move || loop {
                let (message, terminal) = match read_input(&mut reader) {
                    Ok(Some(input)) => (Incoming::Input(input), false),
                    Ok(None) => (Incoming::Closed, true),
                    Err(error) => (Incoming::Failed(error), true),
                };
                if incoming_tx.send(message).is_err() || terminal {
                    break;
                }
            })
            .map_err(|_| {
                let _ = socket.shutdown(Shutdown::Both);
                "cannot start qualification input"
            })?;
        Builder::new()
            .name("qualification-output".into())
            .spawn(move || {
                while let Ok(bytes) = outgoing_rx.recv() {
                    if write.write_all(&bytes).is_err() {
                        let _ = write.shutdown(Shutdown::Both);
                        break;
                    }
                }
            })
            .map_err(|_| {
                let _ = socket.shutdown(Shutdown::Both);
                "cannot start qualification output"
            })?;
        Ok(Self {
            incoming: Mutex::new(incoming),
            outgoing,
            socket,
        })
    }
}

impl Drop for Transport {
    fn drop(&mut self) {
        let _ = self.socket.shutdown(Shutdown::Both);
    }
}

struct Pending {
    input: Input,
    context: ObservationContext,
    scope: Option<RuntimeSessionScope>,
    reviewed: Option<OrganizerCommand>,
    request: Option<u64>,
    choice: OrganizerChoice,
    handled: bool,
    foundation: Option<String>,
    content_hash: Option<String>,
}

#[derive(Clone, Copy)]
enum Tracked {
    Organizer(usize, Action),
    Observer(usize, Action),
}

enum Witness {
    Applied,
    Organizer {
        id: u64,
        kind: RequestKind,
        command: Option<OrganizerCommand>,
    },
    Advance(u64),
}

/// A witness from the existing handler for this exact input message, captured
/// before any response can clear its pending request. Not an engine receipt.
#[derive(Resource, Default)]
pub(crate) struct HandlerReceipt {
    tracked: Option<Tracked>,
    handled: Option<Result<Witness, &'static str>>,
}

impl HandlerReceipt {
    pub(crate) fn organizer_finished(
        &mut self,
        id: MessageId<OrganizerAction>,
        applied: bool,
        client: &OrganizerClient,
    ) {
        let Some(Tracked::Organizer(expected, action)) = self.tracked else {
            return;
        };
        if expected != id.id {
            return;
        }
        self.handled = Some(if !applied {
            Err("ordinary_handler_refused")
        } else if matches!(action, Action::Review | Action::Confirm) {
            client
                .pending
                .as_ref()
                .map_or(Err("ordinary_handler_refused"), |p| {
                    Ok(Witness::Organizer {
                        id: p.id,
                        kind: p.kind,
                        command: p.command.clone(),
                    })
                })
        } else {
            Ok(Witness::Applied)
        });
    }

    pub(crate) fn observer_finished(
        &mut self,
        id: MessageId<ObserverCommand>,
        applied: bool,
        before: Option<u64>,
        session: &ObserverSession,
    ) {
        let Some(Tracked::Observer(expected, action)) = self.tracked else {
            return;
        };
        if expected != id.id {
            return;
        }
        self.handled = Some(if !applied {
            Err("ordinary_handler_refused")
        } else if action == Action::Step {
            match (before, session.pending_advance_request()) {
                (None, Some(request)) => Ok(Witness::Advance(request)),
                _ => Err("ordinary_handler_refused"),
            }
        } else {
            Ok(Witness::Applied)
        });
    }
}

#[derive(Resource)]
struct Controls {
    next_sequence: Option<u64>,
    pending: Option<Pending>,
    reply: Option<Vec<u8>>,
    disabled: bool,
}

impl Default for Controls {
    fn default() -> Self {
        Self {
            next_sequence: Some(1),
            pending: None,
            reply: None,
            disabled: false,
        }
    }
}

fn state(
    session: &ObserverSession,
    client: &OrganizerClient,
    ui: &ObserverUiState,
    opening: &OpeningPresentation,
    view: PrimaryView,
) -> Value {
    json!({"campaign_id": session.campaign.as_uuid().to_string(),
        "scope_epoch": session.runtime_scope().map(|scope| scope.epoch),
        "durable_tick":session.durable_tick,"viewed_tick":session.viewed_tick,
        "generation":session.generation,"phase":format!("{:?}",session.phase),
        "foundation_sha256":session.foundation_digest,"tick_content_hash":session.content_hash,
        "archive_verified_tick":session.archive_verified_tick,
        "advance_pending":session.advance_pending(),"lifecycle_pending":session.lifecycle_pending(),
        "organizer_pending":client.pending.is_some(),"organizer_status_due":client.status_due,
        "organizer_period":client.view.as_ref().map(|view| view.period),
        "choice":client.choice(),"reviewed_command":client.reviewed_command,"preview":client.preview,
        "commitment":client.commitment,"quit_requested":session.quit_requested,
        "splash_visible":ui.splash_visible,"menu_open":ui.menu_open,
        "opening_stage":format!("{:?}",opening.stage),"primary_view":format!("{view:?}"),
        "inspector":format!("{:?}",client.inspector)})
}

fn response(sequence: Option<u64>, event: &str, reason: Option<&str>, state: Value) -> Vec<u8> {
    let mut bytes = serde_json::to_vec(
        &json!({"version":2,"sequence":sequence,"event":event,"reason":reason,"state":state}),
    )
    .expect("control response contains only finite typed state");
    if bytes.len() >= OUTPUT_BYTES {
        bytes = br#"{"version":2,"sequence":null,"event":"refused","reason":"control_response_not_bounded"}"#.to_vec();
    }
    bytes.push(b'\n');
    bytes
}

fn precondition(input: &Input, session: &ObserverSession) -> bool {
    input.campaign_id == session.campaign.as_uuid().to_string()
        && input.scope_epoch == session.runtime_scope().map(|scope| scope.epoch)
        && input.expected_tick == session.durable_tick
        && input.expected_generation == session.generation
}

fn available(
    action: Action,
    session: &ObserverSession,
    client: &OrganizerClient,
    ui: &ObserverUiState,
    opening: &OpeningPresentation,
    view: PrimaryView,
    pipe: bool,
) -> bool {
    if let Some(action) = action.organizer() {
        return ui::visible(action, client, session, ui, view)
            && ui::enabled(action, client, session);
    }
    match action {
        Action::Status => true,
        Action::ContinueWarning => ui.splash_visible && opening.stage == OpeningStage::Warning,
        Action::ContinueTitle => {
            opening.stage == OpeningStage::Title
                && opening.menu_page == MenuPage::Home
                && ui.menu_open
                && !ui.splash_visible
                && !ui.comparison_open
                && !opening.launch_pending
                && crate::observer_title::can_continue(session)
        }
        Action::Step => {
            pipe && !ui.splash_visible
                && !ui.menu_open
                && !ui.comparison_open
                && crate::observer_controls::availability(ObserverCommand::Step, session)
                    == ControlAvailability::Enabled
        }
        Action::Reopen => {
            pipe && !ui.splash_visible
                && !ui.menu_open
                && !ui.comparison_open
                && !session.lifecycle_pending()
                && !session.advance_pending()
                && !session.organizer_control_pending()
                && client.pending.is_none()
                && session.viewed_tick == session.durable_tick
                && matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
                && crate::observer_controls::availability(ObserverCommand::ReopenCampaign, session)
                    == ControlAvailability::Enabled
        }
        Action::Quit => !ui.comparison_open && !session.quit_requested,
        _ => false,
    }
}

#[derive(bevy::ecs::system::SystemParam)]
struct Situation<'w> {
    session: Res<'w, ObserverSession>,
    client: Res<'w, OrganizerClient>,
    ui: Res<'w, ObserverUiState>,
    opening: Res<'w, OpeningPresentation>,
    view: Res<'w, PrimaryView>,
    pipe: Option<Res<'w, RuntimePipe>>,
}

impl Situation<'_> {
    fn allows(&self, input: &Input) -> bool {
        precondition(input, &self.session)
            && available(
                input.action,
                &self.session,
                &self.client,
                &self.ui,
                &self.opening,
                *self.view,
                self.pipe.is_some(),
            )
    }

    fn state(&self) -> Value {
        state(
            &self.session,
            &self.client,
            &self.ui,
            &self.opening,
            *self.view,
        )
    }
}

impl Controls {
    fn respond(
        &mut self,
        sequence: Option<u64>,
        event: &str,
        reason: Option<&str>,
        situation: &Situation,
    ) {
        self.reply = Some(response(sequence, event, reason, situation.state()));
    }
}

enum OutputReady {
    Ready,
    Backpressure,
    Closed,
}

fn flush_reply(transport: &Transport, controls: &mut Controls) -> OutputReady {
    let Some(bytes) = controls.reply.take() else {
        return OutputReady::Ready;
    };
    match transport.outgoing.try_send(bytes) {
        Ok(()) => OutputReady::Ready,
        Err(mpsc::TrySendError::Full(bytes)) => {
            controls.reply = Some(bytes);
            OutputReady::Backpressure
        }
        Err(mpsc::TrySendError::Disconnected(_)) => OutputReady::Closed,
    }
}

#[allow(clippy::too_many_arguments)] // The three message writers route distinct existing input ports.
fn dispatch(
    transport: Res<Transport>,
    mut controls: ResMut<Controls>,
    mut receipt: ResMut<HandlerReceipt>,
    situation: Situation,
    mut organizer: MessageWriter<OrganizerAction>,
    mut observer: MessageWriter<ObserverCommand>,
    mut warning: MessageWriter<ContinueWarning>,
    mut commands: Commands,
) {
    match flush_reply(&transport, &mut controls) {
        OutputReady::Ready => {}
        OutputReady::Backpressure => return,
        OutputReady::Closed => {
            controls.disabled = true;
            controls.pending = None;
            observer.write(ObserverCommand::Quit);
            return;
        }
    }
    if controls.disabled {
        return;
    }
    let received = match transport.incoming.lock() {
        Ok(receiver) => receiver.try_recv(),
        Err(_) => Ok(Incoming::Failed("control_input_lock_failed")),
    };
    let input = match received {
        Err(TryRecvError::Empty) => return,
        Ok(Incoming::Input(input)) if controls.pending.is_none() => input,
        other => {
            let reason = match other {
                Ok(Incoming::Failed(reason)) => reason,
                Ok(Incoming::Input(_)) => "control_input_pipelined",
                _ => "control_input_closed",
            };
            controls.respond(None, "refused", Some(reason), &situation);
            controls.disabled = true;
            controls.pending = None;
            observer.write(ObserverCommand::Quit);
            return;
        }
    };
    let sequence = input.sequence;
    if controls.next_sequence != Some(sequence) {
        controls.respond(
            Some(sequence),
            "refused",
            Some("control_sequence_mismatch"),
            &situation,
        );
        return;
    }
    controls.next_sequence = sequence.checked_add(1);
    if !situation.allows(&input) {
        controls.respond(
            Some(sequence),
            "refused",
            Some("control_stale_or_unavailable"),
            &situation,
        );
        return;
    }
    if input.action == Action::Status {
        controls.respond(Some(sequence), "observed", None, &situation);
        return;
    }
    receipt.tracked = None;
    receipt.handled = None;
    if let Some(action) = input.action.organizer() {
        receipt.tracked = Some(Tracked::Organizer(organizer.write(action).id, input.action));
    } else {
        match input.action {
            Action::ContinueWarning => {
                warning.write(ContinueWarning);
            }
            Action::ContinueTitle => {
                commands.trigger(crate::observer_title::ContinueTitle);
            }
            action @ (Action::Step | Action::Reopen | Action::Quit) => {
                let command = match action {
                    Action::Step => ObserverCommand::Step,
                    Action::Reopen => ObserverCommand::ReopenCampaign,
                    Action::Quit => ObserverCommand::Quit,
                    _ => unreachable!("selected observer input"),
                };
                receipt.tracked = Some(Tracked::Observer(observer.write(command).id, action));
            }
            _ => unreachable!("available action has one existing handler"),
        }
    }
    controls.pending = Some(Pending {
        input,
        context: situation.session.context(),
        scope: situation.session.runtime_scope().cloned(),
        reviewed: situation.client.reviewed_command.clone(),
        request: None,
        choice: situation.client.choice(),
        handled: receipt.tracked.is_none(),
        foundation: situation.session.foundation_digest.clone(),
        content_hash: situation.session.content_hash.clone(),
    });
}

fn capture_handler(pending: &mut Pending, witness: Witness) -> Result<(), &'static str> {
    match witness {
        Witness::Applied
            if !matches!(
                pending.input.action,
                Action::Review | Action::Confirm | Action::Step
            ) => {}
        Witness::Advance(id) if pending.input.action == Action::Step => pending.request = Some(id),
        Witness::Organizer { id, kind, command } => {
            match pending.input.action {
                Action::Review
                    if kind == RequestKind::Preview
                        && command.as_ref().is_some_and(|c| {
                            c.choice == pending.choice
                                && c.expected_period == pending.input.expected_tick
                        }) =>
                {
                    pending.reviewed = command;
                }
                Action::Confirm
                    if kind == RequestKind::Submit
                        && command.is_some()
                        && command == pending.reviewed => {}
                _ => return Err("control_request_changed"),
            }
            pending.request = Some(id);
        }
        _ => return Err("control_request_changed"),
    }
    pending.handled = true;
    Ok(())
}

fn outcome(pending: &Pending, s: &Situation) -> Option<Result<&'static str, &'static str>> {
    if pending.input.action == Action::Reopen {
        return reopen_outcome(pending, &s.session, &s.client);
    }
    if s.session.runtime_scope() != pending.scope.as_ref()
        || matches!(s.session.phase, SessionPhase::Failed | SessionPhase::Closed)
    {
        return Some(Err("control_context_lost"));
    }
    let action = pending.input.action;
    if action == Action::Quit {
        return s.session.quit_requested.then_some(Ok("quit_requested"));
    }
    if action != Action::Step && s.session.context() != pending.context {
        return Some(Err("control_context_changed"));
    }
    if action == Action::Refresh {
        return Some(Ok("refresh_requested"));
    }
    if action == Action::Step {
        if let Some(request) = s.session.pending_advance_request() {
            if pending.request.is_some_and(|id| id != request) {
                return Some(Err("control_request_changed"));
            }
            return None;
        }
        if pending.request.is_none() {
            return Some(Err("ordinary_handler_refused"));
        }
        if pending.input.expected_tick.checked_add(1) != Some(s.session.durable_tick) {
            return Some(Err("control_commit_mismatch"));
        }
        return (matches!(
            s.session.phase,
            SessionPhase::Ready | SessionPhase::Complete
        ) && s.session.viewed_tick == s.session.durable_tick
            && s.session.content_hash.is_some())
        .then_some(Ok("committed_and_installed"));
    }
    if matches!(action, Action::Review | Action::Confirm) {
        return organizer_outcome(pending, s);
    }
    let applied = match action.organizer() {
        Some(OrganizerAction::Choose(choice)) => s.client.choice() == choice,
        Some(OrganizerAction::Open) => *s.view == PrimaryView::Organizer,
        Some(OrganizerAction::Inspect(inspector)) => s.client.inspector == inspector,
        Some(OrganizerAction::CloseInspector) => s.client.inspector == OrganizerInspector::Closed,
        _ => match action {
            Action::ContinueWarning => s.opening.stage == OpeningStage::Production,
            Action::ContinueTitle => !s.ui.menu_open,
            _ => false,
        },
    };
    Some(if applied {
        Ok("applied")
    } else {
        Err("ordinary_handler_refused")
    })
}

fn organizer_outcome(
    pending: &Pending,
    s: &Situation,
) -> Option<Result<&'static str, &'static str>> {
    let action = pending.input.action;
    if action == Action::Confirm
        && pending.reviewed.is_some()
        && s.client
            .commitment
            .as_ref()
            .is_some_and(|c| Some(&c.command) == pending.reviewed.as_ref())
        && (s.client.status_due
            || s.client
                .pending
                .as_ref()
                .is_some_and(|p| p.kind == RequestKind::Status))
    {
        return None;
    }
    if let Some(request) = &s.client.pending {
        let expected = if action == Action::Review {
            RequestKind::Preview
        } else {
            RequestKind::Submit
        };
        if request.kind != expected
            || pending.request.is_some_and(|id| id != request.id)
            || (action == Action::Confirm && request.command != pending.reviewed)
        {
            return Some(Err("control_request_changed"));
        }
        return None;
    }
    if pending.request.is_none() {
        return Some(Err("ordinary_handler_refused"));
    }
    Some(match action {
        Action::Review
            if s.client.review_context.as_ref() == Some(&pending.context)
                && pending.reviewed.is_some()
                && s.client.reviewed_command == pending.reviewed
                && s.client
                    .preview
                    .as_ref()
                    .is_some_and(|p| p.refusal.is_none()) =>
        {
            Ok("preview_admitted")
        }
        Action::Confirm
            if pending.reviewed.is_some()
                && s.client
                    .commitment
                    .as_ref()
                    .is_some_and(|c| Some(&c.command) == pending.reviewed.as_ref()) =>
        {
            Ok("acceptance_admitted")
        }
        _ => Err("ordinary_response_refused"),
    })
}

fn reopen_outcome(
    pending: &Pending,
    session: &ObserverSession,
    client: &OrganizerClient,
) -> Option<Result<&'static str, &'static str>> {
    if matches!(session.phase, SessionPhase::Failed | SessionPhase::Closed) {
        return Some(Err("control_context_lost"));
    }
    let (Some(previous), Some(current)) = (&pending.scope, session.runtime_scope()) else {
        return Some(Err("control_reopen_scope_absent"));
    };
    if session.campaign != pending.context.campaign || current.campaign_id != previous.campaign_id {
        return Some(Err("control_reopen_campaign_changed"));
    }
    if current.epoch == previous.epoch && session.lifecycle_pending() {
        return None;
    }
    if previous.epoch.checked_add(1) != Some(current.epoch) {
        return Some(Err("control_reopen_scope_changed"));
    }
    if session.lifecycle_pending()
        || matches!(
            session.phase,
            SessionPhase::Connecting | SessionPhase::Loading
        )
    {
        return None;
    }
    if session.durable_tick != pending.input.expected_tick
        || session.viewed_tick != pending.input.expected_tick
        || session.foundation_digest != pending.foundation
        || session.content_hash != pending.content_hash
        || session.generation <= pending.context.generation
        || session.advance_pending()
    {
        return Some(Err("control_reopen_state_changed"));
    }
    if session.archive_verified_tick != session.durable_tick
        || client.pending.is_some()
        || client.status_due
        || session.organizer_control_pending()
    {
        return None;
    }
    if !matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
        || (session.organizer_enabled
            && client.view.as_ref().map(|v| v.period) != Some(session.durable_tick))
    {
        return Some(Err("control_reopen_state_not_installed"));
    }
    Some(Ok("reopened_and_installed"))
}

fn complete(
    mut controls: ResMut<Controls>,
    mut receipt: ResMut<HandlerReceipt>,
    situation: Situation,
) {
    if controls.reply.is_some() || controls.disabled {
        return;
    }
    let Some(pending) = controls.pending.as_mut() else {
        return;
    };
    let captured = if pending.handled {
        Ok(())
    } else {
        receipt
            .handled
            .take()
            .unwrap_or(Err("ordinary_handler_not_observed"))
            .and_then(|w| capture_handler(pending, w))
    };
    let result = match captured {
        Ok(()) => outcome(pending, &situation),
        Err(reason) => Some(Err(reason)),
    };
    if let Some(result) = result {
        let sequence = pending.input.sequence;
        let (event, reason) = match result {
            Ok(event) => (event, None),
            Err(reason) => ("refused", Some(reason)),
        };
        controls.reply = Some(response(Some(sequence), event, reason, situation.state()));
        controls.pending = None;
        receipt.tracked = None;
    }
}

pub(crate) fn install(app: &mut App, transport: Transport) {
    app.insert_resource(transport)
        .init_resource::<Controls>()
        .init_resource::<HandlerReceipt>()
        .add_systems(Update, dispatch.before(ObserverSet::Input))
        .add_systems(
            Update,
            // Witness the real warning transition before a long frame reaches Title.
            complete
                .after(ObserverSet::Install)
                .after(crate::observer_warning::apply_continue)
                .before(crate::observer_opening::advance)
                .before(ObserverSet::Paint),
        );
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::observer_opening::ProductionSkip;
    use crate::observer_warning::ContinueWarning;
    use babylon_kernel::clock::CampaignDuration;
    use babylon_persistence::identity::CampaignId;
    use bevy::time::TimeUpdateStrategy;
    use fs::Permissions;
    use std::io::Cursor;
    use std::os::unix::fs::PermissionsExt;
    use std::os::unix::net::UnixListener;
    use std::path::PathBuf;
    use ui::OrganizerAction;
    use uuid::Uuid;

    struct SocketFixture(PathBuf);

    impl Drop for SocketFixture {
        fn drop(&mut self) {
            let _ = fs::remove_file(self.0.join("control.sock"));
            let _ = fs::remove_dir(&self.0);
        }
    }

    #[test]
    fn qualification_socket_is_private_lossless_and_closes_on_drop() {
        let fixture =
            SocketFixture(std::env::temp_dir().join(format!("babylon-q-{}", Uuid::new_v4())));
        fs::create_dir(&fixture.0).unwrap();
        fs::set_permissions(&fixture.0, Permissions::from_mode(0o700)).unwrap();
        let path = fixture.0.join("control.sock");
        let listener = UnixListener::bind(&path).unwrap();
        fs::set_permissions(&path, Permissions::from_mode(0o600)).unwrap();
        let (started, ready) = mpsc::sync_channel(1);
        let connect_path = path.clone();
        let worker = thread::spawn(move || {
            started
                .send(Transport::connect(
                    &connect_path,
                    "00000000-0000-0000-0000-000000000001",
                ))
                .unwrap();
        });
        let (mut peer, _) = listener.accept().unwrap();
        peer.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        assert!(
            matches!(
                ready.recv_timeout(Duration::from_millis(50)),
                Err(mpsc::RecvTimeoutError::Timeout)
            ),
            "campaign startup must wait for explicit capture admission"
        );
        let mut admission = b"{\"version\":2,\"campaign_id\":\"00000000-0000-0000-0000-000000000001\",\"phase\":\"capture_ready\"}\n".to_vec();
        admission.extend(frame(""));
        peer.write_all(&admission).unwrap();
        let transport = ready.recv_timeout(Duration::from_secs(2)).unwrap().unwrap();
        worker.join().unwrap();
        let receiver = transport.incoming.lock().unwrap();
        let Incoming::Input(input) = receiver.recv_timeout(Duration::from_secs(2)).unwrap() else {
            panic!("private socket must preserve the input frame");
        };
        assert_eq!((input.sequence, input.action), (1, Action::Status));
        let bytes = response(Some(1), "observed", None, json!({}));
        transport.outgoing.try_send(bytes.clone()).unwrap();
        let mut read = BufReader::new(peer.try_clone().unwrap());
        let mut decoded = Vec::new();
        read.read_until(b'\n', &mut decoded).unwrap();
        assert_eq!(decoded, bytes);
        peer.shutdown(Shutdown::Write).unwrap();
        assert!(matches!(
            receiver.recv_timeout(Duration::from_secs(2)).unwrap(),
            Incoming::Closed
        ));
        drop(receiver);
        fs::set_permissions(&fixture.0, Permissions::from_mode(0o755)).unwrap();
        assert!(
            Transport::connect(&path, "00000000-0000-0000-0000-000000000001").is_err(),
            "a public directory cannot become a control channel"
        );
        drop(transport);
        let mut trailing = [0; 1];
        assert_eq!(read.read(&mut trailing).unwrap(), 0);
    }

    fn pending(session: &ObserverSession, client: &OrganizerClient, action: Action) -> Pending {
        Pending {
            input: Input {
                version: 2,
                sequence: 1,
                campaign_id: session.campaign.as_uuid().to_string(),
                scope_epoch: session.runtime_scope().map(|s| s.epoch),
                expected_tick: session.durable_tick,
                expected_generation: session.generation,
                action,
            },
            context: session.context(),
            scope: session.runtime_scope().cloned(),
            reviewed: client.reviewed_command.clone(),
            request: None,
            choice: client.choice(),
            handled: false,
            foundation: session.foundation_digest.clone(),
            content_hash: session.content_hash.clone(),
        }
    }

    fn opening_handlers(app: &mut App) {
        app.add_systems(
            Update,
            crate::observer_warning::apply_continue
                .after(ObserverSet::Install)
                .before(ObserverSet::Paint),
        )
        .add_systems(
            Update,
            crate::observer_opening::advance
                .after(ObserverSet::Install)
                .after(crate::observer_warning::apply_continue)
                .before(ObserverSet::Paint),
        );
    }

    #[test]
    fn qualification_opening_controls_wait_for_real_handlers_before_long_frame_progress() {
        // Either plugin order must acknowledge the ordinary handler's exact
        // result, including when the same frame advances Production to Title.
        for adapter_first in [false, true] {
            let (mut app, requests, _responses) = crate::observer_io::tests::quit_app();
            let (client, mut session) = super::super::tests::ready();
            session.foundation_digest = Some("admitted".into());
            app.add_plugins(MinimalPlugins)
                .insert_resource(session)
                .insert_resource(client)
                .insert_resource(ObserverUiState::default())
                .init_resource::<OpeningPresentation>()
                .init_resource::<PrimaryView>()
                .add_message::<OrganizerAction>()
                .add_message::<ContinueWarning>()
                .add_message::<ProductionSkip>()
                .add_observer(crate::observer_title::continue_requested)
                .configure_sets(
                    Update,
                    (
                        ObserverSet::Input,
                        ObserverSet::Receive,
                        ObserverSet::Install,
                        ObserverSet::Paint,
                    )
                        .chain(),
                );
            app.world_mut()
                .resource_mut::<Time<Virtual>>()
                .set_max_delta(Duration::from_secs(60));
            app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs(60)));
            let (socket, _peer) = UnixStream::pair().unwrap();
            let (incoming, receiver) = mpsc::channel();
            let (outgoing, output) = mpsc::sync_channel(1);
            let transport = Transport {
                incoming: Mutex::new(receiver),
                outgoing,
                socket,
            };
            if adapter_first {
                install(&mut app, transport);
                opening_handlers(&mut app);
            } else {
                opening_handlers(&mut app);
                install(&mut app, transport);
            }
            app.update();
            let input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                Action::ContinueWarning,
            )
            .input;
            incoming.send(Incoming::Input(input)).unwrap();
            app.update();
            let reply: Value =
                serde_json::from_slice(app.world().resource::<Controls>().reply.as_ref().unwrap())
                    .unwrap();
            assert_eq!(
                reply["event"], "applied",
                "adapter_first={adapter_first}: {reply}"
            );
            assert_eq!(reply["state"]["opening_stage"], "Production");
            assert_eq!(
                app.world().resource::<OpeningPresentation>().stage,
                OpeningStage::Title,
                "the real presentation may progress after the handler is acknowledged"
            );
            app.update();
            output.try_recv().unwrap();
            let mut input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                Action::ContinueTitle,
            )
            .input;
            input.sequence = 2;
            incoming.send(Incoming::Input(input)).unwrap();
            app.update();
            let reply: Value =
                serde_json::from_slice(app.world().resource::<Controls>().reply.as_ref().unwrap())
                    .unwrap();
            assert_eq!(
                reply["event"], "applied",
                "adapter_first={adapter_first}: {reply}"
            );
            assert_eq!(reply["state"]["menu_open"], false);
            assert_eq!(
                app.world().resource::<OpeningPresentation>().stage,
                OpeningStage::Game
            );
            assert!(
                requests.try_recv().is_err(),
                "opening controls must not advance the economy"
            );
        }
    }

    #[test]
    fn qualification_fast_preview_retains_its_exact_handler_witness() {
        let (mut client, mut session) = super::super::tests::ready();
        let mut pending = pending(&session, &client, Action::Review);
        let mut messages = Messages::<OrganizerAction>::default();
        let id = messages.write(OrganizerAction::Review);
        let mut receipt = HandlerReceipt {
            tracked: Some(Tracked::Organizer(id.id, Action::Review)),
            ..default()
        };
        let command = client.make_command(&session, client.choice()).unwrap();
        client.queue(&mut session, RequestKind::Preview, Some(command.clone()));
        receipt.organizer_finished(id, true, &client);
        let request_id = client.pending.as_ref().unwrap().id;
        client
            .previewed(
                request_id,
                babylon_persistence::runtime_session::OrganizerPreview {
                    choice: command.choice,
                    current_period: command.expected_period,
                    resolves_period: command.expected_period + 1,
                    available_hours: 16,
                    required_hours: 0,
                    replaces_standing_work: false,
                    refusal: None,
                    observations: Vec::new(),
                },
                &mut session,
            )
            .unwrap();
        assert!(client.pending.is_none());
        capture_handler(&mut pending, receipt.handled.take().unwrap().unwrap()).unwrap();
        assert_eq!(pending.request, Some(request_id));
        assert_eq!(pending.reviewed, client.reviewed_command);
        assert_eq!(pending.reviewed.as_ref(), Some(&command));
    }

    #[test]
    fn qualification_review_refuses_a_competing_choice() {
        let (mut client, mut session) = super::super::tests::ready();
        let mut pending = pending(&session, &client, Action::Review);
        client.draft.as_mut().unwrap().choice = OrganizerChoice::Reinforce;
        let command = client.make_command(&session, client.choice()).unwrap();
        client.queue(&mut session, RequestKind::Preview, Some(command.clone()));
        let request = client.pending.as_ref().unwrap();
        assert_eq!(
            capture_handler(
                &mut pending,
                Witness::Organizer {
                    id: request.id,
                    kind: request.kind,
                    command: Some(command)
                }
            ),
            Err("control_request_changed")
        );
        assert!(!pending.handled);
    }

    #[test]
    fn qualification_step_cannot_credit_a_manual_step_in_the_same_batch() {
        let (mut app, requests, _replies) = crate::observer_io::tests::quit_app();
        app.init_resource::<HandlerReceipt>();
        let id = {
            let mut messages = app.world_mut().resource_mut::<Messages<ObserverCommand>>();
            messages.write(ObserverCommand::Step);
            messages.write(ObserverCommand::Step)
        };
        app.world_mut().resource_mut::<HandlerReceipt>().tracked =
            Some(Tracked::Observer(id.id, Action::Step));
        app.update();
        assert!(matches!(
            requests.try_recv().unwrap(),
            babylon_persistence::runtime_session::RuntimeSessionRequest::Advance { .. }
        ));
        assert!(
            requests.try_recv().is_err(),
            "the second input must never submit a second advance"
        );
        assert!(matches!(
            app.world_mut()
                .resource_mut::<HandlerReceipt>()
                .handled
                .take(),
            Some(Err("ordinary_handler_refused"))
        ));
    }

    #[test]
    fn qualification_confirmation_waits_for_the_actual_pending_status_after_acceptance() {
        #[derive(Resource)]
        struct InputWitness(Pending);
        #[derive(Resource, Default)]
        struct Verdict(Option<Result<&'static str, &'static str>>);
        fn inspect(situation: Situation, input: Res<InputWitness>, mut verdict: ResMut<Verdict>) {
            verdict.0 = outcome(&input.0, &situation);
        }
        let (mut client, mut session) = super::super::tests::ready();
        session.duration = Some(CampaignDuration::Continuous);
        let command = client.make_command(&session, client.choice()).unwrap();
        client.reviewed_command = Some(command.clone());
        let mut original = pending(&session, &client, Action::Confirm);
        client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
        let id = client.pending.as_ref().unwrap().id;
        capture_handler(
            &mut original,
            Witness::Organizer {
                id,
                kind: RequestKind::Submit,
                command: Some(command.clone()),
            },
        )
        .unwrap();
        client
            .accepted(
                id,
                babylon_persistence::runtime_session::OrganizerCommitment {
                    command,
                    resolves_period: 4,
                    commitment_id: [23; 32],
                },
                &mut session,
            )
            .unwrap();
        client.require_status(&mut session);
        assert!(session.begin_advance().is_none());
        client.queue(&mut session, RequestKind::Status, None);
        let status_id = client.pending.as_ref().unwrap().id;
        let fresh = babylon_persistence::runtime_session::OrganizerSnapshot {
            view: client.view.clone().unwrap(),
            pending: client.commitment.clone(),
            duration: session.duration.unwrap(),
            aid: client.aid.clone(),
            pending_aid: client.pending_aid.clone(),
            aid_resolutions: client.aid_resolutions.clone(),
            collection: client.collection.clone(),
            collection_resolutions: client.collection_resolutions.clone(),
        };
        let mut app = App::new();
        app.insert_resource(session)
            .insert_resource(client)
            .insert_resource(InputWitness(original))
            .init_resource::<ObserverUiState>()
            .init_resource::<OpeningPresentation>()
            .init_resource::<PrimaryView>()
            .init_resource::<Verdict>()
            .add_systems(Update, inspect);
        app.update();
        assert_eq!(app.world().resource::<Verdict>().0, None);
        app.world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                client
                    .status(
                        status_id,
                        fresh,
                        &mut world.resource_mut::<ObserverSession>(),
                    )
                    .unwrap();
            });
        app.update();
        assert_eq!(
            app.world().resource::<Verdict>().0,
            Some(Ok("acceptance_admitted"))
        );
        assert_eq!(app.world().resource::<ObserverSession>().durable_tick, 3);
    }

    fn frame(extra: &str) -> Vec<u8> {
        format!("{{\"version\":2,\"sequence\":1,\"campaign_id\":\"00000000-0000-0000-0000-000000000342\",\"scope_epoch\":null,\"expected_tick\":0,\"expected_generation\":0,\"action\":\"status\"{extra}}}\n").into_bytes()
    }

    #[test]
    fn capture_startup_refuses_wrong_identity_old_frames_and_corruption() {
        let campaign = "00000000-0000-0000-0000-000000000001";
        let valid = format!(
            "{{\"version\":2,\"campaign_id\":\"{campaign}\",\"phase\":\"capture_ready\"}}\n"
        );
        for bytes in [
            valid.replace("\"version\":2", "\"version\":1").into_bytes(),
            valid
                .replace(campaign, "00000000-0000-0000-0000-000000000002")
                .into_bytes(),
            valid.replace("capture_ready", "unknown").into_bytes(),
            valid
                .replace("\"phase\":", "\"unused\":true,\"phase\":")
                .into_bytes(),
            valid
                .replace("\"phase\":", "\"version\":2,\"phase\":")
                .into_bytes(),
            frame(""),
            valid.trim_end().as_bytes().to_vec(),
            vec![b'x'; usize::try_from(INPUT_BYTES + 1).unwrap()],
        ] {
            let (socket, mut peer) = UnixStream::pair().unwrap();
            let worker = thread::spawn(move || Transport::from_stream(socket, campaign));
            peer.write_all(&bytes).unwrap();
            peer.shutdown(Shutdown::Write).unwrap();
            let refusal = worker
                .join()
                .unwrap()
                .err()
                .expect("invalid startup must refuse");
            assert!(refusal.contains("capture_startup"));
        }
    }

    #[test]
    fn qualification_frames_reject_ambiguous_or_unbounded_input() {
        for bytes in [
            String::from_utf8(frame(""))
                .unwrap()
                .replace("\"version\":2", "\"version\":1")
                .into_bytes(),
            frame(",\"sequence\":2"),
            frame(",\"unused\":true"),
            String::from_utf8(frame(""))
                .unwrap()
                .replace("\"scope_epoch\":null,", "")
                .into_bytes(),
            frame("").into_iter().take_while(|b| *b != b'\n').collect(),
            vec![b'x'; usize::try_from(INPUT_BYTES + 2).unwrap()],
        ] {
            assert!(read_input(&mut Cursor::new(bytes)).is_err());
        }
        let mut input = Cursor::new(frame(""));
        assert_eq!(
            read_input(&mut input).unwrap().unwrap().action,
            Action::Status
        );
        assert!(read_input(&mut input).unwrap().is_none());
    }

    #[test]
    fn qualification_preconditions_bind_campaign_scope_age_and_generation() {
        let session = ObserverSession::new(CampaignId::from_uuid(Uuid::from_u128(0x342)));
        let mut input = read_input(&mut Cursor::new(frame(""))).unwrap().unwrap();
        assert!(precondition(&input, &session));
        input.expected_tick = 1;
        assert!(!precondition(&input, &session));
        input.expected_tick = 0;
        input.expected_generation = 1;
        assert!(!precondition(&input, &session));
        input.expected_generation = 0;
        input.scope_epoch = Some(1);
        assert!(!precondition(&input, &session));
        input.scope_epoch = None;
        input.campaign_id = Uuid::from_u128(0x343).to_string();
        assert!(!precondition(&input, &session));
    }
}
