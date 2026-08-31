//! Ignored live tests for the PER-20 legacy adopter against disposable `PostgreSQL`.

use babylon_persistence::{
    adopt_legacy_schema, compiled_schema_migrations, legacy_adopter_sql_statements,
    parse_legacy_census_fixture, validate_legacy_connection_target, validate_legacy_stamps,
    LegacyAdopterError, LegacyAdopterOperation, LegacyAdopterSqlKind, LegacyBoundedResource,
    LegacyConnectionTargetRejection, LegacyObjectKey, LegacyObjectKind,
    LegacyOwnerAuthorityDisposition, LegacyStampClass, LegacyStampDefinition,
    LEGACY_ADOPTER_CONNECT_TIMEOUT, LEGACY_ADOPTER_STARTUP_OPTIONS,
    LEGACY_ADOPTER_TCP_USER_TIMEOUT, LEGACY_CENSUS_FIXTURE, LEGACY_STAMP_CATALOG,
    MAX_LEGACY_CENSUS_FIXTURE_BYTES, MAX_LEGACY_CENSUS_ROWS,
    MAX_LEGACY_EXTENSION_DEPENDENCY_ADDRESSES, MAX_LEGACY_EXTENSION_MEMBERS,
    MAX_LEGACY_EXTENSION_ROLE_IDENTITIES, MAX_LEGACY_PARTITIONS_PER_FAMILY,
    MAX_LEGACY_SEQUENCE_OWNERSHIP, MAX_LEGACY_STAMP_ROWS, SCHEMA_ADVISORY_LOCK_KEY,
};
use postgres::config::Host;
use postgres::error::SqlState;
use postgres::{Client, Config, IsolationLevel, NoTls};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;
use std::fs::OpenOptions;
use std::io::Write as IoWrite;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::str::FromStr;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

#[path = "support/h3_cell_vectors.rs"]
mod h3_cell_vectors;
#[path = "support/h3_pg_oracle.rs"]
mod h3_pg_oracle;
#[path = "support/h3_reference_installer_postgres.rs"]
mod h3_reference_installer_postgres;
#[path = "support/h3_shadow_backfill_postgres.rs"]
mod h3_shadow_backfill_postgres;
#[path = "support/schema_epoch_postgres.rs"]
mod schema_epoch_postgres;

const DSN_ENV: &str = "BABYLON_LEGACY_ADOPTER_TEST_DSN";
const DISPOSABLE_ACK_ENV: &str = "BABYLON_LEGACY_ADOPTER_DISPOSABLE_ACK";
const DISPOSABLE_ACK_VALUE: &str =
    "I_UNDERSTAND_PER20_DROPS_SCRATCH_DATABASES_ROLES_AND_CREATED_BABYLON_INTEL";
const DISPOSABLE_CANARY_ENV: &str = "BABYLON_LEGACY_ADOPTER_DISPOSABLE_CANARY";
const CURRENT_CENSUS_V2_FOCUS: &str = "runtime_census_v2";
const CURRENT_CENSUS_V2_EXPORT_DIR_ENV: &str = "BABYLON_CURRENT_CENSUS_V2_EXPORT_DIR";
const LIVE_FOCUS_ENV: &str = "BABYLON_LEGACY_ADOPTER_LIVE_FOCUS";
const VALID_DISPOSABLE_CANARY: &str = "0123456789abcdef0123456789abcdef";
const OWNER_PASSWORD: &str = "per20-owner-password";
const SESSION_UUID: &str = "01234567-89ab-cdef-0123-456789abcdef";
const SECOND_UUID: &str = "fedcba98-7654-3210-fedc-ba9876543210";
const LIVE_TASK_SECONDS: &str = "45s";
const LEGACY_CENSUS_V1_ARCHIVE: &str = include_str!("../src/fixtures/legacy_adopter_census_v1.txt");
const FRESH_CENSUS_V1_ARCHIVE: &str =
    include_str!("../src/fixtures/fresh_schema_epoch_census_v1.txt");
const FRESH_CENSUS_WITH_INTEL_V1_ARCHIVE: &str =
    include_str!("../src/fixtures/fresh_schema_epoch_census_with_intel_v1.txt");
const CURRENT_POSTGRES_IMAGE: &str = "postgis/postgis:17-3.5-alpine@sha256:\
08f4b1e1f4a571008c60272ceb9e0d1f9f8f643792d006b74a35b1bec44c2218";
const CURRENT_CENSUS_SQL_BYTES: &[u8] = include_bytes!("../src/legacy_adopter_census.sql");
const MAX_CURRENT_CENSUS_V2_DRIFT_ROWS: usize = MAX_LEGACY_CENSUS_ROWS * 2;
const MAX_CURRENT_CENSUS_V2_INLINE_PAYLOAD_BYTES: usize = 65_536;
const MAX_CURRENT_CENSUS_V2_PAYLOAD_ROW_BYTES: usize = 1_048_576;
const MAX_CURRENT_CENSUS_V2_REPORT_BYTES: usize = 8_388_608;
const CURRENT_CENSUS_V2_LEGACY_FILE: &str = "legacy_adopter_census_v2.txt";
const CURRENT_CENSUS_V2_FRESH_FILE: &str = "fresh_schema_epoch_census_v2.txt";
const CURRENT_CENSUS_V2_FRESH_WITH_INTEL_FILE: &str = "fresh_schema_epoch_census_with_intel_v2.txt";
const CURRENT_CENSUS_V2_REPORT_FILE: &str = "current_census_v2_drift_report.txt";
const DIGEST_PROJECTION: &str = "pg_catalog.encode(\n            \
pg_catalog.sha256(pg_catalog.convert_to(objects.payload::pg_catalog.text, 'UTF8')),\n            \
'hex'\n        ) AS digest_hex";
const OUTPUT_TAIL: &str = "FROM catalog_output AS output\n\
ORDER BY output.kind, output.schema_name, output.object_name\nLIMIT $1";

struct LivePhaseReceipts {
    suite_start: Instant,
}

impl LivePhaseReceipts {
    fn start() -> Self {
        Self {
            suite_start: Instant::now(),
        }
    }

    fn run<T>(&self, name: &'static str, operation: impl FnOnce() -> T) -> T {
        let phase_start = Instant::now();
        self.emit(name, "started", Duration::ZERO);
        let output = operation();
        self.emit(name, "complete", phase_start.elapsed());
        output
    }

    fn emit(&self, name: &'static str, completion: &'static str, phase_elapsed: Duration) {
        eprintln!(
            "PER20_PHASE name={name} completion={completion} phase_ms={} cumulative_ms={}",
            phase_elapsed.as_millis(),
            self.suite_start.elapsed().as_millis()
        );
        let mut stderr = std::io::stderr();
        std::io::Write::flush(&mut stderr).expect("live phase receipt must flush");
    }
}

macro_rules! live_phase {
    ($receipts:expr, $name:literal, $operation:expr) => {
        $receipts.run($name, || $operation)
    };
}

#[test]
fn disposable_harness_accepts_only_the_owned_loopback_shape() {
    let config =
        Config::from_str("host=127.0.0.1 port=55433 user=test password=test dbname=postgres")
            .unwrap();
    assert_eq!(
        validate_disposable_harness_target(&config, Some(VALID_DISPOSABLE_CANARY)),
        Ok(())
    );
}

#[test]
fn disposable_harness_rejects_nonowned_targets_before_connect() {
    let cases = [
        "host=localhost port=55433 user=test dbname=postgres",
        "host=192.0.2.1 port=55433 user=test dbname=postgres",
        "host=/tmp port=55433 user=test dbname=postgres",
        "host=127.0.0.1,127.0.0.1 port=55433 user=test dbname=postgres",
        "host=127.0.0.1 port=55433,55434 user=test dbname=postgres",
        "host=127.0.0.1 hostaddr=127.0.0.1 port=55433 user=test dbname=postgres",
        "host=127.0.0.1 port=55433 user=other dbname=postgres",
        "host=127.0.0.1 port=55433 user=test dbname=babylon_test",
        "host=127.0.0.1 user=test dbname=postgres",
    ];
    for dsn in cases.iter().take(9) {
        let config = Config::from_str(dsn).unwrap();
        assert!(
            validate_disposable_harness_target(&config, Some(VALID_DISPOSABLE_CANARY)).is_err()
        );
    }
}

#[test]
fn disposable_harness_rejects_missing_or_invalid_canary() {
    let config =
        Config::from_str("host=127.0.0.1 port=55433 user=test password=test dbname=postgres")
            .unwrap();
    for canary in [
        None,
        Some(""),
        Some("0123456789abcdef0123456789abcde"),
        Some("0123456789abcdef0123456789abcdef0"),
        Some("0123456789abcdef0123456789abcdeG"),
    ]
    .iter()
    .take(5)
    {
        assert_eq!(
            validate_disposable_harness_target(&config, *canary),
            Err(DisposableHarnessRejection::Canary)
        );
    }
}

#[test]
#[ignore = "requires disposable baseline DSN in BABYLON_LEGACY_ADOPTER_TEST_DSN"]
fn live_adopter_contract_against_independent_builds_and_disposable_mutations() {
    let phases = LivePhaseReceipts::start();
    let base = live_phase!(phases, "config_from_env", config_from_env());
    live_phase!(phases, "preflight", preflight_disposable_harness(&base));
    let babylon_intel = live_phase!(
        phases,
        "capture_babylon_intel",
        BabylonIntelRolePresenceGuard::capture(&base)
    );
    live_phase!(phases, "initial_residue", assert_no_scratch_residue(&base));
    let owner = live_phase!(phases, "create_owner_role", ScratchRole::create(&base));
    let first = live_phase!(
        phases,
        "create_first_database",
        ScratchDatabase::empty(&base, "independent_a", database_user(&base))
    );
    let second = live_phase!(
        phases,
        "create_second_database",
        ScratchDatabase::empty(&base, "independent_b", owner.name())
    );
    let first_config = first.config(&base);
    let second_config = second.config_as(&base, owner.name(), OWNER_PASSWORD);
    let template = first.name().to_owned();

    let run_mutations = run_first_live_phases(
        &phases,
        &base,
        &template,
        &first_config,
        &second_config,
        owner.name(),
    );
    if run_mutations {
        run_second_live_phases(&phases, &base, &template, &first_config);
        live_phase!(
            phases,
            "schema_epoch_matrix",
            schema_epoch_postgres::verify_schema_epoch_matrix(&base, &template, owner.name())
        );
        live_phase!(
            phases,
            "h3_pg_oracle",
            verify_h3_pg_oracle_in_scratch(&base, owner.name())
        );
        live_phase!(
            phases,
            "h3_reference_installer",
            h3_reference_installer_postgres::verify_h3_reference_installer(
                &base,
                &template,
                owner.name(),
            )
        );
    }
    live_phase!(phases, "cleanup_first_database", first.cleanup());
    live_phase!(phases, "cleanup_second_database", second.cleanup());
    live_phase!(phases, "cleanup_owner_role", owner.cleanup());
    live_phase!(phases, "cleanup_babylon_intel", babylon_intel.cleanup());
    live_phase!(phases, "final_residue", assert_no_scratch_residue(&base));
}

fn run_first_live_phases(
    phases: &LivePhaseReceipts,
    base: &Config,
    template: &str,
    first_config: &Config,
    second_config: &Config,
    owner: &str,
) -> bool {
    if std::env::var_os(LIVE_FOCUS_ENV).as_deref()
        == Some(std::ffi::OsStr::new(CURRENT_CENSUS_V2_FOCUS))
    {
        live_phase!(
            phases,
            "runtime_census_v2",
            export_current_census_v2(base, first_config, second_config, owner)
        );
        return false;
    }
    if std::env::var_os(LIVE_FOCUS_ENV).as_deref()
        == Some(std::ffi::OsStr::new("schema_epoch_v5_census"))
    {
        export_fresh_v5_epoch_census(base);
        return false;
    }
    if std::env::var_os(LIVE_FOCUS_ENV).as_deref()
        == Some(std::ffi::OsStr::new("schema_epoch_v6_census"))
    {
        export_v6_epoch_censuses(base, template);
        return false;
    }
    if std::env::var_os(LIVE_FOCUS_ENV).as_deref()
        == Some(std::ffi::OsStr::new("schema_epoch_fresh"))
    {
        schema_epoch_postgres::verify_fresh_migration(base);
        return false;
    }
    live_phase!(phases, "repair_first", run_python_repair(first_config));
    live_phase!(
        phases,
        "repair_second",
        verify_partial_damage_then_separate_repair(second_config)
    );
    live_phase!(
        phases,
        "canonical_fixture_bytes",
        verify_canonical_fixture_bytes(first_config, second_config)
    );
    if run_focused_live_phase(phases, base, template, first_config, owner) {
        return false;
    }
    live_phase!(
        phases,
        "pinned_runtime",
        verify_pinned_postgres_runtime(first_config)
    );
    live_phase!(
        phases,
        "raw_non_catalog_bounds",
        verify_raw_non_catalog_bounds(first_config)
    );
    live_phase!(
        phases,
        "independent_builds",
        verify_independent_builds(first_config, second_config)
    );
    live_phase!(
        phases,
        "hostile_caller",
        verify_hostile_caller_and_connection_redaction(first_config)
    );
    live_phase!(phases, "advisory_lock", verify_lock_outcome(first_config));
    live_phase!(
        phases,
        "blocking_table_lock",
        verify_blocking_table_lock_timeout(base, template)
    );
    live_phase!(
        phases,
        "no_mutation_quoted_extras",
        verify_no_mutation_and_quoted_extras(base, template)
    );
    live_phase!(
        phases,
        "stamp_refusals",
        verify_stamp_refusals(base, template)
    );
    live_phase!(
        phases,
        "authority_epoch",
        verify_authority_epoch_refusal(base, template)
    );
    live_phase!(
        phases,
        "structural_role",
        verify_structural_and_role_refusals(base, template)
    );
    live_phase!(
        phases,
        "effective_authority",
        verify_effective_authority_refusals(base, template)
    );
    true
}

fn run_focused_live_phase(
    phases: &LivePhaseReceipts,
    base: &Config,
    template: &str,
    first_config: &Config,
    owner: &str,
) -> bool {
    let Some(focus) = std::env::var_os(LIVE_FOCUS_ENV) else {
        return false;
    };
    match focus.to_str() {
        Some("extension_dependency_role") => {
            verify_extension_superuser_owner_portability(base, template);
        }
        Some("extension_window_routine") => {
            verify_extension_window_routine_body_refusal(base, template);
        }
        Some("extension_dependency_bound") => {
            verify_raw_non_catalog_bounds(first_config);
            verify_unknown_extension_classification(base, template);
        }
        Some("schema_epoch_fresh") => schema_epoch_postgres::verify_fresh_migration(base),
        Some("schema_epoch_matrix") => {
            schema_epoch_postgres::verify_schema_epoch_matrix(base, template, owner);
        }
        Some("h3_pg_oracle") => verify_h3_pg_oracle_in_scratch(base, owner),
        Some("h3_reference_installer") => {
            h3_reference_installer_postgres::verify_h3_reference_installer(base, template, owner);
        }
        Some("h3_shadow_backfill") => {
            h3_shadow_backfill_postgres::verify_h3_shadow_backfill(base, template);
        }
        Some("installed_mutation") => verify_h3_installed_mutations(phases, base),
        Some("h3_reference_release") => {
            h3_reference_installer_postgres::verify_h3_reference_release_equivalence(base);
        }
        _ => panic!("unknown bounded live focus"),
    }
    true
}

fn export_fresh_v5_epoch_census(base: &Config) {
    const EXPORT_LIMITS: [i64; 6] = [513, 4097, 8193, 16385, 2, 8193];
    let database = ScratchDatabase::empty(base, "epoch_v5_census", database_user(base));
    let config = database.config(base);
    let compiled = compiled_schema_migrations().unwrap();
    let mut client = config.connect(NoTls).unwrap();
    let mut transaction = client.transaction().unwrap();
    for migration in compiled.iter().take(5) {
        transaction.batch_execute(migration.sql()).unwrap();
        let version = migration.version().as_i64();
        let checksum = migration.checksum();
        let checksum_bytes = checksum.as_bytes().as_slice();
        transaction
            .execute(
                "INSERT INTO babylon_state.schema_migration (version, checksum) VALUES ($1, $2)",
                &[&version, &checksum_bytes],
            )
            .unwrap();
    }
    transaction.commit().unwrap();

    let census_sql = legacy_adopter_sql_statements()
        .iter()
        .find(|statement| statement.kind() == LegacyAdopterSqlKind::CatalogCensus)
        .unwrap()
        .sql();
    let rows = client
        .query(
            census_sql,
            &[
                &EXPORT_LIMITS[0],
                &EXPORT_LIMITS[1],
                &EXPORT_LIMITS[2],
                &EXPORT_LIMITS[3],
                &EXPORT_LIMITS[4],
                &EXPORT_LIMITS[5],
            ],
        )
        .unwrap();
    let mut fixture = String::new();
    for row in rows.iter().take(513) {
        let kind: String = row.try_get(0).unwrap();
        let schema: String = row.try_get(1).unwrap();
        let name: String = row.try_get(2).unwrap();
        let digest: String = row.try_get(3).unwrap();
        let epoch_relation =
            kind == "relation" && matches!(schema.as_str(), "babylon_ref" | "babylon_state");
        let epoch_schema = kind == "schema"
            && schema == "pg_namespace"
            && matches!(name.as_str(), "babylon_ref" | "babylon_state");
        let fresh_meta =
            kind == "schema_grant" && schema == "pg_namespace" && name == "babylon_meta";
        if epoch_relation || epoch_schema || fresh_meta {
            writeln!(fixture, "{kind}|{schema}|{name}|{digest}").unwrap();
        }
    }
    eprintln!("PER278_V5_CENSUS_START\n{fixture}PER278_V5_CENSUS_END");
    drop(client);
    database.cleanup();
}

