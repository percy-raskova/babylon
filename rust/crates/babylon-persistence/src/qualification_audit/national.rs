//! Measured national `SQLite` qualification runner and its persisted evidence.
//!
//! The runner builds the real national foundation from the captured sources,
//! stores its complete opening, advances the actual material session, and writes
//! every ordinary advance and positive-growth charge. It never reconstructs the
//! economy from a report and never consults installed package files.
//!
//! Cold open is the store contract this task consumes: open the durable campaign
//! and answer the scoped player queries. Re-adjudicating the economy on reopen is
//! the Task 14 cutover's concern; this runner reports that scope explicitly.

use std::collections::BTreeMap;
use std::collections::BTreeSet;
use std::ffi::OsStr;
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;
use std::fs::OpenOptions;
use std::io::ErrorKind;
use std::path::Path;
use std::path::PathBuf;
use std::time::Instant;

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::content_digest;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_replay::MaterialReplayError;
use babylon_tick::material_replay::MaterialReplaySession;
use babylon_tick::material_replay::PreparedMaterialTick;
use babylon_tick::replay_session::ReplayCommitDisposition;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use super::policy::Refusal;
use super::policy::{
    AdvanceSample, MemorySummary, NationalSqlitePolicy, PeriodCharge, QualificationRun,
    QuerySample, Verdict,
};
use crate::content_package;
use crate::economic_catalog::CapturedEconomicCatalog;
use crate::identity::CampaignId;
use crate::material_storage::EncodedMaterial;
use crate::sqlite_store::chunks::{ChunkSection, ContentEntryKind, JournalKind, SubjectKind};
use crate::sqlite_store::codec::{self, PayloadBudget};
use crate::sqlite_store::retention;
use crate::sqlite_store::{
    AdmittedContent, AdmittedContentEntry, AdmittedOpening, CampaignHandle, CommittedPeriod,
    PlayerQuery, PreparedJournalRecord, PreparedKnowledgeGrant, PreparedPeriod, PreparedSubject,
    ReadError, SaveError, SqliteCampaignStore, StateChunk, TickIdentityPolicy,
    MAX_STATE_CHUNK_BYTES,
};
use crate::CampaignFoundation;
use crate::CampaignQueryReader;

/// Persisted schema of one measured national run.
pub const RUN_SCHEMA: &str = "babylon.qualification.national-sqlite.run.v1";
/// Persisted schema of one cold-open measurement.
pub const COLD_OPEN_SCHEMA: &str = "babylon.qualification.national-sqlite.cold-open.v1";
/// Persisted schema of one evaluated rung.
pub const VERDICT_SCHEMA: &str = "babylon.qualification.national-sqlite.verdict.v1";

const CAMPAIGN_UUID: u128 = 0x2810_0000_0000_0000_0000_0000_0000_0013;
const REPLAY_SEED: i64 = 319;
const SESSION_ID: &str = "national-world";
const PLAYER_ID: [u8; 8] = *b"national";
const HOME_COUNTY: [u8; 5] = *b"26163";
const KNOWN_COUNTIES: [[u8; 5]; 8] = [
    *b"26163", *b"26099", *b"26125", *b"26087", *b"26147", *b"26115", *b"26093", *b"26161",
];
const RESTART_DOMAIN: &[u8] = b"babylon.national-restart.v1\0";
const CATALOG_ENTRY_KEY: &[u8] = b"national-economic-catalog";
const BUNDLE_ENTRY_KEY: &[u8] = b"national-foundation-content-bundle";

/// Typed refusal of one qualification run.
#[derive(Debug)]
pub enum QualificationError {
    /// Host I/O failed.
    Io(std::io::Error),
    /// Evidence JSON failed to encode or decode.
    Json(serde_json::Error),
    /// The `SQLite` store refused.
    Store(SaveError),
    /// A scoped player read refused.
    Read(ReadError),
    /// National source capture or compilation refused.
    Catalog(String),
    /// Material runtime construction refused.
    Material(String),
    /// Material replay refused before a candidate was committed.
    Replay(MaterialReplayError),
    /// The frozen policy refused.
    Policy(Refusal),
    /// A measured artifact was absent or inconsistent.
    Evidence(String),
}

impl std::fmt::Display for QualificationError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::Io(error) => write!(formatter, "national qualification I/O refused: {error}"),
            Self::Json(error) => {
                write!(
                    formatter,
                    "national qualification evidence refused: {error}"
                )
            }
            Self::Store(error) => {
                write!(formatter, "national qualification store refused: {error}")
            }
            Self::Read(error) => write!(formatter, "national qualification read refused: {error}"),
            Self::Catalog(reason) => {
                write!(
                    formatter,
                    "national qualification catalog refused: {reason}"
                )
            }
            Self::Material(reason) => {
                write!(
                    formatter,
                    "national qualification runtime refused: {reason}"
                )
            }
            Self::Replay(error) => {
                write!(formatter, "national qualification replay refused: {error}")
            }
            Self::Policy(error) => {
                write!(formatter, "national qualification policy refused: {error}")
            }
            Self::Evidence(reason) => {
                write!(
                    formatter,
                    "national qualification evidence refused: {reason}"
                )
            }
        }
    }
}

impl std::error::Error for QualificationError {}

impl From<std::io::Error> for QualificationError {
    fn from(error: std::io::Error) -> Self {
        Self::Io(error)
    }
}

impl From<serde_json::Error> for QualificationError {
    fn from(error: serde_json::Error) -> Self {
        Self::Json(error)
    }
}

impl From<SaveError> for QualificationError {
    fn from(error: SaveError) -> Self {
        Self::Store(error)
    }
}

impl From<ReadError> for QualificationError {
    fn from(error: ReadError) -> Self {
        Self::Read(error)
    }
}

impl From<Refusal> for QualificationError {
    fn from(error: Refusal) -> Self {
        Self::Policy(error)
    }
}

/// One measured national run.
#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct RunManifest {
    /// Persisted schema name.
    pub schema: String,
    /// Durable campaign identity.
    pub campaign: String,
    /// Runtime build identity under which the campaign was admitted.
    pub build_hash: String,
    /// Ordinary advances requested.
    pub periods: u64,
    /// Opening restart-root decoded bytes.
    pub opening_decoded_bytes: u64,
    /// Physical store bytes immediately after opening creation.
    pub opening_file_bytes: u64,
    /// Physical store bytes after the final commit.
    pub final_store_bytes: u64,
    /// Write-ahead-log bytes after the final commit.
    pub final_wal_bytes: u64,
    /// Wall-clock nanoseconds spent in the measured run.
    pub elapsed_ns: u64,
    /// Every ordinary advance.
    pub advances: Vec<AdvanceSample>,
    /// Every committed period's positive growth charge.
    pub charges: Vec<PeriodCharge>,
    /// Decoded positive growth by component for the failing-metric breakdown.
    #[serde(default)]
    pub breakdowns: Vec<PeriodBreakdown>,
    /// Warm scoped player queries measured after the final commit.
    pub warm_queries: Vec<QuerySample>,
}

/// One committed period's decoded positive growth by retained component.
#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct PeriodBreakdown {
    /// Completed period.
    pub period: u64,
    /// Compact material state package bytes.
    pub state_package_bytes: u64,
    /// Material receipt package bytes retained with the restart root.
    pub receipt_package_bytes: u64,
    /// Period-local identity lookup delta bytes.
    pub lookup_delta_bytes: u64,
    /// Stable graph section bytes.
    pub stable_graph_bytes: u64,
    /// Material semantic-state section bytes.
    pub semantic_state_bytes: u64,
    /// Resolver, environment, identity, seed and digest section bytes.
    pub metadata_bytes: u64,
    /// Permanent journal record bytes written by the caller.
    pub journal_bytes: u64,
    /// Earned knowledge payload bytes written by the caller.
    pub knowledge_bytes: u64,
    /// Charged stored journal payload bytes.
    #[serde(default)]
    pub journal_stored_bytes: u64,
    /// Charged stored knowledge payload bytes.
    #[serde(default)]
    pub knowledge_stored_bytes: u64,
    /// Charged stored bytes and fragment counts by restart-root section.
    #[serde(default)]
    pub sections: Vec<SectionCharge>,
    /// Every restart-root fragment this period changed.
    #[serde(default)]
    pub fragments: Vec<FragmentChange>,
    /// Stored charge the durable acknowledgement added beyond the encoded
    /// candidate. It has no component attribution and is reported, never hidden.
    #[serde(default)]
    pub acknowledged_residual_bytes: u64,
}

