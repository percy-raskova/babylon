"""The declared shape of the dynamic sentinels' shared tick artifact.

The four *dynamic* sentinels (Determinism, Round-Trip, Economic-Conservation,
Seam Sensor-2 liveness) each assert an invariant over one deterministic tick
run. :class:`DynamicArtifact` is the contract for that run — built once per test
session by the ``shared_tick`` fixture (``tests/unit/sentinels/conftest.py``) and
consumed read-only by every dynamic sentinel, so the tick is run twice total,
not once per sentinel.

This module is deliberately dependency-free (``Any``-typed state/trace, no engine
or topology import) so it can live at the sentinels' layer-0.5 boundary: the
*declared contract* stays in the package while the engine-running harness that
populates it lives in the test layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DynamicArtifact:
    """One deterministic tick run, captured for read-only sentinel consumption.

    Every field is either an immutable value or a frozen ``WorldState`` whose
    ``to_graph()`` builds fresh copies, so concurrent read-only consumers cannot
    corrupt shared state.

    :ivar scenario: The scenario name the run was built from.
    :ivar ticks: The number of ticks run (``0..ticks``).
    :ivar final_state: The live ``WorldState`` after the final tick (run A) — the
        input to Seam Sensor-2 liveness and the Round-Trip round-trip. Typed
        ``Any`` to keep this module below the engine/models import weight.
    :ivar trace: The full per-tick ``regression_test.DenseTrace`` of run A — what
        Economic-Conservation walks to check ``K+v+s`` per tick.
    :ivar hash_a: SHA-256 of run A's canonical dense-trace CSV bytes.
    :ivar hash_b: SHA-256 of an independent, seed-identical run B — Determinism
        asserts ``hash_a == hash_b`` (any inequality is a non-determinism bug).
    """

    scenario: str
    ticks: int
    final_state: Any
    trace: Any
    hash_a: str
    hash_b: str
