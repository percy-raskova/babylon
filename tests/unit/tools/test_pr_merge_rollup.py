"""Tests for ``tools.pr_merge._rollup_failures`` duplicate-check semantics.

A re-run (flake retry, close/reopen refire) leaves MULTIPLE rollup entries
for the same check name on the same head SHA. GitHub branch protection
evaluates the LATEST run per context; the merge gate must do the same,
or a superseded failure poisons the verdict forever (bit PR #673 on
2026-08-21: three stale Security Audit failures outvoted the fresh pass).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "pr_merge", Path(__file__).resolve().parents[3] / "tools" / "pr_merge.py"
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("tools/pr_merge.py failed import-spec resolution")
pr_merge = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pr_merge)


def _entry(
    name: str,
    conclusion: str,
    started_at: str,
    status: str = "COMPLETED",
) -> dict[str, str]:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "startedAt": started_at,
        "completedAt": started_at,
    }


def _criticals_green() -> list[dict[str, str]]:
    return [_entry(name, "SUCCESS", "2026-08-21T17:00:00Z") for name in pr_merge.CRITICAL_CHECKS]


class TestRollupFailuresLatestPerCheck:
    def test_stale_failure_does_not_poison_a_fresh_success(self) -> None:
        rollup = [
            _entry("Security Audit", "FAILURE", "2026-08-21T17:30:44Z"),
            _entry("Security Audit", "FAILURE", "2026-08-21T18:11:11Z"),
            _entry("Security Audit", "SUCCESS", "2026-08-21T18:21:15Z"),
        ]
        assert pr_merge._rollup_failures(rollup + _criticals_green()) == []

    def test_latest_failure_still_refuses(self) -> None:
        rollup = [
            _entry("Security Audit", "SUCCESS", "2026-08-21T17:30:44Z"),
            _entry("Security Audit", "FAILURE", "2026-08-21T18:21:15Z"),
        ]
        failures = pr_merge._rollup_failures(rollup)
        assert any("Security Audit" in f and "FAILURE" in f for f in failures)

    def test_latest_in_progress_still_refuses(self) -> None:
        rollup = [
            _entry("Unit Tests", "SUCCESS", "2026-08-21T17:30:44Z"),
            _entry("Unit Tests", "", "2026-08-21T18:21:15Z", status="IN_PROGRESS"),
        ]
        failures = pr_merge._rollup_failures(rollup)
        assert any("Unit Tests" in f and "IN_PROGRESS" in f for f in failures)

    def test_distinct_names_are_not_deduped_across(self) -> None:
        rollup = [
            _entry("Fast Gate", "FAILURE", "2026-08-21T17:30:44Z"),
            _entry("Rust Gate", "SUCCESS", "2026-08-21T18:21:15Z"),
        ]
        failures = pr_merge._rollup_failures(rollup)
        assert any("Fast Gate" in f for f in failures)

    def test_entries_without_started_at_fall_back_to_run_id(self) -> None:
        base = "https://github.com/o/r/actions/runs"
        rollup = [
            {
                "name": "Security Audit",
                "status": "COMPLETED",
                "conclusion": "FAILURE",
                "detailsUrl": f"{base}/111/job/1",
            },
            {
                "name": "Security Audit",
                "status": "COMPLETED",
                "conclusion": "SUCCESS",
                "detailsUrl": f"{base}/222/job/1",
            },
        ]
        assert pr_merge._rollup_failures(rollup + _criticals_green()) == []

    def test_critical_checks_still_require_explicit_pass(self) -> None:
        """Dedupe must not weaken CRITICAL_CHECKS: a name whose latest entry
        is SKIPPED/NEUTRAL still does not count as an explicit pass."""
        critical = pr_merge.CRITICAL_CHECKS[0]
        rollup = [
            _entry(critical, "SUCCESS", "2026-08-21T17:30:44Z"),
            _entry(critical, "SKIPPED", "2026-08-21T18:21:15Z"),
        ]
        failures = pr_merge._rollup_failures(rollup)
        assert any("required an explicit PASS" in f for f in failures)
