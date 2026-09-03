//! Fog-safe read-only Archive reader handle and the additive reader-role installer (ADR249 R8).
//!
//! `SemanticArchiveReaderV1` is the split read-only counterpart of
//! [`SemanticArchiveStoreV1`](crate::SemanticArchiveStoreV1): it exposes
//! search and projection reads and is structurally incapable of schema
//! installation, knowledge grants, or receipt materialization. Client
//! credentials ship with the client, so fog is enforced by the `PostgreSQL`
//! privilege layer (`babylon_reader` holds `SELECT` on the fog-safe views
//! only) and by the validated local-only connection target, not by client
//! courtesy.

use std::str::FromStr;

use postgres::{Config, NoTls};

use crate::archive::{
    database, decode, decode_digest, decode_search_hit, validate_text, ArchiveSearchHitV1,
    SemanticArchiveErrorV1, ARCHIVE_SEARCH_SQL_V1, MAX_SEARCH_HITS,
};
use crate::identity::CampaignId;
use crate::legacy_adopter::{
    validate_legacy_connection_target, LegacyAdopterError, LegacyConnectionTargetRejection,
    LEGACY_ADOPTER_CONNECT_TIMEOUT, LEGACY_ADOPTER_STARTUP_OPTIONS,
    LEGACY_ADOPTER_TCP_USER_TIMEOUT,
};
use crate::migration_manifest::SCHEMA_ADVISORY_LOCK_KEY;
use crate::postgres_diagnostic::PostgresDiagnosticV1;

/// Environment variable admitting the read-only reader DSN.
pub const READER_DSN_ENV_V1: &str = "BABYLON_READER_DSN";
/// Exact dedicated read-only role identity.
pub const READER_ROLE_NAME_V1: &str = "babylon_reader";
/// Exact fog-safe acknowledged-commit tick-status relation.
pub const COMMITTED_TICK_STATUS_VIEW_V1: &str = "public.v_committed_tick_status_v1";
/// Exact role DDL. `CREATE ROLE` cannot run inside a transaction, so the
/// installer executes this statement outside its view/grant transaction.
pub const READER_ROLE_CREATE_SQL_V1: &str =
    "CREATE ROLE babylon_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE";
/// Transactional additive schema: the tick-status view, its exact SELECT
/// grant, and the guarded archive-table revokes.
pub const READER_ROLE_SCHEMA_V1_SQL: &str = include_str!("../migrations/reader_role_v1.sql");

const READER_ROLE_MARKERS_SQL_V1: &str = "SELECT \
    EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'babylon_reader'), \
    pg_catalog.to_regclass('public.v_committed_tick_status_v1') IS NOT NULL";
const READER_ROLE_ATTRIBUTES_SQL_V1: &str = "SELECT rolsuper, rolcreatedb, rolcreaterole, \
    rolcanlogin FROM pg_catalog.pg_roles WHERE rolname = 'babylon_reader'";
const READER_VIEW_GRANT_SQL_V1: &str = "SELECT pg_catalog.has_table_privilege(\
    'babylon_reader', 'public.v_committed_tick_status_v1', 'SELECT')";
/// Known-acknowledged-commit tick status read. The read goes through the view
/// only; `babylon_state.tick_commit` stays revoked from the reader role.
pub const COMMITTED_TICK_STATUS_SQL_V1: &str = "SELECT campaign_id, resolve_tick, \
    envelope_layout_version, tick_content_hash, envelope_digest \
    FROM public.v_committed_tick_status_v1 \
    WHERE campaign_id = $1::uuid \
    ORDER BY resolve_tick DESC LIMIT 1";

/// One acknowledged-commit tail row observed through the fog-safe view.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CommittedTickStatusV1 {
    campaign_id: CampaignId,
    resolve_tick: u64,
    envelope_layout_version: i16,
    tick_content_hash: [u8; 32],
    envelope_digest: [u8; 32],
}

impl CommittedTickStatusV1 {
    /// Borrow the committed campaign identity.
    #[must_use]
    pub const fn campaign_id(&self) -> &CampaignId {
        &self.campaign_id
    }

    /// Return the acknowledged durable resolve tick.
    #[must_use]
    pub const fn resolve_tick(&self) -> u64 {
        self.resolve_tick
    }

    /// Return the committed envelope layout version.
    #[must_use]
    pub const fn envelope_layout_version(&self) -> i16 {
        self.envelope_layout_version
    }

    /// Return the exact committed tick content hash.
    #[must_use]
    pub const fn tick_content_hash(&self) -> &[u8; 32] {
        &self.tick_content_hash
    }

