//! Contract tests for external content package resolution and admission.

use std::fs;
use std::path::Path;
use std::path::PathBuf;
use std::time::SystemTime;
use std::time::UNIX_EPOCH;

use babylon_bsl::causal_contract::EffectSignature;
use babylon_bsl::causal_contract::EvidenceClass;
use babylon_bsl::causal_contract::RuleRole;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::content_digest;
use babylon_material_circuit::InputOutputCoefficient;
use babylon_material_circuit::UnitId;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_replay::MaterialReplaySession;
use babylon_tick::replay_session::IdentifiedTickReport;
use babylon_tick::replay_session::ReplayCommitDisposition;
use rusqlite::Connection;

use crate::material_runtime::MaterialRuntimeFoundation;
use crate::michigan_content::MichiganContentPreset;
use crate::michigan_material::MichiganMaterialCatalog;
use crate::michigan_material::MichiganMaterialProcess;
use crate::sqlite_store::AuthoredGraphNodeFact;
use crate::sqlite_store::BuildIdentity;
use crate::sqlite_store::CampaignHandle;
use crate::sqlite_store::ChunkSection;
use crate::sqlite_store::CommandError;
use crate::sqlite_store::ContentEntryKind;
use crate::sqlite_store::CurrentChunk;
use crate::sqlite_store::CurrentRoot;
use crate::sqlite_store::HistoryPage;
use crate::sqlite_store::JournalKind;
use crate::sqlite_store::MapSummary;
use crate::sqlite_store::PlayerBody;
use crate::sqlite_store::PlayerCommand;
use crate::sqlite_store::PlayerQuery;
use crate::sqlite_store::PlayerScope;
use crate::sqlite_store::PreparedPeriod;
use crate::sqlite_store::SaveError;
use crate::sqlite_store::SqliteCampaignStore;
use crate::sqlite_store::StateChunk;
use crate::sqlite_store::SubjectCount;
use crate::sqlite_store::SubjectKind;

use super::admission;
use super::audit;
use super::audit::CoefficientAudit;
use super::audit::CoefficientBasis;
use super::audit::CoefficientNormalization;
use super::authored_graph;
use super::error::PackageError;
use super::manifest::HostProfile;
use super::manifest::LoadedPackage;
use super::manifest::SourceKind;
use super::resolver;
use super::resolver::ResolvedContentSet;

const BASE_MANIFEST: &str = r#"format_version = 1
id = "babylon.michigan-regional"
version = "source-99f998e3"
content_abi = "babylon-content-v1"
host_profile = "michigan-regional-v6"
dependencies = []
replacements = []

[[entrypoints]]
source_id = "michigan/defines"
kind = "defines"
path = "defines.toml"
sha256 = "7176764f233190164c985ca3847c42e701ba5421824a4277a51e92739b55a2aa"
"#;

const MOD_MANIFEST: &str = r#"format_version = 1
id = "mods.local.michigan-hours"
version = "1"
content_abi = "babylon-content-v1"
host_profile = "michigan-regional-v6"

[[dependencies]]
id = "babylon.michigan-regional"
version = "source-99f998e3"
manifest_sha256 = "ad2e40c369a427ceb89ce169ed638b2b6f82bcb9d829a24bf9b3aa7262e7e25e"

[[entrypoints]]
source_id = "michigan/defines"
kind = "defines"
path = "defines.toml"
sha256 = "27c7b83e7b0a39dbfc77d325ddd85a7abd3f6538cfea24931088919b1517c7d8"

[[replacements]]
dependency_id = "babylon.michigan-regional"
source_id = "michigan/defines"
expected_sha256 = "7176764f233190164c985ca3847c42e701ba5421824a4277a51e92739b55a2aa"
"#;

const BASE_DEFINES_SHA: &str = "7176764f233190164c985ca3847c42e701ba5421824a4277a51e92739b55a2aa";
const HOURS_44_DEFINES_SHA: &str =
    "27c7b83e7b0a39dbfc77d325ddd85a7abd3f6538cfea24931088919b1517c7d8";

fn authored_scenario() -> &'static str {
    r"(scenario mods/audit-fixture
  (deffield social-class/probability probability intensive)
  (node first NodeType/SOCIAL_CLASS (social-class/probability 0.25p))
  (node second NodeType/SOCIAL_CLASS (social-class/probability 0.5p)))
"
}

fn authored_rule() -> &'static str {
    r#"(rule mods/audit-step
  :role mechanic
  :evidence designed
  :material-basis "A bounded host fixture advances a declared probability field."
  :fuel 64
  (anchor :before survival)
  (bindings
    (binding probability :field social-class/probability))
  (when (<= probability 0.75p))
  (effects
    (update-node self social-class/probability (add 0.125i))))
"#
}

struct TempRoot(PathBuf);

impl TempRoot {
    fn new() -> Self {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("the test clock is after the epoch")
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "babylon-content-package-{}-{nanos}",
            std::process::id()
        ));
        fs::create_dir_all(&path).expect("the temporary package root is creatable");
        Self(path)
    }

    fn path(&self, name: &str) -> PathBuf {
        self.0.join(name)
    }

    fn write(&self, relative: &str, bytes: &[u8]) {
        let path = self.path(relative);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("the package parent directory is creatable");
        }
        fs::write(&path, bytes).expect("the package fixture file is writable");
    }

    fn load(&self, name: &str) -> LoadedPackage {
        LoadedPackage::load(&self.path(name)).expect("the package fixture loads")
    }
}

impl Drop for TempRoot {
    fn drop(&mut self) {
        let result = fs::remove_dir_all(&self.0);
        assert!(
            result.is_ok(),
            "the temporary package root must be removable"
        );
    }
}

fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;

    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut output, "{byte:02x}").expect("writing to a String cannot fail");
    }
    output
}

fn sha256_hex(bytes: &[u8]) -> String {
    hex(&content_digest::sha256_of(bytes))
}

fn base_defines() -> &'static str {
    include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/michigan/defines.toml"
    ))
}

fn defines_with_hours(hours: u32) -> String {
    base_defines().replace(
        "WORK_HOURS_PER_PERSON_WEEK = 40",
        &format!("WORK_HOURS_PER_PERSON_WEEK = {hours}"),
    )
}

fn michigan_base_manifest(defines_sha: &str) -> String {
    format!(
        "format_version = 1\nid = \"babylon.michigan-regional\"\nversion = \"source-99f998e3\"\ncontent_abi = \"babylon-content-v1\"\nhost_profile = \"michigan-regional-v6\"\ndependencies = []\nreplacements = []\n\n[[entrypoints]]\nsource_id = \"michigan/defines\"\nkind = \"defines\"\npath = \"defines.toml\"\nsha256 = \"{defines_sha}\"\n"
    )
}

fn michigan_modification_manifest(defines_sha: &str) -> String {
    format!(
        "format_version = 1\nid = \"mods.local.michigan-hours\"\nversion = \"1\"\ncontent_abi = \"babylon-content-v1\"\nhost_profile = \"michigan-regional-v6\"\n\n[[dependencies]]\nid = \"babylon.michigan-regional\"\nversion = \"source-99f998e3\"\nmanifest_sha256 = \"ad2e40c369a427ceb89ce169ed638b2b6f82bcb9d829a24bf9b3aa7262e7e25e\"\n\n[[entrypoints]]\nsource_id = \"michigan/defines\"\nkind = \"defines\"\npath = \"defines.toml\"\nsha256 = \"{defines_sha}\"\n\n[[replacements]]\ndependency_id = \"babylon.michigan-regional\"\nsource_id = \"michigan/defines\"\nexpected_sha256 = \"{BASE_DEFINES_SHA}\"\n"
    )
}

fn michigan_modification_manifest_for(id: &str, defines_sha: &str) -> String {
    format!(
        "format_version = 1\nid = \"{id}\"\nversion = \"1\"\ncontent_abi = \"babylon-content-v1\"\nhost_profile = \"michigan-regional-v6\"\n\n[[dependencies]]\nid = \"babylon.michigan-regional\"\nversion = \"source-99f998e3\"\nmanifest_sha256 = \"ad2e40c369a427ceb89ce169ed638b2b6f82bcb9d829a24bf9b3aa7262e7e25e\"\n\n[[entrypoints]]\nsource_id = \"michigan/defines\"\nkind = \"defines\"\npath = \"defines.toml\"\nsha256 = \"{defines_sha}\"\n\n[[replacements]]\ndependency_id = \"babylon.michigan-regional\"\nsource_id = \"michigan/defines\"\nexpected_sha256 = \"{BASE_DEFINES_SHA}\"\n"
    )
}

fn write_base(root: &TempRoot, name: &str, defines: &str) {
    let manifest = if defines == base_defines() {
        BASE_MANIFEST.to_owned()
    } else {
        michigan_base_manifest(&sha256_hex(defines.as_bytes()))
    };
    root.write(&format!("{name}/manifest.toml"), manifest.as_bytes());
    root.write(&format!("{name}/defines.toml"), defines.as_bytes());
}

fn write_hours_modification(root: &TempRoot, name: &str, hours: u32) {
    let defines = defines_with_hours(hours);
    let manifest = if defines == defines_with_hours(44) {
        MOD_MANIFEST.to_owned()
    } else {
        michigan_modification_manifest(&sha256_hex(defines.as_bytes()))
    };
    root.write(&format!("{name}/manifest.toml"), manifest.as_bytes());
    root.write(&format!("{name}/defines.toml"), defines.as_bytes());
}

fn resolved_hours(root: &TempRoot, hours: u32) -> ResolvedContentSet {
    write_base(root, "base", base_defines());
    write_hours_modification(root, "mods/local.michigan-hours", hours);
    let packages = [root.load("mods/local.michigan-hours"), root.load("base")];
    resolver::resolve_content_packages(&packages).expect("the authored packages resolve")
}

