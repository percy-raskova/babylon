//! Actual current `NationalWorld` protocol consumer in the one owned measurement game.
use super::{
    elapsed_ns, snapshot, write_native_timings, NativeRunTiming, NativeTimingEvidence,
    NativeTimingSample,
};
use babylon_persistence::{
    identity::CampaignId,
    runtime_session::{
        run_runtime_session, OrganizerAidKind, OrganizerAidSupportStatus,
        OrganizerAidTransportPreview, OrganizerChoice, OrganizerCommand, OrganizerCommitment,
        OrganizerGiftConsent, OrganizerPreview, OrganizerSnapshot, RuntimeAdvanceStage,
        RuntimeSessionErrorCode, RuntimeSessionPreset, RuntimeSessionRequest,
        RuntimeSessionResponse, RuntimeSessionScope, RuntimeSessionTail, RuntimeSessionTarget,
        RUNTIME_SESSION_MAX_LINE_BYTES, RUNTIME_SESSION_PROTOCOL_VERSION,
    },
};
use postgres::{Config, NoTls};
use std::{
    fs::OpenOptions,
    io::{BufRead, BufReader, Read, Write},
    os::unix::net::UnixStream,
    path::PathBuf,
    thread::{self, JoinHandle},
    time::{Duration, Instant},
};

#[path = "national_aid_accounting.rs"]
mod national_aid_accounting;

#[path = "national_boundary_evidence.rs"]
mod national_boundary_evidence;

