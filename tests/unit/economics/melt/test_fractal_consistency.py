"""Tests for fractal consistency validation (Feature 038, US6).

Feature: 038-unified-class-system
TDD Phase: RED then GREEN

Tests cover:
- T045: Fractal zoom validation — same ClassPosition at sub-scale,
  Wayne > Oakland proletariat+lumpen share, valid classifications at
  both resolutions.
"""

from __future__ import annotations

import pytest

from babylon.economics.melt.types import ClassPosition, PrecarityStatus
from tests.constants import ClassSystemDefaults

CS = ClassSystemDefaults()


# Detroit tri-county wealth distribution data (mock county-level distributions)
# Represents the fraction of population at each class position.
# Wayne County: more extraction, higher proletariat/lumpen share
# Oakland County: more wealth accumulation, higher LA/PB share
_WAYNE_DISTRIBUTION: dict[ClassPosition, float] = {
    ClassPosition.BOURGEOISIE: 0.005,
    ClassPosition.PETIT_BOURGEOISIE: 0.04,
    ClassPosition.LABOR_ARISTOCRACY: 0.30,
    ClassPosition.PROLETARIAT: 0.42,
    ClassPosition.LUMPENPROLETARIAT: 0.235,
}

_OAKLAND_DISTRIBUTION: dict[ClassPosition, float] = {
    ClassPosition.BOURGEOISIE: 0.02,
    ClassPosition.PETIT_BOURGEOISIE: 0.12,
    ClassPosition.LABOR_ARISTOCRACY: 0.45,
    ClassPosition.PROLETARIAT: 0.30,
    ClassPosition.LUMPENPROLETARIAT: 0.11,
}

_MACOMB_DISTRIBUTION: dict[ClassPosition, float] = {
    ClassPosition.BOURGEOISIE: 0.01,
    ClassPosition.PETIT_BOURGEOISIE: 0.08,
    ClassPosition.LABOR_ARISTOCRACY: 0.42,
    ClassPosition.PROLETARIAT: 0.35,
    ClassPosition.LUMPENPROLETARIAT: 0.14,
}


@pytest.mark.unit
class TestFractalConsistency:
    """T045: Fractal consistency validation."""

    def test_same_class_position_enum_at_sub_scale(self) -> None:
        """Same ClassPosition enum applies at county sub-scale."""
        from babylon.economics.melt.unified_classifier import (
            DefaultUnifiedClassifier,
        )

        classifier = DefaultUnifiedClassifier()
        # Classify individual households at sub-county level
        # (same code path as metro level)
        result = classifier.classify_with_filtration(
            wealth_percentile=75.0,
            precarity=PrecarityStatus.STABLE,
        )
        assert isinstance(result, ClassPosition)
        assert result == ClassPosition.LABOR_ARISTOCRACY

        # Fractal consistency: sub-county classification uses same enum
        sub_county_result = classifier.classify_with_filtration(
            wealth_percentile=25.0,
            precarity=PrecarityStatus.STABLE,
        )
        assert isinstance(sub_county_result, ClassPosition)
        assert sub_county_result == ClassPosition.PROLETARIAT

    def test_wayne_higher_proletariat_lumpen_share(self) -> None:
        """Wayne County has higher PROLETARIAT+LUMPEN share than Oakland.

        This validates the internal colony thesis: extraction is concentrated
        where the colonial relationship is most direct (urban core).
        """
        from babylon.economics.melt.unified_classifier import (
            validate_fractal_consistency,
        )

        result = validate_fractal_consistency(
            county_distributions={
                CS.WAYNE_FIPS: _WAYNE_DISTRIBUTION,
                CS.OAKLAND_FIPS: _OAKLAND_DISTRIBUTION,
            }
        )
        assert result.is_consistent
        wayne_lower = result.proletariat_lumpen_share[CS.WAYNE_FIPS]
        oakland_lower = result.proletariat_lumpen_share[CS.OAKLAND_FIPS]
        assert wayne_lower > oakland_lower

    def test_four_node_pattern_at_each_county(self) -> None:
        """Each county has all five class positions represented."""
        from babylon.economics.melt.unified_classifier import (
            validate_fractal_consistency,
        )

        result = validate_fractal_consistency(
            county_distributions={
                CS.WAYNE_FIPS: _WAYNE_DISTRIBUTION,
                CS.OAKLAND_FIPS: _OAKLAND_DISTRIBUTION,
                CS.MACOMB_FIPS: _MACOMB_DISTRIBUTION,
            }
        )
        assert result.is_consistent
        # Each county must have all five class positions
        for fips in [CS.WAYNE_FIPS, CS.OAKLAND_FIPS, CS.MACOMB_FIPS]:
            assert len(result.class_positions_present[fips]) == 5

    def test_distributions_sum_to_one(self) -> None:
        """All county distributions must sum to approximately 1.0."""
        from babylon.economics.melt.unified_classifier import (
            validate_fractal_consistency,
        )

        result = validate_fractal_consistency(
            county_distributions={
                CS.WAYNE_FIPS: _WAYNE_DISTRIBUTION,
                CS.OAKLAND_FIPS: _OAKLAND_DISTRIBUTION,
            }
        )
        assert result.is_consistent

    def test_metro_aggregate_preserves_pattern(self) -> None:
        """Metro-level aggregate maintains same class hierarchy as sub-counties."""
        from babylon.economics.melt.unified_classifier import (
            validate_fractal_consistency,
        )

        result = validate_fractal_consistency(
            county_distributions={
                CS.WAYNE_FIPS: _WAYNE_DISTRIBUTION,
                CS.OAKLAND_FIPS: _OAKLAND_DISTRIBUTION,
                CS.MACOMB_FIPS: _MACOMB_DISTRIBUTION,
            }
        )
        assert result.is_consistent
        # Metro aggregate should have all five class positions
        assert len(result.metro_distribution) == 5
        # Metro PROLETARIAT+LUMPEN should be between Wayne and Oakland
        metro_lower = (
            result.metro_distribution[ClassPosition.PROLETARIAT]
            + result.metro_distribution[ClassPosition.LUMPENPROLETARIAT]
        )
        wayne_lower = result.proletariat_lumpen_share[CS.WAYNE_FIPS]
        oakland_lower = result.proletariat_lumpen_share[CS.OAKLAND_FIPS]
        assert oakland_lower < metro_lower < wayne_lower

    def test_fractal_result_is_frozen(self) -> None:
        """FractalConsistencyResult is immutable."""
        from pydantic import ValidationError

        from babylon.economics.melt.unified_classifier import (
            validate_fractal_consistency,
        )

        result = validate_fractal_consistency(
            county_distributions={
                CS.WAYNE_FIPS: _WAYNE_DISTRIBUTION,
            }
        )
        with pytest.raises(ValidationError):
            result.is_consistent = False  # type: ignore[misc]
