#!/usr/bin/env python3
"""Serial Dependabot merge conveyor: ``mise run deps:conveyor``.

Mechanizes the backlog-clearing loop that was twice rebuilt by hand in
``/tmp`` (2026-09-02 sessions): open Dependabot PRs serialize against each
other because every merge to ``dev`` stales the rest, so a human babysitting
``pr:merge`` one PR at a time wastes an hour per pass.

Each pass:

1. ``CLEAN`` PRs merge via the one sanctioned path (``tools/pr_merge.py``),
   then the pass restarts — the merge staled every sibling.
2. ``BEHIND`` but ``MERGEABLE`` PRs get a base-branch update (``gh api
   .../update-branch``), which triggers fresh exact-head CI.
3. Anything else (``BLOCKED``, ``CONFLICTING``, checks pending) waits.

The loop exits 0 when no Dependabot PRs remain open. It never force-merges,
never resolves conflicts itself, and never retries a refused merge within
the same pass — a refusal is state for a human or the next pass, not noise.

Stdlib + ``gh`` only, same contract as ``tools/pr_merge.py``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Final

REPO: Final = "percy-raskova/babylon"
LIST_FIELDS: Final = "number,mergeStateStatus,mergeable"


@dataclass(frozen=True)
class OpenPr:
    number: int
    state: str
    mergeable: str


def gh_json(args: list[str]) -> list[dict[str, object]]:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {proc.stderr.strip()}")
    payload = json.loads(proc.stdout)
    if not isinstance(payload, list):
        raise RuntimeError(f"gh {' '.join(args)} returned non-list payload")
    return payload


def list_open_prs() -> list[OpenPr]:
    rows = gh_json(
        [
            "pr",
            "list",
            "--repo",
            REPO,
            "--state",
            "open",
            "--author",
            "app/dependabot",
            "--limit",
            "30",
            "--json",
            LIST_FIELDS,
        ]
    )
    return [
        OpenPr(
            number=int(row["number"]),
            state=str(row["mergeStateStatus"]),
            mergeable=str(row["mergeable"]),
        )
        for row in rows
    ]


def try_merge(number: int) -> bool:
    """One sanctioned merge attempt; True only on a confirmed merge."""
    proc = subprocess.run(
        [sys.executable, "tools/pr_merge.py", str(number)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (proc.stdout + proc.stderr).strip()
    print(f"~~~ pr:merge {number} exit={proc.returncode}")
    for line in output.splitlines():
        print(f"    {line}")
    return proc.returncode == 0


def update_branch(number: int) -> bool:
    proc = subprocess.run(
        ["gh", "api", f"repos/{REPO}/pulls/{number}/update-branch", "-X", "PUT"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(f"~~~ update-branch {number} failed (conflict?): {proc.stderr.strip()}")
        return False
    print(f"~~~ update-branch {number} accepted")
    return True


def conveyor_pass() -> tuple[int, bool]:
    """One sweep. Returns (open count, merged something this pass)."""
    prs = list_open_prs()
    if not prs:
        return 0, False
    summary = ", ".join(f"{p.number}:{p.state}" for p in prs)
    print(f"=== conveyor pass {time.strftime('%Y-%m-%dT%H:%M:%S%z')}: {summary}")
    for pr in prs:
        if pr.state == "CLEAN":
            if try_merge(pr.number):
                print(f"~~~ MERGED {pr.number}")
                return len(prs), True
            print(f"~~~ pr:merge {pr.number} refused/failed — left for next pass")
        elif pr.state == "BEHIND" and pr.mergeable == "MERGEABLE":
            update_branch(pr.number)
        else:
            print(f"~~~ {pr.number} state={pr.state} mergeable={pr.mergeable} — waiting")
    return len(prs), False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--interval", type=int, default=120, help="seconds between passes")
    parser.add_argument(
        "--max-passes",
        type=int,
        default=0,
        help="stop after N passes even if PRs remain (0 = run until empty)",
    )
    args = parser.parse_args()

    passes = 0
    while True:
        remaining, merged = conveyor_pass()
        passes += 1
        if remaining == 0:
            print(
                f"=== conveyor: no open dependabot PRs — done {time.strftime('%Y-%m-%dT%H:%M:%S%z')}"
            )
            return 0
        if args.max_passes and passes >= args.max_passes:
            print(f"=== conveyor: max-passes {args.max_passes} reached with {remaining} open")
            return 1
        if not merged:
            print(f"~~~ no merge this pass; sleeping {args.interval}s")
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
