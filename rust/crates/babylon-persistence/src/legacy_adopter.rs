//! Read-only adoption checks for the frozen legacy `PostgreSQL` estate.

use std::collections::{BTreeMap, BTreeSet};
use std::net::IpAddr;
use std::time::Duration;

use postgres::config::Host;
use postgres::{Config, IsolationLevel, NoTls, Row, Transaction};

use crate::{PostgresDiagnosticV1, SCHEMA_ADVISORY_LOCK_KEY};

/// Current census fixture text, with provenance comments.
pub const LEGACY_CENSUS_FIXTURE: &str = include_str!("fixtures/legacy_adopter_census_v2.txt");
/// Version of the canonical catalog census contract.
pub const LEGACY_CENSUS_VERSION: u16 = 2;
/// Maximum expected catalog objects accepted from one census.
pub const MAX_LEGACY_CENSUS_ROWS: usize = 512;
/// Maximum bytes accepted by the fixture parser.
pub const MAX_LEGACY_CENSUS_FIXTURE_BYTES: usize = 65_536;
/// Maximum fixture lines scanned by the bounded parser.
pub const MAX_LEGACY_CENSUS_FIXTURE_LINES: usize = MAX_LEGACY_CENSUS_ROWS + 32;
/// Maximum stamp rows read from the legacy stamp table.
pub const MAX_LEGACY_STAMP_ROWS: usize = 64;
/// `PostgreSQL`'s `NAMEDATALEN - 1` identifier byte ceiling.
pub const POSTGRES_IDENTIFIER_MAX_BYTES: usize = 63;
/// Maximum child partitions checked for each governed parent.
pub const MAX_LEGACY_PARTITIONS_PER_FAMILY: usize = 4_096;
/// Maximum extension-owned catalog members checked across each installed extension.
pub const MAX_LEGACY_EXTENSION_MEMBERS: usize = 8_192;
/// Maximum canonical extension member and dependency addresses checked together.
pub const MAX_LEGACY_EXTENSION_DEPENDENCY_ADDRESSES: usize = 16_384;
/// Maximum distinct non-`PUBLIC` role identities referenced by installed extensions.
pub const MAX_LEGACY_EXTENSION_ROLE_IDENTITIES: usize = 8_192;
/// Maximum `OWNED BY` dependency accepted for one sequence.
pub const MAX_LEGACY_SEQUENCE_OWNERSHIP: usize = 1;
/// Bounded connection timeout for local game-managed `PostgreSQL`.
pub const LEGACY_ADOPTER_CONNECT_TIMEOUT: Duration = Duration::from_secs(5);
/// Bounded TCP acknowledgement timeout for local game-managed `PostgreSQL`.
pub const LEGACY_ADOPTER_TCP_USER_TIMEOUT: Duration = Duration::from_secs(5);
/// Hardened startup settings which replace any caller-supplied options.
pub const LEGACY_ADOPTER_STARTUP_OPTIONS: &str =
    "-c default_transaction_read_only=on -c statement_timeout=5000ms \
     -c lock_timeout=5000ms -c idle_in_transaction_session_timeout=5000ms \
     -c quote_all_identifiers=off -c search_path=pg_catalog -c jit=off \
     -c event_triggers=off";

const MAX_ERROR_SOURCE_DEPTH: usize = 8;

const CATALOG_CENSUS_SQL: &str = include_str!("legacy_adopter_census.sql");
const LOCK_SQL: &str = "SELECT pg_catalog.pg_try_advisory_lock($1)";
const UNLOCK_SQL: &str = "SELECT pg_catalog.pg_advisory_unlock($1)";
const TRANSACTION_SETTINGS_SQL: &str = "SELECT \
    pg_catalog.current_setting('transaction_isolation'), \
    pg_catalog.current_setting('transaction_read_only'), \
    pg_catalog.current_setting('search_path'), \
    pg_catalog.current_setting('jit'), \
    pg_catalog.current_setting('event_triggers'), \
    pg_catalog.current_setting('statement_timeout'), \
    pg_catalog.current_setting('lock_timeout'), \
    pg_catalog.current_setting('idle_in_transaction_session_timeout'), \
    pg_catalog.current_setting('quote_all_identifiers')";
const AUTHORITY_SCHEMAS_SQL: &str = "SELECT n.nspname::text \
    FROM pg_catalog.pg_namespace AS n \
    WHERE n.nspname IN ('babylon_ref', 'babylon_state') \
    ORDER BY n.nspname LIMIT 3";
const STAMP_TABLE_EXISTS_SQL: &str =
    "SELECT pg_catalog.to_regclass('public._babylon_schema_stamp') IS NOT NULL";
const READ_STAMPS_SQL: &str = "SELECT \
    pg_catalog.left(s.digest::text, $2) AS digest_prefix, \
    pg_catalog.octet_length(s.digest::text) AS digest_bytes \
    FROM public._babylon_schema_stamp AS s \
    ORDER BY pg_catalog.left(s.digest::text, $2), \
             pg_catalog.octet_length(s.digest::text) LIMIT $1";

/// Classification of an exact legacy stamp.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum LegacyStampClass {
    /// Current full migration/schema evidence required for adoption.
    RequiredCurrent,
    /// The separately stamped legacy `babylon_meta` DDL set.
    AllowedMeta,
    /// A superseded complete migration-set stamp retained as history.
    HistoricalFullMigration,
    /// A historical test-only subset stamp retained as loud residue.
    HistoricalTestSubset,
}

/// Exact source provenance attached to a classified legacy stamp.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LegacyStampProvenance {
    /// A current authority stamp whose public name is canonical.
    Current,
    /// The separately named `BABYLON_META_DDL` stamp.
    AllowedMeta,
    /// Historical complete migration set superseded by the named current set.
    HistoricalFullMigration {
        /// Length of the newline-framed source bytes.
        framed_bytes: usize,
        /// Source commit containing the exact historical migration set.
        source_commit: &'static str,
        /// First development merge containing that set.
        first_dev_merge: &'static str,
        /// Descriptive current stamp name which superseded it.
        superseded_by: &'static str,
    },
    /// Historical test-only subset which re-applied part of the current set.
    HistoricalTestSubset {
        /// Length of the newline-framed source bytes.
        framed_bytes: usize,
        /// Commit which introduced the source files.
        source_introduction_commit: &'static str,
        /// Commit by which the subset fixture existed.
        fixture_commit: &'static str,
        /// Commit containing the stamping producer.
        producer_commit: &'static str,
        /// Development merge containing the producer.
        producer_dev_merge: &'static str,
        /// Commit which removed the test residue.
        removed_commit: &'static str,
        /// Development merge containing the removal.
        removed_dev_merge: &'static str,
    },
}

/// Exact named legacy stamp definition.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LegacyStampDefinition {
    /// Descriptive name reconstructed from its source history.
    pub name: &'static str,
    /// Number of ordered source chunks.
    pub chunk_count: usize,
    /// Lowercase SHA-256 digest stored by Python.
    pub digest_hex: &'static str,
    /// Adoption classification.
    pub class: LegacyStampClass,
    /// Exact source-history evidence for the stamp identity.
    pub provenance: LegacyStampProvenance,
}

