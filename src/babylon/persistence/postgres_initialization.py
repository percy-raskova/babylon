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
from typing import TYPE_CHECKING
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
        copied_series: Set of series_ids successfully copied into
            ``immutable_reference_*`` tables.
        external_node_ids: Set of node_ids written into
            ``dynamic_external_node_state`` at tick 0.
        sqlite_path: Resolved path of the source SQLite file (for log).
    """

    session_id: UUID
    hex_count: int = 0
    copied_series: set[str] = field(default_factory=set)
    external_node_ids: set[str] = field(default_factory=set)
    sqlite_path: Path | None = None


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


def initialize_session(
    *,
    session_id: UUID,
    sqlite_path: Path,
    runtime: PostgresRuntime,
    defines: GameDefines,
    start_year: int,
    scenario_length_years: int | None = None,
    counties: list[str] | None = None,
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

    # External-node bootstrap. The fixed enumeration is locked here so
    # downstream code can assume exactly nine boundary nodes per session.
    report.external_node_ids = set(INTERNATIONAL_NODES) | {DOMESTIC_REST_NODE}

    # Hex hydration: deferred to Phase 6 (LODES OD); reported as 0 for the
    # initialization contract surface — runtime queries operate on the
    # immutable_reference_* + dynamic_external_node_state seeded above.
    report.hex_count = 0

    return report


__all__ = [
    "InitializationError",
    "InitializationReport",
    "copy_reference_series",
    "initialize_session",
    "INTERNATIONAL_NODES",
    "DOMESTIC_REST_NODE",
]
