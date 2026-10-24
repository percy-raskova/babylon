//! Actual current `NationalWorld` protocol consumer in the one owned measurement game.
use super::{NativeRunTiming, NativeTimingEvidence, NativeTimingSample};
use crate::elapsed_ns;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::runtime_session::{
    OrganizerAidKind, OrganizerAidSupportStatus, OrganizerAidTransportPreview, OrganizerChoice,
    OrganizerCommand, OrganizerCommitment, OrganizerGiftConsent, OrganizerPreview,
    OrganizerSnapshot, RuntimeAdvanceStage, RuntimeSessionErrorCode, RuntimeSessionPreset,
    RuntimeSessionRequest, RuntimeSessionResponse, RuntimeSessionScope, RuntimeSessionTail,
    RuntimeSessionTarget, RUNTIME_SESSION_MAX_LINE_BYTES, RUNTIME_SESSION_PROTOCOL_VERSION,
};

use postgres::{Config, NoTls};
use std::fs::OpenOptions;
use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::net::UnixStream;
use std::path::PathBuf;
use std::thread;
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

#[path = "national_boundary_evidence.rs"]
mod national_boundary_evidence;

use babylon_persistence::observer_reader::CommittedMaterialObservation;
use babylon_persistence::observer_reader::ObserverEconomyReader;
use babylon_persistence::observer_reader::ObserverMaterialCursor;
use babylon_persistence::observer_reader::ObserverVisibility;
use babylon_persistence::qualification_audit::{
    aid as national_aid_accounting, economic as national_economic_accounting,
    production_renewal as national_production_renewal, trade as national_trade_accounting,
};
use babylon_persistence::runtime_session;
use babylon_persistence::runtime_session::OrganizerAidPending;
use babylon_persistence::runtime_session::OrganizerAidResolution;
use babylon_persistence::runtime_session::OrganizerMaterialAidPreview;
use national_aid_accounting::Accepted;
use national_boundary_evidence::Limits;
use serde_json::Value;
use std::fs::File;
use uuid::Uuid;

fn accounting_reader() -> ObserverEconomyReader {
    let config: Config = std::env::var("BABYLON_NATIONAL_STORAGE_OBSERVER_DSN")
        .expect("the fixture variable is bound")
        .parse()
        .expect("the authored literal parses as the declared type");
    ObserverEconomyReader::connect(&config, ObserverVisibility::FullObserver)
        .expect("the test database accepts the connection")
}

#[path = "national_offer_controls.rs"]
mod national_offer_controls;

