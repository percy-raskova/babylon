#!/usr/bin/env python3
"""Regression testing for simulation formula drift detection.

Generates and compares baseline JSON files to detect unintended changes
to simulation behavior during refactoring.

Usage:
    # Generate baselines (after intentional changes)
    poetry run python tools/regression_test.py generate --force

    # Also (re)generate the dense per-tick trace CSVs (Program 13 item 2)
    poetry run python tools/regression_test.py generate --force --dense

    # Compare against baselines (in CI) — byte-compares the dense CSVs
    # too, when tests/baselines/dense/<scenario>.csv exists.
    poetry run python tools/regression_test.py compare

Scenarios:
    - imperial_circuit: 4-node default scenario
    - two_node: Minimal worker vs owner
    - starvation: Low extraction efficiency stress
    - glut: High extraction with metabolic overshoot
    - fascist_bifurcation: Consciousness routing to national identity

Dense goldens (Program 13 item 2, Constitution III.12 corollary (c)):
    ``tests/baselines/dense/<scenario>.csv`` pins every tick (not just the
    ~6 sampled checkpoints above) for every entity's wealth/tension-relevant
    fields and every relationship's value_flow/tension. Column contract and
    float-format policy are documented in
    ``docs/reference/determinism-contract.rst`` ("Dense Golden Traces").

See Also:
    :doc:`/ai/tooling.yaml` regression_testing section
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

# Add src and tools to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

# Import from centralized shared module (ADR036)
from regression_scenarios import (  # noqa: F401  (re-export)
    PENDING_CEREMONY,
    SCENARIO_COVERAGE,
    SCENARIOS,
    create_scenario,
)
from shared import (
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    LABOR_ARISTOCRACY_ID,
    PERIPHERY_WORKER_ID,
    is_dead,
)

from babylon.config.defines import GameDefines
from babylon.engine.simulation_engine import step
from babylon.engine.trace_format import format_trace_value, trace_rows_to_csv_bytes

# Constants
BASELINE_DIR: Final[Path] = Path(__file__).parent.parent / "tests" / "baselines"
DENSE_SUBDIR: Final[str] = "dense"
DEFAULT_MAX_TICKS: Final[int] = 52

# E4: machine-readable first-divergence attribution, rewritten fresh every
# `compare` run (removed at the start of `compare_all_baselines` so a green
# run never leaves a stale, misleading report behind).
FIRST_DIVERGENCE_REPORT_PATH: Final[Path] = (
    Path(__file__).parent.parent / "reports" / "qa-first-divergence.json"
)
CHECKPOINT_INTERVAL: Final[int] = 10
TOLERANCE: Final[float] = 1e-5

FRED_FIXTURE_PATH: Final[Path] = (
    Path(__file__).parent.parent / "tests" / "fixtures" / "vol3_fred_series.json"
)


def _load_vol3_fred_fixture() -> dict[str, dict[int, float]]:
    """Load the committed Vol III FRED fixture (D4) — no DB, no drive.

    The JSON on disk stores year as a string (JSON object keys are always
    strings); the Vol III adapters (``FredInterestRateAdapter`` et al.) index
    by ``int`` year, so keys are converted back on load.

    Returns:
        ``{series_id: {year: value}}`` matching
        :func:`babylon.domain.economics.factory.load_fred_series_from_db`'s
        return shape.
    """
    raw: dict[str, dict[str, float]] = json.loads(FRED_FIXTURE_PATH.read_text())
    return {
        series_id: {int(year): value for year, value in years.items()}
        for series_id, years in raw.items()
    }


MELT_FIXTURE_PATH: Final[Path] = (
    Path(__file__).parent.parent / "tests" / "fixtures" / "vol3_melt_national.json"
)


class _FixtureNationalGDPSource:
    """Fixture-backed ``BEADataSource`` — hermetic twin of ``SQLiteBEANationalGDPSource``.

    Returns ``None`` for an absent year, exactly as the SQLite adapter does
    (Constitution III.11) — the fixture omits years the reference DB has no
    row for rather than zero-filling them.
    """

    def __init__(self, gdp_by_year: dict[int, float]) -> None:
        self._gdp_by_year = gdp_by_year

    def get_gdp(self, year: int) -> float | None:
        return self._gdp_by_year.get(year)


class _FixtureNationalEmploymentSource:
    """Fixture-backed ``QCEWDataSource`` — twin of ``SQLiteQCEWNationalEmploymentSource``."""

    def __init__(self, employment_by_year: dict[int, int]) -> None:
        self._employment_by_year = employment_by_year

    def get_national_employment(self, year: int) -> int | None:
        return self._employment_by_year.get(year)


def _load_vol3_melt_fixture() -> tuple[dict[int, float], dict[int, int]]:
    """Load the committed national MELT fixture (D4) — no DB, no drive.

    JSON object keys are always strings; ``DefaultMELTCalculator`` indexes by
    ``int`` year, so keys are converted back on load.

    Returns:
        ``(gdp_by_year, employment_by_year)`` — the two national annual series
        ``DefaultMELTCalculator`` consumes, and nothing else.
    """
    raw: dict[str, dict[str, float]] = json.loads(MELT_FIXTURE_PATH.read_text())
    gdp = {int(year): float(value) for year, value in raw["gdp"].items()}
    employment = {int(year): int(value) for year, value in raw["employment"].items()}
    return gdp, employment


def _build_vol3_melt_calculator() -> Any:
    """Build the fixture-backed ``melt_calculator`` for ``qa:regression``.

    ``create_financial_services`` supplies every Vol III calculator EXCEPT this
    one — it is built only by ``create_economics_services``, which needs a
    SQLAlchemy session the hermetic harness forbids. Without it,
    ``TickDynamicsSystem`` returns early on ``melt_calculator is None`` and the
    entire annual economics pipeline (Steps 2-9, including the Step 5.5 Vol III
    financial layer) is skipped — the gate runs, but sees nothing.

    Deliberately NOT accompanied by a ``TensorRegistry``: ``get_melt`` does not
    consume one, and the five regression scenarios carry no ``county_fips``, so
    a real-FIPS-keyed registry is unreachable from them (county coverage is
    Task U1.9's job, over the Wayne County scenario).
    """
    from babylon.domain.economics.melt import DefaultMELTCalculator

    gdp_by_year, employment_by_year = _load_vol3_melt_fixture()
    return DefaultMELTCalculator(
        _FixtureNationalGDPSource(gdp_by_year),
        _FixtureNationalEmploymentSource(employment_by_year),
    )


def _build_vol3_calculator_overrides(defines: GameDefines) -> dict[str, Any]:
    """Build Vol III ``calculator_overrides`` from the committed FRED fixture.

    D4: gives ``qa:regression`` real (2010-2024) money data without touching
    the babylon-data drive — the harness reads only the committed fixture.

    Args:
        defines: The scenario's resolved ``GameDefines`` (same instance
            passed to ``step()``), so ``capital_vol3``-moddable calculator
            constants (e.g. the housing ground-rent capitalization rate)
            honor scenario/CLI overrides instead of silently reverting to
            ``GameDefines.load_default()`` (honesty sweep, U2.4).
    """
    from babylon.domain.economics.factory import create_financial_services

    overrides = create_financial_services(
        fred_series_cache=_load_vol3_fred_fixture(), defines=defines
    )
    # The one key create_financial_services does not supply, and the one that
    # decides whether TickDynamicsSystem executes at all.
    overrides["melt_calculator"] = _build_vol3_melt_calculator()
    return overrides


SINGLE_COUNTY_FIXTURE_PATH: Final[Path] = (
    Path(__file__).parent.parent / "tests" / "fixtures" / "single_county_wayne.json"
)


def build_single_county_overrides(defines: GameDefines) -> dict[str, Any]:
    """Wayne-county calculator_overrides from the committed fixture (D4).

    Extends the Vol III override set from :func:`_build_vol3_calculator_overrides`
    (the same FRED-fixture-backed ``distribution_calculator``/``melt_calculator``
    the other 5 canonical scenarios use — those national-level FRED series
    already cover Wayne's extraction year, see the fixture's ``_provenance``)
    with a real-FIPS ``tensor_registry`` hydrated from the committed
    ``tests/fixtures/single_county_wayne.json`` extraction (Wayne County,
    FIPS 26163, real reference-DB tensor via the production
    ``MarxianHydrator`` chain — see that fixture's ``_provenance`` for the
    extraction method and year-selection rationale). The production
    calculator chain (``TensorRegistry`` -> ``SurplusDistributionCalculator``)
    runs for real on this data; only the LEAF tensor input is fixture-fed
    (mocking-is-debt boundary, D4).

    Args:
        defines: The scenario's resolved ``GameDefines`` (same instance
            passed to ``step()``), forwarded unchanged to
            :func:`_build_vol3_calculator_overrides`.
    """
    from babylon.domain.economics.tensor import DepartmentRow, ValueTensor4x3
    from babylon.domain.economics.tensor_registry import TensorRegistry

    overrides = _build_vol3_calculator_overrides(defines)

    fixture = json.loads(SINGLE_COUNTY_FIXTURE_PATH.read_text(encoding="utf-8"))
    tensor_data = fixture["tensor"]
    tensor = ValueTensor4x3(
        fips_code=fixture["fips_code"],
        year=fixture["year"],
        dept_I=DepartmentRow(**tensor_data["dept_I"]),
        dept_IIa=DepartmentRow(**tensor_data["dept_IIa"]),
        dept_IIb=DepartmentRow(**tensor_data["dept_IIb"]),
        dept_III=DepartmentRow(**tensor_data["dept_III"]),
        naics_granularity=tensor_data["naics_granularity"],
        excluded_wages=tensor_data["excluded_wages"],
        visibility_g33=tensor_data["visibility_g33"],
    )
    registry = TensorRegistry()
    registry.put(fixture["fips_code"], fixture["year"], tensor)
    overrides["tensor_registry"] = registry

    return overrides


# Dense-trace per-entity/per-edge column contract (Program 13 item 2). Each
# entry is (column-name suffix, getter). Declared once so the CSV header and
# every row are built from the exact same ordered list and can never drift
# relative to each other.
_DENSE_ENTITY_FIELDS: Final[list[tuple[str, Callable[[Any], float | bool]]]] = [
    ("wealth", lambda e: float(e.wealth)),
    ("effective_wealth", lambda e: float(e.effective_wealth)),
    ("p_acquiescence", lambda e: float(e.p_acquiescence)),
    ("p_revolution", lambda e: float(e.p_revolution)),
    ("active", lambda e: bool(e.active)),
    ("class_consciousness", lambda e: float(e.ideology.class_consciousness)),
    ("national_identity", lambda e: float(e.ideology.national_identity)),
    ("agitation", lambda e: float(e.ideology.agitation)),
    ("organization", lambda e: float(e.organization)),
    ("repression_faced", lambda e: float(e.repression_faced)),
]
_DENSE_EDGE_FIELDS: Final[list[tuple[str, Callable[[Any], float | bool]]]] = [
    ("value_flow", lambda r: float(r.value_flow)),
    ("tension", lambda r: float(r.tension)),
]


@dataclass
class CheckpointData:
    """Data captured at each checkpoint tick."""

    tick: int
    p_w_wealth: float
    p_c_wealth: float
    c_b_wealth: float
    c_w_wealth: float
    imperial_rent_pool: float
    exploitation_tension: float
    p_w_consciousness: float
    p_w_p_revolution: float
    p_w_active: bool


@dataclass
class BaselineData:
    """Complete baseline for a scenario."""

    scenario: str
    description: str
    generated_at: str
    defines_hash: str
    max_ticks: int
    checkpoints: list[CheckpointData]
    final_outcome: str
    ticks_survived: int


@dataclass
class DenseTrace:
    """Per-tick, full-variable trace for one scenario run (Program 13 item 2).

    Unlike :class:`BaselineData`'s sparse checkpoints (~9 vars every 10th
    tick), a ``DenseTrace`` covers every tick the scenario actually ran
    (``0..ticks_survived``) and every entity/relationship field in the
    column contract (``_DENSE_ENTITY_FIELDS`` / ``_DENSE_EDGE_FIELDS``).
    Rows are pre-formatted strings (see ``_format_dense_value``) so the
    CSV serialization is a single deterministic byte stream — see
    :func:`dense_trace_to_csv_bytes` and
    ``docs/reference/determinism-contract.rst``.

    Attributes:
        scenario: Scenario name (matches ``BaselineData.scenario``).
        header: Ordered CSV column names, derived once from the tick-0
            topology (:func:`_dense_header`).
        rows: One row per tick, each a list of strings aligned to
            ``header``.
    """

    scenario: str
    header: list[str]
    rows: list[list[str]]


def hash_defines(defines: GameDefines) -> str:
    """Generate hash of GameDefines for change detection.

    Args:
        defines: GameDefines instance

    Returns:
        SHA256 hash string (first 16 chars)
    """
    json_str = defines.model_dump_json(indent=None)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def get_entity_value(state: Any, entity_id: str, field: str, default: float = 0.0) -> float:
    """Safely get entity field value.

    Args:
        state: WorldState
        entity_id: Entity ID
        field: Field name
        default: Default if entity/field missing

    Returns:
        Float value
    """
    entity = state.entities.get(entity_id)
    if entity is None:
        return default
    return float(getattr(entity, field, default))


def get_exploitation_tension(state: Any) -> float:
    """Get maximum exploitation tension from relationships.

    Args:
        state: WorldState

    Returns:
        Maximum tension value
    """
    max_tension = 0.0
    for rel in state.relationships:
        if hasattr(rel, "tension"):
            max_tension = max(max_tension, rel.tension)
    return max_tension


def _format_dense_value(value: float | bool) -> str:
    """Format one dense-trace scalar per the documented float/bool policy.

    Byte-neutral delegation (Task 10, E2b) to
    :func:`babylon.engine.trace_format.format_trace_value` — the shared
    serializer, moved verbatim so both this CLI and the headless-runner
    bundle's ``dense_trace.csv`` (Task 10) use one byte contract. See that
    module's docstring for the full float/bool policy.

    Args:
        value: A float or bool captured from WorldState.

    Returns:
        The exact string written to the dense CSV cell.
    """
    return format_trace_value(value)


#: The 4 national financial columns (E3) — always emitted, every scenario.
#: Column names are fixed regardless of the internal
#: ``EndogenousInterestRate`` field names they read (verified against
#: ``src/babylon/domain/economics/credit/types.py``): ``financial_s_r``
#: reads the real field ``reserve_army_signal``, not a ``s_r`` key.
_DENSE_FINANCIAL_SUFFIXES: Final[list[str]] = [
    "endogenous_rate",
    "profit_rate_ceiling",
    "s_r",
    "tightness",
]

#: The 5 per-county distribution columns (E3) — one set per county_fips a
#: scenario's territories carry (verified against
#: ``src/babylon/domain/economics/distribution/types.py``'s
#: ``SurplusValueDistribution``: ``profit_enterprise`` reads the real
#: computed field ``profit_of_enterprise``).
_DENSE_COUNTY_SUFFIXES: Final[list[str]] = [
    "total_s",
    "interest",
    "ground_rent",
    "taxes",
    "profit_enterprise",
]


def _dense_header(
    state: Any,
) -> tuple[list[str], list[str], list[tuple[str, str]], list[str]]:
    """Derive the dense-trace column contract from a scenario's tick-0 state.

    The header (and the entity/edge/county ordering it encodes) is fixed
    once, from the initial topology, on the documented assumption that a
    regression scenario's entity, relationship, and territory/county set is
    static for its whole run (no scenario in ``SCENARIOS`` adds/removes
    entities, edges, or counties mid-run). :func:`_dense_row` verifies this
    assumption every tick and raises rather than silently misaligning
    columns if it's ever violated (Constitution III.11, Loud Failure).

    Args:
        state: The scenario's tick-0 WorldState.

    Returns:
        Tuple of (header, sorted entity IDs, sorted (source_id, target_id)
        edge keys, sorted county FIPS codes) — the latter three are reused
        by every row to avoid re-deriving the topology every tick.
    """
    entity_ids = sorted(state.entities.keys())
    edge_keys = sorted({(rel.source_id, rel.target_id) for rel in state.relationships})
    counties = sorted(t.county_fips for t in state.territories.values() if t.county_fips)

    header = [
        "tick",
        "economy_imperial_rent_pool",
        "economy_current_super_wage_rate",
        "economy_current_repression_level",
    ]
    header.extend(f"financial_{suffix}" for suffix in _DENSE_FINANCIAL_SUFFIXES)
    for fips in counties:
        header.extend(f"county_{fips}_{suffix}" for suffix in _DENSE_COUNTY_SUFFIXES)
    for entity_id in entity_ids:
        header.extend(f"{entity_id}_{suffix}" for suffix, _getter in _DENSE_ENTITY_FIELDS)
    for source_id, target_id in edge_keys:
        header.extend(
            f"edge_{source_id}_{target_id}_{suffix}" for suffix, _getter in _DENSE_EDGE_FIELDS
        )
    return header, entity_ids, edge_keys, counties


def _dense_row(
    state: Any,
    tick: int,
    entity_ids: list[str],
    edge_keys: list[tuple[str, str]],
    counties: list[str],
    context: dict[str, Any] | None,
) -> list[str]:
    """Build one dense-trace CSV row, asserting the topology hasn't drifted.

    Args:
        state: WorldState at ``tick``.
        tick: Current tick number.
        entity_ids: Sorted entity IDs from :func:`_dense_header` (tick 0).
        edge_keys: Sorted (source_id, target_id) edge keys from
            :func:`_dense_header` (tick 0).
        counties: Sorted county FIPS codes from :func:`_dense_header`
            (tick 0).
        context: The harness's ``persistent_context`` dict (Task 7,
            SAVE-ONLY semantics) — ``_national_financial`` holds the
            last-stamped :class:`NationalFinancialParameters` dump (the
            annual pipeline fires exactly once per 52-tick run, on the
            first ``step()`` call, since ``context.tick`` is the
            pre-increment ``state.tick``); ``_tick_dynamics`` similarly
            holds the last-stamped ``county_states`` dict of real
            ``CountyEconomicState`` model instances. ``None``/absent-key
            degrades to the same all-zero cells a county-free or
            not-yet-boundary scenario would produce.

    Returns:
        List of formatted string cells aligned to the header.

    Raises:
        ValueError: If ``state``'s entity, edge, or county set no longer
            matches the tick-0 topology — a scenario dynamically
            adding/removing entities, edges, or counties is not supported
            by the fixed-column dense format; failing loud here beats
            silently misaligning columns.
    """
    actual_entity_ids = sorted(state.entities.keys())
    if actual_entity_ids != entity_ids:
        raise ValueError(
            f"dense trace topology drift at tick {tick}: entity set changed "
            f"from {entity_ids} to {actual_entity_ids} — dense goldens assume "
            "a static entity topology per scenario (Constitution III.11)"
        )

    edge_lookup = {(rel.source_id, rel.target_id): rel for rel in state.relationships}
    actual_edge_keys = sorted(edge_lookup.keys())
    if actual_edge_keys != edge_keys:
        raise ValueError(
            f"dense trace topology drift at tick {tick}: edge set changed "
            f"from {edge_keys} to {actual_edge_keys} — dense goldens assume "
            "a static relationship topology per scenario (Constitution III.11)"
        )

    actual_counties = sorted(t.county_fips for t in state.territories.values() if t.county_fips)
    if actual_counties != counties:
        raise ValueError(
            f"dense trace topology drift at tick {tick}: county set changed "
            f"from {counties} to {actual_counties} — dense goldens assume "
            "a static territory/county_fips topology per scenario (Constitution III.11)"
        )

    row: list[str] = [str(tick)]
    row.append(_format_dense_value(float(state.economy.imperial_rent_pool)))
    row.append(_format_dense_value(float(state.economy.current_super_wage_rate)))
    row.append(_format_dense_value(float(state.economy.current_repression_level)))

    financial = (context or {}).get("_national_financial") or {}
    endo = financial.get("endogenous_interest") or {}
    row.append(_format_dense_value(float(endo.get("rate", 0.0))))
    row.append(_format_dense_value(float(endo.get("profit_rate_ceiling", 0.0))))
    row.append(_format_dense_value(float(endo.get("reserve_army_signal", 0.0))))
    row.append(_format_dense_value(float(endo.get("tightness", 0.0))))

    county_states = ((context or {}).get("_tick_dynamics") or {}).get("county_states", {})
    for fips in counties:
        cs = county_states.get(fips)
        dist = getattr(cs, "surplus_distribution", None) if cs is not None else None
        for value in (
            getattr(dist, "total_surplus_produced", 0.0),
            getattr(dist, "interest_payments", 0.0),
            getattr(dist, "ground_rent", 0.0),
            getattr(dist, "taxes_on_surplus", 0.0),
            getattr(dist, "profit_of_enterprise", 0.0),
        ):
            row.append(_format_dense_value(float(value)))

    for entity_id in entity_ids:
        entity = state.entities[entity_id]
        for _suffix, getter in _DENSE_ENTITY_FIELDS:
            row.append(_format_dense_value(getter(entity)))

    for source_id, target_id in edge_keys:
        rel = edge_lookup[(source_id, target_id)]
        for _suffix, getter in _DENSE_EDGE_FIELDS:
            row.append(_format_dense_value(getter(rel)))

    return row


def dense_trace_to_csv_bytes(trace: DenseTrace) -> bytes:
    """Serialize a :class:`DenseTrace` to its canonical CSV byte stream.

    Byte-neutral delegation (Task 10, E2b) to
    :func:`babylon.engine.trace_format.trace_rows_to_csv_bytes` — the shared
    serializer, moved verbatim. Matches the ``trace.csv`` behavioral-artifact
    convention documented in ``docs/reference/determinism-contract.rst``:
    UTF-8, comma-delimited, RFC 4180 minimal quoting, ``\\n`` line
    terminator, header row, trailing newline.

    Args:
        trace: The dense trace to serialize.

    Returns:
        The exact bytes that get written to (or compared against)
        ``tests/baselines/dense/<scenario>.csv``.
    """
    return trace_rows_to_csv_bytes(trace.header, trace.rows)


def _parse_dense_csv_bytes(data: bytes) -> tuple[list[str], list[list[str]]]:
    """Inverse of :func:`dense_trace_to_csv_bytes`, for diagnostic diffing.

    Args:
        data: Raw CSV bytes (as read from a committed golden file).

    Returns:
        Tuple of (header, rows) as strings — no type coercion, since
        comparison is done at the string-cell level (byte-identity, not
        tolerance-bounded).
    """
    text = data.decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


@dataclass(frozen=True)
class DivergenceReport:
    """First point where an actual dense trace departs its golden baseline.

    Produced by :func:`attribute_divergence` (E4) — replaces the old
    ``_first_dense_divergence`` free-text diagnostic with a structured
    record naming the tick, column, dialectical channel, county (when the
    column is county-scoped), and the candidate systems
    (:data:`tools.regression_scenarios.CHANNEL_WRITERS`) that could have
    written it, so a dense-gate FAIL doesn't require hand-deriving
    attribution (Program: qa:regression modernization, task 5).
    """

    scenario: str
    tick: int
    column: str
    channel: str
    county: str | None
    expected: str
    actual: str
    magnitude: float | None
    last_agreeing_tick: int | None
    candidate_systems: tuple[str, ...]


def _parse_column(column: str) -> tuple[str, str | None]:
    """Return (channel suffix, county fips or None) for a dense column name.

    Args:
        column: A dense-trace header cell, e.g. ``"C001_wealth"``,
            ``"edge_C001_C002_tension"``, ``"economy_imperial_rent_pool"``,
            or a future ``"county_<fips>_<suffix>"`` / ``"financial_*"``
            column (Task 9 / E3 — no current baseline emits these yet, but
            the column vocabulary is already documented).

    Returns:
        Tuple of (channel, county fips or None). ``channel`` is the key
        looked up in ``CHANNEL_WRITERS``.
    """
    if column.startswith("county_"):
        parts = column.split("_", 2)  # county, <fips>, <suffix>
        if len(parts) == 3:
            return parts[2], parts[1]
    if column.startswith(("economy_", "financial_")):
        return column, None
    if column.startswith("edge_"):
        return column.rsplit("_", 1)[1], None
    _, _, suffix = column.partition("_")  # C001_wealth -> wealth
    return suffix or column, None


def attribute_divergence(
    scenario: str,
    header: list[str],
    expected_rows: list[list[str]],
    actual_rows: list[list[str]],
) -> DivergenceReport | None:
    """Locate and attribute the first cell where actual departs expected.

    The single cell-walk implementation behind both the dense-gate FAIL
    path (:func:`compare_dense_trace`) and direct callers (tests, ad hoc
    diagnosis) — there is intentionally no second copy of this walk.

    Args:
        scenario: Scenario name, threaded through to the report.
        header: Column names shared by both ``expected_rows`` and
            ``actual_rows`` (the golden's header — dense goldens assume a
            static column contract per scenario).
        expected_rows: Committed golden's data rows.
        actual_rows: Freshly-generated data rows.

    Returns:
        The first-divergence attribution, or ``None`` if the two row sets
        are identical (row-for-row, cell-for-cell, and equal in count).
    """
    from regression_scenarios import CHANNEL_WRITERS

    n = min(len(expected_rows), len(actual_rows))
    for i in range(n):
        exp_row, act_row = expected_rows[i], actual_rows[i]
        for j, column in enumerate(header):
            exp = exp_row[j] if j < len(exp_row) else "<absent>"
            act = act_row[j] if j < len(act_row) else "<absent>"
            if exp == act:
                continue
            channel, county = _parse_column(column)
            try:
                magnitude: float | None = abs(float(act) - float(exp))
            except ValueError:
                magnitude = None
            tick = int(exp_row[0]) if exp_row else i  # degrade gracefully on an empty row
            return DivergenceReport(
                scenario=scenario,
                tick=tick,
                column=column,
                channel=channel,
                county=county,
                expected=exp,
                actual=act,
                magnitude=magnitude,
                last_agreeing_tick=int(expected_rows[i - 1][0]) if i > 0 else None,
                candidate_systems=CHANNEL_WRITERS.get(channel, ()),
            )
    if len(expected_rows) != len(actual_rows):
        i = n
        longer = expected_rows if len(expected_rows) > n else actual_rows
        return DivergenceReport(
            scenario=scenario,
            tick=int(longer[i][0]),
            column="<row count>",
            channel="<missing row>",
            county=None,
            expected=str(len(expected_rows)),
            actual=str(len(actual_rows)),
            magnitude=None,
            last_agreeing_tick=int(expected_rows[n - 1][0]) if n else None,
            candidate_systems=(),
        )
    return None


def _format_divergence_report(r: DivergenceReport) -> str:
    """Human-readable one-liner for a :class:`DivergenceReport`."""
    return (
        f"  FIRST DIVERGENCE: tick {r.tick}, {r.column}"
        + (f" (county {r.county})" if r.county else "")
        + f": {r.expected} -> {r.actual}"
        + (f" (Δ={r.magnitude!r})" if r.magnitude is not None else "")
        + f"; last agreed tick {r.last_agreeing_tick}; "
        + f"candidate systems: {', '.join(r.candidate_systems) or 'unmapped channel'}"
    )


def divergence_report_json(report: DivergenceReport) -> dict[str, Any]:
    """JSON-serializable form of a :class:`DivergenceReport`.

    Args:
        report: The attribution to serialize.

    Returns:
        A plain dict (via :func:`dataclasses.asdict`) suitable for
        ``json.dumps`` — the shape written to
        ``reports/qa-first-divergence.json``.
    """
    return asdict(report)


def save_dense_trace(trace: DenseTrace, output_dir: Path) -> Path:
    """Write a dense trace to ``<output_dir>/<scenario>.csv``.

    Args:
        trace: The dense trace to persist.
        output_dir: Directory to write into (typically
            ``tests/baselines/dense``); created if missing.

    Returns:
        Path to the written CSV file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{trace.scenario}.csv"
    output_path.write_bytes(dense_trace_to_csv_bytes(trace))
    return output_path


