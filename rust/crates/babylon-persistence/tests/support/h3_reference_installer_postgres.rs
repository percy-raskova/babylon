//! Live `PostgreSQL` contracts for the representative H3 cohort installer.

use super::{
    assert_lock_released, authority_snapshot, database_user, repository_root, AuthoritySnapshot,
    ScratchDatabase, LIVE_TASK_SECONDS, MAX_LEGACY_CENSUS_ROWS, OWNER_PASSWORD,
};
use babylon_persistence::{
    adopt_legacy_schema, build_representative_h3_cohort_v1, compiled_schema_migrations,
    install_representative_h3_cohort, migrate_schema_epoch, request_rust_writer_authority,
    H3CellId, H3ReferenceCohort, H3ReferenceInstallConflict, H3ReferenceInstallDisposition,
    H3ReferenceInstallError, H3ReferenceInstallOperation, H3ReferenceInstallReport,
    LegacyAdopterError, RefDigest, RustWriterAuthorityError, SchemaEpochError, SchemaEpochOrigin,
    SCHEMA_ADVISORY_LOCK_KEY,
};
use postgres::{Config, NoTls};
use std::mem::size_of;
use std::path::PathBuf;
use std::process::{Command, Stdio};

const SOURCE_FIXTURE: &[u8] = include_bytes!("../fixtures/h3_reference_source_v1.bin");
const SOURCE_DOMAIN: &[u8] = b"babylon.h3.reference-source.v1\0";
const SOURCE_COUNT: usize = 48_764;
const CLOSURE_COUNT: usize = 59_849;
const MAX_COHORT_SNAPSHOT_ROWS: usize = 2;
const MAX_EPOCH_CATALOG_ROWS: usize = 16;
const MAX_LEDGER_ROWS: usize = 3;
const ARTIFACT_DIGEST_HEX: &str =
    "e60d93a43d6c66e84f1e53ecaf633af5911bd5b48b0ef0ad6a012f6d9f5b13a9";
const REF_DIGEST_HEX: &str = "92b21ff325bde67f26565f52882d3664daacd6d51423f2a588344da012fd4161";
const BRIDGE_PARQUET_ENV: &str = "BABYLON_PER62_BRIDGE_PARQUET";
const LAND_MASK_PARQUET_ENV: &str = "BABYLON_PER62_LAND_MASK_PARQUET";
const P27_ARCHIVE_ROOT_ENV: &str = "BABYLON_PER62_P27_ARCHIVE_ROOT";