struct Session {
    input: UnixStream,
    output: BufReader<UnixStream>,
    worker: JoinHandle<Result<(), RuntimeSessionErrorCode>>,
    scope: RuntimeSessionScope,
    tail: RuntimeSessionTail,
    foundation: String,
    next_id: u64,
    archive_verified_tick: u64,
}
impl Session {
    #[allow(
        clippy::too_many_lines,
        reason = "`start` keeps one authored boundary's fixture and assertions together"
    )]
    fn start(config: &Config, campaign: CampaignId, new: bool) -> Self {
        let (local, remote) = UnixStream::pair().expect("bounded local runtime pipe");
        let input = local
            .try_clone()
            .expect("the fixture input satisfies the fallible conversion");
        let source = remote
            .try_clone()
            .expect("the fixture input satisfies the fallible conversion");
        let config = config.clone();
        let defines = PathBuf::from("/dev/null");
        let worker = thread::spawn(move || {
            let mut output = remote;
            runtime_session::run_runtime_session(
                &config,
                &defines,
                BufReader::new(source),
                &mut output,
            )
        });
        let mut session = Self {
            input,
            output: BufReader::new(local),
            worker,
            scope: RuntimeSessionScope::default(),
            tail: RuntimeSessionTail {
                resolve_tick: 0,
                tick_content_hash: None,
            },
            foundation: String::new(),
            next_id: 1,
            archive_verified_tick: 0,
        };
        let RuntimeSessionResponse::Hello {
            protocol_version,
            scope,
        } = session.read()
        else {
            panic!("actual session must begin with Hello")
        };
        assert_eq!(protocol_version, RUNTIME_SESSION_PROTOCOL_VERSION);
        assert_eq!(scope, RuntimeSessionScope::default());
        let id = session.id();
        let target = if new {
            RuntimeSessionTarget::New {
                campaign_id: campaign.as_uuid().to_string(),
                preset: RuntimeSessionPreset::NationalWorld,
            }
        } else {
            RuntimeSessionTarget::Open {
                campaign_id: campaign.as_uuid().to_string(),
            }
        };
        session.send(&RuntimeSessionRequest::Switch {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: id,
            scope: session.scope.clone(),
            target,
        });
        let RuntimeSessionResponse::Switching {
            request_id,
            previous_scope,
            scope,
        } = session.reply(id)
        else {
            panic!("actual switch acceptance required")
        };
        assert_eq!(request_id, id);
        assert_eq!(previous_scope, session.scope);
        assert_eq!(
            scope.epoch,
            session
                .scope
                .epoch
                .checked_add(1)
                .expect("the fixture arithmetic stays in range")
        );
        assert_eq!(
            scope.campaign_id.as_deref(),
            Some(campaign.as_uuid().to_string().as_str())
        );
        session.scope = scope;
        let RuntimeSessionResponse::Ready {
            scope,
            foundation_digest,
            tail,
            organizer,
            duration,
            ..
        } = session.reply(id)
        else {
            panic!("actual campaign admission required")
        };
        assert_eq!(scope, session.scope);
        assert!(organizer, "primary national must be playable");
        assert_eq!(
            duration,
            babylon_kernel::clock::CampaignDuration::Continuous
        );
        assert_eq!(foundation_digest.len(), 64);
        session.foundation = foundation_digest;
        session.tail = tail;
        session
    }
    fn id(&mut self) -> u64 {
        let id = self.next_id;
        self.next_id = id
            .checked_add(1)
            .expect("the fixture arithmetic stays in range");
        id
    }
    fn send(&mut self, request: &RuntimeSessionRequest) {
        let bytes =
            serde_json::to_vec(request).expect("the value serializes to canonical JSON bytes");
        assert!(bytes.len() < RUNTIME_SESSION_MAX_LINE_BYTES);
        self.input
            .write_all(&bytes)
            .expect("the fixture sink accepts the authored bytes");
        self.input
            .write_all(b"\n")
            .expect("the fixture sink accepts the authored bytes");
        self.input.flush().expect("the fixture sink flushes");
    }
    fn read(&mut self) -> RuntimeSessionResponse {
        let mut line = String::new();
        let maximum = u64::try_from(RUNTIME_SESSION_MAX_LINE_BYTES)
            .expect("the fixture value fits the target range")
            .checked_add(1)
            .expect("the fixture arithmetic stays in range");
        let count = Read::by_ref(&mut self.output)
            .take(maximum)
            .read_line(&mut line)
            .expect("actual bounded reply");
        assert!(count > 0 && count <= RUNTIME_SESSION_MAX_LINE_BYTES && line.ends_with('\n'));
        serde_json::from_str(&line).expect("exact current protocol reply")
    }
    fn reply(&mut self, id: u64) -> RuntimeSessionResponse {
        self.correlated_reply(id, false)
    }
    fn correlated_reply(&mut self, id: u64, nonce_conflict: bool) -> RuntimeSessionResponse {
        loop {
            let response = self.read();
            if let RuntimeSessionResponse::ArchiveProgress {
                scope,
                durable_tick,
                verified_tick,
                ..
            } = &response
            {
                assert_eq!(scope, &self.scope);
                assert_eq!(*durable_tick, self.tail.resolve_tick);
                assert!(verified_tick <= durable_tick);
                assert!(*verified_tick >= self.archive_verified_tick);
                self.archive_verified_tick = *verified_tick;
                continue;
            }
            if nonce_conflict {
                let RuntimeSessionResponse::Error {
                    request_id,
                    scope,
                    code,
                    tail,
                } = &response
                else {
                    panic!("nonce conflict must refuse: {response:?}")
                };
                assert_eq!(*request_id, Some(id));
                assert_eq!(scope, &self.scope);
                assert_eq!(*code, RuntimeSessionErrorCode::OrganizerNonceConflict);
                assert_eq!(tail.as_ref(), Some(&self.tail));
                return response;
            }
            assert!(
                !matches!(response, RuntimeSessionResponse::Error { .. }),
                "unexpected refusal: {response:?}"
            );
            let request = match &response {
                RuntimeSessionResponse::Switching { request_id, .. }
                | RuntimeSessionResponse::Ready { request_id, .. }
                | RuntimeSessionResponse::OrganizerStatus { request_id, .. }
                | RuntimeSessionResponse::OrganizerPreview { request_id, .. }
                | RuntimeSessionResponse::OrganizerAccepted { request_id, .. }
                | RuntimeSessionResponse::Committed { request_id, .. }
                | RuntimeSessionResponse::AdvanceProgress { request_id, .. }
                | RuntimeSessionResponse::Stopped { request_id, .. } => *request_id,
                _ => panic!("unexpected reply: {response:?}"),
            };
            assert_eq!(request, id);
            return response;
        }
    }
    fn status(&mut self) -> OrganizerSnapshot {
        let id = self.id();
        self.send(&RuntimeSessionRequest::OrganizerStatus {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: id,
            scope: self.scope.clone(),
        });
        let RuntimeSessionResponse::OrganizerStatus {
            scope, snapshot, ..
        } = self.reply(id)
        else {
            panic!("actual organizer projection required")
        };
        assert_eq!(scope, self.scope);
        assert_eq!(snapshot.view.period, self.tail.resolve_tick);
        *snapshot
    }
    fn accept(
        &mut self,
        campaign: CampaignId,
        snapshot: &OrganizerSnapshot,
        choice: OrganizerChoice,
        nonce: u8,
    ) -> (Option<OrganizerCommitment>, OrganizerPreview) {
        let command = OrganizerCommand {
            campaign_id: *campaign.canonical_bytes(),
            actor_id: snapshot.view.actor_id,
            authority_id: snapshot.view.authority_id,
            expected_period: snapshot.view.period,
            content_digest: snapshot.view.content_digest,
            resource_digest: snapshot.view.resource_digest,
            nonce: [nonce; 16],
            choice,
        };
        let id = self.id();
        self.send(&RuntimeSessionRequest::PreviewOrganizer {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: id,
            scope: self.scope.clone(),
            command: command.clone(),
        });
        let RuntimeSessionResponse::OrganizerPreview { scope, preview, .. } = self.reply(id) else {
            panic!("current authenticated preview required")
        };
        assert_eq!(scope, self.scope);
        assert_eq!(preview.choice, choice);
        if preview.refusal.is_some() {
            return (None, preview);
        }
        assert_eq!(
            preview.resolves_period,
            snapshot
                .view
                .period
                .checked_add(1)
                .expect("the fixture arithmetic stays in range")
        );
        let mut accepted = None;
        for _ in 0..2 {
            let id = self.id();
            self.send(&organizer_submission(
                id,
                self.scope.clone(),
                command.clone(),
            ));
            let RuntimeSessionResponse::OrganizerAccepted {
                scope, commitment, ..
            } = self.reply(id)
            else {
                panic!("actual durable acceptance required")
            };
            assert_eq!(scope, self.scope);
            assert_eq!(commitment.command, command);
            assert_eq!(commitment.resolves_period, preview.resolves_period);
            if let Some(prior) = &accepted {
                assert_eq!(&commitment, prior);
            }
            accepted = Some(commitment);
        }
        let accepted = accepted.expect("the fixture audit returns the accepted value");
        self.reject_nonce_conflict(command, &accepted);
        (Some(accepted), preview)
    }
    fn reject_nonce_conflict(
        &mut self,
        mut command: OrganizerCommand,
        accepted: &OrganizerCommitment,
    ) {
        command.choice = nonce_probe_choice(command.choice);
        let id = self.id();
        self.send(&organizer_submission(id, self.scope.clone(), command));
        self.correlated_reply(id, true);
        assert_eq!(self.status().pending.as_ref(), Some(accepted));
    }
    fn advance(&mut self) -> Instant {
        let id = self.id();
        let next = self
            .tail
            .resolve_tick
            .checked_add(1)
            .expect("the fixture arithmetic stays in range");
        self.send(&RuntimeSessionRequest::Advance {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: id,
            scope: self.scope.clone(),
            expected_tail: self.tail.clone(),
        });
        for expected in [
            RuntimeAdvanceStage::PreparingCommitments,
            RuntimeAdvanceStage::ResolvingEconomy,
            RuntimeAdvanceStage::PreparingStorage,
            RuntimeAdvanceStage::SavingPeriod,
        ] {
            let RuntimeSessionResponse::AdvanceProgress {
                scope,
                resolve_tick,
                stage,
                ..
            } = self.reply(id)
            else {
                panic!("actual sequential phase required")
            };
            assert_eq!(scope, self.scope);
            assert_eq!(resolve_tick, next);
            assert_eq!(stage, expected);
        }
        let RuntimeSessionResponse::Committed { scope, tail, .. } = self.reply(id) else {
            panic!("only actual Committed can publish time")
        };
        assert_eq!(scope, self.scope);
        assert_eq!(tail.resolve_tick, next);
        assert!(tail.tick_content_hash.is_some());
        self.tail = tail;
        Instant::now()
    }
    fn await_archive(&mut self, acknowledged: Instant, maximum: Duration) {
        while self.archive_verified_tick != self.tail.resolve_tick {
            let remaining = maximum
                .checked_sub(acknowledged.elapsed())
                .filter(|duration| !duration.is_zero())
                .expect("Archive catch-up exceeded captured development budget");
            self.output
                .get_mut()
                .set_read_timeout(Some(remaining))
                .expect("the fixture connection accepts the timeout");
            match self.read() {
                RuntimeSessionResponse::ArchiveProgress {
                    scope,
                    durable_tick,
                    verified_tick,
                    ..
                } => {
                    assert_eq!(scope, self.scope);
                    assert_eq!(durable_tick, self.tail.resolve_tick);
                    assert!(
                        verified_tick <= durable_tick
                            && verified_tick >= self.archive_verified_tick
                    );
                    self.archive_verified_tick = verified_tick;
                }
                RuntimeSessionResponse::Error { code, .. } => {
                    panic!("actual Archive catch-up refused: {code:?}")
                }
                response => panic!("unexpected response during Archive catch-up: {response:?}"),
            }
        }
        self.output
            .get_mut()
            .set_read_timeout(None)
            .expect("the fixture connection accepts the timeout");
    }
    fn stop(mut self) {
        let id = self.id();
        self.send(&RuntimeSessionRequest::Stop {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: id,
            scope: self.scope.clone(),
        });
        let RuntimeSessionResponse::Stopped { scope, .. } = self.reply(id) else {
            panic!("clean owned session stop required")
        };
        assert_eq!(scope, self.scope);
        drop(self.input);
        drop(self.output);
        assert_eq!(self.worker.join().expect("runtime worker joins"), Ok(()));
    }
}

