"""Property-based tests for the WorldState graph round-trip identity bound
invariant (INV-012 / spec-055 US4).

See ``specs/055-topology-invariants/contracts/round_trip_identity.md`` for
the full predicate specification. Encodes Constitution II.6 (State is
Data, Engine is Transformation) — the round-trip is the operational
definition of "State is Data."

Three predicates:

  Predicate A — round-trip preserves model_dump exactly (T022)
  Predicate B — round-trip works at maximum supported size (T023)
  Predicate C — every legal EdgeType round-trips faithfully (T024)
"""
