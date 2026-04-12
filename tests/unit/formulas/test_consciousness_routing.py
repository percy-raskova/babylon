"""Tests for consciousness routing formulas (Spec 043, Phase 2).

TDD Red Phase: These tests verify the new value-tensor-to-consciousness
routing pipeline that replaces the legacy ideological_routing.py.

The pipeline works in stages:
1. compute_agitation_delta() - Value tensor crisis → agitation increment
2. compute_exploitation_visibility() - How visible exploitation is
3. compute_reification_buffer() - Commodity fetishism dampening
4. route_agitation_to_ternary() - Agitation → r/l/f ternary shift
5. normalize_to_simplex() - Ensure r + l + f = 1
"""

from __future__ import annotations

import pytest

from babylon.config.defines import ConsciousnessDefines
from babylon.formulas.consciousness_routing import (
    compute_agitation_delta,
    compute_exploitation_visibility,
    compute_reification_buffer,
    normalize_to_simplex,
    route_agitation_to_ternary,
)

# =============================================================================
# Test Constants (test-only scenarios, not domain defaults)
# =============================================================================

# Baseline exploitation rate (s/v) for a typical county
BASELINE_EXPLOITATION_RATE = 1.0  # Workers produce 2x what they're paid
ELEVATED_EXPLOITATION_RATE = 1.5  # Crisis conditions
CRISIS_EXPLOITATION_RATE = 2.0  # Severe extraction

# Imperial rent flows
CORE_RENT = 0.3  # Positive = core (receiving rent)
PERIPHERAL_RENT = -0.2  # Negative = periphery
NO_RENT = 0.0

# Visibility
FULL_VISIBILITY = 1.0  # Fully monetized care work
HALF_VISIBILITY = 0.5
SHADOW_LABOR = 0.1  # Almost all care is unwaged


@pytest.mark.unit
@pytest.mark.math
class TestComputeAgitationDelta:
    """compute_agitation_delta: Δ(value tensor) → agitation increment."""

    def test_no_change_no_agitation(self) -> None:
        """Zero change in all tensor quantities → zero agitation."""
        result = compute_agitation_delta(
            exploitation_rate_delta=0.0,
            imperial_rent_delta=0.0,
            visibility_delta=0.0,
        )
        assert result == pytest.approx(0.0)

    def test_exploitation_increase_generates_agitation(self) -> None:
        """Rising s/v → agitation (workers feel exploitation more)."""
        defines = ConsciousnessDefines()
        delta = compute_agitation_delta(
            exploitation_rate_delta=0.5,  # s/v increased by 0.5
            imperial_rent_delta=0.0,
            visibility_delta=0.0,
        )
        expected = 0.5 * defines.exploitation_sensitivity
        assert delta == pytest.approx(expected)

    def test_rent_decline_generates_agitation(self) -> None:
        """Declining imperial rent → agitation in core (losing bribe)."""
        defines = ConsciousnessDefines()
        delta = compute_agitation_delta(
            exploitation_rate_delta=0.0,
            imperial_rent_delta=-0.2,  # Rent declining
            visibility_delta=0.0,
        )
        # Only decline (negative) generates agitation
        expected = abs(-0.2) * defines.rent_decline_sensitivity
        assert delta == pytest.approx(expected)

    def test_rent_increase_no_agitation(self) -> None:
        """Increasing imperial rent → no agitation (material improvement)."""
        delta = compute_agitation_delta(
            exploitation_rate_delta=0.0,
            imperial_rent_delta=0.3,  # Rent increasing
            visibility_delta=0.0,
        )
        assert delta == pytest.approx(0.0)

    def test_visibility_increase_generates_agitation(self) -> None:
        """g₃₃ increasing → care work becomes visible → agitation."""
        defines = ConsciousnessDefines()
        delta = compute_agitation_delta(
            exploitation_rate_delta=0.0,
            imperial_rent_delta=0.0,
            visibility_delta=0.3,  # Care work becoming visible
        )
        expected = 0.3 * defines.reproduction_visibility_coefficient
        assert delta == pytest.approx(expected)

    def test_multiple_sources_combine(self) -> None:
        """Multiple crisis sources combine additively."""
        defines = ConsciousnessDefines()
        delta = compute_agitation_delta(
            exploitation_rate_delta=0.5,
            imperial_rent_delta=-0.2,
            visibility_delta=0.1,
        )
        expected = (
            0.5 * defines.exploitation_sensitivity
            + 0.2 * defines.rent_decline_sensitivity
            + 0.1 * defines.reproduction_visibility_coefficient
        )
        assert delta == pytest.approx(expected)

    def test_result_always_nonnegative(self) -> None:
        """Agitation delta is always >= 0 (no negative agitation)."""
        delta = compute_agitation_delta(
            exploitation_rate_delta=-0.5,  # Exploitation decreasing
            imperial_rent_delta=0.3,  # Rent increasing
            visibility_delta=-0.2,  # Visibility decreasing
        )
        assert delta >= 0.0

    def test_custom_defines(self) -> None:
        """Custom defines override default sensitivities."""
        custom = ConsciousnessDefines(exploitation_sensitivity=0.5)
        delta = compute_agitation_delta(
            exploitation_rate_delta=1.0,
            imperial_rent_delta=0.0,
            visibility_delta=0.0,
            defines=custom,
        )
        assert delta == pytest.approx(0.5)