fn export_v6_epoch_censuses(base: &Config, legacy_template: &str) {
    let fresh = ScratchDatabase::empty(base, "epoch_v6_fresh_census", database_user(base));
    let fresh_config = fresh.config(base);
    let fresh_fixture = raw_v6_epoch_census(&fresh_config, false);
    eprintln!("PER279_V6_FRESH_CENSUS_START\n{fresh_fixture}PER279_V6_FRESH_CENSUS_END");
    fresh.cleanup();

    let legacy = ScratchDatabase::from_template(base, legacy_template, "epoch_v6_legacy_census");
    let legacy_config = legacy.config(base);
    run_python_repair(&legacy_config);
    adopt_legacy_schema(&legacy_config).expect("repaired legacy template must adopt exactly");
    let legacy_fixture = raw_v6_epoch_census(&legacy_config, true);
    eprintln!("PER279_V6_LEGACY_CENSUS_START\n{legacy_fixture}PER279_V6_LEGACY_CENSUS_END");
    legacy.cleanup();
}

fn raw_v6_epoch_census(config: &Config, legacy_origin: bool) -> String {
    const EXPORT_LIMITS: [i64; 6] = [513, 4097, 8193, 16385, 2, 8193];
    let compiled = compiled_schema_migrations().unwrap();
    let mut bounded = config.clone();
    bounded
        .connect_timeout(LEGACY_ADOPTER_CONNECT_TIMEOUT)
        .tcp_user_timeout(LEGACY_ADOPTER_TCP_USER_TIMEOUT)
        .options(LEGACY_ADOPTER_STARTUP_OPTIONS);
    let mut client = bounded.connect(NoTls).unwrap();
    for migration in compiled.iter().take(5) {
        let mut transaction = client
            .build_transaction()
            .isolation_level(IsolationLevel::Serializable)
            .read_only(false)
            .start()
            .unwrap();
        transaction
            .batch_execute(
                "SET LOCAL search_path TO pg_catalog; SET LOCAL synchronous_commit TO on",
            )
            .unwrap();
        transaction.batch_execute(migration.sql()).unwrap();
        let version = migration.version().as_i64();
        let checksum = migration.checksum();
        let checksum_bytes = checksum.as_bytes().as_slice();
        transaction
            .execute(
                "INSERT INTO babylon_state.schema_migration (version, checksum) VALUES ($1, $2)",
                &[&version, &checksum_bytes],
            )
            .unwrap();
        transaction.commit().unwrap();
    }

    let migration = &compiled[5];
    let mut transaction = client
        .build_transaction()
        .isolation_level(IsolationLevel::Serializable)
        .read_only(false)
        .start()
        .unwrap();
    transaction
        .batch_execute("SET LOCAL search_path TO pg_catalog; SET LOCAL synchronous_commit TO on")
        .unwrap();
    transaction.batch_execute(migration.sql()).unwrap();

    let census_sql = legacy_adopter_sql_statements()
        .iter()
        .find(|statement| statement.kind() == LegacyAdopterSqlKind::CatalogCensus)
        .unwrap()
        .sql();
    let rows = transaction
        .query(
            census_sql,
            &[
                &EXPORT_LIMITS[0],
                &EXPORT_LIMITS[1],
                &EXPORT_LIMITS[2],
                &EXPORT_LIMITS[3],
                &EXPORT_LIMITS[4],
                &EXPORT_LIMITS[5],
            ],
        )
        .unwrap();
    let mut fixture = String::new();
    for row in rows.iter().take(513) {
        let kind: String = row.try_get(0).unwrap();
        let schema: String = row.try_get(1).unwrap();
        let name: String = row.try_get(2).unwrap();
        let digest: String = row.try_get(3).unwrap();
        if is_v6_epoch_census_entry(&kind, &schema, &name, legacy_origin) {
            writeln!(fixture, "{kind}|{schema}|{name}|{digest}").unwrap();
        }
    }
    transaction.rollback().unwrap();
    fixture
}

fn is_v6_epoch_census_entry(kind: &str, schema: &str, name: &str, legacy_origin: bool) -> bool {
    let owned_relation = kind == "relation" && matches!(schema, "babylon_ref" | "babylon_state");
    let owned_schema = kind == "schema"
        && schema == "pg_namespace"
        && matches!(name, "babylon_ref" | "babylon_state");
    let fresh_meta = !legacy_origin
        && kind == "schema_grant"
        && schema == "pg_namespace"
        && name == "babylon_meta";
    let legacy_shadow = legacy_origin
        && matches!(kind, "relation" | "partitioned_table")
        && schema == "public"
        && matches!(
            name,
            "dynamic_hex_state"
                | "hex_activity"
                | "hex_cell"
                | "hex_latest"
                | "hex_map"
                | "hex_r8_linear_features_reference"
                | "hex_r8_reference"
                | "hex_spatial_map"
                | "hex_state"
                | "hex_substrate"
                | "hex_terrain_state"
                | "immutable_reference_lodes_od_matrix"
                | "infrastructure_link_state"
                | "org_snapshot"
                | "tick_event"
        );
    owned_relation || owned_schema || fresh_meta || legacy_shadow
}

fn verify_h3_installed_mutations(phases: &LivePhaseReceipts, base: &Config) {
    phases.run("h3_installed_mutations", || {
        h3_reference_installer_postgres::verify_h3_reference_installed_mutations(base);
    });
}

fn verify_h3_pg_oracle_in_scratch(base: &Config, owner: &str) {
    let database = ScratchDatabase::empty(base, "h3_pg_oracle", owner);
    let owner_config = database.config_as(base, owner, OWNER_PASSWORD);
    let admin_config = database.config(base);
    h3_pg_oracle::verify_h3_pg_oracle(&owner_config, &admin_config);
    database.cleanup();
}

fn run_second_live_phases(
    phases: &LivePhaseReceipts,
    base: &Config,
    template: &str,
    first_config: &Config,
) {
    live_phase!(
        phases,
        "write_semantics",
        verify_write_semantic_refusals(base, template)
    );
    live_phase!(
        phases,
        "inheritance_subpartition",
        verify_inheritance_and_subpartition_refusals(base, template)
    );
    live_phase!(
        phases,
        "partition_children",
        verify_partition_children(base, template)
    );
    live_phase!(
        phases,
        "extra_surfaces",
        verify_extra_schema_routine_and_type_refusal(base, template)
    );
    live_phase!(
        phases,
        "strict_census",
        verify_strict_census_refusals(base, template)
    );
    live_phase!(
        phases,
        "cast_system_namespace",
        verify_cast_and_system_namespace_refusals(base, template)
    );
    live_phase!(
        phases,
        "reserved_roles",
        verify_reserved_role_name_refusals(base, template)
    );
    live_phase!(
        phases,
        "extension_identity",
        verify_extension_identity_refusals(base, template)
    );
    live_phase!(
        phases,
        "column_bound",
        verify_census_column_bound(base, template)
    );
    live_phase!(
        phases,
        "unsupported_catalog_bounds",
        verify_unsupported_catalog_bounds(base, template)
    );
    live_phase!(
        phases,
        "sequence_owned_by",
        verify_sequence_owned_by_refusals(base, template)
    );
    live_phase!(
        phases,
        "sequence_acl_default",
        verify_sequence_acl_default_semantics(first_config)
    );
    live_phase!(
        phases,
        "canonical_after_cleanup",
        verify_canonical_state_after_global_cleanup(first_config)
    );
}

#[derive(Clone, Copy)]
enum CurrentCensusV2Variant {
    LegacyAdopter,
    FreshSchemaEpoch,
    FreshSchemaEpochWithIntel,
}

impl CurrentCensusV2Variant {
    fn title(self) -> &'static str {
        match self {
            Self::LegacyAdopter => "legacy adopter",
            Self::FreshSchemaEpoch => "fresh schema epoch",
            Self::FreshSchemaEpochWithIntel => "fresh schema epoch with babylon_intel",
        }
    }

    fn records_legacy_stamps(self) -> bool {
        matches!(self, Self::LegacyAdopter)
    }

    fn records_optional_intel(self) -> bool {
        matches!(self, Self::FreshSchemaEpochWithIntel)
    }
}

type CurrentCensusKey = (String, String, String);

#[derive(Debug, Clone, PartialEq, Eq)]
struct CurrentCensusV2RuntimeProvenance {
    postgres_server_version_num: String,
    locale_provider: String,
    locale: String,
    encoding: String,
    postgis_version: String,
    pgvector_version: String,
    h3_version: String,
    optional_intel: bool,
}

#[derive(Debug, PartialEq, Eq)]
struct CurrentCensusDrift {
    change: &'static str,
    key: CurrentCensusKey,
    old_digest: Option<String>,
    new_digest: Option<String>,
}

fn export_current_census_v2(
    base: &Config,
    first_config: &Config,
    second_config: &Config,
    owner: &str,
) {
    let admin = admin_config(base);
    assert!(
        !try_cluster_role_exists(&admin, "babylon_intel").unwrap(),
        "current-census-v2 export requires an initially absent babylon_intel role"
    );

    let fresh_without_intel_first = hardened_census_snapshot(first_config);
    let fresh_without_intel_second = hardened_census_snapshot(second_config);
    assert_eq!(fresh_without_intel_first, fresh_without_intel_second);
    let fresh_provenance_first = current_census_v2_runtime_provenance(first_config);
    let fresh_provenance_second = current_census_v2_runtime_provenance(second_config);
    assert_eq!(fresh_provenance_first, fresh_provenance_second);
    assert_current_census_v2_runtime(&fresh_provenance_first, false);
    let fresh_fixture = current_census_v2_fixture_bytes(
        CurrentCensusV2Variant::FreshSchemaEpoch,
        &fresh_without_intel_first,
        &fresh_provenance_first,
    );
    let fresh_drift = current_census_drift(FRESH_CENSUS_V1_ARCHIVE, &fresh_without_intel_first);
    let fresh_payloads =
        census_payloads_for_drift(first_config, &current_census_payload_keys(&fresh_drift));

    run_python_repair(first_config);
    run_python_repair(second_config);
    let legacy_first = hardened_authority_snapshot(first_config);
    let legacy_second = hardened_authority_snapshot(second_config);
    assert_eq!(legacy_first, legacy_second);
    let legacy_stamps_first = validated_current_stamp_definitions(&legacy_first);
    let legacy_stamps_second = validated_current_stamp_definitions(&legacy_second);
    assert_eq!(legacy_stamps_first, legacy_stamps_second);
    let legacy_provenance_first = current_census_v2_runtime_provenance(first_config);
    let legacy_provenance_second = current_census_v2_runtime_provenance(second_config);
    assert_eq!(legacy_provenance_first, legacy_provenance_second);
    assert_current_census_v2_runtime(&legacy_provenance_first, true);
    assert!(try_cluster_role_exists(&admin, "babylon_intel").unwrap());

    let intel_first =
        ScratchDatabase::empty(base, "current_census_v2_intel_a", database_user(base));
    let intel_second = ScratchDatabase::empty(base, "current_census_v2_intel_b", owner);
    let intel_first_config = intel_first.config(base);
    let intel_second_config = intel_second.config_as(base, owner, OWNER_PASSWORD);
    let fresh_with_intel_first = hardened_census_snapshot(&intel_first_config);
    let fresh_with_intel_second = hardened_census_snapshot(&intel_second_config);
    assert_eq!(fresh_with_intel_first, fresh_with_intel_second);
    let intel_provenance_first = current_census_v2_runtime_provenance(&intel_first_config);
    let intel_provenance_second = current_census_v2_runtime_provenance(&intel_second_config);
    assert_eq!(intel_provenance_first, intel_provenance_second);
    assert_current_census_v2_runtime(&intel_provenance_first, true);

    let legacy_fixture = current_census_v2_fixture_bytes(
        CurrentCensusV2Variant::LegacyAdopter,
        &legacy_first,
        &legacy_provenance_first,
    );
    let fresh_with_intel_fixture = current_census_v2_fixture_bytes(
        CurrentCensusV2Variant::FreshSchemaEpochWithIntel,
        &fresh_with_intel_first,
        &intel_provenance_first,
    );

    let legacy_drift = current_census_drift(LEGACY_CENSUS_V1_ARCHIVE, &legacy_first);
    let fresh_with_intel_drift =
        current_census_drift(FRESH_CENSUS_WITH_INTEL_V1_ARCHIVE, &fresh_with_intel_first);
    let legacy_payloads =
        census_payloads_for_drift(first_config, &current_census_payload_keys(&legacy_drift));
    let fresh_with_intel_payloads = census_payloads_for_drift(
        &intel_first_config,
        &current_census_payload_keys(&fresh_with_intel_drift),
    );
    let drift_report = current_census_v2_drift_report(&[
        ("legacy_adopter", legacy_drift.as_slice(), &legacy_payloads),
        (
            "fresh_schema_epoch",
            fresh_drift.as_slice(),
            &fresh_payloads,
        ),
        (
            "fresh_schema_epoch_with_intel",
            fresh_with_intel_drift.as_slice(),
            &fresh_with_intel_payloads,
        ),
    ]);

    intel_first.cleanup();
    intel_second.cleanup();

    write_current_census_v2_artifacts(
        &legacy_fixture,
        &fresh_fixture,
        &fresh_with_intel_fixture,
        &drift_report,
    );
}

fn write_current_census_v2_artifacts(
    legacy_fixture: &[u8],
    fresh_fixture: &[u8],
    fresh_with_intel_fixture: &[u8],
    drift_report: &[u8],
) {
    let output_dir = current_census_v2_export_dir();
    for (name, contents, max_bytes) in [
        (
            CURRENT_CENSUS_V2_LEGACY_FILE,
            legacy_fixture,
            MAX_LEGACY_CENSUS_FIXTURE_BYTES,
        ),
        (
            CURRENT_CENSUS_V2_FRESH_FILE,
            fresh_fixture,
            MAX_LEGACY_CENSUS_FIXTURE_BYTES,
        ),
        (
            CURRENT_CENSUS_V2_FRESH_WITH_INTEL_FILE,
            fresh_with_intel_fixture,
            MAX_LEGACY_CENSUS_FIXTURE_BYTES,
        ),
        (
            CURRENT_CENSUS_V2_REPORT_FILE,
            drift_report,
            MAX_CURRENT_CENSUS_V2_REPORT_BYTES,
        ),
    ] {
        write_current_census_v2_artifact(&output_dir, name, contents, max_bytes);
    }
}

fn hardened_census_snapshot(config: &Config) -> AuthoritySnapshot {
    let mut bounded = config.clone();
    bounded
        .connect_timeout(LEGACY_ADOPTER_CONNECT_TIMEOUT)
        .tcp_user_timeout(LEGACY_ADOPTER_TCP_USER_TIMEOUT)
        .options(LEGACY_ADOPTER_STARTUP_OPTIONS);
    let mut client = bounded.connect(NoTls).unwrap();
    AuthoritySnapshot {
        census: census_snapshot(&mut client),
        stamps: Vec::new(),
        authority_schemas: Vec::new(),
    }
}

fn hardened_authority_snapshot(config: &Config) -> AuthoritySnapshot {
    let mut bounded = config.clone();
    bounded
        .connect_timeout(LEGACY_ADOPTER_CONNECT_TIMEOUT)
        .tcp_user_timeout(LEGACY_ADOPTER_TCP_USER_TIMEOUT)
        .options(LEGACY_ADOPTER_STARTUP_OPTIONS);
    let mut client = bounded.connect(NoTls).unwrap();
    authority_snapshot(&mut client)
}

fn current_census_v2_runtime_provenance(config: &Config) -> CurrentCensusV2RuntimeProvenance {
    let mut bounded = config.clone();
    bounded
        .connect_timeout(LEGACY_ADOPTER_CONNECT_TIMEOUT)
        .tcp_user_timeout(LEGACY_ADOPTER_TCP_USER_TIMEOUT)
        .options(LEGACY_ADOPTER_STARTUP_OPTIONS);
    let mut client = bounded.connect(NoTls).unwrap();
    let row = client
        .query_one(
            "SELECT pg_catalog.current_setting('server_version_num'), \
                    CASE database_row.datlocprovider \
                      WHEN 'b' THEN 'builtin' \
                      WHEN 'c' THEN 'libc' \
                      WHEN 'i' THEN 'icu' \
                      ELSE database_row.datlocprovider::pg_catalog.text \
                    END, \
                    pg_catalog.coalesce(\
                        pg_catalog.nullif(database_row.datlocale, ''), \
                        database_row.datcollate\
                    ), \
                    pg_catalog.pg_encoding_to_char(database_row.encoding), \
                    (SELECT extension_row.extversion::pg_catalog.text \
                     FROM pg_catalog.pg_extension AS extension_row \
                     WHERE extension_row.extname = 'postgis'), \
                    (SELECT extension_row.extversion::pg_catalog.text \
                     FROM pg_catalog.pg_extension AS extension_row \
                     WHERE extension_row.extname = 'vector'), \
                    (SELECT available.default_version::pg_catalog.text \
                     FROM pg_catalog.pg_available_extensions AS available \
                     WHERE available.name = 'h3'), \
                    EXISTS (\
                        SELECT 1 \
                        FROM pg_catalog.pg_roles AS role_row \
                        WHERE role_row.rolname = 'babylon_intel'\
                    ) \
             FROM pg_catalog.pg_database AS database_row \
             WHERE database_row.datname = pg_catalog.current_database()",
            &[],
        )
        .unwrap();
    CurrentCensusV2RuntimeProvenance {
        postgres_server_version_num: row.try_get(0).unwrap(),
        locale_provider: row.try_get(1).unwrap(),
        locale: row.try_get(2).unwrap(),
        encoding: row.try_get(3).unwrap(),
        postgis_version: row.try_get(4).unwrap(),
        pgvector_version: row.try_get(5).unwrap(),
        h3_version: row.try_get(6).unwrap(),
        optional_intel: row.try_get(7).unwrap(),
    }
}