fn admits_hours(root: &TempRoot, hours: u32) -> Result<CampaignHandle, SaveError> {
    let resolved = resolved_hours(root, hours);
    admission::admit_michigan_regional_package(&resolved, &root.path("campaign.sqlite3"))
}

fn sheet_rolling(catalog: &MichiganMaterialCatalog) -> &MichiganMaterialProcess {
    catalog
        .processes()
        .iter()
        .find(|process| process.key == "sheet-rolling")
        .expect("the Michigan fixture carries the sheet-rolling process")
}

fn available_sheet_hours(
    catalog: &MichiganMaterialCatalog,
    foundation: &MaterialRuntimeFoundation,
) -> u64 {
    let site = sheet_rolling(catalog).site_id();
    foundation
        .initial_register()
        .state()
        .labor
        .iter()
        .find(|row| row.site_id == site)
        .expect("the foundation carries the sheet-rolling labor row")
        .available
}

#[test]
fn worked_example_one_admits_replays_and_preserves_captured_hours() {
    let root = TempRoot::new();
    let forty_four = defines_with_hours(44);
    assert_eq!(
        sha256_hex(BASE_MANIFEST.as_bytes()),
        "ad2e40c369a427ceb89ce169ed638b2b6f82bcb9d829a24bf9b3aa7262e7e25e"
    );
    assert_eq!(sha256_hex(base_defines().as_bytes()), BASE_DEFINES_SHA);
    assert_eq!(sha256_hex(forty_four.as_bytes()), HOURS_44_DEFINES_SHA);

    let resolved = resolved_hours(&root, 44);
    assert_eq!(
        resolved
            .unit("michigan/defines")
            .expect("the effective defines unit is present")
            .bytes(),
        forty_four.as_bytes()
    );
    let (build, admitted_root, expected_chunks) =
        admit_worked_example(&root, &resolved, forty_four.as_bytes());
    replay_from_reopened_campaign(&root, build, &admitted_root, &expected_chunks);
}

fn admit_worked_example(
    root: &TempRoot,
    resolved: &ResolvedContentSet,
    forty_four: &[u8],
) -> (BuildIdentity, CurrentRoot, Vec<(ChunkSection, Vec<u8>)>) {
    let store = root.path("campaign.sqlite3");
    let handle = admission::admit_michigan_regional_package(resolved, &store)
        .expect("the 44-hour package admits");
    let build = handle.build();
    assert_eq!(build, admission::content_package_build_identity());
    let admitted_root = handle.current().clone();
    assert_opening_metadata(&handle, resolved);
    let captured = handle
        .read_content_entry(ContentEntryKind::CapturedSource, b"michigan/defines")
        .expect("the captured defines read back");
    assert_eq!(captured.len(), 1);
    assert_eq!(captured[0], forty_four);
    drop(handle);

    let captured_text = std::str::from_utf8(&captured[0]).expect("the captured defines are UTF-8");
    let catalog = MichiganMaterialCatalog::from_defines_toml(captured_text)
        .expect("the captured defines compile");
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&catalog)
        .expect("the captured defines build the ordinary foundation");
    assert_eq!(catalog.staffing().hours_per_worker_period, 176);
    assert_eq!(available_sheet_hours(&catalog, &foundation), 3_520);
    let process = sheet_rolling(&catalog);
    assert_eq!(process.capacity_batches_per_period, 32);
    assert_eq!(process.opening_planned_batches, 32);
    assert_eq!(
        process.opening_planned_batches * process.labor_hours_per_batch,
        3_200
    );

    let expected_chunks = expected_opening_chunks(&foundation);
    let reconstructed = foundation
        .reconstruct_captured()
        .expect("the captured foundation reconstructs through the durable path");
    let expected_world = reconstructed
        .into_session()
        .expect("the reconstructed foundation opens a session")
        .current_world_hash()
        .expect("the reconstructed opening hashes");
    assert_eq!(
        admitted_root.world_hash, expected_world,
        "the admitted opening world hash must be the captured foundation's world identity"
    );
    assert_eq!(
        admitted_root.state_hash,
        content_digest::sha256_of(foundation.initial_register().canonical_bytes()),
        "the admitted opening state hash must be the captured initial register identity"
    );
    assert_opening_root(&admitted_root, &expected_chunks);
    drop(run_one_material_close(foundation));
    (build, admitted_root, expected_chunks)
}

fn assert_opening_metadata(handle: &CampaignHandle, resolved: &ResolvedContentSet) {
    let metadata = handle
        .read_content_entry(
            ContentEntryKind::OpeningMetadata,
            b"michigan-regional-admission",
        )
        .expect("the admission metadata reads back");
    assert_eq!(metadata.len(), 1, "one opening metadata entry is written");
    assert!(
        metadata[0].ends_with(&resolved.digest()),
        "the opening metadata must bind the canonical resolution digest"
    );
    assert!(
        metadata[0]
            .windows(b"michigan-regional-v6".len())
            .any(|window| window == b"michigan-regional-v6"),
        "the opening metadata must name the admitted host profile"
    );
}

fn replay_from_reopened_campaign(
    root: &TempRoot,
    build: BuildIdentity,
    admitted_root: &CurrentRoot,
    expected_chunks: &[(ChunkSection, Vec<u8>)],
) {
    let store = root.path("campaign.sqlite3");
    root.write(
        "mods/local.michigan-hours/defines.toml",
        defines_with_hours(32).as_bytes(),
    );
    let mut reopened =
        SqliteCampaignStore::open(&store, build).expect("the saved campaign reopens");
    assert_eq!(
        reopened.current(),
        admitted_root,
        "reopening must reproduce the admitted opening root exactly"
    );
    assert_current_chunk_decodes(
        &store,
        reopened.current(),
        ChunkSection::WorldRegisters,
        expected_chunk(expected_chunks, ChunkSection::WorldRegisters),
        "the reopened opening world registers",
    );
    let replay = reopened
        .read_content_entry(ContentEntryKind::CapturedSource, b"michigan/defines")
        .expect("the reopened campaign reads its captured defines");
    assert_eq!(
        replay[0],
        defines_with_hours(44).as_bytes(),
        "reopening must use the captured 44-hour content, not the edited installed file"
    );
    let replayed_text = std::str::from_utf8(&replay[0]).expect("the replay bytes are UTF-8");
    let replayed_catalog = MichiganMaterialCatalog::from_defines_toml(replayed_text)
        .expect("the captured replay defines compile");
    let replayed_foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&replayed_catalog)
        .expect("the captured replay defines build the ordinary foundation");
    assert_eq!(replayed_catalog.staffing().hours_per_worker_period, 176);
    assert_eq!(
        available_sheet_hours(&replayed_catalog, &replayed_foundation),
        3_520
    );

    let session = run_one_material_close(replayed_foundation);
    let prepared = prepared_material_close(&session, reopened.current().world_hash);
    let committed = reopened
        .commit(prepared)
        .expect("the reopened campaign commits the captured-content close");
    assert_eq!(committed.period, 1);
    assert_eq!(
        committed.world_hash,
        session
            .current_world_hash()
            .expect("the closed session hashes"),
        "the committed world hash must be the close's own world identity"
    );
    assert_eq!(reopened.current().period, 1);
    let advanced_stable_graph = session
        .graph_session()
        .stable_graph_state()
        .expect("the closed session recomposes its stable graph")
        .canonical_bytes()
        .to_vec();
    drop(reopened);

    let advanced = SqliteCampaignStore::open(&store, build)
        .expect("the advanced campaign reopens after the captured-content close");
    assert_eq!(advanced.current().period, 1);
    assert_eq!(advanced.current().world_hash, committed.world_hash);
    assert_current_chunk_decodes(
        &store,
        advanced.current(),
        ChunkSection::StableGraph,
        &advanced_stable_graph,
        "the advanced stable graph",
    );
}

fn expected_chunk(chunks: &[(ChunkSection, Vec<u8>)], section: ChunkSection) -> &[u8] {
    &chunks
        .iter()
        .find(|(candidate, _)| *candidate == section)
        .expect("the captured foundation carries the requested section")
        .1
}

fn assert_current_chunk_decodes(
    store: &Path,
    root: &CurrentRoot,
    section: ChunkSection,
    expected: &[u8],
    description: &str,
) {
    let chunk = root
        .chunks
        .iter()
        .find(|chunk| chunk.section == section)
        .expect("the current root carries the requested section");
    assert_state_chunk_decodes(store, chunk, expected, description);
}

fn expected_opening_chunks(foundation: &MaterialRuntimeFoundation) -> Vec<(ChunkSection, Vec<u8>)> {
    let graph = foundation.graph_foundation();
    let digest = graph.content_digest();
    let mut content_hash = Vec::with_capacity(64);
    content_hash.extend_from_slice(&digest.defines_hash);
    content_hash.extend_from_slice(&digest.rules_hash);
    vec![
        (
            ChunkSection::StableGraph,
            graph.stable_graph_bytes().to_vec(),
        ),
        (
            ChunkSection::WorldRegisters,
            graph.world_register_bytes().to_vec(),
        ),
        (
            ChunkSection::ResolverManifest,
            graph.resolver_manifest_bytes().to_vec(),
        ),
        (
            ChunkSection::PreparedEnvironment,
            graph.prepared_environment_bytes().to_vec(),
        ),
        (
            ChunkSection::ReplaySessionIdentity,
            graph.replay_session_identity().as_bytes().to_vec(),
        ),
        (
            ChunkSection::RngSeed,
            graph.rng_seed().to_be_bytes().to_vec(),
        ),
        (ChunkSection::ContentDigest, content_hash),
        (
            ChunkSection::ReferenceDigest,
            graph.reference_digest().as_bytes().to_vec(),
        ),
    ]
}