    /// Return the exact committed envelope digest.
    #[must_use]
    pub const fn envelope_digest(&self) -> &[u8; 32] {
        &self.envelope_digest
    }
}

/// Idempotent reader-role install result.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ReaderRoleDispositionV1 {
    /// The role, view, or grants committed now.
    Installed,
    /// The exact role attributes, view, and view grant already existed.
    AlreadyCurrent,
}

/// Stable closed refusal taxonomy for reader construction and installation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum SemanticArchiveReaderErrorV1 {
    /// The reader DSN environment variable is unset.
    MissingEnv(&'static str),
    /// The reader DSN environment variable is not valid UTF-8.
    EnvNotUtf8(&'static str),
    /// The reader DSN did not parse as one `PostgreSQL` configuration.
    InvalidDsn,
    /// The parsed target violated the local-only connection contract.
    ConnectionTarget(LegacyConnectionTargetRejection),
    /// An existing `babylon_reader` role does not have the exact locked attributes.
    RoleMismatch,
    /// The view exists without the exact reader `SELECT` grant.
    ViewMismatch,
    /// The advisory lock did not release from this session.
    LockMismatch,
    /// One database operation failed with a bounded secret-safe driver diagnostic.
    Database {
        /// Stable operation identity.
        operation: &'static str,
        /// Secret-safe `PostgreSQL` classification, SQLSTATE, and message.
        diagnostic: PostgresDiagnosticV1,
    },
}

impl std::fmt::Display for SemanticArchiveReaderErrorV1 {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "semantic Archive reader refusal: {self:?}")
    }
}

impl std::error::Error for SemanticArchiveReaderErrorV1 {}

fn database_error(
    operation: &'static str,
    error: &postgres::Error,
) -> SemanticArchiveReaderErrorV1 {
    SemanticArchiveReaderErrorV1::Database {
        operation,
        diagnostic: PostgresDiagnosticV1::capture(error),
    }
}

fn connection_target_error(error: &LegacyAdopterError) -> SemanticArchiveReaderErrorV1 {
    // The validator is a pure target check: its only failure construction is
    // one bounded target rejection, so any other variant is an internal fault.
    let LegacyAdopterError::UnsupportedConnectionTarget { reason } = error else {
        unreachable!("connection target validation only reports target rejections")
    };
    SemanticArchiveReaderErrorV1::ConnectionTarget(*reason)
}

/// Split read-only `PostgreSQL` handle for fog-safe Archive reads.
///
/// Writer operations (`install_schema`, `grant_knowledge`,
/// `materialize_receipt`, worker sweeps) are unrepresentable on this type;
/// [`SemanticArchiveStoreV1`](crate::SemanticArchiveStoreV1) and the runtime
/// binary remain the sole writers.
#[derive(Clone)]
pub struct SemanticArchiveReaderV1 {
    config: Config,
}

impl SemanticArchiveReaderV1 {
    /// Parse and validate one explicit local-only reader DSN.
    ///
    /// The raw parsed [`Config`] is validated before any bounded startup
    /// options are added, so caller-supplied `options`, host-address
    /// overrides, multi-host targets, and non-loopback hosts refuse before a
    /// socket opens.
    ///
    /// # Errors
    /// Returns [`SemanticArchiveReaderErrorV1`] for a malformed DSN or an
    /// out-of-contract connection target.
    pub fn from_dsn(raw: &str) -> Result<Self, SemanticArchiveReaderErrorV1> {
        let config = Config::from_str(raw).map_err(|_| SemanticArchiveReaderErrorV1::InvalidDsn)?;
        Self::new(&config)
    }

    /// Admit the reader DSN from [`READER_DSN_ENV_V1`].
    ///
    /// # Errors
    /// Returns [`SemanticArchiveReaderErrorV1`] for a missing or non-UTF-8
    /// environment value, a malformed DSN, or an out-of-contract target.
    pub fn from_env() -> Result<Self, SemanticArchiveReaderErrorV1> {
        let raw = std::env::var_os(READER_DSN_ENV_V1)
            .ok_or(SemanticArchiveReaderErrorV1::MissingEnv(READER_DSN_ENV_V1))?;
        let dsn = raw
            .into_string()
            .map_err(|_| SemanticArchiveReaderErrorV1::EnvNotUtf8(READER_DSN_ENV_V1))?;
        Self::from_dsn(&dsn)
    }