fn assert_current_census_v2_runtime(
    actual: &CurrentCensusV2RuntimeProvenance,
    optional_intel: bool,
) {
    assert_eq!(
        actual,
        &CurrentCensusV2RuntimeProvenance {
            postgres_server_version_num: "170011".to_owned(),
            locale_provider: "builtin".to_owned(),
            locale: "C.UTF-8".to_owned(),
            encoding: "UTF8".to_owned(),
            postgis_version: "3.5.7".to_owned(),
            pgvector_version: "0.8.5".to_owned(),
            h3_version: "4.5.0".to_owned(),
            optional_intel,
        }
    );
}

fn validated_current_stamp_definitions(snapshot: &AuthoritySnapshot) -> Vec<LegacyStampDefinition> {
    assert_eq!(
        snapshot.authority_schemas,
        ["babylon_ref".to_owned(), "babylon_state".to_owned()]
    );
    assert_eq!(snapshot.stamps.len(), 2);
    let mut digests = Vec::with_capacity(2);
    for (digest, digest_bytes) in snapshot.stamps.iter().take(MAX_LEGACY_STAMP_ROWS) {
        assert_eq!(*digest_bytes, 64);
        assert_eq!(digest.len(), 64);
        digests.push(digest.clone());
    }
    let report = validate_legacy_stamps(&digests).expect("observed current stamps must classify");
    let observed = report
        .matches()
        .iter()
        .take(MAX_LEGACY_STAMP_ROWS)
        .map(|stamp_match| stamp_match.definition)
        .collect::<Vec<_>>();
    let expected = LEGACY_STAMP_CATALOG
        .iter()
        .copied()
        .filter(|definition| definition.class == LegacyStampClass::RequiredCurrent)
        .take(2)
        .collect::<Vec<_>>();
    assert_eq!(observed, expected);
    observed
}

fn current_census_sql_sha256() -> String {
    sha256_hex(CURRENT_CENSUS_SQL_BYTES)
}

fn current_census_startup_options() -> String {
    let settings = LEGACY_ADOPTER_STARTUP_OPTIONS
        .strip_prefix("-c ")
        .unwrap()
        .split(" -c ")
        .take(9)
        .collect::<Vec<_>>();
    assert_eq!(settings.len(), 8);
    settings.join("|")
}

fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    let mut hex = String::with_capacity(64);
    for byte in digest.iter().take(32) {
        write!(&mut hex, "{byte:02x}").unwrap();
    }
    hex
}

fn current_census_v2_fixture_bytes(
    variant: CurrentCensusV2Variant,
    snapshot: &AuthoritySnapshot,
    provenance: &CurrentCensusV2RuntimeProvenance,
) -> Vec<u8> {
    let mut output = String::with_capacity(MAX_LEGACY_CENSUS_FIXTURE_BYTES);
    writeln!(
        output,
        "# Babylon PER-272 current {} census fixture v2",
        variant.title()
    )
    .unwrap();
    writeln!(output, "# provenance|source|legacy_adopter_census.sql").unwrap();
    writeln!(
        output,
        "# provenance|census_sql_sha256|{}",
        current_census_sql_sha256()
    )
    .unwrap();
    writeln!(
        output,
        "# provenance|postgres_image|{CURRENT_POSTGRES_IMAGE}"
    )
    .unwrap();
    writeln!(
        output,
        "# provenance|postgres_server_version_num|{}",
        provenance.postgres_server_version_num
    )
    .unwrap();
    writeln!(
        output,
        "# provenance|locale_provider|{}",
        provenance.locale_provider
    )
    .unwrap();
    writeln!(output, "# provenance|locale|{}", provenance.locale).unwrap();
    writeln!(output, "# provenance|encoding|{}", provenance.encoding).unwrap();
    writeln!(
        output,
        "# provenance|postgis_version|{}",
        provenance.postgis_version
    )
    .unwrap();
    writeln!(
        output,
        "# provenance|pgvector_version|{}",
        provenance.pgvector_version
    )
    .unwrap();
    writeln!(output, "# provenance|h3_version|{}", provenance.h3_version).unwrap();
    writeln!(
        output,
        "# provenance|artifact_contract|digest-pinned-base|checksum-pinned-sources|\
exact-final-runtime-packages|behaviorally-verified|not-byte-reproducible"
    )
    .unwrap();
    writeln!(
        output,
        "# provenance|startup_options|{}",
        current_census_startup_options()
    )
    .unwrap();
    assert_eq!(
        provenance.optional_intel,
        variant.records_optional_intel() || variant.records_legacy_stamps()
    );
    if provenance.optional_intel {
        writeln!(output, "# provenance|optional_cluster_role|babylon_intel").unwrap();
    }
    if variant.records_legacy_stamps() {
        let stamp_definitions = validated_current_stamp_definitions(snapshot);
        writeln!(
            output,
            "# provenance|authority_schemas|{}",
            snapshot.authority_schemas.join(",")
        )
        .unwrap();
        for definition in stamp_definitions.iter().take(MAX_LEGACY_STAMP_ROWS) {
            writeln!(
                output,
                "# provenance|{}|chunks={}|digest={}",
                definition.name, definition.chunk_count, definition.digest_hex
            )
            .unwrap();
        }
    } else {
        assert!(snapshot.stamps.is_empty());
        assert!(snapshot.authority_schemas.is_empty());
    }
    writeln!(output, "# format|kind|schema|name|sha256").unwrap();
    for ((kind, schema, name, digest), overflow) in
        snapshot.census.iter().take(MAX_LEGACY_CENSUS_ROWS)
    {
        assert_eq!(overflow, &(None, None, None));
        writeln!(output, "{kind}|{schema}|{name}|{digest}").unwrap();
    }
    assert!(output.len() <= MAX_LEGACY_CENSUS_FIXTURE_BYTES);
    let fixture_text = output.as_str();
    parse_legacy_census_fixture(fixture_text)
        .expect("current-census-v2 candidate must satisfy the bounded fixture parser");
    output.into_bytes()
}

fn current_census_drift(
    archived_fixture: &str,
    current: &AuthoritySnapshot,
) -> Vec<CurrentCensusDrift> {
    let archived = census_fixture_digest_map(archived_fixture);
    let current = authority_digest_map(current);
    let keys = archived
        .keys()
        .chain(current.keys())
        .take(MAX_CURRENT_CENSUS_V2_DRIFT_ROWS + 1)
        .cloned()
        .collect::<BTreeSet<_>>();
    assert!(keys.len() <= MAX_CURRENT_CENSUS_V2_DRIFT_ROWS);
    let mut drift = Vec::new();
    for key in keys.iter().take(MAX_CURRENT_CENSUS_V2_DRIFT_ROWS) {
        let old_digest = archived.get(key).cloned();
        let new_digest = current.get(key).cloned();
        let change = match (&old_digest, &new_digest) {
            (Some(old), Some(new)) if old != new => "changed",
            (Some(_), None) => "missing",
            (None, Some(_)) => "extra",
            _ => continue,
        };
        drift.push(CurrentCensusDrift {
            change,
            key: key.clone(),
            old_digest,
            new_digest,
        });
    }
    assert!(drift.len() <= MAX_CURRENT_CENSUS_V2_DRIFT_ROWS);
    drift
}

fn census_fixture_digest_map(fixture: &str) -> BTreeMap<CurrentCensusKey, String> {
    parse_legacy_census_fixture(fixture).expect("archived census fixture must remain parseable");
    let mut rows = BTreeMap::new();
    for line in fixture
        .lines()
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .take(MAX_LEGACY_CENSUS_ROWS)
    {
        let mut fields = line.split('|');
        let key = (
            fields.next().unwrap().to_owned(),
            fields.next().unwrap().to_owned(),
            fields.next().unwrap().to_owned(),
        );
        let digest = fields.next().unwrap().to_owned();
        assert!(fields.next().is_none());
        assert!(rows.insert(key, digest).is_none());
    }
    rows
}

fn authority_digest_map(snapshot: &AuthoritySnapshot) -> BTreeMap<CurrentCensusKey, String> {
    let mut rows = BTreeMap::new();
    for ((kind, schema, name, digest), overflow) in
        snapshot.census.iter().take(MAX_LEGACY_CENSUS_ROWS)
    {
        assert_eq!(overflow, &(None, None, None));
        assert!(rows
            .insert((kind.clone(), schema.clone(), name.clone()), digest.clone(),)
            .is_none());
    }
    rows
}

fn current_census_payload_keys(drift: &[CurrentCensusDrift]) -> Vec<CurrentCensusKey> {
    drift
        .iter()
        .take(MAX_CURRENT_CENSUS_V2_DRIFT_ROWS)
        .filter(|item| item.new_digest.is_some())
        .map(|item| item.key.clone())
        .collect()
}

fn current_census_payload_projection() -> String {
    format!(
        "CASE\n\
            WHEN pg_catalog.octet_length(objects.payload::pg_catalog.text) <= \
{MAX_CURRENT_CENSUS_V2_INLINE_PAYLOAD_BYTES}\n\
            THEN pg_catalog.jsonb_build_object(\n\
                'mode', 'inline',\n\
                'payload_bytes', pg_catalog.octet_length(objects.payload::pg_catalog.text),\n\
                'payload_sha256', pg_catalog.encode(\n\
                    pg_catalog.sha256(pg_catalog.convert_to(\n\
                        objects.payload::pg_catalog.text, 'UTF8'\n\
                    )),\n\
                    'hex'\n\
                ),\n\
                'payload', objects.payload\n\
            )\n\
            ELSE pg_catalog.jsonb_build_object(\n\
                'mode', 'structural',\n\
                'payload_bytes', pg_catalog.octet_length(objects.payload::pg_catalog.text),\n\
                'payload_sha256', pg_catalog.encode(\n\
                    pg_catalog.sha256(pg_catalog.convert_to(\n\
                        objects.payload::pg_catalog.text, 'UTF8'\n\
                    )),\n\
                    'hex'\n\
                ),\n\
                'scalars', coalesce((\n\
                    SELECT pg_catalog.jsonb_object_agg(field.key, field.value ORDER BY field.key)\n\
                    FROM pg_catalog.jsonb_each(objects.payload) AS field(key, value)\n\
                    WHERE pg_catalog.jsonb_typeof(field.value) NOT IN ('array', 'object')\n\
                      AND pg_catalog.octet_length(field.value::pg_catalog.text) <= 4096\n\
                ), '{{}}'::pg_catalog.jsonb),\n\
                'oversize_scalars', coalesce((\n\
                    SELECT pg_catalog.jsonb_object_agg(\n\
                        field.key,\n\
                        pg_catalog.jsonb_build_object(\n\
                            'type', pg_catalog.jsonb_typeof(field.value),\n\
                            'bytes', pg_catalog.octet_length(field.value::pg_catalog.text),\n\
                            'sha256', pg_catalog.encode(\n\
                                pg_catalog.sha256(pg_catalog.convert_to(\n\
                                    field.value::pg_catalog.text, 'UTF8'\n\
                                )),\n\
                                'hex'\n\
                            )\n\
                        )\n\
                        ORDER BY field.key\n\
                    )\n\
                    FROM pg_catalog.jsonb_each(objects.payload) AS field(key, value)\n\
                    WHERE pg_catalog.jsonb_typeof(field.value) NOT IN ('array', 'object')\n\
                      AND pg_catalog.octet_length(field.value::pg_catalog.text) > 4096\n\
                ), '{{}}'::pg_catalog.jsonb),\n\
                'collections', coalesce((\n\
                    SELECT pg_catalog.jsonb_object_agg(\n\
                        field.key,\n\
                        pg_catalog.jsonb_build_object(\n\
                            'type', pg_catalog.jsonb_typeof(field.value),\n\
                            'count', CASE pg_catalog.jsonb_typeof(field.value)\n\
                                WHEN 'array' THEN pg_catalog.jsonb_array_length(field.value)\n\
                                ELSE (\n\
                                    SELECT pg_catalog.count(*)\n\
                                    FROM pg_catalog.jsonb_object_keys(field.value)\n\
                                )\n\
                            END,\n\
                            'bytes', pg_catalog.octet_length(field.value::pg_catalog.text),\n\
                            'sha256', pg_catalog.encode(\n\
                                pg_catalog.sha256(pg_catalog.convert_to(\n\
                                    field.value::pg_catalog.text, 'UTF8'\n\
                                )),\n\
                                'hex'\n\
                            )\n\
                        )\n\
                        ORDER BY field.key\n\
                    )\n\
                    FROM pg_catalog.jsonb_each(objects.payload) AS field(key, value)\n\
                    WHERE pg_catalog.jsonb_typeof(field.value) IN ('array', 'object')\n\
                ), '{{}}'::pg_catalog.jsonb)\n\
            )\n\
        END::pg_catalog.text AS digest_hex"
    )
}

fn census_payloads_for_drift(
    config: &Config,
    keys: &[CurrentCensusKey],
) -> BTreeMap<CurrentCensusKey, String> {
    const FILTERED_OUTPUT_TAIL: &str = "FROM catalog_output AS output\n\
JOIN ROWS FROM (\n    pg_catalog.unnest($7::pg_catalog.text[]),\n    \
pg_catalog.unnest($8::pg_catalog.text[]),\n    \
pg_catalog.unnest($9::pg_catalog.text[])\n) AS wanted(kind, schema_name, object_name)\n  ON wanted.kind = \
output.kind\n AND wanted.schema_name = output.schema_name\n AND wanted.object_name = \
output.object_name\nORDER BY output.kind, output.schema_name, output.object_name\nLIMIT $1";

    if keys.is_empty() {
        return BTreeMap::new();
    }
    assert!(keys.len() <= MAX_CURRENT_CENSUS_V2_DRIFT_ROWS);
    let census_sql = adopter_sql(LegacyAdopterSqlKind::CatalogCensus);
    assert_eq!(census_sql.matches(DIGEST_PROJECTION).count(), 1);
    assert_eq!(census_sql.matches(OUTPUT_TAIL).count(), 1);
    let payload_projection = current_census_payload_projection();
    let payload_sql = census_sql
        .replacen(DIGEST_PROJECTION, payload_projection.as_str(), 1)
        .replacen(OUTPUT_TAIL, FILTERED_OUTPUT_TAIL, 1);
    let kinds = keys.iter().map(|key| key.0.clone()).collect::<Vec<_>>();
    let schemas = keys.iter().map(|key| key.1.clone()).collect::<Vec<_>>();
    let names = keys.iter().map(|key| key.2.clone()).collect::<Vec<_>>();
    let census_limit = i64::try_from(MAX_LEGACY_CENSUS_ROWS + 1).unwrap();
    let partition_limit = i64::try_from(MAX_LEGACY_PARTITIONS_PER_FAMILY + 1).unwrap();
    let extension_member_limit = i64::try_from(MAX_LEGACY_EXTENSION_MEMBERS + 1).unwrap();
    let extension_dependency_address_limit =
        i64::try_from(MAX_LEGACY_EXTENSION_DEPENDENCY_ADDRESSES + 1).unwrap();
    let sequence_ownership_limit = i64::try_from(MAX_LEGACY_SEQUENCE_OWNERSHIP + 1).unwrap();
    let extension_role_identity_limit =
        i64::try_from(MAX_LEGACY_EXTENSION_ROLE_IDENTITIES + 1).unwrap();
    let mut bounded = config.clone();
    bounded
        .connect_timeout(LEGACY_ADOPTER_CONNECT_TIMEOUT)
        .tcp_user_timeout(LEGACY_ADOPTER_TCP_USER_TIMEOUT)
        .options(LEGACY_ADOPTER_STARTUP_OPTIONS);
    let mut client = bounded.connect(NoTls).unwrap();
    let rows = client
        .query(
            payload_sql.as_str(),
            &[
                &census_limit,
                &partition_limit,
                &extension_member_limit,
                &extension_dependency_address_limit,
                &sequence_ownership_limit,
                &extension_role_identity_limit,
                &kinds,
                &schemas,
                &names,
            ],
        )
        .unwrap();
    assert_eq!(rows.len(), keys.len());
    let mut payloads = BTreeMap::new();
    let mut total_bytes = 0_usize;
    for row in rows.iter().take(MAX_CURRENT_CENSUS_V2_DRIFT_ROWS) {
        let key = (
            row.try_get::<_, String>(0).unwrap(),
            row.try_get::<_, String>(1).unwrap(),
            row.try_get::<_, String>(2).unwrap(),
        );
        let payload = row.try_get::<_, String>(3).unwrap();
        assert_eq!(row.try_get::<_, Option<String>>(4).unwrap(), None);
        assert_eq!(row.try_get::<_, Option<i64>>(5).unwrap(), None);
        assert_eq!(row.try_get::<_, Option<i64>>(6).unwrap(), None);
        assert!(payload.len() <= MAX_CURRENT_CENSUS_V2_PAYLOAD_ROW_BYTES);
        total_bytes = total_bytes.checked_add(payload.len()).unwrap();
        assert!(total_bytes <= MAX_CURRENT_CENSUS_V2_REPORT_BYTES);
        assert!(payloads.insert(key, payload).is_none());
    }
    payloads
}

fn current_census_v2_drift_report(
    sections: &[(
        &str,
        &[CurrentCensusDrift],
        &BTreeMap<CurrentCensusKey, String>,
    )],
) -> Vec<u8> {
    let mut report = String::with_capacity(MAX_LEGACY_CENSUS_FIXTURE_BYTES);
    writeln!(report, "# Babylon PER-272 current census v2 drift review").unwrap();
    writeln!(report, "# status|blocked_pending_exact_payload_comparison").unwrap();
    writeln!(
        report,
        "# contract|v1 fixtures remain immutable archives; candidates are not accepted by this export"
    )
    .unwrap();
    for (variant, drift, payloads) in sections.iter().take(3) {
        writeln!(report, "variant|{variant}|drift_rows={}", drift.len()).unwrap();
        for item in drift.iter().take(MAX_CURRENT_CENSUS_V2_DRIFT_ROWS) {
            let (kind, schema, name) = &item.key;
            writeln!(
                report,
                "drift|{}|{kind}|{schema}|{name}|old={}|new={}",
                item.change,
                item.old_digest.as_deref().unwrap_or("absent"),
                item.new_digest.as_deref().unwrap_or("absent")
            )
            .unwrap();
            writeln!(
                report,
                "review|blocked_pending_exact_payload_comparison|{kind}|{schema}|{name}|{}",
                current_census_drift_context(&item.key)
            )
            .unwrap();
            if let Some(payload) = payloads.get(&item.key) {
                writeln!(
                    report,
                    "current_payload_diagnostic|{kind}|{schema}|{name}|bytes={}|{payload}",
                    payload.len()
                )
                .unwrap();
            }
        }
    }
    assert!(report.len() <= MAX_CURRENT_CENSUS_V2_REPORT_BYTES);
    report.into_bytes()
}

