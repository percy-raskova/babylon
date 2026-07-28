"""Unit tests for P26 U5d Φ attribution — the ruled σ-composition (Option C).

The reference DB provides the Hickel drain only as a national aggregate, so
this attributes it across engine nodes via the σ-gradient composition rule
(ADR165 Q1; the retired trade-share proxy is superseded, spec-101 D3): each
node's tier (CORE/SEMI_PERIPHERY/PERIPHERY, from the U5a theory ruling) times
its σ gap (Ricci OUTFLOW value_pct_gdp) times its U5c disjoint-partner trade
volume, renormalized to Σ=1.0. These tests pin the pure math
(:mod:`babylon.domain.economics.sigma.attribution`, not modified here) as
consumed by this module's SQLite-reading + composition helpers, without
touching Postgres.
"""

from __future__ import annotations

import csv
import gzip
import sqlite3
from pathlib import Path

import pytest

from babylon.domain.economics.sigma.attribution import (
    TIER_CORE,
    TIER_PERIPHERY,
    TIER_SEMI_PERIPHERY,
)
from babylon.domain.economics.trade_policy import effective_trade
from babylon.persistence.postgres_initialization import (
    _NODE_TIER,
    _NODE_TO_PARTNERS,
    _NODE_TO_RICCI_REGION,
    INTERNATIONAL_NODES,
    PhiAttributionUnavailableError,
    _attribute_phi_by_sigma_composition,
    _derive_w_semi_from_ricci_sample,
    _preflight_hickel_intensive_coverage,
    _read_faf_bloc_tons,
    _read_partner_trade,
    _read_ricci_outflow_pct_gdp,
    _select_nearest_erdi_row,
    _sigma_gap_for_node,
)

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# U5c — the disjoint partner crosswalk.
# ---------------------------------------------------------------------------


def test_partner_crosswalk_is_disjoint() -> None:
    """No dim_country id may appear under two nodes (U5c denominator law)."""
    seen: dict[int, str] = {}
    for node_id, partner_ids in _NODE_TO_PARTNERS.items():
        for country_id in partner_ids:
            assert country_id not in seen, (
                f"country_id={country_id} double-mapped: {seen[country_id]!r} and {node_id!r}"
            )
            seen[country_id] = node_id


def test_partner_crosswalk_covers_all_eight_nodes() -> None:
    assert set(_NODE_TO_PARTNERS) == set(INTERNATIONAL_NODES)


def test_tier_map_covers_all_eight_nodes_with_known_tiers() -> None:
    assert set(_NODE_TIER) == set(INTERNATIONAL_NODES)
    assert set(_NODE_TIER.values()) <= {TIER_CORE, TIER_SEMI_PERIPHERY, TIER_PERIPHERY}


def test_core_nodes_are_eu_and_canada_only() -> None:
    core = {node for node, tier in _NODE_TIER.items() if tier == TIER_CORE}
    assert core == {"eu", "canada"}


def test_russia_csi_tier_remap() -> None:
    """ADR165 Q2/u5a §3 rule 2: russia_csi is re-mapped off the retired CORE
    "Europe" crosswalk target onto its Ricci-native SEMI_PERIPHERY tier."""
    assert _NODE_TIER["russia_csi"] == TIER_SEMI_PERIPHERY
    assert _NODE_TIER["russia_csi"] != TIER_CORE


def test_ricci_region_map_covers_all_eight_nodes() -> None:
    assert set(_NODE_TO_RICCI_REGION) == set(INTERNATIONAL_NODES)


# ---------------------------------------------------------------------------
# _read_partner_trade — SQLite reader.
# ---------------------------------------------------------------------------


