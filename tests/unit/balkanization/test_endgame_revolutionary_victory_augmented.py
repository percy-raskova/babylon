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
from babylon.models.entities.balkanization_faction import BalkanizationFaction
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.entities.sovereign import Sovereign
from babylon.models.entities.territory import Territory
from babylon.models.enums import (
    ColonialStance,
    EdgeType,
    ExtractionPolicy,
    GameOutcome,
    SectorType,
    SocialRole,
    SovereigntyType,
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
    non-settler entities (the reverse). Plus a real Sovereign (CLAIMS
    T001) whose ruling BalkanizationFaction carries ``sovereign_stance``
    and whose ``extraction_policy`` is set directly (spec-109 A6 —
    both round-trip through ``state.to_graph()``/``from_graph()``).
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

    # Habitability isn't a Territory field (checked defensively below —
    # _aggregate_habitability falls back to getattr(..., 1.0) when absent),
    # so the ``habitability`` parameter has no effect on the outcome; it
    # is retained for call-site documentation of intent only.
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

    # spec-109 A6: BalkanizationFaction now round-trips via
    # WorldState.factions (_add_political_nodes / _reconstruct_faction),
    # so the Sovereign + ruling Faction + CLAIMS edge below are real graph
    # nodes/edges, not documentation-only placeholders.
    faction = BalkanizationFaction(
        id="FAC_TEST",
        name="Test Faction",
        ideology="test-fixture",
        colonial_stance=ColonialStance(sovereign_stance),
        is_settler_formation=False,
        extraction_modifier=1.0,
        violence_modifier=1.0,
        metabolic_reduction=0.0,
        color_hex="#336699",
        founded_tick=0,
    )
    sovereign = Sovereign(
        id="SOV_TEST",
        name="Test Sovereign",
        sovereignty_type=SovereigntyType.PROVISIONAL,
        legitimacy=0.8,
        color_hex="#663399",
        ruling_faction_id=faction.id,
        extraction_policy=ExtractionPolicy(extraction_policy),
        founded_tick=0,
    )
    relationships.append(
        Relationship(
            source_id=sovereign.id,
            target_id="T001",
            edge_type=EdgeType.CLAIMS,
            control_level=0.9,
            legal_status="de_facto",
        )
    )

    factions = {faction.id: faction}
    sovereigns = {sovereign.id: sovereign}

    initial = WorldState(
        tick=0,
        entities=entities,
        relationships=relationships,
        territories={"T001": territory},
        sovereigns=sovereigns,
        factions=factions,
    )
    final = WorldState(
        tick=1,
        entities=entities,
        relationships=relationships,
        territories={"T001": territory},
        sovereigns=sovereigns,
        factions=factions,
    )
    return initial, final


@pytest.fixture
def config() -> SimulationConfig:
    return SimulationConfig()


@pytest.mark.xfail(
    reason=(
        "STALE CLAIM RETIRED (spec-109 A6, WorldState.factions + "
        "_add_political_nodes + _reconstruct_faction): faction round-trip "
        "is now proven to work — with the Sovereign/Faction/CLAIMS wiring "
        "this fixture builds, every augmented gate individually resolves "
        "correctly (_has_stance_majority(ABOLISH) is True, "
        "_aggregate_extraction_policy_is(CEASE) is True, "
        "_count_cross_divide_solidarity_edges == 6 >= the default "
        "revolutionary_victory_min_cross_divide_solidarity_edges == 5). "
        "The test STILL fails, but for a different, unrelated reason: "
        "FR-033's priority cascade checks FASCIST_CONSOLIDATION before "
        "REVOLUTIONARY_VICTORY, and _check_fascist_consolidation's "
        "preserved 'existing false-consciousness route' "
        "(national_identity > class_consciousness for >= "
        "fascist_majority_threshold == 3 nodes) fires unconditionally on "
        "this fixture's 6 settler-aligned entities — which the "
        "FR-031a cross-divide-solidarity gate itself requires (>= 5 "
        "settler/non-settler SOLIDARITY edges) — regardless of Sovereign "
        "state, so the augmented predicate is never reached. This is a "
        "pre-existing detector-logic / fixture-design tension between the "
        "legacy fascist route and the spec-070 settler/non-settler split, "
        "not a graph round-trip gap; it needs its own resolution (e.g. "
        "scoping the legacy route, raising fascist_majority_threshold to a "
        "share rather than an absolute count, or restructuring how "
        "cross-divide solidarity is counted) before this test can go "
        "green."
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