fn current_census_drift_context(key: &CurrentCensusKey) -> &'static str {
    match (key.0.as_str(), key.1.as_str(), key.2.as_str()) {
        ("database", "pg_database", "current_database") => {
            "candidate cause is the PG17.11 Alpine builtin C.UTF-8 runtime envelope; compare exact old/new JSON fields"
        }
        ("extension", "pg_extension", "plpgsql") => {
            "candidate cause is the PostgreSQL-bundled extension catalog moving with PG17.11; compare exact old/new JSON fields"
        }
        ("extension", "pg_extension", "postgis") => {
            "candidate cause is the PostGIS 3.5.2 to 3.5.7 runtime change; compare exact old/new JSON fields"
        }
        ("extension", "pg_extension", "vector") => {
            "logical version remains 0.8.5 but packaging moved to a checksum-pinned source build on Alpine; compare exact old/new JSON fields"
        }
        ("partitioned_table", "public", "conservation_audit_log") => {
            "DDL and census SQL are unchanged; no cause is accepted until an old/new canonical JSON field diff identifies the drift"
        }
        _ => "unexpected drift has no accepted explanation; compare exact old/new JSON fields",
    }
}

fn current_census_v2_export_dir() -> PathBuf {
    let output_dir = PathBuf::from(
        std::env::var_os(CURRENT_CENSUS_V2_EXPORT_DIR_ENV)
            .expect("runtime_census_v2 requires BABYLON_CURRENT_CENSUS_V2_EXPORT_DIR"),
    );
    assert!(output_dir.is_absolute());
    let metadata = std::fs::symlink_metadata(&output_dir).unwrap();
    assert!(metadata.file_type().is_dir());
    assert!(std::fs::read_dir(&output_dir).unwrap().next().is_none());
    output_dir
}

fn write_current_census_v2_artifact(
    output_dir: &Path,
    name: &str,
    contents: &[u8],
    max_bytes: usize,
) {
    assert!(contents.len() <= max_bytes);
    let path = output_dir.join(name);
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .unwrap();
    IoWrite::write_all(&mut file, contents).unwrap();
    file.sync_all().unwrap();
}

fn verify_pinned_postgres_runtime(config: &Config) {
    let mut client = config.connect(NoTls).unwrap();
    let row = client
        .query_one(
            "SELECT pg_catalog.current_setting('server_version_num'), \
                    vector.extversion::text, postgis.extversion::text \
             FROM pg_catalog.pg_extension AS vector \
             CROSS JOIN pg_catalog.pg_extension AS postgis \
             WHERE vector.extname = 'vector' AND postgis.extname = 'postgis'",
            &[],
        )
        .unwrap();
    assert_eq!(row.try_get::<_, String>(0).unwrap(), "170011");
    assert_eq!(row.try_get::<_, String>(1).unwrap(), "0.8.5");
    assert_eq!(row.try_get::<_, String>(2).unwrap(), "3.5.7");
}

fn verify_raw_non_catalog_bounds(config: &Config) {
    let normal = [
        i64::try_from(MAX_LEGACY_CENSUS_ROWS + 1).unwrap(),
        i64::try_from(MAX_LEGACY_PARTITIONS_PER_FAMILY + 1).unwrap(),
        i64::try_from(MAX_LEGACY_EXTENSION_MEMBERS + 1).unwrap(),
        i64::try_from(MAX_LEGACY_EXTENSION_DEPENDENCY_ADDRESSES + 1).unwrap(),
        i64::try_from(MAX_LEGACY_SEQUENCE_OWNERSHIP + 1).unwrap(),
        i64::try_from(MAX_LEGACY_EXTENSION_ROLE_IDENTITIES + 1).unwrap(),
    ];
    let cases = [
        (
            "sequence_ownership",
            [normal[0], normal[1], normal[2], normal[3], 1, normal[5]],
        ),
        (
            "extension_members",
            [normal[0], normal[1], 1, normal[3], normal[4], normal[5]],
        ),
        (
            "extension_dependency_addresses",
            [normal[0], normal[1], normal[2], 1, normal[4], normal[5]],
        ),
        (
            "partition_rows",
            [normal[0], 1, normal[2], normal[3], normal[4], normal[5]],
        ),
        (
            "extension_role_identities",
            [normal[0], normal[1], normal[2], normal[3], normal[4], 1],
        ),
    ];
    let mut client = config.connect(NoTls).unwrap();
    for (expected_resource, limits) in cases.iter().take(5) {
        let rows = client
            .query(
                adopter_sql(LegacyAdopterSqlKind::CatalogCensus),
                &[
                    &limits[0], &limits[1], &limits[2], &limits[3], &limits[4], &limits[5],
                ],
            )
            .unwrap();
        assert_eq!(rows.len(), 1);
        let row = &rows[0];
        let objects = (
            row.try_get::<_, Option<String>>(0).unwrap(),
            row.try_get::<_, Option<String>>(1).unwrap(),
            row.try_get::<_, Option<String>>(2).unwrap(),
            row.try_get::<_, Option<String>>(3).unwrap(),
        );
        assert_eq!(objects, (None, None, None, None));
        assert_eq!(row.try_get::<_, String>(4).unwrap(), *expected_resource);
        assert_eq!(row.try_get::<_, i64>(5).unwrap(), 1);
        assert_eq!(row.try_get::<_, i64>(6).unwrap(), 0);
    }
}

fn verify_canonical_state_after_global_cleanup(config: &Config) {
    let report =
        adopt_legacy_schema(config).expect("global cleanup must restore canonical adoption");
    assert_eq!(report.expected_objects, 102);
    assert_eq!(report.matched_objects, 102);
    assert!(report.extra_objects.is_empty());
    assert!(report.transaction_verified);
    assert_eq!(
        report.owner_authority,
        LegacyOwnerAuthorityDisposition::DeferredToRustMigratorPreflight
    );
    assert_lock_released(config);
}

fn verify_independent_builds(first: &Config, second: &Config) {
    let first_report = adopt_legacy_schema(first).expect("first independent build must adopt");
    let second_report = adopt_legacy_schema(second).expect("second independent build must adopt");
    assert_eq!(first_report, second_report);
    assert_eq!(first_report.expected_objects, 102);
    assert_eq!(first_report.matched_objects, 102);
    assert!(first_report.extra_objects.is_empty());
    assert!(first_report.transaction_verified);
    assert_eq!(
        first_report.owner_authority,
        LegacyOwnerAuthorityDisposition::DeferredToRustMigratorPreflight
    );
    assert_eq!(
        first_report
            .stamps
            .matched_count(LegacyStampClass::RequiredCurrent),
        2
    );
    for config in [first, second] {
        assert_lock_released(config);
    }
}

fn verify_canonical_fixture_bytes(first: &Config, second: &Config) {
    let mut first_config = first.clone();
    first_config.options(LEGACY_ADOPTER_STARTUP_OPTIONS);
    let mut second_config = second.clone();
    second_config.options(LEGACY_ADOPTER_STARTUP_OPTIONS);
    let mut first_client = first_config.connect(NoTls).unwrap();
    let mut second_client = second_config.connect(NoTls).unwrap();
    let first_fixture = canonical_fixture_bytes(&authority_snapshot(&mut first_client));
    let second_fixture = canonical_fixture_bytes(&authority_snapshot(&mut second_client));
    assert_eq!(first_fixture, second_fixture);
}

fn canonical_fixture_bytes(snapshot: &AuthoritySnapshot) -> Vec<u8> {
    const FORMAT_LINE: &str = "# format|kind|schema|name|sha256\n";
    let header_start = LEGACY_CENSUS_FIXTURE.find(FORMAT_LINE).unwrap();
    let header_end = header_start.checked_add(FORMAT_LINE.len()).unwrap();
    let mut output = String::with_capacity(MAX_LEGACY_CENSUS_FIXTURE_BYTES);
    output.push_str(&LEGACY_CENSUS_FIXTURE[..header_end]);
    for ((kind, schema, name, digest), overflow) in
        snapshot.census.iter().take(MAX_LEGACY_CENSUS_ROWS)
    {
        assert_eq!(overflow, &(None, None, None));
        writeln!(output, "{kind}|{schema}|{name}|{digest}").unwrap();
    }
    assert!(output.len() <= MAX_LEGACY_CENSUS_FIXTURE_BYTES);
    output.into_bytes()
}

fn verify_hostile_caller_and_connection_redaction(config: &Config) {
    let mut hostile = config.clone();
    hostile.options(
        "-c search_path=public -c default_transaction_read_only=off \
         -c quote_all_identifiers=on -c jit=on -c event_triggers=on \
         -c statement_timeout=0 -c lock_timeout=0 \
         -c idle_in_transaction_session_timeout=0",
    );
    assert_eq!(
        adopt_legacy_schema(&hostile),
        Err(LegacyAdopterError::UnsupportedConnectionTarget {
            reason: LegacyConnectionTargetRejection::StartupOptionsOverride,
        })
    );
    assert_lock_released(config);

    let mut client = config.connect(NoTls).unwrap();
    let value: i32 = client
        .query_one("SELECT 1", &[])
        .unwrap()
        .try_get(0)
        .unwrap();
    assert_eq!(value, 1);

    let mut unreachable = Config::new();
    unreachable
        .host("127.0.0.1")
        .port(1)
        .user("user")
        .password("do-not-leak-password")
        .dbname("missing");
    let error = adopt_legacy_schema(&unreachable).unwrap_err();
    assert_eq!(error, LegacyAdopterError::Connection);
    assert!(!format!("{error}").contains("do-not-leak-password"));
}

fn verify_lock_outcome(config: &Config) {
    let mut blocker = config.connect(NoTls).unwrap();
    let locked: bool = blocker
        .query_one(
            "SELECT pg_catalog.pg_try_advisory_lock($1)",
            &[&SCHEMA_ADVISORY_LOCK_KEY],
        )
        .unwrap()
        .try_get(0)
        .unwrap();
    assert!(locked);
    assert_eq!(
        adopt_legacy_schema(config),
        Err(LegacyAdopterError::LockUnavailable)
    );
    let unlocked: bool = blocker
        .query_one(
            "SELECT pg_catalog.pg_advisory_unlock($1)",
            &[&SCHEMA_ADVISORY_LOCK_KEY],
        )
        .unwrap()
        .try_get(0)
        .unwrap();
    assert!(unlocked);
    drop(blocker);
    assert_lock_released(config);
}

fn verify_blocking_table_lock_timeout(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "table_lock");
    let config = database.config(base);
    let mut blocker = config.connect(NoTls).unwrap();
    blocker
        .batch_execute("BEGIN; LOCK TABLE public._babylon_schema_stamp IN ACCESS EXCLUSIVE MODE")
        .unwrap();
    assert_eq!(
        adopt_legacy_schema(&config),
        Err(LegacyAdopterError::Timeout {
            operation: LegacyAdopterOperation::Census,
        })
    );
    blocker.batch_execute("ROLLBACK").unwrap();
    drop(blocker);
    assert_lock_released(&config);
}

fn verify_no_mutation_and_quoted_extras(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "quoted_extra");
    let config = database.config(base);
    let mut client = config.connect(NoTls).unwrap();
    client
        .batch_execute(
            "CREATE SCHEMA \"Quoted Ω\"; \
             CREATE TABLE \"Quoted Ω\".\"Míxed Table\" \
                 (key text PRIMARY KEY, payload integer); \
             INSERT INTO \"Quoted Ω\".\"Míxed Table\" VALUES ('canary', 42)",
        )
        .unwrap();
    let authority_before = authority_snapshot(&mut client);
    let canary_before = quoted_canary_identity(&mut client);
    drop(client);

    assert_eq!(
        adopt_legacy_schema(&config),
        Err(LegacyAdopterError::UnsupportedLegacyExtras {
            objects: vec![
                database_key(LegacyObjectKind::Relation, "Quoted Ω", "Míxed Table"),
                database_key(LegacyObjectKind::Schema, "pg_namespace", "Quoted Ω"),
            ],
        })
    );
    let mut after_client = config.connect(NoTls).unwrap();
    assert_eq!(authority_snapshot(&mut after_client), authority_before);
    assert_eq!(quoted_canary_identity(&mut after_client), canary_before);
    drop(after_client);
    assert_lock_released(&config);
}

fn verify_stamp_refusals(base: &Config, template: &str) {
    verify_canonical_stamp_width(base, template);
    verify_stamp_presence_and_value_refusals(base, template);
    verify_stamp_shape_and_bounds_refusals(base, template);
}

fn verify_canonical_stamp_width(base: &Config, template: &str) {
    let mut config = base.clone();
    config.dbname(template);
    let mut client = config.connect(NoTls).unwrap();
    let error = client
        .execute(
            "INSERT INTO public._babylon_schema_stamp (digest) VALUES (repeat('a', 65))",
            &[],
        )
        .unwrap_err();
    assert_eq!(error.code(), Some(&SqlState::STRING_DATA_RIGHT_TRUNCATION));
    drop(client);
    adopt_legacy_schema(&config)
        .expect("rejected oversized stamp must leave the database canonical");
    assert_lock_released(&config);
}

fn verify_stamp_presence_and_value_refusals(base: &Config, template: &str) {
    let absent = ScratchDatabase::from_template(base, template, "absent_stamp");
    let absent_config = absent.config(base);
    mutate(&absent_config, "DROP TABLE public._babylon_schema_stamp");
    assert_outcome_and_lock(&absent_config, &Err(LegacyAdopterError::StampTableMissing));

    let missing = ScratchDatabase::from_template(base, template, "missing_stamp");
    let missing_config = missing.config(base);
    let mut client = missing_config.connect(NoTls).unwrap();
    client
        .execute(
            "DELETE FROM public._babylon_schema_stamp WHERE digest = $1",
            &[&LEGACY_STAMP_CATALOG[1].digest_hex],
        )
        .unwrap();
    drop(client);
    assert_outcome_and_lock(
        &missing_config,
        &Err(LegacyAdopterError::RequiredStampMissing {
            missing: vec![LEGACY_STAMP_CATALOG[1]],
        }),
    );

    let unknown = ScratchDatabase::from_template(base, template, "unknown_stamp");
    let unknown_config = unknown.config(base);
    mutate(
        &unknown_config,
        "INSERT INTO public._babylon_schema_stamp (digest) \
         VALUES ('3333333333333333333333333333333333333333333333333333333333333333')",
    );
    assert_outcome_and_lock(
        &unknown_config,
        &Err(LegacyAdopterError::UnknownStamp {
            digests: vec![
                "3333333333333333333333333333333333333333333333333333333333333333".into(),
            ],
        }),
    );
}

fn verify_stamp_shape_and_bounds_refusals(base: &Config, template: &str) {
    let malformed = ScratchDatabase::from_template(base, template, "malformed_stamp");
    let malformed_config = malformed.config(base);
    mutate(
        &malformed_config,
        "DROP TABLE public._babylon_schema_stamp; \
         CREATE TABLE public._babylon_schema_stamp (digest integer); \
         INSERT INTO public._babylon_schema_stamp VALUES (7)",
    );
    assert_census_change(
        &malformed_config,
        &object_key(
            LegacyObjectKind::Relation,
            "public",
            "_babylon_schema_stamp",
        ),
    );

    let malformed_large = ScratchDatabase::from_template(base, template, "malformed_large_stamp");
    let malformed_large_config = malformed_large.config(base);
    mutate(
        &malformed_large_config,
        "DROP TABLE public._babylon_schema_stamp; \
         CREATE TABLE public._babylon_schema_stamp ( \
             digest text, applied_at timestamptz NOT NULL DEFAULT now() \
         ); \
         INSERT INTO public._babylon_schema_stamp (digest) VALUES (repeat('a', 1000000))",
    );
    assert_census_change(
        &malformed_large_config,
        &object_key(
            LegacyObjectKind::Relation,
            "public",
            "_babylon_schema_stamp",
        ),
    );

    let over_limit = ScratchDatabase::from_template(base, template, "stamp_bound");
    let over_limit_config = over_limit.config(base);
    mutate(
        &over_limit_config,
        "INSERT INTO public._babylon_schema_stamp (digest) \
         SELECT pg_catalog.lpad(pg_catalog.to_hex(value), 64, '0') \
         FROM pg_catalog.generate_series(100, 164) AS value",
    );
    assert_bounds_and_lock(
        &over_limit_config,
        LegacyBoundedResource::StampRows,
        65,
        MAX_LEGACY_STAMP_ROWS,
    );
}

fn verify_authority_epoch_refusal(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "authority_epoch");
    let config = database.config(base);
    mutate(
        &config,
        "CREATE SCHEMA babylon_state; CREATE SCHEMA babylon_ref",
    );
    assert_outcome_and_lock(
        &config,
        &Err(LegacyAdopterError::UnsupportedAuthorityEpoch {
            schemas: vec!["babylon_ref".into(), "babylon_state".into()],
        }),
    );
}

