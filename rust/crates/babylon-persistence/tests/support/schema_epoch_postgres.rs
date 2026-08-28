//! Live schema-epoch checks hosted by the task-owned PER-20 `PostgreSQL` suite.

use super::{
    adopt_legacy_schema, assert_lock_released, database_user, mutate, ScratchDatabase,
    OWNER_PASSWORD, SCHEMA_ADVISORY_LOCK_KEY,
};
use babylon_persistence::{
    compiled_schema_migrations, migrate_schema_epoch, request_rust_writer_authority,
    LegacyAdopterError, RustWriterAuthorityError, SchemaEpochError, SchemaEpochOrigin,
};
use postgres::{Config, NoTls};

const AUTHORITY_REFUSAL_CASES: [(&str, &str); 28] = [
    (
        "epoch_schema_owner",
        "ALTER SCHEMA babylon_ref OWNER TO babylon_intel",
    ),
    (
        "epoch_table_owner",
        "ALTER TABLE babylon_state.schema_migration OWNER TO babylon_intel",
    ),
    (
        "epoch_public_schema",
        "GRANT USAGE ON SCHEMA babylon_ref TO PUBLIC",
    ),
    (
        "epoch_intel_schema",
        "GRANT USAGE ON SCHEMA babylon_ref TO babylon_intel",
    ),
    (
        "epoch_public_table",
        "GRANT SELECT ON babylon_state.schema_migration TO PUBLIC",
    ),
    (
        "epoch_intel_table",
        "GRANT SELECT ON babylon_state.schema_migration TO babylon_intel",
    ),
    (
        "epoch_extra_column",
        "ALTER TABLE babylon_state.schema_migration ADD COLUMN residue BIGINT",
    ),
    (
        "epoch_extra_object",
        "CREATE TABLE babylon_ref.unexpected_epoch_object (id BIGINT)",
    ),
    (
        "epoch_hthree_owner",
        "ALTER TABLE babylon_ref.h3_cell OWNER TO babylon_intel",
    ),
    (
        "epoch_hthree_public",
        "GRANT SELECT ON babylon_ref.h3_cell TO PUBLIC",
    ),
    (
        "epoch_hthree_intel",
        "GRANT SELECT ON babylon_ref.h3_cell TO babylon_intel",
    ),
    (
        "epoch_hthree_column",
        "GRANT SELECT (resolution) ON babylon_ref.h3_cell TO babylon_intel",
    ),
    (
        "epoch_hthree_drift",
        "ALTER TABLE babylon_ref.h3_cell DROP CONSTRAINT h3_cell_resolution_matches_id",
    ),
    (
        "epoch_cohort_owner",
        "ALTER TABLE babylon_ref.h3_reference_cohort OWNER TO babylon_intel",
    ),
    (
        "epoch_membership_public",
        "GRANT SELECT ON babylon_ref.h3_reference_membership TO PUBLIC",
    ),
    (
        "epoch_cohort_intel",
        "GRANT SELECT ON babylon_ref.h3_reference_cohort TO babylon_intel",
    ),
    (
        "epoch_membership_column",
        "GRANT UPDATE (origin) ON babylon_ref.h3_reference_membership TO babylon_intel",
    ),
    (
        "epoch_cohort_drift",
        "ALTER TABLE babylon_ref.h3_reference_cohort DROP CONSTRAINT \
         h3_reference_cohort_closure_count_matches",
    ),
    (
        "epoch_membership_index_drift",
        "DROP INDEX babylon_ref.h3_reference_membership_cell_id_idx",
    ),
    (
        "epoch_campaign_owner",
        "ALTER TABLE babylon_state.campaign OWNER TO babylon_intel",
    ),
    (
        "epoch_commit_public",
        "GRANT SELECT ON babylon_state.tick_commit TO PUBLIC",
    ),
    (
        "epoch_row_intel_column",
        "GRANT UPDATE (row_payload) ON babylon_state.tick_state_row TO babylon_intel",
    ),
    (
        "epoch_row_constraint_drift",
        "ALTER TABLE babylon_state.tick_graph_row DROP CONSTRAINT \
             tick_graph_row_key_length",
    ),
    (
        "epoch_product_owner",
        "ALTER TABLE babylon_ref.reference_product OWNER TO babylon_intel",
    ),
    (
        "epoch_county_public",
        "GRANT SELECT ON babylon_ref.county_identity TO PUBLIC",
    ),
    (
        "epoch_place_column",
        "GRANT UPDATE (name) ON babylon_ref.place_identity TO babylon_intel",
    ),
    (
        "epoch_share_constraint_drift",
        "ALTER TABLE babylon_ref.county_place_h3_land_area DROP CONSTRAINT \
             county_place_h3_land_area_share_formula",
    ),
    (
        "epoch_place_index_drift",
        "DROP INDEX babylon_ref.county_place_h3_land_area_place_idx",
    ),
];

