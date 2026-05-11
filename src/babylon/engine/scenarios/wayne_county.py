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
