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

    def test_three_category_taxonomy(self) -> None:
        """All three hyperedge categories represented in CommunityType."""
        # Category 1: Contradiction Pairs (both sides)
        cat1_hegemonic = {CommunityType.SETTLER, CommunityType.PATRIARCHAL}
        cat1_marginalized = {
            CommunityType.NEW_AFRIKAN,
            CommunityType.FIRST_NATIONS,
            CommunityType.CHICANO,
            CommunityType.WOMEN,
            CommunityType.TRANS,
        }
        # Category 2: Institutional Exclusion (marginalized only)
        cat2 = {
            CommunityType.DISABLED,
            CommunityType.QUEER,
            CommunityType.UNDOCUMENTED,
            CommunityType.INCARCERATED,
        }
        # Category 3: Lifecycle Phases
        cat3 = {CommunityType.YOUTH, CommunityType.ADULT, CommunityType.ELDER}

        all_types = cat1_hegemonic | cat1_marginalized | cat2 | cat3
        assert all_types == set(CommunityType)


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
class TestCommunityTaxonomy:
    """Validate COMMUNITY_CATEGORY_MAP and category sets (Feature 029, US1)."""

    def test_all_14_types_mapped(self) -> None:
        """Every CommunityType has an entry in COMMUNITY_CATEGORY_MAP."""
        from babylon.models.entities.community import COMMUNITY_CATEGORY_MAP

        assert set(COMMUNITY_CATEGORY_MAP.keys()) == set(CommunityType)

    def test_category_map_exhaustive(self) -> None:
        """No unmapped CommunityType members exist."""
        from babylon.models.entities.community import COMMUNITY_CATEGORY_MAP

        unmapped = set(CommunityType) - set(COMMUNITY_CATEGORY_MAP.keys())
        assert unmapped == set(), f"Unmapped types: {unmapped}"

    def test_settler_is_contradiction_pair(self) -> None:
        """SETTLER maps to CONTRADICTION_PAIR."""
        from babylon.models.entities.community import COMMUNITY_CATEGORY_MAP
        from babylon.models.enums import HyperedgeCategory

        assert COMMUNITY_CATEGORY_MAP[CommunityType.SETTLER] == HyperedgeCategory.CONTRADICTION_PAIR

    def test_disabled_is_institutional_exclusion(self) -> None:
        """DISABLED maps to INSTITUTIONAL_EXCLUSION."""
        from babylon.models.entities.community import COMMUNITY_CATEGORY_MAP
        from babylon.models.enums import HyperedgeCategory

        assert (
            COMMUNITY_CATEGORY_MAP[CommunityType.DISABLED]
            == HyperedgeCategory.INSTITUTIONAL_EXCLUSION
        )

    def test_youth_is_lifecycle_phase(self) -> None:
        """YOUTH maps to LIFECYCLE_PHASE."""
        from babylon.models.entities.community import COMMUNITY_CATEGORY_MAP
        from babylon.models.enums import HyperedgeCategory

        assert COMMUNITY_CATEGORY_MAP[CommunityType.YOUTH] == HyperedgeCategory.LIFECYCLE_PHASE

    def test_correct_categories_per_contract(self) -> None:
        """Specific types map to expected categories per taxonomy-api contract."""
        from babylon.models.entities.community import COMMUNITY_CATEGORY_MAP
        from babylon.models.enums import HyperedgeCategory

        # All contradiction pair members
        for ct in [
            CommunityType.SETTLER,
            CommunityType.PATRIARCHAL,
            CommunityType.NEW_AFRIKAN,
            CommunityType.FIRST_NATIONS,
            CommunityType.CHICANO,
            CommunityType.WOMEN,
            CommunityType.TRANS,
        ]:
            assert COMMUNITY_CATEGORY_MAP[ct] == HyperedgeCategory.CONTRADICTION_PAIR, ct

        # All institutional exclusion members
        for ct in [
            CommunityType.DISABLED,
            CommunityType.QUEER,
            CommunityType.UNDOCUMENTED,
            CommunityType.INCARCERATED,
        ]:
            assert COMMUNITY_CATEGORY_MAP[ct] == HyperedgeCategory.INSTITUTIONAL_EXCLUSION, ct

        # All lifecycle phase members
        for ct in [CommunityType.YOUTH, CommunityType.ADULT, CommunityType.ELDER]:
            assert COMMUNITY_CATEGORY_MAP[ct] == HyperedgeCategory.LIFECYCLE_PHASE, ct


