"""`babylon self-update` — wrap ``nix profile upgrade babylon``.

Graceful no-op with an honest message when the install did not come through
the Nix player channel (no ``nix`` on PATH). ADR095 D1: the flake wrapper
and install.sh own the real upgrade path; this is the in-game shortcut.
"""

from __future__ import annotations

import shutil
import subprocess

import typer


def self_update() -> None:
    """Upgrade Babylon via `nix profile upgrade babylon` (no-op if not Nix-installed)."""
    if shutil.which("nix") is None:
        typer.echo(
            "nix not found — Babylon was not installed via the Nix player channel; "
            "nothing to update."
        )
        raise typer.Exit(code=0)
    try:
        subprocess.run(["nix", "profile", "upgrade", "babylon"], check=True)  # noqa: S607 — nix resolved via PATH, same as other CLI wrappers
    except subprocess.CalledProcessError as exc:
        typer.echo(f"`nix profile upgrade babylon` failed (exit {exc.returncode}).")
        raise typer.Exit(code=1) from exc
    typer.echo("Babylon upgraded via nix profile.")