/// Closed exact stamp catalog.
///
/// Python stored only `digest` and `applied_at`; historical names are descriptive labels whose
/// source provenance is pinned by the contract tests.
pub const LEGACY_STAMP_CATALOG: [LegacyStampDefinition; 5] = [
    LegacyStampDefinition {
        name: "POSTGRES_SCHEMA_DDL",
        chunk_count: 112,
        digest_hex: "0902471053ab7a22cdaf0340978712772990e87a63aaaa1636608894fa52590b",
        class: LegacyStampClass::RequiredCurrent,
        provenance: LegacyStampProvenance::Current,
    },
    LegacyStampDefinition {
        name: "migrations-0010-0044",
        chunk_count: 35,
        digest_hex: "4abe69ddc25569d5dff1941b4fbe2973df5cbd70a9bca4c92b9fe26f51dd45db",
        class: LegacyStampClass::RequiredCurrent,
        provenance: LegacyStampProvenance::Current,
    },
    LegacyStampDefinition {
        name: "BABYLON_META_DDL",
        chunk_count: 6,
        digest_hex: "edb77a84d35f30eab061ead7620ea2907554ee9231c92b6acfe11fc530f669d8",
        class: LegacyStampClass::AllowedMeta,
        provenance: LegacyStampProvenance::AllowedMeta,
    },
    LegacyStampDefinition {
        name: "migrations-0010-0043",
        chunk_count: 34,
        digest_hex: "7c77114a3b7053bed1dafae8aea77a894ef2034504306d23745d217252bd6711",
        class: LegacyStampClass::HistoricalFullMigration,
        provenance: LegacyStampProvenance::HistoricalFullMigration {
            framed_bytes: 98_830,
            source_commit: "2de19c1cc8e2dd1d19f6e95d232d1dc71e7caa96",
            first_dev_merge: "1d5efaf7da9e75d531426224015e0e616719bdde",
            superseded_by: "migrations-0010-0044",
        },
    },
    LegacyStampDefinition {
        name: "trace-view-v2-migrations-0020-0023",
        chunk_count: 4,
        digest_hex: "1d0a4f5cbd8f5cba3b59d48a25950fc4874923ed962400d8374d34edb31fd7b2",
        class: LegacyStampClass::HistoricalTestSubset,
        provenance: LegacyStampProvenance::HistoricalTestSubset {
            framed_bytes: 9_440,
            source_introduction_commit: "312065d7859743a81ac2e17899cb5b0c2971ac53",
            fixture_commit: "79d4390b869cda61a7af550626fe02278ab218aa",
            producer_commit: "7b22fdb9d3abc5348aa0710a3e4fdb995848ccfd",
            producer_dev_merge: "073e3b1ee0640e0b00935cf78755f49747e1fd37",
            removed_commit: "894b473625737276eed9550b8e62a7079bedec08",
            removed_dev_merge: "09cc23da6c5c5770df96ccc16143de298a0c7a50",
        },
    },
];

/// Census object class.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum LegacyObjectKind {
    /// Versioned database and server environment contract.
    Database,
    /// `PostgreSQL` domain.
    Domain,
    /// Installed extension identity and version.
    Extension,
    /// Foreign table.
    ForeignTable,
    /// Materialized view.
    MaterializedView,
    /// Partitioned table parent.
    PartitionedTable,
    /// Ordinary table or relation.
    Relation,
    /// Normalized role contract.
    Role,
    /// User-defined routine family.
    Routine,
    /// Extra non-system schema identity.
    Schema,
    /// Governed schema grant.
    SchemaGrant,
    /// Sequence.
    Sequence,
    /// Fail-closed sentinel for an unsupported user-created catalog family.
    UnsupportedCatalog,
    /// Standalone user-defined non-domain type family.
    UserType,
    /// View.
    View,
}

/// Stable catalog object key.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct LegacyObjectKey {
    kind: LegacyObjectKind,
    schema: Box<str>,
    name: Box<str>,
}

/// One object signature row.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LegacyCensusEntry {
    key: LegacyObjectKey,
    digest_hex: Box<str>,
}

/// Parsed bounded census.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LegacyCensus {
    entries: Vec<LegacyCensusEntry>,
}

/// One exact stamp observed during validation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LegacyStampMatch {
    /// Exact catalog definition which matched.
    pub definition: LegacyStampDefinition,
}

/// Stamp validation report with loud per-class identities.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LegacyStampReport {
    matches: Vec<LegacyStampMatch>,
}

/// Successful adoption report.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LegacyAdoptionReport {
    /// Number of frozen expected objects.
    pub expected_objects: usize,
    /// Number of expected objects matched exactly.
    pub matched_objects: usize,
    /// Empty on success; every whole extra object is a typed refusal.
    pub extra_objects: Vec<LegacyObjectKey>,
    /// Exact stamp identities grouped through their typed classes.
    pub stamps: LegacyStampReport,
    /// The internal transaction reported repeatable-read, read-only, and `pg_catalog` search path.
    pub transaction_verified: bool,
    /// Database-owner capability is deliberately left to the future Rust migrator preflight.
    pub owner_authority: LegacyOwnerAuthorityDisposition,
}

/// Honest disposition of database-owner capability outside this read-only adopter's scope.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LegacyOwnerAuthorityDisposition {
    /// The next Rust migrator preflight must verify effective owner capability before writing.
    DeferredToRustMigratorPreflight,
}

/// Strict fixture parser failures.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LegacyCensusParseError {
    /// Fixture bytes exceeded the public ceiling.
    TooManyBytes { actual: usize, max: usize },
    /// The parser hit the fixed line bound.
    TooManyLines { max: usize },
    /// More object rows were present than the fixed bound permits.
    TooManyRows { actual: usize, max: usize },
    /// A row did not have the exact four fields.
    MalformedRecord { line: usize, fields: usize },
    /// A kind field was not in the closed vocabulary.
    InvalidKind { line: usize },
    /// Schema or object identifier was outside the strict vocabulary or byte ceiling.
    InvalidIdentifier { line: usize },
    /// Digest was not 64 lowercase hexadecimal bytes.
    InvalidDigest { line: usize },
    /// The same object key appeared twice.
    DuplicateObject { line: usize },
    /// Fixture entries were not strictly sorted by key.
    OutOfOrder { line: usize },
    /// No object rows were present.
    Empty,
}

/// Bounded database operation names safe for display and logs.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LegacyAdopterOperation {
    /// Establish the fresh connection.
    Connect,
    /// Acquire the schema advisory lock.
    Lock,
    /// Start the verification transaction.
    BeginTransaction,
    /// Verify internal transaction settings.
    VerifyTransaction,
    /// Inspect future authority schemas.
    AuthoritySchemas,
    /// Inspect stamp-table existence.
    StampTable,
    /// Read legacy stamp rows.
    Stamps,
    /// Read the catalog census.
    Census,
    /// Explicitly roll back the verification transaction.
    Rollback,
    /// Release the schema advisory lock.
    Unlock,
}

/// Safe reason that a caller's connection target is outside the local-only contract.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LegacyConnectionTargetRejection {
    /// Caller-supplied startup options could redirect unqualified database operations.
    StartupOptionsOverride,
    /// No explicit target was supplied.
    MissingHost,
    /// More than one host was supplied.
    MultipleHosts,
    /// More than one port was supplied.
    MultiplePorts,
    /// A separate host-address override could redirect the named target.
    HostAddressOverride,
    /// A TCP target was not a literal loopback address.
    NonLoopbackTcp,
    /// A Unix-domain socket path was not absolute.
    NonAbsoluteUnixSocket,
}

/// Fixed resources protected by public bounds.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LegacyBoundedResource {
    /// Authority schema names.
    AuthoritySchemas,
    /// Stamp rows.
    StampRows,
    /// Census rows.
    CensusRows,
    /// Ordinary bounded catalog candidate or subordinate rows.
    CatalogRows,
    /// Direct child partitions within one governed family.
    PartitionRows,
    /// Direct members recorded for one extension.
    ExtensionMembers,
    /// Canonical direct-member and dependency addresses across installed extensions.
    ExtensionDependencyAddresses,
    /// Distinct non-`PUBLIC` role identities referenced by installed extensions.
    ExtensionRoleIdentities,
    /// `OWNED BY` dependencies attached to one sequence.
    SequenceOwnership,
    /// One database-origin identifier.
    IdentifierBytes,
    /// One legacy stamp digest value.
    StampBytes,
}

