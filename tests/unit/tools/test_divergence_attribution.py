"""E4: on dense divergence the tool attributes (tick, system, channel, county)."""

from __future__ import annotations

import pytest
from tools.regression_test import DivergenceReport, attribute_divergence

pytestmark = pytest.mark.unit

_HEADER = [
    "tick",
    "economy_imperial_rent_pool",
    "C001_wealth",
    "county_26163_interest",
    "edge_C001_C002_tension",
]


def _rows(*rows: list[str]) -> list[list[str]]:
    return [list(r) for r in rows]


def test_no_divergence_returns_none() -> None:
    rows = _rows(["0", "1.0", "2.0", "3.0", "0.1"], ["1", "1.1", "2.1", "3.1", "0.2"])
    assert attribute_divergence("s", _HEADER, rows, rows) is None


def test_first_divergence_is_attributed() -> None:
    expected = _rows(["0", "1.0", "2.0", "0.0", "0.1"], ["1", "1.1", "2.5", "0.0", "0.2"])
    actual = _rows(["0", "1.0", "2.0", "0.0", "0.1"], ["1", "1.1", "2.9", "0.0", "0.2"])
    report: DivergenceReport | None = attribute_divergence(
        "imperial_circuit", _HEADER, expected, actual
    )
    assert report is not None
    assert report.tick == 1
    assert report.column == "C001_wealth"
    assert report.channel == "wealth"
    assert report.county is None
    assert report.magnitude == pytest.approx(0.4)
    assert report.last_agreeing_tick == 0
    assert "VitalitySystem" in report.candidate_systems


def test_county_column_yields_county() -> None:
    expected = _rows(["0", "1", "2", "0.0", "0.1"], ["1", "1", "2", "5.0", "0.1"])
    actual = _rows(["0", "1", "2", "0.0", "0.1"], ["1", "1", "2", "6.0", "0.1"])
    report = attribute_divergence("single_county", _HEADER, expected, actual)
    assert report is not None
    assert report.county == "26163"
    assert report.channel == "interest"


def test_row_count_mismatch_attributes_the_missing_tick() -> None:
    expected = _rows(["0", "1", "2", "0", "0"], ["1", "1", "2", "0", "0"])
    actual = _rows(["0", "1", "2", "0", "0"])
    report = attribute_divergence("s", _HEADER, expected, actual)
    assert report is not None
    assert report.tick == 1
    assert report.channel == "<missing row>"


def test_non_numeric_divergence_has_none_magnitude() -> None:
    expected = _rows(["0", "1", "2", "0", "0"], ["1", "1", "True", "0", "0"])
    actual = _rows(["0", "1", "2", "0", "0"], ["1", "1", "False", "0", "0"])
    report = attribute_divergence("s", _HEADER, expected, actual)
    assert report is not None
    assert report.magnitude is None


def test_financial_column_attributes_to_tick_dynamics_system() -> None:
    header = ["tick", "financial_endogenous_rate"]
    expected = _rows(["0", "0.01"], ["1", "0.02"])
    actual = _rows(["0", "0.01"], ["1", "0.03"])
    report = attribute_divergence("s", header, expected, actual)
    assert report is not None
    assert report.channel == "financial_endogenous_rate"
    assert report.candidate_systems == ("TickDynamicsSystem",)


def test_county_interest_column_attributes_to_tick_dynamics_system() -> None:
    header = ["tick", "county_26163_interest"]
    expected = _rows(["0", "0.0"], ["1", "5.0"])
    actual = _rows(["0", "0.0"], ["1", "6.0"])
    report = attribute_divergence("s", header, expected, actual)
    assert report is not None
    assert report.county == "26163"
    assert report.channel == "interest"
    assert report.candidate_systems == ("TickDynamicsSystem",)


def test_edge_value_flow_column_yields_full_channel_name() -> None:
    header = ["tick", "edge_C001_C002_value_flow"]
    expected = _rows(["0", "0.0"], ["1", "5.0"])
    actual = _rows(["0", "0.0"], ["1", "6.0"])
    report = attribute_divergence("s", header, expected, actual)
    assert report is not None
    assert report.channel == "value_flow"
    assert report.candidate_systems != ()
