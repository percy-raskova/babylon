"""`babylon uninstall` — print the honest teardown (deletes nothing)."""

from __future__ import annotations

import typer


def uninstall() -> None:
    """Print the manual teardown steps. This command removes NOTHING itself."""
    typer.echo("Babylon uninstall — manual teardown (this command deletes nothing):")
    typer.echo("  1. nix profile remove babylon     # if installed via the Nix player channel")
    typer.echo("  2. rm -rf ~/.local/share/babylon  # models + game data ($XDG_DATA_HOME/babylon)")
    typer.echo("  3. rm -rf ~/.config/babylon       # config.toml + credentials")