/// Typed adopter refusal and failure states.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LegacyAdopterError {
    /// The supplied target was not one exact local socket endpoint.
    UnsupportedConnectionTarget {
        /// Bounded rejection reason which never contains the target text.
        reason: LegacyConnectionTargetRejection,
    },
    /// The fresh local connection failed with a secret-safe diagnostic.
    Connection { diagnostic: PostgresDiagnosticV1 },
    /// The caller cannot disable login event triggers before connecting.
    EventTriggerSuppressionUnavailable { diagnostic: PostgresDiagnosticV1 },
    /// A bounded database operation timed out.
    Timeout {
        operation: LegacyAdopterOperation,
        diagnostic: PostgresDiagnosticV1,
    },
    /// A read query failed.
    Query {
        operation: LegacyAdopterOperation,
        diagnostic: PostgresDiagnosticV1,
    },
    /// A transaction operation failed or its mode was not exact.
    Transaction {
        operation: LegacyAdopterOperation,
        diagnostic: Option<PostgresDiagnosticV1>,
    },
    /// The exact schema lock was already held.
    LockUnavailable,
    /// A future Rust-authority schema already exists.
    UnsupportedAuthorityEpoch { schemas: Vec<Box<str>> },
    /// The legacy stamp table was absent.
    StampTableMissing,
    /// One or more required current stamp digests were absent.
    RequiredStampMissing { missing: Vec<LegacyStampDefinition> },
    /// A digest did not occur in the exact named catalog.
    UnknownStamp { digests: Vec<Box<str>> },
    /// The same stamp digest appeared more than once.
    DuplicateStamp { digest: Box<str> },
    /// The same actual census key appeared more than once.
    DuplicateCensusObject { key: LegacyObjectKey },
    /// Expected object signatures did not match.
    CensusMismatch {
        /// Expected objects absent from the live census.
        missing_objects: Vec<LegacyObjectKey>,
        /// Expected objects present with changed signatures.
        changed_objects: Vec<LegacyObjectKey>,
        /// Bounded sorted whole extra objects observed concurrently.
        extra_objects: Vec<LegacyObjectKey>,
    },
    /// One or more whole extra objects were observed.
    UnsupportedLegacyExtras { objects: Vec<LegacyObjectKey> },
    /// Database values could not be decoded into the contract shape.
    Decode { operation: LegacyAdopterOperation },
    /// A fixed row bound was exceeded.
    Bounds {
        resource: LegacyBoundedResource,
        actual: usize,
        max: usize,
    },
    /// Rollback or unlock cleanup failed after otherwise successful verification.
    Cleanup {
        operation: LegacyAdopterOperation,
        diagnostic: Option<PostgresDiagnosticV1>,
    },
    /// Verification failed and one or both bounded cleanup operations also failed.
    VerificationAndCleanup {
        /// Primary refusal/failure, preserved without replacement.
        primary: Box<LegacyAdopterError>,
        /// Ordered rollback/unlock failures; at most two entries.
        cleanup: Vec<LegacyAdopterOperation>,
    },
}

/// Closed production SQL statement identity.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LegacyAdopterSqlKind {
    /// Session lock attempt.
    Lock,
    /// Exact session unlock.
    Unlock,
    /// Transaction-mode verification.
    TransactionSettings,
    /// Future authority schema check.
    AuthoritySchemas,
    /// Stamp table existence check.
    StampTableExists,
    /// Bounded stamp read.
    ReadStamps,
    /// Bounded catalog census.
    CatalogCensus,
}

/// One centrally registered production SQL statement.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LegacyAdopterSqlStatement {
    kind: LegacyAdopterSqlKind,
    sql: &'static str,
}

const LEGACY_ADOPTER_SQL: [LegacyAdopterSqlStatement; 7] = [
    LegacyAdopterSqlStatement {
        kind: LegacyAdopterSqlKind::Lock,
        sql: LOCK_SQL,
    },
    LegacyAdopterSqlStatement {
        kind: LegacyAdopterSqlKind::Unlock,
        sql: UNLOCK_SQL,
    },
    LegacyAdopterSqlStatement {
        kind: LegacyAdopterSqlKind::TransactionSettings,
        sql: TRANSACTION_SETTINGS_SQL,
    },
    LegacyAdopterSqlStatement {
        kind: LegacyAdopterSqlKind::AuthoritySchemas,
        sql: AUTHORITY_SCHEMAS_SQL,
    },
    LegacyAdopterSqlStatement {
        kind: LegacyAdopterSqlKind::StampTableExists,
        sql: STAMP_TABLE_EXISTS_SQL,
    },
    LegacyAdopterSqlStatement {
        kind: LegacyAdopterSqlKind::ReadStamps,
        sql: READ_STAMPS_SQL,
    },
    LegacyAdopterSqlStatement {
        kind: LegacyAdopterSqlKind::CatalogCensus,
        sql: CATALOG_CENSUS_SQL,
    },
];

impl LegacyObjectKey {
    /// Create one validated object key.
    ///
    /// # Errors
    /// Returns [`LegacyCensusParseError::InvalidIdentifier`] for non-canonical names.
    pub fn new(
        kind: LegacyObjectKind,
        schema: &str,
        name: &str,
    ) -> Result<Self, LegacyCensusParseError> {
        if !valid_identifier(schema) || !valid_object_name(name) {
            return Err(LegacyCensusParseError::InvalidIdentifier { line: 0 });
        }
        Ok(Self {
            kind,
            schema: schema.into(),
            name: name.into(),
        })
    }

    /// Decode one key from `PostgreSQL` catalog identifiers.
    ///
    /// Database identifiers may be quoted, mixed-case, or Unicode. This path therefore enforces
    /// only `PostgreSQL`'s nonempty 63-byte identifier ceiling; fixture parsing remains canonical.
    ///
    /// # Errors
    /// Returns [`LegacyAdopterError`] when either database value is empty or byte-unbounded.
    pub fn from_database(
        kind: LegacyObjectKind,
        schema: &str,
        name: &str,
    ) -> Result<Self, LegacyAdopterError> {
        validate_database_identifier(schema)?;
        validate_database_identifier(name)?;
        Ok(Self {
            kind,
            schema: schema.into(),
            name: name.into(),
        })
    }

    /// Return the object kind.
    #[must_use]
    pub fn kind(&self) -> LegacyObjectKind {
        self.kind
    }

    /// Return the schema/category namespace.
    #[must_use]
    pub fn schema(&self) -> &str {
        &self.schema
    }

    /// Return the object name.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }
}

impl LegacyCensusEntry {
    /// Create one validated census entry.
    ///
    /// # Errors
    /// Returns [`LegacyCensusParseError`] when the digest is malformed.
    pub fn new(key: LegacyObjectKey, digest_hex: &str) -> Result<Self, LegacyCensusParseError> {
        if !valid_digest(digest_hex) {
            return Err(LegacyCensusParseError::InvalidDigest { line: 0 });
        }
        Ok(Self {
            key,
            digest_hex: digest_hex.into(),
        })
    }

    /// Return the object key.
    #[must_use]
    pub fn key(&self) -> &LegacyObjectKey {
        &self.key
    }
}

impl LegacyCensus {
    /// Return entries in canonical sorted order.
    #[must_use]
    pub fn entries(&self) -> &[LegacyCensusEntry] {
        &self.entries
    }
}

impl LegacyStampReport {
    /// Return exact matched definitions in input digest order.
    #[must_use]
    pub fn matches(&self) -> &[LegacyStampMatch] {
        &self.matches
    }

    /// Count matches in one typed class.
    #[must_use]
    pub fn matched_count(&self, class: LegacyStampClass) -> usize {
        self.matches
            .iter()
            .take(MAX_LEGACY_STAMP_ROWS)
            .filter(|item| item.definition.class == class)
            .count()
    }
}

