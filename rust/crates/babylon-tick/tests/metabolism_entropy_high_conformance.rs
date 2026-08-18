//! The other half of the mutation-verification pair for D-1's scaled-`Int`
//! workaround: `entropy_factor` AT its declared cap (`3.0`, inclusive,
//! domain `(1.0, 3.0]`). See `metabolism_entropy_low_conformance.rs` for
//! the companion — the IDENTICAL territory, differing only in
//! `entropy_factor`.
//!
//! # Provenance
//!
//! ```text
//! PYTHONPATH="$PWD/src" uv run python \
//!     rust/crates/babylon-tick/content/scenarios/metabolism_entropy_high_conformance.py
//! ```
//!
//! Its output on 2026-08-11, verbatim:
//!
//! ```text
//! entropy_factor = 3.0
//! post-tick state:
//!   high-entropy-county  biocapacity=0.0 max_biocapacity=99.95
//! ```

mod support;

use babylon_graph::memory::MemoryGraph;
use support::{assert_deterministic, attribute, run_conformance};

const SCENARIO: &str =
    include_str!("../content/scenarios/metabolism-entropy-high-conformance.bscn");
const RULE: &str = include_str!("../content/rules/metabolism.bsl");

fn run() -> MemoryGraph {
    run_conformance(SCENARIO, RULE)
}

/// At `entropy_factor = 3.0` (the declared cap): `raw_extraction = 1*10 =
/// 10`, `ecological_cost = 10 * 3.0 = 30`, `delta = 2 - 30 = -28`,
/// `current + delta = 10 - 28 = -18` — the `max(0.0, ...)` floor binds at
/// EXACTLY `0.0`. Contrast the low-entropy companion
/// (`metabolism_entropy_low_conformance.rs`), the IDENTICAL territory at
/// `entropy_factor = 1.01`, where the floor does NOT bind (`1.9`) — this
/// swing, driven by nothing but `entropy_factor`, is the clearest possible
/// proof the D-1 scaled-`Int` workaround (`entropy-factor-x1e6`, divided
/// back out by `1000000`) carries the coefficient's effect end to end: an
/// off-by-a-factor-of-ten bug in the descaling would make this vector
/// diverge sharply from `0.0` (or the low-entropy vector diverge from
/// `1.9`).
#[test]
fn a_high_entropy_factor_at_the_cap_floors_biocapacity_at_exactly_zero() {
    let graph = run();
    assert_eq!(attribute(&graph, 0, "territory/biocapacity"), 0.0);
}

/// `damage = raw_extraction * hysteresis_rate = 10 * 0.005 = 0.05`,
/// unaffected by `entropy_factor` — identical to the low-entropy
/// companion's own `max_biocapacity`, confirming the D-1 workaround only
/// touches the ecological-cost term.
#[test]
fn the_hysteresis_damage_is_unaffected_by_entropy_factor() {
    let graph = run();
    assert_eq!(attribute(&graph, 0, "territory/max-biocapacity"), 99.95);
}

/// Byte-determinism.
#[test]
fn the_high_entropy_scenario_tick_is_deterministic() {
    let a = assert_deterministic(SCENARIO, RULE);
    assert_eq!(a.fired, 1);
}
