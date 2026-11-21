//! The County Review's recorded playthroughs (design section 9, "Play proof").
//!
//! Four lines of play from one opening, each in its own disposable database, each through the
//! runtime session's own protocol, as the client speaks it: no contact; one household position
//! contacted in period 3 and never again; two positions; and food runs only. The one-position line
//! is then replayed from its action log and reopened once. Every run writes its record under
//! `reports/county-review-2026-11-19/`.
//!
//! The runs are long (about 40 minutes together), so every test here is ignored and belongs to the
//! `county_review` live focus of `tools/run_rust_postgres.sh`, which is local only.
use super::support::DisposableTarget;
use babylon_material_circuit::{PublicAccountId, PublicTransferTreatment};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::observer_reader::{
    self, ObserverEconomyReader, ObserverMaterialCursor, ObserverVisibility,
};
use babylon_persistence::runtime_session::{
    self, Band, ContactOutcome, ContactPreview, CountyReviewProjection, OrganizerAidKind,
    OrganizerAllocation, OrganizerChoice, OrganizerCommand, OrganizerCommitment, OrganizerPreview,
    OrganizerRefusal, OrganizerSnapshot, PositionKey, RuntimeAdvanceStage, RuntimeSessionErrorCode,
    RuntimeSessionPreset, RuntimeSessionRequest, RuntimeSessionResponse, RuntimeSessionScope,
    RuntimeSessionTail, RuntimeSessionTarget, RUNTIME_SESSION_MAX_LINE_BYTES,
    RUNTIME_SESSION_PROTOCOL_VERSION,
};
use babylon_practice_contract::{
    CountyPeriodFacts, CountyReviewConfig, CountyReviewCrew, CountyReviewGroup, CrewPeriodFacts,
    GroupKind, PayMode, Placement, Roster, SessionRecord, SessionRow, SupportLine,
};
use babylon_tick::material_world::MaterialReceiptHandle;
use postgres::{Config, NoTls};
use serde::Serialize;
use serde_json::{json, Value};
use std::collections::BTreeSet;
use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use std::sync::mpsc::{self, Sender};
use std::thread::{self, JoinHandle};
use std::time::Instant;
use uuid::Uuid;

/// The one campaign of every run and of the replay. It is the campaign of the printed opening.
const CAMPAIGN: u128 = 0x0026_1631_7036;
/// The period whose snapshot the first contact is chosen from: the county's first session is the
/// period after.
const FIRST_CONTACT_VIEW: u64 = 3;
/// The period whose snapshot the second contact is chosen from.
const SECOND_CONTACT_VIEW: u64 = 10;
/// A run stops here at the earliest, and two periods after its first short session at the latest
/// of the two.
const MINIMUM_LAST_PERIOD: u64 = 34;
/// No run goes past this period.
const MAXIMUM_LAST_PERIOD: u64 = 40;
/// A record file stays under the repository's blob limit.
const RECORD_LIMIT_BYTES: usize = 1_048_576;

fn campaign() -> CampaignId {
    CampaignId::from_uuid(Uuid::from_u128(CAMPAIGN))
}

fn reports_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../reports/county-review-2026-11-19")
}

/// The four lines of play. They differ only in what the player does.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Line {
    NoContact,
    OnePosition,
    TwoPositions,
    FoodRuns,
}

impl Line {
    const fn name(self) -> &'static str {
        match self {
            Self::NoContact => "no-contact",
            Self::OnePosition => "one-position",
            Self::TwoPositions => "two-positions",
            Self::FoodRuns => "food-runs",
        }
    }
}

/// What a run is told to do.
struct Spec<'a> {
    line: Line,
    /// A replay follows this action log instead of choosing.
    replay: Option<&'a [Action]>,
    /// A smoke run stops here.
    last_period: Option<u64>,
    /// Reopen the campaign once at the end and read the Archive's grants.
    reopen: bool,
}

/// One position tried for a contact, and what the county's own preview said.
#[derive(Clone, Debug, Serialize)]
struct Probe {
    key: PositionKey,
    refusal: Option<OrganizerRefusal>,
    error: Option<String>,
    outcome: Option<ContactOutcome>,
    asks: Option<bool>,
    place_open: Option<bool>,
}

/// The preview of a choice as the record keeps it: everything but the reports it would draw.
#[derive(Clone, Debug, Serialize)]
struct PreviewRecord {
    current_period: u64,
    resolves_period: u64,
    available_hours: u64,
    required_hours: u64,
    replaces_standing_work: bool,
    refusal: Option<OrganizerRefusal>,
    observations: usize,
    review: Option<ContactPreview>,
}

impl PreviewRecord {
    fn of(preview: &OrganizerPreview) -> Self {
        Self {
            current_period: preview.current_period,
            resolves_period: preview.resolves_period,
            available_hours: preview.available_hours,
            required_hours: preview.required_hours,
            replaces_standing_work: preview.replaces_standing_work,
            refusal: preview.refusal,
            observations: preview.observations.len(),
            review: preview.review.clone(),
        }
    }
}

/// What the player did in one period: the choice made from the snapshot of `view_period`, which
/// resolves in the next period.
#[derive(Clone, Debug, Serialize)]
struct Action {
    view_period: u64,
    choice: OrganizerChoice,
    allocation: OrganizerAllocation,
    nonce: [u8; 16],
    /// The preview of the choice that was submitted, or the refused one.
    preview: Option<PreviewRecord>,
    /// Whether the choice was submitted. A refused preview leaves the standing routine.
    submitted: bool,
    /// The code the session answered the preview request with, when it refused the request itself.
    /// It is in the record only when there was one; a typed refusal in the preview is `preview`'s.
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
    /// The positions tried before the contact was chosen, each with its preview.
    probes: Vec<Probe>,
}

/// A request and reply channel to one runtime session, as `national_playable.rs`'s `Session` is,
/// with only what these runs use.
struct Driver {
    input: UnixStream,
    output: BufReader<UnixStream>,
    worker: JoinHandle<Result<(), RuntimeSessionErrorCode>>,
    scope: RuntimeSessionScope,
    tail: RuntimeSessionTail,
    foundation: String,
    next_id: u64,
}

impl Driver {
    fn start(config: &Config, target: RuntimeSessionTarget) -> Self {
        let (local, remote) = UnixStream::pair().expect("bounded local runtime pipe");
        let input = local.try_clone().expect("the pipe clones");
        let source = remote.try_clone().expect("the pipe clones");
        let config = config.clone();
        let worker = thread::spawn(move || {
            let mut output = remote;
            runtime_session::run_runtime_session(
                &config,
                Path::new("/dev/null"),
                BufReader::new(source),
                &mut output,
            )
        });
        let mut driver = Self {
            input,
            output: BufReader::new(local),
            worker,
            scope: RuntimeSessionScope::default(),
            tail: RuntimeSessionTail {
                resolve_tick: 0,
                tick_content_hash: None,
                world_hash: None,
            },
            foundation: String::new(),
            next_id: 1,
        };
        let RuntimeSessionResponse::Hello { scope, .. } = driver.read() else {
            panic!("a session begins with Hello")
        };
        assert_eq!(scope, RuntimeSessionScope::default());
        let id = driver.id();
        driver.send(&RuntimeSessionRequest::Switch {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: id,
            scope: driver.scope.clone(),
            target,
        });
        let RuntimeSessionResponse::Switching { scope, .. } = driver.reply(id) else {
            panic!("the switch is accepted")
        };
        driver.scope = scope;
        let RuntimeSessionResponse::Ready {
            foundation_digest,
            tail,
            organizer,
            ..
        } = driver.reply(id)
        else {
            panic!("the campaign is admitted")
        };
        assert!(organizer, "the national world is playable");
        driver.foundation = foundation_digest;
        driver.tail = tail;
        driver
    }

    fn id(&mut self) -> u64 {
        let id = self.next_id;
        self.next_id = id.checked_add(1).expect("request counter stays in range");
        id
    }

