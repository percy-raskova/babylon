"""Spec-070 SovereigntySystem unit test (T038 + T041 / FR-019, FR-020,
FR-035, FR-043).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.systems.sovereignty import SovereigntySystem
from babylon.models.enums import EventType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


@dataclass
class _CapturedEvent:
    type: Any
    tick: int
    payload: dict[str, Any]


class _RecordingEventBus:
    def __init__(self) -> None:
        self.events: list[_CapturedEvent] = []

    def publish(self, event: Any) -> None:
        self.events.append(_CapturedEvent(type=event.type, tick=event.tick, payload=event.payload))


@pytest.fixture
def services() -> Any:
    container = MagicMock()
    container.event_bus = _RecordingEventBus()
    # Task #42 fix wave 1: SovereigntySystem now threads defines= through to
    # calculate_metabolic_impact (review MEDIUM-1 sweep); a real GameDefines
    # keeps every existing assertion below numerically unchanged (its
    # BalkanizationDefines defaults ARE the -0.02/-0.005/+0.01 the tests
    # already assert) while proving the call site no longer silently uses
    # the formula's OWN internal default regardless of what services.defines
    # says.
    container.defines = GameDefines()
    return container


def _seed_single_sovereign(adapter: BabylonGraph) -> None:
    adapter.add_node(
        "SOV_USA_FED",
        "sovereign",
        extraction_policy="intensify",
    )
    adapter.add_node("HEX_001", "territory", habitability=0.8)
    adapter.add_edge(
        "SOV_USA_FED",
        "HEX_001",
        "claims",
        control_level=1.0,
        legal_status="de_jure",
    )


def test_sovereignty_writes_metabolic_impact_per_territory(services: Any) -> None:
    adapter = BabylonGraph()
    _seed_single_sovereign(adapter)
    context = TickContext(tick=0, persistent_data={})

    SovereigntySystem().step(adapter, services, context)

    impact = context.persistent_data["balkanization.metabolic_impact_by_territory"]
    assert impact == {"HEX_001": pytest.approx(-0.02)}


def test_sovereignty_writes_effective_controller_per_territory(
    services: Any,
) -> None:
    adapter = BabylonGraph()
    _seed_single_sovereign(adapter)
    context = TickContext(tick=0, persistent_data={})

    SovereigntySystem().step(adapter, services, context)

    controllers = context.persistent_data["balkanization.effective_controller_by_territory"]
    assert controllers == {"HEX_001": "SOV_USA_FED"}


def test_sovereignty_dual_power_tiebreak_only_highest_wins(services: Any) -> None:
    """FR-020: when multiple CLAIMS target one Territory, only the
    highest-control_level Sovereign's metabolic_impact applies."""

    adapter = BabylonGraph()
    adapter.add_node("SOV_A", "sovereign", extraction_policy="cease")
    adapter.add_node("SOV_B", "sovereign", extraction_policy="intensify")
    adapter.add_node("HEX_001", "territory", habitability=0.8)
    adapter.add_edge("SOV_A", "HEX_001", "claims", control_level=0.3, legal_status="de_facto")
    adapter.add_edge("SOV_B", "HEX_001", "claims", control_level=0.7, legal_status="de_facto")
    context = TickContext(tick=0, persistent_data={})

    SovereigntySystem().step(adapter, services, context)

    # SOV_B (higher control) wins; its INTENSIFY policy yields -0.02.
    impact = context.persistent_data["balkanization.metabolic_impact_by_territory"]
    assert impact["HEX_001"] == pytest.approx(-0.02)
    controllers = context.persistent_data["balkanization.effective_controller_by_territory"]
    assert controllers["HEX_001"] == "SOV_B"


def test_sovereignty_emits_dual_power_active_event(services: Any) -> None:
    """FR-035: emit DUAL_POWER_ACTIVE when ≥2 Sovereigns have
    control_level > 0.0 on the same Territory."""

    adapter = BabylonGraph()
    adapter.add_node("SOV_A", "sovereign", extraction_policy="cease")
    adapter.add_node("SOV_B", "sovereign", extraction_policy="intensify")
    adapter.add_node("HEX_001", "territory", habitability=0.8)
    adapter.add_edge("SOV_A", "HEX_001", "claims", control_level=0.3, legal_status="de_facto")
    adapter.add_edge("SOV_B", "HEX_001", "claims", control_level=0.7, legal_status="de_facto")
    context = TickContext(tick=7, persistent_data={})

    SovereigntySystem().step(adapter, services, context)

    bus: _RecordingEventBus = services.event_bus
    dual_power = [e for e in bus.events if e.type is EventType.DUAL_POWER_ACTIVE]
    assert len(dual_power) == 1
    event = dual_power[0]
    assert event.tick == 7
    assert event.payload["territory_id"] == "HEX_001"
    assert set(event.payload["competing_sovereign_ids"]) == {"SOV_A", "SOV_B"}
    assert event.payload["control_level_sum"] == pytest.approx(1.0)


def test_sovereignty_no_dual_power_for_single_claimant(services: Any) -> None:
    adapter = BabylonGraph()
    _seed_single_sovereign(adapter)
    context = TickContext(tick=0, persistent_data={})

    SovereigntySystem().step(adapter, services, context)

    bus: _RecordingEventBus = services.event_bus
    dual_power = [e for e in bus.events if e.type is EventType.DUAL_POWER_ACTIVE]
    assert dual_power == []


def test_sovereignty_skips_territories_with_no_claims(services: Any) -> None:
    adapter = BabylonGraph()
    adapter.add_node("HEX_ORPHAN", "territory", habitability=0.8)
    context = TickContext(tick=0, persistent_data={})

    SovereigntySystem().step(adapter, services, context)

    impact = context.persistent_data["balkanization.metabolic_impact_by_territory"]
    assert "HEX_ORPHAN" not in impact


def test_sovereignty_calls_calculate_metabolic_impact_with_run_defines(services: Any) -> None:
    """Task #42 fix wave 1 (review MEDIUM-1 sweep): a regression discovered
    while surveying the defines-passthrough bug class beyond ideology.py --
    this call site silently used calculate_metabolic_impact's own internal
    BalkanizationDefines() default, ignoring services.defines/defines.yaml
    overrides. Direct call-contract pin, mirroring the ideology.py spy tests."""
    from babylon.formulas.balkanization import (
        calculate_metabolic_impact as _real_calculate_metabolic_impact,
    )

    adapter = BabylonGraph()
    _seed_single_sovereign(adapter)
    context = TickContext(tick=0, persistent_data={})

    with patch(
        "babylon.engine.systems.sovereignty.calculate_metabolic_impact",
        wraps=_real_calculate_metabolic_impact,
    ) as spy:
        SovereigntySystem().step(adapter, services, context)

    assert spy.call_args_list, "calculate_metabolic_impact was never called"
    for call in spy.call_args_list:
        assert call.kwargs.get("defines") is services.defines.balkanization, (
            "calculate_metabolic_impact must receive the run's live "
            "services.defines.balkanization -- omitting it silently falls "
            f"back to schema defaults; actual call: {call}"
        )
