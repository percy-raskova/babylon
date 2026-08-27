"""Contracts for the deterministic governance-context budget."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from check_governance_mass import (  # type: ignore[import-not-found]  # noqa: E402
    MAX_SKILL_BODY_BYTES,
    GovernanceBudgetError,
    measure_governance,
)

pytestmark = pytest.mark.unit


def _write(root: Path, relative: str, content: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    _write(repo, "ai/decisions/ADR001_one.yaml", "status: accepted\n")
    _write(repo, "ai/decisions/index.yaml", "decisions: {}\n")
    _write(repo, "docs/superpowers/plans/old.md", "historical\n")
    _write(
        repo,
        ".agents/skills/one/SKILL.md",
        """---
name: one
description: Use for one bounded job. Do not use elsewhere.
---

Run the deterministic command.
""",
    )
    _write(
        repo,
        "docs/agents/governance.md",
        "Run mise run adr search before reading source.\n",
    )
    _write(
        repo,
        "ai/README.md",
        "Query with mise run adr; the tracked index remains a sentinel input.\n",
    )
    return repo


def test_measurement_separates_corpus_history_and_skill_discovery(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)

    report = measure_governance(repo)

    assert report["adr_corpus"]["files"] == 1
    assert report["adr_corpus"]["largest_path"] == "ai/decisions/ADR001_one.yaml"
    assert report["plan_history"]["files"] == 1
    assert report["repo_skills"]["files"] == 1
    assert report["repo_skills"]["discovery_chars"] == len(
        "oneUse for one bounded job. Do not use elsewhere."
    )
    assert report["violations"] == []


def test_oversized_skill_body_fails_the_budget(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write(
        repo,
        ".agents/skills/one/SKILL.md",
        "---\nname: one\ndescription: bounded\n---\n" + ("x" * MAX_SKILL_BODY_BYTES),
    )

    with pytest.raises(GovernanceBudgetError, match="skill-body-bytes"):
        measure_governance(repo, check=True)


@pytest.mark.parametrize(
    "directive",
    [
        "Read ai/decisions/index.yaml before every architecture question.\n",
        "5. Consult ai/decisions/index.yaml before every architecture question.\n",
        "You must review ai/decisions/index.yaml before architecture work.\n",
        "- Open ai/decisions/index.yaml before architecture work.\n",
    ],
)
def test_live_instruction_to_read_full_index_fails(tmp_path: Path, directive: str) -> None:
    repo = _fixture_repo(tmp_path)
    _write(repo, "docs/agents/governance.md", directive)

    with pytest.raises(GovernanceBudgetError, match="full-index-routing"):
        measure_governance(repo, check=True)
