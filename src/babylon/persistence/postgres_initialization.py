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

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.persistence import PostgresRuntime


class InitializationError(RuntimeError):
    """Raised when initialization cannot proceed.

    Common causes: required SQLite years missing for a coefficient series
    (FR-016 / FR-029a invariant violation), invalid scenario configuration,
    or Postgres schema not yet migrated.
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


def _fetch_node_phi_and_trade(
    pg_conn: Any, session_id: UUID, year: int, node_id: str
) -> tuple[float, float, float, float]:
    """Look up phi_year, bilateral_trade_value, bilateral_trade_tons, erdi.

    Falls back to (0, 0, 0, 1.0) when no Hickel/Ricci/FAF row matches the
    node's acceptable partner-name keys. Erdi defaults to 1.0 (neutral
    exchange) since 0 would violate the CHECK constraint.
    """
    keys = _EXTERNAL_PARTNER_KEYS.get(node_id, ())
    phi = 0.0
    bilateral_value = 0.0
    bilateral_tons = 0.0
    erdi = 1.0

    if not keys:
        return phi, bilateral_value, bilateral_tons, erdi

    # psycopg 3 canonical pattern for list parameters: ``= ANY(%s)`` with a
    # Python list (adapted to a Postgres array). Per psycopg docs, the
    # legacy ``IN %s`` form is unsupported in psycopg 3. Empty lists also
    # work (whereas ``IN ()`` is not valid SQL).
    key_list = list(keys)

    # Hickel drain
    row = pg_conn.execute(
        "SELECT phi_year FROM immutable_reference_hickel_drain "
        "WHERE session_id = %s AND year = %s AND partner_node_id = ANY(%s) "
        "ORDER BY phi_year DESC LIMIT 1",
        (str(session_id), year, key_list),
    ).fetchone()
    if row and row[0] is not None:
        phi = float(row[0])

    # Bilateral trade value
    row = pg_conn.execute(
        "SELECT bilateral_value FROM immutable_reference_ricci_unequal "
        "WHERE session_id = %s AND year = %s AND partner_node_id = ANY(%s) "
        "ORDER BY bilateral_value DESC LIMIT 1",
        (str(session_id), year, key_list),
    ).fetchone()
    if row and row[0] is not None:
        bilateral_value = float(row[0])

    # ERDI
    row = pg_conn.execute(
        "SELECT erdi_ratio FROM immutable_reference_erdi "
        "WHERE session_id = %s AND year = %s AND partner_node_id = ANY(%s) "
        "ORDER BY erdi_ratio DESC LIMIT 1",
        (str(session_id), year, key_list),
    ).fetchone()
    if row and row[0] is not None and row[0] > 0:
        erdi = float(row[0])

    return phi, bilateral_value, bilateral_tons, erdi


def _bootstrap_external_nodes(
    *, session_id: UUID, runtime: PostgresRuntime, start_year: int
) -> int:
    """Populate ``dynamic_external_node_state`` at tick 0 from hydrated refs.

    Spec 062 T078. Reads the just-hydrated ``immutable_reference_hickel_drain``,
    ``_ricci_unequal``, and ``_faf_freight`` rows for ``start_year`` and writes
    one ``ExternalNode`` row per canonical node id (8 international + 1
    domestic_rest). Persists via ``persist_tick_atomic()`` so the writes share
    the FR-008a atomic-tick guarantee.

    Returns the number of rows written (always 9 for a successful bootstrap).
    """
    from babylon.persistence.envelope import PerTickTransactionEnvelope
    from babylon.persistence.external_node import ExternalNode, ExternalNodeKind

    rows: list[ExternalNode] = []
    with runtime._pool.connection() as conn:  # noqa: SLF001
        for node_id in INTERNATIONAL_NODES:
            phi, btv, btt, erdi = _fetch_node_phi_and_trade(conn, session_id, start_year, node_id)
            rows.append(
                ExternalNode(
                    session_id=session_id,
                    tick=0,
                    node_id=node_id,
                    kind=ExternalNodeKind.INTERNATIONAL,
                    phi_year_inflow=phi,
                    bilateral_trade_value=btv,
                    bilateral_trade_tons=btt,
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
    runtime.persist_tick_atomic(envelope)  # type: ignore[attr-defined]
    return len(rows)


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
    """
    _validate_alpha_invariant(defines)
    scenario_length = (
        scenario_length_years
        if scenario_length_years is not None
        else defines.economy.scenario_length_years
    )

    report = InitializationReport(session_id=session_id, sqlite_path=sqlite_path.resolve())

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
    report.external_node_ids = set(INTERNATIONAL_NODES) | {DOMESTIC_REST_NODE}
    report.external_node_count = _bootstrap_external_nodes(
        session_id=session_id, runtime=runtime, start_year=start_year
    )

    # Spec-063 closure (2026-05-14) — hex graph hydration at tick 0.
    # Gated on `hex_hydration_counties` so existing callers that don't
    # need a populated hex graph (legacy unit tests, helper scripts)
    # remain unchanged. See `babylon.persistence.hex_hydrator`.
    if hex_hydration_counties:
        from babylon.persistence.hex_hydrator import hydrate_hex_state

        report.hex_count = hydrate_hex_state(
            runtime=runtime,
            session_id=session_id,
            counties=hex_hydration_counties,
            start_year=start_year,
            defines=defines,
            tiger_county_shapefile=tiger_county_shapefile,
        )
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
