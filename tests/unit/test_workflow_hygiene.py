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
ACTIONS_DIR = Path(".github/actions")
FROZEN_ENGINE_PATH = WORKFLOWS_DIR / "frozen-engine.yml"
FROZEN_REF = "p27-python-freeze"
HYPERGRAPH_REF = "dc1c06abbbc7a3f8633d1561451e61e101ad2090"

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
_V3_1_COMMIT = "3acd1089b6b4e68177c99b4f4cec245e7b74317c"
_V3_1_BLOB = "a265b85120ed2a90be40c72e63ee5bf27fc6e703"
_V3_2_COMMIT = "cbfc67921283ccb6e00c4b0278288a232281440a"
_V3_2_BLOB = "e905e90d66bddc6e4eca36a3896428f5ce63de5b"
_CONSTITUTION_FETCH_STEP = "Fetch pinned Constitution predecessors (bounded)"


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


def _automation_paths() -> list[Path]:
    """Return live workflow and composite-action files."""
    return sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(ACTIONS_DIR.rglob("action.y*ml"))


def _automation_steps(automation: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every executable step from a workflow or composite action."""
    if "jobs" in automation:
        return [
            step
            for job in (automation.get("jobs") or {}).values()
            for step in (job.get("steps") or [])
        ]
    return list((automation.get("runs") or {}).get("steps") or [])


def _sibling_fabrication_errors(automation: dict[str, Any], filename: str) -> list[str]:
    """Reject executable construction of a local hypergraph sibling."""
    errors: list[str] = []
    for index, step in enumerate(_automation_steps(automation)):
        run = str(step.get("run", ""))
        fabricates_sibling = "hypergraph-rs" in run and any(
            command in run for command in ("mkdir", "ln -s", "cp ", "cat >", "tee ")
        )
        if "ci_hypergraph_stub" in run or fabricates_sibling:
            errors.append(f"{filename} step#{index}: fabricates hypergraph-rs sibling")
    return errors


def _frozen_engine_errors(workflow: dict[str, Any]) -> list[str]:
    """Return violations in the immutable frozen-engine checkout contract."""
    errors: list[str] = []
    steps = ((workflow.get("jobs") or {}).get("frozen-canon") or {}).get("steps") or []
    checkouts = {
        (
            str(step.get("with", {}).get("repository", "")),
            str(step.get("with", {}).get("ref", "")),
        ): str(step.get("with", {}).get("path", ""))
        for step in steps
        if str(step.get("uses", "")).startswith("actions/checkout")
    }
    if checkouts.get(("", FROZEN_REF)) != "babylon":
        errors.append("frozen source must check out at babylon")
    if checkouts.get(("percy-raskova/hypergraph-rs", HYPERGRAPH_REF)) != "hypergraph-rs":
        errors.append("historical hypergraph source must use its full pinned SHA")
    for index, step in enumerate(steps):
        run = str(step.get("run", ""))
        if "mise run" not in run and "uv sync" not in run:
            continue
        if step.get("working-directory") != "babylon":
            errors.append(f"frozen command step#{index} must run in babylon")
        if str((step.get("env") or {}).get("UV_FROZEN", "")).lower() not in {"1", "true"}:
            errors.append(f"frozen command step#{index} must set UV_FROZEN")
    return errors


@pytest.mark.skipif(not WORKFLOWS_DIR.is_dir(), reason=".github/workflows not present")
class TestWorkflowStepShape:
    """Every workflow step is GitHub-valid, not merely YAML-valid."""

    def test_no_workflow_materializes_a_hypergraph_sibling(self) -> None:
        """Python CI must not depend on a fabricated local checkout."""
        violations: list[str] = []
        for path in _automation_paths():
            violations.extend(
                _sibling_fabrication_errors(yaml.safe_load(path.read_text()), str(path))
            )
        assert not violations, "\n".join(violations)

    def test_frozen_engine_supplies_its_immutable_historical_sibling(self) -> None:
        """The frozen tag gets its real historical path source, never a fabricated one."""
        assert _frozen_engine_errors(yaml.safe_load(FROZEN_ENGINE_PATH.read_text())) == []

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
                  - name: Run setup
                    run: mise run setup
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


def _constitution_provenance_errors(workflow: dict[str, Any]) -> list[str]:
    """Return violations in the unit job's bounded predecessor supply contract."""
    errors: list[str] = []
    jobs = workflow.get("jobs") or {}
    job = jobs.get("test-unit") or {}
    steps = job.get("steps") or []
    checkout_index = next(
        (
            index
            for index, step in enumerate(steps)
            if str(step.get("uses", "")).startswith("actions/checkout")
        ),
        None,
    )
    unit_index = next(
        (index for index, step in enumerate(steps) if step.get("run") == "mise run test:unit-ci"),
        None,
    )
    fetch_index = next(
        (index for index, step in enumerate(steps) if step.get("name") == _CONSTITUTION_FETCH_STEP),
        None,
    )
    if checkout_index is None:
        return ["test-unit has no actions/checkout step"]
    checkout_with = steps[checkout_index].get("with") or {}
    if checkout_with.get("persist-credentials") is not True:
        errors.append("test-unit checkout must persist credentials for the bounded fetch")
    if checkout_with.get("fetch-depth") == 0:
        errors.append("test-unit checkout must stay shallow, never fetch-depth 0")
    if fetch_index is None:
        errors.append("test-unit has no bounded Constitution predecessor fetch")
        return errors
    if unit_index is None or not checkout_index < fetch_index < unit_index:
        errors.append("bounded predecessor fetch must run after checkout and before unit tests")

    fetch_step = steps[fetch_index]
    if fetch_step.get("shell") != "bash":
        errors.append("bounded predecessor fetch must declare shell: bash")

    run = str(fetch_step.get("run", ""))
    run_lines = [line.strip() for line in run.splitlines() if line.strip()]
    if not run_lines or run_lines[0] != "set -euo pipefail":
        errors.append("bounded predecessor fetch must start with set -euo pipefail")
    normalized = " ".join(run.replace("\\\n", " ").split())
    required_fragments = (
        "git -c protocol.version=2 fetch",
        "--depth=1 --no-tags --prune --no-recurse-submodules origin",
        f'git rev-parse {_V3_1_COMMIT}:CONSTITUTION.md)" = "{_V3_1_BLOB}"',
        f'git rev-parse {_V3_2_COMMIT}:CONSTITUTION.md)" = "{_V3_2_BLOB}"',
    )
    for fragment in required_fragments:
        if fragment not in normalized:
            errors.append(f"bounded predecessor fetch missing {fragment!r}")
    required_refspecs = (
        f"+{_V3_1_COMMIT}:refs/remotes/origin/constitution-v3.1",
        f"+{_V3_2_COMMIT}:refs/remotes/origin/constitution-v3.2",
    )
    run_tokens = normalized.split()
    for refspec in required_refspecs:
        if refspec not in run_tokens:
            errors.append(f"bounded predecessor fetch missing forced refspec {refspec!r}")
    return errors


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
class TestConstitutionProvenanceSupply:
    """The unit job gets exact predecessor blobs without a full-history checkout."""

    def test_unit_job_fetches_exact_constitution_predecessors_before_tests(self) -> None:
        workflow = yaml.safe_load((WORKFLOWS_DIR / "ci.yml").read_text())
        assert _constitution_provenance_errors(workflow) == []

    def test_checker_catches_an_unbounded_or_incomplete_fetch(self) -> None:
        broken = yaml.safe_load(
            f"""
            jobs:
              test-unit:
                steps:
                  - uses: actions/checkout@v7
                    with:
                      fetch-depth: 0
                  - name: {_CONSTITUTION_FETCH_STEP}
                    run: git fetch origin {_V3_2_COMMIT}
                  - run: mise run test:unit-ci
            """
        )
        errors = _constitution_provenance_errors(broken)
        assert "test-unit checkout must persist credentials for the bounded fetch" in errors
        assert "test-unit checkout must stay shallow, never fetch-depth 0" in errors
        assert "bounded predecessor fetch must declare shell: bash" in errors
        assert "bounded predecessor fetch must start with set -euo pipefail" in errors
        assert any("protocol.version=2" in error for error in errors)
        assert any(
            "--depth=1 --no-tags --prune --no-recurse-submodules" in error for error in errors
        )
        assert any("forced refspec" in error and "constitution-v3.1" in error for error in errors)
        assert any("CONSTITUTION.md" in error and _V3_1_BLOB in error for error in errors)


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