@pytest.mark.unit
class TestCategorySets:
    """Validate HEGEMONIC, MARGINALIZED, LIFECYCLE community sets (Feature 029, US1)."""

    def test_hegemonic_communities_correct(self) -> None:
        """Hegemonic set contains exactly SETTLER and PATRIARCHAL."""
        from babylon.models.entities.community import HEGEMONIC_COMMUNITIES

        assert (
            frozenset({CommunityType.SETTLER, CommunityType.PATRIARCHAL}) == HEGEMONIC_COMMUNITIES
        )

    def test_marginalized_communities_correct(self) -> None:
        """Marginalized set contains correct 9 types."""
        from babylon.models.entities.community import MARGINALIZED_COMMUNITIES

        expected = frozenset(
            {
                CommunityType.NEW_AFRIKAN,
                CommunityType.FIRST_NATIONS,
                CommunityType.CHICANO,
                CommunityType.WOMEN,
                CommunityType.TRANS,
                CommunityType.DISABLED,
                CommunityType.QUEER,
                CommunityType.UNDOCUMENTED,
                CommunityType.INCARCERATED,
            }
        )
        assert expected == MARGINALIZED_COMMUNITIES

    def test_lifecycle_communities_correct(self) -> None:
        """Lifecycle set contains exactly YOUTH, ADULT, ELDER."""
        from babylon.models.entities.community import LIFECYCLE_COMMUNITIES

        expected = frozenset({CommunityType.YOUTH, CommunityType.ADULT, CommunityType.ELDER})
        assert expected == LIFECYCLE_COMMUNITIES

    def test_union_covers_all_types(self) -> None:
        """Union of all three sets covers all 14 CommunityType members."""
        from babylon.models.entities.community import (
            HEGEMONIC_COMMUNITIES,
            LIFECYCLE_COMMUNITIES,
            MARGINALIZED_COMMUNITIES,
        )

        union = HEGEMONIC_COMMUNITIES | MARGINALIZED_COMMUNITIES | LIFECYCLE_COMMUNITIES
        assert union == frozenset(CommunityType)

    def test_sets_are_disjoint(self) -> None:
        """The three category sets have no overlap."""
        from babylon.models.entities.community import (
            HEGEMONIC_COMMUNITIES,
            LIFECYCLE_COMMUNITIES,
            MARGINALIZED_COMMUNITIES,
        )

        assert frozenset() == HEGEMONIC_COMMUNITIES & MARGINALIZED_COMMUNITIES
        assert frozenset() == HEGEMONIC_COMMUNITIES & LIFECYCLE_COMMUNITIES
        assert frozenset() == MARGINALIZED_COMMUNITIES & LIFECYCLE_COMMUNITIES


@pytest.mark.unit
class TestCommunityStateCategory:
    """Validate CommunityState.category auto-assignment (Feature 029, US1)."""

    def test_category_auto_assigned_from_community_type(self) -> None:
        """Category is auto-assigned based on community_type."""
        from babylon.models.enums import HyperedgeCategory

        cs = CommunityState(community_type=CommunityType.SETTLER)
        assert cs.category == HyperedgeCategory.CONTRADICTION_PAIR

    def test_category_auto_assigned_exclusion(self) -> None:
        """DISABLED gets INSTITUTIONAL_EXCLUSION category."""
        from babylon.models.enums import HyperedgeCategory

        cs = CommunityState(community_type=CommunityType.DISABLED)
        assert cs.category == HyperedgeCategory.INSTITUTIONAL_EXCLUSION

    def test_category_auto_assigned_lifecycle(self) -> None:
        """YOUTH gets LIFECYCLE_PHASE category."""
        from babylon.models.enums import HyperedgeCategory

        cs = CommunityState(community_type=CommunityType.YOUTH)
        assert cs.category == HyperedgeCategory.LIFECYCLE_PHASE

    def test_all_types_get_category(self) -> None:
        """Every CommunityType produces a CommunityState with valid category."""
        from babylon.models.enums import HyperedgeCategory

        for ct in CommunityType:
            cs = CommunityState(community_type=ct)
            assert isinstance(cs.category, HyperedgeCategory), f"{ct} has no category"


