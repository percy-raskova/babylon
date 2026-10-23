//! Database-free capture of one exact replay campaign foundation.

mod content;

pub use content::{FoundationContentError, FoundationContentKind};

#[path = "foundation/bundle.rs"]
mod bundle;

#[allow(unused_imports)]
use bundle::{copy_bytes, AuthoredFoundationSources, FoundationSources};
pub use bundle::{CampaignFoundation, FoundationContentBundle};

#[allow(unused_imports)]
use crate::runtime::RustPersistenceRuntimeError;
#[allow(unused_imports)]
use crate::semantic_codec;
#[allow(unused_imports)]
use babylon_bsl::canonical_ast::rules_hash_of;
#[allow(unused_imports)]
use babylon_bsl::rule_pipeline::split_content;
#[allow(unused_imports)]
use babylon_bsl::scenario::{load_scenario, load_scenario_with_prelude};
#[allow(unused_imports)]
use babylon_graph::hypergraph_store::HypergraphStore;
#[allow(unused_imports)]
use babylon_graph::stable_element::StableElementResolver;
#[allow(unused_imports)]
use babylon_graph::stable_state::encode_stable_graph_state;
#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use babylon_kernel::content_digest::ContentDigest;
#[allow(unused_imports)]
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
#[allow(unused_imports)]
use babylon_kernel::tick_content_hash::RefDigest;
#[allow(unused_imports)]
use babylon_tick::replay_session::ReplayTickSession;
#[allow(unused_imports)]
use std::collections::TryReserveError;
