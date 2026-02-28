"""Tests for action eligibility checking (Feature 032).

Verifies the 21x4 eligibility matrix and special-case overrides for
REPRESS, SURVEIL, and ASSIMILATE.
"""

from __future__ import annotations

import pytest

from babylon.models.enums import ActionType, OrgType
from babylon.ooda.action_eligibility import ELIGIBILITY_MAP, check_eligibility


class TestEligibilityMapCompleteness:
    """Verify the eligibility matrix has entries for all 21x4 combinations."""

    def test_matrix_size(self) -> None:
        expected = len(OrgType) * len(ActionType)
        assert len(ELIGIBILITY_MAP) == expected

    def test_all_pairs_present(self) -> None:
        for org_type in OrgType:
            for action_type in ActionType:
                assert (org_type.value, action_type.value) in ELIGIBILITY_MAP


class TestUniversalActions:
    """Actions available to all org types."""

    @pytest.mark.parametrize(
        "action_type",
        [
            ActionType.RECRUIT,
            ActionType.ORGANIZE,
            ActionType.EDUCATE,
            ActionType.AGITATE,
            ActionType.PROPAGANDIZE,
            ActionType.FUNDRAISE,
            ActionType.PROTEST,
            ActionType.COUNTER_INTEL,
            ActionType.MAP_NETWORK,
            ActionType.PROPOSE_ALLIANCE,
            ActionType.DENOUNCE,
            ActionType.BUILD_INFRASTRUCTURE,
        ],
    )
    @pytest.mark.parametrize("org_type", list(OrgType))
    def test_universal_actions(
        self,
        action_type: ActionType,
        org_type: OrgType,
    ) -> None:
        assert check_eligibility(org_type, action_type) is True


class TestRestrictedActions:
    """Actions with org-type restrictions."""

    def test_employ_business_only(self) -> None:
        assert check_eligibility(OrgType.BUSINESS, ActionType.EMPLOY) is True
        assert check_eligibility(OrgType.STATE_APPARATUS, ActionType.EMPLOY) is False
        assert check_eligibility(OrgType.POLITICAL_FACTION, ActionType.EMPLOY) is False
        assert check_eligibility(OrgType.CIVIL_SOCIETY, ActionType.EMPLOY) is False

    def test_infiltrate_state_only(self) -> None:
        assert check_eligibility(OrgType.STATE_APPARATUS, ActionType.INFILTRATE) is True
        assert check_eligibility(OrgType.BUSINESS, ActionType.INFILTRATE) is False
        assert check_eligibility(OrgType.POLITICAL_FACTION, ActionType.INFILTRATE) is False
        assert check_eligibility(OrgType.CIVIL_SOCIETY, ActionType.INFILTRATE) is False

    def test_provide_service_not_business(self) -> None:
        assert check_eligibility(OrgType.BUSINESS, ActionType.PROVIDE_SERVICE) is False
        assert check_eligibility(OrgType.STATE_APPARATUS, ActionType.PROVIDE_SERVICE) is True
        assert check_eligibility(OrgType.POLITICAL_FACTION, ActionType.PROVIDE_SERVICE) is True
        assert check_eligibility(OrgType.CIVIL_SOCIETY, ActionType.PROVIDE_SERVICE) is True

    def test_strike_faction_and_civil_society(self) -> None:
        assert check_eligibility(OrgType.POLITICAL_FACTION, ActionType.STRIKE) is True
        assert check_eligibility(OrgType.CIVIL_SOCIETY, ActionType.STRIKE) is True
        assert check_eligibility(OrgType.STATE_APPARATUS, ActionType.STRIKE) is False
        assert check_eligibility(OrgType.BUSINESS, ActionType.STRIKE) is False

    def test_expropriate_faction_only(self) -> None:
        assert check_eligibility(OrgType.POLITICAL_FACTION, ActionType.EXPROPRIATE) is True
        assert check_eligibility(OrgType.STATE_APPARATUS, ActionType.EXPROPRIATE) is False
        assert check_eligibility(OrgType.BUSINESS, ActionType.EXPROPRIATE) is False
        assert check_eligibility(OrgType.CIVIL_SOCIETY, ActionType.EXPROPRIATE) is False

    def test_attack_infrastructure_state_and_faction(self) -> None:
        assert check_eligibility(OrgType.STATE_APPARATUS, ActionType.ATTACK_INFRASTRUCTURE) is True
        assert (
            check_eligibility(OrgType.POLITICAL_FACTION, ActionType.ATTACK_INFRASTRUCTURE) is True
        )
        assert check_eligibility(OrgType.BUSINESS, ActionType.ATTACK_INFRASTRUCTURE) is False
        assert check_eligibility(OrgType.CIVIL_SOCIETY, ActionType.ATTACK_INFRASTRUCTURE) is False


