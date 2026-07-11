"""Unit tests for :mod:`babylon.domain.dialectics.core.opposition`.

The registry is the successor of both the saturating edge-tension scalar
and the dormant layer's ``weight``: each opposition reports a
:class:`GapReading` (gap = how far from closure, balance = signed
dominance of pole B over pole A), the registry derives rate and the
principal contradiction (Mao: the fast-developing sharp contradiction),
and the leading pole persists through balance=0 (the principal aspect
holds until actually overturned).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from babylon.domain.dialectics.core.composition import sum_
from babylon.domain.dialectics.core.opposition import (
    MAX_NESTING_DEPTH,
    BoundOpposition,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
    OppositionState,
    PoleBinding,
)
from babylon.formulas.contradiction import (
    calculate_wealth_asymmetry_balance,
    calculate_wealth_asymmetry_gap,
)

pytestmark = pytest.mark.math


@dataclass(frozen=True)
class Inputs:
    """Minimal Phase-A input carrier (Phase C binds graph snapshots)."""

    readings: dict[str, tuple[float, float]]


def _measure_for(key: str) -> BoundOpposition[Inputs]:
    spec = OppositionSpec(key=key, pole_a=f"{key}-A", pole_b=f"{key}-B")

    def measure(inputs: Inputs) -> GapReading:
        gap, balance = inputs.readings[key]
        return GapReading(gap=gap, balance=balance)

    return BoundOpposition(spec=spec, measure=measure)


def _registry(*keys: str, rate_weight: float = 10.0) -> OppositionRegistry[Inputs]:
    return OppositionRegistry(bindings=[_measure_for(k) for k in keys], rate_weight=rate_weight)


def _by_key(states: tuple[OppositionState, ...]) -> dict[str, OppositionState]:
    return {s.key: s for s in states}


class TestStep:
    def test_first_step_has_zero_rate(self) -> None:
        reg = _registry("capital_labor")
        states = reg.step(Inputs({"capital_labor": (0.4, 0.2)}), tick=0)
        (state,) = states
        assert state.gap == pytest.approx(0.4)
        assert state.rate == 0.0
        assert state.tick == 0

    def test_rate_is_gap_delta_from_previous(self) -> None:
        reg = _registry("capital_labor")
        first = reg.step(Inputs({"capital_labor": (0.4, 0.2)}), tick=1)
        second = reg.step(Inputs({"capital_labor": (0.7, 0.2)}), tick=2, previous=_by_key(first))
        assert second[0].rate == pytest.approx(0.3)

    def test_gap_can_fall(self) -> None:
        """The measure is NOT a ratchet — hegemonic articulation can close gaps."""
        reg = _registry("capital_labor")
        first = reg.step(Inputs({"capital_labor": (0.7, 0.0)}), tick=1)
        second = reg.step(Inputs({"capital_labor": (0.5, 0.0)}), tick=2, previous=_by_key(first))
        assert second[0].gap == pytest.approx(0.5)
        assert second[0].rate == pytest.approx(-0.2)

    def test_purity(self) -> None:
        reg = _registry("a", "b")
        inputs = Inputs({"a": (0.3, -0.1), "b": (0.6, 0.4)})
        assert reg.step(inputs, tick=5) == reg.step(inputs, tick=5)

    def test_empty_registry_steps_to_empty(self) -> None:
        reg: OppositionRegistry[Inputs] = OppositionRegistry(bindings=[])
        assert reg.step(Inputs({}), tick=0) == ()


class TestPrincipal:
    def test_highest_gap_is_principal_when_static(self) -> None:
        reg = _registry("a", "b")
        states = _by_key(reg.step(Inputs({"a": (0.3, 0.0), "b": (0.6, 0.0)}), tick=0))
        assert states["b"].is_principal
        assert not states["a"].is_principal

    def test_fast_developing_contradiction_overtakes(self) -> None:
        """Mao: the principal contradiction is the one whose development leads."""
        reg = _registry("a", "b")
        prev = _by_key(reg.step(Inputs({"a": (0.5, 0.0), "b": (0.1, 0.0)}), tick=0))
        # a stays at 0.5 (score 0.5); b jumps to 0.4 with rate 0.3
        # (score 0.4 * (1 + 10*0.3) = 1.6) — b becomes principal.
        states = _by_key(
            reg.step(Inputs({"a": (0.5, 0.0), "b": (0.4, 0.0)}), tick=1, previous=prev)
        )
        assert states["b"].is_principal
        assert not states["a"].is_principal

    def test_exactly_one_principal(self) -> None:
        reg = _registry("a", "b", "c")
        states = reg.step(Inputs({"a": (0.2, 0.0), "b": (0.2, 0.0), "c": (0.2, 0.0)}), tick=0)
        assert sum(1 for s in states if s.is_principal) == 1

    def test_tie_breaks_lexicographically(self) -> None:
        reg = _registry("zeta", "alpha")
        states = _by_key(reg.step(Inputs({"zeta": (0.5, 0.0), "alpha": (0.5, 0.0)}), tick=0))
        assert states["alpha"].is_principal


class TestLeadingPole:
    def test_sign_of_balance_selects_pole(self) -> None:
        reg = _registry("x")
        neg = reg.step(Inputs({"x": (0.5, -0.3)}), tick=0)
        pos = reg.step(Inputs({"x": (0.5, 0.3)}), tick=0)
        assert neg[0].leading_pole == "a"
        assert pos[0].leading_pole == "b"

    def test_zero_balance_defaults_to_pole_a_initially(self) -> None:
        reg = _registry("x")
        states = reg.step(Inputs({"x": (0.5, 0.0)}), tick=0)
        assert states[0].leading_pole == "a"

    def test_zero_balance_holds_previous_pole(self) -> None:
        """Inertia: the principal aspect persists until actually overturned."""
        reg = _registry("x")
        prev = _by_key(reg.step(Inputs({"x": (0.5, 0.4)}), tick=0))
        assert prev["x"].leading_pole == "b"
        states = reg.step(Inputs({"x": (0.5, 0.0)}), tick=1, previous=prev)
        assert states[0].leading_pole == "b"


class TestValidation:
    def test_duplicate_keys_rejected(self) -> None:
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            OppositionRegistry(bindings=[_measure_for("k"), _measure_for("k")])

    def test_negative_rate_weight_rejected(self) -> None:
        with pytest.raises(ValueError, match="rate_weight"):
            OppositionRegistry(bindings=[], rate_weight=-1.0)

    def test_gap_reading_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            GapReading(gap=1.5, balance=0.0)
        with pytest.raises(ValidationError):
            GapReading(gap=0.5, balance=-2.0)

    def test_spec_requires_key(self) -> None:
        with pytest.raises(ValidationError):
            OppositionSpec(key="", pole_a="a", pole_b="b")


class TestPoleBinding:
    """VIII.9 n-ary protection: a pole references at most one collective."""

    def test_plain_label_binding_is_valid(self) -> None:
        binding = PoleBinding(label="Wage labor")
        assert binding.opposition_key == ""
        assert binding.community_id == ""

    def test_nesting_binding_is_valid(self) -> None:
        assert PoleBinding(label="Core", opposition_key="capital_labor").opposition_key

    def test_community_binding_is_valid(self) -> None:
        assert PoleBinding(label="Wayne County", community_id="H:882a").community_id

    def test_opposition_key_and_community_id_mutually_exclusive(self) -> None:
        with pytest.raises(ValidationError, match="mutually exclusive"):
            PoleBinding(label="both", opposition_key="capital_labor", community_id="H:882a")

    def test_label_is_required(self) -> None:
        with pytest.raises(ValidationError):
            PoleBinding(label="")


class TestApparatusFlavor:
    """Opposition-to-apparatus has no oppressor community on the apparatus pole."""

    def test_default_flavor_is_contradiction(self) -> None:
        assert OppositionSpec(key="k", pole_a="a", pole_b="b").flavor == "contradiction"

    def test_apparatus_pole_may_not_be_a_community(self) -> None:
        with pytest.raises(ValidationError, match="apparatus"):
            OppositionSpec(
                key="carceral",
                pole_a="prisoner",
                pole_b="prison system",
                flavor="apparatus",
                binding_b=PoleBinding(label="prison system", community_id="H:jail"),
            )

    def test_apparatus_pole_as_plain_label_is_valid(self) -> None:
        spec = OppositionSpec(
            key="carceral",
            pole_a="prisoner",
            pole_b="prison system",
            flavor="apparatus",
            binding_b=PoleBinding(label="prison system"),
        )
        assert spec.flavor == "apparatus"

    def test_contradiction_flavor_allows_community_on_either_pole(self) -> None:
        spec = OppositionSpec(
            key="national",
            pole_a="settler",
            pole_b="internal nation",
            binding_b=PoleBinding(label="internal nation", community_id="H:nation"),
        )
        assert spec.binding_b is not None
        assert spec.binding_b.community_id == "H:nation"


def _nesting_spec(key: str, *, a_ref: str = "", b_ref: str = "") -> BoundOpposition[Inputs]:
    """A binding whose poles may nest other oppositions (measure is inert here)."""
    spec = OppositionSpec(
        key=key,
        pole_a=f"{key}-A",
        pole_b=f"{key}-B",
        binding_a=PoleBinding(label=f"{key}-A", opposition_key=a_ref) if a_ref else None,
        binding_b=PoleBinding(label=f"{key}-B", opposition_key=b_ref) if b_ref else None,
    )

    def measure(_inputs: Inputs) -> GapReading:
        return GapReading(gap=0.0, balance=0.0)

    return BoundOpposition(spec=spec, measure=measure)


class TestNestingValidation:
    def test_plain_registry_has_no_nesting_constraints(self) -> None:
        # Backward compatibility: bindings without pole references validate fine.
        reg = _registry("a", "b", "c")
        assert reg.keys == ("a", "b", "c")

    def test_reference_to_unregistered_key_raises_keyerror(self) -> None:
        with pytest.raises(KeyError, match="ghost"):
            OppositionRegistry(bindings=[_nesting_spec("outer", a_ref="ghost")])

    def test_direct_cycle_is_rejected_and_named(self) -> None:
        with pytest.raises(ValueError, match=r"cycle.*(a.*b|b.*a)"):
            OppositionRegistry(
                bindings=[_nesting_spec("a", a_ref="b"), _nesting_spec("b", a_ref="a")]
            )

    def test_self_reference_is_a_cycle(self) -> None:
        with pytest.raises(ValueError, match="cycle"):
            OppositionRegistry(bindings=[_nesting_spec("loop", a_ref="loop")])

    def test_depth_within_bound_is_accepted(self) -> None:
        # Chain of exactly MAX_NESTING_DEPTH (4): d4 -> d3 -> d2 -> d1.
        assert MAX_NESTING_DEPTH == 4
        reg = OppositionRegistry(
            bindings=[
                _nesting_spec("d1"),
                _nesting_spec("d2", a_ref="d1"),
                _nesting_spec("d3", a_ref="d2"),
                _nesting_spec("d4", a_ref="d3"),
            ]
        )
        assert set(reg.keys) == {"d1", "d2", "d3", "d4"}

    def test_depth_beyond_bound_is_rejected(self) -> None:
        # Chain of 5 (depth 5) exceeds MAX_NESTING_DEPTH=4.
        with pytest.raises(ValueError, match="depth"):
            OppositionRegistry(
                bindings=[
                    _nesting_spec("d1"),
                    _nesting_spec("d2", a_ref="d1"),
                    _nesting_spec("d3", a_ref="d2"),
                    _nesting_spec("d4", a_ref="d3"),
                    _nesting_spec("d5", a_ref="d4"),
                ]
            )


@dataclass(frozen=True)
class ZoneInputs:
    """Live inputs for the fractal four-node recursion fixture."""

    core_pair: tuple[float, float]
    periphery_pair: tuple[float, float]


def _zone_measure(attr: str):  # type: ignore[no-untyped-def]
    def measure(inputs: ZoneInputs) -> GapReading:
        a, b = getattr(inputs, attr)
        return GapReading(
            gap=calculate_wealth_asymmetry_gap(a, b),
            balance=calculate_wealth_asymmetry_balance(a, b),
        )

    return measure


class TestFourNodeRecursion:
    """{Core, Periphery} × {Bourgeoisie, Proletariat} — must COMPUTE, not just build."""

    def _fixture(self) -> OppositionRegistry[ZoneInputs]:
        core = BoundOpposition(
            spec=OppositionSpec(
                key="core_capital_labor",
                pole_a="Core Proletariat",
                pole_b="Core Bourgeoisie",
                antagonistic=True,
            ),
            measure=_zone_measure("core_pair"),
        )
        periphery = BoundOpposition(
            spec=OppositionSpec(
                key="periphery_capital_labor",
                pole_a="Periphery Proletariat",
                pole_b="Periphery Bourgeoisie",
                antagonistic=True,
            ),
            measure=_zone_measure("periphery_pair"),
        )
        outer_spec = OppositionSpec(
            key="imperial_nested",
            pole_a="Core",
            pole_b="Periphery",
            binding_a=PoleBinding(label="Core", opposition_key="core_capital_labor"),
            binding_b=PoleBinding(label="Periphery", opposition_key="periphery_capital_labor"),
            antagonistic=True,
        )
        outer = sum_(outer_spec, core, periphery)
        return OppositionRegistry(bindings=[core, periphery, outer])

    def test_fixture_constructs_with_valid_nesting(self) -> None:
        reg = self._fixture()
        assert set(reg.keys) == {
            "core_capital_labor",
            "periphery_capital_labor",
            "imperial_nested",
        }

    def test_outer_carries_composition_provenance_and_bindings(self) -> None:
        outer = self._fixture().spec_for("imperial_nested")
        assert outer.composition == "sum"
        assert outer.component_keys == ("core_capital_labor", "periphery_capital_labor")
        assert outer.binding_a is not None
        assert outer.binding_a.opposition_key == "core_capital_labor"

    def test_outer_gap_responds_to_inner_pair_wealth(self) -> None:
        reg = self._fixture()
        base = {
            s.key: s
            for s in reg.step(
                ZoneInputs(core_pair=(10.0, 10.0), periphery_pair=(5.0, 20.0)), tick=0
            )
        }
        base_outer = base["imperial_nested"].gap
        # Sharpen the CORE inner pair; the outer (⊕) gap must rise in response.
        sharpened = {
            s.key: s
            for s in reg.step(ZoneInputs(core_pair=(1.0, 50.0), periphery_pair=(5.0, 20.0)), tick=1)
        }
        assert sharpened["core_capital_labor"].gap > base["core_capital_labor"].gap
        assert sharpened["imperial_nested"].gap > base_outer


class TestGovernance:
    """Sublation lineage: a successor GOVERNS its predecessor's motion."""

    def _governed(self) -> OppositionRegistry[Inputs]:
        return OppositionRegistry(
            bindings=[_measure_for("capital_labor"), _measure_for("party")],
            governance={"capital_labor": "party"},
        )

    def test_default_state_has_empty_lineage(self) -> None:
        (state,) = _registry("solo").step(Inputs({"solo": (0.5, 0.0)}), tick=0)
        assert state.governed_by == ""
        assert state.successor_key == ""

    def test_governed_state_carries_its_successor(self) -> None:
        states = _by_key(
            self._governed().step(
                Inputs({"capital_labor": (0.9, 0.0), "party": (0.1, 0.0)}), tick=0
            )
        )
        assert states["capital_labor"].governed_by == "party"
        assert states["capital_labor"].successor_key == "party"
        # The successor itself is ungoverned.
        assert states["party"].governed_by == ""
        assert states["party"].successor_key == ""

    def test_governed_opposition_is_never_principal_even_with_top_score(self) -> None:
        # capital_labor carries the largest gap/score, yet the successor leads.
        states = _by_key(
            self._governed().step(
                Inputs({"capital_labor": (0.9, 0.0), "party": (0.1, 0.0)}), tick=0
            )
        )
        assert not states["capital_labor"].is_principal
        assert states["party"].is_principal

    def test_unregistered_predecessor_rejected(self) -> None:
        with pytest.raises(KeyError, match="ghost"):
            OppositionRegistry(bindings=[_measure_for("party")], governance={"ghost": "party"})

    def test_unregistered_successor_rejected(self) -> None:
        with pytest.raises(KeyError, match="ghost"):
            OppositionRegistry(bindings=[_measure_for("cl")], governance={"cl": "ghost"})

    def test_governance_cycle_rejected(self) -> None:
        with pytest.raises(ValueError, match="cycle"):
            OppositionRegistry(
                bindings=[_measure_for("a"), _measure_for("b")],
                governance={"a": "b", "b": "a"},
            )

    def test_governance_chain_within_bound_is_accepted(self) -> None:
        # a->b->c->d is depth 4 (== MAX_NESTING_DEPTH).
        reg = OppositionRegistry(
            bindings=[_measure_for(k) for k in ("a", "b", "c", "d")],
            governance={"a": "b", "b": "c", "c": "d"},
        )
        assert set(reg.keys) == {"a", "b", "c", "d"}

    def test_governance_chain_beyond_bound_is_rejected(self) -> None:
        # a->b->c->d->e is depth 5 (> MAX_NESTING_DEPTH=4).
        with pytest.raises(ValueError, match="depth"):
            OppositionRegistry(
                bindings=[_measure_for(k) for k in ("a", "b", "c", "d", "e")],
                governance={"a": "b", "b": "c", "c": "d", "d": "e"},
            )
