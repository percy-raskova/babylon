"""Tests for the declared measurement-dependency registry.

The coupling graph is a claim ABOUT THE CODE: "``surplus_distribution``
transforms ``debt_spiral``" asserts that the thing computing the debt reading
reads the thing computing the distribution reading. This registry is what makes
that claim checkable — for each opposition, which ``GraphInputs`` fields its
measure reads, which file produces them, and which symbols that file publishes.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.sentinels.coupling.registry import (
    MEASUREMENT_DEPENDENCIES,
    MeasurementDependency,
    dependency_for,
)

pytestmark = pytest.mark.unit


def test_registry_covers_the_four_new_oppositions_and_price_value() -> None:
    """All U5 keys plus the scissors axis they couple to are declared."""
    keys = {row.opposition_key for row in MEASUREMENT_DEPENDENCIES}
    assert {
        "surplus_distribution",
        "debt_spiral",
        "credit",
        "financial",
        "price_value",
    } <= keys


def test_dependency_for_returns_the_row() -> None:
    """Lookup by opposition key returns the declared row."""
    row = dependency_for("financial")
    assert row is not None
    assert "financialization_index" in row.inputs_fields


def test_dependency_for_returns_none_for_unregistered_key() -> None:
    """An unregistered key yields None rather than raising — checks skip it."""
    assert dependency_for("no_such_opposition") is None


def test_price_value_publishes_the_scissors_symbols() -> None:
    """``price_value``'s produces set is what a downstream reader must mention."""
    row = dependency_for("price_value")
    assert row is not None
    assert "market_balance" in row.produces_symbols
    assert "price_log" in row.produces_symbols


def test_row_rejects_empty_inputs_fields() -> None:
    """An opposition with no measured input is not a measurement dependency."""
    with pytest.raises(ValidationError, match="inputs_fields"):
        MeasurementDependency(
            opposition_key="broken",
            inputs_fields=(),
            producer_file="src/babylon/engine/systems/contradiction.py",
            produces_symbols=("x",),
        )


def test_row_rejects_a_non_python_producer_file() -> None:
    """The producer file must be ``.py`` source the AST sensor can read."""
    with pytest.raises(ValidationError, match=r"\.py"):
        MeasurementDependency(
            opposition_key="broken",
            inputs_fields=("x",),
            producer_file="src/babylon/engine/systems/contradiction.yaml",
            produces_symbols=("x",),
        )
