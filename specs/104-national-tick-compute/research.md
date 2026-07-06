# research-104 — National tick-compute profile + budget

## Pre-implementation verification (2026-07-05)

### per_system_ms wiring

The master plan (project/09 line 573) states "`PerformanceBreakdown.per_system_ms`
exists in `headless_runner/models.py` but is empty — wire it". This is
**outdated**: spec-065 T074 already wired it.

**Evidence**:
- `src/babylon/engine/simulation_engine.py:145` — `self._per_system_ms: dict[str, float] = {}`
- `src/babylon/engine/simulation_engine.py:207-218` — `run_tick` wraps each `system.step()`:
  ```python
  t0 = time.perf_counter()
  try:
      system.step(graph, services, context)
  finally:
      elapsed_ms = (time.perf_counter() - t0) * 1000.0
      self._per_system_ms[system_name] = (
          self._per_system_ms.get(system_name, 0.0) + elapsed_ms
      )
  ```
- `src/babylon/engine/headless_runner/runner.py:979` — `per_system_ms = dict(engine.per_system_ms)`
- `src/babylon/engine/headless_runner/runner.py:997,1018` — passed to `PerformanceBreakdown`
- `src/babylon/engine/headless_runner/models.py:187` — `per_system_ms: dict[str, float] = Field(default_factory=dict)`

### DecompositionSystem carceral-enforcer no-op

The master plan (project/09 line 577) says "Close the DecompositionSystem
carceral-enforcer no-op". This is **already closed** by spec-071.

**Evidence**:
- `src/babylon/engine/systems/decomposition.py:298-313`:
  ```python
  enforcer = _find_entity_by_role(graph, SocialRole.CARCERAL_ENFORCER, include_inactive=True)
  if enforcer is None:
      enforcer = self._create_target_entity(
          graph, SocialRole.CARCERAL_ENFORCER, la_id, la_data, _ENFORCER_ID_OFFSET
      )
  internal_proletariat = _find_entity_by_role(
      graph, SocialRole.INTERNAL_PROLETARIAT, include_inactive=True
  )
  if internal_proletariat is None:
      internal_proletariat = self._create_target_entity(...)
  ```
- Comment at line 295-297: "spec-071, create on demand"

### National scope

`--scope=national` resolves ~3,156 US counties from the SQLite reference DB
(`scopes.py:_load_national_fips`, excluding Pacific territories
`state_fips >= 60` and synthetic `\\d{2}999` placeholders).

## National profile results

### National hex hydration bottleneck

The national 5-tick run (`--scope=national --ticks=5`) **timed out at 10
minutes** during hex hydration — it never reached the tick loop. The
hydrator processes ~3,156 counties, generating ~3.17M h3 cells with
per-county QCEW/BEA lookups. This is the dominant national-scale cost.

The national 20-tick run was started with a 30-minute timeout; results
will be appended if it completes.

### Michigan-statewide 5-tick profile (budget gate scope)

The `qa:tick-budget` gate uses `michigan-statewide-no-canada` (83
counties) for practical CI runtime (~80s total). Measured
2026-07-05:

| Metric | Value |
|--------|-------|
| Total wallclock | 81.8s |
| Session init | 24.9s |
| Hex hydration | 24.9s |
| Tick loop (4 ticks) | 8.2s |
| Per-tick median | 2040.6ms |
| Per-tick p99 | 2336.8ms |

## Per-system wallclock budget

Top 5 hotspots (michigan-statewide, 5 ticks, 4 engine ticks):

| System | Total ms | ms/tick | Budget (2×) |
|--------|---------|---------|-------------|
| ContradictionFieldSystem | 898.8 | 224.7 | 1800.0 |
| FieldDerivativeSystem | 636.4 | 159.1 | 1300.0 |
| ConsciousnessSystem | 516.0 | 129.0 | 1100.0 |
| ContradictionSystem | 409.3 | 102.3 | 850.0 |
| ProductionSystem | 242.5 | 60.6 | 500.0 |

Full budget: `specs/104-national-tick-compute/budget.json` (26 systems,
50% headroom for CI variance).

## Hotspots

1. **ContradictionFieldSystem** (224.7ms/tick) — the dominant cost.
   Worth investigating for caching/batching in a future spec.
2. **FieldDerivativeSystem** (159.1ms/tick) — second hotspot, likely
   related to the contradiction field computation.
3. **ConsciousnessSystem** (129.0ms/tick) — third hotspot.
4. **National hex hydration** (>10min for 3,156 counties) — the
   dominant one-time cost; not a tick-loop cost but blocks the national
   profile. A future spec should optimize hydration (batch QCEW/BEA
   lookups, parallelize county processing).

No pure-perf fixes were applied in this spec — the hotspots need
algorithmic investigation (potential float-math reordering → R-PROOF
path) which is out of scope for the measurement spec.
