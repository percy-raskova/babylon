"""The five golden arcs — §5.5's behavioral contracts (P25 U13, ADR140).

Each class drives one golden scenario through ``simulation_engine.step()``
— the qa-harness API, WorldState round-trip every tick — with the SAME
defines overrides the ``SCENARIOS`` registry declares (sync-pinned by the
ceremony commit), and pins the named historical arc:

- ``TestMitterrandGolden`` — the tournant de la rigueur: a 24-item burst
  against real Wayne fiscal facts; borrowing, then bond discipline, then
  the austerity floor; capitulate on fiscal contact.
- ``TestSyrizaGolden`` — capture dominates organs: the fork capitulates
  WITH dual power live; the PASOK slow bleed; the Golden Dawn shadow.
- ``TestDebsGolden`` — the independent line's tax structure: the spoiler
  shift lands on the same-pole machine; organization accumulates anyway.
- ``TestBernieValveGolden`` — the hope years, the derecognition, and both
  routings of one disillusion operator, split by topology alone.
- ``TestWeimarGolden`` — fascist consolidation THROUGH the ballot: a real
  desperation vote, and the first production faction_balance perturbation.

Every asserted number was verified by live spot-runs before pinning
(the ADR090 E1 coverage-authoring method); the byte-level contract is the
``blessed(electoral-goldens)`` baseline pair.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.engine.scenarios import electoral_goldens
from babylon.engine.simulation_engine import step
from babylon.models.enums import EdgeType
from babylon.models.enums.events import EventType

pytestmark = pytest.mark.unit

_FAST_CLOCK = {"federal": 8, "state": 8, "local": 4}

#: Per-golden defines overrides — the SCENARIOS registry declares the same
#: values (sync-pinned there); every coefficient is a declared politics
#: define (III.1), tuned so each arc completes inside the 52-tick horizon.
GOLDEN_OVERRIDES: dict[str, dict[str, Any]] = {
    "mitterrand": {
        "politics.cycle_ticks": _FAST_CLOCK,
        "politics.policy_agenda_rate": 24,
        "politics.bond_discipline_threshold": 0.02,
        "politics.betrayal_threshold": 5.0e7,
    },
    "syriza": {
        "politics.cycle_ticks": _FAST_CLOCK,
        "politics.betrayal_threshold": 2.0e7,
    },
    "weimar": {
        "politics.cycle_ticks": _FAST_CLOCK,
        "politics.suppression_cost_weight": 0.02,
    },
    "debs": {
        "politics.cycle_ticks": _FAST_CLOCK,
        "politics.suppression_cost_weight": 0.001,
    },
    "bernie_valve": {
        "politics.cycle_ticks": _FAST_CLOCK,
        "politics.phi_social_share": 1.0,
        "politics.valve_strength": 1.0,
        "politics.suppression_cost_weight": 0.02,
        "politics.hope_spike_gain": 0.05,
        "politics.betrayal_threshold": 2.3e6,
    },
}

#: Wayne-substrate goldens run with the single_county calculator overrides
#: (the tensor registry that hydrates the fiscal terrain); the two_node
#: goldens run with the plain Vol III set — mirroring the harness.
WAYNE_GOLDENS = frozenset({"mitterrand", "syriza", "bernie_valve"})


def _inject(defines: Any, overrides: dict[str, Any]) -> Any:
    for path, value in overrides.items():
        category, field = path.split(".")
        submodel = getattr(defines, category)
        defines = defines.model_copy(update={category: submodel.model_copy(update={field: value})})
    return defines


def _run(name: str, ticks: int) -> tuple[Any, list[tuple[int, Any]]]:
    """Drive a golden through step(); return (final_state, [(tick, event)])."""
    factory = getattr(electoral_goldens, f"create_{name}_scenario")
    state, config, defines = factory()
    defines = _inject(defines, GOLDEN_OVERRIDES[name])
    overrides = _calculator_overrides(name, defines)
    persistent: dict[str, Any] = {}
    events: list[tuple[int, Any]] = []
    for tick in range(1, ticks + 1):  # fixed bound
        state = step(state, config, persistent, defines, calculator_overrides=overrides)
        events.extend((tick, event) for event in state.events)
    return state, events


def _calculator_overrides(name: str, defines: Any) -> dict[str, Any]:
    import sys
    from pathlib import Path

    tools_dir = Path(__file__).resolve().parents[4] / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    import regression_test as rt  # type: ignore[import-not-found]

    if name in WAYNE_GOLDENS:
        return rt.build_single_county_overrides(defines)
    return rt._build_vol3_calculator_overrides(defines)


def _of_type(events: list[tuple[int, Any]], event_type: EventType) -> list[tuple[int, Any]]:
    return [(t, e) for t, e in events if getattr(e, "event_type", None) == event_type]


class TestMitterrandGolden:
    """Reform enacts past tolerance → strike + bond channels → austerity."""

    @pytest.fixture(scope="class")
    def run(self) -> tuple[Any, list[tuple[int, Any]]]:
        return _run("mitterrand", 12)

    def test_the_burst_drains_at_the_boundary_tick(self, run) -> None:
        state, events = run
        strikes = _of_type(events, EventType.CAPITAL_STRIKE)
        assert len(strikes) == 24
        assert all(t == 1 for t, _ in strikes)
        assert state.superstructure_registers["policy_agenda"] == []

    def test_the_fork_capitulates_on_fiscal_contact(self, run) -> None:
        state, events = run
        forks = _of_type(events, EventType.GOVERNANCE_FORK_RESOLVED)
        assert len(forks) >= 1
        first = forks[0][1]
        assert first.arm == "capitulate"
        assert first.contact == "fiscal"
        register = state.superstructure_registers["governance_endgame"]
        assert register["org/party-socdem"]["arm"] == "capitulate"

    def test_the_austerity_turn_doubles_the_gap(self, run) -> None:
        """Bond discipline binds inside the burst: financing refused, the
        per-item gap jumps to the funded floor and stays there."""
        _state, events = run
        gaps = [
            e.gap
            for _t, e in _of_type(events, EventType.DELIVERY_GAP_CROSSED)
            if e.class_id == "C004"
        ]
        assert len(gaps) == 24
        assert gaps[-1] > 1.5 * gaps[0]
        assert gaps[-1] == pytest.approx(gaps[-2])

    def test_betrayal_crosses_both_classes_and_debt_stands(self, run) -> None:
        state, events = run
        crossed = {e.class_id for _t, e in _of_type(events, EventType.BETRAYAL_INTEGRAL_CROSSED)}
        assert crossed == {"C003", "C004"}
        fiscal = state.superstructure_registers["sovereign_fiscal"]["SOV_USA_FED"]
        assert fiscal["debt_stock"] == pytest.approx(64_630_747.63, rel=1e-6)

    def test_the_electorate_reseats_the_betrayer(self, run) -> None:
        state, _events = run
        seated = state.superstructure_registers["electoral_governments"]["SOV_USA_FED"]
        assert seated["party_id"] == "org/party-socdem"
        assert seated["formed_tick"] == 8


class TestSyrizaGolden:
    """Capture dominates organs; the delivery gap IS the PASOK trajectory."""

    @pytest.fixture(scope="class")
    def run(self) -> tuple[Any, list[tuple[int, Any]]]:
        return _run("syriza", 12)

    def test_capitulates_with_dual_power_live(self, run) -> None:
        state, events = run
        claimants = {
            rel.source_id
            for rel in state.relationships
            if rel.edge_type == EdgeType.CLAIMS and rel.target_id == "T001"
        }
        assert len(claimants) >= 2, "the organs stand on the terrain"
        forks = _of_type(events, EventType.GOVERNANCE_FORK_RESOLVED)
        assert forks[0][1].arm == "capitulate"
        assert forks[0][1].contact == "fiscal"

    def test_the_slow_bleed_holds_delivery_flat(self, run) -> None:
        _state, events = run
        ratios = {
            round(e.delivery_ratio, 6) for _t, e in _of_type(events, EventType.POLICY_ENACTED)
        }
        assert len(ratios) == 1, "PASOK bleeds at a constant ratio, never a cliff"
        assert ratios.pop() == pytest.approx(0.962253, rel=1e-4)

    def test_betrayal_crosses_midrun_and_routes_atomized(self, run) -> None:
        state, events = run
        crossings = _of_type(events, EventType.BETRAYAL_INTEGRAL_CROSSED)
        assert crossings[0][0] == 4, "the integral crosses mid-run, not at the door"
        assert crossings[0][1].class_id == "C004"
        windows = _of_type(events, EventType.DISILLUSION_WINDOW_OPEN)
        assert windows[0][1].bridges_present is False
        assert state.entities["C004"].fascist_alignment > 0.01

    def test_office_is_retained(self, run) -> None:
        state, _events = run
        seated = state.superstructure_registers["electoral_governments"]["SOV_USA_FED"]
        assert seated["party_id"] == "org/party-socdem"


class TestDebsGolden:
    """The independent line's honest trade under FPTP."""

    @pytest.fixture(scope="class")
    def run(self) -> tuple[Any, list[tuple[int, Any]]]:
        return _run("debs", 18)

    def test_the_spoiler_taxes_the_same_pole_machine(self, run) -> None:
        _state, events = run
        elections = _of_type(events, EventType.ELECTION_HELD)
        assert elections, "the clock fired"
        first = elections[0][1]
        assert first.spoiler_target == "org/party-liberal"
        assert first.spoiler_shift > 0.0

    def test_the_share_ceiling_binds(self, run) -> None:
        state, _events = run
        # The share the independent seats with is post-tax arithmetic — the
        # machine's pole was drained by the spoiler shift, and the line's own
        # share never approaches consolidation.
        seated = state.superstructure_registers["electoral_governments"]["SOV_USA_FED"]
        assert seated["share"] < 0.75

    def test_solidarity_accumulates_anyway(self, run) -> None:
        state, _events = run
        assert state.entities["C001"].organization > 0.15