/// How one restart-root fragment position differs from the previous snapshot.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FragmentChangeKind {
    /// The previous snapshot held no fragment at this position.
    Added,
    /// The previous snapshot held different bytes at this position.
    Rewritten,
    /// The previous snapshot held a fragment this snapshot omits.
    Retired,
}

/// One restart-root fragment the period changed or retired.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct FragmentChange {
    /// Closed section code of the fragment.
    pub section: i64,
    /// Manifest ordinal inside the section.
    pub ordinal: u32,
    /// How this position differs from the previous snapshot.
    pub change: FragmentChangeKind,
    /// Decoded bytes this snapshot holds at the position; zero when retired.
    pub decoded_bytes: u64,
    /// Decoded bytes the previous snapshot held at the position.
    pub prior_decoded_bytes: u64,
    /// Charged stored payload bytes; zero when nothing was written.
    pub stored_bytes: u64,
}

/// Charged stored bytes one restart-root section contributed in a period.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SectionCharge {
    /// Closed section code.
    pub section: i64,
    /// Fragments this section added or rewrote.
    pub charged_fragments: u64,
    /// Decoded bytes of the fragments this section added or rewrote.
    pub decoded_bytes: u64,
    /// Decoded bytes previously held at changed and retired positions.
    pub prior_decoded_bytes: u64,
    /// Charged stored payload bytes of the fragments this section wrote.
    pub stored_bytes: u64,
}

/// One cold-open measurement.
#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct ColdOpenManifest {
    /// Persisted schema name.
    pub schema: String,
    /// Durable campaign identity.
    pub campaign: String,
    /// Cold open elapsed nanoseconds.
    pub cold_open_ns: u64,
    /// First scoped query after the open.
    pub cold_queries: Vec<QuerySample>,
    /// Repeated warm scoped queries.
    pub warm_queries: Vec<QuerySample>,
    /// Physical store bytes observed by the reader.
    pub store_bytes: u64,
    /// Write-ahead-log bytes observed by the reader.
    pub wal_bytes: u64,
}

/// One evaluated rung persisted for the ladder driver.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EvaluationManifest {
    /// Persisted schema name.
    pub schema: String,
    /// Frozen policy digest.
    pub policy_sha256: String,
    /// Requested horizon.
    pub horizon: u64,
    /// Full merged measurement input.
    pub run: QualificationRun,
    /// Policy verdict.
    pub verdict: Verdict,
}

/// Build the complete national opening and advance exactly `periods` times.
///
/// # Errors
/// Refuses national source capture, foundation construction, store creation,
/// replay, encoding or evidence publication.
#[allow(
    clippy::too_many_lines,
    reason = "`run_national` keeps one measured create/advance/commit/briefing sequence in order"
)]
pub fn run_national(
    store_path: &Path,
    output_directory: &Path,
    periods: u64,
) -> Result<RunManifest, QualificationError> {
    if periods == 0 || !store_path.is_absolute() || !output_directory.is_absolute() {
        return Err(QualificationError::Evidence(
            "the runner needs a positive horizon and absolute paths".to_owned(),
        ));
    }
    std::fs::create_dir_all(output_directory)?;
    require_no_evidence(output_directory)?;
    let started = Instant::now();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(CAMPAIGN_UUID));
    let captured = CapturedEconomicCatalog::capture_national_campaign(
        crate::economic_catalog::national_catalog_input(),
        campaign,
    )
    .map_err(|error| QualificationError::Catalog(error.to_string()))?;
    let catalog_bytes = captured.canonical_bytes().to_vec();
    let foundation = captured
        .create_foundation(
            ReplaySessionId::try_from(SESSION_ID)
                .map_err(|_| QualificationError::Material("session identity".to_owned()))?,
            ReplaySeed::new(REPLAY_SEED),
        )
        .map_err(|error| QualificationError::Material(error.to_string()))?;
    let opening_register_bytes = foundation.initial_register().canonical_bytes().to_vec();
    let mut opening = material_opening(foundation.graph_foundation(), &opening_register_bytes)?;
    let content = admitted_content(campaign, &catalog_bytes, foundation.graph_foundation());
    drop(catalog_bytes);
    let mut session = foundation
        .into_session()
        .map_err(|error| QualificationError::Material(error.to_string()))?;
    opening.world_hash = session
        .current_world_hash()
        .map_err(QualificationError::Replay)?;
    opening.state_hash = session.material().digest();
    let opening_decoded_bytes = opening
        .chunks
        .iter()
        .map(|chunk| u64::try_from(chunk.bytes.len()).unwrap_or(u64::MAX))
        .chain(
            content
                .entries
                .iter()
                .map(|entry| u64::try_from(entry.bytes.len()).unwrap_or(u64::MAX)),
        )
        .fold(0_u64, u64::saturating_add);
    let mut handle = SqliteCampaignStore::create(store_path, content, opening)?;
    let opening_file_bytes = store_bytes(store_path)?;
    let mut previous = previous_chunks(&handle);
    let opening_lookup = crate::material_storage::seed(session.catalog(), &opening_register_bytes)
        .map_err(|error| QualificationError::Material(error.to_string()))?;
    drop(opening_register_bytes);
    let mut lookup_chain = crate::material_storage::initial_lookup_chain(&opening_lookup)
        .map_err(|error| QualificationError::Material(error.to_string()))?;
    let mut advances = Vec::with_capacity(usize::try_from(periods).map_err(|_| {
        QualificationError::Evidence("the requested horizon does not fit usize".to_owned())
    })?);
    let mut charges = Vec::with_capacity(advances.capacity());
    let mut breakdowns = Vec::with_capacity(advances.capacity());
    for _ in 0..periods {
        let actions = next_actions(&session)?;
        let judgment_started = Instant::now();
        let prepared = session
            .prepare_advance(&actions)
            .map_err(QualificationError::Replay)?;
        let judgment_ns = elapsed_ns(judgment_started)?;
        let period = prepared.identity().resolve_tick();
        let encoding_started = Instant::now();
        let encoded = crate::material_storage::encode(
            prepared.material().register(),
            prepared.material().receipt_bytes(),
            &opening_lookup,
            lookup_chain,
        )
        .map_err(|error| QualificationError::Material(error.to_string()))?;
        let EncodedMaterial {
            register_storage_bytes: state_package,
            receipt_storage_bytes: receipt_package,
            lookup_delta_bytes: lookup_delta,
            lookup: typed_lookup,
            lookup_chain: chain,
        } = encoded;
        drop(typed_lookup);
        lookup_chain = chain;
        let restart_package = restart_package(
            &state_package,
            &receipt_package,
            &lookup_delta,
            lookup_chain,
        );
        let chunks = period_chunks(&prepared, &restart_package)?;
        let journal = briefing_journal(period);
        let knowledge = briefing_knowledge(period);
        let (mut charge, mut breakdown) = period_accounting(
            period,
            &RestartParts {
                state: &state_package,
                receipts: &receipt_package,
                lookup: &lookup_delta,
            },
            &chunks,
            &journal,
            &knowledge,
            &previous,
        )?;
        drop((state_package, receipt_package, lookup_delta));
        let candidate = PreparedPeriod {
            period,
            expected_world_hash: prepared.identity().prior_world_hash(),
            world_hash: prepared.identity().result_world_hash(),
            state_hash: prepared.material().register().digest(),
            chunks,
            journal,
            knowledge,
            detail: Vec::new(),
            tick_identity: Some(*prepared.identity()),
        };
        let encoding_ns = elapsed_ns(encoding_started)?;
        let mut committed: Option<CommittedPeriod> = None;
        let mut commit_ns = 0_u64;
        let mut sink = CollectingSink::default();
        let (identity, disposition) = session
            .commit_prepared_and_publish(&mut sink, prepared, |_, _| {
                let commit_started = Instant::now();
                let acknowledged = handle.commit(candidate)?;
                commit_ns = commit_started
                    .elapsed()
                    .as_nanos()
                    .try_into()
                    .unwrap_or(u64::MAX);
                committed = Some(acknowledged);
                Ok::<ReplayCommitDisposition, SaveError>(ReplayCommitDisposition::Committed)
            })
            .map_err(|error| match error {
                babylon_tick::material_replay::MaterialCommitError::Preflight(error) => {
                    QualificationError::Replay(error)
                }
                babylon_tick::material_replay::MaterialCommitError::Commit(error) => {
                    QualificationError::Store(error)
                }
            })?;
        if disposition != ReplayCommitDisposition::Committed {
            return Err(QualificationError::Evidence(
                "the material period was not committed".to_owned(),
            ));
        }
        let acknowledged = committed.ok_or_else(|| {
            QualificationError::Evidence("the durable acknowledgement is absent".to_owned())
        })?;
        if acknowledged.period != identity.resolve_tick() {
            return Err(QualificationError::Evidence(
                "the store acknowledged another period".to_owned(),
            ));
        }
        let briefing_started = Instant::now();
        measure_queries(&handle, 1)?;
        let briefing_ns = elapsed_ns(briefing_started)?;
        let total_ns = judgment_started
            .elapsed()
            .as_nanos()
            .try_into()
            .map_err(|_| QualificationError::Evidence("advance duration overflow".to_owned()))?;
        previous = previous_chunks(&handle);
        let summary_residual = acknowledged
            .retention
            .gross_bytes_added
            .saturating_sub(charge.decoded_added_bytes);
        charge.decoded_added_bytes = acknowledged.retention.gross_bytes_added;
        charge.stored_added_bytes = charge.stored_added_bytes.saturating_add(summary_residual);
        charge.unreachable_stored_bytes = acknowledged.retention.bytes_made_unreachable;
        breakdown.acknowledged_residual_bytes = summary_residual;
        charges.push(charge);
        breakdowns.push(breakdown);
        advances.push(AdvanceSample {
            period,
            judgment_ns,
            encoding_ns,
            commit_ns,
            briefing_ns,
            total_ns,
        });
        write_advance(
            output_directory,
            advances
                .last()
                .ok_or_else(|| QualificationError::Evidence("advance sample missing".to_owned()))?,
        )?;
    }
    let warm_queries = measure_queries(&handle, 32)?;
    let final_store_bytes = store_bytes(store_path)?;
    let final_wal_bytes = retention::wal_bytes(store_path);
    drop(handle);
    Ok(RunManifest {
        schema: RUN_SCHEMA.to_owned(),
        campaign: campaign.as_uuid().to_string(),
        build_hash: hex(&content_package::content_package_build_identity().hash()),
        periods,
        opening_decoded_bytes,
        opening_file_bytes,
        final_store_bytes,
        final_wal_bytes,
        elapsed_ns: elapsed_ns(started)?,
        advances,
        charges,
        breakdowns,
        warm_queries,
    })
}

