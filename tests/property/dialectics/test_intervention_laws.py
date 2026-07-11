"""Property laws for stance interventions (earn-its-keep §9.1).

Player verbs act as morphism mutations — a signed shove on a target
opposition's balance. Whatever the stream of shoves, the balance stays a
lawful signed dominance in [-1, 1]: this clamp is the load-bearing invariant
(``OppositionState.balance`` is otherwise a bare float under ``model_copy``,
which does not re-validate). The mutation probe for C2 drops the clamp; this
law is what kills that mutant.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.domain.dialectics.core.coupling import StanceIntervention, apply_interventions
from babylon.domain.dialectics.core.opposition import OppositionState

pytestmark = [pytest.mark.property, pytest.mark.math]

_balances = st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_deltas = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)


@given(start=_balances, deltas=st.lists(_deltas, max_size=12))
@settings(max_examples=300, deadline=None)
def test_balance_stays_in_unit_interval_under_any_stream(start: float, deltas: list[float]) -> None:
    state = OppositionState(key="k", tick=0, gap=0.5, balance=start, rate=0.0, leading_pole="a")
    interventions = [
        StanceIntervention(target_key="k", delta_balance=d, source="hyp") for d in deltas
    ]
    (result,) = apply_interventions((state,), interventions)
    assert -1.0 <= result.balance <= 1.0


@given(start=_balances, deltas=st.lists(_deltas, min_size=1, max_size=12))
@settings(max_examples=300, deadline=None)
def test_leading_pole_agrees_with_the_clamped_sign(start: float, deltas: list[float]) -> None:
    state = OppositionState(key="k", tick=0, gap=0.5, balance=start, rate=0.0, leading_pole="a")
    interventions = [
        StanceIntervention(target_key="k", delta_balance=d, source="hyp") for d in deltas
    ]
    (result,) = apply_interventions((state,), interventions)
    if result.balance < 0.0:
        assert result.leading_pole == "a"
    elif result.balance > 0.0:
        assert result.leading_pole == "b"
    else:
        assert result.leading_pole == state.leading_pole  # zero holds previous
