# Contract: Tick Persistence Monotonic-Idempotent (US4, INV-016)

**Invariant ID**: INV-016
**User Story**: US4 (P3) — State persistence is monotonic-idempotent in tick
**Constitutional Basis**: Constitution II.6 (State is Data); II.10 World Runtime; III.7 Determinism (replay from any tick)
**Test File**: `tests/property/invariants/test_tick_persistence_monotonic.py`

**Contract revision (2026-05-07 per F7=B)**: This contract was originally
drafted as "strict raise on any overwrite." Verification of the
existing `RuntimePersistence` Protocol revealed that the documented
contract is "Idempotent via UPSERT semantics" — the persistence
observer and session recorder rely on idempotent retries. The revised
contract, **monotonic-idempotent**, preserves the retry semantics while
blocking history rewrites: same-payload re-persist succeeds; different-
payload re-persist raises `MonotonicityViolationError`. See
`research.md §5` for the implementation strategy and the existing-caller
audit.

## Acceptance-Scenario ↔ Predicate Mapping (D2)

The spec's US4 acceptance scenarios are organized differently than this
contract's predicates. The mapping is:

| Spec AS | Contract Predicate | What it tests |
|---------|--------------------|---------------|
| US4 AS1 | Predicate B (different payload raises) | Strict-raise on rewrite-with-different |
| US4 AS2 | Predicate B' (same payload succeeds) | Idempotent retry preserves state |
| US4 AS3 | Predicate A (sequential writes) | 5-tick clean run + reads |
| US4 AS4 | Predicate C (back-in-time rewrite) | Earlier-tick overwrite raises |

Tasks T024–T026 cover Predicates A / B / B' / C respectively (T024 also
covers AS3, T025 covers AS1+AS2 via parametrized payload-equality, T026
covers AS4).

## Predicate

```text
For every RuntimePersistence implementation P:
  Predicate A — Sequential writes succeed:
    For ticks 0..4: P.persist_tick(tick=N, graph=payload_N) succeeds
    For ticks 0..4: P.hydrate_graph(tick=N) returns payload_N

  Predicate B — Different-payload re-persist raises:
    Given P with tick N already written with payload_N:
    P.persist_tick(tick=N, graph=different_payload) raises MonotonicityViolationError
    AFTER the failed re-persist: P.hydrate_graph(tick=N) returns payload_N (unchanged)

  Predicate B' — Same-payload re-persist succeeds idempotently:
    Given P with tick N already written with payload_N:
    P.persist_tick(tick=N, graph=payload_N) succeeds (no exception)
    AFTER the idempotent re-persist: P.hydrate_graph(tick=N) returns payload_N (unchanged)

  Predicate C — Back-in-time different-payload rewrite raises:
    Given P with ticks 0..4 written:
    P.persist_tick(tick=2, graph=different_payload) raises MonotonicityViolationError
    AFTER the failed rewrite: P.hydrate_graph(tick=N) returns the original payload_N
                              for every N in [0, 5)
```

In plain English: once tick N is persisted, a re-persist with the same
payload succeeds idempotently (preserving observer / recorder retry
semantics). A re-persist with a *different* payload raises
`MonotonicityViolationError` — silent rewrite is a contract violation.
The same applies to back-in-time rewrites of any earlier tick.

## Inputs

- One `RuntimePersistence` implementation per test parametrization:
  - `RuntimeDatabase` (in-memory, default fast gate)
  - `PostgresRuntime` (transient test database, gated under
    `mise run test:integration` per FR-009)
- A multi-tick sequence from `multi_tick_sequence_strategy(n_ticks=5)`
  producing `list[tuple[int, dict]]` of `(tick, payload)` pairs (per
  `research.md §7`)
- A `session_id: UUID` per test (Postgres requires it; in-memory
  accepts `None`)

## Outputs

- Predicate A: 5 successful `persist_tick` calls; 5 successful
  `hydrate_graph` calls returning original payloads
- Predicate B: `MonotonicityViolationError` raised; subsequent
  `hydrate_graph` returns original
- Predicate B': `persist_tick` returns successfully (no exception);
  subsequent `hydrate_graph` returns original
- Predicate C: `MonotonicityViolationError` raised; subsequent
  `hydrate_graph` calls return originals for every tick

## Falsification

| Condition | Failure Mode |
|-----------|--------------|
| `persist_tick` for an already-persisted tick with **different** payload returns success without raising | Monotonic contract violated; failure message names the tick number, the original payload, and the attempted overwrite payload |
| `persist_tick` for an already-persisted tick with **same** payload raises | Idempotency contract violated; failure message names the tick + identical-payload signature; suggests the implementation lost the same-payload short-circuit |
| `persist_tick` raises a different exception type | Diagnostic message points at the exception type mismatch and the implementation that raised it |
| Subsequent `hydrate_graph(N)` returns the attempted overwrite payload | Audit trail invariant violated; failure message shows both payloads and the tick number |
| Subsequent `hydrate_graph(N)` returns None or raises | Original payload was lost during the failed overwrite; failure message names the implementation |

## Implementation Notes

- Per research.md §5 (revised 2026-05-07), the two implementations
  enforce monotonic-idempotency via:
  - `RuntimeDatabase.persist_tick`: in-memory dict comparison — if
    `(session_id, tick) in self._states` and `existing != new_payload`,
    raise `MonotonicityViolationError`; if equal, return silently.
  - `PostgresRuntime.persist_tick`: schema-level `UNIQUE (session_id,
    tick)` constraint surfaces `psycopg.errors.UniqueViolation` on
    re-`persist_tick`; the implementation catches it, performs a
    SELECT to fetch the existing payload, compares against the new
    payload, and either returns silently (same) or raises
    `MonotonicityViolationError` (different).
- The `PostgresRuntime` test parametrization is gated behind
  `pytest.mark.integration` (skipped on the default fast gate; runs
  only under `mise run test:integration` per FR-009).
- Synthetic payloads (per research.md §7) are minimal Pydantic-serializable
  dicts. They need not be valid `WorldState` snapshots — US4 tests the
  persistence contract, not engine semantics. This isolates US4 from
  engine regressions covered by Specs 053–055.
- The `multi_tick_sequence_strategy` produces a 5-tick sequence by
  default; each tick's payload differs from the others to make the
  read-after-failed-overwrite assertions distinguishable.
- Payload comparison is on the **canonical-serialized** form (the
  final dict / JSON / bytes that would be written), not the in-memory
  object. This avoids spurious mismatches from non-deterministic
  ordering of dict keys / set iteration / etc.

## Default-Deny + Opt-Out Marker

A persistence backend that legitimately allows full overwrite (none
currently exist; this is exactly the contract being enforced) MUST
flag itself with a class-level marker:

```python
class SomePersistenceBackend:
    bypasses_causal_invariant: ClassVar[dict[str, str]] = {
        "tick_monotonic_idempotent": (
            "Allows overwrite because <reason>. <Mitigation>."
        ),
    }
```

The harness consumes this marker and skips the parametrization for that
backend. **Adding such a marker is a constitutional change** — a
maintainer who adds one is bypassing II.6 + III.7 and should escalate
per Constitution IX governance rules.

## Hypothesis Profile

- Default profile: `max_examples=50`, `derandomize=True` (smaller than
  US1–US3 because each example invokes 5 writes + 5 reads + 2
  re-persist attempts, which is heavier than a single tick run)
- Slow profile: `max_examples=200`
- Integration profile (Postgres): `max_examples=20` (smaller still
  because each example creates a transient DB)
- Settings: `suppress_health_check=[HealthCheck.too_slow,
  HealthCheck.function_scoped_fixture]`
