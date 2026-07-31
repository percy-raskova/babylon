"""Workflow-file hygiene: catch GitHub-invalid YAML that plain YAML accepts,
plus the scheduled-workflow process classes (ADR181 R9b).

Sentinel for the error class discovered 2026-07-27: commit ``e240a30f``
inserted a ``run:`` step *between* ``- uses: actions/checkout@v7`` and its
``with:`` block in every ``nightly.yml`` job. The result still parses as
YAML (so no local tool objected), but GitHub's workflow validator rejects a
step carrying both ``run:`` and ``with:`` — every push to any branch then
spawned a zero-job stub failure run, and the nightly schedule was dead from
2026-07-22 until the fix. The checkout also silently lost its ``ref: dev``.

Four invariants, one per failure mode:

1. Every step in every workflow declares exactly one of ``run:`` / ``uses:``
   (``with:`` only ever accompanies ``uses:``).
2. Every ``actions/checkout`` step in the scheduled deep-leg workflows
   (``nightly-*.yml`` / ``weekly-*.yml``, the ADR181 R3 split) pins
   ``ref: dev`` — scheduled workflows execute the file from the default
   branch, so an unpinned checkout tests the wrong ref without erroring on a
   dispatch from a non-default ref.
3. Every workflow carrying a ``schedule:`` trigger also declares
   ``workflow_dispatch`` — a cron-only workflow cannot be proof-run, which
   is how the monolithic nightly stayed red 76/76 without a diagnosis loop
   (this is the statically-decidable half of the audit's
   "scheduled workflow must exist on the default branch" rule; the other
   half is not decidable from a PR checkout without network access and is
   enforced by the merge flow itself).
4. Every ``.github/workflows/*.yml`` path referenced in the LIVE doc
   surfaces exists in ``git ls-files`` — the ``openwiki-update.yml`` class:
   docs asserting a workflow that was never committed (a Verifiability
   violation). Historical records (ADRs, reports, plans) are exempt —
   immutability of history.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS_DIR = Path(".github/workflows")

#: Hand-maintained doc surfaces whose workflow references must stay live.
#: Historical quadrants (ai/decisions, reports/, project/, docs/superpowers/
#: plans) are deliberately absent; openwiki/ is generated, never hand-edited.
LIVE_DOC_SURFACES: tuple[str, ...] = (
    "CLAUDE.md",
    "CONTRIBUTORS.md",
    "README.md",
    "NORTH_STAR.md",
    "tests/README.md",
)

_WORKFLOW_REF_RE = re.compile(r"\.github/workflows/([A-Za-z0-9._-]+\.ya?ml)")


def _triggers(workflow: dict[Any, Any]) -> dict[str, Any]:
    """Return the ``on:`` mapping (YAML 1.1 parses the bare key as ``True``)."""
    raw = workflow.get("on", workflow.get(True))
    return raw if isinstance(raw, dict) else {}


def _workflow_path_refs(text: str) -> set[str]:
    """Extract referenced workflow basenames from a doc's text."""
    return set(_WORKFLOW_REF_RE.findall(text))


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


def _unpinned_checkouts(workflow: dict[str, Any], filename: str) -> list[str]:
    """Return one message per ``actions/checkout`` step not pinning ``ref: dev``."""
    violations: list[str] = []
    for job_name, job in (workflow.get("jobs") or {}).items():
        for index, step in enumerate(job.get("steps") or []):
            uses = str(step.get("uses", ""))
            if not uses.startswith("actions/checkout"):
                continue
            ref = (step.get("with") or {}).get("ref")
            if ref != "dev":
                violations.append(f"{filename} job={job_name} step#{index}: checkout ref={ref!r}")
    return violations


@pytest.mark.skipif(not WORKFLOWS_DIR.is_dir(), reason=".github/workflows not present")
class TestScheduledWorkflows:
    """The scheduled estate's shape rules (invariants 2 and 3)."""

    def test_deep_leg_checkouts_pin_dev(self) -> None:
        deep_legs = sorted(WORKFLOWS_DIR.glob("nightly-*.yml")) + sorted(
            WORKFLOWS_DIR.glob("weekly-*.yml")
        )
        assert deep_legs, "the ADR181 R3 per-leg split produced no deep-leg workflows"
        violations: list[str] = []
        for path in deep_legs:
            workflow = yaml.safe_load(path.read_text())
            violations.extend(_unpinned_checkouts(workflow, path.name))
        assert not violations, "\n".join(violations)

    def test_every_scheduled_workflow_is_dispatchable(self) -> None:
        violations: list[str] = []
        for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
            triggers = _triggers(yaml.safe_load(path.read_text()))
            if "schedule" in triggers and "workflow_dispatch" not in triggers:
                violations.append(f"{path.name}: schedule without workflow_dispatch")
        assert not violations, "\n".join(violations)

    def test_checker_catches_an_unpinned_deep_leg_checkout(self) -> None:
        # Mutation validation: the e240a30f ref-loss shape must be flagged.
        broken = yaml.safe_load(
            """
            jobs:
              test-rest:
                steps:
                  - uses: actions/checkout@v7
            """
        )
        assert _unpinned_checkouts(broken, "weekly-test-rest.yml") == [
            "weekly-test-rest.yml job=test-rest step#0: checkout ref=None"
        ]

    def test_checker_catches_a_cron_only_workflow(self) -> None:
        # Mutation validation: yaml parses bare `on:` as the boolean True key.
        broken = yaml.safe_load(
            """
            on:
              schedule:
                - cron: "0 6 * * 3"
            jobs: {}
            """
        )
        triggers = _triggers(broken)
        assert "schedule" in triggers and "workflow_dispatch" not in triggers


@pytest.mark.skipif(not WORKFLOWS_DIR.is_dir(), reason=".github/workflows not present")
class TestDocReferencedWorkflowsTracked:
    """Invariant 4: live docs never assert a workflow git does not track."""

    def test_referenced_workflows_are_tracked(self) -> None:
        tracked = set(
            subprocess.run(  # noqa: S603
                ["git", "ls-files", "--", ".github/workflows"],  # noqa: S607
                capture_output=True,
                text=True,
                check=True,
            ).stdout.split()
        )
        tracked_names = {Path(p).name for p in tracked}
        violations: list[str] = []
        for doc in LIVE_DOC_SURFACES:
            doc_path = Path(doc)
            if not doc_path.is_file():
                continue
            for name in sorted(_workflow_path_refs(doc_path.read_text())):
                if name not in tracked_names:
                    violations.append(f"{doc}: references untracked workflow {name}")
        assert not violations, "\n".join(violations)

    def test_extractor_catches_the_openwiki_class(self) -> None:
        # Mutation validation: a doc referencing a never-committed workflow.
        refs = _workflow_path_refs(
            "The scheduled workflow (.github/workflows/openwiki-update.yml) refreshes the wiki."
        )
        assert refs == {"openwiki-update.yml"}