fn verify_structural_and_role_refusals(base: &Config, template: &str) {
    let mismatch = ScratchDatabase::from_template(base, template, "structural_mismatch");
    let mismatch_config = mismatch.config(base);
    mutate(
        &mismatch_config,
        "ALTER TABLE public.game_session ADD COLUMN adopter_mismatch_probe integer",
    );
    assert_census_change(
        &mismatch_config,
        &object_key(LegacyObjectKind::Relation, "public", "game_session"),
    );

    let view_options = ScratchDatabase::from_template(base, template, "view_options");
    let view_options_config = view_options.config(base);
    mutate(
        &view_options_config,
        "ALTER VIEW public.v_hex_state_asof SET (security_invoker = true)",
    );
    assert_census_change(
        &view_options_config,
        &object_key(LegacyObjectKind::View, "public", "v_hex_state_asof"),
    );

    let owner_drift = ScratchDatabase::from_template(base, template, "owner_drift");
    let owner_config = owner_drift.config(base);
    mutate(
        &owner_config,
        "ALTER TABLE public.game_session OWNER TO babylon_intel",
    );
    assert_census_change(
        &owner_config,
        &object_key(LegacyObjectKind::Relation, "public", "game_session"),
    );

    verify_relation_column_history_refusals(base, template);
    verify_relation_missing_value_state(base, template);

    let role_database = ScratchDatabase::from_template(base, template, "role_escalation");
    let role_config = role_database.config(base);
    let guard = GlobalMutationGuard::apply(
        base,
        "ALTER ROLE babylon_intel SUPERUSER",
        "ALTER ROLE babylon_intel NOSUPERUSER",
    );
    let outcome = adopt_legacy_schema(&role_config);
    guard.cleanup();
    assert_eq!(
        outcome,
        Err(LegacyAdopterError::CensusMismatch {
            missing_objects: Vec::new(),
            changed_objects: vec![object_key(
                LegacyObjectKind::Role,
                "pg_roles",
                "babylon_intel",
            )],
            extra_objects: Vec::new(),
        })
    );
    assert_lock_released(&role_config);
}

fn verify_relation_column_history_refusals(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "relation_column_history");
    let config = database.config(base);
    mutate(
        &config,
        "ALTER TABLE public.game_session ADD COLUMN per20_history_probe integer; \
         ALTER TABLE public.game_session DROP COLUMN per20_history_probe",
    );
    assert_census_change(
        &config,
        &object_key(LegacyObjectKind::Relation, "public", "game_session"),
    );
}

fn verify_relation_missing_value_state(base: &Config, template: &str) {
    let retained = ScratchDatabase::from_template(base, template, "missing_value_retained");
    let rewritten = ScratchDatabase::from_template(base, template, "missing_value_rewritten");
    let retained_config = retained.config(base);
    let rewritten_config = rewritten.config(base);
    let add_column =
        "ALTER TABLE public.game_session ADD COLUMN per20_missing_probe integer DEFAULT 17";
    mutate(&retained_config, add_column);
    mutate(&rewritten_config, add_column);
    mutate(&rewritten_config, "VACUUM FULL public.game_session");
    assert_eq!(
        attribute_missing_state(&retained_config, "per20_missing_probe"),
        (true, Some("[17]".to_owned()))
    );
    assert_eq!(
        attribute_missing_state(&rewritten_config, "per20_missing_probe"),
        (false, None)
    );
    assert_ne!(
        census_digest(&retained_config, "relation", "public", "game_session"),
        census_digest(&rewritten_config, "relation", "public", "game_session")
    );
}

fn attribute_missing_state(config: &Config, column: &str) -> (bool, Option<String>) {
    let mut client = config.connect(NoTls).unwrap();
    let row = client
        .query_one(
            "SELECT attribute.atthasmissing, \
                    pg_catalog.to_jsonb(attribute.attmissingval)::pg_catalog.text \
             FROM pg_catalog.pg_attribute AS attribute \
             WHERE attribute.attrelid = 'public.game_session'::pg_catalog.regclass \
               AND attribute.attname = $1",
            &[&column],
        )
        .unwrap();
    (row.try_get(0).unwrap(), row.try_get(1).unwrap())
}

fn verify_effective_authority_refusals(base: &Config, template: &str) {
    let column = ScratchDatabase::from_template(base, template, "column_acl");
    let column_config = column.config(base);
    mutate(
        &column_config,
        "GRANT UPDATE (current_tick) ON public.game_session TO babylon_intel",
    );
    assert_census_change(
        &column_config,
        &object_key(LegacyObjectKind::Relation, "public", "game_session"),
    );

    let database_acl = ScratchDatabase::from_template(base, template, "database_acl");
    let database_acl_config = database_acl.config(base);
    mutate(
        &database_acl_config,
        &format!(
            "GRANT CREATE ON DATABASE {} TO babylon_intel",
            quote_identifier(database_acl.name())
        ),
    );
    assert_census_change(
        &database_acl_config,
        &object_key(
            LegacyObjectKind::Database,
            "pg_database",
            "current_database",
        ),
    );

    let defaults = ScratchDatabase::from_template(base, template, "default_acl");
    let defaults_config = defaults.config(base);
    mutate(
        &defaults_config,
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public \
         GRANT SELECT ON TABLES TO babylon_intel",
    );
    assert_census_change(
        &defaults_config,
        &object_key(LegacyObjectKind::Role, "pg_roles", "babylon_intel"),
    );

    let owner_defaults = ScratchDatabase::from_template(base, template, "owner_default_acl");
    let owner_defaults_config = owner_defaults.config(base);
    mutate(
        &owner_defaults_config,
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public \
         GRANT SELECT ON TABLES TO PUBLIC",
    );
    assert_census_change(
        &owner_defaults_config,
        &object_key(LegacyObjectKind::Role, "pg_roles", "babylon_intel"),
    );

    verify_global_role_config(base, template);
    verify_global_parameter_privileges(base, template);
    verify_global_membership(base, template);
    verify_database_owner_safety(base, template);
}

fn verify_global_parameter_privileges(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "parameter_acl");
    let config = database.config(base);
    for (apply, cleanup) in [
        (
            "GRANT SET ON PARAMETER work_mem TO babylon_intel WITH GRANT OPTION",
            "REVOKE SET ON PARAMETER work_mem FROM babylon_intel",
        ),
        (
            "GRANT ALTER SYSTEM ON PARAMETER work_mem TO PUBLIC",
            "REVOKE ALTER SYSTEM ON PARAMETER work_mem FROM PUBLIC",
        ),
    ] {
        let guard = GlobalMutationGuard::apply(base, apply, cleanup);
        assert_census_change(
            &config,
            &object_key(LegacyObjectKind::Role, "pg_roles", "babylon_intel"),
        );
        guard.cleanup();
    }
}

fn verify_global_role_config(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "role_config");
    let config = database.config(base);
    let guard = GlobalMutationGuard::apply(
        base,
        "ALTER ROLE babylon_intel SET statement_timeout = '17s'",
        "ALTER ROLE babylon_intel RESET statement_timeout",
    );
    assert_census_change(
        &config,
        &object_key(LegacyObjectKind::Role, "pg_roles", "babylon_intel"),
    );
    guard.cleanup();
}

fn verify_global_membership(base: &Config, template: &str) {
    let granted_role = ScratchRole::create(base);
    let database = ScratchDatabase::from_template(base, template, "membership");
    let config = database.config(base);
    let apply = format!(
        "GRANT {} TO babylon_intel",
        quote_identifier(granted_role.name())
    );
    let cleanup = format!(
        "REVOKE {} FROM babylon_intel",
        quote_identifier(granted_role.name())
    );
    let guard = GlobalMutationGuard::apply(base, &apply, &cleanup);
    assert_census_change(
        &config,
        &object_key(LegacyObjectKind::Role, "pg_roles", "babylon_intel"),
    );
    guard.cleanup();
}

fn verify_reserved_role_name_refusals(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "reserved_roles");
    let config = database.config(base);
    for role_name in [
        r#""$database_owner""#,
        r#""$superuser""#,
        r#""ALL""#,
        r#""PUBLIC""#,
        r#""$other_owner:collision""#,
    ]
    .iter()
    .take(5)
    {
        let apply = format!("CREATE ROLE {role_name}");
        let cleanup = format!("DROP ROLE {role_name}");
        let guard = GlobalMutationGuard::apply(base, &apply, &cleanup);
        assert_unsupported_catalog_and_lock(&config, "pg_roles");
        guard.cleanup();
    }
}

fn verify_database_owner_safety(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "database_owner");
    let config = database.config(base);
    let mut before_client = config.connect(NoTls).unwrap();
    let before = authority_snapshot(&mut before_client);
    drop(before_client);
    let sql = format!(
        "ALTER DATABASE {} OWNER TO babylon_intel",
        quote_identifier(database.name())
    );
    let mut admin = admin_config(base).connect(NoTls).unwrap();
    admin.batch_execute(&sql).unwrap();
    drop(admin);
    let mut after_client = config.connect(NoTls).unwrap();
    let after = authority_snapshot(&mut after_client);
    drop(after_client);
    assert_ne!(database_digest(&before), database_digest(&after));
    assert_census_mismatch(
        &config,
        Vec::new(),
        vec![object_key(
            LegacyObjectKind::Relation,
            "public",
            "_babylon_schema_stamp",
        )],
        Vec::new(),
    );
}

fn verify_write_semantic_refusals(base: &Config, template: &str) {
    verify_relation_mutation(
        base,
        template,
        "instead_rule",
        "CREATE RULE adopter_instead AS ON INSERT TO public.game_session DO INSTEAD NOTHING",
    );
    verify_relation_mutation(
        base,
        template,
        "table_trigger",
        "CREATE TRIGGER adopter_before_update BEFORE UPDATE ON public.game_session \
         FOR EACH ROW EXECUTE FUNCTION pg_catalog.suppress_redundant_updates_trigger()",
    );
    verify_relation_mutation(
        base,
        template,
        "table_policy",
        "ALTER TABLE public.game_session ENABLE ROW LEVEL SECURITY; \
         CREATE POLICY adopter_policy ON public.game_session USING (true)",
    );
    verify_relation_mutation(
        base,
        template,
        "table_options",
        "ALTER TABLE public.game_session SET (fillfactor = 70)",
    );
    verify_clustered_index_state(base, template);
    verify_replica_identity_index_state(base, template);
}

fn verify_clustered_index_state(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "clustered_index_state");
    let config = database.config(base);
    mutate(
        &config,
        "CLUSTER public.game_session USING game_session_pkey",
    );
    assert_eq!(index_state(&config, "game_session_pkey"), (true, false));
    assert_census_change(
        &config,
        &object_key(LegacyObjectKind::Relation, "public", "game_session"),
    );
}

fn verify_replica_identity_index_state(base: &Config, template: &str) {
    let primary = ScratchDatabase::from_template(base, template, "replica_identity_primary");
    let alternate = ScratchDatabase::from_template(base, template, "replica_identity_alternate");
    let primary_config = primary.config(base);
    let alternate_config = alternate.config(base);
    let alternate_index =
        "CREATE UNIQUE INDEX per20_game_session_replica ON public.game_session (id)";
    mutate(&primary_config, alternate_index);
    mutate(&alternate_config, alternate_index);
    mutate(
        &primary_config,
        "ALTER TABLE public.game_session REPLICA IDENTITY USING INDEX game_session_pkey",
    );
    mutate(
        &alternate_config,
        "ALTER TABLE public.game_session REPLICA IDENTITY USING INDEX per20_game_session_replica",
    );
    assert_eq!(
        index_state(&primary_config, "game_session_pkey"),
        (false, true)
    );
    assert_eq!(
        index_state(&alternate_config, "per20_game_session_replica"),
        (false, true)
    );
    assert_ne!(
        census_digest(&primary_config, "relation", "public", "game_session"),
        census_digest(&alternate_config, "relation", "public", "game_session")
    );
}

fn index_state(config: &Config, index_name: &str) -> (bool, bool) {
    let mut client = config.connect(NoTls).unwrap();
    let row = client
        .query_one(
            "SELECT index_row.indisclustered, index_row.indisreplident \
             FROM pg_catalog.pg_index AS index_row \
             JOIN pg_catalog.pg_class AS index_class ON index_class.oid = index_row.indexrelid \
             JOIN pg_catalog.pg_namespace AS index_ns ON index_ns.oid = index_class.relnamespace \
             WHERE index_ns.nspname = 'public' AND index_class.relname = $1",
            &[&index_name],
        )
        .unwrap();
    (row.try_get(0).unwrap(), row.try_get(1).unwrap())
}

fn verify_relation_mutation(base: &Config, template: &str, label: &str, sql: &str) {
    let database = ScratchDatabase::from_template(base, template, label);
    let config = database.config(base);
    mutate(&config, sql);
    assert_census_change(
        &config,
        &object_key(LegacyObjectKind::Relation, "public", "game_session"),
    );
}

fn verify_inheritance_and_subpartition_refusals(base: &Config, template: &str) {
    let inherited = ScratchDatabase::from_template(base, template, "inbound_inheritance");
    let inherited_config = inherited.config(base);
    mutate(
        &inherited_config,
        "CREATE TABLE public.per20_inherited_session () INHERITS (public.game_session)",
    );
    assert_census_mismatch(
        &inherited_config,
        Vec::new(),
        vec![object_key(
            LegacyObjectKind::Relation,
            "public",
            "game_session",
        )],
        vec![object_key(
            LegacyObjectKind::Relation,
            "public",
            "per20_inherited_session",
        )],
    );

    let subpartition = ScratchDatabase::from_template(base, template, "subpartitioned_child");
    let subpartition_config = subpartition.config(base);
    mutate(
        &subpartition_config,
        "DROP TABLE public.tick_commit_default; \
         CREATE TABLE public.tick_commit_default PARTITION OF public.tick_commit DEFAULT \
             PARTITION BY RANGE (tick); \
         CREATE TABLE public.tick_commit_default_leaf \
             PARTITION OF public.tick_commit_default DEFAULT",
    );
    assert_census_mismatch(
        &subpartition_config,
        Vec::new(),
        vec![object_key(
            LegacyObjectKind::PartitionedTable,
            "public",
            "tick_commit",
        )],
        vec![object_key(
            LegacyObjectKind::Relation,
            "public",
            "tick_commit_default_leaf",
        )],
    );
}

fn verify_partition_children(base: &Config, template: &str) {
    verify_valid_partition_children(base, template);
    verify_partition_name_and_bound_refusals(base, template);
    verify_static_partition_refusals(base, template);
}

fn verify_valid_partition_children(base: &Config, template: &str) {
    let valid = ScratchDatabase::from_template(base, template, "valid_partition");
    let valid_config = valid.config(base);
    mutate(
        &valid_config,
        &format!(
            "CREATE TABLE public.dynamic_hex_state_p_{} \
             PARTITION OF public.dynamic_hex_state FOR VALUES IN ('{SESSION_UUID}'); \
             CREATE TABLE public.tick_commit_p_{} \
             PARTITION OF public.tick_commit FOR VALUES IN ('{SECOND_UUID}')",
            SESSION_UUID.replace('-', ""),
            SECOND_UUID.replace('-', "")
        ),
    );
    let report = adopt_legacy_schema(&valid_config).expect("proper dynamic bounds must adopt");
    assert!(report.extra_objects.is_empty());
    assert_lock_released(&valid_config);
}

fn verify_partition_name_and_bound_refusals(base: &Config, template: &str) {
    let malformed = ScratchDatabase::from_template(base, template, "bad_partition");
    let malformed_config = malformed.config(base);
    mutate(
        &malformed_config,
        &format!(
            "CREATE TABLE public.dynamic_hex_state_bad_child \
             PARTITION OF public.dynamic_hex_state FOR VALUES IN ('{SECOND_UUID}')"
        ),
    );
    assert_parent_change(&malformed_config, "dynamic_hex_state");

    let wrong_bound = ScratchDatabase::from_template(base, template, "wrong_bound");
    let wrong_bound_config = wrong_bound.config(base);
    mutate(
        &wrong_bound_config,
        &format!(
            "CREATE TABLE public.dynamic_hex_state_p_{} \
             PARTITION OF public.dynamic_hex_state FOR VALUES IN ('{SECOND_UUID}')",
            SESSION_UUID.replace('-', "")
        ),
    );
    assert_parent_change(&wrong_bound_config, "dynamic_hex_state");

    let cross_schema = ScratchDatabase::from_template(base, template, "cross_schema");
    let cross_schema_config = cross_schema.config(base);
    mutate(
        &cross_schema_config,
        &format!(
            "CREATE SCHEMA adopter_extra; \
             CREATE TABLE adopter_extra.dynamic_hex_state_p_{} \
             PARTITION OF public.dynamic_hex_state FOR VALUES IN ('{SESSION_UUID}')",
            SESSION_UUID.replace('-', "")
        ),
    );
    assert_census_mismatch(
        &cross_schema_config,
        Vec::new(),
        vec![object_key(
            LegacyObjectKind::PartitionedTable,
            "public",
            "dynamic_hex_state",
        )],
        vec![object_key(
            LegacyObjectKind::Schema,
            "pg_namespace",
            "adopter_extra",
        )],
    );
}

fn verify_static_partition_refusals(base: &Config, template: &str) {
    let missing = ScratchDatabase::from_template(base, template, "missing_default");
    let missing_config = missing.config(base);
    mutate(
        &missing_config,
        "DROP TABLE public.dynamic_hex_state_default",
    );
    assert_parent_change(&missing_config, "dynamic_hex_state");

    verify_default_partition_mutation(
        base,
        template,
        "default_options",
        "ALTER TABLE public.dynamic_hex_state_default SET (fillfactor = 70)",
    );
    verify_default_partition_mutation(
        base,
        template,
        "default_acl",
        "GRANT SELECT ON public.dynamic_hex_state_default TO babylon_intel",
    );
    verify_default_partition_mutation(
        base,
        template,
        "default_trigger",
        "CREATE TRIGGER adopter_child_trigger BEFORE UPDATE \
         ON public.dynamic_hex_state_default FOR EACH ROW \
         EXECUTE FUNCTION pg_catalog.suppress_redundant_updates_trigger()",
    );
}