/// Open the durable campaign and answer the scoped player view once cold.
///
/// # Errors
/// Refuses a missing campaign, a mismatched build, a damaged root, a refused
/// scoped read, or evidence publication.
pub fn run_cold_open(
    store_path: &Path,
    output_directory: &Path,
) -> Result<ColdOpenManifest, QualificationError> {
    if !store_path.is_absolute() || !output_directory.is_absolute() {
        return Err(QualificationError::Evidence(
            "the cold open needs absolute paths".to_owned(),
        ));
    }
    std::fs::create_dir_all(output_directory)?;
    let started = Instant::now();
    let handle = SqliteCampaignStore::open(
        store_path,
        content_package::content_package_build_identity(),
    )?;
    let cold_queries = measure_queries(&handle, 1)?;
    let cold_open_ns = elapsed_ns(started)?;
    let warm_queries = measure_queries(&handle, 16)?;
    Ok(ColdOpenManifest {
        schema: COLD_OPEN_SCHEMA.to_owned(),
        campaign: handle.campaign_id().as_uuid().to_string(),
        cold_open_ns,
        cold_queries,
        warm_queries,
        store_bytes: store_bytes(store_path)?,
        wal_bytes: retention::wal_bytes(store_path),
    })
}

/// Merge run, cold-open and sampled-memory evidence, then evaluate the policy.
///
/// # Errors
/// Refuses missing or inconsistent evidence, a policy mismatch, or evaluation
/// arithmetic. A measured target failure is a verdict, never an evaluator error.
pub fn evaluate_run(
    run_directory: &Path,
    policy_path: &Path,
    policy_sha256: [u8; 32],
    horizon: u64,
) -> Result<EvaluationManifest, QualificationError> {
    let run: RunManifest = read_json(&run_directory.join("run.json"))?;
    let cold: ColdOpenManifest = read_json(&run_directory.join("cold-open.json"))?;
    let memory: MemorySummary = read_json(&run_directory.join("memory.json"))?;
    if run.periods != horizon || run.advances.len() != usize::try_from(horizon).unwrap_or(0) {
        return Err(QualificationError::Evidence(
            "the run horizon and evidence count differ".to_owned(),
        ));
    }
    if run.campaign != cold.campaign {
        return Err(QualificationError::Evidence(
            "the run and cold open name different campaigns".to_owned(),
        ));
    }
    let policy = NationalSqlitePolicy::open(policy_path, policy_sha256)?;
    let mut warm = run.warm_queries.clone();
    warm.extend(cold.warm_queries.iter().copied());
    let merged = QualificationRun {
        advances: run.advances.clone(),
        cold_open_ns: cold.cold_open_ns,
        warm_queries: warm,
        cold_queries: cold.cold_queries.clone(),
        memory,
        charges: run.charges.clone(),
        opening_bytes: run.opening_file_bytes,
    };
    let verdict = policy.evaluate(&merged, horizon)?;
    let evaluation = EvaluationManifest {
        schema: VERDICT_SCHEMA.to_owned(),
        policy_sha256: hex(&policy_sha256),
        horizon,
        run: merged,
        verdict,
    };
    write_json(&evaluation_path(run_directory, policy_sha256), &evaluation)?;
    Ok(evaluation)
}

/// Name one verdict after the frozen contract that produced it.
///
/// Re-evaluation under another contract writes beside the earlier verdict
/// instead of replacing it, so an evidence directory keeps every verdict it
/// earned.
fn evaluation_path(directory: &Path, policy_sha256: [u8; 32]) -> PathBuf {
    directory.join(format!("evaluation-{}.json", hex(&policy_sha256)))
}

/// Evidence files one measured run publishes into its own directory.
const EVIDENCE_FILES: [&str; 3] = ["run.json", "cold-open.json", "memory.json"];
/// Every verdict is named `evaluation-<policy sha256>.json`.
const EVALUATION_PREFIX: &str = "evaluation-";
const EVALUATION_SUFFIX: &str = ".json";
/// The append-only advance log.
const ADVANCE_LOG: &str = "advances.jsonl";

/// Refuse a directory that already holds campaign evidence.
///
/// The ladder driver redirects each spawned process's stdout and stderr into
/// the run directory, so its own capture files exist before the measured
/// process starts and are not evidence. What is policed is what the run
/// publishes: a measured run appends every advance as it commits and writes
/// each manifest and each verdict once, so a reused directory would mix two
/// runs and let one verdict input be replaced by another.
fn require_no_evidence(directory: &Path) -> Result<(), QualificationError> {
    for entry in std::fs::read_dir(directory)? {
        let entry = entry?;
        let name = entry.file_name();
        if is_evidence_name(&name, entry.metadata()?.len()) {
            return Err(QualificationError::Evidence(format!(
                "the output directory {} already holds {name}",
                directory.display(),
                name = name.to_string_lossy()
            )));
        }
    }
    Ok(())
}

/// Whether one directory entry is an artifact a measured run owns.
fn is_evidence_name(name: &OsStr, length: u64) -> bool {
    let text = name.to_string_lossy();
    EVIDENCE_FILES.iter().any(|wanted| text == *wanted)
        || (text.starts_with(EVALUATION_PREFIX) && text.ends_with(EVALUATION_SUFFIX))
        || (text == ADVANCE_LOG && length > 0)
}

