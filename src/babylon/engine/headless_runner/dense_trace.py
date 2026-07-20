"""Per-tick dense-trace capture for the headless-runner artifact bundle.

Program: qa:regression modernization, Task 10 (E2b). A companion to
``tools/regression_test.py``'s dense golden traces (Task 9, E3) but a
DIFFERENT column schema, per the design brief: this bundle-side trace
captures the same per-county v/c/s/k/population aggregates
``runner._county_terminal_snapshot`` already computes (there, only at the
terminal tick — here, lifted to every tick), plus each county's
surplus-value distribution breakdown (interest/ground_rent/taxes) and the
national financial parameters, both read directly off the runner's
in-memory ``BabylonGraph`` (it holds the graph across ticks — no extra
Postgres round trip for these two).

Serialized via :func:`babylon.engine.trace_format.trace_rows_to_csv_bytes`
— the same byte contract as every other dense/trace CSV in this program.
"""

from __future__ import annotations

from typing import Any, Final

from babylon.domain.economics.tick.graph_bridge import (
    NATIONAL_FINANCIAL_ATTR,
    TICK_DYNAMICS_KEY,
)
from babylon.engine.trace_format import format_trace_value

#: Per-county columns (E2b). ``total_v/c/s/k/population`` are the same
#: Postgres ``view_runtime_trace_emission`` aggregates
#: ``runner._county_terminal_snapshot`` computes (its ``v``/``c``/``s``/
#: ``k``/``population`` dict keys); ``interest``/``ground_rent``/``taxes``
#: read ``SurplusValueDistribution.interest_payments`` / ``.ground_rent`` /
#: ``.taxes_on_surplus`` off the graph's ``TICK_DYNAMICS_KEY`` county
#: states (verified against
#: ``src/babylon/domain/economics/distribution/types.py``).
DENSE_COUNTY_SUFFIXES: Final[tuple[str, ...]] = (
    "total_v",
    "total_c",
    "total_s",
    "total_k",
    "population",
    "interest",
    "ground_rent",
    "taxes",
)

#: National financial columns (E2b) — same 4 channels + key mapping as
#: ``tools/regression_test.py``'s ``_DENSE_FINANCIAL_SUFFIXES`` (Task 9):
#: ``financial_s_r`` reads the real field ``reserve_army_signal``, not a
#: literal ``s_r`` key (``EndogenousInterestRate``, verified against
#: ``src/babylon/domain/economics/credit/types.py``).
DENSE_FINANCIAL_SUFFIXES: Final[tuple[str, ...]] = (
    "endogenous_rate",
    "profit_rate_ceiling",
    "s_r",
    "tightness",
)


def dense_trace_header(counties: list[str]) -> list[str]:
    """Build the ``dense_trace.csv`` column contract for a sorted county list.

    Args:
        counties: Sorted county FIPS codes (the run's scope — fixed for the
            whole run, per ``SimulationRunConfig.scope_fips``).

    Returns:
        ``["tick", <county_<fips>_* per county, in order>, <financial_*>]``.
    """
    header = ["tick"]
    for fips in counties:
        header.extend(f"county_{fips}_{suffix}" for suffix in DENSE_COUNTY_SUFFIXES)
    header.extend(f"financial_{suffix}" for suffix in DENSE_FINANCIAL_SUFFIXES)
    return header


def dense_trace_row(
    *,
    tick: int,
    counties: list[str],
    county_snapshot: list[dict[str, Any]],
    graph: Any,
) -> list[str]:
    """Build one ``dense_trace.csv`` row for ``tick``.

    Args:
        tick: Current simulation tick.
        counties: Sorted county FIPS codes — header column order, see
            :func:`dense_trace_header`.
        county_snapshot: This tick's per-county rows — the return value of
            ``runner._county_terminal_snapshot(pool=pool,
            session_id=session_id, terminal_tick=tick)``, keyed by
            ``entity_id``.
        graph: The runner's live ``BabylonGraph`` — read post-tick.
            ``TICK_DYNAMICS_KEY`` carries the last-stamped
            ``county_states`` (real ``CountyEconomicState`` model
            instances, not a dump — mirrors
            ``tools/regression_test.py``'s ``_dense_row`` reading of the
            same graph attribute); ``NATIONAL_FINANCIAL_ATTR`` carries the
            ``NationalFinancialParameters.model_dump()`` dict. Both are
            absent (``None``) before the engine's first tick — tick 0 is a
            raw hex-state persist with no engine run — and degrade to an
            all-zero cell block for those columns, same degradation
            ``tools/regression_test.py``'s ``_dense_row`` documents for its
            own county-free / not-yet-boundary case.

    Returns:
        One formatted string cell list aligned to
        :func:`dense_trace_header`'s column order.
    """
    by_fips = {row["entity_id"]: row for row in county_snapshot}
    tick_dynamics = graph.get_graph_attr(TICK_DYNAMICS_KEY) or {}
    county_states = tick_dynamics.get("county_states", {})
    financial = graph.get_graph_attr(NATIONAL_FINANCIAL_ATTR) or {}
    endo = financial.get("endogenous_interest") or {}

    row: list[str] = [str(tick)]
    for fips in counties:
        snap = by_fips.get(fips, {})
        cs = county_states.get(fips)
        dist = getattr(cs, "surplus_distribution", None) if cs is not None else None
        row.append(format_trace_value(float(snap.get("v") or 0.0)))
        row.append(format_trace_value(float(snap.get("c") or 0.0)))
        row.append(format_trace_value(float(snap.get("s") or 0.0)))
        row.append(format_trace_value(float(snap.get("k") or 0.0)))
        row.append(format_trace_value(float(snap.get("population") or 0)))
        row.append(format_trace_value(float(getattr(dist, "interest_payments", 0.0) or 0.0)))
        row.append(format_trace_value(float(getattr(dist, "ground_rent", 0.0) or 0.0)))
        row.append(format_trace_value(float(getattr(dist, "taxes_on_surplus", 0.0) or 0.0)))
    row.append(format_trace_value(float(endo.get("rate", 0.0))))
    row.append(format_trace_value(float(endo.get("profit_rate_ceiling", 0.0))))
    row.append(format_trace_value(float(endo.get("reserve_army_signal", 0.0))))
    row.append(format_trace_value(float(endo.get("tightness", 0.0))))
    return row


__all__ = [
    "DENSE_COUNTY_SUFFIXES",
    "DENSE_FINANCIAL_SUFFIXES",
    "dense_trace_header",
    "dense_trace_row",
]