pub(super) fn verify_fresh_migration(base: &Config) {
    let database = ScratchDatabase::empty(base, "schema_epoch_fresh", database_user(base));
    let config = database.config(base);

    let first = migrate_schema_epoch(&config).expect("pinned fresh template must migrate");
    assert_eq!(first.origin, SchemaEpochOrigin::Fresh);
    assert_eq!(first.prior_applied, 0);
    assert_eq!(first.final_applied, 5);
    assert_eq!(first.applied_versions.len(), 5);
    assert_eq!(first.applied_versions[0].as_i64(), 1);
    assert_eq!(first.applied_versions[1].as_i64(), 2);
    assert_eq!(first.applied_versions[2].as_i64(), 3);
    assert_eq!(first.applied_versions[3].as_i64(), 4);
    assert_eq!(first.applied_versions[4].as_i64(), 5);
    assert!(first.reconciled_versions.is_empty());
    assert!(first.legacy_adoption.is_none());
    assert_oversized_row_key_is_storeable(&config);

    let before = epoch_snapshot(&config);
    let second = migrate_schema_epoch(&config).expect("exact Rust prefix must be idempotent");
    assert_eq!(second.origin, SchemaEpochOrigin::ExistingRustPrefix);
    assert_eq!(second.prior_applied, 5);
    assert_eq!(second.final_applied, 5);
    assert!(second.applied_versions.is_empty());
    assert!(second.reconciled_versions.is_empty());
    assert_eq!(epoch_snapshot(&config), before);
    assert_lock_released(&config);
    database.cleanup();
}

pub(super) fn verify_schema_epoch_matrix(base: &Config, legacy_template: &str, owner: &str) {
    assert_eq!(
        request_rust_writer_authority().unwrap_err(),
        RustWriterAuthorityError::PythonAuthorityActive
    );

    let fresh = ScratchDatabase::empty(base, "epoch_baseline", database_user(base));
    let fresh_config = fresh.config(base);
    assert_fresh_receipt(&migrate_schema_epoch(&fresh_config).unwrap());
    let fresh_snapshot = epoch_snapshot(&fresh_config);
    assert_idempotent(&fresh_config, &fresh_snapshot);
    assert_epoch_authority(&fresh_config);

    verify_non_superuser_owner(base, owner);
    verify_v1_to_v5_upgrade(base);
    verify_v2_to_v5_upgrade(base);
    verify_v3_to_v5_upgrade(base);
    verify_v4_to_v5_upgrade(base);
    verify_lock_refusal(base);
    verify_legacy_epoch(base, legacy_template);
    verify_bad_ledgers(base, fresh.name());
    verify_partial_epochs(base);
    verify_contaminated_fresh(base, fresh.name());
    verify_authority_refusals(base, fresh.name(), owner);

    fresh.cleanup();
}

