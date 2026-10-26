//! `authored-graph-v1` saved campaign admission, replay and viewer facts.
//!
//! The profile wraps the existing replay-session host: the resolved scenario,
//! optional declaration prelude and rules execute over the real checked Michigan
//! geographic `MaterialState` and its reference manifest. The profile's defines
//! bytes are the fixed UTF-8 bytes `{}`; no economic coefficients are admitted.
//!
//! The campaign is stored in the ordinary nine-table container. Its opening and
//! every committed period carry all nine restart-root sections, including the
//! material semantic state that full checkpoints already require. Authored node
//! facts reach the bounded viewer only through ordinary knowledge grants and
//! journal records acquired by a committed period; the scoped query module never
//! reads a chunk. Player commands are unsupported for this profile and refuse
//! with [`CommandError::UnsupportedProfile`].

use std::path::Path;

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_state::StableGraphState;
use babylon_kernel::content_digest;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::replay_identity;
use babylon_tick::replay_session::IdentifiedTickReport;
use babylon_tick::replay_session::ReplayCommitDisposition;
use babylon_tick::replay_session::ReplayTickSession;

use crate::foundation::CampaignFoundation;
use crate::identity::CampaignId;
use crate::michigan_economy;
use crate::michigan_economy::MichiganEconomyError;
use crate::sqlite_store::chunks;
use crate::sqlite_store::query;
use crate::sqlite_store::AdmittedContent;
use crate::sqlite_store::AdmittedContentEntry;
use crate::sqlite_store::AdmittedOpening;
use crate::sqlite_store::CampaignHandle;
use crate::sqlite_store::ChunkSection;
use crate::sqlite_store::CommittedPeriod;
use crate::sqlite_store::ContentEntryKind;
use crate::sqlite_store::JournalKind;
use crate::sqlite_store::PreparedJournalRecord;
use crate::sqlite_store::PreparedKnowledgeGrant;
use crate::sqlite_store::PreparedPeriod;
use crate::sqlite_store::PreparedSubject;
use crate::sqlite_store::SaveError;
use crate::sqlite_store::SqliteCampaignStore;
use crate::sqlite_store::StateChunk;
use crate::sqlite_store::SubjectKind;

use super::admission;
use super::manifest::HostProfile;
use super::manifest::SourceKind;
use super::resolver::ResolvedContentSet;

/// Exact fixed defines bytes of the authored graph profile.
pub const AUTHORED_GRAPH_DEFINES: &[u8] = b"{}";

/// Stable identity of the profile's supported read-only viewer.
pub const AUTHORED_GRAPH_VIEWER_PLAYER_ID: [u8; 8] = *b"authgrph";

/// The declared node field the bounded graph viewer publishes.
pub const AUTHORED_GRAPH_VIEWER_FIELD: &str = "social-class/probability";

/// Content-entry key of the profile's fixed defines artifact.
pub const AUTHORED_GRAPH_DEFINES_ENTRY: &[u8] = b"authored-graph-defines";

const ADMISSION_DOMAIN: &[u8] = b"babylon.authored-graph.admission.v1\0";
const ADMISSION_LAYOUT: u8 = 1;
const SESSION_DOMAIN: &str = "authored-graph-v1/";
const MAX_METADATA_TEXT_BYTES: usize = 256;

/// Admit one resolved `authored-graph-v1` package set into a new campaign store.
///
/// # Errors
///
/// Refuses a different host profile, a source-kind mismatch, a non-UTF-8 source,
/// a seed beyond the replay domain, a scenario that does not reproduce its
/// captured graph, or a `SQLite` store refusal.
pub fn admit_authored_graph_package(
    resolved: &ResolvedContentSet,
    seed: u64,
    store_path: &Path,
) -> Result<CampaignHandle, SaveError> {
    if resolved.host_profile() != HostProfile::AuthoredGraphV1 {
        return Err(package_refused(format!(
            "the resolved set selects {} instead of authored-graph-v1",
            resolved.host_profile().manifest_name()
        )));
    }
    admission::validate_profile_sources(resolved)
        .map_err(|error| package_refused(error.to_string()))?;
    let seed = i64::try_from(seed)
        .map_err(|_| package_refused("the replay seed is too large".to_owned()))?;
    let sources = ReplaySources::from_resolved(resolved)?;
    let session_identity = session_identity(resolved.digest());
    let (session, bundle) = michigan_economy::foundation_from_authored_sources_with_seed(
        &sources.scenario,
        sources.prelude.as_deref(),
        &sources.rules,
        &session_identity,
        AUTHORED_GRAPH_DEFINES,
        seed,
    )
    .map_err(foundation_refused)?;
    let _foundation = CampaignFoundation::capture(&session, bundle)
        .map_err(|error| package_refused(format!("{error:?}")))?;
    let content = admitted_content(resolved, &sources, seed)?;
    let opening = admitted_opening(&session)?;
    SqliteCampaignStore::create(store_path, content, opening)
}