fn assert_opening_root(root: &CurrentRoot, expected_chunks: &[(ChunkSection, Vec<u8>)]) {
    assert_eq!(root.period, 0, "the admitted opening is period zero");
    assert_eq!(
        root.chunks.len(),
        expected_chunks.len(),
        "the admitted opening carries every foundation section exactly once"
    );
    for (chunk, (section, bytes)) in root.chunks.iter().zip(expected_chunks) {
        assert_eq!(
            chunk.section, *section,
            "the admitted opening chunks follow section order"
        );
        assert_eq!(chunk.ordinal, 0, "each opening section has one fragment");
        assert_eq!(
            usize::try_from(chunk.raw_len).expect("a stored chunk length is bounded"),
            bytes.len(),
            "the admitted {section:?} chunk length must match the captured foundation"
        );
        assert_eq!(
            chunk.raw_hash,
            content_digest::sha256_of(bytes),
            "the admitted {section:?} chunk digest must match the captured foundation"
        );
    }
    assert!(
        root.chunks
            .iter()
            .all(|chunk| chunk.section != ChunkSection::SemanticState),
        "the numeric opening leaves SemanticState ordinal zero to profile semantic state"
    );
}

fn assert_state_chunk_decodes(
    store: &Path,
    chunk: &CurrentChunk,
    expected: &[u8],
    description: &str,
) {
    let connection = Connection::open(store).expect("the campaign database opens for a readback");
    let decoded = crate::sqlite_store::read_state_chunk(&connection, chunk.chunk_id)
        .expect("the stored state chunk decodes through the payload codec");
    assert_eq!(
        decoded, expected,
        "{description} must decode to the captured foundation bytes"
    );
}

fn prepared_material_close(
    session: &MaterialReplaySession<HypergraphStore>,
    expected_world: [u8; 32],
) -> PreparedPeriod {
    let graph = session.graph_session();
    let digest = graph.content_digest();
    let mut content_hash = Vec::with_capacity(64);
    content_hash.extend_from_slice(&digest.defines_hash);
    content_hash.extend_from_slice(&digest.rules_hash);
    PreparedPeriod {
        period: session.completed_tick(),
        expected_world_hash: expected_world,
        world_hash: session
            .current_world_hash()
            .expect("the closed session hashes"),
        state_hash: content_digest::sha256_of(session.material().canonical_bytes()),
        chunks: vec![
            StateChunk {
                section: ChunkSection::StableGraph,
                ordinal: 0,
                bytes: graph
                    .stable_graph_state()
                    .expect("the closed session recomposes its stable graph")
                    .canonical_bytes()
                    .to_vec(),
            },
            StateChunk {
                section: ChunkSection::WorldRegisters,
                ordinal: 0,
                bytes: graph
                    .world_registers()
                    .expect("the closed session recomposes its world registers")
                    .canonical_bytes()
                    .to_vec(),
            },
            StateChunk {
                section: ChunkSection::ResolverManifest,
                ordinal: 0,
                bytes: graph.resolver_manifest_bytes().to_vec(),
            },
            StateChunk {
                section: ChunkSection::PreparedEnvironment,
                ordinal: 0,
                bytes: graph.prepared_environment_bytes().to_vec(),
            },
            StateChunk {
                section: ChunkSection::ReplaySessionIdentity,
                ordinal: 0,
                bytes: graph.session_identity().as_bytes().to_vec(),
            },
            StateChunk {
                section: ChunkSection::RngSeed,
                ordinal: 0,
                bytes: graph.rng_seed().to_be_bytes().to_vec(),
            },
            StateChunk {
                section: ChunkSection::ContentDigest,
                ordinal: 0,
                bytes: content_hash,
            },
            StateChunk {
                section: ChunkSection::ReferenceDigest,
                ordinal: 0,
                bytes: graph.reference_digest().as_bytes().to_vec(),
            },
        ],
        journal: Vec::new(),
        knowledge: Vec::new(),
        detail: Vec::new(),
        tick_identity: None,
    }
}

