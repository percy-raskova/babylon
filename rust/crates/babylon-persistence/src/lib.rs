//! Rust-owned `PostgreSQL` persistence contracts and adapters.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod error;
pub mod hashes;
pub mod identity;

pub use error::{PersistenceError, PersistenceFailureKind};
pub use hashes::{
    GraphStateHash, MigrationSetDigest, RefDigest, ReplayIdentityHash, TickContentHash,
};
pub use identity::CampaignId;
