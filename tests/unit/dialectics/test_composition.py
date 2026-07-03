"""Unit tests for :mod:`babylon.dialectics.core.composition`.

Composition operates at the binding level: ``product`` (D1 ⊗ D2, "sharp
only if both are sharp") and ``sum_`` (D1 ⊕ D2, "either develops") take
:class:`BoundOpposition` components and return a new binding whose measure
re-runs the component measures on the same inputs. These tests pin the
concrete arithmetic and the provenance stamping; the universal bound laws
(gap(⊗) ≤ min, gap(⊕) ≥ max, [0, 1]) live in
``tests/property/dialectics/test_composition_laws.py`` as Hypothesis
properties over arbitrary readings.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from babylon.dialectics.core.composition import product, sum_
from babylon.dialectics.core.opposition import BoundOpposition, GapReading, OppositionSpec

pytestmark = [pytest.mark.unit, pytest.mark.math]


@dataclass(frozen=True)
class Inputs:
    """Empty input carrier — constant measures ignore it."""


def _const(key: str, gap: float, balance: float) -> BoundOpposition[Inputs]:
    """A binding whose measure always returns ``GapReading(gap, balance)``."""
    spec = OppositionSpec(key=key, pole_a=f"{key}-A", pole_b=f"{key}-B")

    def measure(_inputs: Inputs) -> GapReading:
        return GapReading(gap=gap, balance=balance)

    return BoundOpposition(spec=spec, measure=measure)


def _spec(key: str = "composite") -> OppositionSpec:
    return OppositionSpec(key=key, pole_a="A", pole_b="B")


class TestProduct:
    def test_gap_is_the_product_of_component_gaps(self) -> None:
        composite = product(_spec(), _const("d1", 0.6, 0.2), _const("d2", 0.5, -0.4))
        assert composite.measure(Inputs()).gap == pytest.approx(0.3)  # 0.6 * 0.5

    def test_balance_is_gap_weighted_mean(self) -> None:
        composite = product(_spec(), _const("d1", 0.6, 0.2), _const("d2", 0.4, -0.5))
        # (0.6*0.2 + 0.4*(-0.5)) / (0.6 + 0.4) = (0.12 - 0.20) / 1.0 = -0.08
        assert composite.measure(Inputs()).balance == pytest.approx(-0.08)

    def test_both_gaps_zero_gives_zero_balance(self) -> None:
        composite = product(_spec(), _const("d1", 0.0, 0.5), _const("d2", 0.0, -0.5))
        reading = composite.measure(Inputs())
        assert reading.gap == 0.0
        assert reading.balance == 0.0

    def test_provenance_is_stamped_from_components(self) -> None:
        composite = product(_spec("p"), _const("alpha", 0.6, 0.2), _const("beta", 0.5, -0.4))
        assert composite.spec.composition == "product"
        assert composite.spec.component_keys == ("alpha", "beta")
        assert composite.spec.key == "p"  # caller identity preserved


class TestSum:
    def test_gap_is_probabilistic_or(self) -> None:
        composite = sum_(_spec(), _const("d1", 0.6, 0.2), _const("d2", 0.5, -0.4))
        # 0.6 + 0.5 - 0.6*0.5 = 1.1 - 0.3 = 0.8
        assert composite.measure(Inputs()).gap == pytest.approx(0.8)

    def test_balance_is_gap_weighted_mean(self) -> None:
        composite = sum_(_spec(), _const("d1", 0.6, 0.2), _const("d2", 0.4, -0.5))
        # weight is the COMPONENT gap, identical to product's weighting
        assert composite.measure(Inputs()).balance == pytest.approx(-0.08)

    def test_both_gaps_zero_gives_zero_balance(self) -> None:
        composite = sum_(_spec(), _const("d1", 0.0, 0.5), _const("d2", 0.0, -0.5))
        reading = composite.measure(Inputs())
        assert reading.gap == 0.0
        assert reading.balance == 0.0

    def test_provenance_is_stamped_from_components(self) -> None:
        composite = sum_(_spec("s"), _const("alpha", 0.6, 0.2), _const("beta", 0.5, -0.4))
        assert composite.spec.composition == "sum"
        assert composite.spec.component_keys == ("alpha", "beta")


class TestProvenanceDefaults:
    def test_plain_spec_has_empty_provenance(self) -> None:
        spec = OppositionSpec(key="plain", pole_a="A", pole_b="B")
        assert spec.component_keys == ()
        assert spec.composition == ""
