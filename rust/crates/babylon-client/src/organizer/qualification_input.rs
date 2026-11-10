//! Opt-in bounded inputs to the real windowed controls. This adapter owns no
//! runtime requests, material effects, authoritative time, or qualification result.

#[cfg(test)]
use babylon_persistence::runtime_session::OrganizerBodyDisclosure;
use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::Shutdown;
use std::os::unix::fs::{FileTypeExt, MetadataExt};
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use std::sync::{mpsc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use bevy::ecs::message::{MessageCursor, MessageId, Messages};
use bevy::input::keyboard::KeyboardInput;
use bevy::prelude::*;
use bevy::render::view::screenshot::{Screenshot, ScreenshotCaptured};
use bevy::window::{MonitorSelection, PrimaryWindow, WindowMode, WindowResized};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

use super::amount_editor::AmountField;
use super::scene::{OrganizerSceneMode, OrganizerSubject};
use super::workspace::DispatchDestination;
use super::workspace_copy::{DatedLink, Destination};
use super::{ui, workspace, OrganizerClient, OrganizerInspector, RequestKind};
use crate::atlas::CountyAtlas;
use crate::map::SelectedCounty;
use crate::observer::{ObservationContext, ObserverSession, SessionPhase};
use crate::observer_controls::ControlAvailability;
use crate::observer_io::qualification::NativeAudit;
use crate::observer_io::{ObserverSet, RuntimePipe};
use crate::observer_opening::MenuPage;
use crate::observer_opening::{OpeningPresentation, OpeningStage};
use crate::observer_ui::{
    NetworkSector, ObserverCommand, ObserverFrame, ObserverUiState, RoadLayer,
};
use crate::observer_warning::ContinueWarning;
use crate::production::{
    PrimaryView, ProductionCommand, ProductionNavigation, ProductionReadingSection,
};
use crate::ui::dossier_card::{
    ArchiveEvidenceApplied, ArchiveEvidenceReceipt, OpenArchiveEvidence,
};
use babylon_persistence::runtime_session::{OrganizerAidKind, OrganizerFoodDelivery};
use babylon_persistence::runtime_session::{
    OrganizerChoice, OrganizerCommand, OrganizerInquiry, RuntimeSessionScope,
};
use mpsc::Receiver;
#[cfg(test)]
use mpsc::Sender;
use mpsc::SyncSender;
use mpsc::TryRecvError;
use thread::Builder;
use ui::OrganizerAction;
use uuid::Uuid;

// Designed bounds for instrumentation, independent of the captured game policy.
const INPUT_BYTES: u64 = 4096;
const OUTPUT_BYTES: usize = 32_768;
const INSTALLED_ROSTER_LIMIT: usize = 32;
const PRESENTATION_TIMEOUT: Duration = Duration::from_secs(3);

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
    if admission.version != 5 || admission.campaign_id != campaign {
        return Err("capture_startup_identity_invalid");
    }
    let StartupPhase::CaptureReady = admission.phase;
    Ok(())
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
enum Action {
    ChooseCollect,
    FocusAmount(AmountField),
    AmountKey(AmountKey),
    SelectAidPartner(OrganizerAidKind),
    InspectSubjectEvidence,
    DraftFromReport,
    ArchiveReport,
    Status,
    AwaitPeriodProof,
    ArmOnePlayAdvance,
    Play,
    Pause,
    Speed,
    World,
    ObserverCampaigns,
    Circuit,
    Flow,
    EconomyNetwork,
    ManufacturingSector,
    AllSectors,
    SelectFirstCountyCohort,
    StandardInterface,
    LargerInterface,
    ReadInquiryReport,
    ContinueWarning,
    ContinueTitle,
    OpenOrganizer,
    OpenDirection,
    InspectPractices,
    InspectReceipts,
    OpenRelationships,
    ScenePlaces,
    SceneRelationships,
    SelectWorkplaceCommittee,
    SelectNeighborhoodGroup,
    InspectEvidence,
    NextEvidence,
    PreviousEvidence,
    ArchiveWorkplace,
    ArchiveOrganization,
    OpenArchiveEvidence,
    PreviousPeriod,
    ReturnLive,
    CaptureFrame,
    Resize1366x768,
    Resize1920x1080,
    CloseInspector,
    ChooseRemoteAid,
    ChooseLocalAid,
    ChooseInquiryWorkLost,
    ChooseInquiryMaintenanceReceived,
    ChooseReinforce,
    ChooseHold,
    ChoosePauseStanding,
    ChooseResumeStanding,
    Review,
    Confirm,
    Step,
    Reopen,
    Refresh,
    Quit,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
enum AmountKey {
    Character(char),
    Backspace,
    Delete,
    Home,
    End,
}
impl AmountKey {
    fn pressed(self, window: Entity) -> KeyboardInput {
        use bevy::input::keyboard::{Key, NativeKeyCode};
        use bevy::input::ButtonState;
        let (key_code, logical_key, text) = match self {
            Self::Character(c) => {
                let raw = c.to_string();
                let key = match c {
                    '0' => KeyCode::Digit0,
                    '1' => KeyCode::Digit1,
                    '2' => KeyCode::Digit2,
                    '3' => KeyCode::Digit3,
                    '4' => KeyCode::Digit4,
                    '5' => KeyCode::Digit5,
                    '6' => KeyCode::Digit6,
                    '7' => KeyCode::Digit7,
                    '8' => KeyCode::Digit8,
                    '9' => KeyCode::Digit9,
                    '-' => KeyCode::Minus,
                    _ => KeyCode::Unidentified(NativeKeyCode::Unidentified),
                };
                (key, Key::Character(raw.clone().into()), Some(raw.into()))
            }
            Self::Backspace => (KeyCode::Backspace, Key::Backspace, None),
            Self::Delete => (KeyCode::Delete, Key::Delete, None),
            Self::Home => (KeyCode::Home, Key::Home, None),
            Self::End => (KeyCode::End, Key::End, None),
        };
        KeyboardInput {
            key_code,
            logical_key,
            state: ButtonState::Pressed,
            text,
            repeat: false,
            window,
        }
    }
}

impl Action {
    fn extent(self) -> Option<UVec2> {
        match self {
            Self::Resize1366x768 => Some(UVec2::new(1366, 768)),
            Self::Resize1920x1080 => Some(UVec2::new(1920, 1080)),
            _ => None,
        }
    }

    fn organizer(
        self,
        client: &OrganizerClient,
        session: &ObserverSession,
    ) -> Option<OrganizerAction> {
        use ui::OrganizerAction as O;
        Some(match self {
            Self::ReadInquiryReport => {
                let dispatch = workspace::dispatch(client, session.viewed_tick)?;
                let report = dispatch
                    .current
                    .reports
                    .iter()
                    .find(|row| row.observation.receipt_id.is_some())?;
                O::Follow(DatedLink::new(
                    session,
                    session.viewed_tick,
                    Destination::Detail(report.destination),
                ))
            }
            Self::ChooseCollect => O::Choose(OrganizerChoice::Collect),
            Self::FocusAmount(field) => O::FocusAmount(field),
            Self::SelectAidPartner(kind) => O::SelectSubject(OrganizerSubject::AidPartner(
                client
                    .view
                    .as_ref()?
                    .aid_partners
                    .iter()
                    .find(|p| p.kind == kind)?
                    .actor_id,
            )),
            Self::InspectSubjectEvidence => O::InspectSubjectEvidence,
            Self::DraftFromReport => O::DraftFromReport,
            Self::ArchiveReport => O::ArchiveReport,
            Self::OpenOrganizer => O::Open,
            Self::InspectPractices => O::Inspect(OrganizerInspector::Practices),
            Self::OpenDirection => O::Inspect(OrganizerInspector::Direction),
            Self::InspectReceipts => O::Inspect(OrganizerInspector::Receipts),
            Self::OpenRelationships => O::Inspect(OrganizerInspector::Relationships),
            Self::ScenePlaces => O::SetSceneMode(OrganizerSceneMode::Places),
            Self::SceneRelationships => O::SetSceneMode(OrganizerSceneMode::Relationships),
            Self::SelectWorkplaceCommittee => O::SelectSubject(
                OrganizerSubject::WorkplaceCommittee(client.view.as_ref()?.workplace_partner_id),
            ),
            Self::SelectNeighborhoodGroup => O::SelectSubject(OrganizerSubject::NeighborhoodGroup(
                client.view.as_ref()?.neighborhood_partner_id,
            )),
            Self::InspectEvidence => O::Inspect(OrganizerInspector::Evidence),
            Self::NextEvidence => O::NextEvidence,
            Self::PreviousEvidence => O::PreviousEvidence,
            Self::ArchiveWorkplace => O::ArchiveWorkplace,
            Self::ArchiveOrganization => O::ArchiveOrganization,
            Self::CloseInspector => O::CloseInspector,
            Self::ChooseRemoteAid => O::Choose(OrganizerChoice::RemoteAid),
            Self::ChooseLocalAid => O::Choose(OrganizerChoice::LocalAid),
            Self::ChooseInquiryWorkLost => {
                O::Choose(OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost))
            }
            Self::ChooseInquiryMaintenanceReceived => O::Choose(OrganizerChoice::Inquiry(
                OrganizerInquiry::MaintenanceReceived,
            )),
            Self::ChooseReinforce => O::Choose(OrganizerChoice::Reinforce),
            Self::ChooseHold => O::Choose(OrganizerChoice::Hold),
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
    if input.version != 5 || input.sequence == 0 {
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
    capture_dir: Option<PathBuf>,
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
        let mut transport = Self::from_stream(socket, campaign)?;
        transport.capture_dir = Some(parent.to_path_buf());
        Ok(transport)
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
            capture_dir: None,
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
    world_hash: Option<String>,
    capture_state: Option<Value>,
    expected_evidence: Option<[u8; 32]>,
    amount_target: Option<(Entity, AmountField)>,
    amount_handled: Option<bool>,
    resize_armed: bool,
    presentation_started: Instant,
}

impl Pending {
    fn new(input: Input, situation: &Situation, tracked: Option<Tracked>) -> Self {
        Self {
            amount_target: situation.amount_target(),
            amount_handled: None,
            resize_armed: false,
            presentation_started: Instant::now(),
            expected_evidence: match input.action {
                Action::NextEvidence => situation
                    .client
                    .evidence_neighbor(true, situation.session.viewed_tick),
                Action::PreviousEvidence => situation
                    .client
                    .evidence_neighbor(false, situation.session.viewed_tick),
                _ => None,
            },
            capture_state: (input.action == Action::CaptureFrame)
                .then(|| situation.capture_state()),
            input,
            context: situation.session.context(),
            scope: situation.session.runtime_scope().cloned(),
            reviewed: situation.client.reviewed_command.clone(),
            request: None,
            choice: situation.client.choice(),
            handled: tracked.is_none(),
            foundation: situation.session.foundation_digest.clone(),
            content_hash: situation.session.content_hash.clone(),
            world_hash: situation.session.world_hash.clone(),
        }
    }
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

#[derive(Serialize)]
#[serde(rename_all = "snake_case")]
enum PlayPhase {
    Armed,
    PausedAfterEnqueue,
}

#[derive(Serialize)]
struct PlayWitness {
    phase: PlayPhase,
    arm_sequence: u64,
    play_sequence: Option<u64>,
    campaign_id: String,
    scope_epoch: u64,
    start_tick: u64,
    start_generation: u64,
    target_tick: u64,
    request_id: Option<u64>,
    pending_at_pause: bool,
    playing_after_pause: Option<bool>,
}

impl PlayWitness {
    fn matches(&self, session: &ObserverSession) -> bool {
        session.campaign.as_uuid().to_string() == self.campaign_id
            && session.runtime_scope().is_some_and(|s| {
                s.epoch == self.scope_epoch
                    && s.campaign_id.as_deref() == Some(self.campaign_id.as_str())
            })
            && session.viewed_tick == self.start_tick
            && session.durable_tick == self.start_tick
            && session.generation == self.start_generation
    }
}

/// Only the qualification socket installs this single-use request witness.
#[derive(Resource, Default)]
pub(crate) struct PlayInterlock {
    witness: Option<PlayWitness>,
    // Private Play's ordinary Bevy message and exact wire sequence.
    play: Option<(usize, u64)>,
    admitted: bool,
    invalid: bool,
}

impl PlayInterlock {
    fn arm(&mut self, input: &Input, session: &ObserverSession) -> bool {
        let (Some(scope), Some(next)) =
            (session.runtime_scope(), session.durable_tick.checked_add(1))
        else {
            return false;
        };
        if scope.campaign_id.as_deref() != Some(input.campaign_id.as_str())
            || self.witness.is_some()
            || !Self::can_start(session)
        {
            return false;
        }
        self.witness = Some(PlayWitness {
            phase: PlayPhase::Armed,
            arm_sequence: input.sequence,
            play_sequence: None,
            campaign_id: session.campaign.as_uuid().to_string(),
            scope_epoch: scope.epoch,
            start_tick: session.durable_tick,
            start_generation: session.generation,
            target_tick: next,
            request_id: None,
            pending_at_pause: false,
            playing_after_pause: None,
        });
        true
    }

    fn can_start(session: &ObserverSession) -> bool {
        session.phase == SessionPhase::Ready
            && !session.playing
            && !session.advance_pending()
            && !session.lifecycle_pending()
            && !session.organizer_control_pending()
            && session.viewed_tick == session.durable_tick
            && !session.quit_requested
            && session
                .duration
                .is_none_or(|d| d.can_advance(session.durable_tick))
    }

    /// Check the privately tracked message before the ordinary handler can start playback.
    pub(crate) fn allows_toggle(
        &mut self,
        id: usize,
        session: &ObserverSession,
        audit: Option<&NativeAudit>,
    ) -> bool {
        if !self.armed() || self.play.is_none_or(|(message, _)| message != id) {
            return true;
        }
        self.invalid |= !Self::can_start(session)
            || audit.is_some_and(|a| !a.can_arm_play(session))
            || !self.witness.as_ref().is_some_and(|w| w.matches(session));
        !self.invalid
    }

    fn visible(&self, session: &ObserverSession) -> Option<&PlayWitness> {
        self.witness.as_ref().filter(|w| {
            !matches!(w.phase, PlayPhase::Armed) || (!self.invalid && w.matches(session))
        })
    }

    fn armed(&self) -> bool {
        self.witness
            .as_ref()
            .is_some_and(|w| matches!(w.phase, PlayPhase::Armed))
    }

    pub(crate) fn toggle_handled(&mut self, id: usize, session: &ObserverSession) {
        if self.armed() {
            self.admitted = !self.invalid
                && self.play.is_some_and(|(message, _)| message == id)
                && session.playing
                && self.witness.as_ref().is_some_and(|w| w.matches(session));
            self.invalid |= !self.admitted;
        }
    }

    pub(crate) fn allows_enqueue(&self, session: &ObserverSession) -> bool {
        !self.admitted
            || !self.armed()
            || (!self.invalid && self.witness.as_ref().is_some_and(|w| w.matches(session)))
    }

    pub(crate) fn enqueued(&mut self, session: &mut ObserverSession, request: u64) -> bool {
        if !self.armed() || !self.admitted {
            return false;
        }
        session.pause_playback();
        let (Some(witness), Some((_, sequence))) = (&mut self.witness, self.play) else {
            self.invalid = true;
            return false;
        };
        if self.invalid || session.pending_advance_request() != Some(request) {
            self.invalid = true;
            return false;
        }
        witness.phase = PlayPhase::PausedAfterEnqueue;
        witness.play_sequence = Some(sequence);
        witness.request_id = Some(request);
        witness.pending_at_pause = session.pending_advance_request() == Some(request);
        witness.playing_after_pause = Some(session.playing);
        true
    }
}

fn installed_organizer(client: &OrganizerClient, session: &ObserverSession) -> Option<Value> {
    let view = client.view.as_ref()?;
    workspace::resources(client, session)?;
    if client.status_due || client.status_refusal(session).is_some() || !session.organizer_enabled {
        return None;
    }
    let pending_freight: Vec<_> = client
        .pending_aid
        .iter()
        .filter(|r| r.dispatch_support.status == OrganizerFoodDelivery::AwaitingDelivery)
        .map(|r| {
            json!({
                "original_commitment_id": r.original_commitment_id,
                "material_commitment_id": r.material_commitment_id,
                "mandate_id": r.mandate_id,
                "dispatch_period": r.dispatch_period,
                "first_response_receipt_id": r.response.as_ref().map(|p| p.receipt_id)
            })
        })
        .collect();
    let aid_response_history: Vec<_> = client
        .aid_resolutions
        .iter()
        .map(|r| {
            json!({
                "original_commitment_id": r.pending.original_commitment_id,
                "period": r.practice.period,
                "practice_receipt_id": r.practice.receipt_id,
                "first_response_receipt_id": r.pending.response.as_ref().map(|p| p.receipt_id)
            })
        })
        .collect();
    Some(json!({
        "period": view.period,
        "actor_id": view.actor_id,
        "authority_id": view.authority_id,
        "content_digest": view.content_digest,
        "resource_digest": view.resource_digest,
        "standing": view.standing,
        "available_hours": view.available_hours,
        "contact_hours": view.contact_hours,
        "hold_reviewable": workspace::reviewable(client, session, OrganizerChoice::Hold),
        "pause_reviewable": workspace::reviewable(client, session, OrganizerChoice::PauseStanding),
        "resume_reviewable": workspace::reviewable(client, session, OrganizerChoice::ResumeStanding),
        "pending_freight": pending_freight,
        "aid_response_history": aid_response_history
    }))
}

#[derive(Resource)]
struct Controls {
    next_sequence: Option<u64>,
    pending: Option<Pending>,
    reply: Option<Vec<u8>>,
    proof_reply: Option<u64>,
    disabled: bool,
    capture_result: Option<Result<(), &'static str>>,
    observed_extent: Option<(Entity, UVec2)>,
    resize_cursor: MessageCursor<WindowResized>,
}

impl Default for Controls {
    fn default() -> Self {
        Self {
            next_sequence: Some(1),
            pending: None,
            reply: None,
            proof_reply: None,
            disabled: false,
            capture_result: None,
            observed_extent: None,
            resize_cursor: MessageCursor::default(),
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
        "inspector":format!("{:?}",client.inspector),
        "playing":session.playing,"periods_per_second":session.periods_per_second,
        "perspective":format!("{:?}",session.perspective),"world_hash":session.world_hash,
        "selected_report_id":client.selected_evidence_id(session.viewed_tick).map(crate::dossier::hex_bytes),
        "selected_report_observed_period":client.selected_evidence_id(session.viewed_tick).and_then(|id| client.lawful_evidence(id, session.viewed_tick)).map(|report| report.observed_period),
        "selected_report_acquired_period":client.selected_evidence_id(session.viewed_tick).and_then(|id| client.lawful_evidence(id, session.viewed_tick)).map(|report| report.acquired_period),
        "selected_subject":client.selected_subject.map(|subject| format!("{subject:?}")),
        "larger_interface":ui.larger_interface,"road_layer":format!("{:?}",ui.road_layer),
        "network_sector":format!("{:?}",ui.network_sector),"menu_page":format!("{:?}",opening.menu_page)})
}

fn response(sequence: Option<u64>, event: &str, reason: Option<&str>, state: Value) -> Vec<u8> {
    bounded_response(sequence, event, reason, &state).unwrap_or_else(|_| {
        let mut bytes = br#"{"version":5,"sequence":null,"event":"refused","reason":"control_response_not_bounded"}"#.to_vec();
        bytes.push(b'\n');
        bytes
    })
}

fn bounded_response(
    sequence: Option<u64>,
    event: &str,
    reason: Option<&str>,
    state: &Value,
) -> Result<Vec<u8>, &'static str> {
    let mut bytes = serde_json::to_vec(
        &json!({"version":5,"sequence":sequence,"event":event,"reason":reason,"state":state}),
    )
    .map_err(|_| "control_response_encoding_failed")?;
    if state.is_null() || bytes.len() >= OUTPUT_BYTES {
        return Err("control_response_not_bounded");
    }
    bytes.push(b'\n');
    Ok(bytes)
}

fn precondition(input: &Input, session: &ObserverSession) -> bool {
    input.campaign_id == session.campaign.as_uuid().to_string()
        && input.scope_epoch == session.runtime_scope().map(|scope| scope.epoch)
        && if input.action == Action::Pause {
            input.expected_tick <= session.durable_tick
                && input.expected_generation <= session.generation
        } else {
            input.expected_tick == session.durable_tick
                && input.expected_generation == session.generation
        }
}

fn period_proof_available(
    session: &ObserverSession,
    client: &OrganizerClient,
    ui: &ObserverUiState,
    opening: &OpeningPresentation,
    view: PrimaryView,
) -> bool {
    matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
        && session.perspective == crate::observer::Perspective::PlayerKnowledge
        && !session.playing
        && !session.advance_pending()
        && !session.lifecycle_pending()
        && !session.organizer_control_pending()
        && !session.quit_requested
        && session.viewed_tick == session.durable_tick
        && session.durable_tick > 0
        && !ui.splash_visible
        && !ui.menu_open
        && opening.stage == OpeningStage::Game
        && view == PrimaryView::Organizer
        && client.pending.is_none()
        && !client.status_due
        && client.status_refusal(session).is_none()
        && client.view.as_ref().map(|v| v.period) == Some(session.durable_tick)
        && installed_organizer(client, session).is_some()
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
    if let Some(result) = presentation_available(action, session, ui, pipe) {
        return result;
    }
    if matches!(
        action,
        Action::OpenRelationships
            | Action::ScenePlaces
            | Action::SceneRelationships
            | Action::SelectWorkplaceCommittee
            | Action::SelectNeighborhoodGroup
    ) && (session.phase != SessionPhase::Ready
        || session.playing
        || session.advance_pending()
        || session.lifecycle_pending()
        || session.organizer_control_pending()
        || session.quit_requested
        || session.viewed_tick != session.durable_tick
        || client.status_due
        || client.pending.is_some()
        || client
            .view
            .as_ref()
            .is_none_or(|view| view.period != session.durable_tick))
    {
        return false;
    }
    if let Some(action) = action.organizer(client, session) {
        return ui::visible(action, client, session, ui, view)
            && ui::enabled(action, client, session);
    }
    match action {
        Action::Status | Action::AmountKey(_) => true,
        Action::AwaitPeriodProof => period_proof_available(session, client, ui, opening, view),
        Action::ArmOnePlayAdvance => {
            pipe && !ui.splash_visible && !ui.menu_open && !ui.comparison_open
        }
        Action::OpenArchiveEvidence => {
            ui.archive_open
                && !ui.splash_visible
                && !ui.menu_open
                && !ui.comparison_open
                && matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
                && !session.playing
                && !session.advance_pending()
                && !session.lifecycle_pending()
                && !session.organizer_control_pending()
        }
        Action::CaptureFrame | Action::Resize1366x768 | Action::Resize1920x1080 => {
            matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
                && !session.playing
                && !session.advance_pending()
                && !session.lifecycle_pending()
        }
        Action::PreviousPeriod | Action::ReturnLive => {
            let command = if action == Action::PreviousPeriod {
                ObserverCommand::PreviousPeriod
            } else {
                ObserverCommand::Live
            };
            pipe && !ui.splash_visible
                && !ui.menu_open
                && !ui.comparison_open
                && crate::observer_controls::availability(command, session)
                    == ControlAvailability::Enabled
        }
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

fn presentation_available(
    action: Action,
    session: &ObserverSession,
    ui: &ObserverUiState,
    pipe: bool,
) -> Option<bool> {
    Some(match action {
        Action::Pause => {
            pipe && !session.quit_requested
                && !session.lifecycle_pending()
                && session.runtime_scope().is_some()
                && matches!(
                    session.phase,
                    SessionPhase::Ready
                        | SessionPhase::Loading
                        | SessionPhase::Advancing
                        | SessionPhase::Complete
                )
        }
        Action::Play
        | Action::Speed
        | Action::ObserverCampaigns
        | Action::EconomyNetwork
        | Action::ManufacturingSector
        | Action::AllSectors => {
            pipe && !ui.splash_visible
                && !ui.menu_open
                && !ui.comparison_open
                && crate::observer_controls::availability(observer_command(action), session)
                    == ControlAvailability::Enabled
        }
        Action::StandardInterface | Action::LargerInterface => {
            !ui.splash_visible
                && !ui.comparison_open
                && !session.playing
                && !session.advance_pending()
                && !session.lifecycle_pending()
                && matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
        }
        Action::World | Action::Circuit | Action::Flow | Action::SelectFirstCountyCohort => {
            !ui.splash_visible
                && !ui.menu_open
                && !ui.comparison_open
                && !session.playing
                && !session.advance_pending()
                && !session.lifecycle_pending()
                && matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
        }
        _ => return None,
    })
}

#[derive(bevy::ecs::system::SystemParam)]
struct Situation<'w, 's> {
    interlock: Option<ResMut<'w, PlayInterlock>>,
    audit: Option<ResMut<'w, NativeAudit>>,
    amount_fields: Query<'w, 's, &'static AmountField>,
    focus: Option<Res<'w, bevy::input_focus::InputFocus>>,
    session: Res<'w, ObserverSession>,
    client: Res<'w, OrganizerClient>,
    ui: Res<'w, ObserverUiState>,
    opening: Res<'w, OpeningPresentation>,
    view: Res<'w, PrimaryView>,
    pipe: Option<Res<'w, RuntimePipe>>,
    frame: Option<Res<'w, ObserverFrame>>,
    navigation: Option<Res<'w, ProductionNavigation>>,
    atlas: Option<Res<'w, CountyAtlas>>,
    selected: Option<Res<'w, SelectedCounty>>,
}

impl Situation<'_, '_> {
    fn amount_target(&self) -> Option<(Entity, AmountField)> {
        let entity = self.focus.as_ref()?.get()?;
        Some((entity, *self.amount_fields.get(entity).ok()?))
    }
    fn focused_amount(&self) -> Option<AmountField> {
        self.amount_target().map(|(_, field)| field)
    }
    fn allows(&self, input: &Input) -> bool {
        precondition(input, &self.session)
            && (!matches!(input.action, Action::AmountKey(_))
                || self.focused_amount().is_some_and(|field| {
                    ui::visible(
                        OrganizerAction::FocusAmount(field),
                        &self.client,
                        &self.session,
                        &self.ui,
                        *self.view,
                    ) && ui::enabled(
                        OrganizerAction::FocusAmount(field),
                        &self.client,
                        &self.session,
                    )
                }))
            && self.production_available(input.action)
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

    fn play_acknowledged(&self, pending: &Pending) -> bool {
        self.interlock
            .as_ref()
            .and_then(|i| i.witness.as_ref())
            .is_some_and(|w| {
                w.play_sequence == Some(pending.input.sequence)
                    && w.pending_at_pause
                    && w.playing_after_pause == Some(false)
                    && w.start_tick == pending.input.expected_tick
                    && w.start_generation == pending.input.expected_generation
            })
    }
    fn state(&self) -> Value {
        let mut result = state(
            &self.session,
            &self.client,
            &self.ui,
            &self.opening,
            *self.view,
        );
        if self.client.pending_aid.len() > INSTALLED_ROSTER_LIMIT
            || self.client.aid_resolutions.len() > INSTALLED_ROSTER_LIMIT
        {
            return Value::Null;
        }
        result["installed_organizer"] = json!(installed_organizer(&self.client, &self.session));
        result["advance_request_id"] = json!(self
            .audit
            .as_deref()
            .and_then(|a| a.advance_request_id(&self.session)));
        result["period_proof"] = json!(self
            .audit
            .as_deref()
            .and_then(|a| a.period_proof_receipt(&self.session)));
        result["play_interlock"] = json!(self
            .interlock
            .as_ref()
            .and_then(|i| i.visible(&self.session)));
        result["focused_amount"] = json!(self.focused_amount());
        result["amount_text"] = json!(self.focused_amount().map(|field| field.text(&self.client)));
        result["allocation_error"] = json!(super::amount_editor::allocation(&self.client).err());
        result["collection_allocation"] = json!(self
            .client
            .draft
            .as_ref()
            .map(|draft| draft.collection_allocation));
        result["aid_allocation"] =
            json!(self.client.draft.as_ref().map(|draft| draft.aid_allocation));
        result["selected_county"] = json!(self
            .selected
            .as_ref()
            .and_then(|selected| selected.0)
            .and_then(|index| self.atlas.as_ref()?.county(index))
            .map(|county| county.fips));
        result["selected_site"] = json!(self
            .navigation
            .as_ref()
            .and_then(|nav| nav.selected_site.as_ref()));
        result["production_details_open"] =
            json!(self.navigation.as_ref().is_some_and(|nav| nav.details_open));
        result["production_reading"] = json!(self
            .navigation
            .as_ref()
            .map(|nav| format!("{:?}", nav.reading_section)));
        result
    }

    fn production_available(&self, action: Action) -> bool {
        if !matches!(
            action,
            Action::World | Action::Circuit | Action::Flow | Action::SelectFirstCountyCohort
        ) {
            return true;
        }
        let Some(command) = self.production_command(action) else {
            return false;
        };
        if self.session.organizer_enabled && matches!(command, ProductionCommand::Open) {
            return true; // The ordinary handler routes this to earned Evidence.
        }
        let Some(navigation) = self.navigation.as_ref() else {
            return false;
        };
        let snapshot = self
            .frame
            .as_ref()
            .and_then(|frame| frame.for_session(&self.session))
            .and_then(|frame| frame.production.as_ref());
        crate::production::navigation::command_enabled(
            &command,
            snapshot,
            navigation,
            &self.session,
        )
    }

    fn production_command(&self, action: Action) -> Option<ProductionCommand> {
        Some(match action {
            Action::World => ProductionCommand::Map,
            Action::Circuit => ProductionCommand::Open,
            Action::Flow => ProductionCommand::Reading(ProductionReadingSection::Flow),
            Action::SelectFirstCountyCohort => {
                let county = self
                    .selected
                    .as_ref()?
                    .0
                    .and_then(|index| self.atlas.as_ref()?.county(index))?;
                let snapshot = self
                    .frame
                    .as_ref()?
                    .for_session(&self.session)?
                    .production
                    .as_ref()?;
                let site = snapshot
                    .sites
                    .iter()
                    .filter(|site| site.is_in_county(county.fips))
                    .min_by(|a, b| a.id.cmp(&b.id))?;
                ProductionCommand::Select {
                    site_id: site.id.clone(),
                    context: self.session.context(),
                }
            }
            _ => return None,
        })
    }

    // The caller labels these as admission/completion samples; pixels remain
    // the evidence for asynchronous Archive contents and other visual detail.
    fn capture_state(&self) -> Value {
        json!({
            "state": self.state(),
            "playing": self.session.playing,
            "archive_open": self.ui.archive_open,
            "history_open": self.ui.history_open,
            "comparison_open": self.ui.comparison_open,
            "organizer_view": self.client.view,
            "organizer_status_refusal": self.client.status_refusal(&self.session),
            "city_pd_encounters": self.client.city_pd_encounters,
            "scene_mode": format!("{:?}", self.client.scene_mode),
            "selected_subject": format!("{:?}", self.client.selected_subject),
        })
    }
}

impl Controls {
    fn stage_result(
        &mut self,
        sequence: u64,
        action: Action,
        result: Result<&'static str, &'static str>,
        situation: &mut Situation,
    ) {
        let proof = action == Action::AwaitPeriodProof;
        let (event, reason) = match result {
            Ok(event) => (event, None),
            Err(reason) => ("refused", Some(reason)),
        };
        let bytes = if proof && reason.is_none() {
            match bounded_response(Some(sequence), event, None, &situation.state()) {
                Ok(bytes) => {
                    self.proof_reply = Some(sequence);
                    bytes
                }
                Err(reason) => {
                    if let Some(audit) = situation.audit.as_deref_mut() {
                        audit.refuse_period_proof(reason);
                    }
                    response(Some(sequence), "refused", Some(reason), situation.state())
                }
            }
        } else {
            if proof {
                if let Some(audit) = situation.audit.as_deref_mut() {
                    audit.refuse_period_proof(reason.unwrap_or("period_proof_completion_failed"));
                }
            }
            response(Some(sequence), event, reason, situation.state())
        };
        self.reply = Some(bytes);
    }

    fn respond(
        &mut self,
        sequence: Option<u64>,
        event: &str,
        reason: Option<&str>,
        situation: &Situation,
    ) {
        self.proof_reply = None;
        self.reply = Some(response(sequence, event, reason, situation.state()));
    }
}

enum OutputReady {
    Ready,
    Backpressure,
    Closed,
}

fn flush_reply(
    transport: &Transport,
    controls: &mut Controls,
    situation: &mut Situation,
) -> OutputReady {
    if controls.proof_reply.is_some() && controls.reply.is_none() {
        if let Some(audit) = situation.audit.as_deref_mut() {
            audit.refuse_period_proof("period_proof_reply_absent");
        }
        controls.proof_reply = None;
        return OutputReady::Closed;
    }
    if let Some(sequence) = controls.proof_reply {
        let ready = situation
            .audit
            .as_deref()
            .ok_or("period_proof_capability_absent")
            .and_then(|audit| {
                audit.fence_reply_ready(
                    &situation.session,
                    sequence,
                    situation
                        .frame
                        .as_deref()
                        .and_then(|f| f.for_session(&situation.session)),
                )
            });
        if ready.is_ok() && proof_status_pending(situation) {
            return OutputReady::Backpressure;
        }
        let ready = ready.and_then(|()| {
            available(
                Action::AwaitPeriodProof,
                &situation.session,
                &situation.client,
                &situation.ui,
                &situation.opening,
                *situation.view,
                situation.pipe.is_some(),
            )
            .then_some(())
            .ok_or("period_proof_context_changed")
        });
        if let Err(reason) = ready {
            if let Some(audit) = situation.audit.as_deref_mut() {
                audit.refuse_period_proof(reason);
            }
            controls.respond(Some(sequence), "refused", Some(reason), situation);
        }
    }
    let Some(bytes) = controls.reply.take() else {
        return OutputReady::Ready;
    };
    match transport.outgoing.try_send(bytes) {
        Ok(()) => {
            if let Some(sequence) = controls.proof_reply.take() {
                situation
                    .audit
                    .as_deref_mut()
                    .expect("the exclusive flush validated this capability before try_send")
                    .fence_reply_queued(sequence);
            }
            OutputReady::Ready
        }
        Err(mpsc::TrySendError::Full(bytes)) => {
            controls.reply = Some(bytes);
            OutputReady::Backpressure
        }
        Err(mpsc::TrySendError::Disconnected(_)) => {
            if controls.proof_reply.take().is_some() {
                if let Some(audit) = situation.audit.as_deref_mut() {
                    audit.refuse_period_proof("period_proof_reply_closed");
                }
            }
            OutputReady::Closed
        }
    }
}

fn observer_command(action: Action) -> ObserverCommand {
    match action {
        Action::Play | Action::Pause => ObserverCommand::TogglePlay,
        Action::Speed => ObserverCommand::Speed,
        Action::ObserverCampaigns => ObserverCommand::ObserverCampaigns,
        Action::EconomyNetwork => ObserverCommand::RoadLayer(RoadLayer::EconomyNetwork),
        Action::ManufacturingSector => ObserverCommand::NetworkSector(NetworkSector::Manufacturing),
        Action::AllSectors => ObserverCommand::NetworkSector(NetworkSector::All),
        Action::StandardInterface | Action::LargerInterface => ObserverCommand::UiScale,
        Action::Step => ObserverCommand::Step,
        Action::Reopen => ObserverCommand::ReopenCampaign,
        Action::Quit => ObserverCommand::Quit,
        Action::PreviousPeriod => ObserverCommand::PreviousPeriod,
        Action::ReturnLive => ObserverCommand::Live,
        _ => unreachable!("selected observer input"),
    }
}

fn request_frame(
    transport: &Transport,
    controls: &mut Controls,
    commands: &mut Commands,
    sequence: u64,
) -> Result<(), &'static str> {
    let directory = transport
        .capture_dir
        .as_ref()
        .ok_or("capture_directory_absent")?;
    let path = directory.join(format!("frame-{sequence}.png"));
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)
        .map_err(|_| "capture_file_unavailable")?;
    controls.capture_result = None;
    commands.spawn(Screenshot::primary_window()).observe(
        move |captured: On<ScreenshotCaptured>, mut controls: ResMut<Controls>| {
            controls.capture_result = Some(
                captured
                    .image
                    .clone()
                    .try_into_dynamic()
                    .map_err(|_| "capture_image_invalid")
                    .and_then(|image| {
                        image
                            .to_rgb8()
                            .save(&path)
                            .map_err(|_| "capture_write_failed")
                    }),
            );
        },
    );
    Ok(())
}

fn request_resize(
    controls: &mut Controls,
    windows: &mut Query<(Entity, &mut Window), With<PrimaryWindow>>,
    action: Action,
) -> Result<(), &'static str> {
    let (entity, mut window) = windows
        .single_mut()
        .map_err(|_| "primary_window_unavailable")?;
    let extent = action.extent().expect("bounded resize action");
    let mode = match action {
        Action::Resize1366x768 => WindowMode::Windowed,
        Action::Resize1920x1080 => WindowMode::BorderlessFullscreen(MonitorSelection::Current),
        _ => unreachable!("bounded resize action"),
    };
    let previously_observed = controls.observed_extent == Some((entity, extent));
    if window.mode == mode && previously_observed && action == Action::Resize1920x1080 {
        return Ok(());
    }
    if window.mode == mode
        && !previously_observed
        && UVec2::new(window.physical_width(), window.physical_height()) == extent
    {
        return Err("primary_window_extent_unobserved");
    }
    controls.observed_extent = None;
    window.mode = mode;
    if action == Action::Resize1366x768 {
        window.set_maximized(false);
        window
            .resolution
            .set_physical_resolution(extent.x, extent.y);
    }
    Ok(())
}

fn admitted_input(
    transport: &Transport,
    controls: &mut Controls,
    situation: &mut Situation,
    observer: &mut MessageWriter<ObserverCommand>,
) -> Option<Input> {
    match flush_reply(transport, controls, situation) {
        OutputReady::Ready if controls.disabled => return None,
        OutputReady::Ready => {}
        OutputReady::Backpressure => return None,
        OutputReady::Closed => {
            controls.disabled = true;
            controls.pending = None;
            observer.write(ObserverCommand::Quit);
            return None;
        }
    }
    let received = match transport.incoming.lock() {
        Ok(receiver) => receiver.try_recv(),
        Err(_) => Ok(Incoming::Failed("control_input_lock_failed")),
    };
    let input = match received {
        Err(TryRecvError::Empty) => return None,
        Ok(Incoming::Input(input)) if controls.pending.is_none() => input,
        other => {
            let reason = match other {
                Ok(Incoming::Failed(reason)) => reason,
                Ok(Incoming::Input(_)) => "control_input_pipelined",
                _ => "control_input_closed",
            };
            controls.respond(None, "refused", Some(reason), situation);
            controls.disabled = true;
            controls.pending = None;
            observer.write(ObserverCommand::Quit);
            return None;
        }
    };
    let sequence = input.sequence;
    if controls.next_sequence != Some(sequence) {
        controls.respond(
            Some(sequence),
            "refused",
            Some("control_sequence_mismatch"),
            situation,
        );
        return None;
    }
    controls.next_sequence = sequence.checked_add(1);
    if !situation.allows(&input) {
        controls.respond(
            Some(sequence),
            "refused",
            Some("control_stale_or_unavailable"),
            situation,
        );
        return None;
    }
    if input.action == Action::Status {
        controls.respond(Some(sequence), "observed", None, situation);
        return None;
    }
    Some(input)
}

fn handle_play_interlock(
    input: &Input,
    situation: &mut Situation,
    controls: &mut Controls,
) -> bool {
    if input.action == Action::ArmOnePlayAdvance {
        let session = &situation.session;
        let applied = situation.client.pending.is_none()
            && !situation.client.status_due
            && (!session.organizer_enabled
                || workspace::resources(&situation.client, session).is_some())
            && situation
                .audit
                .as_deref()
                .is_none_or(|audit| audit.can_arm_play(session))
            && situation
                .interlock
                .as_deref_mut()
                .is_some_and(|i| i.arm(input, session));
        let (event, reason) = if applied {
            ("applied", None)
        } else {
            ("refused", Some("play_interlock_unavailable"))
        };
        controls.respond(Some(input.sequence), event, reason, situation);
        return true;
    }
    if input.action == Action::Play
        && situation.interlock.as_ref().is_some_and(|i| {
            i.witness.is_some()
                && (!i.armed()
                    || i.invalid
                    || i.play.is_some()
                    || situation.session.playing
                    || !i
                        .witness
                        .as_ref()
                        .is_some_and(|w| w.matches(&situation.session)))
        })
    {
        controls.respond(
            Some(input.sequence),
            "refused",
            Some("play_interlock_unavailable"),
            situation,
        );
        return true;
    }
    false
}

fn request_period_proof(input: Input, controls: &mut Controls, situation: &mut Situation) {
    let sequence = input.sequence;
    let result = situation
        .audit
        .as_deref_mut()
        .ok_or("period_proof_capability_absent")
        .and_then(|audit| audit.request_period_proof(&situation.session, sequence));
    if let Err(reason) = result {
        if let Some(audit) = situation.audit.as_deref_mut() {
            audit.refuse_period_proof(reason);
        }
        controls.respond(Some(sequence), "refused", Some(reason), situation);
        return;
    }
    controls.pending = Some(Pending::new(input, situation, None));
}

#[allow(
    clippy::too_many_arguments,
    reason = "`dispatch` declares each Bevy parameter explicitly"
)] // Message writers route distinct existing input ports.
fn dispatch(
    transport: Res<Transport>,
    mut controls: ResMut<Controls>,
    mut receipt: ResMut<HandlerReceipt>,
    mut situation: Situation,
    mut organizer: MessageWriter<OrganizerAction>,
    mut observer: MessageWriter<ObserverCommand>,
    mut production: MessageWriter<ProductionCommand>,
    mut warning: MessageWriter<ContinueWarning>,
    mut evidence: MessageWriter<OpenArchiveEvidence>,
    mut commands: Commands,
    mut windows: Query<(Entity, &mut Window), With<PrimaryWindow>>,
    resized: Res<Messages<WindowResized>>,
) {
    let Some(input) = admitted_input(&transport, &mut controls, &mut situation, &mut observer)
    else {
        return;
    };
    let sequence = input.sequence;
    if handle_play_interlock(&input, &mut situation, &mut controls) {
        return;
    }
    if input.action == Action::AwaitPeriodProof {
        request_period_proof(input, &mut controls, &mut situation);
        return;
    }
    receipt.tracked = None;
    receipt.handled = None;
    if let Some(action) = input
        .action
        .organizer(&situation.client, &situation.session)
    {
        receipt.tracked = Some(Tracked::Organizer(organizer.write(action).id, input.action));
    } else if matches!(
        input.action,
        Action::World | Action::Circuit | Action::Flow | Action::SelectFirstCountyCohort
    ) {
        let Some(command) = situation.production_command(input.action) else {
            controls.respond(
                Some(sequence),
                "refused",
                Some("control_subject_unavailable"),
                &situation,
            );
            return;
        };
        production.write(command);
    } else {
        match input.action {
            Action::AmountKey(_) => {} // Delivered from the admitted pending input on the next frame.
            Action::Play if situation.session.playing => {}
            Action::Pause if !situation.session.playing => {}
            Action::LargerInterface if situation.ui.larger_interface => {}
            Action::StandardInterface if !situation.ui.larger_interface => {}
            Action::ContinueWarning => {
                warning.write(ContinueWarning);
            }
            Action::OpenArchiveEvidence => {
                evidence.write(OpenArchiveEvidence(sequence));
            }
            Action::ContinueTitle => {
                commands.trigger(crate::observer_title::ContinueTitle);
            }
            Action::CaptureFrame => {
                if let Err(reason) =
                    request_frame(&transport, &mut controls, &mut commands, sequence)
                {
                    controls.respond(Some(sequence), "refused", Some(reason), &situation);
                    return;
                }
            }
            action @ (Action::Resize1366x768 | Action::Resize1920x1080) => {
                // Skip only this adapter's pre-request events, not the shared messages.
                controls.resize_cursor.clear(&resized);
                if let Err(reason) = request_resize(&mut controls, &mut windows, action) {
                    controls.respond(Some(sequence), "refused", Some(reason), &situation);
                    return;
                }
            }
            action @ (Action::Play
            | Action::Pause
            | Action::Speed
            | Action::ObserverCampaigns
            | Action::EconomyNetwork
            | Action::ManufacturingSector
            | Action::AllSectors
            | Action::StandardInterface
            | Action::LargerInterface
            | Action::Step
            | Action::Reopen
            | Action::Quit
            | Action::PreviousPeriod
            | Action::ReturnLive) => {
                let message = observer.write(observer_command(action)).id;
                if action == Action::Play {
                    if let Some(interlock) =
                        situation.interlock.as_deref_mut().filter(|i| i.armed())
                    {
                        interlock.play = Some((message, sequence));
                    }
                }
                receipt.tracked = Some(Tracked::Observer(message, action));
            }
            _ => unreachable!("available action has one existing handler"),
        }
    }
    controls.pending = Some(Pending::new(input, &situation, receipt.tracked));
}

/// Bevy's focused event drops the buffered message ID. Bind this one injected event to
/// its original entity and situation, and collect the ordinary observer's synchronous receipt.
fn deliver_amount_key(
    situation: Situation,
    mut controls: ResMut<Controls>,
    windows: Query<Entity, With<PrimaryWindow>>,
    mut commands: Commands,
) {
    let Some(pending) = controls.pending.as_mut() else {
        return;
    };
    let Action::AmountKey(key) = pending.input.action else {
        return;
    };
    if pending.amount_handled.is_some() {
        return;
    }
    let Some((entity, _)) = pending.amount_target else {
        pending.amount_handled = Some(false);
        return;
    };
    let Ok(window) = windows.single() else {
        pending.amount_handled = Some(false);
        return;
    };
    if situation.amount_target() != pending.amount_target
        || !situation.allows(&pending.input)
        || situation.session.context() != pending.context
        || situation.session.runtime_scope() != pending.scope.as_ref()
    {
        pending.amount_handled = Some(false);
        return;
    }
    let sequence = pending.input.sequence;
    let context = pending.context.clone();
    commands.queue(move |world: &mut World| {
        let handled =
            super::amount_editor::deliver_key(world, entity, context, key.pressed(window));
        if let Some(pending) = world
            .resource_mut::<Controls>()
            .pending
            .as_mut()
            .filter(|p| p.input.sequence == sequence)
        {
            pending.amount_handled = Some(handled);
        }
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

fn proof_status_pending(s: &Situation) -> bool {
    s.client.pending.is_some() || s.client.status_due || s.session.organizer_control_pending()
}

fn period_proof_outcome(
    pending: &Pending,
    s: &Situation,
) -> Option<Result<&'static str, &'static str>> {
    let audit = s.audit.as_deref()?;
    let result = audit.period_proof_outcome(pending.input.sequence)?;
    if result.is_ok()
        && (s.session.runtime_scope() != pending.scope.as_ref()
            || s.session.context() != pending.context
            || s.session.foundation_digest != pending.foundation
            || s.session.content_hash != pending.content_hash
            || s.session.world_hash != pending.world_hash
            || audit.period_proof_receipt(&s.session).is_none())
    {
        return Some(Err("period_proof_context_changed"));
    }
    if result.is_ok() {
        if let Err(reason) = audit.fence_reply_ready(
            &s.session,
            pending.input.sequence,
            s.frame.as_deref().and_then(|f| f.for_session(&s.session)),
        ) {
            return Some(Err(reason));
        }
        if proof_status_pending(s) {
            return None;
        }
        if !available(
            Action::AwaitPeriodProof,
            &s.session,
            &s.client,
            &s.ui,
            &s.opening,
            *s.view,
            s.pipe.is_some(),
        ) {
            return Some(Err("period_proof_context_changed"));
        }
    }
    Some(result.map(|()| "period_proof_published"))
}

fn step_outcome(pending: &Pending, s: &Situation) -> Option<Result<&'static str, &'static str>> {
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
    (matches!(
        s.session.phase,
        SessionPhase::Ready | SessionPhase::Complete
    ) && s.session.viewed_tick == s.session.durable_tick
        && s.session.content_hash.is_some())
    .then_some(Ok("committed_and_installed"))
}

fn outcome(pending: &Pending, s: &Situation) -> Option<Result<&'static str, &'static str>> {
    if pending.input.action == Action::AwaitPeriodProof {
        return period_proof_outcome(pending, s);
    }
    if pending.input.action == Action::Reopen {
        return reopen_outcome(pending, &s.session, &s.client);
    }
    if s.session.runtime_scope() != pending.scope.as_ref()
        || matches!(s.session.phase, SessionPhase::Failed | SessionPhase::Closed)
    {
        return Some(Err("control_context_lost"));
    }
    let action = pending.input.action;
    if matches!(action, Action::PreviousPeriod | Action::ReturnLive) {
        let expected = if action == Action::PreviousPeriod {
            pending.context.tick.checked_sub(1)
        } else {
            Some(pending.input.expected_tick)
        };
        if expected != Some(s.session.viewed_tick) {
            return Some(Err("control_view_period_changed"));
        }
        if !matches!(
            s.session.phase,
            SessionPhase::Ready | SessionPhase::Complete
        ) || s.client.pending.is_some()
            || s.client.status_due
            || s.client.view.as_ref().map(|view| view.period) != Some(s.session.durable_tick)
        {
            return None;
        }
        return Some(Ok("applied"));
    }
    if action == Action::Quit {
        return s.session.quit_requested.then_some(Ok("quit_requested"));
    }
    if action == Action::Pause {
        if s.session.campaign != pending.context.campaign
            || s.session.perspective != pending.context.perspective
            || s.session.foundation_digest != pending.foundation
            || s.session.durable_tick < pending.input.expected_tick
            || s.session.generation < pending.context.generation
            || (s.session.durable_tick == pending.input.expected_tick
                && (s.session.content_hash != pending.content_hash
                    || s.session.world_hash != pending.world_hash))
        {
            return Some(Err("control_context_lost"));
        }
        return (!s.session.playing).then_some(Ok("applied"));
    }
    if action == Action::Play && s.play_acknowledged(pending) {
        return Some(Ok("applied"));
    }
    if action != Action::Step && s.session.context() != pending.context {
        return Some(Err("control_context_changed"));
    }
    if matches!(action, Action::AmountKey(_)) {
        if pending.amount_target.is_none()
            || s.amount_target() != pending.amount_target
            || !s.allows(&pending.input)
        {
            return Some(Err("ordinary_handler_refused"));
        }
        return pending.amount_handled.map(|handled| {
            if handled {
                Ok("applied")
            } else {
                Err("ordinary_handler_refused")
            }
        });
    }
    if action == Action::Refresh {
        return Some(Ok("refresh_requested"));
    }
    if action == Action::Step {
        return step_outcome(pending, s);
    }
    if matches!(action, Action::Review | Action::Confirm) {
        return organizer_outcome(pending, s);
    }
    Some(if presentation_applied(pending, s) {
        Ok("applied")
    } else {
        Err("ordinary_handler_refused")
    })
}

fn presentation_applied(pending: &Pending, s: &Situation) -> bool {
    let action = pending.input.action;
    match action.organizer(&s.client, &s.session) {
        Some(OrganizerAction::Choose(choice)) => s.client.choice() == choice,
        Some(OrganizerAction::FocusAmount(field)) => s.focused_amount() == Some(field),
        Some(OrganizerAction::DraftFromReport) => {
            s.client.inspector == OrganizerInspector::Closed
                && s.client.draft.as_ref().is_some_and(|d| {
                    d.selected_reference
                        .is_some_and(|id| d.references.contains(&id))
                })
        }
        Some(OrganizerAction::InspectSubjectEvidence) => {
            s.client.inspector == OrganizerInspector::Evidence
                && matches!(
                    s.client.evidence.mode,
                    super::evidence::EvidenceMode::Subject(_)
                )
        }
        Some(
            OrganizerAction::ArchiveReport
            | OrganizerAction::ArchiveWorkplace
            | OrganizerAction::ArchiveOrganization,
        ) => *s.view == PrimaryView::Map && s.ui.archive_open,
        Some(OrganizerAction::Open) => *s.view == PrimaryView::Organizer,
        Some(OrganizerAction::Inspect(inspector)) => s.client.inspector == inspector,
        Some(OrganizerAction::SetSceneMode(mode)) => s.client.scene_mode == mode,
        Some(OrganizerAction::SelectSubject(subject)) => s.client.selected_subject == Some(subject),
        Some(OrganizerAction::Follow(link)) => match link.destination {
            Destination::Detail(DispatchDestination::Report(id)) => {
                s.client.inspector == OrganizerInspector::Evidence
                    && s.client.selected_evidence_id(s.session.viewed_tick) == Some(id)
            }
            _ => false,
        },
        Some(OrganizerAction::NextEvidence | OrganizerAction::PreviousEvidence) => {
            pending.expected_evidence.is_some()
                && s.client.selected_evidence_id(s.session.viewed_tick) == pending.expected_evidence
        }
        Some(OrganizerAction::CloseInspector) => s.client.inspector == OrganizerInspector::Closed,
        _ => match action {
            Action::Play => s.session.playing,
            Action::Speed => true,
            Action::World => *s.view == PrimaryView::Map,
            Action::Circuit if s.session.organizer_enabled => {
                s.client.inspector == OrganizerInspector::Evidence
            }
            Action::Circuit => *s.view == PrimaryView::Production,
            Action::Flow => s.navigation.as_ref().is_some_and(|nav| {
                nav.details_open && nav.reading_section == ProductionReadingSection::Flow
            }),
            Action::SelectFirstCountyCohort => {
                s.production_command(action)
                    .is_some_and(|command| match command {
                        ProductionCommand::Select { site_id, .. } => s
                            .navigation
                            .as_ref()
                            .is_some_and(|nav| nav.selected_site.as_ref() == Some(&site_id)),
                        _ => false,
                    })
            }
            Action::ObserverCampaigns => {
                s.ui.menu_open && s.opening.menu_page == MenuPage::Campaigns
            }
            Action::EconomyNetwork => s.ui.road_layer == RoadLayer::EconomyNetwork,
            Action::ManufacturingSector => s.ui.network_sector == NetworkSector::Manufacturing,
            Action::AllSectors => s.ui.network_sector == NetworkSector::All,
            Action::StandardInterface => !s.ui.larger_interface,
            Action::LargerInterface => s.ui.larger_interface,
            Action::ContinueWarning => s.opening.stage == OpeningStage::Production,
            Action::ContinueTitle => !s.ui.menu_open,
            _ => false,
        },
    }
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

fn resize_outcome(
    pending: &Pending,
    situation: &Situation,
    observed_extent: Option<(Entity, UVec2)>,
    observed_resize: Option<Entity>,
    windows: &mut Query<(Entity, &mut Window), With<PrimaryWindow>>,
) -> Option<Result<&'static str, &'static str>> {
    if situation.session.runtime_scope() != pending.scope.as_ref()
        || situation.session.context() != pending.context
        || !situation.allows(&pending.input)
    {
        return Some(Err("control_context_changed"));
    }
    if !pending.resize_armed {
        return None;
    }
    let target = pending.input.action.extent().expect("resize action");
    let applied = windows.single_mut().is_ok_and(|(entity, mut window)| {
        let physical = UVec2::new(window.physical_width(), window.physical_height());
        let mode_matches = match pending.input.action {
            Action::Resize1366x768 => window.mode == WindowMode::Windowed,
            Action::Resize1920x1080 => {
                window.mode == WindowMode::BorderlessFullscreen(MonitorSelection::Current)
            }
            _ => false,
        };
        if mode_matches && observed_extent == Some((entity, target)) && physical == target {
            return true;
        }
        // The OS can report an intermediate size while restoring the window.
        if observed_resize == Some(entity) && pending.input.action == Action::Resize1366x768 {
            window
                .resolution
                .set_physical_resolution(target.x, target.y);
        }
        false
    });
    if applied {
        Some(Ok("applied"))
    } else if pending.presentation_started.elapsed() >= PRESENTATION_TIMEOUT {
        Some(Err("primary_window_resize_timeout"))
    } else {
        None
    }
}

fn complete(
    mut controls: ResMut<Controls>,
    mut receipt: ResMut<HandlerReceipt>,
    mut situation: Situation,
    evidence: Res<ArchiveEvidenceReceipt>,
    mut windows: Query<(Entity, &mut Window), With<PrimaryWindow>>,
    resized: Res<Messages<WindowResized>>,
) {
    let mut observation = None;
    for event in controls.resize_cursor.read(&resized) {
        if let Ok((entity, window)) = windows.single_mut() {
            if event.window == entity
                && (event.width - window.width()).abs() < 0.5
                && (event.height - window.height()).abs() < 0.5
            {
                observation = Some((
                    entity,
                    UVec2::new(window.physical_width(), window.physical_height()),
                ));
            }
        }
    }
    if observation.is_some() {
        controls.observed_extent = observation;
    }
    let observed_resize = observation.map(|(entity, _)| entity);
    if controls.reply.is_some() || controls.disabled {
        return;
    }
    let capture_result = controls.capture_result.take();
    let observed_extent = controls.observed_extent;
    let Some(pending) = controls.pending.as_mut() else {
        return;
    };
    let extent = pending.input.action.extent();
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
        Ok(()) if extent.is_some() => {
            let result = resize_outcome(
                pending,
                &situation,
                observed_extent,
                observed_resize,
                &mut windows,
            );
            pending.resize_armed = true;
            result
        }
        Ok(()) if pending.input.action == Action::CaptureFrame => {
            if pending.capture_state.as_ref() == Some(&situation.capture_state()) {
                capture_result.map(|result| result.map(|()| "frame_captured"))
            } else {
                Some(Err("capture_context_changed"))
            }
        }
        Ok(()) if pending.input.action == Action::OpenArchiveEvidence => {
            if situation.session.runtime_scope() != pending.scope.as_ref()
                || situation.session.context() != pending.context
            {
                Some(Err("control_context_changed"))
            } else {
                evidence
                    .result(pending.input.sequence)
                    .map(|result| result.map(|()| "applied"))
            }
        }
        Ok(()) => outcome(pending, &situation),
        Err(reason) => Some(Err(reason)),
    };
    if let Some(result) = result {
        let sequence = pending.input.sequence;
        let action = pending.input.action;
        controls.stage_result(sequence, action, result, &mut situation);
        controls.pending = None;
        receipt.tracked = None;
    }
}

pub(crate) fn install(app: &mut App, transport: Transport) {
    app.insert_resource(transport)
        .add_message::<OpenArchiveEvidence>()
        .add_message::<ProductionCommand>()
        .add_message::<WindowResized>()
        .init_resource::<ArchiveEvidenceReceipt>()
        .init_resource::<Controls>()
        .init_resource::<PlayInterlock>()
        .init_resource::<HandlerReceipt>()
        .add_systems(
            Update,
            (deliver_amount_key, dispatch)
                .chain()
                .before(ObserverSet::Input),
        )
        .add_systems(
            Update,
            // Witness the real warning transition before a long frame reaches Title.
            complete
                .after(ObserverSet::Install)
                .after(ArchiveEvidenceApplied)
                .after(crate::production::navigation::navigate)
                .after(crate::observer_warning::apply_continue)
                .before(crate::observer_opening::advance)
                .before(ObserverSet::Paint),
        );
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::atlas::CountyAtlas;
    use crate::map::SelectedCounty;
    use crate::observer_focus::{ObserverKeyboardActivate, ObserverKeyboardClaim};
    use crate::observer_opening::ProductionSkip;
    use crate::observer_ui::ObserverFeedback;
    use crate::observer_warning::ContinueWarning;
    use crate::ui::dossier_card::ActiveCountyDossier;
    use babylon_kernel::clock::CampaignDuration;
    use babylon_persistence::identity::CampaignId;
    use babylon_persistence::runtime_session::{
        OrganizerAllocation, OrganizerView, RuntimeSessionResponse, RuntimeSessionTail,
    };
    use bevy::input_focus::InputFocus;
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
    fn operator_actions_decode_only_the_bounded_native_controls() {
        for name in [
            "inspect_practices",
            "inspect_receipts",
            "open_relationships",
            "archive_workplace",
            "open_archive_evidence",
            "previous_period",
            "return_live",
            "capture_frame",
            "scene_places",
            "scene_relationships",
            "select_workplace_committee",
            "select_neighborhood_group",
            "inspect_evidence",
            "next_evidence",
            "previous_evidence",
            "archive_organization",
            "resize1366x768",
            "resize1920x1080",
        ] {
            assert!(
                serde_json::from_value::<Action>(json!(name)).is_ok(),
                "{name}"
            );
        }
        assert!(serde_json::from_value::<Action>(json!("capture_desktop")).is_err());
        assert!(serde_json::from_value::<Action>(json!("shell_evidence")).is_err());
    }

    #[test]
    fn qualification_period_proof_is_a_bounded_private_control() {
        let frame = frame("");
        // Use the actual strict decoder, preserving the complete numbered input.
        let mut value: Value = serde_json::from_slice(&frame).expect("fixture JSON");
        value["action"] = json!("await_period_proof");
        let bytes = format!("{value}\n");
        assert!(
            read_input(&mut bytes.as_bytes()).is_ok(),
            "the admitted private proof must have one bounded control variant"
        );
    }

    #[test]
    fn qualification_proof_success_encoding_refuses_null_or_unbounded_state() {
        assert!(bounded_response(Some(7), "period_proof_published", None, &Value::Null).is_err());
        assert!(bounded_response(
            Some(7),
            "period_proof_published",
            None,
            &json!({"oversized": "x".repeat(OUTPUT_BYTES)})
        )
        .is_err());
        let fallback: Value = serde_json::from_slice(&response(
            Some(7),
            "period_proof_published",
            None,
            Value::Null,
        ))
        .expect("bounded refusal");
        assert!(fallback["sequence"].is_null());
        assert_eq!(fallback["event"], "refused");
    }

    #[test]
    fn qualification_foreign_proof_reply_never_becomes_an_acknowledgement() {
        use bevy::ecs::system::RunSystemOnce;
        for output in ["ready", "full", "closed", "absent"] {
            let (mut app, _) = super::ui::tests::allocation_opening();
            let (_peer, _incoming, receiver) = amount_control_transport(&mut app, 1);
            let mut receiver = Some(receiver);
            if output == "full" {
                app.world()
                    .resource::<Transport>()
                    .outgoing
                    .try_send(b"prior".to_vec())
                    .expect("bounded prior reply");
            } else if output == "closed" {
                drop(receiver.take());
            }
            {
                let mut controls = app.world_mut().resource_mut::<Controls>();
                controls.reply = (output != "absent").then(|| b"unadmitted success bytes".to_vec());
                controls.proof_reply = Some(7);
            }
            let result = app
                .world_mut()
                .run_system_once(
                    |transport: Res<Transport>,
                     mut controls: ResMut<Controls>,
                     mut situation: Situation| {
                        flush_reply(&transport, &mut controls, &mut situation)
                    },
                )
                .expect("actual control flush");
            assert!(app.world().resource::<Controls>().proof_reply.is_none());
            match output {
                "ready" => {
                    assert!(matches!(result, OutputReady::Ready));
                    let raw = receiver
                        .as_ref()
                        .expect("receiver")
                        .try_recv()
                        .expect("actual reply");
                    let reply: Value = serde_json::from_slice(&raw).expect("numbered refusal");
                    assert_eq!(reply["event"], "refused");
                }
                "full" => {
                    assert!(matches!(result, OutputReady::Backpressure));
                    let reply: Value = serde_json::from_slice(
                        app.world()
                            .resource::<Controls>()
                            .reply
                            .as_ref()
                            .expect("retained refusal"),
                    )
                    .expect("refusal");
                    assert_eq!(reply["event"], "refused");
                }
                "closed" | "absent" => assert!(matches!(result, OutputReady::Closed)),
                _ => unreachable!(),
            }
        }
    }

    #[test]
    fn qualification_period_proof_requires_a_strict_actionable_ordinary_status() {
        use babylon_persistence::runtime_session::OrganizerBodySource;
        for fault in [
            "none",
            "playing",
            "perspective",
            "viewed",
            "status_due",
            "body",
            "period",
        ] {
            let (mut client, mut session) = crate::organizer::tests::ready();
            session.perspective = crate::observer::Perspective::PlayerKnowledge;
            session.content_hash = Some("04".repeat(32));
            session.world_hash = Some("05".repeat(32));
            let (_, _, _, mut snapshot) = crate::organizer::tests::status_fixture();
            snapshot.body_scope.source = Some(OrganizerBodySource::Committed {
                tick_content_hash: [4; 32],
                world_hash: [5; 32],
            });
            client.queue(&mut session, RequestKind::Status, None);
            let babylon_persistence::runtime_session::RuntimeSessionRequest::OrganizerStatus {
                request_id,
                ..
            } = client.outbox.take().expect("actual status request")
            else {
                unreachable!();
            };
            client
                .status(request_id, snapshot, &mut session)
                .expect("actual admitted status");
            let ui = ObserverUiState {
                splash_visible: false,
                menu_open: false,
                ..default()
            };
            let opening = OpeningPresentation {
                stage: OpeningStage::Game,
                ..default()
            };
            match fault {
                "none" => {}
                "playing" => session.playing = true,
                "perspective" => session.perspective = crate::observer::Perspective::FullObserver,
                "viewed" => session.viewed_tick = 2,
                "status_due" => client.status_due = true,
                "body" => client.body_context = None,
                "period" => client.view.as_mut().expect("actual view").period = 2,
                _ => unreachable!(),
            }
            assert_eq!(
                available(
                    Action::AwaitPeriodProof,
                    &session,
                    &client,
                    &ui,
                    &opening,
                    PrimaryView::Organizer,
                    true
                ),
                fault == "none",
                "{fault}"
            );
        }
    }

    #[test]
    fn qualification_bounded_play_marks_only_its_actual_paused_enqueue_for_early_readiness() {
        use babylon_persistence::runtime_session::OrganizerBodySource;
        crate::observer_io::qualification::with_source_fixture(|audit, mut session, mut status| {
            session.perspective = crate::observer::Perspective::PlayerKnowledge;
            status.body_scope.campaign_id = *session.campaign.as_uuid().as_bytes();
            status.body_scope.source = Some(OrganizerBodySource::Foundation {
                foundation_digest: [0x0a; 32],
            });
            let mut client = OrganizerClient {
                campaign: Some(*session.campaign.as_uuid()),
                ..OrganizerClient::default()
            };
            for _ in 0..2 {
                client.queue(&mut session, RequestKind::Status, None);
                let babylon_persistence::runtime_session::RuntimeSessionRequest::OrganizerStatus {
                    request_id,
                    ..
                } = client.outbox.take().expect("actual status request")
                else {
                    unreachable!();
                };
                client
                    .status(request_id, status.clone(), &mut session)
                    .expect("actual current opening status");
            }
            let scope = session.runtime_scope().expect("scope").clone();
            let (mut app, requests, responses) = crate::observer_io::tests::quit_app();
            crate::observer_io::tests::install_playback(&mut app);
            app.insert_resource(audit)
                .insert_resource(session)
                .insert_resource(client)
                .insert_resource(PrimaryView::Organizer)
                .add_message::<OrganizerAction>();
            app.world_mut().resource_mut::<ObserverUiState>().menu_open = false;
            let (_peer, inputs, _outputs) = amount_control_transport(&mut app, 8);
            app.world_mut().resource_mut::<OpeningPresentation>().stage = OpeningStage::Game;
            app.world_mut()
                .resource_mut::<Time>()
                .advance_by(Duration::from_secs(1));
            issue_playback_input(&mut app, &inputs, 1, "arm_one_play_advance");
            issue_playback_input(&mut app, &inputs, 2, "play");
            let babylon_persistence::runtime_session::RuntimeSessionRequest::Advance {
                request_id,
                ..
            } = requests.try_recv().expect("actual bounded Advance")
            else {
                unreachable!();
            };
            assert!(!app.world().resource::<ObserverSession>().playing);
            assert_ne!(
                request_id, 2,
                "the actual runtime request is not the private Play sequence"
            );
            let paused = app
                .world()
                .resource::<PlayInterlock>()
                .witness
                .as_ref()
                .expect("actual paused witness");
            assert_eq!(paused.request_id, Some(request_id));
            assert!(paused.pending_at_pause);
            responses
                .send(Ok(RuntimeSessionResponse::Committed {
                    request_id,
                    scope,
                    tail: RuntimeSessionTail {
                        resolve_tick: 1,
                        tick_content_hash: Some("ab".repeat(32)),
                        world_hash: Some("cd".repeat(32)),
                    },
                }))
                .expect("accepted Commit");
            app.update();
            let session = app.world().resource::<ObserverSession>();
            assert_eq!(session.durable_tick, 1);
            assert_eq!(
                app.world()
                    .resource::<NativeAudit>()
                    .advance_request_id(session),
                Some(request_id)
            );
            assert!(
                requests.try_recv().is_err(),
                "bounded Play cannot enqueue a second close"
            );
        });
    }

    fn resize_fixture(
        window: Window,
    ) -> (App, Sender<Incoming>, Entity, UnixStream, Receiver<Vec<u8>>) {
        let (client, session) = super::super::tests::ready();
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
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
            .insert_resource(session)
            .insert_resource(client)
            .insert_resource(PrimaryView::Organizer)
            .insert_resource(ObserverUiState {
                menu_open: false,
                splash_visible: false,
                ..default()
            })
            .init_resource::<OpeningPresentation>()
            .add_message::<OrganizerAction>()
            .add_message::<ObserverCommand>()
            .add_message::<ContinueWarning>();
        let entity = app.world_mut().spawn((window, PrimaryWindow)).id();
        let (socket, peer) = UnixStream::pair().expect("fixture sockets");
        let (incoming, receiver) = mpsc::channel();
        let (outgoing, output) = mpsc::sync_channel(1);
        install(
            &mut app,
            Transport {
                incoming: Mutex::new(receiver),
                outgoing,
                socket,
                capture_dir: None,
            },
        );
        (app, incoming, entity, peer, output)
    }

    #[test]
    fn resize_waits_for_observed_primary_extent() {
        for action in [Action::Resize1366x768, Action::Resize1920x1080] {
            let mut window = Window::default();
            if action == Action::Resize1366x768 {
                window.mode = WindowMode::BorderlessFullscreen(MonitorSelection::Current);
                window.resolution.set_physical_resolution(1920, 1080);
            }
            let (mut app, incoming, entity, _peer, _output) = resize_fixture(window);
            let input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                action,
            )
            .input;
            incoming.send(Incoming::Input(input)).expect("receiver");
            app.update();
            app.update();
            assert!(
                app.world().resource::<Controls>().reply.is_none(),
                "requested size is not an observed extent"
            );
            let target = action.extent().expect("resize action");
            app.world_mut().write_message(WindowResized {
                window: entity,
                width: 1.0,
                height: 1.0,
            });
            app.update();
            assert!(
                app.world().resource::<Controls>().reply.is_none(),
                "wrong extent cannot complete"
            );
            if action == Action::Resize1366x768 {
                assert_intermediate_restore(&mut app, entity);
            }
            let mut window = app
                .world_mut()
                .get_mut::<Window>(entity)
                .expect("primary window");
            let expected_mode = match action {
                Action::Resize1366x768 => WindowMode::Windowed,
                Action::Resize1920x1080 => {
                    WindowMode::BorderlessFullscreen(MonitorSelection::Current)
                }
                _ => unreachable!(),
            };
            assert_eq!(window.mode, expected_mode);
            // Bevy's backend installs the physical extent before emitting WindowResized.
            window
                .resolution
                .set_physical_resolution(target.x, target.y);
            let (width, height) = (window.width(), window.height());
            app.world_mut().write_message(WindowResized {
                window: entity,
                width,
                height,
            });
            app.update();
            let reply: Value = serde_json::from_slice(
                app.world()
                    .resource::<Controls>()
                    .reply
                    .as_ref()
                    .expect("observed completion"),
            )
            .expect("JSON");
            assert_eq!(reply["event"], "applied");
        }
    }

    fn assert_intermediate_restore(app: &mut App, entity: Entity) {
        app.world_mut()
            .get_mut::<Window>(entity)
            .expect("window")
            .resolution
            .set_physical_resolution(1920, 1004);
        app.world_mut().write_message(WindowResized {
            window: entity,
            width: 1920.0,
            height: 1004.0,
        });
        app.update();
        let window = app.world().get::<Window>(entity).expect("window");
        assert_eq!(
            (window.physical_width(), window.physical_height()),
            (1366, 768)
        );
        assert!(app.world().resource::<Controls>().reply.is_none());
    }

    #[test]
    fn resize_clamped_or_unobserved_extent_refuses_after_deadline() {
        for observed in [true, false] {
            let (mut app, incoming, entity, _peer, _output) = resize_fixture(Window::default());
            let input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                Action::Resize1920x1080,
            )
            .input;
            incoming.send(Incoming::Input(input)).expect("receiver");
            app.update();
            if observed {
                {
                    let mut window = app.world_mut().get_mut::<Window>(entity).expect("window");
                    window.resolution.set_physical_resolution(1920, 1004);
                }
                app.world_mut().write_message(WindowResized {
                    window: entity,
                    width: 1920.0,
                    height: 1004.0,
                });
                app.update();
                assert!(
                    app.world().resource::<Controls>().reply.is_none(),
                    "intermediate sizes must be allowed"
                );
            } else {
                app.update();
                assert!(app.world().resource::<Controls>().reply.is_none());
            }
            let mut controls = app.world_mut().resource_mut::<Controls>();
            let pending = controls.pending.as_mut().expect("resize remains pending");
            pending.presentation_started = Instant::now()
                .checked_sub(PRESENTATION_TIMEOUT)
                .expect("monotonic clock");
            app.update();
            let controls = app.world().resource::<Controls>();
            let reply: Value =
                serde_json::from_slice(controls.reply.as_ref().expect("bounded refusal"))
                    .expect("JSON");
            assert_eq!(reply["event"], "refused");
            assert_eq!(reply["reason"], "primary_window_resize_timeout");
            assert!(controls.pending.is_none());
        }
    }

    #[test]
    fn resize_same_size_without_observation_refuses() {
        let mut window = Window::default();
        window.resolution.set_physical_resolution(1366, 768);
        let (mut app, incoming, _entity, _peer, _output) = resize_fixture(window);
        let input = pending(
            app.world().resource::<ObserverSession>(),
            app.world().resource::<OrganizerClient>(),
            Action::Resize1366x768,
        )
        .input;
        incoming.send(Incoming::Input(input)).expect("receiver");
        app.update();
        let controls = app.world().resource::<Controls>();
        let reply: Value =
            serde_json::from_slice(controls.reply.as_ref().expect("bounded refusal"))
                .expect("JSON");
        assert_eq!(reply["event"], "refused");
        assert_eq!(reply["reason"], "primary_window_extent_unobserved");
        assert!(controls.pending.is_none());
    }

    #[test]
    fn resize_same_size_requires_fresh_observation_after_unmaximize() {
        let mut window = Window::default();
        window.resolution.set_physical_resolution(1366, 768);
        let (mut app, incoming, entity, _peer, _output) = resize_fixture(window);
        app.world_mut().write_message(WindowResized {
            window: entity,
            width: 1366.0,
            height: 768.0,
        });
        app.update();
        let input = pending(
            app.world().resource::<ObserverSession>(),
            app.world().resource::<OrganizerClient>(),
            Action::Resize1366x768,
        )
        .input;
        incoming.send(Incoming::Input(input)).expect("receiver");
        app.update();
        app.update();
        assert!(
            app.world().resource::<Controls>().reply.is_none(),
            "prior observation cannot acknowledge unmaximize"
        );
        let mut controls = app.world_mut().resource_mut::<Controls>();
        controls
            .pending
            .as_mut()
            .expect("pending resize")
            .presentation_started = Instant::now()
            .checked_sub(PRESENTATION_TIMEOUT)
            .expect("monotonic clock");
        app.update();
        let controls = app.world().resource::<Controls>();
        let reply: Value =
            serde_json::from_slice(controls.reply.as_ref().expect("bounded refusal"))
                .expect("JSON");
        assert_eq!(reply["reason"], "primary_window_resize_timeout");
    }

    #[test]
    fn queued_resize_before_request_cannot_acknowledge_unmaximize() {
        for later_event in [false, true] {
            let mut window = Window::default();
            window.resolution.set_physical_resolution(1366, 768);
            let (mut app, incoming, entity, _peer, _output) = resize_fixture(window);
            let event = WindowResized {
                window: entity,
                width: 1366.0,
                height: 768.0,
            };
            app.world_mut().write_message(event.clone());
            app.update();
            let input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                Action::Resize1366x768,
            )
            .input;
            app.world_mut().write_message(event.clone());
            incoming.send(Incoming::Input(input)).expect("receiver");
            app.update();
            app.update();
            assert!(
                app.world().resource::<Controls>().reply.is_none(),
                "pre-request event cannot acknowledge resize"
            );
            if later_event {
                app.world_mut().write_message(event);
            } else {
                let mut controls = app.world_mut().resource_mut::<Controls>();
                controls
                    .pending
                    .as_mut()
                    .expect("pending resize")
                    .presentation_started = Instant::now()
                    .checked_sub(PRESENTATION_TIMEOUT)
                    .expect("monotonic clock");
            }
            app.update();
            let controls = app.world().resource::<Controls>();
            let reply: Value =
                serde_json::from_slice(controls.reply.as_ref().expect("completed response"))
                    .expect("JSON");
            if later_event {
                assert_eq!(reply["event"], "applied");
            } else {
                assert_eq!(reply["event"], "refused");
                assert_eq!(reply["reason"], "primary_window_resize_timeout");
            }
        }
    }

    fn assert_frame_scenario(app: &mut App, path: &Path, scenario: &str) {
        if matches!(scenario, "playing" | "loading") {
            let reply: Value = serde_json::from_slice(
                app.world()
                    .resource::<Controls>()
                    .reply
                    .as_ref()
                    .expect("refusal"),
            )
            .expect("JSON");
            assert_eq!(reply["reason"], "control_stale_or_unavailable");
            assert!(!path.exists());
        } else if scenario == "existing" {
            let reply: Value = serde_json::from_slice(
                app.world()
                    .resource::<Controls>()
                    .reply
                    .as_ref()
                    .expect("refusal"),
            )
            .expect("JSON");
            assert_eq!(reply["reason"], "capture_file_unavailable");
            assert_eq!(fs::read(path).expect("preserved"), b"preserve");
        } else {
            assert!(
                app.world().resource::<Controls>().reply.is_none(),
                "capture must wait for renderer"
            );
            let mut query = app.world_mut().query_filtered::<Entity, With<Screenshot>>();
            let entity = query.single(app.world()).expect("screenshot request");
            let mut image = Image::default();
            if scenario == "invalid" {
                image.data = None;
            }
            if scenario == "playback_changed" {
                app.world_mut().resource_mut::<ObserverSession>().playing = true;
            }
            if scenario == "presentation_changed" {
                app.world_mut()
                    .resource_mut::<ObserverUiState>()
                    .archive_open = true;
            }
            if scenario == "status_refusal_changed" {
                app.world_mut()
                    .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                        let mut session = world.resource_mut::<ObserverSession>();
                        client.queue(&mut session, RequestKind::Status, None);
                        let request_id = client.pending.as_ref().expect("status pending").id;
                        assert!(client.refused(
                            Some(request_id),
                            "Status refused".into(),
                            &mut session
                        ));
                    });
            }
            if scenario == "selection_changed" {
                app.world_mut()
                    .resource_mut::<OrganizerClient>()
                    .selected_subject = Some(OrganizerSubject::WorkplaceCommittee(92));
            }
            app.world_mut()
                .trigger(ScreenshotCaptured { entity, image });
            app.update();
            let reply: Value = serde_json::from_slice(
                app.world()
                    .resource::<Controls>()
                    .reply
                    .as_ref()
                    .expect("completed capture"),
            )
            .expect("JSON");
            if scenario == "success" {
                assert_eq!(reply["event"], "frame_captured");
                assert!(fs::read(path)
                    .expect("PNG")
                    .starts_with(b"\x89PNG\r\n\x1a\n"));
            } else if scenario == "invalid" {
                assert_eq!(reply["reason"], "capture_image_invalid");
            } else {
                assert_eq!(reply["reason"], "capture_context_changed");
            }
        }
    }

    #[test]
    fn frame_capture_waits_for_render_and_refuses_existing_or_invalid_files() {
        for scenario in [
            "success",
            "existing",
            "invalid",
            "playing",
            "loading",
            "playback_changed",
            "presentation_changed",
            "selection_changed",
            "status_refusal_changed",
        ] {
            let fixture = SocketFixture(
                std::env::temp_dir().join(format!("babylon-frame-{}", Uuid::new_v4())),
            );
            fs::create_dir(&fixture.0).expect("private fixture directory");
            let path = fixture.0.join("frame-1.png");
            if scenario == "existing" {
                fs::write(&path, b"preserve").expect("existing fixture");
            }
            let (client, mut session) = super::super::tests::ready();
            session.playing = scenario == "playing";
            if scenario == "loading" {
                session.phase = SessionPhase::Loading;
            }
            let mut app = App::new();
            app.add_plugins(MinimalPlugins)
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
                .insert_resource(session)
                .insert_resource(client)
                .insert_resource(PrimaryView::Organizer)
                .insert_resource(ObserverUiState {
                    menu_open: false,
                    splash_visible: false,
                    ..default()
                })
                .init_resource::<OpeningPresentation>()
                .add_message::<OrganizerAction>()
                .add_message::<ObserverCommand>()
                .add_message::<ContinueWarning>();
            let (socket, _peer) = UnixStream::pair().expect("fixture sockets");
            let (incoming, receiver) = mpsc::channel();
            let (outgoing, _output) = mpsc::sync_channel(1);
            install(
                &mut app,
                Transport {
                    incoming: Mutex::new(receiver),
                    outgoing,
                    socket,
                    capture_dir: Some(fixture.0.clone()),
                },
            );
            let input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                Action::CaptureFrame,
            )
            .input;
            incoming
                .send(Incoming::Input(input))
                .expect("fixture receiver");
            app.update();
            assert_frame_scenario(&mut app, &path, scenario);
            if !matches!(scenario, "playing" | "loading") {
                fs::remove_file(path).expect("remove exact fixture");
            }
        }
    }

    #[test]
    fn history_control_waits_for_installed_view_while_snapshot_stays_at_tail() {
        #[derive(Resource)]
        struct InputWitness(Pending);
        #[derive(Resource, Default)]
        struct Verdict(Option<Result<&'static str, &'static str>>);
        fn inspect(situation: Situation, input: Res<InputWitness>, mut verdict: ResMut<Verdict>) {
            verdict.0 = outcome(&input.0, &situation);
        }
        let (client, mut session) = super::super::tests::ready();
        let original = pending(&session, &client, Action::PreviousPeriod);
        session.inspect_tick(2);
        assert_eq!(session.phase, SessionPhase::Loading);
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
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        let context = session.context();
        assert!(session.installed(&context));
        app.update();
        assert_eq!(app.world().resource::<Verdict>().0, Some(Ok("applied")));
        assert_eq!(app.world().resource::<ObserverSession>().viewed_tick, 2);
        assert_eq!(
            app.world()
                .resource::<OrganizerClient>()
                .view
                .as_ref()
                .expect("tail view")
                .period,
            3
        );
    }

    #[test]
    fn qualification_socket_is_private_lossless_and_closes_on_drop() {
        let fixture =
            SocketFixture(std::env::temp_dir().join(format!("babylon-q-{}", Uuid::new_v4())));
        fs::create_dir(&fixture.0).expect("the fixture directory is creatable");
        fs::set_permissions(&fixture.0, Permissions::from_mode(0o700))
            .expect("the fixture file mode is settable");
        let path = fixture.0.join("control.sock");
        let listener = UnixListener::bind(&path)
            .expect("the fixture call `bind` succeeds for the authored inputs");
        fs::set_permissions(&path, Permissions::from_mode(0o600))
            .expect("the fixture file mode is settable");
        let (started, ready) = mpsc::sync_channel(1);
        let connect_path = path.clone();
        let worker = thread::spawn(move || {
            started
                .send(Transport::connect(
                    &connect_path,
                    "00000000-0000-0000-0000-000000000001",
                ))
                .expect("the receiver stays alive for the send");
        });
        let (mut peer, _) = listener
            .accept()
            .expect("the fixture call `accept` succeeds for the authored inputs");
        peer.set_read_timeout(Some(Duration::from_secs(2)))
            .expect("the fixture connection accepts the timeout");
        assert!(
            matches!(
                ready.recv_timeout(Duration::from_millis(50)),
                Err(mpsc::RecvTimeoutError::Timeout)
            ),
            "campaign startup must wait for explicit capture admission"
        );
        let mut admission = b"{\"version\":5,\"campaign_id\":\"00000000-0000-0000-0000-000000000001\",\"phase\":\"capture_ready\"}\n".to_vec();
        admission.extend(frame(""));
        peer.write_all(&admission)
            .expect("the fixture sink accepts the authored bytes");
        let transport = ready
            .recv_timeout(Duration::from_secs(2))
            .expect("the producer sends before the fixture timeout")
            .expect("the nested fixture result is present");
        worker
            .join()
            .expect("the fixture worker finishes without panic");
        let receiver = transport
            .incoming
            .lock()
            .expect("the fixture lock is never poisoned");
        let Incoming::Input(input) = receiver
            .recv_timeout(Duration::from_secs(2))
            .expect("the producer sends before the fixture timeout")
        else {
            panic!("private socket must preserve the input frame");
        };
        assert_eq!((input.sequence, input.action), (1, Action::Status));
        let bytes = response(Some(1), "observed", None, json!({}));
        transport
            .outgoing
            .try_send(bytes.clone())
            .expect("the bounded channel has capacity for the fixture message");
        let mut read = BufReader::new(
            peer.try_clone()
                .expect("the fixture input satisfies the fallible conversion"),
        );
        let mut decoded = Vec::new();
        read.read_until(b'\n', &mut decoded)
            .expect("the fixture source is readable");
        assert_eq!(decoded, bytes);
        peer.shutdown(Shutdown::Write)
            .expect("the fixture call `shutdown` succeeds for the authored inputs");
        assert!(matches!(
            receiver
                .recv_timeout(Duration::from_secs(2))
                .expect("the producer sends before the fixture timeout"),
            Incoming::Closed
        ));
        drop(receiver);
        fs::set_permissions(&fixture.0, Permissions::from_mode(0o755))
            .expect("the fixture file mode is settable");
        assert!(
            Transport::connect(&path, "00000000-0000-0000-0000-000000000001").is_err(),
            "a public directory cannot become a control channel"
        );
        drop(transport);
        let mut trailing = [0; 1];
        assert_eq!(
            read.read(&mut trailing)
                .expect("the fixture reader returns its authored facts"),
            0
        );
    }

    fn pending(session: &ObserverSession, client: &OrganizerClient, action: Action) -> Pending {
        Pending {
            input: Input {
                version: 5,
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
            world_hash: session.world_hash.clone(),
            capture_state: None,
            expected_evidence: None,
            amount_target: None,
            amount_handled: None,
            resize_armed: false,
            presentation_started: Instant::now(),
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

    fn configure_relationships_scenario(app: &mut App, scenario: &str) {
        match scenario {
            "playing" => app.world_mut().resource_mut::<ObserverSession>().playing = true,
            "loading" => {
                app.world_mut().resource_mut::<ObserverSession>().phase = SessionPhase::Loading;
            }
            "stale_view" => {
                app.world_mut()
                    .resource_mut::<OrganizerClient>()
                    .view
                    .as_mut()
                    .expect("fixture view")
                    .period = 1;
            }
            "status_due" => app
                .world_mut()
                .resource_mut::<OrganizerClient>()
                .committed(),
            "status_pending" => {
                app.world_mut()
                    .resource_mut::<ObserverSession>()
                    .connected_fixture();
                app.world_mut()
                    .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                        client.queue(
                            &mut world.resource_mut::<ObserverSession>(),
                            RequestKind::Status,
                            None,
                        );
                        assert!(client.pending.is_some());
                    });
            }
            "control_pending" => app
                .world_mut()
                .resource_mut::<ObserverSession>()
                .set_organizer_control_pending(true),
            "quit" => {
                app.world_mut()
                    .resource_mut::<ObserverSession>()
                    .quit_requested = true;
            }
            _ => (),
        }
    }

    #[test]
    fn relationships_control_routes_through_handler_and_refuses_stale_or_unready_context() {
        for scenario in [
            "ready",
            "playing",
            "loading",
            "stale",
            "stale_view",
            "status_due",
            "status_pending",
            "control_pending",
            "quit",
        ] {
            let (mut app, _, _) = ui::tests::dossier_navigation_fixture();
            app.init_resource::<OpeningPresentation>()
                .add_message::<ContinueWarning>();
            let (socket, _peer) = UnixStream::pair().expect("fixture sockets");
            let (incoming, receiver) = mpsc::channel();
            let (outgoing, _output) = mpsc::sync_channel(1);
            install(
                &mut app,
                Transport {
                    incoming: Mutex::new(receiver),
                    outgoing,
                    socket,
                    capture_dir: None,
                },
            );
            app.update();
            configure_relationships_scenario(&mut app, scenario);
            let mut input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                Action::Status,
            )
            .input;
            input.action =
                serde_json::from_value(json!("open_relationships")).expect("action decodes");
            if scenario == "stale" {
                input.expected_generation += 1;
            }
            incoming
                .send(Incoming::Input(input))
                .expect("receiver open");
            app.update();
            let reply: Value = serde_json::from_slice(
                app.world()
                    .resource::<Controls>()
                    .reply
                    .as_ref()
                    .expect("response"),
            )
            .expect("JSON");
            if scenario == "ready" {
                assert_eq!(reply["event"], "applied", "{reply}");
                assert_eq!(
                    app.world().resource::<OrganizerClient>().inspector,
                    OrganizerInspector::Relationships
                );
            } else {
                assert_eq!(
                    reply["reason"], "control_stale_or_unavailable",
                    "{scenario}: {reply}"
                );
                assert_eq!(
                    app.world().resource::<OrganizerClient>().inspector,
                    OrganizerInspector::Closed
                );
            }
        }
    }

    #[test]
    fn queued_private_evidence_refusal_preserves_the_organizer_draft() {
        let (mut app, _) = crate::ui::dossier_card::tests::evidence_route_app();
        let (client, _) = super::super::tests::ready();
        app.insert_resource(client);
        let choice = app.world().resource::<OrganizerClient>().choice();
        let session = app.world().resource::<ObserverSession>().context();
        let tick = app.world().resource::<ObserverSession>().durable_tick;
        let selected = app.world().resource::<SelectedCounty>().0;
        let (entity, context) = crate::ui::dossier_card::tests::evidence_control(&mut app);
        app.world_mut()
            .trigger(ObserverKeyboardActivate { entity, context });
        app.world_mut().write_message(OpenArchiveEvidence(10));
        app.update();
        assert_eq!(
            app.world().resource::<ArchiveEvidenceReceipt>().result(10),
            Some(Err("ordinary_handler_refused"))
        );
        assert_eq!(app.world().resource::<OrganizerClient>().choice(), choice);
        assert_eq!(app.world().resource::<ObserverSession>().context(), session);
        assert_eq!(app.world().resource::<ObserverSession>().durable_tick, tick);
        assert_eq!(app.world().resource::<SelectedCounty>().0, selected);
    }

    #[test]
    fn qualification_evidence_action_uses_the_real_archive_handler() {
        for scenario in ["open", "hidden", "stale"] {
            let (mut app, zone) = crate::ui::dossier_card::tests::evidence_route_app();
            let (client, _) = super::super::tests::ready();
            app.insert_resource(client)
                .insert_resource(PrimaryView::Map)
                .init_resource::<OpeningPresentation>()
                .add_message::<OrganizerAction>()
                .add_message::<ObserverCommand>()
                .add_message::<ContinueWarning>()
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
            let (socket, _peer) = UnixStream::pair().expect("fixture sockets");
            let (incoming, receiver) = mpsc::channel();
            let (outgoing, _output) = mpsc::sync_channel(1);
            install(
                &mut app,
                Transport {
                    incoming: Mutex::new(receiver),
                    outgoing,
                    socket,
                    capture_dir: None,
                },
            );
            if scenario == "hidden" {
                app.world_mut().get_mut::<Node>(zone).expect("zone").display = Display::None;
            }
            let mut input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                Action::OpenArchiveEvidence,
            )
            .input;
            if scenario == "stale" {
                input.expected_generation += 1;
            }
            let context = app.world().resource::<ObserverSession>().context();
            let durable_tick = app.world().resource::<ObserverSession>().durable_tick;
            let choice = app.world().resource::<OrganizerClient>().choice();
            let selected = app.world().resource::<SelectedCounty>().0;
            let page = app.world().resource::<ActiveCountyDossier>().clone();
            incoming.send(Incoming::Input(input)).expect("send request");
            app.update();
            assert_eq!(app.world().resource::<ObserverSession>().context(), context);
            assert_eq!(
                app.world().resource::<ObserverSession>().durable_tick,
                durable_tick
            );
            assert_eq!(app.world().resource::<OrganizerClient>().choice(), choice);
            assert_eq!(app.world().resource::<SelectedCounty>().0, selected);
            assert_eq!(*app.world().resource::<ActiveCountyDossier>(), page);
            let reply: Value = serde_json::from_slice(
                app.world()
                    .resource::<Controls>()
                    .reply
                    .as_ref()
                    .expect("handler reply"),
            )
            .expect("JSON reply");
            if scenario == "open" {
                assert_eq!(reply["event"], "applied", "{reply}");
            } else {
                assert_eq!(reply["event"], "refused", "{scenario}: {reply}");
            }
        }
    }

    fn amount_control_transport(
        app: &mut App,
        capacity: usize,
    ) -> (UnixStream, Sender<Incoming>, Receiver<Vec<u8>>) {
        app.init_resource::<OpeningPresentation>()
            .add_message::<ContinueWarning>();
        let (socket, peer) = UnixStream::pair().expect("local test peer");
        let (incoming, receiver) = mpsc::channel();
        let (outgoing, output) = mpsc::sync_channel(capacity);
        install(
            app,
            Transport {
                incoming: Mutex::new(receiver),
                outgoing,
                socket,
                capture_dir: None,
            },
        );
        (peer, incoming, output)
    }

    #[test]
    fn qualification_amount_keys_require_focused_ordinary_editor_and_report_real_readback() {
        let (mut app, _window) = super::ui::tests::allocation_opening();
        let (_peer, incoming, output) = amount_control_transport(&mut app, 4);
        let mut sequence = 0;
        let mut send = |app: &mut App, action: Value| {
            sequence += 1;
            let session = app.world().resource::<ObserverSession>();
            let record = json!({"version":5,"sequence":sequence,"campaign_id":session.campaign.as_uuid().to_string(),
                "scope_epoch":session.runtime_scope().map(|scope|scope.epoch),"expected_tick":session.durable_tick,
                "expected_generation":session.generation,"action":action});
            let line = format!("{record}\n");
            let input = read_input(&mut line.as_bytes())
                .expect("valid wire")
                .expect("one action");
            println!("Qualification input {record}");
            incoming
                .send(Incoming::Input(input))
                .expect("bounded action");
            for _ in 0..6 {
                app.update();
                if let Ok(raw) = output.try_recv() {
                    let value =
                        serde_json::from_slice::<Value>(&raw).expect("actual producer frame");
                    println!(
                        "Qualification frame {}",
                        std::str::from_utf8(&raw)
                            .expect("UTF-8 response bytes")
                            .trim_end_matches('\n')
                    );
                    return value;
                }
            }
            panic!("ordinary handler did not acknowledge {action:?}");
        };
        assert_eq!(
            send(&mut app, json!({"amount_key":{"character":"1"}}))["event"],
            "refused"
        );
        assert_eq!(
            send(&mut app, json!("inspect_practices"))["event"],
            "applied"
        );
        assert_eq!(
            send(&mut app, json!("choose_collect"))["state"]["choice"],
            "collect"
        );
        let focus = send(&mut app, json!({"focus_amount":"contribution"}));
        assert_eq!(focus["state"]["focused_amount"], "contribution");
        assert_eq!(focus["state"]["amount_text"], "280");
        let edit = send(&mut app, json!({"amount_key":"backspace"}));
        assert_eq!(edit["event"], "applied", "{edit}");
        assert_eq!(
            edit["state"]["collection_allocation"]["collection"]["target_cash_micros"],
            "28000000"
        );
        let bad = send(&mut app, json!({"amount_key":{"character":"-"}}));
        assert_eq!(bad["state"]["amount_text"], "28-");
        assert!(bad["state"]["allocation_error"].is_string());
        assert!(bad["state"]["reviewed_command"].is_null() && bad["state"]["commitment"].is_null());
    }

    #[derive(Clone, Copy, PartialEq, Eq)]
    enum Interference {
        OtherKey,
        AnotherField,
        ChangedContext,
    }
    fn press_focused_home(app: &mut App, window: Entity) {
        use bevy::input::keyboard::{Key, KeyboardInput};
        use bevy::input::ButtonState;
        use bevy::input_focus::FocusedInput;
        let entity = app
            .world()
            .resource::<InputFocus>()
            .get()
            .expect("ordinary field has focus");
        app.world_mut().trigger(FocusedInput::new(
            entity,
            KeyboardInput {
                window,
                key_code: KeyCode::Home,
                logical_key: Key::Home,
                text: None,
                repeat: false,
                state: ButtonState::Pressed,
            },
            window,
        ));
    }

    fn competing_amount_input(race: Interference) {
        use crate::observer::Perspective;
        use bevy::ecs::system::RunSystemOnce;
        use bevy::input_focus::FocusCause;
        let (mut app, window) = super::ui::tests::allocation_opening();
        for action in [
            OrganizerAction::Inspect(OrganizerInspector::Practices),
            OrganizerAction::Choose(OrganizerChoice::LocalAid),
            OrganizerAction::FocusAmount(AmountField::Food),
        ] {
            app.world_mut().write_message(action);
            app.update();
            app.update();
        }
        let (_peer, sender, output) = amount_control_transport(&mut app, 4);
        let input = pending(
            app.world().resource::<ObserverSession>(),
            app.world().resource::<OrganizerClient>(),
            Action::AmountKey(AmountKey::Backspace),
        )
        .input;
        sender
            .send(Incoming::Input(input))
            .expect("live input channel");
        app.world_mut()
            .run_system_once(dispatch)
            .expect("ordinary dispatch resources installed");
        assert!(app.world().resource::<Controls>().pending.is_some());
        if race == Interference::AnotherField {
            let world = app.world_mut();
            let cash = world
                .query::<(Entity, &AmountField)>()
                .iter(world)
                .find(|(_, f)| **f == AmountField::Cash)
                .expect("cash field in the native deck")
                .0;
            world
                .resource_mut::<InputFocus>()
                .set(cash, FocusCause::Navigated);
        }
        if race == Interference::ChangedContext {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            let other = match session.perspective {
                Perspective::FullObserver => Perspective::PlayerKnowledge,
                Perspective::PlayerKnowledge => Perspective::FullObserver,
            };
            session.set_perspective(other);
        }
        press_focused_home(&mut app, window);
        app.world_mut()
            .run_system_once(complete)
            .expect("ordinary completion resources installed");
        if race == Interference::OtherKey {
            assert!(
                app.world().resource::<Controls>().reply.is_none(),
                "a genuine Home key cannot acknowledge a pending Backspace"
            );
            app.update();
            app.update();
            let applied: Value =
                serde_json::from_slice(&output.try_recv().expect("processed original key reply"))
                    .expect("bounded key response");
            assert_eq!(applied["event"], "applied");
            assert_eq!(applied["state"]["focused_amount"], "food");
            assert_eq!(
                AmountField::Food.text(app.world().resource::<OrganizerClient>()),
                "1",
                "the actual Backspace at Home leaves the text intact"
            );
        } else {
            let raw = app
                .world()
                .resource::<Controls>()
                .reply
                .as_ref()
                .expect("original focus lost");
            let value: Value = serde_json::from_slice(raw).expect("bounded refusal frame");
            assert_eq!(value["event"], "refused");
            app.update();
            assert_eq!(
                AmountField::Cash.text(app.world().resource::<OrganizerClient>()),
                "0",
                "queued Food key must not edit cash"
            );
        }
    }
    #[test]
    fn repaired_qualification_competing_key_cannot_acknowledge_another_key() {
        competing_amount_input(Interference::OtherKey);
    }
    #[test]
    fn repaired_qualification_focus_switch_cannot_retarget_or_acknowledge_the_key() {
        competing_amount_input(Interference::AnotherField);
    }

    #[test]
    fn repaired_qualification_context_change_refuses_the_queued_key() {
        competing_amount_input(Interference::ChangedContext);
    }
    fn status_frame(app: &mut App, sequence: u64) -> Value {
        use bevy::ecs::system::RunSystemOnce;
        let raw = app
            .world_mut()
            .run_system_once(move |s: Situation| {
                let mut controls = Controls::default();
                controls.respond(Some(sequence), "observed", None, &s);
                controls.reply.expect("status response")
            })
            .expect("control state");
        let value: Value = serde_json::from_slice(&raw).expect("control frame");
        println!(
            "Qualification status {}",
            std::str::from_utf8(&raw)
                .expect("UTF-8 status bytes")
                .trim_end_matches('\n')
        );
        value
    }

    fn check_installed_status(reviewed: &Value, expected_view: &OrganizerView) {
        let installed = &reviewed["state"]["installed_organizer"];
        assert_eq!(installed["actor_id"], expected_view.actor_id);
        assert_eq!(installed["authority_id"], json!(expected_view.authority_id));
        assert_eq!(installed["standing"], json!(expected_view.standing));
        assert_eq!(installed["available_hours"], expected_view.available_hours);
        assert_eq!(installed["contact_hours"], expected_view.contact_hours);
        assert_eq!(
            installed["content_digest"],
            json!(expected_view.content_digest)
        );
        assert_eq!(
            installed["resource_digest"],
            json!(expected_view.resource_digest)
        );
    }

    #[test]
    fn qualification_status_authenticates_the_reviewed_and_accepted_original() {
        use super::super::draft::OrganizerDraft;
        use babylon_persistence::runtime_session::OrganizerSnapshot;
        use babylon_practice_contract::{OrganizerConfig, OrganizerState};
        use bevy::ecs::system::RunSystemOnce;
        let recorded: Value = serde_json::from_str(include_str!(
            "../../../babylon-persistence/tests/fixtures/food_only_no_payer_v19.json"
        ))
        .expect("producer capture");
        let snapshot: OrganizerSnapshot =
            serde_json::from_value(recorded["snapshot"].clone()).expect("actual status");
        let expected_view = snapshot.view.clone();
        let config: OrganizerConfig =
            serde_json::from_value(recorded["config"].clone()).expect("actual authority");
        let law: OrganizerState =
            serde_json::from_value(recorded["state"].clone()).expect("actual starting state");
        let campaign = Uuid::from_bytes(config.campaign_id);
        let mut session = ObserverSession::new(
            babylon_persistence::identity::CampaignId::from_uuid(campaign),
        );
        session.connected_fixture();
        session.ready(0, None);
        session.organizer_enabled = true;
        assert!(session.installed(&session.context()));
        let mut client = OrganizerClient::default();
        client.admitted(campaign);
        client.draft = Some(OrganizerDraft::captured(&snapshot));
        client.draft_writable = true;
        client.queue(&mut session, RequestKind::Status, None);
        let request = client.pending.as_ref().expect("status sent").id;
        client
            .status(request, snapshot, &mut session)
            .expect("admitted evidence");
        client.draft.as_mut().expect("draft").choice = OrganizerChoice::LocalAid;
        let command = client
            .make_command(&session, OrganizerChoice::LocalAid)
            .expect("captured food-only mandate");
        let ruling = babylon_practice_contract::preview_organizer(&config, &law, &command)
            .expect("authoritative preview");
        client.queue(&mut session, RequestKind::Preview, Some(command.clone()));
        let id = client.pending.as_ref().expect("preview sent").id;
        client
            .previewed(id, ruling, &mut session)
            .expect("matched preview");
        let mut app = App::new();
        app.insert_resource(client)
            .insert_resource(session)
            .insert_resource(PrimaryView::Organizer)
            .init_resource::<ObserverUiState>()
            .init_resource::<OpeningPresentation>();
        let reviewed = status_frame(&mut app, 1);
        check_installed_status(&reviewed, &expected_view);
        assert_eq!(
            reviewed["state"]["reviewed_command"],
            serde_json::to_value(&command).expect("command")
        );
        assert_eq!(
            reviewed["state"]["preview"]["allocation"],
            reviewed["state"]["reviewed_command"]["allocation"]
        );
        assert!(reviewed["state"]["commitment"].is_null());
        let accepted = babylon_practice_contract::admit_organizer(&config, &law, &command)
            .expect("authoritative admission");
        app.world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                let mut session = world.resource_mut::<ObserverSession>();
                client.queue(&mut session, RequestKind::Submit, Some(command));
                let id = client.pending.as_ref().expect("submission sent").id;
                client
                    .accepted(id, accepted.clone(), &mut session)
                    .expect("matched admission");
            });
        let admitted = status_frame(&mut app, 2);
        assert_eq!(
            admitted["state"]["commitment"],
            serde_json::to_value(accepted).expect("accepted original")
        );
        assert_eq!(
            admitted["state"]["commitment"]["command"],
            reviewed["state"]["reviewed_command"]
        );
        assert!(admitted["state"]["reviewed_command"].is_null());
        for choice in ["hold_reviewable", "pause_reviewable", "resume_reviewable"] {
            assert_eq!(
                admitted["state"]["installed_organizer"][choice], false,
                "an accepted original blocks review"
            );
        }
        app.world_mut().resource_mut::<ObserverSession>().generation += 1;
        assert!(
            app.world_mut()
                .run_system_once(|s: Situation| s.state()["installed_organizer"].is_null())
                .expect("stale status read"),
            "same tick with stale generation has no installed authority"
        );
    }

    #[test]
    fn qualification_new_choices_pass_through_real_handler_and_readback() {
        for (name, expected) in [
            ("choose_inquiry_work_lost", json!({"inquiry":"work_lost"})),
            (
                "choose_inquiry_maintenance_received",
                json!({"inquiry":"maintenance_received"}),
            ),
            ("choose_reinforce", json!("reinforce")),
            ("choose_hold", json!("hold")),
        ] {
            let (client, session) = super::super::tests::ready();
            let mut app = App::new();
            app.add_plugins((
                MinimalPlugins,
                crate::test_support::HeadlessVisibilityPlugin,
            ))
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
            .insert_resource(session)
            .insert_resource(client)
            .insert_resource(PrimaryView::Organizer)
            .insert_resource(ObserverUiState {
                menu_open: false,
                splash_visible: false,
                ..default()
            })
            .insert_resource(
                CountyAtlas::parse(include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../assets/map/county_atlas.bin"
                )))
                .expect("fixture atlas parses"),
            )
            .insert_resource(SelectedCounty(Some(0)))
            .init_resource::<InputFocus>()
            .init_resource::<ButtonInput<KeyCode>>()
            .init_resource::<ObserverKeyboardClaim>()
            .init_resource::<OpeningPresentation>()
            .add_message::<ObserverCommand>()
            .add_message::<ContinueWarning>();
            ui::install(&mut app);
            let (socket, _peer) = UnixStream::pair().expect("fixture sockets");
            let (incoming, receiver) = mpsc::channel();
            let (outgoing, _output) = mpsc::sync_channel(1);
            install(
                &mut app,
                Transport {
                    incoming: Mutex::new(receiver),
                    outgoing,
                    socket,
                    capture_dir: None,
                },
            );
            app.update();
            app.world_mut()
                .write_message(OrganizerAction::Inspect(OrganizerInspector::Practices));
            app.update();
            assert_eq!(
                app.world().resource::<OrganizerClient>().inspector,
                OrganizerInspector::Practices
            );
            let mut input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                Action::Status,
            )
            .input;
            input.action = serde_json::from_value(json!(name)).expect("private action decodes");
            incoming
                .send(Incoming::Input(input))
                .expect("fixture receiver stays open");
            app.update();
            let reply: Value = serde_json::from_slice(
                app.world()
                    .resource::<Controls>()
                    .reply
                    .as_ref()
                    .expect("handler yields a response"),
            )
            .expect("response is JSON");
            assert_eq!(reply["event"], "applied", "{name}: {reply}");
            assert_eq!(reply["state"]["choice"], expected, "{name}: {reply}");
        }
    }

    #[test]
    #[allow(
        clippy::too_many_lines,
        reason = "`qualification_opening_controls_wait_for_real_handlers_before_long_frame_progress` keeps one authored boundary's fixture and assertions together"
    )]
    fn qualification_opening_controls_wait_for_real_handlers_before_long_frame_progress() {
        // Either plugin order must acknowledge the ordinary handler's exact
        // result, including when the same frame advances Production to Title.
        for adapter_first in [false, true] {
            let (mut app, requests, _responses) = crate::observer_io::tests::quit_app();
            let (client, mut session) = super::super::tests::ready();
            session.foundation_digest = Some("admitted".into());
            app.add_plugins((
                MinimalPlugins,
                crate::test_support::HeadlessVisibilityPlugin,
            ))
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
            let (socket, _peer) = UnixStream::pair()
                .expect("the fixture call `pair` succeeds for the authored inputs");
            let (incoming, receiver) = mpsc::channel();
            let (outgoing, output) = mpsc::sync_channel(1);
            let transport = Transport {
                incoming: Mutex::new(receiver),
                outgoing,
                socket,
                capture_dir: None,
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
            incoming
                .send(Incoming::Input(input))
                .expect("the receiver stays alive for the send");
            app.update();
            let reply: Value = serde_json::from_slice(
                app.world()
                    .resource::<Controls>()
                    .reply
                    .as_ref()
                    .expect("the fixture set the optional field before this read"),
            )
            .expect("the authored bytes match the declared schema");
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
            output
                .try_recv()
                .expect("the producer sends before this receive");
            let mut input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                Action::ContinueTitle,
            )
            .input;
            input.sequence = 2;
            incoming
                .send(Incoming::Input(input))
                .expect("the receiver stays alive for the send");
            app.update();
            let reply: Value = serde_json::from_slice(
                app.world()
                    .resource::<Controls>()
                    .reply
                    .as_ref()
                    .expect("the fixture set the optional field before this read"),
            )
            .expect("the authored bytes match the declared schema");
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
        let command = client
            .make_command(&session, client.choice())
            .expect("the fixture command builds");
        client.queue(&mut session, RequestKind::Preview, Some(command.clone()));
        receipt.organizer_finished(id, true, &client);
        let request_id = client
            .pending
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .id;
        client
            .previewed(
                request_id,
                babylon_persistence::runtime_session::OrganizerPreview {
                    allocation: OrganizerAllocation::None,
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
            .expect("the fixture call `previewed` succeeds for the authored inputs");
        assert!(client.pending.is_none());
        capture_handler(
            &mut pending,
            receipt
                .handled
                .take()
                .expect("the fixture call `take` succeeds for the authored inputs")
                .expect("the nested fixture result is present"),
        )
        .expect("the fixture captures the authored state");
        assert_eq!(pending.request, Some(request_id));
        assert_eq!(pending.reviewed, client.reviewed_command);
        assert_eq!(pending.reviewed.as_ref(), Some(&command));
    }

    #[test]
    fn qualification_review_refuses_a_competing_choice() {
        let (mut client, mut session) = super::super::tests::ready();
        let mut pending = pending(&session, &client, Action::Review);
        client
            .draft
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .choice = OrganizerChoice::Reinforce;
        let command = client
            .make_command(&session, client.choice())
            .expect("the fixture command builds");
        client.queue(&mut session, RequestKind::Preview, Some(command.clone()));
        let request = client
            .pending
            .as_ref()
            .expect("the fixture set the optional field before this read");
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
            requests
                .try_recv()
                .expect("the producer sends before this receive"),
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
        let command = client
            .make_command(&session, client.choice())
            .expect("the fixture command builds");
        client.reviewed_command = Some(command.clone());
        let mut original = pending(&session, &client, Action::Confirm);
        client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
        let id = client
            .pending
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .id;
        capture_handler(
            &mut original,
            Witness::Organizer {
                id,
                kind: RequestKind::Submit,
                command: Some(command.clone()),
            },
        )
        .expect("the fixture captures the authored state");
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
            .expect("the fixture call `accepted` succeeds for the authored inputs");
        client.require_status(&mut session);
        assert!(session.begin_advance().is_none());
        client.queue(&mut session, RequestKind::Status, None);
        let status_id = client
            .pending
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .id;
        let fresh = babylon_persistence::runtime_session::OrganizerSnapshot {
            body: OrganizerBodyDisclosure::Unavailable,
            body_scope: super::super::tests::body_scope(),
            view: client.view.clone().expect("the fixture value clones"),
            pending: client.commitment.clone(),
            duration: session
                .duration
                .expect("the fixture session records its duration"),
            aid: client.aid.clone(),
            pending_aid: client.pending_aid.clone(),
            aid_resolutions: client.aid_resolutions.clone(),
            city_pd_encounters: client.city_pd_encounters.clone(),
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
                    .expect("the fixture command reports its status");
            });
        app.update();
        assert_eq!(
            app.world().resource::<Verdict>().0,
            Some(Ok("acceptance_admitted"))
        );
        assert_eq!(app.world().resource::<ObserverSession>().durable_tick, 3);
    }

    fn frame(extra: &str) -> Vec<u8> {
        format!("{{\"version\":5,\"sequence\":1,\"campaign_id\":\"00000000-0000-0000-0000-000000000342\",\"scope_epoch\":null,\"expected_tick\":0,\"expected_generation\":0,\"action\":\"status\"{extra}}}\n").into_bytes()
    }

    #[test]
    fn capture_startup_refuses_wrong_identity_old_frames_and_corruption() {
        let campaign = "00000000-0000-0000-0000-000000000001";
        let valid = format!(
            "{{\"version\":5,\"campaign_id\":\"{campaign}\",\"phase\":\"capture_ready\"}}\n"
        );
        for bytes in [
            valid.replace("\"version\":5", "\"version\":1").into_bytes(),
            valid
                .replace(campaign, "00000000-0000-0000-0000-000000000002")
                .into_bytes(),
            valid.replace("capture_ready", "unknown").into_bytes(),
            valid
                .replace("\"phase\":", "\"unused\":true,\"phase\":")
                .into_bytes(),
            valid
                .replace("\"phase\":", "\"version\":5,\"phase\":")
                .into_bytes(),
            frame(""),
            valid.trim_end().as_bytes().to_vec(),
            vec![
                b'x';
                usize::try_from(INPUT_BYTES + 1).expect("the fixture value fits the target range")
            ],
        ] {
            let (socket, mut peer) = UnixStream::pair()
                .expect("the fixture call `pair` succeeds for the authored inputs");
            let worker = thread::spawn(move || Transport::from_stream(socket, campaign));
            peer.write_all(&bytes)
                .expect("the fixture sink accepts the authored bytes");
            peer.shutdown(Shutdown::Write)
                .expect("the fixture call `shutdown` succeeds for the authored inputs");
            let refusal = worker
                .join()
                .expect("the fixture worker finishes without panic")
                .err()
                .expect("invalid startup must refuse");
            assert!(refusal.contains("capture_startup"));
        }
    }

    #[test]
    fn qualification_frames_reject_ambiguous_or_unbounded_input() {
        for bytes in [
            String::from_utf8(frame(""))
                .expect("the fixture bytes came from a UTF-8 string")
                .replace("\"version\":5", "\"version\":1")
                .into_bytes(),
            frame(",\"sequence\":2"),
            frame(",\"unused\":true"),
            String::from_utf8(frame(""))
                .expect("the fixture bytes came from a UTF-8 string")
                .replace("\"scope_epoch\":null,", "")
                .into_bytes(),
            frame("").into_iter().take_while(|b| *b != b'\n').collect(),
            vec![
                b'x';
                usize::try_from(INPUT_BYTES + 2).expect("the fixture value fits the target range")
            ],
        ] {
            assert!(read_input(&mut Cursor::new(bytes)).is_err());
        }
        let mut input = Cursor::new(frame(""));
        assert_eq!(
            read_input(&mut input)
                .expect("the fixture source is readable")
                .expect("the nested fixture result is present")
                .action,
            Action::Status
        );
        assert!(read_input(&mut input)
            .expect("the fixture source is readable")
            .is_none());
    }

    #[test]
    fn qualification_preconditions_bind_campaign_scope_age_and_generation() {
        let session = ObserverSession::new(CampaignId::from_uuid(Uuid::from_u128(0x342)));
        let mut input = read_input(&mut Cursor::new(frame("")))
            .expect("the fixture source is readable")
            .expect("the nested fixture result is present");
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
    #[test]
    fn pause_alone_accepts_a_raced_installed_period_in_the_same_scope() {
        let mut session = ObserverSession::new(CampaignId::from_uuid(Uuid::from_u128(0x342)));
        session.connected_fixture();
        session.phase = SessionPhase::Ready;
        let client = OrganizerClient::default();
        let mut input = pending(&session, &client, Action::Pause).input;
        session.durable_tick = 1;
        session.viewed_tick = 1;
        session.generation += 1;
        assert!(
            precondition(&input, &session),
            "Pause cancels scheduling across an atomic install"
        );
        input.action = Action::Play;
        assert!(!precondition(&input, &session));
        input.action = Action::Pause;
        input.expected_tick = session.durable_tick + 1;
        assert!(!precondition(&input, &session));
        input.expected_tick = session.durable_tick;
        input.expected_generation = session.generation + 1;
        assert!(!precondition(&input, &session));
        input.expected_generation = session.generation;
        input.campaign_id = Uuid::from_u128(0x343).to_string();
        assert!(!precondition(&input, &session));
        input.campaign_id = session.campaign.as_uuid().to_string();
        input.scope_epoch = Some(input.scope_epoch.expect("connected") + 1);
        assert!(!precondition(&input, &session));
    }
    #[test]
    fn stale_scope_and_failed_playback_enqueue_do_not_claim_a_pause() {
        let (mut app, requests, _child) = crate::observer_io::tests::quit_app();
        crate::observer_io::tests::install_playback(&mut app);
        app.world_mut().resource_mut::<ObserverUiState>().menu_open = false;
        app.init_resource::<OrganizerClient>()
            .init_resource::<PrimaryView>()
            .add_message::<OrganizerAction>();
        let (_peer, inputs, _outputs) = amount_control_transport(&mut app, 4);
        app.world_mut()
            .resource_mut::<Time>()
            .advance_by(Duration::from_secs(5));
        let send = |app: &mut App, sequence, action: Action, stale: bool| {
            let mut input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                action,
            )
            .input;
            input.sequence = sequence;
            if stale {
                input.scope_epoch = input.scope_epoch.and_then(|epoch| epoch.checked_add(1));
            }
            inputs
                .send(Incoming::Input(input))
                .expect("control transport");
            app.update();
            let raw = app
                .world_mut()
                .resource_mut::<Controls>()
                .reply
                .take()
                .expect("acknowledgement");
            serde_json::from_slice::<Value>(&raw).expect("actual producer frame")
        };
        assert_eq!(
            send(&mut app, 1, Action::ArmOnePlayAdvance, true)["event"],
            "refused"
        );
        let armed = send(&mut app, 2, Action::ArmOnePlayAdvance, false);
        assert_eq!(armed["event"], "applied");
        assert_eq!(
            send(&mut app, 3, Action::ArmOnePlayAdvance, false)["event"],
            "refused"
        );
        assert_eq!(send(&mut app, 4, Action::Play, true)["event"], "refused");
        drop(requests);
        let failed = send(&mut app, 5, Action::Play, false);
        assert_eq!(failed["event"], "refused");
        assert_eq!(failed["state"]["phase"], "Failed");
        assert_eq!(
            failed["state"]["play_interlock"],
            armed["state"]["play_interlock"]
        );
    }

    fn issue_playback_input(app: &mut App, inputs: &Sender<Incoming>, sequence: u64, action: &str) {
        let s = app.world().resource::<ObserverSession>();
        let line = format!(
            "{}\n",
            json!({
                "version":5,"sequence":sequence,"action":action,
                "campaign_id":s.campaign.as_uuid().to_string(),
                "scope_epoch":s.runtime_scope().map(|scope|scope.epoch),
                "expected_tick":s.durable_tick,"expected_generation":s.generation
            })
        );
        let input = read_input(&mut line.as_bytes())
            .expect("current control codec")
            .expect("input");
        inputs
            .send(Incoming::Input(input))
            .expect("control transport");
        app.update();
    }

    fn install_playback_response(
        app: &mut App,
        responses: &Sender<Result<RuntimeSessionResponse, String>>,
        request: u64,
        tick: u64,
    ) {
        let scope = app
            .world()
            .resource::<ObserverSession>()
            .runtime_scope()
            .expect("installed")
            .clone();
        responses
            .send(Ok(RuntimeSessionResponse::Committed {
                scope: scope.clone(),
                request_id: request,
                tail: RuntimeSessionTail {
                    resolve_tick: tick,
                    tick_content_hash: Some(format!("{tick:064x}")),
                    world_hash: Some(format!("{:064x}", tick + 16)),
                },
            }))
            .expect("ordinary child response channel");
        responses
            .send(Ok(RuntimeSessionResponse::ArchiveProgress {
                request_id: None,
                scope,
                durable_tick: tick,
                verified_tick: tick,
            }))
            .expect("ordinary Archive completion");
        app.update();
        let mut s = app.world_mut().resource_mut::<ObserverSession>();
        assert_eq!(s.durable_tick, tick);
        let context = s.context();
        assert!(s.installed(&context));
    }

    #[derive(Clone, Copy, PartialEq, Eq)]
    enum PlayAck {
        Immediate,
        Unread,
        Backpressured,
    }

    impl PlayAck {
        fn read(self, outputs: &Receiver<Vec<u8>>) -> Value {
            let raw = outputs
                .try_recv()
                .expect("response delivered through ordinary outgoing queue");
            if self == Self::Immediate {
                println!(
                    "Qualification interlock {}",
                    std::str::from_utf8(&raw).expect("actual frame").trim_end()
                );
            }
            serde_json::from_slice::<Value>(&raw).expect("actual frame")
        }
    }

    fn enqueued_play(play: &Value, first: u64) -> &Value {
        assert_eq!(play["sequence"], 2);
        assert_eq!(play["event"], "applied");
        let frozen = &play["state"]["play_interlock"];
        assert_eq!(frozen["arm_sequence"], 1);
        assert_eq!(frozen["play_sequence"], 2);
        assert_eq!(frozen["request_id"], first);
        assert_eq!(frozen["phase"], "paused_after_enqueue");
        assert_eq!(frozen["pending_at_pause"], true);
        assert_eq!(frozen["playing_after_pause"], false);
        frozen
    }

    fn prepare_playback_at_eight(app: &mut App) {
        crate::observer_io::tests::install_playback(app);
        app.world_mut().resource_mut::<ObserverUiState>().menu_open = false;
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.ready(8, Some(format!("{:064x}", 8)));
            session.foundation_digest = Some("ac".repeat(32));
            session.world_hash = Some(format!("{:064x}", 24));
            session.archive_verified_tick = 8;
            let context = session.context();
            assert!(session.installed(&context));
        }
        app.init_resource::<OrganizerClient>()
            .init_resource::<PrimaryView>()
            .add_message::<OrganizerAction>();
    }

    #[test]
    fn invalidated_private_play_refuses_before_two_user_toggles_can_be_undone() {
        let (mut app, requests, _responses) = crate::observer_io::tests::quit_app();
        prepare_playback_at_eight(&mut app);
        let (_peer, inputs, _outputs) = amount_control_transport(&mut app, 4);
        app.world_mut()
            .resource_mut::<Time>()
            .advance_by(Duration::from_secs(10));
        issue_playback_input(&mut app, &inputs, 1, "arm_one_play_advance");
        app.world_mut().write_message(ObserverCommand::TogglePlay);
        app.world_mut().write_message(ObserverCommand::TogglePlay);
        issue_playback_input(&mut app, &inputs, 2, "play");
        let reply = app
            .world()
            .resource::<Controls>()
            .reply
            .as_ref()
            .expect("tracked Play ack");
        let result: Value = serde_json::from_slice(reply).expect("ordinary handler response");
        assert_eq!(result["reason"], "ordinary_handler_refused");
        assert_eq!(result["event"], "refused");
        assert!(result["state"]["play_interlock"].is_null());
        for _ in 0..5 {
            app.update();
        }
        assert!(!app.world().resource::<ObserverSession>().playing);
        assert!(
            requests.try_recv().is_err(),
            "rejected private Play scheduled a request"
        );
        app.world_mut().write_message(ObserverCommand::TogglePlay);
        app.update();
        assert!(app.world().resource::<ObserverSession>().playing);
        assert!(
            requests.try_recv().is_ok(),
            "the next untracked user Play remains usable"
        );
    }

    #[test]
    fn qualification_play_stops_on_its_own_enqueued_request_before_delayed_acknowledgment() {
        use babylon_persistence::runtime_session::RuntimeSessionRequest;
        for timing in [PlayAck::Immediate, PlayAck::Unread, PlayAck::Backpressured] {
            let (mut app, requests, responses) = crate::observer_io::tests::quit_app();
            prepare_playback_at_eight(&mut app);
            let (_peer, inputs, outputs) = amount_control_transport(&mut app, 1);
            app.world_mut()
                .resource_mut::<Time>()
                .advance_by(Duration::from_secs(10));
            let ack = || timing.read(&outputs);
            issue_playback_input(&mut app, &inputs, 1, "arm_one_play_advance");
            issue_playback_input(&mut app, &inputs, 2, "play");
            let RuntimeSessionRequest::Advance {
                request_id: first,
                expected_tail,
                ..
            } = requests.try_recv().expect("P9 enqueue")
            else {
                panic!("advance")
            };
            assert_eq!(expected_tail.resolve_tick, 8);
            let check_arm = || {
                let arm = ack();
                assert_eq!(arm["sequence"], 1);
                assert_eq!(arm["state"]["play_interlock"]["phase"], "armed");
            };
            if timing != PlayAck::Backpressured {
                check_arm();
            }
            app.update();
            assert_eq!(
                app.world().resource::<Controls>().reply.is_some(),
                timing == PlayAck::Backpressured
            );
            let immediate = (timing == PlayAck::Immediate).then(ack);
            if timing != PlayAck::Immediate {
                for _ in 0..5 {
                    app.update();
                }
            }
            install_playback_response(&mut app, &responses, first, 9);
            for _ in 0..5 {
                app.update();
            }
            assert!(
                requests.try_recv().is_err(),
                "no further request while acknowledgment is unread"
            );
            if timing == PlayAck::Backpressured {
                assert!(app.world().resource::<Controls>().reply.is_some());
                check_arm();
                app.update();
            }
            let play = immediate.unwrap_or_else(ack);
            let frozen = enqueued_play(&play, first);
            issue_playback_input(&mut app, &inputs, 3, "pause");
            app.update();
            assert_eq!(ack()["state"]["play_interlock"], *frozen);
            issue_playback_input(&mut app, &inputs, 4, "step");
            let RuntimeSessionRequest::Advance {
                request_id: second,
                expected_tail,
                ..
            } = requests.try_recv().expect("P10 enqueue")
            else {
                panic!("advance")
            };
            assert_ne!(first, second);
            assert_eq!(expected_tail.resolve_tick, 9);
            install_playback_response(&mut app, &responses, second, 10);
            app.update();
            app.update();
            let step = ack();
            assert_eq!(step["event"], "committed_and_installed");
            assert_eq!(step["state"]["play_interlock"], *frozen);
            for _ in 0..5 {
                app.update();
            }
            assert!(requests.try_recv().is_err(), "no P11");
            assert_eq!(
                app.world().resource::<ObserverSession>().phase,
                SessionPhase::Ready
            );
            issue_playback_input(&mut app, &inputs, 5, "arm_one_play_advance");
            app.update();
            assert_eq!(ack()["event"], "refused");
            issue_playback_input(&mut app, &inputs, 6, "play");
            app.update();
            assert_eq!(ack()["event"], "refused");
            assert!(
                requests.try_recv().is_err(),
                "consumed private Play cannot issue P11"
            );
        }
    }

    #[test]
    fn playback_controls_use_ordinary_idempotent_handlers_during_pending_install() {
        let (mut app, requests) = crate::observer_io::tests::command_app();
        app.world_mut().resource_mut::<ObserverUiState>().menu_open = false;
        app.init_resource::<OrganizerClient>()
            .init_resource::<OpeningPresentation>()
            .init_resource::<PrimaryView>()
            .add_message::<OrganizerAction>()
            .add_message::<ContinueWarning>()
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
        let (socket, _peer) = UnixStream::pair().expect("fixture socket");
        let (incoming, receiver) = mpsc::channel();
        let (outgoing, _output) = mpsc::sync_channel(1);
        install(
            &mut app,
            Transport {
                incoming: Mutex::new(receiver),
                outgoing,
                socket,
                capture_dir: None,
            },
        );
        for (index, action) in [Action::Play, Action::Play, Action::Pause, Action::Pause]
            .into_iter()
            .enumerate()
        {
            let mut input = pending(
                app.world().resource::<ObserverSession>(),
                app.world().resource::<OrganizerClient>(),
                action,
            )
            .input;
            input.sequence = u64::try_from(index).expect("bounded") + 1;
            if index == 2 {
                let mut session = app.world_mut().resource_mut::<ObserverSession>();
                assert!(session.begin_advance().is_some());
                session.generation += 1;
            }
            incoming.send(Incoming::Input(input)).expect("receiver");
            app.update();
            let reply: Value = serde_json::from_slice(
                &app.world_mut()
                    .resource_mut::<Controls>()
                    .reply
                    .take()
                    .expect("ordinary handler reply"),
            )
            .expect("JSON");
            assert_eq!(reply["event"], "applied", "{index}: {reply}");
            assert_eq!(app.world().resource::<ObserverSession>().playing, index < 2);
        }
        assert!(
            app.world().resource::<ObserverSession>().advance_pending(),
            "Pause does not cancel the atomic period"
        );
        assert!(
            requests.try_recv().is_err(),
            "scheduling ACKs do not credit a runtime commit"
        );
    }

    #[test]
    fn disclosed_inquiry_control_selects_exact_dated_report_and_keeps_draft() {
        use babylon_persistence::runtime_session::{OrganizerObservation, OrganizerReport};
        let (mut app, _, draft) = ui::tests::dossier_navigation_fixture();
        app.init_resource::<OpeningPresentation>()
            .add_message::<ContinueWarning>();
        {
            let campaign = *app.world().resource::<ObserverSession>().campaign.as_uuid();
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.durable_tick = 3;
            session.viewed_tick = 3;
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.campaign = Some(campaign);
            let view = client.view.as_mut().expect("view");
            view.period = 3;
            let report = OrganizerObservation {
                observation_id: [31; 32],
                actor_id: view.actor_id,
                subject_id: view.workplace_id,
                source_actor_id: view.workplace_partner_id,
                observed_period: 2,
                acquired_period: 3,
                receipt_id: Some([7; 32]),
                report: OrganizerReport::Work {
                    performed_labor_hours: 123,
                    output_kg: 456,
                    previous_labor_hours: None,
                    previous_output_kg: None,
                },
            };
            view.observations = vec![
                report.clone(),
                OrganizerObservation {
                    observation_id: [32; 32],
                    receipt_id: None,
                    ..report
                },
            ];
            view.total_observation_count = 2;
        }
        let (socket, _peer) = UnixStream::pair().expect("socket");
        let (incoming, receiver) = mpsc::channel();
        let (outgoing, _output) = mpsc::sync_channel(1);
        install(
            &mut app,
            Transport {
                incoming: Mutex::new(receiver),
                outgoing,
                socket,
                capture_dir: None,
            },
        );
        let input = pending(
            app.world().resource::<ObserverSession>(),
            app.world().resource::<OrganizerClient>(),
            Action::ReadInquiryReport,
        )
        .input;
        incoming.send(Incoming::Input(input)).expect("receiver");
        app.update();
        let reply: Value = serde_json::from_slice(
            app.world()
                .resource::<Controls>()
                .reply
                .as_ref()
                .expect("reply"),
        )
        .expect("JSON");
        assert_eq!(reply["event"], "applied", "{reply}");
        assert_eq!(reply["state"]["selected_report_id"], "1f".repeat(32));
        assert_eq!(reply["state"]["selected_report_observed_period"], 2);
        assert_eq!(reply["state"]["selected_report_acquired_period"], 3);
        assert_eq!(ui::tests::draft_debug(&app), draft);
    }
    #[test]
    fn organizer_shell_evidence_opens_real_report_and_preserves_subject_and_draft() {
        use babylon_persistence::runtime_session::{OrganizerObservation, OrganizerReport};
        let (mut app, _, draft) = ui::tests::dossier_navigation_fixture();
        app.init_resource::<OpeningPresentation>()
            .init_resource::<ObserverFrame>()
            .init_resource::<ProductionNavigation>()
            .init_resource::<ObserverFeedback>()
            .add_message::<ContinueWarning>()
            .add_systems(
                Update,
                crate::production::navigation::navigate
                    .after(ObserverSet::Install)
                    .before(ObserverSet::Paint),
            );
        let (_runtime_requests, _runtime_responses) =
            crate::observer_io::tests::install_pending_command_fixture(&mut app);
        *app.world_mut().resource_mut::<PrimaryView>() = PrimaryView::Map;
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            let view = client.view.as_mut().expect("view");
            view.observations = vec![OrganizerObservation {
                observation_id: [31; 32],
                actor_id: view.actor_id,
                subject_id: view.workplace_id,
                source_actor_id: view.workplace_partner_id,
                observed_period: 0,
                acquired_period: 0,
                receipt_id: None,
                report: OrganizerReport::Work {
                    performed_labor_hours: 123,
                    output_kg: 456,
                    previous_labor_hours: None,
                    previous_output_kg: None,
                },
            }];
            view.total_observation_count = 1;
            client.selected_subject = Some(OrganizerSubject::WorkplaceCommittee(
                view.workplace_partner_id,
            ));
        }
        let subject = app.world().resource::<OrganizerClient>().selected_subject;
        let (socket, _peer) = UnixStream::pair().expect("socket");
        let (incoming, receiver) = mpsc::channel();
        let (outgoing, _output) = mpsc::sync_channel(1);
        install(
            &mut app,
            Transport {
                incoming: Mutex::new(receiver),
                outgoing,
                socket,
                capture_dir: None,
            },
        );
        let action = Action::Circuit;
        let input = pending(
            app.world().resource::<ObserverSession>(),
            app.world().resource::<OrganizerClient>(),
            action,
        )
        .input;
        incoming.send(Incoming::Input(input)).expect("receiver");
        app.update();
        let reply: Value = serde_json::from_slice(
            app.world()
                .resource::<Controls>()
                .reply
                .as_ref()
                .expect("reply"),
        )
        .expect("JSON");
        assert_eq!(reply["event"], "applied", "{reply}");
        assert_eq!(
            *app.world().resource::<PrimaryView>(),
            PrimaryView::Organizer
        );
        assert_eq!(
            app.world().resource::<OrganizerClient>().inspector,
            OrganizerInspector::Evidence
        );
        assert_eq!(reply["state"]["selected_report_id"], "1f".repeat(32));
        assert!(
            !app.world().resource::<ObserverUiState>().evidence_open,
            "readable Evidence is not verification settings"
        );
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            subject
        );
        app.world_mut()
            .write_message(OrganizerAction::CloseInspector);
        app.update();
        assert_eq!(
            app.world().resource::<OrganizerClient>().inspector,
            OrganizerInspector::Closed
        );
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            subject
        );
        assert_eq!(ui::tests::draft_debug(&app), draft);
    }
}
