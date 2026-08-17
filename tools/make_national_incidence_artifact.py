#!/usr/bin/env python3
"""National-incidence artifact generator — sha-pinned source access + the
derivation skeleton (#334 Phase 0, T2).

Plan: ``docs/superpowers/plans/2026-08-17-334-incidence-artifact.md`` §3 (the
derivation), §2 (A2/A3 shapes T2 does not yet emit). **This module implements
plan §3's steps 1-2** (T2) — resolving the three ``universe_variant`` FIPS
sets and pulling the filtered poverty cells — **plus T3a's four
arithmetic-law guards** (:func:`ratio_of_sums` G1, :func:`classify_zero_denominator`
G2, :func:`assert_t_pole_exactness` G6, :func:`overlap_upper_bound` G8) —
**plus T3b's three absence/small-count guards** (:func:`damp` +
:func:`compute_damped_sigma` G3, :func:`classify_suppression` +
:func:`classify_absence` G4, :func:`reconcile_absence_counts` +
:func:`assert_no_pine_ridge_imputation` G5): separate pure functions, not yet
wired into a per-county measure pipeline. The full step 3-10 derivation/
emission lands in T4; G7 already shipped with T1
(``tools/make_fips_vintage_crosswalk.py``).

ADR098 circularity, resolved the same way T1 states it: these are
**second-order products** derived from **registered parquet sources**
(``dist/data-artifacts/*.parquet``), never from the sqlite build product
directly. **There is no ``--from-sqlite`` derivation path.** The sqlite file
(``data/sqlite/marxist-data-3NF.sqlite``) is touched in exactly two places,
neither of which is "derive the poverty measures from it":

1. ``--export-source`` mode (:func:`export_source_tables`) — PRODUCES the
   registered parquet sources by calling
   ``make_data_artifacts.export_table_parquet``, the ONLY sanctioned
   parquet-writing path (``tools/make_data_artifacts.py:389-409``). This is
   how a fresh box materializes ``dist/data-artifacts/fact_census_poverty.
   parquet`` — ``dist/`` is gitignored, so the parquet is absent until this
   runs. Hard-gated on the pinned SQLite runtime (mirrors
   ``tools/build_reference_db.py``'s identical gate) — an off-pin export
   risks producing bytes that don't match the registered
   ``data-artifacts.yaml`` sha256 pins, which is exactly the kind of silent
   drift step 2 below exists to catch, so it's caught earlier and louder
   here instead. Run inside ``mise run nix -- ...``
   (``docs/how-to/reference-data-pipeline.rst:10-17``).
2. The ``scopes`` universe (:func:`_scopes_universe`) reuses
   ``babylon.engine.headless_runner.scopes._load_national_fips`` directly —
   the same call ``tools/make_fips_vintage_crosswalk.py`` (T1) already
   makes. This is universe-**membership** enumeration against
   ``dim_county`` (which FIPS codes exist), never a ``fact_census_poverty``
   **measure** read. It is not the circularity the ``--from-sqlite``
   prohibition closes off.

Every actual **derivation** read — the filtered poverty cells
(:func:`read_filtered_poverty_cells`) and the ``unrestricted`` universe
(:func:`_unrestricted_universe`) — reads ONLY the sha-pinned parquet sources,
verified by :func:`verify_source_provenance` BEFORE any of those reads
happen. Mismatch or a missing source raises :class:`SourceProvenanceError`,
loud, no fallback.

**Pinned filters** (OQ11: pinned 2019 vintage, never re-cut — the extractor
that could re-cut a different vintage was deleted,
``data-catalog.yaml:1096``): ``time_id=23`` (2019), ``category_id in {1, 2}``
(1 = ``B17001_001`` "Total" = the universe *u*; 2 = ``B17001_002``
"below poverty" = *b*), ``race_id in {1, 2, 3, 4, 9, 10}`` (1=T Total,
2=A White alone, 3=B Black, 4=C AIAN/Indigenous, 9=H White-non-Hispanic/
settler reference, 10=I Hispanic/Chicano — **note the pole-letter trap**:
the charter's B/C/I nation-pole letters are NOT these census race codes;
Chicano resolves to census ``I`` (race_id 10), Indigenous to census ``C``
(race_id 4). Plan §0.).

**A1 applied** (step 1's other half, plan §3): the checked-in crosswalk CSV
(``src/babylon/data/reference/national/county_fips_vintage_crosswalk.csv``,
T1) is **the authority** — loaded directly by :func:`load_crosswalk`, never
re-derived from ``tools/make_fips_vintage_crosswalk.py``'s in-module
``CROSSWALK_ROWS`` constant. :func:`resolve_query_fips` is the concrete
application: a ``recoverable=true`` row substitutes its ``fips_acs2019``
target (Bedford ``51515`` -> ``51019``) as the FIPS to query
``fact_census_poverty`` under; every other engine-universe county —
including ``DECLARED_HOLE`` rows (``46102``, ``02158``) and the
non-recoverable ``SPLIT_UNRESOLVED``/``REORGANIZATION_UNRESOLVED`` rows
(``02063``, ``02066``, the 9 CT planning regions) — queries its own native
FIPS, which for those rows simply returns no data. **T1's report is binding
here**: 02063/02066/02158 must NOT be treated as crosswalk-recovered.
Classifying *why* a county has no data (``ROW_ABSENT`` vs ``DECLARED_HOLE``
vs ``SUPPRESSED``) is G4/T3b's job, not this resolver's — T2 computes
nothing.

**Universe-variant naming, a verified deviation from the plan's literal
strings:** plan §2 A3 names the three ``universe_variant`` enum values
``artifact_3153``, ``scopes_3140``, ``unrestricted_3218``. T1 already
measured the scopes (resolver) universe at **3,156**, not 3,140
(``task-1-report.md``; re-confirmed directly against the read-only
reference DB this pass — see ``task-2-report.md``). Rather than propagate a
verified-wrong count into an identifier three tasks are going to read,
:func:`resolve_universe_variants` returns plain semantic keys (``artifact``
/ ``scopes`` / ``unrestricted``) with the real measured size available from
``len(variant.fips)`` — T4 (A3's emitter) owns picking the final
``universe_variant`` column strings and should use the measured number.

Usage::

    # one-time, pinned-toolchain only — materializes the registered parquet
    # sources this derivation reads (dist/ is gitignored; absent on a fresh box)
    mise run nix -- uv run python tools/make_national_incidence_artifact.py --export-source

    # the skeleton itself (steps 1-2; prints sizes, computes no measures)
    uv run python tools/make_national_incidence_artifact.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

from pyarrow import dataset as ds  # type: ignore[import-untyped]
from pyarrow import parquet as pq

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_data_artifacts  # type: ignore[import-not-found]  # noqa: E402
from build_reference_db import PINNED_SQLITE_VERSION  # type: ignore[import-not-found]  # noqa: E402

from babylon.engine.headless_runner.scopes import (  # noqa: E402
    DEFAULT_SQLITE_PATH,
    _load_national_fips,
)

ENGINE_TERRITORIES_JSON = _REPO_ROOT / "src/babylon/data/game/us_county_territories.json"
CROSSWALK_CSV = _REPO_ROOT / "src/babylon/data/reference/national/county_fips_vintage_crosswalk.csv"
DIST_DIR = _REPO_ROOT / "dist/data-artifacts"
MANIFEST_PATH = _REPO_ROOT / "data-artifacts.yaml"

#: The four registered parquet sources this derivation reads (plan §0 input
#: table; data-artifacts.yaml:291-301, 469-489, 726-736).
SOURCE_TABLES: tuple[str, ...] = (
    "fact_census_poverty",
    "dim_race",
    "dim_county",
    "dim_poverty_category",
)

#: OQ11 pinned vintage: 2019.
TIME_ID = 23
#: 1 = B17001_001 "Total" (universe u); 2 = B17001_002 "below poverty" (b).
CATEGORY_IDS: tuple[int, ...] = (1, 2)
#: T, A(White), B(Black), C/AIAN(Indigenous), H(White-non-Hispanic/settler
#: reference), I(Hispanic/Chicano). See module docstring's pole-letter trap note.
RACE_IDS: tuple[int, ...] = (1, 2, 3, 4, 9, 10)


class ArtifactGenerationError(Exception):
    """A generation or verification step failed loudly. No fallback."""


class SourceProvenanceError(ArtifactGenerationError):
    """Step 2: a source parquet's sha256 does not match the
    data-artifacts.yaml pin, or the source/manifest entry is missing."""


class UnpinnedToolchainError(ArtifactGenerationError):
    """``--export-source`` was invoked off the pinned SQLite runtime."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest_pins(names: tuple[str, ...], manifest_path: Path) -> dict[str, str]:
    """Read sha256 pins for ``names`` directly out of ``data-artifacts.yaml``
    (or a test double with the same ``artifacts: [{name, sha256}, ...]``
    shape) — no hand-typed duplicate hash strings in this module (the same
    "never hand-type a sha256" discipline
    ``docs/how-to/reference-data-pipeline.rst:63-65`` states for newly
    registered artifacts, applied here to reading already-registered ones).

    :raises ArtifactGenerationError: any requested ``name`` has no manifest entry.
    """
    import yaml

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    by_name = {entry["name"]: entry for entry in manifest["artifacts"]}
    missing = [name for name in names if name not in by_name]
    if missing:
        msg = f"{manifest_path}: no artifact entry for {missing}"
        raise ArtifactGenerationError(msg)
    return {name: str(by_name[name]["sha256"]) for name in names}


