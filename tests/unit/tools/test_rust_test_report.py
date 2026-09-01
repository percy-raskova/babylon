"""Agent-oriented Rust test report contracts for PER-310."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from tools import rust_test_report

JUNIT = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="4" failures="1" errors="0" time="3.6">
  <testsuite name="babylon_kernel::contract" tests="4" failures="1" time="3.6">
    <testcase name="passes" classname="babylon_kernel::contract" time="0.1" />
    <testcase name="fails" classname="babylon_kernel::contract" time="0.2">
      <failure message="assertion failed: left == right">thread panicked at crates/kernel/tests/contract.rs:42:9
full failure body</failure>
      <system-out>diagnostic stdout</system-out>
      <system-err>diagnostic stderr</system-err>
    </testcase>
    <testcase name="ignored_case" classname="babylon_kernel::contract" time="0">
      <skipped message="ignored" />
    </testcase>
    <testcase name="flaky_case" classname="babylon_kernel::contract" time="3.3">
      <flakyFailure message="failed on attempt 1">first attempt failed</flakyFailure>
    </testcase>
  </testsuite>
</testsuites>
"""


def test_parse_junit_is_failure_first_and_preserves_drilldown_pointer(tmp_path: Path) -> None:
    """The compact view names every exceptional test without embedding passing output."""
    junit = tmp_path / "junit.xml"
    junit.write_text(JUNIT, encoding="utf-8")

    result = rust_test_report.parse_junit(junit)

    assert result["totals"] == {
        "passed": 1,
        "failed": 1,
        "flaky": 1,
        "timed_out": 0,
        "ignored": 1,
        "tests": 4,
    }
    assert [failure["test"] for failure in result["failures"]] == [
        "babylon_kernel::contract::fails",
        "babylon_kernel::contract::flaky_case",
    ]
    failure = result["failures"][0]
    assert failure["kind"] == "failure"
    assert failure["binary_id"] == "babylon_kernel::contract"
    assert failure["nextest_name"] == "fails"
    assert failure["cause"] == "assertion failed: left == right"
    assert failure["source"] == "crates/kernel/tests/contract.rs:42:9"
    assert failure["stdout"] == "diagnostic stdout"
    assert failure["stderr"] == "diagnostic stderr"
    assert failure["junit"] == "junit.xml"
    assert failure["rerun"] == (
        "mise run rust:test:q -- -E 'binary_id(=babylon_kernel::contract) & test(=fails)'"
    )
    assert result["slowest"][0]["test"].endswith("flaky_case")


def test_finalize_records_build_failure_even_without_junit(tmp_path: Path) -> None:
    """A missing JUnit file must be a classified runner failure, never zero tests."""
    log = tmp_path / "run.log"
    log.write_text("error: could not compile `babylon-kernel`\n", encoding="utf-8")

    summary = rust_test_report.finalize_report(
        report_dir=tmp_path,
        junit_source=tmp_path / "missing.xml",
        exit_code=101,
        command=["cargo", "nextest", "run"],
        started_at="2026-09-01T00:00:00Z",
        duration_ms=1200,
        metadata={"head_sha": "abc123", "dirty": False},
    )

    assert summary["status"] == "failed"
    assert summary["exit_class"] == "build_failed"
    assert summary["totals"]["tests"] == 0
    assert "could not compile" in summary["diagnostic"]
    assert json.loads((tmp_path / "summary.json").read_text()) == summary
    assert (tmp_path / "summary.md").is_file()
    assert (tmp_path / "manifest.json").is_file()


def test_finalize_classifies_a_truncated_junit_receipt(tmp_path: Path) -> None:
    """An interrupted XML write must still leave a useful failed summary."""
    (tmp_path / "junit.xml").write_text("<testsuites><testcase>", encoding="utf-8")
    (tmp_path / "run.log").write_text("runner stopped while writing output\n", encoding="utf-8")

    summary = rust_test_report.finalize_report(
        report_dir=tmp_path,
        junit_source=tmp_path / "junit.xml",
        exit_code=106,
        command=["cargo", "nextest", "run"],
        started_at="2026-09-01T00:00:00Z",
        duration_ms=900,
        metadata={"head_sha": "abc123", "dirty": False},
    )

    assert summary["status"] == "failed"
    assert summary["exit_class"] == "incomplete_run"
    assert summary["totals"]["tests"] == 0
    assert "unable to parse junit.xml" in summary["diagnostic"]
    assert "runner stopped while writing output" in summary["diagnostic"]