def _make_trade_sqlite(tmp_path: Path) -> Path:
    path = tmp_path / "trade.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE dim_time (time_id INTEGER PRIMARY KEY, year INTEGER, is_annual INTEGER);
        CREATE TABLE fact_bilateral_trade_annual (
            time_id INTEGER, country_id INTEGER, total_trade_usd_millions REAL
        );
        """
    )
    conn.execute("INSERT INTO dim_time VALUES (14, 2010, 1)")
    # eu (id 1)
    conn.execute("INSERT INTO fact_bilateral_trade_annual VALUES (14, 1, 500.0)")
    # canada (id 19)
    conn.execute("INSERT INTO fact_bilateral_trade_annual VALUES (14, 19, 200.0)")
    # latin_america (ids 6, 21) — two partner rows summed
    conn.execute("INSERT INTO fact_bilateral_trade_annual VALUES (14, 6, 30.0)")
    conn.execute("INSERT INTO fact_bilateral_trade_annual VALUES (14, 21, 70.0)")
    conn.commit()
    conn.close()
    return path


def test_read_partner_trade_sums_disjoint_partners(tmp_path: Path) -> None:
    path = _make_trade_sqlite(tmp_path)
    out = _read_partner_trade(path, 2010, node_ids=("eu", "canada", "latin_america"))
    assert out == {
        "eu": pytest.approx(500.0),
        "canada": pytest.approx(200.0),
        "latin_america": pytest.approx(100.0),  # 30 + 70
    }


def test_read_partner_trade_no_annual_years_raises_loud(tmp_path: Path) -> None:
    path = tmp_path / "empty.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE dim_time (time_id INTEGER PRIMARY KEY, year INTEGER, is_annual INTEGER);
        CREATE TABLE fact_bilateral_trade_annual (
            time_id INTEGER, country_id INTEGER, total_trade_usd_millions REAL
        );
        """
    )
    conn.commit()
    conn.close()
    with pytest.raises(PhiAttributionUnavailableError):
        _read_partner_trade(path, 2010)


# ---------------------------------------------------------------------------
# Ricci σ-gap reading + nearest-vintage-per-region resolution.
# ---------------------------------------------------------------------------


def _make_ricci_sqlite(tmp_path: Path, rows: list[tuple[int, str, str, str, str, float]]) -> Path:
    """``rows``: (year, region_name, region_type, flow_direction, transfer_type, value_pct_gdp)."""
    path = tmp_path / "ricci.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE fact_ricci_unequal_exchange_gvc (
            ricci_gvc_id INTEGER PRIMARY KEY,
            year INTEGER, region_name TEXT, region_type TEXT,
            flow_direction TEXT, transfer_type TEXT, value_pct_gdp REAL
        );
        """
    )
    for i, row in enumerate(rows):
        conn.execute(
            "INSERT INTO fact_ricci_unequal_exchange_gvc "
            "(ricci_gvc_id, year, region_name, region_type, flow_direction, transfer_type, "
            "value_pct_gdp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (i, *row),
        )
    conn.commit()
    conn.close()
    return path


def test_read_ricci_outflow_prefers_total_over_gvc(tmp_path: Path) -> None:
    path = _make_ricci_sqlite(
        tmp_path,
        [
            (1995, "China", "SEMI_PERIPHERY", "OUTFLOW", "GVC", 7.75),
            (1995, "China", "SEMI_PERIPHERY", "OUTFLOW", "TOTAL", 17.3),
            (1995, "China", "SEMI_PERIPHERY", "INFLOW", "TOTAL", 999.0),  # ignored: not OUTFLOW
        ],
    )
    out = _read_ricci_outflow_pct_gdp(path, "China")
    assert out == {1995: pytest.approx(17.3)}


def test_read_ricci_outflow_null_pct_gdp_skipped(tmp_path: Path) -> None:
    path = tmp_path / "ricci_null.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE fact_ricci_unequal_exchange_gvc (
            ricci_gvc_id INTEGER PRIMARY KEY,
            year INTEGER, region_name TEXT, region_type TEXT,
            flow_direction TEXT, transfer_type TEXT, value_pct_gdp REAL
        );
        """
    )
    conn.execute(
        "INSERT INTO fact_ricci_unequal_exchange_gvc VALUES (0, 2007, 'Non-OECD', 'PERIPHERY', "
        "'OUTFLOW', 'TOTAL', NULL)"
    )
    conn.commit()
    conn.close()
    assert _read_ricci_outflow_pct_gdp(path, "Non-OECD") == {}


