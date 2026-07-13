"""Smoke test for the dynamic-sentinel shared-tick substrate (``conftest.py``).

Proves the ``shared_tick`` fixture builds one deterministic artifact the four
dynamic sentinels can read: a live final ``WorldState``, a full dense trace, and
two seed-identical run hashes. This is the foundation the Determinism /
Round-Trip / Conservation / Seam-liveness sentinels each consume read-only.
"""

from __future__ import annotations

import pytest

from babylon.sentinels.dynamic import DynamicArtifact

pytestmark = pytest.mark.unit


def test_shared_tick_builds_a_complete_artifact(shared_tick: DynamicArtifact) -> None:
    """The fixture yields a fully-populated artifact for the dynamic sentinels."""
    assert shared_tick.scenario == "imperial_circuit"
    assert shared_tick.ticks == 52
    assert shared_tick.final_state is not None
    # One header + one row per tick (0..52 inclusive).
    assert len(shared_tick.trace.rows) == shared_tick.ticks + 1
    assert len(shared_tick.trace.header) > 0


def test_shared_tick_is_deterministic(shared_tick: DynamicArtifact) -> None:
    """Two seed-identical runs hash equal — the substrate is reproducible.

    This is the witness the Determinism sentinel is built on; if it ever reds,
    the shared scenario has acquired a non-determinism source (Constitution
    III.7) and every dynamic sentinel downstream is untrustworthy.
    """
    assert shared_tick.hash_a == shared_tick.hash_b
