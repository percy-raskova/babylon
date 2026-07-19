"""Golden-value tests for the Fundamental Theorem of MLM-TW.

Theoretical basis (CLAUDE.md / CONSTITUTION.md): revolution in the Core is
impossible while ``W_c > V_c`` (core wages exceed value produced) — the gap
is Imperial Rent (Phi). ``babylon.formulas.fundamental_theorem`` implements
three pure, dependency-light functions expressing that theorem:

- ``calculate_labor_aristocracy_ratio``: ``Wc / Vc``.
- ``is_labor_aristocracy``: ``Wc > Vc`` (strict — equality is NOT
  aristocracy, the theorem's own boundary).
- ``calculate_consciousness_drift``: ``dPsi/dt = k(1 - Wc/Vc) - lambda*Psi``,
  with a Fascist-Bifurcation term added when wages are actively falling
  (``wage_change < 0``): SOLIDARITY pressure present pushes the drift toward
  its positive ("revolutionary" per the function's own docstring) pole;
  its absence subtracts, pushing toward the negative ("reactionary") pole.

Behavioral-contract framing (Task 32 / "the rewrite test"): these are pure
arithmetic identities (``+``, ``-``, ``*``, ``/`` only — no transcendentals),
so a byte-faithful reimplementation in any language reproduces them exactly
under IEEE-754 double precision. Golden values below are HAND-DERIVED from
the documented formulas (not copied from a first run of the code), so a
sign or operator-precedence regression is caught, not rubber-stamped.

Tolerance policy
-----------------
Two tiers, chosen for the reason stated at each assertion:

- ``==`` (exact): when every input and every intermediate term is exactly
  representable in binary floating point (integers, halves, quarters —
  e.g. ``0.5``, ``0.25``, ``2.25`` — see ``test_loss_aversion_coefficient_is_pinned``
  for why ``2.25`` qualifies). No rounding occurs anywhere in the
  expression, so bit-for-bit equality is the correct, not merely
  convenient, check.
- ``pytest.approx(expected, abs=1e-9)``: when an input is a decimal
  fraction not exactly representable in binary (``0.1``, ``0.3``, ``0.4``,
  ...), e.g. wage ratios like ``50/100`` are exact but coefficients like
  ``0.2``/``0.1`` are not. ``1e-9`` is ~7 orders of magnitude looser than
  IEEE-754 double epsilon (~2.22e-16) accumulated over the handful of
  operations these formulas perform, so it cannot mask a real regression,
  while it comfortably absorbs re-association/operand-order differences
  between this test's hand-derivation and the source's expression order.
  This is deliberately tighter than the codebase's common ``abs=0.001``
  "business" tolerance (see ``test_trpf.py``) because these are single-shot
  arithmetic identities, not integrated/iterative dynamics.
"""

from __future__ import annotations

import pytest

from babylon.formulas.fundamental_theorem import (
    LOSS_AVERSION_COEFFICIENT,
    calculate_consciousness_drift,
    calculate_labor_aristocracy_ratio,
    is_labor_aristocracy,
)

pytestmark = pytest.mark.unit


@pytest.mark.math
class TestLossAversionCoefficient:
    """Pins the Kahneman-Tversky prospect-theory coefficient this module
    imports from ``GameDefines.behavioral.loss_aversion_lambda`` at import
    time.

    This is deliberately a HARDCODED literal (``2.25``), not a re-read of
    ``GameDefines`` — the whole point is to catch a defines.yaml change to
    this coefficient as a loud, deliberate re-golden decision rather than a
    silent drift absorbed by every downstream bifurcation test.
    """

    def test_coefficient_is_the_documented_prospect_theory_value(self) -> None:
        """Kahneman & Tversky (1979): losses loom ~2.25x larger than gains."""
        assert LOSS_AVERSION_COEFFICIENT == 2.25


@pytest.mark.math
class TestCalculateLaborAristocracyRatio:
    """Wc / Vc — the Fundamental Theorem's core ratio."""

    def test_docstring_example_subsidized_worker(self) -> None:
        """Wc=120, Vc=100 -> 1.2 (the module's own doctest example)."""
        assert calculate_labor_aristocracy_ratio(120.0, 100.0) == 1.2

    def test_docstring_example_exploited_worker(self) -> None:
        """Wc=80, Vc=100 -> 0.8."""
        assert calculate_labor_aristocracy_ratio(80.0, 100.0) == 0.8

    def test_equality_boundary_ratio_is_exactly_one(self) -> None:
        """Wc == Vc (the theorem's own boundary) -> ratio == 1.0 exactly."""
        assert calculate_labor_aristocracy_ratio(100.0, 100.0) == 1.0

    def test_zero_core_wages_is_an_honest_zero_not_an_error(self) -> None:
        """Wc=0 with Vc>0 is a real, valid ratio of 0.0 (fully exploited,
        no wage at all) — not a fabricated or error state."""
        assert calculate_labor_aristocracy_ratio(0.0, 50.0) == 0.0

    def test_negative_core_wages_yields_negative_ratio(self) -> None:
        """The formula performs no domain clamping on core_wages — a
        negative input (outside the engine's normal range but not excluded
        by this pure function) propagates deterministically."""
        assert calculate_labor_aristocracy_ratio(-20.0, 50.0) == -0.4

    def test_zero_value_produced_raises_value_error(self) -> None:
        """Vc == 0 is the exact boundary of the '<= 0' guard."""
        with pytest.raises(ValueError, match="value_produced must be > 0"):
            calculate_labor_aristocracy_ratio(100.0, 0.0)

    def test_negative_value_produced_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="value_produced must be > 0"):
            calculate_labor_aristocracy_ratio(100.0, -10.0)


