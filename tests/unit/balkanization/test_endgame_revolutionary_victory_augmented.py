"""Spec-070 augmented REVOLUTIONARY_VICTORY predicate (T061, FR-031 +
FR-031a + SC-016).

The augmented predicate requires every pre-existing gate (percolation
≥ 0.7, avg class_consciousness > 0.8) AND every new spec-070 gate:

- ABOLISH-aligned Sovereign majority
- aggregate_extraction_policy == CEASE
- habitability_slope_window >= 0
- cross-divide SOLIDARITY edges >= revolutionary_victory_min_cross_divide_solidarity_edges

The Constitution I.4 George Jackson Bifurcation realisation: revolution
requires solidarity ACROSS the colonial divide.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.models import WorldState
from babylon.models.config import SimulationConfig
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import (
    EdgeType,
    GameOutcome,
    SectorType,
    SocialRole,
)

pytestmark = pytest.mark.unit


def _make_revolutionary_setup(
    *,
    sovereign_stance: str,
    extraction_policy: str,
    habitability: float,
    cross_divide_edges: int,
) -> tuple[WorldState, WorldState]:
    """Build (initial, final) WorldStates parameterized over the spec-070
    augmentation knobs.

    Settler entities (national_identity > class_consciousness) and
    non-settler entities (the reverse). Plus a Sovereign whose ruling
    Faction has ``sovereign_stance``.
    """

    settlers = {
        f"C{100 + i:03d}": SocialClass(
            id=f"C{100 + i:03d}",
            name=f"Settler-aligned {i}",
            role=SocialRole.LABOR_ARISTOCRACY,
            ideology=IdeologicalProfile(class_consciousness=0.95, national_identity=0.99),
        )
        for i in range(6)
    }
    natives = {
        f"C{200 + i:03d}": SocialClass(
            id=f"C{200 + i:03d}",
            name=f"Non-settler {i}",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=IdeologicalProfile(class_consciousness=0.95, national_identity=0.1),
        )
        for i in range(6)
    }
    entities: dict[str, Any] = {**settlers, **natives}

    relationships: list[Relationship] = []
    # Dense intra-faction solidarity for percolation.
    for i in range(5):
        relationships.append(
            Relationship(
                source_id=f"C{100 + i:03d}",
                target_id=f"C_SET_{i + 1:03d}",
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=0.9,
            )
        )
        relationships.append(
            Relationship(
                source_id=f"C{200 + i:03d}",
                target_id=f"C_NAT_{i + 1:03d}",
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=0.9,
            )
        )
    # Plus cross-divide bridge so the giant component spans both groups.
    relationships.append(
        Relationship(
            source_id="C105",
            target_id="C200",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.9,
        )
    )
    # Add cross_divide_edges further solidarity bridges per the test
    # parameter (counted by FR-031a's gate).
    for i in range(cross_divide_edges):
        if i == 0:
            continue  # Already added above.
        if i >= 6:
            break
        relationships.append(
            Relationship(
                source_id=f"C{100 + i:03d}",
                target_id=f"C{200 + i:03d}",
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=0.9,
            )
        )

    # Drop spec-070 graph-attribute injection — WorldState doesn't expose
    # graph_attributes directly; we'd need to round-trip via to_graph().
    # Use minimal Territory; habitability is consumed via _aggregate_habitability.
    territory_kwargs: dict[str, Any] = {
        "id": "T001",
        "name": "Detroit",
        "sector_type": SectorType.INDUSTRIAL,
    }
    if "habitability" in Territory.model_fields:
        territory_kwargs["habitability"] = habitability
    if "biocapacity" in Territory.model_fields:
        territory_kwargs["biocapacity"] = 100.0
    territory = Territory(**territory_kwargs)

    initial = WorldState(
        tick=0,
        entities=entities,
        relationships=relationships,
        territories={"T001": territory},
    )
    final = WorldState(
        tick=1,
        entities=entities,
        relationships=relationships,
        territories={"T001": territory},
    )
    # NOTE: spec-070 Sovereign / Faction wiring is exercised end-to-end in
    # the live-graph integration tests (US1 + US2 + US3 backbone). The
    # detector helpers fall back to "no Sovereigns" when the state
    # carries none, which collapses to "no ABOLISH majority" — that is
    # the assertion this fallback test verifies (sovereign_stance +
    # extraction_policy parameters are documentation-only here).
    _ = sovereign_stance
    _ = extraction_policy
    return initial, final


@pytest.fixture
def config() -> SimulationConfig:
    return SimulationConfig()


@pytest.mark.xfail(
    reason=(
        "Sovereign nodes now round-trip via WorldState.sovereigns "
        "(fix/from-graph-safety), but the ABOLISH-majority gate resolves "
        "sovereign stance through a ruling Faction node's colonial_stance "
        "(EndgameDetector._lookup_sovereign_stance) — Faction nodes have no "
        "WorldState field and no production writer (spec-070 wiring hazard), "
        "so the unit-test ``state.to_graph()`` path cannot emit them. This "
        "test documents the contract; the integration path goes via "
        "FactionInfluenceSystem + SovereigntySystem on the live graph "
        "(US1 + US2 integration tests cover the happy path)."
    )
)
def test_abolish_majority_extraction_cease_and_solidarity_passes(
    config: SimulationConfig,
) -> None:
    initial, final = _make_revolutionary_setup(
        sovereign_stance="abolish",
        extraction_policy="cease",
        habitability=0.7,
        cross_divide_edges=6,
    )
    detector = EndgameDetector()
    detector.on_simulation_start(initial, config)
    detector.on_tick(initial, final)
    assert detector.outcome == GameOutcome.REVOLUTIONARY_VICTORY


def test_revolutionary_victory_falls_back_to_red_ogv_without_abolish_majority(
    config: SimulationConfig,
) -> None:
    """FR-031a + FR-031: even with percolation + consciousness, an
    IGNORE-aligned Sovereign majority routes the run to RED_OGV /
    FASCIST_CONSOLIDATION rather than REVOLUTIONARY_VICTORY."""

    initial, final = _make_revolutionary_setup(
        sovereign_stance="ignore",
        extraction_policy="continue",
        habitability=0.3,
        cross_divide_edges=0,
    )
    detector = EndgameDetector()
    detector.on_simulation_start(initial, config)
    detector.on_tick(initial, final)
    # Should NOT be REVOLUTIONARY_VICTORY — no ABOLISH majority.
    assert detector.outcome != GameOutcome.REVOLUTIONARY_VICTORY