fn run_one_material_close(
    foundation: MaterialRuntimeFoundation,
) -> MaterialReplaySession<HypergraphStore> {
    let mut session: MaterialReplaySession<HypergraphStore> = foundation
        .into_session()
        .expect("the admitted foundation opens a material session");
    let actions = OrderedPracticeActionBatch::empty(
        session.graph_session().session_identity().clone(),
        session.completed_tick() + 1,
    )
    .expect("the empty player action batch constructs");
    let prepared = session
        .prepare_advance(&actions)
        .expect("the ordinary material close prepares");
    let mut sink = CollectingSink::default();
    session
        .commit_prepared_and_publish(&mut sink, prepared, |_, _| {
            Ok::<ReplayCommitDisposition, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("the ordinary material close commits");
    assert_eq!(session.completed_tick(), 1);
    session
}

#[test]
fn worked_example_one_shuffled_discovery_preserves_resolved_identity() {
    let first = TempRoot::new();
    write_base(&first, "base", base_defines());
    write_hours_modification(&first, "mods/local.michigan-hours", 44);
    let forward = [first.load("base"), first.load("mods/local.michigan-hours")];
    let forward =
        resolver::resolve_content_packages(&forward).expect("the authored packages resolve");

    let second = TempRoot::new();
    write_base(&second, "base", base_defines());
    write_hours_modification(&second, "mods/local.michigan-hours", 44);
    let reversed = [
        second.load("mods/local.michigan-hours"),
        second.load("base"),
    ];
    let reversed =
        resolver::resolve_content_packages(&reversed).expect("the authored packages resolve");

    assert_eq!(forward.canonical_bytes(), reversed.canonical_bytes());
    assert_eq!(forward.digest(), reversed.digest());
    assert_eq!(
        forward
            .unit("michigan/defines")
            .expect("the effective defines unit is present")
            .origin(),
        "mods.local.michigan-hours"
    );
}

#[test]
fn infeasible_opening_at_32_hours_is_refused() {
    let root = TempRoot::new();
    let error = admits_hours(&root, 32).expect_err("a 2,560-hour opening plan is infeasible");
    assert!(
        error.to_string().contains("opening plan"),
        "the refusal must name the infeasible opening: {error}"
    );
}

#[test]
fn out_of_domain_hours_zero_and_169_are_refused() {
    for hours in [0, 169] {
        let root = TempRoot::new();
        let error = admits_hours(&root, hours).expect_err("the hours domain must refuse");
        assert!(
            error.to_string().contains("WORK_HOURS_PER_PERSON_WEEK"),
            "the refusal must name the hours dial for {hours}: {error}"
        );
    }
}

#[test]
fn unknown_toml_keys_are_refused() {
    let root = TempRoot::new();
    let source = format!("{}UNKNOWN_KEY = 7\n", base_defines());
    write_base(&root, "base", &source);
    let packages = [root.load("base")];
    let resolved =
        resolver::resolve_content_packages(&packages).expect("the package manifests resolve");
    let error =
        admission::admit_michigan_regional_package(&resolved, &root.path("campaign.sqlite3"))
            .expect_err("an unknown TOML key must refuse admission");
    assert!(
        error.to_string().contains("unknown field") || error.to_string().contains("UNKNOWN_KEY"),
        "the refusal must name the unknown key: {error}"
    );
}

#[test]
fn un_chained_duplicate_replacement_is_refused() {
    let root = TempRoot::new();
    write_base(&root, "base", base_defines());
    write_hours_modification(&root, "mods/local.michigan-hours", 44);
    let other = "mods.other.michigan-hours";
    root.write(
        &format!("{other}/manifest.toml"),
        michigan_modification_manifest_for(
            "mods.other.michigan-hours",
            &sha256_hex(defines_with_hours(48).as_bytes()),
        )
        .as_bytes(),
    );
    root.write(
        &format!("{other}/defines.toml"),
        defines_with_hours(48).as_bytes(),
    );
    let packages = [
        root.load("base"),
        root.load("mods/local.michigan-hours"),
        root.load(other),
    ];
    let error = resolver::resolve_content_packages(&packages)
        .expect_err("two packages cannot replace one source without chaining");
    assert!(
        matches!(error, PackageError::ReplacementConflict { .. }),
        "the refusal must name the replacement conflict: {error:?}"
    );
}

#[test]
fn replacement_expected_digest_must_match_the_current_source() {
    let root = TempRoot::new();
    write_base(&root, "base", base_defines());
    let manifest = MOD_MANIFEST.replace(
        "expected_sha256 = \"7176764f233190164c985ca3847c42e701ba5421824a4277a51e92739b55a2aa\"",
        "expected_sha256 = \"0000000000000000000000000000000000000000000000000000000000000000\"",
    );
    root.write(
        "mods/local.michigan-hours/manifest.toml",
        manifest.as_bytes(),
    );
    root.write(
        "mods/local.michigan-hours/defines.toml",
        defines_with_hours(44).as_bytes(),
    );
    let packages = [root.load("base"), root.load("mods/local.michigan-hours")];
    let error = resolver::resolve_content_packages(&packages)
        .expect_err("a replacement must name the current predecessor digest");
    assert!(
        matches!(error, PackageError::ReplacementDigestMismatch { .. }),
        "the refusal must name the replacement digest: {error:?}"
    );
}

#[test]
fn replacement_kind_mismatch_is_refused() {
    let root = TempRoot::new();
    write_base(&root, "base", base_defines());
    let scenario = authored_scenario();
    let manifest = michigan_modification_manifest(&sha256_hex(scenario.as_bytes()))
        .replace("kind = \"defines\"", "kind = \"scenario\"")
        .replace("path = \"defines.toml\"", "path = \"scenario.bscn\"");
    root.write(
        "mods/local.michigan-hours/manifest.toml",
        manifest.as_bytes(),
    );
    root.write(
        "mods/local.michigan-hours/scenario.bscn",
        scenario.as_bytes(),
    );
    let packages = [root.load("base"), root.load("mods/local.michigan-hours")];
    let error = resolver::resolve_content_packages(&packages)
        .expect_err("a replacement cannot change the source kind");
    assert!(
        matches!(error, PackageError::ReplacementKindMismatch { .. }),
        "the refusal must name the replacement kind: {error:?}"
    );
}

#[test]
fn cyclic_dependencies_are_refused() {
    let root = TempRoot::new();
    let scenario = authored_scenario().as_bytes();
    let rules = authored_rule().as_bytes();
    write_package(
        &root,
        "mods.cycle-a",
        "mods.cycle-a",
        "mods.cycle-b",
        Some("mods.cycle-b"),
        scenario,
        rules,
    );
    write_package(
        &root,
        "mods.cycle-b",
        "mods.cycle-b",
        "mods.cycle-a",
        Some("mods.cycle-a"),
        scenario,
        rules,
    );
    let packages = [root.load("mods.cycle-a"), root.load("mods.cycle-b")];
    let error = resolver::resolve_content_packages(&packages)
        .expect_err("the dependency cycle must refuse");
    assert!(
        matches!(error, PackageError::DependencyCycle { .. }),
        "the refusal must name the cycle: {error:?}"
    );
}

#[test]
fn parent_traversal_and_absolute_paths_are_refused() {
    for path in ["../escape.toml", "/tmp/escape.toml", "sub\\escape.toml"] {
        let root = TempRoot::new();
        let manifest =
            authored_manifest_with_path("mods.path-traversal", path, authored_rule().as_bytes());
        root.write("package/manifest.toml", manifest.as_bytes());
        root.write("package/scenario.bscn", authored_scenario().as_bytes());
        let error = LoadedPackage::load(&root.path("package"))
            .expect_err("the escape path must be refused");
        assert!(
            matches!(
                error,
                PackageError::InvalidSourcePath { .. } | PackageError::SourceOutsidePackage { .. }
            ),
            "the refusal must name the path escape for {path}: {error:?}"
        );
    }
}

#[test]
fn missing_dependency_and_digest_mismatch_are_refused() {
    let root = TempRoot::new();
    write_hours_modification(&root, "mods/local.michigan-hours", 44);
    let packages = [root.load("mods/local.michigan-hours")];
    let error = resolver::resolve_content_packages(&packages)
        .expect_err("the absent dependency must refuse");
    assert!(
        matches!(error, PackageError::MissingDependency { .. }),
        "the refusal must name the missing dependency: {error:?}"
    );

    let second = TempRoot::new();
    write_base(&second, "base", base_defines());
    second.write(
        "mods/local.michigan-hours/manifest.toml",
        MOD_MANIFEST.as_bytes(),
    );
    second.write(
        "mods/local.michigan-hours/defines.toml",
        base_defines().as_bytes(),
    );
    let _base = second.load("base");
    let error = LoadedPackage::load(&second.path("mods/local.michigan-hours"))
        .expect_err("a source digest mismatch must refuse before replacement");
    assert!(
        matches!(error, PackageError::DigestMismatch { .. }),
        "the refusal must name the digest mismatch: {error:?}"
    );
}

#[test]
fn source_digest_must_match_the_declared_sha256() {
    let root = TempRoot::new();
    write_base(&root, "base", base_defines());
    root.write("base/defines.toml", defines_with_hours(44).as_bytes());
    let error = LoadedPackage::load(&root.path("base")).expect_err("tampered source must refuse");
    assert!(
        matches!(error, PackageError::DigestMismatch { .. }),
        "the refusal must name the digest mismatch: {error:?}"
    );
}

#[test]
fn unknown_rule_id_is_refused() {
    let rules = authored_rule().replace(":before survival", ":after no-such-system");
    let error = resolve_authored(authored_scenario(), &rules)
        .expect_err("an unknown phase system must refuse at load");
    assert!(
        matches!(error, PackageError::UnknownRuleId { .. }),
        "the refusal must name the unknown rule home: {error:?}"
    );
}

#[test]
fn unconsumed_dial_is_refused() {
    let scenario = authored_scenario().replace(
        "  (deffield social-class/probability probability intensive)",
        "  (deffield social-class/probability probability intensive)\n  (defconst mods/unused-dial 2)",
    );
    let error = resolve_authored(&scenario, authored_rule())
        .expect_err("an unused defconst must refuse at load");
    assert!(
        matches!(error, PackageError::UnconsumedDial { .. }),
        "the refusal must name the unconsumed dial: {error:?}"
    );
}

#[test]
fn unlisted_state_action_pair_is_refused() {
    let rules = authored_rule().replace(
        "social-class/probability (add 0.125i)",
        "social-class/undeclared (add 0.125i)",
    );
    let error = resolve_authored(authored_scenario(), &rules)
        .expect_err("a write to an undeclared state field must refuse at load");
    assert!(
        matches!(error, PackageError::UnlistedStateActionPair { .. }),
        "the refusal must name the unlisted state/action pair: {error:?}"
    );
}

#[test]
fn duplicate_cost_for_one_pair_is_refused() {
    let second = authored_rule()
        .replace("mods/audit-step", "mods/audit-step-two")
        .replace(":fuel 64", ":fuel 32");
    let rules = format!("{}{second}", authored_rule());
    let error = resolve_authored(authored_scenario(), &rules)
        .expect_err("a second cost for one state/action pair must refuse at load");
    assert!(
        matches!(error, PackageError::DuplicateCost { .. }),
        "the refusal must name the duplicate cost: {error:?}"
    );
}

#[test]
fn duplicate_cost_across_phase_anchors_is_refused() {
    let second = authored_rule()
        .replace("mods/audit-step", "mods/audit-step-two")
        .replace(":fuel 64", ":fuel 32")
        .replace("(anchor :before survival)", "(anchor :after survival)");
    let rules = format!("{}{second}", authored_rule());
    let error = resolve_authored(authored_scenario(), &rules)
        .expect_err("the same state/action pair must carry one cost even from two phase anchors");
    assert!(
        matches!(error, PackageError::DuplicateCost { .. }),
        "the refusal must name the duplicate cost across distinct anchors: {error:?}"
    );
}

fn resolve_authored(scenario: &str, rules: &str) -> Result<ResolvedContentSet, PackageError> {
    let root = TempRoot::new();
    let manifest = authored_manifest_for("mods.audit-fixture", scenario, rules);
    root.write("package/manifest.toml", manifest.as_bytes());
    root.write("package/scenario.bscn", scenario.as_bytes());
    root.write("package/rules.bsl", rules.as_bytes());
    resolver::resolve_content_packages(&[root.load("package")])
}

#[test]
fn catalog_coefficients_declare_basis_and_unit() {
    let catalog = crate::test_support::catalog();
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&catalog)
        .expect("the authored catalog builds the foundation");
    let normalization = CoefficientNormalization::new(catalog.staffing().hours_per_worker_period)
        .expect("the authored normalization is a whole number of weeks");
    let audit: CoefficientAudit =
        audit::audit_catalog_coefficients(foundation.material_catalog(), normalization)
            .expect("the authored catalog coefficients declare basis and unit");
    assert!(!audit.rows().is_empty());
    assert!(audit
        .rows()
        .iter()
        .all(|row| row.basis().is_some() && row.unit().is_some()));
    assert!(audit
        .rows()
        .iter()
        .any(|row| row.basis() == Some(CoefficientBasis::PerBatch)));
}

#[test]
fn missing_coefficient_basis_or_unit_is_refused() {
    let catalog = crate::test_support::catalog();
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&catalog)
        .expect("the authored catalog builds the foundation");
    let normalization = CoefficientNormalization::new(catalog.staffing().hours_per_worker_period)
        .expect("the authored normalization is a whole number of weeks");

    let mut missing_unit = foundation.material_catalog().clone();
    let template = missing_unit
        .input_coefficients
        .first()
        .expect("the authored catalog has an input coefficient")
        .clone();
    missing_unit
        .input_coefficients
        .push(InputOutputCoefficient {
            unit_id: UnitId::from_bytes([0; 32]),
            ..template.clone()
        });
    let error = audit::audit_catalog_coefficients(&missing_unit, normalization)
        .expect_err("a coefficient without a declared unit must refuse");
    assert!(
        matches!(error, PackageError::MissingCoefficientUnit { .. }),
        "the refusal must name the missing unit: {error:?}"
    );

    let mut missing_basis = foundation.material_catalog().clone();
    missing_basis
        .labor_coefficients
        .first_mut()
        .expect("the authored catalog has a labor coefficient")
        .quantity_per_batch = 0;
    let error = audit::audit_catalog_coefficients(&missing_basis, normalization)
        .expect_err("a zero coefficient declares no basis and must refuse");
    assert!(
        matches!(error, PackageError::MissingCoefficientBasis { .. }),
        "the refusal must name the missing basis: {error:?}"
    );
}