@pytest.mark.math
class TestIsLaborAristocracy:
    """Wc > Vc (strict) — the theorem's own boundary is NOT aristocracy."""

    def test_docstring_example_true(self) -> None:
        assert is_labor_aristocracy(120.0, 100.0) is True

    def test_docstring_example_false(self) -> None:
        assert is_labor_aristocracy(80.0, 100.0) is False

    def test_equality_boundary_is_not_labor_aristocracy(self) -> None:
        """Wc == Vc: no imperial subsidy exists at exact equality — the
        theorem is a STRICT inequality (W_c > V_c), pinned here so a future
        '>=' regression is caught rather than silently loosening the
        theorem's own boundary."""
        assert is_labor_aristocracy(100.0, 100.0) is False

    def test_just_above_equality_is_labor_aristocracy(self) -> None:
        """The smallest representable step above equality already flips
        the verdict — confirms the boundary is not fuzzed by an epsilon."""
        assert is_labor_aristocracy(100.0 + 1e-9, 100.0) is True

    def test_zero_value_produced_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="value_produced must be > 0"):
            is_labor_aristocracy(100.0, 0.0)

    def test_negative_value_produced_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="value_produced must be > 0"):
            is_labor_aristocracy(100.0, -10.0)


@pytest.mark.math
class TestConsciousnessDriftNoBifurcation:
    """dPsi/dt = k(1 - Wc/Vc) - lambda*Psi, wage_change >= 0 (no Fascist
    Bifurcation term — the function's own ``>= 0`` guard, not ``> 0``)."""

    def test_equality_boundary_zero_drift(self) -> None:
        """Wc == Vc (ratio 1.0), current_consciousness=0.0, decay_lambda=0.0:
        every term is exactly zero. k*(1-1) - 0*0 = 0.0 exactly — the
        Fundamental Theorem's equality line with nothing else acting is a
        clean, exact fixed point."""
        drift = calculate_consciousness_drift(
            core_wages=100.0,
            value_produced=100.0,
            current_consciousness=0.0,
            sensitivity_k=1.0,
            decay_lambda=0.0,
        )
        assert drift == 0.0

    def test_exploited_worker_positive_drift(self) -> None:
        """Wc=50, Vc=100 (ratio 0.5), Psi=0.5, k=2.0, lambda=0.2:
        base_drift = 2.0*(1-0.5) - 0.2*0.5 = 1.0 - 0.1 = 0.9. Uses
        pytest.approx (not ==): 0.2 is not exactly representable in binary
        floating point, so the subtraction can differ from 0.9 by a few
        ULPs even though the mathematical result is exact."""
        drift = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=100.0,
            current_consciousness=0.5,
            sensitivity_k=2.0,
            decay_lambda=0.2,
        )
        assert drift == pytest.approx(0.9, abs=1e-9)

    def test_wage_change_exactly_zero_takes_no_bifurcation_branch(self) -> None:
        """wage_change=0.0 hits the '>= 0' guard exactly — same result as
        omitting wage_change entirely (its default)."""
        with_default = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=100.0,
            current_consciousness=0.5,
            sensitivity_k=2.0,
            decay_lambda=0.2,
        )
        with_explicit_zero = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=100.0,
            current_consciousness=0.5,
            sensitivity_k=2.0,
            decay_lambda=0.2,
            wage_change=0.0,
        )
        assert with_explicit_zero == with_default == pytest.approx(0.9, abs=1e-9)

    def test_negative_zero_wage_change_also_takes_no_bifurcation_branch(self) -> None:
        """IEEE-754 ``-0.0 >= 0`` is True, so this pins the guard is a
        genuine '>= 0' comparison (not '> 0' misread) even at signed zero."""
        drift = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=100.0,
            current_consciousness=0.5,
            sensitivity_k=2.0,
            decay_lambda=0.2,
            wage_change=-0.0,
        )
        assert drift == pytest.approx(0.9, abs=1e-9)

    def test_positive_wage_change_also_takes_no_bifurcation_branch(self) -> None:
        """Rising wages (wage_change > 0): still no bifurcation term —
        Fascist Bifurcation is specifically a falling-wage phenomenon."""
        drift = calculate_consciousness_drift(
            core_wages=50.0,
            value_produced=100.0,
            current_consciousness=0.5,
            sensitivity_k=2.0,
            decay_lambda=0.2,
            wage_change=5.0,
            solidarity_pressure=0.8,  # irrelevant when wage_change >= 0
        )
        assert drift == pytest.approx(0.9, abs=1e-9)

    def test_zero_value_produced_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="value_produced must be > 0"):
            calculate_consciousness_drift(
                core_wages=100.0,
                value_produced=0.0,
                current_consciousness=0.5,
                sensitivity_k=1.0,
                decay_lambda=0.1,
            )

    def test_negative_value_produced_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="value_produced must be > 0"):
            calculate_consciousness_drift(
                core_wages=100.0,
                value_produced=-5.0,
                current_consciousness=0.5,
                sensitivity_k=1.0,
                decay_lambda=0.1,
            )


