//! Closed-authority marker-last `PostgreSQL` writer and deterministic resume reader.

use babylon_kernel::replay::{ReplaySeed, ReplaySessionIdV1};
use babylon_kernel::tick_content_hash::{RefDigestV1, TickContentHashV1};
use babylon_kernel::ContentDigest;
use postgres::binary_copy::BinaryCopyInWriter;
use postgres::types::Type;
use postgres::{Client, Config, GenericClient, IsolationLevel, NoTls, Row, Transaction};

use crate::committed_tick_envelope::{
    CommittedTickEnvelopeV1, CommittedTickRowFamilyV1, MAX_COMMITTED_TICK_ROWS_V1,
    MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1,
};
use crate::committed_tick_storage::{
    CampaignStorageRowV1, CommittedTickStorageEnvelopeV1, CommittedTickStorageErrorV1,
};
use crate::identity::CampaignId;
use crate::legacy_adopter::{
    acquire_lock, release_lock, validate_legacy_connection_target, LegacyAdopterError,
};
use crate::schema_epoch::{
    bounded_config, inspect_schema_epoch_under_lock, SchemaEpochError, SchemaEpochOrigin,
    CURRENT_SCHEMA_EPOCH,
};
use crate::writer_gate::RustWriterAuthority;

const COMMITTED_TICK_SESSION_SETTINGS_SQL: &str = "SET statement_timeout TO '30000ms'";
const COMMITTED_TICK_LOCAL_SETTINGS_SQL: &str = "SET LOCAL search_path TO pg_catalog; \
    SET LOCAL synchronous_commit TO on";
const COMMITTED_TICK_SETTINGS_QUERY: &str = "SELECT \
    pg_catalog.current_setting('transaction_isolation'), \
    pg_catalog.current_setting('transaction_read_only'), \
    pg_catalog.current_setting('search_path'), \
    pg_catalog.current_setting('synchronous_commit'), \
    pg_catalog.current_setting('statement_timeout'), \
    pg_catalog.current_setting('lock_timeout'), \
    pg_catalog.current_setting('idle_in_transaction_session_timeout')";
const READ_CAMPAIGN_SQL: &str = "SELECT replay_layout_version, rng_layout_version, \
    replay_session_id, rng_seed, defines_hash, rules_hash, ref_digest \
    FROM babylon_state.campaign WHERE campaign_id = $1::text::uuid LIMIT 2";
const INSERT_CAMPAIGN_SQL: &str = "INSERT INTO babylon_state.campaign \
    (campaign_id, replay_layout_version, rng_layout_version, replay_session_id, rng_seed, \
     defines_hash, rules_hash, ref_digest) \
    VALUES ($1::text::uuid, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT DO NOTHING";
const LOCK_CAMPAIGN_SQL: &str = "SELECT campaign_id FROM babylon_state.campaign \
    WHERE campaign_id = $1::text::uuid FOR UPDATE";
const READ_MARKER_SQL: &str = "SELECT envelope_layout_version, tick_content_hash, \
    envelope_digest FROM babylon_state.tick_commit \
    WHERE campaign_id = $1::text::uuid AND resolve_tick = $2 LIMIT 2";
const READ_LAST_TICK_SQL: &str = "SELECT resolve_tick FROM babylon_state.tick_commit \
    WHERE campaign_id = $1::text::uuid ORDER BY resolve_tick DESC LIMIT 1";
const INSERT_MARKER_SQL: &str = "INSERT INTO babylon_state.tick_commit \
    (campaign_id, resolve_tick, envelope_layout_version, tick_content_hash, envelope_digest) \
    VALUES ($1::text::uuid, $2, $3, $4, $5)";
const READ_LAST_MARKER_SQL: &str = "SELECT resolve_tick, tick_content_hash, envelope_digest \
    FROM babylon_state.tick_commit WHERE campaign_id = $1::text::uuid \
    ORDER BY resolve_tick DESC LIMIT 1";
const READ_FOUNDATION_CHECKPOINT_SQL: &str = "SELECT marker.resolve_tick, \
    marker.tick_content_hash, marker.envelope_digest \
    FROM babylon_state.tick_commit AS marker \
    WHERE marker.campaign_id = $1::text::uuid AND marker.resolve_tick = 0 \
      AND EXISTS (SELECT 1 FROM babylon_state.tick_checkpoint_row AS checkpoint \
                  WHERE checkpoint.campaign_id = marker.campaign_id \
                    AND checkpoint.resolve_tick = marker.resolve_tick) \
    LIMIT 1";
const READ_REPLAY_TAIL_SQL: &str = "SELECT resolve_tick, tick_content_hash, envelope_digest \
    FROM babylon_state.tick_commit \
    WHERE campaign_id = $1::text::uuid AND resolve_tick > $2 AND resolve_tick <= $3 \
    ORDER BY resolve_tick LIMIT $4";
const MAX_TRANSACTION_ATTEMPTS_V1: usize = 2;
/// Hard safety ceiling for caller-selected checkpoint replay tails.
pub const MAX_COMMITTED_TICK_HYDRATION_TAIL_V1: usize = MAX_COMMITTED_TICK_ROWS_V1;

/// Acknowledged outcomes. Every variant is returned only after logically committed state is observed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommittedTickCommitDispositionV1 {
    /// This invocation received a successful `COMMIT` response.
    Committed,
    /// Exact marker and row bytes already existed before a write attempt.
    AlreadyCommitted,
    /// A transport-ambiguous `COMMIT` was proven exact after reconnecting.
    ReconciledAfterAmbiguousCommit,
}

/// Post-commit acknowledgement returned to the composition root.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CommittedTickCommitReportV1 {
    disposition: CommittedTickCommitDispositionV1,
    resolve_tick: u64,
    commit_attempts: usize,
}

impl CommittedTickCommitReportV1 {
    /// Acknowledged commit disposition.
    #[must_use]
    pub const fn disposition(self) -> CommittedTickCommitDispositionV1 {
        self.disposition
    }

    /// Exact acknowledged tick.
    #[must_use]
    pub const fn resolve_tick(self) -> u64 {
        self.resolve_tick
    }

    /// Number of `COMMIT` operations attempted by this invocation.
    #[must_use]
    pub const fn commit_attempts(self) -> usize {
        self.commit_attempts
    }
}

/// Closed database operations used in credential-safe failures.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommittedTickDatabaseOperationV1 {
    /// Open one bounded local connection.
    Connect,
    /// Apply or verify bounded session settings.
    PrepareSession,
    /// Begin a serializable transaction.
    BeginTransaction,
    /// Apply or verify exact local transaction settings.
    PrepareTransaction,
    /// Read or lock the immutable campaign identity.
    ReadCampaign,
    /// Insert the immutable campaign identity.
    InsertCampaign,
    /// Read one commit marker.
    ReadMarker,
    /// Read exact family rows.
    ReadRows { family: CommittedTickRowFamilyV1 },
    /// Read the last committed marker.
    ReadLastMarker,
    /// Read the nearest committed checkpoint.
    ReadCheckpoint,
    /// Read the bounded committed replay tail.
    ReadReplayTail,
    /// Insert exact family rows.
    InsertRows { family: CommittedTickRowFamilyV1 },
    /// Insert the visibility marker last.
    InsertMarker,
    /// Commit the verified transaction.
    CommitTransaction,
    /// Roll back a refused transaction.
    RollbackTransaction,
}

/// Credential-safe `PostgreSQL` diagnostic.
#[derive(Clone)]
pub struct CommittedTickDatabaseDiagnosticV1 {
    server: Option<Box<postgres::error::DbError>>,
}

impl CommittedTickDatabaseDiagnosticV1 {
    /// Server diagnostic when `PostgreSQL`, rather than transport, supplied one.
    #[must_use]
    pub fn server(&self) -> Option<&postgres::error::DbError> {
        self.server.as_deref()
    }
}

impl std::fmt::Debug for CommittedTickDatabaseDiagnosticV1 {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let (sqlstate, message) = self.server.as_deref().map_or((None, None), |server| {
            (Some(server.code().code()), Some(server.message()))
        });
        formatter
            .debug_struct("CommittedTickDatabaseDiagnosticV1")
            .field("sqlstate", &sqlstate)
            .field("message", &message)
            .finish()
    }
}

/// Exact durable component which differed from the requested commit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommittedTickConflictComponentV1 {
    /// Immutable campaign replay or content identity.
    CampaignIdentity,
    /// Kernel-owned constitutional content identity.
    TickContentHash,
    /// Diagnostic complete-envelope identity.
    EnvelopeDigest,
    /// One exact family row set.
    RowFamily(CommittedTickRowFamilyV1),
}

/// Closed writer and hydration refusal surface.
#[derive(Debug)]
pub enum CommittedTickWriteErrorV1 {
    /// The supplied maintenance target violated the local-only contract.
    ConnectionTarget(LegacyAdopterError),
    /// A bounded connection could not be opened.
    Database {
        /// Failed operation.
        operation: CommittedTickDatabaseOperationV1,
        /// Credential-safe diagnostic.
        diagnostic: CommittedTickDatabaseDiagnosticV1,
    },
    /// The schema advisory lock could not be acquired.
    Lock(LegacyAdopterError),
    /// Exact schema inspection failed.
    SchemaEpoch(SchemaEpochError),
    /// Runtime I/O requires the exact current Rust schema epoch.
    ExactSchemaEpochRequired {
        /// Compiled epoch.
        expected: usize,
        /// Observed applied prefix.
        actual: usize,
        /// Observed schema origin.
        origin: SchemaEpochOrigin,
    },
    /// Envelope-to-SQL mapping refused a value.
    StorageMapping(CommittedTickStorageErrorV1),
    /// Campaign key on the row did not match the envelope claim.
    CampaignKeyMismatch,
    /// Stored bytes differ from the requested canonical identity.
    Conflict {
        /// First exact differing component.
        component: CommittedTickConflictComponentV1,
    },
    /// The new tick was not the next marker after the last survivor.
    TickSequence {
        /// Last surviving committed tick, if any.
        last_committed: Option<u64>,
        /// Requested tick.
        requested: u64,
    },
    /// Family rows existed without their visibility marker.
    RowsWithoutMarker {
        /// First family carrying uncommitted-looking rows.
        family: CommittedTickRowFamilyV1,
    },
    /// Stored values could not be decoded into the governed representation.
    Decode {
        /// Operation at the decoding boundary.
        operation: CommittedTickDatabaseOperationV1,
    },
    /// The transaction did not retain the required bounded writer profile.
    TransactionSetting {
        /// Stable `PostgreSQL` setting name.
        setting: &'static str,
        /// Required rendered value.
        expected: &'static str,
        /// Observed rendered value.
        actual: Box<str>,
    },
    /// A stored or requested bounded collection exceeded its ceiling.
    Bounds {
        /// Stable bounded resource name.
        resource: &'static str,
        /// Observed value.
        actual: usize,
        /// Maximum accepted value.
        maximum: usize,
    },
    /// The bounded commit attempts remained transport-ambiguous and absent.
    AmbiguousCommitUnresolved { attempts: usize },
    /// Ambiguity reconciliation itself failed.
    AmbiguousCommitAndReconciliation {
        attempts: usize,
        reconciliation: Box<CommittedTickWriteErrorV1>,
    },
    /// Explicit advisory-lock release failed.
    Unlock(LegacyAdopterError),
    /// A primary failure and explicit lock cleanup both failed.
    FailureAndCleanup {
        primary: Box<CommittedTickWriteErrorV1>,
        cleanup: Box<CommittedTickWriteErrorV1>,
    },
    /// A transaction failure and explicit rollback both failed.
    FailureAndRollback {
        primary: Box<CommittedTickWriteErrorV1>,
        rollback: Box<CommittedTickWriteErrorV1>,
    },
}

impl std::fmt::Display for CommittedTickWriteErrorV1 {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "committed tick persistence refused: {self:?}")
    }
}

impl std::error::Error for CommittedTickWriteErrorV1 {}