#[test]
fn shared_normalizing_constant_must_be_consistent() {
    let error = CoefficientNormalization::new(161)
        .expect_err("a period normalization must be a whole number of four-week periods");
    assert!(
        matches!(error, PackageError::InconsistentNormalizingConstant { .. }),
        "the refusal must name the inconsistent constant: {error:?}"
    );

    let catalog = crate::test_support::catalog();
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&catalog)
        .expect("the authored catalog builds the foundation");
    let normalization = CoefficientNormalization::new(catalog.staffing().hours_per_worker_period)
        .expect("the authored normalization is a whole number of weeks");
    let mut second_labor_unit = foundation.material_catalog().clone();
    let second_unit = second_labor_unit
        .labor_coefficients
        .first_mut()
        .expect("the authored catalog has a labor coefficient")
        .unit_id;
    second_labor_unit
        .labor_coefficients
        .last_mut()
        .expect("the authored catalog has a labor coefficient")
        .unit_id = UnitId::from_bytes([second_unit.as_bytes()[0].wrapping_add(1); 32]);
    let error = audit::audit_catalog_coefficients(&second_labor_unit, normalization)
        .expect_err("two labor units cannot share one normalization");
    assert!(
        matches!(error, PackageError::InconsistentNormalizingConstant { .. }),
        "the refusal must name the inconsistent constant: {error:?}"
    );
}

#[test]
fn effect_signature_is_closed_and_every_variant_is_reachable_by_footprint() {
    let catalog = crate::test_support::catalog();
    let mechanical = audit::audit_rule_set(
        catalog.graph_scenario_source(),
        None,
        &[catalog.rule_source()],
    )
    .expect("the first-party material content audits");
    let organizer = audit::audit_rule_set(
        effect_coverage_scenario(),
        None,
        &[organizer_effect_rules()],
    )
    .expect("the first-party organizer intrinsics audit");
    let fixture =
        audit::audit_rule_set(effect_coverage_scenario(), None, &[effect_coverage_rules()])
            .expect("the bounded effect fixture audits");

    let mut admitted = Vec::new();
    for audit in [&mechanical, &organizer, &fixture] {
        for rule in audit.rules() {
            for effect in rule.effects() {
                admitted.push(effect_variant(effect));
            }
        }
    }
    // `Shape` verbs are expressible and statically inspected but deferred at
    // load, so `Shape` claims footprint coverage, never admission. The closed
    // enum is still fully enumerated: admission covers the other seven variants.
    let footprint_only = shape_fixture_footprint()
        .iter()
        .map(effect_variant)
        .collect::<Vec<_>>();

    for variant in EffectVariant::ADMITTED {
        assert!(
            admitted.contains(&variant),
            "no admitted content reaches the closed EffectSignature variant {variant:?}; observed {admitted:?}"
        );
    }
    for variant in EffectVariant::FOOTPRINT_ONLY {
        assert!(
            footprint_only.contains(&variant),
            "no content footprint names the deferred EffectSignature variant {variant:?}; observed {footprint_only:?}"
        );
        assert!(
            !admitted.contains(&variant),
            "the deferred EffectSignature variant {variant:?} cannot be claimed as admitted content"
        );
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum EffectVariant {
    MaterialCycle,
    OrganizerProducts,
    OrganizerPractice,
    NodeField,
    EdgeField,
    HyperedgeField,
    Event,
    Shape,
}

impl EffectVariant {
    /// Variants at least one admitted content set reaches.
    const ADMITTED: [Self; 7] = [
        Self::MaterialCycle,
        Self::OrganizerProducts,
        Self::OrganizerPractice,
        Self::NodeField,
        Self::EdgeField,
        Self::HyperedgeField,
        Self::Event,
    ];
    /// Variants reachable in a decoded content footprint but deferred at load.
    const FOOTPRINT_ONLY: [Self; 1] = [Self::Shape];
}

fn effect_variant(effect: &EffectSignature) -> EffectVariant {
    match effect {
        EffectSignature::MaterialCycle => EffectVariant::MaterialCycle,
        EffectSignature::OrganizerProducts => EffectVariant::OrganizerProducts,
        EffectSignature::OrganizerPractice => EffectVariant::OrganizerPractice,
        EffectSignature::NodeField(_) => EffectVariant::NodeField,
        EffectSignature::EdgeField(_) => EffectVariant::EdgeField,
        EffectSignature::HyperedgeField(_) => EffectVariant::HyperedgeField,
        EffectSignature::Event(_) => EffectVariant::Event,
        EffectSignature::Shape(_) => EffectVariant::Shape,
    }
}

fn effect_coverage_scenario() -> &'static str {
    r"(scenario mods/effect-coverage
  (deffield social-class/probability probability intensive)
  (deffield solidarity/strength coefficient intensive)
  (deffield economic-sector/output int extensive)
  (node first NodeType/SOCIAL_CLASS (social-class/probability 0.25p))
  (node second NodeType/SOCIAL_CLASS (social-class/probability 0.5p))
  (edge EdgeType/SOLIDARITY first second 1)
  (hyperedge sector HyperedgeType/ECONOMIC_SECTOR (members first second)))
"
}

fn organizer_effect_rules() -> &'static str {
    r#"(rule organizer/organizer-products
  :role mechanic
  :evidence designed
  :material-basis "Consume only previously committed products through the captured scope."
  :fuel 1000000
  (anchor :before ooda)
  (organizer-products))

(rule organizer/organizer-practice
  :role intent
  :evidence designed
  :material-basis "Resolve one authorized practice against finite contributor time."
  :fuel 1000000
  (anchor :after ooda)
  (organizer-practice))
"#
}

fn effect_coverage_rules() -> &'static str {
    r#"(rule mods/effect-node
  :role mechanic
  :evidence designed
  :material-basis "A bounded host fixture writes a declared node field and emits a recognized pattern."
  :fuel 128
  (anchor :before survival)
  (bindings (binding probability :field social-class/probability))
  (effects
    (update-node self social-class/probability (add 0.125i))
    (emit EventType/RUPTURE)))

(rule mods/effect-edge
  :role mechanic
  :evidence designed
  :material-basis "A bounded host fixture writes a declared edge field."
  :fuel 256
  (anchor :before survival)
  (bindings)
  (effects
    (for-each (edges EdgeType/SOLIDARITY)
      (update-edge it solidarity/strength (set 1)))))

(rule mods/effect-hyperedge
  :role mechanic
  :evidence designed
  :material-basis "A bounded host fixture writes a declared hyperedge field."
  :fuel 256
  (anchor :before survival)
  (bindings)
  (effects
    (for-each (hyperedges HyperedgeType/ECONOMIC_SECTOR)
      (update-hyperedge it economic-sector/output (set 5)))))
"#
}

fn shape_fixture_footprint() -> Vec<EffectSignature> {
    let form = babylon_bsl::reader::read(
        r#"(rule mods/effect-shape
  :role mechanic
  :evidence designed
  :material-basis "A bounded host fixture names a graph-shape operation the loader defers."
  :fuel 64
  (anchor :before survival)
  (bindings)
  (effects (remove-node self)))"#,
    )
    .expect("the shape fixture reads");
    babylon_bsl::causal_contract::effect_footprint(&form.0).expect("the shape footprint walks")
}

fn authored_manifest_with_path(id: &str, path: &str, rules: &[u8]) -> String {
    let toml_path = path.replace('\\', "\\\\");
    format!(
        "format_version = 1\nid = \"{id}\"\nversion = \"1\"\ncontent_abi = \"babylon-content-v1\"\nhost_profile = \"authored-graph-v1\"\ndependencies = []\nreplacements = []\n\n[[entrypoints]]\nsource_id = \"{id}/scenario\"\nkind = \"scenario\"\npath = \"scenario.bscn\"\nsha256 = \"{}\"\n\n[[entrypoints]]\nsource_id = \"{id}/rules\"\nkind = \"rules\"\npath = \"{toml_path}\"\nsha256 = \"{}\"\n",
        sha256_hex(authored_scenario().as_bytes()),
        sha256_hex(rules),
    )
}

fn authored_manifest_for(id: &str, scenario: &str, rules: &str) -> String {
    format!(
        "format_version = 1\nid = \"{id}\"\nversion = \"1\"\ncontent_abi = \"babylon-content-v1\"\nhost_profile = \"authored-graph-v1\"\ndependencies = []\nreplacements = []\n\n[[entrypoints]]\nsource_id = \"{id}/scenario\"\nkind = \"scenario\"\npath = \"scenario.bscn\"\nsha256 = \"{}\"\n\n[[entrypoints]]\nsource_id = \"{id}/rules\"\nkind = \"rules\"\npath = \"rules.bsl\"\nsha256 = \"{}\"\n",
        sha256_hex(scenario.as_bytes()),
        sha256_hex(rules.as_bytes()),
    )
}

fn authored_manifest(id: &str) -> String {
    authored_manifest_with_path(id, "rules.bsl", authored_rule().as_bytes())
}

#[allow(
    clippy::too_many_arguments,
    reason = "the fixture builder names every manifest axis explicitly"
)]
fn write_package(
    root: &TempRoot,
    directory: &str,
    id: &str,
    dependency_id: &str,
    dependency_manifest_id: Option<&str>,
    scenario: &[u8],
    rules: &[u8],
) {
    let dependency = dependency_manifest_id.map_or_else(
        || "dependencies = []\n".to_owned(),
        |manifest_id| {
            format!(
                "[[dependencies]]\nid = \"{manifest_id}\"\nversion = \"1\"\nmanifest_sha256 = \"{}\"\n",
                sha256_hex(authored_manifest(dependency_id).as_bytes())
            )
        },
    );
    let manifest = format!(
        "format_version = 1\nid = \"{id}\"\nversion = \"1\"\ncontent_abi = \"babylon-content-v1\"\nhost_profile = \"authored-graph-v1\"\nreplacements = []\n{dependency}\n[[entrypoints]]\nsource_id = \"{id}/scenario\"\nkind = \"scenario\"\npath = \"scenario.bscn\"\nsha256 = \"{}\"\n\n[[entrypoints]]\nsource_id = \"{id}/rules\"\nkind = \"rules\"\npath = \"rules.bsl\"\nsha256 = \"{}\"\n",
        sha256_hex(scenario),
        sha256_hex(rules),
    );
    root.write(&format!("{directory}/manifest.toml"), manifest.as_bytes());
    root.write(&format!("{directory}/scenario.bscn"), scenario);
    root.write(&format!("{directory}/rules.bsl"), rules);
}