/// Rebuild the admitted replay session from the campaign's captured content.
///
/// The captured sources, `{}` defines and the static restart-root sections
/// authenticate the rebuild; installed package files are never consulted.
///
/// # Errors
///
/// Refuses an absent or malformed admission record, a missing captured source,
/// a static section that disagrees with the rebuilt session, or any ordinary
/// foundation construction refusal.
pub fn authored_graph_replay_session(
    handle: &CampaignHandle,
) -> Result<ReplayTickSession<HypergraphStore>, SaveError> {
    let admission = read_admission(handle)?;
    if admission.host_profile != HostProfile::AuthoredGraphV1.manifest_name() {
        return Err(package_refused(format!(
            "the campaign declares {} instead of authored-graph-v1",
            admission.host_profile
        )));
    }
    let scenario = captured_text(handle, &admission.scenario_source_id)?;
    let prelude = admission
        .prelude_source_id
        .as_deref()
        .map(|source_id| captured_text(handle, source_id))
        .transpose()?;
    let rules = captured_text(handle, &admission.rules_source_id)?;
    let defines = single_entry(
        handle,
        ContentEntryKind::CompiledDefinitions,
        AUTHORED_GRAPH_DEFINES_ENTRY,
    )?;
    if defines != AUTHORED_GRAPH_DEFINES {
        return Err(package_refused(
            "the captured authored graph defines are not the fixed `{}` bytes".to_owned(),
        ));
    }
    let (session, _bundle) = michigan_economy::foundation_from_authored_sources_with_seed(
        &scenario,
        prelude.as_deref(),
        &rules,
        &session_identity(admission.resolution_digest),
        &defines,
        admission.seed,
    )
    .map_err(foundation_refused)?;
    verify_static_sections(handle, &session)?;
    Ok(session)
}

/// Advance one authored graph period from captured content and commit it.
///
/// Authored graph campaigns have no player commands, so the replay path uses the
/// empty action batch for every completed period. The store commit is the
/// durable acknowledgement: the session publishes only after it succeeds.
///
/// # Errors
///
/// Refuses a replay refusal, a store refusal, or a mismatch between the committed
/// period and the detached candidate.
pub fn advance_authored_graph_period(
    handle: &mut CampaignHandle,
) -> Result<(IdentifiedTickReport, CommittedPeriod), SaveError> {
    let mut session = authored_graph_replay_session(handle)?;
    let committed_period = handle.current().period;
    let mut sink = CollectingSink::default();
    loop {
        let completed = u64::try_from(session.completed_tick())
            .map_err(|_| package_refused("the replayed tick is negative".to_owned()))?;
        if completed >= committed_period {
            break;
        }
        replay_one_tick(&mut session, &mut sink)?;
    }
    let next_period = u64::try_from(session.completed_tick().checked_add(1).ok_or(
        SaveError::Arithmetic {
            field: "next period",
        },
    )?)
    .map_err(|_| package_refused("the next period is negative".to_owned()))?;
    let actions =
        OrderedPracticeActionBatch::empty(session.session_identity().clone(), next_period)
            .map_err(|error| package_refused(format!("{error:?}")))?;
    let prepared = session
        .prepare_advance(&actions)
        .map_err(|error| package_refused(error.to_string()))?;
    let mut committed = None;
    let (report, disposition) = session
        .commit_prepared_and_publish(&mut sink, prepared, |report| {
            let candidate =
                authored_graph_period_candidate(report, AUTHORED_GRAPH_VIEWER_PLAYER_ID)?;
            let acknowledgement = handle.commit(candidate)?;
            committed = Some(acknowledgement);
            Ok::<ReplayCommitDisposition, SaveError>(ReplayCommitDisposition::Committed)
        })
        .map_err(|error| match error {
            babylon_tick::replay_session::PreparedReplayCommitError::Preflight(error) => {
                package_refused(format!("{error:?}"))
            }
            babylon_tick::replay_session::PreparedReplayCommitError::Commit(error) => error,
        })?;
    if disposition != ReplayCommitDisposition::Committed {
        return Err(package_refused(
            "the authored graph period was not committed".to_owned(),
        ));
    }
    let committed =
        committed.ok_or_else(|| package_refused("no period was committed".to_owned()))?;
    Ok((report, committed))
}

