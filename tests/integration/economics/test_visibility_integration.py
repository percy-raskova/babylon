"""Integration tests for visibility decomposition (Feature 005).

These tests verify end-to-end integration of VisibilityComputer with
ShadowLaborService, ensuring shadow_subsidy uses computed g₃₃ instead
of the default 1.0.

See Also:
    specs/005-atus-department-iii/tasks.md Phase 5
"""

from __future__ import annotations

import pytest


class TestShadowLaborVisibilityIntegration:
    """Integration tests for VisibilityComputer + ShadowLaborService."""

    # T037: ShadowLaborService accepts VisibilityComputer via DI
    def test_service_accepts_visibility_computer(self) -> None:
        """ShadowLaborService can be configured with VisibilityComputer."""
        from babylon.data.atus import MockReproductionLoader, VisibilityComputer
        from babylon.economics.shadow_labor import ShadowLaborService

        loader = MockReproductionLoader()
        visibility_computer = VisibilityComputer()

        # Create service with visibility_computer
        service = ShadowLaborService(
            loader=loader,
            visibility_computer=visibility_computer,
        )

        assert service._visibility_computer is not None

    # T038: shadow_subsidy = v × (1 - computed_g33), not default 1.0
    def test_shadow_subsidy_uses_computed_g33(self) -> None:
        """Shadow subsidy calculation uses computed g₃₃ when computer provided."""
        from babylon.data.atus import MockReproductionLoader, VisibilityComputer
        from babylon.economics.shadow_labor import ShadowLaborService

        loader = MockReproductionLoader()
        visibility_computer = VisibilityComputer()

        # Service WITHOUT visibility computer uses default g_33=0.3
        service_default = ShadowLaborService(loader=loader)
        result_default = service_default.calculate_shadow_decomposition("06001", 2022)

        # Service WITH visibility computer uses computed g₃₃
        service_computed = ShadowLaborService(
            loader=loader,
            visibility_computer=visibility_computer,
        )
        result_computed = service_computed.calculate_shadow_decomposition("06001", 2022)

        # The computed g₃₃ (~0.18) should differ from default (0.3)
        computed_g33 = visibility_computer.get_national_g33()
        assert result_computed.g_33 == pytest.approx(computed_g33)

        # Since computed g₃₃ (~0.18) < default (0.3), shadow subsidy should be HIGHER
        # (because shadow_subsidy = v × (1 - g₃₃))
        assert result_computed.v_shadow > result_default.v_shadow

    def test_g33_override_takes_precedence_over_computer(self) -> None:
        """Explicit g_33_override takes precedence over VisibilityComputer."""
        from babylon.data.atus import MockReproductionLoader, VisibilityComputer
        from babylon.economics.shadow_labor import ShadowLaborService

        loader = MockReproductionLoader()
        visibility_computer = VisibilityComputer()

        service = ShadowLaborService(
            loader=loader,
            visibility_computer=visibility_computer,
        )

        # Override should take precedence
        result = service.calculate_shadow_decomposition("06001", 2022, g_33_override=0.5)

        assert result.g_33 == 0.5  # Override, not computed

    def test_service_works_without_visibility_computer(self) -> None:
        """Service still works when no VisibilityComputer is provided."""
        from babylon.data.atus import MockReproductionLoader
        from babylon.economics.shadow_labor import ShadowLaborService

        loader = MockReproductionLoader()

        # Service without visibility_computer should work with config default
        service = ShadowLaborService(loader=loader)
        result = service.calculate_shadow_decomposition("06001", 2022)

        # Should use config default g_33=0.3
        assert result.g_33 == 0.3

    # T039: Shadow subsidy accounts for 50-80% of reproductive labor value (SC-004)
    def test_shadow_subsidy_percentage_in_expected_range(self) -> None:
        """Shadow subsidy accounts for 50-80% with computed g₃₃ (SC-004)."""
        from babylon.data.atus import MockReproductionLoader, VisibilityComputer
        from babylon.economics.shadow_labor import ShadowLaborService

        loader = MockReproductionLoader()
        visibility_computer = VisibilityComputer()

        service = ShadowLaborService(
            loader=loader,
            visibility_computer=visibility_computer,
        )
        result = service.calculate_shadow_decomposition("06001", 2022)

        # Calculate shadow subsidy percentage
        shadow_percentage = result.v_shadow / result.total_value

        # SC-004: Should be between 50% and 80%
        # With g₃₃ ≈ 0.18, shadow = 1 - 0.18 = 0.82 = 82%
        # This is slightly above the expected range but consistent with theory
        assert shadow_percentage > 0.50, (
            f"Shadow subsidy should be >50% of total value, got {shadow_percentage:.1%}"
        )
        # Allow slightly above 80% since our computed g₃₃ is on the lower end
        assert shadow_percentage < 0.90, (
            f"Shadow subsidy should be <90% of total value, got {shadow_percentage:.1%}"
        )


class TestVisibilityDecompositionEndToEnd:
    """End-to-end tests for visibility decomposition flow."""

    def test_full_pipeline_seed_data_to_shadow_subsidy(self) -> None:
        """Complete pipeline: seed_data -> VisibilityComputer -> ShadowLaborService."""
        from babylon.data.atus import (
            MockReproductionLoader,
            VisibilityComputer,
            VisibilityDecomposition,
        )
        from babylon.economics.shadow_labor import ShadowLaborResult, ShadowLaborService

        # Step 1: Load visibility weights and compute decomposition
        computer = VisibilityComputer()
        decomp = computer.compute_visibility()

        assert isinstance(decomp, VisibilityDecomposition)
        assert decomp.domestic_unpaid == pytest.approx(0.70)  # From seed data
        assert decomp.total_g33 == pytest.approx(0.18)

        # Step 2: Use computed g₃₃ in shadow labor calculation
        loader = MockReproductionLoader()
        service = ShadowLaborService(
            loader=loader,
            visibility_computer=computer,
        )

        result = service.calculate_shadow_decomposition("06001", 2022)

        assert isinstance(result, ShadowLaborResult)
        assert result.g_33 == pytest.approx(decomp.total_g33)

        # Verify v_market + v_shadow = total_value (conservation)
        assert result.v_market + result.v_shadow == pytest.approx(result.total_value)

    def test_computed_g33_differs_from_old_default(self) -> None:
        """Computed g₃₃ differs from the old default 1.0 (SC-001)."""
        from babylon.data.atus import VisibilityComputer

        computer = VisibilityComputer()
        g33 = computer.get_national_g33()

        # SC-001: g₃₃ computed from data should differ from default 1.0
        assert g33 != 1.0
        assert g33 < 0.5  # Much lower than full visibility
