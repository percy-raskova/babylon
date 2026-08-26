"""Transactional contracts for the GitHub pull-request policy applicator."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "sync_github_pr_policy",
    Path(__file__).resolve().parents[3] / "tools" / "sync_github_pr_policy.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("tools/sync_github_pr_policy.py failed import-spec resolution")
policy_tool = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(policy_tool)

DEV_BLOCKING_CHECKS = (
    "Fast Gate (hygiene, lint, format, imports, types, lock)",
    "Unit Tests (xdist, coverage gate)",
    "Determinism Gate (byte-identical dense goldens)",
    "Secret Scan (gitleaks, full history)",
    "IaC Config Scan (trivy, HIGH+CRITICAL blocking)",
    "Security Audit (pip-audit policy — blocking since item-41)",
    "Rust Gate (fmt, clippy, test, doc — rust/ workspace)",
    "Baseline Ceremony Gate (§6.5 provenance)",
    "Postgres Integration Tier (PG 17, pinned runtime)",
)

MAIN_QUALIFICATION_CHECKS = (
    "Main Qualification / Event Contract",
    "Main Qualification / Non-Unit Behavioral Contracts",
    "Main Qualification / PostgreSQL Determinism Bundle",
    "Main Qualification / Reference-Data Contracts",
    "Main Qualification / Release Documentation",
    "Main Qualification / AI Tests (advisory)",
    "Main Qualification / Container Image Scan (advisory)",
)


def _ruleset(
    *,
    strict: bool,
    threads: bool,
    branch: str = "dev",
    ruleset_id: int = 18807584,
) -> dict[str, Any]:
    contexts = (
        DEV_BLOCKING_CHECKS
        if branch == "dev"
        else (*DEV_BLOCKING_CHECKS, *MAIN_QUALIFICATION_CHECKS[:5])
    )
    return {
        "id": ruleset_id,
        "name": f"{branch} protection",
        "target": "branch",
        "source_type": "Repository",
        "source": "percy-raskova/babylon",
        "enforcement": "active",
        "conditions": {"ref_name": {"exclude": [], "include": [f"refs/heads/{branch}"]}},
        "bypass_actors": [],
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {
                "type": "pull_request",
                "parameters": {
                    "allowed_merge_methods": ["merge"],
                    "dismiss_stale_reviews_on_push": False,
                    "required_reviewers": [],
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_approving_review_count": 0,
                    "required_review_thread_resolution": threads,
                    "require_extra_approval_for_unattributed_changes": False,
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": strict,
                    "do_not_enforce_on_create": False,
                    "required_status_checks": [{"context": context} for context in contexts],
                },
            },
        ],
        "node_id": "read-only",
        "created_at": "yesterday",
        "updated_at": "today",
    }


def _repository(*, merge_only: bool) -> dict[str, Any]:
    return {
        "allow_merge_commit": True,
        "allow_squash_merge": not merge_only,
        "allow_rebase_merge": not merge_only,
        "allow_auto_merge": not merge_only,
        "delete_branch_on_merge": False,
        "id": 123,
        "full_name": "percy-raskova/babylon",
    }


def _policy() -> dict[str, Any]:
    return {
        "repository": policy_tool.normalize_repository(_repository(merge_only=True)),
        "dev_ruleset": policy_tool.normalize_ruleset(_ruleset(strict=True, threads=True)),
        "main_ruleset": policy_tool.normalize_ruleset(
            _ruleset(
                strict=True,
                threads=True,
                branch="main",
                ruleset_id=18807583,
            )
        ),
        "automerge_label": {
            "name": "dependencies:automerge",
            "color": "1f883d",
            "description": "Patch/minor Dependabot update eligible for exact-head merge",
        },
    }


class FakeApi:
    """Small bounded API double with explicit state and injected failures."""

    def __init__(self) -> None:
        self.dev_sha = "a" * 40
        self.ruleset = _ruleset(strict=False, threads=False)
        self.main_ruleset = _ruleset(
            strict=False,
            threads=False,
            branch="main",
            ruleset_id=18807583,
        )
        self.repository = _repository(merge_only=False)
        self.labels: list[dict[str, Any]] = []
        self.check_runs = [
            {
                "id": index,
                "name": context,
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-08-25T00:00:00Z",
            }
            for index, context in enumerate(DEV_BLOCKING_CHECKS, start=1)
        ]
        self.check_runs.extend(
            {
                "id": index,
                "name": context,
                "status": "completed",
                "conclusion": "neutral" if "(advisory)" in context else "success",
                "started_at": "2026-08-26T00:00:00Z",
            }
            for index, context in enumerate(MAIN_QUALIFICATION_CHECKS, start=50)
        )
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
        self.fail_method_endpoint: tuple[str, str] | None = None
        self.fail_oserror_method_endpoint: tuple[str, str] | None = None
        self.mutate_then_fail_method_endpoint: tuple[str, str] | None = None
        self.fail_ruleset_restore = False
        self.mismatch_ruleset_readback = False
        self.concurrent_ruleset_drift = False
        self.policy_error_ruleset_read: int | None = None
        self._ruleset_reads = 0
        self.move_dev_on_read: int | None = None
        self._dev_reads = 0

    def get_json(self, endpoint: str) -> object:
        self.calls.append(("GET", endpoint, None))
        if endpoint == policy_tool.DEV_REF_ENDPOINT:
            self._dev_reads += 1
            if self._dev_reads == self.move_dev_on_read:
                self.dev_sha = "b" * 40
            return {"object": {"sha": self.dev_sha}}
        if endpoint == policy_tool.RULESETS_ENDPOINT:
            return [{"id": 18807584}, {"id": 18807583}]
        if endpoint == policy_tool.DEV_RULESET_ENDPOINT.format(ruleset_id=18807584):
            self._ruleset_reads += 1
            if self._ruleset_reads == self.policy_error_ruleset_read:
                raise policy_tool.PolicyError("injected malformed ruleset readback")
            value = deepcopy(self.ruleset)
            if self.concurrent_ruleset_drift and self._ruleset_reads == 2:
                value["name"] = "concurrent change"
            if self.mismatch_ruleset_readback and self._ruleset_reads == 3:
                value["enforcement"] = "disabled"
            return value
        if endpoint == policy_tool.MAIN_RULESET_ENDPOINT.format(ruleset_id=18807583):
            return deepcopy(self.main_ruleset)
        if endpoint == policy_tool.REPOSITORY_ENDPOINT:
            return deepcopy(self.repository)
        if endpoint == policy_tool.LABELS_LIST_ENDPOINT:
            return deepcopy(self.labels)
        if endpoint == policy_tool.CHECK_RUNS_ENDPOINT.format(sha=self.dev_sha):
            return {"total_count": len(self.check_runs), "check_runs": deepcopy(self.check_runs)}
        raise AssertionError(f"unexpected GET {endpoint}")

    def send_json(self, method: str, endpoint: str, payload: dict[str, Any]) -> object:
        self.calls.append((method, endpoint, deepcopy(payload)))
        if self.fail_method_endpoint == (method, endpoint):
            self.fail_method_endpoint = None
            raise policy_tool.GitHubApiError(f"injected {method} failure")
        if self.fail_oserror_method_endpoint == (method, endpoint):
            self.fail_oserror_method_endpoint = None
            raise OSError(f"injected {method} spawn failure")
        if (
            self.fail_ruleset_restore
            and method == "PUT"
            and payload["rules"][-1]["parameters"]["strict_required_status_checks_policy"] is False
        ):
            raise policy_tool.GitHubApiError("injected ruleset restore failure")
        if method == "POST" and endpoint == policy_tool.LABELS_ENDPOINT:
            label = {"id": 99, **payload}
            self.labels.append(label)
            return self._write_result(method, endpoint, label)
        if method == "DELETE" and endpoint == policy_tool.label_endpoint("dependencies:automerge"):
            self.labels = [label for label in self.labels if label["name"] != payload["name"]]
            return self._write_result(method, endpoint, {})
        if method == "PATCH" and endpoint == policy_tool.REPOSITORY_ENDPOINT:
            self.repository.update(payload)
            return self._write_result(method, endpoint, self.repository)
        if method == "PUT" and endpoint == policy_tool.DEV_RULESET_ENDPOINT.format(
            ruleset_id=18807584
        ):
            current_id = self.ruleset["id"]
            self.ruleset = {"id": current_id, **deepcopy(payload)}
            return self._write_result(method, endpoint, self.ruleset)
        if method == "PUT" and endpoint == policy_tool.MAIN_RULESET_ENDPOINT.format(
            ruleset_id=18807583
        ):
            current_id = self.main_ruleset["id"]
            self.main_ruleset = {"id": current_id, **deepcopy(payload)}
            return self._write_result(method, endpoint, self.main_ruleset)
        raise AssertionError(f"unexpected {method} {endpoint}")

    def _write_result(
        self,
        method: str,
        endpoint: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if self.mutate_then_fail_method_endpoint == (method, endpoint):
            self.mutate_then_fail_method_endpoint = None
            raise policy_tool.GitHubApiError(f"injected ambiguous {method} failure")
        return deepcopy(result)


def test_normalizers_strip_read_only_api_fields() -> None:
    normalized_ruleset = policy_tool.normalize_ruleset(_ruleset(strict=False, threads=False))
    normalized_repository = policy_tool.normalize_repository(_repository(merge_only=False))

    assert set(normalized_ruleset) == {
        "name",
        "target",
        "enforcement",
        "bypass_actors",
        "conditions",
        "rules",
    }
    assert set(normalized_repository) == {
        "allow_merge_commit",
        "allow_squash_merge",
        "allow_rebase_merge",
        "allow_auto_merge",
        "delete_branch_on_merge",
    }


def test_check_reports_drift_without_mutation() -> None:
    api = FakeApi()

    drift = policy_tool.check_policy(api, _policy())

    assert drift == [
        "repository merge settings differ",
        "dev ruleset differs",
        "main ruleset differs",
        "automerge label is absent",
    ]
    assert all(method == "GET" for method, _endpoint, _payload in api.calls)


def test_dev_ruleset_selection_refuses_a_shared_or_non_branch_scope() -> None:
    shared = FakeApi()
    shared.ruleset["conditions"]["ref_name"]["include"].append("refs/heads/main")
    with pytest.raises(policy_tool.PolicyError, match="shared protected-branch scope"):
        policy_tool.check_policy(shared, _policy())

    tagged = FakeApi()
    tagged.ruleset["target"] = "tag"
    with pytest.raises(policy_tool.PolicyError, match="exact dev-only branch scope"):
        policy_tool.check_policy(tagged, _policy())


def test_main_ruleset_selection_refuses_a_shared_scope() -> None:
    shared = FakeApi()
    shared.main_ruleset["conditions"]["ref_name"]["include"].append("refs/heads/dev")

    with pytest.raises(policy_tool.PolicyError, match="shared protected-branch scope"):
        policy_tool.check_policy(shared, _policy())


def test_ruleset_enumeration_requests_one_bounded_complete_page() -> None:
    assert "per_page=100" in policy_tool.RULESETS_ENDPOINT


def test_required_status_contexts_cannot_be_empty() -> None:
    policy = _policy()
    status_rule = next(
        rule for rule in policy["dev_ruleset"]["rules"] if rule["type"] == "required_status_checks"
    )
    status_rule["parameters"]["required_status_checks"] = []

    with pytest.raises(policy_tool.PolicyError, match="at least one required status check"):
        policy_tool._required_contexts(policy)


def test_settings_policy_must_match_the_complete_typed_dev_manifest() -> None:
    policy = _policy()
    status_rule = next(
        rule for rule in policy["dev_ruleset"]["rules"] if rule["type"] == "required_status_checks"
    )
    status_rule["parameters"]["required_status_checks"].pop()

    with pytest.raises(policy_tool.PolicyError, match="complete dev check manifest"):
        policy_tool._validate_policy(policy)


def test_settings_policy_must_match_the_complete_typed_main_manifest() -> None:
    policy = _policy()
    status_rule = next(
        rule for rule in policy["main_ruleset"]["rules"] if rule["type"] == "required_status_checks"
    )
    status_rule["parameters"]["required_status_checks"].pop()

    with pytest.raises(policy_tool.PolicyError, match="complete main check manifest"):
        policy_tool._validate_policy(policy)


def test_settings_policy_context_order_is_not_authoritative() -> None:
    policy = _policy()
    status_rule = next(
        rule for rule in policy["dev_ruleset"]["rules"] if rule["type"] == "required_status_checks"
    )
    status_rule["parameters"]["required_status_checks"].reverse()

    policy_tool._validate_policy(policy)


def test_malformed_check_run_id_is_rejected_at_the_json_boundary(tmp_path: Path) -> None:
    api = FakeApi()
    api.check_runs[0]["id"] = "not-an-integer"

    with pytest.raises(policy_tool.PolicyError, match="integer id"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert all(method == "GET" for method, _endpoint, _payload in api.calls)


def test_gh_api_has_a_fixed_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["timeout"] == policy_tool.API_TIMEOUT_SECONDS
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(policy_tool.subprocess, "run", timeout)

    with pytest.raises(policy_tool.GitHubApiError, match="timed out"):
        policy_tool.GhApi._run(["repos/percy-raskova/babylon"])


def test_gh_api_normalizes_an_os_spawn_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_spawn(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("gh executable unavailable")

    monkeypatch.setattr(policy_tool.subprocess, "run", fail_spawn)

    with pytest.raises(policy_tool.GitHubApiError, match="could not start"):
        policy_tool.GhApi._run(["repos/percy-raskova/babylon"])


def test_alternate_policy_label_is_refused_before_any_api_call(tmp_path: Path) -> None:
    api = FakeApi()
    policy = _policy()
    policy["automerge_label"]["name"] = "dependencies:alternate"

    with pytest.raises(policy_tool.PolicyError, match="canonical automerge label"):
        policy_tool.apply_policy(api, policy, api.dev_sha, tmp_path / "before.json")

    assert api.calls == []


def test_apply_snapshots_before_mutation_and_verifies_readback(tmp_path: Path) -> None:
    api = FakeApi()
    snapshot_path = tmp_path / "before.json"

    policy_tool.apply_policy(api, _policy(), api.dev_sha, snapshot_path)

    snapshot = json.loads(snapshot_path.read_text())
    assert snapshot["dev_sha"] == api.dev_sha
    assert snapshot["dev_ruleset_id"] == 18807584
    assert snapshot["main_ruleset_id"] == 18807583
    assert snapshot["automerge_label"] is None
    first_write = next(index for index, call in enumerate(api.calls) if call[0] != "GET")
    assert snapshot_path.is_file()
    assert first_write > 0
    assert policy_tool.check_policy(api, _policy()) == []


def test_apply_refuses_moved_dev_or_non_green_checks_before_mutation(tmp_path: Path) -> None:
    moved = FakeApi()
    with pytest.raises(policy_tool.PolicyError, match="dev moved"):
        policy_tool.apply_policy(moved, _policy(), "b" * 40, tmp_path / "moved.json")
    assert all(method == "GET" for method, _endpoint, _payload in moved.calls)

    red = FakeApi()
    red.check_runs[0]["conclusion"] = "failure"
    with pytest.raises(policy_tool.PolicyError, match=re.escape(DEV_BLOCKING_CHECKS[0])):
        policy_tool.apply_policy(red, _policy(), red.dev_sha, tmp_path / "red.json")
    assert all(method == "GET" for method, _endpoint, _payload in red.calls)


def test_apply_accepts_the_pr_only_baseline_gate_skipped_on_dev_push(tmp_path: Path) -> None:
    api = FakeApi()
    baseline = next(
        run for run in api.check_runs if run["name"] == "Baseline Ceremony Gate (§6.5 provenance)"
    )
    baseline["conclusion"] = "skipped"

    policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert policy_tool.check_policy(api, _policy()) == []


def test_apply_refuses_any_other_skipped_dev_push_check(tmp_path: Path) -> None:
    api = FakeApi()
    api.check_runs[0]["conclusion"] = "skipped"

    with pytest.raises(policy_tool.PolicyError, match=re.escape(DEV_BLOCKING_CHECKS[0])):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert all(method == "GET" for method, _endpoint, _payload in api.calls)


def test_apply_refuses_missing_main_qualification_evidence(tmp_path: Path) -> None:
    api = FakeApi()
    api.check_runs = [
        run
        for run in api.check_runs
        if run["name"] != "Main Qualification / Reference-Data Contracts"
    ]

    with pytest.raises(policy_tool.PolicyError, match="Reference-Data Contracts"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert all(method == "GET" for method, _endpoint, _payload in api.calls)


def test_existing_snapshot_is_preserved_before_any_remote_mutation(tmp_path: Path) -> None:
    api = FakeApi()
    snapshot_path = tmp_path / "before.json"
    sentinel = b"original rollback bytes\x00\xff"
    snapshot_path.write_bytes(sentinel)

    with pytest.raises(policy_tool.PolicyError, match="already exists"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, snapshot_path)

    assert snapshot_path.read_bytes() == sentinel
    assert all(method == "GET" for method, _endpoint, _payload in api.calls)


def test_concurrent_drift_aborts_before_first_mutation(tmp_path: Path) -> None:
    api = FakeApi()
    api.concurrent_ruleset_drift = True

    with pytest.raises(policy_tool.PolicyError, match="changed after snapshot"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert all(method == "GET" for method, _endpoint, _payload in api.calls)


def test_moved_dev_after_green_evidence_aborts_before_first_mutation(tmp_path: Path) -> None:
    api = FakeApi()
    expected_sha = api.dev_sha
    api.move_dev_on_read = 2

    with pytest.raises(policy_tool.PolicyError, match="dev moved after green evidence"):
        policy_tool.apply_policy(api, _policy(), expected_sha, tmp_path / "before.json")

    assert all(method == "GET" for method, _endpoint, _payload in api.calls)


def test_moved_dev_during_apply_rolls_back_every_mutation(tmp_path: Path) -> None:
    api = FakeApi()
    expected_sha = api.dev_sha
    api.move_dev_on_read = 3
    original_ruleset = deepcopy(api.ruleset)
    original_main_ruleset = deepcopy(api.main_ruleset)
    original_repository = deepcopy(api.repository)

    with pytest.raises(policy_tool.PolicyError, match="dev moved during policy apply"):
        policy_tool.apply_policy(api, _policy(), expected_sha, tmp_path / "before.json")

    assert policy_tool.normalize_ruleset(api.ruleset) == policy_tool.normalize_ruleset(
        original_ruleset
    )
    assert policy_tool.normalize_ruleset(api.main_ruleset) == policy_tool.normalize_ruleset(
        original_main_ruleset
    )
    assert api.repository == original_repository
    assert api.labels == []


def test_failed_ruleset_update_rolls_back_repo_and_new_label(tmp_path: Path) -> None:
    api = FakeApi()
    api.fail_method_endpoint = (
        "PUT",
        policy_tool.DEV_RULESET_ENDPOINT.format(ruleset_id=18807584),
    )
    original_repository = deepcopy(api.repository)

    with pytest.raises(policy_tool.GitHubApiError, match="injected PUT failure"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert api.repository == original_repository
    assert api.labels == []
    ruleset_endpoint = policy_tool.DEV_RULESET_ENDPOINT.format(ruleset_id=18807584)
    assert sum(call[:2] == ("PUT", ruleset_endpoint) for call in api.calls) == 1


@pytest.mark.parametrize(
    ("method", "endpoint"),
    [
        ("POST", policy_tool.LABELS_ENDPOINT),
        ("PATCH", policy_tool.REPOSITORY_ENDPOINT),
        ("PUT", policy_tool.DEV_RULESET_ENDPOINT.format(ruleset_id=18807584)),
        ("PUT", policy_tool.MAIN_RULESET_ENDPOINT.format(ruleset_id=18807583)),
    ],
)
def test_ambiguous_committed_write_is_discovered_and_rolled_back(
    tmp_path: Path,
    method: str,
    endpoint: str,
) -> None:
    api = FakeApi()
    api.mutate_then_fail_method_endpoint = (method, endpoint)
    original_ruleset = deepcopy(api.ruleset)
    original_repository = deepcopy(api.repository)

    with pytest.raises(policy_tool.GitHubApiError, match=f"ambiguous {method} failure"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert policy_tool.normalize_ruleset(api.ruleset) == policy_tool.normalize_ruleset(
        original_ruleset
    )
    assert api.repository == original_repository
    assert api.labels == []


def test_failed_label_create_does_not_delete_an_absent_label(tmp_path: Path) -> None:
    api = FakeApi()
    api.fail_method_endpoint = ("POST", policy_tool.LABELS_ENDPOINT)

    with pytest.raises(policy_tool.GitHubApiError, match="injected POST failure"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert not any(call[0] == "DELETE" for call in api.calls)
    assert api.labels == []


def test_failed_repository_update_rolls_back_only_the_created_label(tmp_path: Path) -> None:
    api = FakeApi()
    api.fail_method_endpoint = ("PATCH", policy_tool.REPOSITORY_ENDPOINT)
    original_ruleset = deepcopy(api.ruleset)
    original_repository = deepcopy(api.repository)

    with pytest.raises(policy_tool.GitHubApiError, match="injected PATCH failure"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert api.repository == original_repository
    assert api.ruleset == original_ruleset
    assert api.labels == []
    assert not any(call[0] == "PUT" for call in api.calls)


def test_oserror_after_label_creation_still_rolls_back_the_label(tmp_path: Path) -> None:
    api = FakeApi()
    api.fail_oserror_method_endpoint = ("PATCH", policy_tool.REPOSITORY_ENDPOINT)

    with pytest.raises(OSError, match="spawn failure"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert api.labels == []


def test_readback_mismatch_rolls_back_every_mutation(tmp_path: Path) -> None:
    api = FakeApi()
    api.mismatch_ruleset_readback = True
    original_ruleset = deepcopy(api.ruleset)
    original_repository = deepcopy(api.repository)

    with pytest.raises(policy_tool.PolicyError, match="readback mismatch"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert policy_tool.normalize_ruleset(api.ruleset) == policy_tool.normalize_ruleset(
        original_ruleset
    )
    assert api.repository == original_repository
    assert api.labels == []


def test_recoverable_policy_error_during_rollback_read_uses_attempted_writes(
    tmp_path: Path,
) -> None:
    api = FakeApi()
    api.move_dev_on_read = 3
    api.policy_error_ruleset_read = 4
    original_ruleset = deepcopy(api.ruleset)
    original_repository = deepcopy(api.repository)

    with pytest.raises(policy_tool.PolicyError, match="dev moved during policy apply"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert policy_tool.normalize_ruleset(api.ruleset) == policy_tool.normalize_ruleset(
        original_ruleset
    )
    assert api.repository == original_repository
    assert api.labels == []


def test_rollback_attempts_every_component_after_one_restore_fails(tmp_path: Path) -> None:
    api = FakeApi()
    api.mismatch_ruleset_readback = True
    api.fail_ruleset_restore = True
    original_repository = deepcopy(api.repository)

    with pytest.raises(policy_tool.PolicyError, match="rollback also failed"):
        policy_tool.apply_policy(api, _policy(), api.dev_sha, tmp_path / "before.json")

    assert api.repository == original_repository
    assert api.labels == []
    assert any(call[0] == "DELETE" for call in api.calls)


def test_manual_rollback_restores_snapshot_and_verifies_readback(tmp_path: Path) -> None:
    api = FakeApi()
    original_ruleset = deepcopy(api.ruleset)
    original_main_ruleset = deepcopy(api.main_ruleset)
    original_repository = deepcopy(api.repository)
    snapshot_path = tmp_path / "before.json"
    policy_tool.apply_policy(api, _policy(), api.dev_sha, snapshot_path)

    policy_tool.rollback_policy(api, policy_tool.load_snapshot(snapshot_path))

    assert policy_tool.normalize_ruleset(api.ruleset) == policy_tool.normalize_ruleset(
        original_ruleset
    )
    assert policy_tool.normalize_ruleset(api.main_ruleset) == policy_tool.normalize_ruleset(
        original_main_ruleset
    )
    assert api.repository == original_repository
    assert api.labels == []


def test_manual_rollback_refuses_a_stale_dev_snapshot_without_mutation(tmp_path: Path) -> None:
    api = FakeApi()
    snapshot_path = tmp_path / "before.json"
    policy_tool.apply_policy(api, _policy(), api.dev_sha, snapshot_path)
    snapshot = policy_tool.load_snapshot(snapshot_path)
    api.calls.clear()
    api.dev_sha = "b" * 40

    with pytest.raises(policy_tool.PolicyError, match="snapshot dev"):
        policy_tool.rollback_policy(api, snapshot)

    assert all(method == "GET" for method, _endpoint, _payload in api.calls)


def test_manual_rollback_refuses_tampered_scope_before_mutation(tmp_path: Path) -> None:
    api = FakeApi()
    snapshot_path = tmp_path / "before.json"
    policy_tool.apply_policy(api, _policy(), api.dev_sha, snapshot_path)
    snapshot = policy_tool.load_snapshot(snapshot_path)
    snapshot["dev_ruleset"]["conditions"]["ref_name"]["include"].append("refs/heads/main")
    api.calls.clear()

    with pytest.raises(policy_tool.PolicyError, match="exact dev-only branch scope"):
        policy_tool.rollback_policy(api, snapshot)

    assert api.calls == []


def test_manual_rollback_refuses_tampered_main_scope_before_mutation(tmp_path: Path) -> None:
    api = FakeApi()
    snapshot_path = tmp_path / "before.json"
    policy_tool.apply_policy(api, _policy(), api.dev_sha, snapshot_path)
    snapshot = policy_tool.load_snapshot(snapshot_path)
    snapshot["main_ruleset"]["conditions"]["ref_name"]["include"].append("refs/heads/dev")
    api.calls.clear()

    with pytest.raises(policy_tool.PolicyError, match="exact main-only branch scope"):
        policy_tool.rollback_policy(api, snapshot)

    assert api.calls == []


def test_manual_rollback_refuses_a_different_ruleset_id_before_mutation(tmp_path: Path) -> None:
    api = FakeApi()
    snapshot_path = tmp_path / "before.json"
    policy_tool.apply_policy(api, _policy(), api.dev_sha, snapshot_path)
    snapshot = policy_tool.load_snapshot(snapshot_path)
    snapshot["dev_ruleset_id"] = 999
    api.calls.clear()

    with pytest.raises(policy_tool.PolicyError, match="ruleset ID changed"):
        policy_tool.rollback_policy(api, snapshot)

    assert all(method == "GET" for method, _endpoint, _payload in api.calls)
