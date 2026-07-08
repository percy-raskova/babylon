# Implementation Brief — `fix/engine-determinism` (Phase 2.3)

Constitution III.7 violations in the engine: one unseeded RNG roll, one unseeded resilience purge, three wall-clock timestamp factories, and an EventBus fan-out with no handler isolation. All fixes are **baseline-affecting** — `qa:regression`, `tests/scenarios/`, and the SC-006 trace artifacts are reconciled in **Phase 2.R, not here**. Base the branch on `dev` (verified at `9101dddf`).

---

## 1. Verified seams (exact current code)

### 1a. Unseeded `random.random()` — `src/babylon/engine/systems/struggle.py:312`

```python
310            # Step 1: Calculate and roll for EXCESSIVE_FORCE spark
311            spark_probability = repression * spark_scale
312            spark_occurred = random.random() < spark_probability
```

`import random` is at struggle.py:34. This is the **only** unseeded engine roll — `rg 'random\.random\(\)' src/babylon/engine src/babylon/formulas src/babylon/models` returns only this line. The spec-071 riot path in the same file is already a deterministic gate (struggle.py:436-438: "a gate, not a stochastic roll — … III.7 determinism holds without RNG"). `tick` is in scope: `tick = context.get("tick", 0)` at struggle.py:278 (works for both dict and `TickContext`, which defines `.get` at `src/babylon/engine/context.py:100`).

**Canonical `_resolve_rng` pattern** — defined identically in TWO system modules:

`src/babylon/engine/systems/faction_influence.py:273-285`:
```python
def _resolve_rng(services: ServiceContainer, tick: int) -> random.Random:
    """Resolve an RNG.

    Prefers ``services.rng`` if present; otherwise derives a
    seed-deterministic Random instance from the tick number. The
    fallback path keeps tests + plain harness runs working without
    requiring the spec-037 RNG infrastructure.
    """

    rng = getattr(services, "rng", None)
    if isinstance(rng, random.Random):
        return rng
    return random.Random(0xBA1AC1A + tick)
```

Canonical usage, `faction_influence.py:61-64`:
```python
        tick = _extract_tick(context)
        persistent = _extract_persistent(context)
        defines = _resolve_defines(services)
        rng = _resolve_rng(services, tick)
```

Duplicate at `src/babylon/engine/systems/reactionary.py:369-378` (used at :238), whose docstring self-identifies the precedent: `"Prefers ``services.rng``; else the ``random.Random(0xBA1AC1A + tick)`` fallback used by :mod:`babylon.engine.systems.faction_influence`."` Note: **`services.rng` is never set anywhere** — `ServiceContainer` (`src/babylon/engine/services.py`) has no `rng` field; the `getattr` branch is dead-but-harmless and the tick-seeded fallback is the only live path.

### 1b. `check_resilience` seed omitted — `src/babylon/engine/topology_monitor.py`

Signature (:182-187) and RNG (:218):
```python
182 def check_resilience(
183     G: GraphProtocol,
184     removal_rate: float | None = None,
185     survival_threshold: float | None = None,
186     seed: int | None = None,
187 ) -> ResilienceResult:
...
218     rng = random.Random(seed)
```

Caller (:477-482) omits `seed`, so `random.Random(None)` seeds from OS entropy:
```python
477        is_resilient: bool | None = None
478        if self._resilience_interval > 0:
479            tick = state.tick
480            if is_start or (tick > 0 and tick % self._resilience_interval == 0):
481                result = check_resilience(graph, removal_rate=self._removal_rate)
482                is_resilient = result.is_resilient
```

This is the **only** src caller with seed omitted (all other callers are tests, which pass seeds explicitly). `tick` is already in scope at :479. Fix = `seed=tick`.

### 1c. Wall-clock timestamps (3 sites)

`src/babylon/engine/event_bus.py:44-47` (frozen dataclass):
```python
44    type: str
45    tick: int
46    payload: dict[str, Any]
47    timestamp: datetime = field(default_factory=datetime.now)
```

