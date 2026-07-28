"""Contract tests for the per-county fog-status rollup (the fog lens producer).

One epistemic verdict per county: ``"exact"`` inside organizing reach (reach
wins outright — the same precedence rule ``apply_fog`` enforces per field),
else the intel ledger's aged tier via ``read_intel`` over the
``territory:political`` field group. A genuinely-existing county with no data
still gets a keyed, explicit ``"unknown"`` — never omitted, never a stale
color (spec-117 §5a / Constitution III.11). Territories without a
``county_fips`` have no county identity and are never emitted.
"""

from __future__ import annotations

import pytest

from babylon.models.enums import NodeType
from babylon.projection.fog.ledger import IntelEntry, IntelLedger
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit

_STALENESS = 5
_UNKNOWN = 20


def _graph() -> BabylonGraph:
    """ORG1 has presence in T1 (county 26163). T2 (01001) and T3 (02002) are
    out of reach; TX carries no county_fips at all."""
    g = BabylonGraph()
    g.add_node("ORG1", NodeType.ORGANIZATION, name="Player Org")
    g.add_node("T1", NodeType.TERRITORY, name="Wayne", county_fips="26163")
    g.add_node("T2", NodeType.TERRITORY, name="Autauga", county_fips="01001")
    g.add_node("T3", NodeType.TERRITORY, name="Anchorage", county_fips="02002")
    g.add_node("TX", NodeType.TERRITORY, name="Abstract")
    g.add_edge("ORG1", "T1", "presence")
    return g


def _ledger(node_id: str, tick_observed: int) -> IntelLedger:
    return IntelLedger(
        entries=(
            IntelEntry(
                node_id=node_id,
                field_group="territory:political",
                tick_observed=tick_observed,
                value_snapshot={"heat": 0.4},
            ),
        )
    )


def _status(ledger: IntelLedger, tick: int, player_org_id: str | None = "ORG1") -> dict[str, str]:
    from babylon.projection.fog.county_status import county_fog_status

    return county_fog_status(
        _graph(),
        player_org_id,
        ledger,
        tick,
        radius=1,
        staleness_ticks=_STALENESS,
        unknown_ticks=_UNKNOWN,
    )


class TestCountyFogStatus:
    """Contract of ``county_fog_status(...) -> dict[county_fips, tier]``."""

    def test_in_reach_county_is_exact(self) -> None:
        assert _status(IntelLedger(), tick=100)["26163"] == "exact"

    def test_never_observed_out_of_reach_county_is_keyed_unknown(self) -> None:
        """Present in the dict with an explicit \"unknown\" — never omitted."""
        status = _status(IntelLedger(), tick=100)

        assert status["01001"] == "unknown"
        assert status["02002"] == "unknown"

    def test_fresh_intel_is_exact(self) -> None:
        status = _status(_ledger("T2", tick_observed=98), tick=100)

        assert status["01001"] == "exact"

    def test_stale_intel_is_approximate(self) -> None:
        status = _status(_ledger("T2", tick_observed=90), tick=100)

        assert status["01001"] == "approximate"

    def test_ancient_intel_is_unknown(self) -> None:
        status = _status(_ledger("T2", tick_observed=10), tick=100)

        assert status["01001"] == "unknown"

    def test_reach_wins_over_any_ledger_state(self) -> None:
        """T1 is in reach; even ancient intel about it cannot demote it."""
        status = _status(_ledger("T1", tick_observed=0), tick=100)

        assert status["26163"] == "exact"

    def test_no_player_org_falls_back_to_pure_ledger_aging(self) -> None:
        """player_org_id=None -> empty reach (the reach primitive's own
        sentinel) -> every county is judged by the ledger alone."""
        status = _status(_ledger("T2", tick_observed=98), tick=100, player_org_id=None)

        assert status["26163"] == "unknown"
        assert status["01001"] == "exact"

    def test_territory_without_county_fips_is_never_emitted(self) -> None:
        status = _status(IntelLedger(), tick=100)

        assert set(status) == {"26163", "01001", "02002"}

    def test_empty_graph_returns_empty_dict(self) -> None:
        from babylon.projection.fog.county_status import county_fog_status

        assert (
            county_fog_status(
                BabylonGraph(),
                None,
                IntelLedger(),
                0,
                radius=1,
                staleness_ticks=_STALENESS,
                unknown_ticks=_UNKNOWN,
            )
            == {}
        )