fn verify_default_partition_mutation(base: &Config, template: &str, label: &str, sql: &str) {
    let database = ScratchDatabase::from_template(base, template, label);
    let config = database.config(base);
    mutate(&config, sql);
    assert_parent_change(&config, "dynamic_hex_state");
}

fn assert_parent_change(config: &Config, parent: &str) {
    assert_census_mismatch(
        config,
        Vec::new(),
        vec![object_key(
            LegacyObjectKind::PartitionedTable,
            "public",
            parent,
        )],
        Vec::new(),
    );
}

fn verify_extra_schema_routine_and_type_refusal(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "extra_surfaces");
    let config = database.config(base);
    mutate(
        &config,
        "CREATE SCHEMA adopter_surface; \
         CREATE DOMAIN adopter_surface.positive_int AS integer CHECK (VALUE > 0); \
         CREATE TYPE adopter_surface.mood AS ENUM ('low', 'high'); \
         CREATE FUNCTION adopter_surface.adopter_probe(value integer) RETURNS integer \
         LANGUAGE SQL IMMUTABLE SECURITY INVOKER AS 'SELECT value + 1'",
    );
    assert_unsupported_extras(
        &config,
        vec![
            object_key(LegacyObjectKind::Domain, "adopter_surface", "positive_int"),
            object_key(
                LegacyObjectKind::Routine,
                "adopter_surface",
                "adopter_probe",
            ),
            object_key(LegacyObjectKind::Schema, "pg_namespace", "adopter_surface"),
            object_key(LegacyObjectKind::UserType, "adopter_surface", "mood"),
        ],
    );

    verify_composite_column_history(base, template);
}

fn verify_composite_column_history(base: &Config, template: &str) {
    let live = ScratchDatabase::from_template(base, template, "composite_live_shape");
    let tombstone = ScratchDatabase::from_template(base, template, "composite_tombstone_shape");
    let live_config = live.config(base);
    let tombstone_config = tombstone.config(base);
    let create_type = "CREATE TYPE public.per20_composite_history AS (value integer)";
    mutate(&live_config, create_type);
    mutate(&tombstone_config, create_type);
    mutate(
        &tombstone_config,
        "ALTER TYPE public.per20_composite_history ADD ATTRIBUTE transient integer; \
         ALTER TYPE public.per20_composite_history DROP ATTRIBUTE transient",
    );
    assert_ne!(
        census_digest(
            &live_config,
            "user_type",
            "public",
            "per20_composite_history",
        ),
        census_digest(
            &tombstone_config,
            "user_type",
            "public",
            "per20_composite_history",
        )
    );
}

fn verify_strict_census_refusals(base: &Config, template: &str) {
    verify_login_event_trigger_suppression(base, template);
    verify_event_publication_and_subscription_refusals(base, template);
    verify_unsafe_routine_refusals(base, template);
    verify_extra_mutation_grant_refusals(base, template);
}

fn verify_cast_and_system_namespace_refusals(base: &Config, template: &str) {
    let cast = ScratchDatabase::from_template(base, template, "builtin_cast");
    let cast_config = cast.config(base);
    mutate(&cast_config, "CREATE CAST (uuid AS integer) WITH INOUT");
    assert_unsupported_catalog_and_lock(&cast_config, "pg_cast");

    verify_system_namespace_relation(base, template);
    verify_system_namespace_routine(base, template);
    verify_system_namespace_type(base, template);
}

fn verify_system_namespace_relation(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "system_relation");
    let config = database.config(base);
    mutate(
        &config,
        "SET allow_system_table_mods = on; \
         CREATE TABLE pg_catalog.per20_system_relation (id integer)",
    );
    assert_unsupported_catalog_and_lock(&config, "pg_class");
}

fn verify_system_namespace_routine(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "system_routine");
    let config = database.config(base);
    mutate(
        &config,
        "SET allow_system_table_mods = on; \
         CREATE FUNCTION pg_catalog.per20_system_routine() RETURNS integer \
             LANGUAGE SQL IMMUTABLE AS 'SELECT 1'",
    );
    assert_unsupported_catalog_and_lock(&config, "pg_proc");
}

fn verify_system_namespace_type(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "system_type");
    let config = database.config(base);
    mutate(
        &config,
        "SET allow_system_table_mods = on; \
         CREATE TYPE pg_catalog.per20_system_type AS ENUM ('one')",
    );
    assert_unsupported_catalog_and_lock(&config, "pg_type");
}

fn verify_login_event_trigger_suppression(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "login_event_trigger");
    let config = database.config(base);
    let mut setup = config.connect(NoTls).unwrap();
    install_login_event_trigger(&mut setup);
    let observer = event_triggers_disabled_config(&config);
    let outcome = adopt_legacy_schema(&config);
    assert_eq!(
        outcome,
        Err(LegacyAdopterError::CensusMismatch {
            missing_objects: Vec::new(),
            changed_objects: vec![
                object_key(
                    LegacyObjectKind::Database,
                    "pg_database",
                    "current_database",
                ),
                object_key(LegacyObjectKind::Extension, "pg_extension", "plpgsql"),
            ],
            extra_objects: vec![
                object_key(LegacyObjectKind::Relation, "public", "per20_login_canary",),
                object_key(
                    LegacyObjectKind::Routine,
                    "public",
                    "per20_login_canary_trigger",
                ),
                object_key(
                    LegacyObjectKind::UnsupportedCatalog,
                    "pg_catalog",
                    "pg_event_trigger",
                ),
            ],
        })
    );
    assert_login_canary_unchanged(&observer);
    assert_lock_released(&observer);
    drop(setup);

    let restricted_role = ScratchRole::create_without_event_trigger_set(base);
    let restricted = ScratchDatabase::from_template(base, template, "login_without_parameter_set");
    let restricted_admin = restricted.config(base);
    let mut restricted_setup = restricted_admin.connect(NoTls).unwrap();
    install_login_event_trigger(&mut restricted_setup);
    let restricted_observer = event_triggers_disabled_config(&restricted_admin);
    let restricted_config = restricted.config_as(base, restricted_role.name(), OWNER_PASSWORD);
    assert_eq!(
        adopt_legacy_schema(&restricted_config),
        Err(LegacyAdopterError::EventTriggerSuppressionUnavailable)
    );
    assert_login_canary_unchanged(&restricted_observer);
    assert_lock_released(&restricted_observer);
    drop(restricted_setup);
    restricted_role.cleanup();
}

fn install_login_event_trigger(setup: &mut Client) {
    setup
        .batch_execute(
            "CREATE TABLE public.per20_login_canary (value integer NOT NULL); \
             INSERT INTO public.per20_login_canary VALUES (0); \
             CREATE FUNCTION public.per20_login_canary_trigger() RETURNS event_trigger \
                 LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog \
                 AS 'BEGIN \
                     UPDATE public.per20_login_canary SET value = value + 1; \
                 END;'; \
             CREATE EVENT TRIGGER per20_login_canary_trigger ON login \
                 EXECUTE FUNCTION public.per20_login_canary_trigger()",
        )
        .unwrap();
}

fn event_triggers_disabled_config(config: &Config) -> Config {
    let mut observer = config.clone();
    observer.options("-c event_triggers=off");
    observer
}

fn assert_login_canary_unchanged(observer: &Config) {
    let value: i32 = observer
        .connect(NoTls)
        .unwrap()
        .query_one("SELECT value FROM public.per20_login_canary", &[])
        .unwrap()
        .try_get(0)
        .unwrap();
    assert_eq!(value, 0);
}

fn verify_event_publication_and_subscription_refusals(base: &Config, template: &str) {
    let event = ScratchDatabase::from_template(base, template, "event_trigger");
    let event_config = event.config(base);
    mutate(
        &event_config,
        "CREATE FUNCTION public.per20_event_trigger() RETURNS event_trigger \
             LANGUAGE plpgsql AS 'BEGIN END;'; \
         CREATE EVENT TRIGGER per20_noop_event ON ddl_command_start \
             EXECUTE FUNCTION public.per20_event_trigger()",
    );
    assert_census_mismatch(
        &event_config,
        Vec::new(),
        vec![object_key(
            LegacyObjectKind::Extension,
            "pg_extension",
            "plpgsql",
        )],
        vec![
            object_key(LegacyObjectKind::Routine, "public", "per20_event_trigger"),
            object_key(
                LegacyObjectKind::UnsupportedCatalog,
                "pg_catalog",
                "pg_event_trigger",
            ),
        ],
    );

    let publication = ScratchDatabase::from_template(base, template, "publication");
    let publication_config = publication.config(base);
    mutate(&publication_config, "CREATE PUBLICATION per20_publication");
    assert_unsupported_catalog_and_lock(&publication_config, "pg_publication");

    let subscription = ScratchDatabase::from_template(base, template, "subscription");
    let subscription_config = subscription.config(base);
    let guard = GlobalMutationGuard::apply(
        &subscription_config,
        "CREATE SUBSCRIPTION per20_disabled_subscription \
             CONNECTION 'host=127.0.0.1 port=1 dbname=postgres connect_timeout=1' \
             PUBLICATION per20_remote_publication \
             WITH (connect = false, enabled = false, create_slot = false, slot_name = NONE)",
        "DROP SUBSCRIPTION per20_disabled_subscription",
    );
    assert_unsupported_catalog_and_lock(&subscription_config, "pg_subscription");
    guard.cleanup();
}

fn verify_unsafe_routine_refusals(base: &Config, template: &str) {
    let definer = ScratchDatabase::from_template(base, template, "security_definer");
    let definer_config = definer.config(base);
    mutate(
        &definer_config,
        "CREATE FUNCTION public.per20_definer(value integer) RETURNS integer \
         LANGUAGE SQL IMMUTABLE SECURITY DEFINER AS 'SELECT value'",
    );
    assert_unsupported_extras(
        &definer_config,
        vec![object_key(
            LegacyObjectKind::Routine,
            "public",
            "per20_definer",
        )],
    );

    let volatile = ScratchDatabase::from_template(base, template, "volatile_invoker");
    let volatile_config = volatile.config(base);
    mutate(
        &volatile_config,
        "CREATE FUNCTION public.per20_volatile(value integer) RETURNS integer \
         LANGUAGE SQL VOLATILE SECURITY INVOKER AS 'SELECT value'",
    );
    assert_unsupported_extras(
        &volatile_config,
        vec![object_key(
            LegacyObjectKind::Routine,
            "public",
            "per20_volatile",
        )],
    );

    let untrusted_owner = ScratchRole::create(base);
    let untrusted = ScratchDatabase::from_template(base, template, "untrusted_routine_owner");
    let untrusted_config = untrusted.config(base);
    mutate(
        &untrusted_config,
        &format!(
            "CREATE FUNCTION public.per20_untrusted(value integer) RETURNS integer \
                 LANGUAGE SQL IMMUTABLE SECURITY INVOKER AS 'SELECT value'; \
             ALTER FUNCTION public.per20_untrusted(integer) OWNER TO {}",
            quote_identifier(untrusted_owner.name())
        ),
    );
    assert_unsupported_extras(
        &untrusted_config,
        vec![object_key(
            LegacyObjectKind::Routine,
            "public",
            "per20_untrusted",
        )],
    );
    untrusted.cleanup();
    untrusted_owner.cleanup();
}

fn verify_extra_mutation_grant_refusals(base: &Config, template: &str) {
    let schema = ScratchDatabase::from_template(base, template, "extra_schema_grant");
    let schema_config = schema.config(base);
    mutate(
        &schema_config,
        "CREATE SCHEMA per20_authority; \
         GRANT CREATE ON SCHEMA per20_authority TO babylon_intel",
    );
    assert_unsupported_extras(
        &schema_config,
        vec![object_key(
            LegacyObjectKind::Schema,
            "pg_namespace",
            "per20_authority",
        )],
    );

    let relation = ScratchDatabase::from_template(base, template, "extra_relation_grant");
    let relation_config = relation.config(base);
    mutate(
        &relation_config,
        "CREATE TABLE public.per20_authority_table (id integer); \
         GRANT INSERT ON public.per20_authority_table TO babylon_intel",
    );
    assert_unsupported_extras(
        &relation_config,
        vec![object_key(
            LegacyObjectKind::Relation,
            "public",
            "per20_authority_table",
        )],
    );

    let maintain = ScratchDatabase::from_template(base, template, "extra_maintain_grant");
    let maintain_config = maintain.config(base);
    mutate(
        &maintain_config,
        "CREATE TABLE public.per20_maintain_table (id integer); \
         GRANT MAINTAIN ON public.per20_maintain_table TO babylon_intel",
    );
    assert_unsupported_extras(
        &maintain_config,
        vec![object_key(
            LegacyObjectKind::Relation,
            "public",
            "per20_maintain_table",
        )],
    );
}

fn verify_extension_identity_refusals(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "extension_schema_object");
    let config = database.config(base);
    mutate(
        &config,
        "CREATE SCHEMA adopter_extension_member; \
         ALTER EXTENSION plpgsql ADD SCHEMA adopter_extension_member",
    );
    assert_census_change(
        &config,
        &object_key(LegacyObjectKind::Extension, "pg_extension", "plpgsql"),
    );

    verify_extension_member_function_refusals(base, template);
    verify_extension_member_relation_refusal(base, template);
    verify_extension_window_routine_body_refusal(base, template);
    verify_extension_superuser_owner_portability(base, template);
    verify_extension_acl_role_completeness(base, template);

    verify_unknown_extension_classification(base, template);
}

fn verify_unknown_extension_classification(base: &Config, template: &str) {
    let unknown = ScratchDatabase::from_template(base, template, "unknown_extension");
    let unknown_config = unknown.config(base);
    mutate(&unknown_config, "CREATE EXTENSION btree_gist");
    assert_eq!(
        adopt_legacy_schema(&unknown_config),
        Err(LegacyAdopterError::UnsupportedLegacyExtras {
            objects: vec![object_key(
                LegacyObjectKind::Extension,
                "pg_extension",
                "btree_gist",
            )],
        })
    );
    assert_lock_released(&unknown_config);
}

fn verify_extension_member_function_refusals(base: &Config, template: &str) {
    for (label, mutation) in [
        (
            "extension_function_definition",
            "CREATE OR REPLACE FUNCTION public.postgis_version() RETURNS text \
             LANGUAGE SQL IMMUTABLE PARALLEL SAFE AS 'SELECT ''per20-mutated''::text'",
        ),
        (
            "extension_function_security",
            "ALTER FUNCTION public.postgis_version() SECURITY DEFINER",
        ),
        (
            "extension_function_acl",
            "REVOKE EXECUTE ON FUNCTION public.postgis_version() FROM PUBLIC",
        ),
    ] {
        let database = ScratchDatabase::from_template(base, template, label);
        let config = database.config(base);
        mutate(&config, mutation);
        assert_census_change(
            &config,
            &object_key(LegacyObjectKind::Extension, "pg_extension", "postgis"),
        );
    }
}

fn verify_extension_member_relation_refusal(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "extension_relation_shape");
    let config = database.config(base);
    mutate(
        &config,
        "ALTER TABLE public.spatial_ref_sys SET (fillfactor = 70)",
    );
    assert_census_change(
        &config,
        &object_key(LegacyObjectKind::Extension, "pg_extension", "postgis"),
    );
}

fn verify_extension_superuser_owner_portability(base: &Config, template: &str) {
    let owners = GlobalMutationGuard::apply(
        base,
        "CREATE ROLE per20_extension_super_owner_a NOLOGIN SUPERUSER; \
         CREATE ROLE per20_extension_super_owner_b NOLOGIN SUPERUSER",
        "DROP ROLE per20_extension_super_owner_a; DROP ROLE per20_extension_super_owner_b",
    );
    let first = ScratchDatabase::from_template(base, template, "extension_super_owner_a");
    let first_config = first.config(base);
    let second = ScratchDatabase::from_template(base, template, "extension_super_owner_b");
    let second_config = second.config(base);
    let baseline_digest = census_digest(&first_config, "extension", "pg_extension", "postgis");
    assert_eq!(
        baseline_digest,
        census_digest(&second_config, "extension", "pg_extension", "postgis")
    );
    let first_raw_owner_dependencies = raw_extension_member_owner_dependency_count(&first_config);
    assert_eq!(first_raw_owner_dependencies, 0);
    assert_eq!(
        raw_extension_member_owner_dependency_count(&second_config),
        0
    );
    mutate(
        &first_config,
        "ALTER FUNCTION public.postgis_version() OWNER TO per20_extension_super_owner_a",
    );
    mutate(
        &second_config,
        "ALTER FUNCTION public.postgis_version() OWNER TO per20_extension_super_owner_b",
    );
    let first_raw_owner_dependencies_after =
        raw_extension_member_owner_dependency_count(&first_config);
    assert_eq!(first_raw_owner_dependencies_after, 1);
    assert_eq!(
        raw_extension_member_owner_dependency_count(&second_config),
        1
    );
    let first_digest = census_digest(&first_config, "extension", "pg_extension", "postgis");
    let second_digest = census_digest(&second_config, "extension", "pg_extension", "postgis");
    assert_eq!(baseline_digest, first_digest);
    assert_eq!(first_digest, second_digest);
    let first_outcome = adopt_legacy_schema(&first_config);
    let second_outcome = adopt_legacy_schema(&second_config);
    assert!(
        first_outcome.is_ok(),
        "first equivalent-superuser owner must adopt: {first_outcome:?}"
    );
    assert!(
        second_outcome.is_ok(),
        "second equivalent-superuser owner must adopt: {second_outcome:?}"
    );
    assert_eq!(first_outcome, second_outcome);
    assert_lock_released(&first_config);
    assert_lock_released(&second_config);
    first.cleanup();
    second.cleanup();
    owners.cleanup();
}