`src/babylon/engine/interceptor.py:85-92` (frozen dataclass; constructed at exactly one src site, event_bus.py:181-185, where `event.tick` is available):
```python
85 @dataclass(frozen=True)
86 class BlockedEvent:
87     """Audit record for blocked events."""
88
89     event: Event
90     interceptor_name: str
91     reason: str
92     blocked_at: datetime = field(default_factory=datetime.now)
```

`src/babylon/models/events/_legacy.py:99-102` (frozen Pydantic base for ALL 30+ typed SimulationEvents):
```python
 99    timestamp: datetime = Field(
100        default_factory=datetime.now,
101        description="Wall-clock time when event was created",
102    )
```

**Downstream consumers (traced):**
- `src/babylon/engine/simulation_engine.py:452` — `timestamp = event.timestamp`, then threaded into every typed Pydantic event in `_convert_bus_event_to_pydantic` (14 `timestamp=timestamp` construction sites, :459-597) → `WorldState.events` (:756).
- `src/babylon/engine/observers/persistence_observer.py:203` and `src/babylon/engine/observers/session_recorder.py:227` — `event.model_dump(mode="json")` → timestamps land in persisted run artifacts, poisoning run-to-run diffs.
- `web/game/engine_bridge.py:791/:831` — `event.model_dump()` (no `mode="json"`) into session `snapshot_json` — this is Phase 1.1's datetime-500 blast radius (fix stays in 1.1: the timestamp remains a `datetime` after this branch; note `engine_bridge.py:3168` already `exclude={"event_type", "tick", "timestamp"}` for tick_event rows).
- `src/babylon/engine/topology_monitor.py:505-514` constructs `PhaseTransitionEvent` **without** a timestamp → hits the `_legacy.py` default — covered by fix below.

**Tick-derived scheme (matches existing convention):** weekly ticks with `year = start_year + tick // 52` is codified at `src/babylon/config/defines/cross_scale.py:31` ("``start_year + (t // 52)`` (FR-013)") and `src/babylon/engine/headless_runner/bridge.py:165` (`self._start_year: int = 2010`), `:969` (`year = self._start_year + tick // 52`). So: `sim_datetime(tick) = datetime(2010 + tick // 52, 1, 1, tzinfo=UTC) + timedelta(weeks=tick % 52)`.

### 1d. EventBus handler fan-out — `src/babylon/engine/event_bus.py:212-220`

```python
212    def _emit_to_handlers(self, event: Event) -> None:
213        """Emit event to all subscribed handlers.
214
215        Args:
216            event: The event to emit.
217        """
218        handlers = self._subscribers.get(event.type, [])
219        for handler in handlers:
220            handler(event)
```

Confirmed: one raising handler aborts the loop → remaining handlers starve → exception propagates through `publish` → `System.step` → `SimulationEngine.run_tick` (which has NO catch around `system.step`, simulation_engine.py:213-219 is `try/finally` for timing only) → tick dies. Note history is appended **before** fan-out (publish :142-143 fast path, :151-152 slow path), so history is not lost — only downstream handlers.

### 1e. Determinism-check reuse inventory (C.2a)

- `compute_determinism_hash` — `src/babylon/persistence/conservation_audit.py:70-111`: `SHA-256 over canonical(tick + sorted hex_state + actions + rng_seed)`, canonicalized via `json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)` (:110). Reuse its **canonicalization idiom**, not the function (it requires hex rows/rng_seed).
- `tick_commit` III.7 hash chain — `src/babylon/persistence/postgres_runtime/_spec_062.py:142-146` + `migrations/0029_tick_commit.sql`: Postgres-only, unusable for an in-process fast-gate test.
- `tests/integration/mvp/test_determinism.py` — in-process A/B exists but only compares `profit_rate` on the MVP `Simulation` facade (events/timestamps never checked).
- `tests/integration/test_baseline_determinism.py::test_sc006_recent_regens_epsilon_deterministic` — artifact-based (skips without two 520-tick trace.csv regens, :62-67). **Stays skipped**; it becomes satisfiable at Phase 2.R regen.
- Scenario builder for the A/B test: `create_imperial_circuit_scenario()` (`src/babylon/engine/scenarios/_legacy.py:239`, exported from `babylon.engine.scenarios`) returns `(WorldState, SimulationConfig, GameDefines)`; drive it with `step()` (`src/babylon/engine/simulation_engine.py:649-655`).

