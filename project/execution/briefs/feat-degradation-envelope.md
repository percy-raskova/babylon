# Phase 3.1 `feat/degradation-envelope` — C.6 silent-degradation policy + C.7 stub-bridge visibility

Everything below verified against dev HEAD 3371dc8c (2026-07-08). All paths absolute-relative to /home/user/projects/game/babylon.

---

## (a) C.6 — Inventory of except-Exception→empty-200 blocks

`rg -n "except Exception" web/game/engine_bridge.py` finds **19** blocks (plan said ~17). Full migration table; endpoint = what the swallowed failure silently blanks:

| # | Line | Site | Feeds | Current fallback | Action |
|---|------|------|-------|------------------|--------|
| 1 | engine_bridge.py:122 | `_fetch_session_rng_seed_from_pool` | POST /resolve/ (called :1975) | `return 0` seed | inline `record_degradation("session_rng_seed", exc)` — CRITICAL: silently breaks replay determinism, worse than empty-list |
| 2 | :143 | `_fetch_session_game_defines` | POST /resolve/ (:1970) | `GameDefines()` | inline record (multiple fallback returns incl. JSONDecodeError :152-154 — decorator doesn't fit) |
| 3 | :204 | `_fetch_contradiction_field_rows` | GET /contradiction/ (api.py:634) | `[]` | `@degrades("contradiction_field_rows", list)` |
| 4 | :312 | `_fetch_boundary_flow_series` | GET /trade/flows/ (api.py:691) | `[]` | `@degrades("boundary_flow_series", list)` |
| 5 | :361 | `_fetch_county_boundary_flows` | GET /counties/{fips}/exposure (api.py:708) | `[]` | `@degrades("county_boundary_flows", list)` |
| 6 | :415 | `_fetch_external_node_latest` | trade flows+panel | `{}` | `@degrades("external_node_latest", dict)` |
| 7 | :449 | `_fetch_county_exposure_weights` | exposure | `{}` + logger.debug | wrap `@degrades("county_exposure_weights_pending", dict)` — spec-100 table absent BY DESIGN; distinct op-name so /health/detail shows it as known-pending, not a fault |
| 8 | :496 | `_fetch_flow_type_totals` | GET /trade/panel/ (api.py:729) | `[]` | `@degrades("flow_type_totals", list)` |
| 9 | :541 | `_compute_avg_node_attr` | contradiction snapshot :1536-1537, endgame :1573-1574 | `return default` — **NO LOG today** | inline record ("avg_node_attr") |
| 10 | :561 | `_count_edges_by_mode` | :1538 | `return 0` — **NO LOG today** | inline record ("edge_mode_count") |
| 11 | :995 | balkanization block in `get_map_snapshot` | GET /map/ (api.py:424) | omits metadata key | keep partial try, add record ("map_balkanization") |
| 12 | :1115 | `get_game_timeseries` query | GET /timeseries/ (api.py:509) | `rows=[]` | inline record ("timeseries_query") |
| 13 | :1340 | `get_journal_dashboard` | GET /journal/ (api.py:588) | `rows=[]` | inline record ("journal_query") |
| 14 | :1366 | `get_alerts_dashboard` | GET /alerts/ (api.py:600) | `rows=[]` | inline record ("alerts_query") |
| 15 | :3243 | `_serialize_event` model_dump | snapshot events | `data={}` | keep defensive, add record ("event_serialize") |
| 16 | :3333 | `_persist_tick_events_safe` | resolve write path | no-op → journal permanently dark | inline record ("persist_tick_events") — keep never-raise contract |
| 17 | :3425 | `_persist_hex_state_safe` | resolve/create write path | no-op → map permanently dark | inline record ("persist_hex_state") — keep never-raise |
| 18 | :3813 | `_persist_action_result` ORM fallback | results page | logger.warning | inline record ("persist_action_result") |
| 19 | :3854 | `init_persistence` init_schema | boot | logger.warning | keep warn + record ("schema_init"); boot health already shows boot_attempts (apps.py:37) |

Out of scope (already loud or non-web): api.py:1077 (`resolve_tick` — restores status + returns **500**, correct); apps.py:100 (boot retry → sys.exit(1), correct); stub_bridge.py:464 (warns, stub-only); stub_bridge.py:721-722 is a bare `except Exception: pass` — add a one-line logger.warning while there. Delete the per-site `# noqa: BLE001` comments as each block migrates; the decorator carries the single sanctioned one.

## `@degrades` decorator design — NEW file `web/game/degradation.py`

Counter storage choice: **per-process, threading.Lock-guarded dicts + a per-request ContextVar**. Precedents: `_session_action_history` module dict (engine_bridge.py:39), `GameConfig.last_boot_attempts` class attr (apps.py:37), `HealthDetailView._last_tick_cache` (health/views.py:97). No Redis/DB — /health/detail already reports per-process diagnostics; multi-worker split is documented, not solved. ContextVar is per-thread-safe under sync Django (one request per thread), reset per request in middleware.

```python
"""C.6 degradation policy — the ONE sanctioned blind-except in web/ (REMEDIATION_PLAN C.6)."""

from __future__ import annotations

import functools
import logging
import threading
from collections.abc import Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

_P = ParamSpec("_P")
_R = TypeVar("_R")

_LOCK = threading.Lock()
_COUNTS: dict[str, int] = {}
_LAST: dict[str, dict[str, str]] = {}
_PROCESS_STARTED_AT = datetime.now(UTC).isoformat()

_REQUEST_DEGRADED: ContextVar[tuple[str, ...]] = ContextVar("babylon_degraded_ops", default=())


def record_degradation(operation: str, exc: BaseException) -> None:
    """Log loudly, bump the per-process counter, tag the current request."""
    logger.error("DEGRADED %s: %s", operation, exc, exc_info=exc)
    with _LOCK:
        _COUNTS[operation] = _COUNTS.get(operation, 0) + 1
        _LAST[operation] = {
            "last_at": datetime.now(UTC).isoformat(),
            "last_error": type(exc).__name__,
        }
    _REQUEST_DEGRADED.set((*_REQUEST_DEGRADED.get(), operation))


def degrades(
    operation: str, fallback: Callable[[], _R]
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """Replace an except-Exception→empty-200 block with a counted, logged fallback."""
    def decorator(func: Callable[_P, _R]) -> Callable[_P, _R]:
        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 — C.6: the one sanctioned catch-all
                record_degradation(operation, exc)
                return fallback()
        return wrapper
    return decorator


def request_degradations() -> tuple[str, ...]:
    return _REQUEST_DEGRADED.get()


def reset_request_degradations() -> None:
    _REQUEST_DEGRADED.set(())


def degradation_snapshot() -> dict[str, Any]:
    with _LOCK:
        ops = {op: {"count": n, **_LAST.get(op, {})} for op, n in sorted(_COUNTS.items())}
    return {"process_started_at": _PROCESS_STARTED_AT, "total": sum(_COUNTS.values()), "operations": ops}


def _reset_counters_for_tests() -> None:
    with _LOCK:
        _COUNTS.clear()
        _LAST.clear()
```

Decorated helpers keep bodies unchanged minus try/except, e.g. `_fetch_contradiction_field_rows` (:166-206) drops :204-206 and gains `@degrades("contradiction_field_rows", list)` — the `if pool is None: return []` stays inside (it is a legitimate SQLite-dev branch, not a fault). For #1 move the trailing `return 0` inside the try (row-missing → 0 inside try) if converting to decorator, else keep inline record.

## Envelope + header wiring

- **Reset per request:** `RequestLoggingMiddleware.__call__` (web/babylon_web/middleware.py:58) — first line: lazy `from game.degradation import reset_request_degradations; reset_request_degradations()` (lazy-import precedent: health/views.py:120 `from game import api as game_api`). After `self.get_response(...)` (:69), stamp `response["X-Babylon-Bridge"] = _bridge_mode()` next to the X-Request-ID stamp (:98) — middleware-level because the 9 per-verb views (api.py:1278-1802) return raw DRF `Response`, NOT `_envelope`.
- **`_envelope` (api.py:110-122):**

```python
def _envelope(data: Any, tick: int | None = None, session_id: str | None = None,
              http_status: int = 200) -> JsonResponse:
    """Wrap data in the standard API response envelope (C.6/C.7)."""
    from game.degradation import request_degradations

    degraded = request_degradations()
    body: dict[str, Any] = {
        "status": "degraded" if degraded else "ok",
        "data": data,
        "bridge": _bridge_mode(),
    }
    if degraded:
        body["degraded"] = sorted(set(degraded))
    ...
```

Safe for the frontend: client.ts only branches on `body.status === "error"` (client.ts:67,76). All ~43 `_envelope` call sites need zero changes.

## /health/detail shape

`HealthDetailView.get` (web/babylon_web/health/views.py:102-114) — add two keys:

```python
payload = {
    "status": "ok",
    "engine": self._engine_state(),          # already has "implementation"
    "database": self._database_state(),
    "degradation": self._degradation_state(),  # game.degradation.degradation_snapshot(), lazy import
    "bridge": self._bridge_state(),             # {"mode": "engine"|"stub", "stub_allowed": settings.ALLOW_STUB_BRIDGE}
    ...
}
```

Import lazily via `from game.degradation import degradation_snapshot` inside the method — health/views.py already violates the web→engine boundary with `babylon.config.llm_config` (:15, tracked by tests/unit/web/test_import_boundary.py); do NOT add counters to `babylon.*` — game-app module keeps the boundary clean.

---

## (b) C.6 — Engine hydration strict policy

Verified fallback sites in src/babylon/engine/hydration/reference.py:
- `hydrate_class_shares` (:222): except→fabricated class-share dict **:374-381** (fallback defined :241-249); plus data-missing early returns :265, :273, :297.
- `hydrate_economy_constants` (:384): except→partial/empty dict **:466-473**.
- `hydrate_reserve_army` (:476): except→empty dict **:541-548**; data-missing returns :509, :515.
- Bonus 4th site: `compute_initial_profit_rate` NaN/inf → `return 0.04  # STUB` **:210-216**.

**Reachability (drift):** these are only called from the `Simulation.from_sqlite` facade (src/babylon/engine/simulation/_legacy.py:198-204 imports, :248-249 calls) and tools/validate_detroit.py:132 — the bridged headless runner hydrates via `WorldStateBridge.hydrate_initial`/postgres_initialization and never touches them. Build the registry generically so C.8 (branch 2.R, pending) feeds it from the runner path.

Design — NEW `src/babylon/engine/hydration/fallbacks.py`:

```python
class HydrationFallbackError(RuntimeError):
    """Strict hydration refused to fabricate constants (REMEDIATION_PLAN C.6)."""

_LOCK = threading.Lock()
_COUNTS: Counter[str] = Counter()

def record_fallback(site: str, *, fips: str, year: int, reason: str) -> None:
    logger.warning("HYDRATION FALLBACK site=%s fips=%s year=%d: %s", site, fips, year, reason)
    with _LOCK:
        _COUNTS[site] += 1

def fallback_counts() -> dict[str, int]: ...
def reset_fallbacks() -> None: ...
```

Each function gains keyword-only `strict: bool = False`. Pattern at every fallback point (exception AND data-missing returns):

```python
    except Exception as exc:
        if strict:
            msg = f"strict hydration: class shares underivable for {fips}/{year}"
            raise HydrationFallbackError(msg) from exc
        record_fallback("class_shares", fips=fips, year=year, reason=str(exc))
        return fallback
```

Plumbing: `Simulation.from_sqlite(..., strict_hydration: bool = False)` → thread into :248-249. `SimulationRunConfig.strict` already exists (src/babylon/engine/headless_runner/models.py:123-131, CLI-plumbed at runner.py:228) — extend its description to cover hydration; do NOT add a second flag.

Manifest counter: `build_manifest` (src/babylon/engine/headless_runner/manifest.py:218-232) gains `hydration_fallbacks: dict[str, int] | None = None`, emitted as a top-level `"hydration_fallbacks"` key exactly mirroring the `bridge_db_reads` precedent (manifest.py:317-318). Call site: runner.py:1483-1504 passes `fallback_counts()`. Honest zero on canonical runs today; C.8 makes it meaningful.

Existing tests to keep green (they pin non-strict fallback behavior): tests/integration/test_constant_hydration.py:52-63, :86-89, :104-107.

---

## (c) C.7 — Stub-bridge visibility

**Bridge selection today:** `game.api._get_bridge()` (api.py:68-88) — `_bridge_instance is None` → logger.warning + `StubEngineBridge()` silently. Real init: `GameConfig.ready()` (apps.py:40-69) → `_initialize_engine_with_retry` (:71-110) → `init_persistence` (engine_bridge.py:3825) + `init_bridge` (api.py:91-102). ready() **returns without initializing** when DATABASES.default isn't postgres/postgis (apps.py:58-61) — that's the stub path. No client-visible marker exists anywhere (`rg X-Babylon` = zero hits).

1. `_bridge_mode()` in api.py next to `_get_bridge`:
```python
def _bridge_mode() -> str:
    """C.7: which bridge implementation is live — "engine" or "stub"."""
    from .stub_bridge import StubEngineBridge
    return "stub" if isinstance(_bridge_instance, StubEngineBridge) else "engine"
```
(Mock-patched test bridges read as "engine" — acceptable.)
2. Envelope field + header: see (a).
3. **Production refusal:** settings flag `ALLOW_STUB_BRIDGE` — base.py `False` (add near :25), stub.py `True` (near STUB_CREATE_TABLES :57), testing.py `True` (unit web tests hit `_get_bridge` unpatched in places); development/production/testing_pg inherit False. In `_get_bridge`:
```python
    if _bridge_instance is None:
        if not getattr(django_settings, "ALLOW_STUB_BRIDGE", False):
            raise ImproperlyConfigured(
                "EngineBridge not initialized and ALLOW_STUB_BRIDGE is False — "
                "boot via GameConfig.ready() with Postgres, or use settings.stub."
            )
        ...existing stub fallback...
```
`django_settings` already imported (api.py:17). Run `mise run test:q -- tests/unit/web/` after — any test relying on silent fallback under non-stub settings will surface.

**Frontend** (client point = web/frontend/src/api/client.ts `request<T>` :31-81, the ONLY typed fetch wrapper; gameStore.ts:6 uses it; NOTE 13/18 hooks fetch() raw and bypass it — gameStore snapshot/map traffic is enough to feed a badge):
- types/game.ts:4-10 — widen: `status: "ok" | "degraded" | "error"; bridge?: "engine" | "stub"; degraded?: string[];`
- client.ts after body parse (~:66):
```ts
const bridge = (response.headers.get("X-Babylon-Bridge") ?? body.bridge) as "engine" | "stub" | null;
if (bridge) useUIStore.getState().setBridgeMode(bridge);
if (body.status === "degraded") useUIStore.getState().noteDegradedResponse(url);
```
(zustand `getState()` outside React is fine; uiStore.ts imports nothing from api/ — no cycle.)
- uiStore: `bridgeMode: "engine" | "stub" | null`, `degradedRecently: boolean` (+ actions).
- Badge precedent: `web/frontend/src/components/ui/IndicatorChip.tsx` (urgency palette: `text-gold` amber / `text-crimson`; TopBar tint `bg-warning-amber/5`, TopBar.tsx:26-30). New `web/frontend/src/components/ui/BridgeBadge.tsx`, mounted in TopBar.tsx next to PersistentIndicators:
```tsx
export function BridgeBadge() {
  const bridgeMode = useUIStore((s) => s.bridgeMode);
  const degraded = useUIStore((s) => s.degradedRecently);
  if (bridgeMode !== "stub" && !degraded) return null;
  const label = bridgeMode === "stub" ? "STUB DATA" : "DEGRADED";
  return (
    <span
      className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded border border-gold text-gold bg-warning-amber/10"
      title={bridgeMode === "stub"
        ? "Serving mock data — engine bridge not initialized"
        : "One or more panels served fallback data this session"}
    >
      {label}
    </span>
  );
}
```

---

## (d) StubEngineBridge.create_game kwargs mismatch — this branch owns it

stub_bridge.py:432-439 signature is `(self, scenario, _config, _defines, _rng_seed, player_id)`; api.py:218-224 calls `bridge.create_game(scenario=..., config=..., defines=..., rng_seed=..., player_id=...)` → **TypeError: unexpected keyword argument 'config'** on every stub-mode game creation. Fix: rename params to `config: dict[str, Any] | None = None, defines: dict[str, Any] | None = None, rng_seed: int = 0` matching EngineBridge.create_game (engine_bridge.py:780-787); body ignores them (optionally store rng_seed in `_stub_sessions`). Other call sites use keywords too (seed_initial_game.py:96 — but it refuses stub; tests/integration pass `scenario=`/`rng_seed=` kwargs) — no caller uses the underscore names.

---

## (e) NoDataSentinel silent drop — recommendation: NOT this branch

Real path: **src/babylon/economics/tick/system/__init__.py:385-390** (prompt's `src/babylon/tick/...` doesn't exist). `_compute_national_params`: `gamma_III_raw = 0.33; if services.gamma_calculator is not None: g3_result = services.gamma_calculator.compute(year); if g3_result and not isinstance(g3_result, type(None)): gamma_III_raw = g3_result.gamma_iii` — a falsy NoDataSentinel silently keeps 0.33 (also note the `not isinstance(..., type(None))` clause is dead/redundant). **Recommend deferring to C.8 (branch 2.R, pending) + Phase 5.1** per REMEDIATION_PLAN.md:91 (C.8 explicitly owns "NoDataSentinel drops logged with reason + counted in manifest") and :145 (5.1 gamma adapter kills the fallback for covered years). This branch's contribution: build `hydration/fallbacks.py` registry (b) with a generic `record_fallback(site, ...)` API so C.8 calls the same registry from the tick system — put that reuse note in the PR description. If 2.R has landed a registry by rebase time, adopt theirs instead.

---

## TDD plan (red → green → refactor)

**Web RED first** — new tests/unit/web/test_degradation.py (+ additions to test_health.py [34 lines today, 3 tests] and test_api.py):
1. decorator: raises→fallback returned, counter==1, op in `request_degradations()`; second call increments; `_reset_counters_for_tests` autouse fixture.
2. envelope: patch `game.api._bridge_instance` with a bridge whose `get_journal_dashboard` internally records a degradation (or monkeypatch persistence `query_session_events` to raise on the real EngineBridge) → GET /api/games/{id}/journal/ is HTTP 200, `status=="degraded"`, `"journal_query" in body["degraded"]`, `resp["X-Babylon-Bridge"]` present.
3. isolation: next request (no failure) → `status=="ok"`, no `degraded` key (middleware reset works).
4. health: staff client → payload has `degradation.total`/`operations` and `bridge.mode` (existing test_health.py style).
5. C.7 refusal: `@override_settings(ALLOW_STUB_BRIDGE=False)` + `_bridge_instance=None` → `_get_bridge()` raises ImproperlyConfigured; `=True` → StubEngineBridge.
6. (d) RED today: `StubEngineBridge().create_game(scenario="wayne_county", config=None, defines=None, rng_seed=7, player_id=1)` → currently TypeError.
   - Run: `mise run test:q -- tests/unit/web/test_degradation.py tests/unit/web/test_health.py tests/unit/web/test_api.py`

**Engine RED** — new tests/unit/engine/hydration/test_strict_fallbacks.py:
7. monkeypatch `babylon.engine.hydration.reference.get_reference_session` to raise → non-strict: returns fallback AND `fallback_counts()["class_shares"]==1`; `strict=True` → `pytest.raises(HydrationFallbackError)`; same for economy_constants/reserve_army/profit-rate-NaN site.
8. manifest: `build_manifest(..., hydration_fallbacks={"class_shares": 2})` → payload has top-level key; None → absent (mirror existing bridge_db_reads tests under tests/unit/engine/headless_runner/).
   - Run: `mise run test:q -- tests/unit/engine/hydration tests/unit/engine/headless_runner` then `mise run test:q -- tests/integration/test_constant_hydration.py` (must stay green, non-strict default).

**Frontend RED**: client.test.ts — mocked fetch returning `X-Babylon-Bridge: stub` header → `useUIStore.getState().bridgeMode==="stub"`; body `status:"degraded"` → `degradedRecently===true`; new BridgeBadge test (renders null on engine+ok, amber label on stub).
   - Run: `mise run web:test` (or `cd web/frontend && npx vitest run src/api src/components/ui`), full `mise run web:check` before merge.

**Merge gate**: `mise run check` (ruff+format+mypy strict+test:unit). Commit per unit via `mise run commit -- "..."`: (1) `feat(web): degradation registry + @degrades decorator (C.6)`, (2) `refactor(web): migrate 19 bridge blocks to degradation policy`, (3) `feat(web): degraded/bridge envelope + X-Babylon-Bridge header + health detail (C.6+C.7)`, (4) `fix(web): stub create_game kwargs parity`, (5) `feat(engine): strict hydration policy + fallback registry + manifest counter`, (6) `feat(frontend): bridge/degraded badge`.

## Overlap warnings for the implementer (re-verify, don't assume)
- Lane 2.4 (verb dispatch, IN FLIGHT) owns engine_bridge.py:91-107 (VERB_TO_ACTION_TYPE/UNSUPPORTED_VERBS) and :1946-2071 (resolve_tick pre/post diff — will be rewritten to read real ActionResults) plus api.py verb views + src/babylon/engine/systems/ooda.py. This branch's targets are mostly disjoint, BUT `_persist_tick_events_safe` (:3333), `_persist_hex_state_safe` (:3425) and `_persist_action_result` (:3813) are invoked inside resolve_tick — rebase onto 2.4's merge and re-run `rg -n "except Exception" web/game/engine_bridge.py` to refresh every line number before editing.
- Lane 2.2 (territory-case) is also in progress; no shared files expected (engine systems only), still re-check.
- If 2.R has landed by start time, its C.8 wiring-audit may already provide a fallback registry/manifest key — reuse, don't duplicate.

## Drift alerts (scout-verified deviations from the plan)

- Count drift: engine_bridge.py has 19 except-Exception blocks, not ~17 (lines 122,143,204,312,361,415,449,496,541,561,995,1115,1340,1366,3243,3333,3425,3813,3854); api.py:1077 is already-loud (500 + status restore, exclude), apps.py:100 is loud boot-retry (exclude), stub_bridge.py:721-722 is a bare 'except Exception: pass' with ZERO logging (stub-only, one-line warn fix).
- Prompt path wrong: the NoDataSentinel drop is src/babylon/economics/tick/system/__init__.py:385-390, not src/babylon/tick/system/__init__.py (which doesn't exist).
- hydration/reference.py fallbacks (374/466/541 + bonus 0.04 stub at :216) are NOT reachable from the canonical bridged headless runner — only Simulation.from_sqlite (simulation/_legacy.py:248-249) and tools/validate_detroit.py:132 call them; the manifest hydration_fallbacks counter will honestly read 0 on canonical runs until C.8 (branch 2.R, still pending) feeds the same registry from the runner/tick path.
- The 9 per-verb GET/POST views (api.py:1278-1802) return raw DRF Response and bypass _envelope entirely — an envelope-only bridge/degraded marker would miss the whole verb pipeline; the X-Babylon-Bridge header must be stamped in RequestLoggingMiddleware (middleware.py:58-100, next to the :98 X-Request-ID stamp).
- 13 of 18 frontend hooks call fetch() directly and bypass web/frontend/src/api/client.ts — badge coverage comes from gameStore traffic through client.ts only; noted in brief, do not claim full-request coverage.
- IN-FLIGHT OVERLAP (2.4 verb dispatch): engine_bridge.py:91-107 and :1946-2071 plus api.py verb views + ooda are being rewritten; three of my migration targets (_persist_tick_events_safe :3333, _persist_hex_state_safe :3425, _persist_action_result :3813) are called inside resolve_tick — implementer must rebase after 2.4 merges and re-run rg to refresh ALL line numbers.
- health/views.py already imports babylon.config.llm_config (line 15) in violation of tests/unit/web/test_import_boundary.py — degradation counters must live in web/game/degradation.py (game app, lazily imported by health views per the existing 'from game import api' pattern at health/views.py:120), never in babylon.*.
- Plan item 0.1's 'stub re-ADD (apps.py:166-170)' is already gone — apps.py is now 164 lines; only STUB_CREATE_TABLES-gated _create_stub_tables remains (apps.py:52-53,112-164).
- Severity note: _fetch_session_rng_seed_from_pool (engine_bridge.py:122) silently falls back to seed 0 — this degrades DETERMINISM (Constitution III.7), not just a blank panel; and _compute_avg_node_attr/:541 + _count_edges_by_mode/:561 currently swallow with no logging at all.