def test_exit_classes_preserve_nextest_discovery_and_selection_failures() -> None:
    """Agents must distinguish failed code from a runner that never ran tests."""
    assert rust_test_report.classify_exit_code(0) == "success"
    assert rust_test_report.classify_exit_code(4) == "no_tests_selected"
    assert rust_test_report.classify_exit_code(100) == "test_failed"
    assert rust_test_report.classify_exit_code(101) == "build_failed"
    assert rust_test_report.classify_exit_code(102) == "cargo_metadata_failed"
    assert rust_test_report.classify_exit_code(104) == "test_list_failed"
    assert rust_test_report.classify_exit_code(1) == "runner_failed"


def test_coverage_totals_are_compact_and_stable(tmp_path: Path) -> None:
    """The agent summary exposes stable metrics without embedding the full export."""
    summary_path = tmp_path / "coverage-summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "type": "llvm.coverage.json.export",
                "version": "3.0.1",
                "data": [
                    {
                        "totals": {
                            "functions": {"count": 20, "covered": 15, "percent": 75.0},
                            "lines": {"count": 100, "covered": 85, "percent": 85.0},
                            "regions": {"count": 150, "covered": 120, "percent": 80.0},
                        }
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert rust_test_report.read_coverage_totals(summary_path) == {
        "functions": {"count": 20, "covered": 15, "percent": 75.0},
        "lines": {"count": 100, "covered": 85, "percent": 85.0},
        "regions": {"count": 150, "covered": 120, "percent": 80.0},
    }


def test_summary_bounds_failures_but_jsonl_preserves_every_record(tmp_path: Path) -> None:
    """The first-read receipt stays bounded while drill-down remains exhaustive."""
    cases = "".join(
        f'<testcase name="case_{index}" classname="suite" time="0.01">'
        f'<failure message="failure {index}">detail {index}</failure></testcase>'
        for index in range(rust_test_report.MAX_SUMMARY_FAILURES + 3)
    )
    junit = tmp_path / "junit.xml"
    junit.write_text(f"<testsuites>{cases}</testsuites>", encoding="utf-8")
    (tmp_path / "run.log").write_text("test failures\n", encoding="utf-8")

    summary = rust_test_report.finalize_report(
        report_dir=tmp_path,
        junit_source=junit,
        exit_code=100,
        command=["cargo", "nextest", "run"],
        started_at="2026-09-01T00:00:00Z",
        duration_ms=100,
        metadata={"head_sha": "abc123", "dirty": False},
    )

    assert summary["failure_count"] == rust_test_report.MAX_SUMMARY_FAILURES + 3
    assert summary["failures_truncated"] is True
    assert len(summary["failures"]) == rust_test_report.MAX_SUMMARY_FAILURES
    assert len((tmp_path / "failures.jsonl").read_text().splitlines()) == (
        rust_test_report.MAX_SUMMARY_FAILURES + 3
    )
    assert "3 more failure records" in (tmp_path / "summary.md").read_text()


def test_run_nextest_returns_finalized_report_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A malformed receipt must fail the gate even when nextest itself passed."""
    monkeypatch.setattr(
        rust_test_report,
        "collect_metadata",
        lambda _profile: {"head_sha": "abc123", "dirty": False},
    )
    monkeypatch.setattr(
        rust_test_report,
        "_report_directory",
        lambda _root, _metadata: ("run-id", tmp_path / "report"),
    )
    monkeypatch.setattr(rust_test_report, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(rust_test_report, "_tee", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        rust_test_report,
        "finalize_report",
        lambda **_kwargs: {"exit_code": 110},
    )
    monkeypatch.setattr(rust_test_report, "_update_latest", lambda *_args: None)
    monkeypatch.setattr(rust_test_report, "_append_github_summary", lambda *_args: None)

    assert (
        rust_test_report.run_nextest(
            profile="ci", workspace=True, extra_args=(), report_root=tmp_path
        )
        == 110
    )


def test_rerun_failed_preserves_red_report_without_test_identities(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Build and discovery failures cannot become a successful rerun no-op."""
    report_dir = tmp_path / "abc123" / "run-id"
    report_dir.mkdir(parents=True)
    (tmp_path / "latest.json").write_text(
        json.dumps({"report_dir": "abc123/run-id"}), encoding="utf-8"
    )
    (report_dir / "summary.json").write_text(
        json.dumps({"status": "failed", "exit_code": 101}), encoding="utf-8"
    )
    (report_dir / "failures.jsonl").write_text("", encoding="utf-8")

    assert rust_test_report.rerun_failed(tmp_path) == 101
    assert "failed before test identities were recorded" in capsys.readouterr().err


def test_tee_replaces_non_utf8_test_output(tmp_path: Path) -> None:
    """Arbitrary test bytes must still produce a finalized UTF-8 run log."""
    log = tmp_path / "run.log"

    exit_code = rust_test_report._tee(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'bad: \\xff\\n')",
        ],
        tmp_path,
        log,
    )

    assert exit_code == 0
    assert log.read_text(encoding="utf-8") == "bad: �\n"
