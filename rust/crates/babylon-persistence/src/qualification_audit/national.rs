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
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;
use std::fs::OpenOptions;
use std::path::Path;
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
    ReadError, SaveError, SqliteCampaignStore, StateChunk, MAX_STATE_CHUNK_BYTES,
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
    let mut previous = chunk_hashes(&handle);
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
        let mut charge = charge_candidate(&chunks, &journal, &knowledge, &previous)?;
        let breakdown = period_breakdown(
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
        );
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
        };
        charge.period = period;
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
        let briefing = measure_queries(&handle, 1)?;
        let briefing_ns = elapsed_ns(briefing_started)?;
        let total_ns = judgment_started
            .elapsed()
            .as_nanos()
            .try_into()
            .map_err(|_| QualificationError::Evidence("advance duration overflow".to_owned()))?;
        previous = chunk_hashes(&handle);
        let summary_residual = acknowledged
            .retention
            .gross_bytes_added
            .saturating_sub(charge.decoded_added_bytes);
        charge.decoded_added_bytes = acknowledged.retention.gross_bytes_added;
        charge.stored_added_bytes = charge.stored_added_bytes.saturating_add(summary_residual);
        charge.unreachable_stored_bytes = acknowledged.retention.bytes_made_unreachable;
        charges.push(charge);
        breakdowns.push(breakdown);
        advances.push(AdvanceSample {
            period,
            judgment_ns,
            encoding_ns,
            commit_ns,
            briefing_ns,
            total_ns,
            chunks_visited: briefing.iter().map(|sample| sample.chunks_visited).sum(),
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
    write_json(&run_directory.join("evaluation.json"), &evaluation)?;
    Ok(evaluation)
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

fn period_breakdown(
    period: u64,
    parts: &RestartParts<'_>,
    chunks: &[StateChunk],
    journal: &[PreparedJournalRecord],
    knowledge: &[PreparedKnowledgeGrant],
    previous: &BTreeMap<(i64, u32), [u8; 32]>,
) -> PeriodBreakdown {
    let mut stable_graph = 0_u64;
    let mut semantic_state = 0_u64;
    let mut metadata = 0_u64;
    for chunk in chunks {
        let hash = content_digest::sha256_of(&chunk.bytes);
        if previous.get(&(chunk.section.code(), chunk.ordinal)) == Some(&hash) {
            continue;
        }
        let length = u64::try_from(chunk.bytes.len()).unwrap_or(u64::MAX);
        match chunk.section {
            ChunkSection::StableGraph => stable_graph = stable_graph.saturating_add(length),
            ChunkSection::SemanticState => semantic_state = semantic_state.saturating_add(length),
            ChunkSection::WorldRegisters => {}
            _ => metadata = metadata.saturating_add(length),
        }
    }
    let journal_bytes = journal.iter().fold(0_u64, |total, record| {
        total.saturating_add(u64::try_from(record.payload.len()).unwrap_or(u64::MAX))
    });
    let knowledge_bytes = knowledge.iter().fold(0_u64, |total, grant| {
        total.saturating_add(u64::try_from(grant.payload.len()).unwrap_or(u64::MAX))
    });
    let world_register_is_new = chunks.iter().any(|chunk| {
        chunk.section == ChunkSection::WorldRegisters
            && previous.get(&(chunk.section.code(), chunk.ordinal))
                != Some(&content_digest::sha256_of(&chunk.bytes))
    });
    let package = |bytes: &[u8]| -> u64 {
        if world_register_is_new {
            u64::try_from(bytes.len()).unwrap_or(u64::MAX)
        } else {
            0
        }
    };
    PeriodBreakdown {
        period,
        state_package_bytes: package(parts.state),
        receipt_package_bytes: package(parts.receipts),
        lookup_delta_bytes: package(parts.lookup),
        stable_graph_bytes: stable_graph,
        semantic_state_bytes: semantic_state,
        metadata_bytes: metadata,
        journal_bytes,
        knowledge_bytes,
    }
}

fn charge_candidate(
    chunks: &[StateChunk],
    journal: &[PreparedJournalRecord],
    knowledge: &[PreparedKnowledgeGrant],
    previous: &BTreeMap<(i64, u32), [u8; 32]>,
) -> Result<PeriodCharge, QualificationError> {
    let mut stored = 0_u64;
    let mut decoded = 0_u64;
    for chunk in chunks {
        let hash = content_digest::sha256_of(&chunk.bytes);
        if previous.get(&(chunk.section.code(), chunk.ordinal)) == Some(&hash) {
            continue;
        }
        let encoded = codec::encode_chunk_payload(PayloadBudget::StateChunk, &chunk.bytes)?;
        stored = stored
            .checked_add(u64::try_from(encoded.payload.len()).map_err(|_| {
                QualificationError::Evidence("stored chunk length overflow".to_owned())
            })?)
            .ok_or_else(|| {
                QualificationError::Evidence("stored chunk total overflow".to_owned())
            })?;
        decoded = decoded
            .checked_add(u64::try_from(chunk.bytes.len()).map_err(|_| {
                QualificationError::Evidence("decoded chunk length overflow".to_owned())
            })?)
            .ok_or_else(|| {
                QualificationError::Evidence("decoded chunk total overflow".to_owned())
            })?;
    }
    for record in journal {
        let encoded =
            codec::encode_chunk_payload(PayloadBudget::PermanentJournal, &record.payload)?;
        stored = stored
            .checked_add(u64::try_from(encoded.payload.len()).map_err(|_| {
                QualificationError::Evidence("stored journal length overflow".to_owned())
            })?)
            .ok_or_else(|| {
                QualificationError::Evidence("stored journal total overflow".to_owned())
            })?;
        decoded = decoded
            .checked_add(u64::try_from(record.payload.len()).map_err(|_| {
                QualificationError::Evidence("decoded journal length overflow".to_owned())
            })?)
            .ok_or_else(|| {
                QualificationError::Evidence("decoded journal total overflow".to_owned())
            })?;
    }
    for grant in knowledge {
        let length = u64::try_from(grant.payload.len())
            .map_err(|_| QualificationError::Evidence("knowledge length overflow".to_owned()))?;
        stored = stored
            .checked_add(length)
            .ok_or_else(|| QualificationError::Evidence("stored knowledge overflow".to_owned()))?;
        decoded = decoded
            .checked_add(length)
            .ok_or_else(|| QualificationError::Evidence("decoded knowledge overflow".to_owned()))?;
    }
    Ok(PeriodCharge {
        period: 0,
        stored_added_bytes: stored,
        decoded_added_bytes: decoded,
        unreachable_stored_bytes: 0,
    })
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
            chunks_visited: 0,
        });
        let started = Instant::now();
        let map = reader.query(scope, PlayerQuery::MapSummary)?;
        let map_ns = elapsed_ns(started)?;
        samples.push(QuerySample {
            elapsed_ns: map_ns,
            rows_visited: u64::from(map.cost.rows_visited()),
            chunks_visited: 0,
        });
        let started = Instant::now();
        let history = reader.history(scope, None, 50)?;
        let history_ns = elapsed_ns(started)?;
        samples.push(QuerySample {
            elapsed_ns: history_ns,
            rows_visited: u64::from(history.cost.rows_visited()),
            chunks_visited: 0,
        });
    }
    Ok(samples)
}

fn chunk_hashes(handle: &CampaignHandle) -> BTreeMap<(i64, u32), [u8; 32]> {
    handle
        .current()
        .chunks
        .iter()
        .map(|chunk| ((chunk.section.code(), chunk.ordinal), chunk.raw_hash))
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
    std::fs::write(path, serde_json::to_vec_pretty(value)?)?;
    Ok(())
}

/// Persist the measured run manifest.
///
/// # Errors
/// Refuses an unwritable output directory.
pub fn write_run(directory: &Path, run: &RunManifest) -> Result<(), QualificationError> {
    write_json(&directory.join("run.json"), run)
}

/// Persist the cold-open manifest.
///
/// # Errors
/// Refuses an unwritable output directory.
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
