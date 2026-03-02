"""Tests for community filtration predicates (Feature 038, US2).

Feature: 038-unified-class-system
TDD Phase: RED then GREEN

Tests cover:
- T014: FiltrationResult model validation
- T015: Per-predicate tests (FIRST_NATIONS, INCARCERATED, UNDOCUMENTED, DISABLED)
- T016: Multi-membership composition (most-restrictive-wins, order-independence)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from tests.constants import ClassSystemDefaults

from babylon.economics.melt.types import PrecarityStatus
from babylon.models.enums import CommunityType

CS = ClassSystemDefaults()


def _make_membership(community_type: CommunityType, agent_id: str = "test-agent") -> object:
    """Create a CommunityMembership for testing."""
    from babylon.models.entities.community import CommunityMembership

    return CommunityMembership(agent_id=agent_id, community_type=community_type)


def _make_community_state(
    community_type: CommunityType,
    reproduction_cost_modifier: float = 1.0,
) -> object:
    """Create a CommunityState for testing."""
    from babylon.models.entities.community import CommunityState

    return CommunityState(
        community_type=community_type,
        reproduction_cost_modifier=reproduction_cost_modifier,
    )


class TestFiltrationResult:
    """T014: FiltrationResult model validation."""

    @pytest.mark.unit
    def test_identity_filtration(self) -> None:
        """No filtration: effective equals original."""
        from babylon.economics.melt.filtration import FiltrationResult

        result = FiltrationResult(
            original_wealth_percentile=60.0,
            effective_wealth_percentile=60.0,
            original_precarity=PrecarityStatus.STABLE,
            effective_precarity=PrecarityStatus.STABLE,
        )
        assert result.effective_wealth_percentile == result.original_wealth_percentile
        assert result.effective_precarity == result.original_precarity

    @pytest.mark.unit
    def test_effective_wealth_less_than_original(self) -> None:
        """Filtration reduces effective wealth."""
        from babylon.economics.melt.filtration import FiltrationResult

        result = FiltrationResult(
            original_wealth_percentile=60.0,
            effective_wealth_percentile=30.0,
            original_precarity=PrecarityStatus.STABLE,
            effective_precarity=PrecarityStatus.STABLE,
            applied_predicates=["FIRST_NATIONS_trust_land"],
        )
        assert result.effective_wealth_percentile < result.original_wealth_percentile

    @pytest.mark.unit
    def test_effective_wealth_exceeds_original_raises(self) -> None:
        """Filtration cannot increase effective wealth."""
        from babylon.economics.melt.filtration import FiltrationResult

        with pytest.raises(ValidationError):
            FiltrationResult(
                original_wealth_percentile=60.0,
                effective_wealth_percentile=70.0,
                original_precarity=PrecarityStatus.STABLE,
                effective_precarity=PrecarityStatus.STABLE,
            )

    @pytest.mark.unit
    def test_precarity_severity_cannot_decrease(self) -> None:
        """Filtration cannot reduce precarity severity (make less precarious)."""
        from babylon.economics.melt.filtration import FiltrationResult

        # EXCLUDED -> STABLE is a decrease in severity -> should fail
        with pytest.raises(ValidationError):
            FiltrationResult(
                original_wealth_percentile=60.0,
                effective_wealth_percentile=60.0,
                original_precarity=PrecarityStatus.EXCLUDED,
                effective_precarity=PrecarityStatus.STABLE,
            )

    @pytest.mark.unit
    def test_frozen_immutability(self) -> None:
        """FiltrationResult must be frozen."""
        from babylon.economics.melt.filtration import FiltrationResult

        result = FiltrationResult(
            original_wealth_percentile=60.0,
            effective_wealth_percentile=60.0,
            original_precarity=PrecarityStatus.STABLE,
            effective_precarity=PrecarityStatus.STABLE,
        )
        with pytest.raises(ValidationError):
            result.effective_wealth_percentile = 30.0  # type: ignore[misc]


class TestFiltrationPredicates:
    """T015: Per-predicate filtration tests."""

    @pytest.mark.unit
    def test_first_nations_trust_land_discount(self) -> None:
        """FIRST_NATIONS applies trust_land_discount to wealth."""
        from babylon.economics.melt.filtration import apply_filtration

        membership = _make_membership(CommunityType.FIRST_NATIONS)
        result = apply_filtration(
            wealth_percentile=CS.WEALTH_FIRST_NATIONS,
            precarity=PrecarityStatus.STABLE,
            memberships=[membership],
            community_states={},
        )
        expected_wealth = CS.WEALTH_FIRST_NATIONS * CS.TRUST_LAND_DISCOUNT
        assert result.effective_wealth_percentile == pytest.approx(expected_wealth)
        assert "FIRST_NATIONS_trust_land" in result.applied_predicates

    @pytest.mark.unit
    def test_incarcerated_overrides_to_excluded(self) -> None:
        """INCARCERATED overrides precarity to EXCLUDED."""
        from babylon.economics.melt.filtration import apply_filtration

        membership = _make_membership(CommunityType.INCARCERATED)
        result = apply_filtration(
            wealth_percentile=CS.WEALTH_INCARCERATED,
            precarity=PrecarityStatus.STABLE,
            memberships=[membership],
            community_states={},
        )
        assert result.effective_precarity == PrecarityStatus.EXCLUDED
        assert "INCARCERATED_exclusion" in result.applied_predicates

    @pytest.mark.unit
    def test_undocumented_discount_and_precarity_floor(self) -> None:
        """UNDOCUMENTED applies doc_exclusion_factor and precarity floor."""
        from babylon.economics.melt.filtration import apply_filtration

        membership = _make_membership(CommunityType.UNDOCUMENTED)
        result = apply_filtration(
            wealth_percentile=CS.WEALTH_UNDOCUMENTED,
            precarity=PrecarityStatus.STABLE,
            memberships=[membership],
            community_states={},
        )
        expected_wealth = CS.WEALTH_UNDOCUMENTED * CS.DOCUMENTATION_EXCLUSION_FACTOR
        assert result.effective_wealth_percentile == pytest.approx(expected_wealth)
        # Precarity floor is at least PRECARIOUS
        assert result.effective_precarity in (
            PrecarityStatus.PRECARIOUS,
            PrecarityStatus.MARGINALLY_ATTACHED,
            PrecarityStatus.EXCLUDED,
        )
        assert "UNDOCUMENTED_exclusion" in result.applied_predicates

    @pytest.mark.unit
    def test_disabled_reproduction_cost_modifier(self) -> None:
        """DISABLED applies reproduction_cost_modifier from CommunityState."""
        from babylon.economics.melt.filtration import apply_filtration

        membership = _make_membership(CommunityType.DISABLED)
        state = _make_community_state(
            CommunityType.DISABLED,
            reproduction_cost_modifier=CS.REPRODUCTION_COST_MODIFIER,
        )
        result = apply_filtration(
            wealth_percentile=CS.WEALTH_DISABLED,
            precarity=PrecarityStatus.STABLE,
            memberships=[membership],
            community_states={CommunityType.DISABLED.value: state},
        )
        expected_wealth = CS.WEALTH_DISABLED / CS.REPRODUCTION_COST_MODIFIER
        assert result.effective_wealth_percentile == pytest.approx(expected_wealth)
        assert "DISABLED_reproduction_cost" in result.applied_predicates

    @pytest.mark.unit
    def test_settler_no_filtration(self) -> None:
        """SETTLER membership produces no filtration (identity)."""
        from babylon.economics.melt.filtration import apply_filtration

        membership = _make_membership(CommunityType.SETTLER)
        result = apply_filtration(
            wealth_percentile=CS.WEALTH_LA,
            precarity=PrecarityStatus.STABLE,
            memberships=[membership],
            community_states={},
        )
        assert result.effective_wealth_percentile == CS.WEALTH_LA
        assert result.effective_precarity == PrecarityStatus.STABLE
        assert len(result.applied_predicates) == 0


class TestMultiMembershipComposition:
    """T016: Multi-membership composition tests."""

    @pytest.mark.unit
    def test_most_restrictive_wins(self) -> None:
        """Multiple memberships: most restrictive effective values used."""
        from babylon.economics.melt.filtration import apply_filtration

        memberships = [
            _make_membership(CommunityType.FIRST_NATIONS),
            _make_membership(CommunityType.DISABLED),
        ]
        state = _make_community_state(
            CommunityType.DISABLED,
            reproduction_cost_modifier=CS.REPRODUCTION_COST_MODIFIER,
        )
        result = apply_filtration(
            wealth_percentile=CS.WEALTH_DISABLED,
            precarity=PrecarityStatus.STABLE,
            memberships=memberships,
            community_states={CommunityType.DISABLED.value: state},
        )
        # Both predicates should fire
        assert len(result.applied_predicates) >= 2
        # Effective wealth should be the minimum of both reductions
        first_nations_wealth = CS.WEALTH_DISABLED * CS.TRUST_LAND_DISCOUNT
        disabled_wealth = CS.WEALTH_DISABLED / CS.REPRODUCTION_COST_MODIFIER
        expected_min = min(first_nations_wealth, disabled_wealth)
        assert result.effective_wealth_percentile == pytest.approx(expected_min)

    @pytest.mark.unit
    def test_order_independence(self) -> None:
        """Filtration result is the same regardless of membership order."""
        from babylon.economics.melt.filtration import apply_filtration

        m1 = _make_membership(CommunityType.FIRST_NATIONS)
        m2 = _make_membership(CommunityType.INCARCERATED)

        result_a = apply_filtration(
            wealth_percentile=CS.WEALTH_FIRST_NATIONS,
            precarity=PrecarityStatus.STABLE,
            memberships=[m1, m2],
            community_states={},
        )
        result_b = apply_filtration(
            wealth_percentile=CS.WEALTH_FIRST_NATIONS,
            precarity=PrecarityStatus.STABLE,
            memberships=[m2, m1],
            community_states={},
        )
        assert result_a.effective_wealth_percentile == result_b.effective_wealth_percentile
        assert result_a.effective_precarity == result_b.effective_precarity

    @pytest.mark.unit
    def test_first_nations_overrides_settler(self) -> None:
        """FIRST_NATIONS membership takes precedence over SETTLER."""
        from babylon.economics.melt.filtration import apply_filtration

        memberships = [
            _make_membership(CommunityType.SETTLER),
            _make_membership(CommunityType.FIRST_NATIONS),
        ]
        result = apply_filtration(
            wealth_percentile=CS.WEALTH_FIRST_NATIONS,
            precarity=PrecarityStatus.STABLE,
            memberships=memberships,
            community_states={},
        )
        # FIRST_NATIONS filtration should still apply
        expected_wealth = CS.WEALTH_FIRST_NATIONS * CS.TRUST_LAND_DISCOUNT
        assert result.effective_wealth_percentile == pytest.approx(expected_wealth)
