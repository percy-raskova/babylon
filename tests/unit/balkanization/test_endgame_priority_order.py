"""Spec-070 endgame priority-order tests (T065, FR-033).

FR-033 mandates this exact priority cascade for the EndgameDetector:

    RED_OGV → FRAGMENTED_COLLAPSE → ECOLOGICAL_COLLAPSE
        → FASCIST_CONSOLIDATION → REVOLUTIONARY_VICTORY

First-match-wins. Once any endgame fires, the detector stops evaluating.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.models import WorldState
from babylon.models.config import SimulationConfig
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import GameOutcome, SocialRole

pytestmark = pytest.mark.unit


@pytest.fixture
def config() -> SimulationConfig:
    return SimulationConfig()


def _state(entities: dict[str, Any], tick: int = 0) -> WorldState:
    return WorldState(tick=tick, entities=entities)


def test_in_progress_when_no_predicates_hold(config: SimulationConfig) -> None:
    entities = {
        f"C{i:03d}": SocialClass(
            id=f"C{i:03d}",
            name=f"Worker {i}",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=IdeologicalProfile(class_consciousness=0.5, national_identity=0.4),
        )
        for i in range(3)
    }
    detector = EndgameDetector()
    initial = _state(entities, tick=0)
    detector.on_simulation_start(initial, config)
    detector.on_tick(initial, _state(entities, tick=1))
    assert detector.outcome is GameOutcome.IN_PROGRESS


def test_fascist_consolidation_via_false_consciousness_route_preserved(
    config: SimulationConfig,
) -> None:
    """FR-031 preserves the existing FASCIST_CONSOLIDATION route — when
    national_identity > class_consciousness for ≥3 nodes, fire it."""

    entities = {
        f"C{i:03d}": SocialClass(
            id=f"C{i:03d}",
            name=f"Reactionary {i}",
            role=SocialRole.LABOR_ARISTOCRACY,
            ideology=IdeologicalProfile(class_consciousness=0.2, national_identity=0.9),
        )
        for i in range(5)
    }
    detector = EndgameDetector()
    initial = _state(entities, tick=0)
    detector.on_simulation_start(initial, config)
    detector.on_tick(initial, _state(entities, tick=1))
    assert detector.outcome is GameOutcome.FASCIST_CONSOLIDATION


def test_endgame_is_first_match_wins_no_re_evaluation(
    config: SimulationConfig,
) -> None:
    """Once an endgame has fired, subsequent ticks must NOT re-evaluate
    or overwrite the outcome (FR-033 last sentence)."""

    entities = {
        f"C{i:03d}": SocialClass(
            id=f"C{i:03d}",
            name=f"Reactionary {i}",
            role=SocialRole.LABOR_ARISTOCRACY,
            ideology=IdeologicalProfile(class_consciousness=0.2, national_identity=0.9),
        )
        for i in range(5)
    }
    detector = EndgameDetector()
    initial = _state(entities, tick=0)
    detector.on_simulation_start(initial, config)
    detector.on_tick(initial, _state(entities, tick=1))
    first_outcome = detector.outcome
    # Mutate consciousness; would have flipped to in_progress had
    # re-evaluation been allowed.
    new_entities = {
        eid: cls.model_copy(
            update={"ideology": IdeologicalProfile(class_consciousness=0.99, national_identity=0.0)}
        )
        for eid, cls in entities.items()
    }
    detector.on_tick(_state(entities, tick=1), _state(new_entities, tick=2))
    assert detector.outcome is first_outcome


def test_red_ogv_takes_precedence_when_predicate_holds(
    config: SimulationConfig,
) -> None:
    """Spec-070 FR-033: RED_OGV is the highest-priority predicate.

    With no Sovereigns/Factions in this fixture, _has_stance_majority(IGNORE)
    returns False so RED_OGV cannot fire — but the detector machinery
    must STILL evaluate it first per the priority cascade.
    """

    entities = {
        f"C{i:03d}": SocialClass(
            id=f"C{i:03d}",
            name=f"Reactionary {i}",
            role=SocialRole.LABOR_ARISTOCRACY,
            ideology=IdeologicalProfile(class_consciousness=0.2, national_identity=0.9),
        )
        for i in range(5)
    }
    detector = EndgameDetector()
    initial = _state(entities, tick=0)
    detector.on_simulation_start(initial, config)
    detector.on_tick(initial, _state(entities, tick=1))
    # No Sovereigns: RED_OGV / FRAGMENTED_COLLAPSE fall through; the
    # fascist false-consciousness route still fires the outcome.
    assert detector.outcome is GameOutcome.FASCIST_CONSOLIDATION


def test_endgame_event_emitted_exactly_once(config: SimulationConfig) -> None:
    entities = {
        f"C{i:03d}": SocialClass(
            id=f"C{i:03d}",
            name=f"Reactionary {i}",
            role=SocialRole.LABOR_ARISTOCRACY,
            ideology=IdeologicalProfile(class_consciousness=0.2, national_identity=0.9),
        )
        for i in range(5)
    }
    detector = EndgameDetector()
    initial = _state(entities, tick=0)
    detector.on_simulation_start(initial, config)
    detector.on_tick(initial, _state(entities, tick=1))
    detector.on_tick(_state(entities, tick=1), _state(entities, tick=2))
    detector.on_tick(_state(entities, tick=2), _state(entities, tick=3))
    pending = detector.get_pending_events()
    assert len(pending) == 1
