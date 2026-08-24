//! Transactional installation of one exact representative H3 reference cohort.

use postgres::{Client, Config, GenericClient, IsolationLevel, NoTls, Row, Transaction};

use crate::h3_reference_cohort::MAX_H3_REFERENCE_CLOSURE_ROWS;
use crate::legacy_adopter::{
    acquire_lock, release_lock, validate_legacy_connection_target, LegacyAdopterError,
};
use crate::schema_epoch::{
    bounded_config, inspect_schema_epoch_under_lock, SchemaEpochError, SchemaEpochOrigin,
};
use crate::{
    build_representative_h3_cohort_v1, H3CellId, H3CellIdError, H3ReferenceCellRow,
    H3ReferenceCohort, H3ReferenceCohortError, H3ReferenceCohortReceipt, H3ReferenceOrigin,
    RefDigest,
};

const H3_REFERENCE_INSTALL_SCHEMA_EPOCH: usize = 3;
const H3_REFERENCE_COHORT_FORMAT_VERSION: i16 = 1;
const H3_REFERENCE_ARTIFACT_NAME: &str = "bridge_county_h3.parquet";
const H3_REFERENCE_ARTIFACT_MANIFEST_VERSION: &str = "2.0.0";
const H3_REFERENCE_SESSION_SETTINGS_SQL: &str = "SET statement_timeout TO '30000ms'";
const H3_REFERENCE_SESSION_SETTINGS_QUERY: &str = "SELECT \
    pg_catalog.current_setting('transaction_read_only'), \
    pg_catalog.current_setting('search_path'), \
    pg_catalog.current_setting('statement_timeout'), \
    pg_catalog.current_setting('lock_timeout'), \
    pg_catalog.current_setting('idle_in_transaction_session_timeout'), \
    pg_catalog.current_setting('quote_all_identifiers'), \
    pg_catalog.current_setting('jit'), \
    pg_catalog.current_setting('event_triggers')";
const H3_REFERENCE_INSTALL_BATCH_ROWS: usize = 1_024;
const MAX_H3_REFERENCE_INSTALL_BATCHES: usize =
    MAX_H3_REFERENCE_CLOSURE_ROWS.div_ceil(H3_REFERENCE_INSTALL_BATCH_ROWS);
const MAX_H3_REFERENCE_CARDINALITY_QUERY_ROWS: usize = MAX_H3_REFERENCE_CLOSURE_ROWS + 1;
const MAX_H3_REFERENCE_HEADER_ROWS: usize = 2;
const H3_REFERENCE_HEADER_QUERY_LIMIT: i64 = 3;
const MAX_H3_REFERENCE_INSTALL_COMMIT_ATTEMPTS: usize = 2;

const READ_HEADER_SQL: &str = "SELECT ref_digest, format_version, artifact_name, \
    artifact_manifest_version, artifact_digest, source_digest, source_r5_digest, \
    source_r7_digest, closure_digest, membership_digest, direct_cell_count, \
    derived_ancestor_count, closure_cell_count \
    FROM babylon_ref.h3_reference_cohort \
    WHERE ref_digest = $1 OR (format_version = $2 AND artifact_digest = $3) \
    ORDER BY ref_digest LIMIT $4";
const READ_MEMBERSHIP_SQL: &str = "WITH bounded_membership AS MATERIALIZED ( \
    SELECT membership.cell_id, membership.origin \
    FROM babylon_ref.h3_reference_membership AS membership \
    WHERE membership.ref_digest = $1 \
    ORDER BY membership.cell_id LIMIT $2 \
) SELECT cell.cell_id, cell.resolution, \
    cell.immediate_parent, cell.ancestor_r4, cell.ancestor_r5, cell.ancestor_r6, \
    cell.ancestor_r7, membership.origin \
    FROM bounded_membership AS membership \
    JOIN babylon_ref.h3_cell AS cell ON cell.cell_id = membership.cell_id \
    ORDER BY membership.cell_id LIMIT $2";
const READ_MEMBERSHIP_CARDINALITY_SQL: &str = "SELECT pg_catalog.count(*) \
    FROM (SELECT 1 \
    FROM babylon_ref.h3_reference_membership AS membership \
    WHERE membership.ref_digest = $1 \
    LIMIT $2) AS bounded_membership";
const INSERT_CELLS_SQL: &str = "INSERT INTO babylon_ref.h3_cell \
    (cell_id, resolution, immediate_parent, ancestor_r4, ancestor_r5, ancestor_r6, ancestor_r7) \
    SELECT input.cell_id, input.resolution, input.immediate_parent, input.ancestor_r4, \
           input.ancestor_r5, input.ancestor_r6, input.ancestor_r7 \
    FROM ROWS FROM (pg_catalog.unnest($1::bigint[]), pg_catalog.unnest($2::smallint[]), \
                    pg_catalog.unnest($3::bigint[]), pg_catalog.unnest($4::bigint[]), \
                    pg_catalog.unnest($5::bigint[]), pg_catalog.unnest($6::bigint[]), \
                    pg_catalog.unnest($7::bigint[])) \
      AS input(cell_id, resolution, immediate_parent, ancestor_r4, ancestor_r5, \
               ancestor_r6, ancestor_r7) ON CONFLICT DO NOTHING";
const INSERT_HEADER_SQL: &str = "INSERT INTO babylon_ref.h3_reference_cohort \
    (ref_digest, format_version, artifact_name, artifact_manifest_version, artifact_digest, \
     source_digest, source_r5_digest, source_r7_digest, closure_digest, membership_digest, \
     direct_cell_count, derived_ancestor_count, closure_cell_count) \
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13) \
    ON CONFLICT DO NOTHING";
const INSERT_MEMBERSHIP_SQL: &str = "INSERT INTO babylon_ref.h3_reference_membership \
    (ref_digest, cell_id, origin) \
    SELECT $1, input.cell_id, input.origin \
    FROM ROWS FROM (pg_catalog.unnest($2::bigint[]), pg_catalog.unnest($3::smallint[])) \
      AS input(cell_id, origin) \
    ON CONFLICT DO NOTHING";
const WRITE_LOCAL_SETTINGS_SQL: &str = "SET LOCAL search_path TO pg_catalog; \
    SET LOCAL synchronous_commit TO on";
const WRITE_SETTINGS_SQL: &str = "SELECT \
    pg_catalog.current_setting('transaction_isolation'), \
    pg_catalog.current_setting('transaction_read_only'), \
    pg_catalog.current_setting('search_path'), \
    pg_catalog.current_setting('synchronous_commit'), \
    pg_catalog.current_setting('statement_timeout'), \
    pg_catalog.current_setting('lock_timeout'), \
    pg_catalog.current_setting('idle_in_transaction_session_timeout'), \
    pg_catalog.current_setting('quote_all_identifiers'), \
    pg_catalog.current_setting('jit'), \
    pg_catalog.current_setting('event_triggers')";

/// Successful installation disposition at the durable `PostgreSQL` boundary.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum H3ReferenceInstallDisposition {
    /// This call committed the exact cohort.
    Installed,
    /// The exact cohort already existed and required no write transaction.
    AlreadyPresent,
    /// A transport-ambiguous commit was proven durable after reconnecting.
    ReconciledAfterAmbiguousCommit,
}

/// Closed database operations used in installer failures.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum H3ReferenceInstallOperation {
    /// Open one fresh bounded local connection.
    Connect,
    /// Read the bounded cohort header identity.
    ReadHeader,
    /// Read the bounded membership cardinality sentinel.
    ReadMembershipCardinality,
    /// Read and verify the bounded primary-key-ordered membership rows.
    ReadMembershipRows,
    /// Begin the serializable write transaction.
    BeginTransaction,
    /// Apply exact local transaction settings.
    SetTransactionSettings,
    /// Verify exact local transaction settings.
    VerifyTransactionSettings,
    /// Apply the installer-only statement bound after epoch inspection.
    SetSessionSettings,
    /// Verify the narrowed installer session profile.
    VerifySessionSettings,
    /// Insert canonical H3 cell rows.
    InsertCells,
    /// Insert the exact cohort header.
    InsertHeader,
    /// Insert direct and derived membership rows.
    InsertMembership,
    /// Commit the verified transaction.
    CommitTransaction,
    /// Roll back a failed transaction explicitly.
    RollbackTransaction,
}

