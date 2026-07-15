"""Smoke tests for the partition-sentinel probe harness (Program 19, ADR070).

The pure analyzer is covered in ``tests/unit/sentinels/test_partition_sentinel``;
this verifies the engine-running harness end-to-end on the cheapest synthetic
scenario: a persistent-graph run that actually collects per-tick stashes and
produces a structurally sound report. ``wayne_county`` is deliberately NOT
probed here — it reads the local reference DB, which tests/CI must never
touch (owner ruling 2026-07-14); it is a dev-box CLI run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from babylon.sentinels.partition.checks import PartitionReport
from babylon.sentinels.partition.registry import PRINCIPAL_AXES

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import partition_probe as pp  # type: ignore[import-not-found]  # noqa: E402

pytestmark = pytest.mark.unit


def test_probe_two_node_smoke() -> None:
    report = pp.run_probe("two_node", ticks=3)

    assert isinstance(report, PartitionReport)
    assert report.scenario == "two_node"
    assert report.ticks == 3
    assert report.class_node_count == 2
    assert tuple(axis for axis, _ in report.unpositioned) == PRINCIPAL_AXES
    # Rate is either honestly absent (no cell-bearing node) or a probability.
    if report.agreement_rate is not None:
        assert 0.0 <= report.agreement_rate <= 1.0


def test_probe_scenarios_match_regression_scenarios() -> None:
    import regression_test as rt  # type: ignore[import-not-found]

    assert tuple(sorted(rt.SCENARIOS)) == pp.PROBE_SCENARIOS
    assert pp.WAYNE not in pp.PROBE_SCENARIOS
