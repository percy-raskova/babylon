"""Unit tests for :mod:`babylon.dialectics.core.regime` — fixed-point regimes.

Three outcomes of the one Picard operator (§9.4): reproduction (converged),
crisis (diverging within the level), sublation (resolved at a higher level).
The county-rooted spatial lattice supplies the Aufhebung probe; fields are
chosen so resolution is hand-computable (single state ``26``).
"""

from __future__ import annotations

import pytest

from babylon.dialectics.core.opposition import OppositionState
from babylon.dialectics.core.regime import classify_regime
from babylon.dialectics.instances.levels import spatial_lattice_for_counties

pytestmark = pytest.mark.math

_EPS = 1e-4
_COUNTY = 1  # capital_labor's level index in the county-rooted lattice


def _state(rate: float, *, is_principal: bool = True, gap: float = 0.5) -> OppositionState:
    return OppositionState(
        key="capital_labor",
        tick=1,
        gap=gap,
        balance=0.0,
        rate=rate,
        leading_pole="b",
        is_principal=is_principal,
    )


def _lattice() -> object:
    return spatial_lattice_for_counties(["26001", "26002"])


_RESOLVED = {"26001": 2.0, "26002": 2.0}  # flat within state 26 -> resolves at state
_UNRESOLVED = {"26001": 2.0, "26002": 10.0}  # varies within state -> resolves nowhere


class TestReproduction:
    def test_converged_rate_is_reproduction(self) -> None:
        regime = classify_regime([_state(0.0)], _lattice(), _RESOLVED, _COUNTY, rate_epsilon=_EPS)
        assert regime == "reproduction"

    def test_reproduction_gate_precedes_aufhebung(self) -> None:
        # A CONVERGED principal (|rate| <= eps) whose field resolves upward is
        # reproduction, NOT sublation — the reproduction gate is checked first.
        # (Kills §9.1 mutation probe (b): sublation checked unconditionally.)
        regime = classify_regime(
            [_state(_EPS / 2.0)], _lattice(), _RESOLVED, _COUNTY, rate_epsilon=_EPS
        )
        assert regime == "reproduction"

    def test_falling_gap_is_reproduction(self) -> None:
        # |rate| > eps but the gap is FALLING: the contradiction is contained.
        regime = classify_regime(
            [_state(-0.2)], _lattice(), _UNRESOLVED, _COUNTY, rate_epsilon=_EPS
        )
        assert regime == "reproduction"

    def test_no_principal_is_reproduction(self) -> None:
        regime = classify_regime(
            [_state(0.5, is_principal=False)], _lattice(), _UNRESOLVED, _COUNTY, rate_epsilon=_EPS
        )
        assert regime == "reproduction"


class TestCrisis:
    def test_rising_gap_unresolved_is_crisis(self) -> None:
        regime = classify_regime([_state(0.2)], _lattice(), _UNRESOLVED, _COUNTY, rate_epsilon=_EPS)
        assert regime == "crisis"

    def test_rising_gap_without_lattice_is_crisis(self) -> None:
        # No lattice: the sublation test cannot run, so a rising gap is crisis.
        regime = classify_regime([_state(0.2)], None, {}, _COUNTY, rate_epsilon=_EPS)
        assert regime == "crisis"


class TestSublation:
    def test_rising_gap_resolved_above_is_sublation(self) -> None:
        regime = classify_regime([_state(0.2)], _lattice(), _RESOLVED, _COUNTY, rate_epsilon=_EPS)
        assert regime == "sublation"
