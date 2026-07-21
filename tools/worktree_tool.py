#!/usr/bin/env python3
"""``wt:new`` / ``wt:done`` workspace primitives (git-doctrine adoption item 2).

Roadmap: ``ai/_inbox/archive/tui-roadmap-update.md`` §5.9 adoption order, item
(2). Two subcommands:

``new NAME``
    Validates ``NAME`` against a strict slug grammar, then creates
    ``.claude/worktrees/NAME`` on a fresh branch ``wt/NAME`` (from the
    invoking checkout's current branch) via ``git worktree add``. Prints the
    shadow-venv usage recipe: worktrees never get their own venv — tests run
    via the *main* checkout's venv with a ``PYTHONPATH`` shadow pointing at
    the worktree's ``src/``.

``done NAME``
    Refuses to retire ``.claude/worktrees/NAME`` unless the worktree is
    clean (``git status --porcelain`` empty) *and* its branch ``wt/NAME`` is
    fully merged into the invoking checkout's current branch. ``--force``
    bypasses both checks. On success: ``git worktree remove`` then
    ``git branch -d`` (``-D`` under ``--force``).

Failures are always loud (Constitution III.11) — no silent fallbacks, no
best-effort degradation. Every git failure surfaces the underlying stderr.

Run: ``uv run python tools/worktree_tool.py new my-slug`` /
``uv run python tools/worktree_tool.py done my-slug`` (wired as the mise
tasks ``wt:new`` / ``wt:done``).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

#: Strict worktree-name slug grammar: lowercase alnum segments joined by
#: single hyphens, no leading/trailing/double hyphen, no slashes or
#: underscores (those would collide with the ``wt/<name>`` branch grammar or
#: produce nested/ambiguous worktree directories). Max 64 chars.
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MAX_LEN = 64

#: Branch namespace prefix for worktree-scoped task branches.
BRANCH_PREFIX = "wt/"

#: Location (relative to the main checkout root) that worktrees live under.
WORKTREES_SUBDIR = Path(".claude") / "worktrees"


class WorktreeToolError(RuntimeError):
    """Raised for any loud, user-facing failure of this tool."""


def is_valid_slug(name: str) -> bool:
    """Return whether ``name`` conforms to the strict worktree slug grammar.

    :param name: candidate worktree/branch slug.
    :returns: ``True`` iff ``name`` matches :data:`SLUG_RE` and is within
        :data:`SLUG_MAX_LEN` characters.
    """
    if not name or len(name) > SLUG_MAX_LEN:
        return False
    return bool(SLUG_RE.match(name))


def _run_git(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand, capturing output as text.

    :param args: arguments after ``git`` (e.g. ``["status", "--porcelain"]``).
    :param cwd: directory to run the command in.
    :returns: the completed process (caller inspects ``returncode``/``stdout``).
    :raises WorktreeToolError: if the ``git`` executable itself cannot be
        invoked (not installed / not on PATH).
    """
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise WorktreeToolError(f"git executable not found: {exc}") from exc


def get_main_worktree_root(cwd: Path) -> Path:
    """Resolve the *main* checkout root, even when invoked from a worktree.

    ``git rev-parse --show-toplevel`` returns the invoking worktree's own
    root when run inside a linked worktree, not the main checkout. The
    shared ``.git`` directory (``--git-common-dir``) is always inside the
    main checkout, so its parent is the stable anchor for
    ``.claude/worktrees/``.

    :param cwd: directory to resolve from (must be inside the repo).
    :returns: absolute path to the main checkout root.
    :raises WorktreeToolError: if ``cwd`` is not inside a git repository.
    """
    result = _run_git(["rev-parse", "--git-common-dir"], cwd=cwd)
    if result.returncode != 0:
        raise WorktreeToolError(f"not inside a git repository ({cwd}): {result.stderr.strip()}")
    common_dir = Path(result.stdout.strip())
    if not common_dir.is_absolute():
        common_dir = (cwd / common_dir).resolve()
    return common_dir.parent