/// Build the prepared period candidate for one identified authored graph report.
///
/// # Errors
///
/// Refuses a negative or zero tick, an overflowing count, or a node fact outside
/// the viewer payload contract.
pub fn authored_graph_period_candidate(
    report: &IdentifiedTickReport,
    player_id: [u8; 8],
) -> Result<PreparedPeriod, SaveError> {
    let period = u64::try_from(report.result_registers().completed_tick())
        .map_err(|_| package_refused("the completed tick is negative".to_owned()))?;
    if period == 0 {
        return Err(package_refused(
            "a committed authored graph period must be positive".to_owned(),
        ));
    }
    // This profile's semantic state is the real geographic material section,
    // exactly as a full checkpoint composes it; authored node facts live in the
    // stable-graph section that full checkpoints already carry.
    let semantic_state = report.material_state_rows().canonical_bytes().to_vec();
    let chunks = committed_chunks(report, semantic_state.clone())?;
    let (journal, knowledge) = viewer_records(report, player_id)?;
    Ok(PreparedPeriod {
        period,
        expected_world_hash: *report.prior_world().digest().as_bytes(),
        world_hash: *report.result_world().digest().as_bytes(),
        state_hash: content_digest::sha256_of(&semantic_state),
        chunks,
        journal,
        knowledge,
        detail: Vec::new(),
    })
}

fn committed_chunks(
    report: &IdentifiedTickReport,
    semantic_state: Vec<u8>,
) -> Result<Vec<StateChunk>, SaveError> {
    let digest = report.content_digest();
    let mut content_hash = Vec::with_capacity(64);
    content_hash.extend_from_slice(&digest.defines_hash);
    content_hash.extend_from_slice(&digest.rules_hash);
    let mut rng_seed = Vec::with_capacity(8);
    rng_seed.extend_from_slice(&report.rng_seed().to_be_bytes());
    let base = vec![
        chunk(
            ChunkSection::StableGraph,
            report.result_stable_graph().canonical_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::WorldRegisters,
            report.result_registers().canonical_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::ResolverManifest,
            report.resolver_manifest_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::PreparedEnvironment,
            report.prepared_environment_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::ReplaySessionIdentity,
            report.replay_session_identity().as_bytes().to_vec(),
        ),
        chunk(ChunkSection::RngSeed, rng_seed),
        chunk(ChunkSection::ContentDigest, content_hash),
        chunk(
            ChunkSection::ReferenceDigest,
            report.reference_digest().as_bytes().to_vec(),
        ),
    ];
    let mut chunks = base;
    chunks.extend(semantic_chunks(semantic_state)?);
    Ok(chunks)
}

