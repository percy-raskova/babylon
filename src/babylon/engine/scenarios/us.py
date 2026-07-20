"""Nationwide US scenario: one Territory per US county + federal county data.

Subclass of :class:`Scenario` (ADR-006.1 / Spec 059 US4). Delegates ``build()``
to the legacy free function ``_legacy.create_us_scenario`` to preserve byte-equality
with the pre-Bundle-2 baseline (SC-007). Re-keyed from the res-3 H3 hex grid to
county grain by Amendment U / #39 T4 -- see ``_legacy.create_us_scenario``'s
docstring for the full rationale.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.engine.scenarios.base import Scenario

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


class USScenario(Scenario):
    """Scenario port: delegates to ``_legacy.create_us_scenario``."""

    name: ClassVar[str] = "us"
    description: ClassVar[str] = (
        "Nationwide US scenario: one Territory per US county (Amendment U)."
    )

    def build(self, *args: Any, **kwargs: Any) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Delegate to the legacy free-function builder for byte-equality (SC-007)."""
        from babylon.engine.scenarios._legacy import create_us_scenario

        return create_us_scenario(*args, **kwargs)
