"""Behavioral contract for the grain-agnostic equalization law (P25 U9, ADR135).

``equalization_deltas`` is the pure core of ``Δc = α(r − r̄)c`` extracted from
``DefaultHexEqualizationComputer`` so the U9 capital-strike arm can apply THE
SAME operator at county grain (the hex lane's ``services.hex_grid`` is None in
every production path). Conservation (``ΣΔc = 0``) holds by the c-weighted
mean construction; non-negativity by proportional scaling.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.substrate.equalization import (
    DefaultHexEqualizationComputer,
    equalization_deltas,
)
from babylon.domain.economics.substrate.types import HexEconomicState, HexGrid

pytestmark = pytest.mark.unit


class TestEqualizationDeltas:
    def test_conservation_sum_is_zero(self) -> None:
        capital = {"a": 100.0, "b": 300.0, "c": 50.0}
        rates = {"a": 0.02, "b": 0.10, "c": 0.05}
        deltas = equalization_deltas(capital, rates, alpha=0.05)
        assert sum(deltas.values()) == pytest.approx(0.0, abs=1e-12)

    def test_capital_flows_up_the_rate_gradient(self) -> None:
        capital = {"low": 100.0, "high": 100.0}
        rates = {"low": 0.01, "high": 0.20}
        deltas = equalization_deltas(capital, rates, alpha=0.1)
        assert deltas["low"] < 0.0 < deltas["high"]

    def test_uniform_rates_move_nothing(self) -> None:
        capital = {"a": 100.0, "b": 400.0}
        rates = {"a": 0.07, "b": 0.07}
        deltas = equalization_deltas(capital, rates, alpha=0.1)
        assert deltas == {"a": pytest.approx(0.0), "b": pytest.approx(0.0)}

    def test_non_negativity_scaling_preserves_conservation(self) -> None:
        """A delta that would overdraw a unit scales ALL deltas down —
        linearity keeps ΣΔc = 0 and every post-step c ≥ 0."""
        capital = {"tiny": 1.0, "big": 1000.0}
        rates = {"tiny": 0.0, "big": 0.5}
        deltas = equalization_deltas(capital, rates, alpha=10.0)
        assert capital["tiny"] + deltas["tiny"] >= 0.0
        assert sum(deltas.values()) == pytest.approx(0.0, abs=1e-9)

    def test_empty_and_single_unit_domains_are_static(self) -> None:
        assert equalization_deltas({}, {}, alpha=0.1) == {}
        assert equalization_deltas({"only": 50.0}, {"only": 0.3}, alpha=0.1) == {
            "only": pytest.approx(0.0)
        }

    def test_zero_capital_units_neither_send_nor_receive_from_formula(self) -> None:
        capital = {"empty": 0.0, "rich": 100.0, "poor": 100.0}
        rates = {"empty": 0.0, "rich": 0.2, "poor": 0.0}
        deltas = equalization_deltas(capital, rates, alpha=0.1)
        assert deltas["empty"] == pytest.approx(0.0)

    def test_hex_computer_delegates_to_the_same_law(self) -> None:
        """The rentless hex path and the pure law produce identical deltas —
        one operator, two grains (the wiring-doctrine honesty condition)."""
        hexes = {
            "8a2a1072b59ffff": HexEconomicState(
                h3_index="8a2a1072b59ffff",
                county_fips="26163",
                constant_capital=100.0,
                variable_capital=50.0,
                surplus_value=30.0,
                employment=10.0,
                dept_shares=(0.25, 0.25, 0.25, 0.25),
            ),
            "8a2a1072b5affff": HexEconomicState(
                h3_index="8a2a1072b5affff",
                county_fips="26125",
                constant_capital=200.0,
                variable_capital=40.0,
                surplus_value=5.0,
                employment=10.0,
                dept_shares=(0.25, 0.25, 0.25, 0.25),
            ),
        }
        grid = HexGrid(
            hexes=hexes,
            county_hex_ids={},
            res6_parents={},
            res5_parents={},
            res6_children={},
            res5_children={},
        )
        result = DefaultHexEqualizationComputer().equalize_capital(grid, alpha=0.05)
        rates = {
            h: hs.surplus_value / (hs.constant_capital + hs.variable_capital)
            for h, hs in hexes.items()
        }
        capital = {h: hs.constant_capital for h, hs in hexes.items()}
        deltas = equalization_deltas(capital, rates, alpha=0.05)
        for h3_id, hex_state in hexes.items():
            assert result.hexes[h3_id].constant_capital == pytest.approx(
                hex_state.constant_capital + deltas[h3_id]
            )
