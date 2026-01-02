"""Tests for is_dead() strict typing in tools/shared.py.

Sprint 1.X Deliverable 2: High-Fidelity State.
Pain Point #3: Loose typing allowed bugs like is_dead(float) instead of is_dead(Entity).

These tests verify that is_dead() uses EntityProtocol to enforce type safety.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from babylon.models import SocialClass, SocialRole
from babylon.models.types import EntityProtocol

# Add tools directory to path so we can import shared
TOOLS_PATH = Path(__file__).parent.parent.parent.parent / "tools"
sys.path.insert(0, str(TOOLS_PATH))


class TestEntityProtocol:
    """Tests for EntityProtocol definition."""

    def test_social_class_implements_entity_protocol(self) -> None:
        """SocialClass should implement EntityProtocol.

        EntityProtocol requires an 'active' property, which SocialClass has.
        """
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            active=True,
        )
        assert isinstance(worker, EntityProtocol)

    def test_inactive_social_class_implements_protocol(self) -> None:
        """Dead SocialClass (active=False) still implements EntityProtocol."""
        dead_worker = SocialClass(
            id="C001",
            name="Dead Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            active=False,
        )
        assert isinstance(dead_worker, EntityProtocol)


class TestIsDeadTypeEnforcement:
    """Tests for is_dead() type enforcement."""

    def test_is_dead_accepts_entity_protocol(self) -> None:
        """is_dead() should accept objects implementing EntityProtocol."""
        from shared import is_dead

        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            active=True,
        )
        assert is_dead(worker) is False

    def test_is_dead_returns_true_for_inactive_entity(self) -> None:
        """is_dead() should return True for inactive entities."""
        from shared import is_dead

        dead_worker = SocialClass(
            id="C001",
            name="Dead Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            active=False,
        )
        assert is_dead(dead_worker) is True

    def test_is_dead_accepts_none(self) -> None:
        """is_dead() should return True for None (missing entity)."""
        from shared import is_dead

        assert is_dead(None) is True

    def test_is_dead_rejects_float(self) -> None:
        """is_dead() should reject raw float values.

        This is the primary test for Pain Point #3.
        Previously is_dead(0.5) would silently return True (via getattr fallback).
        Now it should raise TypeError.
        """
        from shared import is_dead

        with pytest.raises(TypeError) as exc_info:
            is_dead(0.5)  # type: ignore[arg-type]

        assert "EntityProtocol" in str(exc_info.value)

    def test_is_dead_rejects_dict(self) -> None:
        """is_dead() should reject dict values.

        Dicts might have an 'active' key but are not valid entities.
        """
        from shared import is_dead

        fake_entity = {"active": True, "wealth": 100.0}

        with pytest.raises(TypeError) as exc_info:
            is_dead(fake_entity)  # type: ignore[arg-type]

        assert "EntityProtocol" in str(exc_info.value)

    def test_is_dead_rejects_string(self) -> None:
        """is_dead() should reject string values."""
        from shared import is_dead

        with pytest.raises(TypeError) as exc_info:
            is_dead("C001")  # type: ignore[arg-type]

        assert "EntityProtocol" in str(exc_info.value)


class TestIsDeadByWealthPreserved:
    """Tests that is_dead_by_wealth() remains for legacy compatibility."""

    def test_is_dead_by_wealth_accepts_float(self) -> None:
        """is_dead_by_wealth() should accept float values.

        This is the legacy function for wealth-threshold checks.
        """
        from shared import is_dead_by_wealth

        # Wealth above threshold
        assert is_dead_by_wealth(1.0) is False
        assert is_dead_by_wealth(0.1) is False

        # Wealth at/below threshold (0.001)
        assert is_dead_by_wealth(0.001) is True
        assert is_dead_by_wealth(0.0) is True
        assert is_dead_by_wealth(-1.0) is True
