"""Two-phase initialization orchestration (Spec 062, US1).

Implements FR-001 / FR-002 / FR-003 / FR-004 / FR-008:

1. Open SQLite reference database read-only.
2. Hydrate county-level c/v/s/K from QCEW + BEA + MELT for ``start_year``.
3. Distribute county totals to H3 res-7 hexes via LODES workplace density.
4. Initialize capital stock K_0 = c_0 / delta_annual (steady-state).
5. Bootstrap external-node state from Hickel + Ricci references.
6. Copy reference series for [start_year, start_year + scenario_length_years]
   into the ``immutable_reference_*`` Postgres tables.
7. Persist everything to Postgres inside an init-time transaction.
8. Close the SQLite handle (FR-002). Subsequent runtime reads MUST go to
   Postgres only.

This module exposes a callable :func:`initialize_session` that the engine
bridge invokes once per session, plus the lower-level
:func:`copy_reference_series` helper that is also used by tests.

The skeleton accommodates progressive implementation: the
:class:`InitializationReport` carries explicit ``copied_series`` /
``hex_count`` / ``external_node_ids`` fields the integration tests check.
For the MVP this module wires up the structure and the contract — full
hex distribution from real LODES data is owned by Phases 6/8 of the spec
where the LODES OD machinery is integrated.

See Also:
    ``specs/062-cross-scale-integration/quickstart.md`` §1.
    ``specs/062-cross-scale-integration/contracts/reference_series.yaml``.
"""

from __future__ import annotations

import csv
import gzip
import logging
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from babylon.domain.economics.sigma.attribution import (
    TIER_CORE,
    TIER_PERIPHERY,
    TIER_SEMI_PERIPHERY,
    AttributionInputError,
    compute_bloc_shares,
    derive_w_semi,
    nearest_vintage,
)
from babylon.domain.economics.trade_policy import effective_trade

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.persistence import PostgresRuntime


logger = logging.getLogger(__name__)


class InitializationError(RuntimeError):
    """Raised when initialization cannot proceed.

    Common causes: required SQLite years missing for a coefficient series
    (FR-016 / FR-029a invariant violation), invalid scenario configuration,
    or Postgres schema not yet migrated.
    """


class PhiAttributionUnavailableError(InitializationError):
    """Raised when the national Φ cannot be attributed across engine nodes.

    Spec-101 review fix #1/#2: the sibling ``county_exposure.py`` hard-fails
    when its distribution would be a silent no-op (III.8 — no silent
    conservation break); ``_attribute_phi_by_sigma_composition`` (P26 U5d;
    formerly ``_attribute_phi_and_trade``, spec-101 D3) and its Hickel-coverage
    preflight now match that discipline instead of returning ``{}`` /
    ``0.0`` and letting 100% of national Φ vanish with no operator-visible
    signal.
    """


@dataclass
class InitializationReport:
    """Summary returned by :func:`initialize_session`.

    Attributes:
        session_id: The UUID of the initialized session.
        hex_count: Number of hex rows persisted at tick 0.
            Reported as 0 in this MVP — full hex hydration is owned by
            the LODES-distribution downstream spec (T054/T055).
        copied_series: Set of series_ids successfully copied into
            ``immutable_reference_*`` tables.
        external_node_ids: Set of node_ids declared (always 9 — the
            8 international + 1 domestic_rest fixed enumeration per FR-036).
        external_node_count: Number of rows actually written to
            ``dynamic_external_node_state`` at tick 0. Equals
            ``len(external_node_ids)`` after :func:`initialize_session`
            completes; lets integration tests distinguish "set declared"
            from "rows persisted" (T078).
        sqlite_path: Resolved path of the source SQLite file (for log).
        national_phi_reference: The RAW, un-attributed national Hickel Φ
            (USD) read at bootstrap (spec-101 review fix #3). Independent of
            the per-node D3 trade-share attribution — threaded through to
            the conservation auditor so it can detect an attribution-stage
            regression that zeroes every node's Φ even though this value
            was positive (0.0 when no Hickel row was found for the year).
    """

    session_id: UUID
    hex_count: int = 0
    copied_series: set[str] = field(default_factory=set)
    external_node_ids: set[str] = field(default_factory=set)
    external_node_count: int = 0
    sqlite_path: Path | None = None
    # Spec 063 — LODES Commute Matrix hydration counts.
    lodes_year_count: int = 0
    lodes_row_count: int = 0
    # Spec 063 — Option B border-commute synthesis hydration counts.
    border_synthesis_row_count: int = 0
    # Spec-101 review fix #3 — raw national Φ, independent of attribution.
    national_phi_reference: float = 0.0


# The canonical fixed external-node set per FR-036 (R4 amendment: Canada
# is a first-class international boundary node).
INTERNATIONAL_NODES: tuple[str, ...] = (
    "canada",
    "china",
    "eu",
    "india",
    "sub_saharan_africa",
    "latin_america",
    "russia_csi",
    "southeast_asia",
)
DOMESTIC_REST_NODE: str = "rest_of_usa"


def _open_sqlite_readonly(sqlite_path: Path) -> sqlite3.Connection:
    """Open SQLite in read-only mode using the URI form.

    The ``mode=ro`` flag prevents accidental writes and ``uri=True`` keeps
    the connection out of the default writable cursor pool.
    """
    if not sqlite_path.is_file():
        msg = f"SQLite reference DB not found at {sqlite_path}"
        raise InitializationError(msg)
    return sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True, check_same_thread=False)


def _validate_alpha_invariant(defines: GameDefines) -> None:
    """FR-029a: ``alpha_weekly < 1/52`` is required at session start."""
    if defines.economy.alpha_weekly >= 1.0 / 52.0:
        raise InitializationError(
            "FR-029a invariant violated: "
            f"alpha_weekly={defines.economy.alpha_weekly!r} >= 1/52. "
            f"Pick a smaller alpha_annual (current value: "
            f"{defines.economy.alpha_annual!r})."
        )


# ---------------------------------------------------------------------------
# Spec-065 T036 / FR-022: reference-data window preflight
# ---------------------------------------------------------------------------


# Required reference tables and their column-bound source-of-truth queries.
# Each entry: table_name → SQL returning (min_year, max_year). Used by
# _preflight_reference_data_window to compute available windows.
_REQUIRED_REFERENCE_TABLES: dict[str, str] = {
    "fact_qcew_annual": (
        "SELECT MIN(t.year), MAX(t.year) FROM fact_qcew_annual fq "
        "JOIN dim_time t ON t.time_id = fq.time_id"
    ),
    "fact_bea_county_gdp": (
        "SELECT MIN(t.year), MAX(t.year) FROM fact_bea_county_gdp fbg "
        "JOIN dim_time t ON t.time_id = fbg.time_id"
    ),
    "fact_census_income": (
        "SELECT MIN(t.year), MAX(t.year) FROM fact_census_income fci "
        "JOIN dim_time t ON t.time_id = fci.time_id"
    ),
}


