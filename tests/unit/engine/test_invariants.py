"""RED phase: Tests for Invariant protocol and InvariantResult.

Spec 040 Discipline 1: Invariants as First-Class Objects.
"""

from __future__ import annotations

import pytest

from babylon.models.world_state import WorldState


class TestInvariantResult:
    """Tests for InvariantResult dataclass."""

    def test_ok_result(self) -> None:
        from babylon.engine.invariants import InvariantResult

        result = InvariantResult.success()
        assert result.ok is True
        assert result.msg == ""

    def test_violated_result(self) -> None:
        from babylon.engine.invariants import InvariantResult

        result = InvariantResult.violated("wealth went negative")
        assert result.ok is False
        assert "wealth went negative" in result.msg

    def test_result_is_frozen(self) -> None:
        from babylon.engine.invariants import InvariantResult

        result = InvariantResult.success()
        with pytest.raises(AttributeError):
            result.passed = False  # type: ignore[misc]


class TestNonNegativeWealth:
    """Tests for NonNegativeWealth invariant."""

    def test_passes_when_all_wealth_positive(self) -> None:
        from babylon.engine.invariants import NonNegativeWealth

        inv = NonNegativeWealth()
        pre = WorldState()
        post = WorldState()
        result = inv.check(pre, post)
        assert result.ok is True

    def test_name(self) -> None:
        from babylon.engine.invariants import NonNegativeWealth

        inv = NonNegativeWealth()
        assert inv.name == "non_negative_wealth"

    def test_fails_when_entity_has_negative_wealth(self) -> None:
        from babylon.engine.invariants import NonNegativeWealth
        from babylon.models.entities.social_class import SocialClass

        inv = NonNegativeWealth()
        pre = WorldState()
        # Use model_construct to bypass Pydantic ge=0.0 validation
        # This simulates a bug where a system sets wealth negative
        bad_entity = SocialClass.model_construct(
            id="C001",
            name="Worker",
            role="periphery_proletariat",
            wealth=-5.0,  # Negative!
            population=1000,
        )
        post = WorldState.model_construct(
            tick=1,
            entities={"C001": bad_entity},
            territories={},
            relationships=[],
            event_log=[],
            events=[],
        )
        result = inv.check(pre, post)
        assert result.ok is False
        assert "C001" in result.msg


class TestHeatNonNegativity:
    """Tests for HeatNonNegativity invariant."""

    def test_passes_when_no_territories(self) -> None:
        from babylon.engine.invariants import HeatNonNegativity

        inv = HeatNonNegativity()
        pre = WorldState()
        post = WorldState()
        result = inv.check(pre, post)
        assert result.ok is True

    def test_name(self) -> None:
        from babylon.engine.invariants import HeatNonNegativity

        inv = HeatNonNegativity()
        assert inv.name == "heat_non_negativity"

    def test_fails_when_heat_negative(self) -> None:
        from babylon.engine.invariants import HeatNonNegativity
        from babylon.models.entities.territory import Territory

        inv = HeatNonNegativity()
        pre = WorldState()
        # Use model_construct to bypass Pydantic ge=0.0 validation
        # This simulates a bug where a system sets heat negative
        bad_territory = Territory.model_construct(
            id="T001",
            name="Downtown",
            heat=-0.5,  # Negative!
        )
        post = WorldState.model_construct(
            tick=1,
            entities={},
            territories={"T001": bad_territory},
            relationships=[],
            event_log=[],
            events=[],
        )
        result = inv.check(pre, post)
        assert result.ok is False
        assert "T001" in result.msg


class TestInvariantProtocol:
    """Tests for the Invariant protocol itself (runtime_checkable)."""

    def test_concrete_invariant_satisfies_protocol(self) -> None:
        from babylon.engine.invariants import Invariant, NonNegativeWealth

        inv = NonNegativeWealth()
        assert isinstance(inv, Invariant)

    def test_invariant_is_runtime_checkable(self) -> None:
        from babylon.engine.invariants import Invariant

        # Something that doesn't implement the protocol
        assert not isinstance("not an invariant", Invariant)
