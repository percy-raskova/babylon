"""Migration-graph smoke tests (spec-091 US3 / FR-005).

The ``accounts`` app shipped with no ``migrations/`` package, so its
``PlayerProfile`` table was never materialized by ``manage.py migrate``; the
``game`` app additionally accumulated model changes with no migration written.
These tests pin the debt as cleared: every managed model has a migration, and
``makemigrations --check`` reports nothing outstanding.

RED-first: both fail at HEAD (no accounts migrations; pending model changes).
"""

from __future__ import annotations

import importlib
from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.unit
def test_accounts_has_migrations_package() -> None:
    """The ``accounts`` app must own an initial migration for PlayerProfile."""
    migrations = importlib.import_module("accounts.migrations")
    # A migrations package with at least the initial module present.
    assert any(name.startswith("0001") for name in _submodule_names(migrations)), (
        "accounts app has no initial migration"
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_no_pending_model_changes() -> None:
    """``makemigrations --check`` must be clean for accounts + game.

    ``--check`` raises ``SystemExit(1)`` when a model change lacks a migration.
    """
    out = StringIO()
    try:
        call_command(
            "makemigrations",
            "accounts",
            "game",
            "--check",
            "--dry-run",
            stdout=out,
            stderr=out,
        )
    except SystemExit as exc:  # pragma: no cover - only on failure
        if exc.code not in (0, None):
            pytest.fail(f"Pending migrations detected:\n{out.getvalue()}")


def _submodule_names(package: object) -> list[str]:
    import pkgutil

    return [m.name for m in pkgutil.iter_modules(package.__path__)]  # type: ignore[attr-defined]
