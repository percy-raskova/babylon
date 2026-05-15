"""End-game detector fixtures for spec-065 T060/T061/T062.

Two detectors:

* :class:`ImperialCollapseAtTick250` — fires ``IMPERIAL_COLLAPSE`` on tick 250.
* :class:`NeverFires` — returns None forever.

Both implement the implicit ``check(world, tick) -> EndgameEvent | None``
protocol used by :meth:`WorldStateBridge.poll_endgame`.
"""

from __future__ import annotations

from typing import Any


class ImperialCollapseAtTick250:
    """Detector that always fires IMPERIAL_COLLAPSE at tick 250."""

    def check(self, world: Any, tick: int) -> dict[str, Any] | None:  # noqa: ARG002
        if tick == 250:
            return {
                "tick": 250,
                "condition": "IMPERIAL_COLLAPSE",
                "details": {"trigger": "test_fixture"},
            }
        return None


class NeverFires:
    """Detector that returns None at every tick."""

    def check(self, world: Any, tick: int) -> None:  # noqa: ARG002
        return None


class FireAtTick(ImperialCollapseAtTick250):
    """Parameterized: fires IMPERIAL_COLLAPSE at the configured tick."""

    def __init__(self, fire_at: int = 250) -> None:
        self._fire_at = fire_at

    def check(self, world: Any, tick: int) -> dict[str, Any] | None:  # noqa: ARG002
        if tick == self._fire_at:
            return {
                "tick": self._fire_at,
                "condition": "IMPERIAL_COLLAPSE",
                "details": {"trigger": "test_fixture"},
            }
        return None