/// Fixed installer resources with explicit row ceilings.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum H3ReferenceInstallBoundedResource {
    /// Header candidates selected by identity.
    HeaderRows,
    /// Canonical membership rows read back from `PostgreSQL`.
    MembershipRows,
    /// Batched canonical row insertions.
    InsertBatches,
}

/// Exact equivalence surface which failed after an idempotent insert attempt.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum H3ReferenceInstallConflict {
    /// The pinned artifact identity already names another cohort digest.
    ArtifactIdentity,
    /// The expected cohort digest has different provenance or counts.
    CohortHeader,
    /// Stored membership or canonical H3 fields differ from the supplied cohort.
    Membership,
    /// Direct stored membership does not rebuild the supplied immutable cohort.
    RebuiltCohort,
}

/// Closed installer refusal and failure states.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum H3ReferenceInstallError {
    /// The supplied maintenance target violated the local-only connection contract.
    ConnectionTarget(LegacyAdopterError),
    /// The exact schema advisory lock could not be acquired.
    Lock(LegacyAdopterError),
    /// The existing schema epoch or owner contract failed inspection.
    SchemaEpoch(SchemaEpochError),
    /// Installation requires one exact fully migrated Rust epoch.
    ExactSchemaEpochRequired {
        expected: usize,
        actual: usize,
        origin: SchemaEpochOrigin,
    },
    /// A database operation failed without retaining driver text.
    Database {
        operation: H3ReferenceInstallOperation,
    },
    /// A database value could not be decoded into the governed type.
    Decode {
        operation: H3ReferenceInstallOperation,
    },
    /// `PostgreSQL` returned a malformed H3 identity despite the schema contract.
    CellIdentity {
        operation: H3ReferenceInstallOperation,
        source: H3CellIdError,
    },
    /// A fixed row bound was exceeded.
    Bounds {
        resource: H3ReferenceInstallBoundedResource,
        actual: usize,
        max: usize,
    },
    /// Existing durable rows differ from the exact supplied cohort.
    Conflict {
        component: H3ReferenceInstallConflict,
    },
    /// Direct stored rows could not rebuild through the governed cohort constructor.
    Rebuild(H3ReferenceCohortError),
    /// Two transport-ambiguous attempts remained absent after exact reconciliation.
    AmbiguousCommitUnresolved { attempts: usize },
    /// Commit ambiguity remained visible when reconciliation itself refused.
    AmbiguousCommitAndReconciliation {
        attempts: usize,
        reconciliation: Box<H3ReferenceInstallError>,
    },
    /// Explicit schema-lock release failed.
    Unlock(LegacyAdopterError),
    /// A primary failure and explicit unlock failure both occurred.
    FailureAndCleanup {
        primary: Box<H3ReferenceInstallError>,
        cleanup: Box<H3ReferenceInstallError>,
    },
    /// A transaction failure and explicit rollback failure both occurred.
    FailureAndRollback {
        primary: Box<H3ReferenceInstallError>,
        rollback: Box<H3ReferenceInstallError>,
    },
}

impl std::fmt::Display for H3ReferenceInstallError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "H3 reference installation refused: {self:?}")
    }
}

impl std::error::Error for H3ReferenceInstallError {}

/// Exact installation receipt for the durable representative cohort.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct H3ReferenceInstallReport {
    disposition: H3ReferenceInstallDisposition,
    receipt: H3ReferenceCohortReceipt,
    closure_cell_count: usize,
    commit_attempts: usize,
}

impl H3ReferenceInstallReport {
    /// Durable installation outcome.
    #[must_use]
    pub fn disposition(&self) -> H3ReferenceInstallDisposition {
        self.disposition
    }

    /// Identity of the exact installed reference cohort.
    #[must_use]
    pub fn ref_digest(&self) -> RefDigest {
        self.receipt.ref_digest()
    }

    /// SHA-256 identity of the pinned source artifact bytes.
    #[must_use]
    pub fn artifact_digest(&self) -> RefDigest {
        self.receipt.artifact_digest()
    }

    /// Governed cohort framing version.
    #[must_use]
    pub fn format_version(&self) -> i16 {
        H3_REFERENCE_COHORT_FORMAT_VERSION
    }

    /// Pinned source artifact filename.
    #[must_use]
    pub fn artifact_name(&self) -> &str {
        H3_REFERENCE_ARTIFACT_NAME
    }

    /// Pinned artifact manifest version.
    #[must_use]
    pub fn artifact_manifest_version(&self) -> &str {
        H3_REFERENCE_ARTIFACT_MANIFEST_VERSION
    }

    /// Direct source identities committed to membership.
    #[must_use]
    pub fn direct_cell_count(&self) -> usize {
        self.receipt.direct_cell_count()
    }

    /// Strict parents added to close the H3 hierarchy.
    #[must_use]
    pub fn derived_ancestor_count(&self) -> usize {
        self.receipt.derived_ancestor_count()
    }

    /// Total canonical membership rows committed for this cohort.
    #[must_use]
    pub fn closure_cell_count(&self) -> usize {
        self.closure_cell_count
    }