class TestBernieValveGolden:
    """One operator, two routings, topology decides."""

    @pytest.fixture(scope="class")
    def run(self) -> tuple[Any, list[tuple[int, Any]]]:
        return _run("bernie_valve", 12)

    def test_the_hope_years_spike(self, run) -> None:
        _state, events = run
        spiked = {e.class_id for _t, e in _of_type(events, EventType.HOPE_SPIKE)}
        assert {"C003", "C005", "C006"} <= spiked

    def test_the_machine_derecognizes_the_entryist(self, run) -> None:
        state, _events = run
        derecognized = state.superstructure_registers.get("electoral_derecognized", ())
        assert "org/party-socdem" in tuple(derecognized)

    def test_windows_open_with_the_topology_stamped(self, run) -> None:
        _state, events = run
        rows = {
            e.class_id: e.bridges_present
            for _t, e in _of_type(events, EventType.DISILLUSION_WINDOW_OPEN)
        }
        assert rows["C003"] is True
        assert rows["C005"] is False
        assert rows["C006"] is True

    def test_the_same_operator_routes_the_twins_apart(self, run) -> None:
        state, _events = run
        atomized = state.entities["C005"]
        bridged = state.entities["C006"]
        assert atomized.fascist_alignment > 0.0, "Obama→Trump: despair without a bridge"
        assert bridged.fascist_alignment == pytest.approx(0.0), "the bridge holds"
        assert bridged.organization > atomized.organization, "Bernie→DSA: the surge lands"