def get_current_branch(cwd: Path) -> str:
    """Return the current branch name at ``cwd``.

    :param cwd: directory to resolve from.
    :returns: the branch name.
    :raises WorktreeToolError: on detached HEAD or any git failure.
    """
    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if result.returncode != 0:
        raise WorktreeToolError(f"could not resolve current branch: {result.stderr.strip()}")
    branch = result.stdout.strip()
    if branch == "HEAD":
        raise WorktreeToolError(
            "refusing to operate from a detached HEAD; check out a branch first"
        )
    return branch


def print_usage_recipe(main_root: Path, worktree_path: Path) -> None:
    """Print the shadow-venv + lint-imports usage recipe for a new worktree.

    Worktrees must NOT get their own venv (the worktree-shadow reality,
    ``ai/_inbox/archive/tui-roadmap-update.md``): tests run through the
    *main* checkout's venv with ``PYTHONPATH`` shadowed onto the worktree's
    ``src/`` so imports resolve to the worktree's code, not the main
    checkout's.

    :param main_root: the main checkout root (owns the venv).
    :param worktree_path: the newly created worktree directory.
    """
    venv_python = main_root / ".venv" / "bin" / "python"
    venv_lint_imports = main_root / ".venv" / "bin" / "lint-imports"
    print(f"Worktree ready: {worktree_path}")
    print()
    print("Worktrees share the MAIN checkout's venv (never their own). Run")
    print("scoped tests with PYTHONPATH shadowed onto this worktree's src/:")
    print()
    print(f"  cd {worktree_path} && env PYTHONPATH= {venv_python} -m pytest <path> -q")
    print()
    print("Import-boundary contracts (lint-imports) need the shadow PYTHONPATH set:")
    print()
    print(f'  cd {worktree_path} && env PYTHONPATH="$PWD/src" {venv_lint_imports}')


def cmd_new(name: str, *, cwd: Path) -> int:
    """Implement ``wt:new NAME``.

    :param name: worktree slug.
    :param cwd: directory the tool was invoked from.
    :returns: process exit code.
    """
    if not is_valid_slug(name):
        raise WorktreeToolError(
            f"invalid worktree name {name!r}: must match {SLUG_RE.pattern!r} "
            f"(lowercase alnum segments, single hyphens, max {SLUG_MAX_LEN} chars)"
        )
    main_root = get_main_worktree_root(cwd)
    worktree_path = main_root / WORKTREES_SUBDIR / name
    if worktree_path.exists():
        raise WorktreeToolError(f"worktree path already exists: {worktree_path}")
    branch = f"{BRANCH_PREFIX}{name}"
    base_branch = get_current_branch(cwd)

    result = _run_git(
        ["worktree", "add", "-b", branch, str(worktree_path), base_branch],
        cwd=cwd,
    )
    if result.returncode != 0:
        raise WorktreeToolError(f"git worktree add failed: {result.stderr.strip()}")

    print_usage_recipe(main_root, worktree_path)
    return 0


def _check_worktree_clean(worktree_path: Path) -> str | None:
    """Return a non-empty ``git status --porcelain`` output, or ``None`` if clean.

    :param worktree_path: the worktree directory to inspect.
    :returns: the porcelain status text if dirty, else ``None``.
    :raises WorktreeToolError: if the git invocation itself fails.
    """
    result = _run_git(["status", "--porcelain"], cwd=worktree_path)
    if result.returncode != 0:
        raise WorktreeToolError(
            f"could not check worktree status ({worktree_path}): {result.stderr.strip()}"
        )
    return result.stdout if result.stdout.strip() else None


