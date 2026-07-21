"""WO-47: navigation state survives a restart via ``babylon_meta``.

The unit tier proves the same contract against the in-memory fake; this
is the real thing — a :class:`~babylon.tui.nav.NavShell` persisting
through :class:`~babylon.persistence.babylon_meta.BabylonMetaStore` into
Postgres, then a second shell (a "restarted client") restoring it. The
only cross-session loss is unretraced forward depth (the shell resumes at
the newest entry), which is the documented cursor choice, not drift.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest

from babylon.persistence.babylon_meta import BabylonMetaStore
from babylon.tui.nav import NavShell

pytestmark = pytest.mark.integration


@pytest.fixture()
def meta_store(pg_pool: Any) -> Iterator[BabylonMetaStore]:
    """A schema-ensured store; campaigns minted here are cleaned up."""
    store = BabylonMetaStore(pg_pool)
    store.ensure_schema()
    yield store
    with pg_pool.connection() as conn:
        conn.execute("DELETE FROM babylon_meta.campaign WHERE slug LIKE 'wo47-%'")


def _campaign(store: BabylonMetaStore) -> Any:
    return store.create_campaign(
        slug=f"wo47-{uuid.uuid4().hex[:12]}", engine_version="0.24.0", defines_hash="d" * 16
    )


def test_nav_state_survives_restart(meta_store: BabylonMetaStore) -> None:
    campaign = _campaign(meta_store)
    first = NavShell(campaign_id=campaign.campaign_id, persistence=meta_store)
    first.visit("county/26163")
    first.visit("org/tenants-un")
    first.visit("national/USA")

    second = NavShell.restore(campaign_id=campaign.campaign_id, persistence=meta_store)
    assert second.current == "national/USA"
    assert second.back() == "org/tenants-un"
    assert second.back() == "county/26163"
    assert second.trail.entries == ("county/26163", "org/tenants-un", "national/USA")


def test_jumps_after_restore_keep_persisting(meta_store: BabylonMetaStore) -> None:
    """The restored shell is live, not a read-only replay."""
    campaign = _campaign(meta_store)
    first = NavShell(campaign_id=campaign.campaign_id, persistence=meta_store)
    first.visit("county/26163")

    second = NavShell.restore(campaign_id=campaign.campaign_id, persistence=meta_store)
    second.visit("state/26")
    third = NavShell.restore(campaign_id=campaign.campaign_id, persistence=meta_store)
    assert third.current == "state/26"
    assert third.trail.entries == ("county/26163", "state/26")


def test_fresh_campaign_restores_honestly_empty(meta_store: BabylonMetaStore) -> None:
    campaign = _campaign(meta_store)
    shell = NavShell.restore(campaign_id=campaign.campaign_id, persistence=meta_store)
    assert shell.current is None
    assert shell.trail.entries == ()


def test_unknown_campaign_restores_empty_but_cannot_save(
    meta_store: BabylonMetaStore,
) -> None:
    """Loads are honest-empty; a save without a campaign fails loud (FK)."""
    import psycopg

    shell = NavShell.restore(campaign_id=uuid4(), persistence=meta_store)
    assert shell.current is None
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        shell.visit("county/26163")