#[path = "national_trade_accounting.rs"]
mod national_trade_accounting;

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
    fn start(config: &Config, campaign: CampaignId, new: bool) -> Self {
        let (local, remote) = UnixStream::pair().expect("bounded local runtime pipe");
        let input = local.try_clone().unwrap();
        let source = remote.try_clone().unwrap();
        let config = config.clone();
        let defines = PathBuf::from("/dev/null");
        let worker = thread::spawn(move || {
            let mut output = remote;
            run_runtime_session(&config, &defines, BufReader::new(source), &mut output)
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
        assert_eq!(scope.epoch, session.scope.epoch.checked_add(1).unwrap());
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
        self.next_id = id.checked_add(1).unwrap();
        id
    }
    fn send(&mut self, request: &RuntimeSessionRequest) {
        let bytes = serde_json::to_vec(request).unwrap();
        assert!(bytes.len() < RUNTIME_SESSION_MAX_LINE_BYTES);
        self.input.write_all(&bytes).unwrap();
        self.input.write_all(b"\n").unwrap();
        self.input.flush().unwrap();
    }
    fn read(&mut self) -> RuntimeSessionResponse {
        let mut line = String::new();
        let maximum = u64::try_from(RUNTIME_SESSION_MAX_LINE_BYTES)
            .unwrap()
            .checked_add(1)
            .unwrap();
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
            snapshot.view.period.checked_add(1).unwrap()
        );
        let mut accepted = None;
        for _ in 0..2 {
            let id = self.id();
            self.send(&RuntimeSessionRequest::SubmitOrganizer {
                protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
                request_id: id,
                scope: self.scope.clone(),
                command: command.clone(),
            });
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
        let accepted = accepted.unwrap();
        self.reject_nonce_conflict(command, &accepted);
        (Some(accepted), preview)
    }
    fn reject_nonce_conflict(
        &mut self,
        mut command: OrganizerCommand,
        accepted: &OrganizerCommitment,
    ) {
        command.choice = match command.choice {
            OrganizerChoice::RemoteAid => OrganizerChoice::LocalAid,
            OrganizerChoice::LocalAid => OrganizerChoice::RemoteAid,
            _ => panic!("aid command expected"),
        };
        let id = self.id();
        self.send(&RuntimeSessionRequest::SubmitOrganizer {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: id,
            scope: self.scope.clone(),
            command,
        });
        self.correlated_reply(id, true);
        assert_eq!(self.status().pending.as_ref(), Some(accepted));
    }
    fn advance(&mut self) -> Instant {
        let id = self.id();
        let next = self.tail.resolve_tick.checked_add(1).unwrap();
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
                .unwrap();
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
        self.output.get_mut().set_read_timeout(None).unwrap();
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

#[derive(serde::Serialize)]
struct PeriodEvidence {
    period: u64,
    commitment: Option<OrganizerCommitment>,
    preview: OrganizerPreview,
    offered_material: Vec<babylon_persistence::runtime_session::OrganizerMaterialAidPreview>,
    pending_aid: Vec<babylon_persistence::runtime_session::OrganizerAidPending>,
    resolutions: Vec<babylon_persistence::runtime_session::OrganizerAidResolution>,
    positive_consequence: bool,
}
fn identity_rows(config: &Config, campaign: CampaignId) -> Vec<(i64, String, String)> {
    let mut client = config.connect(NoTls).unwrap();
    client.query("SELECT resolve_tick,encode(tick_content_hash,'hex'),encode(envelope_digest,'hex') FROM babylon_state.tick_commit WHERE campaign_id=$1 ORDER BY resolve_tick",&[campaign.as_uuid()]).unwrap()
        .iter().map(|r|(r.get(0),r.get(1),r.get(2))).collect()
}
fn verify_offers(snapshot: &OrganizerSnapshot) {
    assert_eq!(snapshot.view.actor_id, 2_616_301);
    assert_eq!(snapshot.aid.len(), 2);
    assert_eq!(snapshot.view.aid_options.len(), 2);
    for kind in [OrganizerAidKind::Local, OrganizerAidKind::Remote] {
        let preview = snapshot.aid.iter().find(|p| p.kind == kind).unwrap();
        let option = snapshot
            .view
            .aid_options
            .iter()
            .find(|p| p.kind == kind)
            .unwrap();
        assert_ne!(preview.mandate_id, [0; 32]);
        assert_eq!(
            option.partner_actor_id,
            if kind == OrganizerAidKind::Local {
                2_616_302
            } else {
                1_703_101
            }
        );
        assert_eq!(option.receiving_consent, OrganizerGiftConsent::Accept);
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
    let bytes = serde_json::to_vec(snapshot).unwrap();
    let mut digest = String::with_capacity(64);
    for byte in Sha256::digest(bytes) {
        write!(digest, "{byte:02x}").unwrap();
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
        elapsed_ns: elapsed_ns(started.elapsed()),
    };
    assert_eq!(reopened.tail, tail);
    assert_eq!(reopened.foundation, foundation);
    assert_eq!(&reopened.status(), after);
    assert_eq!(identity_rows(config, campaign), hashes);
    snapshot(&format!("tick-{:02}-reopened", tail.resolve_tick), campaign);
    (reopened, timing)
}

struct QualificationRun<'a> {
    config: &'a Config,
    campaign: CampaignId,
    started: Instant,
    limits: national_boundary_evidence::Limits,
}

struct AccountedBoundary {
    proof: serde_json::Value,
    roster: Vec<String>,
    world: String,
    production_timing: NativeTimingSample,
}

#[derive(Default)]
struct QualificationAccounting {
    aid: national_aid_accounting::Audit,
    trade: national_trade_accounting::Audit,
}

impl<'a> QualificationRun<'a> {
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
            limits,
        }
    }

    fn advance(&self, session: &mut Session) -> (Instant, NativeTimingSample) {
        let started = Instant::now();
        let acknowledged = session.advance();
        let tick = session.tail.resolve_tick;
        let timing = NativeTimingSample {
            tick,
            elapsed_ns: elapsed_ns(started.elapsed()),
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
        write_native_timings(&NativeTimingEvidence {
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
                elapsed_ns: elapsed_ns(self.started.elapsed()),
                compilation_included: false,
            },
        });
    }

    fn authenticated_archive(
        &self,
        session: &mut Session,
        acknowledged: Instant,
    ) -> (serde_json::Value, NativeTimingSample) {
        let tick = session.tail.resolve_tick;
        session.await_archive(acknowledged, self.limits.archive);
        let archive = national_boundary_evidence::archive_boundary(
            self.config,
            self.campaign,
            tick,
            session.tail.tick_content_hash.as_deref().unwrap(),
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
                elapsed_ns: elapsed_ns(elapsed),
            },
        )
    }

    fn accounted_boundary(
        &self,
        session: &Session,
        accounting: &mut QualificationAccounting,
        after: &OrganizerSnapshot,
        archive: &serde_json::Value,
    ) -> AccountedBoundary {
        let tick = session.tail.resolve_tick;
        let started = Instant::now();
        // Each observation owns its evidence. Release the reader's admitted
        // foundation before recovery and the next Archive reconstruction.
        let observation = {
            let observer = national_aid_accounting::observer();
            observer
                .committed_material_observation(self.campaign, tick)
                .unwrap()
        };
        let elapsed = started.elapsed();
        assert!(
            elapsed <= self.limits.production,
            "complete production read exceeded captured budget"
        );
        let admitted = accounting.aid.read(
            &observation.accounting,
            self.campaign,
            tick,
            after,
            session.tail.tick_content_hash.as_deref().unwrap(),
        );
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
                &observation.snapshot.production.as_ref().unwrap().sites,
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
        AccountedBoundary {
            proof,
            roster,
            world: national_boundary_evidence::hex(&admitted.result_world_hash()),
            production_timing: NativeTimingSample {
                tick,
                elapsed_ns: elapsed_ns(elapsed),
            },
        }
    }
}

