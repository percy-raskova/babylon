"""`babylon doctor` reports config, provider lane, and DB reachability (ADR095 D1)."""

from __future__ import annotations

from typer.testing import CliRunner

import babylon.cli.doctor as doctor_mod
from babylon.cli import app
from babylon.intelligence.providers import MuteProvider

runner = CliRunner()


def test_doctor_reports_config_dir_and_lane(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("BABYLON_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(doctor_mod, "resolve_provider", lambda: MuteProvider())
    monkeypatch.setattr(doctor_mod, "check_database", lambda _dsn: (False, "no DSN configured"))
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert str(tmp_path) in result.stdout
    assert "mute" in result.stdout
    assert "config.toml" in result.stdout


def test_check_database_handles_missing_dsn() -> None:
    ok, detail = doctor_mod.check_database(None)
    assert ok is False
    assert "DSN" in detail or "dsn" in detail
