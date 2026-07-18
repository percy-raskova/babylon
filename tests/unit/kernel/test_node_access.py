"""Unit tests for ``babylon.kernel.node_access`` graph-payload accessors.

``class_consciousness_from_node`` consolidates four identical readers
(spec-116 Phase 3): three ``_get_class_consciousness_from_node`` copies
(SolidaritySystem, StruggleSystem, ImperialRentSystem) plus
EpistemicHorizonSystem's ``_class_consciousness_of``. It reads
``class_consciousness`` from a node's ``ideology`` sub-dict, defaulting to
``0.0`` for any missing/malformed shape. (Coverage relocated here from the
former ``tests/.../test_economic_extractors.py`` — the test travels with the
code it pins.)
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.kernel.node_access import class_consciousness_from_node


class TestClassConsciousnessFromNode:
    """Read class_consciousness from a graph node's ideology payload."""

    def test_missing_ideology_returns_zero(self) -> None:
        """Empty node_data (no ideology key) -> 0.0 (neutral)."""
        assert class_consciousness_from_node({}) == 0.0

    def test_none_ideology_returns_zero(self) -> None:
        """Explicit ideology=None (post-init state) -> 0.0."""
        assert class_consciousness_from_node({"ideology": None}) == 0.0

    def test_dict_with_class_consciousness(self) -> None:
        """Standard IdeologicalProfile dict returns the value."""
        node_data: dict[str, Any] = {
            "ideology": {"class_consciousness": 0.7, "national_identity": 0.3, "agitation": 0.0}
        }
        assert class_consciousness_from_node(node_data) == pytest.approx(0.7, abs=0.001)

    def test_dict_missing_key_returns_zero(self) -> None:
        """Dict ideology without the key returns 0.0 (malformed-graceful)."""
        node_data: dict[str, Any] = {"ideology": {"national_identity": 0.8, "agitation": 0.2}}
        assert class_consciousness_from_node(node_data) == 0.0

    def test_non_dict_ideology_returns_zero(self) -> None:
        """Legacy float ideology -> 0.0."""
        assert class_consciousness_from_node({"ideology": 0.5}) == 0.0

    def test_boundary_zero(self) -> None:
        assert class_consciousness_from_node({"ideology": {"class_consciousness": 0.0}}) == 0.0

    def test_boundary_one(self) -> None:
        result = class_consciousness_from_node({"ideology": {"class_consciousness": 1.0}})
        assert result == pytest.approx(1.0, abs=0.001)

    def test_integer_class_consciousness_converted_to_float(self) -> None:
        """Integer values are coerced to float; return type is always float."""
        result = class_consciousness_from_node({"ideology": {"class_consciousness": 1}})
        assert result == pytest.approx(1.0, abs=0.001)
        assert isinstance(result, float)

    def test_string_ideology_returns_zero(self) -> None:
        assert class_consciousness_from_node({"ideology": "revolutionary"}) == 0.0

    def test_list_ideology_returns_zero(self) -> None:
        assert class_consciousness_from_node({"ideology": [0.5, 0.3, 0.2]}) == 0.0

    def test_nested_dict_without_class_consciousness(self) -> None:
        node_data: dict[str, Any] = {"ideology": {"beliefs": {"class_consciousness": 0.9}}}
        assert class_consciousness_from_node(node_data) == 0.0
