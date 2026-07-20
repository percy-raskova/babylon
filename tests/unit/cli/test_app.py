"""CLI app contract: entry-point shape, --version, and play-default (ADR095 D1)."""

from __future__ import annotations

from typer.testing import CliRunner

import babylon.__main__ as demo_main
from babylon import __version__
from babylon.cli import app

runner = CliRunner()


def test_help_lists_all_six_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in ("play", "doctor", "login", "telemetry", "self-update", "uninstall"):
        assert name in result.stdout


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_no_subcommand_runs_play(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []
    monkeypatch.setattr(demo_main, "main", lambda: calls.append("ran"))
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert calls == ["ran"]


def test_play_subcommand_runs_demo(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []
    monkeypatch.setattr(demo_main, "main", lambda: calls.append("ran"))
    result = runner.invoke(app, ["play"])
    assert result.exit_code == 0
    assert calls == ["ran"]
