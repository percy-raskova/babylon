//! Immutable checkpoint admission shared by runtime and full-observer reads.

#[cfg(test)]
mod tests;

#[path = "component_identity/identity.rs"]
mod identity;

pub(crate) use identity::MaterialComponentIdentity;

#[cfg(test)]
use super::MaterialRuntimeError;
#[cfg(test)]
use babylon_kernel::content_digest::ContentDigest;
#[cfg(test)]
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
#[cfg(test)]
use babylon_kernel::tick_content_hash::RefDigest;
#[cfg(test)]
use babylon_practice_contract::OrderedPracticeActionBatch;
