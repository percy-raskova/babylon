//! B0's proof that the client links the engine in-process: run the Slice 1
//! seam (scenario -> rule -> one tick -> state hash) at startup and log it.
use babylon_tick::{run_once, TickReport};

const SCENARIO: &str = include_str!("../../babylon-tick/content/scenarios/two-classes.bscn");
const RULE: &str = include_str!("../../babylon-tick/content/rules/fundamental-theorem.bsl");

/// Run one deterministic tick over the pinned two-classes scenario and
/// fundamental-theorem rule — the same `babylon_tick::run_once` seam the
/// CLI driver uses, so "the client links the engine" means sharing this
/// exact code path, not a lookalike reimplementation.
pub fn engine_link_probe() -> Result<TickReport, String> {
    run_once(SCENARIO, RULE)
}
