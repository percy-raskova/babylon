"""Unit tests for hexagon visualization isolation from database layer.

Feature: 011-fundamental-tensor-primitive
Implements: T046 from tasks.md

These tests verify that hexagon visualization components:
1. Do not import database modules
2. Can operate with TensorRegistry as their only data source
3. Handle missing data gracefully via NoDataSentinel
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from babylon.economics.tensor import DepartmentRow, NoDataSentinel, ValueTensor4x3
from babylon.ui.dashboard.tensor_consumer import (
    TensorConsumer,
    TensorConsumerMixin,
    TensorPrimitive,
)

if TYPE_CHECKING:
    pass


class TestTensorConsumerMixin:
    """Test TensorConsumerMixin functionality."""

    def test_mixin_initializes_without_source(self) -> None:
        """TensorConsumerMixin starts with no tensor source."""
        mixin = TensorConsumerMixin()
        assert mixin._tensor_source is None
        assert not mixin.has_tensor_source

    def test_set_tensor_source(self) -> None:
        """set_tensor_source() accepts a TensorPrimitive."""
        mixin = TensorConsumerMixin()

        # Create a mock tensor source
        class MockTensorSource:
            def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel:
                return NoDataSentinel(fips, year, "mock")

        source = MockTensorSource()
        mixin.set_tensor_source(source)

        assert mixin._tensor_source is source
        assert mixin.has_tensor_source

    def test_set_tensor_source_none_clears(self) -> None:
        """set_tensor_source(None) clears the source."""
        mixin = TensorConsumerMixin()

        # Set and then clear
        class MockTensorSource:
            def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel:
                return NoDataSentinel(fips, year, "mock")

        mixin.set_tensor_source(MockTensorSource())
        assert mixin.has_tensor_source

        mixin.set_tensor_source(None)  # type: ignore[arg-type]
        assert not mixin.has_tensor_source

    def test_get_tensor_returns_none_without_source(self) -> None:
        """get_tensor() returns None when no source is set."""
        mixin = TensorConsumerMixin()
        result = mixin.get_tensor("26163", 2022)
        assert result is None

    def test_get_tensor_returns_none_for_none_year(self) -> None:
        """get_tensor() returns None when year is None."""
        mixin = TensorConsumerMixin()

        class MockTensorSource:
            def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel:
                return NoDataSentinel(fips, year, "mock")

        mixin.set_tensor_source(MockTensorSource())
        result = mixin.get_tensor("26163", None)
        assert result is None

    def test_get_tensor_delegates_to_source(self) -> None:
        """get_tensor() delegates to the tensor source."""
        mixin = TensorConsumerMixin()

        expected_tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=100.0, v=50.0, s=50.0),
            dept_IIa=DepartmentRow(c=80.0, v=40.0, s=40.0),
            dept_IIb=DepartmentRow(c=60.0, v=30.0, s=90.0),
            dept_III=DepartmentRow(c=20.0, v=20.0, s=10.0),
            naics_granularity=0.85,
            excluded_wages=1000.0,
        )

        class MockTensorSource:
            def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel:
                if fips == "26163" and year == 2022:
                    return expected_tensor
                return NoDataSentinel(fips, year, "not found")

        mixin.set_tensor_source(MockTensorSource())
        result = mixin.get_tensor("26163", 2022)

        assert result is expected_tensor

    def test_get_tensor_returns_sentinel_for_missing_data(self) -> None:
        """get_tensor() returns NoDataSentinel for missing data."""
        mixin = TensorConsumerMixin()

        class MockTensorSource:
            def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel:
                return NoDataSentinel(fips, year, "No data available")

        mixin.set_tensor_source(MockTensorSource())
        result = mixin.get_tensor("99999", 2022)

        assert isinstance(result, NoDataSentinel)
        assert not result  # Falsy
        assert result.fips == "99999"
        assert result.year == 2022


class TestTensorConsumerProtocol:
    """Test TensorConsumer protocol compliance."""

    def test_mixin_implements_protocol(self) -> None:
        """TensorConsumerMixin implements TensorConsumer protocol."""
        mixin = TensorConsumerMixin()
        assert isinstance(mixin, TensorConsumer)

    def test_protocol_requires_set_tensor_source(self) -> None:
        """TensorConsumer protocol requires set_tensor_source method."""
        # Protocol check at runtime
        assert hasattr(TensorConsumer, "set_tensor_source")


class TestTensorPrimitiveProtocol:
    """Test TensorPrimitive protocol compliance."""

    def test_protocol_requires_get(self) -> None:
        """TensorPrimitive protocol requires get method."""
        assert hasattr(TensorPrimitive, "get")

    def test_class_with_get_satisfies_protocol(self) -> None:
        """Class with get() method satisfies TensorPrimitive protocol."""

        class CustomSource:
            def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel:
                return NoDataSentinel(fips, year, "custom")

        source = CustomSource()
        assert isinstance(source, TensorPrimitive)


class TestUIModuleIsolation:
    """Test that UI modules don't import database modules.

    This is a static analysis test that verifies architectural constraints.
    """

    # Prohibited imports that would violate isolation
    PROHIBITED_IMPORTS = frozenset(
        {
            "babylon.data",
            "babylon.data.reference",
            "babylon.data.reference.database",
            "babylon.data.reference.hydrator",
            "babylon.data.reference.schema",
            "sqlalchemy",
            "sqlalchemy.orm",
            "sqlalchemy.engine",
            "sqlite3",
        }
    )

    def _check_file_imports(self, file_path: Path) -> list[str]:
        """Check a file for prohibited imports.

        Args:
            file_path: Path to Python file.

        Returns:
            List of prohibited import names found.
        """
        try:
            source = file_path.read_text()
            tree = ast.parse(source)
        except (SyntaxError, OSError):
            return []

        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if self._is_prohibited(alias.name):
                        violations.append(alias.name)
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and self._is_prohibited(node.module)
            ):
                violations.append(node.module)

        return violations

    def _is_prohibited(self, module_name: str) -> bool:
        """Check if module name matches prohibited patterns."""
        if module_name in self.PROHIBITED_IMPORTS:
            return True
        for prohibited in self.PROHIBITED_IMPORTS:
            if module_name.startswith(prohibited + "."):
                return True
        return False

    def test_tensor_consumer_module_isolation(self) -> None:
        """tensor_consumer.py should not import database modules."""
        module_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "babylon"
            / "ui"
            / "dashboard"
            / "tensor_consumer.py"
        )
        if not module_path.exists():
            pytest.skip(f"Module not found: {module_path}")

        violations = self._check_file_imports(module_path)
        assert not violations, f"tensor_consumer.py has prohibited imports: {violations}"

    def test_map_viewport_module_isolation(self) -> None:
        """map_viewport.py should not import database modules."""
        module_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "babylon"
            / "ui"
            / "dashboard"
            / "map_viewport.py"
        )
        if not module_path.exists():
            pytest.skip(f"Module not found: {module_path}")

        violations = self._check_file_imports(module_path)
        assert not violations, f"map_viewport.py has prohibited imports: {violations}"

    def test_hex_bridge_module_isolation(self) -> None:
        """hex_bridge.py should not import database modules."""
        module_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "babylon"
            / "ui"
            / "dashboard"
            / "hex_bridge.py"
        )
        if not module_path.exists():
            pytest.skip(f"Module not found: {module_path}")

        violations = self._check_file_imports(module_path)
        assert not violations, f"hex_bridge.py has prohibited imports: {violations}"

    def test_inspector_panel_module_isolation(self) -> None:
        """inspector_panel.py should not import database modules."""
        module_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "babylon"
            / "ui"
            / "dashboard"
            / "inspector_panel.py"
        )
        if not module_path.exists():
            pytest.skip(f"Module not found: {module_path}")

        violations = self._check_file_imports(module_path)
        assert not violations, f"inspector_panel.py has prohibited imports: {violations}"


class TestNoDataSentinelUsage:
    """Test proper NoDataSentinel handling in consumer patterns."""

    def test_sentinel_is_falsy(self) -> None:
        """NoDataSentinel is falsy for walrus operator patterns."""
        sentinel = NoDataSentinel("26163", 2022, "test reason")
        assert not sentinel
        assert bool(sentinel) is False

    def test_tensor_is_truthy(self) -> None:
        """ValueTensor4x3 is truthy."""
        tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=100.0, v=50.0, s=50.0),
            dept_IIa=DepartmentRow(c=80.0, v=40.0, s=40.0),
            dept_IIb=DepartmentRow(c=60.0, v=30.0, s=90.0),
            dept_III=DepartmentRow(c=20.0, v=20.0, s=10.0),
            naics_granularity=0.85,
            excluded_wages=1000.0,
        )
        assert tensor
        assert bool(tensor) is True

    def test_walrus_operator_pattern(self) -> None:
        """Demonstrate correct walrus operator usage pattern."""
        mixin = TensorConsumerMixin()

        class MockTensorSource:
            def __init__(self) -> None:
                self._data: dict[tuple[str, int], ValueTensor4x3] = {
                    ("26163", 2022): ValueTensor4x3(
                        fips_code="26163",
                        year=2022,
                        dept_I=DepartmentRow(c=100.0, v=50.0, s=50.0),
                        dept_IIa=DepartmentRow(c=80.0, v=40.0, s=40.0),
                        dept_IIb=DepartmentRow(c=60.0, v=30.0, s=90.0),
                        dept_III=DepartmentRow(c=20.0, v=20.0, s=10.0),
                        naics_granularity=0.85,
                        excluded_wages=1000.0,
                    )
                }

            def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel:
                if (fips, year) in self._data:
                    return self._data[(fips, year)]
                return NoDataSentinel(fips, year, "Not found")

        mixin.set_tensor_source(MockTensorSource())

        # Pattern 1: Existing data
        if tensor := mixin.get_tensor("26163", 2022):
            # This branch executes because tensor is truthy
            assert tensor.profit_rate > 0
        else:
            pytest.fail("Should have found tensor data")

        # Pattern 2: Missing data
        result = mixin.get_tensor("99999", 2022)
        if result:
            pytest.fail("Should not have found tensor data")
        else:
            # This branch executes because sentinel is falsy
            assert isinstance(result, NoDataSentinel)
            assert result.reason == "Not found"
