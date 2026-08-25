#!/usr/bin/env python3
"""The one sanctioned merge path (ADR181 R10): ``mise run pr:merge -- <pr>``.

Mechanizes the merge-protocol prose rules (CLAUDE.md "Merge protocol"),
each of which has already bitten:

1. Never ``--auto`` (#392: it ignores failing non-required checks) — this
   wrapper simply has no such flag.
2. All checks green AND both PR refs unchanged across the verdict snapshot.
3. A completed Copilot review must target the verified head; every top-level
   Copilot inline comment needs a reply; and every review thread must resolve.
4. Any open code-scanning alert is a STOP (CodeQL no longer runs on PRs — R5b
   — so the alert DB, not a PR check, is the source of truth).
5. ``--delete-branch`` is refused for ``dev`` and while another open PR bases
   on the head (#193: deleting it closes-not-merges the child).

Stdlib + ``gh`` only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.pr_policy import (  # noqa: E402
    DEV_CHECK_MANIFEST,
    CheckRequirement,
    manifest_for_base,
)

MAX_GITHUB_ITEMS = 100

COMPLETED_REVIEW_STATES = {"APPROVED", "CHANGES_REQUESTED", "COMMENTED"}
COPILOT_GRAPHQL_LOGIN = "copilot-pull-request-reviewer"
COPILOT_REST_REVIEW_LOGIN = "copilot-pull-request-reviewer[bot]"
COPILOT_REST_COMMENT_LOGIN = "Copilot"
COPILOT_BOT_ID = 175728472
COPILOT_BOT_NODE_ID = "BOT_kgDOCnlnWA"
DEPENDABOT_LOGIN = "dependabot[bot]"
ALLOWED_DEPENDABOT_UPDATE_TYPES = frozenset(
    {"version-update:semver-patch", "version-update:semver-minor"}
)
_DEPENDABOT_UPDATE_TYPE = re.compile(
    r"^\s*update-type:\s*(version-update:semver-[a-z]+)\s*$",
    re.MULTILINE,
)

_REVIEW_THREADS_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          isResolved
          comments(first: 1) {
            nodes { url }
          }
        }
        pageInfo { hasNextPage }
      }
    }
  }
}
"""


def _gh(*args: str) -> str:
    """Run gh and return stdout; a nonzero exit aborts loudly."""
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def _gh_json(*args: str) -> object:
    return json.loads(_gh(*args))


def _json_dict(value: object, context: str) -> dict[str, object]:
    """Require one JSON object from a GitHub response."""
    if not isinstance(value, dict):
        raise RuntimeError(f"{context} must be a JSON object")
    return value