def export_source_tables(
    sqlite_path: Path = DEFAULT_SQLITE_PATH,
    *,
    dist_dir: Path = DIST_DIR,
    tables: tuple[str, ...] = SOURCE_TABLES,
) -> dict[str, Path]:
    """Step 1: ``--export-source`` mode.

    Opens the reference DB read-only (``mode=ro``, ``uri=True``) and calls
    ``make_data_artifacts.export_table_parquet`` — the ONLY sanctioned
    parquet-writing path — once per table in ``tables``. This PRODUCES the
    registered parquet sources; it never reads them for derivation (that's
    every other function in this module, all of which read only the
    resulting parquet files).

    :raises UnpinnedToolchainError: the runtime SQLite isn't the pinned
        version — an off-pin export risks bytes that don't match the
        registered sha256 pins.
    :raises ArtifactGenerationError: ``sqlite_path`` does not exist.
    """
    if sqlite3.sqlite_version != PINNED_SQLITE_VERSION:
        msg = (
            f"--export-source requires the pinned SQLite runtime "
            f"({PINNED_SQLITE_VERSION}); got {sqlite3.sqlite_version}. Run inside "
            "`mise run nix -- ...` (docs/how-to/reference-data-pipeline.rst:10-17) — "
            "an off-pin export risks producing bytes that don't match the registered "
            "data-artifacts.yaml sha256 pins."
        )
        raise UnpinnedToolchainError(msg)
    if not sqlite_path.exists():
        msg = f"reference DB not found: {sqlite_path}"
        raise ArtifactGenerationError(msg)

    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    out_paths: dict[str, Path] = {}
    try:
        for table in tables:
            dest = dist_dir / f"{table}.parquet"
            rows, size = make_data_artifacts.export_table_parquet(conn, table, dest)
            sha = _sha256_file(dest)
            print(
                f"[national-incidence] exported {table}: {rows} rows, {size} bytes, "
                f"sha256={sha} -> {dest}"
            )
            out_paths[table] = dest
    finally:
        conn.close()
    return out_paths


