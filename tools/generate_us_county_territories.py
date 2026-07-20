"""Generate the deterministic USScenario county-seed artifact.

Owner ruling 2026-07-19 (Amendment U / #39 T4 blocker adjudication): re-keying
``USScenario``'s territories from res-3 H3 hexes to counties needs real
per-county population + geography, never fabricated numbers -- but the
scenario builder (``engine/scenarios/_legacy.py::_create_us_territories``)
must stay reference-DB-free at build/test time (measured cost: ~6.6s per
national-scope population lookup via
:class:`babylon.engine.headless_runner.reference_data_cache.ReferenceDataCache`,
paid at >130 call sites across the test suite if done live -- e.g.
``tests/unit/web/test_engine_bridge.py``'s ``_make_mock_persistence()``).
Per the deterministic-data-artifacts doctrine (CI never touches the data
drive) -- the SAME doctrine that motivated
``src/babylon/data/game/business_seeds.json`` /
``tools/generate_business_seeds.py`` for the QCEW business seeds -- this
``tools/`` script precomputes the per-county rows from
``data/sqlite/marxist-data-3NF.sqlite`` into a committed, hash-stamped JSON
artifact (``src/babylon/data/game/us_county_territories.json``) that
``babylon.engine.scenarios.us_county_data`` reads at runtime.

**Scope**: the same national county universe the headless runner uses
(:func:`babylon.engine.headless_runner.scopes._load_national_fips` --
state fips < '60', excludes the synthetic ``{state}999`` rest-of-state
placeholders), FIPS-sorted.

**Population policy (follows the house consumer, byte-for-byte)**: Census
``fact_census_income`` household-count SUM is primary; QCEW
``fact_qcew_annual`` employment SUM x 0.33 is the fallback -- this is
literally :class:`~babylon.engine.headless_runner.reference_data_cache.
ReferenceDataCache`'s own resolution rule, reused directly (not
reimplemented) so the artifact can never drift from what
``WorldStateBridge`` already treats as the real per-county population.
``population_year`` is 2010: it matches ``WorldStateBridge.hydrate_initial``'s
default ``start_year`` and empirically has the best coverage of the national
scope among the years checked (2010/2015/2018/2019/2020) -- the exact
counties Census/QCEW genuinely never covers (AK/CT post-1990 geography
splits) are named in the committed artifact's own ``gaps`` list, not
restated here to avoid drift.

**Centroid policy**: ``dim_county_geometry.centroid_lat``/``centroid_lon``,
real TIGER centroids (NOT the fabricated hex-cell centroids the old h3 grid
used). A small number of scoped counties lack a geometry row (a different,
non-overlapping set from the population gap) -- also recorded in ``gaps``.

**Retired-FIPS dedup (2026-07-19, scout finding)**: ``dim_county`` carries
BOTH ``46113`` (Shannon County, SD) and ``46102`` (Oglala Lakota County, SD --
the same physical county, renamed by the Census Bureau in 2015) as separate
rows. Both pass ``_load_national_fips``'s scoping filter, so the raw national
scope double-counts this one county. :data:`_RETIRED_FIPS_SUPERSEDED` names
this one, verified, cited exclusion and drops the retired row (keeping the
modern successor) when both are present in the same extraction -- recorded
in the artifact's ``exclusions`` list, never silently dropped. This is a
declared, cited map, NOT generic rename detection: if a similar duplicate
surfaces later, the map is extended with its own citation, not inferred.
``engine.headless_runner.scopes._load_national_fips`` itself carries the
same latent double-count for the nationwide headless-runner path -- that is
a separate, pre-existing production defect, OUT of this script's scope
(flagged for a follow-up task, not fixed here).

Only the RAW reference-derived fields are baked into the artifact
(``fips``, ``county_name``, ``state_abbrev``, ``centroid_lat``/``lon``,
``population``). The pure, in-memory sector/rent/biocapacity/region
classification (``_classify_hex``/``_compute_metro_influence``/
``_get_region_name`` in ``_legacy.py``) stays runtime logic -- it needs no
DB access and predates this artifact (Wayne's untouched precedent uses the
identical hand-authored classification style), so precomputing its output
here would only bloat the artifact without adding real data.

Regeneration::

    poetry run python tools/generate_us_county_territories.py               # year 2010
    poetry run python tools/generate_us_county_territories.py --year 2019

The output is deterministic: counties are FIPS-sorted and every query is a
GROUP BY / ORDER BY over stable keys, so identical DB inputs yield an
identical artifact (identical ``content_hash``). Commit the regenerated
JSON and note the new hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from babylon.engine.headless_runner.reference_data_cache import ReferenceDataCache
from babylon.engine.headless_runner.scopes import DEFAULT_SQLITE_PATH, _load_national_fips
from babylon.reference.database import get_normalized_session_factory
from babylon.reference.schema import DimCounty, DimCountyGeometry, DimState

#: Matches WorldStateBridge.hydrate_initial's default start_year (bridge.py)
#: and empirically has the best national-scope Census/QCEW coverage among
#: the years checked at generation time (2010/2015/2018/2019/2020).
DEFAULT_POPULATION_YEAR = 2010

#: Retired FIPS -> modern successor FIPS for the SAME physical county, both
#: of which are present as separate `dim_county` rows (module docstring,
#: "Retired-FIPS dedup"). Verified empirically (scout finding, 2026-07-19):
#: 46113 = Shannon County SD (retired); 46102 = Oglala Lakota County SD
#: (renamed 2015 per Census Bureau change notice) -- the modern successor.
#: A declared, cited exclusion map ONLY -- no generic rename inference; if
#: another duplicate surfaces later, extend this map with its own citation.
_RETIRED_FIPS_SUPERSEDED: dict[str, str] = {
    "46113": "46102",  # Shannon County, SD -> Oglala Lakota County, SD (2015 rename)
}

_ARTIFACT_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "babylon"
    / "data"
    / "game"
    / "us_county_territories.json"
)


def _load_county_geo_rows(
    session_factory: Any,
) -> dict[str, tuple[str, str, float | None, float | None]]:
    """Real per-county name/state/centroid rows, FIPS-keyed.

    Returns ``{fips: (county_name, state_abbrev, centroid_lat, centroid_lon)}``.
    ``centroid_lat``/``centroid_lon`` are ``None`` for counties without a
    ``dim_county_geometry`` row.
    """
    with session_factory() as session:
        rows = (
            session.query(
                DimCounty.fips,
                DimCounty.county_name,
                DimState.state_abbrev,
                DimCountyGeometry.centroid_lat,
                DimCountyGeometry.centroid_lon,
            )
            .join(DimState, DimState.state_id == DimCounty.state_id)
            .outerjoin(DimCountyGeometry, DimCountyGeometry.county_id == DimCounty.county_id)
            .all()
        )
    return {
        fips: (
            county_name,
            state_abbrev,
            float(lat) if lat is not None else None,
            float(lon) if lon is not None else None,
        )
        for fips, county_name, state_abbrev, lat, lon in rows
    }


def _content_hash(counties: list[dict[str, Any]]) -> str:
    """SHA-256 over the canonical (sorted-key, compact) county-rows payload."""
    canonical = json.dumps(counties, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _dedup_retired_fips(scope_fips: frozenset[str]) -> tuple[frozenset[str], list[dict[str, str]]]:
    """Drop retired FIPS whose modern successor is present in the same scope.

    Only drops a key of :data:`_RETIRED_FIPS_SUPERSEDED` when its successor
    value is ALSO present -- if the successor is somehow absent, the retired
    row is kept rather than silently losing the county entirely.

    Returns:
        ``(deduped_scope, exclusions)`` where ``exclusions`` names each
        dropped FIPS + its successor + a citation, for the artifact's
        ``exclusions`` list.
    """
    exclusions: list[dict[str, str]] = []
    dropped: set[str] = set()
    for retired, successor in _RETIRED_FIPS_SUPERSEDED.items():
        if retired in scope_fips and successor in scope_fips:
            dropped.add(retired)
            exclusions.append(
                {
                    "fips": retired,
                    "successor_fips": successor,
                    "reason": (
                        f"retired FIPS superseded by {successor} (same physical county, "
                        "renamed per Census Bureau change notice); both rows present in "
                        "dim_county -- dropping the retired one to prevent double-counting"
                    ),
                }
            )
    return frozenset(scope_fips - dropped), exclusions


def build_payload(
    year: int = DEFAULT_POPULATION_YEAR,
    sqlite_path: Path = DEFAULT_SQLITE_PATH,
) -> dict[str, Any]:
    """Build the full county-seed artifact payload from the reference DB."""
    raw_scope_fips = _load_national_fips(sqlite_path)
    scope_fips, exclusions = _dedup_retired_fips(raw_scope_fips)
    geo_rows = _load_county_geo_rows(get_normalized_session_factory())

    cache = ReferenceDataCache(sqlite_path)
    cache.hydrate(scope_fips=scope_fips, year_set=frozenset({year}))

    counties: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    for fips in sorted(scope_fips):
        county_name, state_abbrev, lat, lon = geo_rows.get(fips, (fips, "", None, None))

        population = cache.lookup_population(fips, year)
        if population is None:
            gaps.append(
                {
                    "fips": fips,
                    "field": "population",
                    "reason": f"no Census or QCEW row for county={fips} year={year}",
                }
            )

        if lat is None or lon is None:
            gaps.append(
                {
                    "fips": fips,
                    "field": "centroid",
                    "reason": f"no dim_county_geometry row for county={fips}",
                }
            )

        counties.append(
            {
                "fips": fips,
                "county_name": county_name,
                "state_abbrev": state_abbrev,
                "centroid_lat": lat,
                "centroid_lon": lon,
                "population": population,
            }
        )

    # Self-check (2026-07-19 scout finding): no retired FIPS from the
    # exclusion map may survive dedup -- a survivor here means the drop
    # logic failed silently, which must fail LOUD (Constitution III.11)
    # rather than ship a duplicated county.
    final_fips = {c["fips"] for c in counties}
    survivors = final_fips & set(_RETIRED_FIPS_SUPERSEDED)
    if survivors:
        raise AssertionError(
            f"retired FIPS {sorted(survivors)} survived _dedup_retired_fips -- "
            "dedup logic is broken, refusing to write a duplicated artifact"
        )

    return {
        "schema_version": 1,
        "source": {
            "dataset": (
                "dim_county + dim_county_geometry + fact_census_income (Census) "
                "with fact_qcew_annual (QCEW) fallback"
            ),
            "reference_db": "data/sqlite/marxist-data-3NF.sqlite",
            "scope_rule": (
                "national (mirrors engine.headless_runner.scopes._load_national_fips: "
                "state fips < '60', excludes {state}999 placeholders) minus the "
                "retired-FIPS dedup (see 'exclusions')"
            ),
            "population_year": year,
            "population_policy": (
                "Census fact_census_income household_count SUM primary; QCEW "
                "fact_qcew_annual employment SUM x 0.33 fallback (matches "
                "ReferenceDataCache._resolve_population byte-for-byte -- reused "
                "directly, not reimplemented)"
            ),
            "county_count": len(counties),
        },
        "content_hash": _content_hash(counties),
        "counties": counties,
        "gaps": gaps,
        "exclusions": exclusions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--year",
        type=int,
        default=DEFAULT_POPULATION_YEAR,
        help=f"Census/QCEW year to resolve population from (default: {DEFAULT_POPULATION_YEAR})",
    )
    args = parser.parse_args()

    payload = build_payload(args.year)
    _ARTIFACT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {_ARTIFACT_PATH}")
    print(
        f"  counties={payload['source']['county_count']}  year={payload['source']['population_year']}"
        f"  content_hash={payload['content_hash'][:16]}..."
    )
    print(f"  exclusions={len(payload['exclusions'])}")
    for excl in payload["exclusions"]:
        print(f"    {excl['fips']} -> {excl['successor_fips']}: {excl['reason']}")
    print(f"  gaps={len(payload['gaps'])}")
    for gap in payload["gaps"]:
        print(f"    {gap['fips']} [{gap['field']}]: {gap['reason']}")


if __name__ == "__main__":
    main()
