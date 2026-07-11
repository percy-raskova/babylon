"""E5: induced-crisis integration test over the bridged income-circuit world.

Run ~20 ticks of pacified hegemony, then force the crisis through the ECONOMY —
drain the imperial rent pool and cut extraction to ~0 (the SUPERWAGE_CRISIS
path §E5 names), touching NO StruggleSystem severing or consciousness gating —
and assert the crisis proves out: the capital_labor/wage gap grows, the
principal contradiction shifts, and at least one RUPTURE or LEVEL_TRANSITION
fires. Gated exactly like the income-circuit suite (local Postgres + SQLite).
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SQLITE = _REPO_ROOT / "data" / "sqlite" / "marxist-data-3NF.sqlite"
_PG_DSN = "host=localhost port=5433 dbname=babylon_test user=test password=test"

_PACIFIED_TICKS = 20
_CRISIS_TICKS = 20

pytestmark = [pytest.mark.integration, pytest.mark.ledger, pytest.mark.slow]

if not _SQLITE.exists():  # pragma: no cover - environment guard
    pytest.skip("live reference DB absent", allow_module_level=True)

psycopg_pool = pytest.importorskip("psycopg_pool", reason="psycopg_pool required")


def _pg_available() -> bool:
    try:
        pool = psycopg_pool.ConnectionPool(_PG_DSN, min_size=1, max_size=1, open=True, timeout=5)
        pool.close()
    except Exception:
        return False
    return True


if not _pg_available():  # pragma: no cover - environment guard
    pytest.skip("local Postgres test DB unavailable", allow_module_level=True)


def _principal(graph: object) -> str:
    states = graph.graph.get("opposition_states", {})  # type: ignore[attr-defined]
    return next((k for k, s in states.items() if s.get("is_principal")), "")


def _gap(graph: object, key: str) -> float:
    states = graph.graph.get("opposition_states", {})  # type: ignore[attr-defined]
    return float(states.get(key, {}).get("gap", 0.0))


def _regime(graph: object) -> str:
    return str(graph.graph.get("dialectical_regime", {}).get("regime", ""))  # type: ignore[attr-defined]


@pytest.fixture(scope="module")
def crisis_arc():  # type: ignore[no-untyped-def]
    """One bridged county driven 20 pacified + 20 crisis ticks; records the arc."""
    from babylon.config.defines import GameDefines
    from babylon.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.engine.context import TickContext
    from babylon.engine.headless_runner.bridge import WorldStateBridge
    from babylon.engine.headless_runner.runner import EventCapture
    from babylon.engine.services import ServiceContainer
    from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
    from babylon.kernel.event_bus import EventBus
    from babylon.models.enums import EventType
    from babylon.persistence import PostgresRuntime
    from babylon.persistence.conservation_audit import ConservationAuditor
    from babylon.persistence.postgres_initialization import initialize_session

    pool = psycopg_pool.ConnectionPool(_PG_DSN, min_size=1, max_size=2, open=True)
    runtime = PostgresRuntime(pool=pool)
    defines = GameDefines.load_default()
    session_id = uuid.uuid4()
    initialize_session(
        session_id=session_id,
        sqlite_path=_SQLITE,
        runtime=runtime,
        defines=defines,
        start_year=2010,
        scenario_length_years=2,
        counties=["26163"],
        hex_hydration_counties={"26163"},
    )
    bridge = WorldStateBridge(
        runtime=runtime,
        defines=defines,
        boundary_register=BoundaryFlowRegister(),
        event_bus=EventBus(),
        auditor=ConservationAuditor(epsilon=defines.economy.epsilon_conservation, rng_seed=2010),
    )
    world = bridge.hydrate_initial(
        session_id=session_id,
        scope_fips={"26163"},
        event_capture=EventCapture(),
        total_ticks=_PACIFIED_TICKS + _CRISIS_TICKS + 5,
        start_year=2010,
        sqlite_path=_SQLITE,
    )

    # Shared event bus so RUPTURE / LEVEL_TRANSITION from either phase are visible.
    shared_bus = EventBus()
    services = ServiceContainer.create(defines=defines)
    object.__setattr__(services, "event_bus", shared_bus)
    # Crisis defines: zero extraction -> no rent inflow -> the super-wage cannot
    # be paid (SUPERWAGE_CRISIS). Pure economic lever; StruggleSystem untouched.
    crisis_defines = defines.model_copy(
        update={"economy": defines.economy.model_copy(update={"extraction_efficiency": 0.0})}
    )
    services_crisis = ServiceContainer.create(defines=crisis_defines)
    object.__setattr__(services_crisis, "event_bus", shared_bus)

    engine = SimulationEngine(list(_DEFAULT_SYSTEMS))
    graph = world.to_graph()

    pacified: list[dict[str, object]] = []
    crisis: list[dict[str, object]] = []
    tick = 0
    for _ in range(_PACIFIED_TICKS):
        tick += 1
        engine.run_tick(graph, services, TickContext(tick=tick))
        pacified.append(
            {
                "tick": tick,
                "regime": _regime(graph),
                "principal": _principal(graph),
                "cap_labor": _gap(graph, "capital_labor"),
                "wage": _gap(graph, "wage"),
            }
        )

    # ── Force the crisis: drain the pool, switch to zero-extraction services ──
    economy = dict(graph.graph.get("economy", {}))
    economy["imperial_rent_pool"] = 0.0
    graph.graph["economy"] = economy

    for _ in range(_CRISIS_TICKS):
        tick += 1
        engine.run_tick(graph, services_crisis, TickContext(tick=tick))
        crisis.append(
            {
                "tick": tick,
                "regime": _regime(graph),
                "principal": _principal(graph),
                "cap_labor": _gap(graph, "capital_labor"),
                "wage": _gap(graph, "wage"),
            }
        )

    ruptures = [e for e in shared_bus.get_history() if e.type == EventType.RUPTURE]
    level_transitions = [
        e for e in shared_bus.get_history() if e.type == EventType.LEVEL_TRANSITION
    ]

    yield {
        "pacified": pacified,
        "crisis": crisis,
        "ruptures": ruptures,
        "level_transitions": level_transitions,
    }
    pool.close()


def test_pacified_phase_holds_no_rupture(crisis_arc) -> None:  # type: ignore[no-untyped-def]
    """The pacified decade never ruptures (hegemony holds before the drain)."""
    pacified_ticks = {row["tick"] for row in crisis_arc["pacified"]}
    rupture_ticks = {e.tick for e in crisis_arc["ruptures"]}
    assert not (pacified_ticks & rupture_ticks), (
        f"rupture during the pacified phase: {sorted(pacified_ticks & rupture_ticks)}"
    )


def test_crisis_grows_the_gap(crisis_arc) -> None:  # type: ignore[no-untyped-def]
    """The wage/capital_labor gap grows once the pool drains (rate > 0 sustained)."""
    pacified = crisis_arc["pacified"]
    crisis = crisis_arc["crisis"]

    def peak(rows: list[dict[str, object]]) -> float:
        return max(max(float(r["cap_labor"]), float(r["wage"])) for r in rows)

    assert peak(crisis) > peak(pacified) + 1e-3, (
        f"gap did not grow: pacified peak={peak(pacified):.4f}, crisis peak={peak(crisis):.4f}"
    )


def test_principal_contradiction_shifts(crisis_arc) -> None:  # type: ignore[no-untyped-def]
    """The fast-developing contradiction takes over: the principal key changes."""
    seen = {row["principal"] for row in crisis_arc["pacified"] + crisis_arc["crisis"]}
    seen.discard("")
    assert len(seen) > 1, f"principal never shifted (stayed {seen})"


def test_rupture_or_level_transition_fires(crisis_arc) -> None:  # type: ignore[no-untyped-def]
    """At least one RUPTURE or LEVEL_TRANSITION fires — the crisis-gated pathway."""
    crisis_ticks = {row["tick"] for row in crisis_arc["crisis"]}
    fired = [
        e
        for e in crisis_arc["ruptures"] + crisis_arc["level_transitions"]
        if e.tick in crisis_ticks
    ]
    assert fired, "no RUPTURE or LEVEL_TRANSITION fired during the induced crisis"