def verify_source_provenance(
    dist_dir: Path = DIST_DIR,
    *,
    manifest_path: Path = MANIFEST_PATH,
    tables: tuple[str, ...] = SOURCE_TABLES,
) -> dict[str, Path]:
    """Step 2: hard-fail on provenance drift.

    Computes each source parquet's sha256 and compares it to the
    ``data-artifacts.yaml`` pin BEFORE any derivation read. Mismatch or
    absence raises :class:`SourceProvenanceError`, loud, no fallback — no
    "proceed with a warning" path exists.
    """
    pins = _load_manifest_pins(tables, manifest_path)
    verified: dict[str, Path] = {}
    for table in tables:
        path = dist_dir / f"{table}.parquet"
        if not path.exists():
            msg = (
                f"{table}: source parquet missing at {path} — run --export-source "
                "first (dist/ is gitignored; it is absent on a fresh box)"
            )
            raise SourceProvenanceError(msg)
        actual_sha = _sha256_file(path)
        if actual_sha != pins[table]:
            msg = (
                f"{table}: sha256 mismatch — manifest pin {pins[table]}, "
                f"actual {actual_sha} (data-artifacts.yaml drift or a corrupted/stale "
                f"{path})"
            )
            raise SourceProvenanceError(msg)
        verified[table] = path
    return verified


def _load_county_fips_map(county_parquet: Path) -> dict[int, str]:
    """``county_id -> fips`` from the sha-verified ``dim_county`` parquet."""
    table = pq.read_table(county_parquet, columns=["county_id", "fips"])
    return dict(zip(table["county_id"].to_pylist(), table["fips"].to_pylist(), strict=True))


class PovertyCell(NamedTuple):
    """One filtered ``fact_census_poverty`` row, FIPS-resolved."""

    fips: str
    category_id: int
    race_id: int
    person_count: int


def read_filtered_poverty_cells(
    poverty_parquet: Path,
    county_parquet: Path,
    *,
    time_id: int = TIME_ID,
    category_ids: tuple[int, ...] = CATEGORY_IDS,
    race_ids: tuple[int, ...] = RACE_IDS,
) -> tuple[PovertyCell, ...]:
    """Step 3: filtered pyarrow read.

    Pushes the ``time_id``/``category_id``/``race_id`` predicate into the
    dataset scan (column projection + predicate pushdown) — never a bare
    ``fetchall``/``to_pandas`` of the full 26.5M-row table. ``fips`` is
    resolved via ``dim_county``.

    :raises ArtifactGenerationError: a ``county_id`` in the filtered cells
        has no ``dim_county`` row (join integrity failure — never silently
        dropped).
    """
    fips_by_county_id = _load_county_fips_map(county_parquet)

    dataset = ds.dataset(poverty_parquet, format="parquet")
    predicate = (
        (ds.field("time_id") == time_id)
        & ds.field("category_id").isin(list(category_ids))
        & ds.field("race_id").isin(list(race_ids))
    )
    table = dataset.to_table(
        columns=["county_id", "category_id", "race_id", "person_count"],
        filter=predicate,
    )

    cells: list[PovertyCell] = []
    for county_id, category_id, race_id, person_count in zip(
        table["county_id"].to_pylist(),
        table["category_id"].to_pylist(),
        table["race_id"].to_pylist(),
        table["person_count"].to_pylist(),
        strict=True,
    ):
        fips = fips_by_county_id.get(county_id)
        if fips is None:
            msg = (
                f"fact_census_poverty county_id={county_id} has no dim_county row "
                "(join integrity failure)"
            )
            raise ArtifactGenerationError(msg)
        cells.append(
            PovertyCell(
                fips=fips, category_id=category_id, race_id=race_id, person_count=person_count
            )
        )
    return tuple(cells)


class CrosswalkRow(NamedTuple):
    """One A1 row, as read back from the checked-in CSV. Mirrors
    ``tools/make_fips_vintage_crosswalk.py``'s ``CrosswalkRow`` shape."""

    fips_engine: str
    fips_acs2019: str
    relation: str
    vintage_note: str
    recoverable: bool


