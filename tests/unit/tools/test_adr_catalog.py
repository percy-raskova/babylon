"""Behavioral contracts for the disposable ADR SQLite read model."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import adr_catalog  # type: ignore[import-not-found]  # noqa: E402
from adr_catalog import (  # type: ignore[import-not-found]  # noqa: E402
    MAX_TITLE_CHARS,
    DuplicateAdrError,
    SourceChangedError,
    SourceParseError,
    build_cache,
    capture_snapshot,
    check_catalog,
    main,
    search,
    show,
)

pytestmark = pytest.mark.unit


def _write(repo: Path, relative: str, content: str) -> None:
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _write_index(repo: Path, statuses: dict[str, str]) -> None:
    if len(statuses) > 32:
        raise ValueError("test index exceeds its fixed bound")
    lines = ["meta:", "  version: 1", "decisions:"]
    for key, status in list(statuses.items())[:32]:
        lines.extend(
            [
                f"  {key}:",
                f"    title: Index title for {key}",
                f"    status: {status}",
            ]
        )
    _write(repo, "ai/decisions/index.yaml", "\n".join(lines) + "\n")


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    _write(
        repo,
        "ai/decisions/ADR001_wrapper.yaml",
        """ADR001_wrapper:
  status: accepted
  title: Wrapper decision
  date: '2026-08-20'
  decision: Wrapper ruling.
  supersedes:
    - ADR000 only for the obsolete clause
""",
    )
    _write(
        repo,
        "ai/decisions/ADR002_flat.yaml",
        """id: ADR002
status: accepted
title: Flat decision
date: '2026-08-21'
decision: Flat ruling.
""",
    )
    _write(
        repo,
        "ai/decisions/ADR003_alternate.yaml",
        """ADR003:
  status: proposed
  title: Alternate wrapper
  decisions:
    graph:
      action: Everything is nodes and edges.
  consensus:
    supersedes:
      - ADR002 only for the graph deferral
""",
    )
    _write(
        repo,
        "ai/decisions/ADR004_comments.yaml",
        """# ADR-004: Comment metadata decision