def _json_dicts(
    value: object,
    context: str,
    *,
    refuse_full_page: bool = False,
) -> list[dict[str, object]]:
    """Require one JSON array containing only objects."""
    if not isinstance(value, list):
        raise RuntimeError(f"{context} must be a JSON array")
    if len(value) > MAX_GITHUB_ITEMS or (refuse_full_page and len(value) == MAX_GITHUB_ITEMS):
        raise RuntimeError(f"{context} reached the {MAX_GITHUB_ITEMS}-item safety bound")
    items: list[dict[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RuntimeError(f"{context}[{index}] must be a JSON object")
        items.append(item)
    return items


def _entry_sort_key(entry: dict[str, object]) -> tuple[str, int]:
    """Recency key for duplicate check names on one head SHA.

    Re-runs (flake retry, close/reopen refire) leave several rollup entries
    per name; branch protection evaluates the LATEST per context and so must
    we — a superseded failure must not poison the verdict (bit PR #673 on
    2026-08-21). Prefer ``startedAt``; fall back to the run id embedded in
    ``detailsUrl`` (``.../actions/runs/<id>/job/...``).
    """
    started = str(entry.get("startedAt") or "")
    if started:
        return (started, 0)
    url = str(entry.get("detailsUrl") or entry.get("targetUrl") or "")
    run_id = 0
    if "/actions/runs/" in url:
        tail = url.split("/actions/runs/", 1)[1].split("/", 1)[0]
        run_id = int(tail) if tail.isdigit() else 0
    return ("", run_id)


def _rollup_failures(
    rollup: list[dict[str, object]],
    manifest: tuple[CheckRequirement, ...] = DEV_CHECK_MANIFEST,
) -> list[str]:
    """Return incomplete or disallowed latest check conclusions."""
    if len(rollup) >= MAX_GITHUB_ITEMS:
        raise RuntimeError(f"status-check rollup reached the {MAX_GITHUB_ITEMS}-item safety bound")
    if len(manifest) >= MAX_GITHUB_ITEMS:
        raise RuntimeError(f"check manifest reached the {MAX_GITHUB_ITEMS}-item safety bound")
    latest: dict[str, dict[str, object]] = {}
    for entry in rollup:
        name = str(entry.get("name") or entry.get("context") or "?")
        if name not in latest or _entry_sort_key(entry) >= _entry_sort_key(latest[name]):
            latest[name] = entry
    expected = {requirement.context: requirement for requirement in manifest}
    failures: list[str] = []
    reported: set[str] = set()
    for entry in latest.values():
        name = str(entry.get("name") or entry.get("context") or "?")
        status = str(entry.get("status") or "")
        conclusion = str(entry.get("conclusion") or entry.get("state") or "")
        requirement = expected.get(name)
        if status and status != "COMPLETED":
            failures.append(f"{name}: still {status}")
        elif requirement is None and conclusion != "SUCCESS":
            failures.append(f"{name}: {conclusion}")
        elif requirement is not None and conclusion not in requirement.allowed_conclusions:
            failures.append(f"{name}: {conclusion}")
        if requirement is not None:
            reported.add(name)
    failures.extend(
        f"{requirement.context}: missing from complete {requirement.kind} manifest"
        for requirement in manifest
        if requirement.context not in reported
    )
    return failures


def _unharvested_copilot_comments(pr: int) -> list[str]:
    """Top-level Copilot inline comments with no reply."""
    comments = _json_dicts(
        _gh_json(
            "api",
            f"repos/{{owner}}/{{repo}}/pulls/{pr}/comments?per_page={MAX_GITHUB_ITEMS}",
        ),
        "pull-request comments",
        refuse_full_page=True,
    )
    replied_to = {c.get("in_reply_to_id") for c in comments}
    return [
        f"unaddressed Copilot comment {c['html_url']}"
        for c in comments
        if _is_rest_copilot_comment(c.get("user"))
        and c.get("in_reply_to_id") is None
        and c["id"] not in replied_to
    ]


def _is_graphql_copilot_review(author: object) -> bool:
    """Match the exact Copilot identity emitted by ``gh pr view``."""
    if not isinstance(author, dict):
        return False
    return author.get("login") == COPILOT_GRAPHQL_LOGIN


def _is_canonical_rest_copilot(author: object, expected_login: str) -> bool:
    """Match a REST Copilot actor by endpoint login and immutable bot identity."""
    if not isinstance(author, dict):
        return False
    return (
        author.get("login") == expected_login
        and author.get("id") == COPILOT_BOT_ID
        and author.get("node_id") == COPILOT_BOT_NODE_ID
        and author.get("type") == "Bot"
    )


def _is_rest_copilot_review(author: object) -> bool:
    return _is_canonical_rest_copilot(author, COPILOT_REST_REVIEW_LOGIN)


def _is_rest_copilot_comment(author: object) -> bool:
    return _is_canonical_rest_copilot(author, COPILOT_REST_COMMENT_LOGIN)


def _rest_reviews(pr: int) -> list[dict[str, object]]:
    return _json_dicts(
        _gh_json(
            "api",
            f"repos/{{owner}}/{{repo}}/pulls/{pr}/reviews?per_page={MAX_GITHUB_ITEMS}",
        ),
        "REST pull-request reviews",
        refuse_full_page=True,
    )


def _has_completed_copilot_review(
    graphql_reviews: object,
    rest_reviews: list[dict[str, object]],
    head_oid: str,
) -> bool:
    """Whether both GitHub views identify Copilot's completed exact-head review."""
    graphql_match = False
    for review in _json_dicts(graphql_reviews, "GraphQL pull-request reviews"):
        commit = review.get("commit")
        commit_oid = commit.get("oid") if isinstance(commit, dict) else None
        if (
            _is_graphql_copilot_review(review.get("author"))
            and review.get("submittedAt")
            and review.get("state") in COMPLETED_REVIEW_STATES
            and commit_oid == head_oid
        ):
            graphql_match = True
    rest_match = any(
        _is_rest_copilot_review(review.get("user"))
        and review.get("submitted_at")
        and review.get("state") in COMPLETED_REVIEW_STATES
        and review.get("commit_id") == head_oid
        for review in rest_reviews
    )
    return graphql_match and rest_match


def _review_thread_problems(pr: int) -> list[str]:
    """Query at most 100 threads and report every unresolved one."""
    response = _json_dict(
        _gh_json(
            "api",
            "graphql",
            "-F",
            "owner={owner}",
            "-F",
            "name={repo}",
            "-F",
            f"number={pr}",
            "-f",
            f"query={_REVIEW_THREADS_QUERY}",
        ),
        "review-thread response",
    )
    data = _json_dict(response.get("data"), "review-thread data")
    repository = _json_dict(data.get("repository"), "review-thread repository")
    pull_request = _json_dict(repository.get("pullRequest"), "review-thread pull request")
    connection = _json_dict(pull_request.get("reviewThreads"), "review-thread connection")
    page_info = _json_dict(connection.get("pageInfo"), "review-thread page info")
    has_next_page = page_info.get("hasNextPage")
    if not isinstance(has_next_page, bool):
        raise RuntimeError("review-thread hasNextPage must be a boolean")
    problems = (
        ["more than 100 review threads — bounded verification refused"] if has_next_page else []
    )
    for node in _json_dicts(connection.get("nodes"), "review-thread nodes"):
        is_resolved = node.get("isResolved")
        if not isinstance(is_resolved, bool):
            raise RuntimeError("review-thread isResolved must be a boolean")
        if not is_resolved:
            problems.append(f"unresolved review thread {_first_thread_url(node)}")
    return problems


def _first_thread_url(thread: dict[str, object]) -> str:
    """Return the first comment URL identifying a review thread."""
    comments = _json_dict(thread.get("comments"), "review-thread comments")
    nodes = _json_dicts(comments.get("nodes"), "review-thread comment nodes")
    if not nodes:
        return "(URL unavailable)"
    return str(nodes[0].get("url") or "(URL unavailable)")


def _open_alert_count() -> int:
    return len(
        _json_dicts(
            _gh_json(
                "api",
                "repos/{owner}/{repo}/code-scanning/alerts"
                f"?state=open&per_page={MAX_GITHUB_ITEMS}",
            ),
            "code-scanning alerts",
        )
    )


def _child_prs(head_ref: str) -> list[int]:
    prs = _json_dicts(
        _gh_json(
            "pr",
            "list",
            "--state",
            "open",
            "--base",
            head_ref,
            "--limit",
            str(MAX_GITHUB_ITEMS),
            "--json",
            "number",
        ),
        "child pull requests",
    )
    numbers: list[int] = []
    for pr in prs:
        number = pr.get("number")
        if not isinstance(number, int):
            raise RuntimeError("child pull-request number must be an integer")
        numbers.append(number)
    return numbers


def _dependabot_pr_problems(pr: int, head_oid: str) -> list[str]:
    """Revalidate exact-head Dependabot authority from trusted GitHub records."""
    payload = _json_dict(
        _gh_json("api", f"repos/{{owner}}/{{repo}}/pulls/{pr}"),
        "Dependabot pull request",
    )
    problems: list[str] = []
    user = payload.get("user")
    if not isinstance(user, dict) or (
        user.get("login") != DEPENDABOT_LOGIN or user.get("type") != "Bot"
    ):
        problems.append("Dependabot mode requires the exact Dependabot bot author")
    head = payload.get("head")
    rest_head = head.get("sha") if isinstance(head, dict) else None
    if rest_head != head_oid:
        problems.append(f"Dependabot head moved: expected {head_oid}, found {rest_head}")
    base = payload.get("base")
    rest_base = base.get("ref") if isinstance(base, dict) else None
    if rest_base != "dev":
        problems.append(f"Dependabot mode requires base dev, found {rest_base}")
    commits = _json_dicts(
        _gh_json(
            "api",
            f"repos/{{owner}}/{{repo}}/pulls/{pr}/commits?per_page={MAX_GITHUB_ITEMS}",
        ),
        "Dependabot pull-request commits",
        refuse_full_page=True,
    )
    problems.extend(_dependabot_commit_problems(commits, head_oid))
    return problems


def _dependabot_commit_problems(
    commits: list[dict[str, object]],
    head_oid: str,
) -> list[str]:
    """Validate one verified Dependabot commit and its signed update metadata."""
    if len(commits) != 1:
        return [f"Dependabot exact head requires one commit, found {len(commits)}"]
    candidate = commits[0]
    author = candidate.get("author")
    commit = candidate.get("commit")
    commit_payload = commit if isinstance(commit, dict) else {}
    verification = commit_payload.get("verification")
    verified = verification if isinstance(verification, dict) else {}
    if (
        candidate.get("sha") != head_oid
        or not isinstance(author, dict)
        or author.get("login") != DEPENDABOT_LOGIN
        or author.get("type") != "Bot"
        or verified.get("verified") is not True
        or verified.get("reason") != "valid"
    ):
        return ["Dependabot exact head is not one verified Dependabot commit"]
    message = commit_payload.get("message")
    if not isinstance(message, str):
        return ["verified Dependabot commit has no message metadata"]
    update_types = _DEPENDABOT_UPDATE_TYPE.findall(message)
    if not update_types or len(update_types) >= MAX_GITHUB_ITEMS:
        return ["verified Dependabot commit has no bounded update-type metadata"]
    disallowed = sorted(set(update_types) - ALLOWED_DEPENDABOT_UPDATE_TYPES)
    if disallowed:
        return [f"Dependabot update type(s) are not eligible: {disallowed}"]
    return []


def _base_policy_problems(
    base_ref: str,
    head_ref: str,
    *,
    director_main: bool,
    delete_branch: bool,
) -> list[str]:
    """Enforce the ordinary dev lane and Director-only main lane."""
    problems: list[str] = []
    if director_main:
        if base_ref != "main":
            problems.append(f"--director-main requires base main, found {base_ref}")
        elif head_ref != "dev" and not head_ref.startswith("fix/"):
            problems.append(f"main requires head dev or fix/*, found {head_ref}")
    elif base_ref != "dev":
        problems.append(f"base branch {base_ref} is not dev")
    if delete_branch and head_ref == "dev":
        problems.append("--delete-branch refused for protected branch dev")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr", type=int)
    parser.add_argument("--delete-branch", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--expected-head")
    parser.add_argument("--director-main", action="store_true")
    parser.add_argument("--dependabot", action="store_true")
    args = parser.parse_args()

    view = _json_dict(
        _gh_json(
            "pr",
            "view",
            str(args.pr),
            "--json",
            "state,isDraft,headRefOid,headRefName,baseRefOid,baseRefName,statusCheckRollup,reviews",
        ),
        "pull-request snapshot",
    )
    head_oid = str(view.get("headRefOid") or "")
    head_ref = str(view.get("headRefName") or "")
    base_oid = str(view.get("baseRefOid") or "")
    base_ref = str(view.get("baseRefName") or "")
    problems: list[str] = []
    if view.get("state") != "OPEN" or view.get("isDraft"):
        problems.append(f"PR #{args.pr} is {view.get('state')}, draft={view.get('isDraft')}")
    problems.extend(
        _base_policy_problems(
            base_ref,
            head_ref,
            director_main=args.director_main,
            delete_branch=args.delete_branch,
        )
    )
    if args.expected_head is not None and args.expected_head != head_oid:
        problems.append(f"expected head {args.expected_head}, found {head_oid}")
    rollup = view.get("statusCheckRollup") or []
    if not rollup:
        problems.append("no checks reported on the head commit")
    manifest = manifest_for_base(base_ref) if base_ref in {"dev", "main"} else ()
    problems.extend(_rollup_failures(_json_dicts(rollup, "status-check rollup"), manifest))
    if not _has_completed_copilot_review(view.get("reviews"), _rest_reviews(args.pr), head_oid):
        problems.append("no completed Copilot review on verified head")
    problems.extend(_unharvested_copilot_comments(args.pr))
    problems.extend(_review_thread_problems(args.pr))
    if (alerts := _open_alert_count()) > 0:
        problems.append(f"{alerts} open code-scanning alert(s) — the zero floor is a STOP")
    if args.delete_branch and (children := _child_prs(head_ref)):
        problems.append(
            f"--delete-branch refused: open PR(s) {children} base on this branch (#193 class)"
        )
    if args.dependabot:
        problems.extend(_dependabot_pr_problems(args.pr, head_oid))

    # Race guard: neither side may move after its verdict snapshot.
    refs_now = _json_dict(
        _gh_json("pr", "view", str(args.pr), "--json", "headRefOid,baseRefOid"),
        "pull-request ref re-read",
    )
    if refs_now.get("headRefOid") != head_oid:
        problems.append("head moved while verifying — re-run against the new head")
    if refs_now.get("baseRefOid") != base_oid:
        problems.append("base moved while verifying — re-run against the new base")

    if problems:
        for problem in problems:
            print(f"pr:merge REFUSED — {problem}", file=sys.stderr)
        return 1

    if args.verify_only:
        print(f"pr:merge: PR #{args.pr} verified at {head_oid}")
        return 0

    merge_args = [
        "pr",
        "merge",
        str(args.pr),
        "--merge",
        "--match-head-commit",
        head_oid,
    ]
    if args.delete_branch:
        merge_args.append("--delete-branch")
    print(_gh(*merge_args), end="")
    print(f"pr:merge: PR #{args.pr} merged at {head_oid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