def compare_dense_csv_bytes(
    scenario: str, expected_bytes: bytes, actual_bytes: bytes
) -> tuple[bool, DivergenceReport | None]:
    """Byte-compare two dense/trace CSVs, attributing the first divergence.

    The shared cell-walk entry point behind both :func:`compare_dense_trace`
    (regression-scenario dense goldens) and ``compare-bundle``'s
    ``--dense-baseline`` leg (Task 10, E5b) — one comparison implementation,
    two callers, so a future attribution fix lands in both places at once.

    Args:
        scenario: Name threaded through to the report (a regression
            scenario, or ``"detroit_tri_county"`` for the bundle leg).
        expected_bytes: Committed golden CSV bytes.
        actual_bytes: Freshly-produced CSV bytes.

    Returns:
        Tuple of (passed, report). ``passed`` is True and the report is
        None when the bytes match exactly. On mismatch, ``passed`` is
        False. Both blobs are parsed back through
        :func:`_parse_dense_csv_bytes` first, and the two headers are
        compared *before* any cell walk: a changed column set
        (inserted/appended/removed/reordered column — e.g. a future
        dense-schema widening) short-circuits to a loud ``column="<header>"``
        report naming both header lists, rather than either misattributing
        a shifted cell to the wrong column or — worse — silently returning
        ``None`` when the trailing columns happen to still agree
        cell-for-cell. Only once the headers match does ``report``
        attribute the first divergent tick+column (E4) via
        :func:`attribute_divergence`.
    """
    if expected_bytes == actual_bytes:
        return True, None

    expected_header, expected_rows = _parse_dense_csv_bytes(expected_bytes)
    actual_header, actual_rows = _parse_dense_csv_bytes(actual_bytes)
    if expected_header != actual_header:
        return False, DivergenceReport(
            scenario=scenario,
            tick=0,
            column="<header>",
            channel="<column set changed>",
            county=None,
            expected=str(expected_header),
            actual=str(actual_header),
            magnitude=None,
            last_agreeing_tick=None,
            candidate_systems=(),
        )
    report = attribute_divergence(scenario, expected_header, expected_rows, actual_rows)
    return False, report


