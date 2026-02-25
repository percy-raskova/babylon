"""Unit tests for community models (Feature 022).

TDD RED phase: Tests written before implementation of hypergraph builder.
Tests cover CommunityState, CommunityMembership validation, and lookup dicts.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.community import (
    LEGAL_STATUS_MULTIPLIERS,
    LEGAL_STATUS_ORDER,
    ROLE_STRENGTH_WEIGHTS,
    CommunityMembership,
    CommunityState,
)
from babylon.models.enums import CommunityType, LegalStatus, MembershipRole


@pytest.mark.unit
class TestCommunityState:
    """Validate CommunityState frozen model."""

    def test_create_with_defaults(self) -> None:
        """Community state creates with sensible defaults."""
        cs = CommunityState(community_type=CommunityType.NEW_AFRIKAN)
        assert cs.community_type == CommunityType.NEW_AFRIKAN
        assert cs.heat == pytest.approx(0.0, abs=1e-4)
        assert cs.legal_status == LegalStatus.LEGAL
        assert cs.cohesion == pytest.approx(0.5, abs=1e-4)
        assert cs.infrastructure == pytest.approx(0.3, abs=1e-4)
        assert cs.visibility == pytest.approx(0.5, abs=1e-4)
        assert cs.reproduction_cost_modifier == pytest.approx(1.0, abs=1e-4)
        assert cs.rent_access_modifier == pytest.approx(1.0, abs=1e-4)

    def test_frozen_immutability(self) -> None:
        """Community state is frozen — attribute mutation raises error."""
        cs = CommunityState(community_type=CommunityType.TRANS)
        with pytest.raises(ValidationError):
            cs.heat = 0.9  # type: ignore[misc]

    def test_heat_constrained_to_probability(self) -> None:
        """Heat must be in [0.0, 1.0]."""
        with pytest.raises(ValidationError):
            CommunityState(community_type=CommunityType.DISABLED, heat=1.5)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            CommunityState(community_type=CommunityType.DISABLED, heat=-0.1)  # type: ignore[arg-type]

    def test_model_copy_produces_new_instance(self) -> None:
        """Frozen model mutation via model_copy."""
        cs = CommunityState(community_type=CommunityType.QUEER, heat=0.3)  # type: ignore[arg-type]
        cs2 = cs.model_copy(update={"heat": 0.8})
        assert cs.heat == pytest.approx(0.3, abs=1e-4)
        assert cs2.heat == pytest.approx(0.8, abs=1e-4)

    def test_all_community_types_accepted(self) -> None:
        """Every CommunityType enum value is valid."""
        for ct in CommunityType:
            cs = CommunityState(community_type=ct)
            assert cs.community_type == ct

    def test_hegemonic_communities_exist(self) -> None:
        """Hegemonic community types (WHITE, CISGENDER, HETEROSEXUAL, ABLED) exist."""
        hegemonic = {
            CommunityType.WHITE,
            CommunityType.CISGENDER,
            CommunityType.HETEROSEXUAL,
            CommunityType.ABLED,
        }
        for ct in hegemonic:
            cs = CommunityState(community_type=ct)
            assert cs.community_type == ct


@pytest.mark.unit
class TestCommunityMembership:
    """Validate CommunityMembership frozen model."""

    def test_create_with_defaults(self) -> None:
        """Membership creates with sensible defaults."""
        cm = CommunityMembership(
            agent_id="C001",
            community_type=CommunityType.NEW_AFRIKAN,
        )
        assert cm.agent_id == "C001"
        assert cm.community_type == CommunityType.NEW_AFRIKAN
        assert cm.role == MembershipRole.PARTICIPANT
        assert cm.strength == pytest.approx(0.4, abs=1e-4)
        assert cm.visibility == pytest.approx(0.5, abs=1e-4)
        assert cm.overt is False

    def test_effective_visibility_not_overt(self) -> None:
        """Non-overt membership returns base visibility."""
        cm = CommunityMembership(
            agent_id="C001",
            community_type=CommunityType.TRANS,
            visibility=0.6,  # type: ignore[arg-type]
            overt=False,
        )
        assert cm.effective_visibility == pytest.approx(0.6, abs=1e-4)

    def test_effective_visibility_overt_overrides(self) -> None:
        """Overt flag overrides visibility to 1.0."""
        cm = CommunityMembership(
            agent_id="C001",
            community_type=CommunityType.TRANS,
            visibility=0.3,  # type: ignore[arg-type]
            overt=True,
        )
        assert cm.effective_visibility == pytest.approx(1.0, abs=1e-4)

    def test_frozen_immutability(self) -> None:
        """Membership is frozen."""
        cm = CommunityMembership(
            agent_id="C001",
            community_type=CommunityType.DISABLED,
        )
        with pytest.raises(ValidationError):
            cm.overt = True  # type: ignore[misc]


@pytest.mark.unit
class TestLookupDicts:
    """Validate ROLE_STRENGTH_WEIGHTS and LEGAL_STATUS_MULTIPLIERS."""

    def test_role_weights_complete(self) -> None:
        """Every MembershipRole has a weight."""
        for role in MembershipRole:
            assert role in ROLE_STRENGTH_WEIGHTS

    def test_role_weights_values(self) -> None:
        """Role weights match spec: 1.0, 0.7, 0.4, 0.2, 0.1."""
        assert ROLE_STRENGTH_WEIGHTS[MembershipRole.CORE_ORGANIZER] == 1.0
        assert ROLE_STRENGTH_WEIGHTS[MembershipRole.ACTIVE] == 0.7
        assert ROLE_STRENGTH_WEIGHTS[MembershipRole.PARTICIPANT] == 0.4
        assert ROLE_STRENGTH_WEIGHTS[MembershipRole.PERIPHERAL] == 0.2
        assert ROLE_STRENGTH_WEIGHTS[MembershipRole.SYMPATHIZER] == 0.1

    def test_legal_multipliers_complete(self) -> None:
        """Every LegalStatus has a multiplier."""
        for status in LegalStatus:
            assert status in LEGAL_STATUS_MULTIPLIERS

    def test_legal_multipliers_values(self) -> None:
        """Legal multipliers match spec: 0.1, 0.5, 1.0, 2.0, 3.0."""
        assert LEGAL_STATUS_MULTIPLIERS[LegalStatus.LEGAL] == 0.1
        assert LEGAL_STATUS_MULTIPLIERS[LegalStatus.SURVEILLED] == 0.5
        assert LEGAL_STATUS_MULTIPLIERS[LegalStatus.DESIGNATED_EXTREMIST] == 1.0
        assert LEGAL_STATUS_MULTIPLIERS[LegalStatus.DESIGNATED_TERRORIST] == 2.0
        assert LEGAL_STATUS_MULTIPLIERS[LegalStatus.CRIMINALIZED] == 3.0

    def test_legal_status_order_complete(self) -> None:
        """Legal status order contains all statuses in escalation sequence."""
        assert len(LEGAL_STATUS_ORDER) == len(LegalStatus)
        for status in LegalStatus:
            assert status in LEGAL_STATUS_ORDER

    def test_legal_status_order_monotonic(self) -> None:
        """Legal status multipliers increase monotonically along order."""
        for i in range(len(LEGAL_STATUS_ORDER) - 1):
            current = LEGAL_STATUS_MULTIPLIERS[LEGAL_STATUS_ORDER[i]]
            next_val = LEGAL_STATUS_MULTIPLIERS[LEGAL_STATUS_ORDER[i + 1]]
            assert next_val > current


@pytest.mark.unit
class TestCommunityReproductionCost:
    """Tests for compute_community_cost_modifier (Feature 022, US4)."""

    def test_no_memberships_returns_one(self) -> None:
        """No memberships → modifier is 1.0 (no effect)."""
        from babylon.formulas.community import compute_community_cost_modifier

        result = compute_community_cost_modifier([], {})
        assert result == pytest.approx(1.0)

    def test_single_membership_returns_modifier(self) -> None:
        """Single community returns its reproduction_cost_modifier."""
        from babylon.formulas.community import compute_community_cost_modifier

        states = {
            CommunityType.DISABLED: CommunityState(
                community_type=CommunityType.DISABLED,
                reproduction_cost_modifier=1.2,
            ),
        }
        memberships = [
            CommunityMembership(
                agent_id="A1",
                community_type=CommunityType.DISABLED,
            ),
        ]
        result = compute_community_cost_modifier(memberships, states)
        assert result == pytest.approx(1.2)

    def test_multiplicative_compounding(self) -> None:
        """Multiple memberships compound multiplicatively."""
        from babylon.formulas.community import compute_community_cost_modifier

        states = {
            CommunityType.DISABLED: CommunityState(
                community_type=CommunityType.DISABLED,
                reproduction_cost_modifier=1.2,
            ),
            CommunityType.TRANS: CommunityState(
                community_type=CommunityType.TRANS,
                reproduction_cost_modifier=1.1,
            ),
        }
        memberships = [
            CommunityMembership(agent_id="A1", community_type=CommunityType.DISABLED),
            CommunityMembership(agent_id="A1", community_type=CommunityType.TRANS),
        ]
        result = compute_community_cost_modifier(memberships, states)
        assert result == pytest.approx(1.2 * 1.1)
