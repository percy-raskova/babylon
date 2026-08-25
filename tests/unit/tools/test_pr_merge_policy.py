"""Behavior contracts for the sanctioned pull-request merge verifier."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PR_MERGE = REPO_ROOT / "tools" / "pr_merge.py"
HEAD_SHA = "a" * 40
BASE_SHA = "b" * 40
OTHER_SHA = "c" * 40

COPILOT_BOT_ID = 175728472
COPILOT_BOT_NODE_ID = "BOT_kgDOCnlnWA"

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

MAIN_BLOCKING_CHECKS = (
    "Fast Gate (hygiene, lint, format, imports, types, lock)",
    "Unit Tests (xdist, coverage gate)",
    "Determinism Gate (byte-identical dense goldens)",
    "Security Audit (pip-audit policy — blocking since item-41)",
    "Non-Unit Tests (integration, scenarios, property, contract)",
    "Postgres Integration (web bridge)",
    "Determinism Bundle (Postgres-backed, strict)",
    "Reference-Data Tests (ci-data-v1 subset)",
    "Documentation Build (doctest blocks; manual advisory)",
    "Secret Scan (gitleaks, full history)",
    "IaC Config Scan (trivy, HIGH+CRITICAL blocking)",
)

MAIN_ADVISORY_CHECKS = (
    "AI Tests (advisory — non-deterministic)",
    "Image Scan (trivy — advisory until postgis bump)",
)

_FAKE_GH = r"""#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
scenario = json.loads(Path(os.environ["FAKE_GH_SCENARIO"]).read_text())
with Path(os.environ["FAKE_GH_CALLS"]).open("a") as call_log:
    call_log.write(json.dumps(args) + "\n")

if args[:2] == ["pr", "view"]:
    fields = args[args.index("--json") + 1]
    if fields == "headRefOid,baseRefOid":
        print(json.dumps(scenario["reread"]))
    else:
        print(json.dumps(scenario["view"]))
elif args[:2] == ["api", "graphql"]:
    print(json.dumps(scenario["threads"]))
elif args[0] == "api" and args[1].startswith(
    "repos/{owner}/{repo}/code-scanning/alerts?state=open"
):
    print(json.dumps(scenario["alerts"]))
elif args[:2] == ["pr", "list"]:
    print(json.dumps(scenario["children"]))
elif args[:2] == ["pr", "merge"]:
    print("merged")
elif args[0] == "api" and args[1].endswith("/reviews?per_page=100"):
    print(json.dumps(scenario["rest_reviews"]))
elif args[0] == "api" and args[1].endswith("/pulls/742"):
    print(json.dumps(scenario["dependabot_pr"]))
elif args[0] == "api" and args[1].endswith("/pulls/742/commits?per_page=100"):
    print(json.dumps(scenario["dependabot_commits"]))
elif args[0] == "api" and "/comments" in args[1]:
    print(json.dumps(scenario["comments"]))
else:
    print(f"unexpected fake gh arguments: {args}", file=sys.stderr)
    raise SystemExit(97)