fn viewer_records(
    report: &IdentifiedTickReport,
    player_id: [u8; 8],
) -> Result<(Vec<PreparedJournalRecord>, Vec<PreparedKnowledgeGrant>), SaveError> {
    // The nine-table schema's closed subject registry has no authored-node kind.
    // `Observation` is the registry's opaque player-facing subject; the grant
    // payload carries the fixed `Designed` evidence label and the projection never
    // presents the fact as an earned world observation.
    let state = report.result_stable_graph();
    let mut journal = Vec::new();
    let mut knowledge = Vec::new();
    let mut ordinal = 0_i64;
    for (local_name, node_type) in state.rows().nodes() {
        let Some(probability_bits) = probability_bits(state, local_name) else {
            continue;
        };
        let subject_id = viewer_subject_id(state.scenario_scope(), local_name)?;
        let payload = query::encode_authored_graph_node_fact(&query::AuthoredGraphNodeFact {
            subject_id: subject_id.clone(),
            scenario_scope: state.scenario_scope().to_owned(),
            local_name: local_name.clone(),
            node_type: node_type.clone(),
            probability_bits,
            evidence: query::AUTHORED_GRAPH_EVIDENCE_LABEL,
        })
        .map_err(|error| package_refused(error.to_string()))?;
        let subject = PreparedSubject {
            kind: SubjectKind::Observation,
            id: subject_id,
        };
        journal.push(PreparedJournalRecord {
            kind: JournalKind::PlayerReceipt,
            subject: Some(subject.clone()),
            record_key: None,
            payload: payload.clone(),
            resolves_prior_subject: false,
        });
        knowledge.push(PreparedKnowledgeGrant {
            player_id,
            subject,
            grant_key: ordinal,
            payload,
        });
        ordinal = ordinal.checked_add(1).ok_or(SaveError::Arithmetic {
            field: "authored viewer node ordinal",
        })?;
    }
    Ok((journal, knowledge))
}

fn probability_bits(state: &StableGraphState, local_name: &str) -> Option<u64> {
    state
        .rows()
        .node_f64()
        .iter()
        .find(|(node, field, _)| {
            node.as_str() == local_name && field.as_str() == AUTHORED_GRAPH_VIEWER_FIELD
        })
        .map(|(_, _, bits)| *bits)
}

fn viewer_subject_id(scenario_scope: &str, local_name: &str) -> Result<Vec<u8>, SaveError> {
    query::authored_graph_subject_id(scenario_scope, local_name)
        .map_err(|error| package_refused(error.to_string()))
}

fn replay_one_tick(
    session: &mut ReplayTickSession<HypergraphStore>,
    sink: &mut CollectingSink,
) -> Result<(), SaveError> {
    let next_period = u64::try_from(session.completed_tick().checked_add(1).ok_or(
        SaveError::Arithmetic {
            field: "next replayed period",
        },
    )?)
    .map_err(|_| package_refused("the replayed period is negative".to_owned()))?;
    let actions =
        OrderedPracticeActionBatch::empty(session.session_identity().clone(), next_period)
            .map_err(|error| package_refused(format!("{error:?}")))?;
    session
        .advance(sink, &actions)
        .map(|_report| ())
        .map_err(|error| package_refused(error.to_string()))
}

fn admitted_content(
    resolved: &ResolvedContentSet,
    sources: &ReplaySources,
    seed: i64,
) -> Result<AdmittedContent, SaveError> {
    let mut entries = Vec::with_capacity(resolved.units().len() + 3);
    for unit in resolved.units() {
        entries.push(AdmittedContentEntry {
            kind: ContentEntryKind::CapturedSource,
            key: unit.source_id().as_bytes().to_vec(),
            ordinal: 0,
            bytes: unit.bytes().to_vec(),
        });
    }
    entries.push(AdmittedContentEntry {
        kind: ContentEntryKind::Provenance,
        key: b"content-package".to_vec(),
        ordinal: 0,
        bytes: resolved.canonical_bytes().to_vec(),
    });
    entries.push(AdmittedContentEntry {
        kind: ContentEntryKind::CompiledDefinitions,
        key: AUTHORED_GRAPH_DEFINES_ENTRY.to_vec(),
        ordinal: 0,
        bytes: AUTHORED_GRAPH_DEFINES.to_vec(),
    });
    entries.push(AdmittedContentEntry {
        kind: ContentEntryKind::OpeningMetadata,
        key: chunks::AUTHORED_GRAPH_ADMISSION_KEY.to_vec(),
        ordinal: 0,
        bytes: admission_metadata(resolved, sources, seed)?,
    });
    Ok(AdmittedContent {
        campaign_id: CampaignId::from_uuid(admission::campaign_uuid(resolved.digest())),
        build: admission::content_package_build_identity(),
        entries,
    })
}

