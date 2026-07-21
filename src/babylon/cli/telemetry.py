"""`babylon telemetry` — honest local status (ingest lane unratified).

The metrics collector (``babylon.metrics.collector``) is in-process only; no
upload code exists and the telemetry-ingest lane is unratified (no ADR).
This command reports that truth and echoes any ``[telemetry]`` config the
player has set — it never uploads anything.
"""

from __future__ import annotations

import os
import tomllib

import typer

from babylon.intelligence.providers import _config_dir


def telemetry() -> None:
    """Show telemetry status (local, in-process only; ingest is unratified)."""
    typer.echo("Telemetry: local, in-process only (babylon.metrics.collector).")
    typer.echo("Upload lane: NOT configured — telemetry ingest is unratified (no ADR yet).")

    config_toml = _config_dir(os.environ) / "config.toml"
    if config_toml.exists():
        try:
            data = tomllib.loads(config_toml.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            typer.echo(f"config.toml unreadable: {exc}")
            return
        section = data.get("telemetry")
        if isinstance(section, dict):
            typer.echo(f"[telemetry] config: {section}")
        else:
            typer.echo("[telemetry] config: (none set)")
    else:
        typer.echo("[telemetry] config: (no config.toml)")
