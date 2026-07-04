"""Deep-pane integration tests (spec-099).

Two kinds:
* **Archive** — read the REAL archived 520-tick canonical session
  (``edf07b2e-…``) via ``source=archive`` (DuckDB over Parquet; no Postgres
  needed). Skips if the archive session is absent. Asserts read-only.
* **Live** — the deep endpoints over a seeded Postgres session (096 fixtures):
  verify ok, boundary empty-state, conservation empty, diff self = zero.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate

from observatory import deep_views, views
from observatory.sources import archive_dir
from tests.integration.observatory.conftest import SeededSession

pytestmark = pytest.mark.integration

_FACTORY = APIRequestFactory()
_USER = User(pk=1, username="observer")
_ARCHIVED_SID = "edf07b2e-ac2f-4ed7-990e-cadd159ed7b2"


def _call(view: Any, path: str, session_id: str | None = None, **query: Any) -> Any:
    request = _FACTORY.get(path, data=query)
    force_authenticate(request, user=_USER)
    return view(request, session_id=session_id) if session_id is not None else view(request)


def _json(response: Any) -> dict[str, Any]:
    return json.loads(response.content)


@pytest.fixture(autouse=True)
def _enabled(settings: Any) -> None:
    settings.OBSERVATORY_ENABLED = True


def _archive_present() -> bool:
    return (archive_dir(_ARCHIVED_SID) / "tick_commit.parquet").is_file()


@pytest.mark.skipif(not _archive_present(), reason="archived session edf07b2e not present")
class TestArchiveSource:
    def test_verify_archived_chain_valid(self) -> None:
        resp = _call(
            deep_views.observatory_verify,
            f"/api/observatory/sessions/{_ARCHIVED_SID}/verify/",
            session_id=_ARCHIVED_SID,
            source="archive",
        )
        body = _json(resp)["data"]
        assert resp.status_code == 200
        assert body["source"] == "archive"
        assert body["valid"] is True
        assert body["tick_count"] == 520
        assert body["min_tick"] == 0 and body["max_tick"] == 519
        assert body["checkpoint_ticks"][:3] == [0, 52, 104]
        assert body["anomalies"] == []
        # spec-099 fix #1/#2/#7: the verdict is honestly scoped — structural
        # checks only, never a content/tamper claim.
        assert body["verification_scope"] == "structural"

    def test_commits_archived_via_source(self) -> None:
        resp = _call(
            views.observatory_commits,
            f"/api/observatory/sessions/{_ARCHIVED_SID}/commits/",
            session_id=_ARCHIVED_SID,
            source="archive",
        )
        rows = _json(resp)["data"]
        assert resp.status_code == 200
        assert len(rows) == 520
        assert all(len(r["determinism_hash"]) == 64 for r in rows)
        # spec-099 fix #1: created_at_utc must be the REAL archived timestamp,
        # not silently nulled — non-null, ISO-8601, distinct across ticks.
        assert all(r["created_at_utc"] is not None for r in rows)
        assert all("T" in r["created_at_utc"] for r in rows)
        assert len({r["created_at_utc"] for r in rows}) > 1

    def test_hex_archive_source_is_explicit_501(self) -> None:
        # spec-099 fix #3: hex/ dispatches on source but archive is not
        # implemented (hex_spatial_map is reference-only, not exported
        # per-session) — an honest 501, never silent empty/stale live data.
        resp = _call(
            views.observatory_hex,
            f"/api/observatory/sessions/{_ARCHIVED_SID}/hex/",
            session_id=_ARCHIVED_SID,
            source="archive",
            tick=0,
        )
        assert resp.status_code == 501
        assert _json(resp)["status"] == "error"

    def test_sessions_lists_archived(self) -> None:
        resp = _call(views.observatory_sessions, "/api/observatory/sessions/", source="archive")
        ids = {s["session_id"] for s in _json(resp)["data"]}
        assert _ARCHIVED_SID in ids

    def test_national_series_reconstructs(self) -> None:
        resp = _call(
            views.observatory_series,
            f"/api/observatory/sessions/{_ARCHIVED_SID}/series/",
            session_id=_ARCHIVED_SID,
            source="archive",
            scope="national",
            from_tick=0,
            to_tick=10,
        )
        body = _json(resp)["data"]
        assert resp.status_code == 200
        assert [p["tick"] for p in body["points"]] == list(range(11))
        assert all(p["v_sum"] > 0 for p in body["points"])

    def test_boundary_empty_state(self) -> None:
        resp = _call(
            deep_views.observatory_boundary,
            f"/api/observatory/sessions/{_ARCHIVED_SID}/boundary/",
            session_id=_ARCHIVED_SID,
            source="archive",
        )
        body = _json(resp)["data"]
        assert resp.status_code == 200
        assert body["by_flow_type"] == []
        assert body["rows"] == []
        assert body["truncated"] is False

    def test_archive_reads_are_read_only(self) -> None:
        chain_file = archive_dir(_ARCHIVED_SID) / "tick_commit.parquet"
        before = chain_file.stat().st_mtime_ns
        _call(
            deep_views.observatory_verify,
            f"/api/observatory/sessions/{_ARCHIVED_SID}/verify/",
            session_id=_ARCHIVED_SID,
            source="archive",
        )
        assert chain_file.stat().st_mtime_ns == before  # never rewritten


class TestLiveDeepPanes:
    def test_verify_live_valid(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        with django_db_blocker.unblock():
            resp = _call(
                deep_views.observatory_verify,
                f"/api/observatory/sessions/{seeded_session.session_id}/verify/",
                session_id=str(seeded_session.session_id),
            )
        body = _json(resp)["data"]
        assert body["valid"] is True
        assert body["tick_count"] == seeded_session.tick_count
        assert body["source"] == "live"
        assert body["verification_scope"] == "structural"

    def test_boundary_empty_state_live(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        with django_db_blocker.unblock():
            resp = _call(
                deep_views.observatory_boundary,
                f"/api/observatory/sessions/{seeded_session.session_id}/boundary/",
                session_id=str(seeded_session.session_id),
            )
        body = _json(resp)["data"]
        assert resp.status_code == 200
        assert body["by_flow_type"] == []
        assert body["rows"] == []
        assert body["truncated"] is False

    def test_conservation_empty_state_live(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        with django_db_blocker.unblock():
            resp = _call(
                deep_views.observatory_conservation,
                f"/api/observatory/sessions/{seeded_session.session_id}/conservation/",
                session_id=str(seeded_session.session_id),
            )
        assert resp.status_code == 200
        data = _json(resp)["data"]
        assert data["rows"] == []
        assert data["truncated"] is False

    def test_diff_self_is_zero(
        self, seeded_session: SeededSession, sim_alias: str, django_db_blocker: Any
    ) -> None:
        sid = str(seeded_session.session_id)
        with django_db_blocker.unblock():
            resp = _call(deep_views.observatory_diff, "/api/observatory/diff/", a=sid, b=sid)
        body = _json(resp)["data"]
        assert resp.status_code == 200
        assert all(row["delta"] == 0 for row in body["national"])
        assert body["commits"]["tick_count_delta"] == 0
