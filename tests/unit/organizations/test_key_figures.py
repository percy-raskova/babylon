"""Tests for organization cohesion loss on member removal (Feature 031, T026).

Tests cohesion_loss_on_removal() for vulnerability analysis.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import OrganizationDefines
from babylon.domain.organizations.topology import cohesion_loss_on_removal


class TestCohesionLossOnRemoval:
    """cohesion_loss_on_removal: reducing cohesion when key figures removed."""

    @pytest.mark.math
    def test_remove_one_key_figure(self) -> None:
        """Removing one key figure drops cohesion by cohesion_loss_per_key_figure."""
        defines = OrganizationDefines()
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.8,
            removed_count=1,
            defines=defines,
        )
        # 0.8 - 0.2 = 0.6
        assert new_cohesion == pytest.approx(0.6)

    @pytest.mark.math
    def test_remove_two_key_figures(self) -> None:
        """Removing two key figures drops cohesion by 2 × loss_per."""
        defines = OrganizationDefines()
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.8,
            removed_count=2,
            defines=defines,
        )
        # 0.8 - 2*0.2 = 0.4
        assert new_cohesion == pytest.approx(0.4)

    @pytest.mark.math
    def test_floor_at_min_threshold(self) -> None:
        """Cohesion never drops below min_cohesion_threshold."""
        defines = OrganizationDefines()
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.3,
            removed_count=5,
            defines=defines,
        )
        # 0.3 - 5*0.2 = -0.7, clamped to 0.05
        assert new_cohesion == pytest.approx(0.05)

    @pytest.mark.math
    def test_remove_all_key_figures_hits_floor(self) -> None:
        """Removing all key figures leaves cohesion at floor."""
        defines = OrganizationDefines()
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.6,
            removed_count=10,
            defines=defines,
        )
        assert new_cohesion == pytest.approx(0.05)

    @pytest.mark.math
    def test_zero_removed(self) -> None:
        """Removing zero key figures = no change."""
        defines = OrganizationDefines()
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.8,
            removed_count=0,
            defines=defines,
        )
        assert new_cohesion == pytest.approx(0.8)

    @pytest.mark.math
    def test_custom_defines(self) -> None:
        """Custom defines override loss and floor values."""
        defines = OrganizationDefines(
            cohesion_loss_per_key_figure=0.1,
            min_cohesion_threshold=0.1,
        )
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.5,
            removed_count=3,
            defines=defines,
        )
        # 0.5 - 3*0.1 = 0.2
        assert new_cohesion == pytest.approx(0.2)
