//! Immutable checkpoint admission shared by runtime and full-observer reads.

#[cfg(test)]
mod tests;

#[path = "component_identity/identity.rs"]
mod identity;

#[allow(unused_imports)]
pub(crate) use identity::MaterialComponentIdentity;

#[allow(unused_imports)]
use super::{CampaignFoundation, MaterialRuntimeError};
#[allow(unused_imports)]
use babylon_graph::hypergraph_store::HypergraphStore;
#[allow(unused_imports)]
use babylon_kernel::content_digest::ContentDigest;
#[allow(unused_imports)]
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
#[allow(unused_imports)]
use babylon_kernel::tick_content_hash::RefDigest;
#[allow(unused_imports)]
use babylon_practice_contract::OrderedPracticeActionBatch;
#[allow(unused_imports)]
use babylon_tick::replay_session::ReplayTickSession;