fn material_opening(
    graph: &CampaignFoundation,
    register: &[u8],
) -> Result<AdmittedOpening, QualificationError> {
    let mut chunks = Vec::new();
    push_section(
        &mut chunks,
        ChunkSection::StableGraph,
        graph.stable_graph_bytes(),
    )?;
    push_section(&mut chunks, ChunkSection::WorldRegisters, register)?;
    push_section(
        &mut chunks,
        ChunkSection::ResolverManifest,
        graph.resolver_manifest_bytes(),
    )?;
    push_section(
        &mut chunks,
        ChunkSection::PreparedEnvironment,
        graph.prepared_environment_bytes(),
    )?;
    push_section(
        &mut chunks,
        ChunkSection::ReplaySessionIdentity,
        graph.replay_session_identity().as_bytes(),
    )?;
    push_section(
        &mut chunks,
        ChunkSection::RngSeed,
        &graph.rng_seed().to_be_bytes(),
    )?;
    let digest = graph.content_digest();
    let mut content = Vec::with_capacity(64);
    content.extend_from_slice(&digest.defines_hash);
    content.extend_from_slice(&digest.rules_hash);
    push_section(&mut chunks, ChunkSection::ContentDigest, &content)?;
    push_section(
        &mut chunks,
        ChunkSection::ReferenceDigest,
        graph.reference_digest().as_bytes(),
    )?;
    Ok(AdmittedOpening {
        world_hash: [0; 32],
        state_hash: [0; 32],
        chunks,
    })
}

fn admitted_content(
    campaign: CampaignId,
    catalog: &[u8],
    graph: &CampaignFoundation,
) -> AdmittedContent {
    let mut entries = Vec::new();
    push_entry(
        &mut entries,
        ContentEntryKind::CompiledDefinitions,
        CATALOG_ENTRY_KEY,
        catalog,
    );
    push_entry(
        &mut entries,
        ContentEntryKind::OpeningMetadata,
        BUNDLE_ENTRY_KEY,
        graph.content_bundle().canonical_bytes(),
    );
    AdmittedContent {
        campaign_id: campaign,
        build: content_package::content_package_build_identity(),
        // The national run closes real material periods, so every committed
        // period must carry the identity its detached adjudication produced.
        tick_identity_policy: TickIdentityPolicy::Required,
        entries,
    }
}

fn push_entry(
    entries: &mut Vec<AdmittedContentEntry>,
    kind: ContentEntryKind,
    key: &[u8],
    bytes: &[u8],
) {
    if bytes.is_empty() {
        return;
    }
    for (ordinal, fragment) in bytes.chunks(MAX_STATE_CHUNK_BYTES).enumerate() {
        if let Ok(ordinal) = u32::try_from(ordinal) {
            entries.push(AdmittedContentEntry {
                kind,
                key: key.to_vec(),
                ordinal,
                bytes: fragment.to_vec(),
            });
        }
    }
}

fn push_section(
    chunks: &mut Vec<StateChunk>,
    section: ChunkSection,
    bytes: &[u8],
) -> Result<(), QualificationError> {
    if bytes.is_empty() {
        return Err(QualificationError::Evidence(format!(
            "section {} is empty",
            section.code()
        )));
    }
    for (ordinal, fragment) in bytes.chunks(MAX_STATE_CHUNK_BYTES).enumerate() {
        chunks.push(StateChunk {
            section,
            ordinal: u32::try_from(ordinal)
                .map_err(|_| QualificationError::Evidence("chunk ordinal overflow".to_owned()))?,
            bytes: fragment.to_vec(),
        });
    }
    Ok(())
}

fn restart_package(state: &[u8], receipts: &[u8], lookup: &[u8], chain: [u8; 32]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(
        RESTART_DOMAIN.len() + 24 + state.len() + receipts.len() + lookup.len() + 32,
    );
    bytes.extend_from_slice(RESTART_DOMAIN);
    for part in [state, receipts, lookup] {
        bytes.extend_from_slice(&(part.len() as u64).to_be_bytes());
        bytes.extend_from_slice(part);
    }
    bytes.extend_from_slice(&chain);
    bytes
}

fn period_chunks(
    prepared: &PreparedMaterialTick<HypergraphStore>,
    restart_package: &[u8],
) -> Result<Vec<StateChunk>, QualificationError> {
    let report = prepared.graph_report();
    let mut chunks = Vec::new();
    push_section(
        &mut chunks,
        ChunkSection::StableGraph,
        report.result_stable_graph().canonical_bytes(),
    )?;
    push_section(&mut chunks, ChunkSection::WorldRegisters, restart_package)?;
    push_section(
        &mut chunks,
        ChunkSection::ResolverManifest,
        report.resolver_manifest_bytes(),
    )?;
    push_section(
        &mut chunks,
        ChunkSection::PreparedEnvironment,
        report.prepared_environment_bytes(),
    )?;
    push_section(
        &mut chunks,
        ChunkSection::ReplaySessionIdentity,
        report.replay_session_identity().as_bytes(),
    )?;
    push_section(
        &mut chunks,
        ChunkSection::RngSeed,
        &report.rng_seed().to_be_bytes(),
    )?;
    let digest = report.content_digest();
    let mut content = Vec::with_capacity(64);
    content.extend_from_slice(&digest.defines_hash);
    content.extend_from_slice(&digest.rules_hash);
    push_section(&mut chunks, ChunkSection::ContentDigest, &content)?;
    push_section(
        &mut chunks,
        ChunkSection::ReferenceDigest,
        report.reference_digest().as_bytes(),
    )?;
    push_section(
        &mut chunks,
        ChunkSection::SemanticState,
        report.material_state_rows().canonical_bytes(),
    )?;
    Ok(chunks)
}

fn briefing_journal(period: u64) -> Vec<PreparedJournalRecord> {
    vec![PreparedJournalRecord {
        kind: JournalKind::PlayerReceipt,
        subject: Some(PreparedSubject {
            kind: SubjectKind::County,
            id: HOME_COUNTY.to_vec(),
        }),
        record_key: None,
        payload: briefing_payload(period),
        resolves_prior_subject: false,
    }]
}

fn briefing_knowledge(period: u64) -> Vec<PreparedKnowledgeGrant> {
    KNOWN_COUNTIES
        .iter()
        .map(|county| PreparedKnowledgeGrant {
            player_id: PLAYER_ID,
            subject: PreparedSubject {
                kind: SubjectKind::County,
                id: county.to_vec(),
            },
            grant_key: i64::try_from(period).unwrap_or(i64::MAX),
            payload: briefing_payload(period),
        })
        .collect()
}

fn briefing_payload(period: u64) -> Vec<u8> {
    let mut payload = Vec::with_capacity(48);
    payload.extend_from_slice(&period.to_be_bytes());
    payload.extend_from_slice(&HOME_COUNTY);
    payload.extend_from_slice(&period.saturating_mul(7).to_be_bytes());
    payload.resize(48, 0);
    payload
}

struct RestartParts<'a> {
    state: &'a [u8],
    receipts: &'a [u8],
    lookup: &'a [u8],
}

/// One restart-root fragment as the previous snapshot left it.
struct PreviousChunk {
    decoded_bytes: u64,
    hash: [u8; 32],
}

/// Charged restart-root bytes and the fragments that produced them.
struct ChunkAccounting {
    stored_bytes: u64,
    decoded_bytes: u64,
    sections: Vec<SectionCharge>,
    fragments: Vec<FragmentChange>,
}

/// Charged caller bytes for journal records and earned knowledge.
struct CallerAccounting {
    journal_decoded: u64,
    journal_stored: u64,
    knowledge_decoded: u64,
    knowledge_stored: u64,
}

/// Charge one period and record where every charged byte came from.
fn period_accounting(
    period: u64,
    parts: &RestartParts<'_>,
    chunks: &[StateChunk],
    journal: &[PreparedJournalRecord],
    knowledge: &[PreparedKnowledgeGrant],
    previous: &BTreeMap<(i64, u32), PreviousChunk>,
) -> Result<(PeriodCharge, PeriodBreakdown), QualificationError> {
    let chunk = account_chunks(chunks, previous)?;
    let caller = account_caller_bytes(journal, knowledge)?;
    let section = |wanted: ChunkSection| {
        chunk
            .sections
            .iter()
            .find(|charge| charge.section == wanted.code())
    };
    let decoded_of =
        |wanted: ChunkSection| section(wanted).map_or(0, |charge| charge.decoded_bytes);
    let stable_graph_bytes = decoded_of(ChunkSection::StableGraph);
    let semantic_state_bytes = decoded_of(ChunkSection::SemanticState);
    let metadata_bytes = chunk
        .sections
        .iter()
        .filter(|charge| is_metadata_section(charge.section))
        .try_fold(0_u64, |total, charge| {
            accumulate(total, charge.decoded_bytes)
        })?;
    let world_register_is_new =
        section(ChunkSection::WorldRegisters).is_some_and(|charge| charge.charged_fragments > 0);
    let (state, receipts, lookup) = if world_register_is_new {
        (
            byte_count(parts.state)?,
            byte_count(parts.receipts)?,
            byte_count(parts.lookup)?,
        )
    } else {
        (0, 0, 0)
    };
    let breakdown = PeriodBreakdown {
        period,
        state_package_bytes: state,
        receipt_package_bytes: receipts,
        lookup_delta_bytes: lookup,
        stable_graph_bytes,
        semantic_state_bytes,
        metadata_bytes,
        journal_bytes: caller.journal_decoded,
        knowledge_bytes: caller.knowledge_decoded,
        journal_stored_bytes: caller.journal_stored,
        knowledge_stored_bytes: caller.knowledge_stored,
        sections: chunk.sections,
        fragments: chunk.fragments,
        acknowledged_residual_bytes: 0,
    };
    let stored_added_bytes = accumulate(
        accumulate(chunk.stored_bytes, caller.journal_stored)?,
        caller.knowledge_stored,
    )?;
    let decoded_added_bytes = accumulate(
        accumulate(chunk.decoded_bytes, caller.journal_decoded)?,
        caller.knowledge_decoded,
    )?;
    Ok((
        PeriodCharge {
            period,
            stored_added_bytes,
            decoded_added_bytes,
            unreachable_stored_bytes: 0,
        },
        breakdown,
    ))
}

