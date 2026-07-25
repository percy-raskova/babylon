"""CLI app contract: entry-point shape, --version, and play-default (ADR095 D1)."""

from __future__ import annotations

from typer.testing import CliRunner

from babylon import __version__
from babylon.cli import app
from babylon.cli import play as play_cmd

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
    monkeypatch.setattr(play_cmd, "run", lambda: calls.append("ran"))
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert calls == ["ran"]


def test_play_subcommand_boots_the_composition_root(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Since Unit C1, ``babylon play`` boots the real campaign session
    (``babylon.game.session``) through ``play_cmd.run``, not the legacy
    two-node demo — ``play_cmd.play_demo`` preserves the old behavior for
    anyone scripting against it directly, but no entry point calls it.

    T5 Unit U1: ``play`` now threads ``narrator_enabled=`` into ``run`` —
    ON by default with no flag given. T6 Unit U4: ``play`` ALSO threads
    ``tutorial_enabled=`` — ``None`` (unset) by default, the tri-state
    "defer to first-session semantics" signal."""
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(play_cmd, "run", lambda **kwargs: calls.append(kwargs))
    result = runner.invoke(app, ["play"])
    assert result.exit_code == 0
    assert calls == [{"narrator_enabled": True, "tutorial_enabled": None}]


def test_play_subcommand_no_narrator_flag_disables_the_narrator(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """T5 Unit U1: ``--no-narrator`` threads ``narrator_enabled=False``
    through to ``run`` — OFF means ``schedule()`` is never called at all."""
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(play_cmd, "run", lambda **kwargs: calls.append(kwargs))
    result = runner.invoke(app, ["play", "--no-narrator"])
    assert result.exit_code == 0
    assert calls == [{"narrator_enabled": False, "tutorial_enabled": None}]


def test_play_subcommand_tutorial_flag_forces_it_on(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """T6 Unit U4: ``--tutorial`` threads ``tutorial_enabled=True`` through
    to ``run`` — always shows the overlay, even for a resumed campaign."""
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(play_cmd, "run", lambda **kwargs: calls.append(kwargs))
    result = runner.invoke(app, ["play", "--tutorial"])
    assert result.exit_code == 0
    assert calls == [{"narrator_enabled": True, "tutorial_enabled": True}]


def test_play_subcommand_no_tutorial_flag_forces_it_off(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """T6 Unit U4: ``--no-tutorial`` threads ``tutorial_enabled=False``
    through to ``run`` — never shows the overlay, even for a fresh campaign."""
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(play_cmd, "run", lambda **kwargs: calls.append(kwargs))
    result = runner.invoke(app, ["play", "--no-tutorial"])
    assert result.exit_code == 0
    assert calls == [{"narrator_enabled": True, "tutorial_enabled": False}]


def test_play_demo_preserved_for_direct_scripting(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """The legacy demo path still exists (Respect Existing Code) — just
    unwired from any CLI entry point."""
    import babylon.__main__ as demo_main

    calls: list[str] = []
    monkeypatch.setattr(demo_main, "main", lambda: calls.append("ran"))
    play_cmd.play_demo()
    assert calls == ["ran"]