/// Exact owned checkpoint row returned by the resume reader.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommittedTickHydratedRowV1 {
    key: Box<[u8]>,
    payload: Box<[u8]>,
}

impl CommittedTickHydratedRowV1 {
    /// Own one non-empty exact key and its opaque payload.
    ///
    /// # Errors
    /// Refuses an empty key.
    pub fn new(key: Vec<u8>, payload: Vec<u8>) -> Result<Self, CommittedTickWriteErrorV1> {
        if key.is_empty() {
            return Err(CommittedTickWriteErrorV1::Decode {
                operation: CommittedTickDatabaseOperationV1::ReadCheckpoint,
            });
        }
        Ok(Self {
            key: key.into_boxed_slice(),
            payload: payload.into_boxed_slice(),
        })
    }

    /// Borrow exact checkpoint key bytes.
    #[must_use]
    pub fn key(&self) -> &[u8] {
        &self.key
    }

    /// Borrow exact checkpoint payload bytes.
    #[must_use]
    pub fn payload(&self) -> &[u8] {
        &self.payload
    }
}

/// Exact committed marker identity needed to verify deterministic replay.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CommittedTickHydratedMarkerV1 {
    resolve_tick: u64,
    tick_content_hash: TickContentHashV1,
    envelope_digest: [u8; 32],
}

impl CommittedTickHydratedMarkerV1 {
    /// Committed tick number.
    #[must_use]
    pub const fn resolve_tick(self) -> u64 {
        self.resolve_tick
    }

    /// Expected constitutional content identity after replay.
    #[must_use]
    pub const fn tick_content_hash(self) -> TickContentHashV1 {
        self.tick_content_hash
    }

    /// Stored complete-envelope diagnostic bytes.
    #[must_use]
    pub const fn envelope_digest(self) -> [u8; 32] {
        self.envelope_digest
    }
}

/// Immutable replay inputs loaded with the checkpoint plan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommittedTickHydratedCampaignV1 {
    campaign_id: CampaignId,
    replay_session_id: ReplaySessionIdV1,
    rng_seed: ReplaySeed,
    content: ContentDigest,
    reference: RefDigestV1,
}

impl CommittedTickHydratedCampaignV1 {
    /// Durable storage identity, excluded from engine physics.
    #[must_use]
    pub const fn campaign_id(&self) -> CampaignId {
        self.campaign_id
    }

    /// Deterministic replay namespace.
    #[must_use]
    pub const fn replay_session_id(&self) -> &ReplaySessionIdV1 {
        &self.replay_session_id
    }

    /// Explicit signed RNG seed.
    #[must_use]
    pub const fn rng_seed(&self) -> ReplaySeed {
        self.rng_seed
    }

    /// Immutable mechanics content digests.
    #[must_use]
    pub const fn content(&self) -> &ContentDigest {
        &self.content
    }

    /// Pinned canonical H3 reference cohort.
    #[must_use]
    pub const fn reference(&self) -> RefDigestV1 {
        self.reference
    }
}

/// Deterministic checkpoint bytes and the exact contiguous committed replay tail.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommittedTickHydrationPlanV1 {
    last_committed_tick: u64,
    checkpoint_tick: Option<u64>,
    checkpoint_rows: Box<[CommittedTickHydratedRowV1]>,
    replay_tail: Box<[u64]>,
}

impl CommittedTickHydrationPlanV1 {
    /// Validate an ordered checkpoint plan independently of database transport.
    ///
    /// # Errors
    /// Refuses mismatched checkpoint shape, non-strict row keys, a non-contiguous
    /// replay tail, or a tail above the governed ceiling.
    pub fn compose(
        last_committed_tick: u64,
        checkpoint_tick: Option<u64>,
        checkpoint_rows: Vec<CommittedTickHydratedRowV1>,
        replay_tail: Vec<u64>,
    ) -> Result<Self, CommittedTickWriteErrorV1> {
        validate_hydration_shape(
            last_committed_tick,
            checkpoint_tick,
            &checkpoint_rows,
            &replay_tail,
        )?;
        Ok(Self {
            last_committed_tick,
            checkpoint_tick,
            checkpoint_rows: checkpoint_rows.into_boxed_slice(),
            replay_tail: replay_tail.into_boxed_slice(),
        })
    }

    /// Last surviving commit marker.
    #[must_use]
    pub const fn last_committed_tick(&self) -> u64 {
        self.last_committed_tick
    }

    /// Tick-zero foundation checkpoint selected without interpreting opaque payloads.
    #[must_use]
    pub const fn checkpoint_tick(&self) -> Option<u64> {
        self.checkpoint_tick
    }

    /// Exact primary-key-ordered checkpoint rows.
    #[must_use]
    pub fn checkpoint_rows(&self) -> &[CommittedTickHydratedRowV1] {
        &self.checkpoint_rows
    }

    /// Contiguous committed ticks to replay after the checkpoint.
    #[must_use]
    pub fn replay_tail(&self) -> &[u64] {
        &self.replay_tail
    }
}

/// Complete read-only resume result.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommittedTickHydrationV1 {
    campaign: CommittedTickHydratedCampaignV1,
    plan: CommittedTickHydrationPlanV1,
    checkpoint_marker: Option<CommittedTickHydratedMarkerV1>,
    replay_markers: Box<[CommittedTickHydratedMarkerV1]>,
}

impl CommittedTickHydrationV1 {
    /// Immutable replay inputs.
    #[must_use]
    pub const fn campaign(&self) -> &CommittedTickHydratedCampaignV1 {
        &self.campaign
    }

    /// Checkpoint and tick-number replay plan.
    #[must_use]
    pub const fn plan(&self) -> &CommittedTickHydrationPlanV1 {
        &self.plan
    }

    /// Exact committed identity for the restored checkpoint bytes.
    ///
    /// This remains available when the checkpoint is the last committed tick
    /// and the replay tail is therefore empty.
    #[must_use]
    pub const fn checkpoint_marker(&self) -> Option<CommittedTickHydratedMarkerV1> {
        self.checkpoint_marker
    }