class TestRepressSpecialCase:
    """REPRESS: StateApparatus by default, or violence_capacity > 0."""

    def test_state_apparatus_always_eligible(self) -> None:
        assert check_eligibility(OrgType.STATE_APPARATUS, ActionType.REPRESS) is True

    def test_non_state_without_violence_capacity(self) -> None:
        assert check_eligibility(OrgType.POLITICAL_FACTION, ActionType.REPRESS) is False

    def test_non_state_with_violence_capacity(self) -> None:
        attrs = {"violence_capacity": 1}
        assert (
            check_eligibility(
                OrgType.POLITICAL_FACTION,
                ActionType.REPRESS,
                org_attrs=attrs,
            )
            is True
        )

    def test_violence_capacity_zero_not_eligible(self) -> None:
        attrs = {"violence_capacity": 0}
        assert (
            check_eligibility(
                OrgType.POLITICAL_FACTION,
                ActionType.REPRESS,
                org_attrs=attrs,
            )
            is False
        )

    def test_business_with_violence_capacity(self) -> None:
        attrs = {"violence_capacity": 5}
        assert (
            check_eligibility(
                OrgType.BUSINESS,
                ActionType.REPRESS,
                org_attrs=attrs,
            )
            is True
        )


class TestSurveilSpecialCase:
    """SURVEIL: StateApparatus by default, or surveillance_capacity > 0."""

    def test_state_apparatus_always_eligible(self) -> None:
        assert check_eligibility(OrgType.STATE_APPARATUS, ActionType.SURVEIL) is True

    def test_non_state_without_surveillance_capacity(self) -> None:
        assert check_eligibility(OrgType.CIVIL_SOCIETY, ActionType.SURVEIL) is False

    def test_non_state_with_surveillance_capacity(self) -> None:
        attrs = {"surveillance_capacity": 1}
        assert (
            check_eligibility(
                OrgType.CIVIL_SOCIETY,
                ActionType.SURVEIL,
                org_attrs=attrs,
            )
            is True
        )

    def test_surveillance_capacity_zero_not_eligible(self) -> None:
        attrs = {"surveillance_capacity": 0}
        assert (
            check_eligibility(
                OrgType.CIVIL_SOCIETY,
                ActionType.SURVEIL,
                org_attrs=attrs,
            )
            is False
        )


class TestAssimilateSpecialCase:
    """ASSIMILATE: StateApparatus by default, or LIBERAL + is_institution."""

    def test_state_apparatus_always_eligible(self) -> None:
        assert check_eligibility(OrgType.STATE_APPARATUS, ActionType.ASSIMILATE) is True

    def test_faction_not_eligible_by_default(self) -> None:
        assert check_eligibility(OrgType.POLITICAL_FACTION, ActionType.ASSIMILATE) is False

    def test_liberal_institution_faction_eligible(self) -> None:
        attrs = {
            "consciousness_tendency": "liberal",
            "is_institution": True,
        }
        assert (
            check_eligibility(
                OrgType.POLITICAL_FACTION,
                ActionType.ASSIMILATE,
                org_attrs=attrs,
            )
            is True
        )

    def test_liberal_non_institution_not_eligible(self) -> None:
        attrs = {
            "consciousness_tendency": "liberal",
            "is_institution": False,
        }
        assert (
            check_eligibility(
                OrgType.POLITICAL_FACTION,
                ActionType.ASSIMILATE,
                org_attrs=attrs,
            )
            is False
        )

    def test_revolutionary_institution_not_eligible(self) -> None:
        attrs = {
            "consciousness_tendency": "revolutionary",
            "is_institution": True,
        }
        assert (
            check_eligibility(
                OrgType.POLITICAL_FACTION,
                ActionType.ASSIMILATE,
                org_attrs=attrs,
            )
            is False
        )

    def test_civil_society_liberal_institution_eligible(self) -> None:
        attrs = {
            "consciousness_tendency": "liberal",
            "is_institution": True,
        }
        assert (
            check_eligibility(
                OrgType.CIVIL_SOCIETY,
                ActionType.ASSIMILATE,
                org_attrs=attrs,
            )
            is True
        )

    def test_business_never_eligible(self) -> None:
        attrs = {
            "consciousness_tendency": "liberal",
            "is_institution": True,
        }
        assert (
            check_eligibility(
                OrgType.BUSINESS,
                ActionType.ASSIMILATE,
                org_attrs=attrs,
            )
            is False
        )


class TestStringArguments:
    """Verify that string arguments work the same as enum arguments."""

    def test_string_org_type(self) -> None:
        assert check_eligibility("state_apparatus", ActionType.REPRESS) is True

    def test_string_action_type(self) -> None:
        assert check_eligibility(OrgType.STATE_APPARATUS, "repress") is True

    def test_both_strings(self) -> None:
        assert check_eligibility("state_apparatus", "repress") is True

    def test_unknown_pair_returns_false(self) -> None:
        assert check_eligibility("unknown_type", "unknown_action") is False
