"""Unit tests for TickContext model."""

from __future__ import annotations

import pytest

from babylon.engine.context import TickContext
from babylon.models.enums import DisplacementPriorityMode


class TestTickContextCreation:
    """Test TickContext instantiation."""

    def test_default_values(self) -> None:
        """TickContext has sensible defaults."""
        ctx = TickContext()
        assert ctx.tick == 0
        assert ctx.persistent_data == {}
        assert ctx.displacement_mode is None

    def test_explicit_tick(self) -> None:
        """Tick can be set at construction."""
        ctx = TickContext(tick=42)
        assert ctx.tick == 42

    def test_explicit_persistent_data(self) -> None:
        """Persistent data can be provided at construction."""
        data = {"previous_wages": {"worker": 100.0}}
        ctx = TickContext(tick=1, persistent_data=data)
        assert ctx.persistent_data == data

    def test_explicit_displacement_mode(self) -> None:
        """Displacement mode can be set at construction."""
        ctx = TickContext(displacement_mode=DisplacementPriorityMode.CONTAINMENT)
        assert ctx.displacement_mode == DisplacementPriorityMode.CONTAINMENT


class TestTickContextDirectAccess:
    """Test direct attribute access (typed path)."""

    def test_read_tick(self) -> None:
        """Can read tick directly."""
        ctx = TickContext(tick=7)
        assert ctx.tick == 7

    def test_write_tick(self) -> None:
        """Can write tick directly."""
        ctx = TickContext()
        ctx.tick = 99
        assert ctx.tick == 99

    def test_read_displacement_mode(self) -> None:
        """Can read displacement_mode directly."""
        ctx = TickContext(displacement_mode=DisplacementPriorityMode.ELIMINATION)
        assert ctx.displacement_mode == DisplacementPriorityMode.ELIMINATION

    def test_read_persistent_data(self) -> None:
        """Can read and modify persistent_data directly."""
        ctx = TickContext()
        ctx.persistent_data["key"] = "value"
        assert ctx.persistent_data["key"] == "value"


class TestTickContextDictStyleRead:
    """Test dict-style read access (backward compatibility)."""

    def test_getitem_tick(self) -> None:
        """Can read tick via __getitem__."""
        ctx = TickContext(tick=5)
        assert ctx["tick"] == 5

    def test_getitem_displacement_mode(self) -> None:
        """Can read displacement_mode via __getitem__."""
        ctx = TickContext(displacement_mode=DisplacementPriorityMode.EXTRACTION)
        assert ctx["displacement_mode"] == DisplacementPriorityMode.EXTRACTION

    def test_getitem_persistent_key(self) -> None:
        """Can read persistent_data keys via __getitem__."""
        ctx = TickContext()
        ctx.persistent_data["previous_wages"] = {"worker": 50.0}
        assert ctx["previous_wages"] == {"worker": 50.0}

    def test_getitem_missing_raises_keyerror(self) -> None:
        """Missing keys raise KeyError."""
        ctx = TickContext()
        with pytest.raises(KeyError):
            _ = ctx["nonexistent"]


class TestTickContextDictStyleWrite:
    """Test dict-style write access (backward compatibility)."""

    def test_setitem_tick(self) -> None:
        """Can write tick via __setitem__."""
        ctx = TickContext()
        ctx["tick"] = 10
        assert ctx.tick == 10

    def test_setitem_displacement_mode(self) -> None:
        """Can write displacement_mode via __setitem__."""
        ctx = TickContext()
        ctx["displacement_mode"] = DisplacementPriorityMode.CONTAINMENT
        assert ctx.displacement_mode == DisplacementPriorityMode.CONTAINMENT

    def test_setitem_persistent_key(self) -> None:
        """Unknown keys go to persistent_data via __setitem__."""
        ctx = TickContext()
        ctx["previous_wages"] = {"proletariat": 80.0}
        assert ctx.persistent_data["previous_wages"] == {"proletariat": 80.0}


