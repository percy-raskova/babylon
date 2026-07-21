"""telemetry / self-update / uninstall honest-status behavior (ADR095 D1)."""

from __future__ import annotations

from typer.testing import CliRunner

import babylon.cli.self_update as su
from babylon.cli import app

runner = CliRunner()


def test_telemetry_prints_local_only_status(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("BABYLON_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["telemetry"])
    assert result.exit_code == 0
    assert "local" in result.stdout.lower()
    assert "unratified" in result.stdout.lower()


def test_self_update_no_nix_is_graceful(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(su.shutil, "which", lambda _name: None)
    result = runner.invoke(app, ["self-update"])
    assert result.exit_code == 0
    assert "not installed via" in result.stdout.lower() or "nix not found" in result.stdout.lower()


def test_self_update_invokes_nix_when_present(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[list[str]] = []
    monkeypatch.setattr(su.shutil, "which", lambda _name: "/usr/bin/nix")
    monkeypatch.setattr(su.subprocess, "run", lambda cmd, check: calls.append(cmd))  # noqa: ARG005 — kwarg required to match subprocess.run's signature
    result = runner.invoke(app, ["self-update"])
    assert result.exit_code == 0
    assert calls == [["nix", "profile", "upgrade", "babylon"]]


def test_uninstall_prints_steps_deletes_nothing() -> None:
    result = runner.invoke(app, ["uninstall"])
    assert result.exit_code == 0
    assert "nix profile remove babylon" in result.stdout
    assert ".config/babylon" in result.stdout