@pytest.mark.math
class TestConsciousnessDriftBifurcation:
    """wage_change < 0: Fascist Bifurcation adds/subtracts
    ``|wage_change| * LOSS_AVERSION_COEFFICIENT`` (clamped solidarity
    weight) depending on SOLIDARITY pressure.

    Shared base for every case in this class: Wc=100, Vc=100 (ratio 1.0,
    so the pre-bifurcation ``k*(1-ratio)`` term is exactly 0.0), Psi=0.4,
    k=1.0, lambda=0.1 -> base_drift = 0.0 - 0.1*0.4 = -0.04 mathematically.
    0.1 is not exactly representable in binary floating point, so every
    assertion in this class uses ``pytest.approx`` rather than ``==``.
    """

    _BASE_KWARGS = {
        "core_wages": 100.0,
        "value_produced": 100.0,
        "current_consciousness": 0.4,
        "sensitivity_k": 1.0,
        "decay_lambda": 0.1,
    }
    _BASE_DRIFT = -0.04  # 0.0 - 0.1 * 0.4

    def test_solidarity_present_pushes_drift_positive(self) -> None:
        """wage_change=-2.0, solidarity_pressure=0.6 (> 0, unclamped):
        agitation = 2.0 * 2.25 = 4.5; drift = -0.04 + 4.5*0.6 = -0.04 + 2.7
        = 2.66 — solidarity pushes the drift toward its positive
        ("revolutionary" per the function's own docstring) pole."""
        drift = calculate_consciousness_drift(
            **self._BASE_KWARGS, wage_change=-2.0, solidarity_pressure=0.6
        )
        assert drift == pytest.approx(2.66, abs=1e-9)

    def test_solidarity_pressure_exactly_zero_takes_subtractive_branch(self) -> None:
        """solidarity_pressure=0.0 fails the 'solidarity_pressure > 0'
        check (strict, not >=) and falls to the SUBTRACTIVE branch: drift
        = -0.04 - 4.5 = -4.54 — pins the boundary is a genuine '> 0', not
        '>= 0' (which would have taken the additive branch at exactly 0)."""
        drift = calculate_consciousness_drift(
            **self._BASE_KWARGS, wage_change=-2.0, solidarity_pressure=0.0
        )
        assert drift == pytest.approx(-4.54, abs=1e-9)

    def test_no_solidarity_pushes_drift_negative(self) -> None:
        """Default solidarity_pressure=0.0 (omitted): same subtractive
        branch as the explicit-zero case above — -4.54."""
        drift = calculate_consciousness_drift(**self._BASE_KWARGS, wage_change=-2.0)
        assert drift == pytest.approx(-4.54, abs=1e-9)

    def test_solidarity_pressure_above_one_is_clamped(self) -> None:
        """solidarity_pressure=5.0 clamps via min(1.0, 5.0) == 1.0: drift
        = -0.04 + 4.5*1.0 = 4.46 — identical to solidarity_pressure=1.0
        exactly (next test), proving the clamp actually engages above 1.0
        rather than merely scaling further."""
        drift = calculate_consciousness_drift(
            **self._BASE_KWARGS, wage_change=-2.0, solidarity_pressure=5.0
        )
        assert drift == pytest.approx(4.46, abs=1e-9)

    def test_solidarity_pressure_at_exactly_one_matches_the_clamped_case(self) -> None:
        """solidarity_pressure=1.0 (the clamp's own boundary): min(1.0, 1.0)
        == 1.0, identical result to solidarity_pressure=5.0 above — proves
        the clamp ceiling is exactly 1.0, not some other value."""
        drift = calculate_consciousness_drift(
            **self._BASE_KWARGS, wage_change=-2.0, solidarity_pressure=1.0
        )
        assert drift == pytest.approx(4.46, abs=1e-9)

    def test_tiny_negative_wage_change_still_bifurcates(self) -> None:
        """wage_change=-1e-9 (the smallest negative step this test uses)
        still takes the bifurcation branch (any negative value, not just
        'large' ones) — agitation = 1e-9 * 2.25 = 2.25e-9, negligible but
        present: drift = -0.04 - 2.25e-9 (no solidarity)."""
        drift = calculate_consciousness_drift(**self._BASE_KWARGS, wage_change=-1e-9)
        assert drift == pytest.approx(-0.04 - 2.25e-9, abs=1e-12)
        assert drift != -0.04  # bifurcation genuinely applied, however small