fn admitted_opening(
    session: &ReplayTickSession<HypergraphStore>,
) -> Result<AdmittedOpening, SaveError> {
    let graph = session
        .stable_graph_state()
        .map_err(|error| package_refused(error.to_string()))?;
    let registers = session
        .world_registers()
        .map_err(|error| package_refused(error.to_string()))?;
    let world = replay_identity::encode_stable_world(&graph, &registers)
        .map_err(|error| package_refused(format!("{error:?}")))?;
    let semantic_state = session
        .current_material_state_rows()
        .map_err(|error| package_refused(error.to_string()))?
        .canonical_bytes()
        .to_vec();
    let digest = session.content_digest();
    let mut content_hash = Vec::with_capacity(64);
    content_hash.extend_from_slice(&digest.defines_hash);
    content_hash.extend_from_slice(&digest.rules_hash);
    let mut opening = vec![
        chunk(ChunkSection::StableGraph, graph.canonical_bytes().to_vec()),
        chunk(
            ChunkSection::WorldRegisters,
            registers.canonical_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::ResolverManifest,
            session.resolver_manifest_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::PreparedEnvironment,
            session.prepared_environment_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::ReplaySessionIdentity,
            session.session_identity().as_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::RngSeed,
            session.rng_seed().to_be_bytes().to_vec(),
        ),
        chunk(ChunkSection::ContentDigest, content_hash),
        chunk(
            ChunkSection::ReferenceDigest,
            session.reference_digest().as_bytes().to_vec(),
        ),
    ];
    opening.extend(semantic_chunks(semantic_state.clone())?);
    Ok(AdmittedOpening {
        world_hash: *world.digest().as_bytes(),
        state_hash: content_digest::sha256_of(&semantic_state),
        chunks: opening,
    })
}

fn verify_static_sections(
    handle: &CampaignHandle,
    session: &ReplayTickSession<HypergraphStore>,
) -> Result<(), SaveError> {
    let digest = session.content_digest();
    let mut content_hash = Vec::with_capacity(64);
    content_hash.extend_from_slice(&digest.defines_hash);
    content_hash.extend_from_slice(&digest.rules_hash);
    let expected = [
        (
            ChunkSection::ResolverManifest,
            session.resolver_manifest_bytes().to_vec(),
        ),
        (
            ChunkSection::PreparedEnvironment,
            session.prepared_environment_bytes().to_vec(),
        ),
        (
            ChunkSection::ReplaySessionIdentity,
            session.session_identity().as_bytes().to_vec(),
        ),
        (
            ChunkSection::RngSeed,
            session.rng_seed().to_be_bytes().to_vec(),
        ),
        (ChunkSection::ContentDigest, content_hash),
        (
            ChunkSection::ReferenceDigest,
            session.reference_digest().as_bytes().to_vec(),
        ),
    ];
    for (section, bytes) in expected {
        let stored = handle.read_section_bytes(section)?;
        if stored != bytes {
            return Err(package_refused(format!(
                "the rebuilt {section:?} section disagrees with the captured campaign"
            )));
        }
    }
    Ok(())
}

struct ReplaySources {
    scenario: String,
    prelude: Option<String>,
    rules: String,
    scenario_source_id: String,
    prelude_source_id: Option<String>,
    rules_source_id: String,
}

impl ReplaySources {
    fn from_resolved(resolved: &ResolvedContentSet) -> Result<Self, SaveError> {
        let mut scenario = None;
        let mut prelude = None;
        let mut rules = None;
        for unit in resolved.units() {
            let text = std::str::from_utf8(unit.bytes())
                .map_err(|_| package_refused("an authored graph source is not UTF-8".to_owned()))?
                .to_owned();
            match unit.kind() {
                SourceKind::Scenario => scenario = Some((unit.source_id().to_owned(), text)),
                SourceKind::Prelude => prelude = Some((unit.source_id().to_owned(), text)),
                SourceKind::Rules => rules = Some((unit.source_id().to_owned(), text)),
                SourceKind::Defines => {
                    return Err(package_refused(
                        "authored-graph-v1 carries no defines unit".to_owned(),
                    ));
                }
            }
        }
        let (scenario_source_id, scenario) = scenario.ok_or_else(|| {
            package_refused("the resolved set carries no scenario unit".to_owned())
        })?;
        let (rules_source_id, rules) = rules
            .ok_or_else(|| package_refused("the resolved set carries no rules unit".to_owned()))?;
        let (prelude_source_id, prelude) =
            prelude.map_or((None, None), |(id, text)| (Some(id), Some(text)));
        Ok(Self {
            scenario,
            prelude,
            rules,
            scenario_source_id,
            prelude_source_id,
            rules_source_id,
        })
    }
}

