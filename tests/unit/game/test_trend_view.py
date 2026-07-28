"""Contract tests for ``GameSession.trend_view`` / ``national_value_snapshot``
(M6 Task 41, contract §1).

The session tier of the ``trend_json`` stack: ``trend_view(last_n)``
delegates to the store seam's ``fetch_national_trend`` (rows oldest →
newest, computed fresh — never cached) with a LOUD ``ValueError`` on a
non-positive ``last_n`` (the M4 out-of-vocabulary precedent);
``national_value_snapshot`` delegates to ``fetch_latest_national_aggregate``
and passes honest absence (``None``) through untouched. The store is the
Protocol seam — the fake below records calls, so these tests pin the
DELEGATION contract; the SQL itself is pinned in
``tests/unit/persistence/test_trend_fetch.py`` and proved against live
Postgres in ``tests/integration/persistence/test_trend_playability_view.py``.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from babylon.engine.scenarios import WayneCountyScenario
from babylon.game.session import create_new_campaign
from babylon.persistence.postgres_aggregation import NationalValueAggregate
from babylon.projection.view_models import NationalTrendView
from tests.unit.game.test_session import _FakeStore

pytestmark = [pytest.mark.unit]


def _trend_row(tick: int, **overrides: object) -> NationalTrendView:
    return NationalTrendView(session_id=uuid4(), tick=tick, **overrides)  # type: ignore[arg-type]


class _TrendStore(_FakeStore):
    """The shared store fake plus canned trend/aggregate rows + call records."""

    def __init__(self) -> None:
        super().__init__()
        self.trend_rows: list[NationalTrendView] = []
        self.latest_aggregate: NationalValueAggregate | None = None
        self.fetch_trend_calls: list[tuple[UUID, int]] = []
        self.fetch_latest_calls: list[UUID] = []

    def fetch_national_trend(self, session_id: UUID, last_n: int) -> list[NationalTrendView]:
        self.fetch_trend_calls.append((session_id, last_n))
        return list(self.trend_rows)

    def fetch_latest_national_aggregate(self, session_id: UUID) -> NationalValueAggregate | None:
        self.fetch_latest_calls.append(session_id)
        return self.latest_aggregate


def _session(store: _TrendStore):
    return create_new_campaign(store, scenario=WayneCountyScenario())


class TestTrendView:
    def test_delegates_with_the_sessions_own_id_and_last_n(self) -> None:
        store = _TrendStore()
        store.trend_rows = [_trend_row(1), _trend_row(2)]
        session = _session(store)

        rows = session.trend_view(50)

        assert store.fetch_trend_calls == [(session.session_id, 50)]
        assert isinstance(rows, tuple)
        assert [r.tick for r in rows] == [1, 2]

    def test_empty_history_is_an_empty_tuple(self) -> None:
        session = _session(_TrendStore())
        assert session.trend_view(10) == ()

    @pytest.mark.parametrize("bad", [0, -1, -50])
    def test_non_positive_last_n_raises_loud(self, bad: int) -> None:
        store = _TrendStore()
        session = _session(store)
        with pytest.raises(ValueError, match="last_n"):
            session.trend_view(bad)
        assert store.fetch_trend_calls == []  # refused BEFORE the read

    def test_computed_fresh_every_call(self) -> None:
        store = _TrendStore()
        session = _session(store)
        session.trend_view(5)
        store.trend_rows = [_trend_row(9)]
        assert [r.tick for r in session.trend_view(5)] == [9]
        assert len(store.fetch_trend_calls) == 2


class TestNationalValueSnapshot:
    def test_absent_row_is_none(self) -> None:
        store = _TrendStore()
        session = _session(store)
        assert session.national_value_snapshot() is None
        assert store.fetch_latest_calls == [session.session_id]

    def test_present_row_passes_through(self) -> None:
        store = _TrendStore()
        session = _session(store)
        store.latest_aggregate = NationalValueAggregate(
            session_id=session.session_id,
            tick=0,
            national_id="USA",
            c_sum=100.0,
            v_sum=50.0,
            s_sum=75.0,
            k_sum=10.0,
            biocapacity_sum=0.0,
            hex_count=3,
        )
        snap = session.national_value_snapshot()
        assert snap is not None
        assert snap.s_sum == pytest.approx(75.0)