def compare_dense_trace(
    trace: DenseTrace, baseline_dir: Path
) -> tuple[bool, DivergenceReport | None]:
    """Byte-compare a freshly-generated dense trace against its golden CSV.

    Args:
        trace: Freshly-generated dense trace for this comparison run.
        baseline_dir: Root baseline directory (dense goldens live in its
            ``dense/`` subdirectory).

    Returns:
        Tuple of (passed, report). ``passed`` is True and the report is
        None when either the golden doesn't exist yet (dense goldens are
        opt-in per Program 13 item 2 — absence is not a failure) or the
        bytes match exactly (see :func:`compare_dense_csv_bytes` for the
        byte-comparison + attribution mechanics once both exist).
    """
    golden_path = baseline_dir / DENSE_SUBDIR / f"{trace.scenario}.csv"
    if not golden_path.exists():
        return True, None

    expected_bytes = golden_path.read_bytes()
    actual_bytes = dense_trace_to_csv_bytes(trace)
    return compare_dense_csv_bytes(trace.scenario, expected_bytes, actual_bytes)


def check_dead_columns(
    scenario: str,
    header: list[str],
    rows: list[list[str]],
    coverage: tuple[Any, ...],
) -> list[str]:
    """E3: every column must move, or carry a declared at_rest reason.

    A channel that is all-zeros/all-absent across an entire run is an
    inertness signal (the U9 failure mode) — never a default.
    """
    at_rest: dict[str, str] = {}
    for cov in coverage:
        if cov.scenario == scenario:
            at_rest = {c.channel: c.reason for c in cov.at_rest}
            break
    dead_values = {"0.0", "-0.0", "0", "False", ""}
    findings: list[str] = []
    for j, column in enumerate(header):
        if column == "tick":
            continue
        dead = all(row[j] in dead_values for row in rows)
        if dead and column not in at_rest:
            findings.append(
                f"{scenario}: channel {column!r} is at rest across the entire run "
                f"but not declared at_rest in ScenarioCoverage. Either the channel "
                f"is dead (U9-class inertness — investigate) or declare it with a "
                f"reason in tools/regression_scenarios.py."
            )
        if not dead and column in at_rest:
            findings.append(
                f"{scenario}: stale at_rest declaration — channel {column!r} is "
                f"live but declared at rest ({at_rest[column]!r}). Delete the row."
            )
    return findings