# Status: ACCEPTED
context: Legacy unwrapped record.
decision: Comment-backed ruling.
""",
    )
    _write_index(
        repo,
        {
            "ADR001_wrapper": "accepted",
            "ADR002_flat": "proposed",
            "ADR003_alternate": "proposed",
            "ADR004_comments": "accepted",
        },
    )
    return repo


def test_imports_current_record_shapes_without_promoting_comment_status(
    tmp_path: Path,
) -> None:
    repo = _fixture_repo(tmp_path)
    cache = tmp_path / "adr.sqlite3"

    summary = build_cache(repo, cache)

    assert summary.record_count == 4
    assert show(cache, "ADR001")["record"]["selector"] == "ADR001_wrapper"
    assert show(cache, "ADR002")["record"]["selector"] == "$"
    assert show(cache, "ADR003")["record"]["selector"] == "ADR003"
    legacy = show(cache, "ADR004")
    assert legacy["record"]["status"] is None
    assert legacy["record"]["index_status"] == "accepted"
    assert legacy["record"]["title_source"] == "index"
    assert [item["code"] for item in legacy["diagnostics"]] == ["missing-structured-status"]


@pytest.mark.parametrize(
    ("relative", "content", "error_type"),
    [
        (
            "ai/decisions/ADR002_flat.yaml",
            "id: ADR099\nstatus: accepted\ntitle: Wrong identity\n",
            SourceParseError,
        ),
        (
            "ai/decisions/ADR001_collision.yaml",
            "id: ADR001\nstatus: proposed\ntitle: Collision\n",
            DuplicateAdrError,
        ),
    ],
)
def test_declared_id_mismatch_and_duplicate_number_fail(
    tmp_path: Path,
    relative: str,
    content: str,
    error_type: type[Exception],
) -> None:
    repo = _fixture_repo(tmp_path)
    _write(repo, relative, content)

    with pytest.raises(error_type):
        build_cache(repo, tmp_path / "adr.sqlite3")


def test_source_index_conflict_stays_explicit(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    cache = tmp_path / "adr.sqlite3"
    build_cache(repo, cache)

    result = show(cache, "ADR002")

    assert result["record"]["status"] == "accepted"
    assert result["record"]["index_status"] == "proposed"
    assert [item["code"] for item in result["diagnostics"]] == ["index-status-conflict"]


def test_check_rejects_source_index_membership_drift(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    _write_index(
        repo,
        {
            "ADR001_wrapper": "accepted",
            "ADR002_flat": "proposed",
            "ADR003_alternate": "proposed",
            "ADR099_orphan": "accepted",
        },
    )

    with pytest.raises(SourceParseError, match="source/index membership"):
        check_catalog(repo)


def test_nested_and_partial_supersession_is_queryable(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    cache = tmp_path / "adr.sqlite3"
    build_cache(repo, cache)

    wrapper_edges = show(cache, "ADR001")["supersession"]
    flat_edges = show(cache, "ADR002")["supersession"]

    assert wrapper_edges == [
        {
            "source_id": "ADR001",
            "kind": "supersedes",
            "target_id": "ADR000",
            "scope": "ADR000 only for the obsolete clause",
        }
    ]
    assert flat_edges == [
        {
            "source_id": "ADR003",
            "kind": "supersedes",
            "target_id": "ADR002",
            "scope": "ADR002 only for the graph deferral",
        }
    ]


def test_literal_body_search_finds_nonstandard_decisions_without_returning_body(
    tmp_path: Path,
) -> None:
    repo = _fixture_repo(tmp_path)
    cache = tmp_path / "adr.sqlite3"
    build_cache(repo, cache)

    result = search(cache, "Everything is nodes and edges")

    assert [item["id"] for item in result["results"]] == ["ADR003"]
    assert result["results"][0]["match_location"] == "body"
    assert "body" not in result["results"][0]
    assert search(cache, "%")["results"] == []


def test_failed_rebuild_preserves_the_completed_cache(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    cache = tmp_path / "adr.sqlite3"
    original = build_cache(repo, cache)
    _write(repo, "ai/decisions/ADR002_flat.yaml", "id: [unterminated\n")

    with pytest.raises(SourceParseError, match="ADR002_flat.yaml"):
        build_cache(repo, cache)

    assert show(cache, "ADR002")["source_digest"] == original.source_digest


def test_cli_rebuild_discards_a_tampered_local_catalog(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _fixture_repo(tmp_path)
    cache = tmp_path / "adr.sqlite3"
    build_cache(repo, cache)
    connection = sqlite3.connect(cache)
    try:
        connection.execute("UPDATE adr SET title = 'tampered' WHERE id = 'ADR001'")
        connection.commit()
    finally:
        connection.close()

    assert main(["--repo", str(repo), "--cache", str(cache), "show", "ADR001"]) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["record"]["title"] == "Wrapper decision"


def test_source_change_during_build_preserves_prior_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _fixture_repo(tmp_path)
    cache = tmp_path / "adr.sqlite3"
    original = build_cache(repo, cache)
    initial = capture_snapshot(repo)
    changed = adr_catalog.dataclasses.replace(initial, source_digest="changed")
    snapshots = iter((initial, changed))
    monkeypatch.setattr(adr_catalog, "capture_snapshot", lambda _repo: next(snapshots))

    with pytest.raises(SourceChangedError):
        build_cache(repo, cache)

    assert show(cache, "ADR001")["source_digest"] == original.source_digest


def test_cli_show_search_and_check_are_bounded(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _fixture_repo(tmp_path)
    cache = tmp_path / "adr.sqlite3"

    assert main(["--repo", str(repo), "--cache", str(cache), "show", "ADR001"]) == 0
    shown = capsys.readouterr()
    assert json.loads(shown.out)["record"]["id"] == "ADR001"
    assert "body" not in shown.out
    assert len(shown.out.encode("utf-8")) <= 4096

    assert main(["--repo", str(repo), "--cache", str(cache), "search", "graph"]) == 0
    found = capsys.readouterr()
    assert all("body" not in item for item in json.loads(found.out)["results"])
    assert len(found.out.encode("utf-8")) <= 4096

    assert main(["--repo", str(repo), "check"]) == 0
    checked = capsys.readouterr()
    assert json.loads(checked.out) == {
        "conflicts": 1,
        "missing_status": 1,
        "records": 4,
        "status": "ok",
    }


def test_worst_case_show_output_stays_inside_its_contract(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _fixture_repo(tmp_path)
    cache = tmp_path / "adr.sqlite3"
    scopes = "\n".join(
        [
            f"    - ADR010 {'a' * 280}",
            f"    - ADR011 {'b' * 280}",
            f"    - ADR012 {'c' * 280}",
            f"    - ADR013 {'d' * 280}",
            f"    - ADR014 {'e' * 280}",
            f"    - ADR015 {'f' * 280}",
            f"    - ADR016 {'g' * 280}",
            f"    - ADR017 {'h' * 280}",
        ]
    )
    _write(
        repo,
        "ai/decisions/ADR001_wrapper.yaml",
        "ADR001_wrapper:\n"
        "  status: accepted\n"
        f"  title: {'title ' * 200}\n"
        f"  supersedes:\n{scopes}\n",
    )

    exit_code = main(["--repo", str(repo), "--cache", str(cache), "show", "ADR001"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert len(captured.out.encode("utf-8")) <= 4096
    assert len(json.loads(captured.out)["record"]["title"]) <= MAX_TITLE_CHARS


def test_live_estate_retains_the_historical_adr_floor() -> None:
    repo = Path(__file__).resolve().parents[3]

    assert len(capture_snapshot(repo).files) >= 219
