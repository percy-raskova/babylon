"""Generate the deterministic Business-org seed artifact from real QCEW data.

Owner ruling 2026-07-19: the canonical playable scenarios (``us_nationwide`` /
``wayne_county``) must seed :class:`~babylon.models.entities.organization.Business`
organizations sized from REAL Bureau of Labor Statistics QCEW employment, never
fabricated numbers. The scenario builders are pure-hardcode (they take no
reference-DB session at build time), so — per the deterministic-data-artifacts
doctrine (CI never touches the data drive) — this ``tools/`` script precomputes
the aggregates from ``data/sqlite/marxist-data-3NF.sqlite`` into a committed,
hash-stamped JSON artifact (``src/babylon/data/game/business_seeds.json``) that
the builders read at runtime.

**Imputation / ownership policy (follows the house consumer).** Employment is
taken from PRIVATE ownership (``own_code='5'``) only — a ``Business`` models
privately-owned capital employing wage labour; government agencies are
Institutions/StateApparatus, not businesses — folding the 6-digit NAICS leaves
(the only level populated at county grain) up to the 20 combined 2-digit sector
labels in :data:`NAICS_2DIGIT_SECTORS` via ``dim_industry.sector_code``. This
mirrors :meth:`SQLiteQCEWCountyNAICSSource.get_county_employment_by_naics`
byte-for-byte for the county scope (that method is REUSED directly), including
its policy of INCLUDING BLS-imputed leaves (``is_imputed=1``): a suppressed
county-industry cell is real employment the DB has imputed, and excluding it
would undercount the sector. ``dim_industry.industry_title`` values are
generated placeholders ("Industry 62") and are NEVER used — the real 2-digit
sector titles come from :data:`_SECTOR_TITLES` (the in-repo NAICS_2DIGIT_SECTORS
comment vocabulary, promoted to data here).

Regeneration::

    uv run python tools/generate_business_seeds.py          # latest DB year
    uv run python tools/generate_business_seeds.py --year 2023

The output is deterministic: every query is ``ORDER BY`` employment DESC then
sector label ASC, so identical DB inputs yield an identical artifact (identical
``content_hash``). Commit the regenerated JSON and note the new hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import bindparam, text

from babylon.domain.economics.throughput.adapters import (
    NAICS_2DIGIT_SECTORS,
    SQLiteQCEWCountyNAICSSource,
    _sector_codes_for,
)
from babylon.reference.database import get_normalized_session_factory

# Real 2-digit NAICS sector titles. These are the short-form labels that live as
# inline comments beside each code in ``NAICS_2DIGIT_SECTORS``
# (``domain/economics/throughput/adapters.py``), promoted here to accessible data
# so the seed artifact carries a real title (never the placeholder
# ``dim_industry.industry_title``). Keyed by the same combined labels the adapter
# folds to.
_SECTOR_TITLES: dict[str, str] = {
    "11": "Agriculture",
    "21": "Mining",
    "22": "Utilities",
    "23": "Construction",
    "31-33": "Manufacturing",
    "42": "Wholesale",
    "44-45": "Retail",
    "48-49": "Transportation",
    "51": "Information",
    "52": "Finance",
    "53": "Real Estate",
    "54": "Professional Services",
    "55": "Management",
    "56": "Admin/Support",
    "61": "Education",
    "62": "Healthcare",
    "71": "Entertainment",
    "72": "Accommodation/Food",
    "81": "Other Services",
    "92": "Government",
}

# Number of top sectors seeded per scope (owner-tunable; see ADR086 for the
# event-volume rationale — small K keeps the total org count far under the
# engine's max_orgs=1000 layer0/OODA cap and the per-tick turn_resolution
# payload trivial).
TOP_K = 5

WAYNE_COUNTY_FIPS = "26163"

_ARTIFACT_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "babylon"
    / "data"
    / "game"
    / "business_seeds.json"
)


def _latest_year(session: Any) -> int:
    """Return the most recent year with private 6-digit QCEW rows loaded."""
    row = session.execute(
        text(
            "SELECT MAX(dt.year) FROM fact_qcew_annual f "
            "JOIN dim_time dt ON f.time_id = dt.time_id "
            "JOIN dim_industry di ON f.industry_id = di.industry_id "
            "JOIN dim_ownership o ON f.ownership_id = o.ownership_id "
            "WHERE o.is_private = 1 AND di.naics_level = 6"
        )
    ).scalar()
    if row is None:
        raise RuntimeError("No private 6-digit QCEW rows found in the reference DB")
    return int(row)


def _national_employment_by_sector(session: Any, year: int) -> dict[str, int]:
    """Aggregate PRIVATE 6-digit leaves nationwide, folded to 2-digit labels.

    Mirrors ``get_county_employment_by_naics``'s policy (private ownership,
    level-6 leaves, ``sector_code`` -> combined label) but summed over ALL
    counties for the national scope.
    """
    code_to_label = {
        code: label for label in NAICS_2DIGIT_SECTORS for code in _sector_codes_for(label)
    }
    stmt = text(
        "SELECT di.sector_code, SUM(f.employment) AS emp "
        "FROM fact_qcew_annual f "
        "JOIN dim_industry di ON f.industry_id = di.industry_id "
        "JOIN dim_ownership o ON f.ownership_id = o.ownership_id "
        "JOIN dim_time dt ON f.time_id = dt.time_id "
        "WHERE o.is_private = 1 AND di.naics_level = 6 AND dt.year = :year "
        "  AND di.sector_code IN :codes "
        "GROUP BY di.sector_code"
    ).bindparams(bindparam("codes", tuple(code_to_label), expanding=True), year=year)
    rows = session.execute(stmt).all()
    result: dict[str, int] = {}
    for sector_code, emp in rows:
        if emp is None:
            continue
        label = code_to_label[sector_code]
        result[label] = result.get(label, 0) + int(emp)
    return result


def _top_k(employment_by_label: dict[str, int], k: int) -> list[dict[str, Any]]:
    """Deterministic top-K sectors: employment DESC, then label ASC."""
    ordered = sorted(employment_by_label.items(), key=lambda kv: (-kv[1], kv[0]))
    sectors: list[dict[str, Any]] = []
    for rank, (label, emp) in enumerate(ordered[:k], start=1):
        sectors.append(
            {
                "rank": rank,
                "naics_2digit": label,
                "sector_title": _SECTOR_TITLES[label],
                "employment_count": int(emp),
            }
        )
    return sectors


def _content_hash(scopes: dict[str, Any]) -> str:
    """SHA-256 over the canonical (sorted-key, compact) scope payload."""
    canonical = json.dumps(scopes, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_payload(year: int | None = None) -> dict[str, Any]:
    """Build the full seed-artifact payload from the reference DB."""
    session_factory = get_normalized_session_factory()
    source = SQLiteQCEWCountyNAICSSource(session_factory)

    with session_factory() as session:
        resolved_year = year if year is not None else _latest_year(session)
        national = _national_employment_by_sector(session, resolved_year)

    wayne = source.get_county_employment_by_naics(WAYNE_COUNTY_FIPS, resolved_year)

    scopes = {
        "US": {
            "display_name": "United States",
            "id_prefix": "BIZ_US_",
            "sectors": _top_k(national, TOP_K),
        },
        WAYNE_COUNTY_FIPS: {
            "display_name": "Wayne County",
            "id_prefix": "BIZ_WAYNE_",
            "sectors": _top_k(wayne, TOP_K),
        },
    }
    return {
        "schema_version": 1,
        "source": {
            "dataset": "BLS QCEW annual (fact_qcew_annual)",
            "reference_db": "data/sqlite/marxist-data-3NF.sqlite",
            "year": resolved_year,
            "ownership": "private (own_code=5)",
            "naics_level_aggregated": "6-digit leaves -> 2-digit combined labels",
            "imputation_policy": "includes BLS-imputed leaves (house policy)",
            "top_k": TOP_K,
        },
        "content_hash": _content_hash(scopes),
        "scopes": scopes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="QCEW year to aggregate (default: latest year present in the DB)",
    )
    args = parser.parse_args()

    payload = build_payload(args.year)
    _ARTIFACT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {_ARTIFACT_PATH}")
    print(f"  year={payload['source']['year']}  content_hash={payload['content_hash'][:16]}...")
    for scope, entry in payload["scopes"].items():
        print(f"  [{scope}] {entry['display_name']}:")
        for s in entry["sectors"]:
            print(
                f"    {s['rank']}. {s['sector_title']:22s} ({s['naics_2digit']:>5s})"
                f"  employment={s['employment_count']:,}"
            )


if __name__ == "__main__":
    main()