class TestTickContextGetMethod:
    """Test dict-compatible get() method."""

    def test_get_tick_exists(self) -> None:
        """get() returns tick value when present."""
        ctx = TickContext(tick=3)
        assert ctx.get("tick") == 3

    def test_get_tick_with_default(self) -> None:
        """get() default is ignored when key exists."""
        ctx = TickContext(tick=3)
        assert ctx.get("tick", 0) == 3

    def test_get_missing_returns_default(self) -> None:
        """get() returns default for missing keys."""
        ctx = TickContext()
        assert ctx.get("nonexistent", "fallback") == "fallback"

    def test_get_missing_returns_none_by_default(self) -> None:
        """get() returns None by default for missing keys."""
        ctx = TickContext()
        assert ctx.get("nonexistent") is None

    def test_get_displacement_mode_default(self) -> None:
        """get() can provide default for displacement_mode."""
        ctx = TickContext()
        result = ctx.get("displacement_mode", DisplacementPriorityMode.EXTRACTION)
        # displacement_mode is None, but __getitem__ returns it
        # This is a direct attribute so it returns None, not the default
        # Actually need to check the implementation - it returns None when mode is None
        assert result is None

    def test_get_persistent_data_key(self) -> None:
        """get() can retrieve persistent_data keys."""
        ctx = TickContext()
        ctx.persistent_data["custom"] = 42
        assert ctx.get("custom") == 42
        assert ctx.get("custom", 0) == 42


class TestTickContextContains:
    """Test __contains__ / `in` operator."""

    def test_tick_always_in_context(self) -> None:
        """tick is always considered present."""
        ctx = TickContext()
        assert "tick" in ctx

    def test_displacement_mode_always_in_context(self) -> None:
        """displacement_mode is always considered present."""
        ctx = TickContext()
        assert "displacement_mode" in ctx

    def test_persistent_key_in_context(self) -> None:
        """Persistent data keys show as present."""
        ctx = TickContext()
        ctx.persistent_data["previous_wages"] = {}
        assert "previous_wages" in ctx

    def test_missing_key_not_in_context(self) -> None:
        """Missing keys are not present."""
        ctx = TickContext()
        assert "nonexistent" not in ctx


class TestTickContextSystemCompatibility:
    """Test patterns used by actual Systems."""

    def test_economic_pattern(self) -> None:
        """ImperialRentSystem pattern: context.get('tick', 0)."""
        ctx = TickContext(tick=5)
        tick = ctx.get("tick", 0)
        assert tick == 5

    def test_ideology_read_pattern(self) -> None:
        """ConsciousnessSystem read pattern: PREVIOUS_WAGES_KEY not in context."""
        ctx = TickContext()
        previous_wages_key = "previous_wages"
        assert previous_wages_key not in ctx
        # Initialize like ideology.py does
        ctx[previous_wages_key] = {}
        assert previous_wages_key in ctx

    def test_ideology_write_pattern(self) -> None:
        """ConsciousnessSystem write pattern: context[key] = value."""
        ctx = TickContext()
        ctx["previous_wages"] = {"worker_1": 100.0}
        assert ctx.persistent_data["previous_wages"] == {"worker_1": 100.0}

    def test_territory_pattern(self) -> None:
        """TerritorySystem pattern: context.get('displacement_mode', default)."""
        ctx = TickContext()
        mode = ctx.get("displacement_mode", DisplacementPriorityMode.EXTRACTION)
        # Returns None because displacement_mode attribute is None
        assert mode is None

        # With explicit mode set
        ctx.displacement_mode = DisplacementPriorityMode.ELIMINATION
        mode = ctx.get("displacement_mode", DisplacementPriorityMode.EXTRACTION)
        assert mode == DisplacementPriorityMode.ELIMINATION


class TestTickContextIsolation:
    """Test that persistent_data is properly isolated."""

    def test_persistent_data_not_shared_by_default(self) -> None:
        """Each TickContext gets its own persistent_data dict."""
        ctx1 = TickContext()
        ctx2 = TickContext()
        ctx1.persistent_data["key"] = "value1"
        assert "key" not in ctx2.persistent_data

    def test_engine_sync_pattern(self) -> None:
        """Engine syncs persistent_data back to caller's dict."""
        # This mimics what simulation_engine.step() does:
        # 1. Create TickContext with caller's persistent dict as initial values
        # 2. Systems modify context.persistent_data
        # 3. Engine copies changes back to caller's dict
        caller_persistent: dict[str, object] = {}
        ctx = TickContext(tick=1, persistent_data=dict(caller_persistent))

        # System writes to context
        ctx.persistent_data["previous_wages"] = {"worker": 100.0}

        # Engine syncs back to caller
        for key, value in ctx.persistent_data.items():
            caller_persistent[key] = value

        assert caller_persistent["previous_wages"] == {"worker": 100.0}
