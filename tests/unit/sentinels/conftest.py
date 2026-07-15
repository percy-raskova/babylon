"""Shared dynamic-tick substrate for the ``babylon.sentinels`` family.

The four *dynamic* sentinels (Determinism, Round-Trip, Economic-Conservation,
and Seam Sensor-2 liveness) all need the same thing: a real deterministic tick
run so they can assert an invariant over the resulting state / trace. Running a
separate tick per sentinel would be the naive "5× cost" the compute-optimization
spec set out to avoid. Instead this module runs **one** deterministic scenario
(twice — the second run exists solely so Determinism can assert seed-identical
reproducibility) inside a **session-scoped** fixture, and every dynamic sentinel
consumes the resulting :class:`DynamicArtifact` **read-only**.

Why a fixture and not a ``babylon.sentinels`` module: building the artifact runs
the engine (``simulation_engine.step``), which is far above the sentinels'
layer-0.5 import boundary. The engine-running harness therefore lives in the test
layer (which may import anything); only the *declared registries* of what must be
live/conserved stay in the layer-0.5 package. This keeps the package pure and
static while the dynamic sensors run in the fast-gate ``test:unit`` leg.

Reuse (DRY): the tick loop is built from ``tools/regression_test.py``'s existing
primitives (``create_scenario`` / ``step`` / ``_dense_header`` / ``_dense_row`` /
``dense_trace_to_csv_bytes``) — the same canonical dense-trace byte stream the
determinism contract is defined against — so no new tick or hashing logic is
introduced. ``regression_test.py`` itself is not modified, so ``qa:regression``
stays byte-identical.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import pytest

from babylon.sentinels.dynamic import DynamicArtifact

# ``tools/`` is not on the pytest pythonpath; add it like tests/unit/tools/ does.
_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import regression_test as rt  # type: ignore[import-not-found]  # noqa: E402

#: The deterministic scenario the shared artifact is built from. ``imperial_circuit``
#: SURVIVES all 52 ticks (no early death-break) and exercises the imperial-rent /
#: exploitation observables the dynamic sentinels assert over.
SHARED_SCENARIO: str = "imperial_circuit"
SHARED_TICKS: int = rt.DEFAULT_MAX_TICKS


def _run_once(scenario: str, max_ticks: int) -> tuple[Any, Any]:
    """Run ``scenario`` for ``max_ticks`` and return ``(final_state, DenseTrace)``.

    A minimal deterministic tick loop built from ``regression_test`` primitives.
    Unlike ``_run_scenario_ticks`` it captures the *live final state* (needed by
    the liveness and round-trip sentinels) and skips the sampled-checkpoint /
    death-break bookkeeping the sentinels do not use — ``imperial_circuit``
    survives its full run, so no death-break is required.

    :param scenario: Scenario name from ``regression_test.SCENARIOS``.
    :param max_ticks: Number of ticks to run.
    :returns: The final ``WorldState`` and the run's ``DenseTrace``.
    """
    state, sim_config, defines = rt.create_scenario(scenario)
    context: dict[str, Any] = {}

    header, entity_ids, edge_keys = rt._dense_header(state)
    rows = [rt._dense_row(state, 0, entity_ids, edge_keys)]
    for tick in range(1, max_ticks + 1):
        state = rt.step(state, sim_config, context, defines)
        rows.append(rt._dense_row(state, tick, entity_ids, edge_keys))

    trace = rt.DenseTrace(scenario=scenario, header=header, rows=rows)
    return state, trace


@pytest.fixture(scope="session")
def shared_tick() -> DynamicArtifact:
    """Build the one shared deterministic tick artifact for the dynamic sentinels.

    Session-scoped so the ~0.7 s two-run cost is paid once (per xdist worker),
    not per sentinel. Run B is a genuine seed-identical re-execution — the only
    irreducible second tick — so Determinism has a real reproducibility witness.

    :returns: The frozen :class:`DynamicArtifact` every dynamic sentinel reads.
    """
    state_a, trace_a = _run_once(SHARED_SCENARIO, SHARED_TICKS)
    _state_b, trace_b = _run_once(SHARED_SCENARIO, SHARED_TICKS)

    hash_a = hashlib.sha256(rt.dense_trace_to_csv_bytes(trace_a)).hexdigest()
    hash_b = hashlib.sha256(rt.dense_trace_to_csv_bytes(trace_b)).hexdigest()

    return DynamicArtifact(
        scenario=SHARED_SCENARIO,
        ticks=SHARED_TICKS,
        final_state=state_a,
        trace=trace_a,
        hash_a=hash_a,
        hash_b=hash_b,
    )
