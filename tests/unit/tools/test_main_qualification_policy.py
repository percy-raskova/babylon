"""Contracts for the Director-controlled dev-to-main qualification path."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from tools.check_main_qualification_event import (
    QualificationEventError,
    validate_event,
)
from tools.pr_policy import (
    DEV_CHECK_MANIFEST,
    MAIN_CHECK_MANIFEST,
    MAIN_QUALIFICATION_CHECK_MANIFEST,
)

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "main.yml"
POLICY_PATH = ROOT / ".github" / "settings" / "pr-policy.json"
PROMOTE_PATH = ROOT / "tools" / "promote.sh"


def _workflow() -> dict[str, Any]:
    payload = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _triggers(workflow: dict[str, Any]) -> dict[str, Any]:
    payload = workflow.get("on", workflow.get(True))
    assert isinstance(payload, dict)
    return payload


@pytest.mark.parametrize(
    ("event_name", "ref", "base_ref"),
    [
        ("pull_request", "refs/pull/1/merge", "main"),
        ("workflow_dispatch", "refs/heads/dev", ""),
    ],
)
def test_only_main_pr_and_dev_dispatch_are_accepted(
    event_name: str,
    ref: str,
    base_ref: str,
) -> None:
    validate_event(event_name=event_name, ref=ref, base_ref=base_ref)


@pytest.mark.parametrize(
    ("event_name", "ref", "base_ref"),
    [
        ("pull_request", "refs/pull/2/merge", "dev"),
        ("workflow_dispatch", "refs/heads/main", ""),
        ("workflow_dispatch", "refs/heads/feature/test", ""),
        ("push", "refs/heads/main", ""),
        ("schedule", "refs/heads/dev", ""),
    ],
)
def test_every_other_event_branch_combination_is_rejected(
    event_name: str,
    ref: str,
    base_ref: str,
) -> None:
    with pytest.raises(QualificationEventError):
        validate_event(event_name=event_name, ref=ref, base_ref=base_ref)


def test_workflow_runs_before_main_merge_and_can_be_proved_on_dev() -> None:
    workflow = _workflow()
    triggers = _triggers(workflow)

    assert set(triggers) == {"pull_request", "workflow_dispatch"}
    assert triggers["pull_request"] == {"branches": ["main"]}
    assert "push" not in triggers

    jobs = workflow["jobs"]
    event_job = jobs["event-contract"]
    event_step = next(
        step
        for step in event_job["steps"]
        if step.get("name") == "Accept only a main PR or exact dev proof"
    )
    assert "tools/check_main_qualification_event.py" in event_step["run"]


def test_main_manifest_is_ci_plus_unique_qualification_extension() -> None:
    dev_contexts = {requirement.context for requirement in DEV_CHECK_MANIFEST}
    extension_contexts = {requirement.context for requirement in MAIN_QUALIFICATION_CHECK_MANIFEST}
    main_contexts = {requirement.context for requirement in MAIN_CHECK_MANIFEST}

    assert dev_contexts.isdisjoint(extension_contexts)
    assert main_contexts == dev_contexts | extension_contexts
    assert all(context.startswith("Main Qualification / ") for context in extension_contexts)


def test_workflow_emits_every_qualification_context_once() -> None:
    jobs = _workflow()["jobs"]
    names = [job["name"] for job in jobs.values()]
    expected = [requirement.context for requirement in MAIN_QUALIFICATION_CHECK_MANIFEST]

    assert len(names) == len(set(names))
    assert set(names) == set(expected)
    for job_id, job in jobs.items():
        if job_id != "event-contract":
            assert job["needs"] == ["event-contract"]


def test_main_ruleset_requires_the_complete_blocking_manifest() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    ruleset = policy["main_ruleset"]
    rules = {rule["type"]: rule for rule in ruleset["rules"]}
    checks = rules["required_status_checks"]["parameters"]
    pull_request = rules["pull_request"]["parameters"]
    configured = {entry["context"] for entry in checks["required_status_checks"]}
    expected = {
        requirement.context for requirement in MAIN_CHECK_MANIFEST if requirement.kind == "blocking"
    }

    assert ruleset["conditions"] == {"ref_name": {"exclude": [], "include": ["refs/heads/main"]}}
    assert checks["strict_required_status_checks_policy"] is True
    assert configured == expected
    assert pull_request["allowed_merge_methods"] == ["merge"]
    assert pull_request["required_review_thread_resolution"] is True


def test_direct_push_promotion_script_is_retired() -> None:
    assert not PROMOTE_PATH.exists()
