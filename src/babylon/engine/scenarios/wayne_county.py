"""Wayne County (Detroit) tri-county acceptance scenario.

Subclass of :class:`Scenario` (ADR-006.1 / Spec 059 US4). Delegates ``build()``
to the legacy free function ``_legacy_wayne.create_wayne_county_scenario`` to preserve byte-equality
with the pre-Bundle-2 baseline (SC-007).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.engine.scenarios.base import Scenario

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


class WayneCountyScenario(Scenario):
    """Scenario port: delegates to ``_legacy_wayne.create_wayne_county_scenario``."""

    name: ClassVar[str] = "wayne_county"
    description: ClassVar[str] = "Wayne County (Detroit) tri-county acceptance scenario."

    def build(self, *args: Any, **kwargs: Any) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Delegate to the legacy free-function builder for byte-equality (SC-007)."""
        from babylon.engine.scenarios._legacy_wayne import create_wayne_county_scenario

        return create_wayne_county_scenario(*args, **kwargs)


class WayneCountyTradeScenario(Scenario):
    """Wayne County with the imperial circuit seeded (P26 U2, ADR162).

    Same build as :class:`WayneCountyScenario` plus the canonical periphery
    half of the imperial circuit (C005/C006 + EXPLOITATION/TRIBUTE/
    CLIENT_STATE — see ``_legacy_wayne._create_imperial_circuit_extension``),
    so ``_process_tribute_phase`` has an edge to walk in playable campaigns.
    A SEPARATE registered scenario rather than a flag threaded through
    ``create_new_campaign`` (build kwargs are a stated non-goal there):
    the ``cli/play.py`` composition root boots new campaigns with this one,
    while every existing ``wayne_county`` surface — SC-007 byte-equality,
    qa fixtures, the tutorial-pilot arc — keeps its unchanged default build.
    """

    name: ClassVar[str] = "wayne_county_trade"
    description: ClassVar[str] = (
        "Wayne County (Detroit) with the imperial circuit seeded (TRIBUTE live)."
    )

    def build(self, *args: Any, **kwargs: Any) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Build Wayne with ``include_imperial_circuit=True``."""
        from babylon.engine.scenarios._legacy_wayne import create_wayne_county_scenario

        kwargs.setdefault("include_imperial_circuit", True)
        return create_wayne_county_scenario(*args, **kwargs)