/// Diff every changed restart-root fragment against the previous snapshot.
fn account_chunks(
    chunks: &[StateChunk],
    previous: &BTreeMap<(i64, u32), PreviousChunk>,
) -> Result<ChunkAccounting, QualificationError> {
    let mut sections: BTreeMap<i64, SectionCharge> = BTreeMap::new();
    let mut fragments = Vec::new();
    let mut present = BTreeSet::new();
    let mut stored_bytes = 0_u64;
    let mut decoded_bytes = 0_u64;
    for chunk in chunks {
        let key = (chunk.section.code(), chunk.ordinal);
        present.insert(key);
        let prior = previous.get(&key);
        if prior.is_some_and(|prior| prior.hash == content_digest::sha256_of(&chunk.bytes)) {
            continue;
        }
        let encoded = codec::encode_chunk_payload(PayloadBudget::StateChunk, &chunk.bytes)?;
        let stored = byte_count(&encoded.payload)?;
        let decoded = byte_count(&chunk.bytes)?;
        stored_bytes = accumulate(stored_bytes, stored)?;
        decoded_bytes = accumulate(decoded_bytes, decoded)?;
        let charge = sections
            .entry(key.0)
            .or_insert_with(|| empty_section(key.0));
        charge.charged_fragments = accumulate(charge.charged_fragments, 1)?;
        charge.decoded_bytes = accumulate(charge.decoded_bytes, decoded)?;
        charge.prior_decoded_bytes = accumulate(
            charge.prior_decoded_bytes,
            prior.map_or(0, |prior| prior.decoded_bytes),
        )?;
        charge.stored_bytes = accumulate(charge.stored_bytes, stored)?;
        fragments.push(FragmentChange {
            section: key.0,
            ordinal: key.1,
            change: if prior.is_some() {
                FragmentChangeKind::Rewritten
            } else {
                FragmentChangeKind::Added
            },
            decoded_bytes: decoded,
            prior_decoded_bytes: prior.map_or(0, |prior| prior.decoded_bytes),
            stored_bytes: stored,
        });
    }
    for (key, prior) in previous {
        if present.contains(key) {
            continue;
        }
        let charge = sections
            .entry(key.0)
            .or_insert_with(|| empty_section(key.0));
        charge.prior_decoded_bytes = accumulate(charge.prior_decoded_bytes, prior.decoded_bytes)?;
        fragments.push(FragmentChange {
            section: key.0,
            ordinal: key.1,
            change: FragmentChangeKind::Retired,
            decoded_bytes: 0,
            prior_decoded_bytes: prior.decoded_bytes,
            stored_bytes: 0,
        });
    }
    Ok(ChunkAccounting {
        stored_bytes,
        decoded_bytes,
        sections: sections.into_values().collect(),
        fragments,
    })
}

fn account_caller_bytes(
    journal: &[PreparedJournalRecord],
    knowledge: &[PreparedKnowledgeGrant],
) -> Result<CallerAccounting, QualificationError> {
    let mut journal_decoded_bytes = 0_u64;
    let mut journal_stored_bytes = 0_u64;
    for record in journal {
        let encoded =
            codec::encode_chunk_payload(PayloadBudget::PermanentJournal, &record.payload)?;
        journal_stored_bytes = accumulate(journal_stored_bytes, byte_count(&encoded.payload)?)?;
        journal_decoded_bytes = accumulate(journal_decoded_bytes, byte_count(&record.payload)?)?;
    }
    let mut knowledge_bytes = 0_u64;
    for grant in knowledge {
        knowledge_bytes = accumulate(knowledge_bytes, byte_count(&grant.payload)?)?;
    }
    Ok(CallerAccounting {
        journal_decoded: journal_decoded_bytes,
        journal_stored: journal_stored_bytes,
        knowledge_decoded: knowledge_bytes,
        knowledge_stored: knowledge_bytes,
    })
}

const fn empty_section(section: i64) -> SectionCharge {
    SectionCharge {
        section,
        charged_fragments: 0,
        decoded_bytes: 0,
        prior_decoded_bytes: 0,
        stored_bytes: 0,
    }
}

const fn is_metadata_section(section: i64) -> bool {
    matches!(
        ChunkSection::from_code(section),
        Some(
            ChunkSection::ResolverManifest
                | ChunkSection::PreparedEnvironment
                | ChunkSection::ReplaySessionIdentity
                | ChunkSection::RngSeed
                | ChunkSection::ContentDigest
                | ChunkSection::ReferenceDigest
        )
    )
}

fn byte_count(bytes: &[u8]) -> Result<u64, QualificationError> {
    u64::try_from(bytes.len())
        .map_err(|_| QualificationError::Evidence("retained bytes overflow u64".to_owned()))
}

fn accumulate(total: u64, value: u64) -> Result<u64, QualificationError> {
    total
        .checked_add(value)
        .ok_or_else(|| QualificationError::Evidence("retained byte accounting overflow".to_owned()))
}

fn next_actions(
    session: &MaterialReplaySession<HypergraphStore>,
) -> Result<OrderedPracticeActionBatch, QualificationError> {
    let next = session
        .completed_tick()
        .checked_add(1)
        .ok_or_else(|| QualificationError::Evidence("next period overflow".to_owned()))?;
    let identity = session.graph_session().session_identity().clone();
    match (
        session.material().organizer_config(),
        session.material().organizer_state(),
    ) {
        (Some(config), Some(state)) => {
            babylon_practice_contract::organizer_action_batch(config, state, None, identity)
                .map_err(|error| QualificationError::Material(format!("{error:?}")))
        }
        (None, None) => OrderedPracticeActionBatch::empty(identity, next)
            .map_err(|error| QualificationError::Material(format!("{error:?}"))),
        _ => Err(QualificationError::Material(
            "the organizer authority is half-bound".to_owned(),
        )),
    }
}

fn measure_queries(
    handle: &CampaignHandle,
    repetitions: usize,
) -> Result<Vec<QuerySample>, QualificationError> {
    let reader = CampaignQueryReader::new(handle);
    let scope = reader.current_scope(PLAYER_ID)?;
    let mut samples = Vec::with_capacity(repetitions.saturating_mul(3));
    for _ in 0..repetitions {
        let started = Instant::now();
        let county = reader.query(
            scope,
            PlayerQuery::CountySummary {
                county_fips: HOME_COUNTY,
            },
        )?;
        let county_ns = elapsed_ns(started)?;
        samples.push(QuerySample {
            elapsed_ns: county_ns,
            rows_visited: u64::from(county.cost.rows_visited()),
        });
        let started = Instant::now();
        let map = reader.query(scope, PlayerQuery::MapSummary)?;
        let map_ns = elapsed_ns(started)?;
        samples.push(QuerySample {
            elapsed_ns: map_ns,
            rows_visited: u64::from(map.cost.rows_visited()),
        });
        let started = Instant::now();
        let history = reader.history(scope, None, 50)?;
        let history_ns = elapsed_ns(started)?;
        samples.push(QuerySample {
            elapsed_ns: history_ns,
            rows_visited: u64::from(history.cost.rows_visited()),
        });
    }
    Ok(samples)
}

