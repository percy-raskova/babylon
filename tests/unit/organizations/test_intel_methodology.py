"""Tests for IntelMethodology and KeyFigure (Feature 031, T010/T023).

Tests IntelMethodology frozen model with 3 presets (default + defines-driven)
and KeyFigure entity.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from tests.constants import TestConstants

from babylon.config.defines import OrganizationDefines
from babylon.models.entities.organization import IntelMethodology, KeyFigure

TC = TestConstants


class TestIntelMethodologyCreation:
    """IntelMethodology frozen model with capability flags and ceiling."""

    @pytest.mark.math
    def test_create_defaults(self) -> None:
        im = IntelMethodology()
        assert im.centrality_analysis is False
        assert im.equivalence_analysis is False
        assert im.template_matching is False
        assert im.temporal_analysis is False
        assert im.observation_ceiling == pytest.approx(TC.Organization.CEILING_LOCAL_PD)

    @pytest.mark.math
    def test_create_custom(self) -> None:
        im = IntelMethodology(
            centrality_analysis=True,
            equivalence_analysis=True,
            template_matching=True,
            temporal_analysis=True,
            observation_ceiling=0.5,
        )
        assert im.centrality_analysis is True
        assert im.observation_ceiling == pytest.approx(0.5)

    @pytest.mark.math
    def test_rejects_negative_ceiling(self) -> None:
        with pytest.raises(ValidationError):
            IntelMethodology(observation_ceiling=-0.1)

    @pytest.mark.math
    def test_rejects_ceiling_above_one(self) -> None:
        with pytest.raises(ValidationError):
            IntelMethodology(observation_ceiling=1.1)

    @pytest.mark.math
    def test_frozen(self) -> None:
        im = IntelMethodology()
        with pytest.raises(ValidationError):
            im.centrality_analysis = True  # type: ignore[misc]


class TestIntelMethodologyPresets:
    """Three preset configurations from Sparrow calibration."""

    @pytest.mark.math
    def test_local_pd_preset(self) -> None:
        im = IntelMethodology.local_pd()
        assert im.centrality_analysis is True
        assert im.equivalence_analysis is False
        assert im.template_matching is False
        assert im.temporal_analysis is False
        assert im.observation_ceiling == pytest.approx(TC.Organization.CEILING_LOCAL_PD)

    @pytest.mark.math
    def test_fusion_center_preset(self) -> None:
        im = IntelMethodology.fusion_center()
        assert im.centrality_analysis is True
        assert im.equivalence_analysis is False
        assert im.template_matching is False
        assert im.temporal_analysis is True
        assert im.observation_ceiling == pytest.approx(TC.Organization.CEILING_FUSION)

    @pytest.mark.math
    def test_fbi_preset(self) -> None:
        im = IntelMethodology.fbi()
        assert im.centrality_analysis is True
        assert im.equivalence_analysis is True
        assert im.template_matching is True
        assert im.temporal_analysis is True
        assert im.observation_ceiling == pytest.approx(TC.Organization.CEILING_FBI)


class TestIntelMethodologyDefinesDriven:
    """T023: Presets read ceiling values from OrganizationDefines, not hardcoded."""

    @pytest.mark.math
    def test_local_pd_uses_defines_ceiling(self) -> None:
        """local_pd() uses defines.observation_ceiling_local_pd."""
        custom = OrganizationDefines(observation_ceiling_local_pd=0.35)
        im = IntelMethodology.local_pd(defines=custom)
        assert im.observation_ceiling == pytest.approx(0.35)

    @pytest.mark.math
    def test_fusion_uses_defines_ceiling(self) -> None:
        """fusion_center() uses defines.observation_ceiling_fusion."""
        custom = OrganizationDefines(observation_ceiling_fusion=0.65)
        im = IntelMethodology.fusion_center(defines=custom)
        assert im.observation_ceiling == pytest.approx(0.65)

    @pytest.mark.math
    def test_fbi_uses_defines_ceiling(self) -> None:
        """fbi() uses defines.observation_ceiling_fbi."""
        custom = OrganizationDefines(observation_ceiling_fbi=0.55)
        im = IntelMethodology.fbi(defines=custom)
        assert im.observation_ceiling == pytest.approx(0.55)

    @pytest.mark.math
    def test_default_defines_match_hardcoded_defaults(self) -> None:
        """Default OrganizationDefines produce same result as no-arg presets."""
        defaults = OrganizationDefines()
        assert IntelMethodology.local_pd().observation_ceiling == pytest.approx(
            IntelMethodology.local_pd(defines=defaults).observation_ceiling
        )
        assert IntelMethodology.fusion_center().observation_ceiling == pytest.approx(
            IntelMethodology.fusion_center(defines=defaults).observation_ceiling
        )
        assert IntelMethodology.fbi().observation_ceiling == pytest.approx(
            IntelMethodology.fbi(defines=defaults).observation_ceiling
        )


class TestIntelMethodologyTierDifferentiation:
    """T023: Three tiers are observably different."""

    @pytest.mark.math
    def test_tiers_have_different_ceilings(self) -> None:
        """Each tier has a distinct observation ceiling."""
        pd = IntelMethodology.local_pd()
        fusion = IntelMethodology.fusion_center()
        fbi = IntelMethodology.fbi()
        ceilings = {pd.observation_ceiling, fusion.observation_ceiling, fbi.observation_ceiling}
        assert len(ceilings) == 3

    @pytest.mark.math
    def test_tiers_have_different_capability_sets(self) -> None:
        """Each tier has a distinct combination of boolean capabilities."""
        pd = IntelMethodology.local_pd()
        fusion = IntelMethodology.fusion_center()
        fbi = IntelMethodology.fbi()

        pd_caps = (
            pd.centrality_analysis,
            pd.equivalence_analysis,
            pd.template_matching,
            pd.temporal_analysis,
        )
        fusion_caps = (
            fusion.centrality_analysis,
            fusion.equivalence_analysis,
            fusion.template_matching,
            fusion.temporal_analysis,
        )
        fbi_caps = (
            fbi.centrality_analysis,
            fbi.equivalence_analysis,
            fbi.template_matching,
            fbi.temporal_analysis,
        )
        assert pd_caps != fusion_caps
        assert fusion_caps != fbi_caps
        assert pd_caps != fbi_caps

    @pytest.mark.math
    def test_capability_count_increases_with_tier(self) -> None:
        """Higher tiers have strictly more capabilities enabled."""
        pd = IntelMethodology.local_pd()
        fusion = IntelMethodology.fusion_center()
        fbi = IntelMethodology.fbi()

        pd_count = sum(
            [
                pd.centrality_analysis,
                pd.equivalence_analysis,
                pd.template_matching,
                pd.temporal_analysis,
            ]
        )
        fusion_count = sum(
            [
                fusion.centrality_analysis,
                fusion.equivalence_analysis,
                fusion.template_matching,
                fusion.temporal_analysis,
            ]
        )
        fbi_count = sum(
            [
                fbi.centrality_analysis,
                fbi.equivalence_analysis,
                fbi.template_matching,
                fbi.temporal_analysis,
            ]
        )
        assert pd_count < fusion_count < fbi_count


class TestKeyFigureCreation:
    """KeyFigure entity with 6 fields."""

    @pytest.mark.math
    def test_create_minimal(self) -> None:
        kf = KeyFigure(
            id="kf-001",
            name="John Smith",
            organization_id="org-001",
            role="Chairman",
        )
        assert kf.id == "kf-001"
        assert kf.name == "John Smith"
        assert kf.organization_id == "org-001"
        assert kf.role == "Chairman"

    @pytest.mark.math
    def test_default_structural_importance(self) -> None:
        kf = KeyFigure(
            id="kf-001",
            name="John Smith",
            organization_id="org-001",
            role="Chairman",
        )
        assert kf.structural_importance == pytest.approx(0.5)

    @pytest.mark.math
    def test_default_is_singleton(self) -> None:
        kf = KeyFigure(
            id="kf-001",
            name="John Smith",
            organization_id="org-001",
            role="Chairman",
        )
        assert kf.is_singleton is False

    @pytest.mark.math
    def test_rejects_empty_id(self) -> None:
        with pytest.raises(ValidationError):
            KeyFigure(
                id="",
                name="John Smith",
                organization_id="org-001",
                role="Chairman",
            )

    @pytest.mark.math
    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            KeyFigure(
                id="kf-001",
                name="",
                organization_id="org-001",
                role="Chairman",
            )

    @pytest.mark.math
    def test_rejects_empty_role(self) -> None:
        with pytest.raises(ValidationError):
            KeyFigure(
                id="kf-001",
                name="John Smith",
                organization_id="org-001",
                role="",
            )

    @pytest.mark.math
    def test_rejects_negative_structural_importance(self) -> None:
        with pytest.raises(ValidationError):
            KeyFigure(
                id="kf-001",
                name="John Smith",
                organization_id="org-001",
                role="Chairman",
                structural_importance=-0.1,
            )

    @pytest.mark.math
    def test_frozen(self) -> None:
        kf = KeyFigure(
            id="kf-001",
            name="John Smith",
            organization_id="org-001",
            role="Chairman",
        )
        with pytest.raises(ValidationError):
            kf.role = "Vice Chairman"  # type: ignore[misc]

    @pytest.mark.ledger
    def test_serialization_round_trip(self) -> None:
        kf = KeyFigure(
            id="kf-001",
            name="John Smith",
            organization_id="org-001",
            role="Chairman",
            structural_importance=0.8,
            is_singleton=True,
        )
        json_str = kf.model_dump_json()
        restored = KeyFigure.model_validate_json(json_str)
        assert restored.id == kf.id
        assert restored.structural_importance == pytest.approx(kf.structural_importance)
        assert restored.is_singleton is True