@pytest.mark.unit
class TestContradictionAxis:
    """Validate ContradictionAxis model and axis constants (Feature 029, US2)."""

    def test_colonial_axis_exists(self) -> None:
        """COLONIAL_AXIS is a ContradictionAxis instance."""
        from babylon.models.entities.community import COLONIAL_AXIS, ContradictionAxis

        assert isinstance(COLONIAL_AXIS, ContradictionAxis)

    def test_colonial_axis_fields(self) -> None:
        """COLONIAL_AXIS has correct hegemonic and marginalized members."""
        from babylon.models.entities.community import COLONIAL_AXIS

        assert COLONIAL_AXIS.id == "colonial"
        assert COLONIAL_AXIS.name == "Colonial"
        assert COLONIAL_AXIS.hegemonic == CommunityType.SETTLER
        assert COLONIAL_AXIS.marginalized == [
            CommunityType.NEW_AFRIKAN,
            CommunityType.FIRST_NATIONS,
            CommunityType.CHICANO,
        ]
        assert COLONIAL_AXIS.exclusive is True
        assert COLONIAL_AXIS.permeable is False

    def test_patriarchal_axis_exists(self) -> None:
        """PATRIARCHAL_AXIS is a ContradictionAxis instance."""
        from babylon.models.entities.community import PATRIARCHAL_AXIS, ContradictionAxis

        assert isinstance(PATRIARCHAL_AXIS, ContradictionAxis)

    def test_patriarchal_axis_fields(self) -> None:
        """PATRIARCHAL_AXIS has correct hegemonic and marginalized members."""
        from babylon.models.entities.community import PATRIARCHAL_AXIS

        assert PATRIARCHAL_AXIS.id == "patriarchal"
        assert PATRIARCHAL_AXIS.name == "Patriarchal"
        assert PATRIARCHAL_AXIS.hegemonic == CommunityType.PATRIARCHAL
        assert PATRIARCHAL_AXIS.marginalized == [
            CommunityType.WOMEN,
            CommunityType.TRANS,
        ]
        assert PATRIARCHAL_AXIS.exclusive is True
        assert PATRIARCHAL_AXIS.permeable is False

    def test_contradiction_axes_list(self) -> None:
        """CONTRADICTION_AXES contains both axes."""
        from babylon.models.entities.community import (
            COLONIAL_AXIS,
            CONTRADICTION_AXES,
            PATRIARCHAL_AXIS,
        )

        assert len(CONTRADICTION_AXES) == 2
        assert COLONIAL_AXIS in CONTRADICTION_AXES
        assert PATRIARCHAL_AXIS in CONTRADICTION_AXES

    def test_axis_is_frozen(self) -> None:
        """ContradictionAxis model is frozen (immutable)."""
        from babylon.models.entities.community import COLONIAL_AXIS

        with pytest.raises(ValidationError):
            COLONIAL_AXIS.name = "Modified"  # type: ignore[misc]

    def test_axis_extraction_mechanism_nonempty(self) -> None:
        """Both axes have non-empty extraction mechanism descriptions."""
        from babylon.models.entities.community import COLONIAL_AXIS, PATRIARCHAL_AXIS

        assert len(COLONIAL_AXIS.extraction_mechanism) > 0
        assert len(PATRIARCHAL_AXIS.extraction_mechanism) > 0