#[derive(Debug, Clone, PartialEq, Eq)]
struct ReferenceSnapshot {
    h3_cell_count: i64,
    cohort_count: i64,
    membership_count: i64,
    direct_membership_count: i64,
    derived_membership_count: i64,
    cohorts: Vec<CohortSnapshot>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct CohortSnapshot {
    ref_digest: String,
    format_version: i16,
    artifact_name: String,
    artifact_manifest_version: String,
    artifact_digest: String,
    source_digest: String,
    source_r5_digest: String,
    source_r7_digest: String,
    closure_digest: String,
    membership_digest: String,
    direct_cell_count: i64,
    derived_ancestor_count: i64,
    closure_cell_count: i64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct V2Snapshot {
    catalog: Vec<(String, String)>,
    ledger: Vec<(i64, String)>,
    h3_cell_count: i64,
}

pub(super) fn verify_h3_reference_installer(base: &Config, legacy_template: &str, owner: &str) {
    let cohort = representative_cohort();
    verify_connection_failure_redacts_credentials(&cohort);
    verify_frozen_legacy_migration_install(base, legacy_template, &cohort);
    verify_exact_vthree_install_and_retry(base, &cohort);
    verify_fresh_refusal(base, &cohort);
    verify_exact_vtwo_refusal(base, &cohort);
    verify_lock_refusal(base, &cohort);
    verify_non_owner_refusal(base, owner, &cohort);
    verify_installed_state_conflicts(base, &cohort);
    verify_preflight_artifact_identity_conflict(base, &cohort);
}

pub(super) fn verify_h3_reference_release_equivalence(base: &Config) {
    let repository = repository_root();
    let bridge = required_path(BRIDGE_PARQUET_ENV);
    let land_mask = required_path(LAND_MASK_PARQUET_ENV);
    let p27_root = required_path(P27_ARCHIVE_ROOT_ENV);
    let verifier = repository.join("tools/verify_h3_reference_release.py");
    let fixture = repository
        .join("rust/crates/babylon-persistence/tests/fixtures/h3_reference_source_v1.bin");
    let status = Command::new("timeout")
        .args([
            "--signal=TERM",
            "--kill-after=5s",
            LIVE_TASK_SECONDS,
            "uv",
            "run",
            "--frozen",
            "--no-sync",
            "python",
        ])
        .arg(verifier)
        .arg("--bridge")
        .arg(bridge)
        .arg("--land-mask")
        .arg(land_mask)
        .arg("--p27-archive-root")
        .arg(p27_root)
        .arg("--source-fixture")
        .arg(fixture)
        .current_dir(&repository)
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()
        .expect("PER-62 release verifier must launch");
    assert!(status.success(), "PER-62 release verifier must succeed");

    let cohort = representative_cohort();
    let (database, config) = exact_vthree_database(base, "h3_release_equivalence");
    let installed = install_representative_h3_cohort(&config, &cohort)
        .expect("release-proved cohort must install into exact epoch 3");
    assert_exact_report(&installed, H3ReferenceInstallDisposition::Installed, 1);
    let installed_snapshot = reference_snapshot(&config);
    assert_eq!(installed_snapshot, expected_installed_snapshot());
    let retry = install_representative_h3_cohort(&config, &cohort)
        .expect("release-proved cohort retry must be idempotent");
    assert_exact_report(&retry, H3ReferenceInstallDisposition::AlreadyPresent, 0);
    assert_eq!(reference_snapshot(&config), installed_snapshot);
    assert_lock_released(&config);
    database.cleanup();
}

fn required_path(name: &'static str) -> PathBuf {
    std::env::var_os(name).map_or_else(
        || panic!("{name} must name the pinned PER-62 artifact"),
        PathBuf::from,
    )
}

fn verify_frozen_legacy_migration_install(
    base: &Config,
    legacy_template: &str,
    cohort: &H3ReferenceCohort,
) {
    let database = ScratchDatabase::from_template(base, legacy_template, "h3_installer_legacy");
    let config = database.config(base);
    let adoption = adopt_legacy_schema(&config).expect("frozen legacy database must adopt");
    assert_eq!(
        (adoption.expected_objects, adoption.matched_objects),
        (102, 102)
    );
    assert!(adoption.transaction_verified);
    let legacy_before = frozen_legacy_snapshot(&config);
    assert!(legacy_before.authority_schemas.is_empty());
    assert_writer_authority_refused();

    let migration = migrate_schema_epoch(&config).expect("adopted legacy database must migrate");
    assert_eq!(migration.origin, SchemaEpochOrigin::ExactLegacy);
    assert_eq!((migration.prior_applied, migration.final_applied), (0, 3));
    assert_eq!(migration.applied_versions.len(), 3);
    assert_eq!(migration.legacy_adoption.as_ref(), Some(&adoption));
    assert_frozen_legacy_retained(&config, &legacy_before);

    let installed = install_representative_h3_cohort(&config, cohort)
        .expect("migrated frozen legacy database must install the exact cohort");
    assert_exact_report(&installed, H3ReferenceInstallDisposition::Installed, 1);
    let installed_snapshot = reference_snapshot(&config);
    assert_eq!(installed_snapshot, expected_installed_snapshot());
    assert_frozen_legacy_retained(&config, &legacy_before);

    let retry = install_representative_h3_cohort(&config, cohort)
        .expect("identical legacy-migrated cohort install must be idempotent");
    assert_exact_report(&retry, H3ReferenceInstallDisposition::AlreadyPresent, 0);
    assert_eq!(reference_snapshot(&config), installed_snapshot);
    assert_frozen_legacy_retained(&config, &legacy_before);
    assert_writer_authority_refused();
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_exact_vthree_install_and_retry(base: &Config, cohort: &H3ReferenceCohort) {
    let (database, config) = exact_vthree_database(base, "h3_installer_exact");
    assert_writer_authority_refused();

    let installed = install_representative_h3_cohort(&config, cohort)
        .expect("exact epoch 3 must install the representative cohort");
    assert_exact_report(&installed, H3ReferenceInstallDisposition::Installed, 1);
    let before_retry = reference_snapshot(&config);
    assert_eq!(before_retry, expected_installed_snapshot());

    let retry = install_representative_h3_cohort(&config, cohort)
        .expect("an exact installed cohort must be idempotent");
    assert_exact_report(&retry, H3ReferenceInstallDisposition::AlreadyPresent, 0);
    assert_eq!(reference_snapshot(&config), before_retry);
    assert_writer_authority_refused();
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_connection_failure_redacts_credentials(cohort: &H3ReferenceCohort) {
    const PASSWORD: &str = "do-not-leak-h3-password";

    let mut unavailable = Config::new();
    unavailable.host("127.0.0.1").port(1).password(PASSWORD);
    let error = install_representative_h3_cohort(&unavailable, cohort)
        .expect_err("the loopback discard port must refuse the installer connection");

    match &error {
        H3ReferenceInstallError::Database {
            operation: H3ReferenceInstallOperation::Connect,
            diagnostic,
        } => assert!(diagnostic.server().is_none()),
        _ => panic!("connection refusal must remain a redacted typed database error"),
    }
    assert!(!format!("{error:?}").contains(PASSWORD));
    assert!(!format!("{error}").contains(PASSWORD));
}

fn verify_fresh_refusal(base: &Config, cohort: &H3ReferenceCohort) {
    let database = ScratchDatabase::empty(base, "h3_installer_fresh", database_user(base));
    let config = database.config(base);
    let before = babylon_catalog_snapshot(&config);
    match install_representative_h3_cohort(&config, cohort) {
        Err(H3ReferenceInstallError::ExactSchemaEpochRequired {
            expected,
            actual,
            origin,
        }) => {
            assert_eq!(expected, 3);
            assert_eq!(actual, 0);
            assert_eq!(origin, SchemaEpochOrigin::Fresh);
        }
        _ => panic!("fresh database must refuse without migration"),
    }
    assert_eq!(babylon_catalog_snapshot(&config), before);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_exact_vtwo_refusal(base: &Config, cohort: &H3ReferenceCohort) {
    let database = ScratchDatabase::empty(base, "h3_installer_vtwo", database_user(base));
    let config = database.config(base);
    establish_vtwo_prefix(&config);
    let before = vtwo_snapshot(&config);
    match install_representative_h3_cohort(&config, cohort) {
        Err(H3ReferenceInstallError::ExactSchemaEpochRequired {
            expected,
            actual,
            origin,
        }) => {
            assert_eq!(expected, 3);
            assert_eq!(actual, 2);
            assert_eq!(origin, SchemaEpochOrigin::ExistingRustPrefix);
        }
        _ => panic!("exact epoch 2 must refuse without migration"),
    }
    assert_eq!(vtwo_snapshot(&config), before);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_lock_refusal(base: &Config, cohort: &H3ReferenceCohort) {
    let (database, config) = exact_vthree_database(base, "h3_installer_lock");
    let mut blocker = config.connect(NoTls).unwrap();
    let locked: bool = blocker
        .query_one(
            "SELECT pg_catalog.pg_try_advisory_lock($1)",
            &[&SCHEMA_ADVISORY_LOCK_KEY],
        )
        .unwrap()
        .get(0);
    assert!(locked);
    let before = reference_snapshot(&config);
    assert!(matches!(
        install_representative_h3_cohort(&config, cohort),
        Err(H3ReferenceInstallError::Lock(
            LegacyAdopterError::LockUnavailable
        ))
    ));
    assert_eq!(reference_snapshot(&config), before);
    let unlocked: bool = blocker
        .query_one(
            "SELECT pg_catalog.pg_advisory_unlock($1)",
            &[&SCHEMA_ADVISORY_LOCK_KEY],
        )
        .unwrap()
        .get(0);
    assert!(unlocked);
    drop(blocker);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_non_owner_refusal(base: &Config, owner: &str, cohort: &H3ReferenceCohort) {
    let database = ScratchDatabase::empty(base, "h3_installer_non_owner", owner);
    let owner_config = database.config_as(base, owner, OWNER_PASSWORD);
    let report =
        migrate_schema_epoch(&owner_config).expect("database owner must establish epoch 3");
    assert_eq!(report.final_applied, 3);

    let admin_config = database.config(base);
    let before = reference_snapshot(&admin_config);
    assert_eq!(
        install_representative_h3_cohort(&admin_config, cohort),
        Err(H3ReferenceInstallError::SchemaEpoch(
            SchemaEpochError::CurrentUserIsNotDatabaseOwner,
        )),
        "non-owner installer call must refuse through the exact owner check"
    );
    assert_eq!(reference_snapshot(&admin_config), before);
    assert_lock_released(&admin_config);
    database.cleanup();
}

fn verify_preflight_artifact_identity_conflict(base: &Config, cohort: &H3ReferenceCohort) {
    let (database, config) = exact_vthree_database(base, "h3_installer_preflight_conflict");
    seed_conflicting_artifact_identity(&config);
    let before = reference_snapshot(&config);
    assert_eq!((before.h3_cell_count, before.cohort_count), (0, 1));
    assert_eq!(
        install_representative_h3_cohort(&config, cohort),
        Err(H3ReferenceInstallError::Conflict {
            component: H3ReferenceInstallConflict::ArtifactIdentity,
        })
    );
    assert_eq!(reference_snapshot(&config), before);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_installed_state_conflicts(base: &Config, cohort: &H3ReferenceCohort) {
    let (template, config) = exact_vthree_database(base, "h3_installer_mutation_template");
    let installed = install_representative_h3_cohort(&config, cohort)
        .expect("mutation template must contain the exact installed cohort");
    assert_exact_report(&installed, H3ReferenceInstallDisposition::Installed, 1);
    assert_eq!(reference_snapshot(&config), expected_installed_snapshot());

    verify_installed_mutation_refusal(
        base,
        template.name(),
        cohort,
        "h3_installer_header_metadata",
        mutate_header_metadata,
        H3ReferenceInstallConflict::CohortHeader,
    );
    verify_installed_mutation_refusal(
        base,
        template.name(),
        cohort,
        "h3_installer_header_count",
        mutate_header_count,
        H3ReferenceInstallConflict::CohortHeader,
    );
    verify_installed_mutation_refusal(
        base,
        template.name(),
        cohort,
        "h3_installer_missing_membership",
        mutate_missing_membership,
        H3ReferenceInstallConflict::Membership,
    );
    verify_installed_mutation_refusal(
        base,
        template.name(),
        cohort,
        "h3_installer_changed_origin",
        mutate_membership_origin,
        H3ReferenceInstallConflict::Membership,
    );
    verify_installed_mutation_refusal(
        base,
        template.name(),
        cohort,
        "h3_installer_orphan_membership",
        mutate_orphan_membership,
        H3ReferenceInstallConflict::Membership,
    );
    assert_lock_released(&config);
    template.cleanup();
}

fn verify_installed_mutation_refusal(
    base: &Config,
    template: &str,
    cohort: &H3ReferenceCohort,
    label: &str,
    mutate: fn(&Config),
    expected_component: H3ReferenceInstallConflict,
) {
    let database = ScratchDatabase::from_template(base, template, label);
    let config = database.config(base);
    let exact = reference_snapshot(&config);
    assert_eq!(exact, expected_installed_snapshot());
    mutate(&config);
    let conflicted = reference_snapshot(&config);
    assert_ne!(conflicted, exact);
    assert_eq!(
        install_representative_h3_cohort(&config, cohort),
        Err(H3ReferenceInstallError::Conflict {
            component: expected_component,
        }),
        "installed mutation must produce its typed conflict: {label}"
    );
    assert_eq!(
        reference_snapshot(&config),
        conflicted,
        "conflict refusal must not write: {label}"
    );
    assert_lock_released(&config);
    database.cleanup();
}

fn mutate_header_metadata(config: &Config) {
    let ref_digest = digest(REF_DIGEST_HEX);
    let mut client = config.connect(NoTls).unwrap();
    let changed = client
        .execute(
            "UPDATE babylon_ref.h3_reference_cohort \
             SET artifact_name = 'changed_h3.parquet' WHERE ref_digest = $1",
            &[&ref_digest.as_bytes().as_slice()],
        )
        .unwrap();
    assert_eq!(changed, 1);
}

fn mutate_header_count(config: &Config) {
    let ref_digest = digest(REF_DIGEST_HEX);
    let mut client = config.connect(NoTls).unwrap();
    let changed = client
        .execute(
            "UPDATE babylon_ref.h3_reference_cohort \
             SET direct_cell_count = direct_cell_count + 1, \
                 derived_ancestor_count = derived_ancestor_count - 1 \
             WHERE ref_digest = $1",
            &[&ref_digest.as_bytes().as_slice()],
        )
        .unwrap();
    assert_eq!(changed, 1);
}

fn mutate_missing_membership(config: &Config) {
    let ref_digest = digest(REF_DIGEST_HEX);
    let mut client = config.connect(NoTls).unwrap();
    let changed = client
        .execute(
            "DELETE FROM babylon_ref.h3_reference_membership \
             WHERE ref_digest = $1 AND cell_id = ( \
                 SELECT cell_id FROM babylon_ref.h3_reference_membership \
                 WHERE ref_digest = $1 AND origin = 1 ORDER BY cell_id LIMIT 1 \
             )",
            &[&ref_digest.as_bytes().as_slice()],
        )
        .unwrap();
    assert_eq!(changed, 1);
}

fn mutate_membership_origin(config: &Config) {
    let ref_digest = digest(REF_DIGEST_HEX);
    let mut client = config.connect(NoTls).unwrap();
    let changed = client
        .execute(
            "UPDATE babylon_ref.h3_reference_membership SET origin = 2 \
             WHERE ref_digest = $1 AND cell_id = ( \
                 SELECT cell_id FROM babylon_ref.h3_reference_membership \
                 WHERE ref_digest = $1 AND origin = 1 ORDER BY cell_id LIMIT 1 \
             )",
            &[&ref_digest.as_bytes().as_slice()],
        )
        .unwrap();
    assert_eq!(changed, 1);
}

fn mutate_orphan_membership(config: &Config) {
    let ref_digest = digest(REF_DIGEST_HEX);
    let orphan_cell_id = 1_i64;
    let mut client = config.connect(NoTls).unwrap();
    let mut transaction = client.transaction().unwrap();
    let exists: bool = transaction
        .query_one(
            "SELECT EXISTS (SELECT 1 FROM babylon_ref.h3_cell WHERE cell_id = $1)",
            &[&orphan_cell_id],
        )
        .unwrap()
        .get(0);
    assert!(!exists);
    transaction
        .batch_execute("SET LOCAL session_replication_role = replica")
        .unwrap();
    let deleted = transaction
        .execute(
            "DELETE FROM babylon_ref.h3_reference_membership \
             WHERE ref_digest = $1 AND cell_id = ( \
                 SELECT cell_id FROM babylon_ref.h3_reference_membership \
                 WHERE ref_digest = $1 AND origin = 1 ORDER BY cell_id LIMIT 1 \
             )",
            &[&ref_digest.as_bytes().as_slice()],
        )
        .unwrap();
    assert_eq!(deleted, 1);
    let inserted = transaction
        .execute(
            "INSERT INTO babylon_ref.h3_reference_membership (ref_digest, cell_id, origin) \
             VALUES ($1, $2, 2)",
            &[&ref_digest.as_bytes().as_slice(), &orphan_cell_id],
        )
        .unwrap();
    assert_eq!(inserted, 1);
    transaction.commit().unwrap();
}

fn frozen_legacy_snapshot(config: &Config) -> AuthoritySnapshot {
    let mut client = config.connect(NoTls).unwrap();
    authority_snapshot(&mut client)
}

fn assert_frozen_legacy_retained(config: &Config, expected: &AuthoritySnapshot) {
    let actual = frozen_legacy_snapshot(config);
    assert_eq!(actual.stamps, expected.stamps);
    assert_eq!(
        actual.authority_schemas,
        vec!["babylon_ref".to_owned(), "babylon_state".to_owned()]
    );
    assert!(expected.census.len() <= MAX_LEGACY_CENSUS_ROWS);
    assert!(actual.census.len() <= MAX_LEGACY_CENSUS_ROWS);
    for expected_row in expected.census.iter().take(MAX_LEGACY_CENSUS_ROWS) {
        assert!(
            actual
                .census
                .iter()
                .take(MAX_LEGACY_CENSUS_ROWS)
                .any(|actual_row| actual_row == expected_row),
            "migration or install changed frozen legacy object {expected_row:?}"
        );
    }
}

fn assert_exact_report(
    report: &H3ReferenceInstallReport,
    disposition: H3ReferenceInstallDisposition,
    commit_attempts: usize,
) {
    assert_eq!(report.disposition(), disposition);
    assert_eq!(report.ref_digest(), digest(REF_DIGEST_HEX));
    assert_eq!(report.artifact_digest(), digest(ARTIFACT_DIGEST_HEX));
    assert_eq!(report.format_version(), 1);
    assert_eq!(report.artifact_name(), "bridge_county_h3.parquet");
    assert_eq!(report.artifact_manifest_version(), "2.0.0");
    assert_eq!(report.direct_cell_count(), SOURCE_COUNT);
    assert_eq!(report.derived_ancestor_count(), 11_085);
    assert_eq!(report.closure_cell_count(), CLOSURE_COUNT);
    assert_eq!(report.commit_attempts(), commit_attempts);
}

fn exact_vthree_database(base: &Config, label: &str) -> (ScratchDatabase, Config) {
    let database = ScratchDatabase::empty(base, label, database_user(base));
    let config = database.config(base);
    let report = migrate_schema_epoch(&config).expect("fresh database must reach exact epoch 3");
    assert_eq!(report.origin, SchemaEpochOrigin::Fresh);
    assert_eq!((report.prior_applied, report.final_applied), (0, 3));
    assert_eq!(report.applied_versions.len(), 3);
    (database, config)
}

fn establish_vtwo_prefix(config: &Config) {
    let compiled = compiled_schema_migrations().expect("compiled migration registry must validate");
    let mut client = config.connect(NoTls).unwrap();
    let mut transaction = client.transaction().unwrap();
    for migration in compiled.iter().take(2) {
        let version = migration.version().as_i64();
        let checksum = migration.checksum();
        let checksum_bytes = checksum.as_bytes().as_slice();
        transaction.batch_execute(migration.sql()).unwrap();
        transaction
            .execute(
                "INSERT INTO babylon_state.schema_migration (version, checksum) VALUES ($1, $2)",
                &[&version, &checksum_bytes],
            )
            .unwrap();
    }
    transaction.commit().unwrap();
}

fn seed_conflicting_artifact_identity(config: &Config) {
    let mut client = config.connect(NoTls).unwrap();
    client
        .batch_execute(
            "INSERT INTO babylon_ref.h3_reference_cohort ( \
                 ref_digest, format_version, artifact_name, artifact_manifest_version, \
                 artifact_digest, source_digest, source_r5_digest, source_r7_digest, \
                 closure_digest, membership_digest, direct_cell_count, \
                 derived_ancestor_count, closure_cell_count \
             ) VALUES ( \
                 decode(repeat('11', 32), 'hex'), 1, 'bridge_county_h3.parquet', '2.0.0', \
                 decode('e60d93a43d6c66e84f1e53ecaf633af5911bd5b48b0ef0ad6a012f6d9f5b13a9', 'hex'), \
                 decode(repeat('22', 32), 'hex'), decode(repeat('33', 32), 'hex'), \
                 decode(repeat('44', 32), 'hex'), decode(repeat('55', 32), 'hex'), \
                 decode(repeat('66', 32), 'hex'), 1, 0, 1 \
             )",
        )
        .unwrap();
}

fn reference_snapshot(config: &Config) -> ReferenceSnapshot {
    let mut client = config.connect(NoTls).unwrap();
    let counts = client
        .query_one(
            "SELECT (SELECT pg_catalog.count(*) FROM babylon_ref.h3_cell), \
                    (SELECT pg_catalog.count(*) FROM babylon_ref.h3_reference_cohort), \
                    (SELECT pg_catalog.count(*) FROM babylon_ref.h3_reference_membership), \
                    (SELECT pg_catalog.count(*) FILTER (WHERE origin = 1) \
                     FROM babylon_ref.h3_reference_membership), \
                    (SELECT pg_catalog.count(*) FILTER (WHERE origin = 2) \
                     FROM babylon_ref.h3_reference_membership)",
            &[],
        )
        .unwrap();
    let cohort_count = counts.get(1);
    assert!(cohort_count <= i64::try_from(MAX_COHORT_SNAPSHOT_ROWS).unwrap());
    let rows = client
        .query(
            "SELECT pg_catalog.encode(ref_digest, 'hex'), format_version, artifact_name, \
                    artifact_manifest_version, pg_catalog.encode(artifact_digest, 'hex'), \
                    pg_catalog.encode(source_digest, 'hex'), \
                    pg_catalog.encode(source_r5_digest, 'hex'), \
                    pg_catalog.encode(source_r7_digest, 'hex'), \
                    pg_catalog.encode(closure_digest, 'hex'), \
                    pg_catalog.encode(membership_digest, 'hex'), direct_cell_count, \
                    derived_ancestor_count, closure_cell_count \
             FROM babylon_ref.h3_reference_cohort ORDER BY ref_digest LIMIT 2",
            &[],
        )
        .unwrap();
    assert_eq!(i64::try_from(rows.len()).unwrap(), cohort_count);
    ReferenceSnapshot {
        h3_cell_count: counts.get(0),
        cohort_count,
        membership_count: counts.get(2),
        direct_membership_count: counts.get(3),
        derived_membership_count: counts.get(4),
        cohorts: rows
            .iter()
            .take(MAX_COHORT_SNAPSHOT_ROWS)
            .map(cohort_snapshot)
            .collect(),
    }
}

fn cohort_snapshot(row: &postgres::Row) -> CohortSnapshot {
    CohortSnapshot {
        ref_digest: row.get(0),
        format_version: row.get(1),
        artifact_name: row.get(2),
        artifact_manifest_version: row.get(3),
        artifact_digest: row.get(4),
        source_digest: row.get(5),
        source_r5_digest: row.get(6),
        source_r7_digest: row.get(7),
        closure_digest: row.get(8),
        membership_digest: row.get(9),
        direct_cell_count: row.get(10),
        derived_ancestor_count: row.get(11),
        closure_cell_count: row.get(12),
    }
}

fn expected_installed_snapshot() -> ReferenceSnapshot {
    ReferenceSnapshot {
        h3_cell_count: 59_849,
        cohort_count: 1,
        membership_count: 59_849,
        direct_membership_count: 48_764,
        derived_membership_count: 11_085,
        cohorts: vec![CohortSnapshot {
            ref_digest: REF_DIGEST_HEX.into(),
            format_version: 1,
            artifact_name: "bridge_county_h3.parquet".into(),
            artifact_manifest_version: "2.0.0".into(),
            artifact_digest: ARTIFACT_DIGEST_HEX.into(),
            source_digest: "a4685e6ad882930e7064cb225ee649155fb74e52ef8b7d7550691a70a6087f5a"
                .into(),
            source_r5_digest: "83c093393bdf7a0e30ace8e208f3bcaa366fb7c6350abf7ff55d446322dcca87"
                .into(),
            source_r7_digest: "7f8d126ee81356a60605013b4b1c23942a77a4b2d6f890125d6c938dae70228b"
                .into(),
            closure_digest: "467cb7d1af751fe522cc3de818107068373531e51a4d9a7371a3f5f9becae29b"
                .into(),
            membership_digest: "4bbcdbf0c592b2cdc7ad52a8a8a5ef9a7e9989bd1b11b159be6eec5f2150247f"
                .into(),
            direct_cell_count: 48_764,
            derived_ancestor_count: 11_085,
            closure_cell_count: 59_849,
        }],
    }
}

fn vtwo_snapshot(config: &Config) -> V2Snapshot {
    let mut client = config.connect(NoTls).unwrap();
    let limit = i64::try_from(MAX_LEDGER_ROWS + 1).unwrap();
    let rows = client
        .query(
            "SELECT version, pg_catalog.encode(checksum, 'hex') \
             FROM babylon_state.schema_migration ORDER BY version LIMIT $1",
            &[&limit],
        )
        .unwrap();
    assert!(rows.len() <= MAX_LEDGER_ROWS);
    let h3_cell_count = client
        .query_one("SELECT pg_catalog.count(*) FROM babylon_ref.h3_cell", &[])
        .unwrap()
        .get(0);
    V2Snapshot {
        catalog: babylon_catalog_snapshot(config),
        ledger: rows
            .iter()
            .take(MAX_LEDGER_ROWS)
            .map(|row| (row.get(0), row.get(1)))
            .collect(),
        h3_cell_count,
    }
}

fn babylon_catalog_snapshot(config: &Config) -> Vec<(String, String)> {
    let mut client = config.connect(NoTls).unwrap();
    let limit = i64::try_from(MAX_EPOCH_CATALOG_ROWS + 1).unwrap();
    let rows = client
        .query(
            "SELECT object_kind, object_name FROM ( \
                 SELECT 'schema'::pg_catalog.text AS object_kind, \
                        namespace.nspname::pg_catalog.text AS object_name \
                 FROM pg_catalog.pg_namespace AS namespace \
                 WHERE namespace.nspname LIKE 'babylon\\_%' ESCAPE '\\' \
                 UNION ALL \
                 SELECT relation.relkind::pg_catalog.text, \
                        namespace.nspname || '.' || relation.relname \
                 FROM pg_catalog.pg_class AS relation \
                 JOIN pg_catalog.pg_namespace AS namespace \
                   ON namespace.oid = relation.relnamespace \
                 WHERE namespace.nspname LIKE 'babylon\\_%' ESCAPE '\\' \
             ) AS objects ORDER BY object_kind, object_name LIMIT $1",
            &[&limit],
        )
        .unwrap();
    assert!(rows.len() <= MAX_EPOCH_CATALOG_ROWS);
    rows.iter()
        .take(MAX_EPOCH_CATALOG_ROWS)
        .map(|row| (row.get(0), row.get(1)))
        .collect()
}

fn assert_writer_authority_refused() {
    assert_eq!(
        request_rust_writer_authority().unwrap_err(),
        RustWriterAuthorityError::PythonAuthorityActive
    );
}

fn representative_cohort() -> H3ReferenceCohort {
    build_representative_h3_cohort_v1(digest(ARTIFACT_DIGEST_HEX), &source_cells())
        .expect("pinned representative H3 fixture must build")
}

fn source_cells() -> Vec<H3CellId> {
    assert!(SOURCE_FIXTURE.starts_with(SOURCE_DOMAIN));
    let count_offset = SOURCE_DOMAIN.len();
    let payload_offset = count_offset + size_of::<u64>();
    let count = u64::from_be_bytes(
        SOURCE_FIXTURE[count_offset..payload_offset]
            .try_into()
            .expect("fixture count is exactly eight bytes"),
    );
    assert_eq!(usize::try_from(count).unwrap(), SOURCE_COUNT);
    assert_eq!(
        SOURCE_FIXTURE.len(),
        payload_offset + SOURCE_COUNT * size_of::<u64>()
    );
    SOURCE_FIXTURE[payload_offset..]
        .chunks_exact(size_of::<u64>())
        .take(SOURCE_COUNT)
        .map(|chunk| {
            let raw = u64::from_be_bytes(chunk.try_into().expect("cell is exactly eight bytes"));
            H3CellId::try_from(raw).expect("fixture identities must validate")
        })
        .collect()
}

fn digest(text: &str) -> RefDigest {
    assert_eq!(text.len(), 64);
    let mut bytes = [0_u8; 32];
    for (index, byte) in bytes.iter_mut().enumerate().take(32) {
        let offset = index * 2;
        *byte = u8::from_str_radix(&text[offset..offset + 2], 16).unwrap();
    }
    RefDigest::from_bytes(bytes)
}
