"""Report reachability of the current Babylon runtime database."""

from __future__ import annotations

import os

from rich.console import Console

console = Console(soft_wrap=True, highlight=False)


def check_database(dsn: str | None) -> tuple[bool, str]:
    """Best-effort reachability probe. Never raises: an unreachable DB is a
    reported condition, not a doctor crash (III.11 loud-but-degrade)."""
    if not dsn:
        return (
            False,
            "no DSN configured (set BABYLON_RUNTIME_DSN)",
        )
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
    except ImportError as exc:
        return (False, f"psycopg not installed: {exc}")
    except psycopg.Error as exc:
        return (False, f"unreachable: {exc}")
    return (True, "reachable")


def doctor() -> None:
    """Diagnose runtime database reachability."""
    db_ok, db_detail = check_database(os.environ.get("BABYLON_RUNTIME_DSN"))
    console.print(f"[bold]database:[/bold] {'ok' if db_ok else 'unavailable'} — {db_detail}")