def capture_checkpoint(state: Any, tick: int) -> CheckpointData:
    """Capture state at a checkpoint tick.

    Args:
        state: WorldState
        tick: Current tick number

    Returns:
        CheckpointData instance
    """
    p_w = state.entities.get(PERIPHERY_WORKER_ID)

    return CheckpointData(
        tick=tick,
        p_w_wealth=get_entity_value(state, PERIPHERY_WORKER_ID, "wealth"),
        p_c_wealth=get_entity_value(state, COMPRADOR_ID, "wealth"),
        c_b_wealth=get_entity_value(state, CORE_BOURGEOISIE_ID, "wealth"),
        c_w_wealth=get_entity_value(state, LABOR_ARISTOCRACY_ID, "wealth"),
        imperial_rent_pool=float(getattr(state.economy, "imperial_rent_pool", 0.0)),
        exploitation_tension=get_exploitation_tension(state),
        p_w_consciousness=get_entity_value(state, PERIPHERY_WORKER_ID, "consciousness", 0.0),
        p_w_p_revolution=get_entity_value(state, PERIPHERY_WORKER_ID, "p_revolution", 0.0),
        p_w_active=bool(getattr(p_w, "active", True)) if p_w else False,
    )


def _run_scenario_ticks(
    name: str,
    max_ticks: int,
    *,
    capture_dense: bool,
) -> tuple[BaselineData, DenseTrace | None]:
    """Shared tick-loop core for sampled-checkpoint and dense capture.

    Runs the scenario exactly once. Sampled checkpoints (every
    ``CHECKPOINT_INTERVAL`` ticks, tick 0, and the terminal/death tick) are
    always captured; full per-tick dense rows are captured too when
    ``capture_dense`` is True. Sharing one simulation run means enabling the
    dense leg costs zero extra ``step()`` calls — only cheap row formatting
    — which is how ``qa:regression``'s dense comparison avoids doubling
    wall time (Program 13 item 2, wall-time honesty).

    Args:
        name: Scenario name from ``SCENARIOS``.
        max_ticks: Maximum ticks to run.
        capture_dense: Whether to also build a ``DenseTrace``.

    Returns:
        Tuple of (BaselineData, DenseTrace or None). The second element is
        None iff ``capture_dense`` is False.
    """
    state, sim_config, defines = create_scenario(name)
    config_info = SCENARIOS[name]
    persistent_context: dict[str, Any] = {}
    # D4: Vol III calculator_overrides built ONCE per scenario run — the
    # calculators are stateless/reused across ticks, mirroring the cadence
    # _legacy.py's Simulation already uses (one calculator_overrides dict
    # persists across the whole run, rebuilt only per ServiceContainer.create
    # call inside step() itself). single_county additionally needs a
    # real-FIPS tensor_registry (E2a) — every other scenario carries no
    # county_fips, so a registry would be unreachable from them.
    calculator_overrides = (
        build_single_county_overrides(defines)
        if name == "single_county"
        else _build_vol3_calculator_overrides(defines)
    )

    checkpoints: list[CheckpointData] = []
    ticks_survived = 0
    final_outcome = "SURVIVED"

    # Capture initial state
    checkpoints.append(capture_checkpoint(state, 0))

    dense_header: list[str] = []
    dense_rows: list[list[str]] = []
    entity_ids: list[str] = []
    edge_keys: list[tuple[str, str]] = []
    counties: list[str] = []
    if capture_dense:
        dense_header, entity_ids, edge_keys, counties = _dense_header(state)
        dense_rows.append(_dense_row(state, 0, entity_ids, edge_keys, counties, persistent_context))

    for tick in range(1, max_ticks + 1):
        state = step(
            state,
            sim_config,
            persistent_context,
            defines,
            calculator_overrides=calculator_overrides,
        )
        ticks_survived = tick

        # Checkpoint at intervals
        if tick % CHECKPOINT_INTERVAL == 0 or tick == max_ticks:
            checkpoints.append(capture_checkpoint(state, tick))

        if capture_dense:
            dense_rows.append(
                _dense_row(state, tick, entity_ids, edge_keys, counties, persistent_context)
            )

        # Check for death
        p_w = state.entities.get(PERIPHERY_WORKER_ID)
        if p_w and is_dead(p_w):
            final_outcome = "DIED"
            checkpoints.append(capture_checkpoint(state, tick))
            break

    baseline = BaselineData(
        scenario=name,
        description=config_info["description"],
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        defines_hash=hash_defines(defines),
        max_ticks=max_ticks,
        checkpoints=checkpoints,
        final_outcome=final_outcome,
        ticks_survived=ticks_survived,
    )
    dense_trace = (
        DenseTrace(scenario=name, header=dense_header, rows=dense_rows) if capture_dense else None
    )
    return baseline, dense_trace