fn nonce_probe_choice(choice: OrganizerChoice) -> OrganizerChoice {
    match choice {
        OrganizerChoice::RemoteAid => OrganizerChoice::LocalAid,
        OrganizerChoice::LocalAid => OrganizerChoice::RemoteAid,
        OrganizerChoice::PauseStanding => OrganizerChoice::ResumeStanding,
        OrganizerChoice::ResumeStanding => OrganizerChoice::PauseStanding,
        _ => panic!("scheduled organizer command expected"),
    }
}

fn organizer_submission(
    request_id: u64,
    scope: RuntimeSessionScope,
    command: OrganizerCommand,
) -> RuntimeSessionRequest {
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

#[test]
fn standing_pause_nonce_probe_is_a_distinct_valid_control() {
    let choice = nonce_probe_choice(OrganizerChoice::PauseStanding);
    assert_ne!(choice, OrganizerChoice::PauseStanding);
    assert!(matches!(choice, OrganizerChoice::ResumeStanding));
}

#[test]
fn standing_control_submission_retains_exact_command_envelope() {
    let command = OrganizerCommand {
        campaign_id: [1; 16],
        actor_id: 101,
        authority_id: [2; 16],
        expected_period: 1,
        content_digest: [3; 32],
        resource_digest: [4; 32],
        nonce: [5; 16],
        choice: OrganizerChoice::PauseStanding,
    };
    let scope = RuntimeSessionScope {
        epoch: 1,
        campaign_id: Some(Uuid::from_bytes(command.campaign_id).to_string()),
    };
    let request = organizer_submission(17, scope.clone(), command.clone());
    let decoded = serde_json::from_slice::<RuntimeSessionRequest>(
        &serde_json::to_vec(&request).expect("the value serializes to canonical JSON bytes"),
    )
    .expect("the fixture world holds the addressed component");
    let RuntimeSessionRequest::ConfigureOrganizerStanding {
        protocol_version,
        request_id,
        scope: actual_scope,
        command: actual_command,
    } = decoded
    else {
        panic!("standing controls must reach the runtime's configuration port")
    };
    assert_eq!(protocol_version, RUNTIME_SESSION_PROTOCOL_VERSION);
    assert_eq!(request_id, 17);
    assert_eq!(actual_scope, scope);
    assert_eq!(actual_command, command);
}

#[derive(serde::Serialize)]
struct PeriodEvidence {
    period: u64,
    commitment: Option<OrganizerCommitment>,
    preview: OrganizerPreview,
    offered_material: Vec<OrganizerMaterialAidPreview>,
    pending_aid: Vec<OrganizerAidPending>,
    resolutions: Vec<OrganizerAidResolution>,
    positive_consequence: bool,
}
fn identity_rows(config: &Config, campaign: CampaignId) -> Vec<(i64, String, String)> {
    let mut client = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    client.query("SELECT resolve_tick,encode(tick_content_hash,'hex'),encode(envelope_digest,'hex') FROM babylon_state.tick_commit WHERE campaign_id=$1 ORDER BY resolve_tick",&[campaign.as_uuid()]).expect("the seeded rows are readable")
        .iter().map(|r|(r.get(0),r.get(1),r.get(2))).collect()
}
fn verify_offers(snapshot: &OrganizerSnapshot) {
    assert_eq!(snapshot.view.actor_id, 2_616_301);
    assert_eq!(snapshot.aid.len(), 2);
    let kinds = [OrganizerAidKind::Local, OrganizerAidKind::Remote];
    let expected: Vec<_> = kinds
        .into_iter()
        .filter(|kind| !snapshot.pending_aid.iter().any(|row| row.kind == *kind))
        .collect();
    assert_eq!(
        snapshot
            .view
            .aid_options
            .iter()
            .map(|row| row.kind)
            .collect::<Vec<_>>(),
        expected,
        "actionable aid kinds must exclude exactly the already pending kinds"
    );
    assert!(snapshot.pending_aid.len() <= 2);
    for kind in [OrganizerAidKind::Local, OrganizerAidKind::Remote] {
        verify_offer(snapshot, kind);
    }
}

fn verify_offer(snapshot: &OrganizerSnapshot, kind: OrganizerAidKind) {
    assert_eq!(
        snapshot.aid.iter().filter(|row| row.kind == kind).count(),
        1
    );
    let preview = snapshot
        .aid
        .iter()
        .find(|p| p.kind == kind)
        .expect("the fixture holds the searched element");
    let pending: Vec<_> = snapshot
        .pending_aid
        .iter()
        .filter(|row| row.kind == kind)
        .collect();
    assert!(
        pending.len() <= 1,
        "one original commitment per pending kind"
    );
    if let Some(pending) = pending.first() {
        assert_eq!(
            pending.mandate_id, preview.mandate_id,
            "pending mandate must repeat the captured preview mandate"
        );
        assert_eq!(
            (pending.good_id, pending.unit_id),
            (preview.good_id, preview.unit_id),
            "pending goods must repeat the captured preview goods"
        );
        assert_ne!(pending.original_commitment_id, [0; 32]);
        assert!(pending.admitted_period < pending.dispatch_period);
        assert!(pending.dispatch_period <= snapshot.view.period);
        assert_eq!(
            pending.material_commitment_id,
            babylon_material_circuit::aid_commitment_id(
                pending.mandate_id,
                pending.dispatch_period
            )
            .as_bytes()
        );
    }
    let option = snapshot.view.aid_options.iter().find(|p| p.kind == kind);
    assert_ne!(preview.mandate_id, [0; 32]);
    if let Some(option) = option {
        assert_eq!(
            option.partner_actor_id,
            if kind == OrganizerAidKind::Local {
                2_616_302
            } else {
                1_703_101
            }
        );
        assert_eq!(option.receiving_consent, OrganizerGiftConsent::Accept);
        assert_eq!(option.coordination_hours, preview.coordination_hours);
    }
    assert_eq!(preview.receiving_consent, OrganizerGiftConsent::Accept);
    assert_ne!(preview.donor_id, preview.recipient_id);
    assert_eq!(preview.maximum_quantity, 4);
    assert_eq!(preview.gift_cash_per_unit, 100_000);
    match (&preview.transport, kind) {
        (OrganizerAidTransportPreview::Local, OrganizerAidKind::Local) => {}
        (OrganizerAidTransportPreview::Routed { stages, .. }, OrganizerAidKind::Remote) => {
            assert_eq!(stages.len(), 1);
            assert_eq!(stages[0].travel_periods, 1);
            assert_eq!(stages[0].loss_ppm, 0);
            assert_eq!(stages[0].capacities.len(), 5);
        }
        _ => panic!("exact local/remote actual transport required"),
    }
}
fn positive(snapshot: &OrganizerSnapshot, commitment: Option<&OrganizerCommitment>) -> bool {
    let Some(commitment) = commitment else {
        return false;
    };
    snapshot.aid_resolutions.iter().any(|r| {
        if r.pending.original_commitment_id!=commitment.commitment_id {return false;}
        assert_eq!(r.pending.admitted_period,commitment.command.expected_period);
        assert_eq!(r.support.original_commitment_id,commitment.commitment_id);
        matches!(r.support.status,OrganizerAidSupportStatus::Granted {granted_quantity,consumed_quantity}
            if granted_quantity>0 && consumed_quantity>0)
    })
}

fn verify_dispatch(after: &OrganizerSnapshot, commitment: Option<&OrganizerCommitment>) {
    let Some(commitment) = commitment else {
        return;
    };
    assert!(
        after
            .aid_resolutions
            .iter()
            .all(
                |r| r.pending.original_commitment_id != commitment.commitment_id
                    || !matches!(r.support.status, OrganizerAidSupportStatus::Granted { .. })
            ),
        "routed gift cannot be granted at dispatch"
    );
    for pending in &after.pending_aid {
        assert_eq!(pending.original_commitment_id, commitment.commitment_id);
        assert_eq!(pending.admitted_period, 0);
        assert_eq!(pending.dispatch_period, 1);
    }
}

fn snapshot_digest(snapshot: &OrganizerSnapshot) -> String {
    use sha2::{Digest, Sha256};
    use std::fmt::Write as _;
    let bytes = serde_json::to_vec(snapshot).expect("the value serializes to canonical JSON bytes");
    let mut digest = String::with_capacity(64);
    for byte in Sha256::digest(bytes) {
        write!(digest, "{byte:02x}").expect("the in-memory formatter accepts the written text");
    }
    digest
}

fn recover(
    config: &Config,
    campaign: CampaignId,
    session: Session,
    after: &OrganizerSnapshot,
    hashes: &[(i64, String, String)],
) -> (Session, NativeTimingSample) {
    let tail = session.tail.clone();
    let foundation = session.foundation.clone();
    session.stop();
    let started = Instant::now();
    let mut reopened = Session::start(config, campaign, false);
    let timing = NativeTimingSample {
        tick: tail.resolve_tick,
        elapsed_ns: super::elapsed_ns(started.elapsed()),
    };
    assert_eq!(reopened.tail, tail);
    assert_eq!(reopened.foundation, foundation);
    assert_eq!(&reopened.status(), after);
    assert_eq!(identity_rows(config, campaign), hashes);
    super::snapshot(&format!("tick-{:02}-reopened", tail.resolve_tick), campaign);
    (reopened, timing)
}

struct QualificationRun<'a> {
    config: &'a Config,
    campaign: CampaignId,
    started: Instant,
    limits: Limits,
    renewal_seed_tick: u64,
}

