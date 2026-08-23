//! Rust-owned `PostgreSQL` persistence contracts and adapters.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod error;
pub mod hashes;
pub mod identity;
pub mod migration_manifest;

pub use error::{PersistenceError, PersistenceFailureKind};
pub use hashes::{
    GraphStateHash, MigrationSetDigest, RefDigest, ReplayIdentityHash, TickContentHash,
};
pub use identity::{CampaignId, H3CellId, H3CellIdError};
pub use migration_manifest::{
    ManifestError, MigrationManifest, MAX_MANIFEST_BYTES, MAX_MANIFEST_CHUNKS,
    SCHEMA_ADVISORY_LOCK_KEY,
};