    /// Number of write-commit attempts made by this invocation.
    #[must_use]
    pub fn commit_attempts(&self) -> usize {
        self.commit_attempts
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum InstallPresence {
    Absent,
    Exact,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CommitAttempt {
    Committed,
    Ambiguous,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct InstallResolution {
    disposition: H3ReferenceInstallDisposition,
    commit_attempts: usize,
}

trait InstallDriver {
    fn attempt_commit(&mut self) -> Result<CommitAttempt, H3ReferenceInstallError>;
    fn reconcile(&mut self) -> Result<InstallPresence, H3ReferenceInstallError>;
}

/// Install one already-validated representative H3 cohort into exact schema epoch 3.
///
/// This immutable reference-data maintenance entry point does not request runtime writer
/// authority and never advances the schema epoch for the caller.
///
/// # Errors
/// Returns [`H3ReferenceInstallError`] before publication for any target, lock, owner, epoch,
/// transaction, equivalence, reconciliation, or cleanup failure.
pub fn install_representative_h3_cohort(
    config: &Config,
    cohort: &H3ReferenceCohort,
) -> Result<H3ReferenceInstallReport, H3ReferenceInstallError> {
    let mut attempt = attempt_install_transaction;
    install_representative_h3_cohort_using(config, cohort, &mut attempt)
}

fn install_representative_h3_cohort_using<Attempt>(
    config: &Config,
    cohort: &H3ReferenceCohort,
    attempt: &mut Attempt,
) -> Result<H3ReferenceInstallReport, H3ReferenceInstallError>
where
    Attempt:
        FnMut(&mut Client, &H3ReferenceCohort) -> Result<CommitAttempt, H3ReferenceInstallError>,
{
    validate_legacy_connection_target(config).map_err(H3ReferenceInstallError::ConnectionTarget)?;
    let bounded = installer_config(config);
    let mut session = LockedInstallSession::connect(&bounded)?;
    let primary = install_under_lock(&bounded, &mut session, cohort, attempt);
    session.finish(primary)
}

fn installer_config(config: &Config) -> Config {
    bounded_config(config)
}

fn install_under_lock<Attempt>(
    config: &Config,
    session: &mut LockedInstallSession,
    cohort: &H3ReferenceCohort,
    attempt: &mut Attempt,
) -> Result<H3ReferenceInstallReport, H3ReferenceInstallError>
where
    Attempt:
        FnMut(&mut Client, &H3ReferenceCohort) -> Result<CommitAttempt, H3ReferenceInstallError>,
{
    require_exact_schema_epoch(session.client())?;
    prepare_installer_session(session.client())?;
    let initial = inspect_presence(session.client(), cohort)?;
    let resolution = {
        let mut driver = DatabaseInstallDriver {
            config,
            session,
            cohort,
            attempt,
        };
        drive_install(initial, &mut driver)?
    };
    build_report(cohort, resolution)
}

fn drive_install<Driver: InstallDriver>(
    initial: InstallPresence,
    driver: &mut Driver,
) -> Result<InstallResolution, H3ReferenceInstallError> {
    if initial == InstallPresence::Exact {
        return Ok(InstallResolution {
            disposition: H3ReferenceInstallDisposition::AlreadyPresent,
            commit_attempts: 0,
        });
    }
    for attempt_index in 0..MAX_H3_REFERENCE_INSTALL_COMMIT_ATTEMPTS {
        let commit_attempts = attempt_index + 1;
        match driver.attempt_commit()? {
            CommitAttempt::Committed => {
                return Ok(InstallResolution {
                    disposition: H3ReferenceInstallDisposition::Installed,
                    commit_attempts,
                });
            }
            CommitAttempt::Ambiguous => {
                let reconciled = driver.reconcile().map_err(|reconciliation| {
                    H3ReferenceInstallError::AmbiguousCommitAndReconciliation {
                        attempts: commit_attempts,
                        reconciliation: Box::new(reconciliation),
                    }
                })?;
                if reconciled == InstallPresence::Exact {
                    return Ok(InstallResolution {
                        disposition: H3ReferenceInstallDisposition::ReconciledAfterAmbiguousCommit,
                        commit_attempts,
                    });
                }
            }
        }
    }
    Err(H3ReferenceInstallError::AmbiguousCommitUnresolved {
        attempts: MAX_H3_REFERENCE_INSTALL_COMMIT_ATTEMPTS,
    })
}

fn build_report(
    cohort: &H3ReferenceCohort,
    resolution: InstallResolution,
) -> Result<H3ReferenceInstallReport, H3ReferenceInstallError> {
    let receipt = cohort.receipt().clone();
    let closure_cell_count = receipt
        .direct_cell_count()
        .checked_add(receipt.derived_ancestor_count())
        .ok_or(H3ReferenceInstallError::Bounds {
            resource: H3ReferenceInstallBoundedResource::MembershipRows,
            actual: usize::MAX,
            max: MAX_H3_REFERENCE_CLOSURE_ROWS,
        })?;
    Ok(H3ReferenceInstallReport {
        disposition: resolution.disposition,
        receipt,
        closure_cell_count,
        commit_attempts: resolution.commit_attempts,
    })
}

struct LockedInstallSession {
    client: Option<Client>,
}

impl LockedInstallSession {
    fn connect(config: &Config) -> Result<Self, H3ReferenceInstallError> {
        let mut client = config
            .connect(NoTls)
            .map_err(|_| database_error(H3ReferenceInstallOperation::Connect))?;
        acquire_lock(&mut client).map_err(H3ReferenceInstallError::Lock)?;
        Ok(Self {
            client: Some(client),
        })
    }

    fn client(&mut self) -> &mut Client {
        self.client
            .as_mut()
            .expect("locked installer session always contains one client")
    }

    fn reconnect(&mut self, config: &Config) -> Result<(), H3ReferenceInstallError> {
        self.client.take();
        *self = Self::connect(config)?;
        Ok(())
    }

    fn finish<T>(
        mut self,
        primary: Result<T, H3ReferenceInstallError>,
    ) -> Result<T, H3ReferenceInstallError> {
        let cleanup = self.client.as_mut().map_or(Ok(()), |client| {
            release_lock(client).map_err(H3ReferenceInstallError::Unlock)
        });
        match (primary, cleanup) {
            (Ok(value), Ok(())) => Ok(value),
            (Err(error), Ok(())) => Err(error),
            (Ok(_), Err(cleanup)) => Err(cleanup),
            (Err(primary), Err(cleanup)) => Err(H3ReferenceInstallError::FailureAndCleanup {
                primary: Box::new(primary),
                cleanup: Box::new(cleanup),
            }),
        }
    }
}

struct DatabaseInstallDriver<'a, Attempt> {
    config: &'a Config,
    session: &'a mut LockedInstallSession,
    cohort: &'a H3ReferenceCohort,
    attempt: &'a mut Attempt,
}

impl<Attempt> InstallDriver for DatabaseInstallDriver<'_, Attempt>
where
    Attempt:
        FnMut(&mut Client, &H3ReferenceCohort) -> Result<CommitAttempt, H3ReferenceInstallError>,
{
    fn attempt_commit(&mut self) -> Result<CommitAttempt, H3ReferenceInstallError> {
        (self.attempt)(self.session.client(), self.cohort)
    }

    fn reconcile(&mut self) -> Result<InstallPresence, H3ReferenceInstallError> {
        self.session.reconnect(self.config)?;
        require_exact_schema_epoch(self.session.client())?;
        prepare_installer_session(self.session.client())?;
        inspect_presence(self.session.client(), self.cohort)
    }
}

fn require_exact_schema_epoch(client: &mut Client) -> Result<(), H3ReferenceInstallError> {
    let (origin, actual) =
        inspect_schema_epoch_under_lock(client).map_err(H3ReferenceInstallError::SchemaEpoch)?;
    if origin == SchemaEpochOrigin::ExistingRustPrefix
        && actual == H3_REFERENCE_INSTALL_SCHEMA_EPOCH
    {
        Ok(())
    } else {
        Err(H3ReferenceInstallError::ExactSchemaEpochRequired {
            expected: H3_REFERENCE_INSTALL_SCHEMA_EPOCH,
            actual,
            origin,
        })
    }
}

fn prepare_installer_session(client: &mut Client) -> Result<(), H3ReferenceInstallError> {
    client
        .batch_execute(H3_REFERENCE_SESSION_SETTINGS_SQL)
        .map_err(|_| database_error(H3ReferenceInstallOperation::SetSessionSettings))?;
    let operation = H3ReferenceInstallOperation::VerifySessionSettings;
    let row = client
        .query_one(H3_REFERENCE_SESSION_SETTINGS_QUERY, &[])
        .map_err(|_| database_error(operation))?;
    let expected = ["on", "pg_catalog", "30s", "5s", "5s", "off", "off", "off"];
    for (index, wanted) in expected.iter().enumerate().take(8) {
        let actual: String = decode_value(&row, index, operation)?;
        if actual != *wanted {
            return Err(database_error(operation));
        }
    }
    Ok(())
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct CohortHeader {
    ref_digest: RefDigest,
    format_version: i16,
    artifact_name: String,
    artifact_manifest_version: String,
    artifact_digest: RefDigest,
    source_digest: RefDigest,
    source_r5_digest: RefDigest,
    source_r7_digest: RefDigest,
    closure_digest: RefDigest,
    membership_digest: RefDigest,
    direct_cell_count: usize,
    derived_ancestor_count: usize,
    closure_cell_count: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct StoredReferenceRow {
    cell_id: H3CellId,
    resolution: u8,
    immediate_parent: Option<H3CellId>,
    ancestor_r4: Option<H3CellId>,
    ancestor_r5: Option<H3CellId>,
    ancestor_r6: Option<H3CellId>,
    ancestor_r7: Option<H3CellId>,
    origin: H3ReferenceOrigin,
}

fn inspect_presence<ClientType: GenericClient>(
    client: &mut ClientType,
    cohort: &H3ReferenceCohort,
) -> Result<InstallPresence, H3ReferenceInstallError> {
    let receipt = cohort.receipt();
    let ref_digest = receipt.ref_digest();
    let artifact_digest = receipt.artifact_digest();
    let rows = client
        .query(
            READ_HEADER_SQL,
            &[
                &ref_digest.as_bytes().as_slice(),
                &H3_REFERENCE_COHORT_FORMAT_VERSION,
                &artifact_digest.as_bytes().as_slice(),
                &H3_REFERENCE_HEADER_QUERY_LIMIT,
            ],
        )
        .map_err(|_| database_error(H3ReferenceInstallOperation::ReadHeader))?;
    if rows.len() > MAX_H3_REFERENCE_HEADER_ROWS {
        return Err(H3ReferenceInstallError::Bounds {
            resource: H3ReferenceInstallBoundedResource::HeaderRows,
            actual: rows.len(),
            max: MAX_H3_REFERENCE_HEADER_ROWS,
        });
    }
    let Some(row) = rows.first() else {
        return Ok(InstallPresence::Absent);
    };
    if rows.len() != 1 {
        return Err(conflict(H3ReferenceInstallConflict::ArtifactIdentity));
    }
    let header = decode_header(row)?;
    validate_header(&header, receipt)?;
    verify_membership(client, cohort)?;
    Ok(InstallPresence::Exact)
}

fn decode_header(row: &Row) -> Result<CohortHeader, H3ReferenceInstallError> {
    let operation = H3ReferenceInstallOperation::ReadHeader;
    Ok(CohortHeader {
        ref_digest: decode_digest(row, 0, operation)?,
        format_version: decode_value(row, 1, operation)?,
        artifact_name: decode_value(row, 2, operation)?,
        artifact_manifest_version: decode_value(row, 3, operation)?,
        artifact_digest: decode_digest(row, 4, operation)?,
        source_digest: decode_digest(row, 5, operation)?,
        source_r5_digest: decode_digest(row, 6, operation)?,
        source_r7_digest: decode_digest(row, 7, operation)?,
        closure_digest: decode_digest(row, 8, operation)?,
        membership_digest: decode_digest(row, 9, operation)?,
        direct_cell_count: decode_count(row, 10, operation)?,
        derived_ancestor_count: decode_count(row, 11, operation)?,
        closure_cell_count: decode_count(row, 12, operation)?,
    })
}

fn expected_header(
    receipt: &H3ReferenceCohortReceipt,
) -> Result<CohortHeader, H3ReferenceInstallError> {
    let closure_cell_count = receipt
        .direct_cell_count()
        .checked_add(receipt.derived_ancestor_count())
        .ok_or(H3ReferenceInstallError::Bounds {
            resource: H3ReferenceInstallBoundedResource::MembershipRows,
            actual: usize::MAX,
            max: MAX_H3_REFERENCE_CLOSURE_ROWS,
        })?;
    Ok(CohortHeader {
        ref_digest: receipt.ref_digest(),
        format_version: H3_REFERENCE_COHORT_FORMAT_VERSION,
        artifact_name: H3_REFERENCE_ARTIFACT_NAME.to_owned(),
        artifact_manifest_version: H3_REFERENCE_ARTIFACT_MANIFEST_VERSION.to_owned(),
        artifact_digest: receipt.artifact_digest(),
        source_digest: receipt.source_digest(),
        source_r5_digest: receipt.source_r5_digest(),
        source_r7_digest: receipt.source_r7_digest(),
        closure_digest: receipt.closure_digest(),
        membership_digest: receipt.membership_digest(),
        direct_cell_count: receipt.direct_cell_count(),
        derived_ancestor_count: receipt.derived_ancestor_count(),
        closure_cell_count,
    })
}

fn validate_header(
    actual: &CohortHeader,
    receipt: &H3ReferenceCohortReceipt,
) -> Result<(), H3ReferenceInstallError> {
    if actual.ref_digest != receipt.ref_digest() {
        return Err(conflict(H3ReferenceInstallConflict::ArtifactIdentity));
    }
    if actual != &expected_header(receipt)? {
        return Err(conflict(H3ReferenceInstallConflict::CohortHeader));
    }
    Ok(())
}

fn verify_membership<ClientType: GenericClient>(
    client: &mut ClientType,
    cohort: &H3ReferenceCohort,
) -> Result<(), H3ReferenceInstallError> {
    verify_membership_cardinality(client, cohort)?;
    let rows = read_membership_rows(client, cohort)?;
    if rows.len() != cohort.rows().len() {
        return Err(conflict(H3ReferenceInstallConflict::Membership));
    }
    let mut expected_index = 0_usize;
    let mut direct_cells = Vec::with_capacity(cohort.receipt().direct_cell_count());
    for row in rows.iter().take(MAX_H3_REFERENCE_CLOSURE_ROWS) {
        let stored = decode_stored_row(row)?;
        let expected = cohort
            .rows()
            .get(expected_index)
            .ok_or_else(|| conflict(H3ReferenceInstallConflict::Membership))?;
        compare_stored_row(&stored, expected)?;
        if stored.origin == H3ReferenceOrigin::Direct {
            direct_cells.push(stored.cell_id);
        }
        expected_index = expected_index
            .checked_add(1)
            .ok_or(H3ReferenceInstallError::Bounds {
                resource: H3ReferenceInstallBoundedResource::MembershipRows,
                actual: usize::MAX,
                max: MAX_H3_REFERENCE_CLOSURE_ROWS,
            })?;
    }
    finish_membership_verification(expected_index, &direct_cells, cohort)
}

fn verify_membership_cardinality<ClientType: GenericClient>(
    client: &mut ClientType,
    cohort: &H3ReferenceCohort,
) -> Result<(), H3ReferenceInstallError> {
    let operation = H3ReferenceInstallOperation::ReadMembershipCardinality;
    let ref_digest = cohort.receipt().ref_digest();
    let expected = cohort.rows().len();
    let query_limit = expected
        .checked_add(1)
        .filter(|limit| *limit <= MAX_H3_REFERENCE_CARDINALITY_QUERY_ROWS)
        .ok_or(H3ReferenceInstallError::Bounds {
            resource: H3ReferenceInstallBoundedResource::MembershipRows,
            actual: expected,
            max: MAX_H3_REFERENCE_CLOSURE_ROWS,
        })?;
    let query_limit = i64::try_from(query_limit).map_err(|_| H3ReferenceInstallError::Bounds {
        resource: H3ReferenceInstallBoundedResource::MembershipRows,
        actual: expected,
        max: MAX_H3_REFERENCE_CLOSURE_ROWS,
    })?;
    let row = client
        .query_one(
            READ_MEMBERSHIP_CARDINALITY_SQL,
            &[&ref_digest.as_bytes().as_slice(), &query_limit],
        )
        .map_err(|_| database_error(operation))?;
    let actual: i64 = decode_value(&row, 0, operation)?;
    let actual =
        usize::try_from(actual).map_err(|_| H3ReferenceInstallError::Decode { operation })?;
    if actual < expected {
        return Err(conflict(H3ReferenceInstallConflict::Membership));
    }
    if actual > expected {
        return Err(H3ReferenceInstallError::Bounds {
            resource: H3ReferenceInstallBoundedResource::MembershipRows,
            actual,
            max: expected,
        });
    }
    Ok(())
}

fn read_membership_rows<ClientType: GenericClient>(
    client: &mut ClientType,
    cohort: &H3ReferenceCohort,
) -> Result<Vec<Row>, H3ReferenceInstallError> {
    let expected = cohort.rows().len();
    let query_limit = expected
        .checked_add(1)
        .filter(|limit| *limit <= MAX_H3_REFERENCE_CARDINALITY_QUERY_ROWS)
        .ok_or(H3ReferenceInstallError::Bounds {
            resource: H3ReferenceInstallBoundedResource::MembershipRows,
            actual: expected,
            max: MAX_H3_REFERENCE_CLOSURE_ROWS,
        })?;
    let query_limit = i64::try_from(query_limit).map_err(|_| H3ReferenceInstallError::Bounds {
        resource: H3ReferenceInstallBoundedResource::MembershipRows,
        actual: expected,
        max: MAX_H3_REFERENCE_CLOSURE_ROWS,
    })?;
    let ref_digest = cohort.receipt().ref_digest();
    let rows = client
        .query(
            READ_MEMBERSHIP_SQL,
            &[&ref_digest.as_bytes().as_slice(), &query_limit],
        )
        .map_err(|_| database_error(H3ReferenceInstallOperation::ReadMembershipRows))?;
    if rows.len() > expected {
        return Err(H3ReferenceInstallError::Bounds {
            resource: H3ReferenceInstallBoundedResource::MembershipRows,
            actual: rows.len(),
            max: expected,
        });
    }
    Ok(rows)
}

fn finish_membership_verification(
    expected_index: usize,
    direct_cells: &[H3CellId],
    cohort: &H3ReferenceCohort,
) -> Result<(), H3ReferenceInstallError> {
    if expected_index != cohort.rows().len()
        || direct_cells.len() != cohort.receipt().direct_cell_count()
    {
        return Err(conflict(H3ReferenceInstallConflict::Membership));
    }
    let rebuilt =
        build_representative_h3_cohort_v1(cohort.receipt().artifact_digest(), direct_cells)
            .map_err(H3ReferenceInstallError::Rebuild)?;
    if rebuilt != *cohort {
        return Err(conflict(H3ReferenceInstallConflict::RebuiltCohort));
    }
    Ok(())
}

fn decode_stored_row(row: &Row) -> Result<StoredReferenceRow, H3ReferenceInstallError> {
    let operation = H3ReferenceInstallOperation::ReadMembershipRows;
    let cell_id = decode_cell(row, 0, operation)?;
    let resolution: i16 = decode_value(row, 1, operation)?;
    let resolution =
        u8::try_from(resolution).map_err(|_| H3ReferenceInstallError::Decode { operation })?;
    Ok(StoredReferenceRow {
        cell_id,
        resolution,
        immediate_parent: decode_optional_cell(row, 2, operation)?,
        ancestor_r4: decode_optional_cell(row, 3, operation)?,
        ancestor_r5: decode_optional_cell(row, 4, operation)?,
        ancestor_r6: decode_optional_cell(row, 5, operation)?,
        ancestor_r7: decode_optional_cell(row, 6, operation)?,
        origin: decode_origin(row, 7, operation)?,
    })
}

fn compare_stored_row(
    actual: &StoredReferenceRow,
    expected: &H3ReferenceCellRow,
) -> Result<(), H3ReferenceInstallError> {
    let exact = actual.cell_id == expected.cell_id()
        && actual.resolution == expected.resolution()
        && actual.immediate_parent == expected.immediate_parent()
        && actual.ancestor_r4 == expected.ancestor_r4()
        && actual.ancestor_r5 == expected.ancestor_r5()
        && actual.ancestor_r6 == expected.ancestor_r6()
        && actual.ancestor_r7 == expected.ancestor_r7()
        && actual.origin == expected.origin();
    if exact {
        Ok(())
    } else {
        Err(conflict(H3ReferenceInstallConflict::Membership))
    }
}

fn attempt_install_transaction(
    client: &mut Client,
    cohort: &H3ReferenceCohort,
) -> Result<CommitAttempt, H3ReferenceInstallError> {
    let transaction = prepare_install_transaction(client, cohort)?;
    match transaction.commit() {
        Ok(()) => Ok(CommitAttempt::Committed),
        Err(error) if error.as_db_error().is_some() => Err(database_error(
            H3ReferenceInstallOperation::CommitTransaction,
        )),
        Err(_) => Ok(CommitAttempt::Ambiguous),
    }
}

fn prepare_install_transaction<'client>(
    client: &'client mut Client,
    cohort: &H3ReferenceCohort,
) -> Result<Transaction<'client>, H3ReferenceInstallError> {
    let mut transaction = client
        .build_transaction()
        .isolation_level(IsolationLevel::Serializable)
        .read_only(false)
        .start()
        .map_err(|_| database_error(H3ReferenceInstallOperation::BeginTransaction))?;
    let verification = install_and_verify(&mut transaction, cohort);
    if let Err(primary) = verification {
        return rollback_preserving(transaction, primary);
    }
    Ok(transaction)
}

fn install_and_verify(
    transaction: &mut Transaction<'_>,
    cohort: &H3ReferenceCohort,
) -> Result<(), H3ReferenceInstallError> {
    prepare_transaction(transaction)?;
    insert_cells(transaction, cohort.rows())?;
    insert_header(transaction, cohort.receipt())?;
    insert_membership(transaction, cohort)?;
    match inspect_presence(transaction, cohort)? {
        InstallPresence::Exact => Ok(()),
        InstallPresence::Absent => Err(conflict(H3ReferenceInstallConflict::CohortHeader)),
    }
}

fn prepare_transaction(transaction: &mut Transaction<'_>) -> Result<(), H3ReferenceInstallError> {
    transaction
        .batch_execute(WRITE_LOCAL_SETTINGS_SQL)
        .map_err(|_| database_error(H3ReferenceInstallOperation::SetTransactionSettings))?;
    let operation = H3ReferenceInstallOperation::VerifyTransactionSettings;
    let row = transaction
        .query_one(WRITE_SETTINGS_SQL, &[])
        .map_err(|_| database_error(operation))?;
    let expected = [
        "serializable",
        "off",
        "pg_catalog",
        "on",
        "30s",
        "5s",
        "5s",
        "off",
        "off",
        "off",
    ];
    for (index, wanted) in expected.iter().enumerate() {
        let actual: String = decode_value(&row, index, operation)?;
        if actual != *wanted {
            return Err(database_error(operation));
        }
    }
    Ok(())
}

fn insert_cells(
    transaction: &mut Transaction<'_>,
    rows: &[H3ReferenceCellRow],
) -> Result<(), H3ReferenceInstallError> {
    let batch_count = rows.len().div_ceil(H3_REFERENCE_INSTALL_BATCH_ROWS);
    if batch_count > MAX_H3_REFERENCE_INSTALL_BATCHES {
        return Err(H3ReferenceInstallError::Bounds {
            resource: H3ReferenceInstallBoundedResource::InsertBatches,
            actual: batch_count,
            max: MAX_H3_REFERENCE_INSTALL_BATCHES,
        });
    }
    for batch in rows
        .chunks(H3_REFERENCE_INSTALL_BATCH_ROWS)
        .take(MAX_H3_REFERENCE_INSTALL_BATCHES)
    {
        insert_cell_batch(transaction, batch)?;
    }
    Ok(())
}

fn insert_cell_batch(
    transaction: &mut Transaction<'_>,
    rows: &[H3ReferenceCellRow],
) -> Result<(), H3ReferenceInstallError> {
    let mut cell_ids = Vec::with_capacity(rows.len());
    let mut resolutions = Vec::with_capacity(rows.len());
    let mut immediate_parents = Vec::with_capacity(rows.len());
    let mut ancestors_r4 = Vec::with_capacity(rows.len());
    let mut ancestors_r5 = Vec::with_capacity(rows.len());
    let mut ancestors_r6 = Vec::with_capacity(rows.len());
    let mut ancestors_r7 = Vec::with_capacity(rows.len());
    for row in rows.iter().take(H3_REFERENCE_INSTALL_BATCH_ROWS) {
        cell_ids.push(cell_to_sql(
            row.cell_id(),
            H3ReferenceInstallOperation::InsertCells,
        )?);
        resolutions.push(i16::from(row.resolution()));
        immediate_parents.push(optional_cell_to_sql(
            row.immediate_parent(),
            H3ReferenceInstallOperation::InsertCells,
        )?);
        ancestors_r4.push(optional_cell_to_sql(
            row.ancestor_r4(),
            H3ReferenceInstallOperation::InsertCells,
        )?);
        ancestors_r5.push(optional_cell_to_sql(
            row.ancestor_r5(),
            H3ReferenceInstallOperation::InsertCells,
        )?);
        ancestors_r6.push(optional_cell_to_sql(
            row.ancestor_r6(),
            H3ReferenceInstallOperation::InsertCells,
        )?);
        ancestors_r7.push(optional_cell_to_sql(
            row.ancestor_r7(),
            H3ReferenceInstallOperation::InsertCells,
        )?);
    }
    transaction
        .execute(
            INSERT_CELLS_SQL,
            &[
                &cell_ids,
                &resolutions,
                &immediate_parents,
                &ancestors_r4,
                &ancestors_r5,
                &ancestors_r6,
                &ancestors_r7,
            ],
        )
        .map_err(|_| database_error(H3ReferenceInstallOperation::InsertCells))?;
    Ok(())
}

fn insert_header(
    transaction: &mut Transaction<'_>,
    receipt: &H3ReferenceCohortReceipt,
) -> Result<(), H3ReferenceInstallError> {
    let header = expected_header(receipt)?;
    let direct_count = count_to_sql(header.direct_cell_count)?;
    let derived_count = count_to_sql(header.derived_ancestor_count)?;
    let closure_count = count_to_sql(header.closure_cell_count)?;
    transaction
        .execute(
            INSERT_HEADER_SQL,
            &[
                &header.ref_digest.as_bytes().as_slice(),
                &header.format_version,
                &header.artifact_name,
                &header.artifact_manifest_version,
                &header.artifact_digest.as_bytes().as_slice(),
                &header.source_digest.as_bytes().as_slice(),
                &header.source_r5_digest.as_bytes().as_slice(),
                &header.source_r7_digest.as_bytes().as_slice(),
                &header.closure_digest.as_bytes().as_slice(),
                &header.membership_digest.as_bytes().as_slice(),
                &direct_count,
                &derived_count,
                &closure_count,
            ],
        )
        .map_err(|_| database_error(H3ReferenceInstallOperation::InsertHeader))?;
    Ok(())
}

fn insert_membership(
    transaction: &mut Transaction<'_>,
    cohort: &H3ReferenceCohort,
) -> Result<(), H3ReferenceInstallError> {
    let rows = cohort.rows();
    let batch_count = rows.len().div_ceil(H3_REFERENCE_INSTALL_BATCH_ROWS);
    if batch_count > MAX_H3_REFERENCE_INSTALL_BATCHES {
        return Err(H3ReferenceInstallError::Bounds {
            resource: H3ReferenceInstallBoundedResource::InsertBatches,
            actual: batch_count,
            max: MAX_H3_REFERENCE_INSTALL_BATCHES,
        });
    }
    for batch in rows
        .chunks(H3_REFERENCE_INSTALL_BATCH_ROWS)
        .take(MAX_H3_REFERENCE_INSTALL_BATCHES)
    {
        insert_membership_batch(transaction, cohort.receipt().ref_digest(), batch)?;
    }
    Ok(())
}

fn insert_membership_batch(
    transaction: &mut Transaction<'_>,
    ref_digest: RefDigest,
    rows: &[H3ReferenceCellRow],
) -> Result<(), H3ReferenceInstallError> {
    let mut cell_ids = Vec::with_capacity(rows.len());
    let mut origins = Vec::with_capacity(rows.len());
    for row in rows.iter().take(H3_REFERENCE_INSTALL_BATCH_ROWS) {
        cell_ids.push(cell_to_sql(
            row.cell_id(),
            H3ReferenceInstallOperation::InsertMembership,
        )?);
        origins.push(i16::from(row.origin().code()));
    }
    transaction
        .execute(
            INSERT_MEMBERSHIP_SQL,
            &[&ref_digest.as_bytes().as_slice(), &cell_ids, &origins],
        )
        .map_err(|_| database_error(H3ReferenceInstallOperation::InsertMembership))?;
    Ok(())
}

fn rollback_preserving<T>(
    transaction: Transaction<'_>,
    primary: H3ReferenceInstallError,
) -> Result<T, H3ReferenceInstallError> {
    let rollback = transaction
        .rollback()
        .map_err(|_| database_error(H3ReferenceInstallOperation::RollbackTransaction));
    preserve_rollback_result(primary, rollback)
}

fn preserve_rollback_result<T>(
    primary: H3ReferenceInstallError,
    rollback: Result<(), H3ReferenceInstallError>,
) -> Result<T, H3ReferenceInstallError> {
    match rollback {
        Ok(()) => Err(primary),
        Err(rollback) => Err(H3ReferenceInstallError::FailureAndRollback {
            primary: Box::new(primary),
            rollback: Box::new(rollback),
        }),
    }
}

fn decode_value<T>(
    row: &Row,
    index: usize,
    operation: H3ReferenceInstallOperation,
) -> Result<T, H3ReferenceInstallError>
where
    T: postgres::types::FromSqlOwned,
{
    row.try_get(index)
        .map_err(|_| H3ReferenceInstallError::Decode { operation })
}

fn decode_digest(
    row: &Row,
    index: usize,
    operation: H3ReferenceInstallOperation,
) -> Result<RefDigest, H3ReferenceInstallError> {
    let raw: Vec<u8> = decode_value(row, index, operation)?;
    let bytes = <[u8; 32]>::try_from(raw.as_slice())
        .map_err(|_| H3ReferenceInstallError::Decode { operation })?;
    Ok(RefDigest::from_bytes(bytes))
}

fn decode_count(
    row: &Row,
    index: usize,
    operation: H3ReferenceInstallOperation,
) -> Result<usize, H3ReferenceInstallError> {
    let raw: i64 = decode_value(row, index, operation)?;
    usize::try_from(raw).map_err(|_| H3ReferenceInstallError::Decode { operation })
}

fn decode_cell(
    row: &Row,
    index: usize,
    operation: H3ReferenceInstallOperation,
) -> Result<H3CellId, H3ReferenceInstallError> {
    let raw: i64 = decode_value(row, index, operation)?;
    H3CellId::try_from(raw)
        .map_err(|source| H3ReferenceInstallError::CellIdentity { operation, source })
}

fn decode_optional_cell(
    row: &Row,
    index: usize,
    operation: H3ReferenceInstallOperation,
) -> Result<Option<H3CellId>, H3ReferenceInstallError> {
    let raw: Option<i64> = decode_value(row, index, operation)?;
    raw.map(H3CellId::try_from)
        .transpose()
        .map_err(|source| H3ReferenceInstallError::CellIdentity { operation, source })
}

fn decode_origin(
    row: &Row,
    index: usize,
    operation: H3ReferenceInstallOperation,
) -> Result<H3ReferenceOrigin, H3ReferenceInstallError> {
    let raw: i16 = decode_value(row, index, operation)?;
    match raw {
        1 => Ok(H3ReferenceOrigin::Direct),
        2 => Ok(H3ReferenceOrigin::DerivedAncestor),
        _ => Err(H3ReferenceInstallError::Decode { operation }),
    }
}

fn cell_to_sql(
    cell: H3CellId,
    operation: H3ReferenceInstallOperation,
) -> Result<i64, H3ReferenceInstallError> {
    i64::try_from(cell)
        .map_err(|source| H3ReferenceInstallError::CellIdentity { operation, source })
}

fn optional_cell_to_sql(
    cell: Option<H3CellId>,
    operation: H3ReferenceInstallOperation,
) -> Result<Option<i64>, H3ReferenceInstallError> {
    cell.map(|value| cell_to_sql(value, operation)).transpose()
}

fn count_to_sql(count: usize) -> Result<i64, H3ReferenceInstallError> {
    i64::try_from(count).map_err(|_| H3ReferenceInstallError::Bounds {
        resource: H3ReferenceInstallBoundedResource::MembershipRows,
        actual: count,
        max: MAX_H3_REFERENCE_CLOSURE_ROWS,
    })
}

fn database_error(operation: H3ReferenceInstallOperation) -> H3ReferenceInstallError {
    H3ReferenceInstallError::Database { operation }
}

fn conflict(component: H3ReferenceInstallConflict) -> H3ReferenceInstallError {
    H3ReferenceInstallError::Conflict { component }
}

#[cfg(test)]
pub(crate) mod live_postgres_tests {
    use std::mem::size_of;

    use postgres::{Config, NoTls};

    use super::{
        attempt_install_transaction, conflict, install_representative_h3_cohort,
        install_representative_h3_cohort_using, prepare_install_transaction, CommitAttempt,
        H3ReferenceInstallBoundedResource, H3ReferenceInstallConflict,
        H3ReferenceInstallDisposition, H3ReferenceInstallError,
    };
    use crate::{build_representative_h3_cohort_v1, H3CellId, H3ReferenceCohort, RefDigest};

    const SOURCE_FIXTURE: &[u8] = include_bytes!("../tests/fixtures/h3_reference_source_v1.bin");
    const SOURCE_DOMAIN: &[u8] = b"babylon.h3.reference-source.v1\0";
    const SOURCE_COUNT: usize = 48_764;
    const BACKEND_TERMINATION_TIMEOUT_MILLIS: i64 = 5_000;
    const CLOSURE_COUNT: usize = 59_849;
    const EXCESS_MEMBERSHIP_COUNT: usize = 2;
    const RESOLUTION_ZERO_CANDIDATES: [i64; 12] = [
        0x0800_9fff_ffff_ffff,
        0x0801_dfff_ffff_ffff,
        0x0803_1fff_ffff_ffff,
        0x0804_dfff_ffff_ffff,
        0x0806_3fff_ffff_ffff,
        0x0807_5fff_ffff_ffff,
        0x0807_ffff_ffff_ffff,
        0x0809_1fff_ffff_ffff,
        0x080a_7fff_ffff_ffff,
        0x080c_3fff_ffff_ffff,
        0x080d_7fff_ffff_ffff,
        0x080e_bfff_ffff_ffff,
    ];
    const ARTIFACT_DIGEST: [u8; 32] = [
        0xe6, 0x0d, 0x93, 0xa4, 0x3d, 0x6c, 0x66, 0xe8, 0x4f, 0x1e, 0x53, 0xec, 0xaf, 0x63, 0x3a,
        0xf5, 0x91, 0x1b, 0xd5, 0xb4, 0x8b, 0x0e, 0xf0, 0xad, 0x6a, 0x01, 0x2f, 0x6d, 0x9f, 0x5b,
        0x13, 0xa9,
    ];

    pub(crate) fn verify_rollback_and_killed_retry(config: &Config, admin: &Config) {
        let cohort = representative_cohort();
        assert_eq!(reference_counts(config), (0, 0, 0));
        let mut forced_failure = |client: &mut postgres::Client, cohort: &H3ReferenceCohort| {
            let transaction = prepare_install_transaction(client, cohort)?;
            super::rollback_preserving(
                transaction,
                conflict(H3ReferenceInstallConflict::Membership),
            )
        };
        assert!(matches!(
            install_representative_h3_cohort_using(config, &cohort, &mut forced_failure),
            Err(super::H3ReferenceInstallError::Conflict {
                component: H3ReferenceInstallConflict::Membership
            })
        ));
        assert_eq!(reference_counts(config), (0, 0, 0));

        let mut first_attempt = true;
        let mut killed_attempt = |client: &mut postgres::Client, cohort: &H3ReferenceCohort| {
            if first_attempt {
                first_attempt = false;
                killed_before_commit(client, cohort, admin)
            } else {
                attempt_install_transaction(client, cohort)
            }
        };
        let report =
            install_representative_h3_cohort_using(config, &cohort, &mut killed_attempt).unwrap();
        assert_eq!(
            report.disposition(),
            H3ReferenceInstallDisposition::Installed
        );
        assert_eq!(report.commit_attempts(), 2);
        assert_eq!(reference_counts(config), (59_849, 1, 59_849));
    }

    pub(crate) fn verify_committed_reconciliation(config: &Config, admin: &Config) {
        let cohort = representative_cohort();
        let mut first_attempt = true;
        let mut ambiguous_attempt = |client: &mut postgres::Client, cohort: &H3ReferenceCohort| {
            let backend_pid = backend_pid(client);
            let outcome = attempt_install_transaction(client, cohort)?;
            if first_attempt {
                first_attempt = false;
                assert_eq!(outcome, CommitAttempt::Committed);
                terminate_backend(admin, backend_pid);
                Ok(CommitAttempt::Ambiguous)
            } else {
                Ok(outcome)
            }
        };
        let report =
            install_representative_h3_cohort_using(config, &cohort, &mut ambiguous_attempt)
                .unwrap();
        assert_eq!(
            report.disposition(),
            H3ReferenceInstallDisposition::ReconciledAfterAmbiguousCommit
        );
        assert_eq!(report.commit_attempts(), 1);
        assert_eq!(reference_counts(config), (59_849, 1, 59_849));
    }

    pub(crate) fn verify_membership_cardinality_bound(config: &Config) {
        let cohort = representative_cohort();
        let report = install_representative_h3_cohort(config, &cohort).unwrap();
        assert_eq!(
            report.disposition(),
            H3ReferenceInstallDisposition::Installed
        );
        insert_excess_membership(config, cohort.receipt().ref_digest());
        let excess_count = i64::try_from(CLOSURE_COUNT + EXCESS_MEMBERSHIP_COUNT).unwrap();
        assert_eq!(reference_counts(config), (excess_count, 1, excess_count));
        assert_eq!(
            install_representative_h3_cohort(config, &cohort),
            Err(H3ReferenceInstallError::Bounds {
                resource: H3ReferenceInstallBoundedResource::MembershipRows,
                actual: CLOSURE_COUNT + 1,
                max: CLOSURE_COUNT,
            })
        );
    }

    fn insert_excess_membership(config: &Config, ref_digest: RefDigest) {
        let mut client = config.connect(NoTls).unwrap();
        let mut transaction = client.transaction().unwrap();
        let rows = transaction
            .query(
                "INSERT INTO babylon_ref.h3_cell \
                 (cell_id, resolution, immediate_parent, ancestor_r4, ancestor_r5, \
                  ancestor_r6, ancestor_r7) \
                 SELECT candidate.cell_id, 0, NULL, NULL, NULL, NULL, NULL \
                 FROM pg_catalog.unnest($1::bigint[]) AS candidate(cell_id) \
                 WHERE NOT EXISTS (SELECT 1 FROM babylon_ref.h3_cell AS existing \
                                   WHERE existing.cell_id = candidate.cell_id) \
                 ORDER BY candidate.cell_id LIMIT $2 RETURNING cell_id",
                &[
                    &RESOLUTION_ZERO_CANDIDATES.as_slice(),
                    &i64::try_from(EXCESS_MEMBERSHIP_COUNT).unwrap(),
                ],
            )
            .unwrap();
        assert_eq!(rows.len(), EXCESS_MEMBERSHIP_COUNT);
        let inserted = rows
            .iter()
            .take(EXCESS_MEMBERSHIP_COUNT)
            .map(|row| row.get::<_, i64>(0))
            .collect::<Vec<_>>();
        let memberships = transaction
            .execute(
                "INSERT INTO babylon_ref.h3_reference_membership \
                 (ref_digest, cell_id, origin) \
                 SELECT $1, input.cell_id, 2 \
                 FROM pg_catalog.unnest($2::bigint[]) AS input(cell_id)",
                &[&ref_digest.as_bytes().as_slice(), &inserted],
            )
            .unwrap();
        assert_eq!(
            usize::try_from(memberships).unwrap(),
            EXCESS_MEMBERSHIP_COUNT
        );
        transaction.commit().unwrap();
    }

    fn killed_before_commit(
        client: &mut postgres::Client,
        cohort: &H3ReferenceCohort,
        admin: &Config,
    ) -> Result<CommitAttempt, super::H3ReferenceInstallError> {
        let backend_pid = backend_pid(client);
        let transaction = prepare_install_transaction(client, cohort)?;
        terminate_backend(admin, backend_pid);
        assert!(transaction.commit().is_err());
        Ok(CommitAttempt::Ambiguous)
    }

    fn backend_pid(client: &mut postgres::Client) -> i32 {
        client
            .query_one("SELECT pg_catalog.pg_backend_pid()", &[])
            .unwrap()
            .try_get(0)
            .unwrap()
    }

    fn terminate_backend(admin: &Config, backend_pid: i32) {
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
    }

    fn reference_counts(config: &Config) -> (i64, i64, i64) {
        let mut client = config.connect(NoTls).unwrap();
        let row = client
            .query_one(
                "SELECT (SELECT pg_catalog.count(*) FROM babylon_ref.h3_cell), \
                        (SELECT pg_catalog.count(*) FROM babylon_ref.h3_reference_cohort), \
                        (SELECT pg_catalog.count(*) \
                         FROM babylon_ref.h3_reference_membership)",
                &[],
            )
            .unwrap();
        (row.get(0), row.get(1), row.get(2))
    }

    fn representative_cohort() -> H3ReferenceCohort {
        build_representative_h3_cohort_v1(RefDigest::from_bytes(ARTIFACT_DIGEST), &source_cells())
            .unwrap()
    }

    fn source_cells() -> Vec<H3CellId> {
        assert!(SOURCE_FIXTURE.starts_with(SOURCE_DOMAIN));
        let count_offset = SOURCE_DOMAIN.len();
        let payload_offset = count_offset + size_of::<u64>();
        let count = u64::from_be_bytes(
            SOURCE_FIXTURE[count_offset..payload_offset]
                .try_into()
                .unwrap(),
        );
        assert_eq!(usize::try_from(count).unwrap(), SOURCE_COUNT);
        SOURCE_FIXTURE[payload_offset..]
            .chunks_exact(size_of::<u64>())
            .take(SOURCE_COUNT)
            .map(|chunk| {
                let raw = u64::from_be_bytes(chunk.try_into().unwrap());
                H3CellId::try_from(raw).unwrap()
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::{
        drive_install, installer_config, preserve_rollback_result, CommitAttempt, InstallDriver,
        InstallPresence, H3_REFERENCE_SESSION_SETTINGS_SQL,
        MAX_H3_REFERENCE_INSTALL_COMMIT_ATTEMPTS,
    };
    use crate::{
        H3ReferenceInstallConflict, H3ReferenceInstallDisposition, H3ReferenceInstallError,
        H3ReferenceInstallOperation, LEGACY_ADOPTER_CONNECT_TIMEOUT,
        LEGACY_ADOPTER_STARTUP_OPTIONS, LEGACY_ADOPTER_TCP_USER_TIMEOUT,
    };
    use postgres::Config;
    use std::time::Duration;

    struct ScriptedDriver {
        attempts: [Option<CommitAttempt>; MAX_H3_REFERENCE_INSTALL_COMMIT_ATTEMPTS],
        reconciliations: [Option<InstallPresence>; MAX_H3_REFERENCE_INSTALL_COMMIT_ATTEMPTS],
        reconciliation_failure: Option<H3ReferenceInstallError>,
        attempt_calls: usize,
        reconciliation_calls: usize,
    }

    impl ScriptedDriver {
        fn new(
            attempts: [Option<CommitAttempt>; MAX_H3_REFERENCE_INSTALL_COMMIT_ATTEMPTS],
            reconciliations: [Option<InstallPresence>; MAX_H3_REFERENCE_INSTALL_COMMIT_ATTEMPTS],
        ) -> Self {
            Self {
                attempts,
                reconciliations,
                reconciliation_failure: None,
                attempt_calls: 0,
                reconciliation_calls: 0,
            }
        }

        fn with_reconciliation_failure(mut self, failure: H3ReferenceInstallError) -> Self {
            self.reconciliation_failure = Some(failure);
            self
        }
    }

    impl InstallDriver for ScriptedDriver {
        fn attempt_commit(&mut self) -> Result<CommitAttempt, H3ReferenceInstallError> {
            let index = self.attempt_calls;
            self.attempt_calls = self
                .attempt_calls
                .checked_add(1)
                .expect("bounded call count");
            Ok(self.attempts[index].expect("unexpected commit attempt"))
        }

        fn reconcile(&mut self) -> Result<InstallPresence, H3ReferenceInstallError> {
            let index = self.reconciliation_calls;
            self.reconciliation_calls = self
                .reconciliation_calls
                .checked_add(1)
                .expect("bounded call count");
            if let Some(failure) = self.reconciliation_failure.take() {
                return Err(failure);
            }
            Ok(self.reconciliations[index].expect("unexpected reconciliation"))
        }
    }

    #[test]
    fn installer_preserves_epoch_bounds_before_its_closed_session_widening() {
        let mut caller = Config::new();
        caller
            .host("127.0.0.1")
            .connect_timeout(Duration::from_millis(1))
            .tcp_user_timeout(Duration::from_millis(1))
            .options("-c statement_timeout=1ms -c search_path=public");

        let bounded = installer_config(&caller);

        assert_eq!(bounded.get_options(), Some(LEGACY_ADOPTER_STARTUP_OPTIONS));
        assert_eq!(
            bounded.get_connect_timeout().copied(),
            Some(LEGACY_ADOPTER_CONNECT_TIMEOUT)
        );
        assert_eq!(
            bounded.get_tcp_user_timeout().copied(),
            Some(LEGACY_ADOPTER_TCP_USER_TIMEOUT)
        );
        assert_eq!(
            H3_REFERENCE_SESSION_SETTINGS_SQL,
            "SET statement_timeout TO '30000ms'"
        );
    }

    #[test]
    fn committed_install_reports_installed_after_one_attempt() {
        let mut driver = ScriptedDriver::new([Some(CommitAttempt::Committed), None], [None, None]);
        let resolution = drive_install(InstallPresence::Absent, &mut driver).unwrap();

        assert_eq!(
            resolution.disposition,
            H3ReferenceInstallDisposition::Installed
        );
        assert_eq!(resolution.commit_attempts, 1);
        assert_eq!((driver.attempt_calls, driver.reconciliation_calls), (1, 0));
    }

    #[test]
    fn exact_preexisting_cohort_skips_commit() {
        let mut driver = ScriptedDriver::new([None, None], [None, None]);
        let resolution = drive_install(InstallPresence::Exact, &mut driver).unwrap();

        assert_eq!(
            resolution.disposition,
            H3ReferenceInstallDisposition::AlreadyPresent
        );
        assert_eq!(resolution.commit_attempts, 0);
        assert_eq!((driver.attempt_calls, driver.reconciliation_calls), (0, 0));
    }

    #[test]
    fn ambiguous_commit_reconciles_exact_cohort_without_retry() {
        let mut driver = ScriptedDriver::new(
            [Some(CommitAttempt::Ambiguous), None],
            [Some(InstallPresence::Exact), None],
        );
        let resolution = drive_install(InstallPresence::Absent, &mut driver).unwrap();

        assert_eq!(
            resolution.disposition,
            H3ReferenceInstallDisposition::ReconciledAfterAmbiguousCommit
        );
        assert_eq!(resolution.commit_attempts, 1);
        assert_eq!((driver.attempt_calls, driver.reconciliation_calls), (1, 1));
    }

    #[test]
    fn ambiguous_absence_retries_once_then_installs() {
        let mut driver = ScriptedDriver::new(
            [
                Some(CommitAttempt::Ambiguous),
                Some(CommitAttempt::Committed),
            ],
            [Some(InstallPresence::Absent), None],
        );
        let resolution = drive_install(InstallPresence::Absent, &mut driver).unwrap();

        assert_eq!(
            resolution.disposition,
            H3ReferenceInstallDisposition::Installed
        );
        assert_eq!(resolution.commit_attempts, 2);
        assert_eq!((driver.attempt_calls, driver.reconciliation_calls), (2, 1));
    }

    #[test]
    fn two_ambiguous_absences_refuse_without_third_attempt() {
        let mut driver = ScriptedDriver::new(
            [
                Some(CommitAttempt::Ambiguous),
                Some(CommitAttempt::Ambiguous),
            ],
            [Some(InstallPresence::Absent), Some(InstallPresence::Absent)],
        );
        let error = drive_install(InstallPresence::Absent, &mut driver).unwrap_err();

        assert_eq!(
            error,
            H3ReferenceInstallError::AmbiguousCommitUnresolved { attempts: 2 }
        );
        assert_eq!((driver.attempt_calls, driver.reconciliation_calls), (2, 2));
    }

    #[test]
    fn ambiguous_reconciliation_failure_preserves_commit_uncertainty() {
        let reconciliation = H3ReferenceInstallError::Database {
            operation: H3ReferenceInstallOperation::ReadHeader,
        };
        let mut driver = ScriptedDriver::new([Some(CommitAttempt::Ambiguous), None], [None, None])
            .with_reconciliation_failure(reconciliation.clone());

        assert_eq!(
            drive_install(InstallPresence::Absent, &mut driver),
            Err(H3ReferenceInstallError::AmbiguousCommitAndReconciliation {
                attempts: 1,
                reconciliation: Box::new(reconciliation),
            })
        );
        assert_eq!((driver.attempt_calls, driver.reconciliation_calls), (1, 1));
    }

    #[test]
    fn rollback_failure_preserves_the_primary_install_failure() {
        let primary = H3ReferenceInstallError::Conflict {
            component: H3ReferenceInstallConflict::Membership,
        };
        let rollback = H3ReferenceInstallError::Database {
            operation: H3ReferenceInstallOperation::RollbackTransaction,
        };

        assert_eq!(
            preserve_rollback_result::<()>(primary.clone(), Ok(())),
            Err(primary.clone())
        );
        assert_eq!(
            preserve_rollback_result::<()>(primary.clone(), Err(rollback.clone())),
            Err(H3ReferenceInstallError::FailureAndRollback {
                primary: Box::new(primary),
                rollback: Box::new(rollback),
            })
        );
    }
}
