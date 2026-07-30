#!/usr/bin/env python3
"""The one sanctioned merge path (ADR181 R10): ``mise run pr:merge -- <pr>``.

Mechanizes the four merge-protocol prose rules (CLAUDE.md "Merge protocol"),
each of which has already bitten:

1. Never ``--auto`` (#392: it ignores failing non-required checks) — this
   wrapper simply has no such flag.
2. All checks green AND ``headRefOid`` unchanged across the verdict snapshot
   (a push between "checks green" and "merge" invalidates the verdict).
3. The Copilot harvest: every top-level Copilot inline comment must carry a
   reply (the fix-or-reply obligation, enforceable half). Plus the CodeQL
   zero-floor: any open code-scanning alert is a STOP (CodeQL no longer runs
   on PRs — R5b — so the alert DB, not a PR check, is the source of truth).
4. ``--delete-branch`` refused while another open PR bases on this head
   (#193: closes-not-merges the child on stacked PRs).

Stdlib + ``gh`` only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

#: Checks that must be explicit PASSES (a skip is not a verdict for these).
CRITICAL_CHECKS = (
    "Rust Gate (fmt, clippy, test, doc — rust/ workspace)",
    "Baseline Ceremony Gate (§6.5 provenance)",
    "Postgres Integration Tier (PG 17, digest-pinned container)",
)

GREEN = {"SUCCESS", "NEUTRAL", "SKIPPED"}


def _gh(*args: str) -> str:
    """Run gh and return stdout; a nonzero exit aborts loudly."""
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def _gh_json(*args: str) -> object:
    return json.loads(_gh(*args))


def _rollup_failures(rollup: list[dict[str, object]]) -> list[str]:
    """Names of rollup entries that are not green, plus missing criticals."""
    failures: list[str] = []
    passed: set[str] = set()
    for entry in rollup:
        name = str(entry.get("name") or entry.get("context") or "?")
        status = str(entry.get("status") or "")
        conclusion = str(entry.get("conclusion") or entry.get("state") or "")
        if status and status != "COMPLETED":
            failures.append(f"{name}: still {status}")
        elif conclusion not in GREEN:
            failures.append(f"{name}: {conclusion}")
        elif conclusion == "SUCCESS":
            passed.add(name)
    failures.extend(
        f"{name}: required an explicit PASS, none found"
        for name in CRITICAL_CHECKS
        if name not in passed
    )
    return failures


def _unharvested_copilot_comments(pr: int) -> list[str]:
    """Top-level Copilot inline comments with no reply."""
    comments = _gh_json("api", f"repos/{{owner}}/{{repo}}/pulls/{pr}/comments", "--paginate")
    assert isinstance(comments, list)
    replied_to = {c.get("in_reply_to_id") for c in comments}
    return [
        f"unaddressed Copilot comment {c['html_url']}"
        for c in comments
        if "copilot" in str(c.get("user", {}).get("login", "")).lower()
        and c.get("in_reply_to_id") is None
        and c["id"] not in replied_to
    ]


def _open_alert_count() -> int:
    alerts = _gh_json("api", "repos/{owner}/{repo}/code-scanning/alerts?state=open", "--paginate")
    assert isinstance(alerts, list)
    return len(alerts)


def _child_prs(head_ref: str) -> list[int]:
    prs = _gh_json("pr", "list", "--state", "open", "--base", head_ref, "--json", "number")
    assert isinstance(prs, list)
    return [p["number"] for p in prs]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr", type=int)
    parser.add_argument("--delete-branch", action="store_true")
    args = parser.parse_args()

    view = _gh_json(
        "pr",
        "view",
        str(args.pr),
        "--json",
        "state,isDraft,headRefOid,headRefName,statusCheckRollup",
    )
    assert isinstance(view, dict)
    problems: list[str] = []
    if view["state"] != "OPEN" or view["isDraft"]:
        problems.append(f"PR #{args.pr} is {view['state']}, draft={view['isDraft']}")
    rollup = view.get("statusCheckRollup") or []
    if not rollup:
        problems.append("no checks reported on the head commit")
    problems.extend(_rollup_failures(rollup))
    problems.extend(_unharvested_copilot_comments(args.pr))
    if (alerts := _open_alert_count()) > 0:
        problems.append(f"{alerts} open code-scanning alert(s) — the zero floor is a STOP")
    if args.delete_branch and (children := _child_prs(view["headRefName"])):
        problems.append(
            f"--delete-branch refused: open PR(s) {children} base on this branch (#193 class)"
        )

    # Race guard: the head must not have moved since the verdict snapshot.
    head_now = _gh_json("pr", "view", str(args.pr), "--json", "headRefOid")
    assert isinstance(head_now, dict)
    if head_now["headRefOid"] != view["headRefOid"]:
        problems.append("head moved while verifying — re-run against the new head")

    if problems:
        for problem in problems:
            print(f"pr:merge REFUSED — {problem}", file=sys.stderr)
        return 1

    merge_args = ["pr", "merge", str(args.pr), "--merge"]
    if args.delete_branch:
        merge_args.append("--delete-branch")
    print(_gh(*merge_args), end="")
    print(f"pr:merge: PR #{args.pr} merged at {view['headRefOid']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