@pytest.mark.unit
@pytest.mark.math
class TestComputeExploitationVisibility:
    """compute_exploitation_visibility: tensor state → visibility [0, 1]."""

    def test_zero_exploitation_zero_rent(self) -> None:
        """No exploitation, no rent → visibility at floor."""
        vis = compute_exploitation_visibility(
            exploitation_rate=0.0,
            imperial_rent=0.0,
        )
        assert vis == pytest.approx(0.0)

    def test_high_exploitation_low_rent(self) -> None:
        """High exploitation with low rent → high visibility."""
        vis = compute_exploitation_visibility(
            exploitation_rate=2.0,
            imperial_rent=0.05,
        )
        assert vis > 0.5  # Exploitation clearly visible

    def test_rent_obscures_exploitation(self) -> None:
        """Imperial rent dampens visibility (commodity fetishism)."""
        vis_no_rent = compute_exploitation_visibility(
            exploitation_rate=2.0,
            imperial_rent=0.0,
        )
        vis_high_rent = compute_exploitation_visibility(
            exploitation_rate=2.0,
            imperial_rent=0.5,
        )
        assert vis_no_rent > vis_high_rent  # Rent obscures

    def test_visibility_clamped_to_unit(self) -> None:
        """Output clamped to [0, 1]."""
        vis = compute_exploitation_visibility(
            exploitation_rate=100.0,
            imperial_rent=0.0,
        )
        assert 0.0 <= vis <= 1.0


@pytest.mark.unit
@pytest.mark.math
class TestComputeReificationBuffer:
    """compute_reification_buffer: imperial rent → reification [0, 1]."""

    def test_no_rent_low_reification(self) -> None:
        """No imperial rent → low commodity fetishism."""
        reif = compute_reification_buffer(
            imperial_rent=0.0,
            total_v=100.0,
        )
        assert reif < 0.1  # Low reification without rent's obscuring

    def test_high_rent_high_reification(self) -> None:
        """High imperial rent relative to v → commodity fetishism is strong."""
        reif = compute_reification_buffer(
            imperial_rent=50.0,
            total_v=100.0,
        )
        assert reif > 0.3  # Rent obscures class relations

    def test_reification_clamped(self) -> None:
        """Output clamped to [0, 1]."""
        reif = compute_reification_buffer(
            imperial_rent=1000.0,
            total_v=1.0,
        )
        assert 0.0 <= reif <= 1.0

    def test_zero_v_safe(self) -> None:
        """Division by zero is safe when total_v = 0."""
        reif = compute_reification_buffer(
            imperial_rent=0.5,
            total_v=0.0,
        )
        assert 0.0 <= reif <= 1.0


