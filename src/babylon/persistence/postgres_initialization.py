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

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

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
    conservation break); ``_attribute_phi_and_trade`` and its Hickel-coverage
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


# Mapping from canonical ExternalNode.node_id (FR-036) to the partner-name
# strings the SQLite reference uses. Each maps to a list of acceptable
# matches; the first non-empty match wins. Unmatched nodes get phi=0 and
# are still persisted (so the integration tests find all 9 rows).
_EXTERNAL_PARTNER_KEYS: dict[str, tuple[str, ...]] = {
    "canada": ("Canada", "NAFTA with Mexico (Consump)"),
    "china": ("China",),
    "eu": ("European Union",),
    "india": ("India",),
    "sub_saharan_africa": ("Sub-Saharan Africa", "Africa"),
    "latin_america": ("Latin America", "Mexico"),
    "russia_csi": ("Russia", "CSI"),
    "southeast_asia": ("Southeast Asia", "Vietnam", "Indonesia"),
}


# spec-101 D3 — injective engine-node → dim_country ``is_region=1`` bloc crosswalk.
# The reference DB's Hickel drain is a SINGLE national aggregate (scale_type
# 'Intensive'); it has NO per-bloc resolution (research R2), so the national Φ is
# attributed across the international engine nodes by bilateral-trade share
# (``fact_bilateral_trade_annual``). The crosswalk is INJECTIVE (each node → at
# most one distinct bloc) so no bloc's trade is double-counted. dim_country ids:
# 1=European Union, 7=North America, 8=Europe, 9=Africa, 10=Pacific Rim, 12=Asia.
# Fidelity limitations DISCLOSED (spec-101 D3): containing-bloc granularity
# (sub_saharan_africa gets all of Africa; southeast_asia all of Pacific Rim);
# russia_csi→Europe is weak; ``india`` and ``latin_america`` have no distinct
# grounded bloc (Asia is taken by china; there is no Latin-America is_region bloc)
# → they receive Φ=0 rather than a fabricated value (III.8). This is the #1
# owner-review item; a future per-bloc drain / per-country trade slice replaces it.
_NODE_TO_BLOC: dict[str, int] = {
    "eu": 1,  # European Union
    "canada": 7,  # North America
    "russia_csi": 8,  # Europe (weak; Russia is Eurasian — flagged)
    "sub_saharan_africa": 9,  # Africa (containing bloc)
    "southeast_asia": 10,  # Pacific Rim (containing bloc)
    "china": 12,  # Asia (dominant Asian trade partner)
    # india, latin_america: no distinct grounded bloc → Φ=0 (disclosed).
}


def _read_bloc_trade(sqlite_path: Path, year: int) -> dict[int, float]:
    """Read ``fact_bilateral_trade_annual.total_trade_usd_millions`` per bloc.

    Spec-100 R8 handoff: this is the audited annual USD trade aggregate that
    feeds ``ExternalNode.bilateral_trade_value`` (never ``bilateral_trade_tons``).
    Read read-only from SQLite at init-time (the handle is not held past
    :func:`initialize_session`, FR-002).

    Args:
        sqlite_path: Path to ``marxist-data-3NF.sqlite``.
        year: Calendar year whose annual bilateral trade to read.

    Returns:
        ``{country_id: total_trade_usd_millions}`` for the year's annual
        ``time_id`` (empty if the year or table is absent).
    """
    with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as conn:
        time_row = conn.execute(
            "SELECT time_id FROM dim_time WHERE year = ? AND is_annual = 1 "
            "ORDER BY time_id LIMIT 1",
            (year,),
        ).fetchone()
        if time_row is None or time_row[0] is None:
            return {}
        rows = conn.execute(
            "SELECT country_id, total_trade_usd_millions "
            "FROM fact_bilateral_trade_annual WHERE time_id = ?",
            (int(time_row[0]),),
        ).fetchall()
    out: dict[int, float] = {}
    for country_id, total in rows:
        if total is not None:
            out[int(country_id)] = float(total)
    return out