struct AuthoredAdmission {
    host_profile: String,
    scenario_source_id: String,
    prelude_source_id: Option<String>,
    rules_source_id: String,
    resolution_digest: [u8; 32],
    seed: i64,
}

fn admission_metadata(
    resolved: &ResolvedContentSet,
    sources: &ReplaySources,
    seed: i64,
) -> Result<Vec<u8>, SaveError> {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(ADMISSION_DOMAIN);
    bytes.push(ADMISSION_LAYOUT);
    push_text(&mut bytes, resolved.host_profile().manifest_name())?;
    push_text(&mut bytes, &sources.scenario_source_id)?;
    match &sources.prelude_source_id {
        Some(source_id) => {
            bytes.push(1);
            push_text(&mut bytes, source_id)?;
        }
        None => bytes.push(0),
    }
    push_text(&mut bytes, &sources.rules_source_id)?;
    bytes.extend_from_slice(&seed.to_be_bytes());
    bytes.extend_from_slice(&resolved.digest());
    Ok(bytes)
}

fn read_admission(handle: &CampaignHandle) -> Result<AuthoredAdmission, SaveError> {
    let bytes = single_entry(
        handle,
        ContentEntryKind::OpeningMetadata,
        chunks::AUTHORED_GRAPH_ADMISSION_KEY,
    )?;
    let mut reader = MetadataReader::new(&bytes);
    reader.expect(ADMISSION_DOMAIN)?;
    if reader.u8()? != ADMISSION_LAYOUT {
        return Err(package_refused(
            "the authored admission record declares an unsupported layout".to_owned(),
        ));
    }
    let host_profile = reader.text()?;
    let scenario_source_id = reader.text()?;
    let prelude_source_id = match reader.u8()? {
        0 => None,
        1 => Some(reader.text()?),
        _ => {
            return Err(package_refused(
                "the authored admission prelude marker is invalid".to_owned(),
            ));
        }
    };
    let rules_source_id = reader.text()?;
    let seed = reader.i64()?;
    let resolution_digest = reader.hash()?;
    if !reader.is_empty() {
        return Err(package_refused(
            "the authored admission record carries trailing bytes".to_owned(),
        ));
    }
    Ok(AuthoredAdmission {
        host_profile,
        scenario_source_id,
        prelude_source_id,
        rules_source_id,
        resolution_digest,
        seed,
    })
}

fn captured_text(handle: &CampaignHandle, source_id: &str) -> Result<String, SaveError> {
    let bytes = single_entry(
        handle,
        ContentEntryKind::CapturedSource,
        source_id.as_bytes(),
    )?;
    String::from_utf8(bytes)
        .map_err(|_| package_refused(format!("the captured source {source_id} is not UTF-8")))
}

fn single_entry(
    handle: &CampaignHandle,
    kind: ContentEntryKind,
    key: &[u8],
) -> Result<Vec<u8>, SaveError> {
    let mut fragments = handle.read_content_entry(kind, key)?;
    if fragments.len() != 1 {
        return Err(package_refused(format!(
            "the content entry {key:?} carries {} fragments instead of one",
            fragments.len()
        )));
    }
    Ok(fragments.remove(0))
}

fn session_identity(resolution_digest: [u8; 32]) -> String {
    format!(
        "{SESSION_DOMAIN}{}",
        michigan_economy::digest_hex(&resolution_digest)
    )
}

