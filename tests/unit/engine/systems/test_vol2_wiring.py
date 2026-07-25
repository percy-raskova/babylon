"""Tests for ImperialRentSystem._invoke_vol2_circulation_if_wired (Vol II U4).

Exercises the sub-stage 5c wiring in isolation: given all four gate keys,
the real Vol2CirculationStep-shaped ``.step(...)`` call happens and its
return value is stashed into ``context["vol2_circulation_result"]`` for the
ConservationAuditor's ``circulation_preserves_sum_v`` evaluator to read
post-hoc. A stub step (not a real Vol2CirculationStep) keeps this test fast
and DB/graph-free, mirroring ``test_phi_wiring.py``'s convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

from babylon.engine.context import TickContext
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.topology.graph import BabylonGraph

pytestmark = [pytest.mark.unit]


@dataclass(frozen=True)
class _FakeResult:
    tick: int
    pre_total_v: float
    post_total_v_in_area: float
    boundary_out_total_v: float


class _FakeVol2Step:
    """Minimal step-shaped stub: records its call, returns a fixed result."""

    def __init__(self, result: _FakeResult) -> None:
        self._result = result
        self.calls: list[dict[str, object]] = []

    def step(self, **kwargs: object) -> _FakeResult:
        self.calls.append(kwargs)
        return self._result


def test_all_four_keys_present_invokes_step_and_stashes_result() -> None:
    """Full gate satisfied: step() runs, its result lands in context."""
    result = _FakeResult(
        tick=3, pre_total_v=1000.0, post_total_v_in_area=700.0, boundary_out_total_v=300.0
    )
    fake_step = _FakeVol2Step(result)
    session_id = uuid4()
    ctx = TickContext(tick=3)
    ctx.persistent_data["vol2_step"] = fake_step
    ctx.persistent_data["boundary_flow_register"] = object()
    ctx.persistent_data["session_id"] = session_id
    ctx.persistent_data["simulated_year"] = 2015

    system = ImperialRentSystem()
    system._invoke_vol2_circulation_if_wired(BabylonGraph(), ctx)  # noqa: SLF001

    assert len(fake_step.calls) == 1
    assert fake_step.calls[0]["session_id"] == session_id
    assert fake_step.calls[0]["tick"] == 3
    assert fake_step.calls[0]["simulated_year"] == 2015
    assert ctx.persistent_data["vol2_circulation_result"] is result


@pytest.mark.parametrize(
    "missing_key",
    ["vol2_step", "boundary_flow_register", "session_id", "simulated_year"],
)
def test_any_missing_key_is_a_silent_no_op(missing_key: str) -> None:
    """Back-compat: any single missing gate key skips the sub-stage entirely."""
    fake_step = _FakeVol2Step(
        _FakeResult(tick=1, pre_total_v=0.0, post_total_v_in_area=0.0, boundary_out_total_v=0.0)
    )
    keys: dict[str, object] = {
        "vol2_step": fake_step,
        "boundary_flow_register": object(),
        "session_id": uuid4(),
        "simulated_year": 2015,
    }
    del keys[missing_key]
    ctx = TickContext(tick=1)
    for k, v in keys.items():
        ctx.persistent_data[k] = v

    system = ImperialRentSystem()
    system._invoke_vol2_circulation_if_wired(BabylonGraph(), ctx)  # noqa: SLF001

    assert fake_step.calls == []
    assert "vol2_circulation_result" not in ctx.persistent_data
