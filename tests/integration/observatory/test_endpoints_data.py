"""Endpoint data integration tests (spec-096, US1 + US2) — Postgres-gated.

Drives the real Observatory view functions against a live, seeded sim DB. Uses
``APIRequestFactory`` + ``force_authenticate`` (no auth DB needed) and unblocks
the DB for the raw ``sim`` cursor reads. Asserts the acceptance criteria:
one series point per committed tick, CSV row per tick, full commit chain, and a
reconstructed hex frame.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate

from observatory import views
from tests.integration.observatory.conftest import SeededSession

pytestmark = pytest.mark.integration

_FACTORY = APIRequestFactory()
_USER = User(pk=1, username="observer")  # unsaved; is_authenticated == True


def _call(view: Any, path: str, session_id: str | None = None, **query: Any) -> Any:
    request = _FACTORY.get(path, data=query)
    force_authenticate(request, user=_USER)
    if session_id is not None:
        return view(request, session_id=session_id)
    return view(request)


def _json(response: Any) -> dict[str, Any]:
    return json.loads(response.content)


@pytest.fixture(autouse=True)
def _enabled(settings: Any) -> None:
    settings.OBSERVATORY_ENABLED = True


class TestSessionsAndTicks:
    def test_seeded_session_listed(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        with django_db_blocker.unblock():
            resp = _call(views.observatory_sessions, "/api/observatory/sessions/")
        body = _json(resp)
        assert resp.status_code == 200
        match = [s for s in body["data"] if s["session_id"] == str(seeded_session.session_id)]
        assert len(match) == 1
        row = match[0]
        assert row["min_tick"] == seeded_session.min_tick
        assert row["max_tick"] == seeded_session.max_tick
        assert row["tick_count"] == seeded_session.tick_count

    def test_tick_range(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        with django_db_blocker.unblock():
            resp = _call(
                views.observatory_ticks,
                f"/api/observatory/sessions/{seeded_session.session_id}/ticks/",
                session_id=str(seeded_session.session_id),
            )
        body = _json(resp)
        assert resp.status_code == 200
        assert body["data"]["min_tick"] == 0
        assert body["data"]["max_tick"] == seeded_session.max_tick
        assert 0 in body["data"]["checkpoint_ticks"]  # tick 0 is a checkpoint

    def test_ticks_bad_uuid_400(self, sim_alias: str, django_db_blocker: Any) -> None:
        with django_db_blocker.unblock():
            resp = _call(
                views.observatory_ticks,
                "/api/observatory/sessions/not-a-uuid/ticks/",
                session_id="not-a-uuid",
            )
        assert resp.status_code == 400


class TestSeries:
    @pytest.mark.parametrize("scope", ["national", "state", "county"])
    def test_series_one_point_per_committed_tick(
        self,
        scope: str,
        seeded_session: SeededSession,
        sim_alias: str,
        django_db_blocker: Any,
    ) -> None:
        scope_id = {
            "national": "USA",
            "state": seeded_session.state_fips,
            "county": seeded_session.county_fips,
        }[scope]
        with django_db_blocker.unblock():
            resp = _call(
                views.observatory_series,
                f"/api/observatory/sessions/{seeded_session.session_id}/series/",
                session_id=str(seeded_session.session_id),
                scope=scope,
                scope_id=scope_id,
            )
        body = _json(resp)
        assert resp.status_code == 200
        points = body["data"]["points"]
        assert [p["tick"] for p in points] == [0, 1, 2, 3]  # one per committed tick
        assert all(p["v_sum"] > 0 for p in points)

    def test_series_unknown_scope_400(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        with django_db_blocker.unblock():
            resp = _call(
                views.observatory_series,
                f"/api/observatory/sessions/{seeded_session.session_id}/series/",
                session_id=str(seeded_session.session_id),
                scope="galactic",
            )
        assert resp.status_code == 400

    def test_series_csv_header_plus_row_per_tick(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        with django_db_blocker.unblock():
            resp = _call(
                views.observatory_series_csv,
                f"/api/observatory/sessions/{seeded_session.session_id}/series.csv/",
                session_id=str(seeded_session.session_id),
                scope="national",
            )
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/csv"
        lines = resp.content.decode().strip().splitlines()
        assert lines[0].startswith("tick,c_sum,v_sum")
        assert len(lines) == 1 + seeded_session.tick_count  # header + one per tick


class TestCommitsAndHex:
    def test_commit_chain(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        with django_db_blocker.unblock():
            resp = _call(
                views.observatory_commits,
                f"/api/observatory/sessions/{seeded_session.session_id}/commits/",
                session_id=str(seeded_session.session_id),
            )
        body = _json(resp)
        assert resp.status_code == 200
        records = body["data"]
        assert [r["tick"] for r in records] == [0, 1, 2, 3]
        for r in records:
            assert len(r["determinism_hash"]) == 64
            assert isinstance(r["is_checkpoint"], bool)
            assert r["hex_rows_written"] >= 0

    def test_commit_chain_bounded_by_range(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        # The commits endpoint must accept a tick window like the series one.
        with django_db_blocker.unblock():
            body = _json(
                _call(
                    views.observatory_commits,
                    f"/api/observatory/sessions/{seeded_session.session_id}/commits/",
                    session_id=str(seeded_session.session_id),
                    from_tick=1,
                    to_tick=2,
                )
            )
        assert [r["tick"] for r in body["data"]] == [1, 2]

    def test_hex_frame_at_tick(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        with django_db_blocker.unblock():
            resp = _call(
                views.observatory_hex,
                f"/api/observatory/sessions/{seeded_session.session_id}/hex/",
                session_id=str(seeded_session.session_id),
                tick=seeded_session.max_tick,
            )
        body = _json(resp)
        assert resp.status_code == 200
        hexes = body["data"]["hexes"]
        assert len(hexes) == 2  # both seeded hexes reconstruct at the tick
        # Value tuple comes straight from the delta store (h.c), unaffected by
        # the global hex_spatial_map COALESCE in the as-of view. At tick 3,
        # scale=1.3 -> c = 10 * 1.3 = 13.0.
        assert all(h["c"] == pytest.approx(13.0) for h in hexes)
        assert {h["h3_index"] for h in hexes} == {"872a91055ffffff", "872a9105bffffff"}

    def test_hex_county_filter(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        with django_db_blocker.unblock():
            resp = _call(
                views.observatory_hex,
                f"/api/observatory/sessions/{seeded_session.session_id}/hex/",
                session_id=str(seeded_session.session_id),
                tick=seeded_session.max_tick,
                county_fips="99999",  # no hexes here
            )
        body = _json(resp)
        assert resp.status_code == 200
        assert body["data"]["hexes"] == []

    def test_hex_missing_tick_400(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        with django_db_blocker.unblock():
            resp = _call(
                views.observatory_hex,
                f"/api/observatory/sessions/{seeded_session.session_id}/hex/",
                session_id=str(seeded_session.session_id),
            )
        assert resp.status_code == 400

    def test_hex_frame_bounded_and_paginates(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        # CRITICAL fix: /hex/ must be bounded. limit=1 over a 2-hex frame must
        # signal truncation and hand back a cursor; the cursor fetches the rest.
        with django_db_blocker.unblock():
            first = _json(
                _call(
                    views.observatory_hex,
                    f"/api/observatory/sessions/{seeded_session.session_id}/hex/",
                    session_id=str(seeded_session.session_id),
                    tick=seeded_session.max_tick,
                    limit=1,
                )
            )["data"]
        assert first["limit"] == 1
        assert len(first["hexes"]) == 1
        assert first["truncated"] is True
        assert first["next_h3"] == first["hexes"][0]["h3_index"]

        with django_db_blocker.unblock():
            second = _json(
                _call(
                    views.observatory_hex,
                    f"/api/observatory/sessions/{seeded_session.session_id}/hex/",
                    session_id=str(seeded_session.session_id),
                    tick=seeded_session.max_tick,
                    limit=1,
                    after_h3=first["next_h3"],
                )
            )["data"]
        assert len(second["hexes"]) == 1
        assert second["truncated"] is False
        assert second["next_h3"] is None
        # The two pages together cover both hexes, no overlap.
        assert first["hexes"][0]["h3_index"] != second["hexes"][0]["h3_index"]
