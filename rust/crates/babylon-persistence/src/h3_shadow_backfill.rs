//! Bounded maintenance backfill for the frozen legacy H3 estate.

use std::collections::BTreeSet;
use std::str::FromStr;

use babylon_kernel::{H3CellId, H3CellIdError};
use fallible_iterator::FallibleIterator;
use postgres::{Client, Config, GenericClient, IsolationLevel, NoTls, Row, Transaction};
use sha2::{Digest, Sha256};

use crate::h3_reference_cohort::MAX_H3_REFERENCE_CLOSURE_ROWS;
use crate::legacy_adopter::{
    acquire_lock, release_lock, validate_legacy_connection_target, LegacyAdopterError,
};
use crate::postgres_diagnostic::PostgresDiagnosticV1;
use crate::schema_epoch::{
    bounded_config, inspect_schema_epoch_under_lock, SchemaEpochError, SchemaEpochOrigin,
};
/// Exact additive schema epoch consumed by the one-time shadow backfill.
const H3_SHADOW_SCHEMA_EPOCH: usize = 6;
/// Number of frozen persistent H3-bearing relations.
pub const H3_SHADOW_RELATION_COUNT: usize = 15;
/// Number of H3-bearing legacy-to-shadow field mappings.
pub const H3_SHADOW_FIELD_COUNT: usize = 21;
/// Maximum rows mutated by one serializable transaction.
pub const MAX_H3_SHADOW_BACKFILL_BATCH_ROWS: usize = 1_024;
/// Maximum commit attempts after transport ambiguity.
pub const MAX_H3_SHADOW_BACKFILL_COMMIT_ATTEMPTS: usize = 2;
/// Maximum stable refusal records returned to the caller.
pub const MAX_H3_SHADOW_BACKFILL_ISSUES: usize = 64;
/// Maximum distinct legacy/shadow groups inspected per relation.
pub const MAX_H3_SHADOW_DISTINCT_GROUPS: usize = 65_536;
/// Maximum legacy H3 source bytes loaded into one client-side diagnostic.
pub const MAX_H3_SHADOW_TEXT_BYTES: usize = 64;
/// Maximum rows accepted in one legacy relation.
pub const MAX_H3_SHADOW_ROWS_PER_RELATION: u64 = 100_000_000;

const SESSION_SETTINGS_SQL: &str = "SET statement_timeout TO '5min'; \
    SET lock_timeout TO '5s'; \
    SET idle_in_transaction_session_timeout TO '5min'";
const SESSION_SETTINGS_QUERY: &str = "SELECT \
    pg_catalog.current_setting('transaction_read_only'), \
    pg_catalog.current_setting('search_path'), \
    pg_catalog.current_setting('statement_timeout'), \
    pg_catalog.current_setting('lock_timeout'), \
    pg_catalog.current_setting('idle_in_transaction_session_timeout'), \
    pg_catalog.current_setting('quote_all_identifiers'), \
    pg_catalog.current_setting('jit'), \
    pg_catalog.current_setting('event_triggers')";
const WRITE_LOCAL_SETTINGS_SQL: &str = "SET LOCAL search_path TO pg_catalog; \
    SET LOCAL synchronous_commit TO on";
const WRITE_SETTINGS_QUERY: &str = "SELECT \
    pg_catalog.current_setting('transaction_isolation'), \
    pg_catalog.current_setting('transaction_read_only'), \
    pg_catalog.current_setting('search_path'), \
    pg_catalog.current_setting('synchronous_commit'), \
    pg_catalog.current_setting('statement_timeout'), \
    pg_catalog.current_setting('lock_timeout'), \
    pg_catalog.current_setting('idle_in_transaction_session_timeout')";
const LEGACY_ORIGIN_SQL: &str =
    "SELECT pg_catalog.to_regclass('public._babylon_schema_stamp') IS NOT NULL";
const CANONICAL_CELLS_SQL: &str =
    "SELECT cell_id FROM babylon_ref.h3_cell ORDER BY cell_id LIMIT $1";
const LEGACY_SEMANTIC_HASH_DOMAIN: &[u8] = b"BABYLON-H3-SHADOW-LEGACY-SEMANTICS-V2\0";
const INSPECTION_FIELD_WIDTH: usize = 4;

/// Frozen relation identity used in reports and refusal evidence.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum H3ShadowRelation {
    DynamicHexState,
    HexActivity,
    HexCell,
    HexLatest,
    HexMap,
    HexR8LinearFeaturesReference,
    HexR8Reference,
    HexSpatialMap,
    HexState,
    HexSubstrate,
    HexTerrainState,
    ImmutableReferenceLodesOdMatrix,
    InfrastructureLinkState,
    OrgSnapshot,
    TickEvent,
}

impl H3ShadowRelation {
    /// Return the exact public-schema relation name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::DynamicHexState => "dynamic_hex_state",
            Self::HexActivity => "hex_activity",
            Self::HexCell => "hex_cell",
            Self::HexLatest => "hex_latest",
            Self::HexMap => "hex_map",
            Self::HexR8LinearFeaturesReference => "hex_r8_linear_features_reference",
            Self::HexR8Reference => "hex_r8_reference",
            Self::HexSpatialMap => "hex_spatial_map",
            Self::HexState => "hex_state",
            Self::HexSubstrate => "hex_substrate",
            Self::HexTerrainState => "hex_terrain_state",
            Self::ImmutableReferenceLodesOdMatrix => "immutable_reference_lodes_od_matrix",
            Self::InfrastructureLinkState => "infrastructure_link_state",
            Self::OrgSnapshot => "org_snapshot",
            Self::TickEvent => "tick_event",
        }
    }
}

/// Exact reason one legacy value blocks all mutation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum H3ShadowBackfillIssueKind {
    RequiredValueIsNull,
    TextTooLong { actual: u64, max: u64 },
    InvalidText(H3CellIdError),
    UnexpectedResolution { expected: u8, actual: u8 },
    UnknownCanonicalCell { cell_id: i64 },
    ShadowWithoutLegacy { actual: i64 },
    ShadowMismatch { expected: i64, actual: i64 },
    TaggedDestinationMismatch { kind: Option<String> },
    ParentMismatch { expected: i64, actual: i64 },
}

/// One stably ordered, credential-free refusal record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct H3ShadowBackfillIssue {
    pub relation: H3ShadowRelation,
    pub legacy_column: &'static str,
    pub legacy_value: Option<String>,
    pub kind: H3ShadowBackfillIssueKind,
}

/// Bounded resource named by a refusal.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum H3ShadowBackfillBoundedResource {
    CanonicalCells,
    DistinctGroups { relation: H3ShadowRelation },
    RelationRows { relation: H3ShadowRelation },
    Batches { relation: H3ShadowRelation },
}

/// Closed database operation named by a failure.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum H3ShadowBackfillOperation {
    Connect,
    InspectLegacyOrigin,
    PrepareSession,
    VerifySession,
    ReadCanonicalCells,
    InspectRelation { relation: H3ShadowRelation },
    CountPending { relation: H3ShadowRelation },
    BeginTransaction { relation: H3ShadowRelation },
    SetTransactionSettings { relation: H3ShadowRelation },
    UpdateBatch { relation: H3ShadowRelation },
    CommitTransaction { relation: H3ShadowRelation },
    RollbackTransaction { relation: H3ShadowRelation },
}

