"""P26 U6 phase 2 — live trade-dossier markdown rendering (Textual client).

Contract: ``specs/103-trade-surfaces/u6-archive-trade-surfaces-contracts.md``
Contract 3 (phase 2). :func:`~babylon.tui.trade_dossier.render_trade_page`
is a pure function over :class:`~babylon.projection.view_models.
TradeBlocView` — these tests pin its markdown shape directly, independent of
the session/app wiring (:mod:`tests.unit.game.test_session_trade`/
:mod:`tests.unit.tui.test_trade_reachability` pin those seams).
"""

from __future__ import annotations

from babylon.projection.trade import project_trade_bloc, project_trade_overview
from babylon.tui.trade_dossier import render_trade_page

_PHI = {"canada": 100_000_000.0, "china": 300_000_000.0}
_EXPOSURE = {
    "canada": {"26163": 0.6, "26125": 0.4},
    "china": {"26163": 1.0},
}


def test_overview_page_carries_the_national_statblock_and_breakdown_table() -> None:
    view = project_trade_overview(
        external_nodes_phi=_PHI,
        county_exposure_by_external=_EXPOSURE,
        weeks_per_year=52,
        last_flows={"canada": 10.0, "china": 20.0},
        tick=9,
    )

    page = render_trade_page(view)

    assert "id: trade/overview" in page
    assert "verified_tick: 9" in page
    assert "# trade/overview — National Trade Overview" in page
    assert "```{statblock} trade/overview" in page
    assert "phi_year_inflow: 400000000.000000" in page
    assert "last_tick_flow: 30.000000" in page
    assert "## Per-bloc breakdown (Φ DESC)" in page
    # Φ DESC order preserved from the projector.
    china_row = page.index("[[trade/china]]")
    canada_row = page.index("[[trade/canada]]")
    assert china_row < canada_row
    assert "| [[trade/china]] | 300000000.000000 |" in page
    assert "| [[trade/canada]] | 100000000.000000 |" in page
    # Overview carries no exposure section (that's a per-bloc concern).
    assert "## Top county exposure" not in page


def test_overview_page_with_no_flow_this_tick_renders_an_absence_fence() -> None:
    view = project_trade_overview(
        external_nodes_phi=_PHI,
        county_exposure_by_external=_EXPOSURE,
        weeks_per_year=52,
        last_flows={},
        tick=0,
    )

    page = render_trade_page(view)

    assert "```{absence} last_tick_flow — Advance(Tick)" in page


def test_bloc_page_carries_phi_and_top_exposure_rows_weight_desc() -> None:
    view = project_trade_bloc(
        "canada",
        external_nodes_phi=_PHI,
        county_exposure_by_external=_EXPOSURE,
        weeks_per_year=52,
        last_flows={"canada": 1_923_076.92},
        tick=7,
    )
    assert view is not None

    page = render_trade_page(view)

    assert "id: trade/canada" in page
    assert "# trade/canada — Bloc Dossier — canada" in page
    assert "```{statblock} trade/canada" in page
    assert "phi_year_inflow: 100000000.000000" in page
    assert "phi_week_slice:" in page
    assert "last_tick_flow: 1923076.920000" in page
    assert "## Top county exposure" in page
    heavy_row = page.index("| 26163 | 0.600000 |")
    light_row = page.index("| 26125 | 0.400000 |")
    assert heavy_row < light_row
    assert "Back to [[trade/overview]]." in page
    # Bloc page carries no national breakdown table.
    assert "## Per-bloc breakdown" not in page


def test_bloc_page_absent_optional_fields_render_named_remedies() -> None:
    """``bilateral_trade_value``/``bilateral_trade_tons``/``erdi_ratio`` are
    never populated in phase 1/2 (post-U3 data) — every present call site
    renders their absence with a named remedy, never a fabricated zero."""
    view = project_trade_bloc(
        "canada",
        external_nodes_phi={"canada": 0.0},
        county_exposure_by_external={},
        weeks_per_year=52,
        last_flows={},
        tick=1,
    )
    assert view is not None

    page = render_trade_page(view)

    assert "```{absence} bilateral_trade_value — Attribute(BilateralTrade)" in page
    assert "```{absence} bilateral_trade_tons — Attribute(FreightTons)" in page
    assert "```{absence} erdi_ratio — Compute(ERDI)" in page
    assert "```{absence} last_tick_flow — Advance(Tick)" in page
    assert "```{absence} exposure_top — Wire(CountyExposure)" in page
    assert "## Top county exposure" in page  # section still renders, as an absence block


def test_page_is_a_pure_deterministic_function_of_the_view() -> None:
    """Two calls with an equal view yield byte-identical output — no
    wall-clock, no randomness (mirrors ``render_county``'s own determinism
    contract, Constitution III.13)."""
    view = project_trade_bloc(
        "canada",
        external_nodes_phi=_PHI,
        county_exposure_by_external=_EXPOSURE,
        weeks_per_year=52,
        last_flows={},
        tick=3,
    )
    assert view is not None

    assert render_trade_page(view) == render_trade_page(view.model_copy())
