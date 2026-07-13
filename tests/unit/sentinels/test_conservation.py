"""Economic-Conservation sentinel — per-tick accounting identities over a trace.

Instance #3 of the ``babylon.sentinels`` family. Walks the shared deterministic
dense trace (``shared_tick.trace``) and asserts every declared
:class:`~babylon.sentinels.conservation.ConservationIdentity` holds on all 53
rows (ticks 0–52) of the ``imperial_circuit`` scenario, within its declared float
tolerance (Amendment Q — no bare ``==``).

The declared invariants (see ``babylon.sentinels.conservation.registry``):

- **economic_columns_finite** — no ``NaN``/``inf`` in any numeric economic cell.
- **imperial_rent_pool_depletion** — the imperial-rent reserve is finite,
  non-negative, bounded above by its initial value, and non-increasing
  tick-over-tick (a reserve that only depletes).

The check *logic* lives here (not in the layer-0.5 package): it needs the live
engine-built trace, which is far above the sentinels' import boundary. Each
real-trace invariant is paired with an **efficacy proof** — a synthetic corrupted
trace on which the same check reds — so a green invariant is provably falsifiable
(Constitution III.11), not vacuous.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import pytest

from babylon.sentinels.conservation import (
    ALL_NUMERIC_COLUMNS,
    CONSERVATION_REGISTRY,
    IMPERIAL_RENT_POOL_COLUMN,
    ConservationIdentity,
)
from babylon.sentinels.dynamic import DynamicArtifact

pytestmark = pytest.mark.unit

#: Dense-trace cells rendered by ``regression_test._format_dense_value`` for
#: bool fields; skipped by the numeric-finiteness walk (they are not floats).
_BOOL_CELLS: frozenset[str] = frozenset({"True", "False"})


def _is_numeric_cell(column: str, cell: str) -> bool:
    """Whether a dense-trace cell is a numeric (float) value to be checked.

    :param column: The cell's header column name.
    :param cell: The raw string cell.
    :returns: ``False`` for the ``tick`` index column and bool literals
        (``"True"``/``"False"``), ``True`` otherwise.
    """
    return column != "tick" and cell not in _BOOL_CELLS


def _column_series(header: list[str], rows: list[list[str]], column: str) -> list[float]:
    """Extract one column's values across every row as parsed floats.

    :param header: The dense-trace header row.
    :param rows: The dense-trace data rows (string cells aligned to ``header``).
    :param column: The header column to extract.
    :returns: One float per row, in row order.
    :raises KeyError: if ``column`` is not in ``header`` (a loud contract break).
    """
    col_index = header.index(column)
    return [float(row[col_index]) for row in rows]


def _check_finite_all(header: list[str], rows: list[list[str]]) -> list[str]:
    """Assert no numeric cell in any row is ``NaN``/``inf`` (wildcard identity).

    :param header: The dense-trace header row.
    :param rows: The dense-trace data rows.
    :returns: One ``non-finite`` finding per offending cell; empty when clean.
    """
    findings: list[str] = []
    for row in rows:
        tick = row[0]
        for col_index, cell in enumerate(row):
            column = header[col_index]
            if _is_numeric_cell(column, cell) and not math.isfinite(float(cell)):
                findings.append(f"non-finite: tick {tick} column {column} = {cell!r}")
    return findings


def _check_series(identity: ConservationIdentity, series: list[float]) -> list[str]:
    """Apply a single-column identity's enabled clauses to one value series.

    :param identity: The declared identity (its ``column`` names ``series``).
    :param series: One float per row, in row order.
    :returns: Category-tagged findings (``non-finite`` / ``non-negative`` /
        ``bounded`` / ``non-increasing``); empty when every clause holds.
    """
    findings: list[str] = []
    tol = identity.abs_tolerance
    col = identity.column

    for tick, value in enumerate(series):
        if identity.require_finite and not math.isfinite(value):
            findings.append(f"non-finite: tick {tick} {col} = {value!r}")
        if identity.non_negative and value < -tol:
            findings.append(f"non-negative: tick {tick} {col} = {value!r}")

    if identity.bounded_by_initial and series:
        initial = series[0]
        for tick, value in enumerate(series):
            if value > initial + tol:
                findings.append(f"bounded: tick {tick} {col} = {value!r} > initial {initial!r}")

    if identity.non_increasing:
        for tick in range(len(series) - 1):
            delta = series[tick + 1] - series[tick]
            if delta > tol:
                findings.append(f"non-increasing: tick {tick}->{tick + 1} {col} rose by {delta!r}")

    return findings


def check_identity(
    identity: ConservationIdentity,
    header: list[str],
    rows: list[list[str]],
) -> list[str]:
    """Apply one declared conservation identity to a dense trace.

    Pure over its inputs (no engine access), so both the real-trace invariant
    tests and the synthetic efficacy tests drive the same code path. Findings are
    prefixed with a category tag (``non-finite`` / ``non-negative`` /
    ``non-increasing`` / ``bounded``) so efficacy tests can assert the *right*
    clause reds.

    :param identity: The declared identity to enforce.
    :param header: The dense-trace header row.
    :param rows: The dense-trace data rows.
    :returns: A list of human-readable violation strings — empty when the
        identity holds across every row (Constitution III.11: findings are loud).
    """
    if identity.column == ALL_NUMERIC_COLUMNS:
        return _check_finite_all(header, rows) if identity.require_finite else []
    return _check_series(identity, _column_series(header, rows, identity.column))


def _trace_parts(shared_tick: DynamicArtifact) -> tuple[list[str], list[list[str]]]:
    """Return a deep copy of ``(header, rows)`` safe to mutate in efficacy tests.

    The ``shared_tick`` artifact is session-scoped and consumed read-only by
    several sentinels, so efficacy tests corrupt a **copy**, never the fixture.

    :param shared_tick: The shared dynamic-tick artifact.
    :returns: A ``(header, rows)`` deep copy.
    """
    trace: Any = shared_tick.trace
    return list(trace.header), copy.deepcopy(list(trace.rows))


# ---------------------------------------------------------------------------
# Invariants — must hold on the real imperial_circuit trace.
# ---------------------------------------------------------------------------


def test_registry_declares_the_two_identities() -> None:
    """The registry declares finiteness and imperial-rent depletion, well-formed."""
    names = {identity.name for identity in CONSERVATION_REGISTRY}
    assert names == {"economic_columns_finite", "imperial_rent_pool_depletion"}
    pool = next(i for i in CONSERVATION_REGISTRY if i.name == "imperial_rent_pool_depletion")
    assert pool.column == IMPERIAL_RENT_POOL_COLUMN
    assert pool.abs_tolerance > 0.0  # a real, declared tolerance (Amendment Q)


def test_all_declared_identities_hold(shared_tick: DynamicArtifact) -> None:
    """Every declared identity holds across all 53 rows of the real trace."""
    header, rows = shared_tick.trace.header, shared_tick.trace.rows
    assert len(rows) == shared_tick.ticks + 1  # 0..52 inclusive
    for identity in CONSERVATION_REGISTRY:
        findings = check_identity(identity, header, rows)
        assert findings == [], f"{identity.name} violated: {findings}"


def test_imperial_rent_pool_actually_depletes(shared_tick: DynamicArtifact) -> None:
    """The pool genuinely draws down — the invariant is not vacuously flat.

    Guards against an honest-but-empty pass: if the pool never moved, the
    non-increasing clause would hold trivially. It must strictly fall.
    """
    series = _column_series(
        shared_tick.trace.header, shared_tick.trace.rows, IMPERIAL_RENT_POOL_COLUMN
    )
    assert series[-1] < series[0]


# ---------------------------------------------------------------------------
# Efficacy — each clause must RED on a synthetic defect (III.11, TDD).
# ---------------------------------------------------------------------------


def test_finiteness_reds_on_injected_inf(shared_tick: DynamicArtifact) -> None:
    """A single ``inf`` in any economic cell reds the finiteness identity."""
    header, rows = _trace_parts(shared_tick)
    finite = next(i for i in CONSERVATION_REGISTRY if i.name == "economic_columns_finite")
    assert check_identity(finite, header, rows) == []  # clean before corruption
    rows[10][header.index("C001_wealth")] = "inf"
    findings = check_identity(finite, header, rows)
    assert any(f.startswith("non-finite") for f in findings)


def test_finiteness_reds_on_injected_nan(shared_tick: DynamicArtifact) -> None:
    """A single ``nan`` in any economic cell reds the finiteness identity."""
    header, rows = _trace_parts(shared_tick)
    finite = next(i for i in CONSERVATION_REGISTRY if i.name == "economic_columns_finite")
    rows[5][header.index("economy_imperial_rent_pool")] = "nan"
    findings = check_identity(finite, header, rows)
    assert any(f.startswith("non-finite") for f in findings)


def test_depletion_reds_on_pool_refill(shared_tick: DynamicArtifact) -> None:
    """A tick where the pool *rises* reds the non-increasing clause."""
    header, rows = _trace_parts(shared_tick)
    pool = next(i for i in CONSERVATION_REGISTRY if i.name == "imperial_rent_pool_depletion")
    col = header.index(IMPERIAL_RENT_POOL_COLUMN)
    # Bump tick 20 above tick 19: a spontaneous refill the closed circuit forbids.
    prev = float(rows[19][col])
    rows[20][col] = repr(prev + 1.0)
    findings = check_identity(pool, header, rows)
    assert any(f.startswith("non-increasing") for f in findings)


def test_depletion_reds_on_negative_pool(shared_tick: DynamicArtifact) -> None:
    """A negative reserve reds the non-negative clause."""
    header, rows = _trace_parts(shared_tick)
    pool = next(i for i in CONSERVATION_REGISTRY if i.name == "imperial_rent_pool_depletion")
    rows[30][header.index(IMPERIAL_RENT_POOL_COLUMN)] = repr(-5.0)
    findings = check_identity(pool, header, rows)
    assert any(f.startswith("non-negative") for f in findings)


def test_depletion_reds_on_exceeding_initial(shared_tick: DynamicArtifact) -> None:
    """A reserve above its seeded initial value reds the bounded clause."""
    header, rows = _trace_parts(shared_tick)
    pool = next(i for i in CONSERVATION_REGISTRY if i.name == "imperial_rent_pool_depletion")
    col = header.index(IMPERIAL_RENT_POOL_COLUMN)
    initial = float(rows[0][col])
    rows[40][col] = repr(initial + 10.0)
    findings = check_identity(pool, header, rows)
    assert any(f.startswith("bounded") for f in findings)


def test_tolerance_absorbs_subulp_noise_but_not_real_refill(shared_tick: DynamicArtifact) -> None:
    """The declared tolerance is honest: it hides sub-ULP noise, not a real rise.

    A ``+1e-12`` bump (below the ``1e-9`` tolerance) must NOT red; the ``+1.0``
    refill above must. Proves the tolerance is a real threshold, not slack that
    makes the check unfalsifiable.
    """
    header, rows = _trace_parts(shared_tick)
    pool = next(i for i in CONSERVATION_REGISTRY if i.name == "imperial_rent_pool_depletion")
    col = header.index(IMPERIAL_RENT_POOL_COLUMN)
    prev = float(rows[19][col])
    rows[20][col] = repr(prev + 1e-12)  # sub-tolerance: still monotone-clean
    assert not any(f.startswith("non-increasing") for f in check_identity(pool, header, rows))


def test_malformed_identity_reds_at_construction() -> None:
    """A wildcard identity carrying an ordered clause fails loudly at import (III.11)."""
    with pytest.raises(ValueError, match="wildcard column supports only require_finite"):
        ConservationIdentity(
            name="bad",
            column=ALL_NUMERIC_COLUMNS,
            abs_tolerance=0.0,
            non_increasing=True,
        )


def test_negative_tolerance_reds_at_construction() -> None:
    """A negative tolerance is rejected loudly (Amendment Q: tolerances are >= 0)."""
    with pytest.raises(ValueError, match="abs_tolerance must be >= 0"):
        ConservationIdentity(name="bad", column="x", abs_tolerance=-1.0)
