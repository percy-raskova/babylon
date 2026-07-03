"""Spec-070 observability projections tests (T115, FR-051 + SC-007 +
SC-013)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.engine.graph import BabylonGraph
from babylon.engine.observers.balkanization_projections import (
    SovereignProjection,
    TerritoryProjection,
    observe_sovereign,
    observe_territory,
)
from babylon.models.enums import ExtractionPolicy

pytestmark = pytest.mark.unit


def _seed_state(adapter: BabylonGraph) -> None:
    adapter.add_node(
        "SOV_USA_FED",
        "sovereign",
        name="United States Federal Government",
        sovereignty_type="recognized_state",
        legitimacy=1.0,
        ruling_faction_id="FAC_RESTORATIONIST",
        extraction_policy="intensify",
    )
    adapter.add_node("HEX_001", "territory", habitability=0.8)
    adapter.add_node("HEX_002", "territory", habitability=0.6)
    adapter.add_edge(
        "SOV_USA_FED",
        "HEX_001",
        "claims",
        control_level=1.0,
        legal_status="de_jure",
    )
    adapter.add_edge(
        "SOV_USA_FED",
        "HEX_002",
        "claims",
        control_level=0.9,
        legal_status="de_jure",
    )


def test_observe_sovereign_returns_frozen_projection() -> None:
    adapter = BabylonGraph()
    _seed_state(adapter)

    projection = observe_sovereign(adapter, "SOV_USA_FED")

    assert isinstance(projection, SovereignProjection)
    assert projection.sovereign_id == "SOV_USA_FED"
    assert projection.extraction_policy is ExtractionPolicy.INTENSIFY
    assert projection.metabolic_impact == pytest.approx(-0.02)
    assert projection.claimed_territory_count == 2
    # Mean habitability = (0.8 + 0.6) / 2 = 0.7; after 20 ticks of
    # INTENSIFY (-0.02/tick), projected = 0.7 - 0.4 = 0.3.
    assert projection.projected_habitability == pytest.approx(0.3)


def test_observe_sovereign_frozen_cannot_mutate() -> None:
    adapter = BabylonGraph()
    _seed_state(adapter)
    projection = observe_sovereign(adapter, "SOV_USA_FED")
    assert projection is not None
    with pytest.raises(ValidationError):
        projection.legitimacy = 0.5  # type: ignore[misc]


def test_observe_sovereign_returns_none_for_unknown_id() -> None:
    adapter = BabylonGraph()
    assert observe_sovereign(adapter, "SOV_GHOST") is None


def test_observe_sovereign_respects_horizon_override() -> None:
    adapter = BabylonGraph()
    _seed_state(adapter)
    # 5-tick horizon under INTENSIFY: 0.7 - 5×0.02 = 0.6.
    projection = observe_sovereign(adapter, "SOV_USA_FED", horizon_ticks=5)
    assert projection is not None
    assert projection.projected_habitability == pytest.approx(0.6)


def test_observe_sovereign_projection_clamps_to_unit_interval() -> None:
    adapter = BabylonGraph()
    adapter.add_node(
        "SOV_TINY",
        "sovereign",
        name="X",
        sovereignty_type="provisional",
        legitimacy=0.0,
        ruling_faction_id=None,
        extraction_policy="intensify",
    )
    adapter.add_node("HEX_A", "territory", habitability=0.01)
    adapter.add_edge(
        "SOV_TINY",
        "HEX_A",
        "claims",
        control_level=1.0,
        legal_status="de_facto",
    )
    # 100-tick INTENSIFY would project to -1.99 — must clamp to 0.0.
    projection = observe_sovereign(adapter, "SOV_TINY", horizon_ticks=100)
    assert projection is not None
    assert projection.projected_habitability == pytest.approx(0.0)


def test_observe_territory_returns_frozen_projection() -> None:
    adapter = BabylonGraph()
    _seed_state(adapter)
    projection = observe_territory(adapter, "HEX_001")
    assert isinstance(projection, TerritoryProjection)
    assert projection.territory_id == "HEX_001"
    assert projection.habitability == pytest.approx(0.8)
    assert projection.effective_sovereign_id == "SOV_USA_FED"
    assert projection.effective_control_level == pytest.approx(1.0)
    assert projection.is_dual_power is False
    assert projection.claimant_count == 1


def test_observe_territory_flags_dual_power() -> None:
    adapter = BabylonGraph()
    _seed_state(adapter)
    adapter.add_node(
        "SOV_BREAK",
        "sovereign",
        name="Breakaway",
        sovereignty_type="secessionist",
        legitimacy=0.5,
        ruling_faction_id="FAC_DECOLONIAL",
        extraction_policy="cease",
    )
    adapter.add_edge(
        "SOV_BREAK",
        "HEX_001",
        "claims",
        control_level=0.5,
        legal_status="disputed",
    )
    projection = observe_territory(adapter, "HEX_001")
    assert projection is not None
    assert projection.is_dual_power is True
    assert projection.claimant_count == 2


def test_observe_territory_returns_none_for_unknown_id() -> None:
    adapter = BabylonGraph()
    assert observe_territory(adapter, "HEX_NULL") is None


def test_projections_are_deterministic() -> None:
    """Calling either projection twice on identical state yields
    byte-identical results."""

    adapter = BabylonGraph()
    _seed_state(adapter)
    p1 = observe_sovereign(adapter, "SOV_USA_FED")
    p2 = observe_sovereign(adapter, "SOV_USA_FED")
    assert p1 == p2
    t1 = observe_territory(adapter, "HEX_001")
    t2 = observe_territory(adapter, "HEX_001")
    assert t1 == t2