def test_sigma_gap_core_node_is_zero_when_no_outflow_rows(tmp_path: Path) -> None:
    path = _make_ricci_sqlite(
        tmp_path,
        [(1995, "Western Europe", "CORE", "INFLOW", "TOTAL", 8.9)],  # CORE never OUTFLOW
    )
    assert _sigma_gap_for_node(path, "eu", 2010) == 0.0


def test_sigma_gap_resolves_nearest_vintage_per_node_region(tmp_path: Path) -> None:
    """Russia and CSI only has a 1995 row — a global 2009-nearest-vintage pick
    would leave it gapless; the per-region resolution must still find it."""
    path = _make_ricci_sqlite(
        tmp_path,
        [
            (1995, "Russia and CSI", "SEMI_PERIPHERY", "OUTFLOW", "TOTAL", 42.2),
            (2009, "Non-OECD", "PERIPHERY", "OUTFLOW", "TOTAL", 37.0),
        ],
    )
    assert _sigma_gap_for_node(path, "russia_csi", 2010) == pytest.approx(42.2)


# ---------------------------------------------------------------------------
# w_semi derivation.
# ---------------------------------------------------------------------------


@pytest.mark.requires_reference_db
def test_derive_w_semi_from_ricci_sample() -> None:
    """Against the REAL checked-in reference DB (all 4 vintages) — pins the
    computed damping coefficient so a future Ricci re-ingestion drift is
    caught (twice-bitten discipline)."""
    w_semi = _derive_w_semi_from_ricci_sample(Path("data/sqlite/marxist-data-3NF.sqlite"))
    assert 0.0 < w_semi < 1.0
    assert w_semi == pytest.approx(0.7395299978197819, rel=1e-9)


def test_derive_w_semi_raises_when_a_tier_sample_is_empty(tmp_path: Path) -> None:
    path = _make_ricci_sqlite(
        tmp_path,
        [(2007, "India", "PERIPHERY", "OUTFLOW", "TOTAL", 17.0)],  # no SEMI_PERIPHERY row at all
    )
    with pytest.raises(PhiAttributionUnavailableError):
        _derive_w_semi_from_ricci_sample(path)


# ---------------------------------------------------------------------------
# _attribute_phi_by_sigma_composition — the pure composition wrapper.
# ---------------------------------------------------------------------------

_TIERS = {
    "eu": TIER_CORE,
    "canada": TIER_CORE,
    "china": TIER_SEMI_PERIPHERY,
    "india": TIER_PERIPHERY,
}


def test_core_nodes_receive_zero_phi() -> None:
    out = _attribute_phi_by_sigma_composition(
        national_phi=1_000.0,
        tiers_by_node=_TIERS,
        trade_by_node={"eu": 500.0, "canada": 300.0, "china": 100.0, "india": 50.0},
        sigma_gap_by_node={"eu": 0.0, "canada": 0.0, "china": 10.0, "india": 17.0},
        w_semi=0.5,
    )
    assert out["eu"][0] == 0.0
    assert out["canada"][0] == 0.0
    # CORE nodes still carry their real trade value (an observational field,
    # untouched by the share computation).
    assert out["eu"][1] == pytest.approx(500.0 * 1e6)
    assert out["canada"][1] == pytest.approx(300.0 * 1e6)


