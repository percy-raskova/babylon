//! Bounded, exact-prefix contracts for the Rust-owned schema epoch.

use postgres::{Client, Config, IsolationLevel, NoTls, Row, Transaction};

use crate::legacy_adopter::{
    acquire_lock, catalog_census_under_lock, compare_legacy_census, parse_legacy_census_fixture,
    read_census_rows, release_lock, validate_legacy_connection_target, verify_under_lock,
    LegacyAdopterError, LegacyAdoptionReport, LegacyCensusEntry, LegacyCensusParseError,
    LegacyObjectKind, LEGACY_ADOPTER_CONNECT_TIMEOUT, LEGACY_ADOPTER_STARTUP_OPTIONS,
    LEGACY_ADOPTER_TCP_USER_TIMEOUT, MAX_LEGACY_CENSUS_ROWS,
};
use crate::schema_migration::{
    MigrationChecksum, MigrationVersion, SchemaMigration, SchemaMigrationError,
};

/// Maximum number of compiled migrations or persisted ledger rows.
pub const MAX_SCHEMA_MIGRATIONS: usize = 256;
/// Maximum commit/reconciliation attempts for one version.
pub const MAX_COMMIT_ATTEMPTS_PER_VERSION: usize = 2;
pub(crate) const CURRENT_SCHEMA_EPOCH: usize = 5;

const MIGRATION_0001_SQL: &str = include_str!("../migrations/0001_owned_schema_epoch.sql");
const MIGRATION_0002_SQL: &str = include_str!("../migrations/0002_h3_cell.sql");
const MIGRATION_0003_SQL: &str = include_str!("../migrations/0003_h3_reference_cohort.sql");
const MIGRATION_0004_SQL: &str = include_str!("../migrations/0004_committed_tick_storage.sql");
const MIGRATION_0005_SQL: &str = include_str!("../migrations/0005_spatial_reference_products.sql");
const FRESH_CENSUS: &str = include_str!("fixtures/fresh_schema_epoch_census_v1.txt");
const FRESH_CENSUS_WITH_INTEL: &str =
    include_str!("fixtures/fresh_schema_epoch_census_with_intel_v1.txt");
const EPOCH_OWNED_CENSUS_V1: &str = include_str!("fixtures/schema_epoch_owned_census_v1.txt");
const EPOCH_OWNED_FRESH_CENSUS_V1: &str =
    include_str!("fixtures/schema_epoch_owned_fresh_census_v1.txt");
const EPOCH_OWNED_CENSUS_V2: &str = include_str!("fixtures/schema_epoch_owned_census_v2.txt");
const EPOCH_OWNED_FRESH_CENSUS_V2: &str =
    include_str!("fixtures/schema_epoch_owned_fresh_census_v2.txt");
const EPOCH_OWNED_CENSUS_V3: &str = include_str!("fixtures/schema_epoch_owned_census_v3.txt");
const EPOCH_OWNED_FRESH_CENSUS_V3: &str =
    include_str!("fixtures/schema_epoch_owned_fresh_census_v3.txt");
const EPOCH_OWNED_CENSUS_V4: &str = include_str!("fixtures/schema_epoch_owned_census_v4.txt");
const EPOCH_OWNED_FRESH_CENSUS_V4: &str =
    include_str!("fixtures/schema_epoch_owned_fresh_census_v4.txt");
const EPOCH_OWNED_CENSUS_V5: &str = include_str!("fixtures/schema_epoch_owned_census_v5.txt");
const EPOCH_OWNED_FRESH_CENSUS_V5: &str =
    include_str!("fixtures/schema_epoch_owned_fresh_census_v5.txt");
const OWNER_SQL: &str = "SELECT database_row.datdba = role_row.oid \
    FROM pg_catalog.pg_database AS database_row \
    JOIN pg_catalog.pg_roles AS role_row ON role_row.rolname = CURRENT_USER \
    WHERE database_row.datname = pg_catalog.current_database()";
const MARKERS_SQL: &str = "SELECT \
    pg_catalog.to_regnamespace('babylon_ref') IS NOT NULL, \
    pg_catalog.to_regnamespace('babylon_state') IS NOT NULL, \
    pg_catalog.to_regnamespace('babylon_meta') IS NOT NULL, \
    ledger.oid IS NOT NULL, \
    coalesce(ledger.relkind = 'r' AND ledger.relpersistence = 'p', false), \
    stamp.oid IS NOT NULL, \
    coalesce(stamp.relkind = 'r' AND stamp.relpersistence = 'p', false) \
    FROM (SELECT 1) AS singleton \
    LEFT JOIN pg_catalog.pg_class AS ledger \
      ON ledger.oid = pg_catalog.to_regclass('babylon_state.schema_migration') \
    LEFT JOIN pg_catalog.pg_class AS stamp \
      ON stamp.oid = pg_catalog.to_regclass('public._babylon_schema_stamp')";
const FRESH_SENTINELS_SQL: &str = "SELECT \
    NOT EXISTS (SELECT 1 FROM pg_catalog.pg_default_acl LIMIT 1), \
    NOT EXISTS (SELECT 1 FROM pg_catalog.pg_seclabel LIMIT 1), \
    NOT EXISTS (SELECT 1 FROM pg_catalog.pg_shseclabel AS label \
      JOIN pg_catalog.pg_database AS database_row \
        ON label.classoid = 'pg_catalog.pg_database'::pg_catalog.regclass \
       AND label.objoid = database_row.oid \
      WHERE database_row.datname = pg_catalog.current_database() LIMIT 1)";
const LEDGER_SQL: &str = "SELECT version, checksum \
    FROM babylon_state.schema_migration ORDER BY version LIMIT $1";
const INSERT_LEDGER_SQL: &str = "INSERT INTO babylon_state.schema_migration \
    (version, checksum) VALUES ($1, $2)";
const WRITE_SETTINGS_SQL: &str = "SELECT \
    pg_catalog.current_setting('transaction_isolation'), \
    pg_catalog.current_setting('transaction_read_only'), \
    pg_catalog.current_setting('search_path'), \
    pg_catalog.current_setting('synchronous_commit'), \
    pg_catalog.current_setting('statement_timeout'), \
    pg_catalog.current_setting('lock_timeout'), \
    pg_catalog.current_setting('idle_in_transaction_session_timeout')";
const WRITE_LOCAL_SETTINGS_SQL: &str = "SET LOCAL search_path TO pg_catalog; \
    SET LOCAL synchronous_commit TO on";
const EPOCH_V1_SHAPE_SQL: &str = include_str!("schema_epoch_shape.sql");
const EPOCH_V2_SHAPE_SQL: &str = include_str!("schema_epoch_v2_shape.sql");
const EPOCH_V3_SHAPE_SQL: &str = include_str!("schema_epoch_v3_shape.sql");
const EPOCH_V4_SHAPE_SQL: &str = include_str!("schema_epoch_v4_shape.sql");
const EPOCH_V5_SHAPE_SQL: &str = include_str!("schema_epoch_v5_shape.sql");

/// Database lane selected under the schema advisory lock.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SchemaEpochOrigin {
    /// Pinned extension template with no Babylon objects.
    Fresh,
    /// Exact frozen Python estate.
    ExactLegacy,
    /// Existing exact Rust migration prefix.
    ExistingRustPrefix,
}

/// Successful bounded schema migration receipt.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SchemaEpochReport {
    /// Lane observed before any new migration.
    pub origin: SchemaEpochOrigin,
    /// Exact applied prefix before this invocation.
    pub prior_applied: usize,
    /// Exact applied prefix after this invocation.
    pub final_applied: usize,
    /// Versions committed by this invocation.
    pub applied_versions: Vec<MigrationVersion>,
    /// Versions whose ambiguous commit was reconciled as committed.
    pub reconciled_versions: Vec<MigrationVersion>,
    /// Legacy verification receipt when first adopting the frozen estate.
    pub legacy_adoption: Option<LegacyAdoptionReport>,
}

/// Closed database operations used in safe failures.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SchemaEpochOperation {
    Connect,
    VerifyOwner,
    Classify,
    FreshSentinels,
    ReadLedger,
    BeginMigration,
    SetMigrationSettings,
    VerifyMigrationSettings,
    ExecuteMigration,
    VerifyEpochShape,
    InsertLedger,
    CommitMigration,
    ReconcileCommit,
    Unlock,
}

/// Bounded marker state for a partial or mixed authority epoch.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SchemaEpochObservation {
    pub schemas: SchemaEpochSchemas,
    pub ledger: SchemaEpochRelation,
    pub legacy_stamp: SchemaEpochRelation,
}

/// Presence of the three owned schema markers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SchemaEpochSchemas {
    pub babylon_ref: bool,
    pub babylon_state: bool,
    pub babylon_meta: bool,
}

/// Closed relation-marker classification.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SchemaEpochRelation {
    Absent,
    ExactTable,
    WrongShape,
}

/// One decoded row from `babylon_state.schema_migration`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PersistedMigration {
    version: MigrationVersion,
    checksum: MigrationChecksum,
}

impl PersistedMigration {
    /// Decode the signed version and bounded checksum returned by `PostgreSQL`.
    ///
    /// # Errors
    /// Returns [`SchemaMigrationError`] for a non-positive version or a
    /// checksum that is not exactly one SHA-256 value.
    pub fn from_database(version: i64, checksum: &[u8]) -> Result<Self, SchemaMigrationError> {
        Ok(Self {
            version: MigrationVersion::try_from(version)?,
            checksum: MigrationChecksum::from_database_bytes(checksum)?,
        })
    }
}

/// Exact-prefix refusal raised before any pending DDL executes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SchemaEpochError {
    /// The compiled registry exceeded its fixed ceiling.
    CompiledMigrationBound { actual: usize, max: usize },
    /// The persisted ledger exceeded its fixed ceiling.
    LedgerRowBound { actual: usize, max: usize },
    /// A compiled version did not equal its one-based position.
    CompiledVersionMismatch {
        position: usize,
        expected: i64,
        actual: i64,
    },
    /// A ledger version did not equal its one-based row position.
    LedgerVersionMismatch {
        row_index: usize,
        expected: i64,
        actual: i64,
    },
    /// The database contains a version unknown to this binary.
    UnknownFutureVersion { actual: i64, latest_compiled: i64 },
    /// A persisted checksum differs from the exact compiled SQL checksum.
    LedgerChecksumMismatch { version: i64 },
    /// The built-in migration registry is malformed.
    CompiledMigration(SchemaMigrationError),
    /// A frozen census fixture was malformed in this binary.
    CensusFixture(LegacyCensusParseError),
    /// The supplied maintenance target violated the local-only connection contract.
    ConnectionTarget(LegacyAdopterError),
    /// Schema-lock acquisition failed before epoch inspection.
    Lock(LegacyAdopterError),
    /// Exact legacy adoption refused under the retained session lock.
    LegacyAdoption(LegacyAdopterError),
    /// A fresh or recorded-prefix census operation failed.
    Census(LegacyAdopterError),
    /// Explicit schema-lock release failed.
    Unlock(LegacyAdopterError),
    /// A database operation failed without retaining driver text.
    Database { operation: SchemaEpochOperation },
    /// The connected principal is not exactly the current database owner.
    CurrentUserIsNotDatabaseOwner,
    /// Marker presence selected no complete supported epoch.
    PartialAuthorityEpoch { observation: SchemaEpochObservation },
    /// Rust-owned objects exist without even the first durable ledger marker.
    UnrecordedRustEpoch,
    /// Neither exact pinned fresh census variant matched.
    FreshCensusMismatch {
        without_intel: Box<LegacyAdopterError>,
        with_intel: Box<LegacyAdopterError>,
    },
    /// Database-local default privileges or security labels were present.
    AuthoritySentinelResidue,
    /// The three owned schemas or migration ledger have the wrong shape or authority.
    EpochShapeMismatch,
    /// The bounded post-epoch catalog census did not match its frozen origin.
    EpochCensusMismatch,
    /// A ledger insert affected a count other than one.
    AffectedRowCount {
        operation: SchemaEpochOperation,
        expected: u64,
        actual: u64,
    },
    /// A commit failed and its durable outcome could not be resolved safely.
    AmbiguousCommitUnresolved { version: i64, attempts: usize },
    /// Commit ambiguity remained visible when reconciliation itself refused.
    AmbiguousCommitAndReconciliation {
        version: i64,
        reconciliation: Box<SchemaEpochError>,
    },
    /// A primary failure and explicit unlock failure both occurred.
    FailureAndCleanup {
        primary: Box<SchemaEpochError>,
        cleanup: Box<SchemaEpochError>,
    },
}