struct AccountedBoundary {
    proof: Value,
    roster: Vec<String>,
    world: String,
    production_timing: NativeTimingSample,
}

#[derive(Default)]
struct QualificationAccounting {
    aid: national_aid_accounting::Audit,
    trade: national_trade_accounting::Audit,
    economic: national_economic_accounting::Audit,
    production_renewal: Option<national_production_renewal::Audit>,
    production_renewal_evidence: Option<Value>,
    production_cursor: Option<ObserverMaterialCursor>,
}

impl QualificationAccounting {
    fn capture_aid(
        &mut self,
        before: &OrganizerSnapshot,
        admission: Option<&(Option<OrganizerCommitment>, OrganizerPreview)>,
    ) -> bool {
        let Some((Some(commitment), preview)) = admission else {
            return false;
        };
        if !matches!(
            commitment.command.choice,
            OrganizerChoice::RemoteAid | OrganizerChoice::LocalAid
        ) {
            return false;
        }
        self.aid
            .accept(
                Accepted::capture(commitment, preview, before)
                    .expect("the fixture captures the authored state"),
            )
            .expect("the fixture call `accept` succeeds for the authored inputs");
        true
    }

    fn renewal_fact(
        &mut self,
        observation: &CommittedMaterialObservation,
        seed_tick: u64,
    ) -> Option<Value> {
        let identity = &observation.accounting.identity;
        let tick = identity.resolve_tick();
        if tick < seed_tick {
            return None;
        }
        let register = self
            .production_cursor
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .current_register()
            .expect("the fixture call `current_register` succeeds for the authored inputs");
        assert_eq!(register.completed_tick(), tick);
        assert_eq!(
            babylon_tick::material_world::nominal_material_world_hash(
                identity.graph_world_after(),
                register
            ),
            identity.result_world_hash()
        );
        let evidence = if tick == seed_tick {
            assert!(self.production_renewal.is_none());
            let audit =
                national_production_renewal::Audit::seed(register.state(), tick, register.digest())
                    .expect("renewal seed agrees with authenticated material state");
            let evidence = audit
                .evidence()
                .expect("the fixture call `evidence` succeeds for the authored inputs");
            self.production_renewal = Some(audit);
            evidence
        } else {
            self.production_renewal
                .as_mut()
                .expect("terminal production witness requires its exact committed seed")
                .read(&observation.accounting.receipts)
                .expect("renewal custody bounds agree with authenticated receipts")
        };
        let mut fact = serde_json::to_value(evidence).expect("the value serializes to JSON");
        fact["through_tick_content_hash"] = serde_json::json!(national_boundary_evidence::hex(
            identity.tick_content_hash().as_bytes()
        ));
        fact["canonical_receipt_sha256"] =
            serde_json::json!(national_boundary_evidence::hex(&identity.receipt_digest()));
        self.production_renewal_evidence = Some(fact.clone());
        Some(fact)
    }