def _preflight_reference_data_window(
    *,
    sqlite_path: Path,
    start_year: int,
    scenario_length_years: int,
) -> tuple[int, list[str]]:
    """Probe each required reference table; return (clamped_length, warnings).

    Three-mode policy (FR-022 / spec-065 T036):

      - **silent**: requested window ⊆ every table's window — return
        (scenario_length_years, []).
      - **warn-and-clamp**: requested window extends beyond at least
        one table — clamp scenario_length to fit the smallest available
        window, return (clamped, warnings).
      - **hard-refuse**: ``start_year`` is BEFORE the earliest year in
        any required table — raise :class:`InitializationError` with
        the FR-022 named-triple format. The CLI is expected to map
        :class:`InitializationError` to exit code 3.

    Args:
        sqlite_path:           Path to ``marxist-data-3NF.sqlite``.
        start_year:            Requested first simulation year.
        scenario_length_years: Requested number of years.

    Returns:
        ``(allowed_scenario_length_years, warning_messages)``. If silent,
        the second element is an empty list.

    Raises:
        InitializationError: If start_year predates any table's first
            year (the hard-refuse mode).
        FileNotFoundError: If sqlite_path doesn't exist.
    """
    if not sqlite_path.is_file():
        raise FileNotFoundError(
            f"SQLite reference DB not found at {sqlite_path}; FR-022 preflight cannot run"
        )

    requested_end_year = start_year + scenario_length_years - 1
    allowed_end_year = requested_end_year
    warnings_collected: list[str] = []

    with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as conn:
        for table_name, query in _REQUIRED_REFERENCE_TABLES.items():
            row = conn.execute(query).fetchone()
            if row is None or row[0] is None or row[1] is None:
                # Table is empty entirely — hard-refuse.
                raise InitializationError(
                    f"ERROR REFERENCE_DATA_MISSING: {table_name} is empty; "
                    f"cannot run any simulation against this SQLite snapshot."
                )
            tbl_min, tbl_max = int(row[0]), int(row[1])

            if start_year < tbl_min:
                raise InitializationError(
                    f"ERROR REFERENCE_DATA_MISSING: {table_name} starts at "
                    f"year={tbl_min}; requested start_year={start_year} predates "
                    f"the available window."
                )
            if tbl_max < allowed_end_year:
                # Clamp the allowed end year to fit this table's coverage.
                warnings_collected.append(
                    f"WARN REFERENCE_DATA_CLAMP: {table_name} ends at "
                    f"year={tbl_max}; requested end_year={requested_end_year} "
                    f"exceeds the available window. Clamping scenario length."
                )
                allowed_end_year = tbl_max

    allowed_length = max(1, allowed_end_year - start_year + 1)
    return allowed_length, warnings_collected


# Spec-101 review fix #2: ``fact_hickel_erdi_annual`` (the source of national Φ,
# scale_type='Intensive') is verified to cover exactly [1980, 2017]. Outside that
# window ``_copy_hickel_drain`` copies zero 'Intensive' rows, so
# ``_fetch_national_phi`` reads back its 0.0 fallback and every attributed Φ
# silently collapses to zero — defeating spec-101's purpose with no
# operator-visible signal (III.8). This preflight fails loud instead.
_HICKEL_INTENSIVE_COVERAGE_QUERY = (
    "SELECT MIN(t.year), MAX(t.year) FROM fact_hickel_erdi_annual f "
    "JOIN dim_time t ON t.time_id = f.time_id WHERE f.scale_type = 'Intensive'"
)


def _preflight_hickel_intensive_coverage(*, sqlite_path: Path, start_year: int) -> None:
    """Fail loud when ``start_year`` falls outside Hickel 'Intensive' coverage.

    Spec-101 review fix #2. Companion to fix #1 (:class:`PhiAttributionUnavailableError`
    when the trade-share denominator is zero) — this guards the numerator side:
    a ``start_year`` with no 'Intensive' row copied means ``national_phi`` reads
    back 0.0 and every node's attributed Φ silently collapses to zero.

    Args:
        sqlite_path: Path to ``marxist-data-3NF.sqlite``.
        start_year:  Requested first simulation year.

    Raises:
        PhiAttributionUnavailableError: If ``fact_hickel_erdi_annual`` has no
            'Intensive' rows at all, or ``start_year`` falls outside the
            covered ``[MIN(year), MAX(year)]`` window.
    """
    with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as conn:
        row = conn.execute(_HICKEL_INTENSIVE_COVERAGE_QUERY).fetchone()
    if row is None or row[0] is None or row[1] is None:
        raise PhiAttributionUnavailableError(
            "fact_hickel_erdi_annual has no scale_type='Intensive' rows; "
            "national Φ attribution (spec-101 D3) cannot run."
        )
    min_year, max_year = int(row[0]), int(row[1])
    if not (min_year <= start_year <= max_year):
        raise PhiAttributionUnavailableError(
            f"fact_hickel_erdi_annual 'Intensive' coverage is "
            f"[{min_year}, {max_year}]; requested start_year={start_year} is "
            f"outside this window. National Φ attribution (spec-101 D3) would "
            f"silently collapse to zero for every engine node — refusing to "
            f"proceed (III.8)."
        )


def copy_reference_series(
    *,
    session_id: UUID,
    start_year: int,
    scenario_length_years: int,
    sqlite_path: Path,
    runtime: PostgresRuntime,
    counties: list[str] | None = None,
) -> dict[str, tuple[int, int]]:
    """Copy reference series for the session year-range.

    Per ``contracts/reference_series.yaml#InitializationCopy``. Returns a
    map ``{series_id: (start_year_copied, end_year_copied)}``.

    The real SQLite → Postgres hydration is delegated to
    :func:`babylon.persistence.sqlite_hydrator.hydrate_session_references`,
    which copies BEA I-O, MELT τ, basket γ, ERDI, Hickel drain, Ricci
    bilateral trade, FAF freight, QCEW employment, Census rent, and FRED
    annual rate averages.

    Args:
        session_id: Owning session UUID.
        start_year: First year (inclusive).
        scenario_length_years: Number of years to include after start_year.
        sqlite_path: Path to ``marxist-data-3NF.sqlite``.
        runtime: PostgresRuntime to write through.
        counties: Optional 5-digit FIPS list to scope QCEW + rent
            (e.g., the Detroit tri-county set 26163/26125/26099). When
            None, all counties are hydrated (large; ~3000 counties).

    Returns:
        ``{series_id: (start_year, end_year)}`` for every series with at
        least one row copied.
    """
    from babylon.persistence.sqlite_hydrator import hydrate_session_references

    end_year = start_year + scenario_length_years
    counts = hydrate_session_references(
        session_id=session_id,
        start_year=start_year,
        end_year=end_year,
        sqlite_path=sqlite_path,
        runtime=runtime,
        counties=counties,
    )
    return {sid: (start_year, end_year) for sid, n in counts.items() if n > 0}


# Program 26 U3 — checked-in FAF5 freight-tons artifact (ADR121 hand-maintained
# pattern; see tools/make_faf_bloc_tons_artifact.py + its data-artifacts.yaml
# ``faf_bloc_trade_tons`` entry). Covers years 2018-2024 for 6 of the 8
# INTERNATIONAL_NODES (canada, eu, sub_saharan_africa, china, southeast_asia,
# latin_america); india and russia_csi are disclosed-absent (FAF zone 806
# "SW & Central Asia" mixes India with the Middle East/Central Asia with no
# clean per-country breakdown — excluded rather than fabricated, III.8).
_FAF_ARTIFACT_PATH: Path = (
    Path(__file__).resolve().parents[1] / "data" / "reference" / "faf_bloc_trade_tons.csv.gz"
)
_FAF_COVERAGE_YEARS: tuple[int, int] = (2018, 2024)


