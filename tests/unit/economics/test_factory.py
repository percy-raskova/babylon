"""Unit tests for the economics calculator factory function.

Feature: 020-detroit-vertical-slice
Task: T006

Tests that create_economics_services() returns a properly wired dict
of calculator instances suitable for injection into ServiceContainer.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from babylon.economics.factory import create_economics_services
from babylon.economics.tensor_registry import TensorRegistry

# Expected keys that must be present in the factory output
_EXPECTED_KEYS = frozenset(
    {
        "melt_calculator",
        "basket_calculator",
        "gamma_calculator",
        "capital_calculator",
        "throughput_calculator",
        "transition_engine",
        "imperial_rent_calculator",
        "tensor_registry",
    }
)


class TestCreateEconomicsServices:
    """Test create_economics_services factory function."""

    def test_returns_dict_with_expected_keys(self) -> None:
        """Factory returns dict with exactly the 8 expected keys."""
        mock_session_factory = MagicMock()
        tensor_registry = TensorRegistry()

        result = create_economics_services(mock_session_factory, tensor_registry)

        assert isinstance(result, dict)
        assert set(result.keys()) == _EXPECTED_KEYS

    def test_all_values_non_none(self) -> None:
        """Every value in the factory output is non-None."""
        mock_session_factory = MagicMock()
        tensor_registry = TensorRegistry()

        result = create_economics_services(mock_session_factory, tensor_registry)

        for key, value in result.items():
            assert value is not None, f"Expected non-None value for key '{key}'"

    def test_tensor_registry_is_passed_through(self) -> None:
        """The tensor_registry value is the same object passed in."""
        mock_session_factory = MagicMock()
        tensor_registry = TensorRegistry()

        result = create_economics_services(mock_session_factory, tensor_registry)

        assert result["tensor_registry"] is tensor_registry

    def test_result_unpacks_into_service_container(self) -> None:
        """Factory output can be unpacked as kwargs into ServiceContainer.create()."""
        from babylon.engine.services import ServiceContainer

        mock_session_factory = MagicMock()
        tensor_registry = TensorRegistry()

        overrides = create_economics_services(mock_session_factory, tensor_registry)
        container = ServiceContainer.create(**overrides)

        assert container.melt_calculator is not None
        assert container.tensor_registry is tensor_registry

    def test_key_count_is_exactly_eight(self) -> None:
        """Factory returns exactly 8 keys (no extra, no missing)."""
        mock_session_factory = MagicMock()
        tensor_registry = TensorRegistry()

        result = create_economics_services(mock_session_factory, tensor_registry)

        assert len(result) == 8
