"""Settings-wiring tests for the Observatory (spec-096).

The fast unit gate runs under ``babylon_web.settings.testing`` (SQLite), which
reassigns ``DATABASES`` to the in-memory default only — so the ``sim`` alias is
asserted against the ``base`` module directly (where it is defined), while
INSTALLED_APPS / DATABASE_ROUTERS / OBSERVATORY_ENABLED are inherited by
``testing`` from ``base`` and asserted on the live settings.
"""

from __future__ import annotations

import pytest
from django.conf import settings

pytestmark = pytest.mark.unit


class TestObservatoryAppWiring:
    def test_observatory_app_installed(self) -> None:
        assert "observatory.apps.ObservatoryConfig" in settings.INSTALLED_APPS

    def test_router_registered(self) -> None:
        assert "observatory.router.SimDatabaseRouter" in settings.DATABASE_ROUTERS

    def test_flag_present_and_bool(self) -> None:
        assert isinstance(settings.OBSERVATORY_ENABLED, bool)


class TestSimAliasInBaseSettings:
    def test_base_defines_sim_alias(self) -> None:
        from babylon_web.settings import base

        assert "sim" in base.DATABASES
        sim = base.DATABASES["sim"]
        assert sim["ENGINE"] == "django.db.backends.postgresql"
        assert sim["OPTIONS"]["options"] == "-c default_transaction_read_only=on"

    def test_default_alias_untouched(self) -> None:
        from babylon_web.settings import base

        # The product DB stays the PostGIS backend; the Observatory does not
        # repurpose it.
        assert base.DATABASES["default"]["ENGINE"] == ("django.contrib.gis.db.backends.postgis")


class TestFlagPerEnvironment:
    def test_development_enables_observatory(self) -> None:
        from babylon_web.settings import development

        assert development.OBSERVATORY_ENABLED is True

    def test_production_disables_observatory(self) -> None:
        from babylon_web.settings import production

        assert production.OBSERVATORY_ENABLED is False