@pytest.mark.unit
class TestAxisQueryFunctions:
    """Validate axis query functions (Feature 029, US2)."""

    # --- get_contradiction_axis ---

    def test_get_axis_settler(self) -> None:
        """SETTLER belongs to COLONIAL_AXIS."""
        from babylon.models.entities.community import COLONIAL_AXIS, get_contradiction_axis

        assert get_contradiction_axis(CommunityType.SETTLER) == COLONIAL_AXIS

    def test_get_axis_new_afrikan(self) -> None:
        """NEW_AFRIKAN belongs to COLONIAL_AXIS."""
        from babylon.models.entities.community import COLONIAL_AXIS, get_contradiction_axis

        assert get_contradiction_axis(CommunityType.NEW_AFRIKAN) == COLONIAL_AXIS

    def test_get_axis_patriarchal(self) -> None:
        """PATRIARCHAL belongs to PATRIARCHAL_AXIS."""
        from babylon.models.entities.community import PATRIARCHAL_AXIS, get_contradiction_axis

        assert get_contradiction_axis(CommunityType.PATRIARCHAL) == PATRIARCHAL_AXIS

    def test_get_axis_women(self) -> None:
        """WOMEN belongs to PATRIARCHAL_AXIS."""
        from babylon.models.entities.community import PATRIARCHAL_AXIS, get_contradiction_axis

        assert get_contradiction_axis(CommunityType.WOMEN) == PATRIARCHAL_AXIS

    def test_get_axis_disabled_returns_none(self) -> None:
        """DISABLED has no axis (institutional exclusion)."""
        from babylon.models.entities.community import get_contradiction_axis

        assert get_contradiction_axis(CommunityType.DISABLED) is None

    def test_get_axis_youth_returns_none(self) -> None:
        """YOUTH has no axis (lifecycle phase)."""
        from babylon.models.entities.community import get_contradiction_axis

        assert get_contradiction_axis(CommunityType.YOUTH) is None

    # --- is_hegemonic ---

    def test_settler_is_hegemonic(self) -> None:
        """SETTLER is hegemonic."""
        from babylon.models.entities.community import is_hegemonic

        assert is_hegemonic(CommunityType.SETTLER) is True

    def test_patriarchal_is_hegemonic(self) -> None:
        """PATRIARCHAL is hegemonic."""
        from babylon.models.entities.community import is_hegemonic

        assert is_hegemonic(CommunityType.PATRIARCHAL) is True

    def test_new_afrikan_not_hegemonic(self) -> None:
        """NEW_AFRIKAN is not hegemonic."""
        from babylon.models.entities.community import is_hegemonic

        assert is_hegemonic(CommunityType.NEW_AFRIKAN) is False

    def test_disabled_not_hegemonic(self) -> None:
        """DISABLED is not hegemonic."""
        from babylon.models.entities.community import is_hegemonic

        assert is_hegemonic(CommunityType.DISABLED) is False

    def test_youth_not_hegemonic(self) -> None:
        """YOUTH is not hegemonic."""
        from babylon.models.entities.community import is_hegemonic

        assert is_hegemonic(CommunityType.YOUTH) is False

    # --- is_marginalized ---

    def test_new_afrikan_is_marginalized(self) -> None:
        """NEW_AFRIKAN is marginalized."""
        from babylon.models.entities.community import is_marginalized

        assert is_marginalized(CommunityType.NEW_AFRIKAN) is True

    def test_disabled_is_marginalized(self) -> None:
        """DISABLED is marginalized (institutional exclusion counts)."""
        from babylon.models.entities.community import is_marginalized

        assert is_marginalized(CommunityType.DISABLED) is True

    def test_settler_not_marginalized(self) -> None:
        """SETTLER is not marginalized."""
        from babylon.models.entities.community import is_marginalized

        assert is_marginalized(CommunityType.SETTLER) is False

    def test_youth_not_marginalized(self) -> None:
        """YOUTH is not marginalized (lifecycle, not marginalized)."""
        from babylon.models.entities.community import is_marginalized

        assert is_marginalized(CommunityType.YOUTH) is False

    # --- get_opposing_communities ---

    def test_opposing_settler(self) -> None:
        """SETTLER opposes NEW_AFRIKAN, FIRST_NATIONS, CHICANO."""
        from babylon.models.entities.community import get_opposing_communities

        result = get_opposing_communities(CommunityType.SETTLER)
        assert result == [
            CommunityType.NEW_AFRIKAN,
            CommunityType.FIRST_NATIONS,
            CommunityType.CHICANO,
        ]

    def test_opposing_new_afrikan(self) -> None:
        """NEW_AFRIKAN opposes SETTLER."""
        from babylon.models.entities.community import get_opposing_communities

        result = get_opposing_communities(CommunityType.NEW_AFRIKAN)
        assert result == [CommunityType.SETTLER]

    def test_opposing_patriarchal(self) -> None:
        """PATRIARCHAL opposes WOMEN, TRANS."""
        from babylon.models.entities.community import get_opposing_communities

        result = get_opposing_communities(CommunityType.PATRIARCHAL)
        assert result == [CommunityType.WOMEN, CommunityType.TRANS]

    def test_opposing_disabled_empty(self) -> None:
        """DISABLED has no opposing communities (institutional exclusion)."""
        from babylon.models.entities.community import get_opposing_communities

        assert get_opposing_communities(CommunityType.DISABLED) == []

    # --- shared_marginalized_communities ---

    def test_shared_marginalized_overlap(self) -> None:
        """Shared marginalized between overlapping sets."""
        from babylon.models.entities.community import shared_marginalized_communities

        result = shared_marginalized_communities(
            {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED},
            {CommunityType.NEW_AFRIKAN, CommunityType.QUEER},
        )
        assert result == {CommunityType.NEW_AFRIKAN}

    def test_shared_marginalized_hegemonic_excluded(self) -> None:
        """Hegemonic types are excluded even if shared."""
        from babylon.models.entities.community import shared_marginalized_communities

        result = shared_marginalized_communities(
            {CommunityType.SETTLER, CommunityType.DISABLED},
            {CommunityType.SETTLER, CommunityType.DISABLED},
        )
        assert result == {CommunityType.DISABLED}

    def test_shared_marginalized_lifecycle_excluded(self) -> None:
        """Lifecycle types are excluded."""
        from babylon.models.entities.community import shared_marginalized_communities

        result = shared_marginalized_communities(
            {CommunityType.YOUTH, CommunityType.ADULT},
            {CommunityType.YOUTH},
        )
        assert result == set()