/// Closed backfill refusal and failure states.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum H3ShadowBackfillError {
    ConnectionTarget(LegacyAdopterError),
    Lock(LegacyAdopterError),
    SchemaEpoch(SchemaEpochError),
    ExactSchemaEpochRequired {
        expected: usize,
        actual: usize,
        origin: SchemaEpochOrigin,
    },
    Database {
        operation: H3ShadowBackfillOperation,
        diagnostic: Option<PostgresDiagnosticV1>,
    },
    Bounds {
        resource: H3ShadowBackfillBoundedResource,
        actual: u64,
        max: u64,
    },
    Refused {
        issue_count: usize,
        evidence: Vec<H3ShadowBackfillIssue>,
    },
    AmbiguousCommitUnresolved {
        relation: H3ShadowRelation,
        attempts: usize,
    },
    AmbiguousCommitDrift {
        relation: H3ShadowRelation,
        before: u64,
        updated: u64,
        after: u64,
    },
    Unlock(LegacyAdopterError),
    FailureAndCleanup {
        primary: Box<H3ShadowBackfillError>,
        cleanup: Box<H3ShadowBackfillError>,
    },
}

impl std::fmt::Display for H3ShadowBackfillError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "H3 shadow backfill failed: {self:?}")
    }
}

impl std::error::Error for H3ShadowBackfillError {}

/// Final disposition of one maintenance invocation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum H3ShadowBackfillDisposition {
    NoLegacyEstate,
    AlreadyComplete,
    Backfilled,
}

/// Exact per-field coverage proof after the final verification pass.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct H3ShadowFieldReport {
    pub relation: H3ShadowRelation,
    pub legacy_column: &'static str,
    pub shadow_column: &'static str,
    pub row_count: u64,
    pub source_value_count: u64,
    pub mapped_value_count: u64,
    pub preserved_null_or_external_count: u64,
}

/// Exact per-relation mutation receipt.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct H3ShadowRelationReport {
    pub relation: H3ShadowRelation,
    pub row_count: u64,
    pub distinct_semantic_group_count: u64,
    pub ordered_semantic_hash: [u8; 32],
    pub rows_backfilled: u64,
    pub batches_committed: usize,
    pub batches_reconciled: usize,
}

/// Successful bounded backfill receipt.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct H3ShadowBackfillReport {
    pub disposition: H3ShadowBackfillDisposition,
    pub fields: Vec<H3ShadowFieldReport>,
    pub relations: Vec<H3ShadowRelationReport>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum FieldKind {
    Required,
    Nullable,
    Tagged,
}

#[derive(Debug, Clone, Copy)]
struct FieldSpec {
    legacy: &'static str,
    shadow: &'static str,
    kind: FieldKind,
    resolution: u8,
}

#[derive(Debug, Clone, Copy)]
struct ParentLaw {
    child: usize,
    parent: usize,
    resolution: u8,
}

#[derive(Debug, Clone, Copy)]
struct RelationSpec {
    relation: H3ShadowRelation,
    fields: &'static [FieldSpec],
    tag_column: Option<&'static str>,
    parent_laws: &'static [ParentLaw],
}

const REQUIRED_R7: FieldSpec = FieldSpec {
    legacy: "h3_index",
    shadow: "cell_id",
    kind: FieldKind::Required,
    resolution: 7,
};
const FIELDS_DYNAMIC_HEX_STATE: [FieldSpec; 1] = [REQUIRED_R7];
const FIELDS_HEX_ACTIVITY: [FieldSpec; 1] = [REQUIRED_R7];
const FIELDS_HEX_CELL: [FieldSpec; 3] = [
    REQUIRED_R7,
    FieldSpec {
        legacy: "res5_parent",
        shadow: "ancestor_r5",
        kind: FieldKind::Required,
        resolution: 5,
    },
    FieldSpec {
        legacy: "res6_parent",
        shadow: "ancestor_r6",
        kind: FieldKind::Required,
        resolution: 6,
    },
];
const FIELDS_HEX_LATEST: [FieldSpec; 1] = [REQUIRED_R7];
const FIELDS_HEX_MAP: [FieldSpec; 1] = [REQUIRED_R7];
const REQUIRED_R8: FieldSpec = FieldSpec {
    legacy: "h3_index",
    shadow: "cell_id",
    kind: FieldKind::Required,
    resolution: 8,
};
const FIELDS_R8_FEATURE: [FieldSpec; 1] = [REQUIRED_R8];
const FIELDS_R8_REFERENCE: [FieldSpec; 2] = [
    REQUIRED_R8,
    FieldSpec {
        legacy: "parent_h3",
        shadow: "parent_cell_id",
        kind: FieldKind::Required,
        resolution: 7,
    },
];
const FIELDS_HEX_SPATIAL_MAP: [FieldSpec; 1] = [REQUIRED_R7];
const FIELDS_HEX_STATE: [FieldSpec; 1] = [REQUIRED_R7];
const FIELDS_HEX_SUBSTRATE: [FieldSpec; 2] = [
    REQUIRED_R8,
    FieldSpec {
        legacy: "r7_parent",
        shadow: "ancestor_r7",
        kind: FieldKind::Required,
        resolution: 7,
    },
];
const FIELDS_HEX_TERRAIN_STATE: [FieldSpec; 1] = [REQUIRED_R7];
const FIELDS_LODES: [FieldSpec; 2] = [
    FieldSpec {
        legacy: "home_hex",
        shadow: "home_cell_id",
        kind: FieldKind::Required,
        resolution: 7,
    },
    FieldSpec {
        legacy: "workplace_dest",
        shadow: "workplace_cell_id",
        kind: FieldKind::Tagged,
        resolution: 7,
    },
];
const FIELDS_INFRASTRUCTURE: [FieldSpec; 2] = [
    FieldSpec {
        legacy: "source_h3",
        shadow: "source_cell_id",
        kind: FieldKind::Required,
        resolution: 7,
    },
    FieldSpec {
        legacy: "target_h3",
        shadow: "target_cell_id",
        kind: FieldKind::Required,
        resolution: 7,
    },
];
const FIELDS_ORG_SNAPSHOT: [FieldSpec; 1] = [FieldSpec {
    legacy: "home_hex",
    shadow: "home_cell_id",
    kind: FieldKind::Nullable,
    resolution: 7,
}];
const FIELDS_TICK_EVENT: [FieldSpec; 1] = [FieldSpec {
    legacy: "h3_index",
    shadow: "cell_id",
    kind: FieldKind::Nullable,
    resolution: 7,
}];
const HEX_CELL_PARENT_LAWS: [ParentLaw; 2] = [
    ParentLaw {
        child: 0,
        parent: 1,
        resolution: 5,
    },
    ParentLaw {
        child: 0,
        parent: 2,
        resolution: 6,
    },
];
const R8_PARENT_LAW: [ParentLaw; 1] = [ParentLaw {
    child: 0,
    parent: 1,
    resolution: 7,
}];
const NO_PARENT_LAWS: [ParentLaw; 0] = [];