fn semantic_chunks(bytes: Vec<u8>) -> Result<Vec<StateChunk>, SaveError> {
    if bytes.is_empty() {
        return Ok(vec![StateChunk {
            section: ChunkSection::SemanticState,
            ordinal: 0,
            bytes,
        }]);
    }
    let mut chunks = Vec::new();
    for (ordinal, fragment) in bytes
        .chunks(crate::sqlite_store::MAX_STATE_CHUNK_BYTES)
        .enumerate()
    {
        chunks.push(StateChunk {
            section: ChunkSection::SemanticState,
            ordinal: u32::try_from(ordinal).map_err(|_| SaveError::Arithmetic {
                field: "semantic state fragment ordinal",
            })?,
            bytes: fragment.to_vec(),
        });
    }
    Ok(chunks)
}

fn chunk(section: ChunkSection, bytes: Vec<u8>) -> StateChunk {
    StateChunk {
        section,
        ordinal: 0,
        bytes,
    }
}

fn push_text(output: &mut Vec<u8>, value: &str) -> Result<(), SaveError> {
    if value.is_empty() || value.len() > MAX_METADATA_TEXT_BYTES {
        return Err(package_refused(
            "the authored admission text is empty or beyond its allowance".to_owned(),
        ));
    }
    let length = u32::try_from(value.len()).map_err(|_| SaveError::Arithmetic {
        field: "authored admission text length",
    })?;
    output.extend_from_slice(&length.to_be_bytes());
    output.extend_from_slice(value.as_bytes());
    Ok(())
}

struct MetadataReader<'a> {
    bytes: &'a [u8],
    cursor: usize,
}

impl<'a> MetadataReader<'a> {
    const fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, cursor: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], SaveError> {
        let end = self
            .cursor
            .checked_add(count)
            .filter(|end| *end <= self.bytes.len())
            .ok_or_else(|| {
                package_refused("the authored admission record is truncated".to_owned())
            })?;
        let output = &self.bytes[self.cursor..end];
        self.cursor = end;
        Ok(output)
    }

    fn expect(&mut self, expected: &[u8]) -> Result<(), SaveError> {
        if self.take(expected.len())? != expected {
            return Err(package_refused(
                "the authored admission record carries the wrong domain tag".to_owned(),
            ));
        }
        Ok(())
    }

    fn u8(&mut self) -> Result<u8, SaveError> {
        let [value] = self.take(1)? else {
            return Err(package_refused(
                "the authored admission record is truncated".to_owned(),
            ));
        };
        Ok(*value)
    }

    fn u32(&mut self) -> Result<u32, SaveError> {
        let bytes = self.take(4)?;
        <[u8; 4]>::try_from(bytes)
            .map(u32::from_be_bytes)
            .map_err(|_| package_refused("the authored admission record is truncated".to_owned()))
    }

    fn i64(&mut self) -> Result<i64, SaveError> {
        let bytes = self.take(8)?;
        <[u8; 8]>::try_from(bytes)
            .map(i64::from_be_bytes)
            .map_err(|_| package_refused("the authored admission record is truncated".to_owned()))
    }

    fn hash(&mut self) -> Result<[u8; 32], SaveError> {
        let bytes = self.take(32)?;
        <[u8; 32]>::try_from(bytes).map_err(|_| {
            package_refused("the authored admission digest width is invalid".to_owned())
        })
    }

    fn text(&mut self) -> Result<String, SaveError> {
        let length = usize::try_from(self.u32()?).map_err(|_| {
            package_refused("the authored admission text length is out of range".to_owned())
        })?;
        if length == 0 || length > MAX_METADATA_TEXT_BYTES {
            return Err(package_refused(
                "the authored admission text is empty or beyond its allowance".to_owned(),
            ));
        }
        let bytes = self.take(length)?;
        String::from_utf8(bytes.to_vec())
            .map_err(|_| package_refused("the authored admission text is not UTF-8".to_owned()))
    }

    fn is_empty(&self) -> bool {
        self.cursor == self.bytes.len()
    }
}

fn foundation_refused(error: MichiganEconomyError) -> SaveError {
    package_refused(error.to_string())
}

fn package_refused(reason: String) -> SaveError {
    SaveError::ContentPackage { reason }
}