def test_shares_sum_to_one_over_non_core_nodes() -> None:
    national_phi = 1_000.0
    out = _attribute_phi_by_sigma_composition(
        national_phi=national_phi,
        tiers_by_node=_TIERS,
        trade_by_node={"eu": 500.0, "canada": 300.0, "china": 100.0, "india": 50.0},
        sigma_gap_by_node={"eu": 0.0, "canada": 0.0, "china": 10.0, "india": 17.0},
        w_semi=0.5,
    )
    total_phi = sum(phi for phi, _ in out.values())
    assert total_phi == pytest.approx(national_phi, rel=1e-12)  # conservation (Σ=1.0)


def test_hand_computed_periphery_share() -> None:
    """china (SEMI, damped w_semi) and india (PERIPHERY, undamped) — hand
    -computed raw masses: china = 0.5*10*100=500; india = 1*17*50=850;
    total=1350 => india share = 850/1350."""
    national_phi = 1_000.0
    out = _attribute_phi_by_sigma_composition(
        national_phi=national_phi,
        tiers_by_node=_TIERS,
        trade_by_node={"eu": 500.0, "canada": 300.0, "china": 100.0, "india": 50.0},
        sigma_gap_by_node={"eu": 0.0, "canada": 0.0, "china": 10.0, "india": 17.0},
        w_semi=0.5,
    )
    expected_india_share = 850.0 / 1350.0
    assert out["india"][0] == pytest.approx(national_phi * expected_india_share)
    expected_china_share = 500.0 / 1350.0
    assert out["china"][0] == pytest.approx(national_phi * expected_china_share)


def test_attribution_is_deterministic_across_repeated_runs() -> None:
    kwargs: dict[str, object] = {
        "national_phi": 1_000.0,
        "tiers_by_node": _TIERS,
        "trade_by_node": {"eu": 500.0, "canada": 300.0, "china": 100.0, "india": 50.0},
        "sigma_gap_by_node": {"eu": 0.0, "canada": 0.0, "china": 10.0, "india": 17.0},
        "w_semi": 0.5,
    }
    first = _attribute_phi_by_sigma_composition(**kwargs)  # type: ignore[arg-type]
    second = _attribute_phi_by_sigma_composition(**kwargs)  # type: ignore[arg-type]
    assert first == second


def test_zero_total_attributable_mass_raises_loud() -> None:
    """Every node CORE-tier or gapless => zero attributable mass; must fail
    loud (III.8), matching the prior trade-share attribution's discipline."""
    with pytest.raises(PhiAttributionUnavailableError):
        _attribute_phi_by_sigma_composition(
            national_phi=1_000.0,
            tiers_by_node={"eu": TIER_CORE, "canada": TIER_CORE},
            trade_by_node={"eu": 500.0, "canada": 300.0},
            sigma_gap_by_node={"eu": 0.0, "canada": 0.0},
            w_semi=0.5,
        )


def test_tariff_seam_changes_shares() -> None:
    """A nonzero tariff on one node dampens its effective trade, shifting
    the renormalized shares (P26 U5f, ADR165 tariff directive)."""
    raw_trade = {"eu": 500.0, "canada": 300.0, "china": 100.0, "india": 50.0}
    gaps = {"eu": 0.0, "canada": 0.0, "china": 10.0, "india": 17.0}

    baseline = _attribute_phi_by_sigma_composition(
        national_phi=1_000.0,
        tiers_by_node=_TIERS,
        trade_by_node=raw_trade,
        sigma_gap_by_node=gaps,
        w_semi=0.5,
    )
    dampened_trade = effective_trade(raw_trade, {"india": 0.5}, dampening=1.0)
    assert dampened_trade["india"] == pytest.approx(25.0)  # halved
    tariffed = _attribute_phi_by_sigma_composition(
        national_phi=1_000.0,
        tiers_by_node=_TIERS,
        trade_by_node=dampened_trade,
        sigma_gap_by_node=gaps,
        w_semi=0.5,
    )
    assert tariffed["india"][0] < baseline["india"][0]
    # Default-inert law: a zero tariff_rates map leaves shares unchanged.
    inert_trade = effective_trade(raw_trade, {}, dampening=1.0)
    assert inert_trade == raw_trade