---

## 2. Implementation steps (one commit per unit, `mise run commit -- "..."`)

### Step 1 — `src/babylon/sim_clock.py` (NEW leaf module) + tests

`babylon/__init__.py` is a light leaf (version only), so a top-level module is importable from BOTH `engine.event_bus`/`engine.interceptor` (which must not import the heavy `babylon.models` package — the models→formulas.balkanization circular-import gotcha) AND `models/events/_legacy.py`. No name clash (`rg sim_clock` → empty).

```python
"""Deterministic simulation clock (Constitution III.7).

Maps a weekly tick to a canonical in-world datetime so timestamps are a
pure function of tick, never of wall clock. Year mapping mirrors FR-013
(``year = start_year + tick // 52`` — see config/defines/cross_scale.py:31
and engine/headless_runner/bridge.py:969); tick-0 year matches the
headless bridge default (bridge.py:165).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Final

SIM_EPOCH_YEAR: Final[int] = 2010
WEEKS_PER_YEAR: Final[int] = 52

#: Sentinel meaning "derive from tick" — frozen dataclass/model defaults
#: cannot see sibling fields, so construction sites leave this in place
#: and ``__post_init__`` / the before-validator replaces it.
UNSET_TIMESTAMP: Final[datetime] = datetime.min.replace(tzinfo=UTC)


def sim_datetime(tick: int) -> datetime:
    """Return the deterministic in-world datetime for ``tick``. ..."""
    if tick < 0:
        raise ValueError(f"tick must be >= 0, got {tick}")
    year = SIM_EPOCH_YEAR + tick // WEEKS_PER_YEAR
    return datetime(year, 1, 1, tzinfo=UTC) + timedelta(weeks=tick % WEEKS_PER_YEAR)
```

RED-first tests `tests/unit/test_sim_clock.py`: `sim_datetime(0) == datetime(2010,1,1,tzinfo=UTC)`; `sim_datetime(52).year == 2011` (FR-013 alignment); purity (`sim_datetime(7) == sim_datetime(7)`); `ValueError` on negative tick. Full RST docstrings (Sphinx `-W`).

### Step 2 — tick-derived timestamps (3 sites)

**event_bus.py** — replace :47 and add `__post_init__`; drop the now-unused `field` import if nothing else uses it (`payload` has no factory — check: only :47 uses `field`; keep `dataclass` import):

```python
from babylon.sim_clock import UNSET_TIMESTAMP, sim_datetime
...
    type: str
    tick: int
    payload: dict[str, Any]
    timestamp: datetime = UNSET_TIMESTAMP

    def __post_init__(self) -> None:
        if self.timestamp is UNSET_TIMESTAMP:
            object.__setattr__(self, "timestamp", sim_datetime(self.tick))
```
Update the class docstring's `timestamp:` line (:41 "Wall-clock time…" → "Deterministic sim-time derived from tick (Constitution III.7)").

**interceptor.py:92** — same sentinel pattern, deriving from the wrapped event's tick (available at the sole construction site, event_bus.py:181):
```python
    blocked_at: datetime = UNSET_TIMESTAMP

    def __post_init__(self) -> None:
        if self.blocked_at is UNSET_TIMESTAMP:
            object.__setattr__(self, "blocked_at", sim_datetime(self.event.tick))
```
(`self.event` is a runtime attribute; the TYPE_CHECKING-only `Event` import at :19-20 is untouched.)

