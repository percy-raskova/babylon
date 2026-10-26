//! Contract tests for external content package resolution and admission.

use std::fs;
use std::path::PathBuf;
use std::time::SystemTime;
use std::time::UNIX_EPOCH;

use babylon_bsl::causal_contract::EffectSignature;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::content_digest;
use babylon_material_circuit::InputOutputCoefficient;
use babylon_material_circuit::UnitId;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_replay::MaterialReplaySession;
use babylon_tick::replay_session::ReplayCommitDisposition;

use crate::material_runtime::MaterialRuntimeFoundation;
use crate::michigan_content::MichiganContentPreset;
use crate::michigan_material::MichiganMaterialCatalog;
use crate::michigan_material::MichiganMaterialProcess;
use crate::sqlite_store::CampaignHandle;
use crate::sqlite_store::ContentEntryKind;
use crate::sqlite_store::SaveError;
use crate::sqlite_store::SqliteCampaignStore;

use super::admission;
use super::audit;
use super::audit::CoefficientAudit;
use super::audit::CoefficientBasis;
use super::audit::CoefficientNormalization;
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

    let store = root.path("campaign.sqlite3");
    let handle = admission::admit_michigan_regional_package(&resolved, &store)
        .expect("the 44-hour package admits");
    let build = handle.build();
    assert_eq!(build, admission::content_package_build_identity());
    let captured = handle
        .read_content_entry(ContentEntryKind::CapturedSource, b"michigan/defines")
        .expect("the captured defines read back");
    assert_eq!(captured.len(), 1);
    assert_eq!(captured[0], forty_four.as_bytes());
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

    run_one_material_close(foundation);

    let modified_on_disk = defines_with_hours(32);
    root.write(
        "mods/local.michigan-hours/defines.toml",
        modified_on_disk.as_bytes(),
    );
    let reopened = SqliteCampaignStore::open(&store, build).expect("the saved campaign reopens");
    let replay = reopened
        .read_content_entry(ContentEntryKind::CapturedSource, b"michigan/defines")
        .expect("the reopened campaign reads its captured defines");
    assert_eq!(
        replay[0],
        forty_four.as_bytes(),
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
    run_one_material_close(replayed_foundation);
}

fn run_one_material_close(foundation: MaterialRuntimeFoundation) {
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
fn effect_signature_is_closed_and_every_variant_is_content_reachable() {
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

    let mut observed = Vec::new();
    for audit in [&mechanical, &organizer, &fixture] {
        for rule in audit.rules() {
            for effect in rule.effects() {
                observed.push(effect_variant(effect));
            }
        }
    }
    // `Shape` verbs are expressible and statically inspected but deferred at
    // load, so the closed enum is covered by footprint rather than execution.
    for effect in shape_fixture_footprint() {
        observed.push(effect_variant(&effect));
    }

    for variant in EffectVariant::ALL {
        assert!(
            observed.contains(&variant),
            "no admitted content reaches the closed EffectSignature variant {variant:?}; observed {observed:?}"
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
    const ALL: [Self; 8] = [
        Self::MaterialCycle,
        Self::OrganizerProducts,
        Self::OrganizerPractice,
        Self::NodeField,
        Self::EdgeField,
        Self::HyperedgeField,
        Self::Event,
        Self::Shape,
    ];
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
