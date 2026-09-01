"""Safety and native-type contracts for analysis override/range grammar."""

from __future__ import annotations

import math

import pytest
from tools.devtools.sim_analysis.ranges import (
    expand_range,
    parse_override,
    parse_range,
)


def test_integer_override_is_parsed_as_native_int() -> None:
    path, value = parse_override("crisis.crisis_period_ticks=7")

    assert path == "crisis.crisis_period_ticks"
    assert value == 7
    assert type(value) is int


def test_fractional_integer_override_is_refused() -> None:
    with pytest.raises(ValueError, match="cannot use fractional value"):
        parse_override("crisis.crisis_period_ticks=7.5")


@pytest.mark.parametrize("value", ["nan", "NaN", "inf", "+Infinity", "-inf"])
def test_non_finite_override_is_refused(value: str) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        parse_override(f"economy.extraction_efficiency={value}")


@pytest.mark.parametrize(
    "range_spec",
    [
        "nan:1:0.1",
        "0:inf:0.1",
        "0:1:-inf",
    ],
)
def test_non_finite_range_component_is_refused(range_spec: str) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        parse_range(f"economy.extraction_efficiency={range_spec}")


def test_reversed_range_is_refused_instead_of_returning_empty() -> None:
    with pytest.raises(ValueError, match="start must not exceed end"):
        parse_range("economy.extraction_efficiency=1:0:0.1")


def test_direct_non_finite_range_is_refused_before_expansion() -> None:
    with pytest.raises(ValueError, match="range start must be finite"):
        expand_range(-math.inf, math.inf, 1.0)


def test_integer_range_expands_to_native_ints() -> None:
    path, values = parse_range("crisis.crisis_period_ticks=1:7:2")

    assert path == "crisis.crisis_period_ticks"
    assert values == [1, 3, 5, 7]
    assert all(type(value) is int for value in values)


def test_integer_range_refuses_fractional_components() -> None:
    with pytest.raises(ValueError, match="requires integer range components"):
        parse_range("crisis.crisis_period_ticks=1:7.5:1")


def test_range_size_is_bounded() -> None:
    with pytest.raises(ValueError, match="maximum is"):
        expand_range(0, 1_000_000, 1)


def test_underflow_sized_step_is_refused_without_iterating() -> None:
    with pytest.raises(ValueError, match="range step count must be finite"):
        expand_range(0.0, 1.0, math.nextafter(0.0, math.inf))