**models/events/_legacy.py:99-102** — Pydantic frozen model, so use a before-validator (imports: add `Any` to :63, `model_validator` to :65, `from babylon.sim_clock import UNSET_TIMESTAMP, sim_datetime`):

```python
    timestamp: datetime = Field(
        default=UNSET_TIMESTAMP,
        description="Deterministic sim-time derived from tick (Constitution III.7)",
    )

    @model_validator(mode="before")
    @classmethod
    def _derive_timestamp_from_tick(cls, data: Any) -> Any:
        """III.7: default timestamps are a pure function of tick."""
        if isinstance(data, dict):
            ts = data.get("timestamp")
            if ts is None or ts is UNSET_TIMESTAMP:
                data = dict(data)
                data["timestamp"] = sim_datetime(int(data.get("tick", 0)))
        return data
```

Explicit timestamps are preserved everywhere (so `simulation_engine.py:452/459-597` passthrough and `tests/unit/engine/test_event_conversion.py:312-328 test_preserves_timestamp` keep working unchanged).

**RED-first tests:**
- REWRITE `tests/unit/engine/test_event_bus.py:30-38` (it asserts a wall-clock window `before <= event.timestamp <= after` — it WILL fail post-fix). Replacement: `Event(type="test", tick=3, payload={})` twice → `e1.timestamp == e2.timestamp == sim_datetime(3)`. This replacement is red at HEAD (wall-clock differs from `sim_datetime(3)`).
- NEW in `tests/unit/engine/test_interceptor.py`: publish through a blocking interceptor with `tick=7` → `bus.get_blocked_events()[0].blocked_at == sim_datetime(7)` (existing :507 `blocked.blocked_at is not None` keeps passing).
- NEW in `tests/unit/models/test_events.py`: two `SparkEvent(tick=5, node_id="C001", repression=0.5, spark_probability=0.05)` → equal timestamps `== sim_datetime(5)` (existing :73-76 isinstance check keeps passing).

### Step 3 — struggle RNG (extract `resolve_rng`, DRY: third consumer)

Add to `src/babylon/engine/systems/base.py` as a module-level function (runtime `import random`, `Final`; `ServiceContainer` already TYPE_CHECKING-imported at :25):

```python
_SYSTEM_RNG_SEED_SALT: Final[int] = 0xBA1AC1A


def resolve_rng(services: ServiceContainer, tick: int) -> random.Random:
    """Seed-deterministic RNG for stochastic System rolls (III.7).

    Prefers ``services.rng`` when a harness injects one; otherwise a
    fresh ``random.Random(0xBA1AC1A + tick)`` — the spec-070 fallback
    previously duplicated by :mod:`~babylon.engine.systems.faction_influence`
    and :mod:`~babylon.engine.systems.reactionary`.
    """
    rng = getattr(services, "rng", None)
    if isinstance(rng, random.Random):
        return rng
    return random.Random(_SYSTEM_RNG_SEED_SALT + tick)
```

Then:
- **struggle.py**: after :278 (`tick = context.get("tick", 0)`) add `rng = resolve_rng(services, tick)`; change :312 to `spark_occurred = rng.random() < spark_probability`; remove the orphaned `import random` at :34; import `resolve_rng` alongside the existing `from babylon.engine.systems.base import SystemBase` at :45.
- **faction_influence.py**: delete local `_resolve_rng` (:273-285), change :64 to `rng = resolve_rng(services, tick)`, extend the existing base import (:30).
- **reactionary.py**: delete local `_resolve_rng` (:369-378), change :238, extend base import, and update the module-docstring reference at :31 (`seed RNG (:func:`_resolve_rng`).`).
- Behavior of the two existing systems is **byte-identical** (same seed constant, same fallback); only struggle changes trajectory.
- Decision point (document in commit body): all three systems now share one per-tick stream (each from its own fresh instance, so no cross-consumption interference; roll→node assignment is stable because BabylonGraph iteration is deterministic per Amendment L). Per-system seed salts are a possible 2.R refinement — do NOT add speculatively.

