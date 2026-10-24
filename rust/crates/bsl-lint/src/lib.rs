//! `bsl-lint` library surface: the finding shape, repository access, and the
//! check registry that the binary and integration tests share.
//!
//! The binary is a thin CLI over [`CHECKS`]; a check lives in its own module
//! and exposes a `CHECK` name plus a `run(&Repo, &[String])` function.

pub mod finding;
pub mod google_rust_style;
pub mod repo;

mod citation_drift;
mod namespace_unique;
mod registry;
mod rust_contract_authority;
mod sfs_non_authorability;

pub use registry::{Check, CheckFn, CHECKS};
