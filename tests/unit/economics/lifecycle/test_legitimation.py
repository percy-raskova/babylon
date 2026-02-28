"""Tests for LegitimationCalculator (Feature 030, US2).

Covers legitimation index computation, crisis classification,
blended legitimation for bifurcation, and pension default scenarios.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import LifecycleDefines
from babylon.economics.lifecycle.legitimation import DefaultLegitimationCalculator
from babylon.economics.lifecycle.types import LegitimationState
from babylon.models.enums import LegitimationClassification


class TestLegitimationCalculator:
    """T012: LegitimationCalculator tests."""

    @pytest.fixture
    def calc(self) -> DefaultLegitimationCalculator:
        return DefaultLegitimationCalculator()

    @pytest.fixture
    def defines(self) -> LifecycleDefines:
        return LifecycleDefines()

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_2_index(
        self,
        calc: DefaultLegitimationCalculator,
        defines: LifecycleDefines,
        scenario_2_legitimation_state: LegitimationState,
    ) -> None:
        """Scenario 2: Legitimation index = 0.6055, classified STABLE."""
        index = calc.compute_index(scenario_2_legitimation_state, defines)
        assert abs(index - 0.6055) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_2_classification(
        self,
        calc: DefaultLegitimationCalculator,
        defines: LifecycleDefines,
        scenario_2_legitimation_state: LegitimationState,
    ) -> None:
        """Scenario 2: Classification is STABLE (index >= 0.5)."""
        index = calc.compute_index(scenario_2_legitimation_state, defines)
        classification = calc.classify_crisis(index, defines)
        assert classification == LegitimationClassification.STABLE

    @pytest.mark.unit
    @pytest.mark.math
    def test_all_low_crisis(
        self,
        calc: DefaultLegitimationCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """All components at 0.2 → CRISIS."""
        state = LegitimationState(
            pension_coverage=0.2,
            ss_replacement_rate=0.2,
            healthcare_security=0.2,
            home_ownership_rate=0.2,
            retirement_confidence=0.2,
        )
        index = calc.compute_index(state, defines)
        assert abs(index - 0.2) < 0.001
        assert calc.classify_crisis(index, defines) == LegitimationClassification.CRISIS

    @pytest.mark.unit
    @pytest.mark.math
    def test_boundary_unstable(
        self,
        calc: DefaultLegitimationCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """Index at 0.3 → UNSTABLE (exactly at crisis threshold)."""
        classification = calc.classify_crisis(0.3, defines)
        assert classification == LegitimationClassification.UNSTABLE

    @pytest.mark.unit
    @pytest.mark.math
    def test_boundary_stable(
        self,
        calc: DefaultLegitimationCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """Index at 0.5 → STABLE (exactly at unstable threshold)."""
        classification = calc.classify_crisis(0.5, defines)
        assert classification == LegitimationClassification.STABLE

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_4_blend(
        self,
        calc: DefaultLegitimationCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """Scenario 4: Blended legitimation for bifurcation feed.

        index=0.25, agitation_inverse=0.4, blend=0.6
        blended = 0.6 * 0.25 + 0.4 * 0.4 = 0.15 + 0.16 = 0.31
        """
        blended = calc.compute_blended_legitimation(
            lifecycle_legitimation=0.25,
            agitation_inverse=0.4,
            blend_weight=defines.legitimation_blend_weight,
        )
        assert abs(blended - 0.31) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_blend_pure_structural(
        self,
        calc: DefaultLegitimationCalculator,
    ) -> None:
        """Blend weight 1.0 → pure structural legitimation."""
        blended = calc.compute_blended_legitimation(
            lifecycle_legitimation=0.7,
            agitation_inverse=0.3,
            blend_weight=1.0,
        )
        assert abs(blended - 0.7) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_blend_pure_agitation(
        self,
        calc: DefaultLegitimationCalculator,
    ) -> None:
        """Blend weight 0.0 → pure agitation inverse."""
        blended = calc.compute_blended_legitimation(
            lifecycle_legitimation=0.7,
            agitation_inverse=0.3,
            blend_weight=0.0,
        )
        assert abs(blended - 0.3) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_pension_default(
        self,
        calc: DefaultLegitimationCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """Pension default: pension coverage → 0 reduces index."""
        original_state = LegitimationState(
            pension_coverage=0.73,
            ss_replacement_rate=0.43,
            healthcare_security=0.60,
            home_ownership_rate=0.66,
            retirement_confidence=0.50,
        )
        defaulted_state = calc.apply_pension_default(original_state)
        original_index = calc.compute_index(original_state, defines)
        defaulted_index = calc.compute_index(defaulted_state, defines)
        assert defaulted_index < original_index
        assert defaulted_state.pension_coverage == 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_weight_ranking_reflected_in_index(
        self,
        calc: DefaultLegitimationCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """Higher-weighted components have more impact on index."""
        # Home ownership (w=0.35) matters more than SS replacement (w=0.05)
        high_home = LegitimationState(
            pension_coverage=0.5,
            ss_replacement_rate=0.0,
            healthcare_security=0.5,
            home_ownership_rate=1.0,
            retirement_confidence=0.5,
        )
        high_ss = LegitimationState(
            pension_coverage=0.5,
            ss_replacement_rate=1.0,
            healthcare_security=0.5,
            home_ownership_rate=0.0,
            retirement_confidence=0.5,
        )
        idx_home = calc.compute_index(high_home, defines)
        idx_ss = calc.compute_index(high_ss, defines)
        assert idx_home > idx_ss
