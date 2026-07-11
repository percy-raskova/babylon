#!/usr/bin/env python3
"""Repo-hygiene gate: allowlisted root, no tracked-ignored files, no fat blobs.

Program 14 (Correspondence) Phase 0.5. Enforces three invariants, loudly
(Constitution III.11 — no silent degradation):

a. **Root allowlist** — every *tracked* top-level entry must appear in
   ``ALLOWED_TOP_LEVEL_DIRS`` or ``ALLOWED_TOP_LEVEL_FILES``. Untracked local
   state (``.venv``, ``data/`` mount symlinks, caches) is ``.gitignore``'s
   jurisdiction, not this gate's.
b. **No tracked-but-ignored files** — the failure mode that let 70 MB of
   ``reports/`` artifacts ride in git (ignore rules added after commit, index
   never purged). The ``.gitkeep`` convention (tracked keeper inside an
   ignored directory) is exempt.
c. **No tracked blob over 1 MiB at HEAD** — LFS pointers are ~130-byte blobs,
   so blob size alone separates pointers from real heavyweights; a >1 MiB
   blob is either missing an LFS attribute or missing a renormalize. Named
   exemptions live in ``LARGE_BLOB_EXEMPTIONS`` (empty by design).

Run: ``poetry run python tools/check_repo_hygiene.py`` (wired into
``mise run check`` as ``check:hygiene`` and into CI). Exit 0 = clean,
1 = violations (printed), 2 = git itself failed.
"""

from __future__ import annotations

import subprocess
import sys

#: Sanctioned tracked top-level directories (Program 14 root architecture).
ALLOWED_TOP_LEVEL_DIRS: frozenset[str] = frozenset(
    {
        ".agents",  # AGENTS.md cross-tool standard config
        ".claude",  # Claude Code project settings/agents
        ".design-sync",  # claude.ai/design converter durable inputs
        ".github",
        ".opencode",
        ".serena",
        ".specify",  # spec-kit remnant; teardown is a separate deferred item
        ".understand-anything",
        "ai",  # Claude's owned tree: context yamls, decisions/ ADRs, scratch/
        "assets",
        "deploy",
        "design",
        "docker",
        "docs",
        "project",  # long-horizon governance: programs/owner/execution/notes
        "reports",  # tracked audit evidence; run artifacts are gitignored
        "results",  # gitignored output dir; tracked .gitkeep only
        "security",  # pip-audit expiring-ignores policy (program 15)
        "sources",  # Percy's theory texts (LFS)
        "specs",
        "src",
        "tests",
        "tools",
        "web",
    }
)

#: Sanctioned tracked top-level files (root canon + tool dot-configs).
ALLOWED_TOP_LEVEL_FILES: frozenset[str] = frozenset(
    {
        ".env.example",
        ".gitattributes",
        ".gitignore",
        ".gitleaks.toml",  # secret-scan policy shared by CI + pre-commit (program 15)
        ".markdownlint.yaml",
        ".markdownlintignore",
        ".mdformat.toml",
        ".mise.toml",
        ".pre-commit-config.yaml",
        ".semgrep.yml",
        ".tflint.hcl",  # terraform lint config for infra-validate (program 15)
        ".trivyignore",  # curated IaC-scan ignores, every entry evidenced (program 15)
        ".yamllint.yaml",
        "AGENTS.md",
        "babylon.code-workspace",
        "docker-compose.yml",
        "CHANGELOG.md",
        "CLAUDE.md",
        "CONSTITUTION.md",
        "CONTRIBUTORS.md",
        "LICENSE",
        "README.md",
        "SETUP_GUIDE.md",
        "data-catalog.yaml",
        "logging.yaml",  # runtime logging config (src/babylon/config/logging_config.py)
        "poetry.lock",
        "pyproject.toml",
        "setup.cfg",  # doc8 config; doc8 cannot read pyproject (documented upstream issue)
    }
)

#: Tracked blobs allowed to exceed MAX_BLOB_BYTES. Grow it only with an
#: owner-visible justification comment per entry.
LARGE_BLOB_EXEMPTIONS: frozenset[str] = frozenset(
    {
        # Runtime seed read by the engine bridge and CI unit tests
        # (tests/unit/balkanization/) — LFS would force lfs:true + quota spend
        # on every CI checkout for one 1.6MB file. Tolerated in-pack.
        "src/babylon/data/game/balkanization/seed_influences.json",
    }
)

#: 1 MiB — anything larger in plain git belongs in LFS (or out of the repo).
MAX_BLOB_BYTES: int = 1_048_576

