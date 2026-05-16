"""Unit tests for Bug E — engine integration into bridged runner (spec-066 US2).

Spec: 066-marx-coherence-fixes (T024-T025).

These tests verify that:
- ``ServiceContainer`` is constructed exactly once before the tick loop
- ``SimulationEngine.run_tick(...)`` is called exactly once per tick

Without these checks, the engine is silently bypassed (the spec-065 bug
that this spec addresses): the runner persists state via the bridge but
never invokes engine systems, so consciousness/ideology don't evolve.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


def test_service_container_constructed_once_before_tick_loop() -> None:
    """T024: ServiceContainer.create is called exactly once across a 5-tick run."""
    pytest.skip("WIP — implemented in spec-066 US2 phase (T034 instantiates services)")


def test_engine_run_tick_called_per_tick() -> None:
    """T025: SimulationEngine.run_tick is called exactly 5 times for a 5-tick run
    (once per tick from tick 0 through tick 4)."""
    pytest.skip("WIP — implemented in spec-066 US2 phase (T035-T036 invokes engine)")