    fn send(&mut self, request: &RuntimeSessionRequest) {
        let bytes = serde_json::to_vec(request).expect("the request serializes");
        assert!(bytes.len() < RUNTIME_SESSION_MAX_LINE_BYTES);
        self.input
            .write_all(&bytes)
            .expect("the session accepts the request");
        self.input
            .write_all(b"\n")
            .expect("the session accepts the request");
        self.input.flush().expect("the request flushes");
    }

    fn read(&mut self) -> RuntimeSessionResponse {
        let mut line = String::new();
        let limit = u64::try_from(RUNTIME_SESSION_MAX_LINE_BYTES).expect("the bound fits") + 1;
        let count = Read::by_ref(&mut self.output)
            .take(limit)
            .read_line(&mut line)
            .expect("the session replies");
        assert!(count > 0 && count <= RUNTIME_SESSION_MAX_LINE_BYTES && line.ends_with('\n'));
        serde_json::from_str(&line).expect("a reply of the current protocol")
    }

    /// The reply to request `id`, skipping the Archive's own progress lines. A refusal is `Err`.
    fn try_reply(&mut self, id: u64) -> Result<RuntimeSessionResponse, RuntimeSessionErrorCode> {
        loop {
            let response = self.read();
            let request = match &response {
                RuntimeSessionResponse::ArchiveProgress { .. } => continue,
                RuntimeSessionResponse::Error { code, .. } => return Err(*code),
                RuntimeSessionResponse::Switching { request_id, .. }
                | RuntimeSessionResponse::Ready { request_id, .. }
                | RuntimeSessionResponse::OrganizerStatus { request_id, .. }
                | RuntimeSessionResponse::OrganizerPreview { request_id, .. }
                | RuntimeSessionResponse::OrganizerAccepted { request_id, .. }
                | RuntimeSessionResponse::Committed { request_id, .. }
                | RuntimeSessionResponse::AdvanceProgress { request_id, .. }
                | RuntimeSessionResponse::Stopped { request_id, .. } => *request_id,
                RuntimeSessionResponse::Hello { .. } => panic!("a second Hello: {response:?}"),
            };
            assert_eq!(request, id);
            return Ok(response);
        }
    }

    fn reply(&mut self, id: u64) -> RuntimeSessionResponse {
        self.try_reply(id)
            .unwrap_or_else(|code| panic!("the session refused request {id}: {code:?}"))
    }

    fn status(&mut self) -> OrganizerSnapshot {
        let id = self.id();
        self.send(&RuntimeSessionRequest::OrganizerStatus {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: id,
            scope: self.scope.clone(),
        });
        let RuntimeSessionResponse::OrganizerStatus { snapshot, .. } = self.reply(id) else {
            panic!("an organizer projection")
        };
        assert_eq!(snapshot.view.period, self.tail.resolve_tick);
        *snapshot
    }

    /// The preview of a command: the client's `PreviewOrganizer` request.
    fn preview(
        &mut self,
        command: &OrganizerCommand,
    ) -> Result<OrganizerPreview, RuntimeSessionErrorCode> {
        let id = self.id();
        self.send(&RuntimeSessionRequest::PreviewOrganizer {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: id,
            scope: self.scope.clone(),
            command: command.clone(),
        });
        match self.try_reply(id)? {
            RuntimeSessionResponse::OrganizerPreview { preview, .. } => Ok(preview),
            other => panic!("a preview was asked for: {other:?}"),
        }
    }

    /// The client's `SubmitOrganizer` request, the nonce path.
    fn submit(&mut self, command: &OrganizerCommand) -> OrganizerCommitment {
        let id = self.id();
        self.send(&RuntimeSessionRequest::SubmitOrganizer {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: id,
            scope: self.scope.clone(),
            command: command.clone(),
        });
        let RuntimeSessionResponse::OrganizerAccepted { commitment, .. } = self.reply(id) else {
            panic!("a durable acceptance")
        };
        assert_eq!(&commitment.command, command);
        commitment
    }

    /// One period: the four stages, then the commit. It does not wait for the Archive.
    fn advance(&mut self) {
        let id = self.id();
        let next = self.tail.resolve_tick + 1;
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
                resolve_tick,
                stage,
                ..
            } = self.reply(id)
            else {
                panic!("a stage of the close")
            };
            assert_eq!((resolve_tick, stage), (next, expected));
        }
        let RuntimeSessionResponse::Committed { tail, .. } = self.reply(id) else {
            panic!("only Committed publishes time")
        };
        assert_eq!(tail.resolve_tick, next);
        assert!(tail.tick_content_hash.is_some() && tail.world_hash.is_some());
        self.tail = tail;
    }

    fn stop(mut self) {
        let id = self.id();
        self.send(&RuntimeSessionRequest::Stop {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION,
            request_id: id,
            scope: self.scope.clone(),
        });
        let RuntimeSessionResponse::Stopped { .. } = self.reply(id) else {
            panic!("a clean stop")
        };
        drop(self.input);
        drop(self.output);
        assert_eq!(
            self.worker.join().expect("the session worker joins"),
            Ok(())
        );
    }
}

fn build_command(
    snapshot: &OrganizerSnapshot,
    choice: OrganizerChoice,
    allocation: OrganizerAllocation,
    nonce: [u8; 16],
) -> OrganizerCommand {
    OrganizerCommand {
        allocation,
        campaign_id: *campaign().canonical_bytes(),
        actor_id: snapshot.view.actor_id,
        authority_id: snapshot.view.authority_id,
        expected_period: snapshot.view.period,
        content_digest: snapshot.view.content_digest,
        resource_digest: snapshot.view.resource_digest,
        nonce,
        choice,
    }
}

/// A tax the engine collected in one period, summed by basis and rate.
#[derive(Clone, Debug, Serialize)]
struct TaxLine {
    basis: u8,
    rate_bps: u16,
    receipts: u64,
    assessed_micros: String,
    collected_micros: String,
}

/// The county's public budget in one period, summed by treatment.
#[derive(Clone, Debug, Serialize)]
struct BudgetLine {
    treatment: u8,
    claims: u64,
    requested_micros: String,
    paid_micros: String,
    unfunded_micros: String,
}

fn tax_lines(receipts: &MaterialReceiptHandle, county: PublicAccountId) -> Vec<TaxLine> {
    let mut lines: Vec<(u8, u16, u64, i128, i128)> = Vec::new();
    for tax in receipts
        .taxes
        .iter()
        .filter(|tax| tax.public_recipient == county)
    {
        let basis = tax.basis as u8;
        let slot = lines
            .iter()
            .position(|line| line.0 == basis && line.1 == tax.rate_bps)
            .unwrap_or_else(|| {
                lines.push((basis, tax.rate_bps, 0, 0, 0));
                lines.len() - 1
            });
        let line = &mut lines[slot];
        line.2 += 1;
        line.3 += tax.assessed.micro_units();
        line.4 += tax.collected.micro_units();
    }
    lines.sort_by_key(|line| (line.0, line.1));
    lines
        .into_iter()
        .map(|(basis, rate_bps, receipts, assessed, collected)| TaxLine {
            basis,
            rate_bps,
            receipts,
            assessed_micros: assessed.to_string(),
            collected_micros: collected.to_string(),
        })
        .collect()
}

fn budget_lines(receipts: &MaterialReceiptHandle, county: PublicAccountId) -> Vec<BudgetLine> {
    let mut lines: Vec<(u8, u64, i128, i128, i128)> = Vec::new();
    for budget in receipts
        .public_budgets
        .iter()
        .filter(|budget| budget.public_account == county)
    {
        let treatment = budget.treatment as u8;
        let slot = lines
            .iter()
            .position(|line| line.0 == treatment)
            .unwrap_or_else(|| {
                lines.push((treatment, 0, 0, 0, 0));
                lines.len() - 1
            });
        let line = &mut lines[slot];
        line.1 += 1;
        line.2 += budget.requested.micro_units();
        line.3 += budget.paid.micro_units();
        line.4 += budget.unfunded.micro_units();
    }
    lines.sort_by_key(|line| line.0);
    lines
        .into_iter()
        .map(
            |(treatment, claims, requested, paid, unfunded)| BudgetLine {
                treatment,
                claims,
                requested_micros: requested.to_string(),
                paid_micros: paid.to_string(),
                unfunded_micros: unfunded.to_string(),
            },
        )
        .collect()
}