    fn economic_fact(&mut self, observation: &CommittedMaterialObservation) -> Value {
        let mut fact = serde_json::to_value(
            self.economic
                .read(&observation.accounting.receipts)
                .expect("independent economic accounting agrees with committed receipts"),
        )
        .expect("the value serializes to JSON");
        let identity = &observation.accounting.identity;
        fact["tick_content_hash"] = serde_json::json!(national_boundary_evidence::hex(
            identity.tick_content_hash().as_bytes()
        ));
        fact["canonical_receipt_sha256"] =
            serde_json::json!(national_boundary_evidence::hex(&identity.receipt_digest()));
        fact
    }
}

impl<'a> QualificationRun<'a> {
    fn authenticated_opening(
        &self,
        session: &Session,
        before: &OrganizerSnapshot,
        accounting: &mut QualificationAccounting,
    ) {
        self.record_organizer_opening(session, before);
        let reader = accounting_reader();
        let opening = reader
            .snapshot_with_cursor(self.campaign, 0, &mut accounting.production_cursor)
            .expect("the fixture snapshot carries its cursor");
        assert_eq!(opening.foundation_digest, session.foundation);
        assert_eq!(opening.resolve_tick, 0);
        let cursor = accounting
            .production_cursor
            .as_ref()
            .expect("the fixture set the optional field before this read");
        cursor
            .with_opening_register(self.campaign, |register| {
                accounting.aid.open(register, before)
            })
            .expect("the fixture builder accepts the authored options")
            .expect("the nested fixture result is present");
    }
    fn start(config: &'a Config, campaign: CampaignId, periods: u64, started: Instant) -> Self {
        let limits = national_boundary_evidence::limits();
        write_progress(
            campaign,
            0,
            "starting",
            started,
            &serde_json::json!({"requested_periods":periods,"policy_sha256":limits.policy_sha256}),
        );
        write_report(
            "national-capture-mode.json",
            &serde_json::json!({"version":1,"mode":"playable-aid",
            "consumer":"runtime_session","preset":"national-world","periods":periods,"campaign":campaign.as_uuid().to_string()}),
        );
        Self {
            config,
            campaign,
            started,
            renewal_seed_tick: periods
                .saturating_sub(limits.economic_renewal_window_ticks)
                .max(1),
            limits,
        }
    }

