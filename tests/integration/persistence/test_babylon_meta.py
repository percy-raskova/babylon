"""WO-46 database-backed contracts for the ``babylon_meta`` epistemic tier.

What the store DOES against a real Postgres (behavioral, not choreography):
idempotent digest-stamped DDL apply, campaign catalog CRUD with the WO-49
lifecycle (reversible ``ABANDONED``, terminal delete with cascade), and the
three navigation-list round-trips — including the ``WatchlistPersistence``
seam methods (:meth:`load` / :meth:`save`) the TUI composition root will
inject. Loud-failure policy is pinned too: duplicate slugs, orphan saves
and progress against a missing campaign all raise, never silently no-op.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import psycopg
import pytest

from babylon.persistence.babylon_meta import BabylonMetaStore

pytestmark = pytest.mark.integration

_META_TABLES = ("campaign", "watchlist", "jumplist", "breadcrumb")


@pytest.fixture()
def meta_store(pg_pool: Any) -> Iterator[BabylonMetaStore]:
    """A schema-ensured store; campaigns minted by the test are cleaned up."""
    store = BabylonMetaStore(pg_pool)
    store.ensure_schema()
    yield store
    with pg_pool.connection() as conn:
        conn.execute("DELETE FROM babylon_meta.campaign WHERE slug LIKE 'wo46-%'")


def _slug() -> str:
    return f"wo46-{uuid.uuid4().hex[:12]}"


def _mint(store: BabylonMetaStore) -> Any:
    return store.create_campaign(slug=_slug(), engine_version="0.24.0", defines_hash="d" * 16)


class TestSchemaApply:
    def test_tables_exist_and_reapply_fast_paths(
        self, meta_store: BabylonMetaStore, pg_pool: Any
    ) -> None:
        """All four tables exist; a repeat ensure executes nothing."""
        with pg_pool.connection() as conn:
            for table in _META_TABLES:
                row = conn.execute("SELECT to_regclass(%s)", (f"babylon_meta.{table}",)).fetchone()
                assert row is not None and row[0] is not None, table
        assert meta_store.ensure_schema() is False


class TestCampaignCatalog:
    def test_create_returns_the_full_row_with_defaults(self, meta_store: BabylonMetaStore) -> None:
        record = _mint(meta_store)
        assert record.last_tick == 0
        assert record.status == "ACTIVE"
        assert record.last_played_at is None
        assert record.created_at is not None

    def test_get_round_trips_and_unknown_is_none(self, meta_store: BabylonMetaStore) -> None:
        record = _mint(meta_store)
        assert meta_store.get_campaign(record.campaign_id) == record
        assert meta_store.get_campaign(uuid4()) is None

    def test_list_contains_minted_campaigns_newest_first(
        self, meta_store: BabylonMetaStore
    ) -> None:
        first = _mint(meta_store)
        second = _mint(meta_store)
        listed_ids = [c.campaign_id for c in meta_store.list_campaigns()]
        assert listed_ids.index(second.campaign_id) < listed_ids.index(first.campaign_id)

    def test_duplicate_slug_raises_loud(self, meta_store: BabylonMetaStore) -> None:
        slug = _slug()
        meta_store.create_campaign(slug=slug, engine_version="0.24.0", defines_hash="d")
        with pytest.raises(psycopg.errors.UniqueViolation):
            meta_store.create_campaign(slug=slug, engine_version="0.24.0", defines_hash="d")

    def test_record_progress_updates_tick_and_played_at(self, meta_store: BabylonMetaStore) -> None:
        record = _mint(meta_store)
        meta_store.record_progress(record.campaign_id, last_tick=52)
        fetched = meta_store.get_campaign(record.campaign_id)
        assert fetched is not None
        assert fetched.last_tick == 52
        assert fetched.last_played_at is not None

    def test_record_progress_against_missing_campaign_raises(
        self, meta_store: BabylonMetaStore
    ) -> None:
        with pytest.raises(LookupError):
            meta_store.record_progress(uuid4(), last_tick=1)

    def test_abandon_is_reversible(self, meta_store: BabylonMetaStore) -> None:
        """WO-49's soft-delete: ABANDONED is a status, not a deletion."""
        record = _mint(meta_store)
        meta_store.set_status(record.campaign_id, "ABANDONED")
        abandoned = meta_store.get_campaign(record.campaign_id)
        assert abandoned is not None and abandoned.status == "ABANDONED"
        meta_store.set_status(record.campaign_id, "ACTIVE")
        restored = meta_store.get_campaign(record.campaign_id)
        assert restored is not None and restored.status == "ACTIVE"

    def test_delete_is_terminal_and_reports_honestly(self, meta_store: BabylonMetaStore) -> None:
        record = _mint(meta_store)
        assert meta_store.delete_campaign(record.campaign_id) is True
        assert meta_store.get_campaign(record.campaign_id) is None
        assert meta_store.delete_campaign(record.campaign_id) is False


