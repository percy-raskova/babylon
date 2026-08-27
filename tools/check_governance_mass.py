#!/usr/bin/env python3
"""Measure Babylon governance mass and enforce only recurring-context budgets."""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Final

import yaml

MAX_FILES: Final = 2048
MAX_REPO_SKILLS: Final = 8
MAX_SKILL_BODY_BYTES: Final = 5000
MAX_SKILL_DISCOVERY_CHARS: Final = 2500

_INDEX_REFERENCE = "ai/decisions/index.yaml"
_INDEX_ACTION = re.compile(r"\b(?:read|consult|load|open|review)\b", re.IGNORECASE)
_NEGATED_INDEX_ACTION = re.compile(
    r"\b(?:do\s+not|don't|never)\s+(?:need\s+to\s+)?"
    r"(?:read|consult|load|open|review)\b",
    re.IGNORECASE,
)
_LIVE_ROUTING_FILES: Final = (
    "docs/agents/governance.md",
    "ai/README.md",
)


class GovernanceBudgetError(Exception):
    """One or more recurring-context budgets were exceeded."""


def _bounded_files(root: Path, pattern: str) -> list[Path]:
    matches = itertools.islice(root.glob(pattern), MAX_FILES + 1)
    files = sorted(path for path in matches if path.is_file())
    if len(files) > MAX_FILES:
        raise GovernanceBudgetError(
            f"file-count: {pattern} matched {len(files)}, above {MAX_FILES}"
        )
    return files


def _mass(paths: list[Path], repo_root: Path) -> dict[str, int | float | str | None]:
    sizes = [(path.stat().st_size, path) for path in paths[:MAX_FILES]]
    total = sum(size for size, _ in sizes[:MAX_FILES])
    largest_size, largest_path = max(sizes, default=(0, None))
    return {
        "files": len(paths),
        "bytes": total,
        "estimated_tokens_bytes_div_4": total / 4,
        "largest_bytes": largest_size,
        "largest_path": largest_path.relative_to(repo_root).as_posix() if largest_path else None,
    }


def _frontmatter(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) < 3 or lines[0] != "---":
        raise GovernanceBudgetError(f"skill-frontmatter: {path} has no YAML header")
    try:
        end = lines[1:128].index("---") + 1
    except ValueError as error:
        raise GovernanceBudgetError(
            f"skill-frontmatter: {path} has no closing delimiter"
        ) from error
    try:
        metadata = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as error:
        raise GovernanceBudgetError(
            f"skill-frontmatter: {path} has invalid YAML: {error}"
        ) from error
    if not isinstance(metadata, dict):
        raise GovernanceBudgetError(f"skill-frontmatter: {path} must be a mapping")
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not isinstance(description, str):
        raise GovernanceBudgetError(f"skill-frontmatter: {path} needs string name and description")
    return name, description


def _skill_report(skill_files: list[Path]) -> tuple[dict[str, int], list[str]]:
    discovery_chars = 0
    largest_body = 0
    violations: list[str] = []
    if len(skill_files) > MAX_REPO_SKILLS:
        violations.append(f"repo-skill-count: {len(skill_files)} exceeds {MAX_REPO_SKILLS}")
    for path in skill_files[:MAX_REPO_SKILLS]:
        name, description = _frontmatter(path)
        discovery_chars += len(name) + len(description)
        body_bytes = path.stat().st_size
        largest_body = max(largest_body, body_bytes)
        if body_bytes > MAX_SKILL_BODY_BYTES:
            violations.append(
                f"skill-body-bytes: {path} is {body_bytes}, above {MAX_SKILL_BODY_BYTES}"
            )
    if discovery_chars > MAX_SKILL_DISCOVERY_CHARS:
        violations.append(
            f"skill-discovery-chars: {discovery_chars} exceeds {MAX_SKILL_DISCOVERY_CHARS}"
        )
    return (
        {
            "files": len(skill_files),
            "discovery_chars": discovery_chars,
            "largest_body_bytes": largest_body,
        },
        violations,
    )


def _routing_violations(repo_root: Path) -> list[str]:
    violations: list[str] = []
    for relative in _LIVE_ROUTING_FILES:
        path = repo_root / relative
        if not path.is_file():
            violations.append(f"routing-file-missing: {relative}")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        directs_full_read = any(
            _INDEX_REFERENCE in line
            and _INDEX_ACTION.search(line) is not None
            and _NEGATED_INDEX_ACTION.search(line) is None
            for line in lines[:MAX_FILES]
        )
        if directs_full_read:
            violations.append(
                f"full-index-routing: {relative} directs agents to load the full index"
            )
    return violations


def measure_governance(repo_root: Path, *, check: bool = False) -> dict[str, object]:
    """Return deterministic mass metrics and optionally enforce lean routing."""
    root = repo_root.resolve()
    adr_files = _bounded_files(root, "ai/decisions/ADR[0-9][0-9][0-9]_*.yaml")
    plan_files = _bounded_files(root, "docs/superpowers/plans/*.md")
    skill_files = _bounded_files(root, ".agents/skills/*/SKILL.md")
    adr_mass = _mass(adr_files, root)
    plan_mass = _mass(plan_files, root)
    skill_report, violations = _skill_report(skill_files)
    violations.extend(_routing_violations(root))
    index_path = root / "ai/decisions/index.yaml"
    index_bytes = index_path.stat().st_size if index_path.is_file() else 0
    adr_bytes_value = adr_mass["bytes"]
    if not isinstance(adr_bytes_value, int):
        raise GovernanceBudgetError("internal metric error: ADR bytes are not an integer")
    adr_bytes = adr_bytes_value
    report: dict[str, object] = {
        "adr_corpus": adr_mass,
        "adr_index": {
            "bytes": index_bytes,
            "estimated_tokens_bytes_div_4": index_bytes / 4,
            "index_to_corpus_ratio": index_bytes / adr_bytes if adr_bytes else None,
        },
        "plan_history": plan_mass,
        "repo_skills": skill_report,
        "budgets": {
            "max_repo_skills": MAX_REPO_SKILLS,
            "max_skill_body_bytes": MAX_SKILL_BODY_BYTES,
            "max_skill_discovery_chars": MAX_SKILL_DISCOVERY_CHARS,
        },
        "violations": violations,
    }
    if check and violations:
        raise GovernanceBudgetError("; ".join(violations))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = measure_governance(args.repo, check=args.check)
    except (GovernanceBudgetError, OSError) as error:
        print(f"governance-mass: {error}", file=sys.stderr)
        return 2
    if args.check:
        print("governance-mass: ok")
    else:
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
