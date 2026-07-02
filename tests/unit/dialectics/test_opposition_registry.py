"""Unit tests for :mod:`babylon.dialectics.core.opposition`.

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

from babylon.dialectics.core.opposition import (
    BoundOpposition,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
    OppositionState,
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