@pytest.mark.unit
class TestCommunityConsciousness:
    """Validate CommunityConsciousness model (Feature 029, US3)."""

    def test_create_with_defaults(self) -> None:
        """CommunityConsciousness creates with default values."""
        from babylon.models.entities.community import CommunityConsciousness
        from babylon.models.enums import ConsciousnessTendency

        cc = CommunityConsciousness()
        assert cc.collective_identity == pytest.approx(0.3, abs=1e-4)
        assert cc.dominant_tendency == ConsciousnessTendency.LIBERAL
        assert cc.ideological_contestation == pytest.approx(0.2, abs=1e-4)

    def test_create_with_custom_values(self) -> None:
        """CommunityConsciousness accepts custom values."""
        from babylon.models.entities.community import CommunityConsciousness
        from babylon.models.enums import ConsciousnessTendency

        cc = CommunityConsciousness(
            collective_identity=0.8,  # type: ignore[arg-type]
            dominant_tendency=ConsciousnessTendency.REVOLUTIONARY,
            ideological_contestation=0.6,  # type: ignore[arg-type]
        )
        assert cc.collective_identity == pytest.approx(0.8, abs=1e-4)
        assert cc.dominant_tendency == ConsciousnessTendency.REVOLUTIONARY
        assert cc.ideological_contestation == pytest.approx(0.6, abs=1e-4)

    def test_collective_identity_constrained(self) -> None:
        """collective_identity must be in [0, 1]."""
        from babylon.models.entities.community import CommunityConsciousness

        with pytest.raises(ValidationError):
            CommunityConsciousness(collective_identity=1.5)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            CommunityConsciousness(collective_identity=-0.1)  # type: ignore[arg-type]

    def test_contestation_constrained(self) -> None:
        """ideological_contestation must be in [0, 1]."""
        from babylon.models.entities.community import CommunityConsciousness

        with pytest.raises(ValidationError):
            CommunityConsciousness(ideological_contestation=2.0)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            CommunityConsciousness(ideological_contestation=-0.5)  # type: ignore[arg-type]

    def test_frozen_immutability(self) -> None:
        """CommunityConsciousness is frozen."""
        from babylon.models.entities.community import CommunityConsciousness

        cc = CommunityConsciousness()
        with pytest.raises(ValidationError):
            cc.collective_identity = 0.9  # type: ignore[misc]


