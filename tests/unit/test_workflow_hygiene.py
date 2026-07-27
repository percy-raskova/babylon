"""Workflow-file hygiene: catch GitHub-invalid YAML that plain YAML accepts.

Sentinel for the error class discovered 2026-07-27: commit ``e240a30f``
inserted a ``run:`` step *between* ``- uses: actions/checkout@v7`` and its
``with:`` block in every ``nightly.yml`` job. The result still parses as
YAML (so no local tool objected), but GitHub's workflow validator rejects a
step carrying both ``run:`` and ``with:`` — every push to any branch then
spawned a zero-job stub failure run, and the nightly schedule was dead from
2026-07-22 until the fix. The checkout also silently lost its ``ref: dev``.

Two invariants, one per failure mode:

1. Every step in every workflow declares exactly one of ``run:`` / ``uses:``
   (``with:`` only ever accompanies ``uses:``).
2. Every ``actions/checkout`` step in ``nightly.yml`` pins ``ref: dev`` —
   scheduled workflows execute the file from the default branch, so an
   unpinned checkout tests the wrong ref without erroring.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS_DIR = Path(".github/workflows")


def _step_shape_errors(workflow: dict[str, Any], filename: str) -> list[str]:
    """Return one message per step whose run/uses/with combination GitHub rejects.

    :param workflow: Parsed workflow mapping (``yaml.safe_load`` output).
    :param filename: Display name used in the error messages.
    :returns: Human-readable violation messages; empty when the file is clean.
    """
    errors: list[str] = []
    jobs = workflow.get("jobs") or {}
    for job_name, job in jobs.items():
        for index, step in enumerate(job.get("steps") or []):
            has_run = "run" in step
            has_uses = "uses" in step
            where = f"{filename} job={job_name} step#{index}"
            if has_run and has_uses:
                errors.append(f"{where}: step has both 'run' and 'uses'")
            elif has_run and "with" in step:
                errors.append(f"{where}: 'with' on a 'run' step (GitHub rejects this)")
            elif not has_run and not has_uses:
                errors.append(f"{where}: step has neither 'run' nor 'uses'")
    return errors


@pytest.mark.skipif(not WORKFLOWS_DIR.is_dir(), reason=".github/workflows not present")
class TestWorkflowStepShape:
    """Every workflow step is GitHub-valid, not merely YAML-valid."""

    def test_no_step_mixes_run_and_with(self) -> None:
        violations: list[str] = []
        for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
            workflow = yaml.safe_load(path.read_text())
            violations.extend(_step_shape_errors(workflow, path.name))
        assert not violations, "\n".join(violations)

    def test_checker_catches_the_e240a30f_breakage(self) -> None:
        # Mutation validation: the exact historical bad shape must be flagged.
        broken = yaml.safe_load(
            """
            jobs:
              test-rest:
                steps:
                  - uses: actions/checkout@v7
                  - name: Materialize hypergraph-rs metadata stub
                    run: sh tools/ci_hypergraph_stub.sh
                    with:
                      ref: dev
            """
        )
        errors = _step_shape_errors(broken, "nightly.yml")
        assert errors == [
            "nightly.yml job=test-rest step#1: 'with' on a 'run' step (GitHub rejects this)"
        ]


@pytest.mark.skipif(not WORKFLOWS_DIR.is_dir(), reason=".github/workflows not present")
class TestNightlyCheckoutRef:
    """Nightly runs from the default branch; its checkouts must pin ref: dev."""

    def test_every_nightly_checkout_pins_dev(self) -> None:
        workflow = yaml.safe_load((WORKFLOWS_DIR / "nightly.yml").read_text())
        violations: list[str] = []
        for job_name, job in (workflow.get("jobs") or {}).items():
            for index, step in enumerate(job.get("steps") or []):
                uses = str(step.get("uses", ""))
                if not uses.startswith("actions/checkout"):
                    continue
                ref = (step.get("with") or {}).get("ref")
                if ref != "dev":
                    violations.append(f"job={job_name} step#{index}: checkout ref={ref!r}")
        assert not violations, "\n".join(violations)