impl std::fmt::Display for SchemaEpochError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "schema epoch refused: {self:?}")
    }
}

impl std::error::Error for SchemaEpochError {}

impl From<SchemaMigrationError> for SchemaEpochError {
    fn from(error: SchemaMigrationError) -> Self {
        Self::CompiledMigration(error)
    }
}

impl From<LegacyCensusParseError> for SchemaEpochError {
    fn from(error: LegacyCensusParseError) -> Self {
        Self::CensusFixture(error)
    }
}

impl PersistedMigration {
    /// Return the positive ledger version.
    #[must_use]
    pub fn version(self) -> MigrationVersion {
        self.version
    }

    /// Return the exact persisted checksum.
    #[must_use]
    pub fn checksum(self) -> MigrationChecksum {
        self.checksum
    }
}

/// Validate, classify, and advance the closed Rust schema migration epoch.
///
/// This maintenance entry point cannot grant runtime writer authority.
///
/// # Errors
/// Returns [`SchemaEpochError`] for any target, authority, census, prefix,
/// transaction, commit-reconciliation, or cleanup failure.
pub fn migrate_schema_epoch(config: &Config) -> Result<SchemaEpochReport, SchemaEpochError> {
    validate_legacy_connection_target(config).map_err(SchemaEpochError::ConnectionTarget)?;
    let bounded = bounded_config(config);
    let mut session = LockedSession::connect(&bounded)?;
    let result = migrate_locked(&bounded, &mut session);
    session.finish(result)
}

pub(crate) fn bounded_config(config: &Config) -> Config {
    let mut bounded = config.clone();
    bounded
        .connect_timeout(LEGACY_ADOPTER_CONNECT_TIMEOUT)
        .tcp_user_timeout(LEGACY_ADOPTER_TCP_USER_TIMEOUT)
        .options(LEGACY_ADOPTER_STARTUP_OPTIONS);
    bounded
}

struct LockedSession {
    client: Option<Client>,
}

impl LockedSession {
    fn connect(config: &Config) -> Result<Self, SchemaEpochError> {
        let mut client = config
            .connect(NoTls)
            .map_err(|_| SchemaEpochError::Database {
                operation: SchemaEpochOperation::Connect,
            })?;
        acquire_lock(&mut client).map_err(SchemaEpochError::Lock)?;
        Ok(Self {
            client: Some(client),
        })
    }

    fn client(&mut self) -> &mut Client {
        self.client
            .as_mut()
            .expect("locked session always contains one client")
    }

    fn reconnect(&mut self, config: &Config) -> Result<(), SchemaEpochError> {
        self.client.take();
        *self = Self::connect(config)?;
        Ok(())
    }

    fn finish<T>(mut self, primary: Result<T, SchemaEpochError>) -> Result<T, SchemaEpochError> {
        let cleanup = self.client.as_mut().map_or(Ok(()), |client| {
            release_lock(client)
                .map_err(SchemaEpochError::Unlock)
                .map_err(Box::new)
        });
        match (primary, cleanup) {
            (Ok(value), Ok(())) => Ok(value),
            (Err(error), Ok(())) => Err(error),
            (Ok(_), Err(cleanup)) => Err(*cleanup),
            (Err(primary), Err(cleanup)) => Err(SchemaEpochError::FailureAndCleanup {
                primary: Box::new(primary),
                cleanup,
            }),
        }
    }
}

type ClientPrefixVerifier = fn(&mut Client, bool) -> Result<(), SchemaEpochError>;
type TransactionPrefixVerifier =
    for<'transaction> fn(&mut Transaction<'transaction>, bool) -> Result<(), SchemaEpochError>;

#[derive(Clone, Copy)]
struct SchemaPrefixContract {
    verify_client: ClientPrefixVerifier,
    verify_transaction: TransactionPrefixVerifier,
}

#[derive(Clone, Copy)]
struct SchemaEpochMigration {
    migration: SchemaMigration,
    prefix_contract: SchemaPrefixContract,
}

impl SchemaEpochMigration {
    fn new(migration: SchemaMigration, prefix_contract: SchemaPrefixContract) -> Self {
        Self {
            migration,
            prefix_contract,
        }
    }
}

trait MigrationRegistryEntry {
    fn migration(&self) -> SchemaMigration;
}

impl MigrationRegistryEntry for SchemaMigration {
    fn migration(&self) -> SchemaMigration {
        *self
    }
}

impl MigrationRegistryEntry for SchemaEpochMigration {
    fn migration(&self) -> SchemaMigration {
        self.migration
    }
}

const PREFIX_V1: SchemaPrefixContract = SchemaPrefixContract {
    verify_client: verify_v1_prefix_client,
    verify_transaction: verify_v1_prefix_transaction,
};
const PREFIX_V2: SchemaPrefixContract = SchemaPrefixContract {
    verify_client: verify_v2_prefix_client,
    verify_transaction: verify_v2_prefix_transaction,
};
const PREFIX_V3: SchemaPrefixContract = SchemaPrefixContract {
    verify_client: verify_v3_prefix_client,
    verify_transaction: verify_v3_prefix_transaction,
};
const PREFIX_V4: SchemaPrefixContract = SchemaPrefixContract {
    verify_client: verify_v4_prefix_client,
    verify_transaction: verify_v4_prefix_transaction,
};
const PREFIX_V5: SchemaPrefixContract = SchemaPrefixContract {
    verify_client: verify_v5_prefix_client,
    verify_transaction: verify_v5_prefix_transaction,
};

fn compiled_schema_epoch_migrations(
) -> Result<[SchemaEpochMigration; CURRENT_SCHEMA_EPOCH], SchemaMigrationError> {
    let migration_v1 = SchemaMigration::new(MigrationVersion::try_from(1)?, MIGRATION_0001_SQL)?;
    let migration_v2 = SchemaMigration::new(MigrationVersion::try_from(2)?, MIGRATION_0002_SQL)?;
    let migration_v3 = SchemaMigration::new(MigrationVersion::try_from(3)?, MIGRATION_0003_SQL)?;
    let migration_v4 = SchemaMigration::new(MigrationVersion::try_from(4)?, MIGRATION_0004_SQL)?;
    let migration_v5 = SchemaMigration::new(MigrationVersion::try_from(5)?, MIGRATION_0005_SQL)?;
    Ok([
        SchemaEpochMigration::new(migration_v1, PREFIX_V1),
        SchemaEpochMigration::new(migration_v2, PREFIX_V2),
        SchemaEpochMigration::new(migration_v3, PREFIX_V3),
        SchemaEpochMigration::new(migration_v4, PREFIX_V4),
        SchemaEpochMigration::new(migration_v5, PREFIX_V5),
    ])
}

/// Build the checked-in migration registry from exact SQL bytes.
///
/// # Errors
/// Returns [`SchemaMigrationError`] if a checked-in migration violates its
/// bounded byte contract.
pub fn compiled_schema_migrations(
) -> Result<[SchemaMigration; CURRENT_SCHEMA_EPOCH], SchemaMigrationError> {
    let compiled = compiled_schema_epoch_migrations()?;
    Ok([
        compiled[0].migration,
        compiled[1].migration,
        compiled[2].migration,
        compiled[3].migration,
        compiled[4].migration,
    ])
}

/// Verify that persisted rows are an exact prefix of contiguous migrations.
///
/// The returned count is the first pending migration index.
///
/// # Errors
/// Returns [`SchemaEpochError`] for any bound, order, future-version, or
/// checksum conflict.
pub fn validate_migration_prefix(
    compiled: &[SchemaMigration],
    persisted: &[PersistedMigration],
) -> Result<usize, SchemaEpochError> {
    validate_registry_prefix(compiled, persisted)
}

fn validate_registry_prefix<RegistryEntry: MigrationRegistryEntry>(
    compiled: &[RegistryEntry],
    persisted: &[PersistedMigration],
) -> Result<usize, SchemaEpochError> {
    check_bounds(compiled.len(), persisted.len())?;
    validate_compiled_versions(compiled)?;
    validate_persisted_rows(compiled, persisted)?;
    Ok(persisted.len())
}

fn check_bounds(compiled: usize, persisted: usize) -> Result<(), SchemaEpochError> {
    if compiled > MAX_SCHEMA_MIGRATIONS {
        return Err(SchemaEpochError::CompiledMigrationBound {
            actual: compiled,
            max: MAX_SCHEMA_MIGRATIONS,
        });
    }
    if persisted > MAX_SCHEMA_MIGRATIONS {
        return Err(SchemaEpochError::LedgerRowBound {
            actual: persisted,
            max: MAX_SCHEMA_MIGRATIONS,
        });
    }
    Ok(())
}

fn validate_compiled_versions<RegistryEntry: MigrationRegistryEntry>(
    compiled: &[RegistryEntry],
) -> Result<(), SchemaEpochError> {
    for (position, migration) in compiled.iter().enumerate().take(MAX_SCHEMA_MIGRATIONS) {
        let expected = one_based_version(position);
        let actual = migration.migration().version().as_i64();
        if actual != expected {
            return Err(SchemaEpochError::CompiledVersionMismatch {
                position,
                expected,
                actual,
            });
        }
    }
    Ok(())
}

fn validate_persisted_rows<RegistryEntry: MigrationRegistryEntry>(
    compiled: &[RegistryEntry],
    persisted: &[PersistedMigration],
) -> Result<(), SchemaEpochError> {
    let latest_compiled = i64::try_from(compiled.len()).expect("migration bound fits i64");
    for (row_index, row) in persisted.iter().enumerate().take(MAX_SCHEMA_MIGRATIONS) {
        let expected = one_based_version(row_index);
        let actual = row.version.as_i64();
        if actual != expected {
            return Err(SchemaEpochError::LedgerVersionMismatch {
                row_index,
                expected,
                actual,
            });
        }
        if actual > latest_compiled {
            return Err(SchemaEpochError::UnknownFutureVersion {
                actual,
                latest_compiled,
            });
        }
        if row.checksum != compiled[row_index].migration().checksum() {
            return Err(SchemaEpochError::LedgerChecksumMismatch { version: actual });
        }
    }
    Ok(())
}

fn one_based_version(zero_based: usize) -> i64 {
    let one_based = zero_based
        .checked_add(1)
        .expect("migration bound cannot wrap");
    i64::try_from(one_based).expect("migration bound fits i64")
}

