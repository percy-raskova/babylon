"""Tests for CommunityState.education_pressure field (Spec 043, Phase 1).

TDD Red Phase: These tests verify that CommunityState has an
education_pressure field that accumulates EDUCATE verb effects and
decays per tick. This field is the bridge between player action
(EDUCATE verb) and community-level consciousness routing.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.community import CommunityState
from babylon.models.enums import CommunityType


@pytest.mark.unit
class TestEducationPressureField:
    """Verify education_pressure field on CommunityState."""

    def test_default_education_pressure_is_zero(self) -> None:
        """New communities start with zero education pressure."""
        state = CommunityState(community_type=CommunityType.NEW_AFRIKAN)
        assert state.education_pressure == pytest.approx(0.0)

    def test_custom_education_pressure(self) -> None:
        """education_pressure can be set at construction."""
        state = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            education_pressure=0.35,
        )
        assert state.education_pressure == pytest.approx(0.35)

    def test_education_pressure_nonnegative(self) -> None:
        """education_pressure >= 0.0."""
        with pytest.raises(ValidationError):
            CommunityState(
                community_type=CommunityType.SETTLER,
                education_pressure=-0.1,
            )

    def test_education_pressure_survives_model_copy(self) -> None:
        """education_pressure persists through model_copy update."""
        original = CommunityState(
            community_type=CommunityType.INCARCERATED,
            education_pressure=0.5,
        )
        updated = original.model_copy(update={"education_pressure": 0.7})
        assert updated.education_pressure == pytest.approx(0.7)
        assert original.education_pressure == pytest.approx(0.5)

    def test_education_pressure_unaffected_by_other_updates(self) -> None:
        """Updating other fields does not reset education_pressure."""
        state = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            education_pressure=0.4,
        )
        updated = state.model_copy(update={"heat": 0.8})
        assert updated.education_pressure == pytest.approx(0.4)