class TestWeimarGolden:
    """Consolidation through the ballot, never via script."""

    @pytest.fixture(scope="class")
    def run(self) -> tuple[Any, list[tuple[int, Any]]]:
        return _run("weimar", 10)

    def test_the_fascist_wins_a_real_election(self, run) -> None:
        _state, events = run
        elections = _of_type(events, EventType.ELECTION_HELD)
        assert elections[0][0] == 9, "the federal clock (context tick 8, loop tick 9)"
        first = elections[0][1]
        assert first.winning_coalition == "org/party-fascist"
        assert first.turnout > 0.003, "a desperation vote, not a coin flip"

    def test_the_win_perturbs_the_state_apparatus(self, run) -> None:
        state, events = run
        formed = _of_type(events, EventType.GOVERNMENT_FORMED)
        assert formed[0][1].faction_balance_shift > 0.04
        interior = state.organizations["org/state-interior"]
        assert interior.faction_balance is not None
        assert interior.faction_balance.settler_populist > 0.3

    def test_the_conjuncture_stands_from_the_first_tick(self, run) -> None:
        state, events = run
        called = _of_type(events, EventType.POPULAR_FRONT_CALLED)
        assert called[0][0] == 1
        assert called[0][1].axis_progress == pytest.approx(1.0)
        front = state.superstructure_registers["popular_front"]
        assert front["active"] is True

    def test_atomized_despair_routes_to_the_vehicle(self, run) -> None:
        state, events = run
        windows = _of_type(events, EventType.DISILLUSION_WINDOW_OPEN)
        assert windows, "the loss opened a window"
        assert all(e.bridges_present is False for _t, e in windows)
        assert state.entities["C001"].fascist_alignment >= 0.0