impl LegacyAdopterSqlStatement {
    /// Return the statement's closed identity.
    #[must_use]
    pub fn kind(&self) -> LegacyAdopterSqlKind {
        self.kind
    }

    /// Return the exact production SQL.
    #[must_use]
    pub fn sql(&self) -> &'static str {
        self.sql
    }
}

/// Parse the checked-in expected census.
///
/// # Errors
/// Returns [`LegacyCensusParseError`] if the committed fixture is malformed.
pub fn expected_legacy_census() -> Result<LegacyCensus, LegacyCensusParseError> {
    parse_legacy_census_fixture(LEGACY_CENSUS_FIXTURE)
}

/// Parse one bounded, strictly sorted census fixture.
///
/// # Errors
/// Returns [`LegacyCensusParseError`] for malformed or unbounded input.
pub fn parse_legacy_census_fixture(text: &str) -> Result<LegacyCensus, LegacyCensusParseError> {
    if text.len() > MAX_LEGACY_CENSUS_FIXTURE_BYTES {
        return Err(LegacyCensusParseError::TooManyBytes {
            actual: text.len(),
            max: MAX_LEGACY_CENSUS_FIXTURE_BYTES,
        });
    }
    let mut entries = Vec::new();
    let mut keys = BTreeSet::new();
    let mut previous_key: Option<LegacyObjectKey> = None;
    for (line_index, line) in text
        .lines()
        .enumerate()
        .take(MAX_LEGACY_CENSUS_FIXTURE_LINES + 1)
    {
        check_fixture_line_bound(line_index)?;
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let line_number = line_index + 1;
        let entry = parse_census_line(line, line_number)?;
        check_fixture_order(&entry, previous_key.as_ref(), line_number)?;
        if !keys.insert(entry.key.clone()) {
            return Err(LegacyCensusParseError::DuplicateObject { line: line_number });
        }
        previous_key = Some(entry.key.clone());
        entries.push(entry);
        check_fixture_row_bound(entries.len())?;
    }
    if entries.is_empty() {
        return Err(LegacyCensusParseError::Empty);
    }
    Ok(LegacyCensus { entries })
}

/// Compare the expected and actual census after validating actual row bounds and uniqueness.
///
/// # Errors
/// Returns [`LegacyAdopterError`] for unbounded, duplicate, missing, or changed actual objects.
pub fn compare_legacy_census(
    expected: &LegacyCensus,
    actual: &[LegacyCensusEntry],
) -> Result<LegacyAdoptionReport, LegacyAdopterError> {
    let actual_map = checked_census_map(actual)?;
    let expected_map = checked_census_map(expected.entries())?;
    let mut missing_objects = Vec::new();
    let mut changed_objects = Vec::new();
    for (key, expected_digest) in expected_map.iter().take(MAX_LEGACY_CENSUS_ROWS) {
        match actual_map.get(key) {
            Some(actual_digest) if actual_digest == expected_digest => {}
            Some(_) => changed_objects.push(key.clone()),
            None => missing_objects.push(key.clone()),
        }
    }
    let extra_objects = actual_map
        .keys()
        .filter(|key| !expected_map.contains_key(*key))
        .take(MAX_LEGACY_CENSUS_ROWS)
        .cloned()
        .collect::<Vec<_>>();
    if !missing_objects.is_empty() || !changed_objects.is_empty() {
        return Err(LegacyAdopterError::CensusMismatch {
            missing_objects,
            changed_objects,
            extra_objects,
        });
    }
    if !extra_objects.is_empty() {
        return Err(LegacyAdopterError::UnsupportedLegacyExtras {
            objects: extra_objects,
        });
    }
    Ok(LegacyAdoptionReport {
        expected_objects: expected.entries().len(),
        matched_objects: expected.entries().len(),
        extra_objects: Vec::new(),
        stamps: LegacyStampReport {
            matches: Vec::new(),
        },
        transaction_verified: false,
        owner_authority: LegacyOwnerAuthorityDisposition::DeferredToRustMigratorPreflight,
    })
}

/// Validate bounded legacy stamp rows against the exact named catalog.
///
/// # Errors
/// Returns [`LegacyAdopterError`] for missing, unknown, duplicate, malformed, or unbounded stamps.
pub fn validate_legacy_stamps(actual: &[String]) -> Result<LegacyStampReport, LegacyAdopterError> {
    check_row_bound(
        LegacyBoundedResource::StampRows,
        actual.len(),
        MAX_LEGACY_STAMP_ROWS,
    )?;
    let mut seen = BTreeSet::new();
    let mut matches = Vec::new();
    let mut unknown = Vec::new();
    for digest in actual.iter().take(MAX_LEGACY_STAMP_ROWS) {
        if !valid_digest(digest) {
            return Err(LegacyAdopterError::Decode {
                operation: LegacyAdopterOperation::Stamps,
            });
        }
        if !seen.insert(digest.as_str()) {
            return Err(LegacyAdopterError::DuplicateStamp {
                digest: digest.clone().into(),
            });
        }
        match stamp_definition(digest) {
            Some(definition) => matches.push(LegacyStampMatch { definition }),
            None => unknown.push(digest.clone().into_boxed_str()),
        }
    }
    if !unknown.is_empty() {
        return Err(LegacyAdopterError::UnknownStamp { digests: unknown });
    }
    require_current_stamps(matches.as_slice())?;
    Ok(LegacyStampReport { matches })
}

/// Adopt a legacy database only if exact stamps and the frozen census match.
///
/// The function always creates one fresh synchronous `NoTls` connection from a cloned config.
///
/// # Errors
/// Returns [`LegacyAdopterError`] for every expected refusal or database failure.
pub fn adopt_legacy_schema(config: &Config) -> Result<LegacyAdoptionReport, LegacyAdopterError> {
    validate_legacy_connection_target(config)?;
    let mut bounded_config = config.clone();
    bounded_config
        .connect_timeout(LEGACY_ADOPTER_CONNECT_TIMEOUT)
        .tcp_user_timeout(LEGACY_ADOPTER_TCP_USER_TIMEOUT)
        .options(LEGACY_ADOPTER_STARTUP_OPTIONS);
    let mut client = bounded_config
        .connect(NoTls)
        .map_err(|error| connection_error(&error))?;
    acquire_lock(&mut client)?;
    let verification = verify_under_lock(&mut client);
    let unlock = release_lock(&mut client);
    preserve_primary(verification, unlock)
}

/// Require one explicit local-only connection target before any socket is opened.
///
/// # Errors
/// Returns [`LegacyAdopterError::UnsupportedConnectionTarget`] for caller startup options or a
/// missing, remote, DNS, multi-host, or multi-port target.
pub fn validate_legacy_connection_target(config: &Config) -> Result<(), LegacyAdopterError> {
    if config.get_options().is_some() {
        return Err(connection_target_error(
            LegacyConnectionTargetRejection::StartupOptionsOverride,
        ));
    }
    if !config.get_hostaddrs().is_empty() {
        return Err(connection_target_error(
            LegacyConnectionTargetRejection::HostAddressOverride,
        ));
    }
    if config.get_ports().len() > 1 {
        return Err(connection_target_error(
            LegacyConnectionTargetRejection::MultiplePorts,
        ));
    }
    let [host] = config.get_hosts() else {
        let reason = if config.get_hosts().is_empty() {
            LegacyConnectionTargetRejection::MissingHost
        } else {
            LegacyConnectionTargetRejection::MultipleHosts
        };
        return Err(connection_target_error(reason));
    };
    match host {
        Host::Tcp(address) => address
            .parse::<IpAddr>()
            .ok()
            .filter(IpAddr::is_loopback)
            .map_or_else(
                || {
                    Err(connection_target_error(
                        LegacyConnectionTargetRejection::NonLoopbackTcp,
                    ))
                },
                |_| Ok(()),
            ),
        Host::Unix(path) if path.is_absolute() => Ok(()),
        Host::Unix(_) => Err(connection_target_error(
            LegacyConnectionTargetRejection::NonAbsoluteUnixSocket,
        )),
    }
}