    /// Validate one explicit local-only connection target and bind the reader.
    ///
    /// # Errors
    /// Returns [`SemanticArchiveReaderErrorV1::ConnectionTarget`] for
    /// caller-supplied startup options, host-address overrides, multi-host or
    /// multi-port targets, a missing host, or a non-loopback TCP target.
    pub fn new(config: &Config) -> Result<Self, SemanticArchiveReaderErrorV1> {
        validate_legacy_connection_target(config)
            .map_err(|error| connection_target_error(&error))?;
        Ok(Self {
            config: config.clone(),
        })
    }

    /// Search only SQL-known materialized pages.
    ///
    /// This reuses the exact store search boundary
    /// ([`ARCHIVE_SEARCH_SQL_V1`](crate::ARCHIVE_SEARCH_SQL_V1)); against a
    /// bare `babylon_reader` credential the `PostgreSQL` privilege layer
    /// refuses the base page/grant tables until the Slice 2 fog-safe search
    /// views land, which is the intended fog behavior.
    ///
    /// # Errors
    /// Refuses a limit above 100, malformed stored rows, or database failure.
    pub fn search_known(
        &self,
        campaign_id: CampaignId,
        query: &str,
        limit: u32,
    ) -> Result<Vec<ArchiveSearchHitV1>, SemanticArchiveErrorV1> {
        if query.trim().is_empty() {
            return Ok(Vec::new());
        }
        if limit == 0 || limit > MAX_SEARCH_HITS {
            return Err(SemanticArchiveErrorV1::CollectionBound);
        }
        validate_text(query)?;
        let limit = i64::from(limit);
        let mut client = self.connect("connect known Archive reader search")?;
        client
            .query(
                ARCHIVE_SEARCH_SQL_V1,
                &[campaign_id.as_uuid(), &query, &limit],
            )
            .map_err(|error| database("search known Archive reader pages", &error))?
            .iter()
            .map(decode_search_hit)
            .collect()
    }

    /// Read the acknowledged-commit tick status through the fog-safe view.
    ///
    /// The view projects `babylon_state.tick_commit`, which stays revoked
    /// from the reader role; `tick_commit`, not `MAX(tick)`, marks durability.
    ///
    /// # Errors
    /// Refuses a malformed stored row or a database failure.
    pub fn committed_tick_status(
        &self,
        campaign_id: CampaignId,
    ) -> Result<Option<CommittedTickStatusV1>, SemanticArchiveErrorV1> {
        let mut client = self.connect("connect committed tick status reader")?;
        client
            .query_opt(COMMITTED_TICK_STATUS_SQL_V1, &[campaign_id.as_uuid()])
            .map_err(|error| database("read committed tick status view", &error))?
            .map(|row| decode_committed_tick_status(campaign_id, &row))
            .transpose()
    }

    fn connect(&self, operation: &'static str) -> Result<postgres::Client, SemanticArchiveErrorV1> {
        // The stored config stays raw: validation must observe the caller's
        // exact target, not the bounded startup options added here.
        let mut bounded = self.config.clone();
        bounded
            .connect_timeout(LEGACY_ADOPTER_CONNECT_TIMEOUT)
            .tcp_user_timeout(LEGACY_ADOPTER_TCP_USER_TIMEOUT)
            .options(LEGACY_ADOPTER_STARTUP_OPTIONS);
        bounded
            .connect(NoTls)
            .map_err(|error| database(operation, &error))
    }
}

/// Install the additive reader role and fog-safe tick-status view idempotently.
///
/// The installer mirrors the additive Archive pattern: one advisory lock, one
/// role-DDL statement outside the transaction (`CREATE ROLE` is not
/// transactional), and one transaction for the view, its exact grant, and the
/// guarded archive-table revokes. The base `babylon_state` tables are never
/// granted. This maintenance entry point does not advance the schema epoch.
///
/// # Errors
/// Refuses an out-of-contract target, an existing role with wrong attributes,
/// a view without the exact grant, or database failure.
pub fn install_reader_role_v1(
    config: &Config,
) -> Result<ReaderRoleDispositionV1, SemanticArchiveReaderErrorV1> {
    validate_legacy_connection_target(config).map_err(|error| connection_target_error(&error))?;
    let mut client = config
        .connect(NoTls)
        .map_err(|error| database_error("connect reader role installer", &error))?;
    client
        .query_one(
            "SELECT pg_catalog.pg_advisory_lock($1)",
            &[&SCHEMA_ADVISORY_LOCK_KEY],
        )
        .map_err(|error| database_error("lock reader role installer", &error))?;
    let result = install_reader_role_locked(&mut client);
    let unlock = client
        .query_one(
            "SELECT pg_catalog.pg_advisory_unlock($1)",
            &[&SCHEMA_ADVISORY_LOCK_KEY],
        )
        .and_then(|row| row.try_get::<_, bool>(0))
        .map_err(|error| database_error("unlock reader role installer", &error));
    match (result, unlock) {
        (Err(error), _) | (Ok(_), Err(error)) => Err(error),
        (Ok(disposition), Ok(true)) => Ok(disposition),
        (Ok(_), Ok(false)) => Err(SemanticArchiveReaderErrorV1::LockMismatch),
    }
}