fn verify_lock_refusal(base: &Config) {
    let database = ScratchDatabase::empty(base, "epoch_lock", database_user(base));
    let config = database.config(base);
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
    let before = marker_snapshot(&config);
    assert_eq!(
        migrate_schema_epoch(&config),
        Err(SchemaEpochError::Lock(LegacyAdopterError::LockUnavailable))
    );
    assert_eq!(marker_snapshot(&config), before);
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
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_non_superuser_owner(base: &Config, owner: &str) {
    let database = ScratchDatabase::empty(base, "epoch_owner", owner);
    let config = database.config_as(base, owner, OWNER_PASSWORD);
    assert_fresh_receipt(&migrate_schema_epoch(&config).unwrap());
    assert_epoch_authority(&config);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_v1_to_v5_upgrade(base: &Config) {
    let database = ScratchDatabase::empty(base, "epoch_v1_upgrade", database_user(base));
    let config = database.config(base);
    establish_v1_prefix(&config);
    let before = raw_epoch_snapshot(&config);
    assert_eq!(before.len(), 4);
    assert!(before.iter().any(|row| row.0 == "ledger" && row.1 == "1"));
    assert!(!before.iter().any(|row| row.1 == "2"));

    let upgraded = migrate_schema_epoch(&config).expect("exact epoch 1 must upgrade to epoch 5");
    assert_eq!(upgraded.origin, SchemaEpochOrigin::ExistingRustPrefix);
    assert_eq!(upgraded.prior_applied, 1);
    assert_eq!(upgraded.final_applied, 5);
    assert_eq!(upgraded.applied_versions.len(), 4);
    assert_eq!(upgraded.applied_versions[0].as_i64(), 2);
    assert_eq!(upgraded.applied_versions[1].as_i64(), 3);
    assert_eq!(upgraded.applied_versions[2].as_i64(), 4);
    assert_eq!(upgraded.applied_versions[3].as_i64(), 5);
    assert!(upgraded.reconciled_versions.is_empty());
    assert_epoch_authority(&config);
    let snapshot = epoch_snapshot(&config);
    assert_idempotent(&config, &snapshot);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_v2_to_v5_upgrade(base: &Config) {
    let database = ScratchDatabase::empty(base, "epoch_v2_upgrade", database_user(base));
    let config = database.config(base);
    establish_v2_prefix(&config);
    let before = raw_epoch_snapshot(&config);
    assert_eq!(before.len(), 5);
    assert!(before.iter().any(|row| row.0 == "ledger" && row.1 == "1"));
    assert!(before.iter().any(|row| row.0 == "ledger" && row.1 == "2"));
    assert!(!before.iter().any(|row| row.1 == "3"));

    let upgraded = migrate_schema_epoch(&config).expect("exact epoch 2 must upgrade to epoch 5");
    assert_eq!(upgraded.origin, SchemaEpochOrigin::ExistingRustPrefix);
    assert_eq!(upgraded.prior_applied, 2);
    assert_eq!(upgraded.final_applied, 5);
    assert_eq!(upgraded.applied_versions.len(), 3);
    assert_eq!(upgraded.applied_versions[0].as_i64(), 3);
    assert_eq!(upgraded.applied_versions[1].as_i64(), 4);
    assert_eq!(upgraded.applied_versions[2].as_i64(), 5);
    assert!(upgraded.reconciled_versions.is_empty());
    assert_epoch_authority(&config);
    let snapshot = epoch_snapshot(&config);
    assert_idempotent(&config, &snapshot);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_v3_to_v5_upgrade(base: &Config) {
    let database = ScratchDatabase::empty(base, "epoch_v3_upgrade", database_user(base));
    let config = database.config(base);
    establish_v3_prefix(&config);
    let before = raw_epoch_snapshot(&config);
    assert_eq!(before.len(), 6);
    assert!(before.iter().any(|row| row.0 == "ledger" && row.1 == "3"));
    assert!(!before.iter().any(|row| row.1 == "4"));

    let upgraded = migrate_schema_epoch(&config).expect("exact epoch 3 must upgrade to epoch 5");
    assert_eq!(upgraded.origin, SchemaEpochOrigin::ExistingRustPrefix);
    assert_eq!(upgraded.prior_applied, 3);
    assert_eq!(upgraded.final_applied, 5);
    assert_eq!(upgraded.applied_versions.len(), 2);
    assert_eq!(upgraded.applied_versions[0].as_i64(), 4);
    assert_eq!(upgraded.applied_versions[1].as_i64(), 5);
    assert!(upgraded.reconciled_versions.is_empty());
    assert_epoch_authority(&config);
    let snapshot = epoch_snapshot(&config);
    assert_idempotent(&config, &snapshot);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_v4_to_v5_upgrade(base: &Config) {
    let database = ScratchDatabase::empty(base, "epoch_v4_upgrade", database_user(base));
    let config = database.config(base);
    establish_v4_prefix(&config);

    let upgraded = migrate_schema_epoch(&config).expect("exact epoch 4 must upgrade to epoch 5");
    assert_eq!(upgraded.origin, SchemaEpochOrigin::ExistingRustPrefix);
    assert_eq!(upgraded.prior_applied, 4);
    assert_eq!(upgraded.final_applied, 5);
    assert_eq!(upgraded.applied_versions.len(), 1);
    assert_eq!(upgraded.applied_versions[0].as_i64(), 5);
    assert!(upgraded.reconciled_versions.is_empty());
    assert_epoch_authority(&config);
    let snapshot = epoch_snapshot(&config);
    assert_idempotent(&config, &snapshot);
    assert_lock_released(&config);
    database.cleanup();
}

fn establish_v1_prefix(config: &Config) {
    let compiled = compiled_schema_migrations().expect("compiled registry must be valid");
    let version = compiled[0].version().as_i64();
    let checksum = compiled[0].checksum();
    let checksum_bytes = checksum.as_bytes().as_slice();
    let mut client = config.connect(NoTls).unwrap();
    let mut transaction = client.transaction().unwrap();
    transaction.batch_execute(compiled[0].sql()).unwrap();
    transaction
        .execute(
            "INSERT INTO babylon_state.schema_migration (version, checksum) VALUES ($1, $2)",
            &[&version, &checksum_bytes],
        )
        .unwrap();
    transaction.commit().unwrap();
}

fn establish_v2_prefix(config: &Config) {
    let compiled = compiled_schema_migrations().expect("compiled registry must be valid");
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

fn establish_v3_prefix(config: &Config) {
    let compiled = compiled_schema_migrations().expect("compiled registry must be valid");
    let mut client = config.connect(NoTls).unwrap();
    let mut transaction = client.transaction().unwrap();
    for migration in compiled.iter().take(3) {
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

fn establish_v4_prefix(config: &Config) {
    let compiled = compiled_schema_migrations().expect("compiled registry must be valid");
    let mut client = config.connect(NoTls).unwrap();
    let mut transaction = client.transaction().unwrap();
    for migration in compiled.iter().take(4) {
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

fn verify_legacy_epoch(base: &Config, template: &str) {
    let database = ScratchDatabase::from_template(base, template, "epoch_legacy");
    let config = database.config(base);
    let before = legacy_meta_snapshot(&config);
    let adoption = adopt_legacy_schema(&config).unwrap();
    assert_eq!(adoption.expected_objects, 102);
    assert_eq!(adoption.matched_objects, 102);

    let first = migrate_schema_epoch(&config).unwrap();
    assert_eq!(first.origin, SchemaEpochOrigin::ExactLegacy);
    assert_eq!(first.prior_applied, 0);
    assert_eq!(first.final_applied, 5);
    assert_eq!(first.applied_versions.len(), 5);
    assert_eq!(first.legacy_adoption, Some(adoption));
    assert_eq!(legacy_meta_snapshot(&config), before);
    assert_epoch_authority(&config);

    let snapshot = epoch_snapshot(&config);
    assert_idempotent(&config, &snapshot);
    assert_eq!(legacy_meta_snapshot(&config), before);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_bad_ledgers(base: &Config, migrated_template: &str) {
    let empty = ScratchDatabase::from_template(base, migrated_template, "epoch_empty_ledger");
    let empty_config = empty.config(base);
    mutate(&empty_config, "DELETE FROM babylon_state.schema_migration");
    let before = raw_epoch_snapshot(&empty_config);
    assert_eq!(
        migrate_schema_epoch(&empty_config),
        Err(SchemaEpochError::UnrecordedRustEpoch)
    );
    assert_eq!(raw_epoch_snapshot(&empty_config), before);
    assert_lock_released(&empty_config);
    empty.cleanup();

    verify_checksum_refusal(base, migrated_template, "epoch_checksum", 1, "55");
    verify_checksum_refusal(base, migrated_template, "epoch_checksum_vtwo", 2, "66");
    verify_checksum_refusal(base, migrated_template, "epoch_checksum_vthree", 3, "77");
    verify_checksum_refusal(base, migrated_template, "epoch_checksum_vfour", 4, "88");
    verify_checksum_refusal(base, migrated_template, "epoch_checksum_vfive", 5, "99");

    let future = ScratchDatabase::from_template(base, migrated_template, "epoch_future");
    let future_config = future.config(base);
    mutate(
        &future_config,
        "INSERT INTO babylon_state.schema_migration (version, checksum) \
         VALUES (6, decode(repeat('44', 32), 'hex'))",
    );
    let before = raw_epoch_snapshot(&future_config);
    assert_eq!(
        migrate_schema_epoch(&future_config),
        Err(SchemaEpochError::UnknownFutureVersion {
            actual: 6,
            latest_compiled: 5,
        })
    );
    assert_eq!(raw_epoch_snapshot(&future_config), before);
    assert_lock_released(&future_config);
    future.cleanup();

    let gap = ScratchDatabase::from_template(base, migrated_template, "epoch_gap");
    let gap_config = gap.config(base);
    mutate(
        &gap_config,
        "DELETE FROM babylon_state.schema_migration; \
         INSERT INTO babylon_state.schema_migration (version, checksum) \
         VALUES (2, decode(repeat('22', 32), 'hex'))",
    );
    let before = raw_epoch_snapshot(&gap_config);
    assert_eq!(
        migrate_schema_epoch(&gap_config),
        Err(SchemaEpochError::LedgerVersionMismatch {
            row_index: 0,
            expected: 1,
            actual: 2,
        })
    );
    assert_eq!(raw_epoch_snapshot(&gap_config), before);
    assert_lock_released(&gap_config);
    gap.cleanup();
}

fn verify_checksum_refusal(
    base: &Config,
    migrated_template: &str,
    label: &str,
    version: i64,
    replacement_byte: &str,
) {
    let database = ScratchDatabase::from_template(base, migrated_template, label);
    let config = database.config(base);
    mutate(
        &config,
        &format!(
            "UPDATE babylon_state.schema_migration \
             SET checksum = decode(repeat('{replacement_byte}', 32), 'hex') \
             WHERE version = {version}"
        ),
    );
    let before = raw_epoch_snapshot(&config);
    assert_eq!(
        migrate_schema_epoch(&config),
        Err(SchemaEpochError::LedgerChecksumMismatch { version })
    );
    assert_eq!(raw_epoch_snapshot(&config), before);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_partial_epochs(base: &Config) {
    let one = ScratchDatabase::empty(base, "epoch_partial_one", database_user(base));
    let one_config = one.config(base);
    mutate(&one_config, "CREATE SCHEMA babylon_ref");
    let before = marker_snapshot(&one_config);
    assert!(matches!(
        migrate_schema_epoch(&one_config),
        Err(SchemaEpochError::PartialAuthorityEpoch { .. })
    ));
    assert_eq!(marker_snapshot(&one_config), before);
    assert_lock_released(&one_config);
    one.cleanup();

    let three = ScratchDatabase::empty(base, "epoch_partial_three", database_user(base));
    let three_config = three.config(base);
    mutate(
        &three_config,
        "CREATE SCHEMA babylon_ref; CREATE SCHEMA babylon_state; CREATE SCHEMA babylon_meta",
    );
    let before = marker_snapshot(&three_config);
    assert!(matches!(
        migrate_schema_epoch(&three_config),
        Err(SchemaEpochError::PartialAuthorityEpoch { .. })
    ));
    assert_eq!(marker_snapshot(&three_config), before);
    assert_lock_released(&three_config);
    three.cleanup();
}

fn verify_contaminated_fresh(base: &Config, migrated_template: &str) {
    let database = ScratchDatabase::empty(base, "epoch_contaminated", database_user(base));
    let config = database.config(base);
    mutate(
        &config,
        "CREATE TABLE public.unexpected_epoch_object (id bigint)",
    );
    let before = marker_snapshot(&config);
    assert!(matches!(
        migrate_schema_epoch(&config),
        Err(SchemaEpochError::FreshCensusMismatch { .. })
    ));
    assert_eq!(marker_snapshot(&config), before);
    assert_lock_released(&config);
    database.cleanup();

    let defaults = ScratchDatabase::empty(base, "epoch_defaults", database_user(base));
    let defaults_config = defaults.config(base);
    mutate(
        &defaults_config,
        "ALTER DEFAULT PRIVILEGES GRANT SELECT ON TABLES TO PUBLIC",
    );
    assert_eq!(
        migrate_schema_epoch(&defaults_config),
        Err(SchemaEpochError::AuthoritySentinelResidue)
    );
    assert_lock_released(&defaults_config);
    defaults.cleanup();

    let prefix = ScratchDatabase::from_template(base, migrated_template, "epoch_prefix_defaults");
    let prefix_config = prefix.config(base);
    mutate(
        &prefix_config,
        "ALTER DEFAULT PRIVILEGES GRANT SELECT ON TABLES TO PUBLIC",
    );
    let before = raw_epoch_snapshot(&prefix_config);
    assert_eq!(
        migrate_schema_epoch(&prefix_config),
        Err(SchemaEpochError::AuthoritySentinelResidue)
    );
    assert_eq!(raw_epoch_snapshot(&prefix_config), before);
    assert_lock_released(&prefix_config);
    prefix.cleanup();
}

fn verify_authority_refusals(base: &Config, migrated_template: &str, owner: &str) {
    let non_owner = ScratchDatabase::empty(base, "epoch_wrong_caller", owner);
    let non_owner_config = non_owner.config(base);
    let before = marker_snapshot(&non_owner_config);
    assert_eq!(
        migrate_schema_epoch(&non_owner_config),
        Err(SchemaEpochError::CurrentUserIsNotDatabaseOwner)
    );
    assert_eq!(marker_snapshot(&non_owner_config), before);
    assert_lock_released(&non_owner_config);
    non_owner.cleanup();

    let cases = AUTHORITY_REFUSAL_CASES;
    for (label, mutation) in cases.iter().take(28) {
        let database = ScratchDatabase::from_template(base, migrated_template, label);
        let config = database.config(base);
        mutate(&config, mutation);
        let before = authority_snapshot(&config);
        assert_eq!(
            migrate_schema_epoch(&config),
            Err(SchemaEpochError::EpochShapeMismatch),
            "authority mutation must refuse: {label}"
        );
        assert_eq!(
            authority_snapshot(&config),
            before,
            "refusal must not mutate: {label}"
        );
        assert_lock_released(&config);
        database.cleanup();
    }
}

fn assert_fresh_receipt(report: &babylon_persistence::SchemaEpochReport) {
    assert_eq!(report.origin, SchemaEpochOrigin::Fresh);
    assert_eq!(report.prior_applied, 0);
    assert_eq!(report.final_applied, 5);
    assert_eq!(report.applied_versions.len(), 5);
    assert_eq!(report.applied_versions[0].as_i64(), 1);
    assert_eq!(report.applied_versions[1].as_i64(), 2);
    assert_eq!(report.applied_versions[2].as_i64(), 3);
    assert_eq!(report.applied_versions[3].as_i64(), 4);
    assert_eq!(report.applied_versions[4].as_i64(), 5);
    assert!(report.reconciled_versions.is_empty());
    assert!(report.legacy_adoption.is_none());
}

fn assert_idempotent(config: &Config, expected_snapshot: &[(String, String, String)]) {
    let second = migrate_schema_epoch(config).unwrap();
    assert_eq!(second.origin, SchemaEpochOrigin::ExistingRustPrefix);
    assert_eq!(second.prior_applied, 5);
    assert_eq!(second.final_applied, 5);
    assert!(second.applied_versions.is_empty());
    assert!(second.reconciled_versions.is_empty());
    assert_eq!(epoch_snapshot(config), expected_snapshot);
}

fn assert_epoch_authority(config: &Config) {
    let mut client = config.connect(NoTls).unwrap();
    let row = client
        .query_one(
            "WITH schemas AS ( \
             SELECT namespace.oid, namespace.nspacl, namespace.nspowner \
             FROM pg_catalog.pg_namespace AS namespace \
             WHERE namespace.nspname IN ('babylon_ref', 'babylon_state', 'babylon_meta') \
             ), intel AS ( \
             SELECT role_row.oid FROM pg_catalog.pg_roles AS role_row \
             WHERE role_row.rolname = 'babylon_intel' \
             ) \
             SELECT (SELECT pg_catalog.count(*) = 3 FROM schemas), \
                    NOT EXISTS (SELECT 1 FROM schemas CROSS JOIN LATERAL \
                      pg_catalog.aclexplode(coalesce(nspacl, pg_catalog.acldefault('n', nspowner))) acl \
                      WHERE acl.grantee = 0), \
                    NOT EXISTS (SELECT 1 FROM schemas CROSS JOIN intel \
                      WHERE pg_catalog.has_schema_privilege(intel.oid, schemas.oid, 'USAGE') \
                         OR pg_catalog.has_schema_privilege(intel.oid, schemas.oid, 'CREATE')), \
                    (SELECT pg_catalog.count(*) = 22 \
                     FROM pg_catalog.pg_class AS relation \
                     JOIN pg_catalog.pg_namespace AS namespace \
                       ON namespace.oid = relation.relnamespace \
                     WHERE namespace.nspname IN ('babylon_ref', 'babylon_state') \
                       AND relation.relkind = 'r' AND relation.relpersistence = 'p'), \
                    NOT EXISTS (SELECT 1 FROM intel \
                      CROSS JOIN pg_catalog.pg_class AS relation \
                      JOIN pg_catalog.pg_namespace AS namespace \
                        ON namespace.oid = relation.relnamespace \
                      WHERE namespace.nspname IN ('babylon_ref', 'babylon_state') \
                        AND relation.relkind = 'r' \
                        AND pg_catalog.has_table_privilege( \
                          intel.oid, relation.oid, \
                          'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER,MAINTAIN'))",
            &[],
        )
        .unwrap();
    for index in 0..5 {
        assert!(row.try_get::<_, bool>(index).unwrap());
    }
}

fn assert_oversized_row_key_is_storeable(config: &Config) {
    let key = incompressible_oversized_btree_key();
    let payload = vec![0x5a_u8];
    let mut client = config.connect(NoTls).unwrap();
    let mut transaction = client.transaction().unwrap();
    let inserted = transaction
        .execute(
            "INSERT INTO babylon_state.tick_graph_row \
             (campaign_id, resolve_tick, row_ordinal, row_key, row_payload) \
             VALUES ('00112233-4455-6677-8899-aabbccddeeff', 0, 0, $1, $2)",
            &[&key, &payload],
        )
        .unwrap();
    assert_eq!(inserted, 1);
    transaction.rollback().unwrap();
}

fn incompressible_oversized_btree_key() -> Vec<u8> {
    const OVERSIZED_BTREE_KEY_BYTES: usize = 4_096;
    const MULTIPLIER: u64 = 6_364_136_223_846_793_005;
    const INCREMENT: u64 = 1_442_695_040_888_963_407;
    let mut state = 0x0011_2233_4455_6677_u64;
    let mut key = Vec::with_capacity(OVERSIZED_BTREE_KEY_BYTES);
    for _ in 0..OVERSIZED_BTREE_KEY_BYTES {
        state = state.wrapping_mul(MULTIPLIER).wrapping_add(INCREMENT);
        key.push(state.to_be_bytes()[0]);
    }
    key
}

fn legacy_meta_snapshot(config: &Config) -> Vec<(String, String)> {
    let mut client = config.connect(NoTls).unwrap();
    client
        .query(
            "SELECT relation.relname, relation.oid::pg_catalog.text \
             FROM pg_catalog.pg_class AS relation \
             JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace \
             WHERE namespace.nspname = 'babylon_meta' AND relation.relkind = 'r' \
             ORDER BY relation.relname LIMIT 5",
            &[],
        )
        .unwrap()
        .iter()
        .take(5)
        .map(|row| (row.try_get(0).unwrap(), row.try_get(1).unwrap()))
        .collect()
}

fn marker_snapshot(config: &Config) -> Vec<(String, String)> {
    let mut client = config.connect(NoTls).unwrap();
    client
        .query(
            "SELECT 'schema'::pg_catalog.text, namespace.nspname \
             FROM pg_catalog.pg_namespace AS namespace \
             WHERE namespace.nspname LIKE 'babylon\\_%' ESCAPE '\\' \
             UNION ALL \
             SELECT 'relation', namespace.nspname || '.' || relation.relname \
             FROM pg_catalog.pg_class AS relation \
             JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace \
             WHERE namespace.nspname LIKE 'babylon\\_%' ESCAPE '\\' \
             ORDER BY 1, 2 LIMIT 16",
            &[],
        )
        .unwrap()
        .iter()
        .take(16)
        .map(|row| (row.try_get(0).unwrap(), row.try_get(1).unwrap()))
        .collect()
}

fn epoch_snapshot(config: &Config) -> Vec<(String, String, String)> {
    let snapshot = raw_epoch_snapshot(config);
    assert_eq!(snapshot.len(), 8);
    let compiled = compiled_schema_migrations().unwrap();
    for (index, migration) in compiled.iter().enumerate().take(5) {
        let version = (index + 1).to_string();
        assert!(snapshot.iter().any(|row| {
            row.0 == "ledger"
                && row.1 == version
                && row.2 == lower_hex(migration.checksum().as_bytes())
        }));
    }
    snapshot
}

fn raw_epoch_snapshot(config: &Config) -> Vec<(String, String, String)> {
    let mut client = config.connect(NoTls).unwrap();
    let rows = client
        .query(
            "SELECT object_kind, object_name, object_value FROM ( \
             SELECT 'schema'::pg_catalog.text AS object_kind, namespace.nspname AS object_name, \
                    pg_catalog.pg_get_userbyid(namespace.nspowner)::pg_catalog.text AS object_value \
             FROM pg_catalog.pg_namespace AS namespace \
             WHERE namespace.nspname IN ('babylon_ref', 'babylon_state', 'babylon_meta') \
             UNION ALL \
             SELECT 'ledger', version::pg_catalog.text, \
                    pg_catalog.encode(checksum, 'hex') \
             FROM babylon_state.schema_migration \
             ) AS epoch ORDER BY object_kind, object_name LIMIT 8",
            &[],
        )
        .unwrap();
    rows.iter()
        .take(8)
        .map(|row| {
            (
                row.try_get(0).unwrap(),
                row.try_get(1).unwrap(),
                row.try_get(2).unwrap(),
            )
        })
        .collect::<Vec<_>>()
}

fn authority_snapshot(config: &Config) -> Vec<(String, String, String)> {
    let mut client = config.connect(NoTls).unwrap();
    client
        .query(
            "SELECT object_kind, object_name, object_value FROM ( \
             SELECT 'schema'::pg_catalog.text AS object_kind, namespace.nspname AS object_name, \
                    pg_catalog.pg_get_userbyid(namespace.nspowner) || '|' || \
                    coalesce(namespace.nspacl::pg_catalog.text, '<null>') AS object_value \
             FROM pg_catalog.pg_namespace AS namespace \
             WHERE namespace.nspname IN ('babylon_ref', 'babylon_state', 'babylon_meta') \
             UNION ALL \
             SELECT 'relation', namespace.nspname || '.' || relation.relname, \
                    relation.relkind::pg_catalog.text || '|' || \
                    pg_catalog.pg_get_userbyid(relation.relowner) || '|' || \
                    coalesce(relation.relacl::pg_catalog.text, '<null>') \
             FROM pg_catalog.pg_class AS relation \
             JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace \
             WHERE namespace.nspname IN ('babylon_ref', 'babylon_state') \
             UNION ALL \
             SELECT 'column', namespace.nspname || '.' || relation.relname || '.' || \
                    attribute.attnum::pg_catalog.text, attribute.attname || '|' || \
                    pg_catalog.format_type(attribute.atttypid, attribute.atttypmod) || '|' || \
                    attribute.attnotnull::pg_catalog.text \
             FROM pg_catalog.pg_attribute AS attribute \
             JOIN pg_catalog.pg_class AS relation ON relation.oid = attribute.attrelid \
             JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace \
             WHERE namespace.nspname IN ('babylon_ref', 'babylon_state') \
               AND attribute.attnum > 0 AND NOT attribute.attisdropped \
             UNION ALL \
             SELECT 'ledger', version::pg_catalog.text, pg_catalog.encode(checksum, 'hex') \
             FROM babylon_state.schema_migration \
             ) AS authority ORDER BY object_kind, object_name LIMIT 128",
            &[],
        )
        .unwrap()
        .iter()
        .take(128)
        .map(|row| {
            (
                row.try_get(0).unwrap(),
                row.try_get(1).unwrap(),
                row.try_get(2).unwrap(),
            )
        })
        .collect()
}

fn lower_hex(bytes: &[u8; 32]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(64);
    for byte in bytes.iter().take(32) {
        output.push(char::from(HEX[usize::from(byte >> 4)]));
        output.push(char::from(HEX[usize::from(byte & 0x0f)]));
    }
    output
}
