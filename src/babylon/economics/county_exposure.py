"""County import-exposure map loader for the imperial-rent Φ distribution (spec-101).

Reads spec-100's ``fact_county_exposure_by_external`` reference table and produces
the ``{county_fips: weight}`` map that
:func:`babylon.engine.systems.phi_distribution.distribute_phi_week_to_counties`
consumes to split a bloc's weekly imperial-rent inflow across US counties.

Two spec-101 decisions are realised here (see ``specs/101-trade-activation``):

- **Bloc-invariance (D-exposure)**: spec-100 stores per-bloc rows, but the county
  distribution is identical across all eight ``is_region=1`` blocs (research R6;
  verified: 0 differing weights). This loader therefore reads ONE bloc's map and
  the caller broadcasts it to every engine external node.
- **Scope renormalisation (D2)**: a scoped run (e.g. Michigan) is a strict subset
  of the ~3,100 nationally-weighted counties, so the filtered weights sum to less
  than 1.0. ``distribute_phi_week_to_counties`` requires a unit sum (it rejects a
  non-unit sum rather than silently renormalise, Constitution III.1). This loader
  renormalises the *present* scope weights to sum to 1.0 — an explicit
  caller-side study-area projection: "the study area receives the full bloc
  Φ_week, split by relative intra-scope exposure." At national scope this is a
  near-no-op. It is the projection the conservation identity
  (``Σ DRAIN_EDGE ≡ Φ_week`` per bloc) requires.

See Also:
    :func:`babylon.engine.systems.phi_distribution.distribute_phi_week_to_counties`.
    ``specs/100-county-exposure`` research R6; ``specs/101-trade-activation`` D2.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Collection
from pathlib import Path

__all__ = ["CountyExposureUnavailableError", "load_county_exposure_map"]


class CountyExposureUnavailableError(RuntimeError):
    """Raised when no county-exposure rows exist for the requested year/scope.

    A hard failure (never a silent empty map): a missing exposure table or an
    empty scope means the Φ distribution cannot run, which the operator must
    fix (run ``mise run data:exposure``) rather than silently drain nothing.
    """


def _resolve_annual_time_id(conn: sqlite3.Connection, year: int) -> int:
    """Return the annual ``dim_time.time_id`` for ``year`` (``is_annual = 1``).

    Args:
        conn: Read-only SQLite connection to the reference DB.
        year: Calendar year (e.g. 2010).

    Returns:
        The annual ``time_id``.

    Raises:
        CountyExposureUnavailableError: If no annual ``time_id`` exists for
            ``year``.
    """
    row = conn.execute(
        "SELECT time_id FROM dim_time WHERE year = ? AND is_annual = 1 ORDER BY time_id LIMIT 1",
        (year,),
    ).fetchone()
    if row is None or row[0] is None:
        raise CountyExposureUnavailableError(
            f"No annual dim_time.time_id for year={year}; cannot load county exposure."
        )
    return int(row[0])


def load_county_exposure_map(
    *,
    sqlite_path: Path,
    year: int,
    scope_fips: Collection[str] | None = None,
) -> dict[str, float]:
    """Load the bloc-invariant county-exposure map, renormalised to the scope.

    Reads ``fact_county_exposure_by_external`` for the annual ``time_id`` of
    ``year`` and a single bloc (the smallest ``external_country_id`` present —
    the map is bloc-invariant), joins ``dim_county`` for the 5-digit FIPS, filters
    to ``scope_fips`` when given, and renormalises the present weights to sum to
    1.0 (D2). Counties are iterated in sorted-FIPS order for determinism.

    Args:
        sqlite_path: Path to ``marxist-data-3NF.sqlite``.
        year: Calendar year whose annual exposure to load (the run's start year).
        scope_fips: 5-digit FIPS codes to restrict to (the run's scope). When
            ``None``, all exposed counties are returned (national scope).

    Returns:
        ``{county_fips: weight}`` with the weights summing to 1.0 within 1e-9.

    Raises:
        CountyExposureUnavailableError: If the reference file is missing, the
            year has no annual ``time_id``, or no exposure rows fall inside the
            scope (an empty map would make the Φ distribution a silent no-op).
    """
    if not sqlite_path.is_file():
        raise CountyExposureUnavailableError(
            f"SQLite reference DB not found at {sqlite_path}; cannot load county exposure."
        )

    with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as conn:
        time_id = _resolve_annual_time_id(conn, year)

        # Bloc-invariant: read the single smallest-id bloc present for this year.
        bloc_row = conn.execute(
            "SELECT MIN(external_country_id) FROM fact_county_exposure_by_external "
            "WHERE time_id = ?",
            (time_id,),
        ).fetchone()
        if bloc_row is None or bloc_row[0] is None:
            raise CountyExposureUnavailableError(
                f"fact_county_exposure_by_external has no rows for year={year} "
                f"(time_id={time_id}); run `mise run data:exposure`."
            )
        bloc_id = int(bloc_row[0])

        rows = conn.execute(
            "SELECT dc.fips, ce.weight "
            "FROM fact_county_exposure_by_external ce "
            "JOIN dim_county dc ON dc.county_id = ce.county_id "
            "WHERE ce.time_id = ? AND ce.external_country_id = ? "
            "ORDER BY dc.fips",
            (time_id, bloc_id),
        ).fetchall()

    scope_set = {str(f) for f in scope_fips} if scope_fips is not None else None
    raw: dict[str, float] = {}
    for fips, weight in rows:
        fips_str = str(fips)
        if scope_set is not None and fips_str not in scope_set:
            continue
        w = float(weight)
        if w <= 0.0:
            continue
        raw[fips_str] = w

    total = sum(raw.values())
    if not raw or total <= 0.0:
        scope_note = "national scope" if scope_set is None else f"scope={sorted(scope_set)}"
        raise CountyExposureUnavailableError(
            f"No positive county-exposure weights for year={year}, {scope_note}. "
            f"The Φ distribution would drain nothing — check the scope counties "
            f"against fact_county_exposure_by_external."
        )

    # Scope renormalisation (D2): present weights → unit sum. Iterate sorted for
    # a deterministic map ordering (dict preserves insertion order).
    return {fips: raw[fips] / total for fips in sorted(raw)}