/// A tax rate in force: the public account it is paid to, its basis and its rate in basis points.
type TaxRate = ([u8; 32], u8, u16);

/// Every tax rate the period's receipts show, whoever received the tax: each distinct recipient,
/// basis and rate once, in order.
fn tax_rates(receipts: &MaterialReceiptHandle) -> Vec<TaxRate> {
    receipts
        .taxes
        .iter()
        .map(|tax| {
            (
                tax.public_recipient.as_bytes(),
                tax.basis as u8,
                tax.rate_bps,
            )
        })
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}

/// What the full observer reads of one committed period.
struct Observed {
    /// The county's own taxes, summed: the lines its cash and receipts are made of.
    taxes: Vec<TaxLine>,
    /// The rate of every tax of the period, whoever it was paid to.
    tax_rates: Vec<TaxRate>,
    budgets: Vec<BudgetLine>,
    roster: Roster,
    facts: CountyPeriodFacts,
    session: Option<SessionRecord>,
}

fn observer_reader(config: &Config) -> ObserverEconomyReader {
    ObserverEconomyReader::connect(config, ObserverVisibility::FullObserver)
        .expect("the full observer connects")
}

/// The opening roster and the county's configuration, from the authenticated opening.
fn read_opening(
    config: &Config,
    cursor: &mut Option<ObserverMaterialCursor>,
) -> (CountyReviewConfig, Roster) {
    let reader = observer_reader(config);
    reader
        .snapshot_with_cursor(campaign(), 0, cursor)
        .expect("the authenticated opening");
    cursor
        .as_ref()
        .expect("the opening read leaves its cursor")
        .with_opening_register(campaign(), |register| {
            let county = register.county_review().expect("a county section");
            (county.config().clone(), county.state().roster.clone())
        })
        .expect("the opening register")
}

fn observe(
    config: &Config,
    county: PublicAccountId,
    tick: u64,
    cursor: &mut Option<ObserverMaterialCursor>,
) -> Observed {
    let reader = observer_reader(config);
    let committed = reader
        .committed_material_receipts_with_cursor(campaign(), tick, cursor)
        .expect("the committed period's receipts");
    let register = cursor
        .as_ref()
        .expect("the read leaves its cursor")
        .current_register()
        .expect("the read leaves the period's register");
    assert_eq!(register.completed_tick(), tick);
    let state = register.county_review().expect("a county section").state();
    let facts = state
        .last_facts
        .clone()
        .expect("a close the county has seen");
    assert_eq!(facts.period, tick);
    Observed {
        taxes: tax_lines(&committed.receipts, county),
        tax_rates: tax_rates(&committed.receipts),
        budgets: budget_lines(&committed.receipts, county),
        roster: state.roster.clone(),
        facts,
        session: state
            .last_session
            .clone()
            .filter(|session| session.period == tick),
    }
}

/// One closed period of a run.
struct Period {
    tick: u64,
    tail: RuntimeSessionTail,
    /// The player's choice that resolved in this period, if one was submitted.
    action: Option<Action>,
    observed: Observed,
    seconds: f64,
}

/// One closed period as the player's side saw it, before the observer's read joins it.
struct Closed {
    tick: u64,
    tail: RuntimeSessionTail,
    action: Option<Action>,
    seconds: f64,
}

/// The player's side of a run: the session, the choices made and the closes.
struct Played {
    driver: Driver,
    foundation: String,
    actions: Vec<Action>,
    closed: Vec<Closed>,
    first_short_hint: Option<u64>,
    watch: Option<Watch>,
}

/// A finished run.
struct Run {
    line: Line,
    config: CountyReviewConfig,
    opening_roster: Roster,
    foundation: String,
    actions: Vec<Action>,
    periods: Vec<Period>,
    first_short_period: Option<u64>,
    /// The first session the player's own reading of the county called short.
    first_short_hint: Option<u64>,
    reopened: Option<Value>,
}

impl Run {
    fn is_short(session: &SessionRecord) -> bool {
        session.relief_micros < session.roll_total_micros
    }
}

/// Whether the last session of this snapshot paid fewer household units than the roll held. It is
/// the player's own reading of the county, and decides when a run stops; the record's first short
/// session is worked out from the session record itself and must agree.
fn session_was_short(county: &CountyReviewProjection) -> bool {
    county
        .household_units_payable
        .zip(county.household_units_listed)
        .is_some_and(|(payable, listed)| payable < listed)
}

/// Whether a run stops after this period: at its smoke limit, at period 34 or two periods after
/// its first short session (whichever is later), and never past period 40.
fn last_period_reached(spec: &Spec<'_>, period: u64, first_short: Option<u64>) -> bool {
    if spec.last_period == Some(period) {
        return true;
    }
    match first_short {
        Some(short) => period >= MAXIMUM_LAST_PERIOD.min(MINIMUM_LAST_PERIOD.max(short + 2)),
        None => period >= MAXIMUM_LAST_PERIOD,
    }
}

/// The full observer's reads of a run, made one after another on their own thread while the next
/// period closes. A read costs about as much as a close, and no choice depends on one.
struct Watch {
    sender: Sender<u64>,
    worker: JoinHandle<Watched>,
}

struct Watched {
    config: CountyReviewConfig,
    opening_roster: Roster,
    observed: Vec<Observed>,
}

fn watch(observer_config: Config, line: Line) -> Watch {
    let (sender, receiver) = mpsc::channel::<u64>();
    let worker = thread::spawn(move || {
        let started = Instant::now();
        let mut cursor = None;
        let (config, opening_roster) = read_opening(&observer_config, &mut cursor);
        eprintln!(
            "county_review {}: opening read in {:.0} s, {} positions",
            line.name(),
            started.elapsed().as_secs_f64(),
            opening_roster.rows.len()
        );
        let county = PublicAccountId::from_bytes(config.public_account_id);
        let mut observed = Vec::new();
        for tick in receiver {
            let reading = Instant::now();
            observed.push(observe(&observer_config, county, tick, &mut cursor));
            eprintln!(
                "county_review {}: period {tick} read in {:.1} s",
                line.name(),
                reading.elapsed().as_secs_f64()
            );
        }
        Watched {
            config,
            opening_roster,
            observed,
        }
    });
    Watch { sender, worker }
}

/// The aid terms of the standing local food run.
fn local_aid_allocation(snapshot: &OrganizerSnapshot) -> OrganizerAllocation {
    let terms = snapshot
        .aid
        .iter()
        .find(|row| row.kind == OrganizerAidKind::Local)
        .expect("captured local aid terms");
    OrganizerAllocation::Aid {
        food_quantity: terms.initial_food_quantity,
        cash_micros: terms.initial_cash_micros,
    }
}

fn nonce_for(period: u64) -> [u8; 16] {
    [u8::try_from(period + 1).expect("a nonce for a period below 255"); 16]
}

