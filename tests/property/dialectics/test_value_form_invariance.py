"""Numeraire invariance of the value-form defect Φ (Phase D1 / §9.3).

In the spirit of ``tests/property/invariants/test_numeraire_invariance.py``
(spec-060) and ``tests/property/dialectics/test_wealth_asymmetry_invariance.py``:
a dimensionless relative defect cannot depend on the monetary unit. Φ_class
divides by the value produced, so scaling wage and value by any ``k > 0``
leaves it invariant; the FLOW-axis class sort compares wage against τ_eff and
the reproduction floor, so a common rescale preserves both signs and therefore
the class.

This is the structural reason imperial rent is a *rate*, not a dollar count —
"Oakland's labor-aristocrat hour IS Wayne's super-exploited hour" holds
regardless of the currency the wage is quoted in.
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from babylon.domain.dialectics.instances.value_form import (
    class_position_by_phi_hour,
    phi_class,
)

pytestmark = [pytest.mark.property, pytest.mark.math]

_REL_TOL = 1e-9

# Monetary quantities and scale factors spanning six orders of magnitude each.
_money = st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False)
_scales = st.floats(min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False)


@given(w=_money, v=_money, k=_scales)
@settings(max_examples=300, deadline=None)
def test_phi_class_invariant_under_currency_rescale(w: float, v: float, k: float) -> None:
    """Φ_class = (W − V)/V is unchanged when W and V both scale by k > 0."""
    base = phi_class(w_c=w, v_c=v)
    scaled = phi_class(w_c=w * k, v_c=v * k)
    assert scaled == pytest.approx(base, rel=_REL_TOL, abs=1e-12)


@given(wage=_money, tau_eff=_money, v_repro=_money, k=_scales)
@settings(max_examples=300, deadline=None)
def test_class_position_invariant_under_currency_rescale(
    wage: float, tau_eff: float, v_repro: float, k: float
) -> None:
    """The FLOW-axis class is invariant when wage, τ_eff, V_repro all scale by k.

    Boundary examples (wage exactly at τ_eff or at V_repro) are assumed away:
    at an exact threshold, floating-point rounding could legitimately flip the
    sign across scales — that is a measure-zero precision artifact, not a
    failure of the invariance law.
    """
    assume(abs(wage - tau_eff) > 1e-3)
    assume(abs(wage - v_repro) > 1e-3)
    base = class_position_by_phi_hour(
        wage_hourly=wage, tau_effective=tau_eff, v_reproduction=v_repro
    )
    scaled = class_position_by_phi_hour(
        wage_hourly=wage * k, tau_effective=tau_eff * k, v_reproduction=v_repro * k
    )
    assert scaled is base
