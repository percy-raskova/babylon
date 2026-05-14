"""Unit test for fail-fast preflight (T020b, spec-064 FR-019 + edge cases).

Three scenarios, each driven purely through ``main_from_argv`` with
patched preflight components — no Postgres, no SQLite, no engine:

* E1: Postgres unreachable → exit 4 + ERROR POSTGRES_UNREACHABLE on stderr
* E2: SQLite reference DB missing → exit 3 + ERROR REFERENCE_DATA_MISSING
* E3: hex hydration returns 0 rows → exit 3 + ERROR REFERENCE_DATA_MISSING
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from babylon.engine.headless_runner import runner as runner_mod
from babylon.engine.headless_runner.argparse_cli import build_parser


def _args(tmp_path: Path, **overrides: Any) -> Any:
    parser = build_parser()
    base = [
        "--scope",
        "detroit-tri-county",
        "--ticks",
        "5",
        "--output-dir",
        str(tmp_path / "out"),
        "--sqlite-path",
        str(overrides.pop("sqlite_path", "data/sqlite/marxist-data-3NF.sqlite")),
    ]
    return parser.parse_args(base)


def test_e1_postgres_unreachable_yields_exit_4(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E1: When the pool fails to open, exit code MUST be 4."""

    def _raise(*_a: Any, **_kw: Any) -> Any:
        raise runner_mod.PostgresUnreachableError("Connection pool failed to open (port 5433)")

    monkeypatch.setattr(runner_mod, "_open_postgres_pool", _raise)
    # We must avoid the SQLite preflight tripping first, so use a real file.
    args = _args(tmp_path)
    monkeypatch.setattr(runner_mod, "_validate_preflight", lambda _c: None)

    code = runner_mod.main_from_argv(args)
    assert code == 4
    err = capsys.readouterr().err
    assert "ERROR POSTGRES_UNREACHABLE" in err
    assert re.search(r"partial_artifacts=NONE", err) is not None


def test_e2_sqlite_reference_missing_yields_exit_3(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E2: SQLite path missing → exit 3 + REFERENCE_DATA_MISSING."""
    missing = tmp_path / "absent.sqlite"
    parser = build_parser()
    args = parser.parse_args(
        [
            "--scope",
            "detroit-tri-county",
            "--ticks",
            "5",
            "--output-dir",
            str(tmp_path / "out"),
            "--sqlite-path",
            str(missing),
        ],
    )
    # Don't open Postgres just to fail at SQLite.
    monkeypatch.setattr(runner_mod, "_open_postgres_pool", lambda: object())
    code = runner_mod.main_from_argv(args)
    assert code == 3
    err = capsys.readouterr().err
    assert "ERROR REFERENCE_DATA_MISSING" in err
    assert "absent.sqlite" in err


def test_e3_hex_hydration_zero_rows_yields_exit_3(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E3: hex_count==0 from initialize_session → exit 3."""

    class _Report:
        hex_count = 0

    def _fake_run(config: Any) -> Any:
        raise runner_mod.ReferenceDataMissingError(
            "Hex hydration produced zero rows for the requested scope."
        )

    monkeypatch.setattr(runner_mod, "run", _fake_run)
    args = _args(tmp_path)
    code = runner_mod.main_from_argv(args)
    assert code == 3
    err = capsys.readouterr().err
    assert "ERROR REFERENCE_DATA_MISSING" in err
    assert "Hex hydration produced zero rows" in err


def test_config_error_yields_exit_2(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Malformed --fips → exit 2 + CONFIG_ERROR."""
    parser = build_parser()
    args = parser.parse_args(
        [
            "--fips",
            "ABC,12,99999",  # not 5-digit
            "--ticks",
            "5",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )
    code = runner_mod.main_from_argv(args)
    assert code == 2
    err = capsys.readouterr().err
    assert "ERROR CONFIG_ERROR" in err