class TestWatchlistSeam:
    def test_round_trip_preserves_pin_order(self, meta_store: BabylonMetaStore) -> None:
        record = _mint(meta_store)
        key = str(record.campaign_id)
        meta_store.save(key, ("county/26163", "org/tenants-un", "class/C001"))
        assert meta_store.load(key) == ("county/26163", "org/tenants-un", "class/C001")

    def test_save_replaces_the_full_list(self, meta_store: BabylonMetaStore) -> None:
        record = _mint(meta_store)
        key = str(record.campaign_id)
        meta_store.save(key, ("a", "b", "c"))
        meta_store.save(key, ("c", "a"))
        assert meta_store.load(key) == ("c", "a")

    def test_unknown_campaign_loads_honestly_empty(self, meta_store: BabylonMetaStore) -> None:
        assert meta_store.load(str(uuid4())) == ()

    def test_save_for_missing_campaign_raises_loud(self, meta_store: BabylonMetaStore) -> None:
        """A watchlist cannot outlive (or predate) its campaign."""
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            meta_store.save(str(uuid4()), ("county/26163",))

    def test_empty_save_round_trips(self, meta_store: BabylonMetaStore) -> None:
        record = _mint(meta_store)
        key = str(record.campaign_id)
        meta_store.save(key, ("a",))
        meta_store.save(key, ())
        assert meta_store.load(key) == ()


class TestNavigationLists:
    def test_jumplist_allows_revisits_and_preserves_order(
        self, meta_store: BabylonMetaStore
    ) -> None:
        """A back-stack legitimately revisits pages — repeats are data."""
        record = _mint(meta_store)
        stack = ("county/26163", "org/tenants-un", "county/26163")
        meta_store.save_jumplist(record.campaign_id, stack)
        assert meta_store.load_jumplist(record.campaign_id) == stack

    def test_breadcrumbs_round_trip(self, meta_store: BabylonMetaStore) -> None:
        record = _mint(meta_store)
        trail = ("national/USA", "state/26", "county/26163")
        meta_store.save_breadcrumbs(record.campaign_id, trail)
        assert meta_store.load_breadcrumbs(record.campaign_id) == trail

    def test_lists_are_isolated_per_campaign(self, meta_store: BabylonMetaStore) -> None:
        one = _mint(meta_store)
        two = _mint(meta_store)
        meta_store.save_jumplist(one.campaign_id, ("a",))
        meta_store.save_jumplist(two.campaign_id, ("b", "c"))
        assert meta_store.load_jumplist(one.campaign_id) == ("a",)
        assert meta_store.load_jumplist(two.campaign_id) == ("b", "c")

    def test_delete_campaign_cascades_all_lists(self, meta_store: BabylonMetaStore) -> None:
        record = _mint(meta_store)
        key = str(record.campaign_id)
        meta_store.save(key, ("a",))
        meta_store.save_jumplist(record.campaign_id, ("b",))
        meta_store.save_breadcrumbs(record.campaign_id, ("c",))
        meta_store.delete_campaign(record.campaign_id)
        assert meta_store.load(key) == ()
        assert meta_store.load_jumplist(record.campaign_id) == ()
        assert meta_store.load_breadcrumbs(record.campaign_id) == ()
