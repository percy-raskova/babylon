"""`babylon doctor` diagnoses only the current runtime database."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import babylon.cli.doctor as doctor_mod
from babylon.cli import app

runner = CliRunner()


def test_doctor_reports_database_without_reading_retired_model_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("BABYLON_CONFIG_DIR", str(tmp_path))
    config = tmp_path / "config.toml"
    credentials = tmp_path / "credentials"
    config.write_text("[invalid legacy config")
    credentials.write_text("private existing credentials")
    monkeypatch.setattr(doctor_mod, "check_database", lambda _dsn: (False, "no DSN configured"))
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "database: unavailable — no DSN configured"
    assert config.read_text() == "[invalid legacy config"
    assert credentials.read_text() == "private existing credentials"


def test_check_database_handles_missing_dsn() -> None:
    ok, detail = doctor_mod.check_database(None)
    assert ok is False
    assert "DSN" in detail or "dsn" in detail


def test_doctor_probes_the_current_runtime_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BABYLON_RUNTIME_DSN", raising=False)
    for name in ("BABYLON_DSN", "BABYLON_DATABASE_URL", "BABYLON_PG_DSN", "BABYLON_TEST_PG_DSN"):
        monkeypatch.setenv(name, "postgresql://retired/db")
    seen_dsns: list[str | None] = []

    def probe(dsn: str | None) -> tuple[bool, str]:
        seen_dsns.append(dsn)
        return (False, "no DSN configured")

    monkeypatch.setattr(doctor_mod, "check_database", probe)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert seen_dsns == [None]

    monkeypatch.setenv("BABYLON_RUNTIME_DSN", "host=/var/run/postgresql dbname=campaign")
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert seen_dsns[-1] == "host=/var/run/postgresql dbname=campaign"


def test_doctor_has_no_model_download_option() -> None:
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "--provision" not in result.stdout
    result = runner.invoke(app, ["doctor", "--provision"])
    assert result.exit_code == 2
    assert "No such option" in result.stderr
