"""Integration tests for visibility decomposition (Feature 005).

These tests verify end-to-end integration of VisibilityComputer with
ShadowLaborService, ensuring shadow_subsidy uses computed g_33 instead
of the default 1.0.

Note: VisibilityComputer requires the babylon-data package (ATUS seed data).
Tests will be skipped if babylon-data is not installed.

See Also:
    specs/005-atus-department-iii/tasks.md Phase 5
"""

from __future__ import annotations

import pytest

# VisibilityComputer lives in babylon-data; skip entire module if unavailable
pytestmark = pytest.mark.skipif(
    True,  # babylon-data package not yet installable
    reason="VisibilityComputer requires babylon-data package (not yet available)",
)


class TestShadowLaborVisibilityIntegration:
    """Integration tests for VisibilityComputer + ShadowLaborService."""

    def test_service_accepts_visibility_computer(self) -> None:
        """ShadowLaborService can be configured with VisibilityComputer."""
        pytest.skip("Requires babylon-data package")

    def test_shadow_subsidy_uses_computed_g33(self) -> None:
        """Shadow subsidy calculation uses computed g_33 when computer provided."""
        pytest.skip("Requires babylon-data package")

    def test_g33_override_takes_precedence_over_computer(self) -> None:
        """Explicit g_33_override takes precedence over VisibilityComputer."""
        pytest.skip("Requires babylon-data package")

    def test_service_works_without_visibility_computer(self) -> None:
        """Service still works when no VisibilityComputer is provided."""
        from babylon.domain.economics.atus_compat import MockReproductionLoader
        from babylon.domain.economics.shadow_labor import ShadowLaborService

        loader = MockReproductionLoader()
        service = ShadowLaborService(loader=loader)
        result = service.calculate_shadow_decomposition("06001", 2022)
        assert result.g_33 == 0.3

    def test_shadow_subsidy_percentage_in_expected_range(self) -> None:
        """Shadow subsidy accounts for 50-80% with computed g_33 (SC-004)."""
        pytest.skip("Requires babylon-data package")


class TestVisibilityDecompositionEndToEnd:
    """End-to-end tests for visibility decomposition flow."""

    def test_full_pipeline_seed_data_to_shadow_subsidy(self) -> None:
        """Complete pipeline: seed_data -> VisibilityComputer -> ShadowLaborService."""
        pytest.skip("Requires babylon-data package")

    def test_computed_g33_differs_from_old_default(self) -> None:
        """Computed g_33 differs from the old default 1.0 (SC-001)."""
        pytest.skip("Requires babylon-data package")
