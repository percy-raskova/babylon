"""`babylon doctor` reports config, provider lane, and DB reachability (ADR095 D1).

``--provision`` (D3, ADR096) is covered here too — it consumes the tested
``provision.py`` core, so these tests only pin the CLI wiring: manifest and
dest-dir plumbing, per-result output, and the error->nonzero-exit path.
"""

from __future__ import annotations

from typer.testing import CliRunner

import babylon.cli.doctor as doctor_mod
from babylon.cli import app
from babylon.intelligence.providers import MuteProvider
from babylon.intelligence.provision import ProvisionResult

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


def test_doctor_provision_reports_gated_result(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("BABYLON_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(doctor_mod, "resolve_provider", lambda: MuteProvider())
    monkeypatch.setattr(doctor_mod, "check_database", lambda _dsn: (False, "no DSN configured"))
    monkeypatch.setattr(doctor_mod, "load_bundled_manifest", lambda: object())
    monkeypatch.setattr(doctor_mod, "default_models_dir", lambda: tmp_path)
    monkeypatch.setattr(
        doctor_mod,
        "provision_models",
        lambda _manifest, _dest: [
            ProvisionResult(name="babylon-embed", status="gated", detail="owner-provisioned")
        ],
    )
    result = runner.invoke(app, ["doctor", "--provision"])
    assert result.exit_code == 0
    assert "babylon-embed: gated" in result.stdout
    assert "owner-provisioned" in result.stdout


def test_doctor_provision_error_exits_nonzero(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("BABYLON_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(doctor_mod, "resolve_provider", lambda: MuteProvider())
    monkeypatch.setattr(doctor_mod, "check_database", lambda _dsn: (False, "no DSN configured"))
    monkeypatch.setattr(doctor_mod, "load_bundled_manifest", lambda: object())
    monkeypatch.setattr(doctor_mod, "default_models_dir", lambda: tmp_path)

    def _raise(_manifest: object, _dest: object) -> None:
        raise ValueError("provision babylon-chat failed after 3 attempts: sha256 mismatch")

    monkeypatch.setattr(doctor_mod, "provision_models", _raise)
    result = runner.invoke(app, ["doctor", "--provision"])
    assert result.exit_code == 1
    assert "provisioning error" in result.stdout
