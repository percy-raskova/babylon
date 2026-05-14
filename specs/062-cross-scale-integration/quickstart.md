# Quickstart: Cross-Scale Integration

**Feature**: 062-cross-scale-integration
**Audience**: Babylon engine developers integrating with the cross-scale propagation engine
**Diataxis quadrant**: How-To Guide (goal-oriented, assumes Python + Postgres familiarity)

This guide walks through the five most common developer interactions with the cross-scale integration engine: initializing a session, advancing one tick, querying an aggregate, inspecting the audit log, and adding a new reference series.

---

## Prerequisites

```bash
# Postgres is running (per Spec 037 / Constitution X)
mise run web:status   # confirm web stack is up
mise run web:migrate  # apply migrations 0010-0015 (this feature)

# SQLite reference DB exists in canonical location
ls data/sqlite/marxist-data-3NF.sqlite
```

The `pg_pool` test fixture is available in `tests/conftest.py`; integration tests gracefully skip when no test DB is configured.

---

## 1. Initialize a session for the Detroit 2010-2025 scenario

```python
from uuid import UUID
from pathlib import Path
from babylon.persistence.postgres_runtime import PostgresRuntime
from babylon.persistence.postgres_initialization import initialize_session
from babylon.config.defines import GameDefines

defines = GameDefines()  # uses pyproject.toml [tool.babylon] defaults
runtime = PostgresRuntime(pool=...)  # from your psycopg pool

session_id: UUID = runtime.create_session(
    scenario="detroit-2010-2025",
    config_json={
        "start_year": 2010,
        "scenario_length_years": 15,  # FR-004a — immutable for session lifetime
        "study_area": "tri_county",   # Wayne + Oakland + Macomb
    },
    game_defines_json=defines.model_dump(),
    rng_seed=42,
)

# Single-call initialization. Reads SQLite, hydrates ~1700 hexes, copies
# reference series for [2010, 2026], persists to dynamic_* tables, then
# closes the SQLite handle (FR-002).
report = initialize_session(
    session_id=session_id,
    sqlite_path=Path("data/sqlite/marxist-data-3NF.sqlite"),
    runtime=runtime,
    defines=defines,
)

print(f"Hydrated {report.hex_count} hex states")
print(f"Copied reference series: {sorted(report.copied_series)}")
print(f"External nodes: {sorted(report.external_node_ids)}")
# Expected output:
#   Hydrated 1734 hex states
#   Copied reference series: ['basket_gamma', 'bea_io_imports', ...]
#   External nodes: ['canada', 'china', 'eu', 'india', 'latin_america',
#                    'rest_of_usa', 'russia_csi', 'southeast_asia',
#                    'sub_saharan_africa']  # 8 international + 1 domestic
```

After this call, **the SQLite handle is closed**. Any subsequent attempt to read the SQLite file from runtime code is an architectural violation (FR-001).

---

## 2. Advance one tick

```python
from babylon.engine.simulation_engine import SimulationEngine

engine = SimulationEngine(runtime=runtime, defines=defines)

# Hydrate state at current tick.
result = runtime.hydrate_state(session_id=session_id, tick=0)
# result.world_state, result.hex_graph, result.hypergraph
# result.current_simulated_year == 2010

# Advance one tick. The engine runs all 15 systems in materialist causality
# order with Substrate at position 2.5, then computes invariants, then
# commits everything atomically per FR-008a.
new_state = engine.advance_one_tick(
    world_state=result.world_state,
    hex_graph=result.hex_graph,
    hypergraph=result.hypergraph,
    actions=[],  # player actions for this tick
)

# After this returns, dynamic_hex_state, dynamic_external_node_state,
# boundary_flow_register, and conservation_audit_log all reflect tick 1.
# If anything failed, no rows were committed — you can retry from tick 0.

# Verify by querying:
last_committed = runtime.get_last_committed_tick(session_id)
assert last_committed == 1
```

### Crash recovery

```python
# Simulate a crash mid-tick: kill the worker process while engine.advance_one_tick()
# is running. On restart:
last = runtime.get_last_committed_tick(session_id)
print(f"Resume from tick {last + 1}")  # Either tick 0 (if crash before commit)
                                       # or tick 1 (if crash after commit).
# No partial-tick rows are visible; FR-008a per-tick atomicity guarantees this.
```

---

## 3. Query an aggregate

```python
from babylon.persistence.postgres_aggregation import (
    fetch_county_aggregate,
    fetch_state_aggregate,
    fetch_national_aggregate,
    fetch_global_phi_balance,
)

# County total at a specific tick:
wayne_county = fetch_county_aggregate(
    runtime=runtime,
    session_id=session_id,
    tick=137,
    county_fips="26163",  # Wayne County, MI
)
print(f"Wayne County tick 137: c={wayne_county.c_sum}, "
      f"v={wayne_county.v_sum}, s={wayne_county.s_sum}, "
      f"hex_count={wayne_county.hex_count}")

# Verify FR-018: the value equals the offline sum over the hexes.
import psycopg
with runtime.pool.connection() as conn:
    rows = conn.execute(
        "SELECT c, v, s FROM dynamic_hex_state "
        "WHERE session_id = %s AND tick = %s AND county_fips = %s",
        (session_id, 137, "26163"),
    ).fetchall()
manual_c = sum(r[0] for r in rows)
assert abs(manual_c - wayne_county.c_sum) <= 1e-10  # SC-002

# National time-series:
ts = fetch_national_aggregate(
    runtime=runtime,
    session_id=session_id,
    tick_range=(0, 779),
)
print(f"National c trajectory: tick 0 = {ts[0].c_sum}, "
      f"tick 780 = {ts[-1].c_sum}")

# Annual Φ-balance check:
balance = fetch_global_phi_balance(
    runtime=runtime,
    session_id=session_id,
    annual_only=True,  # only year-boundary ticks
)
for row in balance:
    if abs(row.residual) > 1e-10:
        print(f"WARNING: tick {row.tick} Φ residual = {row.residual:.3e}")
```

