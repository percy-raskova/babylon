# Dossier exposure boundary implementation plan

> **For agentic workers:** Use `superpowers:subagent-driven-development` with
> GPT-6.1 Terra at extra-high reasoning. Use meaningful RED/GREEN regressions.

**Goal:** Compute an actor's believed structural exposure from its actual known
nodes and ties, without consulting undisclosed authoritative graph structure.

**Architecture:** Exposure only needs existence and neighbor queries. Introduce
one narrow read interface for those queries. Both the authoritative substrate
and the actor's dossier provide current representations through that interface.
The dossier answers from its own sorted records, including unreconciled beliefs.

**Tech Stack:** Existing `babylon-graph`, deterministic sorted collections, Rust.

**Spec:** Active thread Goal, ADR184's actor-owned belief contract, and the
hidden-edge failure in `reports/gameplay-delivery-audit-2026-10-29.md`.

## Constraints and review focus

- No new mathematical primitive, political effect, response curve or game value.
- Do not change generic allocation or reject negative finite yields: ADR184
  defines unaffordability as the allocator's sole decline reason.
- A known node does not authorize its hidden edges or attributes.
- Knowledge remains stale until explicit reconciliation. A ranking read must
  not consult authoritative existence and silently learn that a node disappeared.
- Preserve direction, sorted iteration, duplicate-neighbor elimination, exact
  topology mathematics, loud unknown-node errors and existing truth queries.

## Task 1: Make the known topology a real exposure input

**Files:** `rust/crates/babylon-graph/src/exposure.rs`, `dossier.rs`, `lib.rs`
and one focused read-interface module if needed.

**Interfaces:** Add `ExposureGraph` with only `node_exists(NodeId) -> bool` and
`neighbors(NodeId, &str, Direction) -> Result<Vec<NodeId>, GraphError>`.
Existing `GraphSubstrate` implementations provide these queries through a
blanket implementation. `Dossier` provides the same queries from its own stored
knowledge. Exposure functions accept this narrow read interface. No graph
mutations, attributes or hyperedge inspection become dossier capabilities.

- [x] Reproduce the current known-endpoints/unknown-edge failure before fixing
  the API. Keep the concrete counterexample and expected believed components.
- [x] Test two actor dossiers with different known edges over the same truth.
- [x] Test forgotten ties, unreconciled stale nodes, unknown-node refusal,
  `Out`/`In`/`Any`, reverse-tie deduplication and insertion-order invariance.
- [x] Implement the narrow interface and update existing belief-based exposure
  callers/tests to pass the dossier itself, not truth plus a node-only scope.
- [x] Correct documentation that currently equates node scope with edge knowledge.
- [x] Run graph tests, formatting, applicable Clippy and BSL sentinels serially.
  Run consumer compile checks because the exposure parameter bound changes.
- [x] Obtain independent spec/quality review and commit the verified repair.

Reviewed commit: `3825f642e6e78f12977f0170af7f037422eab7a8` on
`codex/PER-355-private-exposure`. Graph checks passed: 124 unit and 24 integration
tests, formatting, scoped Clippy, BSL sentinels and BSL/tick consumer checks.

This repairs a foundation, not campaign opponent delivery. Agency funding,
political intent approval, tick integration, persistence and player receipts
remain required by the full active Goal.