def _attribute_phi_and_trade(
    *, national_phi: float, bloc_trade: dict[int, float]
) -> dict[str, tuple[float, float]]:
    """Split the national Φ across engine nodes by bilateral-trade share (D3).

    For each node with a grounded containing bloc (``_NODE_TO_BLOC``) and positive
    bloc trade, ``share = bloc_trade / Σ(mapped bloc_trade)`` and
    ``phi = national_phi × share``. Because the crosswalk is injective and shares
    sum to 1.0, ``Σ_nodes phi = national_phi`` exactly (national conservation).
    ``bilateral_trade_value`` is the node's bloc trade in USD (millions × 1e6).

    Args:
        national_phi: The national Hickel Φ inflow (USD) for the year.
        bloc_trade: ``{country_id: total_trade_usd_millions}`` from
            :func:`_read_bloc_trade`.

    Returns:
        ``{node_id: (phi_year_inflow_usd, bilateral_trade_value_usd)}`` for nodes
        with a grounded, positive-trade bloc. Nodes absent from the map get
        ``(0.0, 0.0)`` at the call site (disclosed Φ=0 for india / latin_america).

    Raises:
        PhiAttributionUnavailableError: If no mapped bloc has positive
            recorded trade (spec-101 review fix #1). Silently returning
            ``{}`` would zero 100% of national Φ across every engine node
            with no operator-visible signal — the same conservation-break
            class the sibling ``county_exposure.py`` hard-fails on.
    """
    node_trade: dict[str, float] = {}
    for node_id, bloc_id in _NODE_TO_BLOC.items():
        trade = bloc_trade.get(bloc_id)
        if trade is not None and trade > 0.0:
            node_trade[node_id] = trade
    total_trade = sum(node_trade.values())
    if total_trade <= 0.0:
        raise PhiAttributionUnavailableError(
            f"No _NODE_TO_BLOC bloc has positive recorded trade (national_phi="
            f"{national_phi!r}); attribution would silently drop 100% of "
            f"national Φ across every engine node. Check "
            f"fact_bilateral_trade_annual coverage for this start_year."
        )
    out: dict[str, tuple[float, float]] = {}
    for node_id in sorted(node_trade):
        trade = node_trade[node_id]
        share = trade / total_trade
        out[node_id] = (national_phi * share, trade * 1e6)
    return out


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


def _fetch_node_erdi(pg_conn: Any, session_id: UUID, year: int, node_id: str) -> float:
    """Look up the per-node ERDI ratio (neutral 1.0 default).

    Spec-101 review cleanup: phi_year and bilateral_trade_value were
    superseded by the D3 trade-share attribution (:func:`_attribute_phi_and_trade`)
    and are no longer consumed by :func:`_bootstrap_external_nodes` — this
    function used to also query ``immutable_reference_hickel_drain`` and
    ``immutable_reference_ricci_unequal`` and discard both results. Only
    ``erdi_ratio`` (from ``immutable_reference_erdi``, no D3 equivalent) is
    still needed per node.

    Falls back to 1.0 (neutral exchange) when no ``immutable_reference_erdi``
    row matches the node's acceptable partner-name keys, since 0 would
    violate the CHECK constraint.
    """
    keys = _EXTERNAL_PARTNER_KEYS.get(node_id, ())
    if not keys:
        return 1.0

    # psycopg 3 canonical pattern for list parameters: ``= ANY(%s)`` with a
    # Python list (adapted to a Postgres array). Per psycopg docs, the
    # legacy ``IN %s`` form is unsupported in psycopg 3. Empty lists also
    # work (whereas ``IN ()`` is not valid SQL).
    key_list = list(keys)

    row = pg_conn.execute(
        "SELECT erdi_ratio FROM immutable_reference_erdi "
        "WHERE session_id = %s AND year = %s AND partner_node_id = ANY(%s) "
        "ORDER BY erdi_ratio DESC LIMIT 1",
        (str(session_id), year, key_list),
    ).fetchone()
    if row and row[0] is not None and row[0] > 0:
        return float(row[0])
    return 1.0