def load_crosswalk(csv_path: Path = CROSSWALK_CSV) -> tuple[CrosswalkRow, ...]:
    """A1, loaded from the checked-in CSV — **the authority** (T1,
    review-verified). Not re-derived from
    ``tools/make_fips_vintage_crosswalk.py``'s in-module ``CROSSWALK_ROWS``
    constant; this module reads the artifact, the way any other A1
    consumer would."""
    rows: list[CrosswalkRow] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            rows.append(
                CrosswalkRow(
                    fips_engine=record["fips_engine"],
                    fips_acs2019=record["fips_acs2019"],
                    relation=record["relation"],
                    vintage_note=record["vintage_note"],
                    recoverable=record["recoverable"] == "true",
                )
            )
    return tuple(rows)


def resolve_query_fips(fips_engine: str, crosswalk_by_engine_fips: dict[str, CrosswalkRow]) -> str:
    """A1 applied: which FIPS to actually query ``fact_census_poverty``
    under for one engine-universe county.

    Only a ``recoverable=True`` row substitutes a target (Bedford ``51515``
    -> ``51019``). Every other case — no crosswalk row at all, a
    ``DECLARED_HOLE`` row, or a non-recoverable ``SPLIT_UNRESOLVED`` /
    ``REORGANIZATION_UNRESOLVED`` row — queries its own native
    ``fips_engine``, which for the latter two simply returns no data.
    Classifying *why* that data is absent is T3b's job (G4/G5); this
    resolver computes nothing.
    """
    row = crosswalk_by_engine_fips.get(fips_engine)
    if row is not None and row.recoverable and row.fips_acs2019:
        return row.fips_acs2019
    return fips_engine


class UniverseVariant(NamedTuple):
    """One resolved universe: a semantic name + its FIPS membership."""

    name: str
    fips: frozenset[str]


def _artifact_universe(territories_json: Path = ENGINE_TERRITORIES_JSON) -> frozenset[str]:
    """The engine territory universe (``us_county_territories.json``)."""
    payload = json.loads(territories_json.read_text(encoding="utf-8"))
    return frozenset(county["fips"] for county in payload["counties"])


def _scopes_universe(sqlite_path: Path = DEFAULT_SQLITE_PATH) -> frozenset[str]:
    """The resolver universe. Reuses ``scopes._load_national_fips`` directly
    (DRY; T1's own precedent) — see module docstring for why this sqlite
    read is not the ``--from-sqlite`` circularity."""
    return _load_national_fips(sqlite_path)


def _unrestricted_universe(
    poverty_parquet: Path, county_parquet: Path, *, time_id: int = TIME_ID
) -> frozenset[str]:
    """The raw set of FIPS present in ``fact_census_poverty`` at
    ``time_id`` — whatever the data itself contains, no universe
    restriction applied."""
    fips_by_county_id = _load_county_fips_map(county_parquet)
    dataset = ds.dataset(poverty_parquet, format="parquet")
    table = dataset.to_table(columns=["county_id"], filter=ds.field("time_id") == time_id)
    county_ids = set(table["county_id"].to_pylist())
    return frozenset(
        fips_by_county_id[county_id] for county_id in county_ids if county_id in fips_by_county_id
    )


def resolve_universe_variants(
    *,
    territories_json: Path = ENGINE_TERRITORIES_JSON,
    sqlite_path: Path = DEFAULT_SQLITE_PATH,
    poverty_parquet: Path,
    county_parquet: Path,
    time_id: int = TIME_ID,
) -> tuple[UniverseVariant, ...]:
    """Step 4 (plan §3 step 1): the three declared FIPS sets.

    DECLARED_HOLE counties (``46102``, ``02158``) are **not** removed from
    any universe here — they remain ordinary members of ``artifact`` and
    ``scopes`` (both static county registries) and are naturally absent
    from ``unrestricted`` (zero ``fact_census_poverty`` rows at any FIPS
    they've held). G5 (T3b) requires them "present ... in every universe
    variant" for reconciliation; this function does not classify absence at
    all — see :func:`resolve_query_fips` for A1's actual application
    (which FIPS a downstream cell-pull queries under).
    """
    return (
        UniverseVariant("artifact", _artifact_universe(territories_json)),
        UniverseVariant("scopes", _scopes_universe(sqlite_path)),
        UniverseVariant(
            "unrestricted",
            _unrestricted_universe(poverty_parquet, county_parquet, time_id=time_id),
        ),
    )


# ---------------------------------------------------------------------------
# T3a — arithmetic-law guards: G1, G2, G6, G8 (plan §3 guard register).
# Each is a separate pure function; none is yet wired into a per-county
# measure pipeline (that lands with T3b/T4). G3/G4/G5 land with T3b; G7
# already shipped with T1 (tools/make_fips_vintage_crosswalk.py).
# ---------------------------------------------------------------------------


class AggregationCell(NamedTuple):
    """One ``(fips, universe_u, below_b)`` pair fed to a G1 pooled ratio.
    Callers exclude ``ZERO_DENOMINATOR`` cells (G2) before building this
    sequence — :func:`ratio_of_sums` has no zero-denominator policy of its
    own; that classification is :func:`classify_zero_denominator`'s job."""

    fips: str
    universe_u: int
    below_b: int


