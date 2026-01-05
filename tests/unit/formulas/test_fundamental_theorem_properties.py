"""Property-based tests for Fundamental Theorem formulas.

Uses Hypothesis to verify formula properties hold across the entire input space,
catching edge cases that example-based tests might miss.

Properties Verified:
- Imperial Rent: Non-negativity, boundedness, monotonicity
- Labor Aristocracy Ratio: Positivity for positive inputs
- Consciousness Drift: Bounded output, correct sign under material conditions
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from tests.constants import TestConstants

from babylon.systems.formulas import (
    calculate_consciousness_drift,
    calculate_imperial_rent,
    calculate_labor_aristocracy_ratio,
    is_labor_aristocracy,
)

TC = TestConstants

# =============================================================================
# IMPERIAL RENT PROPERTIES
# =============================================================================


@pytest.mark.math
@pytest.mark.property
class TestImperialRentProperties:
    """Property-based tests for imperial rent formula.

    Formula: Phi = alpha * Wp * (1 - Psi_p)

    Properties:
    1. Rent is always non-negative
    2. Rent is zero when consciousness = 1 (full revolution)
    3. Rent is maximal when consciousness = 0 (full submission)
    4. Rent decreases monotonically with consciousness
    """

    @given(
        alpha=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        periphery_wages=st.floats(
            min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        periphery_consciousness=st.floats(
            min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_rent_is_always_non_negative(
        self, alpha: float, periphery_wages: float, periphery_consciousness: float
    ) -> None:
        """Imperial rent is always >= 0 for valid inputs."""
        rent = calculate_imperial_rent(
            alpha=alpha,
            periphery_wages=periphery_wages,
            periphery_consciousness=periphery_consciousness,
        )
        assert rent >= 0.0

    @given(
        alpha=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        periphery_wages=st.floats(
            min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    def test_rent_is_zero_when_full_consciousness(
        self, alpha: float, periphery_wages: float
    ) -> None:
        """When Psi_p = 1.0 (full revolution), rent must be zero."""
        rent = calculate_imperial_rent(
            alpha=alpha,
            periphery_wages=periphery_wages,
            periphery_consciousness=1.0,  # Full consciousness
        )
        assert rent == pytest.approx(0.0, abs=1e-9)

    @given(
        alpha=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        periphery_wages=st.floats(
            min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    def test_rent_equals_alpha_times_wages_when_no_consciousness(
        self, alpha: float, periphery_wages: float
    ) -> None:
        """When Psi_p = 0.0 (no consciousness), rent = alpha * Wp."""
        rent = calculate_imperial_rent(
            alpha=alpha,
            periphery_wages=periphery_wages,
            periphery_consciousness=0.0,  # No consciousness
        )
        expected = alpha * periphery_wages
        assert rent == pytest.approx(expected, rel=1e-9)

    @given(
        alpha=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False),
        periphery_wages=st.floats(
            min_value=0.1, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        consciousness_low=st.floats(
            min_value=0.0, max_value=0.4, allow_nan=False, allow_infinity=False
        ),
        consciousness_high=st.floats(
            min_value=0.6, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_rent_decreases_with_consciousness(
        self,
        alpha: float,
        periphery_wages: float,
        consciousness_low: float,
        consciousness_high: float,
    ) -> None:
        """Imperial rent monotonically decreases with consciousness."""
        rent_low = calculate_imperial_rent(
            alpha=alpha,
            periphery_wages=periphery_wages,
            periphery_consciousness=consciousness_low,
        )
        rent_high = calculate_imperial_rent(
            alpha=alpha,
            periphery_wages=periphery_wages,
            periphery_consciousness=consciousness_high,
        )
        assert rent_low >= rent_high


# =============================================================================
# LABOR ARISTOCRACY RATIO PROPERTIES
# =============================================================================


@pytest.mark.math
@pytest.mark.property
class TestLaborAristocracyRatioProperties:
    """Property-based tests for labor aristocracy ratio formula.

    Formula: ratio = Wc / Vc

    Properties:
    1. Ratio is always positive for positive value_produced
    2. Ratio correctly determines labor aristocracy status (Wc/Vc > 1)
    3. Ratio scales linearly with wages
    """

    @given(
        core_wages=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        value_produced=st.floats(
            min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    def test_ratio_is_non_negative(self, core_wages: float, value_produced: float) -> None:
        """Labor aristocracy ratio is always >= 0 for valid inputs."""
        ratio = calculate_labor_aristocracy_ratio(
            core_wages=core_wages,
            value_produced=value_produced,
        )
        assert ratio >= 0.0

    @given(
        value_produced=st.floats(
            min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    def test_ratio_equals_wage_over_value(self, value_produced: float) -> None:
        """Ratio correctly equals wages / value_produced."""
        core_wages = value_produced * 1.5  # Arbitrary multiplier
        ratio = calculate_labor_aristocracy_ratio(
            core_wages=core_wages,
            value_produced=value_produced,
        )
        assert ratio == pytest.approx(1.5, rel=1e-9)

    @given(
        core_wages=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        value_produced=st.floats(
            min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    def test_is_aristocracy_matches_ratio_greater_than_one(
        self, core_wages: float, value_produced: float
    ) -> None:
        """is_labor_aristocracy returns True iff ratio > 1."""
        ratio = calculate_labor_aristocracy_ratio(
            core_wages=core_wages,
            value_produced=value_produced,
        )
        is_aristocracy = is_labor_aristocracy(
            core_wages=core_wages,
            value_produced=value_produced,
        )
        if ratio > 1.0:
            assert is_aristocracy is True
        else:
            assert is_aristocracy is False

    @given(
        wages1=st.floats(min_value=0.0, max_value=1e5, allow_nan=False, allow_infinity=False),
        wages2=st.floats(min_value=0.0, max_value=1e5, allow_nan=False, allow_infinity=False),
        value_produced=st.floats(
            min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    def test_higher_wages_higher_ratio(
        self, wages1: float, wages2: float, value_produced: float
    ) -> None:
        """Higher wages produce higher ratio."""
        assume(wages1 != wages2)
        # Skip when wages are too close to distinguish after division
        # Uses COMPARISON_EPSILON from TestConstants (derived from precision defines)
        assume(abs(wages1 - wages2) > TC.Quantization.COMPARISON_EPSILON)
        ratio1 = calculate_labor_aristocracy_ratio(
            core_wages=wages1,
            value_produced=value_produced,
        )
        ratio2 = calculate_labor_aristocracy_ratio(
            core_wages=wages2,
            value_produced=value_produced,
        )
        if wages1 > wages2:
            assert ratio1 > ratio2
        else:
            assert ratio1 < ratio2


# =============================================================================
# CONSCIOUSNESS DRIFT PROPERTIES
# =============================================================================


@pytest.mark.math
@pytest.mark.property
class TestConsciousnessDriftProperties:
    """Property-based tests for consciousness drift formula.

    Formula: dPsi/dt = k(1 - Wc/Vc) - lambda*Psi + bifurcation

    Properties:
    1. Drift direction depends on Wc/Vc ratio
    2. Decay term always reduces consciousness
    3. Bifurcation only triggers on negative wage_change
    """

    @given(
        value_produced=st.floats(
            min_value=10.0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        current_consciousness=st.floats(
            min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        sensitivity_k=st.floats(
            min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_drift_negative_when_receiving_rent(
        self, value_produced: float, current_consciousness: float, sensitivity_k: float
    ) -> None:
        """When Wc/Vc > 1.2 (receiving rent), base drift tends negative."""
        core_wages = value_produced * 1.5  # Wc/Vc = 1.5 > 1
        decay_lambda = 0.0  # Isolate wage ratio effect

        drift = calculate_consciousness_drift(
            core_wages=core_wages,
            value_produced=value_produced,
            current_consciousness=current_consciousness,
            sensitivity_k=sensitivity_k,
            decay_lambda=decay_lambda,
        )

        # k(1 - 1.5) = k * (-0.5) < 0
        assert drift < 0.0

    @given(
        value_produced=st.floats(
            min_value=10.0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        current_consciousness=st.floats(
            min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        sensitivity_k=st.floats(
            min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_drift_positive_when_no_rent(
        self, value_produced: float, current_consciousness: float, sensitivity_k: float
    ) -> None:
        """When Wc/Vc < 0.8 (not receiving rent), base drift tends positive."""
        core_wages = value_produced * 0.5  # Wc/Vc = 0.5 < 1
        decay_lambda = 0.0  # Isolate wage ratio effect

        drift = calculate_consciousness_drift(
            core_wages=core_wages,
            value_produced=value_produced,
            current_consciousness=current_consciousness,
            sensitivity_k=sensitivity_k,
            decay_lambda=decay_lambda,
        )

        # k(1 - 0.5) = k * 0.5 > 0
        assert drift > 0.0

    @given(
        value_produced=st.floats(
            min_value=10.0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        current_consciousness=st.floats(
            min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        decay_lambda=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    def test_decay_reduces_consciousness(
        self, value_produced: float, current_consciousness: float, decay_lambda: float
    ) -> None:
        """Decay term (-lambda * Psi) always reduces drift when Psi > 0."""
        # At Wc/Vc = 1, base drift = 0, only decay remains
        drift = calculate_consciousness_drift(
            core_wages=value_produced,  # Wc/Vc = 1.0
            value_produced=value_produced,
            current_consciousness=current_consciousness,
            sensitivity_k=1.0,
            decay_lambda=decay_lambda,
        )

        # Expected: 0 - lambda * consciousness = negative
        assert drift < 0.0
        expected = -decay_lambda * current_consciousness
        assert drift == pytest.approx(expected, rel=1e-9)

    @given(
        value_produced=st.floats(
            min_value=10.0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        wage_change_positive=st.floats(
            min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        solidarity_pressure=st.floats(
            min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_no_bifurcation_when_wages_rising(
        self,
        value_produced: float,
        wage_change_positive: float,
        solidarity_pressure: float,
    ) -> None:
        """Bifurcation does not trigger when wage_change >= 0."""
        drift_no_change = calculate_consciousness_drift(
            core_wages=value_produced,
            value_produced=value_produced,
            current_consciousness=0.0,
            sensitivity_k=1.0,
            decay_lambda=0.0,
            solidarity_pressure=solidarity_pressure,
            wage_change=0.0,
        )

        drift_with_positive = calculate_consciousness_drift(
            core_wages=value_produced,
            value_produced=value_produced,
            current_consciousness=0.0,
            sensitivity_k=1.0,
            decay_lambda=0.0,
            solidarity_pressure=solidarity_pressure,
            wage_change=wage_change_positive,
        )

        # No bifurcation: both should be equal (base drift only)
        assert drift_no_change == pytest.approx(drift_with_positive, rel=1e-9)

    @given(
        value_produced=st.floats(
            min_value=10.0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        wage_drop=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
        solidarity_pressure=st.floats(
            min_value=0.1, max_value=2.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=200)  # More examples for bifurcation
    def test_bifurcation_with_solidarity_increases_drift(
        self, value_produced: float, wage_drop: float, solidarity_pressure: float
    ) -> None:
        """When wages fall AND solidarity exists, drift increases (revolution)."""
        drift_no_crisis = calculate_consciousness_drift(
            core_wages=value_produced,
            value_produced=value_produced,
            current_consciousness=0.0,
            sensitivity_k=1.0,
            decay_lambda=0.0,
            solidarity_pressure=solidarity_pressure,
            wage_change=0.0,  # No crisis
        )

        drift_with_crisis = calculate_consciousness_drift(
            core_wages=value_produced,
            value_produced=value_produced,
            current_consciousness=0.0,
            sensitivity_k=1.0,
            decay_lambda=0.0,
            solidarity_pressure=solidarity_pressure,
            wage_change=-wage_drop,  # Crisis!
        )

        # With solidarity, crisis increases drift (toward revolution)
        assert drift_with_crisis > drift_no_crisis

    @given(
        value_produced=st.floats(
            min_value=10.0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        wage_drop=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200)  # More examples for bifurcation
    def test_bifurcation_without_solidarity_decreases_drift(
        self, value_produced: float, wage_drop: float
    ) -> None:
        """When wages fall AND NO solidarity, drift decreases (fascism)."""
        drift_no_crisis = calculate_consciousness_drift(
            core_wages=value_produced,
            value_produced=value_produced,
            current_consciousness=0.0,
            sensitivity_k=1.0,
            decay_lambda=0.0,
            solidarity_pressure=0.0,  # No solidarity
            wage_change=0.0,  # No crisis
        )

        drift_with_crisis = calculate_consciousness_drift(
            core_wages=value_produced,
            value_produced=value_produced,
            current_consciousness=0.0,
            sensitivity_k=1.0,
            decay_lambda=0.0,
            solidarity_pressure=0.0,  # No solidarity
            wage_change=-wage_drop,  # Crisis!
        )

        # Without solidarity, crisis decreases drift (toward fascism)
        assert drift_with_crisis < drift_no_crisis
