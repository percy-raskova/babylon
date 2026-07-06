"""Unit tests for ``SimDatabaseRouter`` (spec-096, US3 read-only guarantee).

The router's single load-bearing job: NEVER let Django migrate the ``sim``
alias. The runner's idempotent ``migrations/00*.sql`` are the sole schema owner
of the ``dynamic_*`` tables (Constitution II.11). Product models keep default
routing (the router abstains).
"""

from __future__ import annotations

import pytest

from observatory.router import SimDatabaseRouter

pytestmark = pytest.mark.unit


class _Model:
    """Stand-in for any Django model instance/class."""


class TestSimDatabaseRouter:
    def setup_method(self) -> None:
        self.router = SimDatabaseRouter()

    def test_migrations_refused_on_sim_alias(self) -> None:
        assert self.router.allow_migrate("sim", "auth") is False
        assert self.router.allow_migrate("sim", "observatory", model_name="x") is False
        assert self.router.allow_migrate("sim", "game", model_name="GameSession") is False

    def test_migrations_permitted_elsewhere(self) -> None:
        # None = "no opinion" → Django's default (allow) applies to `default`.
        assert self.router.allow_migrate("default", "auth") is None
        assert self.router.allow_migrate("default", "game", model_name="GameSession") is None

    def test_router_abstains_from_read_write_routing(self) -> None:
        # The Observatory targets the `sim` alias explicitly via connections["sim"];
        # it must NOT hijack routing for product models.
        assert self.router.db_for_read(_Model) is None
        assert self.router.db_for_write(_Model) is None

    def test_relations_not_constrained(self) -> None:
        assert self.router.allow_relation(_Model(), _Model()) is None