# ---------------------------------------------------------------------------
# ERDI fix (ADR165 Q7).
# ---------------------------------------------------------------------------


def test_select_nearest_erdi_row_exact_year() -> None:
    rows = [(2009, 7.47), (2010, 7.6), (2011, 7.73)]
    assert _select_nearest_erdi_row(rows, 2010) == pytest.approx(7.6)


def test_select_nearest_erdi_row_nearest_below_when_year_absent() -> None:
    """Fixture shaped exactly like the real Hickel 'Intensive' series
    (nonzero, monotone by year) — the ERDI fix must return a REAL value,
    never the old dead 1.0 default, for any year within the fixture's span."""
    rows = [(2006, 7.08), (2007, 7.21), (2008, 7.34), (2009, 7.47), (2010, 7.6)]
    assert _select_nearest_erdi_row(rows, 2020) == pytest.approx(7.6)
    assert _select_nearest_erdi_row(rows, 2007) == pytest.approx(7.21)


def test_select_nearest_erdi_row_empty_falls_back_to_neutral() -> None:
    assert _select_nearest_erdi_row([], 2010) == 1.0


# ---------------------------------------------------------------------------
# Hickel coverage preflight — unchanged from spec-101, re-pinned here.
# ---------------------------------------------------------------------------


def _make_hickel_sqlite(tmp_path: Path, *, years: list[int]) -> Path:
    path = tmp_path / "hickel.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE dim_time (time_id INTEGER PRIMARY KEY, year INTEGER, is_annual INTEGER);
        CREATE TABLE fact_hickel_erdi_annual (
            id INTEGER PRIMARY KEY, time_id INTEGER, scale_type TEXT,
            erdi REAL, annual_drain_usd_billions REAL
        );
        """
    )
    for i, year in enumerate(years):
        conn.execute("INSERT INTO dim_time VALUES (?, ?, 1)", (i, year))
        conn.execute(
            "INSERT INTO fact_hickel_erdi_annual (time_id, scale_type, erdi, "
            "annual_drain_usd_billions) VALUES (?, 'Intensive', 1.0, 100.0)",
            (i,),
        )
    conn.commit()
    conn.close()
    return path


def test_hickel_coverage_preflight_raises_outside_window(tmp_path: Path) -> None:
    """Spec-101 review fix #2: start_year=2020 is outside the verified

    1980-2017 'Intensive' coverage — must fail loud, not let
    ``_fetch_national_phi`` read back its silent 0.0 fallback.
    """
    path = _make_hickel_sqlite(tmp_path, years=[1980, 2017])
    with pytest.raises(PhiAttributionUnavailableError):
        _preflight_hickel_intensive_coverage(sqlite_path=path, start_year=2020)


def test_hickel_coverage_preflight_passes_inside_window(tmp_path: Path) -> None:
    path = _make_hickel_sqlite(tmp_path, years=[1980, 2010, 2017])
    _preflight_hickel_intensive_coverage(sqlite_path=path, start_year=2010)  # no raise


def test_hickel_coverage_preflight_raises_when_no_intensive_rows(tmp_path: Path) -> None:
    path = _make_hickel_sqlite(tmp_path, years=[])
    with pytest.raises(PhiAttributionUnavailableError):
        _preflight_hickel_intensive_coverage(sqlite_path=path, start_year=2010)


# ---------------------------------------------------------------------------
# Program 26 U3 — FAF freight-tons bootstrap stamping (fake artifact rows).
# Unchanged from the prior lane — bilateral_trade_tons is independent of the
# σ-composition attribution (its own artifact, its own read path).
# ---------------------------------------------------------------------------


def _write_fake_faf_artifact(path: Path, rows: list[tuple[str, int, float]]) -> None:
    with gzip.open(path, mode="wt", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["node_id", "year", "tons"])
        for node_id, year, tons in rows:
            writer.writerow([node_id, year, tons])


def test_read_faf_bloc_tons_covered_year(tmp_path: Path) -> None:
    artifact = tmp_path / "faf.csv.gz"
    _write_fake_faf_artifact(
        artifact,
        [
            ("canada", 2018, 613124.6),
            ("canada", 2019, 623131.4),
            ("eu", 2018, 301882.0),
        ],
    )
    out = _read_faf_bloc_tons(year=2018, artifact_path=artifact)
    assert out == {"canada": pytest.approx(613124.6), "eu": pytest.approx(301882.0)}


def test_read_faf_bloc_tons_outside_coverage_window_logs_and_returns_empty(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Spec-101 ADR055 no-fabrication precedent: a start_year outside the
    artifact's 2018-2024 coverage must NOT fabricate tons — one loud log
    line naming the coverage window, empty dict (every node falls back to
    0.0 at the call site)."""
    artifact = tmp_path / "faf.csv.gz"
    _write_fake_faf_artifact(artifact, [("canada", 2018, 613124.6)])
    with caplog.at_level("WARNING"):
        out = _read_faf_bloc_tons(year=2010, artifact_path=artifact)
    assert out == {}
    assert any("2018" in r.message and "2024" in r.message for r in caplog.records)