#[test]
fn authored_graph_profile_requires_exact_source_kinds() {
    let root = TempRoot::new();
    root.write(
        "package/manifest.toml",
        authored_manifest("mods.valid").as_bytes(),
    );
    root.write("package/scenario.bscn", authored_scenario().as_bytes());
    root.write("package/rules.bsl", authored_rule().as_bytes());
    let package = root.load("package");
    let resolved =
        resolver::resolve_content_packages(&[package]).expect("the authored package resolves");
    assert_eq!(resolved.host_profile(), HostProfile::AuthoredGraphV1);
    admission::validate_profile_sources(&resolved).expect("the exact source kinds admit");

    let root = TempRoot::new();
    let prelude = b"(deffield social-class/extra probability intensive)\n";
    let mut manifest = authored_manifest("mods.missing-rules");
    manifest = manifest.replace("kind = \"rules\"", "kind = \"prelude\"");
    manifest = manifest.replace(
        &sha256_hex(authored_rule().as_bytes()),
        &sha256_hex(prelude),
    );
    root.write("package/manifest.toml", manifest.as_bytes());
    root.write("package/scenario.bscn", authored_scenario().as_bytes());
    root.write("package/rules.bsl", prelude);
    let package = root.load("package");
    let resolved = resolver::resolve_content_packages(&[package]).expect("the package resolves");
    let error = admission::validate_profile_sources(&resolved)
        .expect_err("the authored profile requires exactly one rules unit");
    assert!(
        matches!(error, PackageError::ProfileSourceKinds { .. }),
        "the refusal must name the profile source kinds: {error:?}"
    );
}

#[test]
fn michigan_regional_profile_refuses_a_rules_unit() {
    let root = TempRoot::new();
    let manifest = authored_manifest("mods.wrong-profile").replace(
        "host_profile = \"authored-graph-v1\"",
        "host_profile = \"michigan-regional-v6\"",
    );
    root.write("package/manifest.toml", manifest.as_bytes());
    root.write("package/scenario.bscn", authored_scenario().as_bytes());
    root.write("package/rules.bsl", authored_rule().as_bytes());
    let package = root.load("package");
    let resolved = resolver::resolve_content_packages(&[package]).expect("the package resolves");
    let error = admission::validate_profile_sources(&resolved)
        .expect_err("the Michigan profile accepts one defines unit only");
    assert!(
        matches!(error, PackageError::ProfileSourceKinds { .. }),
        "the refusal must name the profile source kinds: {error:?}"
    );
}

#[test]
fn unit_unknown_fields_and_relative_paths_stay_strict() {
    let root = TempRoot::new();
    let manifest = MOD_MANIFEST.replace(
        "host_profile = \"michigan-regional-v6\"",
        "host_profile = \"michigan-regional-v6\"\nunknown = 1",
    );
    write_base(&root, "base", base_defines());
    root.write("mods/manifest.toml", manifest.as_bytes());
    root.write("mods/defines.toml", base_defines().as_bytes());
    let error = LoadedPackage::load(&root.path("mods"))
        .expect_err("an unknown manifest field must refuse at every level");
    assert!(
        matches!(error, PackageError::ManifestToml { .. }),
        "the refusal must name the manifest parse failure: {error:?}"
    );
    assert_eq!(SourceKind::Defines.as_str(), "defines");
    assert_eq!(
        HostProfile::MichiganRegionalV6.manifest_name(),
        "michigan-regional-v6"
    );
}

fn committed_package(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../../content/packages")
        .join(name)
}

fn copy_tree(source: &Path, destination: &Path) {
    fs::create_dir_all(destination).expect("the copied package directory is creatable");
    for entry in fs::read_dir(source).expect("the committed package directory is readable") {
        let entry = entry.expect("the committed package entry is readable");
        let target = destination.join(entry.file_name());
        if entry
            .file_type()
            .expect("the committed package entry type is readable")
            .is_dir()
        {
            copy_tree(&entry.path(), &target);
        } else {
            fs::copy(entry.path(), &target).expect("the committed package file is copyable");
        }
    }
}

fn authored_from_committed(root: &TempRoot, names: &[&str]) -> ResolvedContentSet {
    let packages = names
        .iter()
        .map(|name| {
            let directory = format!("packages/{name}");
            copy_tree(&committed_package(name), &root.path(&directory));
            root.load(&directory)
        })
        .collect::<Vec<_>>();
    resolver::resolve_content_packages(&packages).expect("the committed authored packages resolve")
}

fn viewer_scope(handle: &CampaignHandle) -> PlayerScope {
    let tails = handle
        .durable_tails()
        .expect("the authored campaign publishes its durable tails");
    PlayerScope::new(
        authored_graph::AUTHORED_GRAPH_VIEWER_PLAYER_ID,
        handle.current().period,
        tails.knowledge_seq(),
        tails.journal_seq(),
    )
}

fn viewer_nodes(
    handle: &CampaignHandle,
    scenario_scope: &str,
    expected_names: &[&str],
) -> Vec<AuthoredGraphNodeFact> {
    let scope = viewer_scope(handle);
    let summary = handle
        .query(scope, PlayerQuery::MapSummary)
        .expect("the authored viewer map summary reads");
    let PlayerBody::MapSummary(MapSummary { known_subjects }) = summary.body else {
        panic!("the map summary query must answer a map summary");
    };
    assert_eq!(
        known_subjects,
        vec![SubjectCount {
            kind: SubjectKind::Observation,
            count: u64::try_from(expected_names.len()).expect("the node count fits"),
        }],
        "the viewer discloses exactly its designed node facts"
    );
    expected_names
        .iter()
        .map(|name| {
            let subject_id = crate::sqlite_store::authored_graph_subject_id(scenario_scope, name)
                .expect("the authored subject identity encodes");
            let result = handle
                .query(
                    scope,
                    PlayerQuery::KnownSubject {
                        subject_kind: SubjectKind::Observation,
                        subject_id,
                    },
                )
                .expect("the authored viewer node fact is disclosed");
            let PlayerBody::Subject(fact) = result.body else {
                panic!("the known subject query must answer a subject fact");
            };
            let node = crate::sqlite_store::decode_authored_graph_node_fact(
                &fact.subject_id,
                &fact.payload,
            )
            .expect("the authored viewer payload decodes");
            assert_eq!(node.evidence, "Designed");
            node
        })
        .collect()
}

fn assert_authored_opening(root: &CurrentRoot, store: &Path) {
    assert_eq!(root.period, 0, "the admitted opening is period zero");
    let required = [
        ChunkSection::StableGraph,
        ChunkSection::WorldRegisters,
        ChunkSection::ResolverManifest,
        ChunkSection::PreparedEnvironment,
        ChunkSection::ReplaySessionIdentity,
        ChunkSection::RngSeed,
        ChunkSection::ContentDigest,
        ChunkSection::ReferenceDigest,
    ];
    let present = root
        .chunks
        .iter()
        .map(|chunk| chunk.section)
        .collect::<Vec<_>>();
    assert!(
        required.iter().all(|section| present.contains(section)),
        "the authored opening carries every foundation section: {present:?}"
    );
    assert!(
        present.contains(&ChunkSection::SemanticState),
        "the authored opening supplies the ninth semantic-state section"
    );
    let connection = Connection::open(store).expect("the campaign database opens for a readback");
    let bytes = crate::sqlite_store::read_section_bytes(
        &connection,
        &root.chunks,
        ChunkSection::SemanticState,
    )
    .expect("the semantic-state section reads back");
    assert!(
        !bytes.is_empty(),
        "the real Michigan geographic material state is captured"
    );
    assert_eq!(
        root.state_hash,
        content_digest::sha256_of(&bytes),
        "the opening state hash is the semantic-state identity"
    );
}

fn assert_rule_producer(report: &IdentifiedTickReport) {
    let receipts = &report.report().audit_receipts;
    assert!(
        receipts.iter().any(|receipt| {
            receipt.rule_id == "mods/local-probability-step"
                && receipt.role == RuleRole::Mechanic
                && receipt.evidence == EvidenceClass::Designed
                && receipt.effect
                    == EffectSignature::NodeField("social-class/probability".to_owned())
        }),
        "the authored rule must produce an audited node-field receipt: {receipts:?}"
    );
}

fn advance_viewer(
    handle: &mut CampaignHandle,
    scenario_scope: &str,
    expected_names: &[&str],
) -> (IdentifiedTickReport, Vec<AuthoredGraphNodeFact>) {
    let (report, committed) = authored_graph::advance_authored_graph_period(handle)
        .expect("the authored graph period advances and commits");
    assert_eq!(committed.period, handle.current().period);
    assert_eq!(
        committed.world_hash,
        *report.result_world().digest().as_bytes()
    );
    assert_eq!(
        committed.state_hash,
        content_digest::sha256_of(report.material_state_rows().canonical_bytes())
    );
    assert_rule_producer(&report);
    let nodes = viewer_nodes(handle, scenario_scope, expected_names);
    (report, nodes)
}

fn replay_one_authored_period(handle: &CampaignHandle) -> IdentifiedTickReport {
    let mut session = authored_graph::authored_graph_replay_session(handle)
        .expect("the captured authored content rebuilds a replay session");
    let actions = OrderedPracticeActionBatch::empty(session.session_identity().clone(), 1)
        .expect("the empty authored action batch constructs");
    let mut sink = CollectingSink::default();
    session
        .advance(&mut sink, &actions)
        .expect("the captured authored content replays one period")
}

