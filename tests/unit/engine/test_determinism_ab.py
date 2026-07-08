"""C.2(a): in-process determinism A/B gate (Constitution III.7).

Two 10-tick runs of the imperial-circuit scenario — with the global RNG
deliberately seeded differently — must produce identical per-tick event
streams (hash equality, timestamps included) and identical final states.
Canonicalization mirrors ``compute_determinism_hash``
(persistence/conservation_audit.py): sorted-key compact JSON, sha256.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any

import pytest

from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation_engine import step
from babylon.models import WorldState

pytestmark = pytest.mark.unit

_TICKS = 10  # fixed upper bound


def _run(global_seed: int) -> tuple[list[str], WorldState]:
    """Run the scenario for ``_TICKS`` ticks, hashing each tick's events.

    Args:
        global_seed: Seed for the *global* RNG — deliberately varied
            between runs to prove the engine never consults it.

    Returns:
        Tuple of (per-tick event-stream sha256 hashes, final WorldState).
    """
    random.seed(global_seed)  # prove the engine never consults global RNG
    state, config, defines = create_imperial_circuit_scenario()
    ctx: dict[str, Any] = {}
    tick_hashes: list[str] = []
    for _ in range(_TICKS):
        state = step(state, config, persistent_context=ctx, defines=defines)
        canon = json.dumps(
            [e.model_dump(mode="json") for e in state.events],
            sort_keys=True,
            separators=(",", ":"),
        )
        tick_hashes.append(hashlib.sha256(canon.encode("utf-8")).hexdigest())
    return tick_hashes, state


def test_two_runs_produce_identical_event_hashes_and_final_state() -> None:
    """III.7: event streams and final state are pure functions of the scenario."""
    hashes_a, final_a = _run(global_seed=1234)
    hashes_b, final_b = _run(global_seed=5678)

    assert hashes_a == hashes_b, (
        f"per-tick event-hash divergence at tick(s) "
        f"{[i for i, (a, b) in enumerate(zip(hashes_a, hashes_b, strict=True)) if a != b]}"
    )
    assert final_a.model_dump(mode="json") == final_b.model_dump(mode="json")