def run_scenario(
    name: str,
    max_ticks: int = DEFAULT_MAX_TICKS,
) -> BaselineData:
    """Run scenario and collect baseline data.

    Args:
        name: Scenario name
        max_ticks: Maximum ticks to run

    Returns:
        BaselineData instance
    """
    baseline, _dense = _run_scenario_ticks(name, max_ticks, capture_dense=False)
    return baseline


def run_scenario_dense(
    name: str,
    max_ticks: int = DEFAULT_MAX_TICKS,
) -> tuple[BaselineData, DenseTrace]:
    """Run scenario, collecting both sampled checkpoints and a dense trace.

    Args:
        name: Scenario name
        max_ticks: Maximum ticks to run

    Returns:
        Tuple of (BaselineData, DenseTrace) from the same simulation run.
    """
    baseline, dense = _run_scenario_ticks(name, max_ticks, capture_dense=True)
    assert dense is not None  # capture_dense=True guarantees this
    return baseline, dense


def save_baseline(baseline: BaselineData, output_dir: Path) -> Path:
    """Save baseline to JSON file.

    Args:
        baseline: BaselineData to save
        output_dir: Output directory

    Returns:
        Path to saved file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{baseline.scenario}.json"

    # Convert to dict with checkpoint dicts
    data = {
        "scenario": baseline.scenario,
        "description": baseline.description,
        "generated_at": baseline.generated_at,
        "defines_hash": baseline.defines_hash,
        "max_ticks": baseline.max_ticks,
        "checkpoints": [asdict(cp) for cp in baseline.checkpoints],
        "final_outcome": baseline.final_outcome,
        "ticks_survived": baseline.ticks_survived,
    }

    output_path.write_text(json.dumps(data, indent=2))
    return output_path


def load_baseline(path: Path) -> BaselineData:
    """Load baseline from JSON file.

    Args:
        path: Path to JSON file

    Returns:
        BaselineData instance
    """
    data = json.loads(path.read_text())

    checkpoints = [
        CheckpointData(
            tick=cp["tick"],
            p_w_wealth=cp["p_w_wealth"],
            p_c_wealth=cp["p_c_wealth"],
            c_b_wealth=cp["c_b_wealth"],
            c_w_wealth=cp["c_w_wealth"],
            imperial_rent_pool=cp["imperial_rent_pool"],
            exploitation_tension=cp["exploitation_tension"],
            p_w_consciousness=cp["p_w_consciousness"],
            p_w_p_revolution=cp["p_w_p_revolution"],
            p_w_active=cp["p_w_active"],
        )
        for cp in data["checkpoints"]
    ]

    return BaselineData(
        scenario=data["scenario"],
        description=data["description"],
        generated_at=data["generated_at"],
        defines_hash=data["defines_hash"],
        max_ticks=data["max_ticks"],
        checkpoints=checkpoints,
        final_outcome=data["final_outcome"],
        ticks_survived=data["ticks_survived"],
    )


def compare_checkpoints(
    expected: CheckpointData,
    actual: CheckpointData,
    tolerance: float = TOLERANCE,
) -> list[str]:
    """Compare two checkpoints, return list of differences.

    Args:
        expected: Expected checkpoint
        actual: Actual checkpoint
        tolerance: Tolerance for float comparison

    Returns:
        List of difference descriptions (empty if match)
    """
    diffs: list[str] = []

    if expected.tick != actual.tick:
        diffs.append(f"tick: {expected.tick} != {actual.tick}")

    # Compare float fields
    float_fields = [
        "p_w_wealth",
        "p_c_wealth",
        "c_b_wealth",
        "c_w_wealth",
        "imperial_rent_pool",
        "exploitation_tension",
        "p_w_consciousness",
        "p_w_p_revolution",
    ]

    for field in float_fields:
        exp_val = getattr(expected, field)
        act_val = getattr(actual, field)
        if abs(exp_val - act_val) > tolerance:
            diffs.append(f"{field}: {exp_val:.6f} != {act_val:.6f}")

    # Compare bool fields
    if expected.p_w_active != actual.p_w_active:
        diffs.append(f"p_w_active: {expected.p_w_active} != {actual.p_w_active}")

    return diffs


def compare_baselines(
    expected: BaselineData,
    actual: BaselineData,
) -> tuple[bool, list[str]]:
    """Compare two baselines.

    Args:
        expected: Expected baseline
        actual: Actual baseline

    Returns:
        Tuple of (passed, list of differences)
    """
    diffs: list[str] = []

    # Compare outcomes
    if expected.final_outcome != actual.final_outcome:
        diffs.append(f"final_outcome: {expected.final_outcome} != {actual.final_outcome}")

    if expected.ticks_survived != actual.ticks_survived:
        diffs.append(f"ticks_survived: {expected.ticks_survived} != {actual.ticks_survived}")

    # E5a (modernization program): defines_hash gates. A GameDefines change
    # without a baseline ceremony is exactly the silent-drift the gate exists
    # to catch; the five stale hashes that motivated this were refreshed
    # (value-identical) in the same commit that armed this tooth.
    if expected.defines_hash != actual.defines_hash:
        diffs.append(
            f"defines_hash mismatch ({expected.defines_hash} -> {actual.defines_hash}): "
            f"GameDefines changed without a baseline ceremony. If intentional, run "
            f"'mise run qa:regression-generate-dense' and commit the regenerated "
            f"baselines with a declared drift table (test(baselines): ...)."
        )

    # Compare checkpoints
    min_checkpoints = min(len(expected.checkpoints), len(actual.checkpoints))

    for i in range(min_checkpoints):
        cp_diffs = compare_checkpoints(expected.checkpoints[i], actual.checkpoints[i])
        if cp_diffs:
            tick = expected.checkpoints[i].tick
            for d in cp_diffs:
                diffs.append(f"tick {tick}: {d}")

    # Check for different checkpoint counts
    if len(expected.checkpoints) != len(actual.checkpoints):
        diffs.append(f"checkpoint count: {len(expected.checkpoints)} != {len(actual.checkpoints)}")

    passed = len([d for d in diffs if not d.startswith("WARNING")]) == 0
    return passed, diffs


def _abort_on_dead_columns(name: str, trace: DenseTrace) -> None:
    """E3: print dead-column findings and abort the write with exit 1.

    Called before :func:`save_dense_trace` in both the all-scenarios and
    single-scenario ``generate`` paths. A freshly-generated dense trace
    carrying an undeclared dead channel (or a stale ``at_rest`` row that no
    longer describes reality) must never be written as a new golden — that
    would silently canonize the very inertness/staleness
    :func:`check_dead_columns` exists to catch (Constitution III.11, Loud
    Failure).

    Args:
        name: Scenario name, used both to look up its coverage row and to
            prefix the printed findings.
        trace: The freshly-built dense trace, not yet saved.

    Raises:
        SystemExit: With code 1, if any dead-column findings exist. Nothing
            is written in that case.
    """
    findings = check_dead_columns(name, trace.header, trace.rows, SCENARIO_COVERAGE)
    if findings:
        for finding in findings:
            print(f"  DEAD COLUMN: {finding}")
        raise SystemExit(1)


def generate_all_baselines(
    output_dir: Path, force: bool = False, dense: bool = False
) -> list[Path]:
    """Generate baselines for all scenarios.

    Args:
        output_dir: Output directory
        force: Overwrite existing files
        dense: Also (re)generate the per-tick dense trace CSV under
            ``<output_dir>/dense/<scenario>.csv`` (Program 13 item 2). Does
            not change whether a scenario is (re)generated — that's still
            governed by ``force`` — only what gets written when it is.

    Returns:
        List of generated file paths (JSON only; dense CSV paths are
        printed but not included, to keep this function's return contract
        unchanged for any existing caller).

    Raises:
        SystemExit: With code 1, via :func:`_abort_on_dead_columns`, if any
            scenario's freshly-generated dense trace carries an undeclared
            dead channel or a stale ``at_rest`` row (E3). Nothing for that
            scenario (or any scenario after it in iteration order) is
            written in that case.
    """
    generated: list[Path] = []

    for name in SCENARIOS:
        output_path = output_dir / f"{name}.json"

        if output_path.exists() and not force:
            print(f"  SKIP {name}: baseline exists (use --force to overwrite)")
            continue

        print(f"  Generating {name}...", end=" ", flush=True)
        baseline, dense_trace = _run_scenario_ticks(name, DEFAULT_MAX_TICKS, capture_dense=dense)
        if dense and dense_trace is not None:
            _abort_on_dead_columns(name, dense_trace)
        path = save_baseline(baseline, output_dir)
        if dense and dense_trace is not None:
            dense_path = save_dense_trace(dense_trace, output_dir / DENSE_SUBDIR)
            print(
                f"OK ({baseline.ticks_survived} ticks, {baseline.final_outcome}) + {dense_path.name}"
            )
        else:
            print(f"OK ({baseline.ticks_survived} ticks, {baseline.final_outcome})")
        generated.append(path)

    return generated


def compare_all_baselines(baseline_dir: Path) -> tuple[int, int]:
    """Compare current behavior against all baselines.

    Every scenario run also builds a dense trace (zero extra ``step()``
    calls — see :func:`_run_scenario_ticks`) and byte-compares it against
    ``<baseline_dir>/dense/<scenario>.csv`` when that golden exists
    (Program 13 item 2); a dense mismatch fails the scenario just like a
    checkpoint mismatch.

    On any dense-gate FAIL, the first-divergence attribution (E4,
    :func:`attribute_divergence`) is printed and every failing scenario's
    :class:`DivergenceReport` is written to
    :data:`FIRST_DIVERGENCE_REPORT_PATH` (``reports/qa-first-divergence.json``)
    for machine consumption. Any stale report from a prior run is removed
    up front, and the file is only (re)written when at least one scenario
    actually diverged — a green run leaves no misleading report behind.

    E3: :func:`check_dead_columns` also runs on every scenario's freshly
    computed actual trace, unconditionally — never gated behind
    ``dense_ok`` — so an undeclared dead channel (or a stale ``at_rest`` row)
    is reported even on a run where the bytes already mismatched for an
    unrelated reason; both signals matter during triage. Any finding is a
    non-WARNING diff and fails the scenario's gate.

    Args:
        baseline_dir: Directory containing baseline JSON files

    Returns:
        Tuple of (passed_count, failed_count)
    """
    passed = 0
    failed = 0
    divergence_reports: list[DivergenceReport] = []

    if FIRST_DIVERGENCE_REPORT_PATH.exists():
        FIRST_DIVERGENCE_REPORT_PATH.unlink()

    for name in SCENARIOS:
        baseline_path = baseline_dir / f"{name}.json"

        if not baseline_path.exists():
            # Loud, not a silent skip: a scenario declared in SCENARIOS with
            # no committed baseline is a known pending state (e.g.
            # single_county, Task 8/E2a — its baseline mints in Task 11's
            # ceremony), not a bug. Neither passed nor failed is incremented,
            # so this never hard-fails compare — the other scenarios still
            # gate normally.
            print(f"  PENDING CEREMONY: {name} (no baseline committed — run 'generate' first)")
            continue

        print(f"  Comparing {name}...", end=" ", flush=True)

        # Load expected baseline
        expected = load_baseline(baseline_path)

        # Run current simulation once, capturing both checkpoints and the
        # dense trace.
        actual, dense_actual = run_scenario_dense(name, max_ticks=expected.max_ticks)

        # Compare. Dead-column findings are computed on the freshly-computed
        # actual trace unconditionally (not nested behind `dense_ok`) — a
        # byte mismatch must never short-circuit this check; both signals
        # matter during triage.
        ok, diffs = compare_baselines(expected, actual)
        dense_ok, dense_report = compare_dense_trace(dense_actual, baseline_dir)
        dead_column_findings = check_dead_columns(
            name, dense_actual.header, dense_actual.rows, SCENARIO_COVERAGE
        )

        if ok and dense_ok and not dead_column_findings:
            print("PASS")
            passed += 1
        else:
            print("FAIL")
            failed += 1
            for diff in diffs:
                print(f"    {diff}")
            if not dense_ok and dense_report is not None:
                print(_format_divergence_report(dense_report))
                divergence_reports.append(dense_report)
            for finding in dead_column_findings:
                print(f"    {finding}")

    if divergence_reports:
        FIRST_DIVERGENCE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        FIRST_DIVERGENCE_REPORT_PATH.write_text(
            json.dumps([divergence_report_json(r) for r in divergence_reports], indent=2)
        )

    return passed, failed


def _determinism_leg(scenario: str = "imperial_circuit") -> tuple[bool, list[str]]:
    """Two independent OS processes generate the same scenario; bytes must match.

    Folded from tests/unit/tools/test_regression_construction_cadence_determinism.py
    (U7.0) into the gate itself (E5b). PYTHONHASHSEED is stripped so each
    child randomizes its own hash seed — two processes sharing one seed would
    be a false-positive determinism proof. The fast-tier unit test stays in
    place unchanged (a mirror of this same mechanism, run on every ``pytest``
    invocation rather than only on ``compare``).

    Args:
        scenario: Scenario name passed to both child ``generate`` calls.

    Returns:
        Tuple of (passed, problems). ``problems`` is empty iff both
        processes' sampled-checkpoint JSON (minus the wall-clock
        ``generated_at`` field) and dense-trace CSV bytes agree exactly.
    """
    import tempfile

    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        dirs = [Path(tmp) / "a", Path(tmp) / "b"]
        for d in dirs:
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "generate",
                    "--scenario",
                    scenario,
                    "--dense",
                    "--output",
                    str(d),
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
                env={k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"},
                timeout=300,
            )
            if result.returncode != 0:
                return False, [f"determinism leg: generate failed in {d}: {result.stderr[-500:]}"]
        a = json.loads((dirs[0] / f"{scenario}.json").read_text())
        b = json.loads((dirs[1] / f"{scenario}.json").read_text())
        a.pop("generated_at", None)
        b.pop("generated_at", None)
        if a != b:
            problems.append(f"determinism leg: {scenario}.json differs between two processes")
        csv_a = (dirs[0] / DENSE_SUBDIR / f"{scenario}.csv").read_bytes()
        csv_b = (dirs[1] / DENSE_SUBDIR / f"{scenario}.csv").read_bytes()
        if csv_a != csv_b:
            problems.append(
                f"determinism leg: dense CSV differs between two processes ({scenario})"
            )
    return not problems, problems


def _compare_bundle_command(args: Any) -> int:
    """Spec-064 US4: compare a headless-runner bundle to the baseline summary.

    Returns 0 on PASS (within tolerances), 1 on FAIL.
    """
    import json as _json

    bundle_dir: Path = args.bundle
    baseline_path: Path = args.baseline
    summary_path = bundle_dir / "summary.json"

    if not summary_path.exists():
        print(f"ERROR: bundle summary not found at {summary_path}", file=sys.stderr)
        return 1
    if not baseline_path.exists():
        print(f"ERROR: baseline not found at {baseline_path}", file=sys.stderr)
        return 1

    actual = _json.loads(summary_path.read_text())
    expected = _json.loads(baseline_path.read_text())

    print("Spec-064 e2e regression compare")
    print(f"  bundle:   {summary_path}")
    print(f"  baseline: {baseline_path}")
    print()

    failures: list[str] = []

    # 1. counties_alive: exact match (per spec — terminal-tick scope sanity).
    actual_alive = int(actual["terminal_state"]["counties_alive"])
    expected_alive = int(expected["terminal_state"]["counties_alive"])
    if actual_alive != expected_alive:
        failures.append(
            f"counties_alive mismatch: actual={actual_alive}, expected={expected_alive}"
        )
    else:
        print(f"  ✓ counties_alive == {actual_alive}")

    # 1b. Population liveness (ADR044-completion gate, 2026-07-02): every
    # econ-alive county must still hold a living population at the terminal
    # tick. Guards against the closed-drain extinction class of failure
    # (statewide death at tick ~68-70) that hid for two months because no
    # gate asserted survival. Tolerant of old bundles/baselines that
    # predate the field.
    actual_pop = actual["terminal_state"].get("counties_with_population")
    if actual_pop is not None:
        actual_pop = int(actual_pop)
        if actual_pop != actual_alive:
            failures.append(
                f"population liveness: only {actual_pop} of {actual_alive} "
                "econ-alive counties have living populations at the terminal tick"
            )
        else:
            print(f"  ✓ population liveness: {actual_pop}/{actual_alive} counties alive")

    # 2. total_v: within ±tolerance%.
    actual_v = float(actual["terminal_state"]["total_v"])
    expected_v = float(expected["terminal_state"]["total_v"])
    if expected_v != 0:
        delta_pct = abs(actual_v - expected_v) / abs(expected_v) * 100.0
        marker = "✓" if delta_pct <= args.total_v_tolerance_pct else "✗"
        print(
            f"  {marker} total_v: actual={actual_v:.4g}, expected={expected_v:.4g}, "
            f"Δ={delta_pct:.3f}%% (tolerance ±{args.total_v_tolerance_pct}%%)"
        )
        if delta_pct > args.total_v_tolerance_pct:
            failures.append(
                f"total_v drift: Δ={delta_pct:.3f}%% exceeds tolerance ±{args.total_v_tolerance_pct}%%"
            )
    elif actual_v != 0:
        failures.append(f"total_v drift: baseline=0, actual={actual_v}")

    # 3. critical conservation violations: zero allowed.
    critical = [a for a in actual.get("conservation_audit", []) if a.get("severity") == "critical"]
    if critical:
        failures.append(f"{len(critical)} critical conservation violation(s)")
    else:
        print("  ✓ no critical conservation violations")

    # 4. dense_trace.csv byte-compare against the detroit_tri_county dense
    # golden (Task 10, E2b). The Task 11 ceremony mints
    # tests/baselines/dense/detroit_tri_county.csv, so a missing golden is
    # now a hard regression (deletion/never-minted), not a pending state.
    dense_baseline_path: Path = args.dense_baseline
    dense_bundle_path = bundle_dir / "dense_trace.csv"
    if not dense_bundle_path.exists():
        failures.append(f"dense_trace.csv missing from bundle: {dense_bundle_path}")
    else:
        dense_bundle_bytes = dense_bundle_path.read_bytes()
        if not dense_baseline_path.exists():
            failures.append(f"detroit_tri_county dense golden not found: {dense_baseline_path}")
        else:
            dense_ok, dense_report = compare_dense_csv_bytes(
                "detroit_tri_county",
                dense_baseline_path.read_bytes(),
                dense_bundle_bytes,
            )
            if dense_ok:
                print("  ✓ dense_trace.csv byte-identical to detroit_tri_county golden")
            else:
                failures.append("dense_trace.csv diverged from detroit_tri_county golden")
                if dense_report is not None:
                    print(_format_divergence_report(dense_report))

        # 5. Bundle-path dead-column guard (Task 11, E3 extension): runs
        # unconditionally on the bundle's own dense trace — never gated
        # behind dense_ok/golden-presence above, mirroring
        # compare_all_baselines's "never gated" dead-column check — so an
        # undeclared dead channel (or a stale at_rest row) is caught even on
        # a bundle whose byte-compare already failed for an unrelated reason.
        bundle_header, bundle_rows = _parse_dense_csv_bytes(dense_bundle_bytes)
        dead_column_findings = check_dead_columns(
            "detroit_tri_county", bundle_header, bundle_rows, SCENARIO_COVERAGE
        )
        if dead_column_findings:
            failures.extend(dead_column_findings)
            for finding in dead_column_findings:
                print(f"  {finding}")
        elif bundle_header:
            print("  ✓ no dead columns in dense_trace.csv (bundle)")

    print()
    if failures:
        print("REGRESSION DETECTED:")
        for f in failures:
            print(f"  - {f}")
        print()
        print("If these changes are intentional, regenerate the baseline:")
        print("  cp <bundle>/summary.json tests/baselines/michigan-e2e.json")
        return 1

    print("All regression checks passed.")
    return 0


def main() -> int:
    """Run regression testing."""
    parser = argparse.ArgumentParser(
        description="Regression testing for simulation formula drift",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate baselines (after intentional changes)
    %(prog)s generate --force

    # Compare against baselines (in CI)
    %(prog)s compare

    # Generate specific scenario
    %(prog)s generate --scenario imperial_circuit
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Generate subcommand
    gen_parser = subparsers.add_parser("generate", help="Generate baseline files")
    gen_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing baselines",
    )
    gen_parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Generate only specific scenario",
    )
    gen_parser.add_argument(
        "--output",
        type=Path,
        default=BASELINE_DIR,
        help=f"Output directory (default: {BASELINE_DIR})",
    )
    gen_parser.add_argument(
        "--dense",
        action="store_true",
        help=(
            "Also (re)generate the per-tick dense trace CSV under "
            "<output>/dense/<scenario>.csv (Program 13 item 2)"
        ),
    )

    # Compare subcommand
    cmp_parser = subparsers.add_parser("compare", help="Compare against baselines")
    cmp_parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=BASELINE_DIR,
        help=f"Baseline directory (default: {BASELINE_DIR})",
    )

    # List subcommand
    subparsers.add_parser("list", help="List available scenarios")

    # Spec-064: compare-bundle subcommand — diff a headless-runner
    # artifact bundle's summary.json against tests/baselines/michigan-e2e.json.
    bundle_parser = subparsers.add_parser(
        "compare-bundle",
        help="Compare a spec-064 artifact bundle against the michigan-e2e baseline",
    )
    bundle_parser.add_argument(
        "--bundle",
        type=Path,
        required=True,
        help="Path to the artifact bundle directory (containing summary.json)",
    )
    bundle_parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("tests/baselines/michigan-e2e.json"),
        help="Path to the baseline summary.json (default: tests/baselines/michigan-e2e.json)",
    )
    bundle_parser.add_argument(
        "--total-v-tolerance-pct",
        type=float,
        default=1.0,
        help="±%% tolerance on terminal_state.total_v (default: 1.0%%)",
    )
    bundle_parser.add_argument(
        "--dense-baseline",
        type=Path,
        default=Path("tests/baselines/dense/detroit_tri_county.csv"),
        help=(
            "Path to the committed detroit_tri_county dense golden CSV "
            "(default: tests/baselines/dense/detroit_tri_county.csv). Byte-"
            "compared against the bundle's dense_trace.csv (Task 10, E2b)."
        ),
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "compare-bundle":
        return _compare_bundle_command(args)

    if args.command == "list":
        print("Available scenarios:")
        for name, config in SCENARIOS.items():
            print(f"  {name}: {config['description']}")
            if config["defines_overrides"]:
                for k, v in config["defines_overrides"].items():
                    print(f"    {k}={v}")
        return 0

    if args.command == "generate":
        print("Generating regression baselines...")
        print(f"Output directory: {args.output}")
        print()

        if args.scenario:
            if args.scenario not in SCENARIOS:
                print(f"Error: Unknown scenario '{args.scenario}'")
                return 1
            # Generate single scenario
            baseline, dense_trace = _run_scenario_ticks(
                args.scenario, DEFAULT_MAX_TICKS, capture_dense=args.dense
            )
            if args.dense and dense_trace is not None:
                _abort_on_dead_columns(args.scenario, dense_trace)
            path = save_baseline(baseline, args.output)
            print(f"Generated: {path}")
            if args.dense and dense_trace is not None:
                dense_path = save_dense_trace(dense_trace, args.output / DENSE_SUBDIR)
                print(f"Generated dense: {dense_path}")
        else:
            generate_all_baselines(args.output, force=args.force, dense=args.dense)

        print()
        print("Done!")
        return 0

    if args.command == "compare":
        print("Regression comparison...")
        print(f"Baseline directory: {args.baseline_dir}")
        print()

        if not args.baseline_dir.exists():
            print(f"Error: Baseline directory not found: {args.baseline_dir}")
            print("Run 'generate' first to create baselines")
            return 1

        passed, failed = compare_all_baselines(args.baseline_dir)

        print()
        print(f"Results: {passed} passed, {failed} failed")

        # E5b: two-process determinism proof, folded into the gate itself
        # (Task 10). Runs unconditionally, every `compare` invocation,
        # regardless of the scenario-comparison outcome above — this leg
        # answers a different question (is a single scenario's construction
        # deterministic across independent OS processes?), so it must not
        # be skipped just because a header mismatch already failed the
        # scenario loop (the sanctioned qa:regression-modernization red
        # window: this leg is expected to PASS even while the 5 originals
        # are red on the widened header).
        print()
        print("Determinism leg (E5b): two independent processes, imperial_circuit...")
        det_start = time.perf_counter()
        det_ok, det_problems = _determinism_leg()
        det_elapsed = time.perf_counter() - det_start
        if det_ok:
            print(f"  PASS ({det_elapsed:.2f}s)")
        else:
            print(f"  FAIL ({det_elapsed:.2f}s)")
            for problem in det_problems:
                print(f"    {problem}")
            failed += 1

        if failed > 0:
            print()
            print("REGRESSION DETECTED!")
            print("If these changes are intentional, regenerate baselines:")
            print("  poetry run python tools/regression_test.py generate --force")
            return 1

        print("All regression tests passed!")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
