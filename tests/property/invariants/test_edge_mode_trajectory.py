"""Property-based tests for the edge-mode trajectory legality bound invariant
(INV-009 / spec-055 US1).

See ``specs/055-topology-invariants/contracts/edge_mode_trajectory.md`` for
the full predicate specification.

Three predicates implemented across two test methods + four file-local
helpers (T013):

  Predicate A — synthesized trajectory across N evidence events (T014)
  Predicate B — observed end-to-end trajectory via SimulationEngine (T015)
  Predicate C — final mode is a legal ``EdgeMode`` enum value
                (operationalized inside every read helper via
                ``EdgeMode(value)`` construction, T013)
"""
