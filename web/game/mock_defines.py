"""Non-empirical progression coefficients for the MockEngineBridge.

These values are **scaffolding placeholders** designed to produce
visible state changes in the UI.  They have no theoretical basis
and must NEVER be used for engine calibration or gameplay tuning.

.. warning::
    This file is disposable.  It will be deleted when the real engine
    is wired into ``engine_bridge.py``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MockDefines:
    """Frozen coefficients for deterministic mock progression.

    All values are hand-tuned for visual feedback, not realism.
    """

    # Passive drift per tick
    HEAT_DECAY: float = 0.95

    # EDUCATE verb
    EDUCATE_CONSCIOUSNESS: float = 0.05
    EDUCATE_HEAT: float = 0.02

    # MOBILIZE verb
    MOBILIZE_HEAT: float = 0.10
    MOBILIZE_AGITATION: float = 0.03

    # ATTACK verb
    ATTACK_HEAT: float = 0.15
    ATTACK_CONSCIOUSNESS: float = -0.02
    ATTACK_WEALTH_DAMAGE: float = 5.0

    # CAMPAIGN verb
    CAMPAIGN_CONSCIOUSNESS: float = 0.03
    CAMPAIGN_ADJACENT: float = 0.01

    # AID verb
    AID_HEAT: float = -0.05
    AID_WEALTH: float = 3.0

    # REPRODUCE verb
    REPRODUCE_MEMBERSHIP: int = 1
    REPRODUCE_COHESION: float = 0.02

    # Action resolution
    INITIATIVE_SCORE: float = 0.5
    ACTION_COST: float = 1.0

    # Clamping
    HEAT_FLOOR: float = 0.0
    HEAT_CEILING: float = 1.0
    CONSCIOUSNESS_FLOOR: float = 0.0
    CONSCIOUSNESS_CEILING: float = 1.0
    WEALTH_FLOOR: float = 0.0