@pytest.mark.unit
@pytest.mark.math
class TestRouteAgitationToTernary:
    """route_agitation_to_ternary: agitation → (Δr, Δl, Δf) ternary shift."""

    def test_no_agitation_no_shift(self) -> None:
        """Zero agitation → zero ternary shift."""
        dr, dl, df = route_agitation_to_ternary(
            agitation=0.0,
            solidarity_factor=0.5,
            education_pressure=0.0,
        )
        assert dr == pytest.approx(0.0)
        assert dl == pytest.approx(0.0)
        assert df == pytest.approx(0.0)

    def test_high_solidarity_routes_to_revolutionary(self) -> None:
        """High solidarity → agitation routes toward r."""
        dr, dl, df = route_agitation_to_ternary(
            agitation=1.0,
            solidarity_factor=0.9,
            education_pressure=0.0,
        )
        assert dr > 0.0  # Positive shift toward revolutionary
        assert df < dr  # Much less goes to fascist

    def test_low_solidarity_routes_to_fascist(self) -> None:
        """Low solidarity → agitation routes toward f."""
        dr, dl, df = route_agitation_to_ternary(
            agitation=1.0,
            solidarity_factor=0.1,
            education_pressure=0.0,
        )
        assert df > dr  # More goes to fascist than revolutionary

    def test_education_pressure_boosts_revolutionary(self) -> None:
        """Education pressure biases agitation toward r."""
        dr_no_edu, _, _ = route_agitation_to_ternary(
            agitation=1.0,
            solidarity_factor=0.5,
            education_pressure=0.0,
        )
        dr_edu, _, _ = route_agitation_to_ternary(
            agitation=1.0,
            solidarity_factor=0.5,
            education_pressure=0.5,
        )
        assert dr_edu > dr_no_edu  # Education boosts revolutionary routing

    def test_deltas_sum_to_consumption(self) -> None:
        """Sum of |Δ| values approximates consumed agitation fraction."""
        dr, dl, df = route_agitation_to_ternary(
            agitation=1.0,
            solidarity_factor=0.5,
            education_pressure=0.0,
        )
        # The magnitude should reflect consumption rate
        total_shift = abs(dr) + abs(dl) + abs(df)
        assert total_shift > 0.0  # Non-trivial routing happened


@pytest.mark.unit
@pytest.mark.math
class TestNormalizeToSimplex:
    """normalize_to_simplex: ensure r + l + f = 1."""

    def test_already_normalized(self) -> None:
        """Values already summing to 1 are unchanged."""
        r, lib, f = normalize_to_simplex(0.3, 0.5, 0.2)
        assert r + lib + f == pytest.approx(1.0)
        assert r == pytest.approx(0.3)

    def test_over_one_scales_down(self) -> None:
        """Values summing > 1 are scaled down proportionally."""
        r, lib, f = normalize_to_simplex(0.6, 0.6, 0.6)
        assert r + lib + f == pytest.approx(1.0)
        # All equal inputs → all equal outputs
        assert r == pytest.approx(lib)
        assert lib == pytest.approx(f)

    def test_under_one_assigns_remainder_to_liberal(self) -> None:
        """Values summing < 1 → remainder goes to liberal (hegemonic default)."""
        r, lib, f = normalize_to_simplex(0.1, 0.2, 0.1)
        assert r + lib + f == pytest.approx(1.0)
        assert lib > 0.2  # Liberal absorbed the remainder

    def test_negative_values_clamped(self) -> None:
        """Negative inputs are clamped to zero."""
        r, lib, f = normalize_to_simplex(-0.1, 0.5, 0.3)
        assert r >= 0.0
        assert r + lib + f == pytest.approx(1.0)

    def test_all_zeros_pure_liberal(self) -> None:
        """All zeros → pure liberal default."""
        r, lib, f = normalize_to_simplex(0.0, 0.0, 0.0)
        assert lib == pytest.approx(1.0)
        assert r == pytest.approx(0.0)
        assert f == pytest.approx(0.0)
