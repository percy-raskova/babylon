"""Tests for IntelMethodology and KeyFigure (Feature 031, T010).

Tests IntelMethodology frozen model with 3 presets and KeyFigure entity.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from tests.constants import TestConstants

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
