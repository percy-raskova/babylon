"""Labor-aristocracy scenario emphasising W_c > V_c (imperial pacification).

Subclass of :class:`Scenario` (ADR-006.1 / Spec 059 US4). Delegates ``build()``
to the legacy free function ``_legacy.create_labor_aristocracy_scenario`` to preserve byte-equality
with the pre-Bundle-2 baseline (SC-007).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.engine.scenarios.base import Scenario

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


class LaborAristocracyScenario(Scenario):
    """Scenario port: delegates to ``_legacy.create_labor_aristocracy_scenario``."""

    name: ClassVar[str] = "labor_aristocracy"
    description: ClassVar[str] = (
        "Labor-aristocracy scenario emphasising W_c > V_c (imperial pacification)."
    )

    def build(self, *args: Any, **kwargs: Any) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Delegate to the legacy free-function builder for byte-equality (SC-007)."""
        from babylon.engine.scenarios._legacy import create_labor_aristocracy_scenario

        return create_labor_aristocracy_scenario(*args, **kwargs)