    fn record_organizer_opening(&self, session: &Session, snapshot: &OrganizerSnapshot) {
        assert_eq!(session.tail.resolve_tick, 0);
        assert_eq!(snapshot.view.period, 0);
        assert!(snapshot.pending.is_none());
        write_report(
            "organizer-opening.json",
            &serde_json::json!({
                "version":1,"source":"runtime_session.organizer_status",
                "campaign":self.campaign.as_uuid().to_string(),
                "foundation_sha256":session.foundation,"policy_sha256":self.limits.policy_sha256,
                "scope":session.scope,"tail":session.tail,"snapshot":snapshot,
            }),
        );
    }

    fn advance(&self, session: &mut Session) -> (Instant, NativeTimingSample) {
        let started = Instant::now();
        let acknowledged = session.advance();
        let tick = session.tail.resolve_tick;
        let timing = NativeTimingSample {
            tick,
            elapsed_ns: super::elapsed_ns(started.elapsed()),
        };
        write_progress(
            self.campaign,
            tick,
            "committed",
            self.started,
            &serde_json::json!({"tail":session.tail,"advance_elapsed_ns":timing.elapsed_ns}),
        );
        (acknowledged, timing)
    }

    fn write_timings(
        &self,
        periods: u64,
        advances: Vec<NativeTimingSample>,
        cold_reopens: Vec<NativeTimingSample>,
        archive_catchups: Vec<NativeTimingSample>,
        production_reads: Vec<NativeTimingSample>,
    ) {
        super::write_native_timings(&NativeTimingEvidence {
            version: 2,
            source: "authoritative_native_instants_v2",
            clock: "monotonic",
            campaign: self.campaign.as_uuid().to_string(),
            advances,
            cold_reopens,
            archive_catchups,
            production_reads,
            run: NativeRunTiming {
                periods,
                elapsed_ns: super::elapsed_ns(self.started.elapsed()),
                compilation_included: false,
            },
        });
    }

    fn authenticated_archive(
        &self,
        session: &mut Session,
        acknowledged: Instant,
    ) -> (Value, NativeTimingSample) {
        let tick = session.tail.resolve_tick;
        session.await_archive(acknowledged, self.limits.archive);
        let archive = national_boundary_evidence::archive_boundary(
            self.config,
            self.campaign,
            tick,
            session
                .tail
                .tick_content_hash
                .as_deref()
                .expect("the fixture set the optional value before this read"),
        );
        let elapsed = acknowledged.elapsed();
        assert!(
            elapsed <= self.limits.archive,
            "authenticated Archive catch-up exceeded captured budget"
        );
        write_progress(self.campaign, tick, "archive", self.started, &archive);
        (
            archive,
            NativeTimingSample {
                tick,
                elapsed_ns: super::elapsed_ns(elapsed),
            },
        )
    }

