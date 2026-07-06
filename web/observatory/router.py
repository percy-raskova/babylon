"""Database router enforcing the Observatory's read-only boundary (spec-096).

The runner's idempotent ``migrations/00*.sql`` are the SOLE schema owner of the
``dynamic_*`` tables (Constitution II.11 — subsystem table ownership). Django
must therefore NEVER attempt DDL against the ``sim`` alias. This router refuses
migrations for that alias and otherwise abstains — product models keep default
routing, and the Observatory targets the ``sim`` alias explicitly via
``connections["sim"]`` rather than through model routing.
"""

from __future__ import annotations

from typing import Any

SIM_ALIAS = "sim"


class SimDatabaseRouter:
    """Refuse migrations for the read-only simulation alias; abstain otherwise.

    Returning ``None`` from the read/write/relation hooks means "no opinion",
    so Django's default routing governs all product models. Only
    :meth:`allow_migrate` takes a stand — and only to say *no* for ``sim``.
    """

    def db_for_read(self, model: Any, **hints: Any) -> str | None:  # noqa: ARG002
        """Abstain — product models route by default; Observatory reads target
        the ``sim`` alias explicitly."""
        return None

    def db_for_write(self, model: Any, **hints: Any) -> str | None:  # noqa: ARG002
        """Abstain — see :meth:`db_for_read`."""
        return None

    def allow_relation(self, obj1: Any, obj2: Any, **hints: Any) -> bool | None:  # noqa: ARG002
        """Abstain — no cross-alias relations are declared by this app."""
        return None

    def allow_migrate(
        self,
        db: str,
        app_label: str,  # noqa: ARG002
        model_name: str | None = None,  # noqa: ARG002
        **hints: Any,  # noqa: ARG002
    ) -> bool | None:
        """Forbid every migration against the ``sim`` alias; abstain elsewhere.

        Args:
            db: The database alias a migration would run against.
            app_label: The app whose migration is being considered.
            model_name: The model being migrated, if any.

        Returns:
            ``False`` iff ``db == "sim"`` (block); ``None`` otherwise (default).
        """
        if db == SIM_ALIAS:
            return False
        return None


__all__ = ["SIM_ALIAS", "SimDatabaseRouter"]
