"""Unit tests for community formulas (Feature 022).

TDD RED phase tests for solidarity_potential, threat_score,
infrastructure_decay, and solidarity_amplification formulas.
"""

from __future__ import annotations

import pytest

from babylon.formulas.community import (
    calculate_infrastructure_decay,
    calculate_solidarity_amplification,
    calculate_solidarity_potential,
    calculate_threat_score,
)


@pytest.mark.unit
@pytest.mark.math
class TestSolidarityPotential:
    """Tests for calculate_solidarity_potential()."""

    def test_overlap_bonus_increases_potential(self) -> None:
        """More shared communities → higher solidarity potential."""
        zero_overlap = calculate_solidarity_potential(0.3, 0, 0.0, 0.0)
        two_overlap = calculate_solidarity_potential(0.3, 2, 0.0, 0.0)
        assert two_overlap > zero_overlap

    def test_zero_overlap_returns_base(self) -> None:
        """With no shared communities, potential equals base solidarity."""
        result = calculate_solidarity_potential(0.3, 0, 0.0, 0.0)
        assert result == pytest.approx(0.3)

    def test_rent_differential_reduces_potential(self) -> None:
        """Rent gap penalizes solidarity potential even with shared communities."""
        no_gap = calculate_solidarity_potential(0.3, 2, 0.5, 0.5)
        large_gap = calculate_solidarity_potential(0.3, 2, 1.0, 0.0)
        assert large_gap < no_gap

    def test_rent_penalty_can_make_potential_negative(self) -> None:
        """Extreme rent differential can push potential below zero."""
        result = calculate_solidarity_potential(0.1, 0, 10.0, 0.0)
        assert result < 0.0

    def test_doctest_examples(self) -> None:
        """Verify docstring examples."""
        assert calculate_solidarity_potential(0.3, 2, 0.0, 0.0) == pytest.approx(0.5)
        assert calculate_solidarity_potential(0.3, 0, 0.0, 0.0) == pytest.approx(0.3)

    def test_custom_coefficients(self) -> None:
        """Custom overlap_bonus and rent_penalty override defaults."""
        result = calculate_solidarity_potential(
            0.0, 3, 0.0, 0.0, overlap_bonus=0.2, rent_penalty=0.0
        )
        assert result == pytest.approx(0.6)


@pytest.mark.unit
@pytest.mark.math
class TestThreatScore:
    """Tests for calculate_threat_score()."""

    def test_single_membership(self) -> None:
        """Single membership: heat * vis * role * legal."""
        result = calculate_threat_score([(0.4, 0.8, 1.0, 1.0)])
        assert result == pytest.approx(0.32)

    def test_cumulative_across_memberships(self) -> None:
        """Threat score sums across all memberships."""
        single = calculate_threat_score([(0.4, 0.8, 1.0, 1.0)])
        double = calculate_threat_score(
            [
                (0.4, 0.8, 1.0, 1.0),
                (0.3, 0.5, 0.7, 2.0),
            ]
        )
        assert double > single

    def test_empty_memberships_returns_zero(self) -> None:
        """No memberships → zero threat score."""
        assert calculate_threat_score([]) == 0.0

    def test_high_legal_multiplier_dominates(self) -> None:
        """CRIMINALIZED (3.0) membership dominates threat score."""
        low_legal = calculate_threat_score([(0.5, 1.0, 1.0, 0.1)])
        high_legal = calculate_threat_score([(0.5, 1.0, 1.0, 3.0)])
        assert high_legal == pytest.approx(high_legal)
        assert high_legal / low_legal == pytest.approx(30.0)


@pytest.mark.unit
@pytest.mark.math
class TestInfrastructureDecay:
    """Tests for calculate_infrastructure_decay()."""

    def test_decays_without_organizers(self) -> None:
        """Infrastructure decays when no CORE_ORGANIZERs present."""
        new_value = calculate_infrastructure_decay(0.5, 0.04, 0)
        assert new_value < 0.5
        assert new_value == pytest.approx(0.48)

    def test_organizers_slow_decay(self) -> None:
        """CORE_ORGANIZERs counteract decay via maintenance."""
        no_org = calculate_infrastructure_decay(0.5, 0.04, 0)
        with_org = calculate_infrastructure_decay(0.5, 0.04, 2)
        assert with_org > no_org

    def test_clamped_to_zero_one(self) -> None:
        """Result always in [0, 1] regardless of inputs."""
        assert calculate_infrastructure_decay(0.0, 1.0, 0) >= 0.0
        assert calculate_infrastructure_decay(1.0, 0.0, 100) <= 1.0

    def test_zero_decay_alpha_preserves(self) -> None:
        """Zero decay rate preserves current value."""
        assert calculate_infrastructure_decay(0.7, 0.0, 0) == pytest.approx(0.7)


@pytest.mark.unit
@pytest.mark.math
class TestSolidarityAmplification:
    """Tests for calculate_solidarity_amplification()."""

    def test_no_shared_returns_base(self) -> None:
        """No shared communities → return base strength unchanged."""
        result = calculate_solidarity_amplification(0.5, [])
        assert result == pytest.approx(0.5)

    def test_shared_communities_amplify(self) -> None:
        """Shared communities increase solidarity strength."""
        base = calculate_solidarity_amplification(0.5, [])
        amplified = calculate_solidarity_amplification(0.5, [(0.8, 0.6, 0.7, 0.4)])
        assert amplified > base

    def test_amplification_scales_with_infrastructure(self) -> None:
        """Higher infrastructure → more amplification."""
        low_infra = calculate_solidarity_amplification(0.5, [(0.2, 0.6, 0.7, 0.4)])
        high_infra = calculate_solidarity_amplification(0.5, [(0.9, 0.6, 0.7, 0.4)])
        assert high_infra > low_infra

    def test_doctest_example(self) -> None:
        """Verify docstring example."""
        result = calculate_solidarity_amplification(0.5, [(0.8, 0.6, 0.7, 0.4)])
        assert result == pytest.approx(0.567, abs=0.001)
