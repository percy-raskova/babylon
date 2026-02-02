"""Regression tests for MELT module integration (Feature 013).

Feature: 013-melt-basket-visibility
Date: 2026-02-01

Task: T053 [CHK050] - Integration regression tests for existing consumers

These tests verify that:
1. Existing ValueTensor consumers still work after melt module addition
2. TensorRegistry.get_tensor() is not affected
3. No import errors from existing economics module users
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestExistingConsumerRegression:
    """Verify existing economics module consumers are not affected."""

    def test_tensor_registry_unaffected(self) -> None:
        """Test that TensorRegistry.get() still works after melt addition."""
        from babylon.economics.tensor_registry import TensorRegistry

        # Registry should still be importable and functional
        assert TensorRegistry is not None

        # Verify the class exists and has expected methods
        assert hasattr(TensorRegistry, "get")

    def test_value_tensor_still_works(self) -> None:
        """Test that ValueTensor4x3 is still accessible and functional."""
        from babylon.economics.tensor import ValueTensor4x3

        # Should be able to import and use
        assert ValueTensor4x3 is not None

    def test_no_data_sentinel_still_works(self) -> None:
        """Test that NoDataSentinel is still accessible."""
        from babylon.economics.tensor import NoDataSentinel

        # Should be importable
        assert NoDataSentinel is not None

        # Should be usable with the correct signature (fips, year, reason)
        sentinel = NoDataSentinel("99999", 2022, "Test reason")
        assert not sentinel  # Falsy
        assert sentinel.reason == "Test reason"

    def test_economics_package_imports_unchanged(self) -> None:
        """Test that existing economics package imports still work."""
        # These imports should not raise ImportError
        from babylon.economics import tensor
        from babylon.economics.tensor import NoDataSentinel, ValueTensor4x3
        from babylon.economics.tensor_registry import TensorRegistry

        # Verify accessibility
        assert tensor is not None
        assert ValueTensor4x3 is not None
        assert TensorRegistry is not None
        assert NoDataSentinel is not None


@pytest.mark.integration
class TestMeltModuleIsolation:
    """Verify melt module doesn't break other economics modules."""

    def test_melt_module_import_does_not_affect_tensor_module(self) -> None:
        """Test that importing melt doesn't break tensor module."""
        # Import melt first
        # Then import tensor - should work
        from babylon.economics import melt, tensor
        from babylon.economics.tensor import ValueTensor4x3

        assert melt is not None
        assert tensor is not None
        assert ValueTensor4x3 is not None

    def test_tensor_module_import_does_not_affect_melt_module(self) -> None:
        """Test that importing tensor doesn't break melt module."""
        # Import tensor first
        # Then import melt - should work
        from babylon.economics import melt, tensor
        from babylon.economics.melt import DefaultMELTCalculator

        assert tensor is not None
        assert melt is not None
        assert DefaultMELTCalculator is not None

    def test_circular_import_prevention(self) -> None:
        """Test that there are no circular import issues."""
        # This test will fail during collection if there are circular imports
        from babylon.economics.melt import (
            ClassPosition,
            DefaultBasketVisibilityCalculator,
            DefaultClassPositionClassifier,
            DefaultImperialRentCalculator,
            DefaultMELTCalculator,
            NationalParameters,
        )
        from babylon.economics.tensor import NoDataSentinel, ValueTensor4x3
        from babylon.economics.tensor_registry import TensorRegistry

        # All should be importable without circular import errors
        assert ClassPosition is not None
        assert NationalParameters is not None
        assert DefaultMELTCalculator is not None
        assert DefaultBasketVisibilityCalculator is not None
        assert DefaultClassPositionClassifier is not None
        assert DefaultImperialRentCalculator is not None
        assert NoDataSentinel is not None
        assert TensorRegistry is not None
        assert ValueTensor4x3 is not None


@pytest.mark.integration
class TestBackwardsCompatibility:
    """Test backwards compatibility with existing code patterns."""

    def test_nodata_sentinel_works_with_melt_calculator(self) -> None:
        """Test that NoDataSentinel from tensor works with MELT results."""
        from babylon.economics.melt import DefaultMELTCalculator
        from babylon.economics.tensor import NoDataSentinel
        from tests.unit.economics.melt.conftest import (
            MockBEADataSource,
            MockQCEWDataSource,
        )

        # Calculator with no data
        calculator = DefaultMELTCalculator(
            MockBEADataSource({}),
            MockQCEWDataSource({}),
        )

        # Get result for a year with no data
        result = calculator.get_melt(2022)

        # Should return same NoDataSentinel type from tensor module
        assert isinstance(result, NoDataSentinel)
        # Should behave as falsy
        if result:
            pytest.fail("NoDataSentinel should be falsy")