#[test]
fn worked_examples_two_and_three_admit_view_and_replay_the_authored_graph() {
    let root = TempRoot::new();
    let baseline = authored_from_committed(&root, &["mods.local-probability-fixture"]);
    assert_eq!(baseline.host_profile(), HostProfile::AuthoredGraphV1);
    let store = root.path("baseline.sqlite3");
    let mut handle =
        authored_graph::admit_authored_graph_package(&baseline, 319, &store).expect("admits");
    assert_eq!(handle.build(), admission::content_package_build_identity());
    assert_authored_opening(handle.current(), &store);
    let (report, nodes) = advance_viewer(
        &mut handle,
        "mods/local-probability-fixture",
        &["first", "second"],
    );
    assert_eq!(nodes[0].node_type, "SOCIAL_CLASS");
    assert_eq!(nodes[0].probability_bits, 0.375_f64.to_bits());
    assert_eq!(nodes[1].probability_bits, 0.625_f64.to_bits());
    let baseline_graph = *report.result_stable_graph_digest().as_bytes();

    let stepped = authored_from_committed(
        &root,
        &[
            "mods.local-probability-step",
            "mods.local-probability-fixture",
        ],
    );
    assert_ne!(
        stepped.digest(),
        baseline.digest(),
        "the two increments are different content identities"
    );
    let stepped_store = root.path("stepped.sqlite3");
    let mut stepped_handle =
        authored_graph::admit_authored_graph_package(&stepped, 319, &stepped_store)
            .expect("the 0.25i variant admits");
    let (stepped_report, stepped_nodes) = advance_viewer(
        &mut stepped_handle,
        "mods/local-probability-fixture",
        &["first", "second"],
    );
    assert_eq!(stepped_nodes[0].probability_bits, 0.5_f64.to_bits());
    assert_eq!(stepped_nodes[1].probability_bits, 0.75_f64.to_bits());
    assert_ne!(
        *stepped_report.result_stable_graph_digest().as_bytes(),
        baseline_graph,
        "the two increments must produce different post-state"
    );
}

#[test]
fn three_node_variant_reaches_the_viewer_with_a_designed_fact() {
    let root = TempRoot::new();
    let resolved = authored_from_committed(&root, &["mods.local-probability-three-node"]);
    let store = root.path("three-node.sqlite3");
    let mut handle = authored_graph::admit_authored_graph_package(&resolved, 319, &store)
        .expect("the three-node variant admits");
    let (_, nodes) = advance_viewer(
        &mut handle,
        "mods/local-probability-three-node",
        &["first", "second", "third"],
    );
    assert_eq!(nodes[0].probability_bits, 0.5_f64.to_bits());
    assert_eq!(nodes[1].probability_bits, 0.75_f64.to_bits());
    assert_eq!(nodes[2].probability_bits, 0.375_f64.to_bits());
    assert_eq!(nodes[2].local_name, "third");
    for node in &nodes {
        assert_eq!(node.evidence, "Designed");
        assert_eq!(node.node_type, "SOCIAL_CLASS");
    }
}

struct AuthoredSaveVariant {
    name: &'static str,
    packages: &'static [&'static str],
    scenario_scope: &'static str,
    scenario_package: &'static str,
    store_name: &'static str,
    expected_nodes: &'static [(&'static str, f64)],
    second_period_nodes: &'static [(&'static str, f64)],
}

const SAVED_AUTHORED_VARIANTS: [AuthoredSaveVariant; 3] = [
    AuthoredSaveVariant {
        name: "baseline 0.125i",
        packages: &["mods.local-probability-fixture"],
        scenario_scope: "mods/local-probability-fixture",
        scenario_package: "mods.local-probability-fixture",
        store_name: "baseline-reopen.sqlite3",
        expected_nodes: &[("first", 0.375), ("second", 0.625)],
        second_period_nodes: &[("first", 0.5), ("second", 0.75)],
    },
    AuthoredSaveVariant {
        name: "step 0.25i",
        packages: &[
            "mods.local-probability-step",
            "mods.local-probability-fixture",
        ],
        scenario_scope: "mods/local-probability-fixture",
        scenario_package: "mods.local-probability-fixture",
        store_name: "step-reopen.sqlite3",
        expected_nodes: &[("first", 0.5), ("second", 0.75)],
        second_period_nodes: &[],
    },
    AuthoredSaveVariant {
        name: "three-node",
        packages: &["mods.local-probability-three-node"],
        scenario_scope: "mods/local-probability-three-node",
        scenario_package: "mods.local-probability-three-node",
        store_name: "three-node-reopen.sqlite3",
        expected_nodes: &[("first", 0.5), ("second", 0.75), ("third", 0.375)],
        second_period_nodes: &[],
    },
];

const REPLACED_SCENARIO: &[u8] = b"(scenario mods/replaced\n  (deffield social-class/probability probability intensive)\n  (node only NodeType/SOCIAL_CLASS (social-class/probability 0.5p)))\n";

const REPLACED_RULES: &[u8] = b"(rule mods/replaced-step\n  :role mechanic\n  :evidence designed\n  :material-basis \"a different installed rule\"\n  :fuel 64\n  (anchor :before survival)\n  (bindings (binding probability :field social-class/probability))\n  (effects (update-node self social-class/probability (set 0.5p))))\n";

fn replace_installed_sources(root: &TempRoot, packages: &[&str]) {
    for package in packages {
        for (file, bytes) in [
            ("scenario.bscn", REPLACED_SCENARIO),
            ("rules.bsl", REPLACED_RULES),
        ] {
            let relative = format!("packages/{package}/{file}");
            if root.path(&relative).exists() {
                root.write(&relative, bytes);
            }
        }
    }
}

fn assert_variant_nodes(expected: &[(&str, f64)], nodes: &[AuthoredGraphNodeFact], context: &str) {
    assert_eq!(
        nodes.len(),
        expected.len(),
        "{context}: the viewer discloses exactly the authored nodes"
    );
    for (node, (name, probability)) in nodes.iter().zip(expected) {
        assert_eq!(node.local_name, *name, "{context}: node identity");
        assert_eq!(node.node_type, "SOCIAL_CLASS", "{context}: node type");
        assert_eq!(node.evidence, "Designed", "{context}: evidence label");
        assert_eq!(
            node.probability_bits,
            probability.to_bits(),
            "{context}: {name} probability"
        );
    }
}

fn assert_saved_variant_keeps_its_captured_structure(variant: &AuthoredSaveVariant) {
    let root = TempRoot::new();
    let resolved = authored_from_committed(&root, variant.packages);
    let store = root.path(variant.store_name);
    let mut handle = authored_graph::admit_authored_graph_package(&resolved, 319, &store)
        .expect("the authored variant admits");
    assert_authored_opening(handle.current(), &store);
    let names = variant
        .expected_nodes
        .iter()
        .map(|(name, _)| *name)
        .collect::<Vec<_>>();
    let (report, nodes) = advance_viewer(&mut handle, variant.scenario_scope, &names);
    assert_variant_nodes(variant.expected_nodes, &nodes, variant.name);
    let history = handle
        .history(viewer_scope(&handle), None, 0)
        .expect("the authored campaign publishes its bounded public history");
    assert_eq!(
        history
            .entries
            .iter()
            .filter(|entry| entry.kind == JournalKind::PlayerReceipt)
            .count(),
        names.len(),
        "{}: each disclosed node keeps one public receipt",
        variant.name
    );
    let committed_root = handle.current().clone();
    let build = handle.build();
    drop(handle);

    replace_installed_sources(&root, variant.packages);

    let mut reopened =
        SqliteCampaignStore::open(&store, build).expect("the saved campaign reopens");
    assert_eq!(
        reopened.current(),
        &committed_root,
        "{}: reopen restores the committed root",
        variant.name
    );
    let semantic = reopened
        .read_section_bytes(ChunkSection::SemanticState)
        .expect("the saved semantic-state section reads back");
    assert_eq!(
        content_digest::sha256_of(&semantic),
        committed_root.state_hash,
        "{}: the saved restart root rehydrates the semantic-state identity",
        variant.name
    );
    assert_reopened_variant(variant, &mut reopened, &report, &history, &names);
}

fn assert_reopened_variant(
    variant: &AuthoredSaveVariant,
    reopened: &mut CampaignHandle,
    report: &IdentifiedTickReport,
    history: &HistoryPage,
    names: &[&str],
) {
    let scenario_source = format!("{}/scenario", variant.scenario_scope);
    let captured = reopened
        .read_content_entry(ContentEntryKind::CapturedSource, scenario_source.as_bytes())
        .expect("the captured scenario reads back");
    assert_eq!(
        captured,
        vec![
            fs::read(committed_package(variant.scenario_package).join("scenario.bscn"))
                .expect("the committed scenario is readable")
        ],
        "{}: reopening must use captured content, not the edited installed file",
        variant.name
    );
    let reopened_nodes = viewer_nodes(reopened, variant.scenario_scope, names);
    assert_variant_nodes(variant.expected_nodes, &reopened_nodes, variant.name);
    let replayed = replay_one_authored_period(reopened);
    assert_eq!(
        replayed.result_stable_graph_digest().as_bytes(),
        report.result_stable_graph_digest().as_bytes(),
        "{}: replay must reproduce the identical GraphStateHash",
        variant.name
    );
    assert_eq!(
        replayed.report().audit_receipts,
        report.report().audit_receipts,
        "{}: replay must reproduce the same audit producer identity",
        variant.name
    );
    let reopened_history = reopened
        .history(viewer_scope(reopened), None, 0)
        .expect("the reopened campaign publishes its bounded public history");
    assert_eq!(
        reopened_history.committed_period, history.committed_period,
        "{}: history reports the same committed period after reopen",
        variant.name
    );
    assert_eq!(
        reopened_history.entries, history.entries,
        "{}: public history must survive close, source replacement and reopen",
        variant.name
    );
    if !variant.second_period_nodes.is_empty() {
        let second_names = variant
            .second_period_nodes
            .iter()
            .map(|(name, _)| *name)
            .collect::<Vec<_>>();
        let (_, second) = authored_graph::advance_authored_graph_period(reopened)
            .expect("the reopened campaign advances another period");
        assert_eq!(
            second.period, 2,
            "{}: the second advance commits period two",
            variant.name
        );
        let second_nodes = viewer_nodes(reopened, variant.scenario_scope, &second_names);
        assert_variant_nodes(
            variant.second_period_nodes,
            &second_nodes,
            &format!("{} second period", variant.name),
        );
    }
}

