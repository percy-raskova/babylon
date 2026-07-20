"""Tests for the agent-legible sentinel finding formatter.

Every U7 sensor emits its findings through :func:`babylon.sentinels.report.finding`
so that a coding agent reading a red gate always gets the same five facts in the
same order: which error CLASS, which SYMBOL, where (``file:line``), what is
WRONG, and what to DO.
"""

from __future__ import annotations

import pytest

from babylon.sentinels.report import finding

pytestmark = pytest.mark.unit


def test_finding_contains_all_five_fields_in_order() -> None:
    """The rendered string carries class, symbol, file:line, problem, remedy."""
    rendered = finding(
        error_class="computed-but-never-consumed",
        symbol="POLE_READINGS_ATTR",
        file="src/babylon/engine/systems/contradiction.py",
        line=89,
        problem="written to the graph but no production module reads it",
        remedy="add a consumer_file to the liveness registry row, or declare dormant_reason",
    )
    assert rendered.startswith("[computed-but-never-consumed]")
    assert "POLE_READINGS_ATTR" in rendered
    assert "src/babylon/engine/systems/contradiction.py:89" in rendered
    assert "written to the graph but no production module reads it" in rendered
    assert rendered.endswith(
        "REMEDY: add a consumer_file to the liveness registry row, or declare dormant_reason"
    )


def test_finding_accepts_line_zero_for_file_level_findings() -> None:
    """Line 0 means 'the whole file', and renders without a line suffix."""
    rendered = finding(
        error_class="gate-blindness",
        symbol="create_financial_services",
        file="tools/regression_test.py",
        line=0,
        problem="the gate harness injects none of this factory's service keys",
        remedy="build calculator_overrides from the committed FRED fixture",
    )
    assert "tools/regression_test.py " in rendered
    assert "tools/regression_test.py:0" not in rendered


def test_finding_rejects_a_blank_remedy() -> None:
    """A finding without a remedy is not agent-legible and is refused loudly."""
    with pytest.raises(ValueError, match="remedy"):
        finding(
            error_class="correct-but-inert",
            symbol="SomeSystem",
            file="src/babylon/engine/systems/some.py",
            line=1,
            problem="runs but nothing reads its outputs",
            remedy="   ",
        )


def test_finding_rejects_a_blank_error_class() -> None:
    """The error class names the failure taxonomy; blank is refused loudly."""
    with pytest.raises(ValueError, match="error_class"):
        finding(
            error_class="",
            symbol="SomeSystem",
            file="src/babylon/engine/systems/some.py",
            line=1,
            problem="runs but nothing reads its outputs",
            remedy="wire a consumer",
        )