pub(super) fn qualify(config: &Config, campaign: CampaignId, periods: u64, run_started: Instant) {
    let run = QualificationRun::start(config, campaign, periods, run_started);
    let mut session = Session::start(config, campaign, true);
    assert_eq!(session.tail.resolve_tick, 0);
    snapshot("opening-created", campaign);
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
        verify_offers(&before);
        let admission = match tick {
            1 => Some(session.accept(campaign, &before, OrganizerChoice::RemoteAid, 1)),
            2 => Some(session.accept(campaign, &before, OrganizerChoice::LocalAid, 2)),
            _ => {
                assert!(before.pending.is_none());
                None
            }
        };
        let commitment = admission
            .as_ref()
            .and_then(|(commitment, _)| commitment.as_ref());
        if let Some(commitment) = commitment {
            accounting.aid.accept(commitment, &before);
        }
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
        snapshot(&format!("tick-{tick:02}"), campaign);
        let hashes = identity_rows(config, campaign);
        assert_eq!(hashes.len(), usize::try_from(tick).unwrap());
        let (reopened, timing) = recover(config, campaign, session, &after, &hashes);
        session = reopened;
        cold_reopens.push(timing);
        write_progress(
            campaign,
            tick,
            "reopened",
            run_started,
            &serde_json::json!({"tail":session.tail,"foundation_sha256":foundation,"cold_reopen_elapsed_ns":cold_reopens.last().unwrap().elapsed_ns}),
        );
        continuations.push(serde_json::json!({"period":tick,"tail":session.tail,
            "organizer_snapshot_sha256":snapshot_digest(&after),"latest_marker":hashes.last(),"nominal_world_hash":world}));
        if let Some((commitment, preview)) = admission {
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
        &serde_json::json!({"version":3,"capture_mode":"playable-aid","policy_sha256":run.limits.policy_sha256,
        "campaign":campaign.as_uuid().to_string(),"foundation_sha256":foundation,"county_geoids":county_geoids.unwrap(),"requested_periods":periods,"aid_periods":evidence,"continuations":continuations,"boundaries":boundaries,
        "canonical_protocol_recovery":"passed","positive_aid_consequences":if remote&&local {"passed"} else {"incomplete"},
        "remote_consumed":remote,"local_consumed":local,"independent_finite_aid_practice":accounting.aid.practice_report(),"native_window_evidence":"not_run",
        "independent_account_posting_audit":accounting.aid.report(),"independent_trade_accounting":accounting.trade.report()}),
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
    evidence: &serde_json::Value,
) {
    write_report(
        &format!("progress-{tick:03}-{stage}.json"),
        &serde_json::json!({
            "version":2,"status":"incomplete","campaign":campaign.as_uuid().to_string(),
            "tick":tick,"completed_stage":stage,"elapsed_ns":elapsed_ns(started.elapsed()),"evidence":evidence,
        }),
    );
}

fn write_report(name: &str, report: &serde_json::Value) {
    let directory = PathBuf::from(std::env::var("BABYLON_STORAGE_REPORT_DIRECTORY").unwrap());
    assert!(directory.is_absolute() && directory.is_dir());
    let target = directory.join(name);
    assert!(!target.exists(), "never replace evidence");
    let temporary = directory.join(format!("{name}.partial"));
    let bytes = serde_json::to_vec(report).unwrap();
    assert!(bytes.len() <= 1_048_576);
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary)
        .unwrap();
    file.write_all(&bytes).unwrap();
    file.write_all(b"\n").unwrap();
    file.sync_all().unwrap();
    drop(file);
    std::fs::rename(temporary, target).unwrap();
    std::fs::File::open(directory).unwrap().sync_all().unwrap();
}