/// The first position of the county's list, in its order, that the county's own preview says
/// would be reached, would ask and would find a place. `exclude_crew` skips the crew of an
/// earlier contact. Every position tried is logged.
fn choose_position(
    driver: &mut Driver,
    snapshot: &OrganizerSnapshot,
    first: Option<&PositionKey>,
) -> (PositionKey, OrganizerPreview, Vec<Probe>) {
    let county: &CountyReviewProjection = snapshot
        .county_review
        .as_ref()
        .expect("the national world has a county review");
    let mut probes = Vec::new();
    for position in &county.positions {
        if first.is_some_and(|first| first.crew == position.key.crew) {
            continue;
        }
        let key = position.key;
        let command = build_command(
            snapshot,
            OrganizerChoice::ReviewContact(key),
            OrganizerAllocation::None,
            nonce_for(snapshot.view.period),
        );
        match driver.preview(&command) {
            Ok(preview) => {
                let review = preview.review.as_ref();
                probes.push(Probe {
                    key,
                    refusal: preview.refusal,
                    error: None,
                    outcome: review.map(|review| review.outcome),
                    asks: review.map(|review| review.asks),
                    place_open: review.map(|review| review.place_open),
                });
                let suitable = preview.refusal.is_none()
                    && review.is_some_and(|review| {
                        review.outcome == ContactOutcome::Reached
                            && review.asks
                            && review.place_open
                    });
                if suitable {
                    return (key, preview, probes);
                }
            }
            Err(code) => probes.push(Probe {
                key,
                refusal: None,
                error: Some(format!("{code:?}")),
                outcome: None,
                asks: None,
                place_open: None,
            }),
        }
    }
    panic!(
        "no position of the period-{} list is reached, asks and finds a place: {probes:#?}",
        snapshot.view.period
    );
}

/// What the session answered a preview request with: the preview, or the code it refused the
/// request with.
fn preview_answer(
    driver: &mut Driver,
    command: &OrganizerCommand,
) -> (Option<OrganizerPreview>, Option<String>) {
    match driver.preview(command) {
        Ok(preview) => (Some(preview), None),
        Err(code) => (None, Some(format!("{code:?}"))),
    }
}

/// Previews and, unless refused, submits one choice. A refused preview leaves the standing
/// routine and is logged.
fn act(
    driver: &mut Driver,
    snapshot: &OrganizerSnapshot,
    choice: OrganizerChoice,
    allocation: OrganizerAllocation,
    probes: Vec<Probe>,
) -> Action {
    let nonce = nonce_for(snapshot.view.period);
    let command = build_command(snapshot, choice, allocation, nonce);
    let (preview, error) = preview_answer(driver, &command);
    let submitted = preview
        .as_ref()
        .is_some_and(|preview| preview.refusal.is_none());
    if submitted {
        driver.submit(&command);
    }
    Action {
        view_period: snapshot.view.period,
        choice,
        allocation,
        nonce,
        preview: preview.as_ref().map(PreviewRecord::of),
        submitted,
        error,
        probes,
    }
}

/// Whether the line of play reaches a household from the snapshot of this period.
const fn wants_contact(line: Line, period: u64) -> bool {
    matches!(
        (line, period),
        (Line::OnePosition | Line::TwoPositions, FIRST_CONTACT_VIEW)
            | (Line::TwoPositions, SECOND_CONTACT_VIEW)
    )
}

/// The position of the first contact the player made, if any.
fn first_contact(actions: &[Action]) -> Option<PositionKey> {
    actions.iter().find_map(|action| match action.choice {
        OrganizerChoice::ReviewContact(key) if action.submitted => Some(key),
        _ => None,
    })
}

/// The player's choice for the period after this snapshot, if the line of play makes one.
fn decide(
    driver: &mut Driver,
    spec: &Spec<'_>,
    snapshot: &OrganizerSnapshot,
    earlier: &[Action],
) -> Option<Action> {
    let period = snapshot.view.period;
    if let Some(log) = spec.replay {
        let recorded = log.iter().find(|action| action.view_period == period)?;
        let command = build_command(
            snapshot,
            recorded.choice,
            recorded.allocation,
            recorded.nonce,
        );
        let (preview, error) = preview_answer(driver, &command);
        assert_eq!(
            preview.as_ref().map(|preview| preview.refusal),
            recorded.preview.as_ref().map(|preview| preview.refusal),
            "the replay's preview agrees with the recorded one"
        );
        assert_eq!(
            error, recorded.error,
            "the replay's preview request is answered as the recorded one was"
        );
        if recorded.submitted {
            driver.submit(&command);
        }
        return Some(recorded.clone());
    }
    if wants_contact(spec.line, period) {
        let first = first_contact(earlier);
        let (key, _, probes) = choose_position(driver, snapshot, first.as_ref());
        return Some(act(
            driver,
            snapshot,
            OrganizerChoice::ReviewContact(key),
            OrganizerAllocation::None,
            probes,
        ));
    }
    (spec.line == Line::FoodRuns).then(|| {
        act(
            driver,
            snapshot,
            OrganizerChoice::LocalAid,
            local_aid_allocation(snapshot),
            Vec::new(),
        )
    })
}

fn provisioned_observer(target: &mut DisposableTarget) -> Config {
    observer_reader::provision_observer_role(&target.writer).expect("observer role");
    target.login("babylon_observer", "cprun")
}

/// Plays the periods of one line in a new campaign. With an observer the full observer's reads
/// follow each close on their own thread.
fn drive(spec: &Spec<'_>, writer: &Config, observer_config: Option<Config>) -> Played {
    let started = Instant::now();
    let driver = Driver::start(
        writer,
        RuntimeSessionTarget::New {
            campaign_id: campaign().as_uuid().to_string(),
            preset: RuntimeSessionPreset::NationalWorld,
        },
    );
    eprintln!(
        "county_review {}: campaign ready in {:.0} s",
        spec.line.name(),
        started.elapsed().as_secs_f64()
    );
    let mut played = Played {
        foundation: driver.foundation.clone(),
        driver,
        actions: Vec::new(),
        closed: Vec::new(),
        first_short_hint: None,
        watch: observer_config.map(|config| watch(config, spec.line)),
    };
    loop {
        let snapshot = played.driver.status();
        let period = snapshot.view.period;
        let short = snapshot
            .county_review
            .as_ref()
            .is_some_and(session_was_short);
        if short && played.first_short_hint.is_none() {
            played.first_short_hint = Some(period);
        }
        if period > 0 && last_period_reached(spec, period, played.first_short_hint) {
            return played;
        }
        let action = decide(&mut played.driver, spec, &snapshot, &played.actions);
        let closing = Instant::now();
        played.driver.advance();
        let seconds = closing.elapsed().as_secs_f64();
        let tick = played.driver.tail.resolve_tick;
        if let Some(watch) = &played.watch {
            watch
                .sender
                .send(tick)
                .expect("the observer thread is alive");
        }
        eprintln!(
            "county_review {}: period {tick} closed in {seconds:.1} s{}",
            spec.line.name(),
            action.as_ref().map_or(String::new(), |action| format!(
                ", chose {:?} (submitted: {})",
                action.choice, action.submitted
            ))
        );
        if let Some(action) = &action {
            played.actions.push(action.clone());
        }
        played.closed.push(Closed {
            tick,
            tail: played.driver.tail.clone(),
            action,
            seconds,
        });
    }
}

/// Plays one line from a new campaign in its own disposable database, observed.
fn play(spec: &Spec<'_>) -> Run {
    let mut target = DisposableTarget::create();
    let observer_config = provisioned_observer(&mut target);
    let played = drive(spec, &target.writer, Some(observer_config));
    let Played {
        driver,
        foundation,
        actions,
        closed,
        first_short_hint,
        watch,
    } = played;
    let Watch { sender, worker } = watch.expect("an observed run has a watcher");
    drop(sender);
    let started = Instant::now();
    let watched = worker.join().expect("the observer thread finishes");
    eprintln!(
        "county_review {}: the observer's backlog took {:.0} s more",
        spec.line.name(),
        started.elapsed().as_secs_f64()
    );
    assert_eq!(watched.observed.len(), closed.len());
    let periods: Vec<Period> = closed
        .into_iter()
        .zip(watched.observed)
        .map(|(closed, observed)| {
            assert_eq!(closed.tick, observed.facts.period);
            Period {
                tick: closed.tick,
                tail: closed.tail,
                action: closed.action,
                observed,
                seconds: closed.seconds,
            }
        })
        .collect();
    let first_short_period = periods
        .iter()
        .find(|period| period.observed.session.as_ref().is_some_and(Run::is_short))
        .map(|period| period.tick);
    let mut run = Run {
        line: spec.line,
        config: watched.config,
        opening_roster: watched.opening_roster,
        foundation,
        actions,
        periods,
        first_short_period,
        first_short_hint,
        reopened: None,
    };
    if spec.reopen {
        run.reopened = Some(reopen_and_read_grants(&target, driver, &run));
    } else {
        driver.stop();
    }
    run
}

