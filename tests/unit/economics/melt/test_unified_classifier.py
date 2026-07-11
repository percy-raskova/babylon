"""Tests for the UnifiedClassifier (Feature 038, US1 + US2).

Feature: 038-unified-class-system
TDD Phase: RED (tests written before implementation)

Tests cover:
- T006: DualCriteriaResult model validation
- T007: classify_with_filtration no-filtration path (6 acceptance scenarios)
- T008: classify_dual_criteria agreement/disagreement/event emission
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.economics.melt.types import ClassPosition, PrecarityStatus
from tests.constants import ClassSystemDefaults

CS = ClassSystemDefaults()


class TestDualCriteriaResult:
    """T006: DualCriteriaResult model validation."""

    @pytest.mark.unit
    def test_agreement_case(self) -> None:
        """When agrees=True, magnitude must be 0.0 and classes must match."""
        from babylon.domain.economics.melt.unified_classifier import DualCriteriaResult

        result = DualCriteriaResult(
            wealth_class=ClassPosition.PROLETARIAT,
            accounting_class=ClassPosition.PROLETARIAT,
            agrees=True,
            magnitude=CS.MAGNITUDE_ZERO,
        )
        assert result.agrees is True
        assert result.magnitude == 0.0
        assert result.wealth_class == result.accounting_class

    @pytest.mark.unit
    def test_disagreement_case(self) -> None:
        """When agrees=False, classes must differ and magnitude > 0."""
        from babylon.domain.economics.melt.unified_classifier import DualCriteriaResult

        result = DualCriteriaResult(
            wealth_class=ClassPosition.LABOR_ARISTOCRACY,
            accounting_class=ClassPosition.PROLETARIAT,
            agrees=False,
            magnitude=15.0,
        )
        assert result.agrees is False
        assert result.magnitude > 0.0
        assert result.wealth_class != result.accounting_class

    @pytest.mark.unit
    def test_frozen_immutability(self) -> None:
        """DualCriteriaResult must be frozen (immutable)."""
        from babylon.domain.economics.melt.unified_classifier import DualCriteriaResult

        result = DualCriteriaResult(
            wealth_class=ClassPosition.PROLETARIAT,
            accounting_class=ClassPosition.PROLETARIAT,
            agrees=True,
            magnitude=0.0,
        )
        with pytest.raises(ValidationError):
            result.agrees = False  # type: ignore[misc]

    @pytest.mark.unit
    def test_agrees_true_but_classes_differ_raises(self) -> None:
        """Validator rejects agrees=True when classes differ."""
        from babylon.domain.economics.melt.unified_classifier import DualCriteriaResult

        with pytest.raises(ValidationError):
            DualCriteriaResult(
                wealth_class=ClassPosition.LABOR_ARISTOCRACY,
                accounting_class=ClassPosition.PROLETARIAT,
                agrees=True,
                magnitude=0.0,
            )

    @pytest.mark.unit
    def test_agrees_false_but_classes_match_raises(self) -> None:
        """Validator rejects agrees=False when classes match."""
        from babylon.domain.economics.melt.unified_classifier import DualCriteriaResult

        with pytest.raises(ValidationError):
            DualCriteriaResult(
                wealth_class=ClassPosition.PROLETARIAT,
                accounting_class=ClassPosition.PROLETARIAT,
                agrees=False,
                magnitude=10.0,
            )

    @pytest.mark.unit
    def test_agrees_true_nonzero_magnitude_raises(self) -> None:
        """Validator rejects nonzero magnitude when agrees=True."""
        from babylon.domain.economics.melt.unified_classifier import DualCriteriaResult

        with pytest.raises(ValidationError):
            DualCriteriaResult(
                wealth_class=ClassPosition.PROLETARIAT,
                accounting_class=ClassPosition.PROLETARIAT,
                agrees=True,
                magnitude=5.0,
            )

    @pytest.mark.unit
    def test_negative_magnitude_raises(self) -> None:
        """Magnitude must be >= 0.0."""
        from babylon.domain.economics.melt.unified_classifier import DualCriteriaResult

        with pytest.raises(ValidationError):
            DualCriteriaResult(
                wealth_class=ClassPosition.LABOR_ARISTOCRACY,
                accounting_class=ClassPosition.PROLETARIAT,
                agrees=False,
                magnitude=-1.0,
            )


class TestClassifyWithFiltrationNoFiltration:
    """T007: classify_with_filtration no-filtration path (backward compat).

    All 6 acceptance scenarios from spec.md US1.
    No community memberships -> identical to DefaultClassPositionClassifier.
    """

    @pytest.mark.unit
    def test_75th_percentile_returns_la(self) -> None:
        """Scenario 1: 75th percentile -> LABOR_ARISTOCRACY."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier

        classifier = DefaultUnifiedClassifier()
        result = classifier.classify_with_filtration(CS.WEALTH_LA, PrecarityStatus.STABLE)
        assert result == ClassPosition.LABOR_ARISTOCRACY

    @pytest.mark.unit
    def test_25th_stable_returns_proletariat(self) -> None:
        """Scenario 2: 25th percentile + STABLE -> PROLETARIAT."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier

        classifier = DefaultUnifiedClassifier()
        result = classifier.classify_with_filtration(CS.WEALTH_PROLETARIAT, PrecarityStatus.STABLE)
        assert result == ClassPosition.PROLETARIAT

    @pytest.mark.unit
    def test_10th_excluded_returns_lumpen(self) -> None:
        """Scenario 3: 10th percentile + EXCLUDED -> LUMPENPROLETARIAT."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier

        classifier = DefaultUnifiedClassifier()
        result = classifier.classify_with_filtration(CS.WEALTH_LUMPEN, PrecarityStatus.EXCLUDED)
        assert result == ClassPosition.LUMPENPROLETARIAT

    @pytest.mark.unit
    def test_95th_returns_petit_bourgeoisie(self) -> None:
        """Scenario 4: 95th percentile -> PETIT_BOURGEOISIE."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier

        classifier = DefaultUnifiedClassifier()
        result = classifier.classify_with_filtration(CS.WEALTH_PB, PrecarityStatus.STABLE)
        assert result == ClassPosition.PETIT_BOURGEOISIE

    @pytest.mark.unit
    def test_99_5th_returns_bourgeoisie(self) -> None:
        """Scenario 5: 99.5th percentile -> BOURGEOISIE."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier

        classifier = DefaultUnifiedClassifier()
        result = classifier.classify_with_filtration(CS.WEALTH_BOURGEOISIE, PrecarityStatus.STABLE)
        assert result == ClassPosition.BOURGEOISIE

    @pytest.mark.unit
    def test_55th_excluded_returns_la(self) -> None:
        """Scenario 6: 55th percentile + EXCLUDED -> LA (wealth overrides)."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier

        classifier = DefaultUnifiedClassifier()
        result = classifier.classify_with_filtration(
            CS.WEALTH_LA_EXCLUDED, PrecarityStatus.EXCLUDED
        )
        assert result == ClassPosition.LABOR_ARISTOCRACY

    @pytest.mark.unit
    def test_backward_compatibility_with_base_classifier(self) -> None:
        """No-filtration path matches DefaultClassPositionClassifier exactly."""
        from babylon.domain.economics.melt.class_position import (
            DefaultClassPositionClassifier,
        )
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier

        base = DefaultClassPositionClassifier()
        unified = DefaultUnifiedClassifier()

        test_cases = [
            (CS.WEALTH_LA, PrecarityStatus.STABLE),
            (CS.WEALTH_PROLETARIAT, PrecarityStatus.STABLE),
            (CS.WEALTH_LUMPEN, PrecarityStatus.EXCLUDED),
            (CS.WEALTH_PB, PrecarityStatus.STABLE),
            (CS.WEALTH_BOURGEOISIE, PrecarityStatus.STABLE),
            (CS.WEALTH_LA_EXCLUDED, PrecarityStatus.EXCLUDED),
        ]
        for wealth, precarity in test_cases:
            expected = base.classify_by_wealth_and_precarity(wealth, precarity)
            actual = unified.classify_with_filtration(wealth, precarity)
            assert actual == expected, f"Mismatch at wealth={wealth}, precarity={precarity}"


class TestClassifyDualCriteria:
    """T008: classify_dual_criteria tests."""

    @pytest.mark.unit
    def test_agreement_both_criteria_match(self) -> None:
        """When accounting and wealth agree, result.agrees=True."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier

        classifier = DefaultUnifiedClassifier()
        # V_produced ~ V_reproduction (ratio ~1.0) -> PROLETARIAT
        # wealth=25th -> PROLETARIAT with STABLE precarity
        # Both criteria agree on PROLETARIAT
        result = classifier.classify_dual_criteria(
            wealth_percentile=CS.WEALTH_PROLETARIAT,
            precarity=PrecarityStatus.STABLE,
            v_produced=CS.V_REPRODUCTION,
            v_reproduction=CS.V_REPRODUCTION,
        )
        assert result.agrees is True
        assert result.magnitude == 0.0

    @pytest.mark.unit
    def test_disagreement_different_criteria(self) -> None:
        """When accounting and wealth disagree, result.agrees=False."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier

        classifier = DefaultUnifiedClassifier()
        # Low V_produced suggests proletarian, but high wealth says LA
        result = classifier.classify_dual_criteria(
            wealth_percentile=CS.WEALTH_LA,
            precarity=PrecarityStatus.STABLE,
            v_produced=CS.V_PRODUCED_LOW,
            v_reproduction=CS.V_REPRODUCTION,
        )
        assert result.agrees is False
        assert result.magnitude > 0.0
        assert result.wealth_class == ClassPosition.LABOR_ARISTOCRACY

    @pytest.mark.unit
    def test_wealth_class_is_primary(self) -> None:
        """Wealth class is always the primary classification result."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier

        classifier = DefaultUnifiedClassifier()
        result = classifier.classify_dual_criteria(
            wealth_percentile=CS.WEALTH_LA,
            precarity=PrecarityStatus.STABLE,
            v_produced=CS.V_PRODUCED_HIGH,
            v_reproduction=CS.V_REPRODUCTION,
        )
        # Wealth class should match direct classification
        assert result.wealth_class == ClassPosition.LABOR_ARISTOCRACY