@pytest.mark.unit
class TestConsciousnessDefaults:
    """Validate CONSCIOUSNESS_DEFAULTS for all 14 types (Feature 029, US3)."""

    def test_all_14_types_present(self) -> None:
        """Every CommunityType has a default consciousness."""
        from babylon.models.entities.community import CONSCIOUSNESS_DEFAULTS

        assert set(CONSCIOUSNESS_DEFAULTS.keys()) == set(CommunityType)

    def test_incarcerated_is_revolutionary(self) -> None:
        """INCARCERATED default tendency is REVOLUTIONARY (George Jackson tradition)."""
        from babylon.models.entities.community import CONSCIOUSNESS_DEFAULTS
        from babylon.models.enums import ConsciousnessTendency

        cc = CONSCIOUSNESS_DEFAULTS[CommunityType.INCARCERATED]
        assert cc.dominant_tendency == ConsciousnessTendency.REVOLUTIONARY
        assert cc.collective_identity == pytest.approx(0.6, abs=1e-4)

    def test_first_nations_is_revolutionary(self) -> None:
        """FIRST_NATIONS default tendency is REVOLUTIONARY (sovereignty framing)."""
        from babylon.models.entities.community import CONSCIOUSNESS_DEFAULTS
        from babylon.models.enums import ConsciousnessTendency

        cc = CONSCIOUSNESS_DEFAULTS[CommunityType.FIRST_NATIONS]
        assert cc.dominant_tendency == ConsciousnessTendency.REVOLUTIONARY
        assert cc.collective_identity == pytest.approx(0.6, abs=1e-4)

    def test_settler_is_liberal(self) -> None:
        """SETTLER default tendency is LIBERAL (passive beneficiary)."""
        from babylon.models.entities.community import CONSCIOUSNESS_DEFAULTS
        from babylon.models.enums import ConsciousnessTendency

        cc = CONSCIOUSNESS_DEFAULTS[CommunityType.SETTLER]
        assert cc.dominant_tendency == ConsciousnessTendency.LIBERAL
        assert cc.collective_identity == pytest.approx(0.4, abs=1e-4)

    def test_youth_contestation_from_entropy(self) -> None:
        """YOUTH contestation is Shannon entropy of (0.2, 0.6, 0.2)."""
        from babylon.models.entities.community import CONSCIOUSNESS_DEFAULTS
        from babylon.models.enums import ConsciousnessTendency

        cc = CONSCIOUSNESS_DEFAULTS[CommunityType.YOUTH]
        assert cc.dominant_tendency == ConsciousnessTendency.LIBERAL
        assert cc.collective_identity == pytest.approx(0.2, abs=1e-4)
        assert cc.ideological_contestation == pytest.approx(0.8650, abs=1e-3)

    def test_adult_contestation_from_entropy(self) -> None:
        """ADULT contestation is Shannon entropy of (0.1, 0.675, 0.225)."""
        from babylon.models.entities.community import CONSCIOUSNESS_DEFAULTS
        from babylon.models.enums import ConsciousnessTendency

        cc = CONSCIOUSNESS_DEFAULTS[CommunityType.ADULT]
        assert cc.dominant_tendency == ConsciousnessTendency.LIBERAL
        assert cc.collective_identity == pytest.approx(0.1, abs=1e-4)
        assert cc.ideological_contestation == pytest.approx(0.7566, abs=1e-3)


@pytest.mark.unit
class TestConsciousnessSerialization:
    """Validate consciousness JSON roundtrip (Feature 029, US3)."""

    def test_roundtrip_all_defaults(self) -> None:
        """All 14 consciousness defaults survive model_dump→model_validate."""
        from babylon.models.entities.community import (
            CONSCIOUSNESS_DEFAULTS,
            CommunityConsciousness,
        )

        for ct, original in CONSCIOUSNESS_DEFAULTS.items():
            data = original.model_dump(mode="json")
            restored = CommunityConsciousness.model_validate(data)
            assert restored == original, f"Roundtrip failed for {ct}"

    def test_consciousness_on_community_state_roundtrip(self) -> None:
        """CommunityState with consciousness survives serialization roundtrip."""
        from babylon.models.entities.community import CommunityConsciousness
        from babylon.models.enums import ConsciousnessTendency

        cs = CommunityState(
            community_type=CommunityType.INCARCERATED,
            consciousness=CommunityConsciousness(
                collective_identity=0.8,  # type: ignore[arg-type]
                dominant_tendency=ConsciousnessTendency.REVOLUTIONARY,
                ideological_contestation=0.4,  # type: ignore[arg-type]
            ),
        )
        data = cs.model_dump(mode="json")
        restored = CommunityState.model_validate(data)
        assert restored.consciousness == cs.consciousness