const RELATIONS: [RelationSpec; H3_SHADOW_RELATION_COUNT] = [
    relation(H3ShadowRelation::DynamicHexState, &FIELDS_DYNAMIC_HEX_STATE),
    relation(H3ShadowRelation::HexActivity, &FIELDS_HEX_ACTIVITY),
    RelationSpec {
        relation: H3ShadowRelation::HexCell,
        fields: &FIELDS_HEX_CELL,
        tag_column: None,
        parent_laws: &HEX_CELL_PARENT_LAWS,
    },
    relation(H3ShadowRelation::HexLatest, &FIELDS_HEX_LATEST),
    relation(H3ShadowRelation::HexMap, &FIELDS_HEX_MAP),
    relation(
        H3ShadowRelation::HexR8LinearFeaturesReference,
        &FIELDS_R8_FEATURE,
    ),
    RelationSpec {
        relation: H3ShadowRelation::HexR8Reference,
        fields: &FIELDS_R8_REFERENCE,
        tag_column: None,
        parent_laws: &R8_PARENT_LAW,
    },
    relation(H3ShadowRelation::HexSpatialMap, &FIELDS_HEX_SPATIAL_MAP),
    relation(H3ShadowRelation::HexState, &FIELDS_HEX_STATE),
    RelationSpec {
        relation: H3ShadowRelation::HexSubstrate,
        fields: &FIELDS_HEX_SUBSTRATE,
        tag_column: None,
        parent_laws: &R8_PARENT_LAW,
    },
    relation(H3ShadowRelation::HexTerrainState, &FIELDS_HEX_TERRAIN_STATE),
    RelationSpec {
        relation: H3ShadowRelation::ImmutableReferenceLodesOdMatrix,
        fields: &FIELDS_LODES,
        tag_column: Some("workplace_dest_kind"),
        parent_laws: &NO_PARENT_LAWS,
    },
    relation(
        H3ShadowRelation::InfrastructureLinkState,
        &FIELDS_INFRASTRUCTURE,
    ),
    relation(H3ShadowRelation::OrgSnapshot, &FIELDS_ORG_SNAPSHOT),
    relation(H3ShadowRelation::TickEvent, &FIELDS_TICK_EVENT),
];

const fn relation(relation: H3ShadowRelation, fields: &'static [FieldSpec]) -> RelationSpec {
    RelationSpec {
        relation,
        fields,
        tag_column: None,
        parent_laws: &NO_PARENT_LAWS,
    }
}

