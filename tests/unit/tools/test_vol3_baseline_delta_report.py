"""Structural contract for reports/vol3-baseline-delta.md (U8.3).

Does not assert on the FILLED content (scenario-specific numbers only
exist once someone has actually run qa:regression against the real U1-U7
diff -- that's U8.2's job) -- it asserts the document's required shape: a
title, an unmissable Owner Approval Gate section, and one dated subsection
per scenario in tools/regression_test.py's own SCENARIOS dict, so the
report can never silently drop a scenario the gate actually covers.
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import regression_test as rt  # type: ignore[import-not-found]  # noqa: E402

REPORT_PATH = Path(__file__).resolve().parents[3] / "reports" / "vol3-baseline-delta.md"


def test_report_exists() -> None:
    assert REPORT_PATH.exists(), f"missing {REPORT_PATH} -- see design spec U8"


def test_report_has_owner_approval_gate_section() -> None:
    text = REPORT_PATH.read_text()
    assert "## Owner Approval Gate" in text
    assert "STOP" in text


def test_report_has_one_section_per_scenario() -> None:
    text = REPORT_PATH.read_text()
    for scenario_name in rt.SCENARIOS:
        assert f"### {scenario_name}" in text, (
            f"reports/vol3-baseline-delta.md is missing a section for "
            f"scenario {scenario_name!r} -- every SCENARIOS entry must be covered"
        )


def test_report_scenario_sections_require_named_mechanism() -> None:
    text = REPORT_PATH.read_text()
    assert "Named mechanism" in text
    assert "Materiality argument" in text
    assert "Principal contradiction" in text


def test_report_has_no_unfilled_placeholders_outside_the_approval_gate() -> None:
    """Every <FILL> must be resolved before the report is evidence.

    The three Owner Approval Gate fields are the ONLY legitimate remaining
    placeholders at U8.3 time — U8.4 fills those, and U8.5's Step 1 grep
    gate refuses to proceed while they are unfilled.
    """
    text = REPORT_PATH.read_text()
    remaining = text.count("<FILL")
    assert remaining <= 3, (
        f"reports/vol3-baseline-delta.md still has {remaining} <FILL> markers; "
        "only the three Owner Approval Gate fields may remain unfilled at U8.3"
    )
