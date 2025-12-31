"""Tests for Solidarity Transmission - Proletarian Internationalism.

Sprint 3.4.2: The Counterforce to Imperial Rent Bribery.

When periphery workers are in revolutionary struggle (consciousness >= threshold),
their consciousness transmits through SOLIDARITY edges to core workers, awakening
class consciousness that counters the super-wage bribery.

Key Formula:
    dPsi_target = sigma_edge * (Psi_source - Psi_target)

Where:
- sigma_edge = solidarity_strength (STORED ON EDGE, default 0.0)
- Transmission only if source_consciousness >= activation_threshold (0.3)
- Transmission only if solidarity_strength > 0

This implements the Fascist Bifurcation scenario:
- Periphery revolts BUT solidarity_strength=0 -> NO transmission -> Fascist turn
- Periphery revolts AND solidarity_strength>0 -> Transmission -> Revolutionary turn
"""

import pytest
from tests.constants import TestConstants

from babylon.systems.formulas import calculate_solidarity_transmission

# Alias for readability
TC = TestConstants.Solidarity


@pytest.mark.math
class TestSolidarityTransmissionFormula:
    """Test the solidarity transmission formula.

    dPsi_target = sigma * (Psi_source - Psi_target)

    This formula calculates consciousness change in the target (core worker)
    based on:
    - sigma: solidarity_strength (stored on edge)
    - Psi_source: source consciousness (periphery worker)
    - Psi_target: target consciousness (core worker)
    """

    def test_basic_transmission(self) -> None:
        """Basic consciousness transmission with strong solidarity."""
        # P_w consciousness = 0.9 (revolutionary)
        # C_w consciousness = 0.1 (passive)
        # solidarity_strength = 0.8 (strong built infrastructure)
        delta = calculate_solidarity_transmission(
            source_consciousness=0.9,
            target_consciousness=0.1,
            solidarity_strength=0.8,
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        # delta = 0.8 * (0.9 - 0.1) = 0.64
        assert delta == pytest.approx(0.64, abs=0.001)

    def test_no_transmission_below_activation_threshold(self) -> None:
        """No transmission if source consciousness below activation threshold."""
        # Source consciousness (0.2) < activation_threshold (0.3)
        delta = calculate_solidarity_transmission(
            source_consciousness=0.2,
            target_consciousness=0.1,
            solidarity_strength=0.8,
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        assert delta == 0.0

    def test_no_transmission_at_threshold_boundary(self) -> None:
        """No transmission if source consciousness exactly at threshold (exclusive)."""
        # Edge case: source exactly at threshold should NOT transmit
        # Threshold is exclusive (>) not inclusive (>=)
        delta = calculate_solidarity_transmission(
            source_consciousness=0.3,
            target_consciousness=0.1,
            solidarity_strength=0.8,
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        # At exactly threshold, no transmission (must be strictly above)
        assert delta == 0.0

    def test_transmission_just_above_threshold(self) -> None:
        """Transmission occurs when source is just above threshold."""
        delta = calculate_solidarity_transmission(
            source_consciousness=0.31,
            target_consciousness=0.1,
            solidarity_strength=0.8,
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        # delta = 0.8 * (0.31 - 0.1) = 0.168
        assert delta == pytest.approx(0.168, abs=0.001)

    def test_zero_solidarity_strength_fascist_scenario(self) -> None:
        """Zero solidarity_strength = Fascist Bifurcation.

        Even with periphery in full revolutionary struggle,
        NO consciousness transmits to core if solidarity_strength=0.
        This is the key design decision for the Fascist turn scenario.
        """
        delta = calculate_solidarity_transmission(
            source_consciousness=0.9,  # Full revolutionary struggle
            target_consciousness=0.1,
            solidarity_strength=0.0,  # No built infrastructure
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        assert delta == 0.0

    def test_equal_consciousness_no_transmission(self) -> None:
        """No transmission when source and target have equal consciousness."""
        delta = calculate_solidarity_transmission(
            source_consciousness=0.5,
            target_consciousness=0.5,
            solidarity_strength=0.8,
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        # delta = 0.8 * (0.5 - 0.5) = 0.0
        assert delta == 0.0

    def test_target_higher_consciousness_negative_delta(self) -> None:
        """Negative delta when target has higher consciousness than source.

        This is mathematically possible but represents the unusual case
        where core workers are MORE conscious than periphery workers.
        The formula allows this for mathematical consistency.
        """
        delta = calculate_solidarity_transmission(
            source_consciousness=0.4,  # Above threshold
            target_consciousness=0.8,
            solidarity_strength=0.5,
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        # delta = 0.5 * (0.4 - 0.8) = -0.2
        assert delta == pytest.approx(-0.2, abs=0.001)

    def test_maximum_transmission(self) -> None:
        """Maximum possible transmission with perfect solidarity."""
        delta = calculate_solidarity_transmission(
            source_consciousness=1.0,  # Full revolutionary consciousness
            target_consciousness=0.0,  # Zero consciousness
            solidarity_strength=1.0,  # Perfect solidarity infrastructure
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        # delta = 1.0 * (1.0 - 0.0) = 1.0
        assert delta == pytest.approx(1.0, abs=0.001)


@pytest.mark.math
class TestSolidarityTransmissionBoundaries:
    """Test boundary conditions and edge cases."""

    def test_solidarity_strength_bounds(self) -> None:
        """Solidarity strength should be in [0, 1] range."""
        # Valid solidarity_strength values
        for sigma in [0.0, 0.5, 1.0]:
            delta = calculate_solidarity_transmission(
                source_consciousness=0.9,
                target_consciousness=0.1,
                solidarity_strength=sigma,
                activation_threshold=TC.ACTIVATION_THRESHOLD,
            )
            # Should not raise
            assert isinstance(delta, float)

    def test_consciousness_bounds(self) -> None:
        """Consciousness values should be in [0, 1] range."""
        # Test with boundary consciousness values
        delta = calculate_solidarity_transmission(
            source_consciousness=1.0,
            target_consciousness=0.0,
            solidarity_strength=0.5,
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        # delta = 0.5 * (1.0 - 0.0) = 0.5
        assert delta == pytest.approx(0.5, abs=0.001)

    def test_default_activation_threshold(self) -> None:
        """Default activation threshold is 0.3."""
        # Without explicit threshold, should use 0.3
        delta = calculate_solidarity_transmission(
            source_consciousness=0.9,
            target_consciousness=0.1,
            solidarity_strength=0.8,
        )
        # Should work with default threshold
        assert delta == pytest.approx(0.64, abs=0.001)


@pytest.mark.math
class TestSolidarityTransmissionScenarios:
    """Test real-world scenarios from the sprint specification."""

    def test_scenario_a_revolutionary(self) -> None:
        """Scenario A: Revolutionary (sigma=0.8).

        P_w Psi=0.9, C_w Psi=0.1
        delta = 0.8 * (0.9 - 0.1) = 0.64 -> C_w awakens
        """
        delta = calculate_solidarity_transmission(
            source_consciousness=0.9,
            target_consciousness=0.1,
            solidarity_strength=0.8,
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        assert delta == pytest.approx(0.64, abs=0.001)
        # This delta would push C_w to 0.1 + 0.64 = 0.74 (awakened!)

    def test_scenario_b_fascist(self) -> None:
        """Scenario B: Fascist (sigma=0.0).

        Same nodes, but solidarity_strength=0
        delta = 0.0 * (0.9 - 0.1) = 0.0 -> NO transmission, fascist turn
        """
        delta = calculate_solidarity_transmission(
            source_consciousness=0.9,
            target_consciousness=0.1,
            solidarity_strength=0.0,  # Key difference!
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        assert delta == 0.0
        # C_w stays at 0.1, remains passive consumer

    def test_moderate_solidarity_partial_awakening(self) -> None:
        """Moderate solidarity leads to partial awakening."""
        delta = calculate_solidarity_transmission(
            source_consciousness=0.6,  # Moderate revolutionary consciousness
            target_consciousness=0.2,  # Low consciousness
            solidarity_strength=0.5,  # Moderate infrastructure
            activation_threshold=TC.ACTIVATION_THRESHOLD,
        )
        # delta = 0.5 * (0.6 - 0.2) = 0.2
        assert delta == pytest.approx(0.2, abs=0.001)
