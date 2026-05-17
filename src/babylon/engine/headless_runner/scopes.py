"""Predefined scope resolver for the headless simulation runner.

Resolves a scope name like ``"michigan-canada"`` into a concrete
``(scope_fips, external_node_ids)`` pair. The four canonical scopes
match ``contracts/cli_contract.yaml``.

The Michigan FIPS list is enumerated from
``data/sqlite/marxist-data-3NF.sqlite`` (``dim_county`` filtered to state
26, excluding the synthetic ``26999`` rest-of-state code). The national
list is resolved lazily by querying SQLite at scope-resolution time —
hard-coding ~3,200 codes here would create unnecessary maintenance churn
when TIGER vintages bump.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import NamedTuple

DEFAULT_SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite")


class Scope(NamedTuple):
    """Concrete scope resolution: county FIPS + external boundary nodes."""

    scope_fips: frozenset[str]
    external_node_ids: frozenset[str]


# Canonical 83 Michigan county FIPS codes (state 26, excluding the
# synthetic ``26999`` rest-of-state code). Pulled from dim_county on
# 2026-05-14 against the TIGER 2024 vintage.
MICHIGAN_FIPS: frozenset[str] = frozenset(
    {
        "26001",
        "26003",
        "26005",
        "26007",
        "26009",
        "26011",
        "26013",
        "26015",
        "26017",
        "26019",
        "26021",
        "26023",
        "26025",
        "26027",
        "26029",
        "26031",
        "26033",
        "26035",
        "26037",
        "26039",
        "26041",
        "26043",
        "26045",
        "26047",
        "26049",
        "26051",
        "26053",
        "26055",
        "26057",
        "26059",
        "26061",
        "26063",
        "26065",
        "26067",
        "26069",
        "26071",
        "26073",
        "26075",
        "26077",
        "26079",
        "26081",
        "26083",
        "26085",
        "26087",
        "26089",
        "26091",
        "26093",
        "26095",
        "26097",
        "26099",
        "26101",
        "26103",
        "26105",
        "26107",
        "26109",
        "26111",
        "26113",
        "26115",
        "26117",
        "26119",
        "26121",
        "26123",
        "26125",
        "26127",
        "26129",
        "26131",
        "26133",
        "26135",
        "26137",
        "26139",
        "26141",
        "26143",
        "26145",
        "26147",
        "26149",
        "26151",
        "26153",
        "26155",
        "26157",
        "26159",
        "26161",
        "26163",
        "26165",
    }
)

# Detroit tri-county: Wayne, Oakland, Macomb (spec-063 fixture).
DETROIT_TRI_COUNTY_FIPS: frozenset[str] = frozenset({"26163", "26125", "26099"})


class UnknownScopeError(ValueError):
    """Raised when an unrecognized scope name is requested."""


def resolve_scope(name: str, *, sqlite_path: Path = DEFAULT_SQLITE_PATH) -> Scope:
    """Resolve a predefined scope name to its concrete FIPS + externals.

    Args:
        name: One of ``michigan-canada``, ``michigan-statewide-no-canada``,
            ``detroit-tri-county``, ``national``.
        sqlite_path: Override for the SQLite reference DB. Only consulted
            when ``name == "national"`` — other scopes are fully
            resolvable from the hard-coded literals above.

    Returns:
        Scope tuple with ``scope_fips`` and ``external_node_ids``.

    Raises:
        UnknownScopeError: If ``name`` is not a recognized scope.
        FileNotFoundError: If ``name == "national"`` and ``sqlite_path``
            does not exist.
    """
    if name == "michigan-canada":
        return Scope(MICHIGAN_FIPS, frozenset({"canada"}))
    if name == "michigan-statewide-no-canada":
        return Scope(MICHIGAN_FIPS, frozenset())
    if name == "detroit-tri-county":
        return Scope(DETROIT_TRI_COUNTY_FIPS, frozenset({"canada"}))
    if name == "national":
        return Scope(_load_national_fips(sqlite_path), frozenset({"canada", "china"}))
    raise UnknownScopeError(
        f"Unknown scope {name!r}; expected one of: "
        "michigan-canada, michigan-statewide-no-canada, "
        "detroit-tri-county, national"
    )


def _load_national_fips(sqlite_path: Path) -> frozenset[str]:
    """Read US-county FIPS from the SQLite reference DB.

    Excludes Pacific territories (state codes ≥60) and synthetic rest-of-
    state placeholders (``\\d{2}999``).
    """
    if not sqlite_path.exists():
        raise FileNotFoundError(
            f"SQLite reference DB not found at {sqlite_path} (needed to resolve --scope=national)."
        )
    with sqlite3.connect(sqlite_path) as conn:
        cur = conn.execute(
            "SELECT fips FROM dim_county "
            "WHERE substr(fips, 1, 2) < '60' "
            "AND substr(fips, 3, 3) != '999' "
            "ORDER BY fips"
        )
        return frozenset(row[0] for row in cur.fetchall())


__all__ = [
    "DEFAULT_SQLITE_PATH",
    "DETROIT_TRI_COUNTY_FIPS",
    "MICHIGAN_FIPS",
    "Scope",
    "UnknownScopeError",
    "resolve_scope",
]