/// Return the central production SQL registry for authority audits.
#[must_use]
pub fn legacy_adopter_sql_statements() -> &'static [LegacyAdopterSqlStatement] {
    &LEGACY_ADOPTER_SQL
}

fn statement(kind: LegacyAdopterSqlKind) -> &'static str {
    match kind {
        LegacyAdopterSqlKind::Lock => LEGACY_ADOPTER_SQL[0].sql,
        LegacyAdopterSqlKind::Unlock => LEGACY_ADOPTER_SQL[1].sql,
        LegacyAdopterSqlKind::TransactionSettings => LEGACY_ADOPTER_SQL[2].sql,
        LegacyAdopterSqlKind::AuthoritySchemas => LEGACY_ADOPTER_SQL[3].sql,
        LegacyAdopterSqlKind::StampTableExists => LEGACY_ADOPTER_SQL[4].sql,
        LegacyAdopterSqlKind::ReadStamps => LEGACY_ADOPTER_SQL[5].sql,
        LegacyAdopterSqlKind::CatalogCensus => LEGACY_ADOPTER_SQL[6].sql,
    }
}

pub(crate) fn verify_under_lock(
    client: &mut postgres::Client,
) -> Result<LegacyAdoptionReport, LegacyAdopterError> {
    let mut transaction = client
        .build_transaction()
        .isolation_level(IsolationLevel::RepeatableRead)
        .read_only(true)
        .start()
        .map_err(|error| transaction_error(&error, LegacyAdopterOperation::BeginTransaction))?;
    let verification = verify_transaction(&mut transaction);
    let rollback = transaction
        .rollback()
        .map_err(|error| LegacyAdopterError::Cleanup {
            operation: LegacyAdopterOperation::Rollback,
            diagnostic: Some(PostgresDiagnosticV1::capture(&error)),
        });
    preserve_primary(verification, rollback)
}

pub(crate) fn catalog_census_under_lock(
    client: &mut postgres::Client,
    require_authority_schemas_absent: bool,
) -> Result<Vec<LegacyCensusEntry>, LegacyAdopterError> {
    let mut transaction = client
        .build_transaction()
        .isolation_level(IsolationLevel::RepeatableRead)
        .read_only(true)
        .start()
        .map_err(|error| transaction_error(&error, LegacyAdopterOperation::BeginTransaction))?;
    let census = catalog_census_transaction(&mut transaction, require_authority_schemas_absent);
    let rollback = transaction
        .rollback()
        .map_err(|error| LegacyAdopterError::Cleanup {
            operation: LegacyAdopterOperation::Rollback,
            diagnostic: Some(PostgresDiagnosticV1::capture(&error)),
        });
    preserve_primary(census, rollback)
}

fn catalog_census_transaction(
    transaction: &mut Transaction<'_>,
    require_authority_schemas_absent: bool,
) -> Result<Vec<LegacyCensusEntry>, LegacyAdopterError> {
    verify_transaction_settings(transaction)?;
    if require_authority_schemas_absent {
        refuse_authority_schemas(transaction)?;
    }
    read_census_rows(transaction)
}

fn verify_transaction(
    transaction: &mut Transaction<'_>,
) -> Result<LegacyAdoptionReport, LegacyAdopterError> {
    verify_transaction_settings(transaction)?;
    refuse_authority_schemas(transaction)?;
    if !stamp_table_exists(transaction)? {
        return Err(LegacyAdopterError::StampTableMissing);
    }
    let expected = expected_legacy_census().map_err(|_| LegacyAdopterError::Decode {
        operation: LegacyAdopterOperation::Census,
    })?;
    let actual = read_census_rows(transaction)?;
    verify_stamp_table_shape(&expected, actual.as_slice())?;
    let stamp_report = validate_legacy_stamps(&read_stamp_rows(transaction)?)?;
    let mut report = compare_legacy_census(&expected, actual.as_slice())?;
    report.stamps = stamp_report;
    report.transaction_verified = true;
    Ok(report)
}

fn verify_transaction_settings(
    transaction: &mut Transaction<'_>,
) -> Result<(), LegacyAdopterError> {
    let operation = LegacyAdopterOperation::VerifyTransaction;
    let row = transaction
        .query_one(statement(LegacyAdopterSqlKind::TransactionSettings), &[])
        .map_err(|error| query_error(&error, operation))?;
    let isolation = try_text(&row, 0, operation)?;
    let read_only = try_text(&row, 1, operation)?;
    let search_path = try_text(&row, 2, operation)?;
    let jit = try_text(&row, 3, operation)?;
    let event_triggers = try_text(&row, 4, operation)?;
    let statement_timeout = try_text(&row, 5, operation)?;
    let lock_timeout = try_text(&row, 6, operation)?;
    let idle_timeout = try_text(&row, 7, operation)?;
    let quote_all_identifiers = try_text(&row, 8, operation)?;
    if isolation == "repeatable read"
        && read_only == "on"
        && search_path == "pg_catalog"
        && jit == "off"
        && event_triggers == "off"
        && statement_timeout == "5s"
        && lock_timeout == "5s"
        && idle_timeout == "5s"
        && quote_all_identifiers == "off"
    {
        Ok(())
    } else {
        Err(LegacyAdopterError::Transaction {
            operation,
            diagnostic: None,
        })
    }
}

fn refuse_authority_schemas(transaction: &mut Transaction<'_>) -> Result<(), LegacyAdopterError> {
    let operation = LegacyAdopterOperation::AuthoritySchemas;
    let rows = transaction
        .query(statement(LegacyAdopterSqlKind::AuthoritySchemas), &[])
        .map_err(|error| query_error(&error, operation))?;
    check_row_bound(LegacyBoundedResource::AuthoritySchemas, rows.len(), 2)?;
    let mut schemas = Vec::with_capacity(rows.len());
    for row in rows.iter().take(2) {
        schemas.push(try_text(row, 0, operation)?.into_boxed_str());
    }
    if schemas.is_empty() {
        Ok(())
    } else {
        Err(LegacyAdopterError::UnsupportedAuthorityEpoch { schemas })
    }
}

fn stamp_table_exists(transaction: &mut Transaction<'_>) -> Result<bool, LegacyAdopterError> {
    let operation = LegacyAdopterOperation::StampTable;
    transaction
        .query_one(statement(LegacyAdopterSqlKind::StampTableExists), &[])
        .map_err(|error| query_error(&error, operation))?
        .try_get(0)
        .map_err(|_| LegacyAdopterError::Decode { operation })
}

fn read_stamp_rows(transaction: &mut Transaction<'_>) -> Result<Vec<String>, LegacyAdopterError> {
    let operation = LegacyAdopterOperation::Stamps;
    let limit = bounded_limit(MAX_LEGACY_STAMP_ROWS, LegacyBoundedResource::StampRows)?;
    let prefix_bytes = 64_i32;
    let rows = transaction
        .query(
            statement(LegacyAdopterSqlKind::ReadStamps),
            &[&limit, &prefix_bytes],
        )
        .map_err(|error| query_error(&error, operation))?;
    check_row_bound(
        LegacyBoundedResource::StampRows,
        rows.len(),
        MAX_LEGACY_STAMP_ROWS,
    )?;
    let mut stamps = Vec::with_capacity(rows.len());
    for row in rows.iter().take(MAX_LEGACY_STAMP_ROWS) {
        let prefix = try_text(row, 0, operation)?;
        let bytes: i32 = row
            .try_get(1)
            .map_err(|_| LegacyAdopterError::Decode { operation })?;
        let actual =
            usize::try_from(bytes).map_err(|_| LegacyAdopterError::Decode { operation })?;
        if actual > 64 {
            return Err(LegacyAdopterError::Bounds {
                resource: LegacyBoundedResource::StampBytes,
                actual,
                max: 64,
            });
        }
        stamps.push(prefix);
    }
    Ok(stamps)
}