def ratio_of_sums(cells: Sequence[AggregationCell]) -> float:
    """G1: p̄/q̄ = Σb / Σu — the pooled rate is the ratio of the summed
    counts, **never** ``mean(rate_i)`` over per-county rates (that would
    silently overweight small-universe counties relative to their actual
    population share — plan §3 guard table, G1 row).

    :raises ArtifactGenerationError: Σu == 0 (no cells, or every cell has a
        zero universe) — undefined over an empty universe, never silently 0.0.
    """
    total_u = sum(cell.universe_u for cell in cells)
    total_b = sum(cell.below_b for cell in cells)
    if total_u == 0:
        msg = "ratio_of_sums: Σu == 0 — no defined ratio over an empty universe"
        raise ArtifactGenerationError(msg)
    return total_b / total_u


class ZeroDenominatorResult(NamedTuple):
    """G2's classification result. ``absence_class`` is ``"ZERO_DENOMINATOR"``
    when ``universe_u == 0``, else ``None`` (the caller applies its other
    absence-class rules — G4/G5, T3b). ``rate`` is the empty measure cell:
    ``None`` on zero-denominator, **never** a fabricated ``0.0`` — a ``0.0``
    on a diverging ramp renders *at the settler norm*, a fabricated data
    point (Constitution III.11)."""

    absence_class: str | None
    rate: float | None


def classify_zero_denominator(universe_u: int, below_b: int) -> ZeroDenominatorResult:
    """G2: ``u == 0`` ⇒ ``absence_class=ZERO_DENOMINATOR``, ``rate=None`` —
    all measure cells EMPTY, never zero (plan §3 guard table, G2 row; same
    error class as ``check:aggregation``'s "all-masked group input must
    yield None, never a fabricated 0.0").

    :raises ArtifactGenerationError: ``universe_u`` is negative (a malformed
        cell — a count can never be negative).
    """
    if universe_u < 0:
        msg = f"classify_zero_denominator: universe_u={universe_u} < 0 (malformed cell)"
        raise ArtifactGenerationError(msg)
    if universe_u == 0:
        return ZeroDenominatorResult(absence_class="ZERO_DENOMINATOR", rate=None)
    return ZeroDenominatorResult(absence_class=None, rate=below_b / universe_u)


#: The 7 mutually-exclusive census race/combination iterations that sum
#: exactly to T (the standard ACS detailed-table scheme). H (White-alone
#: non-Hispanic) and I (Hispanic, any race) are separate, overlapping
#: breakdowns — never part of this sum (G8 handles their overlap).
POLE_PART_LETTERS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G")


def assert_t_pole_exactness(
    fips: str,
    t: int,
    parts: Mapping[str, int],
    *,
    h: int,
    i: int,
) -> None:
    """G6: ``T == Σ(A..G)`` per county, **exact** equality — no tolerance
    window, ever (plan's F4: max residual 0 over 3,218 counties). Also
    enforces ``H <= A`` (H is the White-alone-non-Hispanic subset of A) and
    ``I <= T`` (I, Hispanic of any race, cannot exceed the county total).

    :raises ArtifactGenerationError: ``parts`` is missing one of the seven
        required letters, ``T != Σ(A..G)``, ``H > A``, or ``I > T``.
    """
    missing = [letter for letter in POLE_PART_LETTERS if letter not in parts]
    if missing:
        msg = f"{fips}: assert_t_pole_exactness missing pole parts {missing}"
        raise ArtifactGenerationError(msg)
    total_parts = sum(parts[letter] for letter in POLE_PART_LETTERS)
    if total_parts != t:
        residual = t - total_parts
        msg = (
            f"{fips}: T-pole exactness violated — T={t}, Σ(A..G)={total_parts}, "
            f"residual={residual} (exact equality required, no tolerance)"
        )
        raise ArtifactGenerationError(msg)
    if h > parts["A"]:
        msg = f"{fips}: H={h} exceeds A={parts['A']} (H must be the White-alone-non-Hispanic subset of A)"
        raise ArtifactGenerationError(msg)
    if i > t:
        msg = f"{fips}: I={i} exceeds T={t}"
        raise ArtifactGenerationError(msg)


def overlap_upper_bound(total_a: int, white_non_hispanic_h: int, hispanic_i: int) -> int:
    """G8: the disclosed, **never-subtracted** overlap bound — ``I - (A - H)``.
    ``(A - H)`` is the White-alone-Hispanic subgroup; subtracting it from
    ``I`` (all Hispanic persons, any race) bounds how many Hispanic persons
    are also counted in a non-white racial pole (B..G) — a double-count
    risk this function only DISCLOSES. No caller may net this out of any
    pole sum (that is exactly what G8 forbids — plan §3 guard table, G8 row).

    :raises ArtifactGenerationError: ``white_non_hispanic_h > total_a`` (H
        must be a subset of A), or the resulting bound is negative (fewer
        Hispanic persons than the White-Hispanic subgroup alone —
        impossible for valid census data).
    """
    if white_non_hispanic_h > total_a:
        msg = f"overlap_upper_bound: H={white_non_hispanic_h} > A={total_a} (H must be ⊆ A)"
        raise ArtifactGenerationError(msg)
    white_hispanic = total_a - white_non_hispanic_h
    bound = hispanic_i - white_hispanic
    if bound < 0:
        msg = (
            f"overlap_upper_bound: computed bound {bound} < 0 — I={hispanic_i} implies "
            f"fewer Hispanic persons than the White-Hispanic subgroup ({white_hispanic})"
        )
        raise ArtifactGenerationError(msg)
    return bound