    #[allow(
        clippy::too_many_lines,
        reason = "`accounted_boundary` keeps one authored boundary's fixture and assertions together"
    )]
    fn accounted_boundary(
        &self,
        session: &Session,
        accounting: &mut QualificationAccounting,
        after: &OrganizerSnapshot,
        archive: &Value,
    ) -> AccountedBoundary {
        let tick = session.tail.resolve_tick;
        let started = Instant::now();
        // Retain authenticated history while releasing the reader's foundation
        // graph/catalogue before recovery and the next Archive reconstruction.
        // The cursor's weak admission owner does not extend that lifetime.
        let observation = {
            let observer = accounting_reader();
            observer
                .committed_material_observation_with_cursor(
                    self.campaign,
                    tick,
                    &mut accounting.production_cursor,
                )
                .expect("the fixture call `committed_material_observation_with_cursor` succeeds for the authored inputs")
        };
        let elapsed = started.elapsed();
        assert!(
            elapsed <= self.limits.production,
            "complete production read exceeded captured budget"
        );
        assert!(
            observation.accounting.material_register_bytes <= self.limits.material_register_bytes,
            "canonical material register exceeded captured byte budget"
        );
        assert!(
            observation.production_evidence.body_bytes()
                <= self.limits.production_evidence_body_bytes,
            "streamed production evidence exceeded captured byte budget"
        );
        let economic = accounting.economic_fact(&observation);
        let production_renewal = accounting.renewal_fact(&observation, self.renewal_seed_tick);
        accounting
            .aid
            .read(
                &observation.accounting,
                accounting
                    .production_cursor
                    .as_ref()
                    .expect("the fixture set the optional field before this read")
                    .current_register()
                    .expect("the fixture call `current_register` succeeds for the authored inputs"),
                after,
            )
            .expect("the fixture reader returns its authored facts");
        let admitted = observation.accounting.identity;
        write_progress(
            self.campaign,
            tick,
            "accounting",
            self.started,
            &serde_json::json!({"canonical_receipt_sha256":national_boundary_evidence::hex(&admitted.receipt_digest())}),
        );
        let (production, roster) = national_boundary_evidence::production_boundary(
            &observation,
            self.campaign,
            tick,
            &session.foundation,
            &admitted,
        );
        let mut trade_fact = accounting
            .trade
            .read(
                &observation.accounting.receipts,
                &observation
                    .snapshot
                    .production
                    .as_ref()
                    .expect("the fixture set the optional field before this read")
                    .sites,
            )
            .expect("independent funded trade accounting agrees with committed receipts");
        trade_fact["tick_content_hash"] = serde_json::json!(session.tail.tick_content_hash);
        trade_fact["canonical_receipt_sha256"] =
            serde_json::json!(national_boundary_evidence::hex(&admitted.receipt_digest()));
        drop(observation);
        write_progress(self.campaign, tick, "production", self.started, &production);
        write_progress(self.campaign, tick, "trade", self.started, &trade_fact);
        let mut proof = national_boundary_evidence::boundary(
            self.config,
            self.campaign,
            tick,
            &session.foundation,
            &admitted,
            archive,
            &production,
        );
        proof["trade"] = trade_fact;
        proof["economic"] = economic.clone();
        write_progress(self.campaign, tick, "economic", self.started, &economic);
        if let Some(renewal) = production_renewal {
            write_progress(
                self.campaign,
                tick,
                "production-renewal",
                self.started,
                &renewal,
            );
        }
        AccountedBoundary {
            proof,
            roster,
            world: national_boundary_evidence::hex(&admitted.result_world_hash()),
            production_timing: NativeTimingSample {
                tick,
                elapsed_ns: super::elapsed_ns(elapsed),
            },
        }
    }
}

fn scheduled_admission(
    session: &mut Session,
    campaign: CampaignId,
    before: &OrganizerSnapshot,
    tick: u64,
) -> Option<(Option<OrganizerCommitment>, OrganizerPreview)> {
    match tick {
        1 => Some(session.accept(campaign, before, OrganizerChoice::RemoteAid, 1)),
        // Reserve the arrival period through a real organizer action.
        // Without a command, ordinary standing work would consume the same
        // finite participant commitment before remote aid.
        2 => Some(session.accept(campaign, before, OrganizerChoice::PauseStanding, 2)),
        3 => Some(session.accept(campaign, before, OrganizerChoice::LocalAid, 3)),
        _ => {
            assert!(before.pending.is_none());
            None
        }
    }
}

