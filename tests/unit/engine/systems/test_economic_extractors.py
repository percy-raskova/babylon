"""Tests for helper extractors in the economic systems.

Task 3: Unit tests for _get_class_consciousness_from_node (20% -> 90%)

This tests the internal helper function that extracts class consciousness
from graph node data in various formats (dict, IdeologicalProfile, etc.).
"""

from typing import Any

import pytest

from babylon.engine.systems.economic import _get_class_consciousness_from_node


@pytest.mark.unit
class TestGetClassConsciousnessFromNode:
    """Test the _get_class_consciousness_from_node helper function.

    This function extracts class_consciousness from graph node data,
    handling various data formats:
    - Missing ideology key: returns 0.0
    - ideology = None: returns 0.0
    - ideology = dict with class_consciousness: returns the value
    - ideology = dict missing class_consciousness: returns 0.0
    - ideology = non-dict value: returns 0.0
    """

    def test_none_ideology_returns_zero(self) -> None:
        """Empty node_data (no ideology key) should return 0.0.

        Workers without ideology attributes are treated as neutral.
        """
        node_data: dict[str, Any] = {}

        result = _get_class_consciousness_from_node(node_data)

        assert result == 0.0

    def test_none_value_returns_zero(self) -> None:
        """Explicitly None ideology should return 0.0.

        Node data can have ideology=None after initialization.
        """
        node_data: dict[str, Any] = {"ideology": None}

        result = _get_class_consciousness_from_node(node_data)

        assert result == 0.0

    def test_dict_with_class_consciousness(self) -> None:
        """Dict ideology with class_consciousness key returns the value.

        This is the standard IdeologicalProfile format.
        """
        node_data: dict[str, Any] = {
            "ideology": {
                "class_consciousness": 0.7,
                "national_identity": 0.3,
                "agitation": 0.0,
            }
        }

        result = _get_class_consciousness_from_node(node_data)

        assert result == pytest.approx(0.7, abs=0.001)

    def test_dict_missing_key_returns_zero(self) -> None:
        """Dict ideology without class_consciousness key returns 0.0.

        Handles malformed ideology data gracefully.
        """
        node_data: dict[str, Any] = {
            "ideology": {
                "national_identity": 0.8,
                "agitation": 0.2,
            }
        }

        result = _get_class_consciousness_from_node(node_data)

        assert result == 0.0

    def test_non_dict_ideology_returns_zero(self) -> None:
        """Non-dict ideology value returns 0.0.

        Legacy data might have ideology as a simple float.
        The function should handle this gracefully.
        """
        node_data: dict[str, Any] = {"ideology": 0.5}

        result = _get_class_consciousness_from_node(node_data)

        assert result == 0.0

    def test_boundary_zero(self) -> None:
        """Class consciousness of 0.0 is returned correctly.

        Boundary test for minimum valid consciousness value.
        """
        node_data: dict[str, Any] = {
            "ideology": {
                "class_consciousness": 0.0,
            }
        }

        result = _get_class_consciousness_from_node(node_data)

        assert result == 0.0

    def test_boundary_one(self) -> None:
        """Class consciousness of 1.0 is returned correctly.

        Boundary test for maximum valid consciousness value.
        """
        node_data: dict[str, Any] = {
            "ideology": {
                "class_consciousness": 1.0,
            }
        }

        result = _get_class_consciousness_from_node(node_data)

        assert result == pytest.approx(1.0, abs=0.001)

    def test_integer_class_consciousness_converted_to_float(self) -> None:
        """Integer class_consciousness values are converted to float.

        The return type should always be float.
        """
        node_data: dict[str, Any] = {
            "ideology": {
                "class_consciousness": 1,  # Integer, not float
            }
        }

        result = _get_class_consciousness_from_node(node_data)

        assert result == pytest.approx(1.0, abs=0.001)
        assert isinstance(result, float)

    def test_string_ideology_returns_zero(self) -> None:
        """String ideology value returns 0.0.

        Edge case: ideology stored as a string reference.
        """
        node_data: dict[str, Any] = {"ideology": "revolutionary"}

        result = _get_class_consciousness_from_node(node_data)

        assert result == 0.0

    def test_list_ideology_returns_zero(self) -> None:
        """List ideology value returns 0.0.

        Edge case: ideology stored as a list.
        """
        node_data: dict[str, Any] = {"ideology": [0.5, 0.3, 0.2]}

        result = _get_class_consciousness_from_node(node_data)

        assert result == 0.0

    def test_nested_dict_without_class_consciousness(self) -> None:
        """Nested dict without the correct key returns 0.0."""
        node_data: dict[str, Any] = {
            "ideology": {
                "beliefs": {
                    "class_consciousness": 0.9,  # Nested too deep
                }
            }
        }

        result = _get_class_consciousness_from_node(node_data)

        assert result == 0.0
