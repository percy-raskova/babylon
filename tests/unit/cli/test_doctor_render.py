"""Smoke: ``babylon doctor`` emits the render verdict (ADR097 D4, consumes ADR095)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from babylon.cli import app

runner = CliRunner()


def test_doctor_prints_render_tier(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("BABYLON_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("TERM", "dumb")
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "render tier:" in result.stdout
