"""Contract for the RustClientHost seam (M0 lobby surface + M1 read surface, ADR150).

The host is THE seam between the Python composition root and the Rust
client: every read crosses as a JSON string of primitives, and the Rust
side's ``LobbyRow`` deserializer requires ``campaign_id``/``name``/``tick``
keys on each row (extra keys are tolerated by serde and carry provenance).

The M1 classes below (``TestReadPage``/``TestKnownSubjects``/
``TestBacklinks``/``TestSubjectView``/``TestWatchlist``) extend the contract
to the M1 read surface: :meth:`~babylon.tui.host.RustClientHost.read_page_json`,
:meth:`~babylon.tui.host.RustClientHost.known_subjects_json`,
:meth:`~babylon.tui.host.RustClientHost.backlinks_json`,
:meth:`~babylon.tui.host.RustClientHost.subject_view_json`, and
:meth:`~babylon.tui.host.RustClientHost.watchlist_json`. ``_FakeCampaign``
mirrors ``test_app_watchlist_live.py``'s own minimal ``CampaignHandle``
double — only the members the M1 host methods actually call
(``session_id``/``tick``/``read_page``/``known_subjects``/``subject_view``)
rather than the full Protocol surface (``dashboard_view``/``issue_verb``/
etc., which no M1 host method touches); :meth:`RustClientHost.bind_session`
accepts it via the same ``# type: ignore[arg-type]`` the pre-existing
``TestBindSession`` class already uses for its own trivial ``object()``
double.
"""

from __future__ import annotations

import json
from typing import Final
from uuid import UUID

import pytest

from babylon.projection.view_models import CountyView, ProjectionRecord
from babylon.tui.campaign_menu import InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.host import RustClientHost
from babylon.tui.watchlist import InMemoryWatchlistPersistence

pytestmark = pytest.mark.unit

_DEFINES_HASH = "deadbeef" * 8
_ENGINE_VERSION = "1.2.3"
_SESSION_ID = UUID("00000000-0000-0000-0000-0000000000f1")


def _catalog() -> InMemoryCampaignCatalog:
    return InMemoryCampaignCatalog(
        seed=[
            InMemoryCampaign(
                campaign_id=UUID("00000000-0000-0000-0000-000000000001"),
                slug="wayne-county",
                engine_version=_ENGINE_VERSION,
                defines_hash=_DEFINES_HASH,
                last_tick=7,
            ),
            InMemoryCampaign(
                campaign_id=UUID("00000000-0000-0000-0000-000000000002"),
                slug="rust-belt",
                engine_version=_ENGINE_VERSION,
                defines_hash=_DEFINES_HASH,
                last_tick=0,
                status="ABANDONED",
            ),
        ]
    )


def _host(catalog: InMemoryCampaignCatalog | None = None) -> RustClientHost:
    return RustClientHost(
        catalog if catalog is not None else _catalog(),
        defines_hash=_DEFINES_HASH,
        engine_version=_ENGINE_VERSION,
    )


class TestLobbyCatalogJson:
    def test_rows_round_trip_the_catalog(self) -> None:
        rows = json.loads(_host().lobby_catalog_json())
        assert [r["campaign_id"] for r in rows] == [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
        ]
        assert [r["name"] for r in rows] == ["wayne-county", "rust-belt"]
        assert [r["tick"] for r in rows] == [7, 0]
        assert [r["status"] for r in rows] == ["ACTIVE", "ABANDONED"]

    def test_defines_hash_and_engine_version_stamp_every_row(self) -> None:
        rows = json.loads(_host().lobby_catalog_json())
        assert {r["defines_hash"] for r in rows} == {_DEFINES_HASH}
        assert {r["engine_version"] for r in rows} == {_ENGINE_VERSION}

    def test_empty_catalog_is_an_empty_array(self) -> None:
        # Honest absence (III.11): no campaigns is [], never a fabricated row.
        assert json.loads(_host(InMemoryCampaignCatalog()).lobby_catalog_json()) == []


