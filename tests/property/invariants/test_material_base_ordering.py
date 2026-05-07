"""Property-based tests for the Material Base ordering causal invariant
(INV-013 / spec-056 US1).

See ``specs/056-causal-invariants/contracts/material_base_ordering.md`` for
the full predicate specification. Encodes ADR032 Materialist Causality
(Material Base before Action Phase) and Constitution I.18
(Material-Ideological Distinction) — organizations must observe a
fully-resolved material state before deliberating.

Four predicates:

  AS1 — Every Material Base System runs before any Action Phase System (T014)
  AS2 — Permuted system list catches inversion (T015)
  AS3 — OODASystem invoked exactly once per tick (T016)
  FR-012 — Spy non-interference: spied tick == unspied tick (T017)
"""