pub(crate) fn read_census_rows(
    transaction: &mut Transaction<'_>,
) -> Result<Vec<LegacyCensusEntry>, LegacyAdopterError> {
    let operation = LegacyAdopterOperation::Census;
    let row_limit = bounded_limit(MAX_LEGACY_CENSUS_ROWS, LegacyBoundedResource::CensusRows)?;
    let partition_limit = bounded_limit(
        MAX_LEGACY_PARTITIONS_PER_FAMILY,
        LegacyBoundedResource::PartitionRows,
    )?;
    let extension_member_limit = bounded_limit(
        MAX_LEGACY_EXTENSION_MEMBERS,
        LegacyBoundedResource::ExtensionMembers,
    )?;
    let extension_dependency_address_limit = bounded_limit(
        MAX_LEGACY_EXTENSION_DEPENDENCY_ADDRESSES,
        LegacyBoundedResource::ExtensionDependencyAddresses,
    )?;
    let extension_role_identity_limit = bounded_limit(
        MAX_LEGACY_EXTENSION_ROLE_IDENTITIES,
        LegacyBoundedResource::ExtensionRoleIdentities,
    )?;
    let sequence_ownership_limit = bounded_limit(
        MAX_LEGACY_SEQUENCE_OWNERSHIP,
        LegacyBoundedResource::SequenceOwnership,
    )?;
    let rows = transaction
        .query(
            statement(LegacyAdopterSqlKind::CatalogCensus),
            &[
                &row_limit,
                &partition_limit,
                &extension_member_limit,
                &extension_dependency_address_limit,
                &sequence_ownership_limit,
                &extension_role_identity_limit,
            ],
        )
        .map_err(|error| query_error(&error, operation))?;
    decode_census_rows(rows.as_slice())
}

fn decode_census_rows(rows: &[Row]) -> Result<Vec<LegacyCensusEntry>, LegacyAdopterError> {
    let operation = LegacyAdopterOperation::Census;
    let first = rows
        .first()
        .ok_or(LegacyAdopterError::Decode { operation })?;
    decode_catalog_overflow(first)?;
    check_row_bound(
        LegacyBoundedResource::CensusRows,
        rows.len(),
        MAX_LEGACY_CENSUS_ROWS,
    )?;
    let mut entries = Vec::with_capacity(rows.len());
    let mut keys = BTreeSet::new();
    for row in rows.iter().take(MAX_LEGACY_CENSUS_ROWS) {
        let kind = parse_kind(try_text(row, 0, operation)?.as_str())
            .ok_or(LegacyAdopterError::Decode { operation })?;
        let schema = try_text(row, 1, operation)?;
        let name = try_text(row, 2, operation)?;
        let digest = try_text(row, 3, operation)?;
        let key = LegacyObjectKey::from_database(kind, &schema, &name)?;
        if !keys.insert(key.clone()) {
            return Err(LegacyAdopterError::DuplicateCensusObject { key });
        }
        entries.push(
            LegacyCensusEntry::new(key, &digest)
                .map_err(|_| LegacyAdopterError::Decode { operation })?,
        );
    }
    Ok(entries)
}

fn decode_catalog_overflow(row: &Row) -> Result<(), LegacyAdopterError> {
    let operation = LegacyAdopterOperation::Census;
    let raw_resource: Option<String> = row
        .try_get(4)
        .map_err(|_| LegacyAdopterError::Decode { operation })?;
    let actual: Option<i64> = row
        .try_get(5)
        .map_err(|_| LegacyAdopterError::Decode { operation })?;
    let max: Option<i64> = row
        .try_get(6)
        .map_err(|_| LegacyAdopterError::Decode { operation })?;
    let (raw_resource, actual, max) = match (raw_resource, actual, max) {
        (None, None, None) => return Ok(()),
        (Some(resource), Some(actual), Some(max)) => (resource, actual, max),
        _ => return Err(LegacyAdopterError::Decode { operation }),
    };
    let resource =
        parse_bounded_resource(&raw_resource).ok_or(LegacyAdopterError::Decode { operation })?;
    let actual = usize::try_from(actual).map_err(|_| LegacyAdopterError::Decode { operation })?;
    let max = usize::try_from(max).map_err(|_| LegacyAdopterError::Decode { operation })?;
    Err(LegacyAdopterError::Bounds {
        resource,
        actual,
        max,
    })
}

pub(crate) fn acquire_lock(client: &mut postgres::Client) -> Result<(), LegacyAdopterError> {
    let operation = LegacyAdopterOperation::Lock;
    let locked: bool = client
        .query_one(
            statement(LegacyAdopterSqlKind::Lock),
            &[&SCHEMA_ADVISORY_LOCK_KEY],
        )
        .map_err(|error| query_error(&error, operation))?
        .try_get(0)
        .map_err(|_| LegacyAdopterError::Decode { operation })?;
    if locked {
        Ok(())
    } else {
        Err(LegacyAdopterError::LockUnavailable)
    }
}

pub(crate) fn release_lock(client: &mut postgres::Client) -> Result<(), LegacyAdopterError> {
    let operation = LegacyAdopterOperation::Unlock;
    let row = client
        .query_one(
            statement(LegacyAdopterSqlKind::Unlock),
            &[&SCHEMA_ADVISORY_LOCK_KEY],
        )
        .map_err(|error| LegacyAdopterError::Cleanup {
            operation,
            diagnostic: Some(PostgresDiagnosticV1::capture(&error)),
        })?;
    let unlocked: bool = row
        .try_get(0)
        .map_err(|error| LegacyAdopterError::Cleanup {
            operation,
            diagnostic: Some(PostgresDiagnosticV1::capture(&error)),
        })?;
    if unlocked {
        Ok(())
    } else {
        Err(LegacyAdopterError::Cleanup {
            operation,
            diagnostic: None,
        })
    }
}

pub(crate) fn preserve_primary<T>(
    primary: Result<T, LegacyAdopterError>,
    cleanup: Result<(), LegacyAdopterError>,
) -> Result<T, LegacyAdopterError> {
    match (primary, cleanup) {
        (Ok(value), Ok(())) => Ok(value),
        (Ok(_), Err(cleanup_error)) => Err(cleanup_error),
        (Err(primary_error), Ok(())) => Err(primary_error),
        (Err(primary_error), Err(cleanup_error)) => {
            Err(combine_primary_cleanup(primary_error, &cleanup_error))
        }
    }
}

fn combine_primary_cleanup(
    primary: LegacyAdopterError,
    cleanup_error: &LegacyAdopterError,
) -> LegacyAdopterError {
    let LegacyAdopterError::Cleanup { operation, .. } = cleanup_error else {
        return primary;
    };
    if let LegacyAdopterError::VerificationAndCleanup {
        primary,
        cleanup: prior_cleanup,
    } = primary
    {
        let mut cleanup = Vec::with_capacity(2);
        cleanup.extend(prior_cleanup.into_iter().take(2));
        if cleanup.len() < 2 {
            cleanup.push(*operation);
        }
        LegacyAdopterError::VerificationAndCleanup { primary, cleanup }
    } else {
        LegacyAdopterError::VerificationAndCleanup {
            primary: Box::new(primary),
            cleanup: vec![*operation],
        }
    }
}

