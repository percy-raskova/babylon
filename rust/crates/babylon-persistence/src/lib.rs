//! Rust-owned `PostgreSQL` persistence contracts and adapters.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod error;
pub mod h3_reference_cohort;
mod h3_reference_installer;
pub mod hashes;
pub mod identity;
pub mod legacy_adopter;
pub mod migration_manifest;
pub mod schema_epoch;
pub mod schema_migration;
pub mod writer_gate;

pub use error::{PersistenceError, PersistenceFailureKind};
pub use h3_reference_cohort::{
    build_representative_h3_cohort_v1, H3ReferenceCellRow, H3ReferenceCohort,
    H3ReferenceCohortError, H3ReferenceCohortReceipt, H3ReferenceOrigin,
    MAX_H3_REFERENCE_SOURCE_CELLS,
};
pub use h3_reference_installer::{
    install_representative_h3_cohort, H3ReferenceInstallBoundedResource,
    H3ReferenceInstallConflict, H3ReferenceInstallDisposition, H3ReferenceInstallError,
    H3ReferenceInstallOperation, H3ReferenceInstallReport,
};
pub use hashes::{
    GraphStateHash, MigrationSetDigest, RefDigest, ReplayIdentityHash, TickContentHash,
};
pub use identity::{CampaignId, H3CellId, H3CellIdError};
pub use legacy_adopter::{
    adopt_legacy_schema, compare_legacy_census, expected_legacy_census,
    legacy_adopter_sql_statements, parse_legacy_census_fixture, validate_legacy_connection_target,
    validate_legacy_stamps, LegacyAdopterError, LegacyAdopterOperation, LegacyAdopterSqlKind,
    LegacyAdopterSqlStatement, LegacyAdoptionReport, LegacyBoundedResource, LegacyCensus,
    LegacyCensusEntry, LegacyCensusParseError, LegacyConnectionTargetRejection, LegacyObjectKey,
    LegacyObjectKind, LegacyOwnerAuthorityDisposition, LegacyStampClass, LegacyStampDefinition,
    LegacyStampMatch, LegacyStampProvenance, LegacyStampReport, LEGACY_ADOPTER_CONNECT_TIMEOUT,
    LEGACY_ADOPTER_STARTUP_OPTIONS, LEGACY_ADOPTER_TCP_USER_TIMEOUT, LEGACY_CENSUS_FIXTURE,
    LEGACY_CENSUS_VERSION, LEGACY_STAMP_CATALOG, MAX_LEGACY_CENSUS_FIXTURE_BYTES,
    MAX_LEGACY_CENSUS_FIXTURE_LINES, MAX_LEGACY_CENSUS_ROWS,
    MAX_LEGACY_EXTENSION_DEPENDENCY_ADDRESSES, MAX_LEGACY_EXTENSION_MEMBERS,
    MAX_LEGACY_EXTENSION_ROLE_IDENTITIES, MAX_LEGACY_PARTITIONS_PER_FAMILY,
    MAX_LEGACY_SEQUENCE_OWNERSHIP, MAX_LEGACY_STAMP_ROWS, POSTGRES_IDENTIFIER_MAX_BYTES,
};
pub use migration_manifest::{
    ManifestError, MigrationManifest, MAX_MANIFEST_BYTES, MAX_MANIFEST_CHUNKS,
    SCHEMA_ADVISORY_LOCK_KEY,
};
pub use schema_epoch::{
    compiled_schema_migrations, migrate_schema_epoch, validate_migration_prefix,
    PersistedMigration, SchemaEpochError, SchemaEpochObservation, SchemaEpochOperation,
    SchemaEpochOrigin, SchemaEpochRelation, SchemaEpochReport, SchemaEpochSchemas,
    MAX_COMMIT_ATTEMPTS_PER_VERSION, MAX_SCHEMA_MIGRATIONS,
};
pub use schema_migration::{
    MigrationChecksum, MigrationVersion, SchemaMigration, SchemaMigrationError,
    MAX_SCHEMA_MIGRATION_SQL_BYTES, MIGRATION_CHECKSUM_BYTES,
};
pub use writer_gate::{
    request_rust_writer_authority, RustWriterAuthority, RustWriterAuthorityError,
};