const fn distinct_group_limit(specification: RelationSpec) -> u64 {
    match specification.relation {
        H3ShadowRelation::ImmutableReferenceLodesOdMatrix => MAX_H3_SHADOW_ROWS_PER_RELATION,
        _ => MAX_H3_SHADOW_DISTINCT_GROUPS as u64,
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct BoundedText {
    value: Option<String>,
    byte_len: Option<u64>,
    digest: Option<String>,
}

struct Inspection {
    fields: Vec<H3ShadowFieldReport>,
    relations: Vec<H3ShadowRelationSemantics>,
    issue_count: usize,
    evidence: Vec<H3ShadowBackfillIssue>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct H3ShadowRelationSemantics {
    relation: H3ShadowRelation,
    row_count: u64,
    distinct_group_count: u64,
    ordered_hash: [u8; 32],
}

struct IssueCollector {
    total: usize,
    evidence: Vec<H3ShadowBackfillIssue>,
}

impl IssueCollector {
    fn new() -> Self {
        Self {
            total: 0,
            evidence: Vec::with_capacity(MAX_H3_SHADOW_BACKFILL_ISSUES),
        }
    }

    fn push(&mut self, issue: H3ShadowBackfillIssue) {
        self.total = self.total.saturating_add(1);
        if self.evidence.len() < MAX_H3_SHADOW_BACKFILL_ISSUES {
            self.evidence.push(issue);
        }
    }
}

/// Validate and backfill the exact frozen legacy H3 estate.
///
/// This maintenance-only entry point assumes the Python writer is quiesced.
/// It never creates canonical H3 identity, publishes a view, or requests
/// runtime writer authority.
///
/// # Errors
/// Refuses target, authority, epoch, bounds, malformed/unknown identity,
/// transaction, reconciliation, or cleanup failures.
pub fn backfill_legacy_h3_shadow_keys(
    config: &Config,
) -> Result<H3ShadowBackfillReport, H3ShadowBackfillError> {
    validate_legacy_connection_target(config).map_err(H3ShadowBackfillError::ConnectionTarget)?;
    let bounded = bounded_config(config);
    let mut session = LockedBackfillSession::connect(&bounded)?;
    let primary = backfill_under_lock(&bounded, &mut session);
    session.finish(primary)
}

fn backfill_under_lock(
    config: &Config,
    session: &mut LockedBackfillSession,
) -> Result<H3ShadowBackfillReport, H3ShadowBackfillError> {
    require_exact_schema_epoch(session.client())?;
    prepare_session(session.client())?;
    if !has_legacy_origin(session.client())? {
        return Ok(H3ShadowBackfillReport {
            disposition: H3ShadowBackfillDisposition::NoLegacyEstate,
            fields: Vec::new(),
            relations: Vec::new(),
        });
    }

    let canonical = read_canonical_cells(session.client())?;
    let before = inspect_estate(session.client(), &canonical)?;
    refuse_issues(&before)?;

    let mut relation_reports = Vec::with_capacity(H3_SHADOW_RELATION_COUNT);
    let mut changed = false;
    for specification in RELATIONS {
        let relation_report = backfill_relation(config, session, specification)?;
        changed |= relation_report.rows_backfilled > 0;
        relation_reports.push(relation_report);
    }

    let after = inspect_estate(session.client(), &canonical)?;
    refuse_issues(&after)?;
    if before
        .fields
        .iter()
        .map(field_source_shape)
        .ne(after.fields.iter().map(field_source_shape))
        || before.relations != after.relations
    {
        return Err(database_error(H3ShadowBackfillOperation::VerifySession));
    }
    if after
        .fields
        .iter()
        .any(|field| field.source_value_count != field.mapped_value_count)
    {
        return Err(H3ShadowBackfillError::Refused {
            issue_count: 1,
            evidence: Vec::new(),
        });
    }
    for (report, semantics) in relation_reports.iter_mut().zip(&after.relations) {
        if report.relation != semantics.relation {
            return Err(database_error(H3ShadowBackfillOperation::VerifySession));
        }
        report.row_count = semantics.row_count;
        report.distinct_semantic_group_count = semantics.distinct_group_count;
        report.ordered_semantic_hash = semantics.ordered_hash;
    }

    Ok(H3ShadowBackfillReport {
        disposition: if changed {
            H3ShadowBackfillDisposition::Backfilled
        } else {
            H3ShadowBackfillDisposition::AlreadyComplete
        },
        fields: after.fields,
        relations: relation_reports,
    })
}

fn field_source_shape(field: &H3ShadowFieldReport) -> (H3ShadowRelation, &'static str, u64, u64) {
    (
        field.relation,
        field.legacy_column,
        field.row_count,
        field.source_value_count,
    )
}

fn refuse_issues(inspection: &Inspection) -> Result<(), H3ShadowBackfillError> {
    if inspection.issue_count == 0 {
        Ok(())
    } else {
        Err(H3ShadowBackfillError::Refused {
            issue_count: inspection.issue_count,
            evidence: inspection.evidence.clone(),
        })
    }
}

fn require_exact_schema_epoch(client: &mut Client) -> Result<(), H3ShadowBackfillError> {
    let (origin, actual) =
        inspect_schema_epoch_under_lock(client).map_err(H3ShadowBackfillError::SchemaEpoch)?;
    if origin == SchemaEpochOrigin::ExistingRustPrefix && actual == H3_SHADOW_SCHEMA_EPOCH {
        Ok(())
    } else {
        Err(H3ShadowBackfillError::ExactSchemaEpochRequired {
            expected: H3_SHADOW_SCHEMA_EPOCH,
            actual,
            origin,
        })
    }
}

fn prepare_session(client: &mut Client) -> Result<(), H3ShadowBackfillError> {
    client
        .batch_execute(SESSION_SETTINGS_SQL)
        .map_err(|error| {
            postgres_database_error(H3ShadowBackfillOperation::PrepareSession, &error)
        })?;
    let operation = H3ShadowBackfillOperation::VerifySession;
    let row = client
        .query_one(SESSION_SETTINGS_QUERY, &[])
        .map_err(|error| postgres_database_error(operation, &error))?;
    let expected = [
        "on",
        "pg_catalog",
        "5min",
        "5s",
        "5min",
        "off",
        "off",
        "off",
    ];
    for (index, wanted) in expected.iter().enumerate() {
        let actual: String = decode(&row, index, operation)?;
        if actual != *wanted {
            return Err(database_error(operation));
        }
    }
    Ok(())
}

fn has_legacy_origin(client: &mut Client) -> Result<bool, H3ShadowBackfillError> {
    let operation = H3ShadowBackfillOperation::InspectLegacyOrigin;
    let row = client
        .query_one(LEGACY_ORIGIN_SQL, &[])
        .map_err(|error| postgres_database_error(operation, &error))?;
    decode(&row, 0, operation)
}

fn read_canonical_cells(client: &mut Client) -> Result<BTreeSet<i64>, H3ShadowBackfillError> {
    let limit =
        i64::try_from(MAX_H3_REFERENCE_CLOSURE_ROWS + 1).expect("canonical H3 row bound fits i64");
    let operation = H3ShadowBackfillOperation::ReadCanonicalCells;
    let rows = client
        .query(CANONICAL_CELLS_SQL, &[&limit])
        .map_err(|error| postgres_database_error(operation, &error))?;
    if rows.len() > MAX_H3_REFERENCE_CLOSURE_ROWS {
        return Err(H3ShadowBackfillError::Bounds {
            resource: H3ShadowBackfillBoundedResource::CanonicalCells,
            actual: u64::try_from(rows.len()).unwrap_or(u64::MAX),
            max: u64::try_from(MAX_H3_REFERENCE_CLOSURE_ROWS).expect("bound fits u64"),
        });
    }
    let mut canonical = BTreeSet::new();
    for row in rows.iter().take(MAX_H3_REFERENCE_CLOSURE_ROWS) {
        let cell: i64 = decode(row, 0, operation)?;
        canonical.insert(cell);
    }
    Ok(canonical)
}

fn inspect_estate(
    client: &mut Client,
    canonical: &BTreeSet<i64>,
) -> Result<Inspection, H3ShadowBackfillError> {
    let mut fields = Vec::with_capacity(H3_SHADOW_FIELD_COUNT);
    let mut relations = Vec::with_capacity(H3_SHADOW_RELATION_COUNT);
    let mut issues = IssueCollector::new();
    for specification in RELATIONS {
        relations.push(inspect_relation(
            client,
            specification,
            canonical,
            &mut fields,
            &mut issues,
        )?);
    }
    debug_assert_eq!(fields.len(), H3_SHADOW_FIELD_COUNT);
    debug_assert_eq!(relations.len(), H3_SHADOW_RELATION_COUNT);
    Ok(Inspection {
        fields,
        relations,
        issue_count: issues.total,
        evidence: issues.evidence,
    })
}

fn inspect_relation(
    client: &mut Client,
    specification: RelationSpec,
    canonical: &BTreeSet<i64>,
    reports: &mut Vec<H3ShadowFieldReport>,
    issues: &mut IssueCollector,
) -> Result<H3ShadowRelationSemantics, H3ShadowBackfillError> {
    let operation = H3ShadowBackfillOperation::InspectRelation {
        relation: specification.relation,
    };
    let query = grouped_inspection_sql(specification);
    let group_limit = distinct_group_limit(specification);
    let query_limit = i64::try_from(group_limit + 1).expect("distinct group bound fits i64");
    let mut rows = client
        .query_raw(&query, [&query_limit])
        .map_err(|error| postgres_database_error(operation, &error))?;

    let report_start = reports.len();
    reports.extend(
        specification
            .fields
            .iter()
            .map(|field| H3ShadowFieldReport {
                relation: specification.relation,
                legacy_column: field.legacy,
                shadow_column: field.shadow,
                row_count: 0,
                source_value_count: 0,
                mapped_value_count: 0,
                preserved_null_or_external_count: 0,
            }),
    );
    let mut hasher = Sha256::new();
    hasher.update(LEGACY_SEMANTIC_HASH_DOMAIN);
    update_semantic_bytes(&mut hasher, specification.relation.as_str().as_bytes());
    let mut current_key: Option<Vec<BoundedText>> = None;
    let mut current_count = 0_u64;
    let mut distinct_group_count = 0_u64;
    let mut raw_group_count = 0_u64;
    let mut row_count = 0_u64;
    while let Some(row) = rows
        .next()
        .map_err(|error| postgres_database_error(operation, &error))?
    {
        raw_group_count = raw_group_count.saturating_add(1);
        if raw_group_count > group_limit {
            return Err(H3ShadowBackfillError::Bounds {
                resource: H3ShadowBackfillBoundedResource::DistinctGroups {
                    relation: specification.relation,
                },
                actual: raw_group_count,
                max: group_limit,
            });
        }
        let (semantic_key, count) = semantic_group(&row, specification, operation)?;
        if current_key
            .as_ref()
            .is_some_and(|current| current != &semantic_key)
        {
            let key = current_key
                .take()
                .expect("the semantic key was checked as present");
            update_semantic_group(&mut hasher, &key, current_count);
            distinct_group_count = distinct_group_count.saturating_add(1);
            row_count = checked_row_add(row_count, current_count, specification.relation)?;
            current_count = 0;
        }
        if current_key.is_none() {
            current_key = Some(semantic_key);
        }
        current_count = checked_row_add(current_count, count, specification.relation)?;
        inspect_group(
            &row,
            specification,
            canonical,
            &mut reports[report_start..],
            issues,
            operation,
        )?;
    }
    if let Some(key) = current_key {
        update_semantic_group(&mut hasher, &key, current_count);
        distinct_group_count = distinct_group_count.saturating_add(1);
        row_count = checked_row_add(row_count, current_count, specification.relation)?;
    }
    for report in reports.iter().skip(report_start) {
        if report.row_count > MAX_H3_SHADOW_ROWS_PER_RELATION {
            return Err(H3ShadowBackfillError::Bounds {
                resource: H3ShadowBackfillBoundedResource::RelationRows {
                    relation: specification.relation,
                },
                actual: report.row_count,
                max: MAX_H3_SHADOW_ROWS_PER_RELATION,
            });
        }
    }
    hasher.update(distinct_group_count.to_be_bytes());
    Ok(H3ShadowRelationSemantics {
        relation: specification.relation,
        row_count,
        distinct_group_count,
        ordered_hash: ordered_semantic_hash(hasher),
    })
}

fn semantic_group(
    row: &Row,
    specification: RelationSpec,
    operation: H3ShadowBackfillOperation,
) -> Result<(Vec<BoundedText>, u64), H3ShadowBackfillError> {
    let mut key = Vec::with_capacity(
        specification.fields.len() + usize::from(specification.tag_column.is_some()),
    );
    for index in 0..specification.fields.len() {
        key.push(decode_bounded_text(
            row,
            index * INSPECTION_FIELD_WIDTH,
            operation,
        )?);
    }
    let tag_index = specification.fields.len() * INSPECTION_FIELD_WIDTH;
    if specification.tag_column.is_some() {
        key.push(decode_bounded_text(row, tag_index, operation)?);
    }
    let count_index = tag_index + 3 * usize::from(specification.tag_column.is_some());
    let raw_count: i64 = decode(row, count_index, operation)?;
    let count = u64::try_from(raw_count).map_err(|_| database_error(operation))?;
    Ok((key, count))
}

fn decode_bounded_text(
    row: &Row,
    index: usize,
    operation: H3ShadowBackfillOperation,
) -> Result<BoundedText, H3ShadowBackfillError> {
    let value: Option<String> = decode(row, index, operation)?;
    let raw_byte_len: Option<i64> = decode(row, index + 1, operation)?;
    let digest: Option<String> = decode(row, index + 2, operation)?;
    let byte_len = raw_byte_len
        .map(u64::try_from)
        .transpose()
        .map_err(|_| database_error(operation))?;
    if value.is_some() != byte_len.is_some() || value.is_some() != digest.is_some() {
        return Err(database_error(operation));
    }
    Ok(BoundedText {
        value,
        byte_len,
        digest,
    })
}

fn update_semantic_group(hasher: &mut Sha256, key: &[BoundedText], count: u64) {
    hasher.update(
        u64::try_from(key.len())
            .expect("static semantic key width fits u64")
            .to_be_bytes(),
    );
    for value in key {
        match (&value.value, value.byte_len, &value.digest) {
            (None, None, None) => hasher.update([0]),
            (Some(_), Some(byte_len), Some(digest)) => {
                hasher.update([1]);
                update_semantic_bytes(hasher, digest.as_bytes());
                hasher.update(byte_len.to_be_bytes());
            }
            _ => unreachable!("bounded text decode keeps value and byte length aligned"),
        }
    }
    hasher.update(count.to_be_bytes());
}

fn update_semantic_bytes(hasher: &mut Sha256, value: &[u8]) {
    hasher.update(
        u64::try_from(value.len())
            .expect("bounded semantic value length fits u64")
            .to_be_bytes(),
    );
    hasher.update(value);
}

fn ordered_semantic_hash(hasher: Sha256) -> [u8; 32] {
    hasher.finalize().into()
}

fn bounded_text_sql(column: &str) -> String {
    format!(
        "CASE WHEN {column} IS NULL THEN NULL \
         WHEN pg_catalog.octet_length({column}::pg_catalog.text) <= {MAX_H3_SHADOW_TEXT_BYTES} \
         THEN {column}::pg_catalog.text ELSE 'hex:'::pg_catalog.text || \
         pg_catalog.encode(pg_catalog.substring(\
         pg_catalog.convert_to({column}::pg_catalog.text, 'UTF8'), \
         1, {MAX_H3_SHADOW_TEXT_BYTES}), 'hex') END"
    )
}

fn text_digest_sql(column: &str) -> String {
    format!(
        "CASE WHEN {column} IS NULL THEN NULL ELSE pg_catalog.encode(\
         pg_catalog.sha256(pg_catalog.convert_to({column}::pg_catalog.text, 'UTF8')), 'hex') END"
    )
}

fn grouped_inspection_sql(specification: RelationSpec) -> String {
    let mut selected = Vec::with_capacity(specification.fields.len() * 4 + 4);
    let mut grouped = Vec::with_capacity(specification.fields.len() * 2 + 1);
    let mut source_ordered = Vec::with_capacity(specification.fields.len() + 1);
    let mut shadow_ordered = Vec::with_capacity(specification.fields.len());
    for field in specification.fields {
        selected.push(bounded_text_sql(field.legacy));
        selected.push(format!(
            "pg_catalog.octet_length({}::pg_catalog.text)::pg_catalog.int8",
            field.legacy
        ));
        selected.push(text_digest_sql(field.legacy));
        selected.push(field.shadow.to_owned());
        grouped.push(field.legacy.to_owned());
        grouped.push(field.shadow.to_owned());
        source_ordered.push(format!("{} COLLATE \"C\" NULLS FIRST", field.legacy));
        shadow_ordered.push(format!("{} NULLS FIRST", field.shadow));
    }
    if let Some(tag_column) = specification.tag_column {
        selected.push(bounded_text_sql(tag_column));
        selected.push(format!(
            "pg_catalog.octet_length({tag_column}::pg_catalog.text)::pg_catalog.int8"
        ));
        selected.push(text_digest_sql(tag_column));
        grouped.push(tag_column.to_owned());
        source_ordered.push(format!("{tag_column} COLLATE \"C\" NULLS FIRST"));
    }
    selected.push("pg_catalog.count(*)".to_owned());
    source_ordered.extend(shadow_ordered);
    format!(
        "SELECT {} FROM public.{} GROUP BY {} ORDER BY {} LIMIT $1",
        selected.join(", "),
        specification.relation.as_str(),
        grouped.join(", "),
        source_ordered.join(", ")
    )
}

fn inspect_group(
    row: &Row,
    specification: RelationSpec,
    canonical: &BTreeSet<i64>,
    reports: &mut [H3ShadowFieldReport],
    issues: &mut IssueCollector,
    operation: H3ShadowBackfillOperation,
) -> Result<(), H3ShadowBackfillError> {
    let tag_index = specification.fields.len() * INSPECTION_FIELD_WIDTH;
    let tag = specification
        .tag_column
        .map(|_| decode_bounded_text(row, tag_index, operation))
        .transpose()?
        .and_then(|value| value.value);
    let count_index = tag_index + 3 * usize::from(specification.tag_column.is_some());
    let raw_count: i64 = decode(row, count_index, operation)?;
    let count = u64::try_from(raw_count).map_err(|_| database_error(operation))?;
    let mut parsed = Vec::with_capacity(specification.fields.len());
    for (index, field) in specification.fields.iter().enumerate() {
        let legacy = decode_bounded_text(row, index * INSPECTION_FIELD_WIDTH, operation)?;
        let shadow: Option<i64> = decode(row, index * INSPECTION_FIELD_WIDTH + 3, operation)?;
        let report = reports
            .get_mut(index)
            .expect("field report count matches static descriptor");
        report.row_count = checked_row_add(report.row_count, count, specification.relation)?;
        let cell = inspect_field(
            specification.relation,
            *field,
            legacy.value.as_deref(),
            legacy.byte_len,
            shadow,
            tag.as_deref(),
            canonical,
            report,
            count,
            issues,
        );
        parsed.push(cell);
    }
    for law in specification.parent_laws {
        let (Some(child), Some(parent)) = (parsed[law.child], parsed[law.parent]) else {
            continue;
        };
        let expected = child
            .ancestor_at(law.resolution)
            .expect("field resolution contract permits the parent law");
        if expected != parent {
            let expected_sql =
                i64::try_from(expected).expect("validated H3 identities fit the signed SQL seam");
            let actual_sql =
                i64::try_from(parent).expect("validated H3 identities fit the signed SQL seam");
            issues.push(H3ShadowBackfillIssue {
                relation: specification.relation,
                legacy_column: specification.fields[law.parent].legacy,
                legacy_value: Some(parent.to_string()),
                kind: H3ShadowBackfillIssueKind::ParentMismatch {
                    expected: expected_sql,
                    actual: actual_sql,
                },
            });
        }
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn inspect_field(
    relation: H3ShadowRelation,
    field: FieldSpec,
    legacy: Option<&str>,
    legacy_byte_len: Option<u64>,
    shadow: Option<i64>,
    tag: Option<&str>,
    canonical: &BTreeSet<i64>,
    report: &mut H3ShadowFieldReport,
    count: u64,
    issues: &mut IssueCollector,
) -> Option<H3CellId> {
    if field.kind == FieldKind::Tagged {
        match (tag, legacy) {
            (Some("external"), Some("canada" | "rest_of_usa")) if shadow.is_none() => {
                report.preserved_null_or_external_count = report
                    .preserved_null_or_external_count
                    .saturating_add(count);
                return None;
            }
            (Some("hex"), Some(_)) => {}
            _ => {
                issues.push(H3ShadowBackfillIssue {
                    relation,
                    legacy_column: field.legacy,
                    legacy_value: legacy.map(str::to_owned),
                    kind: H3ShadowBackfillIssueKind::TaggedDestinationMismatch {
                        kind: tag.map(str::to_owned),
                    },
                });
                return None;
            }
        }
    }
    let Some(legacy) = legacy else {
        if field.kind == FieldKind::Nullable && shadow.is_none() {
            report.preserved_null_or_external_count = report
                .preserved_null_or_external_count
                .saturating_add(count);
        } else if let Some(actual) = shadow {
            issues.push(H3ShadowBackfillIssue {
                relation,
                legacy_column: field.legacy,
                legacy_value: None,
                kind: H3ShadowBackfillIssueKind::ShadowWithoutLegacy { actual },
            });
        } else {
            issues.push(H3ShadowBackfillIssue {
                relation,
                legacy_column: field.legacy,
                legacy_value: None,
                kind: H3ShadowBackfillIssueKind::RequiredValueIsNull,
            });
        }
        return None;
    };

    report.source_value_count = report.source_value_count.saturating_add(count);
    if refuse_oversized_text(relation, field, legacy, legacy_byte_len, issues) {
        return None;
    }
    let cell = match H3CellId::from_str(legacy) {
        Ok(cell) => cell,
        Err(error) => {
            issues.push(H3ShadowBackfillIssue {
                relation,
                legacy_column: field.legacy,
                legacy_value: Some(legacy.to_owned()),
                kind: H3ShadowBackfillIssueKind::InvalidText(error),
            });
            return None;
        }
    };
    if cell.resolution() != field.resolution {
        issues.push(H3ShadowBackfillIssue {
            relation,
            legacy_column: field.legacy,
            legacy_value: Some(legacy.to_owned()),
            kind: H3ShadowBackfillIssueKind::UnexpectedResolution {
                expected: field.resolution,
                actual: cell.resolution(),
            },
        });
        return None;
    }
    let expected = i64::try_from(cell).expect("validated H3 identities fit the signed SQL seam");
    if !canonical.contains(&expected) {
        issues.push(H3ShadowBackfillIssue {
            relation,
            legacy_column: field.legacy,
            legacy_value: Some(legacy.to_owned()),
            kind: H3ShadowBackfillIssueKind::UnknownCanonicalCell { cell_id: expected },
        });
    }
    match shadow {
        Some(actual) if actual == expected => {
            report.mapped_value_count = report.mapped_value_count.saturating_add(count);
        }
        Some(actual) => issues.push(H3ShadowBackfillIssue {
            relation,
            legacy_column: field.legacy,
            legacy_value: Some(legacy.to_owned()),
            kind: H3ShadowBackfillIssueKind::ShadowMismatch { expected, actual },
        }),
        None => {}
    }
    Some(cell)
}

fn refuse_oversized_text(
    relation: H3ShadowRelation,
    field: FieldSpec,
    legacy: &str,
    legacy_byte_len: Option<u64>,
    issues: &mut IssueCollector,
) -> bool {
    let actual = legacy_byte_len.expect("bounded non-null text includes its byte length");
    let max = u64::try_from(MAX_H3_SHADOW_TEXT_BYTES).expect("text bound fits u64");
    if actual <= max {
        return false;
    }
    issues.push(H3ShadowBackfillIssue {
        relation,
        legacy_column: field.legacy,
        legacy_value: Some(legacy.to_owned()),
        kind: H3ShadowBackfillIssueKind::TextTooLong { actual, max },
    });
    true
}

fn checked_row_add(
    current: u64,
    count: u64,
    relation: H3ShadowRelation,
) -> Result<u64, H3ShadowBackfillError> {
    current
        .checked_add(count)
        .ok_or(H3ShadowBackfillError::Bounds {
            resource: H3ShadowBackfillBoundedResource::RelationRows { relation },
            actual: u64::MAX,
            max: MAX_H3_SHADOW_ROWS_PER_RELATION,
        })
}

fn backfill_relation(
    config: &Config,
    session: &mut LockedBackfillSession,
    specification: RelationSpec,
) -> Result<H3ShadowRelationReport, H3ShadowBackfillError> {
    let mut report = H3ShadowRelationReport {
        relation: specification.relation,
        row_count: 0,
        distinct_semantic_group_count: 0,
        ordered_semantic_hash: [0; 32],
        rows_backfilled: 0,
        batches_committed: 0,
        batches_reconciled: 0,
    };
    let max_batches = usize::try_from(
        MAX_H3_SHADOW_ROWS_PER_RELATION
            .div_ceil(u64::try_from(MAX_H3_SHADOW_BACKFILL_BATCH_ROWS).expect("batch fits u64")),
    )
    .expect("batch bound fits usize");
    let mut remaining = pending_count(session.client(), specification)?;
    for _ in 0..=max_batches {
        if remaining == 0 {
            return Ok(report);
        }
        if report.batches_committed == max_batches {
            return Err(H3ShadowBackfillError::Bounds {
                resource: H3ShadowBackfillBoundedResource::Batches {
                    relation: specification.relation,
                },
                actual: u64::try_from(report.batches_committed + 1).unwrap_or(u64::MAX),
                max: u64::try_from(max_batches).unwrap_or(u64::MAX),
            });
        }
        let resolution = commit_one_batch(config, session, specification, remaining)?;
        remaining = remaining.checked_sub(resolution.updated).ok_or_else(|| {
            database_error(H3ShadowBackfillOperation::UpdateBatch {
                relation: specification.relation,
            })
        })?;
        report.rows_backfilled = report
            .rows_backfilled
            .checked_add(resolution.updated)
            .ok_or(H3ShadowBackfillError::Bounds {
                resource: H3ShadowBackfillBoundedResource::RelationRows {
                    relation: specification.relation,
                },
                actual: u64::MAX,
                max: MAX_H3_SHADOW_ROWS_PER_RELATION,
            })?;
        report.batches_committed += 1;
        report.batches_reconciled += usize::from(resolution.reconciled);
    }
    unreachable!("bounded batch loop returns or refuses")
}

#[derive(Debug, PartialEq, Eq)]
struct BatchResolution {
    updated: u64,
    reconciled: bool,
}

fn commit_one_batch(
    config: &Config,
    session: &mut LockedBackfillSession,
    specification: RelationSpec,
    initial_before: u64,
) -> Result<BatchResolution, H3ShadowBackfillError> {
    let mut before = initial_before;
    for attempt in 1..=MAX_H3_SHADOW_BACKFILL_COMMIT_ATTEMPTS {
        let batch = attempt_batch(session.client(), specification)?;
        match batch.outcome {
            CommitOutcome::Committed => {
                return Ok(BatchResolution {
                    updated: batch.updated,
                    reconciled: false,
                });
            }
            CommitOutcome::Ambiguous => {
                session.reconnect(config)?;
                require_exact_schema_epoch(session.client())?;
                prepare_session(session.client())?;
                let after = pending_count(session.client(), specification)?;
                if let Some(resolution) = reconcile_ambiguous_batch(
                    specification.relation,
                    before,
                    batch.updated,
                    after,
                    attempt,
                )? {
                    return Ok(resolution);
                }
                before = after;
            }
        }
    }
    unreachable!("commit attempt loop returns or refuses")
}

fn reconcile_ambiguous_batch(
    relation: H3ShadowRelation,
    before: u64,
    updated: u64,
    after: u64,
    attempt: usize,
) -> Result<Option<BatchResolution>, H3ShadowBackfillError> {
    let committed_after = before
        .checked_sub(updated)
        .ok_or_else(|| database_error(H3ShadowBackfillOperation::CommitTransaction { relation }))?;
    if after == committed_after {
        return Ok(Some(BatchResolution {
            updated,
            reconciled: true,
        }));
    }
    if after != before {
        return Err(H3ShadowBackfillError::AmbiguousCommitDrift {
            relation,
            before,
            updated,
            after,
        });
    }
    if attempt == MAX_H3_SHADOW_BACKFILL_COMMIT_ATTEMPTS {
        return Err(H3ShadowBackfillError::AmbiguousCommitUnresolved {
            relation,
            attempts: attempt,
        });
    }
    Ok(None)
}

struct BatchAttempt {
    updated: u64,
    outcome: CommitOutcome,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CommitOutcome {
    Committed,
    Ambiguous,
}

fn attempt_batch(
    client: &mut Client,
    specification: RelationSpec,
) -> Result<BatchAttempt, H3ShadowBackfillError> {
    let begin_operation = H3ShadowBackfillOperation::BeginTransaction {
        relation: specification.relation,
    };
    let mut transaction = client
        .build_transaction()
        .isolation_level(IsolationLevel::Serializable)
        .read_only(false)
        .start()
        .map_err(|error| postgres_database_error(begin_operation, &error))?;
    let prepared = prepare_batch_transaction(&mut transaction, specification);
    let updated = match prepared {
        Ok(updated) => updated,
        Err(primary) => return rollback_preserving(transaction, primary, specification.relation),
    };
    match transaction.commit() {
        Ok(()) => Ok(BatchAttempt {
            updated,
            outcome: CommitOutcome::Committed,
        }),
        Err(error) if error.as_db_error().is_some() => Err(postgres_database_error(
            H3ShadowBackfillOperation::CommitTransaction {
                relation: specification.relation,
            },
            &error,
        )),
        Err(_) => Ok(BatchAttempt {
            updated,
            outcome: CommitOutcome::Ambiguous,
        }),
    }
}

fn prepare_batch_transaction(
    transaction: &mut Transaction<'_>,
    specification: RelationSpec,
) -> Result<u64, H3ShadowBackfillError> {
    let settings_operation = H3ShadowBackfillOperation::SetTransactionSettings {
        relation: specification.relation,
    };
    transaction
        .batch_execute(WRITE_LOCAL_SETTINGS_SQL)
        .map_err(|error| postgres_database_error(settings_operation, &error))?;
    let settings = transaction
        .query_one(WRITE_SETTINGS_QUERY, &[])
        .map_err(|error| postgres_database_error(settings_operation, &error))?;
    for (index, wanted) in [
        "serializable",
        "off",
        "pg_catalog",
        "on",
        "5min",
        "5s",
        "5min",
    ]
    .iter()
    .enumerate()
    {
        let actual: String = decode(&settings, index, settings_operation)?;
        if actual != *wanted {
            return Err(database_error(settings_operation));
        }
    }
    let batch_rows =
        i64::try_from(MAX_H3_SHADOW_BACKFILL_BATCH_ROWS).expect("batch bound fits i64");
    let operation = H3ShadowBackfillOperation::UpdateBatch {
        relation: specification.relation,
    };
    let updated = transaction
        .execute(&batch_update_sql(specification), &[&batch_rows])
        .map_err(|error| postgres_database_error(operation, &error))?;
    if updated == 0 || updated > u64::try_from(MAX_H3_SHADOW_BACKFILL_BATCH_ROWS).unwrap() {
        return Err(database_error(operation));
    }
    Ok(updated)
}

fn rollback_preserving<T>(
    transaction: Transaction<'_>,
    primary: H3ShadowBackfillError,
    relation: H3ShadowRelation,
) -> Result<T, H3ShadowBackfillError> {
    match transaction.rollback() {
        Ok(()) => Err(primary),
        Err(error) => Err(H3ShadowBackfillError::FailureAndCleanup {
            primary: Box::new(primary),
            cleanup: Box::new(postgres_database_error(
                H3ShadowBackfillOperation::RollbackTransaction { relation },
                &error,
            )),
        }),
    }
}

fn pending_count(
    client: &mut impl GenericClient,
    specification: RelationSpec,
) -> Result<u64, H3ShadowBackfillError> {
    let operation = H3ShadowBackfillOperation::CountPending {
        relation: specification.relation,
    };
    let query = format!(
        "SELECT pg_catalog.count(*) FROM public.{} WHERE {}",
        specification.relation.as_str(),
        pending_predicate(specification)
    );
    let row = client
        .query_one(&query, &[])
        .map_err(|error| postgres_database_error(operation, &error))?;
    let raw: i64 = decode(&row, 0, operation)?;
    let count = u64::try_from(raw).map_err(|_| database_error(operation))?;
    if count > MAX_H3_SHADOW_ROWS_PER_RELATION {
        Err(H3ShadowBackfillError::Bounds {
            resource: H3ShadowBackfillBoundedResource::RelationRows {
                relation: specification.relation,
            },
            actual: count,
            max: MAX_H3_SHADOW_ROWS_PER_RELATION,
        })
    } else {
        Ok(count)
    }
}

fn pending_predicate(specification: RelationSpec) -> String {
    specification
        .fields
        .iter()
        .map(|field| match field.kind {
            FieldKind::Required | FieldKind::Nullable => {
                format!(
                    "({} IS NOT NULL AND {} IS NULL)",
                    field.legacy, field.shadow
                )
            }
            FieldKind::Tagged => format!(
                "({} = 'hex' AND {} IS NULL)",
                specification
                    .tag_column
                    .expect("tagged field requires the static tag column"),
                field.shadow
            ),
        })
        .collect::<Vec<_>>()
        .join(" OR ")
}

fn batch_update_sql(specification: RelationSpec) -> String {
    let assignments = specification
        .fields
        .iter()
        .map(|field| {
            let conversion = format!(
                "(('x' || pg_catalog.lpad(target.{}, 16, '0'))::pg_catalog.bit(64)::pg_catalog.int8)",
                field.legacy
            );
            let value = match field.kind {
                FieldKind::Required => conversion,
                FieldKind::Nullable => format!(
                    "CASE WHEN target.{} IS NULL THEN NULL ELSE {conversion} END",
                    field.legacy
                ),
                FieldKind::Tagged => format!(
                    "CASE WHEN target.{} = 'hex' THEN {conversion} ELSE NULL END",
                    specification
                        .tag_column
                        .expect("tagged field requires the static tag column")
                ),
            };
            format!(
                "{} = COALESCE(target.{}, {value})",
                field.shadow, field.shadow
            )
        })
        .collect::<Vec<_>>()
        .join(", ");
    format!(
        "WITH candidate AS (\
             SELECT tableoid, ctid FROM public.{table} \
             WHERE {pending} ORDER BY tableoid::pg_catalog.oid, ctid LIMIT $1 FOR UPDATE\
         ) \
         UPDATE public.{table} AS target SET {assignments} FROM candidate \
         WHERE target.tableoid = candidate.tableoid AND target.ctid = candidate.ctid",
        table = specification.relation.as_str(),
        pending = pending_predicate(specification),
    )
}

struct LockedBackfillSession {
    client: Option<Client>,
}

impl LockedBackfillSession {
    fn connect(config: &Config) -> Result<Self, H3ShadowBackfillError> {
        let mut client = config
            .connect(NoTls)
            .map_err(|error| postgres_database_error(H3ShadowBackfillOperation::Connect, &error))?;
        acquire_lock(&mut client).map_err(H3ShadowBackfillError::Lock)?;
        Ok(Self {
            client: Some(client),
        })
    }

    fn client(&mut self) -> &mut Client {
        self.client
            .as_mut()
            .expect("locked H3 shadow session always has one client")
    }

    fn reconnect(&mut self, config: &Config) -> Result<(), H3ShadowBackfillError> {
        self.client.take();
        *self = Self::connect(config)?;
        Ok(())
    }

    fn finish<T>(
        mut self,
        primary: Result<T, H3ShadowBackfillError>,
    ) -> Result<T, H3ShadowBackfillError> {
        let cleanup = self.client.as_mut().map_or(Ok(()), |client| {
            release_lock(client).map_err(H3ShadowBackfillError::Unlock)
        });
        self.client.take();
        match (primary, cleanup) {
            (Ok(value), Ok(())) => Ok(value),
            (Err(error), Ok(())) => Err(error),
            (Ok(_), Err(cleanup)) => Err(cleanup),
            (Err(primary), Err(cleanup)) => Err(H3ShadowBackfillError::FailureAndCleanup {
                primary: Box::new(primary),
                cleanup: Box::new(cleanup),
            }),
        }
    }
}

impl Drop for LockedBackfillSession {
    fn drop(&mut self) {
        debug_assert!(
            self.client.is_none(),
            "locked H3 shadow session requires explicit finish"
        );
    }
}

fn decode<T: postgres::types::FromSqlOwned>(
    row: &Row,
    index: usize,
    operation: H3ShadowBackfillOperation,
) -> Result<T, H3ShadowBackfillError> {
    row.try_get(index)
        .map_err(|error| postgres_database_error(operation, &error))
}

fn database_error(operation: H3ShadowBackfillOperation) -> H3ShadowBackfillError {
    H3ShadowBackfillError::Database {
        operation,
        diagnostic: None,
    }
}

fn postgres_database_error(
    operation: H3ShadowBackfillOperation,
    error: &postgres::Error,
) -> H3ShadowBackfillError {
    H3ShadowBackfillError::Database {
        operation,
        diagnostic: Some(PostgresDiagnosticV1::capture(error)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const RELATION: H3ShadowRelation = H3ShadowRelation::HexActivity;

    #[test]
    fn ambiguous_commit_reconciles_the_exact_committed_count() {
        let resolution = reconcile_ambiguous_batch(RELATION, 7, 3, 4, 1)
            .unwrap()
            .expect("the exact committed count must reconcile");
        assert_eq!(resolution.updated, 3);
        assert!(resolution.reconciled);
    }

    #[test]
    fn ambiguous_rollback_retries_only_while_the_pending_count_is_unchanged() {
        assert!(reconcile_ambiguous_batch(RELATION, 7, 3, 7, 1)
            .unwrap()
            .is_none());
        assert_eq!(
            reconcile_ambiguous_batch(RELATION, 7, 3, 7, 2),
            Err(H3ShadowBackfillError::AmbiguousCommitUnresolved {
                relation: RELATION,
                attempts: 2,
            })
        );
    }

    #[test]
    fn ambiguous_commit_refuses_partial_or_concurrent_drift() {
        assert_eq!(
            reconcile_ambiguous_batch(RELATION, 7, 3, 5, 1),
            Err(H3ShadowBackfillError::AmbiguousCommitDrift {
                relation: RELATION,
                before: 7,
                updated: 3,
                after: 5,
            })
        );
    }

    #[test]
    fn impossible_updated_count_is_a_closed_commit_failure() {
        assert_eq!(
            reconcile_ambiguous_batch(RELATION, 2, 3, 0, 1),
            Err(database_error(
                H3ShadowBackfillOperation::CommitTransaction { relation: RELATION }
            ))
        );
    }
}
