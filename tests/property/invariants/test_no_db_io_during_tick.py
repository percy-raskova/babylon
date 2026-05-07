"""Property-based tests for the No-DB-I/O-during-tick causal invariant
(INV-015 / spec-056 US3).

See ``specs/056-causal-invariants/contracts/no_db_io_during_tick.md`` for
the full predicate specification. Encodes Constitution II.6 verbatim
("No DB I/O during tick"), II.10 World Runtime, II.11 Subsystem Table
Ownership, and ADR037 Postgres Runtime — the engine is a pure
transformation; intra-tick I/O is non-determinism by another name.

Three predicates:

  AS1 — Random WorldState run_tick under no_db_io_during_tick patch succeeds (T021)
  AS2 — Deliberate DB call from a System raises DBIONotPermittedError (T022)
  AS3 — Hydration before patch + persistence after patch are uninterrupted (T023)
"""