---

## 4. Inspect the audit log

```python
from babylon.persistence.conservation_audit import ConservationAuditQuery

audit = ConservationAuditQuery(runtime=runtime)

# Quick health check after a run:
counts = audit.count_by_severity(session_id, tick_range=(0, 779))
print(counts)
# Expected on a clean run: {'ok': N, 'warn': 0, 'alarm': 0}

# Find the first alarm if any:
first_alarm = audit.fetch(
    session_id=session_id,
    severity="alarm",
)
if first_alarm:
    a = first_alarm[0]
    print(f"First alarm: tick {a.tick}, scale={a.scale}, "
          f"invariant={a.invariant_name}, residual={a.residual:.3e}")
    print(f"Determinism hash: {a.determinism_hash}")
    # Use the hash for replay-from-this-tick debugging (Constitution III.7).

# Time-series for one invariant:
hex_to_county = audit.fetch(
    session_id=session_id,
    invariant_name="hex_to_county_sum_c",
)
import statistics
residuals = [abs(r.residual) for r in hex_to_county]
print(f"Max |residual|: {max(residuals):.3e}")
print(f"Median |residual|: {statistics.median(residuals):.3e}")
```

### Subscribing to alarm events (per FR-047 / Clarification Q3)

```python
from babylon.engine.observer import SimulationObserver

class AlarmBanner(SimulationObserver):
    def on_conservation_alarm(self, event):
        print(f"⚠️  ALARM: tick {event.tick} {event.invariant_name} "
              f"residual={event.residual:.3e}")

engine.attach_observer(AlarmBanner())
# Now alarm-severity rows will print as the simulation advances.
# The tick does NOT pause; observers are passive subscribers.
```

---

## 5. Add a new immutable reference series

```python
# 1) Add the SeriesDescriptor to GameDefines.coefficient_lookup_policies.
#    This documents the lookup policy and federal data class.
defines.coefficient_lookup_policies["my_new_series"] = CoefficientLookupPolicy(
    series_id="my_new_series",
    policy=LookupPolicy.SLOWLY_VARYING,
    canonical_reference="My Federal Agency Series 2010-2024",
)

# 2) Create a Postgres migration adding the immutable_reference_my_new_series table.
#    See migrations/0010_immutable_reference_tables.sql for the pattern.

# 3) Extend `babylon.persistence.postgres_initialization.copy_reference_series`
#    to read from the appropriate SQLite table and INSERT into the new
#    immutable_reference_my_new_series Postgres table.

# 4) Add typed access via ImmutableReferenceLookup:
class MyNewSeriesValue(BaseModel):
    model_config = ConfigDict(frozen=True)
    coefficient: float

# 5) Existing systems can now consume the new series:
from babylon.persistence.postgres_reference import ImmutableReferenceLookup

lookup = ImmutableReferenceLookup(runtime=runtime, session_id=session_id)
result = lookup.get(series_id="my_new_series", tick=137)
print(f"my_new_series at tick 137: {result.value} "
      f"(method: {result.lookup_method}, "
      f"bracketing_years: {result.bracketing_years})")
```

### Constitutional checklist for a new series

Before merging:

- [ ] Series is in `data-catalog.yaml` (Constitution III.4.1)
- [ ] Series is classified as Runtime or Fixture (Constitution III.4.2)
- [ ] Lookup policy chosen (slowly_varying or event_discrete) and documented
- [ ] Source SQLite table populated with all years required by the test scenario
- [ ] Postgres migration adds `REVOKE INSERT, UPDATE, DELETE FROM <runtime_role>` to the new table
- [ ] Hypothesis property test added: lookup at tick `t` returns the policy-correct value

---

## Where to look next

- **Spec**: `specs/062-cross-scale-integration/spec.md`
- **Data model**: `specs/062-cross-scale-integration/data-model.md`
- **Contracts**: `specs/062-cross-scale-integration/contracts/`
- **Phase 0 research**: `specs/062-cross-scale-integration/research.md`
- **Per-tick pipeline ordering**: ADR032 (in `ai-docs/decisions/`)
- **Postgres runtime conventions**: Spec 037 (`specs/037-postgres-runtime-db/`)
- **Conservation invariants test harness**: Specs 053-056 (Hypothesis-based)

## Common pitfalls

- ❌ Reading `marxist-data-3NF.sqlite` from a runtime code path. Violates FR-001. Use `ImmutableReferenceLookup` against the Postgres copy instead.
- ❌ Persisting county/state/national `c_sum` aggregates as primary state. Violates FR-019. Always derive on read via the `v_*` views.
- ❌ Mutating a `conservation_audit_log` row after commit. Violates FR-049. Postgres GRANT enforces this at the DB level.
- ❌ Using `δ_annual / 52` as the per-tick depreciation rate. Violates FR-014. Use `1 - (1 - δ_annual)^(1/52)` (geometric weekly).
- ❌ Treating `start_year` as mutable mid-session. Violates FR-004a. The session contract is fixed at creation.
- ❌ Treating the `Rest-of-USA` boundary node as the destination for Canada-bound flows. Violates Constitution IV.1 — Canada is a first-class international boundary node per the R4 amendment to FR-036.