pub(super) fn qualify(config: &Config, campaign: CampaignId, periods: u64, run_started: Instant) {
    let run = QualificationRun::start(config, campaign, periods, run_started);
    let mut session = Session::start(config, campaign, true);
    assert_eq!(session.tail.resolve_tick, 0);
    super::snapshot("opening-created", campaign);
    let mut accounting = QualificationAccounting::default();
    let foundation = session.foundation.clone();
    let mut advances = Vec::new();
    let mut cold_reopens = Vec::new();
    let mut archive_catchups = Vec::new();
    let mut production_reads = Vec::new();
    let mut boundaries = Vec::new();
    let mut county_geoids: Option<Vec<String>> = None;
    let mut evidence = Vec::new();
    let mut continuations = Vec::new();
    let mut remote = false;
    let mut local = false;
    for tick in 1..=periods {
        let before = session.status();
        if tick == 1 {
            run.authenticated_opening(&session, &before, &mut accounting);
        }
        verify_offers(&before);
        let admission = scheduled_admission(&mut session, campaign, &before, tick);
        let commitment = admission
            .as_ref()
            .and_then(|(commitment, _)| commitment.as_ref());
        let aid_admission = accounting.capture_aid(&before, admission.as_ref());
        let (acknowledged, timing) = run.advance(&mut session);
        advances.push(timing);
        let (archive, timing) = run.authenticated_archive(&mut session, acknowledged);
        archive_catchups.push(timing);
        let after = session.status();
        assert!(after.pending.is_none());
        if tick == 1 {
            verify_dispatch(&after, commitment);
        }
        let boundary = run.accounted_boundary(&session, &mut accounting, &after, &archive);
        production_reads.push(boundary.production_timing);
        if let Some(expected) = county_geoids.as_ref() {
            assert_eq!(&boundary.roster, expected);
        } else {
            county_geoids = Some(boundary.roster);
        }
        let world = boundary.world;
        boundaries.push(boundary.proof);
        super::snapshot(&format!("tick-{tick:02}"), campaign);
        let hashes = identity_rows(config, campaign);
        assert_eq!(
            hashes.len(),
            usize::try_from(tick).expect("the fixture value fits the target range")
        );
        let (reopened, timing) = recover(config, campaign, session, &after, &hashes);
        session = reopened;
        cold_reopens.push(timing);
        write_progress(
            campaign,
            tick,
            "reopened",
            run_started,
            &serde_json::json!({"tail":session.tail,"foundation_sha256":foundation,"cold_reopen_elapsed_ns":cold_reopens.last().expect("the fixture sequence is non-empty").elapsed_ns}),
        );
        continuations.push(serde_json::json!({"period":tick,"tail":session.tail,
            "organizer_snapshot_sha256":snapshot_digest(&after),"latest_marker":hashes.last(),"nominal_world_hash":world}));
        if let Some((commitment, preview)) = admission.filter(|_| aid_admission) {
            evidence.push(PeriodEvidence {
                period: tick,
                positive_consequence: positive(&after, commitment.as_ref()),
                commitment,
                preview,
                offered_material: before.aid,
                pending_aid: after.pending_aid.clone(),
                resolutions: after.aid_resolutions.clone(),
            });
        }
        remote |= positive(&after, evidence.first().and_then(|e| e.commitment.as_ref()));
        local |= positive(&after, evidence.get(1).and_then(|e| e.commitment.as_ref()));
    }
    session.stop();
    write_report(
        "national-playable-qualification.json",
        &serde_json::json!({"version":6,"capture_mode":"playable-aid","policy_sha256":run.limits.policy_sha256,
        "campaign":campaign.as_uuid().to_string(),"foundation_sha256":foundation,"county_geoids":county_geoids.expect("the fixture value `county_geoids` is present before this read"),"requested_periods":periods,"aid_periods":evidence,"continuations":continuations,"boundaries":boundaries,
        "canonical_protocol_recovery":"passed","positive_aid_consequences":if remote&&local {"passed"} else {"incomplete"},
        "remote_consumed":remote,"local_consumed":local,"independent_finite_aid_practice":accounting.aid.practice_report(),"native_window_evidence":"not_run",
        "independent_account_posting_audit":accounting.aid.report(),"independent_trade_accounting":accounting.trade.report(),"independent_economic_accounting":accounting.economic.summary(),"independent_production_renewal":accounting.production_renewal_evidence}),
    );
    run.write_timings(
        periods,
        advances,
        cold_reopens,
        archive_catchups,
        production_reads,
    );
}

fn write_progress(
    campaign: CampaignId,
    tick: u64,
    stage: &str,
    started: Instant,
    evidence: &Value,
) {
    write_report(
        &format!("progress-{tick:03}-{stage}.json"),
        &serde_json::json!({
            "version":2,"status":"incomplete","campaign":campaign.as_uuid().to_string(),
            "tick":tick,"completed_stage":stage,"elapsed_ns":elapsed_ns(started.elapsed()),"evidence":evidence,
        }),
    );
}

fn write_report(name: &str, report: &Value) {
    let directory = PathBuf::from(
        std::env::var("BABYLON_STORAGE_REPORT_DIRECTORY").expect("the fixture variable is bound"),
    );
    assert!(directory.is_absolute() && directory.is_dir());
    let target = directory.join(name);
    assert!(!target.exists(), "never replace evidence");
    let temporary = directory.join(format!("{name}.partial"));
    let bytes = serde_json::to_vec(report).expect("the value serializes to canonical JSON bytes");
    assert!(
        bytes.len() <= 4_000_000,
        "bounded qualification metadata includes 325 compact accounting boundaries"
    );
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary)
        .expect("the fixture opens the authored source");
    file.write_all(&bytes)
        .expect("the fixture sink accepts the authored bytes");
    file.write_all(b"\n")
        .expect("the fixture sink accepts the authored bytes");
    file.sync_all().expect("the fixture file syncs");
    drop(file);
    std::fs::rename(temporary, target)
        .expect("the fixture call `rename` succeeds for the authored inputs");
    File::open(directory)
        .expect("the fixture opens the authored source")
        .sync_all()
        .expect("the fixture file syncs");
}