fn verify_extension_window_routine_body_refusal(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "extension_window_body");
    let config = database.config(base);
    let mut client = config.connect(NoTls).unwrap();
    let row = client
        .query_one(
            "SELECT \
                 pg_catalog.pg_get_functiondef(target.oid), \
                 target.prosrc, \
                 coalesce(target.probin, ''), \
                 replacement.prosrc, \
                 coalesce(replacement.probin, '') \
             FROM pg_catalog.pg_proc AS target \
             JOIN pg_catalog.pg_namespace AS target_ns \
               ON target_ns.oid = target.pronamespace \
             JOIN pg_catalog.pg_proc AS replacement \
               ON replacement.proname = 'st_clusterwithinwin' \
              AND replacement.prokind = 'w' \
             JOIN pg_catalog.pg_namespace AS replacement_ns \
               ON replacement_ns.oid = replacement.pronamespace \
              AND replacement_ns.nspname = 'public' \
             WHERE target_ns.nspname = 'public' \
               AND target.proname = 'st_clusterdbscan' \
               AND target.prokind = 'w'",
            &[],
        )
        .unwrap();
    let definition: String = row.try_get(0).unwrap();
    let source: String = row.try_get(1).unwrap();
    let binary: String = row.try_get(2).unwrap();
    let replacement_source: String = row.try_get(3).unwrap();
    let replacement_binary: String = row.try_get(4).unwrap();
    drop(client);
    assert_eq!(binary, replacement_binary);
    assert_ne!(source, replacement_source);
    assert!(definition.starts_with("CREATE OR REPLACE FUNCTION public.st_clusterdbscan("));
    let source_body = format!("$function${source}$function$");
    let replacement_body = format!("$function${replacement_source}$function$");
    assert!(definition.contains(&source_body));
    let replacement_definition = definition.replacen(&source_body, &replacement_body, 1);
    assert_ne!(definition, replacement_definition);
    let before_digest = census_digest(&config, "extension", "pg_extension", "postgis");
    mutate(&config, &replacement_definition);
    assert_ne!(
        before_digest,
        census_digest(&config, "extension", "pg_extension", "postgis")
    );
}

fn verify_extension_acl_role_completeness(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "extension_acl_roles");
    let config = database.config(base);
    let irrelevant_roles = GlobalMutationGuard::apply(
        &config,
        "DO $per20$ BEGIN FOR role_index IN 0..512 LOOP \
         EXECUTE pg_catalog.format('CREATE ROLE %I', pg_catalog.format( \
         'yyyy_per20_extension_role_%s', pg_catalog.lpad(role_index::pg_catalog.text, 4, '0'))); \
         END LOOP; END $per20$",
        "DO $per20$ BEGIN FOR role_index IN REVERSE 512..0 LOOP \
         EXECUTE pg_catalog.format('DROP ROLE %I', pg_catalog.format( \
         'yyyy_per20_extension_role_%s', pg_catalog.lpad(role_index::pg_catalog.text, 4, '0'))); \
         END LOOP; END $per20$",
    );
    adopt_legacy_schema(&config).expect("irrelevant roles must not affect extension adoption");
    assert_lock_released(&config);
    let before_digest = census_digest(&config, "extension", "pg_extension", "plpgsql");
    let referenced_grantor = GlobalMutationGuard::apply(
        &config,
        "CREATE ROLE zzzz_per20_extension_grantor; SET allow_system_table_mods = on; \
         UPDATE pg_catalog.pg_language AS language SET lanacl = \
         coalesce(language.lanacl, pg_catalog.acldefault('l', language.lanowner)) || \
         ARRAY[pg_catalog.makeaclitem(0, (SELECT oid FROM pg_catalog.pg_roles \
         WHERE rolname = 'zzzz_per20_extension_grantor'), 'USAGE', false)] \
         WHERE language.lanname = 'plpgsql'",
        "SET allow_system_table_mods = on; UPDATE pg_catalog.pg_language AS language SET lanacl = \
         pg_catalog.array_remove(language.lanacl, pg_catalog.makeaclitem(0, \
         (SELECT oid FROM pg_catalog.pg_roles WHERE rolname = 'zzzz_per20_extension_grantor'), \
         'USAGE', false)) WHERE language.lanname = 'plpgsql'; \
         DROP ROLE zzzz_per20_extension_grantor",
    );
    let (raw_acl_count, prefix_acl_count) = extension_language_acl_counts(&config);
    assert_eq!(raw_acl_count, prefix_acl_count + 1);
    assert_ne!(
        before_digest,
        census_digest(&config, "extension", "pg_extension", "plpgsql")
    );
    assert_census_change(
        &config,
        &object_key(LegacyObjectKind::Extension, "pg_extension", "plpgsql"),
    );
    referenced_grantor.cleanup();
    irrelevant_roles.cleanup();
}

fn extension_language_acl_counts(config: &Config) -> (i64, i64) {
    let mut client = config.connect(NoTls).unwrap();
    let prefix_limit = i64::try_from(MAX_LEGACY_CENSUS_ROWS + 1).unwrap();
    let row = client
        .query_one(
            "WITH raw_acl AS ( \
                 SELECT acl.grantor FROM pg_catalog.pg_language AS language \
                 CROSS JOIN LATERAL pg_catalog.aclexplode(coalesce( \
                     language.lanacl, pg_catalog.acldefault('l', language.lanowner))) AS acl \
                 WHERE language.lanname = 'plpgsql' \
             ), old_prefix AS ( \
                 SELECT role_row.oid FROM pg_catalog.pg_roles AS role_row \
                 ORDER BY role_row.rolname, role_row.oid LIMIT $1 \
             ) SELECT (SELECT pg_catalog.count(*) FROM raw_acl), \
                      (SELECT pg_catalog.count(*) FROM raw_acl \
                       JOIN old_prefix ON old_prefix.oid = raw_acl.grantor)",
            &[&prefix_limit],
        )
        .unwrap();
    (row.try_get(0).unwrap(), row.try_get(1).unwrap())
}

fn verify_census_column_bound(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "column_bound");
    let config = database.config(base);
    let mut sql = String::from("CREATE TABLE public.per20_wide_table (");
    for index in 0..=MAX_LEGACY_CENSUS_ROWS {
        if index > 0 {
            sql.push_str(", ");
        }
        write!(sql, "field_{index:03} integer").unwrap();
    }
    sql.push(')');
    mutate(&config, &sql);
    assert_bounds_and_lock(
        &config,
        LegacyBoundedResource::CatalogRows,
        MAX_LEGACY_CENSUS_ROWS + 1,
        MAX_LEGACY_CENSUS_ROWS,
    );
}

fn verify_unsupported_catalog_bounds(base: &Config, template: &str) {
    let collation = ScratchDatabase::from_template(base, template, "unsupported_collation");
    let collation_config = collation.config(base);
    mutate(
        &collation_config,
        "CREATE COLLATION public.per20_collation FROM pg_catalog.\"C\"",
    );
    assert_unsupported_catalog_and_lock(&collation_config, "pg_collation");

    let statistics = ScratchDatabase::from_template(base, template, "unsupported_statistics");
    let statistics_config = statistics.config(base);
    mutate(
        &statistics_config,
        "CREATE STATISTICS public.per20_statistics (dependencies) \
         ON player_id, current_tick FROM public.game_session",
    );
    assert_unsupported_catalog_and_lock(&statistics_config, "pg_statistic_ext");

    let large_objects = ScratchDatabase::from_template(base, template, "large_object_bound");
    let large_object_config = large_objects.config(base);
    mutate(
        &large_object_config,
        "SELECT pg_catalog.lo_create(0) FROM pg_catalog.generate_series(1, 513)",
    );
    assert_bounds_and_lock(
        &large_object_config,
        LegacyBoundedResource::CatalogRows,
        MAX_LEGACY_CENSUS_ROWS + 1,
        MAX_LEGACY_CENSUS_ROWS,
    );
}

fn verify_sequence_owned_by_refusals(base: &Config, template: &str) {
    for (label, mutation) in [
        (
            "sequence_owned_by_none",
            "ALTER SEQUENCE public.action_result_id_seq OWNED BY NONE",
        ),
        (
            "sequence_owned_by_retarget",
            "ALTER SEQUENCE public.action_result_id_seq OWNED BY public.game_turn.id",
        ),
    ] {
        let database = ScratchDatabase::from_template(base, template, label);
        let config = database.config(base);
        mutate(&config, mutation);
        assert_census_change(
            &config,
            &object_key(LegacyObjectKind::Sequence, "public", "action_result_id_seq"),
        );
    }
}

fn verify_sequence_acl_default_semantics(config: &Config) {
    let mut client = config.connect(NoTls).unwrap();
    let rows = client
        .query(
            "SELECT acl.privilege_type::text \
             FROM pg_catalog.aclexplode(pg_catalog.acldefault( \
                 's', (SELECT role_row.oid FROM pg_catalog.pg_roles AS role_row \
                       WHERE role_row.rolname = current_user) \
             )) AS acl \
             ORDER BY acl.privilege_type",
            &[],
        )
        .unwrap();
    assert_eq!(rows.len(), 3);
    let privileges = rows
        .iter()
        .take(3)
        .map(|row| row.try_get::<_, String>(0).unwrap())
        .collect::<Vec<_>>();
    assert_eq!(privileges, vec!["SELECT", "UPDATE", "USAGE"]);
}

fn assert_census_change(config: &Config, expected_key: &LegacyObjectKey) {
    assert_census_mismatch(config, Vec::new(), vec![expected_key.clone()], Vec::new());
}

fn assert_census_mismatch(
    config: &Config,
    expected_missing: Vec<LegacyObjectKey>,
    expected_changed: Vec<LegacyObjectKey>,
    expected_extra: Vec<LegacyObjectKey>,
) {
    assert_eq!(
        adopt_legacy_schema(config),
        Err(LegacyAdopterError::CensusMismatch {
            missing_objects: expected_missing,
            changed_objects: expected_changed,
            extra_objects: expected_extra,
        })
    );
    assert_lock_released(config);
}

fn assert_unsupported_catalog_and_lock(config: &Config, family: &str) {
    let expected = object_key(LegacyObjectKind::UnsupportedCatalog, "pg_catalog", family);
    assert_eq!(
        adopt_legacy_schema(config),
        Err(LegacyAdopterError::UnsupportedLegacyExtras {
            objects: vec![expected],
        })
    );
    assert_lock_released(config);
}

fn assert_unsupported_extras(config: &Config, objects: Vec<LegacyObjectKey>) {
    assert_eq!(
        adopt_legacy_schema(config),
        Err(LegacyAdopterError::UnsupportedLegacyExtras { objects })
    );
    assert_lock_released(config);
}

fn assert_bounds_and_lock(
    config: &Config,
    resource: LegacyBoundedResource,
    actual: usize,
    max: usize,
) {
    assert_eq!(
        adopt_legacy_schema(config),
        Err(LegacyAdopterError::Bounds {
            resource,
            actual,
            max,
        })
    );
    assert_lock_released(config);
}

fn assert_outcome_and_lock(
    config: &Config,
    expected: &Result<babylon_persistence::LegacyAdoptionReport, LegacyAdopterError>,
) {
    assert_eq!(&adopt_legacy_schema(config), expected);
    assert_lock_released(config);
}

fn assert_lock_released(config: &Config) {
    let mut client = config.connect(NoTls).unwrap();
    let locked: bool = client
        .query_one(
            "SELECT pg_catalog.pg_try_advisory_lock($1)",
            &[&SCHEMA_ADVISORY_LOCK_KEY],
        )
        .unwrap()
        .try_get(0)
        .unwrap();
    assert!(locked);
    let unlocked: bool = client
        .query_one(
            "SELECT pg_catalog.pg_advisory_unlock($1)",
            &[&SCHEMA_ADVISORY_LOCK_KEY],
        )
        .unwrap()
        .try_get(0)
        .unwrap();
    assert!(unlocked);
}

#[derive(Debug, PartialEq, Eq)]
struct AuthoritySnapshot {
    census: Vec<(CensusObjectSnapshot, CensusOverflowSnapshot)>,
    stamps: Vec<(String, i32)>,
    authority_schemas: Vec<String>,
}

type CensusObjectSnapshot = (String, String, String, String);
type CensusOverflowSnapshot = (Option<String>, Option<i64>, Option<i64>);

fn authority_snapshot(client: &mut Client) -> AuthoritySnapshot {
    AuthoritySnapshot {
        census: census_snapshot(client),
        stamps: stamp_snapshot(client),
        authority_schemas: authority_schema_snapshot(client),
    }
}

fn census_snapshot(client: &mut Client) -> Vec<(CensusObjectSnapshot, CensusOverflowSnapshot)> {
    let census_limit = i64::try_from(MAX_LEGACY_CENSUS_ROWS + 1).unwrap();
    let partition_limit = i64::try_from(MAX_LEGACY_PARTITIONS_PER_FAMILY + 1).unwrap();
    let extension_member_limit = i64::try_from(MAX_LEGACY_EXTENSION_MEMBERS + 1).unwrap();
    let extension_dependency_address_limit =
        i64::try_from(MAX_LEGACY_EXTENSION_DEPENDENCY_ADDRESSES + 1).unwrap();
    let sequence_ownership_limit = i64::try_from(MAX_LEGACY_SEQUENCE_OWNERSHIP + 1).unwrap();
    let extension_role_identity_limit =
        i64::try_from(MAX_LEGACY_EXTENSION_ROLE_IDENTITIES + 1).unwrap();
    let census_rows = client
        .query(
            adopter_sql(LegacyAdopterSqlKind::CatalogCensus),
            &[
                &census_limit,
                &partition_limit,
                &extension_member_limit,
                &extension_dependency_address_limit,
                &sequence_ownership_limit,
                &extension_role_identity_limit,
            ],
        )
        .unwrap();
    assert!(census_rows.len() <= MAX_LEGACY_CENSUS_ROWS);
    let mut census = Vec::with_capacity(census_rows.len());
    for row in census_rows.iter().take(MAX_LEGACY_CENSUS_ROWS) {
        census.push((
            (
                row.try_get(0).unwrap(),
                row.try_get(1).unwrap(),
                row.try_get(2).unwrap(),
                row.try_get(3).unwrap(),
            ),
            (
                row.try_get(4).unwrap(),
                row.try_get(5).unwrap(),
                row.try_get(6).unwrap(),
            ),
        ));
    }
    census
}

fn database_digest(snapshot: &AuthoritySnapshot) -> &str {
    snapshot
        .census
        .iter()
        .take(MAX_LEGACY_CENSUS_ROWS)
        .find(|((kind, schema, name, _), _)| {
            kind == "database" && schema == "pg_database" && name == "current_database"
        })
        .map(|((_, _, _, digest), _)| digest.as_str())
        .unwrap()
}

fn census_digest(config: &Config, kind: &str, schema: &str, name: &str) -> String {
    let mut client = config.connect(NoTls).unwrap();
    authority_snapshot(&mut client)
        .census
        .into_iter()
        .take(MAX_LEGACY_CENSUS_ROWS)
        .find(|((row_kind, row_schema, row_name, _), _)| {
            row_kind == kind && row_schema == schema && row_name == name
        })
        .map(|((_, _, _, digest), _)| digest)
        .unwrap()
}

fn raw_extension_member_owner_dependency_count(config: &Config) -> i64 {
    let mut client = config.connect(NoTls).unwrap();
    client
        .query_one(
            "SELECT pg_catalog.count(*) \
             FROM pg_catalog.pg_shdepend AS dependency \
             JOIN pg_catalog.pg_proc AS routine \
               ON dependency.classid = 'pg_catalog.pg_proc'::pg_catalog.regclass \
              AND dependency.objid = routine.oid \
              AND dependency.objsubid = 0 \
             JOIN pg_catalog.pg_namespace AS routine_ns \
               ON routine_ns.oid = routine.pronamespace \
             JOIN pg_catalog.pg_database AS database_row \
               ON database_row.oid = dependency.dbid \
              AND database_row.datname = pg_catalog.current_database() \
             WHERE routine_ns.nspname = 'public' \
               AND routine.proname = 'postgis_version' \
               AND dependency.refclassid = 'pg_catalog.pg_authid'::pg_catalog.regclass \
               AND dependency.deptype = 'o'",
            &[],
        )
        .unwrap()
        .try_get(0)
        .unwrap()
}

fn stamp_snapshot(client: &mut Client) -> Vec<(String, i32)> {
    let row_limit = i64::try_from(MAX_LEGACY_STAMP_ROWS + 1).unwrap();
    let prefix_bytes = 64_i32;
    let rows = client
        .query(
            adopter_sql(LegacyAdopterSqlKind::ReadStamps),
            &[&row_limit, &prefix_bytes],
        )
        .unwrap();
    assert!(rows.len() <= MAX_LEGACY_STAMP_ROWS);
    rows.iter()
        .take(MAX_LEGACY_STAMP_ROWS)
        .map(|row| (row.try_get(0).unwrap(), row.try_get(1).unwrap()))
        .collect()
}

fn authority_schema_snapshot(client: &mut Client) -> Vec<String> {
    let rows = client
        .query(adopter_sql(LegacyAdopterSqlKind::AuthoritySchemas), &[])
        .unwrap();
    assert!(rows.len() <= 2);
    rows.iter()
        .take(2)
        .map(|row| row.try_get(0).unwrap())
        .collect()
}

fn adopter_sql(kind: LegacyAdopterSqlKind) -> &'static str {
    legacy_adopter_sql_statements()
        .iter()
        .take(8)
        .find(|statement| statement.kind() == kind)
        .unwrap()
        .sql()
}

fn quoted_canary_identity(client: &mut Client) -> (String, i32) {
    let row = client
        .query_one(
            "SELECT key, payload FROM \"Quoted Ω\".\"Míxed Table\" ORDER BY key",
            &[],
        )
        .unwrap();
    (row.try_get(0).unwrap(), row.try_get(1).unwrap())
}

fn mutate(config: &Config, sql: &str) {
    let mut client = config.connect(NoTls).unwrap();
    client.batch_execute(sql).unwrap();
}

fn verify_partial_damage_then_separate_repair(config: &Config) {
    run_python_damage(config);
    assert_eq!(
        adopt_legacy_schema(config),
        Err(LegacyAdopterError::StampTableMissing)
    );
    assert_lock_released(config);
    run_python_repair(config);
    assert_lock_released(config);
}