# ---------------------------------------------------------------------------
# T3b — absence + small-count guards: G3, G4, G5 (plan §3 guard register).
# Each is a separate pure function; none is yet wired into a per-county
# measure pipeline (that lands with T4). G1/G2/G6/G8 shipped with T3a; G7
# already shipped with T1.
# ---------------------------------------------------------------------------


#: G3's declared damping measure. **Derivation** (ADR172 ruling 5, the
#: standing no-imposed-forms line — ``damp`` is a MEASURE derived from
#: counting statistics, never a stipulated curve shape): a per-county rate
#: built from a universe of size ``u`` is, to first order, a proportion
#: estimate over ``u`` independent Bernoulli trials. Its own sampling noise
#: has a coefficient of variation (relative standard error) of
#: ``1/sqrt(u)`` — the standard result for a Poisson/binomial count
#: (SD ≈ sqrt(u), so SD/u == 1/sqrt(u)). That fraction is exactly how much
#: of the raw deviation ``|w|`` is attributable to the count's own sampling
#: noise rather than real signal; ``damp(u) = 1 - 1/sqrt(u)`` is the
#: complementary reliability fraction — the share of ``|w|`` trusted as
#: signal. It is undefined at ``u=0`` (G2's ZERO_DENOMINATOR territory
#: fires first — there is no rate, let alone a reliability fraction, over
#: an empty universe), strictly increasing in ``u`` (``d/du(1 - u^-0.5) =
#: 0.5 u^-1.5 > 0`` for all ``u > 0`` — monotone by construction, not by
#: inspection), and approaches 1 in the limit (an infinite count carries no
#: relative sampling noise).
def damp(universe_u: int) -> float:
    """G3: ``damp(u) = 1 - 1/sqrt(u)`` — see the module-level derivation
    comment immediately above this function for why this shape, not an
    imposed sigmoid.

    :raises ArtifactGenerationError: ``universe_u <= 0`` — undefined at 0
        (G2 fires first), and a negative count is malformed.
    """
    if universe_u <= 0:
        msg = f"damp: universe_u={universe_u} <= 0 — damp(0) is undefined (G2 fires first)"
        raise ArtifactGenerationError(msg)
    return 1.0 - (1.0 / math.sqrt(universe_u))


class DampedSigma(NamedTuple):
    """G3's output: ``sigma_damped`` plus the ``damping_weight`` actually
    applied, published separately so the damping is auditable per row
    rather than baked invisibly into ``sigma_damped`` alone (T3b step 2)."""

    sigma_damped: float
    damping_weight: float


def compute_damped_sigma(w: float, universe_u: int) -> DampedSigma:
    """``sigma_damped = |w| * damp(u)`` (plan §3 step 8). Calls the module
    global ``damp`` (not a bound alias), so patching ``damp`` on this
    module reaches every caller.

    :raises ArtifactGenerationError: propagated from :func:`damp` when
        ``universe_u <= 0``.
    """
    weight = damp(universe_u)
    return DampedSigma(sigma_damped=abs(w) * weight, damping_weight=weight)


#: G4's material relation (Aleksandrov Test): why SUPPRESSED vs PRESENT is
#: not decorative. ``fact_census_poverty.person_count`` is **NOT NULL**
#: (plan §0, verified against the live schema) — an ACS-suppressed cell can
#: therefore ONLY surface in this table as the same literal 0 a genuine
#: zero-below-poverty count would produce; there is no suppression flag
#: this module can read. Trusting every reported zero as real would
#: silently launder small-sample statistical unreliability into a "this
#: county has zero deprivation" claim on exactly the axis this artifact
#: exists to measure honestly — the III.11 failure this guard prevents.
#: **This module declares its own statistical-plausibility policy** (below,
#: :func:`classify_suppression`) rather than claiming to reproduce an
#: internal Census suppression rule this data source does not expose.
G4_MATERIAL_RELATION = (
    "fact_census_poverty.person_count is NOT NULL, so an ACS-suppressed cell can only "
    "surface as a literal 0 -- identical to a genuine zero-below-poverty count. This module "
    "classifies SUPPRESSED vs PRESENT by a declared statistical-plausibility policy (see "
    "classify_suppression's docstring), never by trusting every reported zero as real, "
    "because a silently-trusted fabricated zero on this axis is exactly the III.11 failure "
    "the national-incidence artifact exists to prevent."
)

#: The reference poverty-incidence rate used ONLY to test the statistical
#: plausibility of an exact-zero below-poverty count (G4). This is a
#: declared POLICY PARAMETER, not the pipeline's own measured p̄/q̄ (G1,
#: step 5) — G4 (step 4) must run BEFORE G1 computes those, so it cannot
#: depend on them without a circular ordering.
SUPPRESSION_REFERENCE_RATE = 0.10
#: The conventional "surprising" significance threshold: a genuine-zero
#: event with probability below this under the reference rate is treated
#: as more likely explained by suppression than by chance.
SUPPRESSION_IMPLAUSIBILITY_ALPHA = 0.05


