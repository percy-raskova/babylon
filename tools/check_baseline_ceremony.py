#!/usr/bin/env python3
"""Baseline-ceremony gate — §6.5 Provenance & Ceremony (owner ruling 2026-07-20).

Constitution III.7 says "regenerate the baselines *and say so*"; III.12 makes
the baseline estate a behavioral-contract artifact. This gate makes "say so"
machine-checkable: any commit that touches ``tests/baselines/**`` is a
*ceremony* and must carry a declaration trailer::

    Baselines: blessed(<ceremony-slug>)

where the slug is a lowercase ``[a-z0-9-]`` name for the ceremony (convention:
``<what>-<date>``, e.g. ``post-merge-regen-2026-07-20``). The commit subject
stays the existing ``test(baselines): ...`` convention and the body records
the drift table; the trailer is the greppable provenance record::

    git log --grep 'Baselines: blessed' --format='%h %s'

Two modes (Constitution III.11 — both fail loudly):

``--commit-msg-file PATH``
    Local commit-msg hook: if staged paths touch the baseline estate, the
    commit message must declare the ceremony. Best-effort (an ``--amend``
    with an already-committed baseline change can slip it); CI is
    authoritative.

``--range A..B``
    CI leg: every non-merge commit in the range that touches the baseline
    estate must declare its ceremony. Merge commits are skipped — their
    non-merge parents are inspected individually.

Exit codes: 0 = clean, 1 = undeclared ceremony, 2 = usage or git failure.
Doctrine home: CLAUDE.md "Baseline ceremonies"; the ruling deliberately kept
this out of the constitution (workflow, not law).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# The governed artifact estate. Everything under these prefixes is a pinned
# behavioral-contract artifact (regression baselines, dense goldens, the
# mutation and storage-budget baselines); moving any of it is a ceremony.
BASELINE_PREFIXES: tuple[str, ...] = ("tests/baselines/",)

# Strict trailer grammar: a full line, lowercase slug, no empty blessing.
_TRAILER_RE = re.compile(r"^Baselines: blessed\([a-z0-9][a-z0-9-]*\)$", re.MULTILINE)

_DOCTRINE = """\
tests/baselines/** changed without a ceremony declaration.

  If UNINTENDED: STOP — unexplained baseline drift is a red gate.
  Investigate before committing (Constitution III.7).

  If INTENTIONAL: this commit is a ceremony. Declare it:
    - subject:  test(baselines): <what moved and why>
    - body:     the drift table (per-scenario columns, cell counts, max |d|)
    - trailer:  Baselines: blessed(<ceremony-slug>)
  See CLAUDE.md "Baseline ceremonies".
"""


def _git(repo_root: Path, *args: str) -> str:
    """Run a git plumbing command, raising ``CalledProcessError`` on failure."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def message_declares_ceremony(message: str) -> bool:
    """True iff the message carries a well-formed blessing trailer.

    Comment lines (``#``-prefixed, stripped by git's default cleanup) are
    removed first so a declaration cannot live only inside one.
    """
    effective = "\n".join(line for line in message.splitlines() if not line.startswith("#"))
    return _TRAILER_RE.search(effective) is not None


def touches_baselines(paths: list[str]) -> bool:
    """True iff any path lies inside the governed baseline estate."""
    return any(path.startswith(BASELINE_PREFIXES) for path in paths)


def check_commit_msg(msg_file: Path, repo_root: Path) -> list[str]:
    """commit-msg hook leg: staged baseline paths demand a declared message."""
    staged_raw = _git(repo_root, "diff", "--cached", "--name-only")
    staged = [line for line in staged_raw.splitlines() if line]
    if not touches_baselines(staged):
        return []
    if message_declares_ceremony(msg_file.read_text(encoding="utf-8")):
        return []
    hit = ", ".join(p for p in staged if p.startswith(BASELINE_PREFIXES))
    return [f"staged baseline change(s) without declaration: {hit}"]


def check_range(range_spec: str, repo_root: Path) -> list[str]:
    """CI leg: every non-merge commit in the range must declare its ceremony."""
    shas_raw = _git(repo_root, "rev-list", "--no-merges", range_spec)
    violations: list[str] = []
    for sha in [line for line in shas_raw.splitlines() if line]:
        changed_raw = _git(repo_root, "diff-tree", "--no-commit-id", "--name-only", "-r", sha)
        changed = [line for line in changed_raw.splitlines() if line]
        if not touches_baselines(changed):
            continue
        message = _git(repo_root, "log", "-1", "--format=%B", sha)
        if message_declares_ceremony(message):
            continue
        subject = message.splitlines()[0] if message.splitlines() else ""
        violations.append(f"{sha[:12]} ({subject}): baseline change undeclared")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Baseline-ceremony gate — §6.5 Provenance & Ceremony"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--commit-msg-file",
        type=Path,
        help="commit-msg hook mode: path to the message file under edit",
    )
    mode.add_argument(
        "--range",
        dest="range_spec",
        help="CI mode: git revision range (BASE..HEAD) to inspect",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="repository root (default: current directory)",
    )
    args = parser.parse_args(argv)

    if args.commit_msg_file is None and args.range_spec is None:
        parser.print_usage(sys.stderr)
        print("check_baseline_ceremony: one of --commit-msg-file/--range required", file=sys.stderr)
        return 2

    try:
        if args.commit_msg_file is not None:
            violations = check_commit_msg(args.commit_msg_file, args.repo)
        else:
            violations = check_range(args.range_spec, args.repo)
    except subprocess.CalledProcessError as exc:
        print(f"check_baseline_ceremony: git failed: {exc.stderr.strip()}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"check_baseline_ceremony: {exc}", file=sys.stderr)
        return 2

    if violations:
        for violation in violations:
            print(f"CEREMONY VIOLATION: {violation}", file=sys.stderr)
        print(_DOCTRINE, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
