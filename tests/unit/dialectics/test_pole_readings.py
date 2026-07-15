"""Unit tests for the per-node pole channel (Program 19 Phase 1, ADR070).

:class:`PoleSample`/:class:`PoleReading` are per-node coarse-grainings of the
aggregate :class:`GapReading`: which side of an opposition's axis a node sits
on, derived from the SAME inputs the registry already measures. The contract
pinned here:

- a binding without a ``pole_measure`` contributes nothing (inert by default);
- ``side`` derives centrally from the sigma sign with ``_lead``'s exact tie
  rule — negative = pole A, positive = pole B, zero holds the previous side
  for that ``(opposition_key, entity_id)`` and defaults to ``"a"``;
- UNPOSITIONED nodes (no contributing edge/attr on an axis) get NO reading —
  absence over fabrication (Constitution III.11), never a ``sigma=0.0``;
- output is defensively sorted by ``(opposition_key, entity_id)``;
- the catalog's capital_labor/wage/imperial pole measures reproduce
  hand-computed asymmetry balances from the id-carrying ``GraphInputs`` pairs.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from babylon.domain.dialectics.core.opposition import (
    BoundOpposition,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
    PoleReading,
    PoleSample,
)
from babylon.domain.dialectics.instances.catalog import GraphInputs, build_default_registry

pytestmark = [pytest.mark.unit, pytest.mark.math]


@dataclass(frozen=True)
class Inputs:
    """Minimal input carrier: pre-cooked samples per opposition key."""

    samples: dict[str, tuple[PoleSample, ...]]


def _binding(key: str, *, with_poles: bool) -> BoundOpposition[Inputs]:
    spec = OppositionSpec(key=key, pole_a=f"{key}-A", pole_b=f"{key}-B")

    def measure(inputs: Inputs) -> GapReading:
        return GapReading(gap=0.0, balance=0.0)

    if not with_poles:
        return BoundOpposition(spec=spec, measure=measure)

    def poles(inputs: Inputs) -> tuple[PoleSample, ...]:
        return inputs.samples.get(key, ())

    return BoundOpposition(spec=spec, measure=measure, pole_measure=poles)


def _readings(
    registry: OppositionRegistry[Inputs],
    inputs: Inputs,
    previous: dict[tuple[str, str], PoleReading] | None = None,
) -> tuple[PoleReading, ...]:
    return registry.read_poles(inputs, previous)


class TestModels:
    def test_pole_sample_is_frozen_and_bounded(self) -> None:
        sample = PoleSample(entity_id="C001", sigma=-0.5)
        with pytest.raises(ValidationError):
            sample.sigma = 0.0  # type: ignore[misc]
        with pytest.raises(ValidationError):
            PoleSample(entity_id="C001", sigma=1.5)  # Balance is [-1, 1]
        with pytest.raises(ValidationError):
            PoleSample(entity_id="", sigma=0.0)

    def test_pole_reading_side_is_a_or_b_only(self) -> None:
        reading = PoleReading(opposition_key="wage", entity_id="C001", side="b", sigma=0.8)
        assert reading.side == "b"
        with pytest.raises(ValidationError):
            PoleReading(opposition_key="wage", entity_id="C001", side="c", sigma=0.0)  # type: ignore[arg-type]


class TestReadPoles:
    def test_binding_without_pole_measure_contributes_nothing(self) -> None:
        registry = OppositionRegistry(bindings=[_binding("mute", with_poles=False)])
        assert _readings(registry, Inputs(samples={})) == ()

    def test_side_from_sigma_sign(self) -> None:
        registry = OppositionRegistry(bindings=[_binding("axis", with_poles=True)])
        inputs = Inputs(
            samples={
                "axis": (
                    PoleSample(entity_id="labor", sigma=-0.5),
                    PoleSample(entity_id="capital", sigma=0.5),
                )
            }
        )
        by_id = {r.entity_id: r for r in _readings(registry, inputs)}
        assert by_id["labor"].side == "a"
        assert by_id["labor"].sigma == pytest.approx(-0.5)
        assert by_id["capital"].side == "b"
        assert by_id["capital"].sigma == pytest.approx(0.5)

    def test_zero_sigma_defaults_to_pole_a(self) -> None:
        registry = OppositionRegistry(bindings=[_binding("axis", with_poles=True)])
        inputs = Inputs(samples={"axis": (PoleSample(entity_id="tied", sigma=0.0),)})
        (reading,) = _readings(registry, inputs)
        assert reading.side == "a"

    def test_zero_sigma_holds_previous_side(self) -> None:
        registry = OppositionRegistry(bindings=[_binding("axis", with_poles=True)])
        inputs = Inputs(samples={"axis": (PoleSample(entity_id="tied", sigma=0.0),)})
        previous = {
            ("axis", "tied"): PoleReading(
                opposition_key="axis", entity_id="tied", side="b", sigma=0.4
            )
        }
        (reading,) = _readings(registry, inputs, previous)
        assert reading.side == "b"  # a pole persists until actually overturned

    def test_previous_is_keyed_per_opposition_not_just_entity(self) -> None:
        registry = OppositionRegistry(
            bindings=[_binding("one", with_poles=True), _binding("two", with_poles=True)]
        )
        inputs = Inputs(
            samples={
                "one": (PoleSample(entity_id="tied", sigma=0.0),),
                "two": (PoleSample(entity_id="tied", sigma=0.0),),
            }
        )
        previous = {
            ("one", "tied"): PoleReading(
                opposition_key="one", entity_id="tied", side="b", sigma=0.1
            )
        }
        by_key = {r.opposition_key: r for r in _readings(registry, inputs, previous)}
        assert by_key["one"].side == "b"  # held from history
        assert by_key["two"].side == "a"  # no history on THIS axis -> default

    def test_output_sorted_by_key_then_entity(self) -> None:
        registry = OppositionRegistry(
            bindings=[_binding("zeta", with_poles=True), _binding("alpha", with_poles=True)]
        )
        inputs = Inputs(
            samples={
                "zeta": (
                    PoleSample(entity_id="n2", sigma=0.3),
                    PoleSample(entity_id="n1", sigma=0.3),
                ),
                "alpha": (PoleSample(entity_id="n9", sigma=-0.3),),
            }
        )
        ordered = [(r.opposition_key, r.entity_id) for r in _readings(registry, inputs)]
        assert ordered == [("alpha", "n9"), ("zeta", "n1"), ("zeta", "n2")]


class TestCatalogPoleMeasures:
    """The production measures, hand-computed from asymmetry balances."""

    def test_capital_labor_poles_hand_computed(self) -> None:
        # One EXPLOITATION edge worker(10) -> owner(30): edge balance
        # (30-10)/40 = +0.5 (capital dominant). The source sits on the labor
        # side (sigma -0.5 -> pole a); the target on capital (+0.5 -> pole b).
        inputs = GraphInputs(exploitation_id_pairs=(("worker", "owner", 10.0, 30.0),))
        readings = build_default_registry().read_poles(inputs)
        by_id = {r.entity_id: r for r in readings if r.opposition_key == "capital_labor"}
        assert by_id["worker"].sigma == pytest.approx(-0.5)
        assert by_id["worker"].side == "a"
        assert by_id["owner"].sigma == pytest.approx(0.5)
        assert by_id["owner"].side == "b"

    def test_capital_labor_node_on_both_sides_takes_the_mean(self) -> None:
        # mid is exploited by top (source: -0.5) AND exploits bot (target: +0.5)
        # -> mean sigma 0.0 -> tie -> defaults to pole a with no history.
        inputs = GraphInputs(
            exploitation_id_pairs=(
                ("mid", "top", 10.0, 30.0),
                ("bot", "mid", 10.0, 30.0),
            )
        )
        readings = build_default_registry().read_poles(inputs)
        by_id = {r.entity_id: r for r in readings if r.opposition_key == "capital_labor"}
        assert by_id["mid"].sigma == pytest.approx(0.0)
        assert by_id["mid"].side == "a"
        assert by_id["bot"].sigma == pytest.approx(-0.5)
        assert by_id["top"].sigma == pytest.approx(0.5)

    def test_wage_and_imperial_read_the_same_defect(self) -> None:
        # bribed: w_paid=18 > v_produced=2 -> sigma (18-2)/20 = +0.8 (pole b,
        # price-of-labor-power / core). exploited: w=2 < v=18 -> -0.8 (pole a).
        inputs = GraphInputs(
            wage_value_id_pairs=(
                ("bribed", 18.0, 2.0),
                ("exploited", 2.0, 18.0),
            )
        )
        readings = build_default_registry().read_poles(inputs)
        for key in ("wage", "imperial"):
            by_id = {r.entity_id: r for r in readings if r.opposition_key == key}
            assert by_id["bribed"].sigma == pytest.approx(0.8)
            assert by_id["bribed"].side == "b"
            assert by_id["exploited"].sigma == pytest.approx(-0.8)
            assert by_id["exploited"].side == "a"

    def test_unpositioned_is_absence_not_zero(self) -> None:
        # Empty id-pairs -> NO readings at all (Constitution III.11): a node
        # with no participation on an axis must be absent, never sigma=0.0.
        assert build_default_registry().read_poles(GraphInputs()) == ()

    def test_axis_isolation(self) -> None:
        # A node positioned ONLY on the wage axis gets no capital_labor reading.
        inputs = GraphInputs(wage_value_id_pairs=(("solo", 18.0, 2.0),))
        readings = build_default_registry().read_poles(inputs)
        keys_for_solo = {r.opposition_key for r in readings if r.entity_id == "solo"}
        assert keys_for_solo == {"imperial", "wage"}