"""


def _check(
    name: str,
    *,
    conclusion: str = "SUCCESS",
    status: str = "COMPLETED",
) -> dict[str, str]:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "startedAt": "2026-08-25T12:00:00Z",
    }


def _copilot_review(commit_oid: str = HEAD_SHA) -> dict[str, object]:
    return {
        "author": {"login": "copilot-pull-request-reviewer"},
        "commit": {"oid": commit_oid},
        "state": "COMMENTED",
        "submittedAt": "2026-08-25T12:01:00Z",
    }


def _rest_copilot_review(commit_oid: str = HEAD_SHA) -> dict[str, object]:
    return {
        "user": {
            "login": "copilot-pull-request-reviewer[bot]",
            "id": COPILOT_BOT_ID,
            "node_id": COPILOT_BOT_NODE_ID,
            "type": "Bot",
        },
        "commit_id": commit_oid,
        "state": "COMMENTED",
        "submitted_at": "2026-08-25T12:01:00Z",
    }


def _dependabot_commit(
    *,
    head_sha: str = HEAD_SHA,
    update_type: str = "version-update:semver-minor",
) -> dict[str, object]:
    return {
        "sha": head_sha,
        "author": {"login": "dependabot[bot]", "type": "Bot"},
        "commit": {
            "message": (
                "Bump dependencies\n\n---\nupdated-dependencies:\n"
                "- dependency-name: example\n"
                f"  update-type: {update_type}\n..."
            ),
            "verification": {"verified": True, "reason": "valid"},
        },
    }


def _default_scenario() -> dict[str, object]:
    return {
        "view": {
            "state": "OPEN",
            "isDraft": False,
            "headRefOid": HEAD_SHA,
            "headRefName": "codex/PER-264-pr-policy",
            "baseRefOid": BASE_SHA,
            "baseRefName": "dev",
            "statusCheckRollup": [_check(name) for name in DEV_BLOCKING_CHECKS],
            "reviews": [_copilot_review()],
        },
        "reread": {"headRefOid": HEAD_SHA, "baseRefOid": BASE_SHA},
        "rest_reviews": [_rest_copilot_review()],
        "comments": [],
        "alerts": [],
        "children": [],
        "dependabot_pr": {
            "head": {"sha": HEAD_SHA},
            "base": {"ref": "dev"},
            "user": {"login": "dependabot[bot]", "type": "Bot"},
        },
        "dependabot_commits": [_dependabot_commit()],
        "threads": {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [],
                            "pageInfo": {"hasNextPage": False},
                        }
                    }
                }
            }
        },
    }


def _run_pr_merge(
    tmp_path: Path,
    *arguments: str,
    scenario: dict[str, object] | None = None,
) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(_FAKE_GH)
    fake_gh.chmod(0o755)
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario or _default_scenario()))
    calls_path = tmp_path / "calls.jsonl"
    env = os.environ.copy()
    env.update(
        {
            "FAKE_GH_CALLS": str(calls_path),
            "FAKE_GH_SCENARIO": str(scenario_path),
            "PATH": f"{fake_bin}:{env['PATH']}",
        }
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(PR_MERGE), "742", *arguments],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    calls = (
        [json.loads(line) for line in calls_path.read_text().splitlines()]
        if calls_path.exists()
        else []
    )
    return result, calls


def _view(scenario: dict[str, object]) -> dict[str, object]:
    view = scenario["view"]
    assert isinstance(view, dict)
    return view


def _merge_calls(calls: list[list[str]]) -> list[list[str]]:
    return [call for call in calls if call[:2] == ["pr", "merge"]]


def _use_main_manifest(scenario: dict[str, object]) -> None:
    _view(scenario)["statusCheckRollup"] = [
        *(_check(name) for name in MAIN_BLOCKING_CHECKS),
        *(_check(name, conclusion="NEUTRAL") for name in MAIN_ADVISORY_CHECKS),
    ]


def _thread_connection(scenario: dict[str, object]) -> dict[str, object]:
    threads = scenario["threads"]
    assert isinstance(threads, dict)
    data = threads["data"]
    assert isinstance(data, dict)
    repository = data["repository"]
    assert isinstance(repository, dict)
    pull_request = repository["pullRequest"]
    assert isinstance(pull_request, dict)
    connection = pull_request["reviewThreads"]
    assert isinstance(connection, dict)
    return connection


def test_verify_only_runs_full_policy_without_merging(tmp_path: Path) -> None:
    result, calls = _run_pr_merge(tmp_path, "--verify-only")

    assert result.returncode == 0, result.stderr
    assert _merge_calls(calls) == []
    assert "verified at" in result.stdout
    assert any(call[:2] == ["api", "graphql"] for call in calls)


def test_all_rest_list_queries_are_bounded_without_pagination(tmp_path: Path) -> None:
    result, calls = _run_pr_merge(tmp_path, "--verify-only", "--delete-branch")

    assert result.returncode == 0, result.stderr
    assert not any("--paginate" in call for call in calls)
    comments = next(call for call in calls if call[0] == "api" and "/comments" in call[1])
    alerts = next(call for call in calls if call[0] == "api" and "code-scanning/alerts" in call[1])
    children = next(call for call in calls if call[:2] == ["pr", "list"])
    assert "per_page=100" in comments[1]
    assert "per_page=100" in alerts[1]
    assert children[children.index("--limit") + 1] == "100"


def test_one_hundred_rest_items_refuses_at_the_static_bound(tmp_path: Path) -> None:
    scenario = _default_scenario()
    scenario["comments"] = [
        {
            "id": index,
            "html_url": f"https://example.test/comment/{index}",
            "in_reply_to_id": None,
            "user": {"login": "human-reviewer"},
        }
        for index in range(100)
    ]

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode != 0
    assert "100-item safety bound" in result.stderr
    assert _merge_calls(calls) == []


def test_one_hundred_check_entries_refuse_a_potentially_truncated_rollup(
    tmp_path: Path,
) -> None:
    scenario = _default_scenario()
    rollup = _view(scenario)["statusCheckRollup"]
    assert isinstance(rollup, list)
    rollup.extend(
        _check(f"Unknown successful extension {index}")
        for index in range(100 - len(DEV_BLOCKING_CHECKS))
    )

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode != 0
    assert "100-item safety bound" in result.stderr
    assert _merge_calls(calls) == []


def test_expected_head_refuses_a_different_snapshot(tmp_path: Path) -> None:
    result, calls = _run_pr_merge(
        tmp_path,
        "--verify-only",
        "--expected-head",
        OTHER_SHA,
    )

    assert result.returncode == 1
    assert "expected head" in result.stderr
    assert _merge_calls(calls) == []


@pytest.mark.parametrize("moved_ref", ["headRefOid", "baseRefOid"])
def test_moved_snapshot_refuses_merge(tmp_path: Path, moved_ref: str) -> None:
    scenario = _default_scenario()
    reread = scenario["reread"]
    assert isinstance(reread, dict)
    reread[moved_ref] = OTHER_SHA

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert f"{moved_ref.removesuffix('RefOid')} moved" in result.stderr
    assert _merge_calls(calls) == []


def test_default_policy_requires_dev_base(tmp_path: Path) -> None:
    scenario = _default_scenario()
    _view(scenario)["baseRefName"] = "feature/stack"

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert "base branch feature/stack is not dev" in result.stderr
    assert _merge_calls(calls) == []


def test_main_base_requires_director_main_flag(tmp_path: Path) -> None:
    scenario = _default_scenario()
    _view(scenario).update({"baseRefName": "main", "headRefName": "fix/security"})

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert "base branch main is not dev" in result.stderr
    assert _merge_calls(calls) == []


@pytest.mark.parametrize("head_name", ["dev", "fix/security"])
def test_director_main_accepts_only_sanctioned_main_sources(tmp_path: Path, head_name: str) -> None:
    scenario = _default_scenario()
    _view(scenario).update({"baseRefName": "main", "headRefName": head_name})
    _use_main_manifest(scenario)

    result, calls = _run_pr_merge(tmp_path, "--director-main", scenario=scenario)

    assert result.returncode == 0, result.stderr
    assert len(_merge_calls(calls)) == 1


def test_director_main_refuses_feature_source(tmp_path: Path) -> None:
    scenario = _default_scenario()
    _view(scenario).update({"baseRefName": "main", "headRefName": "feature/unsafe"})

    result, calls = _run_pr_merge(tmp_path, "--director-main", scenario=scenario)

    assert result.returncode == 1
    assert "main requires head dev or fix/*" in result.stderr
    assert _merge_calls(calls) == []


def test_director_main_flag_is_invalid_for_dev_base(tmp_path: Path) -> None:
    result, calls = _run_pr_merge(tmp_path, "--director-main")

    assert result.returncode == 1
    assert "--director-main requires base main" in result.stderr
    assert _merge_calls(calls) == []


def test_delete_branch_never_deletes_dev(tmp_path: Path) -> None:
    scenario = _default_scenario()
    _view(scenario).update({"baseRefName": "main", "headRefName": "dev"})
    _use_main_manifest(scenario)

    result, calls = _run_pr_merge(
        tmp_path,
        "--director-main",
        "--delete-branch",
        scenario=scenario,
    )

    assert result.returncode == 1
    assert "refused for protected branch dev" in result.stderr
    assert _merge_calls(calls) == []


def test_merge_is_atomically_matched_to_verified_head(tmp_path: Path) -> None:
    result, calls = _run_pr_merge(tmp_path)

    assert result.returncode == 0, result.stderr
    assert _merge_calls(calls) == [
        ["pr", "merge", "742", "--merge", "--match-head-commit", HEAD_SHA]
    ]


@pytest.mark.parametrize(
    "reviews",
    [
        [],
        [_copilot_review(OTHER_SHA)],
        [
            {
                **_copilot_review(),
                "state": "PENDING",
                "submittedAt": None,
            }
        ],
    ],
    ids=["missing", "stale", "pending"],
)
def test_copilot_review_must_be_completed_on_verified_head(
    tmp_path: Path, reviews: list[dict[str, object]]
) -> None:
    scenario = _default_scenario()
    _view(scenario)["reviews"] = reviews

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert "completed Copilot review on verified head" in result.stderr
    assert _merge_calls(calls) == []


@pytest.mark.parametrize(
    "login",
    ["attacker-copilot-reviewer", "copilot-pull-request-reviewer[bot]"],
)
def test_graphql_copilot_review_identity_is_exact(tmp_path: Path, login: str) -> None:
    scenario = _default_scenario()
    review = _copilot_review()
    review["author"] = {"login": login}
    _view(scenario)["reviews"] = [review]

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert "completed Copilot review on verified head" in result.stderr
    assert _merge_calls(calls) == []


@pytest.mark.parametrize(
    ("field", "value"),
    [("id", 1), ("node_id", "BOT_impostor"), ("type", "User")],
)
def test_rest_copilot_review_requires_immutable_bot_identity(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    scenario = _default_scenario()
    review = _rest_copilot_review()
    user = review["user"]
    assert isinstance(user, dict)
    user[field] = value
    scenario["rest_reviews"] = [review]

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert "completed Copilot review on verified head" in result.stderr
    assert _merge_calls(calls) == []


def test_top_level_copilot_comment_still_requires_reply(tmp_path: Path) -> None:
    scenario = _default_scenario()
    scenario["comments"] = [
        {
            "id": 91,
            "html_url": "https://example.test/comment/91",
            "in_reply_to_id": None,
            "user": {
                "login": "Copilot",
                "id": COPILOT_BOT_ID,
                "node_id": COPILOT_BOT_NODE_ID,
                "type": "Bot",
            },
        }
    ]

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert "unaddressed Copilot comment" in result.stderr
    assert _merge_calls(calls) == []


@pytest.mark.parametrize(
    ("name", "conclusion", "status"),
    [
        (DEV_BLOCKING_CHECKS[0], "", "IN_PROGRESS"),
        (DEV_BLOCKING_CHECKS[1], "SKIPPED", "COMPLETED"),
        (DEV_BLOCKING_CHECKS[2], "NEUTRAL", "COMPLETED"),
    ],
    ids=["late", "skipped", "neutral"],
)
def test_every_dev_blocking_check_requires_explicit_success(
    tmp_path: Path,
    name: str,
    conclusion: str,
    status: str,
) -> None:
    scenario = _default_scenario()
    rollup = _view(scenario)["statusCheckRollup"]
    assert isinstance(rollup, list)
    rollup[:] = [
        _check(check_name, conclusion=conclusion, status=status)
        if check_name == name
        else _check(check_name)
        for check_name in DEV_BLOCKING_CHECKS
    ]

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert name in result.stderr
    assert _merge_calls(calls) == []


def test_missing_expected_dev_check_blocks_registration_race(tmp_path: Path) -> None:
    scenario = _default_scenario()
    rollup = _view(scenario)["statusCheckRollup"]
    assert isinstance(rollup, list)
    rollup.pop(0)

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert DEV_BLOCKING_CHECKS[0] in result.stderr
    assert "missing" in result.stderr
    assert _merge_calls(calls) == []


@pytest.mark.parametrize("conclusion", ["NEUTRAL", "SKIPPED"])
def test_unknown_non_successful_check_is_not_globally_advisory(
    tmp_path: Path,
    conclusion: str,
) -> None:
    scenario = _default_scenario()
    rollup = _view(scenario)["statusCheckRollup"]
    assert isinstance(rollup, list)
    rollup.append(_check("Unknown extension", conclusion=conclusion))

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert "Unknown extension" in result.stderr
    assert _merge_calls(calls) == []


def test_unknown_success_is_informational_after_complete_manifest(tmp_path: Path) -> None:
    scenario = _default_scenario()
    rollup = _view(scenario)["statusCheckRollup"]
    assert isinstance(rollup, list)
    rollup.append(_check("Unknown successful extension"))

    result, calls = _run_pr_merge(tmp_path, "--verify-only", scenario=scenario)

    assert result.returncode == 0, result.stderr
    assert _merge_calls(calls) == []


def test_director_main_rejects_complete_dev_manifest_as_wrong_qualification(
    tmp_path: Path,
) -> None:
    scenario = _default_scenario()
    _view(scenario).update({"baseRefName": "main", "headRefName": "dev"})

    result, calls = _run_pr_merge(tmp_path, "--director-main", scenario=scenario)

    assert result.returncode == 1
    assert MAIN_BLOCKING_CHECKS[4] in result.stderr
    assert _merge_calls(calls) == []


def test_dependabot_mode_revalidates_verified_exact_head_metadata(tmp_path: Path) -> None:
    result, calls = _run_pr_merge(tmp_path, "--dependabot")

    assert result.returncode == 0, result.stderr
    assert len(_merge_calls(calls)) == 1
    assert any(call[0] == "api" and call[1].endswith("/commits?per_page=100") for call in calls)


def test_dependabot_major_update_is_never_authorized_by_a_label(tmp_path: Path) -> None:
    scenario = _default_scenario()
    scenario["dependabot_commits"] = [_dependabot_commit(update_type="version-update:semver-major")]

    result, calls = _run_pr_merge(tmp_path, "--dependabot", scenario=scenario)

    assert result.returncode == 1
    assert "semver-major" in result.stderr
    assert _merge_calls(calls) == []


def test_dependabot_synchronization_invalidates_old_head_classification(tmp_path: Path) -> None:
    scenario = _default_scenario()
    dependabot_pr = scenario["dependabot_pr"]
    assert isinstance(dependabot_pr, dict)
    dependabot_pr["head"] = {"sha": OTHER_SHA}

    result, calls = _run_pr_merge(tmp_path, "--dependabot", scenario=scenario)

    assert result.returncode == 1
    assert "Dependabot head" in result.stderr
    assert _merge_calls(calls) == []


def test_dependabot_exact_head_must_be_one_verified_bot_commit(tmp_path: Path) -> None:
    scenario = _default_scenario()
    commit = _dependabot_commit()
    commit_payload = commit["commit"]
    assert isinstance(commit_payload, dict)
    commit_payload["verification"] = {"verified": False, "reason": "unsigned"}
    scenario["dependabot_commits"] = [commit]

    result, calls = _run_pr_merge(tmp_path, "--dependabot", scenario=scenario)

    assert result.returncode == 1
    assert "verified Dependabot commit" in result.stderr
    assert _merge_calls(calls) == []


def test_unresolved_review_thread_refuses_merge(tmp_path: Path) -> None:
    scenario = _default_scenario()
    _thread_connection(scenario)["nodes"] = [
        {
            "isResolved": False,
            "comments": {"nodes": [{"url": "https://example.test/thread/17"}]},
        }
    ]

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert "unresolved review thread https://example.test/thread/17" in result.stderr
    assert _merge_calls(calls) == []


def test_more_than_one_hundred_review_threads_refuses_instead_of_paging(
    tmp_path: Path,
) -> None:
    scenario = _default_scenario()
    connection = _thread_connection(scenario)
    page_info = connection["pageInfo"]
    assert isinstance(page_info, dict)
    page_info["hasNextPage"] = True

    result, calls = _run_pr_merge(tmp_path, scenario=scenario)

    assert result.returncode == 1
    assert "more than 100 review threads" in result.stderr
    graph_calls = [call for call in calls if call[:2] == ["api", "graphql"]]
    assert len(graph_calls) == 1
    assert "--paginate" not in graph_calls[0]
    assert "reviewThreads(first: 100)" in " ".join(graph_calls[0])
    assert _merge_calls(calls) == []


def test_exactly_one_hundred_complete_review_threads_remain_within_bound(
    tmp_path: Path,
) -> None:
    scenario = _default_scenario()
    connection = _thread_connection(scenario)
    connection["nodes"] = [
        {
            "isResolved": True,
            "comments": {"nodes": [{"url": f"https://example.test/thread/{index}"}]},
        }
        for index in range(100)
    ]

    result, calls = _run_pr_merge(tmp_path, "--verify-only", scenario=scenario)

    assert result.returncode == 0, result.stderr
    assert _merge_calls(calls) == []


def test_delete_branch_still_refuses_a_stacked_child(tmp_path: Path) -> None:
    scenario = copy.deepcopy(_default_scenario())
    scenario["children"] = [{"number": 743}]

    result, calls = _run_pr_merge(tmp_path, "--delete-branch", scenario=scenario)

    assert result.returncode == 1
    assert "open PR(s) [743] base on this branch" in result.stderr
    assert _merge_calls(calls) == []