fn run_python_damage(config: &Config) {
    let script = r#"
import os
import psycopg
from babylon.persistence.postgres_schema import POSTGRES_SCHEMA_DDL

dsn = os.environ['PER20_BUILD_DSN']
with psycopg.connect(dsn, autocommit=True) as conn:
    for statement in POSTGRES_SCHEMA_DDL[:8]:
        conn.execute(statement)
    assert conn.execute("SELECT pg_catalog.to_regclass('public._babylon_schema_stamp')").fetchone()[0] is None
"#;
    run_python_child(config, script, "partial autocommit damage");
}

fn run_python_repair(config: &Config) {
    let script = r"
import os
import psycopg
from psycopg_pool import ConnectionPool
from babylon.engine.headless_runner.runner import _apply_migrations
from babylon.persistence.postgres_schema import POSTGRES_SCHEMA_DDL, ensure_ddl_applied

dsn = os.environ['PER20_BUILD_DSN']
with psycopg.connect(dsn, autocommit=True) as conn:
    ensure_ddl_applied(conn, POSTGRES_SCHEMA_DDL)
with ConnectionPool(dsn, min_size=1, max_size=1, open=True) as pool:
    _apply_migrations(pool)
";
    run_python_child(config, script, "surviving Python repair/build");
}

fn run_python_child(config: &Config, script: &str, description: &str) {
    let status = Command::new("timeout")
        .args([
            "--signal=TERM",
            "--kill-after=5s",
            LIVE_TASK_SECONDS,
            "uv",
            "run",
            "python",
            "-c",
            script,
        ])
        .current_dir(repository_root())
        .env("PER20_BUILD_DSN", config_dsn(config))
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .unwrap_or_else(|error| panic!("{description} must launch: {error}"));
    assert!(
        status.success(),
        "{description} must complete within its bound"
    );
}

struct ScratchDatabase {
    name: String,
    admin: Config,
    active: bool,
}

struct BabylonIntelRolePresenceGuard {
    admin: Config,
    initially_present: bool,
    active: bool,
}

struct GlobalMutationGuard {
    connection: Config,
    cleanup_sql: Box<str>,
    active: bool,
}

impl BabylonIntelRolePresenceGuard {
    fn capture(base: &Config) -> Self {
        let admin = admin_config(base);
        let initially_present = try_cluster_role_exists(&admin, "babylon_intel").unwrap();
        Self {
            admin,
            initially_present,
            active: true,
        }
    }

    fn cleanup(mut self) {
        match self.try_cleanup() {
            Ok(()) => self.active = false,
            Err(()) => panic!("babylon_intel presence cleanup must succeed"),
        }
    }

    fn try_cleanup(&self) -> Result<(), ()> {
        let exists = try_cluster_role_exists(&self.admin, "babylon_intel")?;
        if self.initially_present {
            return exists.then_some(()).ok_or(());
        }
        if exists {
            let mut client = self.admin.connect(NoTls).map_err(|_| ())?;
            client
                .batch_execute("DROP ROLE babylon_intel")
                .map_err(|_| ())?;
        }
        (!try_cluster_role_exists(&self.admin, "babylon_intel")?)
            .then_some(())
            .ok_or(())
    }
}

impl Drop for BabylonIntelRolePresenceGuard {
    fn drop(&mut self) {
        if !self.active {
            return;
        }
        if std::thread::panicking() {
            let _unwind_cleanup = self.try_cleanup();
            return;
        }
        match self.try_cleanup() {
            Ok(()) => {
                self.active = false;
                panic!("babylon_intel presence guard requires explicit checked cleanup");
            }
            Err(()) => panic!("babylon_intel presence cleanup failed"),
        }
    }
}

impl GlobalMutationGuard {
    fn apply(base: &Config, apply_sql: &str, cleanup_sql: &str) -> Self {
        assert!(apply_sql.len() <= 1_024);
        assert!(cleanup_sql.len() <= 1_024);
        let connection = base.clone();
        let mut client = connection.connect(NoTls).unwrap();
        client.batch_execute(apply_sql).unwrap();
        drop(client);
        Self {
            connection,
            cleanup_sql: cleanup_sql.into(),
            active: true,
        }
    }

    fn cleanup(mut self) {
        match self.try_cleanup() {
            Ok(()) => self.active = false,
            Err(()) => panic!("global mutation cleanup must succeed"),
        }
    }

    fn try_cleanup(&self) -> Result<(), ()> {
        let mut client = self.connection.connect(NoTls).map_err(|_| ())?;
        client.batch_execute(&self.cleanup_sql).map_err(|_| ())
    }
}

impl Drop for GlobalMutationGuard {
    fn drop(&mut self) {
        if !self.active {
            return;
        }
        if std::thread::panicking() {
            let _unwind_cleanup = self.try_cleanup();
            return;
        }
        match self.try_cleanup() {
            Ok(()) => {
                self.active = false;
                panic!("global mutation guard requires explicit checked cleanup");
            }
            Err(()) => panic!("global mutation cleanup failed"),
        }
    }
}

impl ScratchDatabase {
    fn empty(base: &Config, label: &str, owner: &str) -> Self {
        let name = scratch_name(label);
        let admin = admin_config(base);
        let mut client = admin.connect(NoTls).unwrap();
        client
            .batch_execute(
                format!(
                    "CREATE DATABASE {} OWNER {} TEMPLATE template1",
                    quote_identifier(&name),
                    quote_identifier(owner)
                )
                .as_str(),
            )
            .unwrap();
        Self {
            name,
            admin,
            active: true,
        }
    }

    fn from_template(base: &Config, template: &str, label: &str) -> Self {
        let name = scratch_name(label);
        let admin = admin_config(base);
        let mut client = admin.connect(NoTls).unwrap();
        client
            .batch_execute(
                format!(
                    "CREATE DATABASE {} WITH TEMPLATE {}",
                    quote_identifier(&name),
                    quote_identifier(template)
                )
                .as_str(),
            )
            .unwrap();
        Self {
            name,
            admin,
            active: true,
        }
    }

    fn name(&self) -> &str {
        &self.name
    }

    fn config(&self, base: &Config) -> Config {
        let mut config = base.clone();
        config.dbname(&self.name);
        config
    }

    fn config_as(&self, base: &Config, user: &str, password: &str) -> Config {
        let mut config = self.config(base);
        config.user(user).password(password);
        config
    }

    fn cleanup(mut self) {
        match self.try_cleanup() {
            Ok(()) => self.active = false,
            Err(()) => panic!("scratch database cleanup must succeed"),
        }
    }

    fn try_cleanup(&self) -> Result<(), ()> {
        let mut client = self.admin.connect(NoTls).map_err(|_| ())?;
        let sql = format!(
            "DROP DATABASE IF EXISTS {} WITH (FORCE)",
            quote_identifier(&self.name)
        );
        client.batch_execute(&sql).map_err(|_| ())
    }
}

impl Drop for ScratchDatabase {
    fn drop(&mut self) {
        if !self.active {
            return;
        }
        if std::thread::panicking() {
            let _unwind_cleanup = self.try_cleanup();
            return;
        }
        match self.try_cleanup() {
            Ok(()) => self.active = false,
            Err(()) => panic!("scratch database cleanup failed"),
        }
    }
}

struct ScratchRole {
    name: String,
    admin: Config,
    active: bool,
}

impl ScratchRole {
    fn create(base: &Config) -> Self {
        let role = Self::create_without_event_trigger_set(base);
        let mut client = role.admin.connect(NoTls).unwrap();
        client
            .batch_execute(
                format!(
                    "GRANT SET ON PARAMETER event_triggers TO {}",
                    quote_identifier(&role.name)
                )
                .as_str(),
            )
            .unwrap();
        drop(client);
        role
    }

    fn create_without_event_trigger_set(base: &Config) -> Self {
        let name = scratch_name("owner");
        let admin = admin_config(base);
        let mut client = admin.connect(NoTls).unwrap();
        client
            .batch_execute(
                format!(
                    "CREATE ROLE {} LOGIN PASSWORD '{}' NOSUPERUSER NOCREATEDB NOCREATEROLE",
                    quote_identifier(&name),
                    OWNER_PASSWORD
                )
                .as_str(),
            )
            .unwrap();
        Self {
            name,
            admin,
            active: true,
        }
    }

    fn name(&self) -> &str {
        &self.name
    }

    fn cleanup(mut self) {
        match self.try_cleanup() {
            Ok(()) => self.active = false,
            Err(error) => panic!(
                "scratch role cleanup must succeed for {}: {error}",
                self.name
            ),
        }
    }

    fn try_cleanup(&self) -> Result<(), postgres::Error> {
        let mut client = self.admin.connect(NoTls)?;
        let role = quote_identifier(&self.name);
        let sql = format!(
            "REVOKE SET ON PARAMETER event_triggers FROM {role}; DROP ROLE IF EXISTS {role}"
        );
        client.batch_execute(&sql)
    }
}

impl Drop for ScratchRole {
    fn drop(&mut self) {
        if !self.active {
            return;
        }
        if std::thread::panicking() {
            let _unwind_cleanup = self.try_cleanup();
            return;
        }
        match self.try_cleanup() {
            Ok(()) => self.active = false,
            Err(error) => panic!("scratch role cleanup failed for {}: {error}", self.name),
        }
    }
}

fn object_key(kind: LegacyObjectKind, schema: &str, name: &str) -> LegacyObjectKey {
    LegacyObjectKey::new(kind, schema, name).unwrap()
}

fn database_key(kind: LegacyObjectKind, schema: &str, name: &str) -> LegacyObjectKey {
    LegacyObjectKey::from_database(kind, schema, name).unwrap()
}

fn admin_config(base: &Config) -> Config {
    let mut admin = base.clone();
    admin.dbname("postgres");
    admin
}

fn database_user(config: &Config) -> &str {
    config
        .get_user()
        .expect("DSN must name an administrative user")
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum DisposableHarnessRejection {
    Target,
    User,
    Database,
    Canary,
    Connection,
    Runtime,
}

fn validate_disposable_harness_target(
    config: &Config,
    canary: Option<&str>,
) -> Result<(), DisposableHarnessRejection> {
    validate_legacy_connection_target(config).map_err(|_| DisposableHarnessRejection::Target)?;
    let target_is_exact = matches!(
        config.get_hosts(),
        [Host::Tcp(host)] if host == "127.0.0.1"
    ) && config.get_hostaddrs().is_empty()
        && config.get_ports().len() == 1;
    if !target_is_exact {
        return Err(DisposableHarnessRejection::Target);
    }
    if config.get_user() != Some("test") {
        return Err(DisposableHarnessRejection::User);
    }
    if config.get_dbname() != Some("postgres") {
        return Err(DisposableHarnessRejection::Database);
    }
    let canary = canary.ok_or(DisposableHarnessRejection::Canary)?;
    let valid_canary = canary.len() == 32
        && canary
            .bytes()
            .take(33)
            .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'));
    valid_canary
        .then_some(())
        .ok_or(DisposableHarnessRejection::Canary)
}

fn preflight_disposable_harness(config: &Config) {
    let canary = std::env::var(DISPOSABLE_CANARY_ENV)
        .map_err(|_| DisposableHarnessRejection::Canary)
        .and_then(|value| {
            validate_disposable_harness_target(config, Some(&value))?;
            Ok(value)
        })
        .unwrap_or_else(|_| panic!("disposable harness target/canary preflight failed"));
    let mut bounded = config.clone();
    bounded
        .connect_timeout(LEGACY_ADOPTER_CONNECT_TIMEOUT)
        .tcp_user_timeout(LEGACY_ADOPTER_TCP_USER_TIMEOUT)
        .options(LEGACY_ADOPTER_STARTUP_OPTIONS);
    let mut client = bounded
        .connect(NoTls)
        .map_err(|_| DisposableHarnessRejection::Connection)
        .unwrap_or_else(|_| panic!("disposable harness connection preflight failed"));
    let row = client
        .query_one(
            "SELECT pg_catalog.current_setting('server_version_num'), \
                    pg_catalog.current_setting('babylon.per20_disposable', true), \
                    current_user::pg_catalog.text, pg_catalog.current_database(), \
                    role_row.rolsuper, \
                    (SELECT available.default_version FROM pg_catalog.pg_available_extensions \
                     AS available WHERE available.name = 'postgis'), \
                    (SELECT available.default_version FROM pg_catalog.pg_available_extensions \
                     AS available WHERE available.name = 'vector'), \
                    (SELECT available.default_version FROM pg_catalog.pg_available_extensions \
                     AS available WHERE available.name = 'h3'), \
                    pg_catalog.current_setting('transaction_read_only') \
             FROM pg_catalog.pg_roles AS role_row WHERE role_row.rolname = current_user",
            &[],
        )
        .map_err(|_| DisposableHarnessRejection::Runtime)
        .unwrap_or_else(|_| panic!("disposable harness runtime query failed"));
    let runtime = (
        row.try_get::<_, String>(0)
            .map_err(|_| DisposableHarnessRejection::Runtime),
        row.try_get::<_, Option<String>>(1)
            .map_err(|_| DisposableHarnessRejection::Runtime),
        row.try_get::<_, String>(2)
            .map_err(|_| DisposableHarnessRejection::Runtime),
        row.try_get::<_, String>(3)
            .map_err(|_| DisposableHarnessRejection::Runtime),
        row.try_get::<_, bool>(4)
            .map_err(|_| DisposableHarnessRejection::Runtime),
        row.try_get::<_, Option<String>>(5)
            .map_err(|_| DisposableHarnessRejection::Runtime),
        row.try_get::<_, Option<String>>(6)
            .map_err(|_| DisposableHarnessRejection::Runtime),
        row.try_get::<_, Option<String>>(7)
            .map_err(|_| DisposableHarnessRejection::Runtime),
        row.try_get::<_, String>(8)
            .map_err(|_| DisposableHarnessRejection::Runtime),
    );
    assert_eq!(
        runtime,
        (
            Ok("170011".into()),
            Ok(Some(canary)),
            Ok("test".into()),
            Ok("postgres".into()),
            Ok(true),
            Ok(Some("3.5.7".into())),
            Ok(Some("0.8.5".into())),
            Ok(Some("4.5.0".into())),
            Ok("on".into()),
        ),
        "disposable harness runtime profile must match the pinned oracle"
    );
}

fn config_from_env() -> Config {
    let acknowledgement = std::env::var(DISPOSABLE_ACK_ENV)
        .expect("BABYLON_LEGACY_ADOPTER_DISPOSABLE_ACK must be set");
    assert_eq!(
        acknowledgement, DISPOSABLE_ACK_VALUE,
        "BABYLON_LEGACY_ADOPTER_DISPOSABLE_ACK must exactly acknowledge destructive cleanup"
    );
    let dsn = std::env::var(DSN_ENV).expect("BABYLON_LEGACY_ADOPTER_TEST_DSN must be set");
    let canary = std::env::var(DISPOSABLE_CANARY_ENV)
        .expect("BABYLON_LEGACY_ADOPTER_DISPOSABLE_CANARY must be set");
    let config = Config::from_str(&dsn).expect("BABYLON_LEGACY_ADOPTER_TEST_DSN must parse");
    validate_disposable_harness_target(&config, Some(&canary))
        .unwrap_or_else(|_| panic!("disposable harness target/canary validation failed"));
    config
}

fn assert_no_scratch_residue(base: &Config) {
    let mut client = admin_config(base).connect(NoTls).unwrap();
    let rows = client
        .query(
            "SELECT residue.kind, residue.name FROM ( \
             SELECT 'database'::pg_catalog.text AS kind, d.datname::pg_catalog.text AS name \
             FROM pg_catalog.pg_database AS d \
             WHERE d.datname LIKE 'per20\\_%' ESCAPE '\\' \
             UNION ALL \
             SELECT 'role'::pg_catalog.text, r.rolname::pg_catalog.text \
             FROM pg_catalog.pg_roles AS r \
             WHERE r.rolname LIKE 'per20\\_%' ESCAPE '\\' \
                OR r.rolname LIKE 'yyyy\\_per20\\_%' ESCAPE '\\' \
                OR r.rolname LIKE 'zzzz\\_per20\\_%' ESCAPE '\\' \
             ) AS residue ORDER BY residue.kind, residue.name LIMIT 1",
            &[],
        )
        .unwrap();
    assert!(
        rows.is_empty(),
        "disposable endpoint must contain no PER-20 scratch database or role residue"
    );
}

fn try_cluster_role_exists(admin: &Config, role_name: &str) -> Result<bool, ()> {
    admin
        .connect(NoTls)
        .map_err(|_| ())?
        .query_one(
            "SELECT EXISTS( \
             SELECT 1 FROM pg_catalog.pg_roles AS role_row WHERE role_row.rolname = $1 \
             )",
            &[&role_name],
        )
        .map_err(|_| ())?
        .try_get(0)
        .map_err(|_| ())
}

fn config_dsn(config: &Config) -> String {
    let host = match config.get_hosts().first() {
        Some(Host::Tcp(host)) => host.as_str(),
        _ => panic!("live adopter test requires one TCP host"),
    };
    let port = config.get_ports().first().copied().unwrap_or(5432);
    let user = config.get_user().expect("test config user");
    let password = std::str::from_utf8(config.get_password().expect("test config password"))
        .expect("test password must be UTF-8");
    let dbname = config.get_dbname().expect("test config database");
    format!("host={host} port={port} dbname={dbname} user={user} password={password}")
}

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../..")
        .canonicalize()
        .unwrap()
}

fn scratch_name(label: &str) -> String {
    format!("per20_{label}_{}", unique_suffix())
}

fn unique_suffix() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos()
}

fn quote_identifier(identifier: &str) -> String {
    assert!(identifier.len() <= 63);
    assert!(identifier
        .bytes()
        .all(|byte| matches!(byte, b'a'..=b'z' | b'0'..=b'9' | b'_')));
    format!("\"{identifier}\"")
}
