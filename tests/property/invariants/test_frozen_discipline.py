"""Property-based tests for the frozen Pydantic discipline bound invariant
(INV-011 / spec-055 US3).

See ``specs/055-topology-invariants/contracts/frozen_discipline.md`` for
the full predicate specification. Encodes Constitution III.7 (Determinism
Hash and Replayability) — the engine's ``step(WorldState) -> WorldState``
purity claim.

Three predicates across two layers:

  Predicate A — Layer 1 static class-level frozen=True audit (T019)
  Predicate B — Layer 2 runtime per-tick id() identity check (T020)
  Predicate C — seeded dunder-bypass mutation is detected (T021)
"""