@pytest.mark.unit
class TestCommunityStateConsciousnessField:
    """Validate consciousness field on CommunityState (Feature 029, US3)."""

    def test_default_consciousness(self) -> None:
        """CommunityState gets default CommunityConsciousness if not specified."""
        from babylon.models.entities.community import CommunityConsciousness

        cs = CommunityState(community_type=CommunityType.SETTLER)
        assert isinstance(cs.consciousness, CommunityConsciousness)

    def test_custom_consciousness(self) -> None:
        """CommunityState accepts custom consciousness."""
        from babylon.models.entities.community import CommunityConsciousness
        from babylon.models.enums import ConsciousnessTendency

        cc = CommunityConsciousness(
            collective_identity=0.9,  # type: ignore[arg-type]
            dominant_tendency=ConsciousnessTendency.REVOLUTIONARY,
            ideological_contestation=0.7,  # type: ignore[arg-type]
        )
        cs = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            consciousness=cc,
        )
        assert cs.consciousness.collective_identity == pytest.approx(0.9, abs=1e-4)
        assert cs.consciousness.dominant_tendency == ConsciousnessTendency.REVOLUTIONARY


@pytest.mark.unit
class TestCrossClassBridge:
    """Validate is_cross_class_bridge computed field (Feature 029, US5)."""

    def test_institutional_exclusion_is_bridge(self) -> None:
        """INSTITUTIONAL_EXCLUSION communities are cross-class bridges."""
        for ct in [
            CommunityType.DISABLED,
            CommunityType.QUEER,
            CommunityType.UNDOCUMENTED,
            CommunityType.INCARCERATED,
        ]:
            cs = CommunityState(community_type=ct)
            assert cs.is_cross_class_bridge is True, f"{ct} should be bridge"

    def test_contradiction_pair_not_bridge(self) -> None:
        """CONTRADICTION_PAIR communities are not bridges."""
        for ct in [
            CommunityType.SETTLER,
            CommunityType.PATRIARCHAL,
            CommunityType.NEW_AFRIKAN,
            CommunityType.WOMEN,
        ]:
            cs = CommunityState(community_type=ct)
            assert cs.is_cross_class_bridge is False, f"{ct} should not be bridge"

    def test_lifecycle_not_bridge(self) -> None:
        """LIFECYCLE_PHASE communities are not bridges."""
        for ct in [CommunityType.YOUTH, CommunityType.ADULT, CommunityType.ELDER]:
            cs = CommunityState(community_type=ct)
            assert cs.is_cross_class_bridge is False, f"{ct} should not be bridge"


@pytest.mark.unit
class TestInfiltrationResistance:
    """Validate infiltration_resistance computed field (Feature 029, US4)."""

    def test_high_ci_high_cohesion(self) -> None:
        """CI=0.9, cohesion=0.8 → resistance≈0.852."""
        from babylon.models.entities.community import CommunityConsciousness

        cs = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            cohesion=0.8,  # type: ignore[arg-type]
            consciousness=CommunityConsciousness(collective_identity=0.9),  # type: ignore[arg-type]
        )
        assert cs.infiltration_resistance == pytest.approx(0.852, abs=1e-3)

    def test_low_ci_low_cohesion(self) -> None:
        """CI=0.1, cohesion=0.2 → resistance≈0.122."""
        from babylon.models.entities.community import CommunityConsciousness

        cs = CommunityState(
            community_type=CommunityType.SETTLER,
            cohesion=0.2,  # type: ignore[arg-type]
            consciousness=CommunityConsciousness(collective_identity=0.1),  # type: ignore[arg-type]
        )
        assert cs.infiltration_resistance == pytest.approx(0.122, abs=1e-3)

    def test_high_ci_low_cohesion(self) -> None:
        """CI=0.9, cohesion=0.1 → resistance≈0.579."""
        from babylon.models.entities.community import CommunityConsciousness

        cs = CommunityState(
            community_type=CommunityType.INCARCERATED,
            cohesion=0.1,  # type: ignore[arg-type]
            consciousness=CommunityConsciousness(collective_identity=0.9),  # type: ignore[arg-type]
        )
        assert cs.infiltration_resistance == pytest.approx(0.579, abs=1e-3)

    def test_low_ci_high_cohesion(self) -> None:
        """CI=0.1, cohesion=0.9 → resistance≈0.339."""
        from babylon.models.entities.community import CommunityConsciousness

        cs = CommunityState(
            community_type=CommunityType.DISABLED,
            cohesion=0.9,  # type: ignore[arg-type]
            consciousness=CommunityConsciousness(collective_identity=0.1),  # type: ignore[arg-type]
        )
        assert cs.infiltration_resistance == pytest.approx(0.339, abs=1e-3)

    def test_zero_boundary(self) -> None:
        """CI=0, cohesion=0 → resistance=0."""
        from babylon.models.entities.community import CommunityConsciousness

        cs = CommunityState(
            community_type=CommunityType.ADULT,
            cohesion=0.0,  # type: ignore[arg-type]
            consciousness=CommunityConsciousness(collective_identity=0.0),  # type: ignore[arg-type]
        )
        assert cs.infiltration_resistance == pytest.approx(0.0, abs=1e-6)

    def test_max_boundary(self) -> None:
        """CI=1, cohesion=1 → resistance=1."""
        from babylon.models.entities.community import CommunityConsciousness

        cs = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            cohesion=1.0,  # type: ignore[arg-type]
            consciousness=CommunityConsciousness(collective_identity=1.0),  # type: ignore[arg-type]
        )
        assert cs.infiltration_resistance == pytest.approx(1.0, abs=1e-6)