**RED-first test** (`tests/unit/engine/systems/test_struggle.py`, new): prove the roll ignores global RNG state. Reference rolls: `random.Random(1).random()=0.13436…`, `random.Random(2).random()=0.95603…`, `random.Random(0xBA1AC1A + 1).random()=0.13636…`.

```python
    def test_spark_roll_ignores_global_random_state(self) -> None:
        """III.7: spark outcome is a pure function of tick, not global RNG."""
        import random as global_rng

        from babylon.config.defines import GameDefines, StruggleDefines

        outcomes: list[int] = []
        for seed in (1, 2):  # global rolls 0.134 vs 0.956 straddle prob=0.5
            custom = StruggleDefines(spark_probability_scale=0.5)
            svc = ServiceContainer.create(defines=GameDefines(struggle=custom))
            graph = _create_minimal_struggle_graph(repression=1.0, agitation=0.0)
            captured: list = []
            svc.event_bus.subscribe(EventType.EXCESSIVE_FORCE, lambda e, c=captured: c.append(e))
            global_rng.seed(seed)
            StruggleSystem().step(graph, svc, {"tick": 1})
            outcomes.append(len(captured))
            svc.database.close()

        assert outcomes[0] == outcomes[1]
```
RED at HEAD (spark_prob=0.5: seed 1 sparks, seed 2 doesn't → 1 != 0); GREEN after (both = `Random(0xBA1AC1A+1).random()=0.136 < 0.5` → spark).

**Existing-test updates (same commit):**
- `test_spark_probability_is_repression_times_scale` (:357-380): derive the roll from the new mechanism — `expected_roll = resolve_rng(services, tick=1).random()` (=0.13636 > 0.05 → still no spark; same assertions), delete the `rng.seed(42)` lines.
- Delete now-inert `rng.seed(42)` / `random.seed(...)` lines at test_struggle.py:327, 365-366, 375, 404, 430, 475 and test_struggle_volatility.py:49, 64, 71, 81 (+ stale first-roll comments). Verified the volatility assertions survive: at tick=3 the new roll is `0.01614 < 0.05` so a spark now FIRES for the lumpen node, but SPONTANEOUS_RIOT counts, wealth destruction, and the no-solidarity-edges assertions are all unaffected (no SOLIDARITY edges exist in those fixtures; riot gate is independent of the spark). Re-run to confirm.

### Step 4 — topology monitor seed

`topology_monitor.py:481`:
```python
            if is_start or (tick > 0 and tick % self._resilience_interval == 0):
                # III.7: seed by tick so the purge sample is a pure
                # function of simulation state, not process entropy.
                result = check_resilience(graph, removal_rate=self._removal_rate, seed=tick)
```

**RED-first test** (`tests/unit/topology/test_topology_monitor.py`): monkeypatch `babylon.engine.topology_monitor.check_resilience` with a spy returning a stub `ResilienceResult(is_resilient=True, original_max_component=0, post_purge_max_component=0, removal_rate=0.2, survival_threshold=0.5, seed=kwargs.get("seed"))`; build `TopologyMonitor(resilience_test_interval=1)`; take any solidarity-bearing `WorldState` (e.g. `create_two_node_scenario()[0]`) and `model_copy(update={"tick": 4})`; call `monitor.on_tick_complete(state, state)` (signature at :425-436 is `(_previous_state, new_state)` — pass the state twice); assert `captured_kwargs[0]["seed"] == 4`. RED at HEAD (`"seed" not in kwargs`).

### Step 5 — EventBus handler isolation

Replace `_emit_to_handlers` (:212-220). Policy: **isolate the fan-out, then fail loud** — every handler receives the event; every failure is `logger.exception`-logged; failures re-raise as an `ExceptionGroup` after the loop (Python 3.12; matches CLAUDE.md "Let exceptions bubble up in the Logic layer" and the no-silent-swallow constitution rule). Ruff select is `E,W,F,I,B,C4,C90,UP,ARG,SIM` (pyproject.toml:224-235) — `except Exception` needs no noqa (BLE not enabled).

```python
    def _emit_to_handlers(self, event: Event) -> None:
        """Emit event to all subscribed handlers.

        Handler isolation (Constitution III.7): every subscribed handler
        receives the event even when an earlier handler raises. Failures
        are logged via ``logger.exception`` and re-raised together AFTER
        the fan-out completes — isolation without silent swallowing.

        Args:
            event: The event to emit.

        Raises:
            ExceptionGroup: If one or more handlers raised.
        """
        handlers = self._subscribers.get(event.type, [])
        failures: list[Exception] = []
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # isolation fan-out; re-raised below
                logger.exception(
                    "Event handler %r failed for event type %s (tick %d)",
                    handler,
                    event.type,
                    event.tick,
                )
                failures.append(exc)
        if failures:
            raise ExceptionGroup(
                f"{len(failures)} event handler(s) failed for {event.type}",
                failures,
            )
```

**RED-first tests** (`tests/unit/engine/test_event_bus.py`, new `TestHandlerIsolation`):
1. bad handler + good handler subscribed to same type → `pytest.raises(ExceptionGroup)`, `calls == ["good"]` (RED at HEAD: raw `ValueError` propagates and good handler never runs), inner exception is the original `ValueError`.
2. failure logged: `caplog.at_level(logging.ERROR, logger="babylon.engine.event_bus")` → record present.
3. all-green fan-out raises nothing (existing :80-99 also covers).
4. history still contains the event after a failing fan-out (`bus.get_history()` — documents the append-before-emit ordering at :142-143).

### Step 6 — C.2(a) in-process determinism A/B gate

NEW `tests/unit/engine/test_determinism_ab.py` (runs in the fast gate; precedent: `tests/unit/engine/test_imperial_circuit_scenario.py` already drives this scenario in unit scope):

```python
"""C.2(a): in-process determinism A/B gate (Constitution III.7).

Two 10-tick runs of the imperial-circuit scenario — with the global RNG
deliberately seeded differently — must produce identical per-tick event
streams (hash equality, timestamps included) and identical final states.
Canonicalization mirrors compute_determinism_hash
(persistence/conservation_audit.py:110): sorted-key compact JSON, sha256.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any

import pytest

from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation_engine import step
from babylon.models import WorldState

pytestmark = pytest.mark.unit

_TICKS = 10  # fixed upper bound


def _run(global_seed: int) -> tuple[list[str], WorldState]:
    random.seed(global_seed)  # prove the engine never consults global RNG
    state, config, defines = create_imperial_circuit_scenario()
    ctx: dict[str, Any] = {}
    tick_hashes: list[str] = []
    for _ in range(_TICKS):
        state = step(state, config, persistent_context=ctx, defines=defines)
        canon = json.dumps(
            [e.model_dump(mode="json") for e in state.events],
            sort_keys=True,
            separators=(",", ":"),
        )
        tick_hashes.append(hashlib.sha256(canon.encode("utf-8")).hexdigest())
    return tick_hashes, state


def test_two_runs_produce_identical_event_hashes_and_final_state() -> None:
    hashes_a, final_a = _run(global_seed=1234)
    hashes_b, final_b = _run(global_seed=5678)

    assert hashes_a == hashes_b, (
        f"per-tick event-hash divergence at tick(s) "
        f"{[i for i, (a, b) in enumerate(zip(hashes_a, hashes_b, strict=True)) if a != b]}"
    )
    assert final_a.model_dump(mode="json") == final_b.model_dump(mode="json")
```

RED at HEAD with certainty (wall-clock timestamps differ between runs at microsecond resolution) and independently guards the struggle RNG (divergent global seeds). GREEN only when Steps 2+3 are both in. Note the per-tick `uuid4` correlation_id (simulation_engine.py:203) is log-scope only and does not enter state. Because pre-commit hooks run staged tests, keep each step's red test uncommitted until its fix turns it green; commit test+fix together (project convention).

---

## 3. Test inventory

**Existing coverage (must stay green):** `tests/unit/engine/test_event_bus.py` (except :30-38, rewritten), `test_interceptor.py` (:507 unaffected), `test_event_conversion.py` (:312-328 explicit-timestamp passthrough), `tests/unit/models/test_events.py` (:73-76), `tests/unit/engine/systems/test_struggle.py` + `test_struggle_volatility.py` (seed lines removed, one test rewritten, all assertions verified to hold under the new rolls), `tests/unit/topology/test_topology_monitor.py` (:254-315 all pass explicit seeds), `tests/integration/system/test_topology_integration.py` (explicit seeds), `tests/integration/mvp/test_determinism.py`, `tests/unit/engine/test_jackson_bifurcation.py` (deterministic paths).

**Skipped tests:** `tests/integration/test_baseline_determinism.py` stays skipped on this branch — it un-skips itself in Phase 2.R when two fresh 520-tick regens exist. No other skips in the affected files.

**New/rewritten (all red-first):** see Steps 1-6.

---

## 4. Verification commands

```bash
# Per-step scoped (fast inner loop):
poetry run pytest tests/unit/test_sim_clock.py -q
poetry run pytest tests/unit/engine/test_event_bus.py tests/unit/engine/test_interceptor.py \
  tests/unit/engine/test_event_conversion.py tests/unit/models/test_events.py -q
poetry run pytest tests/unit/engine/systems/test_struggle.py \
  tests/unit/engine/systems/test_struggle_volatility.py -q
poetry run pytest tests/unit/topology/ tests/integration/system/test_topology_integration.py -q
poetry run pytest tests/unit/engine/test_determinism_ab.py -q
# or: mise run test:q -- <paths>   (then mise run test:failed for --lf)

# Cross-cutting sweeps (systems that share the bus / events / rng):
poetry run pytest tests/unit/engine/ tests/unit/models/ -q
mise run check:quick        # ruff lint + format + mypy strict (no test leg)
mise run check              # full fast gate incl. test:unit
mise run test:scenario      # EXPECT possible shifts — record, defer reconciliation to 2.R
mise run qa:regression      # EXPECT RED (baseline-affecting) — do NOT regen here
```

---

## 5. Baseline impact (defer ALL regen to Phase 2.R)

Every fix here is baseline-affecting: (1) struggle spark rolls change from process-entropy to `Random(0xBA1AC1A + tick)` — this is the memory-documented 3897-vs-3915 tick-survival divergence root cause; `tests/baselines/*.json` were generated with **no seeding at all** (`tools/regression_test.py` contains zero `seed` references), so `qa:regression` diffs are expected and `tests/scenarios/` outcomes may flip; (2) timestamps in persisted event JSON change shape (tz-aware, tick-derived); (3) resilience `is_resilient` flags in snapshots may flip. Do NOT run `qa:regression-generate` or `sim:e2e-michigan` regen on this branch — Phase 2.R does the coordinated regen + proof.md, at which point `test_sc006_recent_regens_epsilon_deterministic` becomes runnable and the A/B gate from Step 6 protects it permanently. Out of scope (metadata-only wall clocks, do not touch): `metrics/collector.py:96`, `engine/observers/metrics.py:209`, `engine/history/io.py:155`, `utils/recorder.py`, `headless_runner/runner.py:941/1143`, `persistence/conservation_audit.py:346` (`created_at_utc` is not part of the determinism hash), RAG `time.time()` timing.