fn install_reader_role_locked(
    client: &mut postgres::Client,
) -> Result<ReaderRoleDispositionV1, SemanticArchiveReaderErrorV1> {
    let row = client
        .query_one(READER_ROLE_MARKERS_SQL_V1, &[])
        .map_err(|error| database_error("inspect reader role markers", &error))?;
    let role_exists: bool = row
        .try_get(0)
        .map_err(|error| database_error("decode reader role marker", &error))?;
    let view_exists: bool = row
        .try_get(1)
        .map_err(|error| database_error("decode reader view marker", &error))?;
    let mut installed = false;
    if role_exists {
        verify_reader_role_attributes(client)?;
    } else {
        client
            .batch_execute(READER_ROLE_CREATE_SQL_V1)
            .map_err(|error| database_error("create reader role", &error))?;
        installed = true;
    }
    if view_exists {
        verify_reader_view_grant(client)?;
    } else {
        let mut transaction = client
            .build_transaction()
            .isolation_level(postgres::IsolationLevel::Serializable)
            .start()
            .map_err(|error| database_error("begin reader schema install", &error))?;
        transaction
            .batch_execute(
                "SET LOCAL search_path TO pg_catalog; SET LOCAL synchronous_commit TO on",
            )
            .map_err(|error| database_error("set reader schema install settings", &error))?;
        transaction
            .batch_execute(READER_ROLE_SCHEMA_V1_SQL)
            .map_err(|error| database_error("install reader schema", &error))?;
        transaction
            .commit()
            .map_err(|error| database_error("commit reader schema install", &error))?;
        installed = true;
    }
    if installed {
        Ok(ReaderRoleDispositionV1::Installed)
    } else {
        Ok(ReaderRoleDispositionV1::AlreadyCurrent)
    }
}

fn verify_reader_role_attributes(
    client: &mut postgres::Client,
) -> Result<(), SemanticArchiveReaderErrorV1> {
    let row = client
        .query_one(READER_ROLE_ATTRIBUTES_SQL_V1, &[])
        .map_err(|error| database_error("inspect reader role attributes", &error))?;
    let locked = [
        row.try_get::<_, bool>(0)
            .map_err(|error| database_error("decode reader role superuser attribute", &error))?,
        row.try_get::<_, bool>(1)
            .map_err(|error| database_error("decode reader role createdb attribute", &error))?,
        row.try_get::<_, bool>(2)
            .map_err(|error| database_error("decode reader role createrole attribute", &error))?,
        row.try_get::<_, bool>(3)
            .map_err(|error| database_error("decode reader role login attribute", &error))?,
    ];
    if locked == [false; 4] {
        Ok(())
    } else {
        Err(SemanticArchiveReaderErrorV1::RoleMismatch)
    }
}

fn verify_reader_view_grant(
    client: &mut postgres::Client,
) -> Result<(), SemanticArchiveReaderErrorV1> {
    let granted: bool = client
        .query_one(READER_VIEW_GRANT_SQL_V1, &[])
        .map_err(|error| database_error("inspect reader view grant", &error))?
        .try_get(0)
        .map_err(|error| database_error("decode reader view grant", &error))?;
    if granted {
        Ok(())
    } else {
        Err(SemanticArchiveReaderErrorV1::ViewMismatch)
    }
}

fn decode_committed_tick_status(
    campaign_id: CampaignId,
    row: &postgres::Row,
) -> Result<CommittedTickStatusV1, SemanticArchiveErrorV1> {
    let stored_campaign: uuid::Uuid = decode(row, 0)?;
    if stored_campaign != *campaign_id.as_uuid() {
        return Err(SemanticArchiveErrorV1::StoredPageMismatch);
    }
    let resolve_tick = u64::try_from(decode::<i64>(row, 1)?)
        .ok()
        .filter(|tick| *tick > 0)
        .ok_or(SemanticArchiveErrorV1::StoredPageMismatch)?;
    let envelope_layout_version: i16 = decode(row, 2)?;
    Ok(CommittedTickStatusV1 {
        campaign_id,
        resolve_tick,
        envelope_layout_version,
        tick_content_hash: decode_digest(row, 3)?,
        envelope_digest: decode_digest(row, 4)?,
    })
}
