"""Property-based tests for the hyperedges-not-pairwise structural linter
(INV-010 / spec-055 US2).

See ``specs/055-topology-invariants/contracts/community_membership_lint.md``
for the full predicate specification. Encodes Constitution II.7 (Edges vs
Hyperedges) and Anti-Pattern VIII.9 (Community as Pairwise Edge).

Three predicates:

  Predicate A — full-pipeline post-state linter (T016)
  Predicate B — MEMBERSHIP edge count delta is legitimate-only (T017)
  Predicate C — seeded violation is detected (negative test, T018)
"""