fn checked_census_map(
    entries: &[LegacyCensusEntry],
) -> Result<BTreeMap<LegacyObjectKey, Box<str>>, LegacyAdopterError> {
    check_row_bound(
        LegacyBoundedResource::CensusRows,
        entries.len(),
        MAX_LEGACY_CENSUS_ROWS,
    )?;
    let mut map = BTreeMap::new();
    for entry in entries.iter().take(MAX_LEGACY_CENSUS_ROWS) {
        if map
            .insert(entry.key.clone(), entry.digest_hex.clone())
            .is_some()
        {
            return Err(LegacyAdopterError::DuplicateCensusObject {
                key: entry.key.clone(),
            });
        }
    }
    Ok(map)
}

fn verify_stamp_table_shape(
    expected: &LegacyCensus,
    actual: &[LegacyCensusEntry],
) -> Result<(), LegacyAdopterError> {
    let stamp_key = LegacyObjectKey::new(
        LegacyObjectKind::Relation,
        "public",
        "_babylon_schema_stamp",
    )
    .map_err(|_| LegacyAdopterError::Decode {
        operation: LegacyAdopterOperation::Census,
    })?;
    let expected_map = checked_census_map(expected.entries())?;
    let actual_map = checked_census_map(actual)?;
    let Some(expected_digest) = expected_map.get(&stamp_key) else {
        return Err(LegacyAdopterError::Decode {
            operation: LegacyAdopterOperation::Census,
        });
    };
    match actual_map.get(&stamp_key) {
        Some(actual_digest) if actual_digest == expected_digest => Ok(()),
        Some(_) => Err(LegacyAdopterError::CensusMismatch {
            missing_objects: Vec::new(),
            changed_objects: vec![stamp_key],
            extra_objects: Vec::new(),
        }),
        None => Err(LegacyAdopterError::CensusMismatch {
            missing_objects: vec![stamp_key],
            changed_objects: Vec::new(),
            extra_objects: Vec::new(),
        }),
    }
}

fn parse_census_line(
    line: &str,
    line_number: usize,
) -> Result<LegacyCensusEntry, LegacyCensusParseError> {
    let field_count = census_field_count(line);
    let mut fields = line.split('|');
    let kind = fields.next();
    let schema = fields.next();
    let name = fields.next();
    let digest = fields.next();
    let fifth = fields.next();
    let (Some(kind), Some(schema), Some(name), Some(digest), None) =
        (kind, schema, name, digest, fifth)
    else {
        return Err(LegacyCensusParseError::MalformedRecord {
            line: line_number,
            fields: field_count,
        });
    };
    let kind = parse_kind(kind).ok_or(LegacyCensusParseError::InvalidKind { line: line_number })?;
    let key = LegacyObjectKey::new(kind, schema, name)
        .map_err(|_| LegacyCensusParseError::InvalidIdentifier { line: line_number })?;
    LegacyCensusEntry::new(key, digest)
        .map_err(|_| LegacyCensusParseError::InvalidDigest { line: line_number })
}

fn census_field_count(line: &str) -> usize {
    line.as_bytes()
        .iter()
        .take(MAX_LEGACY_CENSUS_FIXTURE_BYTES + 1)
        .filter(|byte| **byte == b'|')
        .count()
        .checked_add(1)
        .expect("bounded census field count must fit usize")
}

fn parse_kind(raw: &str) -> Option<LegacyObjectKind> {
    match raw {
        "database" => Some(LegacyObjectKind::Database),
        "domain" => Some(LegacyObjectKind::Domain),
        "extension" => Some(LegacyObjectKind::Extension),
        "foreign_table" => Some(LegacyObjectKind::ForeignTable),
        "materialized_view" => Some(LegacyObjectKind::MaterializedView),
        "partitioned_table" => Some(LegacyObjectKind::PartitionedTable),
        "relation" => Some(LegacyObjectKind::Relation),
        "role" => Some(LegacyObjectKind::Role),
        "routine" => Some(LegacyObjectKind::Routine),
        "schema" => Some(LegacyObjectKind::Schema),
        "schema_grant" => Some(LegacyObjectKind::SchemaGrant),
        "sequence" => Some(LegacyObjectKind::Sequence),
        "unsupported_catalog" => Some(LegacyObjectKind::UnsupportedCatalog),
        "user_type" => Some(LegacyObjectKind::UserType),
        "view" => Some(LegacyObjectKind::View),
        _ => None,
    }
}

fn parse_bounded_resource(raw: &str) -> Option<LegacyBoundedResource> {
    match raw {
        "census_rows" => Some(LegacyBoundedResource::CensusRows),
        "catalog_rows" => Some(LegacyBoundedResource::CatalogRows),
        "partition_rows" => Some(LegacyBoundedResource::PartitionRows),
        "extension_members" => Some(LegacyBoundedResource::ExtensionMembers),
        "extension_dependency_addresses" => {
            Some(LegacyBoundedResource::ExtensionDependencyAddresses)
        }
        "extension_role_identities" => Some(LegacyBoundedResource::ExtensionRoleIdentities),
        "sequence_ownership" => Some(LegacyBoundedResource::SequenceOwnership),
        _ => None,
    }
}

fn stamp_definition(digest: &str) -> Option<LegacyStampDefinition> {
    LEGACY_STAMP_CATALOG
        .iter()
        .take(LEGACY_STAMP_CATALOG.len())
        .copied()
        .find(|definition| definition.digest_hex == digest)
}

fn require_current_stamps(matches: &[LegacyStampMatch]) -> Result<(), LegacyAdopterError> {
    let mut missing = Vec::new();
    for definition in LEGACY_STAMP_CATALOG
        .iter()
        .filter(|item| item.class == LegacyStampClass::RequiredCurrent)
        .take(2)
    {
        if !matches
            .iter()
            .take(MAX_LEGACY_STAMP_ROWS)
            .any(|item| item.definition == *definition)
        {
            missing.push(*definition);
        }
    }
    if missing.is_empty() {
        Ok(())
    } else {
        Err(LegacyAdopterError::RequiredStampMissing { missing })
    }
}

fn check_fixture_line_bound(line_index: usize) -> Result<(), LegacyCensusParseError> {
    if line_index < MAX_LEGACY_CENSUS_FIXTURE_LINES {
        Ok(())
    } else {
        Err(LegacyCensusParseError::TooManyLines {
            max: MAX_LEGACY_CENSUS_FIXTURE_LINES,
        })
    }
}

fn check_fixture_row_bound(actual: usize) -> Result<(), LegacyCensusParseError> {
    if actual <= MAX_LEGACY_CENSUS_ROWS {
        Ok(())
    } else {
        Err(LegacyCensusParseError::TooManyRows {
            actual,
            max: MAX_LEGACY_CENSUS_ROWS,
        })
    }
}

fn check_fixture_order(
    entry: &LegacyCensusEntry,
    previous: Option<&LegacyObjectKey>,
    line: usize,
) -> Result<(), LegacyCensusParseError> {
    if previous.is_some_and(|key| key > entry.key()) {
        Err(LegacyCensusParseError::OutOfOrder { line })
    } else {
        Ok(())
    }
}

fn check_row_bound(
    resource: LegacyBoundedResource,
    actual: usize,
    max: usize,
) -> Result<(), LegacyAdopterError> {
    if actual <= max {
        Ok(())
    } else {
        Err(LegacyAdopterError::Bounds {
            resource,
            actual,
            max,
        })
    }
}

fn bounded_limit(max: usize, resource: LegacyBoundedResource) -> Result<i64, LegacyAdopterError> {
    let actual = max.checked_add(1).ok_or(LegacyAdopterError::Bounds {
        resource,
        actual: max,
        max,
    })?;
    i64::try_from(actual).map_err(|_| LegacyAdopterError::Bounds {
        resource,
        actual,
        max,
    })
}