class TestBindSession:
    def test_bind_session_stores_the_handles(self) -> None:
        host = _host()
        session = object()
        driver = object()
        host.bind_session(session, driver)  # type: ignore[arg-type]
        assert host.session is session
        assert host.driver is driver

    def test_unbound_host_has_no_session(self) -> None:
        host = _host()
        assert host.session is None
        assert host.driver is None


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double covering only what the M1 host
    read methods call — see this module's own docstring for why the full
    Protocol surface is unneeded here."""

    def __init__(
        self,
        pages: dict[str, str],
        *,
        session_id: UUID = _SESSION_ID,
        tick: int = 0,
        views: dict[str, ProjectionRecord] | None = None,
    ) -> None:
        self.session_id = session_id
        self.tick = tick
        self._pages = pages
        self._views: dict[str, ProjectionRecord] = views if views is not None else {}

    def read_page(self, subject: str) -> str | None:
        return self._pages.get(subject)

    def known_subjects(self) -> frozenset[str]:
        return frozenset(self._pages)

    def subject_view(self, subject_id: str) -> ProjectionRecord | None:
        return self._views.get(subject_id)


def _bound_host(
    pages: dict[str, str],
    *,
    tick: int = 0,
    views: dict[str, ProjectionRecord] | None = None,
    watchlist_persistence: InMemoryWatchlistPersistence | None = None,
) -> tuple[RustClientHost, _FakeCampaign]:
    host = RustClientHost(
        _catalog(),
        defines_hash=_DEFINES_HASH,
        engine_version=_ENGINE_VERSION,
        watchlist_persistence=watchlist_persistence,
    )
    session = _FakeCampaign(pages, tick=tick, views=views)
    host.bind_session(session, object())  # type: ignore[arg-type]
    return host, session


class TestReadPage:
    def test_unbound_host_reads_null(self) -> None:
        assert _host().read_page_json("county/26163") == "null"

    def test_unknown_subject_reads_null(self) -> None:
        host, _ = _bound_host({"county/26163": "# Wayne"})
        assert host.read_page_json("org/nowhere") == "null"

    def test_known_subject_round_trips_its_markdown(self) -> None:
        host, _ = _bound_host({"county/26163": "# Wayne County"})
        assert json.loads(host.read_page_json("county/26163")) == "# Wayne County"

    def test_read_page_never_bakes_a_missing_subject(self) -> None:
        # read_page is a pure passthrough — reading twice never conjures a
        # page that wasn't there the first time (Constitution III.11).
        host, _ = _bound_host({})
        assert host.read_page("county/26163") is None
        assert host.read_page("county/26163") is None


class TestKnownSubjectsJson:
    def test_unbound_host_is_empty(self) -> None:
        assert json.loads(_host().known_subjects_json()) == []

    def test_known_subjects_are_sorted(self) -> None:
        host, _ = _bound_host(
            {"county/26163": "# W", "org/uaw-9999": "# U", "county/06037": "# LA"}
        )
        assert json.loads(host.known_subjects_json()) == [
            "county/06037",
            "county/26163",
            "org/uaw-9999",
        ]


class TestBacklinksJson:
    """Exercises a tiny 3-page fixture vault: A links to B and C; B links to
    C; C links to nothing. Reuses ``babylon.tui.wikilinks``' own
    ``[[target]]`` grammar — the SAME grammar
    ``babylon.tui.shell.backlinks.build_backlink_index`` inverts."""

    _PAGES: dict[str, str] = {
        "page/a": "# A\n\nSee [[page/b]] and [[page/c|See C]].",
        "page/b": "# B\n\nAlso see [[page/c]].",
        "page/c": "# C\n\nNo outbound links here.",
    }

    def test_unbound_host_has_no_backlinks(self) -> None:
        assert json.loads(_host().backlinks_json("page/c")) == []

    def test_target_with_two_inbound_links_is_sorted(self) -> None:
        host, _ = _bound_host(self._PAGES)
        assert json.loads(host.backlinks_json("page/c")) == ["page/a", "page/b"]

    def test_target_with_one_inbound_link(self) -> None:
        host, _ = _bound_host(self._PAGES)
        assert json.loads(host.backlinks_json("page/b")) == ["page/a"]

    def test_page_with_no_inbound_links_is_empty(self) -> None:
        host, _ = _bound_host(self._PAGES)
        assert json.loads(host.backlinks_json("page/a")) == []

    def test_redlink_target_with_no_baked_page_still_gets_a_backlink(self) -> None:
        # A page can link to a subject the vault never baked (a redlink) —
        # the backlink index records links MADE, not resolvable targets.
        host, _ = _bound_host({"page/a": "# A\n\nSee [[org/never-baked]]."})
        assert json.loads(host.backlinks_json("org/never-baked")) == ["page/a"]

    def test_cache_recomputes_across_a_tick_boundary(self) -> None:
        # Same session_id, tick 0 -> tick 1: a newly-baked page's outbound
        # link must be reflected, proving the cache key includes tick.
        host, session = _bound_host(dict(self._PAGES), tick=0)
        assert json.loads(host.backlinks_json("page/c")) == ["page/a", "page/b"]
        session._pages["page/c"] = "# C\n\nNow links to [[page/a]]."
        session.tick = 1
        assert json.loads(host.backlinks_json("page/a")) == ["page/c"]


class TestSubjectViewJson:
    _VIEW: Final = CountyView(county_fips="26163", verified_tick=7, population=1_749_343)

    def test_unbound_host_is_null(self) -> None:
        assert _host().subject_view_json("county/26163") == "null"

    def test_unresolvable_subject_is_null(self) -> None:
        host, _ = _bound_host({}, views={"county/26163": self._VIEW})
        assert host.subject_view_json("org/nowhere") == "null"

    def test_known_subject_round_trips_a_discriminating_field(self) -> None:
        host, _ = _bound_host({}, views={"county/26163": self._VIEW})
        payload = json.loads(host.subject_view_json("county/26163"))
        assert payload["kind"] == "county"
        assert payload["county_fips"] == "26163"
        assert payload["population"] == 1_749_343


class TestWatchlistJson:
    def test_unbound_host_is_empty(self) -> None:
        assert json.loads(_host().watchlist_json()) == []

    def test_bound_session_with_no_persistence_wired_is_empty(self) -> None:
        host, _ = _bound_host({})  # watchlist_persistence defaults to None
        assert json.loads(host.watchlist_json()) == []

    def test_bound_session_with_empty_watchlist_is_empty(self) -> None:
        host, _ = _bound_host({}, watchlist_persistence=InMemoryWatchlistPersistence())
        assert json.loads(host.watchlist_json()) == []

    def test_pinned_subjects_round_trip_in_pin_order(self) -> None:
        persistence = InMemoryWatchlistPersistence()
        persistence.save(str(_SESSION_ID), ("org/uaw-9999", "county/26163"))
        host, _ = _bound_host({}, watchlist_persistence=persistence)
        assert json.loads(host.watchlist_json()) == [
            {"subject": "org/uaw-9999"},
            {"subject": "county/26163"},
        ]