class TestClassifyWithFiltrationPath:
    """T017: classify_with_filtration WITH filtration memberships."""

    @staticmethod
    def _make_membership(community_type: object, agent_id: str = "test-agent") -> object:
        from babylon.models.entities.community import CommunityMembership

        return CommunityMembership(agent_id=agent_id, community_type=community_type)

    @staticmethod
    def _make_community_state(
        community_type: object,
        reproduction_cost_modifier: float = 1.0,
    ) -> object:
        from babylon.models.entities.community import CommunityState

        return CommunityState(
            community_type=community_type,
            reproduction_cost_modifier=reproduction_cost_modifier,
        )

    @pytest.mark.unit
    def test_first_nations_shifts_to_proletariat(self) -> None:
        """60th percentile + FIRST_NATIONS -> PROLETARIAT (60*0.5=30th)."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier
        from babylon.models.enums import CommunityType

        classifier = DefaultUnifiedClassifier()
        membership = self._make_membership(CommunityType.FIRST_NATIONS)
        result = classifier.classify_with_filtration(
            CS.WEALTH_FIRST_NATIONS,
            PrecarityStatus.STABLE,
            memberships=[membership],
        )
        assert result == ClassPosition.PROLETARIAT

    @pytest.mark.unit
    def test_incarcerated_shifts_to_lumpen(self) -> None:
        """45th + INCARCERATED -> LUMPEN (precarity EXCLUDED, below 50th)."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier
        from babylon.models.enums import CommunityType

        classifier = DefaultUnifiedClassifier()
        membership = self._make_membership(CommunityType.INCARCERATED)
        result = classifier.classify_with_filtration(
            CS.WEALTH_INCARCERATED,
            PrecarityStatus.STABLE,
            memberships=[membership],
        )
        assert result == ClassPosition.LUMPENPROLETARIAT

    @pytest.mark.unit
    def test_undocumented_shifts_classification(self) -> None:
        """55th + UNDOCUMENTED -> shifted downward (55*0.6=33rd)."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier
        from babylon.models.enums import CommunityType

        classifier = DefaultUnifiedClassifier()
        membership = self._make_membership(CommunityType.UNDOCUMENTED)
        result = classifier.classify_with_filtration(
            CS.WEALTH_UNDOCUMENTED,
            PrecarityStatus.STABLE,
            memberships=[membership],
        )
        # 55 * 0.6 = 33rd percentile + PRECARIOUS floor -> PROLETARIAT
        assert result == ClassPosition.PROLETARIAT

    @pytest.mark.unit
    def test_disabled_shifts_classification(self) -> None:
        """65th + DISABLED (modifier=1.3) -> shifted (65/1.3=50th)."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier
        from babylon.models.enums import CommunityType

        classifier = DefaultUnifiedClassifier()
        membership = self._make_membership(CommunityType.DISABLED)
        state = self._make_community_state(
            CommunityType.DISABLED,
            reproduction_cost_modifier=CS.REPRODUCTION_COST_MODIFIER,
        )
        result = classifier.classify_with_filtration(
            CS.WEALTH_DISABLED,
            PrecarityStatus.STABLE,
            memberships=[membership],
            community_states={CommunityType.DISABLED.value: state},
        )
        # 65 / 1.3 = 50.0 -> exactly at LA threshold -> LA
        assert result == ClassPosition.LABOR_ARISTOCRACY

    @pytest.mark.unit
    def test_no_memberships_unchanged(self) -> None:
        """No memberships -> same as base classifier."""
        from babylon.domain.economics.melt.unified_classifier import DefaultUnifiedClassifier

        classifier = DefaultUnifiedClassifier()
        result = classifier.classify_with_filtration(
            CS.WEALTH_LA,
            PrecarityStatus.STABLE,
            memberships=None,
        )
        assert result == ClassPosition.LABOR_ARISTOCRACY
