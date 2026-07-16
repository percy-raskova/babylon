"""End-game detector fixtures for spec-065 T060/T061/T062.

Detectors:

* :class:`ImperialCollapseAtTick250` — fires ``IMPERIAL_COLLAPSE`` on tick 250.
* :class:`NeverFires` — returns None forever.
* :class:`FireAtTick` — parameterized fire tick, for direct instantiation.
* :class:`FireAtTick3` — fires ``IMPERIAL_COLLAPSE`` on tick 3; zero-arg
  constructor so it is reachable via ``--endgame-detector``'s dotted-path
  resolution (:meth:`WorldStateBridge.set_endgame_detector` instantiates
  with no args, so the parameterized :class:`FireAtTick` cannot be aimed
  at a non-default tick that way).

All implement the implicit ``check(world, tick) -> EndgameEvent | None``
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


class FireAtTick3:
    """Detector that always fires IMPERIAL_COLLAPSE at tick 3.

    Zero-arg constructor (unlike :class:`FireAtTick`) so it can be
    resolved via the ``--endgame-detector`` dotted-path mechanism, which
    instantiates the resolved class with no constructor arguments.
    """

    def check(self, world: Any, tick: int) -> dict[str, Any] | None:  # noqa: ARG002
        if tick == 3:
            return {
                "tick": 3,
                "condition": "IMPERIAL_COLLAPSE",
                "details": {"trigger": "test_fixture"},
            }
        return None
