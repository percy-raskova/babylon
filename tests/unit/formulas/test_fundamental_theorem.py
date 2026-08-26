"""Golden-value tests for the Fundamental Theorem of MLM-TW.

Theoretical basis (CLAUDE.md / CONSTITUTION.md): revolution in the Core is
impossible while ``W_c > V_c`` (core wages exceed value produced) — the gap
is Imperial Rent (Phi). ``babylon.formulas.fundamental_theorem`` implements
three pure, dependency-light functions expressing that theorem:

- ``calculate_imperial_rent_gap``: ``Wc - Vc`` (the absolute, dollar-
  denominated gap — matches the reference calibration surface
  ``view_imperial_rent.imperial_rent_millions``, ``data-catalog.yaml``).
- ``calculate_labor_aristocracy_ratio``: ``Wc / Vc``.
- ``is_labor_aristocracy``: ``Wc > Vc`` (strict — equality is NOT
  aristocracy, the theorem's own boundary).

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
  e.g. ``0.5`` and ``0.25``). No rounding occurs anywhere in the
  expression, so bit-for-bit equality is the correct, not merely
  convenient, check.
- ``pytest.approx(expected, abs=1e-9)``: when an input is a decimal
  fraction not exactly representable in binary, such as the pinned
  BLS-derived reference values. ``1e-9`` is ~7 orders of magnitude looser than
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
    calculate_imperial_rent_gap,
    calculate_labor_aristocracy_ratio,
    is_labor_aristocracy,
)

pytestmark = pytest.mark.unit


@pytest.mark.math
class TestCalculateImperialRentGap:
    """Phi = Wc - Vc — the absolute, dollar-denominated Fundamental Theorem gap.

    Matches ``view_imperial_rent.imperial_rent_millions`` exactly
    (``wages_core_millions - value_produced_millions``,
    ``data-catalog.yaml``/the reference sqlite view SQL) — the calibration
    test in ``tests/unit/reference/test_marxian_views.py`` cross-checks this
    function against that view's real BLS-derived numbers.
    """

    def test_docstring_example_imperial_bribe(self) -> None:
        """Wc=120, Vc=100 -> +20.0 (the imperial bribe: paid more than produced)."""
        assert calculate_imperial_rent_gap(120.0, 100.0) == 20.0

    def test_docstring_example_super_exploitation(self) -> None:
        """Wc=60, Vc=100 -> -40.0 (super-exploited: produced more than paid)."""
        assert calculate_imperial_rent_gap(60.0, 100.0) == -40.0

    def test_equality_boundary_is_zero(self) -> None:
        """Wc == Vc -> Phi == 0.0 exactly (no rounding: pure subtraction)."""
        assert calculate_imperial_rent_gap(100.0, 100.0) == 0.0

    def test_zero_value_produced_is_not_an_error(self) -> None:
        """Unlike the ratio formulas, subtraction has no singularity at
        Vc == 0 — no ValueError, just the honest gap Wc - 0 == Wc."""
        assert calculate_imperial_rent_gap(50.0, 0.0) == 50.0

    def test_both_zero_is_zero(self) -> None:
        assert calculate_imperial_rent_gap(0.0, 0.0) == 0.0

    def test_agrees_with_ratio_sign_above_one(self) -> None:
        """ratio > 1 (labor aristocracy) <=> gap > 0 — the two forms of the
        same theorem must never disagree on which side of the line a class
        falls."""
        core_wages, value_produced = 150.0, 100.0
        assert calculate_labor_aristocracy_ratio(core_wages, value_produced) > 1.0
        assert calculate_imperial_rent_gap(core_wages, value_produced) > 0.0

    def test_agrees_with_ratio_sign_below_one(self) -> None:
        core_wages, value_produced = 50.0, 100.0
        assert calculate_labor_aristocracy_ratio(core_wages, value_produced) < 1.0
        assert calculate_imperial_rent_gap(core_wages, value_produced) < 0.0


@pytest.mark.math
class TestGoldenReferenceRows:
    """CI-unconditional companion to
    ``tests/unit/reference/test_marxian_views.py::
    TestFundamentalTheoremCalibration`` (adversarial re-review correction,
    Constitution III.12).

    That class's redundant-verification is entirely gated behind the live
    reference DB (``pytest.mark.requires_reference_db``, skipped on the
    ci-data subset) — so it never actually ran in CI, only on a dev box with
    the full reference DB mounted. These two rows are literal, pinned golden
    values captured from ``view_imperial_rent`` in
    ``data/sqlite/marxist-data-3NF.sqlite`` on 2026-07-21 (NAICS ``'21'``
    mining and NAICS ``'493'`` warehousing, both year 2023) — no DB
    connection, no skip, executed on every CI run regardless of
    reference-DB presence.

    Two DISTINCT rows, deliberately spanning BOTH signs of Φ: mining is
    deep-negative (super-exploited, ratio << 1) and warehousing is positive
    (an actual labor-aristocracy reading, ratio > 1) — the sign/
    operand-order-inversion failure mode a single-row same-arithmetic check
    catches only by accident is here an explicit, intentional two-case
    assertion pinned against real BLS-derived data.
    """

    #: (wages_core_millions, value_produced_millions, imperial_rent_millions,
    #:  labor_aristocracy_ratio) — captured 2026-07-21 from view_imperial_rent.
    _MINING_2023 = (92189.496, 573679.598, -481490.102, 0.16069857865156292)
    _WAREHOUSING_2023 = (114593.056, 56155.266, 58437.78999999999, 2.0406466599232207)

    @pytest.mark.parametrize("golden", [_MINING_2023, _WAREHOUSING_2023])
    def test_reproduces_the_pinned_reference_row(
        self, golden: tuple[float, float, float, float]
    ) -> None:
        wages_core, value_produced, imperial_rent, ratio = golden
        assert calculate_imperial_rent_gap(wages_core, value_produced) == pytest.approx(
            imperial_rent
        )
        assert calculate_labor_aristocracy_ratio(wages_core, value_produced) == pytest.approx(ratio)
        assert is_labor_aristocracy(wages_core, value_produced) is (ratio > 1.0)


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
