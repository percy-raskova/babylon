"""Spec-116 FR-116-4.7 event-whitelist payloads (Playability Spine).

Each payload is a frozen Pydantic model mirroring the ``payload={...}`` dict
built at its live bus-publish site (named per class). These are the ten
event types the 4d.7 whitelist sweep promoted onto the wire that had no
existing payload class — SECESSION_DECLARED reuses
:class:`~babylon.models.events.balkanization_payloads.SecessionDeclaredPayload`
and the calibration trio reuses the ``_legacy`` classes.

Light Program-17 pattern (like ``reactionary_payloads`` /
``struggle_payloads``): no ``kind`` field, NOT in the ``TickEvent``
discriminated union — on a WorldState graph round-trip these replay as bare
:class:`~babylon.models.events._legacy.SimulationEvent` with a loud WARNING
(``world_state._validate_event``). Wire delivery is same-tick from live
``WorldState.events``, so the toast/journal path is unaffected.

Naming convention: ``{EventType}Event`` (legacy suffix).
"""

from __future__ import annotations

from pydantic import Field

from babylon.models.enums import EventType
from babylon.models.events._legacy import SimulationEvent


class MarketCorrectionEvent(SimulationEvent):
    """MARKET_CORRECTION event payload (market_scissors.py:342-356).

    ADR078: the scissors snapped — fictitious/real divergence exceeded
    profit-rate serviceability and the correction fired live. ``profit_rate``
    is honestly None when ``_mean_profit_rate`` (market_scissors.py:408) finds
    no territory carrying ``tick_profit_rate`` that tick (III.11 — no rate is
    fabricated).
    """

    event_type: EventType = Field(default=EventType.MARKET_CORRECTION)
    overhang: float
    serviceable: float
    profit_rate: float | None = None
    fictitious_log_before: float
    fictitious_log_after: float
    price_log_before: float
    price_log_after: float


class EntityDeathEvent(SimulationEvent):
    """ENTITY_DEATH event payload (vitality.py:181-194).

    A social-class node's full extinction (extinction / starvation /
    wealth-threshold zombie trap).
    """

    event_type: EventType = Field(default=EventType.ENTITY_DEATH)
    entity_id: str
    wealth: float
    consumption_needs: float
    s_bio: float
    s_class: float
    cause: str


class PopulationAttritionEvent(SimulationEvent):
    """POPULATION_ATTRITION event payload (vitality.py:131-142).

    Grinding attrition — coverage-ratio threshold mortality below extinction.
    """

    event_type: EventType = Field(default=EventType.POPULATION_ATTRITION)
    entity_id: str
    deaths: int
    remaining_population: int
    attrition_rate: float


class CrisisPhaseTransitionEvent(SimulationEvent):
    """CRISIS_PHASE_TRANSITION event payload (tick/system/__init__.py:994-1006).

    A county's crisis phase changed (FR-004/FR-022 of the tick-dynamics spec).
    ``profit_rate`` is honestly None when the publisher had none.
    """

    event_type: EventType = Field(default=EventType.CRISIS_PHASE_TRANSITION)
    fips: str
    previous_phase: str
    new_phase: str
    profit_rate: float | None = None
    crisis_duration: int


class BifurcationThresholdEvent(SimulationEvent):
    """BIFURCATION_THRESHOLD event payload (tick/system/__init__.py:1701-1715).

    A county's bifurcation-risk metric crossed the threshold; ``direction``
    is "revolutionary" (score < 0) or "fascist".
    """

    event_type: EventType = Field(default=EventType.BIFURCATION_THRESHOLD)
    fips: str
    score: float
    direction: str
    solidarity_density: float
    legitimation: float
    class_burden_ratio: float
    threshold: float


class EdgeModeTransitionEvent(SimulationEvent):
    """EDGE_MODE_TRANSITION event payload (edge_transition/_legacy.py:666-679).

    Feature 002: an edge's qualitative contradiction mode changed.
    """

    event_type: EventType = Field(default=EventType.EDGE_MODE_TRANSITION)
    source_id: str
    target_id: str
    from_mode: str
    to_mode: str
    predicate: str
    description: str


class CoOptiveBreakdownEvent(SimulationEvent):
    """CO_OPTIVE_BREAKDOWN event payload (edge_transition/_legacy.py:772-783).

    A CO-OPTIVE edge broke down; suppressed contradiction is released.
    """

    event_type: EventType = Field(default=EventType.CO_OPTIVE_BREAKDOWN)
    source_id: str
    target_id: str
    latent_released: dict[str, float] = Field(default_factory=dict)
    multiplier: float


class LatentContradictionReleaseEvent(SimulationEvent):
    """LATENT_CONTRADICTION_RELEASE event payload (edge_transition/_legacy.py:785-795).

    The multiplier-scaled latent field spike accompanying a breakdown.
    """

    event_type: EventType = Field(default=EventType.LATENT_CONTRADICTION_RELEASE)
    node_id: str
    released_fields: dict[str, float] = Field(default_factory=dict)


class AspectReversalEvent(SimulationEvent):
    """ASPECT_REVERSAL event payload (edge_transition/_legacy.py:848-859).

    FR-019: the dominant party (material power) on a directed edge switched.
    """

    event_type: EventType = Field(default=EventType.ASPECT_REVERSAL)
    source_id: str
    target_id: str
    previous_dominant: str
    new_dominant: str


class LevelTransitionEvent(SimulationEvent):
    """LEVEL_TRANSITION event payload (contradiction.py:524-536).

    Lawverian sublation — an opposition's contradiction lifted to a higher
    level of the lattice (aufhebung).
    """

    event_type: EventType = Field(default=EventType.LEVEL_TRANSITION)
    opposition: str
    from_level: str
    to_level: str
    gap: float
    rate: float


__all__ = [
    "AspectReversalEvent",
    "BifurcationThresholdEvent",
    "CoOptiveBreakdownEvent",
    "CrisisPhaseTransitionEvent",
    "EdgeModeTransitionEvent",
    "EntityDeathEvent",
    "LatentContradictionReleaseEvent",
    "LevelTransitionEvent",
    "MarketCorrectionEvent",
    "PopulationAttritionEvent",
]