/// Replays an action log in a new campaign with no observer. Returns the seed and the committed
/// tail of every period.
fn replay(line: Line, log: &[Action], last_period: u64) -> (String, Vec<RuntimeSessionTail>) {
    let target = DisposableTarget::create();
    let spec = Spec {
        line,
        replay: Some(log),
        last_period: Some(last_period),
        reopen: false,
    };
    let played = drive(&spec, &target.writer, None);
    let tails = played
        .closed
        .iter()
        .map(|closed| closed.tail.clone())
        .collect();
    played.driver.stop();
    (played.foundation, tails)
}

/// Stops the session, opens the campaign again and reads the Archive's grants through the owner
/// connection: one `county-review-{period}` grant on the organization for each session held.
fn reopen_and_read_grants(target: &DisposableTarget, driver: Driver, run: &Run) -> Value {
    let before = driver.tail.clone();
    driver.stop();
    let mut reopened = Driver::start(
        &target.writer,
        RuntimeSessionTarget::Open {
            campaign_id: campaign().as_uuid().to_string(),
        },
    );
    assert_eq!(
        reopened.tail, before,
        "the reopened campaign stands at the same tail"
    );
    assert_eq!(reopened.foundation, run.foundation);
    let snapshot = reopened.status();
    assert_eq!(snapshot.view.period, before.resolve_tick);
    let last = run.periods.last().expect("a run has periods");
    let county = snapshot
        .county_review
        .as_ref()
        .expect("a county projection");
    assert_eq!(county.session_period, Some(last.tick));
    let reopened_tail = reopened.tail.clone();
    reopened.stop();
    let mut owner = target.writer.connect(NoTls).expect("the owner connection");
    let rows = owner
        .query(
            "SELECT subject_kind::text, grant_key, granted_tick FROM \
             babylon_meta.archive_knowledge_grant_witness_v1 \
             WHERE campaign_id=$1 AND grant_key LIKE 'county-review-%' ORDER BY granted_tick",
            &[campaign().as_uuid()],
        )
        .expect("the Archive's grant witness");
    let held: Vec<u64> = run
        .periods
        .iter()
        .filter(|period| period.observed.session.is_some())
        .map(|period| period.tick)
        .collect();
    let found: Vec<(String, String, u64)> = rows
        .iter()
        .map(|row| {
            (
                row.get::<_, String>(0),
                row.get::<_, String>(1),
                u64::try_from(row.get::<_, i64>(2)).expect("a granted tick"),
            )
        })
        .collect();
    let expected: Vec<(String, String, u64)> = held
        .iter()
        .map(|period| {
            (
                "organization".to_owned(),
                format!("county-review-{period}"),
                *period,
            )
        })
        .collect();
    assert_eq!(
        found, expected,
        "one grant on the organization for each session held"
    );
    json!({"reopened_tail": reopened_tail.tick_content_hash, "sessions_held": held,
        "archive_grants": found.len(), "archive_grant_first": found.first(),
        "archive_grant_last": found.last()})
}

fn micros_string(value: i128) -> String {
    value.to_string()
}

/// The household lines of a session in the order of the groups, with the groups' own names.
fn lines_json(config: &CountyReviewConfig, lines: &[SupportLine]) -> Vec<Value> {
    lines
        .iter()
        .map(|line| {
            let group = &config.groups[usize::try_from(line.group).expect("a group index")];
            json!({"group": line.group, "label": group.label, "units": line.units,
                "amount_micros": micros_string(line.amount_micros)})
        })
        .collect()
}

/// The hours a session charged each group, from its rows.
fn hours_json(config: &CountyReviewConfig, session: &SessionRecord) -> Vec<Value> {
    let mut hours = vec![(0_u64, 0_u64); config.groups.len()];
    for row in &session.rows {
        let slot = &mut hours[usize::try_from(row.key.group).expect("a group index")];
        slot.0 += row.hours_in_room;
        slot.1 += row.hours_bringing;
    }
    hours
        .iter()
        .enumerate()
        .filter(|(_, hours)| hours.0 + hours.1 > 0)
        .map(|(index, hours)| {
            json!({"group": index, "label": config.groups[index].label,
                "hours_in_room": hours.0, "hours_bringing": hours.1})
        })
        .collect()
}

fn session_json(config: &CountyReviewConfig, session: &SessionRecord) -> Value {
    let reached: Vec<&SessionRow> = session.rows.iter().filter(|row| row.reached > 0).collect();
    json!({
        "relief_micros": micros_string(session.relief_micros),
        "roll_total_micros": micros_string(session.roll_total_micros),
        "short": Run::is_short(session),
        "household_units_listed": session.household_units_listed,
        "household_units_payable": session.household_units_payable,
        "kept_back_units": session.kept_back_units,
        "contact": session.contact,
        "lines": lines_json(config, &session.lines),
        "collective_lines": lines_json(config, &session.collective_lines),
        "claimants_roll_households": session.claimants_roll_households,
        "aid_roll_households": session.aid_roll_households,
        "hour_charges": hours_json(config, session),
        "reached_rows": reached,
    })
}

fn period_json(config: &CountyReviewConfig, period: &Period) -> Value {
    let facts = &period.observed.facts;
    json!({
        "period": period.tick,
        "close_seconds": (period.seconds * 10.0).round() / 10.0,
        "tick_content_hash": period.tail.tick_content_hash,
        "world_hash": period.tail.world_hash,
        "action": period.action,
        "cash_micros": micros_string(facts.cash_micros),
        "spending_limit_micros": micros_string(facts.spending_limit_micros),
        "first_class_micros": micros_string(facts.first_class_micros),
        "taxes": period.observed.taxes,
        "budgets": period.observed.budgets,
        "bands": period.observed.roster.band_counts(),
        "session": period.observed.session.as_ref().map(|session| session_json(config, session)),
        "facts": facts,
    })
}

/// The record of one run: seed, action log and result.
fn run_json(run: &Run) -> Value {
    json!({
        "version": 1,
        "line": run.line.name(),
        "seed": {"campaign": campaign().as_uuid().to_string(), "foundation_sha256": run.foundation,
            "replay_seed": 319},
        "first_short_session": run.first_short_period,
        "first_short_session_by_the_players_reading": run.first_short_hint,
        "last_period": run.periods.last().map(|period| period.tick),
        "action_log": run.actions,
        "county_config": run.config,
        "opening_roster": run.opening_roster,
        "opening_bands": run.opening_roster.band_counts(),
        "periods": run.periods.iter().map(|period| period_json(&run.config, period)).collect::<Vec<_>>(),
        "reopened": run.reopened,
    })
}

fn write_record(directory: &Path, name: &str, record: &Value) -> usize {
    let mut bytes = serde_json::to_vec(record).expect("the record serializes");
    bytes.push(b'\n');
    assert!(
        bytes.len() < RECORD_LIMIT_BYTES,
        "{name} is {} bytes, past the repository's blob limit",
        bytes.len()
    );
    fs::create_dir_all(directory).expect("the reports directory");
    fs::write(directory.join(name), &bytes).expect("the record is written");
    bytes.len()
}

/// Plays a line and writes its record at once, before any assertion, so a failed check does not
/// lose the run.
fn play_and_record(spec: &Spec<'_>, directory: &Path) -> Run {
    let run = play(spec);
    let name = format!("{}.json", run.line.name());
    let bytes = write_record(directory, &name, &run_json(&run));
    eprintln!("county_review: {name} written, {bytes} bytes");
    run
}

// ---------------------------------------------------------------------------------------------
// What every run must show.

