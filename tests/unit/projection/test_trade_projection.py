"""P26 U6 phase 1 — trade projections (contract:
``specs/103-trade-surfaces/u6-archive-trade-surfaces-contracts.md``).

Written RED first (TDD). Pins the client-agnostic backend seam: a
``TradeBlocView`` (``kind="trade"``) joins the ``ProjectionRecord``
discriminated union, projected by pure functions over plain session-held
data — no ``babylon.game`` import (layering: game imports projection,
never the reverse), no graph/world dependency, honest ``None`` for every
absent input (the ``project_county`` documented shape).
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter

from babylon.projection.trade import project_trade_bloc, project_trade_overview
from babylon.projection.view_models import ProjectionRecord, TradeBlocView

_PHI = {"canada": 100_000_000.0, "china": 300_000_000.0}
_EXPOSURE = {
    "canada": {"26163": 0.6, "26125": 0.4},
    "china": {"26163": 1.0},
}


def test_project_trade_bloc_projects_phi_slice_exposure_and_flow() -> None:
    view = project_trade_bloc(
        "canada",
        external_nodes_phi=_PHI,
        county_exposure_by_external=_EXPOSURE,
        weeks_per_year=52,
        last_flows={"canada": 1_923_076.92},
        tick=7,
    )

    assert view is not None
    assert view.kind == "trade"
    assert view.node_id == "canada"
    assert view.verified_tick == 7
    assert view.phi_year_inflow == 100_000_000.0
    assert view.phi_week_slice == pytest.approx(100_000_000.0 / 52.0)
    assert view.last_tick_flow == pytest.approx(1_923_076.92)
    # Exposure rows sorted by weight DESC then FIPS for determinism.
    assert view.exposure_top is not None
    assert [(r.county_fips, r.weight) for r in view.exposure_top] == [
        ("26163", 0.6),
        ("26125", 0.4),
    ]
    assert view.breakdown is None  # per-bloc view carries no national fold


def test_project_trade_bloc_unknown_node_is_honest_absence() -> None:
    view = project_trade_bloc(
        "atlantis",
        external_nodes_phi=_PHI,
        county_exposure_by_external=_EXPOSURE,
        weeks_per_year=52,
        last_flows={},
        tick=1,
    )
    assert view is None


def test_project_trade_bloc_missing_optional_inputs_hydrate_to_none() -> None:
    """A node with Φ but no exposure row and no flow this tick projects
    honest ``None``s, never fabricated zeros (Constitution III.8)."""
    view = project_trade_bloc(
        "canada",
        external_nodes_phi={"canada": 0.0},
        county_exposure_by_external={},
        weeks_per_year=52,
        last_flows={},
        tick=1,
    )
    assert view is not None
    assert view.phi_year_inflow == 0.0
    assert view.exposure_top is None
    assert view.last_tick_flow is None


def test_project_trade_overview_folds_the_national_view() -> None:
    view = project_trade_overview(
        external_nodes_phi=_PHI,
        county_exposure_by_external=_EXPOSURE,
        weeks_per_year=52,
        last_flows={"canada": 10.0, "china": 20.0},
        tick=9,
    )

    assert view.kind == "trade"
    assert view.node_id == "overview"
    assert view.verified_tick == 9
    assert view.phi_year_inflow == pytest.approx(400_000_000.0)  # national total
    assert view.last_tick_flow == pytest.approx(30.0)
    assert view.breakdown is not None
    # Deterministic order: phi DESC then node_id.
    assert [(r.node_id, r.phi_year_inflow) for r in view.breakdown] == [
        ("china", 300_000_000.0),
        ("canada", 100_000_000.0),
    ]


def test_trade_bloc_view_is_a_projection_record_kind() -> None:
    """The union actually dispatches ``kind="trade"`` — a serialized view
    round-trips through the discriminated ``ProjectionRecord`` adapter."""
    view = project_trade_overview(
        external_nodes_phi=_PHI,
        county_exposure_by_external=_EXPOSURE,
        weeks_per_year=52,
        last_flows={},
        tick=0,
    )
    adapter: TypeAdapter[ProjectionRecord] = TypeAdapter(ProjectionRecord)
    round_tripped = adapter.validate_python(view.model_dump())
    assert isinstance(round_tripped, TradeBlocView)
    assert round_tripped == view