def classify_suppression(universe_u: int, below_b: int) -> str:
    """G4: distinguishes a genuine small-count zero (``"PRESENT"``) from a
    suppression-consistent zero (``"SUPPRESSED"``) for a cell where
    ``universe_u > 0`` and ``below_b == 0`` (``universe_u == 0`` is G2's
    ZERO_DENOMINATOR territory; a nonzero ``below_b`` needs no suppression
    judgment at all).

    **The declared rule**: under the reference rate ``r`` =
    :data:`SUPPRESSION_REFERENCE_RATE`, modeling each of the ``u`` persons'
    poverty status as an independent Bernoulli trial, the probability of a
    genuine zero count is ``(1 - r) ** u``. When that probability falls
    below :data:`SUPPRESSION_IMPLAUSIBILITY_ALPHA`, the observed exact zero
    would be statistically surprising even under complete independence —
    exactly the pattern ACS small-count disclosure-avoidance is documented
    to produce (see :data:`G4_MATERIAL_RELATION`) — so this cell is
    classified SUPPRESSED rather than trusted. Below the threshold, a
    genuine zero is unremarkable and the cell is PRESENT.

    :raises ArtifactGenerationError: ``universe_u <= 0`` (G2's territory),
        or ``below_b != 0`` (out of this function's domain).
    """
    if universe_u <= 0:
        msg = f"classify_suppression: universe_u={universe_u} <= 0 is G2's territory, not G4's"
        raise ArtifactGenerationError(msg)
    if below_b != 0:
        msg = f"classify_suppression: below_b={below_b} != 0 — only exact-zero cells need a suppression judgment"
        raise ArtifactGenerationError(msg)
    probability_of_genuine_zero = (1.0 - SUPPRESSION_REFERENCE_RATE) ** universe_u
    if probability_of_genuine_zero < SUPPRESSION_IMPLAUSIBILITY_ALPHA:
        return "SUPPRESSED"
    return "PRESENT"


class PoleCellPair(NamedTuple):
    """One (fips, pole)'s already-joined universe/below-poverty counts —
    the shape :func:`classify_absence` consumes. A missing pair (``None``)
    for a (fips, pole) in the declared universe means no
    ``fact_census_poverty`` rows exist at all for that cell — ROW_ABSENT,
    never an imputed count."""

    universe_u: int
    below_b: int


class AbsenceClassification(NamedTuple):
    """G4's full per-cell result: which A2 absence class the cell belongs
    to, plus its rate — ``None`` for every non-PRESENT class (G2's
    "absence is a value, never 0.0" law applies identically to SUPPRESSED
    and ROW_ABSENT, not just ZERO_DENOMINATOR)."""

    absence_class: str
    rate: float | None


def classify_absence(
    cell: PoleCellPair | None, *, fips: str, declared_hole_fips: frozenset[str]
) -> AbsenceClassification:
    """The full per-(fips, pole) absence classification: DECLARED_HOLE (A1;
    overrides everything else — a declared-hole fips is never trusted even
    if a malformed cell somehow carried data for it), ROW_ABSENT (``cell``
    is ``None``), ZERO_DENOMINATOR (G2, reused), SUPPRESSED/PRESENT (G4,
    :func:`classify_suppression`), or PRESENT (a normal nonzero cell).

    :raises ArtifactGenerationError: propagated from
        :func:`classify_zero_denominator` or :func:`classify_suppression`.
    """
    if fips in declared_hole_fips:
        return AbsenceClassification(absence_class="DECLARED_HOLE", rate=None)
    if cell is None:
        return AbsenceClassification(absence_class="ROW_ABSENT", rate=None)
    zero_denom = classify_zero_denominator(cell.universe_u, cell.below_b)
    if zero_denom.absence_class == "ZERO_DENOMINATOR":
        return AbsenceClassification(absence_class="ZERO_DENOMINATOR", rate=None)
    if cell.below_b == 0:
        label = classify_suppression(cell.universe_u, cell.below_b)
        rate = zero_denom.rate if label == "PRESENT" else None
        return AbsenceClassification(absence_class=label, rate=rate)
    return AbsenceClassification(absence_class="PRESENT", rate=zero_denom.rate)


#: G5's declared absence-class taxonomy — every (fips, pole) cell in the
#: declared universe lands in exactly one of these (PRESENT included so the
#: reconciliation is exhaustive: presence + absence == universe_size).
ABSENCE_CLASSES: tuple[str, ...] = (
    "PRESENT",
    "ZERO_DENOMINATOR",
    "ROW_ABSENT",
    "DECLARED_HOLE",
    "SUPPRESSED",
)


class AbsenceReconciliation(NamedTuple):
    """G5's per-class county counts plus the exact reconciliation."""

    counts_by_class: Mapping[str, int]
    counties_present: int
    counties_absent: int
    universe_size: int


