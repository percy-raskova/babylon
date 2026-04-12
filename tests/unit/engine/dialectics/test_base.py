"""TDD RED phase: Tests for the Dialectic[A, B] base primitive.

Validates:
- Construction with generic typed poles
- Frozen immutability (ConfigDict frozen=True)
- Weight bounds [-1, 1]
- Abstract step() enforcement
- Default sublate() returns None
- Default observe() returns expected dict
- Default invariants() returns empty list
- UUID generation and tick tracking
- Parent lineage via parent_id
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView

# ---------------------------------------------------------------------------
# Concrete test fixtures — a minimal dialectic for testing
# ---------------------------------------------------------------------------


class PoleFoo(BaseModel):
    """Trivial pole A for testing."""

    value: float = 1.0


class PoleBar(BaseModel):
    """Trivial pole B for testing."""

    label: str = "bar"


class StubDialectic(Dialectic[PoleFoo, PoleBar]):
    """Minimal concrete dialectic for testing the base class."""

    type_tag: str = "StubDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> StubDialectic:
        """Identity motion law — returns self unchanged."""
        return self.model_copy(update={"tick_updated": self.tick_updated + 1})


class BadStepDialectic(Dialectic[PoleFoo, PoleBar]):
    """Dialectic whose step() intentionally returns wrong type for testing."""

    type_tag: str = "BadStepDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> Dialectic[PoleFoo, PoleBar]:
        """Returns a different concrete type — should fail invariant check."""
        return StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )


# ===========================================================================
# Tests
# ===========================================================================


class TestDialecticConstruction:
    """Test construction semantics of the Dialectic base class."""

    def test_construct_with_valid_poles_and_weight(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(value=42.0),
            pole_b=PoleBar(label="test"),
            weight=0.7,
            tick_created=0,
            tick_updated=0,
        )
        assert d.pole_a.value == 42.0
        assert d.pole_b.label == "test"
        assert d.weight == 0.7
        assert d.tick_created == 0
        assert d.tick_updated == 0

    def test_id_is_uuid(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert isinstance(d.id, UUID)

    def test_id_unique_per_instance(self) -> None:
        d1 = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        d2 = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert d1.id != d2.id

    def test_explicit_id_preserved(self) -> None:
        fixed_id = uuid4()
        d = StubDialectic(
            id=fixed_id,
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert d.id == fixed_id

    def test_parent_id_default_none(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert d.parent_id is None

    def test_parent_id_tracks_lineage(self) -> None:
        parent_id = uuid4()
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
            parent_id=parent_id,
        )
        assert d.parent_id == parent_id

    def test_type_tag_set_by_subclass(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert d.type_tag == "StubDialectic"


class TestDialecticImmutability:
    """Frozen model — mutation attempts should raise."""

    def test_frozen_weight_mutation_raises(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        with pytest.raises(ValidationError):
            d.weight = 0.9  # type: ignore[misc]

    def test_frozen_pole_mutation_raises(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        with pytest.raises(ValidationError):
            d.pole_a = PoleFoo(value=99.0)  # type: ignore[misc]


class TestDialecticWeightBounds:
    """Weight must be in [-1.0, 1.0]."""

    def test_weight_zero_valid(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        assert d.weight == 0.0

    def test_weight_one_valid(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=1.0,
            tick_created=0,
            tick_updated=0,
        )
        assert d.weight == 1.0

    def test_weight_negative_one_valid(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=-1.0,
            tick_created=0,
            tick_updated=0,
        )
        assert d.weight == -1.0

    def test_weight_below_negative_one_raises(self) -> None:
        with pytest.raises(ValidationError):
            StubDialectic(
                pole_a=PoleFoo(),
                pole_b=PoleBar(),
                weight=-1.1,
                tick_created=0,
                tick_updated=0,
            )

    def test_weight_above_one_raises(self) -> None:
        with pytest.raises(ValidationError):
            StubDialectic(
                pole_a=PoleFoo(),
                pole_b=PoleBar(),
                weight=1.1,
                tick_created=0,
                tick_updated=0,
            )


class TestDialecticStep:
    """Motion law (step) semantics."""

    def test_step_returns_new_instance(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        inputs = TickInputs()
        world = WorldView(tick=0, dialectics={})
        result = d.step(inputs, world)
        assert isinstance(result, StubDialectic)
        assert result.tick_updated == 1

    def test_step_preserves_id(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        result = d.step(TickInputs(), WorldView(tick=0, dialectics={}))
        assert result.id == d.id


class TestDialecticSublation:
    """Sublation predicate defaults to None."""

    def test_default_sublate_returns_none(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert d.sublate() is None


class TestDialecticObservation:
    """Observation (measurement projection) for frontend/analytics."""

    def test_observe_returns_dict(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.7,
            tick_created=0,
            tick_updated=0,
        )
        obs = d.observe()
        assert isinstance(obs, dict)
        assert obs["type"] == "StubDialectic"
        assert obs["weight"] == 0.7
        assert obs["principal_aspect"] == "B"  # weight > 0 = B dominant

    def test_observe_principal_aspect_a(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=-0.3,
            tick_created=0,
            tick_updated=0,
        )
        obs = d.observe()
        assert obs["principal_aspect"] == "A"  # weight < 0 = A dominant

    def test_observe_principal_aspect_b(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.3,
            tick_created=0,
            tick_updated=0,
        )
        obs = d.observe()
        assert obs["principal_aspect"] == "B"  # weight > 0 = B dominant

    def test_observe_includes_id(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        obs = d.observe()
        assert obs["id"] == str(d.id)


class TestDialecticInvariants:
    """Per-type invariant checks — base returns empty list."""

    def test_default_invariants_empty(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert d.invariants() == []


class TestTickInputsAndWorldView:
    """Supporting types for the step() interface."""

    def test_tick_inputs_construction(self) -> None:
        inputs = TickInputs()
        assert isinstance(inputs, TickInputs)

    def test_world_view_construction(self) -> None:
        wv = WorldView(tick=5, dialectics={})
        assert wv.tick == 5
        assert wv.dialectics == {}

    def test_world_view_provides_read_access(self) -> None:
        d = StubDialectic(
            pole_a=PoleFoo(),
            pole_b=PoleBar(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        wv = WorldView(tick=0, dialectics={d.id: d})
        assert d.id in wv.dialectics