fn sum_micros(values: impl Iterator<Item = i128>) -> i128 {
    values.sum()
}

/// In every period of every run: the bands add back to the roster, the top 1% are outside the
/// labor force, and no band gains a household.
fn assert_bands(run: &Run) {
    let opening = run.opening_roster.band_counts();
    let mut previous: Vec<u64> = opening.iter().map(|band| band.households).collect();
    let ordinary_opening: u64 = run
        .config
        .groups
        .iter()
        .map(|group| group.opening_households)
        .sum();
    assert_eq!(previous.iter().sum::<u64>(), ordinary_opening);
    assert_eq!(opening[0].band, Band::Top1);
    for period in &run.periods {
        let bands = period.observed.roster.band_counts();
        let top = &bands[0];
        assert_eq!(top.band, Band::Top1);
        assert_eq!(
            (
                top.with_work,
                top.seeking_only,
                top.people_at_work,
                top.people_seeking
            ),
            (0, 0, 0, 0),
            "period {}: no household of the top 1% is in the labor force",
            period.tick
        );
        let total: u64 = bands.iter().map(|band| band.households).sum();
        let engine: u64 = period
            .observed
            .facts
            .groups
            .iter()
            .map(|group| group.closing_households)
            .sum();
        let roster: u64 = period
            .observed
            .roster
            .groups
            .iter()
            .map(|group| group.households)
            .sum();
        assert_eq!(
            (total, roster),
            (engine, engine),
            "period {}: the bands add back to the engine's households",
            period.tick
        );
        for (band, before) in bands.iter().zip(&previous) {
            assert!(
                band.households <= *before,
                "period {}: the {:?} band gained households",
                period.tick,
                band.band
            );
        }
        previous = bands.iter().map(|band| band.households).collect();
    }
}

/// The county's own books: relief announced at a session is relief requested at the next close.
fn assert_county_keeps_its_word(run: &Run) {
    for pair in run.periods.windows(2) {
        let Some(session) = &pair[0].observed.session else {
            continue;
        };
        let announced = sum_micros(
            session
                .lines
                .iter()
                .chain(&session.collective_lines)
                .map(|line| line.amount_micros),
        );
        let relief =
            pair[1].observed.budgets.iter().find(|line| {
                line.treatment == PublicTransferTreatment::HouseholdIncomeSupport as u8
            });
        let requested: i128 = relief.map_or(0, |line| {
            line.requested_micros.parse().expect("a requested amount")
        });
        assert_eq!(
            requested,
            announced,
            "{}: the relief requested at the close of period {} is the lines announced at the \
             session of period {}",
            run.line.name(),
            pair[1].tick,
            pair[0].tick
        );
    }
}

fn listed_units_by_group(config: &CountyReviewConfig, session: &SessionRecord) -> Vec<u64> {
    let mut units = vec![0_u64; config.groups.len()];
    for row in &session.rows {
        units[usize::try_from(row.key.group).expect("a group index")] += row.units_listed;
    }
    units
}

/// No contact: until the county is short, every household line is the roll's own and no hour is
/// charged. Returns the number of sessions checked.
fn assert_no_contact_moves_nothing(run: &Run) -> usize {
    let mut checked = 0;
    for period in &run.periods {
        let Some(session) = &period.observed.session else {
            continue;
        };
        if Run::is_short(session) {
            continue;
        }
        let listed = listed_units_by_group(&run.config, session);
        for line in &session.lines {
            assert_eq!(
                line.units,
                listed[usize::try_from(line.group).expect("a group index")],
                "period {}: the line of group {} is the roll's own",
                period.tick,
                line.group
            );
        }
        assert_eq!(
            session.lines.iter().map(|line| line.units).sum::<u64>(),
            session.household_units_listed
        );
        assert!(
            session.rows.iter().all(|row| row.hours_in_room == 0
                && row.hours_bringing == 0
                && row.asked_paid == 0),
            "period {}: with no contact nobody asks and no hour is charged",
            period.tick
        );
        checked += 1;
    }
    assert!(
        checked > 0,
        "at least one session before the county is short"
    );
    checked
}

/// The households of a contacted position's family: its group, band and crew. A household's
/// answers move as hires and layoffs touch its crew, so a family is followed by these three.
fn family_rows<'a>(session: &'a SessionRecord, key: &PositionKey) -> Vec<&'a SessionRow> {
    session
        .rows
        .iter()
        .filter(|row| {
            (row.key.group, row.key.band, row.key.crew) == (key.group, key.band, key.crew)
        })
        .collect()
}

fn came(rows: &[&SessionRow]) -> u64 {
    rows.iter()
        .map(|row| row.asked_paid + row.came_from_roll)
        .sum()
}

/// What the first session after a contact must show. The first contact is chosen by the county's
/// own preview in the period before, from the same close, so it must move a unit. A later contact
/// lands a period after its preview, on the facts of one more close, so it need only be reached;
/// what its session did is recorded either way.
#[derive(Clone, Copy)]
enum Landing {
    UnitMoves,
    ReachedOnly,
}

/// What a contact did in the sessions after it: a unit moves in the first, the households that
/// came double each session while a place stays open and the family has households left, and the
/// first session without a place is named. Returns the figures for the record.
fn assert_contact_spreads(
    run: &Run,
    contact_period: u64,
    key: &PositionKey,
    landing: Landing,
) -> Value {
    let first = contact_period + 1;
    let sessions: Vec<(u64, &SessionRecord)> = run
        .periods
        .iter()
        .filter(|period| period.tick >= first)
        .filter_map(|period| period.observed.session.as_ref().map(|s| (period.tick, s)))
        .collect();
    let (first_tick, first_session) = sessions.first().expect("a session after the contact");
    assert_eq!(*first_tick, first);
    assert_eq!(
        first_session.contact,
        Some((*key, ContactOutcome::Reached)),
        "the contact lands in the first session after it"
    );
    let family = family_rows(first_session, key);
    if matches!(landing, Landing::UnitMoves) {
        assert!(
            family.iter().map(|row| row.asked_paid).sum::<u64>() >= 1
                && first_session
                    .rows
                    .iter()
                    .map(|row| row.units_unpaid)
                    .sum::<u64>()
                    >= 1,
            "a unit moves in the first session after the contact"
        );
    }
    let mut figures = Vec::new();
    let mut doubling_ends: Option<u64> = None;
    for (index, (tick, session)) in sessions.iter().enumerate() {
        let family = family_rows(session, key);
        let reached: u64 = family.iter().map(|row| row.reached).sum();
        let households_left: u64 = family.iter().map(|row| row.households - row.reached).sum();
        let no_place: u64 = family.iter().map(|row| row.asked_no_place).sum();
        let brought: u64 = family.iter().map(|row| row.brought).sum();
        figures.push(
            json!({"session": tick, "reached": reached, "came": came(&family),
            "asked": family.iter().map(|row| row.asked).sum::<u64>(),
            "asked_no_place": no_place, "brought": brought, "households_left": households_left}),
        );
        let open = no_place == 0 && came(&family) > 0 && households_left >= came(&family);
        if doubling_ends.is_none() && !open {
            doubling_ends = Some(*tick);
        }
        if doubling_ends.is_some() {
            continue;
        }
        let Some((next_tick, next)) = sessions.get(index + 1) else {
            continue;
        };
        let next_reached: u64 = family_rows(next, key).iter().map(|row| row.reached).sum();
        assert_eq!(
            next_reached,
            reached * 2,
            "session {tick}: every household that came brought one, so the next session ({next_tick}) \
             holds twice the reached households"
        );
    }
    json!({"contact_period": contact_period, "key": key, "doubling_held_through_session":
        doubling_ends.map_or(Value::Null, |end| json!(end - 1)),
        "doubling_ended_in_session": doubling_ends, "sessions": figures})
}

