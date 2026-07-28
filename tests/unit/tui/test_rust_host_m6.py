"""Contract tests for ``RustClientHost.trend_json`` / ``dashboard_view_json``
(M6 Task 41, contract §1).

The wire tier only — session behavior is pinned in
``tests/unit/game/test_trend_view.py``. Pins: ``"null"`` for the unbound
session; the pinned envelope ``{"verified_tick", "rows",
"national_value"}``; rows via ``model_dump(mode="json")`` (``session_id``
is a UUID — a raw ``model_dump`` would not serialize); ``national_value``
rates derived RATIO-OF-SUMS (``s/v`` and ``s/(c+v)``, the
intensive-aggregation law) with ``None`` on a zero denominator (honest
absence — a rate over nothing is not a signal) and carrying its OWN
``tick`` (the hex ledger is tick-0-frozen today, M5 recon — the client
must be able to disclose staleness); the session's loud ``ValueError``
propagating for a bad ``last_n`` (never laundered to ``"null"``);
``dashboard_view_json`` as the thin ``model_dump_json`` passthrough.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from uuid import UUID

import pytest

from babylon.persistence.postgres_aggregation import NationalValueAggregate
from babylon.projection.economy import project_economy
from babylon.projection.view_models import EconomyView, NationalTrendView
from babylon.tui.campaign_menu import InMemoryCampaignCatalog
from babylon.tui.host import RustClientHost

pytestmark = pytest.mark.unit

_SESSION_ID = UUID("00000000-0000-0000-0000-000000000042")


def _aggregate(**overrides: float) -> NationalValueAggregate:
    values: dict[str, object] = {
        "session_id": _SESSION_ID,
        "tick": 0,
        "national_id": "USA",
        "c_sum": 100.0,
        "v_sum": 50.0,
        "s_sum": 75.0,
        "k_sum": 10.0,
        "biocapacity_sum": 0.0,
        "hex_count": 3,
    }
    values.update(overrides)
    return NationalValueAggregate(**values)  # type: ignore[arg-type]


@dataclass
class _FakeSession:
    """Just enough session for the passthrough: canned rows + the real
    ValueError contract."""

    tick: int = 7
    rows: tuple[NationalTrendView, ...] = ()
    aggregate: NationalValueAggregate | None = None
    dashboard: EconomyView | None = None
    calls: list[int] = field(default_factory=list)

    def trend_view(self, last_n: int) -> tuple[NationalTrendView, ...]:
        if last_n < 1:
            raise ValueError(f"trend_view last_n must be positive, got {last_n}")
        self.calls.append(last_n)
        return self.rows

    def national_value_snapshot(self) -> NationalValueAggregate | None:
        return self.aggregate

    def dashboard_view(self) -> EconomyView | None:
        return self.dashboard


def _host(session: _FakeSession | None) -> RustClientHost:
    host = RustClientHost(InMemoryCampaignCatalog(), defines_hash="dh1", engine_version="ev1")
    host.session = session  # type: ignore[assignment]
    return host


class TestTrendJson:
    def test_unbound_session_is_null(self) -> None:
        assert _host(None).trend_json('{"last_n": 50}') == "null"

    def test_envelope_is_the_pinned_shape(self) -> None:
        row = NationalTrendView(session_id=_SESSION_ID, tick=3, imperial_rent=12.5)
        session = _FakeSession(rows=(row,))

        parsed = json.loads(_host(session).trend_json('{"last_n": 50}'))

        assert list(parsed.keys()) == ["verified_tick", "rows", "national_value"]
        assert parsed["verified_tick"] == 7
        assert session.calls == [50]
        assert len(parsed["rows"]) == 1
        assert parsed["rows"][0]["tick"] == 3
        assert parsed["rows"][0]["imperial_rent"] == pytest.approx(12.5)
        # UUIDs must have crossed as strings (model_dump(mode="json")).
        assert parsed["rows"][0]["session_id"] == str(_SESSION_ID)
        assert parsed["national_value"] is None

    def test_national_value_carries_ratio_of_sums_rates_and_its_own_tick(self) -> None:
        session = _FakeSession(aggregate=_aggregate())

        parsed = json.loads(_host(session).trend_json('{"last_n": 10}'))

        nv = parsed["national_value"]
        assert list(nv.keys()) == [
            "tick",
            "c_sum",
            "v_sum",
            "s_sum",
            "k_sum",
            "exploitation_rate",
            "profit_rate",
        ]
        assert nv["tick"] == 0
        assert nv["exploitation_rate"] == pytest.approx(75.0 / 50.0)
        assert nv["profit_rate"] == pytest.approx(75.0 / 150.0)

    def test_zero_denominators_are_honest_none_never_a_fabricated_rate(self) -> None:
        session = _FakeSession(aggregate=_aggregate(c_sum=0.0, v_sum=0.0))

        nv = json.loads(_host(session).trend_json('{"last_n": 10}'))["national_value"]

        assert nv["exploitation_rate"] is None
        assert nv["profit_rate"] is None
        assert nv["s_sum"] == pytest.approx(75.0)

    def test_bad_last_n_raises_through_the_seam(self) -> None:
        with pytest.raises(ValueError, match="last_n"):
            _host(_FakeSession()).trend_json('{"last_n": 0}')


class TestDashboardViewJson:
    def test_unbound_session_is_null(self) -> None:
        assert _host(None).dashboard_view_json() == "null"

    def test_absent_view_is_null(self) -> None:
        assert _host(_FakeSession()).dashboard_view_json() == "null"

    def test_round_trips_the_economy_view_verbatim(self) -> None:
        from babylon.models.world_state import WorldState
        from babylon.topology import BabylonGraph

        world = WorldState(tick=0)
        view = project_economy("USA", graph=BabylonGraph(), world=world, tick=0)
        session = _FakeSession(dashboard=view)

        raw = _host(session).dashboard_view_json()

        assert json.loads(raw) == json.loads(view.model_dump_json())
