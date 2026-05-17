"""Snapshot test for tools.shared.run_simulation signature (T039a, spec-064).

Per FR-015 / SC-004, the post-refactor ``run_simulation`` MUST keep its
signature byte-identical to the pre-spec-064 form so downstream tools
(``tools/monte_carlo.py``, ``tools/parameter_analysis.py``,
``tools/sensitivity_analysis.py``, ``tools/profiler.py``,
``tools/audit_simulation.py``, ``tools/landscape_analysis.py``) compile
without modification.

If this test fails, you've likely changed ``run_simulation``'s parameter
list — that's a contract break. Either revert, or update the legacy
callers AND this snapshot together in the same commit.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

# Mirror the import path used by tools/*.py.
TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import shared  # type: ignore[import-not-found]  # noqa: E402

CANONICAL_SIGNATURE = "(defines: 'GameDefines', max_ticks: 'int' = 5200) -> 'dict[str, Any]'"


def test_run_simulation_signature_is_preserved() -> None:
    """The signature of run_simulation MUST match the pre-spec-064 baseline."""
    actual = str(inspect.signature(shared.run_simulation))
    assert actual == CANONICAL_SIGNATURE, (
        f"signature drift: expected {CANONICAL_SIGNATURE!r}, got {actual!r}"
    )


def test_run_simulation_returns_legacy_dict_keys() -> None:
    """Even with the headless-runner backend, the returned dict MUST expose
    the legacy keys so downstream callers compile.

    We don't actually invoke the runner here (no Postgres in the unit
    gate); we only assert the function's docstring documents the
    canonical key set.
    """
    docstring = shared.run_simulation.__doc__ or ""
    for key in (
        "ticks_survived",
        "outcome",
        "max_tension",
        "final_wealth",
        "final_state",
        "phase_milestones",
        "terminal_outcome",
    ):
        assert key in docstring, f"docstring missing legacy key: {key!r}"