fn previous_chunks(handle: &CampaignHandle) -> BTreeMap<(i64, u32), PreviousChunk> {
    handle
        .current()
        .chunks
        .iter()
        .map(|chunk| {
            (
                (chunk.section.code(), chunk.ordinal),
                PreviousChunk {
                    decoded_bytes: u64::from(chunk.raw_len),
                    hash: chunk.raw_hash,
                },
            )
        })
        .collect()
}

fn store_bytes(path: &Path) -> Result<u64, QualificationError> {
    Ok(std::fs::metadata(path)?.len())
}

fn elapsed_ns(started: Instant) -> Result<u64, QualificationError> {
    started
        .elapsed()
        .as_nanos()
        .try_into()
        .map_err(|_| QualificationError::Evidence("elapsed duration overflow".to_owned()))
}

fn write_advance(directory: &Path, sample: &AdvanceSample) -> Result<(), QualificationError> {
    use std::io::Write;
    let path = directory.join("advances.jsonl");
    let mut file = OpenOptions::new().create(true).append(true).open(path)?;
    serde_json::to_writer(&mut file, sample)?;
    file.write_all(b"\n")?;
    Ok(())
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, QualificationError> {
    Ok(serde_json::from_slice(&std::fs::read(path)?)?)
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), QualificationError> {
    use std::io::Write;
    let bytes = serde_json::to_vec_pretty(value)?;
    let mut file = match OpenOptions::new().write(true).create_new(true).open(path) {
        Ok(file) => file,
        Err(error) if error.kind() == ErrorKind::AlreadyExists => {
            return Err(QualificationError::Evidence(format!(
                "the evidence file {} already exists and is never replaced",
                path.display()
            )));
        }
        Err(error) => return Err(error.into()),
    };
    file.write_all(&bytes)?;
    Ok(())
}

/// Persist the measured run manifest.
///
/// # Errors
/// Refuses an existing evidence file or an unwritable output directory.
pub fn write_run(directory: &Path, run: &RunManifest) -> Result<(), QualificationError> {
    write_json(&directory.join("run.json"), run)
}

/// Persist the cold-open manifest.
///
/// # Errors
/// Refuses an existing evidence file or an unwritable output directory.
pub fn write_cold_open(
    directory: &Path,
    cold: &ColdOpenManifest,
) -> Result<(), QualificationError> {
    write_json(&directory.join("cold-open.json"), cold)
}

fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    let mut text = String::with_capacity(bytes.len().saturating_mul(2));
    for byte in bytes {
        write!(&mut text, "{byte:02x}").expect("writing to String cannot fail");
    }
    text
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::qualification_audit::policy::MemorySample;
    use serde_json::Value;
    use sha2::{Digest, Sha256};
    use std::sync::atomic::{AtomicU64, Ordering};

    const CAMPAIGN: &str = "28100000-0000-0000-0000-000000000013";

    struct Scratch(PathBuf);

    impl Scratch {
        fn new() -> Self {
            static NEXT: AtomicU64 = AtomicU64::new(0);
            let path = std::env::temp_dir().join(format!(
                "babylon-national-evidence-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            std::fs::create_dir_all(&path).expect("the scratch root is creatable");
            Self(path)
        }
    }

    impl Drop for Scratch {
        fn drop(&mut self) {
            std::fs::remove_dir_all(&self.0).ok();
        }
    }

    fn contract() -> (PathBuf, [u8; 32]) {
        let path = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../contracts/national_sqlite_qualification_v1.json");
        let bytes = std::fs::read(&path).expect("the authored contract is readable");
        (path, <[u8; 32]>::from(Sha256::digest(bytes)))
    }

    fn advance(period: u64) -> AdvanceSample {
        AdvanceSample {
            period,
            judgment_ns: 1_000_000,
            encoding_ns: 0,
            commit_ns: 0,
            briefing_ns: 0,
            total_ns: 1_000_000,
        }
    }

    fn evidence_run() -> RunManifest {
        RunManifest {
            schema: RUN_SCHEMA.to_owned(),
            campaign: CAMPAIGN.to_owned(),
            build_hash: hex(&[0; 32]),
            periods: 2,
            opening_decoded_bytes: 1_000,
            opening_file_bytes: 1_000,
            final_store_bytes: 2_000,
            final_wal_bytes: 0,
            elapsed_ns: 2_000,
            advances: (1..=2).map(advance).collect(),
            charges: (1..=2)
                .map(|period| PeriodCharge {
                    period,
                    stored_added_bytes: 1_000_000,
                    decoded_added_bytes: 2_000_000,
                    unreachable_stored_bytes: 0,
                })
                .collect(),
            breakdowns: Vec::new(),
            warm_queries: vec![QuerySample {
                elapsed_ns: 1_000_000,
                rows_visited: 4,
            }],
        }
    }

    fn evidence_cold_open() -> ColdOpenManifest {
        ColdOpenManifest {
            schema: COLD_OPEN_SCHEMA.to_owned(),
            campaign: CAMPAIGN.to_owned(),
            cold_open_ns: 1_000_000,
            cold_queries: vec![QuerySample {
                elapsed_ns: 2_000_000,
                rows_visited: 4,
            }],
            warm_queries: vec![QuerySample {
                elapsed_ns: 1_000_000,
                rows_visited: 4,
            }],
            store_bytes: 1_000,
            wal_bytes: 0,
        }
    }

    fn evidence_memory() -> MemorySummary {
        MemorySummary {
            samples: vec![
                MemorySample {
                    elapsed_ns: 0,
                    rss_bytes: 3_000_000_000,
                },
                MemorySample {
                    elapsed_ns: 250_000_000,
                    rss_bytes: 3_000_000_000,
                },
            ],
        }
    }

    fn write_evidence(directory: &Path, run: &RunManifest, cold: &ColdOpenManifest) {
        for (name, bytes) in [
            (
                "run.json",
                serde_json::to_vec_pretty(run).expect("the run manifest serializes"),
            ),
            (
                "cold-open.json",
                serde_json::to_vec_pretty(cold).expect("the cold-open manifest serializes"),
            ),
            (
                "memory.json",
                serde_json::to_vec_pretty(&evidence_memory())
                    .expect("the memory summary serializes"),
            ),
        ] {
            std::fs::write(directory.join(name), bytes).expect("the scratch root is writable");
        }
    }

    #[test]
    fn scoped_query_evidence_names_only_the_counter_the_reader_exposes() {
        let sample = QuerySample {
            elapsed_ns: 1,
            rows_visited: 3,
        };
        assert_eq!(
            serde_json::to_value(sample).expect("the query sample serializes"),
            serde_json::json!({"elapsed_ns": 1, "rows_visited": 3}),
            "the reader exposes stored rows only, so no chunk counter may be invented"
        );
    }

    /// The exact capture files `run_rung` opens before it spawns this process.
    ///
    /// `national_sqlite_qualification_runner.py` redirects the spawned
    /// process's stdout and stderr into the run directory, so these files exist
    /// before the measured process starts.
    const DRIVER_CAPTURE_FILES: [&str; 6] = [
        "qualify.stdout.json",
        "qualify.stderr.log",
        "cold-open.stdout.json",
        "cold-open.stderr.log",
        "evaluate.stdout.json",
        "evaluate.stderr.log",
    ];

    fn touch(directory: &Path, name: &str, body: &[u8]) {
        std::fs::write(directory.join(name), body).expect("the scratch root is writable");
    }

    #[test]
    fn driver_capture_files_do_not_count_as_campaign_evidence() {
        let scratch = Scratch::new();
        for name in DRIVER_CAPTURE_FILES {
            touch(&scratch.0, name, b"");
        }
        require_no_evidence(&scratch.0)
            .expect("the driver's own capture files are not campaign evidence");
    }

    #[test]
    fn existing_evidence_is_refused_before_the_run_starts() {
        let evaluation = format!("evaluation-{}.json", "0".repeat(64));
        for name in [
            "run.json",
            "cold-open.json",
            "memory.json",
            evaluation.as_str(),
            "advances.jsonl",
        ] {
            let scratch = Scratch::new();
            touch(&scratch.0, name, b"{}\n");
            let error = require_no_evidence(&scratch.0)
                .expect_err("existing evidence must refuse the run before it starts");
            assert!(error.to_string().contains(name), "{error}");
        }
    }

    #[test]
    fn an_empty_advance_log_is_not_evidence() {
        let scratch = Scratch::new();
        touch(&scratch.0, "advances.jsonl", b"");
        require_no_evidence(&scratch.0).expect("an advance log without an advance mixes nothing");
    }

    #[test]
    fn a_reused_run_directory_is_refused_before_the_run_starts() {
        let scratch = Scratch::new();
        touch(&scratch.0, "advances.jsonl", b"{}\n");
        let error = run_national(&scratch.0.join("campaign.sqlite"), &scratch.0, 1)
            .expect_err("a reused output directory must be refused");
        assert!(error.to_string().contains("advances.jsonl"), "{error}");
        assert_eq!(
            std::fs::read(scratch.0.join("advances.jsonl")).expect("the earlier advance survives"),
            b"{}\n",
            "the refusal leaves the earlier evidence untouched"
        );
    }

    #[test]
    fn evidence_files_are_never_replaced() {
        let scratch = Scratch::new();
        let run = evidence_run();
        write_run(&scratch.0, &run).expect("the first run manifest is written");
        let first =
            std::fs::read(scratch.0.join("run.json")).expect("the run manifest is readable");
        let error = write_run(&scratch.0, &run).expect_err("a second write must be refused");
        assert!(error.to_string().contains("already exists"), "{error}");
        assert_eq!(
            std::fs::read(scratch.0.join("run.json")).expect("the run manifest is readable"),
            first
        );
        let cold = evidence_cold_open();
        write_cold_open(&scratch.0, &cold).expect("the first cold-open manifest is written");
        assert!(write_cold_open(&scratch.0, &cold).is_err());
    }

    #[test]
    fn re_evaluation_writes_beside_the_earlier_verdict() {
        let scratch = Scratch::new();
        let (contract, digest) = contract();
        write_evidence(&scratch.0, &evidence_run(), &evidence_cold_open());
        let first = evaluate_run(&scratch.0, &contract, digest, 2)
            .expect("the recorded evidence is evaluated");
        assert!(first.verdict.passed, "{:?}", first.verdict.metrics);
        let first_path = evaluation_path(&scratch.0, digest);
        assert!(
            first_path.exists(),
            "the verdict is named after its contract"
        );
        assert!(
            !scratch.0.join("evaluation.json").exists(),
            "a fixed verdict filename would be replaced by the next contract"
        );
        let first_bytes = std::fs::read(&first_path).expect("the verdict is readable");

        let other_contract = scratch.0.join("contract-other.json");
        let mut value: Value = serde_json::from_slice(
            &std::fs::read(&contract).expect("the authored contract is readable"),
        )
        .expect("the authored contract is JSON");
        value["review_note"] = serde_json::json!("distinct bytes, same consumed fields");
        std::fs::write(
            &other_contract,
            serde_json::to_vec(&value).expect("the edited contract serializes"),
        )
        .expect("the scratch root is writable");
        let other_digest = <[u8; 32]>::from(Sha256::digest(
            std::fs::read(&other_contract).expect("the edited contract is readable"),
        ));
        assert_ne!(other_digest, digest);
        evaluate_run(&scratch.0, &other_contract, other_digest, 2)
            .expect("the same evidence is re-evaluated under another contract");
        assert!(evaluation_path(&scratch.0, other_digest).exists());
        assert_eq!(
            std::fs::read(&first_path).expect("the earlier verdict survives"),
            first_bytes,
            "re-evaluation must not destroy the earlier verdict"
        );
        assert!(
            evaluate_run(&scratch.0, &contract, digest, 2).is_err(),
            "the same verdict is never silently replaced"
        );
    }

    fn previous_chunk(decoded_bytes: u64, bytes: &[u8]) -> PreviousChunk {
        PreviousChunk {
            decoded_bytes,
            hash: content_digest::sha256_of(bytes),
        }
    }

    /// A snapshot with two rewritten fragments, one added and one retired.
    fn churn_previous() -> BTreeMap<(i64, u32), PreviousChunk> {
        BTreeMap::from([
            (
                (ChunkSection::StableGraph.code(), 0),
                previous_chunk(16, &[1; 16]),
            ),
            (
                (ChunkSection::StableGraph.code(), 1),
                previous_chunk(8, &[2; 8]),
            ),
            (
                (ChunkSection::StableGraph.code(), 3),
                previous_chunk(5, &[3; 5]),
            ),
            (
                (ChunkSection::WorldRegisters.code(), 0),
                previous_chunk(4, &[4; 4]),
            ),
        ])
    }

    /// The next snapshot: the restart package repeats, the graph churns.
    fn churn_chunks() -> Vec<StateChunk> {
        vec![
            StateChunk {
                section: ChunkSection::StableGraph,
                ordinal: 0,
                bytes: vec![5; 16],
            },
            StateChunk {
                section: ChunkSection::StableGraph,
                ordinal: 1,
                bytes: vec![6; 8],
            },
            StateChunk {
                section: ChunkSection::StableGraph,
                ordinal: 2,
                bytes: vec![7; 12],
            },
            StateChunk {
                section: ChunkSection::WorldRegisters,
                ordinal: 0,
                bytes: vec![4; 4],
            },
        ]
    }

    #[test]
    fn fragment_diff_attributes_rewrites_additions_and_retirements() {
        let previous = churn_previous();
        let chunks = churn_chunks();
        let journal = briefing_journal(7);
        let knowledge = briefing_knowledge(7);
        let parts = RestartParts {
            state: &[1; 100],
            receipts: &[2; 200],
            lookup: &[3; 300],
        };
        let (charge, breakdown) =
            period_accounting(7, &parts, &chunks, &journal, &knowledge, &previous)
                .expect("the fixture period is accounted");
        let stable = breakdown
            .sections
            .iter()
            .find(|section| section.section == ChunkSection::StableGraph.code())
            .expect("the stable graph changed");
        assert_eq!(stable.charged_fragments, 3);
        assert_eq!(stable.decoded_bytes, 36);
        assert_eq!(
            stable.prior_decoded_bytes, 29,
            "a retired fragment is attributed instead of dropped"
        );
        assert!(
            stable.stored_bytes > 0,
            "the stable graph charge is stored payload bytes"
        );
        assert_eq!(
            stable.stored_bytes,
            breakdown
                .fragments
                .iter()
                .filter(|fragment| fragment.section == ChunkSection::StableGraph.code())
                .try_fold(0_u64, |total, fragment| {
                    total.checked_add(fragment.stored_bytes)
                })
                .expect("the fragment charges fit u64"),
            "the section charge is the sum of its fragment charges"
        );
        assert_eq!(
            breakdown.state_package_bytes, 0,
            "an unchanged restart package charges nothing"
        );
        let find = |ordinal: u32| {
            breakdown
                .fragments
                .iter()
                .find(|fragment| {
                    fragment.section == ChunkSection::StableGraph.code()
                        && fragment.ordinal == ordinal
                })
                .copied()
                .expect("the fixture changed the requested fragment")
        };
        let rewritten = find(0);
        assert_eq!(rewritten.change, FragmentChangeKind::Rewritten);
        assert_eq!(
            rewritten.decoded_bytes, rewritten.prior_decoded_bytes,
            "equal decoded lengths with new bytes are serialization churn"
        );
        let added = find(2);
        assert_eq!(added.change, FragmentChangeKind::Added);
        assert_eq!(added.prior_decoded_bytes, 0);
        let retired = find(3);
        assert_eq!(retired.change, FragmentChangeKind::Retired);
        assert_eq!(retired.decoded_bytes, 0);
        assert_eq!(retired.stored_bytes, 0);
        let section_stored = breakdown
            .sections
            .iter()
            .try_fold(0_u64, |total, section| {
                total.checked_add(section.stored_bytes)
            })
            .expect("the section charges fit u64");
        assert_eq!(breakdown.acknowledged_residual_bytes, 0);
        assert_eq!(
            charge.stored_added_bytes,
            section_stored
                + breakdown.journal_stored_bytes
                + breakdown.knowledge_stored_bytes
                + breakdown.acknowledged_residual_bytes,
            "component charges and the unattributed residual sum to the charged period"
        );
        assert_eq!(breakdown.journal_bytes, 48);
        assert_eq!(breakdown.knowledge_bytes, 384);
    }

    #[test]
    fn a_changed_restart_package_is_charged_and_attributed() {
        let previous = BTreeMap::from([(
            (ChunkSection::WorldRegisters.code(), 0),
            previous_chunk(4, &[4; 4]),
        )]);
        let chunks = vec![StateChunk {
            section: ChunkSection::WorldRegisters,
            ordinal: 0,
            bytes: vec![9; 600],
        }];
        let parts = RestartParts {
            state: &[1; 100],
            receipts: &[2; 200],
            lookup: &[3; 300],
        };
        let (charge, breakdown) = period_accounting(1, &parts, &chunks, &[], &[], &previous)
            .expect("the fixture period is accounted");
        assert_eq!(breakdown.state_package_bytes, 100);
        assert_eq!(breakdown.receipt_package_bytes, 200);
        assert_eq!(breakdown.lookup_delta_bytes, 300);
        let registers = breakdown
            .sections
            .iter()
            .find(|section| section.section == ChunkSection::WorldRegisters.code())
            .expect("the restart package changed");
        assert_eq!(registers.charged_fragments, 1);
        assert_eq!(registers.decoded_bytes, 600);
        assert_eq!(registers.prior_decoded_bytes, 4);
        assert_eq!(charge.stored_added_bytes, registers.stored_bytes);
        assert_eq!(charge.decoded_added_bytes, 600);
    }

    /// Split one restart package into its three exact parts and chain.
    fn restart_parts(bytes: &[u8]) -> (&[u8], &[u8], &[u8], [u8; 32]) {
        let mut cursor = 0_usize;
        assert_eq!(
            bytes.get(..RESTART_DOMAIN.len()),
            Some(RESTART_DOMAIN),
            "the restart package carries its domain"
        );
        cursor += RESTART_DOMAIN.len();
        let part = |cursor: &mut usize| {
            let length_bytes: [u8; 8] = bytes
                .get(*cursor..*cursor + 8)
                .expect("the restart package frames each part")
                .try_into()
                .expect("the part length is eight bytes");
            *cursor += 8;
            let length = usize::try_from(u64::from_be_bytes(length_bytes))
                .expect("the part length fits the host");
            let slice = bytes
                .get(*cursor..*cursor + length)
                .expect("the restart part is present");
            *cursor += length;
            slice
        };
        let state = part(&mut cursor);
        let receipts = part(&mut cursor);
        let lookup = part(&mut cursor);
        let chain: [u8; 32] = bytes
            .get(cursor..cursor + 32)
            .expect("the restart package ends with one chain")
            .try_into()
            .expect("the chain is thirty-two bytes");
        cursor += 32;
        assert_eq!(
            cursor,
            bytes.len(),
            "the restart package carries no trailing bytes"
        );
        (state, receipts, lookup, chain)
    }

    use crate::material_storage::LookupAnchor;
    use crate::material_storage::OpeningRegister;
    use babylon_tick::material_world::MaterialWorldRegister;

    type NationalSession = MaterialReplaySession<HypergraphStore>;

    /// Rebuild the admitted foundation and its opening lookup authority.
    fn admitted_national_session() -> (NationalSession, OpeningRegister) {
        let campaign = CampaignId::from_uuid(Uuid::from_u128(CAMPAIGN_UUID));
        let captured = CapturedEconomicCatalog::capture_national_campaign(
            crate::economic_catalog::national_catalog_input(),
            campaign,
        )
        .expect("the national catalog captures deterministically");
        let foundation = captured
            .create_foundation(
                ReplaySessionId::try_from(SESSION_ID).expect("the session identity is valid"),
                ReplaySeed::new(REPLAY_SEED),
            )
            .expect("the same admitted foundation is reproducible");
        let opening_bytes = foundation.initial_register().canonical_bytes().to_vec();
        let session = foundation
            .into_session()
            .expect("the admitted foundation opens one fresh session");
        let opening = crate::material_storage::seed(session.catalog(), &opening_bytes)
            .expect("the captured opening seeds the lookup authority");
        (session, opening)
    }

    /// Decode the current root's material restart package into its register.
    fn stored_material_register(
        handle: &CampaignHandle,
        session: &NationalSession,
        opening: &OpeningRegister,
        period: u64,
    ) -> MaterialWorldRegister {
        let restart = handle
            .read_section_bytes(ChunkSection::WorldRegisters)
            .expect("the current root carries the restart package");
        let (state_package, receipt_package, lookup_delta, chain) = restart_parts(&restart);
        let period_lookup = crate::material_storage::read_period_lookup(
            opening,
            period,
            lookup_delta,
            LookupAnchor::Current(chain),
        )
        .expect("the period lookup authenticates against its opening");
        let (register_bytes, _receipts) = crate::material_storage::decode(
            session.catalog(),
            opening,
            period,
            state_package,
            receipt_package,
            &period_lookup.lookup,
            period_lookup.chain,
        )
        .expect("the material restart package decodes into one canonical register");
        MaterialWorldRegister::decode_external(session.catalog(), register_bytes)
            .expect("the decoded register bytes are one canonical material world")
    }

    /// Assert every committed period's identity is readable and chain-linked.
    fn assert_recorded_period_identities(handle: &CampaignHandle, period: u64) {
        let mut prior_world: Option<[u8; 32]> = None;
        for completed in 1..=period {
            let identity = handle
                .period_tick_identity(completed)
                .expect("every committed period records a summary")
                .expect("a material campaign records one tick identity per period");
            assert_eq!(
                identity.resolve_tick(),
                completed,
                "the recorded identity names its own period"
            );
            assert_eq!(
                identity.tick_content_hash().as_bytes(),
                &content_digest::sha256_of(identity.canonical_bytes()),
                "the recorded content hash authenticates the persisted identity bytes"
            );
            if let Some(previous) = prior_world {
                assert_eq!(
                    identity.prior_world_hash(),
                    previous,
                    "the per-period identity chain links consecutive periods"
                );
            }
            prior_world = Some(identity.result_world_hash());
        }
        assert_eq!(
            prior_world.expect("the run committed at least one period"),
            handle.current().world_hash,
            "the last recorded identity names the committed current world"
        );
    }

    #[test]
    fn a_cold_reopen_restores_the_live_session_from_store_bytes() {
        use babylon_graph::stable_state::StableGraphState;
        use babylon_tick::material_state::MaterialStateRows;
        use babylon_tick::replay_identity;

        let scratch = Scratch::new();
        let output = scratch.0.join("evidence");
        let store_path = output.join("campaign.sqlite");
        let run = run_national(&store_path, &output, 2).expect("the campaign advances two turns");
        assert_eq!(run.periods, 2, "the run commits the requested horizon");

        let (mut session, opening) = admitted_national_session();
        let handle = SqliteCampaignStore::open(
            &store_path,
            content_package::content_package_build_identity(),
        )
        .expect("the committed campaign cold reopens");
        let period = handle.current().period;
        assert_eq!(period, 2, "the store holds the two committed periods");

        let graph_bytes = handle
            .read_section_bytes(ChunkSection::StableGraph)
            .expect("the current root carries the stable graph section");
        let graph_state = StableGraphState::decode(&graph_bytes)
            .expect("the persisted graph bytes decode into the canonical state");
        assert_eq!(
            graph_state.canonical_bytes(),
            graph_bytes,
            "the stored graph section is the canonical encoder image"
        );
        let material_bytes = handle
            .read_section_bytes(ChunkSection::SemanticState)
            .expect("the current root carries the semantic material section");
        let material_rows = MaterialStateRows::decode(&material_bytes)
            .expect("the persisted material bytes decode into the canonical rows");
        assert_eq!(
            material_rows.canonical_bytes(),
            material_bytes,
            "the stored semantic section is the canonical encoder image"
        );

        let register = stored_material_register(&handle, &session, &opening, period);
        let registers = replay_identity::encode_world_register_set(
            &replay_identity::world_register_manifest()
                .expect("the governed register manifest encodes"),
            i64::try_from(period).expect("the completed period fits the register lane"),
        )
        .expect("the completed-tick register set encodes");
        session
            .restore_full_checkpoint(
                &graph_state,
                &material_rows,
                registers.canonical_bytes(),
                register,
            )
            .expect("the live session restores from the store bytes alone");
        assert_eq!(
            session.completed_tick(),
            period,
            "the restored session continues at the committed period"
        );
        assert_eq!(
            session
                .current_world_hash()
                .expect("the restored session hashes its complete world"),
            handle.current().world_hash,
            "the restored session reproduces the committed world identity"
        );

        assert_recorded_period_identities(&handle, period);
    }
}