struct InspectedEpoch {
    origin: SchemaEpochOrigin,
    legacy_origin: bool,
    persisted: Vec<PersistedMigration>,
    legacy_adoption: Option<LegacyAdoptionReport>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum MigrationAttempt {
    Committed,
    Ambiguous,
}

fn migrate_locked(
    config: &Config,
    session: &mut LockedSession,
) -> Result<SchemaEpochReport, SchemaEpochError> {
    let compiled = compiled_schema_epoch_migrations()?;
    migrate_locked_with_registry(config, session, &compiled)
}

fn migrate_locked_with_registry(
    config: &Config,
    session: &mut LockedSession,
    compiled: &[SchemaEpochMigration],
) -> Result<SchemaEpochReport, SchemaEpochError> {
    migrate_locked_with_registry_using(config, session, compiled, &mut attempt_migration)
}

fn migrate_locked_with_registry_using<Attempt>(
    config: &Config,
    session: &mut LockedSession,
    compiled: &[SchemaEpochMigration],
    attempt_migration_fn: &mut Attempt,
) -> Result<SchemaEpochReport, SchemaEpochError>
where
    Attempt: FnMut(
        &mut Client,
        SchemaEpochMigration,
        bool,
    ) -> Result<MigrationAttempt, SchemaEpochError>,
{
    validate_registry_prefix(compiled, &[])?;
    let initial = inspect_epoch(session.client(), compiled)?;
    let prior_applied = validate_registry_prefix(compiled, &initial.persisted)?;
    let legacy_origin = initial.legacy_origin;
    let mut report = SchemaEpochReport {
        origin: initial.origin,
        prior_applied,
        final_applied: prior_applied,
        applied_versions: Vec::with_capacity(compiled.len()),
        reconciled_versions: Vec::with_capacity(compiled.len()),
        legacy_adoption: initial.legacy_adoption,
    };
    let mut next_pending = prior_applied;
    for _attempt in 0..MAX_SCHEMA_MIGRATIONS {
        let Some(migration) = compiled.get(next_pending).copied() else {
            break;
        };
        next_pending = apply_with_reconciliation_using(
            config,
            session,
            compiled,
            migration,
            legacy_origin,
            &mut report,
            attempt_migration_fn,
        )?;
    }
    if next_pending < compiled.len() {
        return Err(SchemaEpochError::CompiledMigrationBound {
            actual: compiled.len(),
            max: MAX_SCHEMA_MIGRATIONS,
        });
    }
    let final_state = inspect_epoch(session.client(), compiled)?;
    let final_applied = validate_registry_prefix(compiled, &final_state.persisted)?;
    if final_state.origin != SchemaEpochOrigin::ExistingRustPrefix
        || final_applied != compiled.len()
    {
        return Err(SchemaEpochError::EpochShapeMismatch);
    }
    report.final_applied = final_applied;
    Ok(report)
}

fn apply_with_reconciliation_using<Attempt>(
    config: &Config,
    session: &mut LockedSession,
    compiled: &[SchemaEpochMigration],
    migration: SchemaEpochMigration,
    legacy_origin: bool,
    report: &mut SchemaEpochReport,
    attempt_migration_fn: &mut Attempt,
) -> Result<usize, SchemaEpochError>
where
    Attempt: FnMut(
        &mut Client,
        SchemaEpochMigration,
        bool,
    ) -> Result<MigrationAttempt, SchemaEpochError>,
{
    let target_index = usize::try_from(migration.migration.version().as_i64() - 1)
        .expect("positive bounded migration version fits usize");
    for attempt in 0..MAX_COMMIT_ATTEMPTS_PER_VERSION {
        match attempt_migration_fn(session.client(), migration, legacy_origin)? {
            MigrationAttempt::Committed => {
                report.applied_versions.push(migration.migration.version());
                return Ok(target_index + 1);
            }
            MigrationAttempt::Ambiguous => {
                let applied =
                    reconcile_ambiguous(config, session, compiled).map_err(|reconciliation| {
                        SchemaEpochError::AmbiguousCommitAndReconciliation {
                            version: migration.migration.version().as_i64(),
                            reconciliation: Box::new(reconciliation),
                        }
                    })?;
                if applied > target_index {
                    report
                        .reconciled_versions
                        .push(migration.migration.version());
                    return Ok(applied);
                }
                if applied != target_index || attempt + 1 == MAX_COMMIT_ATTEMPTS_PER_VERSION {
                    return Err(SchemaEpochError::AmbiguousCommitUnresolved {
                        version: migration.migration.version().as_i64(),
                        attempts: attempt + 1,
                    });
                }
            }
        }
    }
    Err(SchemaEpochError::AmbiguousCommitUnresolved {
        version: migration.migration.version().as_i64(),
        attempts: MAX_COMMIT_ATTEMPTS_PER_VERSION,
    })
}

fn reconcile_ambiguous(
    config: &Config,
    session: &mut LockedSession,
    compiled: &[SchemaEpochMigration],
) -> Result<usize, SchemaEpochError> {
    session.reconnect(config)?;
    let reconciled = inspect_epoch(session.client(), compiled)?;
    validate_registry_prefix(compiled, &reconciled.persisted)
}

fn inspect_epoch(
    client: &mut Client,
    compiled: &[SchemaEpochMigration],
) -> Result<InspectedEpoch, SchemaEpochError> {
    verify_database_owner(client)?;
    let observation = read_observation(client)?;
    match classify_observation(observation)? {
        SchemaEpochOrigin::Fresh => {
            verify_fresh_epoch(client)?;
            Ok(InspectedEpoch {
                origin: SchemaEpochOrigin::Fresh,
                legacy_origin: false,
                persisted: Vec::new(),
                legacy_adoption: None,
            })
        }
        SchemaEpochOrigin::ExactLegacy => {
            let legacy_adoption =
                verify_under_lock(client).map_err(SchemaEpochError::LegacyAdoption)?;
            Ok(InspectedEpoch {
                origin: SchemaEpochOrigin::ExactLegacy,
                legacy_origin: true,
                persisted: Vec::new(),
                legacy_adoption: Some(legacy_adoption),
            })
        }
        SchemaEpochOrigin::ExistingRustPrefix => {
            let persisted = read_ledger(client, compiled.len())?;
            require_recorded_rust_prefix(&persisted)?;
            let applied = validate_registry_prefix(compiled, &persisted)?;
            let legacy_origin = observation.legacy_stamp == SchemaEpochRelation::ExactTable;
            verify_recorded_prefix_client(client, compiled, applied, legacy_origin)?;
            Ok(InspectedEpoch {
                origin: SchemaEpochOrigin::ExistingRustPrefix,
                legacy_origin,
                persisted,
                legacy_adoption: None,
            })
        }
    }
}

pub(crate) fn inspect_schema_epoch_under_lock(
    client: &mut Client,
) -> Result<(SchemaEpochOrigin, usize), SchemaEpochError> {
    let compiled = compiled_schema_epoch_migrations()?;
    validate_registry_prefix(&compiled, &[])?;
    let inspected = inspect_epoch(client, &compiled)?;
    let applied = validate_registry_prefix(&compiled, &inspected.persisted)?;
    Ok((inspected.origin, applied))
}

fn require_recorded_rust_prefix(persisted: &[PersistedMigration]) -> Result<(), SchemaEpochError> {
    if persisted.is_empty() {
        Err(SchemaEpochError::UnrecordedRustEpoch)
    } else {
        Ok(())
    }
}

fn verify_recorded_prefix_client(
    client: &mut Client,
    compiled: &[SchemaEpochMigration],
    applied: usize,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    let prefix_index = applied
        .checked_sub(1)
        .ok_or(SchemaEpochError::UnrecordedRustEpoch)?;
    let contract = compiled
        .get(prefix_index)
        .ok_or(SchemaEpochError::EpochShapeMismatch)?
        .prefix_contract;
    (contract.verify_client)(client, legacy_origin)
}

fn verify_database_owner(client: &mut Client) -> Result<(), SchemaEpochError> {
    let row = client
        .query_opt(OWNER_SQL, &[])
        .map_err(|_| database_error(SchemaEpochOperation::VerifyOwner))?
        .ok_or_else(|| database_error(SchemaEpochOperation::VerifyOwner))?;
    let is_owner = row
        .try_get::<_, bool>(0)
        .map_err(|_| database_error(SchemaEpochOperation::VerifyOwner))?;
    if is_owner {
        Ok(())
    } else {
        Err(SchemaEpochError::CurrentUserIsNotDatabaseOwner)
    }
}

fn read_observation(client: &mut Client) -> Result<SchemaEpochObservation, SchemaEpochError> {
    let row = client
        .query_one(MARKERS_SQL, &[])
        .map_err(|_| database_error(SchemaEpochOperation::Classify))?;
    Ok(SchemaEpochObservation {
        schemas: SchemaEpochSchemas {
            babylon_ref: decode_bool(&row, 0, SchemaEpochOperation::Classify)?,
            babylon_state: decode_bool(&row, 1, SchemaEpochOperation::Classify)?,
            babylon_meta: decode_bool(&row, 2, SchemaEpochOperation::Classify)?,
        },
        ledger: decode_relation_marker(&row, 3, 4)?,
        legacy_stamp: decode_relation_marker(&row, 5, 6)?,
    })
}

fn classify_observation(
    observation: SchemaEpochObservation,
) -> Result<SchemaEpochOrigin, SchemaEpochError> {
    let no_authority = !observation.schemas.babylon_ref && !observation.schemas.babylon_state;
    let fresh = no_authority
        && !observation.schemas.babylon_meta
        && observation.ledger == SchemaEpochRelation::Absent
        && observation.legacy_stamp == SchemaEpochRelation::Absent;
    if fresh {
        return Ok(SchemaEpochOrigin::Fresh);
    }
    let legacy = no_authority
        && observation.ledger == SchemaEpochRelation::Absent
        && observation.legacy_stamp == SchemaEpochRelation::ExactTable;
    if legacy {
        return Ok(SchemaEpochOrigin::ExactLegacy);
    }
    let rust_prefix = observation.schemas.babylon_ref
        && observation.schemas.babylon_state
        && observation.schemas.babylon_meta
        && observation.ledger == SchemaEpochRelation::ExactTable
        && observation.legacy_stamp != SchemaEpochRelation::WrongShape;
    if rust_prefix {
        return Ok(SchemaEpochOrigin::ExistingRustPrefix);
    }
    Err(SchemaEpochError::PartialAuthorityEpoch { observation })
}

fn decode_relation_marker(
    row: &Row,
    exists_index: usize,
    exact_index: usize,
) -> Result<SchemaEpochRelation, SchemaEpochError> {
    let exists = decode_bool(row, exists_index, SchemaEpochOperation::Classify)?;
    let exact = decode_bool(row, exact_index, SchemaEpochOperation::Classify)?;
    Ok(match (exists, exact) {
        (false, false) => SchemaEpochRelation::Absent,
        (true, true) => SchemaEpochRelation::ExactTable,
        _ => SchemaEpochRelation::WrongShape,
    })
}

fn verify_fresh_epoch(client: &mut Client) -> Result<(), SchemaEpochError> {
    verify_authority_sentinels_client(client)?;
    let actual = catalog_census_under_lock(client, true).map_err(SchemaEpochError::Census)?;
    compare_fresh_census(actual.as_slice())
}

fn compare_fresh_census(actual: &[LegacyCensusEntry]) -> Result<(), SchemaEpochError> {
    let without_intel = parse_legacy_census_fixture(FRESH_CENSUS)?;
    let Err(without_intel) = compare_legacy_census(&without_intel, actual) else {
        return Ok(());
    };
    let with_intel = parse_legacy_census_fixture(FRESH_CENSUS_WITH_INTEL)?;
    match compare_legacy_census(&with_intel, actual) {
        Ok(_) => Ok(()),
        Err(with_intel) => Err(SchemaEpochError::FreshCensusMismatch {
            without_intel: Box::new(without_intel),
            with_intel: Box::new(with_intel),
        }),
    }
}

fn verify_v1_prefix_client(
    client: &mut Client,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    verify_epoch_shape_client(client, EPOCH_V1_SHAPE_SQL)?;
    verify_post_epoch_census_client(client, legacy_origin, SchemaEpochPrefix::V1)
}

fn verify_v1_prefix_transaction(
    transaction: &mut Transaction<'_>,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    verify_epoch_shape_transaction(transaction, EPOCH_V1_SHAPE_SQL)?;
    verify_post_epoch_census_transaction(transaction, legacy_origin, SchemaEpochPrefix::V1)
}

fn verify_v2_prefix_client(
    client: &mut Client,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    verify_epoch_shape_client(client, EPOCH_V2_SHAPE_SQL)?;
    verify_post_epoch_census_client(client, legacy_origin, SchemaEpochPrefix::V2)
}

fn verify_v2_prefix_transaction(
    transaction: &mut Transaction<'_>,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    verify_epoch_shape_transaction(transaction, EPOCH_V2_SHAPE_SQL)?;
    verify_post_epoch_census_transaction(transaction, legacy_origin, SchemaEpochPrefix::V2)
}

fn verify_v3_prefix_client(
    client: &mut Client,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    verify_epoch_shape_client(client, EPOCH_V3_SHAPE_SQL)?;
    verify_post_epoch_census_client(client, legacy_origin, SchemaEpochPrefix::V3)
}

fn verify_v3_prefix_transaction(
    transaction: &mut Transaction<'_>,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    verify_epoch_shape_transaction(transaction, EPOCH_V3_SHAPE_SQL)?;
    verify_post_epoch_census_transaction(transaction, legacy_origin, SchemaEpochPrefix::V3)
}

fn verify_v4_prefix_client(
    client: &mut Client,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    verify_epoch_shape_client(client, EPOCH_V4_SHAPE_SQL)?;
    verify_post_epoch_census_client(client, legacy_origin, SchemaEpochPrefix::V4)
}

fn verify_v4_prefix_transaction(
    transaction: &mut Transaction<'_>,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    verify_epoch_shape_transaction(transaction, EPOCH_V4_SHAPE_SQL)?;
    verify_post_epoch_census_transaction(transaction, legacy_origin, SchemaEpochPrefix::V4)
}

fn verify_v5_prefix_client(
    client: &mut Client,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    verify_epoch_shape_client(client, EPOCH_V5_SHAPE_SQL)?;
    verify_post_epoch_census_client(client, legacy_origin, SchemaEpochPrefix::V5)
}

fn verify_v5_prefix_transaction(
    transaction: &mut Transaction<'_>,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    verify_epoch_shape_transaction(transaction, EPOCH_V5_SHAPE_SQL)?;
    verify_post_epoch_census_transaction(transaction, legacy_origin, SchemaEpochPrefix::V5)
}

fn verify_post_epoch_census_client(
    client: &mut Client,
    legacy_origin: bool,
    prefix: SchemaEpochPrefix,
) -> Result<(), SchemaEpochError> {
    verify_authority_sentinels_client(client)?;
    let actual = catalog_census_under_lock(client, false).map_err(SchemaEpochError::Census)?;
    verify_post_epoch_census(actual.as_slice(), legacy_origin, prefix)
}

fn verify_post_epoch_census_transaction(
    transaction: &mut Transaction<'_>,
    legacy_origin: bool,
    prefix: SchemaEpochPrefix,
) -> Result<(), SchemaEpochError> {
    verify_authority_sentinels_transaction(transaction)?;
    let actual = read_census_rows(transaction).map_err(SchemaEpochError::Census)?;
    verify_post_epoch_census(actual.as_slice(), legacy_origin, prefix)
}

fn verify_post_epoch_census(
    actual: &[LegacyCensusEntry],
    legacy_origin: bool,
    prefix: SchemaEpochPrefix,
) -> Result<(), SchemaEpochError> {
    let mut baseline = Vec::with_capacity(actual.len());
    let mut epoch = Vec::with_capacity(25);
    for entry in actual.iter().take(MAX_LEGACY_CENSUS_ROWS) {
        if is_epoch_entry(entry, legacy_origin, prefix) {
            epoch.push(entry.clone());
        } else {
            baseline.push(entry.clone());
        }
    }
    let epoch_fixture = match (prefix, legacy_origin) {
        (SchemaEpochPrefix::V1, true) => EPOCH_OWNED_CENSUS_V1,
        (SchemaEpochPrefix::V1, false) => EPOCH_OWNED_FRESH_CENSUS_V1,
        (SchemaEpochPrefix::V2, true) => EPOCH_OWNED_CENSUS_V2,
        (SchemaEpochPrefix::V2, false) => EPOCH_OWNED_FRESH_CENSUS_V2,
        (SchemaEpochPrefix::V3, true) => EPOCH_OWNED_CENSUS_V3,
        (SchemaEpochPrefix::V3, false) => EPOCH_OWNED_FRESH_CENSUS_V3,
        (SchemaEpochPrefix::V4, true) => EPOCH_OWNED_CENSUS_V4,
        (SchemaEpochPrefix::V4, false) => EPOCH_OWNED_FRESH_CENSUS_V4,
        (SchemaEpochPrefix::V5, true) => EPOCH_OWNED_CENSUS_V5,
        (SchemaEpochPrefix::V5, false) => EPOCH_OWNED_FRESH_CENSUS_V5,
    };
    let expected_epoch = parse_legacy_census_fixture(epoch_fixture)?;
    compare_legacy_census(&expected_epoch, epoch.as_slice())
        .map_err(|_| SchemaEpochError::EpochCensusMismatch)?;
    if legacy_origin {
        let expected = crate::legacy_adopter::expected_legacy_census()?;
        compare_legacy_census(&expected, baseline.as_slice())
            .map(|_| ())
            .map_err(|_| SchemaEpochError::EpochCensusMismatch)
    } else {
        compare_fresh_census(baseline.as_slice())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum SchemaEpochPrefix {
    V1,
    V2,
    V3,
    V4,
    V5,
}

fn is_epoch_entry(
    entry: &LegacyCensusEntry,
    legacy_origin: bool,
    prefix: SchemaEpochPrefix,
) -> bool {
    let key = entry.key();
    let migration_relation = key.kind() == LegacyObjectKind::Relation
        && key.schema() == "babylon_state"
        && key.name() == "schema_migration";
    let h3_relation = matches!(
        prefix,
        SchemaEpochPrefix::V2
            | SchemaEpochPrefix::V3
            | SchemaEpochPrefix::V4
            | SchemaEpochPrefix::V5
    ) && key.kind() == LegacyObjectKind::Relation
        && key.schema() == "babylon_ref"
        && key.name() == "h3_cell";
    let h3_cohort_relation = matches!(
        prefix,
        SchemaEpochPrefix::V3 | SchemaEpochPrefix::V4 | SchemaEpochPrefix::V5
    ) && key.kind() == LegacyObjectKind::Relation
        && key.schema() == "babylon_ref"
        && matches!(
            key.name(),
            "h3_reference_cohort" | "h3_reference_membership"
        );
    let committed_tick_relation = matches!(prefix, SchemaEpochPrefix::V4 | SchemaEpochPrefix::V5)
        && key.kind() == LegacyObjectKind::Relation
        && key.schema() == "babylon_state"
        && matches!(
            key.name(),
            "campaign"
                | "tick_commit"
                | "tick_graph_row"
                | "tick_state_row"
                | "tick_event_row"
                | "tick_subsystem_row"
                | "tick_conservation_row"
                | "tick_boundary_flow_row"
                | "tick_checkpoint_row"
                | "tick_archive_dirty_receipt_row"
        );
    let owned_schema = key.kind() == LegacyObjectKind::Schema
        && key.schema() == "pg_namespace"
        && matches!(key.name(), "babylon_ref" | "babylon_state");
    let fresh_meta = !legacy_origin
        && key.kind() == LegacyObjectKind::SchemaGrant
        && key.schema() == "pg_namespace"
        && key.name() == "babylon_meta";
    let spatial_reference_relation = prefix == SchemaEpochPrefix::V5
        && key.kind() == LegacyObjectKind::Relation
        && key.schema() == "babylon_ref"
        && matches!(
            key.name(),
            "reference_product"
                | "county_identity"
                | "place_identity"
                | "h3_land_fraction"
                | "h3_population_count"
                | "h3_workplace_count"
                | "county_h3_land_area"
                | "county_place_h3_land_area"
        );
    migration_relation
        || h3_relation
        || h3_cohort_relation
        || committed_tick_relation
        || spatial_reference_relation
        || owned_schema
        || fresh_meta
}

fn verify_authority_sentinels_client(client: &mut Client) -> Result<(), SchemaEpochError> {
    let row = client
        .query_one(FRESH_SENTINELS_SQL, &[])
        .map_err(|_| database_error(SchemaEpochOperation::FreshSentinels))?;
    require_authority_sentinels(&row)
}

fn verify_authority_sentinels_transaction(
    transaction: &mut Transaction<'_>,
) -> Result<(), SchemaEpochError> {
    let row = transaction
        .query_one(FRESH_SENTINELS_SQL, &[])
        .map_err(|_| database_error(SchemaEpochOperation::FreshSentinels))?;
    require_authority_sentinels(&row)
}

fn require_authority_sentinels(row: &Row) -> Result<(), SchemaEpochError> {
    let mut clean = true;
    for index in 0..3 {
        clean &= decode_bool(row, index, SchemaEpochOperation::FreshSentinels)?;
    }
    if clean {
        Ok(())
    } else {
        Err(SchemaEpochError::AuthoritySentinelResidue)
    }
}

fn read_ledger(
    client: &mut Client,
    compiled_count: usize,
) -> Result<Vec<PersistedMigration>, SchemaEpochError> {
    let bounded_count = compiled_count.min(MAX_SCHEMA_MIGRATIONS);
    let query_count = bounded_count
        .checked_add(1)
        .expect("migration bound cannot wrap");
    let limit = i64::try_from(query_count).expect("ledger bound fits i64");
    let rows = client
        .query(LEDGER_SQL, &[&limit])
        .map_err(|_| database_error(SchemaEpochOperation::ReadLedger))?;
    decode_ledger_rows(rows.as_slice(), query_count)
}

fn decode_ledger_rows(
    rows: &[Row],
    query_count: usize,
) -> Result<Vec<PersistedMigration>, SchemaEpochError> {
    let mut persisted = Vec::with_capacity(rows.len().min(query_count));
    for row in rows.iter().take(query_count) {
        let version = row
            .try_get::<_, i64>(0)
            .map_err(|_| database_error(SchemaEpochOperation::ReadLedger))?;
        let checksum = row
            .try_get::<_, Vec<u8>>(1)
            .map_err(|_| database_error(SchemaEpochOperation::ReadLedger))?;
        let decoded = PersistedMigration::from_database(version, checksum.as_slice())
            .map_err(|_| database_error(SchemaEpochOperation::ReadLedger))?;
        persisted.push(decoded);
    }
    Ok(persisted)
}

fn attempt_migration(
    client: &mut Client,
    migration: SchemaEpochMigration,
    legacy_origin: bool,
) -> Result<MigrationAttempt, SchemaEpochError> {
    let mut transaction = begin_migration_transaction(client)?;
    execute_migration_before_marker(&mut transaction, migration, legacy_origin)?;
    insert_ledger_marker(&mut transaction, migration.migration)?;
    commit_migration(transaction)
}

fn commit_migration(transaction: Transaction<'_>) -> Result<MigrationAttempt, SchemaEpochError> {
    match transaction.commit() {
        Ok(()) => Ok(MigrationAttempt::Committed),
        Err(error) if error.as_db_error().is_some() => {
            Err(database_error(SchemaEpochOperation::CommitMigration))
        }
        Err(_) => Ok(MigrationAttempt::Ambiguous),
    }
}

fn begin_migration_transaction(client: &mut Client) -> Result<Transaction<'_>, SchemaEpochError> {
    client
        .build_transaction()
        .isolation_level(IsolationLevel::Serializable)
        .read_only(false)
        .start()
        .map_err(|_| database_error(SchemaEpochOperation::BeginMigration))
}

fn execute_migration_before_marker(
    transaction: &mut Transaction<'_>,
    migration: SchemaEpochMigration,
    legacy_origin: bool,
) -> Result<(), SchemaEpochError> {
    prepare_migration_transaction(transaction)?;
    transaction
        .batch_execute(migration.migration.sql())
        .map_err(|_| database_error(SchemaEpochOperation::ExecuteMigration))?;
    (migration.prefix_contract.verify_transaction)(transaction, legacy_origin)
}

fn prepare_migration_transaction(
    transaction: &mut Transaction<'_>,
) -> Result<(), SchemaEpochError> {
    transaction
        .batch_execute(WRITE_LOCAL_SETTINGS_SQL)
        .map_err(|_| database_error(SchemaEpochOperation::SetMigrationSettings))?;
    let row = transaction
        .query_one(WRITE_SETTINGS_SQL, &[])
        .map_err(|_| database_error(SchemaEpochOperation::VerifyMigrationSettings))?;
    let expected = ["serializable", "off", "pg_catalog", "on", "5s", "5s", "5s"];
    for (index, value) in expected.iter().enumerate().take(7) {
        let actual = row
            .try_get::<_, String>(index)
            .map_err(|_| database_error(SchemaEpochOperation::VerifyMigrationSettings))?;
        if actual != *value {
            return Err(database_error(
                SchemaEpochOperation::VerifyMigrationSettings,
            ));
        }
    }
    Ok(())
}

fn insert_ledger_marker(
    transaction: &mut Transaction<'_>,
    migration: SchemaMigration,
) -> Result<(), SchemaEpochError> {
    let version = migration.version().as_i64();
    let migration_checksum = migration.checksum();
    let checksum: &[u8] = migration_checksum.as_bytes();
    let affected = transaction
        .execute(INSERT_LEDGER_SQL, &[&version, &checksum])
        .map_err(|_| database_error(SchemaEpochOperation::InsertLedger))?;
    if affected == 1 {
        Ok(())
    } else {
        Err(SchemaEpochError::AffectedRowCount {
            operation: SchemaEpochOperation::InsertLedger,
            expected: 1,
            actual: affected,
        })
    }
}

fn verify_epoch_shape_client(client: &mut Client, shape_sql: &str) -> Result<(), SchemaEpochError> {
    let row = client
        .query_one(shape_sql, &[])
        .map_err(|_| database_error(SchemaEpochOperation::VerifyEpochShape))?;
    require_epoch_shape(&row)
}

fn verify_epoch_shape_transaction(
    transaction: &mut Transaction<'_>,
    shape_sql: &str,
) -> Result<(), SchemaEpochError> {
    let row = transaction
        .query_one(shape_sql, &[])
        .map_err(|_| database_error(SchemaEpochOperation::VerifyEpochShape))?;
    require_epoch_shape(&row)
}

fn require_epoch_shape(row: &Row) -> Result<(), SchemaEpochError> {
    if decode_bool(row, 0, SchemaEpochOperation::VerifyEpochShape)? {
        Ok(())
    } else {
        Err(SchemaEpochError::EpochShapeMismatch)
    }
}

fn decode_bool(
    row: &Row,
    index: usize,
    operation: SchemaEpochOperation,
) -> Result<bool, SchemaEpochError> {
    row.try_get(index).map_err(|_| database_error(operation))
}

fn database_error(operation: SchemaEpochOperation) -> SchemaEpochError {
    SchemaEpochError::Database { operation }
}

#[cfg(test)]
mod pure_tests {
    use super::*;

    #[test]
    fn compiled_registry_binds_each_migration_to_a_prefix_contract() {
        let compiled = compiled_schema_epoch_migrations().unwrap();

        assert_eq!(compiled.len(), 5);
        assert_eq!(compiled[0].migration.version().as_i64(), 1);
        assert_eq!(compiled[1].migration.version().as_i64(), 2);
        assert_eq!(compiled[2].migration.version().as_i64(), 3);
        assert_eq!(compiled[3].migration.version().as_i64(), 4);
        assert_eq!(compiled[4].migration.version().as_i64(), 5);
    }

    #[test]
    fn marker_state_machine_accepts_only_complete_lane_candidates() {
        assert_eq!(
            classify_observation(observation(
                [false, false, false],
                SchemaEpochRelation::Absent,
                SchemaEpochRelation::Absent,
            )),
            Ok(SchemaEpochOrigin::Fresh)
        );
        assert_eq!(
            classify_observation(observation(
                [false, false, true],
                SchemaEpochRelation::Absent,
                SchemaEpochRelation::ExactTable,
            )),
            Ok(SchemaEpochOrigin::ExactLegacy)
        );
        for stamp in [SchemaEpochRelation::Absent, SchemaEpochRelation::ExactTable] {
            assert_eq!(
                classify_observation(observation(
                    [true, true, true],
                    SchemaEpochRelation::ExactTable,
                    stamp,
                )),
                Ok(SchemaEpochOrigin::ExistingRustPrefix)
            );
        }
    }

    #[test]
    fn partial_or_wrong_shape_markers_refuse_with_the_exact_observation() {
        let cases = [
            observation(
                [true, false, false],
                SchemaEpochRelation::Absent,
                SchemaEpochRelation::Absent,
            ),
            observation(
                [true, true, true],
                SchemaEpochRelation::Absent,
                SchemaEpochRelation::Absent,
            ),
            observation(
                [true, true, true],
                SchemaEpochRelation::WrongShape,
                SchemaEpochRelation::Absent,
            ),
            observation(
                [true, true, true],
                SchemaEpochRelation::ExactTable,
                SchemaEpochRelation::WrongShape,
            ),
        ];
        for observation in cases {
            assert_eq!(
                classify_observation(observation),
                Err(SchemaEpochError::PartialAuthorityEpoch { observation })
            );
        }
    }

    #[test]
    fn an_existing_rust_epoch_requires_a_recorded_prefix() {
        assert_eq!(
            require_recorded_rust_prefix(&[]),
            Err(SchemaEpochError::UnrecordedRustEpoch)
        );
    }

    fn observation(
        schemas: [bool; 3],
        ledger: SchemaEpochRelation,
        legacy_stamp: SchemaEpochRelation,
    ) -> SchemaEpochObservation {
        SchemaEpochObservation {
            schemas: SchemaEpochSchemas {
                babylon_ref: schemas[0],
                babylon_state: schemas[1],
                babylon_meta: schemas[2],
            },
            ledger,
            legacy_stamp,
        }
    }
}

#[cfg(test)]
mod live_rollback_tests {
    use std::str::FromStr;
    use std::time::Instant;

    use postgres::error::SqlState;

    use super::*;

    const DSN_ENV: &str = "BABYLON_LEGACY_ADOPTER_TEST_DSN";
    const ACK_ENV: &str = "BABYLON_LEGACY_ADOPTER_DISPOSABLE_ACK";
    const ACK: &str = "I_UNDERSTAND_PER20_DROPS_SCRATCH_DATABASES_ROLES_AND_CREATED_BABYLON_INTEL";
    const CANARY_ENV: &str = "BABYLON_LEGACY_ADOPTER_DISPOSABLE_CANARY";
    const BACKEND_TERMINATION_TIMEOUT_MILLIS: i64 = 5_000;

    #[test]
    #[ignore = "requires the task-owned disposable PER-20 PostgreSQL runtime"]
    fn rollback_and_ambiguous_commit_reconciliation_are_atomic() {
        let base = validated_base_config();
        verify_post_ddl_rollback(&base);
        verify_definite_commit_failure(&base);
        verify_killed_commit_retry(&base);
        verify_committed_reconciliation(&base);
        verify_multi_version_upgrade_and_idempotence(&base);
        verify_v2_pre_marker_rollback(&base);
        verify_v2_marker_rollback(&base);
        verify_v2_killed_commit_retry(&base);
        verify_v2_committed_reconciliation(&base);
        verify_v3_pre_marker_rollback(&base);
        verify_v3_marker_rollback(&base);
        verify_v3_killed_commit_retry(&base);
        verify_v3_committed_reconciliation(&base);
        verify_v4_pre_marker_rollback(&base);
        verify_v4_marker_rollback(&base);
        verify_v4_killed_commit_retry(&base);
        verify_v4_committed_reconciliation(&base);
        verify_v5_pre_marker_rollback(&base);
        verify_v5_marker_rollback(&base);
        verify_v5_killed_commit_retry(&base);
        verify_v5_committed_reconciliation(&base);
        verify_leap_ahead_reconciliation(&base);
        verify_h3_installer_commit_protocol(&base);
    }

    #[test]
    #[ignore = "requires the task-owned disposable PER-20 PostgreSQL runtime"]
    fn migration_four_rollback_and_ambiguous_commit_reconciliation_are_atomic() {
        let base = validated_base_config();
        verify_v4_pre_marker_rollback(&base);
        verify_v4_marker_rollback(&base);
        verify_v4_killed_commit_retry(&base);
        verify_v4_committed_reconciliation(&base);
    }

    #[test]
    #[ignore = "requires the task-owned disposable PER-278 PostgreSQL runtime"]
    fn migration_five_rollback_and_ambiguous_commit_reconciliation_are_atomic() {
        let base = validated_base_config();
        verify_v5_pre_marker_rollback(&base);
        verify_v5_marker_rollback(&base);
        verify_v5_killed_commit_retry(&base);
        verify_v5_committed_reconciliation(&base);
        let database = TestDatabase::create(&base, "spatialproducts");
        let config = database.config(&base);
        assert_eq!(migrate_schema_epoch(&config).unwrap().final_applied, 5);
        crate::spatial_reference_installer::live_postgres_tests::verify_commit_protocol(
            &config, &base,
        );
        database.cleanup();
    }

    #[test]
    #[ignore = "requires the task-owned disposable PER-20 PostgreSQL runtime"]
    fn h3_installer_rollback_and_ambiguous_commit_reconciliation_are_atomic() {
        let base = validated_base_config();
        verify_h3_installer_commit_protocol(&base);
    }

    #[test]
    #[ignore = "requires the task-owned disposable PER-20 PostgreSQL runtime"]
    fn h3_installer_membership_cardinality_is_bounded() {
        let base = validated_base_config();
        let database = TestDatabase::create(&base, "hcardinality");
        let config = database.config(&base);
        assert_eq!(migrate_schema_epoch(&config).unwrap().final_applied, 5);
        crate::h3_reference_installer::live_postgres_tests::verify_membership_cardinality_bound(
            &config,
        );
        database.cleanup();
    }

    fn verify_h3_installer_commit_protocol(base: &Config) {
        let suite_started = Instant::now();
        let rollback_retry = TestDatabase::create(base, "hrollback");
        let rollback_config = rollback_retry.config(base);
        assert_eq!(
            migrate_schema_epoch(&rollback_config)
                .unwrap()
                .final_applied,
            5
        );
        crate::h3_reference_installer::live_postgres_tests::verify_rollback_and_killed_retry(
            &rollback_config,
            base,
            suite_started,
        );
        rollback_retry.cleanup();

        let reconciliation = TestDatabase::create(base, "hreconcile");
        let reconciliation_config = reconciliation.config(base);
        assert_eq!(
            migrate_schema_epoch(&reconciliation_config)
                .unwrap()
                .final_applied,
            5
        );
        crate::h3_reference_installer::live_postgres_tests::verify_committed_reconciliation(
            &reconciliation_config,
            base,
            suite_started,
        );
        reconciliation.cleanup();
    }

    fn verify_post_ddl_rollback(base: &Config) {
        let database = TestDatabase::create(base, "rollback");
        let config = database.config(base);
        let compiled = compiled_schema_epoch_migrations().unwrap();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let initial = inspect_epoch(session.client(), &compiled).unwrap();
        assert_eq!(initial.origin, SchemaEpochOrigin::Fresh);

        let mut transaction = begin_migration_transaction(session.client()).unwrap();
        execute_migration_before_marker(&mut transaction, compiled[0], false).unwrap();
        let failure = transaction.batch_execute("SELECT 1 / 0").unwrap_err();
        assert_eq!(failure.code(), Some(&SqlState::DIVISION_BY_ZERO));
        transaction.rollback().unwrap();
        session.finish(Ok(())).unwrap();

        let mut client = config.connect(NoTls).unwrap();
        assert_eq!(read_observation(&mut client).unwrap(), empty_observation());
        drop(client);
        let retry = migrate_schema_epoch(&config).unwrap();
        assert_eq!(retry.origin, SchemaEpochOrigin::Fresh);
        assert_eq!(retry.final_applied, 5);
        assert_eq!(retry.applied_versions.len(), 5);
        database.cleanup();
    }

    fn verify_definite_commit_failure(base: &Config) {
        let database = TestDatabase::create(base, "commiterror");
        let config = database.config(base);
        let compiled = compiled_schema_epoch_migrations().unwrap();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut transaction = begin_migration_transaction(session.client()).unwrap();
        execute_migration_before_marker(&mut transaction, compiled[0], false).unwrap();
        transaction
            .batch_execute(
                "CREATE TEMP TABLE deferred_collision (\
                    value INTEGER, UNIQUE (value) DEFERRABLE INITIALLY DEFERRED\
                 ); \
                 INSERT INTO deferred_collision (value) VALUES (1), (1)",
            )
            .unwrap();
        insert_ledger_marker(&mut transaction, compiled[0].migration).unwrap();
        assert_eq!(
            commit_migration(transaction),
            Err(SchemaEpochError::Database {
                operation: SchemaEpochOperation::CommitMigration,
            })
        );
        session.finish(Ok(())).unwrap();

        let mut client = config.connect(NoTls).unwrap();
        assert_eq!(read_observation(&mut client).unwrap(), empty_observation());
        database.cleanup();
    }

    fn verify_killed_commit_retry(base: &Config) {
        let database = TestDatabase::create(base, "killed");
        let config = database.config(base);
        let bounded = bounded_config(&config);
        let compiled = compiled_schema_epoch_migrations().unwrap();
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut report = empty_report();
        let mut first_attempt = true;
        let mut attempt =
            |client: &mut Client, migration: SchemaEpochMigration, legacy_origin: bool| {
                if first_attempt {
                    first_attempt = false;
                    killed_before_commit_attempt(client, migration, legacy_origin, base)
                } else {
                    attempt_migration(client, migration, legacy_origin)
                }
            };
        apply_with_reconciliation_using(
            &bounded,
            &mut session,
            &compiled,
            compiled[0],
            false,
            &mut report,
            &mut attempt,
        )
        .unwrap();
        session.finish(Ok(())).unwrap();
        assert_eq!(
            report.applied_versions,
            vec![compiled[0].migration.version()]
        );
        assert!(report.reconciled_versions.is_empty());
        let completed = migrate_schema_epoch(&config).unwrap();
        assert_eq!(completed.prior_applied, 1);
        assert_eq!(completed.final_applied, 5);
        database.cleanup();
    }

    fn verify_committed_reconciliation(base: &Config) {
        let database = TestDatabase::create(base, "reconciled");
        let config = database.config(base);
        let bounded = bounded_config(&config);
        let compiled = compiled_schema_epoch_migrations().unwrap();
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut report = empty_report();
        let mut first_attempt = true;
        let mut attempt = |client: &mut Client, migration, legacy_origin| {
            let outcome = attempt_migration(client, migration, legacy_origin)?;
            if first_attempt {
                first_attempt = false;
                assert_eq!(outcome, MigrationAttempt::Committed);
                Ok(MigrationAttempt::Ambiguous)
            } else {
                Ok(outcome)
            }
        };
        apply_with_reconciliation_using(
            &bounded,
            &mut session,
            &compiled,
            compiled[0],
            false,
            &mut report,
            &mut attempt,
        )
        .unwrap();
        session.finish(Ok(())).unwrap();
        assert!(report.applied_versions.is_empty());
        assert_eq!(
            report.reconciled_versions,
            vec![compiled[0].migration.version()]
        );
        let completed = migrate_schema_epoch(&config).unwrap();
        assert_eq!(completed.prior_applied, 1);
        assert_eq!(completed.final_applied, 5);
        database.cleanup();
    }

    fn verify_multi_version_upgrade_and_idempotence(base: &Config) {
        let database = TestDatabase::create(base, "vupgrade");
        let config = database.config(base);
        establish_v1(&config);
        let registry = production_registry();
        assert_v1_prefix(&config, &registry);

        let first = migrate_schema_epoch(&config).unwrap();
        assert_eq!(first.origin, SchemaEpochOrigin::ExistingRustPrefix);
        assert_eq!(first.prior_applied, 1);
        assert_eq!(first.final_applied, 5);
        assert_eq!(
            first.applied_versions,
            vec![
                registry[1].migration.version(),
                registry[2].migration.version(),
                registry[3].migration.version(),
                registry[4].migration.version()
            ]
        );
        assert!(first.reconciled_versions.is_empty());
        let before = v5_snapshot(&config, &registry);

        let second = migrate_schema_epoch(&config).unwrap();
        assert_eq!(second.prior_applied, 5);
        assert_eq!(second.final_applied, 5);
        assert!(second.applied_versions.is_empty());
        assert!(second.reconciled_versions.is_empty());
        assert_eq!(v5_snapshot(&config, &registry), before);
        database.cleanup();
    }

    fn verify_v2_pre_marker_rollback(base: &Config) {
        let database = TestDatabase::create(base, "vprerollback");
        let config = database.config(base);
        establish_v1(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut transaction = begin_migration_transaction(session.client()).unwrap();
        execute_migration_before_marker(&mut transaction, registry[1], false).unwrap();
        force_transaction_rollback(&mut transaction);
        transaction.rollback().unwrap();
        session.finish(Ok(())).unwrap();

        assert_v1_prefix(&config, &registry);
        assert_eq!(migrate_schema_epoch(&config).unwrap().final_applied, 5);
        database.cleanup();
    }

    fn verify_v2_marker_rollback(base: &Config) {
        let database = TestDatabase::create(base, "vmarkerrollback");
        let config = database.config(base);
        establish_v1(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut transaction = begin_migration_transaction(session.client()).unwrap();
        execute_migration_before_marker(&mut transaction, registry[1], false).unwrap();
        insert_ledger_marker(&mut transaction, registry[1].migration).unwrap();
        force_transaction_rollback(&mut transaction);
        transaction.rollback().unwrap();
        session.finish(Ok(())).unwrap();

        assert_v1_prefix(&config, &registry);
        assert_eq!(migrate_schema_epoch(&config).unwrap().final_applied, 5);
        database.cleanup();
    }

    fn verify_v2_killed_commit_retry(base: &Config) {
        let database = TestDatabase::create(base, "vkilled");
        let config = database.config(base);
        establish_v1(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut report = v2_report();
        let mut first_attempt = true;
        let mut attempt = |client: &mut Client, migration, legacy_origin| {
            if first_attempt {
                first_attempt = false;
                killed_before_commit_attempt(client, migration, legacy_origin, base)
            } else {
                attempt_migration(client, migration, legacy_origin)
            }
        };
        apply_with_reconciliation_using(
            &bounded,
            &mut session,
            &registry,
            registry[1],
            false,
            &mut report,
            &mut attempt,
        )
        .unwrap();
        session.finish(Ok(())).unwrap();
        assert_eq!(
            report.applied_versions,
            vec![registry[1].migration.version()]
        );
        assert!(report.reconciled_versions.is_empty());
        let completed = migrate_schema_epoch(&config).unwrap();
        assert_eq!(completed.prior_applied, 2);
        assert_eq!(completed.final_applied, 5);
        database.cleanup();
    }

    fn verify_v2_committed_reconciliation(base: &Config) {
        let database = TestDatabase::create(base, "vreconciled");
        let config = database.config(base);
        establish_v1(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut report = v2_report();
        let mut first_attempt = true;
        let mut attempt = |client: &mut Client, migration, legacy_origin| {
            let outcome = attempt_migration(client, migration, legacy_origin)?;
            if first_attempt {
                first_attempt = false;
                assert_eq!(outcome, MigrationAttempt::Committed);
                Ok(MigrationAttempt::Ambiguous)
            } else {
                Ok(outcome)
            }
        };
        apply_with_reconciliation_using(
            &bounded,
            &mut session,
            &registry,
            registry[1],
            false,
            &mut report,
            &mut attempt,
        )
        .unwrap();
        session.finish(Ok(())).unwrap();
        assert!(report.applied_versions.is_empty());
        assert_eq!(
            report.reconciled_versions,
            vec![registry[1].migration.version()]
        );
        let completed = migrate_schema_epoch(&config).unwrap();
        assert_eq!(completed.prior_applied, 2);
        assert_eq!(completed.final_applied, 5);
        database.cleanup();
    }

    fn verify_v3_pre_marker_rollback(base: &Config) {
        let database = TestDatabase::create(base, "vthreeprerollback");
        let config = database.config(base);
        establish_v2(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut transaction = begin_migration_transaction(session.client()).unwrap();
        execute_migration_before_marker(&mut transaction, registry[2], false).unwrap();
        force_transaction_rollback(&mut transaction);
        transaction.rollback().unwrap();
        session.finish(Ok(())).unwrap();

        assert_v2_prefix(&config, &registry);
        assert_eq!(migrate_schema_epoch(&config).unwrap().final_applied, 5);
        database.cleanup();
    }

    fn verify_v3_marker_rollback(base: &Config) {
        let database = TestDatabase::create(base, "vthreerollback");
        let config = database.config(base);
        establish_v2(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut transaction = begin_migration_transaction(session.client()).unwrap();
        execute_migration_before_marker(&mut transaction, registry[2], false).unwrap();
        insert_ledger_marker(&mut transaction, registry[2].migration).unwrap();
        force_transaction_rollback(&mut transaction);
        transaction.rollback().unwrap();
        session.finish(Ok(())).unwrap();

        assert_v2_prefix(&config, &registry);
        assert_eq!(migrate_schema_epoch(&config).unwrap().final_applied, 5);
        database.cleanup();
    }

    fn verify_v3_killed_commit_retry(base: &Config) {
        let database = TestDatabase::create(base, "vthreekilled");
        let config = database.config(base);
        establish_v2(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut report = v3_report();
        let mut first_attempt = true;
        let mut attempt = |client: &mut Client, migration, legacy_origin| {
            if first_attempt {
                first_attempt = false;
                killed_before_commit_attempt(client, migration, legacy_origin, base)
            } else {
                attempt_migration(client, migration, legacy_origin)
            }
        };
        apply_with_reconciliation_using(
            &bounded,
            &mut session,
            &registry,
            registry[2],
            false,
            &mut report,
            &mut attempt,
        )
        .unwrap();
        session.finish(Ok(())).unwrap();
        assert_eq!(
            report.applied_versions,
            vec![registry[2].migration.version()]
        );
        assert!(report.reconciled_versions.is_empty());
        assert_eq!(migrate_schema_epoch(&config).unwrap().prior_applied, 3);
        database.cleanup();
    }

    fn verify_v3_committed_reconciliation(base: &Config) {
        let database = TestDatabase::create(base, "vthreereconciled");
        let config = database.config(base);
        establish_v2(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut report = v3_report();
        let mut first_attempt = true;
        let mut attempt = |client: &mut Client, migration, legacy_origin| {
            let outcome = attempt_migration(client, migration, legacy_origin)?;
            if first_attempt {
                first_attempt = false;
                assert_eq!(outcome, MigrationAttempt::Committed);
                Ok(MigrationAttempt::Ambiguous)
            } else {
                Ok(outcome)
            }
        };
        apply_with_reconciliation_using(
            &bounded,
            &mut session,
            &registry,
            registry[2],
            false,
            &mut report,
            &mut attempt,
        )
        .unwrap();
        session.finish(Ok(())).unwrap();
        assert!(report.applied_versions.is_empty());
        assert_eq!(
            report.reconciled_versions,
            vec![registry[2].migration.version()]
        );
        assert_eq!(migrate_schema_epoch(&config).unwrap().prior_applied, 3);
        database.cleanup();
    }

    fn verify_v4_pre_marker_rollback(base: &Config) {
        let database = TestDatabase::create(base, "vfourprerollback");
        let config = database.config(base);
        establish_v3(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut transaction = begin_migration_transaction(session.client()).unwrap();
        execute_migration_before_marker(&mut transaction, registry[3], false).unwrap();
        force_transaction_rollback(&mut transaction);
        transaction.rollback().unwrap();
        session.finish(Ok(())).unwrap();

        assert_v3_prefix(&config, &registry);
        assert_eq!(migrate_schema_epoch(&config).unwrap().final_applied, 5);
        database.cleanup();
    }

    fn verify_v4_marker_rollback(base: &Config) {
        let database = TestDatabase::create(base, "vfourmarkerrollback");
        let config = database.config(base);
        establish_v3(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut transaction = begin_migration_transaction(session.client()).unwrap();
        execute_migration_before_marker(&mut transaction, registry[3], false).unwrap();
        insert_ledger_marker(&mut transaction, registry[3].migration).unwrap();
        force_transaction_rollback(&mut transaction);
        transaction.rollback().unwrap();
        session.finish(Ok(())).unwrap();

        assert_v3_prefix(&config, &registry);
        assert_eq!(migrate_schema_epoch(&config).unwrap().final_applied, 5);
        database.cleanup();
    }

    fn verify_v4_killed_commit_retry(base: &Config) {
        let database = TestDatabase::create(base, "vfourkilled");
        let config = database.config(base);
        establish_v3(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut report = v4_report();
        let mut first_attempt = true;
        let mut attempt = |client: &mut Client, migration, legacy_origin| {
            if first_attempt {
                first_attempt = false;
                killed_before_commit_attempt(client, migration, legacy_origin, base)
            } else {
                attempt_migration(client, migration, legacy_origin)
            }
        };
        apply_with_reconciliation_using(
            &bounded,
            &mut session,
            &registry,
            registry[3],
            false,
            &mut report,
            &mut attempt,
        )
        .unwrap();
        session.finish(Ok(())).unwrap();
        assert_eq!(
            report.applied_versions,
            vec![registry[3].migration.version()]
        );
        assert!(report.reconciled_versions.is_empty());
        assert_eq!(migrate_schema_epoch(&config).unwrap().prior_applied, 4);
        database.cleanup();
    }

    fn verify_v4_committed_reconciliation(base: &Config) {
        let database = TestDatabase::create(base, "vfourreconciled");
        let config = database.config(base);
        establish_v3(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut report = v4_report();
        let mut first_attempt = true;
        let mut attempt = |client: &mut Client, migration, legacy_origin| {
            let outcome = attempt_migration(client, migration, legacy_origin)?;
            if first_attempt {
                first_attempt = false;
                assert_eq!(outcome, MigrationAttempt::Committed);
                Ok(MigrationAttempt::Ambiguous)
            } else {
                Ok(outcome)
            }
        };
        apply_with_reconciliation_using(
            &bounded,
            &mut session,
            &registry,
            registry[3],
            false,
            &mut report,
            &mut attempt,
        )
        .unwrap();
        session.finish(Ok(())).unwrap();
        assert!(report.applied_versions.is_empty());
        assert_eq!(
            report.reconciled_versions,
            vec![registry[3].migration.version()]
        );
        assert_eq!(migrate_schema_epoch(&config).unwrap().prior_applied, 4);
        database.cleanup();
    }

    fn verify_v5_pre_marker_rollback(base: &Config) {
        let database = TestDatabase::create(base, "vfiveprerollback");
        let config = database.config(base);
        establish_v4(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut transaction = begin_migration_transaction(session.client()).unwrap();
        execute_migration_before_marker(&mut transaction, registry[4], false).unwrap();
        force_transaction_rollback(&mut transaction);
        transaction.rollback().unwrap();
        session.finish(Ok(())).unwrap();

        assert_v4_prefix(&config, &registry);
        assert_eq!(migrate_schema_epoch(&config).unwrap().final_applied, 5);
        database.cleanup();
    }

    fn verify_v5_marker_rollback(base: &Config) {
        let database = TestDatabase::create(base, "vfivemarkerrollback");
        let config = database.config(base);
        establish_v4(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut transaction = begin_migration_transaction(session.client()).unwrap();
        execute_migration_before_marker(&mut transaction, registry[4], false).unwrap();
        insert_ledger_marker(&mut transaction, registry[4].migration).unwrap();
        force_transaction_rollback(&mut transaction);
        transaction.rollback().unwrap();
        session.finish(Ok(())).unwrap();

        assert_v4_prefix(&config, &registry);
        assert_eq!(migrate_schema_epoch(&config).unwrap().final_applied, 5);
        database.cleanup();
    }

    fn verify_v5_killed_commit_retry(base: &Config) {
        let database = TestDatabase::create(base, "vfivekilled");
        let config = database.config(base);
        establish_v4(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut report = v5_report();
        let mut first_attempt = true;
        let mut attempt = |client: &mut Client, migration, legacy_origin| {
            if first_attempt {
                first_attempt = false;
                killed_before_commit_attempt(client, migration, legacy_origin, base)
            } else {
                attempt_migration(client, migration, legacy_origin)
            }
        };
        apply_with_reconciliation_using(
            &bounded,
            &mut session,
            &registry,
            registry[4],
            false,
            &mut report,
            &mut attempt,
        )
        .unwrap();
        session.finish(Ok(())).unwrap();
        assert_eq!(
            report.applied_versions,
            vec![registry[4].migration.version()]
        );
        assert!(report.reconciled_versions.is_empty());
        assert_eq!(migrate_schema_epoch(&config).unwrap().prior_applied, 5);
        database.cleanup();
    }

    fn verify_v5_committed_reconciliation(base: &Config) {
        let database = TestDatabase::create(base, "vfivereconciled");
        let config = database.config(base);
        establish_v4(&config);
        let registry = production_registry();
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut report = v5_report();
        let mut first_attempt = true;
        let mut attempt = |client: &mut Client, migration, legacy_origin| {
            let outcome = attempt_migration(client, migration, legacy_origin)?;
            if first_attempt {
                first_attempt = false;
                assert_eq!(outcome, MigrationAttempt::Committed);
                Ok(MigrationAttempt::Ambiguous)
            } else {
                Ok(outcome)
            }
        };
        apply_with_reconciliation_using(
            &bounded,
            &mut session,
            &registry,
            registry[4],
            false,
            &mut report,
            &mut attempt,
        )
        .unwrap();
        session.finish(Ok(())).unwrap();
        assert!(report.applied_versions.is_empty());
        assert_eq!(
            report.reconciled_versions,
            vec![registry[4].migration.version()]
        );
        assert_eq!(migrate_schema_epoch(&config).unwrap().prior_applied, 5);
        database.cleanup();
    }

    fn verify_leap_ahead_reconciliation(base: &Config) {
        let database = TestDatabase::create(base, "vleapahead");
        let config = database.config(base);
        let registry = production_registry();
        let leap_registry = registry;
        let bounded = bounded_config(&config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let mut attempt_calls = 0_usize;
        let mut attempt =
            |client: &mut Client, migration: SchemaEpochMigration, legacy_origin: bool| {
                attempt_calls += 1;
                assert_eq!(migration.migration.version().as_i64(), 1);
                assert_eq!(
                    attempt_migration(client, leap_registry[0], legacy_origin)?,
                    MigrationAttempt::Committed
                );
                assert_eq!(
                    attempt_migration(client, leap_registry[1], legacy_origin)?,
                    MigrationAttempt::Committed
                );
                assert_eq!(
                    attempt_migration(client, leap_registry[2], legacy_origin)?,
                    MigrationAttempt::Committed
                );
                assert_eq!(
                    attempt_migration(client, leap_registry[3], legacy_origin)?,
                    MigrationAttempt::Committed
                );
                assert_eq!(
                    attempt_migration(client, leap_registry[4], legacy_origin)?,
                    MigrationAttempt::Committed
                );
                Ok(MigrationAttempt::Ambiguous)
            };
        let report =
            migrate_locked_with_registry_using(&bounded, &mut session, &registry, &mut attempt)
                .unwrap();
        session.finish(Ok(())).unwrap();

        assert_eq!(attempt_calls, 1);
        assert_eq!(report.prior_applied, 0);
        assert_eq!(report.final_applied, 5);
        assert!(report.applied_versions.is_empty());
        assert_eq!(
            report.reconciled_versions,
            vec![registry[0].migration.version()]
        );
        v5_snapshot(&config, &registry);
        database.cleanup();
    }

    fn establish_v1(config: &Config) {
        let registry = production_registry();
        let bounded = bounded_config(config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        assert_eq!(
            attempt_migration(session.client(), registry[0], false).unwrap(),
            MigrationAttempt::Committed
        );
        session.finish(Ok(())).unwrap();
        assert_v1_prefix(config, &registry);
    }

    fn assert_v1_prefix(config: &Config, registry: &[SchemaEpochMigration]) {
        let bounded = bounded_config(config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let inspected = inspect_epoch(session.client(), registry).unwrap();
        assert_eq!(inspected.origin, SchemaEpochOrigin::ExistingRustPrefix);
        assert_eq!(
            validate_registry_prefix(registry, &inspected.persisted),
            Ok(1)
        );
        session.finish(Ok(())).unwrap();
    }

    fn establish_v2(config: &Config) {
        establish_v1(config);
        let registry = production_registry();
        let bounded = bounded_config(config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        assert_eq!(
            attempt_migration(session.client(), registry[1], false).unwrap(),
            MigrationAttempt::Committed
        );
        session.finish(Ok(())).unwrap();
        assert_v2_prefix(config, &registry);
    }

    fn assert_v2_prefix(config: &Config, registry: &[SchemaEpochMigration]) {
        let bounded = bounded_config(config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let inspected = inspect_epoch(session.client(), registry).unwrap();
        assert_eq!(inspected.origin, SchemaEpochOrigin::ExistingRustPrefix);
        assert_eq!(
            validate_registry_prefix(registry, &inspected.persisted),
            Ok(2)
        );
        session.finish(Ok(())).unwrap();
    }

    fn establish_v3(config: &Config) {
        establish_v2(config);
        let registry = production_registry();
        let bounded = bounded_config(config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        assert_eq!(
            attempt_migration(session.client(), registry[2], false).unwrap(),
            MigrationAttempt::Committed
        );
        session.finish(Ok(())).unwrap();
        assert_v3_prefix(config, &registry);
    }

    fn assert_v3_prefix(config: &Config, registry: &[SchemaEpochMigration]) {
        let bounded = bounded_config(config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let inspected = inspect_epoch(session.client(), registry).unwrap();
        assert_eq!(inspected.origin, SchemaEpochOrigin::ExistingRustPrefix);
        assert_eq!(
            validate_registry_prefix(registry, &inspected.persisted),
            Ok(3)
        );
        session.finish(Ok(())).unwrap();
    }

    fn establish_v4(config: &Config) {
        establish_v3(config);
        let registry = production_registry();
        let bounded = bounded_config(config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        assert_eq!(
            attempt_migration(session.client(), registry[3], false).unwrap(),
            MigrationAttempt::Committed
        );
        session.finish(Ok(())).unwrap();
        assert_v4_prefix(config, &registry);
    }

    fn assert_v4_prefix(config: &Config, registry: &[SchemaEpochMigration]) {
        let bounded = bounded_config(config);
        let mut session = LockedSession::connect(&bounded).unwrap();
        let inspected = inspect_epoch(session.client(), registry).unwrap();
        assert_eq!(inspected.origin, SchemaEpochOrigin::ExistingRustPrefix);
        assert_eq!(
            validate_registry_prefix(registry, &inspected.persisted),
            Ok(4)
        );
        session.finish(Ok(())).unwrap();
    }

    fn force_transaction_rollback(transaction: &mut Transaction<'_>) {
        let failure = transaction.batch_execute("SELECT 1 / 0").unwrap_err();
        assert_eq!(failure.code(), Some(&SqlState::DIVISION_BY_ZERO));
    }

    fn production_registry() -> [SchemaEpochMigration; 5] {
        compiled_schema_epoch_migrations().unwrap()
    }

    fn v2_report() -> SchemaEpochReport {
        SchemaEpochReport {
            origin: SchemaEpochOrigin::ExistingRustPrefix,
            prior_applied: 1,
            final_applied: 1,
            applied_versions: Vec::new(),
            reconciled_versions: Vec::new(),
            legacy_adoption: None,
        }
    }

    fn v3_report() -> SchemaEpochReport {
        SchemaEpochReport {
            origin: SchemaEpochOrigin::ExistingRustPrefix,
            prior_applied: 2,
            final_applied: 2,
            applied_versions: Vec::new(),
            reconciled_versions: Vec::new(),
            legacy_adoption: None,
        }
    }

    fn v4_report() -> SchemaEpochReport {
        SchemaEpochReport {
            origin: SchemaEpochOrigin::ExistingRustPrefix,
            prior_applied: 3,
            final_applied: 3,
            applied_versions: Vec::new(),
            reconciled_versions: Vec::new(),
            legacy_adoption: None,
        }
    }

    fn v5_report() -> SchemaEpochReport {
        SchemaEpochReport {
            origin: SchemaEpochOrigin::ExistingRustPrefix,
            prior_applied: 4,
            final_applied: 4,
            applied_versions: Vec::new(),
            reconciled_versions: Vec::new(),
            legacy_adoption: None,
        }
    }

    fn v5_snapshot(config: &Config, registry: &[SchemaEpochMigration; 5]) -> Vec<(i64, Vec<u8>)> {
        let mut client = config.connect(NoTls).unwrap();
        let relations = client
            .query_one(
                "SELECT pg_catalog.to_regclass('babylon_ref.h3_cell')::pg_catalog.text, \
                        pg_catalog.to_regclass('babylon_ref.h3_reference_cohort')::pg_catalog.text, \
                        pg_catalog.to_regclass('babylon_ref.h3_reference_membership')::pg_catalog.text, \
                        pg_catalog.to_regclass('babylon_state.campaign')::pg_catalog.text, \
                        pg_catalog.to_regclass('babylon_state.tick_commit')::pg_catalog.text, \
                        pg_catalog.to_regclass( \
                            'babylon_state.tick_archive_dirty_receipt_row' \
                        )::pg_catalog.text, \
                        pg_catalog.to_regclass( \
                            'babylon_ref.reference_product' \
                        )::pg_catalog.text",
                &[],
            )
            .unwrap();
        let expected_relations = [
            "babylon_ref.h3_cell",
            "babylon_ref.h3_reference_cohort",
            "babylon_ref.h3_reference_membership",
            "babylon_state.campaign",
            "babylon_state.tick_commit",
            "babylon_state.tick_archive_dirty_receipt_row",
            "babylon_ref.reference_product",
        ];
        for (index, expected) in expected_relations.iter().enumerate() {
            let actual = relations.try_get::<_, Option<String>>(index).unwrap();
            assert_eq!(actual.as_deref(), Some(*expected));
        }
        let counts = client
            .query_one(
                "SELECT (SELECT pg_catalog.count(*) FROM babylon_ref.h3_cell), \
                        (SELECT pg_catalog.count(*) FROM babylon_ref.h3_reference_cohort), \
                        (SELECT pg_catalog.count(*) FROM babylon_ref.h3_reference_membership)",
                &[],
            )
            .unwrap();
        for column in 0..3 {
            assert_eq!(counts.try_get::<_, i64>(column).unwrap(), 0);
        }
        let rows = client
            .query(
                "SELECT version, checksum FROM babylon_state.schema_migration \
                 ORDER BY version LIMIT 5",
                &[],
            )
            .unwrap();
        let snapshot = rows
            .iter()
            .take(5)
            .map(|row| {
                (
                    row.try_get::<_, i64>(0).unwrap(),
                    row.try_get::<_, Vec<u8>>(1).unwrap(),
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(snapshot.len(), 5);
        for (index, row) in snapshot.iter().enumerate().take(5) {
            assert_eq!(row.0, one_based_version(index));
            assert_eq!(
                row.1.as_slice(),
                registry[index].migration.checksum().as_bytes()
            );
        }
        snapshot
    }

    fn killed_before_commit_attempt(
        client: &mut Client,
        migration: SchemaEpochMigration,
        legacy_origin: bool,
        admin: &Config,
    ) -> Result<MigrationAttempt, SchemaEpochError> {
        let backend_pid: i32 = client
            .query_one("SELECT pg_catalog.pg_backend_pid()", &[])
            .unwrap()
            .try_get(0)
            .unwrap();
        let mut transaction = begin_migration_transaction(client)?;
        execute_migration_before_marker(&mut transaction, migration, legacy_origin)?;
        insert_ledger_marker(&mut transaction, migration.migration)?;
        let terminated: bool = admin
            .connect(NoTls)
            .unwrap()
            .query_one(
                "SELECT pg_catalog.pg_terminate_backend($1, $2)",
                &[&backend_pid, &BACKEND_TERMINATION_TIMEOUT_MILLIS],
            )
            .unwrap()
            .try_get(0)
            .unwrap();
        assert!(terminated);
        assert!(transaction.commit().is_err());
        Ok(MigrationAttempt::Ambiguous)
    }

    fn empty_report() -> SchemaEpochReport {
        SchemaEpochReport {
            origin: SchemaEpochOrigin::Fresh,
            prior_applied: 0,
            final_applied: 0,
            applied_versions: Vec::new(),
            reconciled_versions: Vec::new(),
            legacy_adoption: None,
        }
    }

    fn validated_base_config() -> Config {
        assert_eq!(std::env::var(ACK_ENV).as_deref(), Ok(ACK));
        let canary = std::env::var(CANARY_ENV).expect("runner supplies the disposable canary");
        assert_eq!(canary.len(), 32);
        let dsn = std::env::var(DSN_ENV).expect("runner supplies the disposable DSN");
        let config = Config::from_str(&dsn).expect("runner DSN parses");
        validate_legacy_connection_target(&config).unwrap();
        assert_eq!(config.get_user(), Some("test"));
        assert_eq!(config.get_dbname(), Some("postgres"));
        let mut client = config.connect(NoTls).unwrap();
        let actual: Option<String> = client
            .query_one(
                "SELECT pg_catalog.current_setting('babylon.per20_disposable', true)",
                &[],
            )
            .unwrap()
            .try_get(0)
            .unwrap();
        assert_eq!(actual.as_deref(), Some(canary.as_str()));
        config
    }

    fn empty_observation() -> SchemaEpochObservation {
        SchemaEpochObservation {
            schemas: SchemaEpochSchemas {
                babylon_ref: false,
                babylon_state: false,
                babylon_meta: false,
            },
            ledger: SchemaEpochRelation::Absent,
            legacy_stamp: SchemaEpochRelation::Absent,
        }
    }

    struct TestDatabase {
        name: String,
        admin: Config,
        active: bool,
    }

    impl TestDatabase {
        fn create(base: &Config, label: &str) -> Self {
            assert!(label.bytes().all(|byte| byte.is_ascii_lowercase()));
            let name = format!("per20_epoch_{label}_{}", std::process::id());
            let mut admin = base.clone();
            admin.dbname("postgres");
            let sql = format!("CREATE DATABASE \"{name}\" OWNER test TEMPLATE template1");
            admin.connect(NoTls).unwrap().batch_execute(&sql).unwrap();
            Self {
                name,
                admin,
                active: true,
            }
        }

        fn config(&self, base: &Config) -> Config {
            let mut config = base.clone();
            config.dbname(&self.name);
            config
        }

        fn cleanup(mut self) {
            match self.try_drop_database() {
                Ok(()) => self.active = false,
                Err(()) => panic!("schema-epoch test database cleanup must succeed"),
            }
        }

        fn try_drop_database(&self) -> Result<(), ()> {
            let sql = format!("DROP DATABASE IF EXISTS \"{}\" WITH (FORCE)", self.name);
            self.admin
                .connect(NoTls)
                .map_err(|_| ())?
                .batch_execute(&sql)
                .map_err(|_| ())
        }
    }

    impl Drop for TestDatabase {
        fn drop(&mut self) {
            if !self.active {
                return;
            }
            if std::thread::panicking() {
                let _unwind_cleanup = self.try_drop_database();
                return;
            }
            match self.try_drop_database() {
                Ok(()) => self.active = false,
                Err(()) => panic!("schema-epoch test database cleanup failed"),
            }
        }
    }
}