def _check_branch_merged(branch: str, into_branch: str, *, cwd: Path) -> bool:
    """Return whether ``branch`` is fully merged into ``into_branch``.

    :param branch: candidate branch (e.g. ``wt/my-slug``).
    :param into_branch: target branch (e.g. the invoking checkout's current branch).
    :param cwd: directory to run git in (must be able to see both branches).
    :returns: ``True`` iff every commit on ``branch`` is an ancestor of ``into_branch``.
    :raises WorktreeToolError: if the merge-base check itself errors (not a
        simple "not merged" result — e.g. unknown branch/ref).
    """
    result = _run_git(
        ["merge-base", "--is-ancestor", branch, into_branch],
        cwd=cwd,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise WorktreeToolError(
        f"could not determine merge status of {branch} into {into_branch}: {result.stderr.strip()}"
    )


def cmd_done(name: str, *, cwd: Path, force: bool) -> int:
    """Implement ``wt:done NAME``.

    :param name: worktree slug.
    :param cwd: directory the tool was invoked from.
    :param force: bypass the clean/merged checks (and use ``git worktree
        remove --force`` / ``git branch -D``).
    :returns: process exit code.
    """
    if not is_valid_slug(name):
        raise WorktreeToolError(
            f"invalid worktree name {name!r}: must match {SLUG_RE.pattern!r} "
            f"(lowercase alnum segments, single hyphens, max {SLUG_MAX_LEN} chars)"
        )
    main_root = get_main_worktree_root(cwd)
    worktree_path = main_root / WORKTREES_SUBDIR / name
    if not worktree_path.exists():
        raise WorktreeToolError(f"no such worktree: {worktree_path}")
    branch = f"{BRANCH_PREFIX}{name}"
    into_branch = get_current_branch(cwd)

    if not force:
        dirty = _check_worktree_clean(worktree_path)
        if dirty is not None:
            raise WorktreeToolError(
                f"worktree {worktree_path} is not clean; refusing to retire it "
                f"(commit or stash first, or pass --force):\n{dirty}"
            )
        merged = _check_branch_merged(branch, into_branch, cwd=cwd)
        if not merged:
            raise WorktreeToolError(
                f"branch {branch} is not fully merged into {into_branch}; "
                "refusing to retire it (merge it first, or pass --force)"
            )

    remove_args = ["worktree", "remove"]
    if force:
        remove_args.append("--force")
    remove_args.append(str(worktree_path))
    result = _run_git(remove_args, cwd=cwd)
    if result.returncode != 0:
        raise WorktreeToolError(f"git worktree remove failed: {result.stderr.strip()}")

    delete_flag = "-D" if force else "-d"
    result = _run_git(["branch", delete_flag, branch], cwd=cwd)
    if result.returncode != 0:
        raise WorktreeToolError(f"git branch {delete_flag} failed: {result.stderr.strip()}")

    print(f"Retired worktree {worktree_path} and deleted branch {branch}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the ``wt:new``/``wt:done`` argparse CLI.

    :returns: configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="worktree_tool.py",
        description="wt:new / wt:done workspace primitives (git-doctrine item 2).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser(
        "new", help="Create .claude/worktrees/NAME on a fresh wt/NAME branch."
    )
    new_parser.add_argument("name", help="Worktree slug (strict grammar, see --help).")

    done_parser = subparsers.add_parser(
        "done", help="Retire .claude/worktrees/NAME after clean+merged checks."
    )
    done_parser.add_argument("name", help="Worktree slug to retire.")
    done_parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the clean/merged checks (force-remove worktree, -D delete branch).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    :param argv: argument vector (defaults to ``sys.argv[1:]``).
    :returns: process exit code (0 on success, 1 on a loud
        :class:`WorktreeToolError`).
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    cwd = Path.cwd()

    try:
        if args.command == "new":
            return cmd_new(args.name, cwd=cwd)
        if args.command == "done":
            return cmd_done(args.name, cwd=cwd, force=args.force)
        raise WorktreeToolError(f"unknown command: {args.command}")
    except WorktreeToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
