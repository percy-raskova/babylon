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
#![allow(
    clippy::result_large_err,
    reason = "the error carries the full authored refusal context"
)]

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

use tick_runner::run_prepared_tick_with;
pub use tick_runner::{
    analyze_content_set_sources, analyze_content_set_sources_with_kernel_slots, any_over_budget,
    diagnose_content_set_sources, forecast_event_likelihoods,
    forecast_event_likelihoods_with_kernel_slots, forecast_scenario_determined_event_likelihoods,
    forecast_scenario_determined_event_likelihoods_with_kernel_slots, fuel_bound_report, hex,
    run_once, run_once_into, run_once_into_with_prelude, run_once_with_prelude, ContentRuleSource,
    ContentSetSourceAnalysisError, ForecastError, FuelBoundRow, PrepareError, SourcedPrepareError,
    TickReport,
};
#[cfg(test)]
use tick_runner::{
    checked_fired_total, prepare_rules_with_kernel_slots, run_prepared_tick_transaction,
    ExecutionIdentity,
};
pub(crate) use tick_runner::{
    prepare_rules, prepare_rules_with_graph_seed, run_prepared_replay_tick, EventRecord,
    PreparedRules,
};
#[cfg(test)]
pub(crate) use tick_runner::{HashBoundary, PreparedEventBatchSink};