fn try_text(
    row: &Row,
    index: usize,
    operation: LegacyAdopterOperation,
) -> Result<String, LegacyAdopterError> {
    row.try_get(index)
        .map_err(|_| LegacyAdopterError::Decode { operation })
}

fn transaction_error(
    error: &postgres::Error,
    operation: LegacyAdopterOperation,
) -> LegacyAdopterError {
    let diagnostic = PostgresDiagnosticV1::capture(error);
    if is_timeout(error) {
        LegacyAdopterError::Timeout {
            operation,
            diagnostic,
        }
    } else {
        LegacyAdopterError::Transaction {
            operation,
            diagnostic: Some(diagnostic),
        }
    }
}

fn connection_error(error: &postgres::Error) -> LegacyAdopterError {
    let diagnostic = PostgresDiagnosticV1::capture(error);
    if error.code() == Some(&postgres::error::SqlState::INSUFFICIENT_PRIVILEGE) {
        LegacyAdopterError::EventTriggerSuppressionUnavailable { diagnostic }
    } else if is_timeout(error) {
        LegacyAdopterError::Timeout {
            operation: LegacyAdopterOperation::Connect,
            diagnostic,
        }
    } else {
        LegacyAdopterError::Connection { diagnostic }
    }
}

fn query_error(error: &postgres::Error, operation: LegacyAdopterOperation) -> LegacyAdopterError {
    let diagnostic = PostgresDiagnosticV1::capture(error);
    if is_timeout(error) {
        LegacyAdopterError::Timeout {
            operation,
            diagnostic,
        }
    } else {
        LegacyAdopterError::Query {
            operation,
            diagnostic,
        }
    }
}

fn is_timeout(error: &postgres::Error) -> bool {
    error.code().is_some_and(|code| {
        code == &postgres::error::SqlState::QUERY_CANCELED
            || code == &postgres::error::SqlState::LOCK_NOT_AVAILABLE
    }) || error_chain_has_timeout(error)
}

fn error_chain_has_timeout(error: &(dyn std::error::Error + 'static)) -> bool {
    let mut current = Some(error);
    for _depth in 0..MAX_ERROR_SOURCE_DEPTH {
        let Some(source) = current else {
            return false;
        };
        if source
            .downcast_ref::<std::io::Error>()
            .is_some_and(|io_error| io_error.kind() == std::io::ErrorKind::TimedOut)
        {
            return true;
        }
        current = source.source();
    }
    false
}

fn valid_digest(text: &str) -> bool {
    text.len() == 64
        && text
            .bytes()
            .take(POSTGRES_IDENTIFIER_MAX_BYTES + 1)
            .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
}

fn valid_identifier(text: &str) -> bool {
    valid_identifier_length(text) && valid_identifier_bytes(text, false)
}

fn validate_database_identifier(text: &str) -> Result<(), LegacyAdopterError> {
    validate_database_identifier_for(text, LegacyAdopterOperation::Census)
}

fn validate_database_identifier_for(
    text: &str,
    operation: LegacyAdopterOperation,
) -> Result<(), LegacyAdopterError> {
    if text.is_empty() || text.contains('\0') {
        return Err(LegacyAdopterError::Decode { operation });
    }
    if text.len() > POSTGRES_IDENTIFIER_MAX_BYTES {
        return Err(LegacyAdopterError::Bounds {
            resource: LegacyBoundedResource::IdentifierBytes,
            actual: text.len(),
            max: POSTGRES_IDENTIFIER_MAX_BYTES,
        });
    }
    Ok(())
}

fn connection_target_error(reason: LegacyConnectionTargetRejection) -> LegacyAdopterError {
    LegacyAdopterError::UnsupportedConnectionTarget { reason }
}

fn valid_object_name(text: &str) -> bool {
    valid_identifier_length(text) && valid_identifier_bytes(text, true)
}

fn valid_identifier_length(text: &str) -> bool {
    !text.is_empty() && text.len() <= POSTGRES_IDENTIFIER_MAX_BYTES
}

fn valid_identifier_bytes(text: &str, allow_hyphen: bool) -> bool {
    let mut bytes = text.bytes().take(POSTGRES_IDENTIFIER_MAX_BYTES + 1);
    let Some(first) = bytes.next() else {
        return false;
    };
    matches!(first, b'a'..=b'z' | b'_')
        && bytes.all(|byte| {
            matches!(byte, b'a'..=b'z' | b'0'..=b'9' | b'_') || (allow_hyphen && byte == b'-')
        })
}

impl std::fmt::Display for LegacyCensusParseError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "invalid legacy census fixture: {self:?}")
    }
}

impl std::error::Error for LegacyCensusParseError {}

impl std::fmt::Display for LegacyAdopterError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "legacy adopter failure: {self:?}")
    }
}

impl std::error::Error for LegacyAdopterError {}

#[cfg(test)]
mod tests {
    use super::{
        check_row_bound, error_chain_has_timeout, preserve_primary, LegacyAdopterError,
        LegacyAdopterOperation, LegacyBoundedResource, MAX_LEGACY_EXTENSION_DEPENDENCY_ADDRESSES,
    };

    #[test]
    fn extension_dependency_address_bound_refuses_first_excess() {
        let actual = 16_385_usize;
        assert_eq!(actual, MAX_LEGACY_EXTENSION_DEPENDENCY_ADDRESSES + 1);
        assert_eq!(
            check_row_bound(
                LegacyBoundedResource::ExtensionDependencyAddresses,
                actual,
                MAX_LEGACY_EXTENSION_DEPENDENCY_ADDRESSES,
            ),
            Err(LegacyAdopterError::Bounds {
                resource: LegacyBoundedResource::ExtensionDependencyAddresses,
                actual,
                max: MAX_LEGACY_EXTENSION_DEPENDENCY_ADDRESSES,
            })
        );
    }

    #[test]
    fn primary_verification_failure_preserves_bounded_cleanup_evidence() {
        let primary = LegacyAdopterError::Decode {
            operation: LegacyAdopterOperation::Census,
        };
        let cleanup = LegacyAdopterError::Cleanup {
            operation: LegacyAdopterOperation::Rollback,
            diagnostic: None,
        };
        assert_eq!(
            preserve_primary::<()>(Err(primary.clone()), Err(cleanup)),
            Err(LegacyAdopterError::VerificationAndCleanup {
                primary: Box::new(primary),
                cleanup: vec![LegacyAdopterOperation::Rollback],
            })
        );
    }

    #[test]
    fn rollback_and_unlock_failures_are_bounded_and_ordered() {
        let primary = LegacyAdopterError::Decode {
            operation: LegacyAdopterOperation::Census,
        };
        let rollback = LegacyAdopterError::Cleanup {
            operation: LegacyAdopterOperation::Rollback,
            diagnostic: None,
        };
        let unlock = LegacyAdopterError::Cleanup {
            operation: LegacyAdopterOperation::Unlock,
            diagnostic: None,
        };
        let after_rollback = preserve_primary::<()>(Err(primary.clone()), Err(rollback));
        assert_eq!(
            preserve_primary::<()>(after_rollback, Err(unlock)),
            Err(LegacyAdopterError::VerificationAndCleanup {
                primary: Box::new(primary),
                cleanup: vec![
                    LegacyAdopterOperation::Rollback,
                    LegacyAdopterOperation::Unlock,
                ],
            })
        );
    }

    #[test]
    fn io_timeout_is_classified_without_exposing_error_text() {
        let timeout = std::io::Error::new(std::io::ErrorKind::TimedOut, "secret-bearing context");
        let refused = std::io::Error::new(std::io::ErrorKind::ConnectionRefused, "ordinary error");
        assert!(error_chain_has_timeout(&timeout));
        assert!(!error_chain_has_timeout(&refused));
    }
}