def reconcile_absence_counts(
    absence_classes: Sequence[str], *, universe_size: int
) -> AbsenceReconciliation:
    """G5: honest absence accounting. ``counties_present`` (the ``PRESENT``
    label) + ``counties_absent`` (every other label in
    :data:`ABSENCE_CLASSES`) must equal ``universe_size`` EXACTLY — no
    tolerance, no dropped class (F3: the real run budgets 466 pole-cells +
    14/16 whole-county, not 14/16 alone — this function's law is generic;
    it must reconcile exactly regardless of which classes carry the counts).

    :raises ArtifactGenerationError: any label outside
        :data:`ABSENCE_CLASSES`, or the reconciled total does not equal
        ``universe_size``.
    """
    unknown = sorted(set(absence_classes) - set(ABSENCE_CLASSES))
    if unknown:
        msg = f"reconcile_absence_counts: unknown absence class(es) {unknown}"
        raise ArtifactGenerationError(msg)
    counts: dict[str, int] = dict.fromkeys(ABSENCE_CLASSES, 0)
    for label in absence_classes:
        counts[label] += 1
    counties_present = counts["PRESENT"]
    counties_absent = sum(counts[label] for label in ABSENCE_CLASSES if label != "PRESENT")
    total = counties_present + counties_absent
    if total != universe_size:
        msg = (
            f"reconcile_absence_counts: counties_present({counties_present}) + "
            f"counties_absent({counties_absent}) = {total} != universe_size={universe_size}"
        )
        raise ArtifactGenerationError(msg)
    return AbsenceReconciliation(
        counts_by_class=counts,
        counties_present=counties_present,
        counties_absent=counties_absent,
        universe_size=universe_size,
    )


#: G5's Pine Ridge invariant. 46102 (Oglala Lakota) is a permanent
#: DECLARED_HOLE (A1, T1) — zero fact_census_poverty rows at every
#: time_id; its retired predecessor 46113 (Shannon County) carries rows
#: only 2010-2014, stale before the pinned 2019 vintage (OQ11). Never
#: imputed.
PINE_RIDGE_FIPS = "46102"
PINE_RIDGE_RETIRED_PREDECESSOR_FIPS = "46113"


def assert_no_pine_ridge_imputation(
    fips: str, absence_class: str, *, source_fips: str | None = None
) -> None:
    """G5's Pine Ridge leg. Out of scope (no-op) for any ``fips`` other
    than :data:`PINE_RIDGE_FIPS`.

    :raises ArtifactGenerationError: ``fips == PINE_RIDGE_FIPS`` and either
        ``source_fips == PINE_RIDGE_RETIRED_PREDECESSOR_FIPS`` (an
        imputation attempt from the retired predecessor), or
        ``absence_class != "DECLARED_HOLE"`` (Pine Ridge must classify
        DECLARED_HOLE in every universe variant).
    """
    if fips != PINE_RIDGE_FIPS:
        return
    if source_fips == PINE_RIDGE_RETIRED_PREDECESSOR_FIPS:
        msg = (
            f"{fips}: Pine Ridge imputed from its retired predecessor "
            f"{PINE_RIDGE_RETIRED_PREDECESSOR_FIPS} — never permitted (G5)"
        )
        raise ArtifactGenerationError(msg)
    if absence_class != "DECLARED_HOLE":
        msg = (
            f"{fips}: Pine Ridge must classify DECLARED_HOLE in every universe variant, "
            f"got {absence_class!r}"
        )
        raise ArtifactGenerationError(msg)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--export-source",
        action="store_true",
        help=(
            "materialize the four registered parquet sources "
            f"({', '.join(SOURCE_TABLES)}) from the read-only reference DB via "
            "make_data_artifacts.export_table_parquet — the ONLY sanctioned "
            "parquet-writing path. PRODUCES the registered sources; run inside "
            "`mise run nix -- ...` (pinned SQLite required). There is no "
            "--from-sqlite derivation flag — every other mode reads only the "
            "sha-pinned parquet sources."
        ),
    )
    parser.add_argument("--sqlite-path", type=Path, default=DEFAULT_SQLITE_PATH)
    parser.add_argument("--dist-dir", type=Path, default=DIST_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.export_source:
        export_source_tables(args.sqlite_path, dist_dir=args.dist_dir)
        return 0

    verified = verify_source_provenance(args.dist_dir)
    print(f"[national-incidence] provenance verified (sha-pinned): {sorted(verified)}")

    cells = read_filtered_poverty_cells(verified["fact_census_poverty"], verified["dim_county"])
    print(
        f"[national-incidence] filtered cells pulled: {len(cells)} "
        f"(time_id={TIME_ID}, category_id in {CATEGORY_IDS}, race_id in {RACE_IDS})"
    )

    variants = resolve_universe_variants(
        sqlite_path=args.sqlite_path,
        poverty_parquet=verified["fact_census_poverty"],
        county_parquet=verified["dim_county"],
    )
    for variant in variants:
        print(f"[national-incidence] universe '{variant.name}': {len(variant.fips)} counties")

    print(
        "[national-incidence] skeleton complete — no measures computed "
        "(T3a/T3b land the guards, T4 the emission)."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ArtifactGenerationError as error:
        print(f"[national-incidence] ABORT: {error}", file=sys.stderr)
        sys.exit(2)
