"""Unit tests for ClassConsciousnessDialectic."""

import uuid

import pytest

from babylon.engine.dialectics.base import TickInputs, WorldView
from babylon.engine.dialectics.consciousness import ClassConsciousnessDialectic
from babylon.models.components.material_conditions import MaterialConditionsBuffer
from babylon.models.entities.consciousness import TernaryConsciousness


# Need to provide some boilerplate setup if needed
@pytest.fixture
def empty_world() -> WorldView:
    return WorldView(tick=1, dialectics={}, morphisms=[], events=[])


def test_consciousness_equilibrium(empty_world: WorldView) -> None:
    """Test consciousness dialectic at equilibrium."""
    mc = MaterialConditionsBuffer(
        agitation=0.0, exploitation_visibility=0.5, reification_buffer=0.5
    )
    tc = TernaryConsciousness(r=0.2, l=0.8, f=0.0)  # liberal majority

    dialectic = ClassConsciousnessDialectic(
        id=uuid.uuid4(),
        type_tag="ClassConsciousnessDialectic",
        weight=-0.5,  # Reified
        pole_a=mc,
        pole_b=tc,
        tick_created=1,
        tick_updated=1,
    )

    inputs = TickInputs(upstream={})
    new_dialectic = dialectic.step(inputs, empty_world)

    # Without agitation, consciousness components stand still
    assert new_dialectic.pole_b.r == pytest.approx(0.2)
    assert new_dialectic.pole_b.l == pytest.approx(0.8)
    assert new_dialectic.pole_b.f == pytest.approx(0.0)

    violations = new_dialectic.invariants()
    assert not violations


def test_consciousness_agitation_and_solidarity(empty_world: WorldView) -> None:
    """Test consciousness shifts with agitation and solidarity."""
    mc = MaterialConditionsBuffer(
        agitation=0.0, exploitation_visibility=0.8, reification_buffer=0.2
    )
    tc = TernaryConsciousness(r=0.2, l=0.8, f=0.0)

    dialectic = ClassConsciousnessDialectic(
        id=uuid.uuid4(),
        type_tag="ClassConsciousnessDialectic",
        weight=-0.5,
        pole_a=mc,
        pole_b=tc,
        tick_created=1,
        tick_updated=1,
    )

    inputs = TickInputs(
        upstream={
            dialectic.id: {
                "added_agitation": 1.0,
                "solidarity": 1.0,
                "education_pressure": 0.0,
            }
        }
    )

    new_dialectic = dialectic.step(inputs, empty_world)

    # With solidarity=1.0, agitation should be pumped entirely into revolutionary (r)
    assert float(new_dialectic.pole_b.r) > 0.2
    assert float(new_dialectic.pole_b.l) < 0.8
    assert float(new_dialectic.pole_b.f) == pytest.approx(0.0)

    # Weight should shift positive (toward imputation)
    assert new_dialectic.weight > dialectic.weight

    violations = new_dialectic.invariants()
    assert not violations
