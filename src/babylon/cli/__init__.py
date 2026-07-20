"""Babylon command-line interface (ADR095 D1).

Entry point: ``[project.scripts] babylon = "babylon.cli:app"``. ``babylon``
with no subcommand runs ``play``. The subcommand modules reuse the landed
§A8 provider seam and config-dir conventions — nothing here reinvents them.
"""

from __future__ import annotations

import typer

from babylon import __version__
from babylon.cli import play as play_cmd

app = typer.Typer(
    name="babylon",
    help="Babylon — The Fall of America. A Marxist simulation engine.",
    add_completion=False,
    no_args_is_help=False,
)


def _register() -> None:
    """Register subcommands. Lazy imports keep the root ``--help`` fast and
    avoid import cycles between subcommand modules and the seam."""
    from babylon.cli import doctor as doctor_cmd
    from babylon.cli import login as login_cmd
    from babylon.cli import self_update as self_update_cmd
    from babylon.cli import telemetry as telemetry_cmd
    from babylon.cli import uninstall as uninstall_cmd

    app.command(name="play")(play_cmd.play)
    app.command(name="doctor")(doctor_cmd.doctor)
    app.command(name="login")(login_cmd.login)
    app.command(name="telemetry")(telemetry_cmd.telemetry)
    app.command(name="self-update")(self_update_cmd.self_update)
    app.command(name="uninstall")(uninstall_cmd.uninstall)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(  # noqa: ARG001 — consumed via eager callback, not body
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the Babylon version and exit.",
    ),
) -> None:
    """Babylon CLI root. With no subcommand, launches the game (play)."""
    if ctx.invoked_subcommand is None:
        play_cmd.run()


_register()