/// After the county's money for relief ends, nobody is paid.
fn assert_nobody_paid_when_relief_ends(run: &Run) -> Option<u64> {
    let mut ended = None;
    for period in &run.periods {
        let Some(session) = &period.observed.session else {
            continue;
        };
        if session.relief_micros == 0 {
            ended.get_or_insert(period.tick);
            assert!(
                session.lines.is_empty() && session.rows.iter().all(|row| row.asked_paid == 0),
                "period {}: with no money for relief nobody is paid",
                period.tick
            );
        }
    }
    ended
}

/// The figures no player move can touch: the first class, the spending limit and every tax rate
/// (whoever receives the tax), compared period by period across runs.
fn untouchable(run: &Run) -> Vec<Value> {
    run.periods
        .iter()
        .map(|period| {
            let first_class: Vec<(u8, u64, &str)> = period
                .observed
                .budgets
                .iter()
                .filter(|line| {
                    line.treatment != PublicTransferTreatment::HouseholdIncomeSupport as u8
                })
                .map(|line| (line.treatment, line.claims, line.requested_micros.as_str()))
                .collect();
            let rates = &period.observed.tax_rates;
            json!({"period": period.tick,
                "first_class_micros": micros_string(period.observed.facts.first_class_micros),
                "spending_limit_micros": micros_string(period.observed.facts.spending_limit_micros),
                "first_class_requested": first_class, "tax_rates": rates})
        })
        .collect()
}

fn assert_untouchable_alike(runs: &[&Run]) {
    let base = untouchable(runs[0]);
    for run in &runs[1..] {
        let other = untouchable(run);
        assert_eq!(
            base.len(),
            other.len(),
            "{}: as many periods as the no-contact run, so every period is compared",
            run.line.name()
        );
        for (left, right) in base.iter().zip(&other) {
            assert_eq!(
                left,
                right,
                "{}: the first class, the spending limit and the tax rates match the no-contact run",
                run.line.name()
            );
        }
    }
}

fn total_tax(period: &Period) -> i128 {
    period
        .observed
        .taxes
        .iter()
        .map(|line| {
            line.collected_micros
                .parse::<i128>()
                .expect("a collected amount")
        })
        .sum()
}

/// The difference in the county's cash and tax receipts between two runs, period by period.
fn difference(left: &Run, right: &Run) -> Vec<Value> {
    left.periods
        .iter()
        .zip(&right.periods)
        .map(|(a, b)| {
            json!({"period": a.tick,
                "cash_micros": micros_string(b.observed.facts.cash_micros - a.observed.facts.cash_micros),
                "tax_collected_micros": micros_string(total_tax(b) - total_tax(a))})
        })
        .collect()
}

// ---------------------------------------------------------------------------------------------
// Step 4: the other bounds of the declared placement.

/// Whether a household in this position has a wage in the period the facts report: it has a crew,
/// somebody at work, a crew that is paid a wage, and wages that accrued to that crew.
fn has_wage(config: &CountyReviewConfig, facts: &CountyPeriodFacts, key: &PositionKey) -> bool {
    let Some(crew) = key.crew else {
        return false;
    };
    let paid_a_wage = usize::try_from(crew)
        .ok()
        .and_then(|at| config.crews.get(at))
        .is_some_and(|configured| configured.pay_mode == PayMode::Wage);
    let accrued = facts
        .crews
        .iter()
        .find(|reported| reported.crew == crew)
        .is_some_and(|reported| reported.accrued_wages_micros > 0);
    key.at_work >= 1 && paid_a_wage && accrued
}

/// Units held by households with no wage: no crew, nobody at work, a crew that is not paid a wage,
/// or a crew whose wages accrued to nothing in the period the facts report.
fn units_without_wage(
    config: &CountyReviewConfig,
    facts: &CountyPeriodFacts,
    roster: &Roster,
) -> u64 {
    roster
        .rows
        .iter()
        .filter(|row| !has_wage(config, facts, &row.key))
        .map(|row| u64::from(row.key.units) * row.households)
        .sum()
}

/// A county of one group and three crews, which pay a wage, a working owner and a wage, with the
/// facts of one period in which the third crew's wages accrued to nothing.
fn wage_county() -> (CountyReviewConfig, CountyPeriodFacts) {
    let crew = |at: u8, pay_mode| CountyReviewCrew {
        crew_id: [at; 32],
        group: 0,
        site_id: [at; 32],
        unit_id: [at; 32],
        workplace_label: format!("Crew {at}"),
        pay_mode,
    };
    let config = CountyReviewConfig {
        schema_version: babylon_practice_contract::COUNTY_REVIEW_SCHEMA_VERSION,
        campaign_id: [1; 16],
        actor_id: 9,
        authority_id: [2; 16],
        county: *b"26163",
        administration_label: "Administration".to_owned(),
        claimants_body_label: "Claimants".to_owned(),
        aid_body_label: "Aid".to_owned(),
        public_account_id: [3; 32],
        unit_price_micros: 280_000_000,
        going_wage_micros: 24_000_000,
        session_hours: 2,
        bring_hours: 2,
        first_session_period: 1,
        groups: vec![CountyReviewGroup {
            group_id: [1; 32],
            label: "Wayne households".to_owned(),
            kind: GroupKind::Ordinary,
            opening_households: 10,
            roll_units: 10,
            has_ownership_income: false,
            receives_mutual_aid: false,
        }],
        crews: vec![
            crew(0, PayMode::Wage),
            crew(1, PayMode::WorkingOwner),
            crew(2, PayMode::Wage),
        ],
        content_digest: [6; 32],
        policy_source_digest: [7; 32],
    };
    let reported = |crew: u32, accrued_wages_micros: i128| CrewPeriodFacts {
        crew,
        accrued_wages_micros,
        opening_at_work: 1,
        opening_seeking: 0,
        left_at_work: 0,
        left_seeking: 0,
        hires: 0,
        separations: 0,
        closing_at_work: 1,
        closing_seeking: 0,
    };
    let facts = CountyPeriodFacts {
        period: 5,
        crews: vec![
            reported(0, 24_000_000),
            reported(1, 24_000_000),
            reported(2, 0),
        ],
        groups: vec![],
        cash_micros: 0,
        cash_floor_micros: 0,
        spending_limit_micros: 0,
        first_class_micros: 0,
    };
    (config, facts)
}

#[test]
fn a_household_has_a_wage_only_where_the_crew_is_paid_one_and_its_wages_accrued() {
    let (config, facts) = wage_county();
    let at = |crew: Option<u32>, at_work: u16| PositionKey {
        group: 0,
        band: Band::Bottom50,
        crew,
        at_work,
        seeking: 0,
        units: 1,
    };
    assert!(has_wage(&config, &facts, &at(Some(0), 1)), "a paid crew");
    assert!(!has_wage(&config, &facts, &at(None, 1)), "no crew");
    assert!(
        !has_wage(&config, &facts, &at(Some(0), 0)),
        "nobody at work"
    );
    assert!(
        !has_wage(&config, &facts, &at(Some(1), 1)),
        "a working owner is paid no wage"
    );
    assert!(
        !has_wage(&config, &facts, &at(Some(2), 1)),
        "a crew whose wages accrued to nothing pays none in that period"
    );
    assert!(
        !has_wage(&config, &facts, &at(Some(7), 1)),
        "a crew the config does not hold pays none"
    );
}

#[test]
fn the_record_of_an_action_carries_a_refused_request_only_when_there_was_one() {
    let action = |error: Option<&str>| Action {
        view_period: 3,
        choice: OrganizerChoice::LocalAid,
        allocation: OrganizerAllocation::None,
        nonce: [0; 16],
        preview: None,
        submitted: false,
        error: error.map(str::to_owned),
        probes: Vec::new(),
    };
    let quiet = serde_json::to_value(action(None)).expect("the action serializes");
    assert!(
        quiet.get("error").is_none(),
        "no error field when the session answered the preview: {quiet}"
    );
    let refused = serde_json::to_value(action(Some("OrganizerRefused"))).expect("it serializes");
    assert_eq!(refused["error"], "OrganizerRefused");
}

