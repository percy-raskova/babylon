"""Tests for the ``pacing_probe`` management command (spec-116 Task 6).

Headless null-play instrument: runs the real engine ``step()`` loop
in-memory (no DB) while an ``EndgameDetector`` observes, then writes a
JSON report. These are fast unit tests on tiny scenarios/tick counts —
the calibration runs (``us``/``wayne_county`` at 5200 ticks) are exercised
manually per ``reports/pacing-calibration-2026-07-17.md``, not in CI.
"""

from __future__ import annotations

import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

pytestmark = pytest.mark.unit


def test_pacing_probe_produces_report(tmp_path) -> None:
    """The command writes a JSON report with the documented shape."""
    report = tmp_path / "r.json"
    call_command("pacing_probe", scenario="two_node", ticks=3, seed=0, report=str(report))
    data = json.loads(report.read_text())
    assert data["ticks_completed"] == 3
    assert set(data["first_recognition"]) == {
        "revolutionary_victory",
        "ecological_collapse",
        "fascist_consolidation",
        "red_ogv",
        "fragmented_collapse",
    }
    assert data["event_type_counts"]  # non-empty histogram


def test_pacing_probe_rejects_out_of_range_ticks(tmp_path) -> None:
    """``--ticks`` is argparse-validated to [1, 10000] (Power-of-10 rule 2).

    Invoked CLI-style (raw ``--flag value`` tokens, not keyword arguments) so
    the value actually round-trips through ``argparse``'s ``type=`` callable
    — ``call_command``'s keyword-argument path bypasses ``type=`` conversion
    for non-required options (Django ``call_command`` merges ``**options``
    over the parsed defaults verbatim).
    """
    report = tmp_path / "r.json"
    with pytest.raises(CommandError):
        call_command(
            "pacing_probe",
            "--scenario",
            "two_node",
            "--ticks",
            "10001",
            "--seed",
            "0",
            "--report",
            str(report),
        )