def _bootstrap_external_nodes(
    *,
    session_id: UUID,
    runtime: PostgresRuntime,
    start_year: int,
    sqlite_path: Path,
    node_ids: tuple[str, ...] = INTERNATIONAL_NODES,
) -> tuple[int, float]:
    """Populate ``dynamic_external_node_state`` at tick 0 from hydrated refs.

    Spec 062 T078 + spec-101 D3/FR-101-3/FR-101-4. Reads the national Hickel Φ
    aggregate (``immutable_reference_hickel_drain`` 'Intensive') and the spec-100
    ``fact_bilateral_trade_annual`` USD trade totals, then **attributes** the
    national Φ across the international engine nodes by bilateral-trade share via
    the injective ``_NODE_TO_BLOC`` crosswalk, and sets each node's
    ``bilateral_trade_value`` from its bloc's USD trade (never
    ``bilateral_trade_tons`` — spec-100 R8). ``erdi_ratio`` retains the existing
    lookup (neutral 1.0 default absent per-node data). Writes one ``ExternalNode``
    per canonical node id (8 international + 1 domestic_rest) via
    ``persist_tick_atomic()`` under the FR-008a atomic-tick guarantee.

    ``node_ids`` defaults to :data:`INTERNATIONAL_NODES` (the canonical 8);
    the spec-063 FR-026 ``external_node_overrides`` seam threads a caller-
    supplied set here so a session can be bootstrapped with a reduced
    registry (e.g. one that omits canada) to exercise the FR-026 guard.

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

    bloc_trade = _read_bloc_trade(sqlite_path, start_year)

    rows: list[ExternalNode] = []
    with runtime._pool.connection() as conn:  # noqa: SLF001
        national_phi = _fetch_national_phi(conn, session_id, start_year)
        attribution = _attribute_phi_and_trade(national_phi=national_phi, bloc_trade=bloc_trade)
        for node_id in node_ids:
            # erdi still comes from the per-node reference lookup (neutral default);
            # phi + bilateral_trade_value are the attributed values (D3).
            erdi = _fetch_node_erdi(conn, session_id, start_year, node_id)
            phi, btv = attribution.get(node_id, (0.0, 0.0))
            rows.append(
                ExternalNode(
                    session_id=session_id,
                    tick=0,
                    node_id=node_id,
                    kind=ExternalNodeKind.INTERNATIONAL,
                    phi_year_inflow=phi,
                    bilateral_trade_value=btv,
                    bilateral_trade_tons=0.0,
                    erdi_ratio=erdi,
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
    # _spec_062.py at module load; mypy doesn't see the attachment.
    # Spec-089 FR-003: like the hex hydrator, the init-time bootstrap must
    # NOT claim the (session, 0) commit marker — its placeholder hash would
    # shadow the bridge's real tick-0 marker via ON CONFLICT DO NOTHING.
    runtime.persist_tick_atomic(  # type: ignore[attr-defined]
        envelope, write_commit_marker=False
    )
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
        node_ids=effective_international,
    )

    # Spec-063 test seam (quickstart §5 / SC-006): inject one synthetic canada
    # OD row so the FR-026 guard + downstream Detroit-Windsor routing can be
    # exercised without operator LODES data. Placed OUTSIDE the LODES gate so
    # the injection is meaningful for sessions that pass no lodes_root.
    # Idempotent via the OD table's composite PK.
    if synthetic_lodes_canadian_rows:
        from babylon.economics.border_commute_synthesis import default_tri_county_aggregate_hex

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
        from babylon.economics.lodes_commute_matrix import LODESCommuteMatrixLoader

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
            except Exception:  # noqa: BLE001 — surface partial hydration in counts
                continue
        report.lodes_year_count = years_persisted
        report.lodes_row_count = rows_persisted

        # Spec 063 T042 — Option B border-commute synthesis (FR-031..FR-036).
        # Gated on GameDefines; FR-036 fail-fast fires inside the loader
        # constructor when the BTS CSV is absent. Nested inside the LODES
        # gate deliberately: synthesis without LODES hydration would merge
        # into an OD table the session never reads.
        if defines.economy.enable_border_commute_synthesis:
            from babylon.economics.border_commute_synthesis import (
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
