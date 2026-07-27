"""Contract for the RustClientHost seam (M0 lobby surface, ADR150).

The host is THE seam between the Python composition root and the Rust
client: every read crosses as a JSON string of primitives, and the Rust
side's ``LobbyRow`` deserializer requires ``campaign_id``/``name``/``tick``
keys on each row (extra keys are tolerated by serde and carry provenance).
"""

from __future__ import annotations

import json
from uuid import UUID

import pytest

from babylon.tui.campaign_menu import InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.host import RustClientHost

pytestmark = pytest.mark.unit

_DEFINES_HASH = "deadbeef" * 8
_ENGINE_VERSION = "1.2.3"


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
