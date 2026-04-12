"""Tests for MaterialConditionsBuffer model (Spec 043, Phase 1).

TDD Red Phase: These tests verify the new MaterialConditionsBuffer model
that replaces IdeologicalComponent on population nodes.

MaterialConditionsBuffer stores the material preconditions for consciousness
change on population nodes. It buffers value-tensor-derived quantities that
feed into the community-level ternary routing.

Fields:
    agitation: Raw political energy from value tensor crisis.
    exploitation_visibility: How visible exploitation is to this population.
    reification_buffer: How much commodity fetishism obscures class relations.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.components.material_conditions import MaterialConditionsBuffer


@pytest.mark.unit
class TestMaterialConditionsBufferCreation:
    """Verify MaterialConditionsBuffer model creation and defaults."""

    def test_default_creation(self) -> None:
        """Default MaterialConditionsBuffer has zero agitation."""
        buffer = MaterialConditionsBuffer()
        assert buffer.agitation == pytest.approx(0.0)
        assert buffer.exploitation_visibility == pytest.approx(0.0)
        assert buffer.reification_buffer == pytest.approx(0.5)

    def test_custom_creation(self) -> None:
        """MaterialConditionsBuffer accepts all fields."""
        buffer = MaterialConditionsBuffer(
            agitation=1.5,
            exploitation_visibility=0.7,
            reification_buffer=0.3,
        )
        assert buffer.agitation == pytest.approx(1.5)
        assert buffer.exploitation_visibility == pytest.approx(0.7)
        assert buffer.reification_buffer == pytest.approx(0.3)

    def test_frozen_model(self) -> None:
        """MaterialConditionsBuffer is frozen (immutable)."""
        buffer = MaterialConditionsBuffer()
        with pytest.raises(ValidationError):
            buffer.agitation = 0.5  # type: ignore[misc]


@pytest.mark.unit
class TestMaterialConditionsBufferBounds:
    """Verify field validation constraints."""

    def test_agitation_must_be_nonnegative(self) -> None:
        """Agitation >= 0.0 (no negative crisis energy)."""
        with pytest.raises(ValidationError):
            MaterialConditionsBuffer(agitation=-0.1)

    def test_agitation_unbounded_above(self) -> None:
        """Agitation has no upper bound (crisis can accumulate)."""
        buffer = MaterialConditionsBuffer(agitation=100.0)
        assert buffer.agitation == pytest.approx(100.0)

    def test_exploitation_visibility_bounded(self) -> None:
        """exploitation_visibility in [0, 1]."""
        with pytest.raises(ValidationError):
            MaterialConditionsBuffer(exploitation_visibility=-0.01)
        with pytest.raises(ValidationError):
            MaterialConditionsBuffer(exploitation_visibility=1.01)

    def test_reification_buffer_bounded(self) -> None:
        """reification_buffer in [0, 1]."""
        with pytest.raises(ValidationError):
            MaterialConditionsBuffer(reification_buffer=-0.01)
        with pytest.raises(ValidationError):
            MaterialConditionsBuffer(reification_buffer=1.01)


@pytest.mark.unit
class TestMaterialConditionsBufferEquality:
    """Verify equality and hashing behaviors."""

    def test_equal_buffers(self) -> None:
        """Two buffers with same values are equal."""
        a = MaterialConditionsBuffer(agitation=0.5, exploitation_visibility=0.3)
        b = MaterialConditionsBuffer(agitation=0.5, exploitation_visibility=0.3)
        assert a == b

    def test_unequal_buffers(self) -> None:
        """Buffers with different values are not equal."""
        a = MaterialConditionsBuffer(agitation=0.5)
        b = MaterialConditionsBuffer(agitation=0.6)
        assert a != b