def _read_faf_bloc_tons(*, year: int, artifact_path: Path = _FAF_ARTIFACT_PATH) -> dict[str, float]:
    """Read ``faf_bloc_trade_tons.csv.gz`` for ``year`` (thousand tons per node).

    Spec-101 R8 / ADR055 disclosed-gap closure: ``bilateral_trade_tons`` was
    a permanent 0.0 stub because no FAF-freight grounding existed. This
    reads the checked-in artifact (:data:`_FAF_ARTIFACT_PATH`,
    hand-maintained by ``tools/make_faf_bloc_tons_artifact.py`` — see that
    module's docstring for the full FAF-zone-to-node mapping + disclosure
    table) for the exact ``year``.

    Years outside the artifact's covered span (:data:`_FAF_COVERAGE_YEARS`,
    2018-2024) get a SINGLE loud log line naming the coverage window and an
    empty dict — every node's ``bilateral_trade_tons`` then falls back to
    0.0 at the call site (the ADR055 no-fabrication precedent: the default
    campaign starts in 2010, outside coverage, so tons deliberately stay
    0.0 there; the fix is a start-year bump into [2018, 2024] or a FAF
    backcast to earlier years — neither attempted here).

    Args:
        year: Calendar year to read.
        artifact_path: Override for tests; defaults to the checked-in artifact.

    Returns:
        ``{node_id: tons_thousands}`` for the year (empty if outside the
        covered span or the artifact has no rows for it).
    """
    if not (_FAF_COVERAGE_YEARS[0] <= year <= _FAF_COVERAGE_YEARS[1]):
        logger.warning(
            "FAF freight-tons artifact covers years %d-%d only; start_year=%d is "
            "outside that window, so bilateral_trade_tons stays 0.0 for every "
            "international node this session (fix: bump start_year into the "
            "covered window, or extend the artifact with a FAF backcast).",
            _FAF_COVERAGE_YEARS[0],
            _FAF_COVERAGE_YEARS[1],
            year,
        )
        return {}
    if not artifact_path.is_file():
        logger.warning(
            "FAF freight-tons artifact not found at %s; bilateral_trade_tons stays 0.0.",
            artifact_path,
        )
        return {}
    out: dict[str, float] = {}
    with gzip.open(artifact_path, mode="rt", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if int(row["year"]) == year:
                out[row["node_id"]] = float(row["tons"])
    return out


# P26 U5c — disjoint engine-node -> dim_country id crosswalk (ADR165 Q4).
# HISTORICAL NOTE: this replaces the retired ``_NODE_TO_BLOC`` (spec-101 D3),
# which mapped each node onto a CONTAINING Census bloc (e.g. "Africa" for
# sub_saharan_africa, "Asia" for china) — those blocs overlap (Asia contains
# China; Africa contains Sub-Saharan Africa; "Europe" duplicated "European
# Union"), so summing all 8 mapped blocs' trade double-counted dollars and
# totalled ~138.6% of measured world trade (the denominator the U5c contract
# names). ``_NODE_TO_PARTNERS`` instead maps each node onto a DISJOINT set of
# individual-country / genuinely non-overlapping-aggregate ``dim_country`` ids
# (pinned by ``tools/ingest_census_bilateral_trade_blocs.py::_TARGET_CTY_CODES``,
# which populated the underlying ``fact_bilateral_trade_annual`` rows — every id
# below is a key of that dict, grouped identically). No id appears under two
# nodes (verified: 29 ids, 29 unique). ADR165 Q3: Mexico (21) joins
# latin_america; canada shrinks to actual Canada (19), no longer the whole
# "North America" aggregate.
_NODE_TO_PARTNERS: dict[str, tuple[int, ...]] = {
    "eu": (1,),  # European Union
    "canada": (19,),  # Canada
    "china": (168,),  # China
    "india": (149,),  # India
    "sub_saharan_africa": (15,),  # Sub Saharan Africa
    "latin_america": (6, 21),  # South and Central America + Mexico (ADR165 Q3)
    "russia_csi": (96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107),
    "southeast_asia": (154, 155, 156, 157, 158, 159, 160, 161, 163, 164),
}


def _read_partner_trade(
    sqlite_path: Path, start_year: int, node_ids: tuple[str, ...] = INTERNATIONAL_NODES
) -> dict[str, float]:
    """Sum ``fact_bilateral_trade_annual.total_trade_usd_millions`` per node.

    Per :data:`_NODE_TO_PARTNERS` (U5c disjoint crosswalk). The calendar year
    is chosen ONCE, deterministically, for every node together: the nearest
    annual year (:func:`~babylon.domain.economics.sigma.attribution.nearest_vintage`)
    to ``start_year`` among every ``is_annual=1`` year the table has ANY row
    for — not per-node, so the whole attribution reads off one consistent
    year even if a future partner set has gaps. With the current U5c coverage
    (2010-2024, every one of the 8 nodes' partner ids populated by
    ``tools/ingest_census_bilateral_trade_blocs.py``), the campaign default
    ``start_year=2010`` always resolves to the exact requested year.

    Args:
        sqlite_path: Path to ``marxist-data-3NF.sqlite``.
        start_year: Requested first simulation year.
        node_ids: Which nodes to sum (default: the canonical 8).

    Returns:
        ``{node_id: total_trade_usd_millions}`` — 0.0 for a node whose
        partner ids have no rows at the resolved year (disclosed, not fatal;
        :func:`_attribute_phi_by_sigma_composition`'s zero-mass guard catches
        the case where every node is 0.0).

    Raises:
        PhiAttributionUnavailableError: If ``fact_bilateral_trade_annual`` has
            no annual-year rows at all.
    """
    with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as conn:
        year_rows = conn.execute(
            "SELECT DISTINCT dt.year FROM fact_bilateral_trade_annual f "
            "JOIN dim_time dt ON dt.time_id = f.time_id WHERE dt.is_annual = 1"
        ).fetchall()
        available_years = tuple(sorted(int(row[0]) for row in year_rows))
        if not available_years:
            raise PhiAttributionUnavailableError(
                "fact_bilateral_trade_annual has no annual-year rows; "
                "the U5c partner-trade attribution cannot run."
            )
        resolved_year = nearest_vintage(start_year, available_years)
        time_row = conn.execute(
            "SELECT time_id FROM dim_time WHERE year = ? AND is_annual = 1 ORDER BY time_id LIMIT 1",
            (resolved_year,),
        ).fetchone()
        time_id = int(time_row[0])

        out: dict[str, float] = {}
        for node_id in sorted(node_ids):
            partner_ids = _NODE_TO_PARTNERS[node_id]
            placeholders = ",".join("?" * len(partner_ids))
            # Placeholders are only "?" chars (one per partner id); values are bound
            # separately, so this is not an injection vector despite the f-string shape.
            query = f"SELECT total_trade_usd_millions FROM fact_bilateral_trade_annual WHERE time_id = ? AND country_id IN ({placeholders})"  # noqa: S608, E501
            rows = conn.execute(query, (time_id, *partner_ids)).fetchall()
            out[node_id] = sum(float(r[0]) for r in rows if r[0] is not None)
    return out


# P26 U5a — Ricci region_type tier per engine node (theory rule, not a data
# lookup): eu/canada = CORE (weight 0, Amin/Wallerstein/MIM converge — no
# core-to-core drain mechanism, `specs/101-trade-activation/
# u5a-core-bloc-theory.md` §3 rule 1); china/russia_csi = SEMI_PERIPHERY
# (damped `w_semi`, rule 3 — russia_csi is a REMARKED re-map off its old
# CORE "Europe" crosswalk target, ADR165 Q2/u5a §3 rule 2, forced by the
# Ricci data itself: "Russia and CSI" is 100%-OUTFLOW, never CORE);
# india/southeast_asia/sub_saharan_africa/latin_america = PERIPHERY
# (undamped, rule 4).
_NODE_TIER: dict[str, str] = {
    "eu": TIER_CORE,
    "canada": TIER_CORE,
    "china": TIER_SEMI_PERIPHERY,
    "russia_csi": TIER_SEMI_PERIPHERY,
    "india": TIER_PERIPHERY,
    "southeast_asia": TIER_PERIPHERY,
    "sub_saharan_africa": TIER_PERIPHERY,
    "latin_america": TIER_PERIPHERY,
}

# P26 U5d — engine node -> `fact_ricci_unequal_exchange_gvc.region_name`
# (verified via SQL against the live reference DB — 13 distinct region_name
# values, see the U5d stage-2 report). Seven nodes have a direct, individually
# -named Ricci region. ``latin_america`` does NOT: Ricci has no "Latin
# America" row (confirmed empirically, and independently documented at
# `specs/101-trade-activation/u4-phi-attribution-options.md:434-439` —
# "latin_america has no grounded region under any option"). Rather than
# fabricate a σ gap for it (III.8), it is anchored on "Non-OECD" — the
# broadest genuine PERIPHERY aggregate in the table (the complement of OECD,
# which structurally contains the developing-country mass latin_america is
# part of) — a disclosed proxy, not a measurement. eu/canada's CORE regions
# never carry an OUTFLOW row (see :func:`_sigma_gap_for_node`), so their gap
# is 0.0 regardless of the region-name precision.
_NODE_TO_RICCI_REGION: dict[str, str] = {
    "eu": "Western Europe",
    "canada": "North America",
    "china": "China",
    "russia_csi": "Russia and CSI",
    "india": "India",
    "southeast_asia": "Southeast Asia",
    "sub_saharan_africa": "Sub-Saharan Africa",
    "latin_america": "Non-OECD",  # disclosed proxy — no Ricci Latin-America row
}


def _read_ricci_outflow_pct_gdp(sqlite_path: Path, region_name: str) -> dict[int, float]:
    """Read ``{year: value_pct_gdp}`` OUTFLOW rows for one Ricci region.

    Where both ``transfer_type`` values exist for a (region, year), TOTAL is
    preferred over GVC (TOTAL is the broader, all-channel unequal-exchange
    transfer; GVC is a component of it — program-10 §3 grounds σ in the whole
    transfer, not just its global-value-chain slice). Rows with a NULL
    ``value_pct_gdp`` are skipped (2007's Non-OECD rows, e.g., have
    ``value_usd_billions`` but no ``value_pct_gdp`` — not usable here).

    Args:
        sqlite_path: Path to ``marxist-data-3NF.sqlite``.
        region_name: Exact ``fact_ricci_unequal_exchange_gvc.region_name``.

    Returns:
        ``{year: value_pct_gdp}`` — empty for a region with no OUTFLOW rows
        at all (true for every CORE region; also true if a proxy region's
        name is mistyped, so keep this in sync with the SQL-verified
        :data:`_NODE_TO_RICCI_REGION` values).
    """
    with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as conn:
        rows = conn.execute(
            "SELECT year, transfer_type, value_pct_gdp "
            "FROM fact_ricci_unequal_exchange_gvc "
            "WHERE region_name = ? AND flow_direction = 'OUTFLOW' AND value_pct_gdp IS NOT NULL",
            (region_name,),
        ).fetchall()
    by_year: dict[int, dict[str, float]] = {}
    for year, transfer_type, value_pct_gdp in rows:
        by_year.setdefault(int(year), {})[str(transfer_type)] = float(value_pct_gdp)
    return {
        year: by_type.get("TOTAL", by_type.get("GVC", 0.0)) for year, by_type in by_year.items()
    }


def _sigma_gap_for_node(sqlite_path: Path, node_id: str, start_year: int) -> float:
    """The node's σ gap: ``max(0, OUTFLOW value_pct_gdp)`` at the nearest Ricci vintage.

    Per the U5d contract's simplified anchoring: the OUTFLOW value_pct_gdp
    IS the down-gradient distance directly (no separate ``σ_US`` observation
    is fabricated — Ricci has no United-States-labeled row to anchor one on;
    the CORE tier's structural zero-OUTFLOW property already implements
    "σ_US is at or above every CORE region"). The nearest vintage is resolved
    PER NODE (not globally) against whichever years that node's own region
    has an OUTFLOW row for — the 4 Ricci vintages (1995/2000/2007/2009) are
    sparse per-region (e.g. "Russia and CSI" has only a 1995 row), so a
    single global nearest-vintage pick would leave most nodes gapless for
    plausible campaign years.

    Args:
        sqlite_path: Path to ``marxist-data-3NF.sqlite``.
        node_id: One of :data:`_NODE_TO_RICCI_REGION`'s keys.
        start_year: Requested first simulation year.

    Returns:
        The gap (0.0 for CORE nodes, and for any node whose region has zero
        OUTFLOW rows — never negative).
    """
    region = _NODE_TO_RICCI_REGION[node_id]
    series = _read_ricci_outflow_pct_gdp(sqlite_path, region)
    if not series:
        return 0.0
    resolved_year = nearest_vintage(start_year, tuple(sorted(series)))
    return max(0.0, series[resolved_year])


def _derive_w_semi_from_ricci_sample(sqlite_path: Path) -> float:
    """Derive ``w_semi`` from the FULL Ricci OUTFLOW sample (all 4 vintages).

    Deliberately NOT vintage-gated to ``start_year``: Wallerstein's
    semi-periphery/periphery structural ratio (u5a §3 rule 3 — a
    semi-periphery's *net* outward transfer is damped relative to a pure
    periphery's because part of what it generates is retained as its own
    extraction from peripheries beneath it) is a claim about a stable
    cross-vintage regularity, not a per-year measurement — and vintage-gating
    it would make ``w_semi``'s availability an accident of data sparsity
    (the vintage nearest ``start_year=2010`` is 2009, which the live
    reference DB carries exactly ONE PERIPHERY OUTFLOW row for and ZERO
    SEMI_PERIPHERY rows — :func:`~babylon.domain.economics.sigma.attribution.derive_w_semi`
    would raise on an empty semi sample every single campaign start_year
    whose nearest vintage happens to land there). One (region, year) pair
    contributes once, TOTAL preferred over GVC per :func:`_read_ricci_outflow_pct_gdp`'s
    rule.

    Args:
        sqlite_path: Path to ``marxist-data-3NF.sqlite``.

    Returns:
        The derived damping coefficient in ``[0, 1]``.

    Raises:
        PhiAttributionUnavailableError: If either tier's OUTFLOW sample is
            empty (wraps :class:`~babylon.domain.economics.sigma.attribution.AttributionInputError`).
    """
    with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as conn:
        rows = conn.execute(
            "SELECT region_name, region_type, year, transfer_type, value_pct_gdp "
            "FROM fact_ricci_unequal_exchange_gvc "
            "WHERE flow_direction = 'OUTFLOW' AND value_pct_gdp IS NOT NULL"
        ).fetchall()
    grouped: dict[tuple[str, str, int], dict[str, float]] = {}
    for region_name, region_type, year, transfer_type, value_pct_gdp in rows:
        key = (str(region_name), str(region_type), int(year))
        grouped.setdefault(key, {})[str(transfer_type)] = float(value_pct_gdp)

    semi_sample: list[float] = []
    periphery_sample: list[float] = []
    for (_region_name, region_type, _year), by_type in sorted(grouped.items()):
        value = by_type.get("TOTAL", by_type.get("GVC", 0.0))
        if region_type == TIER_SEMI_PERIPHERY:
            semi_sample.append(value)
        elif region_type == TIER_PERIPHERY:
            periphery_sample.append(value)
    try:
        return derive_w_semi(
            semi_outflow_pct_gdp=semi_sample, periphery_outflow_pct_gdp=periphery_sample
        )
    except AttributionInputError as exc:
        raise PhiAttributionUnavailableError(f"w_semi derivation failed: {exc}") from exc


# ADR165's Q6/spec-107 D1 delegated the composition WEIGHTS to a
# ``SigmaDefines`` category that does not exist yet (out of this unit's
# write surface — config/defines/ is read-only here). The gap EXPONENT
# (`p` in `max(0, gap)^p`) is a separate, simpler knob the U5d contract names
# with a default of 1.0 (linear — "simplest form consistent with 'value
# transfer up-gradient'", `u5-engine-train-contracts.md` §U5d); until a
# `sigma.attribution_gap_exponent` define exists, 1.0 is used directly.
_GAP_EXPONENT_DEFAULT = 1.0


def _attribute_phi_by_sigma_composition(
    *,
    national_phi: float,
    tiers_by_node: dict[str, str],
    trade_by_node: dict[str, float],
    sigma_gap_by_node: dict[str, float],
    w_semi: float,
    gap_exponent: float = _GAP_EXPONENT_DEFAULT,
) -> dict[str, tuple[float, float]]:
    """Split the national Φ across engine nodes by the ruled σ-composition (U5d, Option C).

    Thin wrapper around :func:`~babylon.domain.economics.sigma.attribution.compute_bloc_shares`
    (``tiers_by_node``'s theory-ruled weights x each node's σ gap x its U5c
    disjoint trade volume, renormalized to Σ=1.0) that folds the resulting
    shares back into ``national_phi`` and re-attaches each node's raw USD
    trade value (``bilateral_trade_value``, unaffected by the share
    computation). CORE nodes get share 0 by construction — conservation
    still holds exactly because shares renormalize over the whole node set.

    Args:
        national_phi: The national Hickel Φ inflow (USD) for the year.
        tiers_by_node: ``{node_id: TIER_*}`` (:data:`_NODE_TIER`, filtered to
            the active node set by the caller — the FR-026
            ``external_node_overrides`` seam can shrink the registry).
        trade_by_node: ``{node_id: total_trade_usd_millions}`` — already
            tariff-dampened (:func:`~babylon.domain.economics.trade_policy.effective_trade`)
            by the caller.
        sigma_gap_by_node: ``{node_id: max(0, σ gap)}`` (:func:`_sigma_gap_for_node`).
        w_semi: SEMI_PERIPHERY damping (:func:`_derive_w_semi_from_ricci_sample`).
        gap_exponent: The declared ``p`` (default :data:`_GAP_EXPONENT_DEFAULT`).

    Returns:
        ``{node_id: (phi_year_inflow_usd, bilateral_trade_value_usd)}`` for
        every key of ``tiers_by_node``.

    Raises:
        PhiAttributionUnavailableError: Wraps
            :class:`~babylon.domain.economics.sigma.attribution.AttributionInputError`
            (key mismatch, unknown tier, or zero total attributable mass —
            every mapped bloc CORE-tier, gapless, or trade-less).
    """
    try:
        shares = compute_bloc_shares(
            tiers=tiers_by_node,
            sigma_gap=sigma_gap_by_node,
            trade=trade_by_node,
            w_semi=w_semi,
            gap_exponent=gap_exponent,
        )
    except AttributionInputError as exc:
        raise PhiAttributionUnavailableError(
            f"σ-composition attribution failed (national_phi={national_phi!r}): {exc}"
        ) from exc
    return {
        node_id: (national_phi * shares[node_id], trade_by_node[node_id] * 1e6)
        for node_id in sorted(shares)
    }


def _fetch_national_phi(pg_conn: Any, session_id: UUID, year: int) -> float:
    """Return the national Hickel Φ inflow (USD) for ``year``.

    The reference DB carries the drain only as a national aggregate keyed by
    ``scale_type`` (hydrated into ``immutable_reference_hickel_drain`` with
    ``partner_node_id='Intensive'``). Falls back to 0.0 if absent (no drain →
    no DRAIN_EDGE rows, per FR-020).
    """
    row = pg_conn.execute(
        "SELECT phi_year FROM immutable_reference_hickel_drain "
        "WHERE session_id = %s AND year = %s AND partner_node_id = 'Intensive' "
        "ORDER BY phi_year DESC LIMIT 1",
        (str(session_id), year),
    ).fetchone()
    if row and row[0] is not None:
        return float(row[0])
    return 0.0


def _select_nearest_erdi_row(rows: Sequence[tuple[int, float]], target_year: int) -> float:
    """Pick the ERDI value nearest ``target_year`` from already-fetched rows.

    Pure helper (no I/O) so the nearest-year selection logic is unit
    -testable without a live Postgres connection — :func:`_fetch_national_erdi`
    does the fetch and delegates here.

    Args:
        rows: ``(year, erdi_ratio)`` pairs (any order; duplicates by year
            are not expected from the source query but the last one wins).
        target_year: The year to anchor to.

    Returns:
        The nearest-year ``erdi_ratio``, or the neutral fallback ``1.0`` when
        ``rows`` is empty (``ExternalNode.erdi_ratio`` requires ``> 0``).
    """
    if not rows:
        return 1.0
    by_year = {int(year): float(erdi) for year, erdi in rows}
    resolved_year = nearest_vintage(target_year, tuple(sorted(by_year)))
    return by_year[resolved_year]


def _fetch_national_erdi(pg_conn: Any, session_id: UUID, year: int) -> float:
    """Return the real national Hickel ERDI ratio (nearest year, scale_type='Intensive').

    ADR165 Q7 fix. The previous ``_fetch_node_erdi`` queried
    ``immutable_reference_erdi.partner_node_id`` against country/bloc NAME
    strings (``_EXTERNAL_PARTNER_KEYS``, e.g. ``"Canada"``), but
    :func:`~babylon.persistence.sqlite_hydrator._copy_erdi` writes rows keyed
    by ``fact_hickel_erdi_annual.scale_type`` instead — the two vocabularies
    never intersected, so every lookup silently fell through to the neutral
    1.0 default (dead code: every campaign, every node, always 1.0).

    Fixed to read the real national 'Intensive' series (the same series
    :func:`_fetch_national_phi` reads for the Φ drain itself) instead.
    **DISCLOSED NATIONAL-ONLY**: the reference DB carries ERDI as a single
    national aggregate with no per-bloc resolution (the same limitation as
    the Hickel Φ drain, spec-101 D3) — every one of the 8 international
    nodes receives the SAME ``erdi_ratio`` value this returns. σ (via
    :func:`_attribute_phi_by_sigma_composition`), not ERDI, is the
    attribution driver (U5d) — ``erdi_ratio`` is now an honest observational
    field instead of a dead constant.

    Args:
        pg_conn: Open Postgres connection/cursor (psycopg 3 execute API).
        session_id: Owning session UUID.
        year: Calendar year to anchor to (nearest available 'Intensive' year
            wins via :func:`_select_nearest_erdi_row`).

    Returns:
        The nearest-year national ERDI ratio, or ``1.0`` (neutral) if no
        'Intensive' row was hydrated this session.
    """
    rows = pg_conn.execute(
        "SELECT year, erdi_ratio FROM immutable_reference_erdi "
        "WHERE session_id = %s AND partner_node_id = 'Intensive' AND erdi_ratio > 0",
        (str(session_id),),
    ).fetchall()
    return _select_nearest_erdi_row(rows, year)


def _bootstrap_external_nodes(
    *,
    session_id: UUID,
    runtime: PostgresRuntime,
    start_year: int,
    sqlite_path: Path,
    defines: GameDefines,
    node_ids: tuple[str, ...] = INTERNATIONAL_NODES,
) -> tuple[int, float]:
    """Populate ``dynamic_external_node_state`` at tick 0 from hydrated refs.

    Spec 062 T078 + P26 U5d (supersedes spec-101 D3's trade-share proxy with
    the ruled σ-composition attribution, ADR165 Q1). Reads the national
    Hickel Φ aggregate (``immutable_reference_hickel_drain`` 'Intensive'),
    the U5c disjoint-partner ``fact_bilateral_trade_annual`` USD trade totals
    (:func:`_read_partner_trade`), each node's σ gap from the Ricci
    unequal-exchange table (:func:`_sigma_gap_for_node`), and the
    data-derived SEMI_PERIPHERY damping (:func:`_derive_w_semi_from_ricci_sample`),
    then **attributes** the national Φ across the international engine nodes
    via :func:`_attribute_phi_by_sigma_composition`. Raw trade is passed
    through the tariff seam (:func:`~babylon.domain.economics.trade_policy.effective_trade`,
    P26 U5f) before attribution — ``defines.trade_policy`` START values,
    default-inert. ``bilateral_trade_tons`` (Program 26 U3) is read from the
    checked-in FAF freight artifact via :func:`_read_faf_bloc_tons` for
    ``start_year``; falls back to 0.0 for nodes/years the artifact does not
    cover. ``erdi_ratio`` is the real national Hickel 'Intensive' series
    (:func:`_fetch_national_erdi`, ADR165 Q7 fix — same value for every
    node, disclosed national-only). Writes one ``ExternalNode`` per canonical
    node id (8 international + 1 domestic_rest) via ``persist_tick_atomic()``
    under the FR-008a atomic-tick guarantee.

    ``node_ids`` defaults to :data:`INTERNATIONAL_NODES` (the canonical 8);
    the spec-063 FR-026 ``external_node_overrides`` seam threads a caller-
    supplied set here so a session can be bootstrapped with a reduced
    registry (e.g. one that omits canada) to exercise the FR-026 guard — the
    σ-composition inputs (:data:`_NODE_TIER`, trade, gaps) are filtered to
    ``node_ids`` before attribution so ``compute_bloc_shares``'s key-set
    guard still passes on a reduced registry.

    Returns:
        ``(row_count, national_phi)`` — ``row_count`` is the number of rows
        written (``len(node_ids) + 1``; 9 for the default set); ``national_phi`` is
        the RAW, un-attributed national Φ read from
        ``immutable_reference_hickel_drain`` (spec-101 review fix #3 — an
        independent ground-truth signal, distinct from the per-node
        attributed values, threaded through :attr:`InitializationReport.national_phi_reference`
        so the conservation auditor can detect an attribution-stage
        regression that zeroes every node's Φ even though the true national
        Φ was positive).
    """
    from babylon.persistence.envelope import PerTickTransactionEnvelope
    from babylon.persistence.external_node import ExternalNode, ExternalNodeKind

    raw_trade = _read_partner_trade(sqlite_path, start_year, node_ids=node_ids)
    trade_by_node = effective_trade(
        raw_trade,
        defines.trade_policy.tariff_rates,
        dampening=defines.trade_policy.tariff_dampening_coefficient,
    )
    sigma_gap_by_node = {
        node_id: _sigma_gap_for_node(sqlite_path, node_id, start_year) for node_id in node_ids
    }
    tiers_by_node = {node_id: _NODE_TIER[node_id] for node_id in node_ids}
    w_semi = _derive_w_semi_from_ricci_sample(sqlite_path)
    faf_tons = _read_faf_bloc_tons(year=start_year)

    rows: list[ExternalNode] = []
    with runtime._pool.connection() as conn:  # noqa: SLF001
        national_phi = _fetch_national_phi(conn, session_id, start_year)
        national_erdi = _fetch_national_erdi(conn, session_id, start_year)
        attribution = _attribute_phi_by_sigma_composition(
            national_phi=national_phi,
            tiers_by_node=tiers_by_node,
            trade_by_node=trade_by_node,
            sigma_gap_by_node=sigma_gap_by_node,
            w_semi=w_semi,
        )
        for node_id in node_ids:
            phi, btv = attribution[node_id]
            rows.append(
                ExternalNode(
                    session_id=session_id,
                    tick=0,
                    node_id=node_id,
                    kind=ExternalNodeKind.INTERNATIONAL,
                    phi_year_inflow=phi,
                    bilateral_trade_value=btv,
                    bilateral_trade_tons=faf_tons.get(node_id, 0.0),
                    erdi_ratio=national_erdi,
                )
            )
    # Rest-of-USA carries no Hickel drain / no foreign trade; pure domestic sink.
    rows.append(
        ExternalNode(
            session_id=session_id,
            tick=0,
            node_id=DOMESTIC_REST_NODE,
            kind=ExternalNodeKind.DOMESTIC_REST,
            phi_year_inflow=0.0,
            bilateral_trade_value=0.0,
            bilateral_trade_tons=0.0,
            erdi_ratio=1.0,
        )
    )

    envelope = PerTickTransactionEnvelope(
        session_id=session_id,
        tick=0,
        external_node_rows=rows,
        determinism_hash="0" * 64,  # init-time bootstrap; real hashes start tick 1
    )
    # persist_tick_atomic is monkey-patched onto PostgresRuntime by
    # _spec_062.py at module load; a TYPE_CHECKING-only stub on the class
    # (added alongside babylon.game.session's GameRuntimeStore Protocol)
    # now makes it visible to mypy, so no ignore is needed here anymore.
    # Spec-089 FR-003: like the hex hydrator, the init-time bootstrap must
    # NOT claim the (session, 0) commit marker — its placeholder hash would
    # shadow the bridge's real tick-0 marker via ON CONFLICT DO NOTHING.
    runtime.persist_tick_atomic(envelope, write_commit_marker=False)
    return len(rows), national_phi


def _resolve_effective_international_registry(
    *,
    external_node_overrides: frozenset[str] | None,
    synthetic_lodes_canadian_rows: bool,
) -> tuple[str, ...]:
    """Resolve the effective international external-node set + FR-026 fail-fast.

    Spec-063 FR-026 / SC-006. ``external_node_overrides`` (test seam) replaces
    the canonical :data:`INTERNATIONAL_NODES`; when synthetic Canadian LODES
    rows are also requested but canada is absent from the resolved set, this
    raises BEFORE any SQLite/Postgres work so the SC-006 ``< 5s`` fail-fast
    budget holds regardless of OS page-cache state (the reference-window
    preflight can cost ~6s cold on the 6 GB SQLite).

    Args:
        external_node_overrides: Optional replacement international-node set.
        synthetic_lodes_canadian_rows: Whether a synthetic canada OD row will
            be injected (which requires canada in the registry).

    Returns:
        The effective international-node tuple (sorted when overridden).

    Raises:
        InitializationError: FR-026 — synthetic canada rows requested while
            canada is absent from the resolved registry.
    """
    effective = (
        tuple(sorted(external_node_overrides))
        if external_node_overrides is not None
        else INTERNATIONAL_NODES
    )
    if synthetic_lodes_canadian_rows and "canada" not in effective:
        raise InitializationError(
            "Spec 063 FR-026 fail-fast: canada destination present in the LODES "
            "matrix (synthetic injection requested) but canada is not present in "
            "the external-node registry. Add canada to external_node_overrides "
            "or disable synthetic_lodes_canadian_rows."
        )
    return effective


def initialize_session(
    *,
    session_id: UUID,
    sqlite_path: Path,
    runtime: PostgresRuntime,
    defines: GameDefines,
    start_year: int,
    scenario_length_years: int | None = None,
    counties: list[str] | None = None,
    lodes_root: Path | None = None,
    lodes_crosswalk: Path | None = None,
    lodes_study_area_hexes: frozenset[str] | None = None,
    lodes_study_area_states: frozenset[str] | None = None,
    hex_hydration_counties: frozenset[str] | None = None,
    tiger_county_shapefile: Path | None = None,
    border_bts_csv: Path | None = None,
    border_statcan_csv: Path | None = None,
    border_port_codes: frozenset[str] | None = None,
    border_aggregate_hex: str | None = None,
    # Spec-063 FR-026 / SC-006 test seams (quickstart §5):
    external_node_overrides: frozenset[str] | None = None,
    synthetic_lodes_canadian_rows: bool = False,
) -> InitializationReport:
    """Single-call session initialization.

    Per the quickstart §1 contract. The SQLite handle is provably closed
    before the function returns (FR-002).

    Args:
        session_id: Owning session UUID.
        sqlite_path: Path to ``marxist-data-3NF.sqlite``.
        runtime: PostgresRuntime to write through.
        defines: GameDefines (FR-029a alpha_weekly invariant checked).
        start_year: First simulated year.
        scenario_length_years: Override for ``defines.economy.scenario_length_years``.
        counties: Optional 5-digit FIPS list to scope QCEW + rent
            (Detroit tri-county = ``["26163", "26125", "26099"]``).
        border_bts_csv: Spec 063 T042 — BTS Border Crossing CSV path. Only
            consulted when ``defines.economy.enable_border_commute_synthesis``
            is True (falls back to the canonical data-trove location).
        border_statcan_csv: Optional StatCan Frontier Counts CSV path
            (same gate; FR-033 tolerates absence with one warning).
        border_port_codes: Override for the Detroit-Windsor BTS port codes
            (same gate; defaults to Ambassador Bridge + Tunnel).
        border_aggregate_hex: Tri-county aggregate H3 cell used as the
            synthesized flows' origin. REQUIRED when the synthesis gate
            is enabled; there is no meaningful default (FR-035).
        external_node_overrides: Spec-063 FR-026 test seam. Replaces the
            fixed ``INTERNATIONAL_NODES`` enumeration for the external-node
            registry (bootstrap + ``report.external_node_ids``). Default
            ``None`` keeps the canonical 8-international set (canada present).
        synthetic_lodes_canadian_rows: Spec-063 test seam (quickstart §5).
            When True, injects one synthetic ``canada`` OD row so the FR-026
            guard + downstream routing can be exercised without operator
            LODES data. Combined with an ``external_node_overrides`` set that
            omits canada, this triggers the FR-026 fail-fast (SC-006).

    Raises:
        InitializationError: On FR-029a alpha violation, reference-window
            hard-refuse, Hickel coverage gap, or the FR-026 fail-fast
            (synthetic canada rows requested while canada is absent from the
            external-node registry).
    """
    _validate_alpha_invariant(defines)

    # Spec-063 FR-026 / SC-006 fail-fast BEFORE any SQLite/Postgres work (the
    # helper raises when synthetic canada rows are requested without canada in
    # the registry — see its docstring for the <5s budget rationale).
    effective_international = _resolve_effective_international_registry(
        external_node_overrides=external_node_overrides,
        synthetic_lodes_canadian_rows=synthetic_lodes_canadian_rows,
    )

    scenario_length = (
        scenario_length_years
        if scenario_length_years is not None
        else defines.economy.scenario_length_years
    )

    # Spec-065 T036 / FR-022: reference-data window preflight.
    # Three-mode policy: silent / warn-and-clamp / hard-refuse (raise).
    # Hard-refuse manifests as InitializationError → CLI exit 3.
    allowed_length, preflight_warnings = _preflight_reference_data_window(
        sqlite_path=sqlite_path,
        start_year=start_year,
        scenario_length_years=scenario_length,
    )
    for msg in preflight_warnings:
        # FR-022 requires stderr; logger at WARNING level routes to stderr
        # by default in the headless runner's logging config.
        logger.warning("%s", msg)
    if allowed_length < scenario_length:
        scenario_length = allowed_length

    # Spec-101 review fix #2: fail loud (before any Postgres write) when
    # start_year falls outside Hickel 'Intensive' coverage — otherwise
    # national Φ attribution silently collapses to zero for every node.
    _preflight_hickel_intensive_coverage(sqlite_path=sqlite_path, start_year=start_year)

    report = InitializationReport(session_id=session_id, sqlite_path=sqlite_path.resolve())

    # Spec-088 FR-005: create this session's partitions before any
    # dynamic-table write (external-node bootstrap writes tick 0 below).
    from babylon.persistence.partitioning import ensure_session_partitions

    ensure_session_partitions(pool=runtime._pool, session_id=session_id)  # noqa: SLF001

    copied = copy_reference_series(
        session_id=session_id,
        start_year=start_year,
        scenario_length_years=scenario_length,
        sqlite_path=sqlite_path,
        runtime=runtime,
        counties=counties,
    )

    # The hydrator returns Postgres-table-keyed identifiers (e.g.
    # 'bea_io', 'hickel_drain'). Map to the canonical lookup-policy
    # series_ids that downstream code uses:
    _table_to_series = {
        "bea_io": "bea_io_imports",
        "melt_tau": "melt_tau",
        "basket_gamma": "basket_gamma",
        "erdi": "erdi_ratio",
        "hickel_drain": "hickel_drain",
        "ricci_unequal": "ricci_unequal",
        "faf_freight": "faf_freight",
        "qcew_employment": "qcew_employment",
        "bea_reis_rent": "bea_reis_rent",
        "fred_rates": "fred_fed_funds_rate",
    }
    report.copied_series = {_table_to_series.get(table, table) for table in copied}

    # External-node bootstrap (T078). The fixed enumeration is locked here
    # so downstream code can assume exactly nine boundary nodes per session.
    # The bootstrap function reads the just-hydrated Hickel/Ricci/FAF rows
    # and persists one ExternalNode per canonical node_id at tick 0.
    # Uses effective_international (FR-026 seam) so an override that omits
    # canada makes report.external_node_ids lack canada — which revives the
    # otherwise-dead FR-026 data-driven guard below (it was unreachable while
    # this was hardcoded to the full 9-node set).
    report.external_node_ids = set(effective_international) | {DOMESTIC_REST_NODE}
    report.external_node_count, report.national_phi_reference = _bootstrap_external_nodes(
        session_id=session_id,
        runtime=runtime,
        start_year=start_year,
        sqlite_path=sqlite_path,
        defines=defines,
        node_ids=effective_international,
    )

    # Spec-063 test seam (quickstart §5 / SC-006): inject one synthetic canada
    # OD row so the FR-026 guard + downstream Detroit-Windsor routing can be
    # exercised without operator LODES data. Placed OUTSIDE the LODES gate so
    # the injection is meaningful for sessions that pass no lodes_root.
    # Idempotent via the OD table's composite PK.
    if synthetic_lodes_canadian_rows:
        from babylon.domain.economics.border_commute_synthesis import (
            default_tri_county_aggregate_hex,
        )

        with (
            runtime._pool.connection() as pg,  # noqa: SLF001
            pg.cursor() as cur,
        ):
            cur.execute(
                """
                INSERT INTO immutable_reference_lodes_od_matrix
                    (session_id, year, home_hex, workplace_dest,
                     workplace_dest_kind, s000_workers)
                VALUES (%s, %s, %s, 'canada', 'external', 100)
                ON CONFLICT (session_id, year, home_hex, workplace_dest) DO NOTHING
                """,
                (session_id, start_year, default_tri_county_aggregate_hex()),
            )

    # Spec-063 closure (2026-05-14) — hex graph hydration at tick 0.
    # Gated on `hex_hydration_counties` so existing callers that don't
    # need a populated hex graph (legacy unit tests, helper scripts)
    # remain unchanged. See `babylon.persistence.hex_hydrator`.
    #
    # Spec-068 T057: construct a ``DefaultBEAShareLookupService`` from the
    # reference DB so the hydrator uses per-county BEA I-O shares instead
    # of the 0.5 economy-wide constant. The service reads through the II.11
    # Protocol (QCEW-employment-weighted concordance → fact_bea_national_industry).
    # ``GLOBAL_FALLBACK_SHARE = 0.5`` preserves the FR-010 baseline for
    # counties/years with no BEA data.
    if hex_hydration_counties:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session as _SASession

        from babylon.persistence.hex_hydrator import hydrate_hex_state
        from babylon.reference.bea import DefaultBEAShareLookupService

        bea_engine = create_engine(f"sqlite:///{sqlite_path}")
        bea_session = _SASession(bea_engine)
        try:
            bea_share_service = DefaultBEAShareLookupService(bea_session)
            report.hex_count = hydrate_hex_state(
                runtime=runtime,
                session_id=session_id,
                counties=hex_hydration_counties,
                start_year=start_year,
                defines=defines,
                tiger_county_shapefile=tiger_county_shapefile,
                sqlite_path=sqlite_path,
                bea_share_service=bea_share_service,
            )
        finally:
            bea_session.close()
            bea_engine.dispose()
    else:
        report.hex_count = 0

    # Spec 063 T020 — hydrate LODES OD matrix per scenario year if inputs supplied.
    # Gated on all four LODES paths being present so existing test surfaces that
    # don't pass LODES inputs remain green.
    if (
        lodes_root is not None
        and lodes_crosswalk is not None
        and lodes_study_area_hexes is not None
        and lodes_study_area_states is not None
    ):
        from babylon.domain.economics.lodes_commute_matrix import LODESCommuteMatrixLoader

        loader = LODESCommuteMatrixLoader(
            lodes_root=lodes_root,
            crosswalk_path=lodes_crosswalk,
            study_area_hexes=lodes_study_area_hexes,
            study_area_states=lodes_study_area_states,
        )
        rows_persisted = 0
        years_persisted = 0
        for offset in range(scenario_length):
            year = start_year + offset
            clamped = loader.clamp_to_available(year)
            try:
                count = loader.persist_to_postgres(
                    runtime=runtime, session_id=session_id, year=clamped
                )
                rows_persisted += count
                years_persisted += 1
            except Exception as exc:  # noqa: BLE001 — surface partial hydration in counts
                logger.warning("LODES persist failed for year %s: %s", clamped, exc)
                continue
        report.lodes_year_count = years_persisted
        report.lodes_row_count = rows_persisted

        # Spec 063 T042 — Option B border-commute synthesis (FR-031..FR-036).
        # Gated on GameDefines; FR-036 fail-fast fires inside the loader
        # constructor when the BTS CSV is absent. Nested inside the LODES
        # gate deliberately: synthesis without LODES hydration would merge
        # into an OD table the session never reads.
        if defines.economy.enable_border_commute_synthesis:
            from babylon.domain.economics.border_commute_synthesis import (
                DEFAULT_BTS_CSV,
                DEFAULT_STATCAN_CSV,
                DETROIT_PORT_CODES,
                BorderCommuteSynthesisLoader,
            )

            if border_aggregate_hex is None:
                raise InitializationError(
                    "enable_border_commute_synthesis=True requires "
                    "border_aggregate_hex (the tri-county aggregate H3 cell); "
                    "spec 063 FR-035 has no meaningful default."
                )
            synthesizer = BorderCommuteSynthesisLoader(
                bts_csv_path=border_bts_csv or DEFAULT_BTS_CSV,
                statcan_csv_path=border_statcan_csv or DEFAULT_STATCAN_CSV,
                border_commute_share=defines.economy.border_commute_share,
                detroit_port_codes=border_port_codes or DETROIT_PORT_CODES,
                tri_county_aggregate_hex=border_aggregate_hex,
                enabled=True,
            )
            years = tuple(start_year + offset for offset in range(scenario_length))
            report.border_synthesis_row_count = synthesizer.persist_to_postgres(
                runtime=runtime, session_id=session_id, years=years
            )
            # FR-035: merge us_to_canada rows into the OD matrix so
            # LODESCommuteMatrixLoader.load_year_from_postgres() reads back
            # the merged matrix (T042).
            for year in years:
                synthesizer.merge_into_postgres_lodes(
                    runtime=runtime, session_id=session_id, year=year
                )

        # Spec 063 FR-026 fail-fast invariant — if any LODES row has
        # workplace_dest='canada' but the external-node registry omits canada,
        # refuse to proceed. (Default LODES has no Canadian rows per research §4,
        # so this is a guard for the Option B synthesis path + synthetic tests.)
        if "canada" not in report.external_node_ids:
            with (
                runtime._pool.connection() as pg,  # noqa: SLF001
                pg.cursor() as cur,
            ):
                cur.execute(
                    """
                    SELECT COUNT(*) FROM immutable_reference_lodes_od_matrix
                    WHERE session_id = %s AND workplace_dest = 'canada'
                    """,
                    (session_id,),
                )
                canada_rows = cur.fetchone()
                if canada_rows and canada_rows[0] > 0:
                    raise InitializationError(
                        "Spec 063 FR-026 fail-fast: canada destination present "
                        "in LODES matrix but canada not present in external_node "
                        "registry. Add canada to INTERNATIONAL_NODES or disable "
                        "the Canadian-row injection that produced these rows."
                    )

    return report


__all__ = [
    "InitializationError",
    "InitializationReport",
    "copy_reference_series",
    "initialize_session",
    "INTERNATIONAL_NODES",
    "DOMESTIC_REST_NODE",
]
