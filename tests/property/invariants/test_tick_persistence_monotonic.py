"""Property-based tests for the monotonic-idempotent persistence causal
invariant (INV-016 / spec-056 US4).

See ``specs/056-causal-invariants/contracts/tick_persistence_monotonic.md``
for the full predicate specification. Encodes Constitution II.6 (State is
Data), II.10 World Runtime, and III.7 Determinism (replay from any tick) —
once a tick is persisted, same-payload retries succeed (preserving
existing UPSERT-retry callers in persistence_observer + session_recorder)
and different-payload re-persists raise MonotonicityViolationError.

Four predicates:

  Predicate A — Sequential persists succeed (covers spec US4 AS3) (T024)
  Predicate B — Different-payload re-persist raises (covers AS1) (T025)
  Predicate B' — Same-payload re-persist succeeds idempotently (covers AS2) (T025)
  Predicate C — Back-in-time rewrite raises (covers AS4) (T026)

Parametrized over RuntimeDatabase (default fast gate) and PostgresRuntime
(integration only, T027).
"""