    /// Exact expected identities for every tick in the replay tail.
    #[must_use]
    pub fn replay_markers(&self) -> &[CommittedTickHydratedMarkerV1] {
        &self.replay_markers
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum StoredPresence {
    Absent,
    Exact,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CommitAttempt {
    Committed,
    AlreadyCommitted,
    AmbiguousBeforeCommit,
    AmbiguousCommit,
}

impl CommitAttempt {
    const fn attempted_commit_operation(self) -> bool {
        matches!(self, Self::Committed | Self::AmbiguousCommit)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CommitTransactionStepV1 {
    Begin,
    PrepareTransaction,
    EnsureCampaign,
    LockCampaign,
    InspectPresence,
    RequireNextTick,
    InsertRows { family: CommittedTickRowFamilyV1 },
    InsertMarker,
    Commit,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CommitBoundarySideV1 {
    Before,
    After,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct CommitTransactionBoundaryV1 {
    step: CommitTransactionStepV1,
    side: CommitBoundarySideV1,
}

impl CommitTransactionBoundaryV1 {
    const fn before(step: CommitTransactionStepV1) -> Self {
        Self {
            step,
            side: CommitBoundarySideV1::Before,
        }
    }

    const fn after(step: CommitTransactionStepV1) -> Self {
        Self {
            step,
            side: CommitBoundarySideV1::After,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct CommitResolution {
    disposition: CommittedTickCommitDispositionV1,
    commit_attempts: usize,
}

trait CommitDriver {
    fn attempt_commit(
        &mut self,
        attempt: usize,
    ) -> Result<CommitAttempt, CommittedTickWriteErrorV1>;

    fn reconcile(
        &mut self,
        after_attempt: usize,
    ) -> Result<StoredPresence, CommittedTickWriteErrorV1>;
}

/// Commit one exact envelope through the closed Rust-authority capability.
///
/// The capability currently has no successful production construction path.
/// A successful return is an acknowledgement after `COMMIT`, or after exact
/// post-ambiguity reconciliation observes the marker and every row.
///
/// # Errors
/// Returns a typed target, schema, serialization, conflict, sequence,
/// transaction, commit, ambiguity, or cleanup failure.
pub fn commit_committed_tick_v1(
    config: &Config,
    _authority: &RustWriterAuthority,
    campaign: CampaignStorageRowV1<'_>,
    envelope: &CommittedTickEnvelopeV1,
) -> Result<CommittedTickCommitReportV1, CommittedTickWriteErrorV1> {
    validate_legacy_connection_target(config)
        .map_err(CommittedTickWriteErrorV1::ConnectionTarget)?;
    if campaign.campaign_id() != envelope.claim().campaign_id() {
        return Err(CommittedTickWriteErrorV1::CampaignKeyMismatch);
    }
    let storage = CommittedTickStorageEnvelopeV1::try_from(envelope)
        .map_err(CommittedTickWriteErrorV1::StorageMapping)?;
    let bounded = bounded_config(config);
    let mut session = LockedCommittedTickSession::connect(&bounded)?;
    let result = commit_under_lock(&bounded, &mut session, campaign, &storage);
    session.finish(result)
}

/// Load exact replay inputs, the last surviving marker, committed tick-zero
/// foundation checkpoint rows, and a caller-bounded contiguous committed replay tail.
/// Later checkpoint rows remain inside the replay history because V1 intentionally
/// carries opaque complete-or-delta payloads with no completeness discriminator.
///
/// This read-only path does not require writer authority.
///
/// # Errors
/// Returns a typed target, schema, decode, corruption, bound, or cleanup failure.
pub fn hydrate_committed_tick_checkpoint_v1(
    config: &Config,
    campaign_id: CampaignId,
    max_replay_ticks: usize,
) -> Result<Option<CommittedTickHydrationV1>, CommittedTickWriteErrorV1> {
    if max_replay_ticks > MAX_COMMITTED_TICK_HYDRATION_TAIL_V1 {
        return Err(CommittedTickWriteErrorV1::Bounds {
            resource: "checkpoint replay tail",
            actual: max_replay_ticks,
            maximum: MAX_COMMITTED_TICK_HYDRATION_TAIL_V1,
        });
    }
    validate_legacy_connection_target(config)
        .map_err(CommittedTickWriteErrorV1::ConnectionTarget)?;
    let bounded = bounded_config(config);
    let mut session = LockedCommittedTickSession::connect(&bounded)?;
    let result = hydrate_under_lock(session.client(), campaign_id, max_replay_ticks);
    session.finish(result)
}

struct LockedCommittedTickSession {
    client: Option<Client>,
}

impl LockedCommittedTickSession {
    fn connect(config: &Config) -> Result<Self, CommittedTickWriteErrorV1> {
        let mut client = config
            .connect(NoTls)
            .map_err(|error| database_error(CommittedTickDatabaseOperationV1::Connect, &error))?;
        acquire_lock(&mut client).map_err(CommittedTickWriteErrorV1::Lock)?;
        Ok(Self {
            client: Some(client),
        })
    }

    fn client(&mut self) -> &mut Client {
        self.client
            .as_mut()
            .expect("locked committed-tick session always owns its client")
    }

    fn reconnect(&mut self, config: &Config) -> Result<(), CommittedTickWriteErrorV1> {
        self.client.take();
        *self = Self::connect(config)?;
        Ok(())
    }

    fn finish<T>(
        mut self,
        primary: Result<T, CommittedTickWriteErrorV1>,
    ) -> Result<T, CommittedTickWriteErrorV1> {
        let cleanup = self.client.as_mut().map_or(Ok(()), |client| {
            release_lock(client).map_err(CommittedTickWriteErrorV1::Unlock)
        });
        match (primary, cleanup) {
            (Ok(value), Ok(())) => Ok(value),
            (Err(error), Ok(())) => Err(error),
            (Ok(_), Err(cleanup)) => Err(cleanup),
            (Err(primary), Err(cleanup)) => Err(CommittedTickWriteErrorV1::FailureAndCleanup {
                primary: Box::new(primary),
                cleanup: Box::new(cleanup),
            }),
        }
    }
}

fn commit_under_lock(
    config: &Config,
    session: &mut LockedCommittedTickSession,
    campaign: CampaignStorageRowV1<'_>,
    storage: &CommittedTickStorageEnvelopeV1<'_>,
) -> Result<CommittedTickCommitReportV1, CommittedTickWriteErrorV1> {
    require_exact_schema_epoch(session.client())?;
    prepare_session(session.client())?;
    let initial = match inspect_campaign(session.client(), campaign)? {
        Some(false) => {
            return Err(CommittedTickWriteErrorV1::Conflict {
                component: CommittedTickConflictComponentV1::CampaignIdentity,
            });
        }
        Some(true) => inspect_presence(session.client(), storage)?,
        None => StoredPresence::Absent,
    };
    let mut driver = DatabaseCommitDriver {
        config,
        session,
        campaign,
        storage,
    };
    let resolution = drive_commit(initial, &mut driver)?;
    Ok(CommittedTickCommitReportV1 {
        disposition: resolution.disposition,
        resolve_tick: u64::try_from(storage.marker().resolve_tick())
            .expect("storage mapping checked non-negative u64 tick"),
        commit_attempts: resolution.commit_attempts,
    })
}

fn drive_commit<Driver: CommitDriver>(
    initial: StoredPresence,
    driver: &mut Driver,
) -> Result<CommitResolution, CommittedTickWriteErrorV1> {
    if initial == StoredPresence::Exact {
        return Ok(CommitResolution {
            disposition: CommittedTickCommitDispositionV1::AlreadyCommitted,
            commit_attempts: 0,
        });
    }
    let mut commit_attempts = 0;
    for attempt_index in 0..MAX_TRANSACTION_ATTEMPTS_V1 {
        let transaction_attempts = attempt_index + 1;
        let attempt = driver.attempt_commit(transaction_attempts)?;
        commit_attempts += usize::from(attempt.attempted_commit_operation());
        match attempt {
            CommitAttempt::Committed => {
                return Ok(CommitResolution {
                    disposition: CommittedTickCommitDispositionV1::Committed,
                    commit_attempts,
                });
            }
            CommitAttempt::AlreadyCommitted => {
                return Ok(CommitResolution {
                    disposition: CommittedTickCommitDispositionV1::AlreadyCommitted,
                    commit_attempts,
                });
            }
            CommitAttempt::AmbiguousBeforeCommit | CommitAttempt::AmbiguousCommit => {
                let reconciled =
                    driver
                        .reconcile(transaction_attempts)
                        .map_err(|reconciliation| {
                            CommittedTickWriteErrorV1::AmbiguousCommitAndReconciliation {
                                attempts: transaction_attempts,
                                reconciliation: Box::new(reconciliation),
                            }
                        })?;
                if reconciled == StoredPresence::Exact {
                    return Ok(CommitResolution {
                        disposition:
                            CommittedTickCommitDispositionV1::ReconciledAfterAmbiguousCommit,
                        commit_attempts,
                    });
                }
            }
        }
    }
    Err(CommittedTickWriteErrorV1::AmbiguousCommitUnresolved {
        attempts: MAX_TRANSACTION_ATTEMPTS_V1,
    })
}

struct DatabaseCommitDriver<'config, 'session, 'campaign, 'storage> {
    config: &'config Config,
    session: &'session mut LockedCommittedTickSession,
    campaign: CampaignStorageRowV1<'campaign>,
    storage: &'storage CommittedTickStorageEnvelopeV1<'storage>,
}

impl CommitDriver for DatabaseCommitDriver<'_, '_, '_, '_> {
    fn attempt_commit(
        &mut self,
        _attempt: usize,
    ) -> Result<CommitAttempt, CommittedTickWriteErrorV1> {
        attempt_commit(self.session.client(), self.campaign, self.storage)
    }

    fn reconcile(
        &mut self,
        _after_attempt: usize,
    ) -> Result<StoredPresence, CommittedTickWriteErrorV1> {
        reconcile_after_ambiguous_commit(self.config, self.session, self.campaign, self.storage)
    }
}

fn reconcile_after_ambiguous_commit(
    config: &Config,
    session: &mut LockedCommittedTickSession,
    campaign: CampaignStorageRowV1<'_>,
    storage: &CommittedTickStorageEnvelopeV1<'_>,
) -> Result<StoredPresence, CommittedTickWriteErrorV1> {
    session.reconnect(config)?;
    require_exact_schema_epoch(session.client())?;
    prepare_session(session.client())?;
    match inspect_campaign(session.client(), campaign)? {
        Some(true) => inspect_presence(session.client(), storage),
        Some(false) => Err(CommittedTickWriteErrorV1::Conflict {
            component: CommittedTickConflictComponentV1::CampaignIdentity,
        }),
        None => match inspect_presence(session.client(), storage)? {
            StoredPresence::Absent => Ok(StoredPresence::Absent),
            StoredPresence::Exact => Err(CommittedTickWriteErrorV1::Conflict {
                component: CommittedTickConflictComponentV1::CampaignIdentity,
            }),
        },
    }
}

fn attempt_commit(
    client: &mut Client,
    campaign: CampaignStorageRowV1<'_>,
    storage: &CommittedTickStorageEnvelopeV1<'_>,
) -> Result<CommitAttempt, CommittedTickWriteErrorV1> {
    attempt_commit_using(client, campaign, storage, &mut |_| {})
}

fn attempt_commit_using<Probe>(
    client: &mut Client,
    campaign: CampaignStorageRowV1<'_>,
    storage: &CommittedTickStorageEnvelopeV1<'_>,
    probe: &mut Probe,
) -> Result<CommitAttempt, CommittedTickWriteErrorV1>
where
    Probe: FnMut(CommitTransactionBoundaryV1),
{
    let begin_step = CommitTransactionStepV1::Begin;
    probe(CommitTransactionBoundaryV1::before(begin_step));
    let mut transaction = match client
        .build_transaction()
        .isolation_level(IsolationLevel::Serializable)
        .read_only(false)
        .start()
    {
        Ok(transaction) => transaction,
        Err(error) if postgres_error_is_connection_loss(&error) => {
            return Ok(CommitAttempt::AmbiguousBeforeCommit);
        }
        Err(error) => {
            return Err(database_error(
                CommittedTickDatabaseOperationV1::BeginTransaction,
                &error,
            ));
        }
    };
    probe(CommitTransactionBoundaryV1::after(begin_step));
    let write = write_transaction_using(&mut transaction, campaign, storage, probe);
    match write {
        Ok(StoredPresence::Exact) => {
            rollback(transaction)?;
            Ok(CommitAttempt::AlreadyCommitted)
        }
        Ok(StoredPresence::Absent) => {
            let commit_step = CommitTransactionStepV1::Commit;
            probe(CommitTransactionBoundaryV1::before(commit_step));
            match transaction.commit() {
                Ok(()) => {
                    probe(CommitTransactionBoundaryV1::after(commit_step));
                    Ok(CommitAttempt::Committed)
                }
                Err(error) if postgres_error_is_connection_loss(&error) => {
                    Ok(CommitAttempt::AmbiguousCommit)
                }
                Err(error) => Err(database_error(
                    CommittedTickDatabaseOperationV1::CommitTransaction,
                    &error,
                )),
            }
        }
        Err(primary) => {
            let failure = rollback_preserving(transaction, primary);
            match failure {
                Err(error) if is_connection_loss_transaction_failure(&error) => {
                    Ok(CommitAttempt::AmbiguousBeforeCommit)
                }
                other => other,
            }
        }
    }
}

fn write_transaction_using<Probe>(
    transaction: &mut Transaction<'_>,
    campaign: CampaignStorageRowV1<'_>,
    storage: &CommittedTickStorageEnvelopeV1<'_>,
    probe: &mut Probe,
) -> Result<StoredPresence, CommittedTickWriteErrorV1>
where
    Probe: FnMut(CommitTransactionBoundaryV1),
{
    let prepare_step = CommitTransactionStepV1::PrepareTransaction;
    probe(CommitTransactionBoundaryV1::before(prepare_step));
    prepare_transaction(transaction)?;
    probe(CommitTransactionBoundaryV1::after(prepare_step));

    let campaign_step = CommitTransactionStepV1::EnsureCampaign;
    probe(CommitTransactionBoundaryV1::before(campaign_step));
    ensure_campaign(transaction, campaign)?;
    probe(CommitTransactionBoundaryV1::after(campaign_step));

    let campaign_text = campaign.campaign_id().as_uuid().to_string();
    let lock_step = CommitTransactionStepV1::LockCampaign;
    probe(CommitTransactionBoundaryV1::before(lock_step));
    transaction
        .query_one(LOCK_CAMPAIGN_SQL, &[&campaign_text])
        .map_err(|error| database_error(CommittedTickDatabaseOperationV1::ReadCampaign, &error))?;
    probe(CommitTransactionBoundaryV1::after(lock_step));

    let presence_step = CommitTransactionStepV1::InspectPresence;
    probe(CommitTransactionBoundaryV1::before(presence_step));
    match inspect_presence(transaction, storage)? {
        StoredPresence::Exact => {
            probe(CommitTransactionBoundaryV1::after(presence_step));
            return Ok(StoredPresence::Exact);
        }
        StoredPresence::Absent => {}
    }
    probe(CommitTransactionBoundaryV1::after(presence_step));

    let sequence_step = CommitTransactionStepV1::RequireNextTick;
    probe(CommitTransactionBoundaryV1::before(sequence_step));
    require_next_tick(transaction, storage)?;
    probe(CommitTransactionBoundaryV1::after(sequence_step));

    for batch in storage.batches() {
        let insert_step = CommitTransactionStepV1::InsertRows {
            family: batch.target().family(),
        };
        probe(CommitTransactionBoundaryV1::before(insert_step));
        insert_batch(transaction, batch)?;
        probe(CommitTransactionBoundaryV1::after(insert_step));
    }

    let marker_step = CommitTransactionStepV1::InsertMarker;
    probe(CommitTransactionBoundaryV1::before(marker_step));
    insert_marker(transaction, storage)?;
    probe(CommitTransactionBoundaryV1::after(marker_step));
    Ok(StoredPresence::Absent)
}

fn require_exact_schema_epoch(client: &mut Client) -> Result<(), CommittedTickWriteErrorV1> {
    let (origin, actual) =
        inspect_schema_epoch_under_lock(client).map_err(CommittedTickWriteErrorV1::SchemaEpoch)?;
    if origin == SchemaEpochOrigin::ExistingRustPrefix && actual == CURRENT_SCHEMA_EPOCH {
        Ok(())
    } else {
        Err(CommittedTickWriteErrorV1::ExactSchemaEpochRequired {
            expected: CURRENT_SCHEMA_EPOCH,
            actual,
            origin,
        })
    }
}

fn prepare_session(client: &mut Client) -> Result<(), CommittedTickWriteErrorV1> {
    client
        .batch_execute(COMMITTED_TICK_SESSION_SETTINGS_SQL)
        .map_err(|error| database_error(CommittedTickDatabaseOperationV1::PrepareSession, &error))
}

fn prepare_transaction(transaction: &mut Transaction<'_>) -> Result<(), CommittedTickWriteErrorV1> {
    let operation = CommittedTickDatabaseOperationV1::PrepareTransaction;
    transaction
        .batch_execute(COMMITTED_TICK_LOCAL_SETTINGS_SQL)
        .map_err(|error| database_error(operation, &error))?;
    let row = transaction
        .query_one(COMMITTED_TICK_SETTINGS_QUERY, &[])
        .map_err(|error| database_error(operation, &error))?;
    let expected = [
        ("transaction_isolation", "serializable"),
        ("transaction_read_only", "off"),
        ("search_path", "pg_catalog"),
        ("synchronous_commit", "on"),
        ("statement_timeout", "30s"),
        ("lock_timeout", "5s"),
        ("idle_in_transaction_session_timeout", "5s"),
    ];
    for (index, (setting, wanted)) in expected.iter().enumerate() {
        let actual: String = decode(&row, index, operation)?;
        if actual != *wanted {
            return Err(CommittedTickWriteErrorV1::TransactionSetting {
                setting,
                expected: wanted,
                actual: actual.into_boxed_str(),
            });
        }
    }
    Ok(())
}

fn inspect_campaign<ClientType: GenericClient>(
    client: &mut ClientType,
    expected: CampaignStorageRowV1<'_>,
) -> Result<Option<bool>, CommittedTickWriteErrorV1> {
    let operation = CommittedTickDatabaseOperationV1::ReadCampaign;
    let campaign_text = expected.campaign_id().as_uuid().to_string();
    let rows = client
        .query(READ_CAMPAIGN_SQL, &[&campaign_text])
        .map_err(|error| database_error(operation, &error))?;
    if rows.is_empty() {
        return Ok(None);
    }
    if rows.len() != 1 {
        return Err(CommittedTickWriteErrorV1::Decode { operation });
    }
    let replay_layout: i16 = decode(&rows[0], 0, operation)?;
    let rng_layout: i16 = decode(&rows[0], 1, operation)?;
    let replay_session: String = decode(&rows[0], 2, operation)?;
    let rng_seed: i64 = decode(&rows[0], 3, operation)?;
    let defines_hash: Vec<u8> = decode(&rows[0], 4, operation)?;
    let rules_hash: Vec<u8> = decode(&rows[0], 5, operation)?;
    let ref_digest: Vec<u8> = decode(&rows[0], 6, operation)?;
    Ok(Some(
        replay_layout == expected.replay_layout_version()
            && rng_layout == expected.rng_layout_version()
            && replay_session.as_bytes() == expected.replay_session_bytes()
            && rng_seed == expected.rng_seed()
            && defines_hash.as_slice() == expected.defines_hash()
            && rules_hash.as_slice() == expected.rules_hash()
            && ref_digest.as_slice() == expected.reference().as_bytes(),
    ))
}

fn ensure_campaign(
    transaction: &mut Transaction<'_>,
    expected: CampaignStorageRowV1<'_>,
) -> Result<(), CommittedTickWriteErrorV1> {
    match inspect_campaign(transaction, expected)? {
        Some(true) => return Ok(()),
        Some(false) => {
            return Err(CommittedTickWriteErrorV1::Conflict {
                component: CommittedTickConflictComponentV1::CampaignIdentity,
            });
        }
        None => {}
    }
    let operation = CommittedTickDatabaseOperationV1::InsertCampaign;
    let campaign_text = expected.campaign_id().as_uuid().to_string();
    let replay_session = std::str::from_utf8(expected.replay_session_bytes())
        .map_err(|_| CommittedTickWriteErrorV1::Decode { operation })?;
    let defines_hash = expected.defines_hash().as_slice();
    let rules_hash = expected.rules_hash().as_slice();
    let reference = expected.reference();
    let ref_digest = reference.as_bytes().as_slice();
    transaction
        .execute(
            INSERT_CAMPAIGN_SQL,
            &[
                &campaign_text,
                &expected.replay_layout_version(),
                &expected.rng_layout_version(),
                &replay_session,
                &expected.rng_seed(),
                &defines_hash,
                &rules_hash,
                &ref_digest,
            ],
        )
        .map_err(|error| database_error(operation, &error))?;
    match inspect_campaign(transaction, expected)? {
        Some(true) => Ok(()),
        Some(false) => Err(CommittedTickWriteErrorV1::Conflict {
            component: CommittedTickConflictComponentV1::CampaignIdentity,
        }),
        None => Err(CommittedTickWriteErrorV1::Decode { operation }),
    }
}

fn inspect_presence<ClientType: GenericClient>(
    client: &mut ClientType,
    expected: &CommittedTickStorageEnvelopeV1<'_>,
) -> Result<StoredPresence, CommittedTickWriteErrorV1> {
    let operation = CommittedTickDatabaseOperationV1::ReadMarker;
    let marker = expected.marker();
    let campaign_text = marker.campaign_id().as_uuid().to_string();
    let rows = client
        .query(READ_MARKER_SQL, &[&campaign_text, &marker.resolve_tick()])
        .map_err(|error| database_error(operation, &error))?;
    if rows.is_empty() {
        reject_rows_without_marker(client, expected)?;
        return Ok(StoredPresence::Absent);
    }
    if rows.len() != 1 {
        return Err(CommittedTickWriteErrorV1::Decode { operation });
    }
    let layout: i16 = decode(&rows[0], 0, operation)?;
    let tick_content_hash: Vec<u8> = decode(&rows[0], 1, operation)?;
    let envelope_digest: Vec<u8> = decode(&rows[0], 2, operation)?;
    if layout != marker.envelope_layout_version() {
        return Err(CommittedTickWriteErrorV1::Decode { operation });
    }
    if tick_content_hash.as_slice() != marker.tick_content_hash().as_bytes() {
        return Err(CommittedTickWriteErrorV1::Conflict {
            component: CommittedTickConflictComponentV1::TickContentHash,
        });
    }
    if envelope_digest.as_slice() != marker.envelope_digest().as_bytes() {
        return Err(CommittedTickWriteErrorV1::Conflict {
            component: CommittedTickConflictComponentV1::EnvelopeDigest,
        });
    }
    for batch in expected.batches() {
        compare_batch(client, batch)?;
    }
    Ok(StoredPresence::Exact)
}

fn reject_rows_without_marker<ClientType: GenericClient>(
    client: &mut ClientType,
    expected: &CommittedTickStorageEnvelopeV1<'_>,
) -> Result<(), CommittedTickWriteErrorV1> {
    let marker = expected.marker();
    let campaign_text = marker.campaign_id().as_uuid().to_string();
    for batch in expected.batches() {
        let operation = CommittedTickDatabaseOperationV1::ReadRows {
            family: batch.target().family(),
        };
        let sql = format!(
            "SELECT 1 FROM {} WHERE campaign_id = $1::text::uuid AND resolve_tick = $2 LIMIT 1",
            batch.target().table().qualified_name()
        );
        if client
            .query_opt(&sql, &[&campaign_text, &marker.resolve_tick()])
            .map_err(|error| database_error(operation, &error))?
            .is_some()
        {
            return Err(CommittedTickWriteErrorV1::RowsWithoutMarker {
                family: batch.target().family(),
            });
        }
    }
    Ok(())
}

fn compare_batch<ClientType: GenericClient>(
    client: &mut ClientType,
    expected: &crate::committed_tick_storage::CommittedTickStorageBatchV1<'_>,
) -> Result<(), CommittedTickWriteErrorV1> {
    let family = expected.target().family();
    let operation = CommittedTickDatabaseOperationV1::ReadRows { family };
    let campaign_text = expected.campaign_id().as_uuid().to_string();
    let (stored_rows, stored_body_bytes) = read_stored_batch_shape(
        client,
        expected.target().table().qualified_name(),
        &campaign_text,
        expected.resolve_tick(),
        operation,
    )?;
    if stored_rows > MAX_COMMITTED_TICK_ROWS_V1 {
        return Err(CommittedTickWriteErrorV1::Bounds {
            resource: family.name(),
            actual: stored_rows,
            maximum: MAX_COMMITTED_TICK_ROWS_V1,
        });
    }
    if stored_body_bytes > MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1 {
        return Err(CommittedTickWriteErrorV1::Bounds {
            resource: family.name(),
            actual: stored_body_bytes,
            maximum: MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1,
        });
    }
    if stored_rows != expected.row_count() {
        return Err(CommittedTickWriteErrorV1::Conflict {
            component: CommittedTickConflictComponentV1::RowFamily(family),
        });
    }
    let limit = i64::try_from(stored_rows).expect("stored row ceiling fits PostgreSQL BIGINT");
    let sql = format!(
        "SELECT row_ordinal, row_key, row_payload FROM {} \
         WHERE campaign_id = $1::text::uuid AND resolve_tick = $2 \
         ORDER BY row_ordinal LIMIT $3",
        expected.target().table().qualified_name()
    );
    let rows = client
        .query(&sql, &[&campaign_text, &expected.resolve_tick(), &limit])
        .map_err(|error| database_error(operation, &error))?;
    if rows.len() != expected.row_count() {
        return Err(CommittedTickWriteErrorV1::Conflict {
            component: CommittedTickConflictComponentV1::RowFamily(family),
        });
    }
    for (index, row) in rows.iter().enumerate() {
        let ordinal: i32 = decode(row, 0, operation)?;
        let key: Vec<u8> = decode(row, 1, operation)?;
        let payload: Vec<u8> = decode(row, 2, operation)?;
        let wanted = expected
            .storage_row(index)
            .ok_or(CommittedTickWriteErrorV1::Conflict {
                component: CommittedTickConflictComponentV1::RowFamily(family),
            })?;
        if ordinal != wanted.row_ordinal()
            || key.as_slice() != wanted.key()
            || payload.as_slice() != wanted.payload()
        {
            return Err(CommittedTickWriteErrorV1::Conflict {
                component: CommittedTickConflictComponentV1::RowFamily(family),
            });
        }
    }
    Ok(())
}

fn read_stored_batch_shape<ClientType: GenericClient>(
    client: &mut ClientType,
    qualified_table: &str,
    campaign_text: &str,
    resolve_tick: i64,
    operation: CommittedTickDatabaseOperationV1,
) -> Result<(usize, usize), CommittedTickWriteErrorV1> {
    let limit =
        i64::try_from(MAX_COMMITTED_TICK_ROWS_V1 + 1).expect("row ceiling fits PostgreSQL BIGINT");
    let sql = format!(
        "SELECT pg_catalog.count(*), \
                COALESCE(pg_catalog.sum(8::bigint \
                    + pg_catalog.octet_length(row_key)::bigint \
                    + pg_catalog.octet_length(row_payload)::bigint), 0::numeric)::text \
         FROM (SELECT row_key, row_payload FROM {qualified_table} \
               WHERE campaign_id = $1::text::uuid AND resolve_tick = $2 \
               ORDER BY row_ordinal LIMIT $3) AS bounded_rows"
    );
    let row = client
        .query_one(&sql, &[&campaign_text, &resolve_tick, &limit])
        .map_err(|error| database_error(operation, &error))?;
    let row_count: i64 = decode(&row, 0, operation)?;
    let body_bytes_text: String = decode(&row, 1, operation)?;
    let row_count =
        usize::try_from(row_count).map_err(|_| CommittedTickWriteErrorV1::Decode { operation })?;
    let body_bytes = body_bytes_text
        .parse::<usize>()
        .map_err(|_| CommittedTickWriteErrorV1::Decode { operation })?;
    Ok((row_count, body_bytes))
}

fn require_next_tick(
    transaction: &mut Transaction<'_>,
    storage: &CommittedTickStorageEnvelopeV1<'_>,
) -> Result<(), CommittedTickWriteErrorV1> {
    let operation = CommittedTickDatabaseOperationV1::ReadLastMarker;
    let marker = storage.marker();
    let campaign_text = marker.campaign_id().as_uuid().to_string();
    let row = transaction
        .query_opt(READ_LAST_TICK_SQL, &[&campaign_text])
        .map_err(|error| database_error(operation, &error))?;
    let last = row
        .as_ref()
        .map(|row| decode::<i64>(row, 0, operation))
        .transpose()?
        .map(|value| {
            u64::try_from(value).map_err(|_| CommittedTickWriteErrorV1::Decode { operation })
        })
        .transpose()?;
    let requested = u64::try_from(marker.resolve_tick())
        .expect("storage mapping checked non-negative u64 tick");
    let valid = match last {
        None => requested == 0,
        Some(previous) => previous.checked_add(1) == Some(requested),
    };
    if valid {
        Ok(())
    } else {
        Err(CommittedTickWriteErrorV1::TickSequence {
            last_committed: last,
            requested,
        })
    }
}

fn insert_batch(
    transaction: &mut Transaction<'_>,
    batch: &crate::committed_tick_storage::CommittedTickStorageBatchV1<'_>,
) -> Result<(), CommittedTickWriteErrorV1> {
    let family = batch.target().family();
    let operation = CommittedTickDatabaseOperationV1::InsertRows { family };
    let sql = format!(
        "COPY {} (campaign_id, resolve_tick, row_ordinal, row_key, row_payload) \
         FROM STDIN BINARY",
        batch.target().table().qualified_name()
    );
    let copy = transaction
        .copy_in(&sql)
        .map_err(|error| database_error(operation, &error))?;
    let mut copy = BinaryCopyInWriter::new(
        copy,
        &[Type::UUID, Type::INT8, Type::INT4, Type::BYTEA, Type::BYTEA],
    );
    for index in 0..batch.row_count() {
        let row = batch
            .storage_row(index)
            .expect("checked storage batch owns every bounded ordinal");
        copy.write(&[
            batch.campaign_id().as_uuid(),
            &row.resolve_tick(),
            &row.row_ordinal(),
            &row.key(),
            &row.payload(),
        ])
        .map_err(|error| database_error(operation, &error))?;
    }
    let inserted = copy
        .finish()
        .map_err(|error| database_error(operation, &error))?;
    if usize::try_from(inserted).ok() != Some(batch.row_count()) {
        return Err(CommittedTickWriteErrorV1::Decode { operation });
    }
    Ok(())
}

fn insert_marker(
    transaction: &mut Transaction<'_>,
    storage: &CommittedTickStorageEnvelopeV1<'_>,
) -> Result<(), CommittedTickWriteErrorV1> {
    let operation = CommittedTickDatabaseOperationV1::InsertMarker;
    let marker = storage.marker();
    let campaign_text = marker.campaign_id().as_uuid().to_string();
    let tick_content_hash = marker.tick_content_hash();
    let envelope_digest = marker.envelope_digest();
    transaction
        .execute(
            INSERT_MARKER_SQL,
            &[
                &campaign_text,
                &marker.resolve_tick(),
                &marker.envelope_layout_version(),
                &tick_content_hash.as_bytes().as_slice(),
                &envelope_digest.as_bytes().as_slice(),
            ],
        )
        .map_err(|error| database_error(operation, &error))?;
    Ok(())
}

fn hydrate_under_lock(
    client: &mut Client,
    campaign_id: CampaignId,
    max_replay_ticks: usize,
) -> Result<Option<CommittedTickHydrationV1>, CommittedTickWriteErrorV1> {
    require_exact_schema_epoch(client)?;
    prepare_session(client)?;
    let Some(campaign) = read_hydrated_campaign(client, campaign_id)? else {
        return Ok(None);
    };
    let campaign_text = campaign_id.as_uuid().to_string();
    let operation = CommittedTickDatabaseOperationV1::ReadLastMarker;
    let Some(last_row) = client
        .query_opt(READ_LAST_MARKER_SQL, &[&campaign_text])
        .map_err(|error| database_error(operation, &error))?
    else {
        return Ok(None);
    };
    let last_marker = decode_hydrated_marker(&last_row, operation)?;
    let last_tick_i64 = i64::try_from(last_marker.resolve_tick)
        .map_err(|_| CommittedTickWriteErrorV1::Decode { operation })?;
    let checkpoint_marker = client
        .query_opt(READ_FOUNDATION_CHECKPOINT_SQL, &[&campaign_text])
        .map_err(|error| database_error(CommittedTickDatabaseOperationV1::ReadCheckpoint, &error))?
        .map(|row| decode_hydrated_marker(&row, CommittedTickDatabaseOperationV1::ReadCheckpoint))
        .transpose()?;
    let checkpoint_tick = checkpoint_marker.map(CommittedTickHydratedMarkerV1::resolve_tick);
    let checkpoint_rows = checkpoint_tick.map_or_else(
        || Ok(Vec::new()),
        |tick| read_checkpoint_rows(client, campaign_id, tick),
    )?;
    let after_tick = checkpoint_tick.map_or(-1_i64, |tick| {
        i64::try_from(tick).expect("stored checkpoint tick originated as non-negative i64")
    });
    let query_limit =
        i64::try_from(max_replay_ticks + 1).map_err(|_| CommittedTickWriteErrorV1::Bounds {
            resource: "checkpoint replay tail",
            actual: max_replay_ticks,
            maximum: MAX_COMMITTED_TICK_HYDRATION_TAIL_V1,
        })?;
    let tail_rows = client
        .query(
            READ_REPLAY_TAIL_SQL,
            &[&campaign_text, &after_tick, &last_tick_i64, &query_limit],
        )
        .map_err(|error| {
            database_error(CommittedTickDatabaseOperationV1::ReadReplayTail, &error)
        })?;
    if tail_rows.len() > max_replay_ticks {
        return Err(CommittedTickWriteErrorV1::Bounds {
            resource: "checkpoint replay tail",
            actual: tail_rows.len(),
            maximum: max_replay_ticks,
        });
    }
    let replay_markers = tail_rows
        .iter()
        .map(|row| decode_hydrated_marker(row, CommittedTickDatabaseOperationV1::ReadReplayTail))
        .collect::<Result<Vec<_>, _>>()?;
    let replay_tail = replay_markers
        .iter()
        .map(|marker| marker.resolve_tick)
        .collect::<Vec<_>>();
    let plan = CommittedTickHydrationPlanV1::compose(
        last_marker.resolve_tick,
        checkpoint_tick,
        checkpoint_rows,
        replay_tail,
    )?;
    Ok(Some(CommittedTickHydrationV1 {
        campaign,
        plan,
        checkpoint_marker,
        replay_markers: replay_markers.into_boxed_slice(),
    }))
}

fn read_hydrated_campaign(
    client: &mut Client,
    campaign_id: CampaignId,
) -> Result<Option<CommittedTickHydratedCampaignV1>, CommittedTickWriteErrorV1> {
    let operation = CommittedTickDatabaseOperationV1::ReadCampaign;
    let campaign_text = campaign_id.as_uuid().to_string();
    let rows = client
        .query(READ_CAMPAIGN_SQL, &[&campaign_text])
        .map_err(|error| database_error(operation, &error))?;
    if rows.is_empty() {
        return Ok(None);
    }
    if rows.len() != 1 {
        return Err(CommittedTickWriteErrorV1::Decode { operation });
    }
    let replay_layout: i16 = decode(&rows[0], 0, operation)?;
    let rng_layout: i16 = decode(&rows[0], 1, operation)?;
    if replay_layout != 1 || rng_layout != 2 {
        return Err(CommittedTickWriteErrorV1::Decode { operation });
    }
    let replay_session: String = decode(&rows[0], 2, operation)?;
    let replay_session_id = ReplaySessionIdV1::try_from(replay_session.as_str())
        .map_err(|_| CommittedTickWriteErrorV1::Decode { operation })?;
    let rng_seed: i64 = decode(&rows[0], 3, operation)?;
    let defines_hash = decode_digest(&rows[0], 4, operation)?;
    let rules_hash = decode_digest(&rows[0], 5, operation)?;
    let ref_digest = decode_digest(&rows[0], 6, operation)?;
    Ok(Some(CommittedTickHydratedCampaignV1 {
        campaign_id,
        replay_session_id,
        rng_seed: ReplaySeed::new(rng_seed),
        content: ContentDigest {
            defines_hash,
            rules_hash,
        },
        reference: RefDigestV1::from_bytes(ref_digest),
    }))
}

fn read_checkpoint_rows(
    client: &mut Client,
    campaign_id: CampaignId,
    tick: u64,
) -> Result<Vec<CommittedTickHydratedRowV1>, CommittedTickWriteErrorV1> {
    let operation = CommittedTickDatabaseOperationV1::ReadCheckpoint;
    let campaign_text = campaign_id.as_uuid().to_string();
    let tick = i64::try_from(tick).map_err(|_| CommittedTickWriteErrorV1::Decode { operation })?;
    let (stored_rows, stored_body_bytes) = read_stored_batch_shape(
        client,
        "babylon_state.tick_checkpoint_row",
        &campaign_text,
        tick,
        operation,
    )?;
    if stored_rows > MAX_COMMITTED_TICK_ROWS_V1 {
        return Err(CommittedTickWriteErrorV1::Bounds {
            resource: "checkpoint rows",
            actual: stored_rows,
            maximum: MAX_COMMITTED_TICK_ROWS_V1,
        });
    }
    if stored_body_bytes > MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1 {
        return Err(CommittedTickWriteErrorV1::Bounds {
            resource: "checkpoint bytes",
            actual: stored_body_bytes,
            maximum: MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1,
        });
    }
    let limit = i64::try_from(stored_rows).expect("stored row ceiling fits PostgreSQL BIGINT");
    let rows = client
        .query(
            "SELECT row_ordinal, row_key, row_payload \
             FROM babylon_state.tick_checkpoint_row \
             WHERE campaign_id = $1::text::uuid AND resolve_tick = $2 \
             ORDER BY row_ordinal LIMIT $3",
            &[&campaign_text, &tick, &limit],
        )
        .map_err(|error| database_error(operation, &error))?;
    if rows.len() != stored_rows {
        return Err(CommittedTickWriteErrorV1::Decode { operation });
    }
    rows.iter()
        .enumerate()
        .map(|(index, row)| {
            let ordinal: i32 = decode(row, 0, operation)?;
            if usize::try_from(ordinal).ok() != Some(index) {
                return Err(CommittedTickWriteErrorV1::Decode { operation });
            }
            let key: Vec<u8> = decode(row, 1, operation)?;
            let payload: Vec<u8> = decode(row, 2, operation)?;
            CommittedTickHydratedRowV1::new(key, payload)
        })
        .collect()
}

fn decode_hydrated_marker(
    row: &Row,
    operation: CommittedTickDatabaseOperationV1,
) -> Result<CommittedTickHydratedMarkerV1, CommittedTickWriteErrorV1> {
    let resolve_tick: i64 = decode(row, 0, operation)?;
    Ok(CommittedTickHydratedMarkerV1 {
        resolve_tick: u64::try_from(resolve_tick)
            .map_err(|_| CommittedTickWriteErrorV1::Decode { operation })?,
        tick_content_hash: TickContentHashV1::from_bytes(decode_digest(row, 1, operation)?),
        envelope_digest: decode_digest(row, 2, operation)?,
    })
}

fn validate_hydration_shape(
    last_committed_tick: u64,
    checkpoint_tick: Option<u64>,
    checkpoint_rows: &[CommittedTickHydratedRowV1],
    replay_tail: &[u64],
) -> Result<(), CommittedTickWriteErrorV1> {
    if replay_tail.len() > MAX_COMMITTED_TICK_HYDRATION_TAIL_V1 {
        return Err(CommittedTickWriteErrorV1::Bounds {
            resource: "checkpoint replay tail",
            actual: replay_tail.len(),
            maximum: MAX_COMMITTED_TICK_HYDRATION_TAIL_V1,
        });
    }
    if checkpoint_tick.is_some() == checkpoint_rows.is_empty()
        || checkpoint_tick.is_some_and(|tick| tick > last_committed_tick)
    {
        return Err(CommittedTickWriteErrorV1::Decode {
            operation: CommittedTickDatabaseOperationV1::ReadCheckpoint,
        });
    }
    for pair in checkpoint_rows.windows(2) {
        if pair[0].key() >= pair[1].key() {
            return Err(CommittedTickWriteErrorV1::Decode {
                operation: CommittedTickDatabaseOperationV1::ReadCheckpoint,
            });
        }
    }
    let expected_first = checkpoint_tick.map_or(0, |tick| tick.saturating_add(1));
    let empty_tail_is_complete =
        replay_tail.is_empty() && checkpoint_tick == Some(last_committed_tick);
    let nonempty_tail_is_complete = replay_tail.first().copied() == Some(expected_first)
        && replay_tail.last().copied() == Some(last_committed_tick)
        && !replay_tail
            .windows(2)
            .any(|pair| pair[0].checked_add(1) != Some(pair[1]));
    if !empty_tail_is_complete && !nonempty_tail_is_complete {
        return Err(CommittedTickWriteErrorV1::Decode {
            operation: CommittedTickDatabaseOperationV1::ReadReplayTail,
        });
    }
    Ok(())
}

fn rollback(transaction: Transaction<'_>) -> Result<(), CommittedTickWriteErrorV1> {
    transaction.rollback().map_err(|error| {
        database_error(
            CommittedTickDatabaseOperationV1::RollbackTransaction,
            &error,
        )
    })
}

fn rollback_preserving<T>(
    transaction: Transaction<'_>,
    primary: CommittedTickWriteErrorV1,
) -> Result<T, CommittedTickWriteErrorV1> {
    match rollback(transaction) {
        Ok(()) => Err(primary),
        Err(rollback) => Err(CommittedTickWriteErrorV1::FailureAndRollback {
            primary: Box::new(primary),
            rollback: Box::new(rollback),
        }),
    }
}

fn postgres_error_is_connection_loss(error: &postgres::Error) -> bool {
    error
        .as_db_error()
        .is_none_or(|server| sqlstate_is_connection_loss(server.code().code()))
}

fn sqlstate_is_connection_loss(code: &str) -> bool {
    code.starts_with("08") || matches!(code, "57P01" | "57P02" | "57P03")
}

fn is_connection_loss_transaction_failure(error: &CommittedTickWriteErrorV1) -> bool {
    match error {
        CommittedTickWriteErrorV1::Database { diagnostic, .. } => diagnostic
            .server()
            .is_none_or(|server| sqlstate_is_connection_loss(server.code().code())),
        CommittedTickWriteErrorV1::FailureAndRollback { primary, .. } => {
            is_connection_loss_transaction_failure(primary)
        }
        _ => false,
    }
}

fn decode<T: postgres::types::FromSqlOwned>(
    row: &Row,
    index: usize,
    operation: CommittedTickDatabaseOperationV1,
) -> Result<T, CommittedTickWriteErrorV1> {
    row.try_get(index)
        .map_err(|_| CommittedTickWriteErrorV1::Decode { operation })
}

fn decode_digest(
    row: &Row,
    index: usize,
    operation: CommittedTickDatabaseOperationV1,
) -> Result<[u8; 32], CommittedTickWriteErrorV1> {
    let bytes: Vec<u8> = decode(row, index, operation)?;
    bytes
        .try_into()
        .map_err(|_| CommittedTickWriteErrorV1::Decode { operation })
}

fn database_error(
    operation: CommittedTickDatabaseOperationV1,
    error: &postgres::Error,
) -> CommittedTickWriteErrorV1 {
    CommittedTickWriteErrorV1::Database {
        operation,
        diagnostic: CommittedTickDatabaseDiagnosticV1 {
            server: error.as_db_error().cloned().map(Box::new),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::str::FromStr as _;
    use std::time::{SystemTime, UNIX_EPOCH};

    use crate::committed_tick_envelope::{CommittedTickRowFamiliesV1, CommittedTickRowV1};
    use crate::schema_epoch::migrate_schema_epoch;
    use crate::tick_commit_claim::TickCommitClaimV1;
    use uuid::Uuid;

    fn row(key: u8, payload: u8) -> CommittedTickHydratedRowV1 {
        CommittedTickHydratedRowV1::new(vec![key], vec![payload]).expect("valid row")
    }

    #[test]
    fn hydration_shape_refuses_gaps_and_noncanonical_rows() {
        assert!(
            CommittedTickHydrationPlanV1::compose(12, Some(10), vec![row(1, 1)], vec![12]).is_err()
        );
        assert!(CommittedTickHydrationPlanV1::compose(
            12,
            Some(10),
            vec![row(2, 1), row(1, 2)],
            vec![11, 12],
        )
        .is_err());
        assert!(CommittedTickHydrationPlanV1::compose(0, None, Vec::new(), vec![0]).is_ok());
    }

    #[test]
    fn hydration_shape_accepts_checkpoint_at_last_marker_without_a_tail() {
        let plan = CommittedTickHydrationPlanV1::compose(12, Some(12), vec![row(1, 1)], Vec::new())
            .expect("checkpoint at last marker needs no replay");
        assert!(plan.replay_tail().is_empty());
    }

    #[test]
    fn commit_driver_acknowledges_only_direct_or_exactly_reconciled_outcomes() {
        let mut direct = ScriptedCommitDriver::new(
            [CommitAttempt::Committed, CommitAttempt::Committed],
            [StoredPresence::Absent, StoredPresence::Absent],
        );
        assert_eq!(
            drive_commit(StoredPresence::Absent, &mut direct).expect("direct commit"),
            CommitResolution {
                disposition: CommittedTickCommitDispositionV1::Committed,
                commit_attempts: 1,
            }
        );

        let mut reconciled = ScriptedCommitDriver::new(
            [CommitAttempt::AmbiguousCommit, CommitAttempt::Committed],
            [StoredPresence::Exact, StoredPresence::Absent],
        );
        assert_eq!(
            drive_commit(StoredPresence::Absent, &mut reconciled)
                .expect("exact ambiguity reconciliation"),
            CommitResolution {
                disposition: CommittedTickCommitDispositionV1::ReconciledAfterAmbiguousCommit,
                commit_attempts: 1,
            }
        );
    }

    #[test]
    fn connection_retry_before_commit_does_not_count_as_a_commit_attempt() {
        let mut retried = ScriptedCommitDriver::new(
            [
                CommitAttempt::AmbiguousBeforeCommit,
                CommitAttempt::Committed,
            ],
            [StoredPresence::Absent, StoredPresence::Absent],
        );
        assert_eq!(
            drive_commit(StoredPresence::Absent, &mut retried)
                .expect("pre-commit connection retry then direct commit"),
            CommitResolution {
                disposition: CommittedTickCommitDispositionV1::Committed,
                commit_attempts: 1,
            }
        );
    }

    #[test]
    fn commit_driver_bounds_two_ambiguous_absent_attempts_without_acknowledgement() {
        let mut unresolved = ScriptedCommitDriver::new(
            [
                CommitAttempt::AmbiguousCommit,
                CommitAttempt::AmbiguousCommit,
            ],
            [StoredPresence::Absent, StoredPresence::Absent],
        );
        assert!(matches!(
            drive_commit(StoredPresence::Absent, &mut unresolved),
            Err(CommittedTickWriteErrorV1::AmbiguousCommitUnresolved { attempts: 2 })
        ));
        assert_eq!(unresolved.attempt_index, 2);
        assert_eq!(unresolved.reconciliation_index, 2);
    }

    #[test]
    fn connection_loss_failures_require_ambiguity_reconciliation() {
        assert!(sqlstate_is_connection_loss("08006"));
        assert!(sqlstate_is_connection_loss("57P01"));
        assert!(!sqlstate_is_connection_loss("23505"));

        let transport = CommittedTickWriteErrorV1::Database {
            operation: CommittedTickDatabaseOperationV1::InsertMarker,
            diagnostic: CommittedTickDatabaseDiagnosticV1 { server: None },
        };
        assert!(is_connection_loss_transaction_failure(&transport));

        let wrapped = CommittedTickWriteErrorV1::FailureAndRollback {
            primary: Box::new(transport),
            rollback: Box::new(CommittedTickWriteErrorV1::Database {
                operation: CommittedTickDatabaseOperationV1::RollbackTransaction,
                diagnostic: CommittedTickDatabaseDiagnosticV1 { server: None },
            }),
        };
        assert!(is_connection_loss_transaction_failure(&wrapped));

        assert!(!is_connection_loss_transaction_failure(
            &CommittedTickWriteErrorV1::TickSequence {
                last_committed: Some(3),
                requested: 5,
            }
        ));
    }

    #[test]
    #[ignore = "requires the owned disposable PER-20 PostgreSQL harness"]
    fn live_marker_last_commit_retry_conflict_and_hydration_are_atomic() {
        require_owned_disposable_harness();
        let base = Config::from_str(
            &std::env::var("BABYLON_LEGACY_ADOPTER_TEST_DSN").expect("owned harness DSN"),
        )
        .expect("valid owned harness DSN");
        let scratch = WriterScratchDatabase::create(&base);
        migrate_schema_epoch(&scratch.config).expect("fresh exact Rust schema epoch");
        install_writer_reference_fixture(&scratch.config);

        let campaign_id =
            CampaignId::from_uuid(Uuid::from_u128(0x0011_2233_4455_6677_8899_aabb_ccdd_eeff));
        let replay_session_id =
            ReplaySessionIdV1::try_from("per20-writer-live").expect("valid replay session");
        let content = ContentDigest {
            defines_hash: [0x31; 32],
            rules_hash: [0x42; 32],
        };
        let reference = RefDigestV1::from_bytes([0x53; 32]);
        let campaign = CampaignStorageRowV1::new(
            campaign_id,
            &replay_session_id,
            ReplaySeed::new(-54),
            &content,
            reference,
        );
        let tick_zero = live_envelope(campaign_id, 0, 0x10, 0xa0, true);
        let storage_zero =
            CommittedTickStorageEnvelopeV1::try_from(&tick_zero).expect("mapped tick zero");

        prove_marker_last_visibility_and_rollback(&scratch.config, campaign, &storage_zero);

        let retry =
            commit_through_test_seam(&scratch.config, campaign, &tick_zero).expect("exact retry");
        assert_eq!(
            retry.disposition(),
            CommittedTickCommitDispositionV1::AlreadyCommitted
        );
        assert_eq!(retry.commit_attempts(), 0);

        let checkpoint_marker =
            assert_checkpoint_only_hydration(&scratch.config, campaign_id, &tick_zero);

        let payload_conflict = live_envelope(campaign_id, 0, 0x10, 0xff, true);
        assert!(matches!(
            commit_through_test_seam(&scratch.config, campaign, &payload_conflict),
            Err(CommittedTickWriteErrorV1::Conflict {
                component: CommittedTickConflictComponentV1::EnvelopeDigest,
            })
        ));

        // A later checkpoint row is an opaque delta, not a proven restoration base.
        let tick_one = live_envelope(campaign_id, 1, 0x11, 0xa1, true);
        let tick_two = live_envelope(campaign_id, 2, 0x12, 0xa2, false);
        for (expected_tick, envelope) in [(1_u64, &tick_one), (2_u64, &tick_two)] {
            let report = commit_through_test_seam(&scratch.config, campaign, envelope)
                .expect("next marker commits");
            assert_eq!(
                report.disposition(),
                CommittedTickCommitDispositionV1::Committed
            );
            assert_eq!(report.resolve_tick(), expected_tick);
        }

        let hydrated = hydrate_committed_tick_checkpoint_v1(&scratch.config, campaign_id, 2)
            .expect("bounded hydration")
            .expect("committed campaign");
        assert_eq!(hydrated.campaign().replay_session_id(), &replay_session_id);
        assert_eq!(hydrated.campaign().rng_seed(), ReplaySeed::new(-54));
        assert_eq!(hydrated.campaign().reference(), reference);
        assert_eq!(hydrated.plan().checkpoint_tick(), Some(0));
        assert_eq!(hydrated.plan().last_committed_tick(), 2);
        assert_eq!(hydrated.plan().replay_tail(), &[1, 2]);
        assert_eq!(hydrated.checkpoint_marker(), Some(checkpoint_marker));
        assert_eq!(
            hydrated
                .replay_markers()
                .iter()
                .map(|marker| marker.resolve_tick())
                .collect::<Vec<_>>(),
            vec![1, 2]
        );

        remove_last_committed_tick(&scratch.config, campaign_id, 2);
        let recovered = hydrate_committed_tick_checkpoint_v1(&scratch.config, campaign_id, 1)
            .expect("lost-tail hydration")
            .expect("surviving campaign");
        assert_eq!(recovered.plan().last_committed_tick(), 1);
        assert_eq!(recovered.plan().checkpoint_tick(), Some(0));
        assert_eq!(recovered.plan().replay_tail(), &[1]);

        prove_failed_commit_is_unacknowledged_and_rolls_back(
            &scratch.config,
            &replay_session_id,
            &content,
        );

        let unavailable = Config::from_str(&format!(
            "postgresql://test:test@127.0.0.1:1/{}",
            scratch.name
        ))
        .expect("single unavailable loopback target");
        assert!(matches!(
            hydrate_committed_tick_checkpoint_v1(&unavailable, campaign_id, 1),
            Err(CommittedTickWriteErrorV1::Database {
                operation: CommittedTickDatabaseOperationV1::Connect,
                ..
            })
        ));
    }

    #[test]
    #[ignore = "requires the owned disposable PER-20 PostgreSQL harness"]
    fn live_crash_boundary_matrix_is_atomic_and_retryable() {
        require_owned_disposable_harness();
        let base = Config::from_str(
            &std::env::var("BABYLON_LEGACY_ADOPTER_TEST_DSN").expect("owned harness DSN"),
        )
        .expect("valid owned harness DSN");
        let scratch = WriterScratchDatabase::create(&base);
        migrate_schema_epoch(&scratch.config).expect("fresh exact Rust schema epoch");
        install_writer_reference_fixture(&scratch.config);

        for (index, boundary) in committed_tick_crash_boundaries_v1().into_iter().enumerate() {
            prove_crash_boundary_is_atomic(&scratch, index, boundary);
        }
    }

    fn committed_tick_crash_boundaries_v1() -> Vec<CommitTransactionBoundaryV1> {
        let mut steps = vec![
            CommitTransactionStepV1::Begin,
            CommitTransactionStepV1::PrepareTransaction,
            CommitTransactionStepV1::EnsureCampaign,
            CommitTransactionStepV1::LockCampaign,
            CommitTransactionStepV1::InspectPresence,
            CommitTransactionStepV1::RequireNextTick,
        ];
        steps.extend(
            crate::committed_tick_envelope::ALL_COMMITTED_TICK_ROW_FAMILIES_V1
                .map(|family| CommitTransactionStepV1::InsertRows { family }),
        );
        steps.extend([
            CommitTransactionStepV1::InsertMarker,
            CommitTransactionStepV1::Commit,
        ]);

        let mut boundaries = Vec::with_capacity(steps.len() * 2);
        for step in steps {
            boundaries.push(CommitTransactionBoundaryV1::before(step));
            boundaries.push(CommitTransactionBoundaryV1::after(step));
        }
        assert_eq!(boundaries.len(), 32, "V1 crash matrix must stay exhaustive");
        boundaries
    }

    fn prove_crash_boundary_is_atomic(
        scratch: &WriterScratchDatabase,
        index: usize,
        boundary: CommitTransactionBoundaryV1,
    ) {
        let campaign_id = CampaignId::from_uuid(Uuid::from_u128(
            0x3011_2233_4455_6677_8899_aabb_ccdd_0000
                + u128::try_from(index).expect("bounded crash-matrix index"),
        ));
        let replay_session = ReplaySessionIdV1::try_from(format!("per20-crash-{index}").as_str())
            .expect("valid crash-matrix replay session");
        let content = ContentDigest {
            defines_hash: [0x71; 32],
            rules_hash: [0x82; 32],
        };
        let campaign = CampaignStorageRowV1::new(
            campaign_id,
            &replay_session,
            ReplaySeed::new(-72),
            &content,
            RefDigestV1::from_bytes([0x53; 32]),
        );
        let index_byte = u8::try_from(index).expect("V1 crash matrix fits one byte");
        let envelope = live_envelope(
            campaign_id,
            0,
            0x60_u8.wrapping_add(index_byte),
            0xd0_u8.wrapping_add(index_byte),
            true,
        );
        let storage =
            CommittedTickStorageEnvelopeV1::try_from(&envelope).expect("mapped crash envelope");

        let proof = commit_through_crash_boundary_test_seam(
            &scratch.config,
            &scratch.base,
            campaign,
            &envelope,
            boundary,
        )
        .unwrap_or_else(|error| panic!("crash boundary {boundary:?} failed: {error:?}"));
        let committed_response_lost =
            boundary == CommitTransactionBoundaryV1::after(CommitTransactionStepV1::Commit);
        let first_transaction_attempted_commit = matches!(
            boundary,
            CommitTransactionBoundaryV1 {
                step: CommitTransactionStepV1::InsertMarker,
                side: CommitBoundarySideV1::After,
            } | CommitTransactionBoundaryV1 {
                step: CommitTransactionStepV1::Commit,
                ..
            }
        );
        assert_eq!(
            proof.observed_after_crash,
            if committed_response_lost {
                StoredPresence::Exact
            } else {
                StoredPresence::Absent
            },
            "unexpected restart state after {boundary:?}"
        );
        assert_eq!(proof.campaign_present_after_crash, committed_response_lost);
        assert_eq!(
            proof.report.disposition(),
            if committed_response_lost {
                CommittedTickCommitDispositionV1::ReconciledAfterAmbiguousCommit
            } else {
                CommittedTickCommitDispositionV1::Committed
            }
        );
        assert_eq!(
            proof.report.commit_attempts(),
            if committed_response_lost || !first_transaction_attempted_commit {
                1
            } else {
                2
            }
        );

        let mut verifier = scratch.config.connect(NoTls).expect("matrix verifier");
        assert_eq!(
            inspect_campaign(&mut verifier, campaign).unwrap(),
            Some(true)
        );
        assert_eq!(
            inspect_presence(&mut verifier, &storage).unwrap(),
            StoredPresence::Exact
        );
    }

    struct CrashBoundaryProofV1 {
        report: CommittedTickCommitReportV1,
        observed_after_crash: StoredPresence,
        campaign_present_after_crash: bool,
    }

    fn commit_through_crash_boundary_test_seam(
        config: &Config,
        admin: &Config,
        campaign: CampaignStorageRowV1<'_>,
        envelope: &CommittedTickEnvelopeV1,
        target: CommitTransactionBoundaryV1,
    ) -> Result<CrashBoundaryProofV1, CommittedTickWriteErrorV1> {
        validate_legacy_connection_target(config)
            .map_err(CommittedTickWriteErrorV1::ConnectionTarget)?;
        let storage = CommittedTickStorageEnvelopeV1::try_from(envelope)
            .map_err(CommittedTickWriteErrorV1::StorageMapping)?;
        let bounded = bounded_config(config);
        let mut session = LockedCommittedTickSession::connect(&bounded)?;
        require_exact_schema_epoch(session.client())?;
        prepare_session(session.client())?;
        let initial = match inspect_campaign(session.client(), campaign)? {
            Some(false) => {
                return Err(CommittedTickWriteErrorV1::Conflict {
                    component: CommittedTickConflictComponentV1::CampaignIdentity,
                });
            }
            Some(true) => inspect_presence(session.client(), &storage)?,
            None => StoredPresence::Absent,
        };
        let (resolution, injected, observed_after_crash, campaign_present_after_crash) = {
            let mut driver = CrashBoundaryCommitDriver {
                admin,
                config: &bounded,
                session: &mut session,
                campaign,
                storage: &storage,
                target,
                injected: false,
                observed_after_crash: None,
                campaign_present_after_crash: None,
            };
            let resolution = drive_commit(initial, &mut driver);
            (
                resolution,
                driver.injected,
                driver.observed_after_crash,
                driver.campaign_present_after_crash,
            )
        };
        let result = resolution.map(|resolution| {
            assert!(
                injected,
                "target crash boundary was not reached: {target:?}"
            );
            CrashBoundaryProofV1 {
                report: CommittedTickCommitReportV1 {
                    disposition: resolution.disposition,
                    resolve_tick: u64::try_from(storage.marker().resolve_tick())
                        .expect("storage mapping checked non-negative u64 tick"),
                    commit_attempts: resolution.commit_attempts,
                },
                observed_after_crash: observed_after_crash
                    .expect("injected ambiguity must be reconciled"),
                campaign_present_after_crash: campaign_present_after_crash
                    .expect("injected ambiguity must observe campaign presence"),
            }
        });
        session.finish(result)
    }

    fn assert_checkpoint_only_hydration(
        config: &Config,
        campaign_id: CampaignId,
        envelope: &CommittedTickEnvelopeV1,
    ) -> CommittedTickHydratedMarkerV1 {
        let hydration = hydrate_committed_tick_checkpoint_v1(config, campaign_id, 0)
            .expect("checkpoint-only hydration")
            .expect("committed campaign");
        assert!(hydration.plan().replay_tail().is_empty());
        let marker = hydration
            .checkpoint_marker()
            .expect("checkpoint identity survives an empty replay tail");
        assert_eq!(marker.resolve_tick(), 0);
        assert_eq!(
            marker.tick_content_hash(),
            TickContentHashV1::from_bytes([0x10; 32])
        );
        assert_eq!(marker.envelope_digest(), *envelope.digest().as_bytes());
        marker
    }

    fn live_envelope(
        campaign_id: CampaignId,
        tick: u64,
        hash_byte: u8,
        payload: u8,
        checkpoint: bool,
    ) -> CommittedTickEnvelopeV1 {
        let canonical_row =
            |key| CommittedTickRowV1::compose(vec![key], vec![payload]).expect("canonical row");
        CommittedTickEnvelopeV1::compose(
            TickCommitClaimV1::compose(
                campaign_id,
                tick,
                TickContentHashV1::from_bytes([hash_byte; 32]),
            ),
            CommittedTickRowFamiliesV1 {
                graph: vec![canonical_row(0x01)],
                state: vec![canonical_row(0x02)],
                event: vec![canonical_row(0x03)],
                subsystem: vec![canonical_row(0x04)],
                conservation: vec![canonical_row(0x05)],
                boundary_flow: vec![canonical_row(0x06)],
                checkpoint: checkpoint
                    .then(|| canonical_row(0x07))
                    .into_iter()
                    .collect(),
                archive_dirty_receipt: vec![canonical_row(0x08)],
            },
        )
        .expect("canonical live envelope")
    }

    fn prove_marker_last_visibility_and_rollback(
        config: &Config,
        campaign: CampaignStorageRowV1<'_>,
        storage: &CommittedTickStorageEnvelopeV1<'_>,
    ) {
        let mut writer = bounded_config(config)
            .connect(NoTls)
            .expect("writer connection");
        let mut observer = config.connect(NoTls).expect("observer connection");
        prepare_session(&mut writer).expect("bounded writer session");
        let mut transaction = writer
            .build_transaction()
            .isolation_level(IsolationLevel::Serializable)
            .read_only(false)
            .start()
            .expect("serializable transaction");
        prepare_transaction(&mut transaction).expect("exact transaction settings");
        ensure_campaign(&mut transaction, campaign).expect("campaign row");
        require_next_tick(&mut transaction, storage).expect("first tick");
        for batch in storage.batches() {
            insert_batch(&mut transaction, batch).expect("family insert");
        }
        assert_tick_visibility(&mut observer, campaign.campaign_id(), 0, 0, 0);
        insert_marker(&mut transaction, storage).expect("marker inserted last");
        assert_tick_visibility(&mut observer, campaign.campaign_id(), 0, 0, 0);
        transaction.commit().expect("marker-last commit");
        assert_tick_visibility(&mut observer, campaign.campaign_id(), 0, 1, 1);

        let rollback_campaign_id =
            CampaignId::from_uuid(Uuid::from_u128(0x1011_2233_4455_6677_8899_aabb_ccdd_eeff));
        let rollback_envelope = live_envelope(rollback_campaign_id, 0, 0x20, 0xb0, true);
        let rollback_storage =
            CommittedTickStorageEnvelopeV1::try_from(&rollback_envelope).expect("rollback storage");
        let rollback_session =
            ReplaySessionIdV1::try_from("per20-writer-rollback").expect("rollback session");
        let rollback_content = ContentDigest {
            defines_hash: [0x31; 32],
            rules_hash: [0x42; 32],
        };
        let rollback_campaign = CampaignStorageRowV1::new(
            rollback_campaign_id,
            &rollback_session,
            ReplaySeed::new(campaign.rng_seed()),
            &rollback_content,
            campaign.reference(),
        );
        let mut transaction = writer
            .build_transaction()
            .isolation_level(IsolationLevel::Serializable)
            .read_only(false)
            .start()
            .expect("rollback transaction");
        prepare_transaction(&mut transaction).expect("rollback settings");
        ensure_campaign(&mut transaction, rollback_campaign).expect("rollback campaign");
        for batch in rollback_storage.batches() {
            insert_batch(&mut transaction, batch).expect("rollback family insert");
        }
        transaction
            .rollback()
            .expect("injected pre-marker rollback");
        assert_tick_visibility(&mut observer, rollback_campaign_id, 0, 0, 0);
    }

    fn assert_tick_visibility(
        client: &mut Client,
        campaign_id: CampaignId,
        tick: i64,
        expected_markers: i64,
        expected_graph_rows: i64,
    ) {
        let campaign_text = campaign_id.as_uuid().to_string();
        let marker_count: i64 = client
            .query_one(
                "SELECT pg_catalog.count(*) FROM babylon_state.tick_commit \
                 WHERE campaign_id = $1::text::uuid AND resolve_tick = $2",
                &[&campaign_text, &tick],
            )
            .expect("marker visibility query")
            .get(0);
        let graph_count: i64 = client
            .query_one(
                "SELECT pg_catalog.count(*) FROM babylon_state.tick_graph_row \
                 WHERE campaign_id = $1::text::uuid AND resolve_tick = $2",
                &[&campaign_text, &tick],
            )
            .expect("graph visibility query")
            .get(0);
        assert_eq!(marker_count, expected_markers);
        assert_eq!(graph_count, expected_graph_rows);
    }

    fn remove_last_committed_tick(config: &Config, campaign_id: CampaignId, tick: i64) {
        let mut client = config.connect(NoTls).expect("lost-tail connection");
        let mut transaction = client.transaction().expect("lost-tail transaction");
        let campaign_text = campaign_id.as_uuid().to_string();
        for target in crate::committed_tick_storage::ALL_COMMITTED_TICK_STORAGE_TARGETS_V1 {
            let sql = format!(
                "DELETE FROM {} WHERE campaign_id = $1::text::uuid AND resolve_tick = $2",
                target.table().qualified_name()
            );
            transaction
                .execute(&sql, &[&campaign_text, &tick])
                .expect("remove lost family rows");
        }
        transaction
            .execute(
                "DELETE FROM babylon_state.tick_commit \
                 WHERE campaign_id = $1::text::uuid AND resolve_tick = $2",
                &[&campaign_text, &tick],
            )
            .expect("remove lost marker");
        transaction.commit().expect("simulate lost tail");
    }

    fn prove_failed_commit_is_unacknowledged_and_rolls_back(
        config: &Config,
        replay_session_id: &ReplaySessionIdV1,
        content: &ContentDigest,
    ) {
        let campaign_id =
            CampaignId::from_uuid(Uuid::from_u128(0x2011_2233_4455_6677_8899_aabb_ccdd_eeff));
        let campaign = CampaignStorageRowV1::new(
            campaign_id,
            replay_session_id,
            ReplaySeed::new(-54),
            content,
            RefDigestV1::from_bytes([0xfe; 32]),
        );
        let envelope = live_envelope(campaign_id, 0, 0x30, 0xc0, true);
        assert!(matches!(
            commit_through_test_seam(config, campaign, &envelope),
            Err(CommittedTickWriteErrorV1::Database {
                operation: CommittedTickDatabaseOperationV1::CommitTransaction,
                ..
            })
        ));
        let mut observer = config.connect(NoTls).expect("failed commit observer");
        assert_tick_visibility(&mut observer, campaign_id, 0, 0, 0);
        let campaign_text = campaign_id.as_uuid().to_string();
        let campaign_count: i64 = observer
            .query_one(
                "SELECT pg_catalog.count(*) FROM babylon_state.campaign \
                 WHERE campaign_id = $1::text::uuid",
                &[&campaign_text],
            )
            .expect("failed campaign visibility")
            .get(0);
        assert_eq!(campaign_count, 0);
    }

    fn commit_through_test_seam(
        config: &Config,
        campaign: CampaignStorageRowV1<'_>,
        envelope: &CommittedTickEnvelopeV1,
    ) -> Result<CommittedTickCommitReportV1, CommittedTickWriteErrorV1> {
        validate_legacy_connection_target(config)
            .map_err(CommittedTickWriteErrorV1::ConnectionTarget)?;
        let storage = CommittedTickStorageEnvelopeV1::try_from(envelope)
            .map_err(CommittedTickWriteErrorV1::StorageMapping)?;
        let bounded = bounded_config(config);
        let mut session = LockedCommittedTickSession::connect(&bounded)?;
        let result = commit_under_lock(&bounded, &mut session, campaign, &storage);
        session.finish(result)
    }

    fn install_writer_reference_fixture(config: &Config) {
        let mut client = config.connect(NoTls).expect("reference fixture connection");
        let digests = (0_u8..7)
            .map(|offset| vec![0x53_u8.wrapping_add(offset); 32])
            .collect::<Vec<_>>();
        client
            .execute(
                "INSERT INTO babylon_ref.h3_reference_cohort \
                 (ref_digest, format_version, artifact_name, artifact_manifest_version, \
                  artifact_digest, source_digest, source_r5_digest, source_r7_digest, \
                  closure_digest, membership_digest, direct_cell_count, \
                  derived_ancestor_count, closure_cell_count) \
                 VALUES ($1, 1, 'writer-live-fixture', '1', $2, $3, $4, $5, $6, $7, 1, 0, 1)",
                &[
                    &digests[0],
                    &digests[1],
                    &digests[2],
                    &digests[3],
                    &digests[4],
                    &digests[5],
                    &digests[6],
                ],
            )
            .expect("reference cohort fixture");
    }

    fn require_owned_disposable_harness() {
        assert_eq!(
            std::env::var("BABYLON_LEGACY_ADOPTER_DISPOSABLE_ACK").as_deref(),
            Ok("I_UNDERSTAND_PER20_DROPS_SCRATCH_DATABASES_ROLES_AND_CREATED_BABYLON_INTEL")
        );
        let canary = std::env::var("BABYLON_LEGACY_ADOPTER_DISPOSABLE_CANARY")
            .expect("owned harness canary");
        assert!(canary.len() == 32 && canary.bytes().all(|byte| byte.is_ascii_hexdigit()));
    }

    struct WriterScratchDatabase {
        base: Config,
        name: String,
        config: Config,
    }

    impl WriterScratchDatabase {
        fn create(base: &Config) -> Self {
            let nonce = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .expect("clock after epoch")
                .as_nanos();
            let name = format!("per20_writer_{}_{}", std::process::id(), nonce);
            let mut client = base.connect(NoTls).expect("base database connection");
            client
                .batch_execute(&format!("CREATE DATABASE \"{name}\""))
                .expect("create writer scratch database");
            let mut config = base.clone();
            config.dbname(&name);
            Self {
                base: base.clone(),
                name,
                config,
            }
        }
    }

    impl Drop for WriterScratchDatabase {
        fn drop(&mut self) {
            let mut client = self
                .base
                .connect(NoTls)
                .expect("cleanup base database connection");
            client
                .execute(
                    "SELECT pg_catalog.pg_terminate_backend(pid) \
                     FROM pg_catalog.pg_stat_activity \
                     WHERE datname = $1 AND pid <> pg_catalog.pg_backend_pid()",
                    &[&self.name],
                )
                .expect("terminate writer scratch sessions");
            client
                .batch_execute(&format!("DROP DATABASE \"{}\"", self.name))
                .expect("drop writer scratch database");
        }
    }

    struct CrashBoundaryCommitDriver<'admin, 'config, 'session, 'campaign, 'storage> {
        admin: &'admin Config,
        config: &'config Config,
        session: &'session mut LockedCommittedTickSession,
        campaign: CampaignStorageRowV1<'campaign>,
        storage: &'storage CommittedTickStorageEnvelopeV1<'storage>,
        target: CommitTransactionBoundaryV1,
        injected: bool,
        observed_after_crash: Option<StoredPresence>,
        campaign_present_after_crash: Option<bool>,
    }

    impl CommitDriver for CrashBoundaryCommitDriver<'_, '_, '_, '_, '_> {
        fn attempt_commit(
            &mut self,
            _attempt: usize,
        ) -> Result<CommitAttempt, CommittedTickWriteErrorV1> {
            let pid = backend_pid(self.session.client());
            let eligible = !self.injected;
            let target = self.target;
            let admin = self.admin;
            let mut injected_now = false;
            let mut probe = |boundary| {
                if eligible && boundary == target {
                    terminate_backend(admin, pid);
                    injected_now = true;
                }
            };
            let result = attempt_commit_using(
                self.session.client(),
                self.campaign,
                self.storage,
                &mut probe,
            );
            self.injected |= injected_now;
            match result {
                Ok(CommitAttempt::Committed)
                    if injected_now
                        && target
                            == CommitTransactionBoundaryV1::after(
                                CommitTransactionStepV1::Commit,
                            ) =>
                {
                    Ok(CommitAttempt::AmbiguousCommit)
                }
                other => other,
            }
        }

        fn reconcile(
            &mut self,
            _after_attempt: usize,
        ) -> Result<StoredPresence, CommittedTickWriteErrorV1> {
            let presence = reconcile_after_ambiguous_commit(
                self.config,
                self.session,
                self.campaign,
                self.storage,
            )?;
            self.observed_after_crash = Some(presence);
            self.campaign_present_after_crash = Some(
                inspect_campaign(self.session.client(), self.campaign)?.is_some_and(|exact| exact),
            );
            Ok(presence)
        }
    }

    fn backend_pid(client: &mut Client) -> i32 {
        client
            .query_one("SELECT pg_catalog.pg_backend_pid()", &[])
            .expect("writer backend pid")
            .try_get(0)
            .expect("integer writer backend pid")
    }

    fn terminate_backend(admin: &Config, pid: i32) {
        const TERMINATION_TIMEOUT_MILLIS: i64 = 5_000;
        let terminated: bool = admin
            .connect(NoTls)
            .expect("crash injector connection")
            .query_one(
                "SELECT pg_catalog.pg_terminate_backend($1, $2)",
                &[&pid, &TERMINATION_TIMEOUT_MILLIS],
            )
            .expect("terminate writer backend")
            .try_get(0)
            .expect("boolean backend termination result");
        assert!(
            terminated,
            "writer backend must terminate at the target boundary"
        );
    }

    struct ScriptedCommitDriver {
        attempts: [CommitAttempt; MAX_TRANSACTION_ATTEMPTS_V1],
        reconciliations: [StoredPresence; MAX_TRANSACTION_ATTEMPTS_V1],
        attempt_index: usize,
        reconciliation_index: usize,
    }

    impl ScriptedCommitDriver {
        const fn new(
            attempts: [CommitAttempt; MAX_TRANSACTION_ATTEMPTS_V1],
            reconciliations: [StoredPresence; MAX_TRANSACTION_ATTEMPTS_V1],
        ) -> Self {
            Self {
                attempts,
                reconciliations,
                attempt_index: 0,
                reconciliation_index: 0,
            }
        }
    }

    impl CommitDriver for ScriptedCommitDriver {
        fn attempt_commit(
            &mut self,
            _attempt: usize,
        ) -> Result<CommitAttempt, CommittedTickWriteErrorV1> {
            let outcome = self.attempts[self.attempt_index];
            self.attempt_index += 1;
            Ok(outcome)
        }

        fn reconcile(
            &mut self,
            _after_attempt: usize,
        ) -> Result<StoredPresence, CommittedTickWriteErrorV1> {
            let outcome = self.reconciliations[self.reconciliation_index];
            self.reconciliation_index += 1;
            Ok(outcome)
        }
    }
}
