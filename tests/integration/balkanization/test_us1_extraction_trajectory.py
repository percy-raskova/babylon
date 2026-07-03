"""Spec-070 US1 integration test (T039 + T040, FR-019 + FR-043 + SC-003).

Drives SovereigntySystem + MetabolismSystem together over multiple
ticks to verify that a Sovereign's ``extraction_policy`` produces the
documented habitability trajectory per spec.md US1 Acceptance
Scenarios 1-4:

1. INTENSIFY drops habitability ≈0.2 over 10 ticks.
2. CONTINUE flattens the slope.
3. CEASE reverses the slope (≥0 within 5 ticks).
4. Multiple Territories all receive the effect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.engine.systems.sovereignty import SovereigntySystem
from babylon.models.enums import ExtractionPolicy

pytestmark = pytest.mark.integration


@dataclass
class _MetabolismDefines:
    entropy_factor: float = 0.5
    overshoot_threshold: float = 1.0
    max_overshoot_ratio: float = 10.0


@dataclass
class _AllDefines:
    metabolism: _MetabolismDefines


@pytest.fixture
def services() -> Any:
    container = MagicMock()
    container.event_bus = MagicMock()
    container.event_bus.publish = MagicMock()
    container.defines = _AllDefines(metabolism=_MetabolismDefines())
    return container


def _build_world(
    extraction_policy: str,
    n_territories: int = 1,
    starting_habitability: float = 0.8,
) -> BabylonGraph:
    adapter = BabylonGraph()
    adapter.add_node(
        "SOV_USA_FED",
        "sovereign",
        extraction_policy=extraction_policy,
    )
    for i in range(n_territories):
        territory_id = f"HEX_{i:03d}"
        adapter.add_node(
            territory_id,
            "territory",
            habitability=starting_habitability,
            regeneration_rate=0.0,
            max_biocapacity=100.0,
            extraction_intensity=0.0,
            biocapacity=100.0,
            s_bio=0.0,
            s_class=0.0,
            population=1,
            active=True,
        )
        adapter.add_edge(
            "SOV_USA_FED",
            territory_id,
            "claims",
            control_level=1.0,
            legal_status="de_jure",
        )
    return adapter


def _tick_pipeline(
    adapter: BabylonGraph,
    services: Any,
    persistent: dict[str, Any],
    tick: int,
) -> None:
    """Run the spec-070 portion of one tick: SovereigntySystem writes
    metabolic_impact, MetabolismSystem applies it to habitability."""

    context: dict[str, Any] = {"tick": tick, "persistent_data": persistent}
    SovereigntySystem().step(adapter, services, context)
    MetabolismSystem().step(adapter, services, context)


def _habitability(adapter: BabylonGraph, territory_id: str) -> float:
    node = adapter.get_node(territory_id)
    assert node is not None
    return float(node.attributes["habitability"])


def test_intensify_drops_habitability_over_10_ticks(services: Any) -> None:
    """US1 AS1: INTENSIFY → habitability drops ~0.2 over 10 ticks."""

    adapter = _build_world(extraction_policy=ExtractionPolicy.INTENSIFY.value)
    persistent: dict[str, Any] = {}
    initial = _habitability(adapter, "HEX_000")
    for tick in range(10):
        _tick_pipeline(adapter, services, persistent, tick)
    final = _habitability(adapter, "HEX_000")
    # INTENSIFY = -0.02/tick × 10 ticks = -0.2
    assert final == pytest.approx(initial - 0.2, abs=1e-9)


def test_continue_flattens_habitability(services: Any) -> None:
    """US1 AS2: CONTINUE → much slower decline than INTENSIFY."""

    adapter_intensify = _build_world(extraction_policy=ExtractionPolicy.INTENSIFY.value)
    adapter_continue = _build_world(extraction_policy=ExtractionPolicy.CONTINUE.value)
    persistent_i: dict[str, Any] = {}
    persistent_c: dict[str, Any] = {}
    initial_i = _habitability(adapter_intensify, "HEX_000")
    initial_c = _habitability(adapter_continue, "HEX_000")
    for tick in range(10):
        _tick_pipeline(adapter_intensify, services, persistent_i, tick)
        _tick_pipeline(adapter_continue, services, persistent_c, tick)
    drop_i = initial_i - _habitability(adapter_intensify, "HEX_000")
    drop_c = initial_c - _habitability(adapter_continue, "HEX_000")
    # CONTINUE drops at 1/4 the rate of INTENSIFY (-0.005 vs -0.02).
    assert drop_c == pytest.approx(0.05, abs=1e-9)
    assert drop_i == pytest.approx(0.2, abs=1e-9)
    assert drop_c < drop_i


def test_cease_reverses_slope_within_5_ticks(services: Any) -> None:
    """US1 AS3: CEASE → habitability recovers (≥0 slope) within 5 ticks."""

    adapter = _build_world(
        extraction_policy=ExtractionPolicy.CEASE.value,
        starting_habitability=0.5,
    )
    persistent: dict[str, Any] = {}
    initial = _habitability(adapter, "HEX_000")
    for tick in range(5):
        _tick_pipeline(adapter, services, persistent, tick)
    final = _habitability(adapter, "HEX_000")
    # CEASE = +0.01/tick × 5 ticks = +0.05
    assert final == pytest.approx(initial + 0.05, abs=1e-9)
    assert final > initial


def test_multiple_territories_all_receive_effect(services: Any) -> None:
    """US1 AS4: every claimed Territory receives the metabolic_impact."""

    adapter = _build_world(
        extraction_policy=ExtractionPolicy.INTENSIFY.value,
        n_territories=5,
    )
    persistent: dict[str, Any] = {}
    for tick in range(3):
        _tick_pipeline(adapter, services, persistent, tick)
    expected = 0.8 - 0.06  # -0.02 × 3 ticks.
    for i in range(5):
        territory_id = f"HEX_{i:03d}"
        assert _habitability(adapter, territory_id) == pytest.approx(expected, abs=1e-9)


def test_unclaimed_territory_unaffected(services: Any) -> None:
    """US1 AS sanity: a Territory with no CLAIMS edge is untouched."""

    adapter = _build_world(extraction_policy=ExtractionPolicy.INTENSIFY.value)
    adapter.add_node(
        "HEX_ORPHAN",
        "territory",
        habitability=0.5,
        regeneration_rate=0.0,
        max_biocapacity=100.0,
        extraction_intensity=0.0,
        biocapacity=100.0,
        s_bio=0.0,
        s_class=0.0,
        population=1,
        active=True,
    )
    persistent: dict[str, Any] = {}
    for tick in range(5):
        _tick_pipeline(adapter, services, persistent, tick)
    assert _habitability(adapter, "HEX_ORPHAN") == pytest.approx(0.5, abs=1e-9)
    assert _habitability(adapter, "HEX_000") == pytest.approx(0.8 - 0.1, abs=1e-9)


def test_habitability_clamped_to_unit_interval(services: Any) -> None:
    """Sanity: even with extreme metabolic_impact, habitability stays in
    [0, 1] (the clamp is applied at the MetabolismSystem read site)."""

    adapter = _build_world(
        extraction_policy=ExtractionPolicy.INTENSIFY.value,
        starting_habitability=0.01,
    )
    persistent: dict[str, Any] = {}
    for tick in range(100):
        _tick_pipeline(adapter, services, persistent, tick)
    # Long INTENSIFY exposure clamps at 0.0.
    assert _habitability(adapter, "HEX_000") == pytest.approx(0.0, abs=1e-9)
