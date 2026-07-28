"""Contract tests for ``RustClientHost.choropleth_json`` (M5 Task 37).

The thin-passthrough layer only — envelope CONTENT is pinned at the
session level (``tests/unit/game/test_choropleth_view.py``); here the
wire behavior is: ``"null"`` for the three absence cases, verbatim
JSON round-trip otherwise, and the session's own loud ``ValueError``
propagating for out-of-vocabulary args (never laundered to ``"null"``,
the M4 precedent).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from babylon.tui.campaign_menu import InMemoryCampaignCatalog
from babylon.tui.host import RustClientHost

pytestmark = pytest.mark.unit

_ENVELOPE: dict[str, object] = {
    "tier": "county",
    "lens": "value",
    "verified_tick": 3,
    "bands": [[None, "panel"], [1.0, "dim"], [2.0, "gold"], [None, "crimson"]],
    "overlay_absent": "national overlay ruled (ADR171); Phase-0 incidence artifact not yet built",
    "cells": [
        {"region_id": "01001", "value": "inf", "wkt": None, "centroid": None},
        {"region_id": "26163", "value": 2.5, "wkt": "POLYGON((0 0,1 0,1 1,0 0))", "centroid": None},
    ],
}


@dataclass
class _FakeSession:
    """Just enough session for the passthrough: canned envelopes + the
    real ValueError contract."""

    calls: list[tuple[str, str]] = field(default_factory=list)
    envelope: dict[str, object] | None = None

    def choropleth_view(self, tier: str, lens: str) -> dict[str, object] | None:
        if tier not in ("county", "state", "ea"):
            raise ValueError(f"unknown choropleth tier {tier!r}")
        if lens not in ("value", "tension", "fog"):
            raise ValueError(f"unknown choropleth lens {lens!r}")
        self.calls.append((tier, lens))
        return self.envelope


def _host(session: _FakeSession | None) -> RustClientHost:
    host = RustClientHost(InMemoryCampaignCatalog(), defines_hash="dh1", engine_version="ev1")
    host.session = session  # type: ignore[assignment]
    return host


class TestChoroplethJson:
    def test_unbound_session_is_null(self) -> None:
        assert _host(None).choropleth_json('{"tier": "county", "lens": "value"}') == "null"

    def test_absent_envelope_is_null(self) -> None:
        assert (
            _host(_FakeSession()).choropleth_json('{"tier": "county", "lens": "tension"}') == "null"
        )

    def test_envelope_round_trips_with_pinned_field_order(self) -> None:
        session = _FakeSession(envelope=dict(_ENVELOPE))

        raw = _host(session).choropleth_json('{"tier": "county", "lens": "value"}')

        parsed = json.loads(raw)
        assert list(parsed.keys()) == list(_ENVELOPE.keys())
        assert parsed == _ENVELOPE
        assert session.calls == [("county", "value")]

    def test_inf_crosses_the_wire_as_a_string(self) -> None:
        raw = _host(_FakeSession(envelope=dict(_ENVELOPE))).choropleth_json(
            '{"tier": "county", "lens": "value"}'
        )

        assert '"inf"' in raw
        assert "Infinity" not in raw

    def test_out_of_vocabulary_args_raise_through_the_seam(self) -> None:
        with pytest.raises(ValueError, match="tier"):
            _host(_FakeSession()).choropleth_json('{"tier": "planet", "lens": "value"}')
        with pytest.raises(ValueError, match="lens"):
            _host(_FakeSession()).choropleth_json('{"tier": "county", "lens": "poverty"}')
