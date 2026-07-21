"""WO-49: the campaign menu lists from ``babylon_meta`` — the real store.

The unit tier proves the lobby against the in-memory catalog; this pins
the seam's whole point: :class:`~babylon.tui.campaign_menu.CampaignMenu`
running unmodified over :class:`~babylon.persistence.babylon_meta.
BabylonMetaStore`, with mint / archive / delete visible to a SECOND menu
instance (a restarted client) reading the same database.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from babylon.persistence.babylon_meta import BabylonMetaStore
from babylon.tui.campaign_menu import CampaignMenu

pytestmark = pytest.mark.integration


@pytest.fixture()
def meta_store(pg_pool: Any) -> Iterator[BabylonMetaStore]:
    """A schema-ensured store; menu-minted campaigns are cleaned up."""
    store = BabylonMetaStore(pg_pool)
    store.ensure_schema()
    yield store
    with pg_pool.connection() as conn:
        conn.execute("DELETE FROM babylon_meta.campaign WHERE slug LIKE 'campaign-%'")


def _menu(store: BabylonMetaStore) -> CampaignMenu:
    return CampaignMenu(store, engine_version="0.24.0", defines_hash="d" * 16)


def test_mint_is_visible_to_a_restarted_menu(meta_store: BabylonMetaStore) -> None:
    first = _menu(meta_store)
    minted = first.new_campaign()

    second = _menu(meta_store)
    row = next(r for r in second.rows() if r.campaign_id == minted.campaign_id)
    assert row.codename == minted.codename
    assert row.tick_label == "Tick 0"
    assert row.status == "ACTIVE"


def test_archive_survives_restart_and_reverses(meta_store: BabylonMetaStore) -> None:
    first = _menu(meta_store)
    minted = first.new_campaign()
    first.toggle_archive(minted.campaign_id)

    second = _menu(meta_store)
    statuses = {r.campaign_id: r.status for r in second.rows()}
    assert statuses[minted.campaign_id] == "ABANDONED"
    assert second.toggle_archive(minted.campaign_id) == "ACTIVE"


def test_armed_confirm_hard_deletes_from_the_catalog(meta_store: BabylonMetaStore) -> None:
    menu = _menu(meta_store)
    minted = menu.new_campaign()
    menu.arm_delete(minted.campaign_id)
    assert menu.confirm_delete(minted.campaign_id) is True
    assert minted.campaign_id not in {r.campaign_id for r in _menu(meta_store).rows()}