def test_read_faf_bloc_tons_missing_artifact_file_returns_empty(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "does-not-exist.csv.gz"
    with caplog.at_level("WARNING"):
        out = _read_faf_bloc_tons(year=2020, artifact_path=missing)
    assert out == {}
    assert len(caplog.records) == 1


def test_read_faf_bloc_tons_real_checked_in_artifact_canada_2018() -> None:
    """Bootstrap-stamping proof against the REAL checked-in artifact
    (default ``artifact_path``): the exact FAF-computed pinned value for
    canada/2018 comes back, matching what ``_bootstrap_external_nodes``
    would stamp onto ``ExternalNode.bilateral_trade_tons``."""
    out = _read_faf_bloc_tons(year=2018)
    assert out["canada"] == pytest.approx(613124.597691, rel=1e-9)
    assert "india" not in out
    assert "russia_csi" not in out


# ---------------------------------------------------------------------------
# Real-DB end-to-end sanity (deliverable report numbers) — the live
# reference DB, start_year=2010, exercising the full read+attribute chain.
# ---------------------------------------------------------------------------


@pytest.mark.requires_reference_db
def test_real_db_2010_attribution_matches_pinned_numbers() -> None:
    """Regression pin against the checked-in reference DB: if Ricci/Census
    re-ingestion ever drifts these inputs, this test catches it loudly
    rather than silently shipping a different attribution."""
    sqlite_path = Path("data/sqlite/marxist-data-3NF.sqlite")
    national_phi = 8.625e12  # 2010 Hickel 'Intensive' annual_drain_usd_billions=8625.0

    trade = _read_partner_trade(sqlite_path, 2010)
    gaps = {n: _sigma_gap_for_node(sqlite_path, n, 2010) for n in INTERNATIONAL_NODES}
    w_semi = _derive_w_semi_from_ricci_sample(sqlite_path)
    tiers = {n: _NODE_TIER[n] for n in INTERNATIONAL_NODES}

    out = _attribute_phi_by_sigma_composition(
        national_phi=national_phi,
        tiers_by_node=tiers,
        trade_by_node=trade,
        sigma_gap_by_node=gaps,
        w_semi=w_semi,
    )

    assert out["eu"][0] == 0.0
    assert out["canada"][0] == 0.0
    total_phi = sum(phi for phi, _ in out.values())
    assert total_phi == pytest.approx(national_phi, rel=1e-9)

    # Pinned shares (see the U5d stage-2 report for the full derivation).
    assert out["latin_america"][0] / national_phi == pytest.approx(0.671818, abs=1e-5)
    assert out["china"][0] / national_phi == pytest.approx(0.100758, abs=1e-5)
    assert out["india"][0] / national_phi == pytest.approx(0.022689, abs=1e-5)