/// Replays the recorded facts and contacts through the kernel under one placement. Returns the
/// units held by households with no wage after each period.
fn replay_placement(record: &Value, placement: Placement) -> Vec<u64> {
    let config: CountyReviewConfig =
        serde_json::from_value(record["county_config"].clone()).expect("the recorded config");
    let mut roster: Roster =
        serde_json::from_value(record["opening_roster"].clone()).expect("the recorded opening");
    let mut held = Vec::new();
    for period in record["periods"].as_array().expect("the recorded periods") {
        let facts: CountyPeriodFacts =
            serde_json::from_value(period["facts"].clone()).expect("the recorded facts");
        roster = if facts.period < config.first_session_period {
            babylon_practice_contract::roll_forward_with(&config, &roster, &facts, placement)
                .expect("a roster rolls")
        } else {
            let contact: Option<PositionKey> = period["session"]["contact"]
                .as_array()
                .map(|pair| serde_json::from_value(pair[0].clone()).expect("a recorded contact"));
            let outcome =
                babylon_practice_contract::hold_session(&config, &roster, &facts, contact)
                    .expect("a session is held");
            babylon_practice_contract::roll_forward_with(
                &config,
                &outcome.roster,
                &facts,
                placement,
            )
            .expect("a roster rolls")
        };
        held.push(units_without_wage(&config, &facts, &roster));
    }
    held
}

fn placement_bounds(record: &Value, run: &Run) -> Value {
    let declared = replay_placement(record, Placement::Declared);
    let actual: Vec<u64> = run
        .periods
        .iter()
        .map(|period| {
            units_without_wage(&run.config, &period.observed.facts, &period.observed.roster)
        })
        .collect();
    assert_eq!(
        declared, actual,
        "the kernel replay of the declared placement reproduces the run"
    );
    let first = replay_placement(record, Placement::HoldersFirst);
    let last = replay_placement(record, Placement::HoldersLast);
    let periods: Vec<Value> = run
        .periods
        .iter()
        .enumerate()
        .map(|(index, period)| {
            json!({"period": period.tick, "declared": declared[index],
                "holders_first": first[index], "holders_last": last[index]})
        })
        .collect();
    json!({"version": 1, "line": run.line.name(),
        "meaning": "units held by households with no wage after each period, under the declared \
            placement and its two other bounds, replayed from the record's opening roster, \
            facts and contacts. A report for the Director, not a pass or a fail.",
        "periods": periods})
}

// ---------------------------------------------------------------------------------------------
// The tests.

fn assert_every_run(run: &Run) {
    assert_eq!(
        run.first_short_period, run.first_short_hint,
        "the player's reading of the county and the session record agree on the first short session"
    );
    assert_bands(run);
    assert_county_keeps_its_word(run);
    assert_nobody_paid_when_relief_ends(run);
}

fn contact_key(run: &Run, index: usize) -> (u64, PositionKey) {
    run.actions
        .iter()
        .filter_map(|action| match action.choice {
            OrganizerChoice::ReviewContact(key) if action.submitted => {
                Some((action.view_period, key))
            }
            _ => None,
        })
        .nth(index)
        .expect("the contact was made")
}

fn replay_agrees(original: &Run, foundation: &str, tails: &[RuntimeSessionTail]) {
    assert_eq!(original.foundation, foundation, "the same seed");
    assert_eq!(original.periods.len(), tails.len());
    for (period, tail) in original.periods.iter().zip(tails) {
        assert_eq!(
            &period.tail, tail,
            "period {}: the replay's register digest equals the recorded one",
            period.tick
        );
    }
}

/// A short run of the driver: no contact and one position, each through period 6. It
/// proves the driver, the reads and the assertions before the 40-minute test is started. Its
/// records go to the temporary directory, not to the reports.
#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and national source"]
fn county_review_playthroughs_smoke() {
    let directory = std::env::temp_dir().join("county-review-smoke");
    let none = play_and_record(
        &Spec {
            line: Line::NoContact,
            replay: None,
            last_period: Some(6),
            reopen: false,
        },
        &directory,
    );
    assert_every_run(&none);
    assert_no_contact_moves_nothing(&none);
    let one = play_and_record(
        &Spec {
            line: Line::OnePosition,
            replay: None,
            last_period: Some(6),
            reopen: true,
        },
        &directory,
    );
    assert_every_run(&one);
    assert_eq!(none.foundation, one.foundation, "one opening");
    let (period, key) = contact_key(&one, 0);
    let spread = assert_contact_spreads(&one, period, &key, Landing::UnitMoves);
    assert_untouchable_alike(&[&none, &one]);
    eprintln!("smoke: spread {spread}");
    let bounds = placement_bounds(&run_json(&one), &one);
    eprintln!("smoke: placement bounds {bounds}");
    let last = one.periods.last().expect("periods").tick;
    let (foundation, tails) = replay(Line::OnePosition, &one.actions, last);
    replay_agrees(&one, &foundation, &tails);
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and national source"]
fn county_review_playthroughs() {
    let directory = reports_dir();
    let live = |line, reopen| Spec {
        line,
        replay: None,
        last_period: None,
        reopen,
    };
    let none = play_and_record(&live(Line::NoContact, false), &directory);
    assert_every_run(&none);
    let sessions = assert_no_contact_moves_nothing(&none);
    let one = play_and_record(&live(Line::OnePosition, true), &directory);
    assert_every_run(&one);
    let (period, key) = contact_key(&one, 0);
    let one_spread = assert_contact_spreads(&one, period, &key, Landing::UnitMoves);
    let two = play_and_record(&live(Line::TwoPositions, false), &directory);
    assert_every_run(&two);
    let (first_period, first) = contact_key(&two, 0);
    let (second_period, second) = contact_key(&two, 1);
    assert_ne!(first.crew, second.crew);
    let two_spreads = [
        assert_contact_spreads(&two, first_period, &first, Landing::UnitMoves),
        assert_contact_spreads(&two, second_period, &second, Landing::ReachedOnly),
    ];
    let food = play_and_record(&live(Line::FoodRuns, false), &directory);
    assert_every_run(&food);
    // One opening: the Ready foundation digest, which is the seed, is the same in every run.
    for run in [&one, &two, &food] {
        assert_eq!(
            none.foundation,
            run.foundation,
            "{}: the same opening as the no-contact run",
            run.line.name()
        );
    }
    assert_untouchable_alike(&[&none, &one, &two, &food]);
    let finals: Vec<_> = [&none, &one, &two, &food]
        .iter()
        .map(|run| run.periods.last().expect("periods").tail.world_hash.clone())
        .collect();
    for (index, left) in finals.iter().enumerate() {
        for right in &finals[index + 1..] {
            assert_ne!(left, right, "the four final records differ");
        }
    }
    eprintln!(
        "difference in cash and tax receipts, one position against no contact: {}",
        json!(difference(&none, &one))
    );
    let mut records = Vec::new();
    for (run, spreads) in [
        (&none, json!({"sessions_before_short_checked": sessions})),
        (&one, json!([one_spread])),
        (&two, json!(two_spreads)),
        (&food, Value::Null),
    ] {
        let mut record = run_json(run);
        record["contact_spread"] = spreads;
        record["against_no_contact"] = json!(difference(&none, run));
        record["relief_ended_in_session"] = json!(assert_nobody_paid_when_relief_ends(run));
        records.push((run.line.name(), record));
    }
    for (name, record) in &records {
        let bytes = write_record(&directory, &format!("{name}.json"), record);
        eprintln!("county_review: {name}.json is {bytes} bytes");
    }
    let bounds = placement_bounds(&records[1].1, &one);
    write_record(&directory, "placement-bounds.json", &bounds);
    let last = one.periods.last().expect("periods").tick;
    let (foundation, tails) = replay(Line::OnePosition, &one.actions, last);
    replay_agrees(&one, &foundation, &tails);
    eprintln!("county_review: the replay's register digest equals the record's in every period");
}
