//! `babylon-tick`'s `run_once` seam — the Phase 2 Slice 1 flow (scenario load
//! -> rule load -> one tick -> state hash) as a library function, so both
//! the CLI driver (`main.rs`) and `babylon-client`'s engine link (B0) call
//! exactly one implementation. See `main.rs` for the CLI-facing docs; this
//! module is the seam itself.

// `PrepareError` (§2.3, issue #652 Task 3) wraps `ScenarioError`, which is
// already past clippy's 128-byte `result_large_err` threshold on its own
// (`babylon-bsl/src/scenario.rs:69-77`'s own citation) — wrapping it behind
// one more enum layer cannot shrink that. The lint fires on every function
// in THIS module that returns `Result<_, PrepareError>`
// (`seed_implicit_edge_strength_fields`, `build_shared_load_inputs`,
// `prepare_rules`) — the same "one error type, many signatures" shape
// `scenario.rs`'s own module-scope allow exists for, so this follows that
// precedent at module scope rather than three separate function-level
// allows. The load path is cold (a content set either loads once or the
// whole run fails), so paying the extra stack bytes on every one of these
// rarely-taken error branches is the right trade against boxing a field
// §2.3 specifies unboxed, or `Box`-wrapping every wrapped error type for a
// branch that is rarely taken.
#![allow(clippy::result_large_err)]

pub mod choice_receipt;

pub mod committed_event;

pub mod diagnostic;

pub mod h3_runtime;

pub mod kernel_slot;

pub mod material_replay;

pub mod material_staffing;

pub mod material_state;

pub mod material_world;

mod phase_order;

pub mod replay_identity;

pub mod replay_session;

mod world_hash;

mod tick_runner;

pub use tick_runner::{
    analyze_content_set_sources, analyze_content_set_sources_with_kernel_slots, any_over_budget,
    diagnose_content_set_sources, forecast_event_likelihoods,
    forecast_event_likelihoods_with_kernel_slots, forecast_scenario_determined_event_likelihoods,
    forecast_scenario_determined_event_likelihoods_with_kernel_slots, fuel_bound_report, hex,
    run_once, run_once_into, run_once_into_with_prelude, run_once_with_prelude, ContentRuleSource,
    ContentSetSourceAnalysisError, ForecastError, FuelBoundRow, PrepareError, SourcedPrepareError,
    TickReport,
};
#[allow(unused_imports)]
use tick_runner::{
    analyze_content_set_sources_before_kernel_slots, build_shared_load_inputs,
    checked_considered_total, checked_fired_total, complete_tick_transaction,
    enforce_ranked_composition, execute_prepared_rules, hydrate_scenario,
    hydrate_scenario_instances, prepare_error_from_schedule, prepare_error_source_id,
    prepare_rules_with_instances, prepare_rules_with_kernel_slots, prepare_tick_transaction,
    probability_prepare_error, registered_systems, run_once_session, run_prepared_tick,
    run_prepared_tick_transaction, run_prepared_tick_with, seed_implicit_edge_strength_fields,
    transaction_error, validate_material_cycle_cardinality, ExecutedRules, ExecutionIdentity,
    SharedLoadInputs, TickTransactionError, TickTransactionResult, TransactionPrelude,
};
#[allow(unused_imports)]
pub(crate) use tick_runner::{
    prepare_rules, prepare_rules_with_graph_seed, run_prepared_replay_tick, EventRecord,
    HashBoundary, PreparedEventBatchSink, PreparedRules,
};

#[allow(unused_imports)]
use babylon_bsl::bindings::BindingVocabulary;
#[allow(unused_imports)]
use babylon_bsl::causal_contract::{reduce_audit_receipts, AuditReceipt};
#[allow(unused_imports)]
use babylon_bsl::declarations::{parse_intrinsic_decls, DeclError, FieldRegistry};
#[allow(unused_imports)]
use babylon_bsl::error_identity::ErrorIdentity;
#[allow(unused_imports)]
use babylon_bsl::evaluator::Value;
#[allow(unused_imports)]
use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
#[allow(unused_imports)]
use babylon_bsl::intrinsic_host::KernelIntrinsicHost;
#[allow(unused_imports)]
use babylon_bsl::probability::{KernelInstanceIdentity, ProbabilityError};
#[allow(unused_imports)]
use babylon_bsl::reader::{FormPath, SExpr};
#[allow(unused_imports)]
use babylon_bsl::rule_pipeline::{
    check_unique_rule_ids, load_rule_form, split_content, LoadContext, LoadError, LoadedRule,
};
#[allow(unused_imports)]
use babylon_bsl::same_tick_order::{diagnose_ranked, ENFORCE_RANK_AWARE_AGGREGATE_ORDERING};
#[allow(unused_imports)]
use babylon_bsl::scenario::{
    load_scenario, load_scenario_with_prelude, LoadedScenario, ScenarioError,
};
#[allow(unused_imports)]
use babylon_bsl::structural_verbs::CollectingSink;
#[allow(unused_imports)]
use babylon_bsl::tick::run_tick_observed;
#[allow(unused_imports)]
use babylon_bsl::typecheck::TypeEnv;
#[allow(unused_imports)]
use babylon_bsl::types::{EnumRegistry, FieldDecl};
#[allow(unused_imports)]
use babylon_bsl::write_log::CollectingWriteLog;
#[allow(unused_imports)]
use babylon_graph::allocator_state::AllocatorState;
#[allow(unused_imports)]
use babylon_graph::hypergraph_store::HypergraphStore;
#[allow(unused_imports)]
use babylon_graph::stable_element::{StableElementKey, StableElementResolver};
#[allow(unused_imports)]
use babylon_graph::state_hash::CanonicalState;
#[allow(unused_imports)]
use babylon_graph::substrate::{GraphError, GraphSubstrate, HyperedgeId, NodeId};
#[allow(unused_imports)]
use babylon_graph::working_copy::DetachedCopy;
#[allow(unused_imports)]
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId, RngSeedContext};
#[allow(unused_imports)]
use replay_session::{IdentifiedTickReport, ReplayTickError};
#[allow(unused_imports)]
use std::collections::{HashMap, HashSet};
