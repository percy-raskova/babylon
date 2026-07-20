"""E3: an all-zeros channel FAILS unless declared at_rest with a reason."""

from __future__ import annotations

import pytest
from tools.regression_scenarios import AtRestChannel, ScenarioCoverage
from tools.regression_test import check_dead_columns

pytestmark = pytest.mark.unit

_COV = ScenarioCoverage(
    scenario="s",
    layers=(),
    systems=(),
    at_rest=(
        AtRestChannel(
            channel="financial_endogenous_rate",
            reason="county-free scenario: no tensors, no interest",
        ),
    ),
)


def test_live_columns_pass() -> None:
    header = ["tick", "C001_wealth"]
    rows = [["0", "1.0"], ["1", "2.0"]]
    assert check_dead_columns("s", header, rows, (_COV,)) == []


def test_declared_at_rest_dead_column_passes() -> None:
    header = ["tick", "financial_endogenous_rate"]
    rows = [["0", "0.0"], ["1", "0.0"]]
    assert check_dead_columns("s", header, rows, (_COV,)) == []


def test_undeclared_dead_column_fails_naming_it() -> None:
    header = ["tick", "county_26163_interest"]
    rows = [["0", "0.0"], ["1", "0.0"]]
    findings = check_dead_columns("s", header, rows, (_COV,))
    assert len(findings) == 1
    assert "county_26163_interest" in findings[0]
    assert "at_rest" in findings[0]


def test_all_false_bool_column_is_dead() -> None:
    header = ["tick", "C001_active"]
    rows = [["0", "False"], ["1", "False"]]
    findings = check_dead_columns("s", header, rows, ())
    assert len(findings) == 1


def test_at_rest_channel_that_is_actually_live_fails() -> None:
    """A stale at_rest declaration over a live channel is itself a defect."""
    header = ["tick", "financial_endogenous_rate"]
    rows = [["0", "0.0"], ["1", "0.019855"]]
    findings = check_dead_columns("s", header, rows, (_COV,))
    assert len(findings) == 1
    assert "stale at_rest" in findings[0]
