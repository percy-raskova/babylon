"""Unit tests for Bug A — hex_hydrator Marx accounting (spec-066 US1).

Spec: 066-marx-coherence-fixes (T012-T014).

These tests verify the formula change `s = max(0, GDP/52 - v)` (NOT
`max(0, GDP/52 - v - c)`), the addition of `industry_id = 1` to the QCEW
SUM query, and the emission of a `severity='alarm'` audit row when the
raw residual is negative.

Mock the SQLite reads so these tests can run without Postgres or the
reference DB.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


def test_s_formula_uses_value_added_identity() -> None:
    """T012: hex_hydrator computes s = max(0, GDP/52 - v), not GDP/52 - v - c."""
    pytest.skip("WIP — implemented in spec-066 US1 phase (T018 changes hex_hydrator.py:373)")


def test_qcew_query_filters_industry_id_1() -> None:
    """T013: QCEW SUM query includes `AND fq.industry_id = 1` in WHERE clause."""
    pytest.skip("WIP — implemented in spec-066 US1 phase (T019 adds filter)")


def test_negative_residual_emits_alarm_audit_row() -> None:
    """T014: when GDP/52 < v, an audit row with severity='alarm' and
    invariant_name='s_residual_negative' is emitted."""
    pytest.skip("WIP — implemented in spec-066 US1 phase (T020 adds alarm emission)")
