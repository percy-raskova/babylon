"""Property laws for the composition combinators (earn-its-keep §9.1).

The dormant design ratified two combinator bounds; here they are executable
Hypothesis laws over *arbitrary* component readings, not examples:

- ``product`` (D1 ⊗ D2): ``gap(⊗) ≤ min(gap1, gap2)`` — a conjunction is
  sharp only if both conjuncts are sharp.
- ``sum_`` (D1 ⊕ D2): ``gap(⊕) ≥ max(gap1, gap2)`` — a disjunction is at
  least as sharp as its sharpest disjunct.
- Both stay in the measurable ranges (gap ∈ [0, 1], balance ∈ [-1, 1]) by
  construction, so :class:`GapReading` never rejects the composite.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.domain.dialectics.core.composition import product, sum_
from babylon.domain.dialectics.core.opposition import BoundOpposition, GapReading, OppositionSpec

pytestmark = [pytest.mark.property, pytest.mark.math]

_gaps = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_balances = st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# ``GapReading.gap`` is an :class:`Intensity`, snapped to the 10^-6 quantization
# grid. The measure snaps its component readings AND the composite, so the bound
# laws are compared against the *snapped* component gaps with one grid step of
# tolerance to absorb the composite's own rounding.
_GRID_TOL = 2e-6


@dataclass(frozen=True)
class _Inputs:
    """Empty input carrier for constant measures."""


def _const(key: str, gap: float, balance: float) -> BoundOpposition[_Inputs]:
    spec = OppositionSpec(key=key, pole_a="A", pole_b="B")
    return BoundOpposition(spec=spec, measure=lambda _inp: GapReading(gap=gap, balance=balance))


def _composite_spec() -> OppositionSpec:
    return OppositionSpec(key="composite", pole_a="A", pole_b="B")


@given(g1=_gaps, b1=_balances, g2=_gaps, b2=_balances)
@settings(max_examples=300, deadline=None)
def test_product_gap_never_exceeds_the_smaller_component(
    g1: float, b1: float, g2: float, b2: float
) -> None:
    d1, d2 = _const("d1", g1, b1), _const("d2", g2, b2)
    composite = product(_composite_spec(), d1, d2)
    reading = composite.measure(_Inputs())
    # Reference the snapped component gaps the combinator actually multiplied.
    smaller = min(d1.measure(_Inputs()).gap, d2.measure(_Inputs()).gap)
    assert reading.gap <= smaller + _GRID_TOL
    assert 0.0 <= reading.gap <= 1.0
    assert -1.0 <= reading.balance <= 1.0


@given(g1=_gaps, b1=_balances, g2=_gaps, b2=_balances)
@settings(max_examples=300, deadline=None)
def test_sum_gap_never_below_the_larger_component(
    g1: float, b1: float, g2: float, b2: float
) -> None:
    d1, d2 = _const("d1", g1, b1), _const("d2", g2, b2)
    composite = sum_(_composite_spec(), d1, d2)
    reading = composite.measure(_Inputs())
    larger = max(d1.measure(_Inputs()).gap, d2.measure(_Inputs()).gap)
    assert reading.gap >= larger - _GRID_TOL
    assert 0.0 <= reading.gap <= 1.0
    assert -1.0 <= reading.balance <= 1.0