#: Fixed upper bound on git output lines (Power-of-10 rule 2). The repo
#: tracks ~7k files; hitting this bound means something is deeply wrong.
MAX_GIT_OUTPUT_LINES: int = 100_000

#: Symlink mode in git tree entries — their blobs are target paths, not data.
_SYMLINK_MODE: str = "120000"


def _git_lines(args: list[str]) -> list[str]:
    """Run a git subcommand and return its stdout lines (bounded).

    :param args: Arguments after ``git`` (e.g. ``["ls-files"]``).
    :returns: Non-empty stdout lines.
    :raises RuntimeError: If git exits non-zero or output exceeds the fixed
        line bound — both are loud infrastructure failures, never ignored.
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git {args[0]} failed: {exc.stderr.strip()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"git {args[0]} timed out after 120s") from exc
    lines = [line for line in proc.stdout.splitlines() if line]
    if len(lines) > MAX_GIT_OUTPUT_LINES:
        raise RuntimeError(
            f"git {args[0]} returned {len(lines)} lines (bound {MAX_GIT_OUTPUT_LINES})"
        )
    return lines


def check_top_level_allowlist(tracked_paths: list[str]) -> list[str]:
    """Return tracked top-level entries that are not on the allowlist.

    :param tracked_paths: Repo-relative tracked paths (``git ls-files``).
    :returns: Sorted offending top-level entry names.
    """
    allowed = ALLOWED_TOP_LEVEL_DIRS | ALLOWED_TOP_LEVEL_FILES
    top_level = {path.split("/", 1)[0] for path in tracked_paths[:MAX_GIT_OUTPUT_LINES]}
    return sorted(entry for entry in top_level if entry not in allowed)


def check_tracked_but_ignored(ignored_tracked_paths: list[str]) -> list[str]:
    """Return tracked files matching ignore rules, minus the .gitkeep convention.

    :param ignored_tracked_paths: Output of
        ``git ls-files -i -c --exclude-standard``.
    :returns: Sorted offending paths.
    """
    return sorted(
        path
        for path in ignored_tracked_paths[:MAX_GIT_OUTPUT_LINES]
        if path.rsplit("/", 1)[-1] != ".gitkeep"
    )


def check_large_non_lfs_blobs(ls_tree_lines: list[str]) -> list[str]:
    """Return HEAD blobs larger than MAX_BLOB_BYTES (LFS pointers are tiny).

    :param ls_tree_lines: Output of ``git ls-tree -r -l HEAD`` — each line is
        ``<mode> <type> <oid> <size>\\t<path>`` (size is ``-`` for non-blobs).
    :returns: Sorted ``"path (size bytes)"`` strings for offending blobs.
    """
    violations: list[str] = []
    for line in ls_tree_lines[:MAX_GIT_OUTPUT_LINES]:
        meta, _, path = line.partition("\t")
        if not path or path in LARGE_BLOB_EXEMPTIONS:
            continue
        fields = meta.split()
        if len(fields) != 4 or fields[0] == _SYMLINK_MODE or fields[1] != "blob":
            continue
        size_field = fields[3]
        if not size_field.isdigit():
            continue
        if int(size_field) > MAX_BLOB_BYTES:
            violations.append(f"{path} ({size_field} bytes)")
    return sorted(violations)


def main() -> int:
    """Run all three hygiene checks against the repository; print violations.

    :returns: 0 clean, 1 violations found, 2 git infrastructure failure.
    """
    try:
        tracked = _git_lines(["ls-files"])
        ignored_tracked = _git_lines(["ls-files", "-i", "-c", "--exclude-standard"])
        tree_lines = _git_lines(["ls-tree", "-r", "-l", "HEAD"])
    except RuntimeError as exc:
        print(f"HYGIENE GATE ERROR: {exc}", file=sys.stderr)
        return 2

    failures: list[tuple[str, list[str]]] = [
        ("top-level entry not on root allowlist", check_top_level_allowlist(tracked)),
        ("tracked file matches .gitignore", check_tracked_but_ignored(ignored_tracked)),
        (
            f"tracked blob exceeds {MAX_BLOB_BYTES} bytes and is not LFS",
            check_large_non_lfs_blobs(tree_lines),
        ),
    ]

    exit_code = 0
    for label, violations in failures:
        for violation in violations:
            print(f"HYGIENE VIOLATION [{label}]: {violation}", file=sys.stderr)
            exit_code = 1
    if exit_code == 0:
        print("Repo hygiene: clean (allowlist, ignore-consistency, blob sizes).")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