@pytest.mark.unit
class TestEffectiveInfiltrationCeiling:
    """Validate effective_infiltration_ceiling function (Feature 029, US4)."""

    def test_empty_list_returns_base(self) -> None:
        """No community states → base ceiling unchanged."""
        from babylon.models.entities.community import effective_infiltration_ceiling

        assert effective_infiltration_ceiling(0.8, []) == pytest.approx(0.8, abs=1e-6)

    def test_high_resistance_reduces_ceiling(self) -> None:
        """High resistance community significantly reduces ceiling."""
        from babylon.models.entities.community import (
            CommunityConsciousness,
            effective_infiltration_ceiling,
        )

        # Create a community with resistance ≈ 0.852
        cs = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            cohesion=0.8,  # type: ignore[arg-type]
            consciousness=CommunityConsciousness(collective_identity=0.9),  # type: ignore[arg-type]
        )
        result = effective_infiltration_ceiling(0.8, [cs])
        # 0.8 * (1.0 - 0.852 * 0.7) ≈ 0.8 * 0.4036 ≈ 0.3229
        assert result == pytest.approx(0.323, abs=0.01)

    def test_max_resistance_ceiling(self) -> None:
        """Max resistance (1.0) drops ceiling to 30% of base."""
        from babylon.models.entities.community import (
            CommunityConsciousness,
            effective_infiltration_ceiling,
        )

        cs = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            cohesion=1.0,  # type: ignore[arg-type]
            consciousness=CommunityConsciousness(collective_identity=1.0),  # type: ignore[arg-type]
        )
        result = effective_infiltration_ceiling(0.8, [cs])
        # 0.8 * (1.0 - 1.0 * 0.7) = 0.8 * 0.3 = 0.24
        assert result == pytest.approx(0.24, abs=1e-6)

    def test_uses_max_resistance(self) -> None:
        """Multiple communities → uses the max resistance."""
        from babylon.models.entities.community import (
            CommunityConsciousness,
            effective_infiltration_ceiling,
        )

        cs_low = CommunityState(
            community_type=CommunityType.SETTLER,
            cohesion=0.2,  # type: ignore[arg-type]
            consciousness=CommunityConsciousness(collective_identity=0.1),  # type: ignore[arg-type]
        )
        cs_high = CommunityState(
            community_type=CommunityType.INCARCERATED,
            cohesion=0.8,  # type: ignore[arg-type]
            consciousness=CommunityConsciousness(collective_identity=0.9),  # type: ignore[arg-type]
        )
        result = effective_infiltration_ceiling(0.8, [cs_low, cs_high])
        # Should use max resistance (≈0.852), not average
        expected = 0.8 * (1.0 - 0.852 * 0.7)
        assert result == pytest.approx(expected, abs=0.01)


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
