"""TDD RED phase: Tests for the DialecticRegistry.

Validates:
- Registration of concrete Dialectic subclasses by type_tag
- Lookup by type_tag returns the correct class
- Unknown type_tag raises KeyError
- Duplicate registration raises ValueError
- All registered types are discoverable
"""

from __future__ import annotations

import pytest

from babylon.engine.dialectics.registry import DialecticRegistry
from babylon.engine.dialectics.volume_1 import CommodityDialectic


class TestDialecticRegistry:
    """Type registry maps type_tag strings to concrete classes."""

    def test_register_and_lookup(self) -> None:
        registry = DialecticRegistry()
        registry.register(CommodityDialectic)
        assert registry.lookup("CommodityDialectic") is CommodityDialectic

    def test_lookup_unknown_raises(self) -> None:
        registry = DialecticRegistry()
        with pytest.raises(KeyError):
            registry.lookup("NonexistentDialectic")

    def test_duplicate_registration_raises(self) -> None:
        registry = DialecticRegistry()
        registry.register(CommodityDialectic)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(CommodityDialectic)

    def test_registered_types(self) -> None:
        registry = DialecticRegistry()
        registry.register(CommodityDialectic)
        tags = registry.registered_types()
        assert "CommodityDialectic" in tags

    def test_empty_registry(self) -> None:
        registry = DialecticRegistry()
        assert len(registry.registered_types()) == 0

    def test_default_registry_includes_v1(self) -> None:
        """The module-level default registry should have V1 types."""
        from babylon.engine.dialectics.registry import default_registry

        assert "CommodityDialectic" in default_registry.registered_types()