#[test]
fn every_saved_variant_keeps_its_captured_structure_after_installed_sources_change() {
    for variant in &SAVED_AUTHORED_VARIANTS {
        assert_saved_variant_keeps_its_captured_structure(variant);
    }
}

#[test]
fn authored_negative_content_refuses_before_publication() {
    let zero_fuel = authored_rule().replace(":fuel 64", ":fuel 0");
    let error = resolve_authored(authored_scenario(), &zero_fuel)
        .expect_err("zero fuel must refuse at load");
    assert!(
        error.to_string().contains("fuel"),
        "the refusal must name fuel: {error}"
    );

    let unknown_field = authored_rule().replace(
        "social-class/probability (add 0.125i)",
        "social-class/undeclared (add 0.125i)",
    );
    let error = resolve_authored(authored_scenario(), &unknown_field)
        .expect_err("an undeclared field must refuse at load");
    assert!(
        matches!(error, PackageError::UnlistedStateActionPair { .. }),
        "the refusal must name the unlisted pair: {error:?}"
    );

    let invalid_probability = authored_rule().replace(
        "(when (<= probability 0.75p))",
        "(when (<= probability 1.5p))",
    );
    let error = resolve_authored(authored_scenario(), &invalid_probability)
        .expect_err("a probability above one must refuse at load");
    assert!(
        error.to_string().contains("literals")
            || error.to_string().contains("probability")
            || error.to_string().contains("1.5"),
        "the refusal must name the invalid probability: {error}"
    );

    let material_anchor =
        authored_rule().replace("(anchor :before survival)", "(anchor :after vitality)");
    let error = resolve_authored(authored_scenario(), &material_anchor)
        .expect_err("an anchor inside the material causal spine must refuse");
    assert!(
        error.to_string().contains("Material Base"),
        "the refusal must name the material spine: {error}"
    );

    for (field, value) in [
        ("territory/county-fips", "26163"),
        ("household/persons", "1"),
        ("household/households", "1"),
    ] {
        let scenario = authored_scenario().replace(
            "(deffield social-class/probability probability intensive)",
            &format!(
                "(deffield social-class/probability probability intensive)\n  (deffield {field} int extensive)"
            ),
        );
        let rules = authored_rule().replace(
            "social-class/probability (add 0.125i)",
            &format!("{field} (set {value})"),
        );
        let error = resolve_authored(&scenario, &rules)
            .expect_err("a governed field write must refuse at load");
        assert!(
            error.to_string().contains(field),
            "the refusal must name {field}: {error}"
        );
    }
}

#[test]
fn swap_admits_both_profiles_on_one_binary_with_divergent_behavior() {
    // The no-Rust-delta proof is the content-only comparison in
    // `worked_examples_two_and_three_admit_view_and_replay_the_authored_graph`:
    // the same binary admits both probability increments and only content
    // varies. An in-process digest of this source tree cannot observe a Rust
    // delta, because nothing writes `.rs` files between its two reads.
    let michigan_root = TempRoot::new();
    let michigan = resolved_hours(&michigan_root, 44);
    let authored_root = TempRoot::new();
    let authored = authored_from_committed(
        &authored_root,
        &[
            "mods.local-probability-step",
            "mods.local-probability-fixture",
        ],
    );
    assert_eq!(michigan.host_profile(), HostProfile::MichiganRegionalV6);
    assert_eq!(authored.host_profile(), HostProfile::AuthoredGraphV1);

    let refused = admission::admit_michigan_regional_package(
        &authored,
        &authored_root.path("wrong-michigan.sqlite3"),
    )
    .expect_err("the Michigan numeric profile refuses an authored graph set");
    assert!(
        refused.to_string().contains("authored-graph-v1"),
        "the numeric admission must name the selected profile: {refused}"
    );
    let refused = authored_graph::admit_authored_graph_package(
        &michigan,
        319,
        &authored_root.path("wrong-authored.sqlite3"),
    )
    .expect_err("the authored graph profile refuses a numeric set");
    assert!(
        refused.to_string().contains("michigan-regional-v6"),
        "the authored admission must name the selected profile: {refused}"
    );

    let michigan_store = michigan_root.path("michigan.sqlite3");
    let mut michigan_handle =
        admission::admit_michigan_regional_package(&michigan, &michigan_store)
            .expect("the numeric campaign admits");
    let authored_store = authored_root.path("authored.sqlite3");
    let mut authored_handle =
        authored_graph::admit_authored_graph_package(&authored, 319, &authored_store)
            .expect("the authored campaign admits");
    assert_eq!(
        michigan_handle.build(),
        authored_handle.build(),
        "both profiles were admitted by the same binary"
    );

    let command = PlayerCommand {
        period: 1,
        actor_id: [0x51; 8],
        payload: b"organizer-action".to_vec(),
    };
    let accepted = michigan_handle
        .accept_command(command.clone(), [0x7a; 16])
        .expect("the economic profile still validates and accepts player commands");
    assert_eq!(accepted.period, 1);
    let refused = authored_handle
        .accept_command(command, [0x7b; 16])
        .expect_err("the authored profile publishes no player commands");
    assert!(
        matches!(refused, CommandError::UnsupportedProfile),
        "the refusal must be the specific unsupported profile: {refused:?}"
    );

    let (_, authored_nodes) = advance_viewer(
        &mut authored_handle,
        "mods/local-probability-fixture",
        &["first", "second"],
    );
    assert_eq!(authored_nodes[0].probability_bits, 0.5_f64.to_bits());
    assert_eq!(authored_nodes[1].probability_bits, 0.75_f64.to_bits());
    assert_eq!(
        michigan_handle.current().chunks.len(),
        8,
        "the numeric opening keeps its eight economic restart sections"
    );
    assert!(
        authored_handle
            .current()
            .chunks
            .iter()
            .any(|chunk| chunk.section == ChunkSection::SemanticState),
        "the authored period carries the semantic-state section"
    );
}

#[test]
fn first_party_declarations_resolve_through_the_package_boundary() {
    let resolved = crate::economic_content::resolve_first_party_content()
        .expect("the embedded first-party declarations resolve");
    assert_eq!(resolved.host_profile(), HostProfile::AuthoredGraphV1);
    assert_eq!(resolved.units().len(), 3);
    assert_eq!(resolved.units_of(SourceKind::Scenario).count(), 1);
    assert_eq!(resolved.units_of(SourceKind::Rules).count(), 2);
    assert_eq!(
        resolved
            .unit(crate::economic_content::FIRST_PARTY_NATIONAL_SCENARIO_SOURCE_ID)
            .expect("the national scenario is effective")
            .bytes(),
        include_bytes!("../../../../../content/scenarios/national/structure.bscn")
    );
    assert_eq!(
        resolved
            .unit(crate::economic_content::FIRST_PARTY_MICHIGAN_MATERIAL_SOURCE_ID)
            .expect("the material rule is effective")
            .bytes(),
        include_bytes!("../../../../../content/scenarios/michigan/material-cycle.bsl")
    );
    assert_eq!(
        resolved
            .unit(crate::economic_content::FIRST_PARTY_MICHIGAN_ORGANIZER_SOURCE_ID)
            .expect("the organizer rules are effective")
            .bytes(),
        include_bytes!("../../../../../content/scenarios/michigan/organizer-cycle.bsl")
    );
    let again = crate::economic_content::resolve_first_party_content()
        .expect("the embedded first-party declarations resolve deterministically");
    assert_eq!(again.digest(), resolved.digest());
    let refused = admission::validate_profile_sources(&resolved)
        .expect_err("the first-party source categories are not a campaign admission");
    assert!(
        matches!(refused, PackageError::ProfileSourceKinds { .. }),
        "the refusal must preserve each host's categories: {refused:?}"
    );
}

#[test]
fn authored_admission_supplies_the_ninth_semantic_state_section() {
    let root = TempRoot::new();
    let resolved = authored_from_committed(&root, &["mods.local-probability-fixture"]);
    let store = root.path("sections.sqlite3");
    let handle = authored_graph::admit_authored_graph_package(&resolved, 319, &store)
        .expect("the authored campaign admits");
    let root = handle.current();
    let semantic = root
        .chunks
        .iter()
        .filter(|chunk| chunk.section == ChunkSection::SemanticState)
        .collect::<Vec<_>>();
    assert!(!semantic.is_empty(), "the semantic state is present");
    assert_eq!(
        semantic
            .iter()
            .map(|chunk| chunk.ordinal)
            .collect::<Vec<_>>(),
        (0..u32::try_from(semantic.len()).expect("the fragment count fits")).collect::<Vec<_>>(),
        "the semantic state starts at ordinal zero and stays dense"
    );
    let connection = Connection::open(&store).expect("the campaign database opens for a readback");
    let state = crate::sqlite_store::read_section_bytes(
        &connection,
        &root.chunks,
        ChunkSection::SemanticState,
    )
    .expect("the semantic-state section reads back");
    assert!(
        !state.is_empty(),
        "the real Michigan geographic material state is captured, not an empty placeholder"
    );
}
