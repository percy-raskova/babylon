#!/usr/bin/env python3
"""Detroit Validation Harness (Feature 020, T016).

Runs the Detroit multi-year simulation and compares model class
distributions against Census ACS income distribution proxies.

Census income brackets are mapped to class position proxies:
  - Proletariat:       <$25k     (brackets 1-4)
  - Petit-bourgeoisie: $25k-$50k (brackets 5-9)
  - Labor Aristocracy: $50k-$200k (brackets 10-15)
  - Bourgeoisie:       $200k+    (bracket 16)

Usage:
    python tools/validate_detroit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging

from sqlalchemy import text

from babylon.data.reference.database import get_normalized_session_factory
from babylon.engine.simulation import Simulation

logger = logging.getLogger(__name__)

# Detroit metro FIPS codes
WAYNE_FIPS = "26163"
OAKLAND_FIPS = "26125"
DETROIT_FIPS = [WAYNE_FIPS, OAKLAND_FIPS]

# Simulation parameters
START_YEAR = 2015
END_YEAR = 2023  # inclusive
YEARS = list(range(START_YEAR, END_YEAR + 1))
TOTAL_TICKS = len(YEARS) * 52  # 468

# Census income bracket → class proxy mapping
# bracket_order values from dim_income_bracket
_PROLETARIAT_BRACKETS = range(1, 5)  # <$25k
_PETIT_BOURGEOISIE_BRACKETS = range(5, 10)  # $25k-$50k
_LA_BRACKETS = range(10, 16)  # $50k-$200k
_BOURGEOISIE_BRACKETS = range(16, 17)  # $200k+

_CENSUS_QUERY = text("""
    SELECT
        dt.year,
        dc.fips,
        ib.bracket_order,
        SUM(ci.household_count) as total
    FROM fact_census_income ci
    JOIN dim_county dc ON ci.county_id = dc.county_id
    JOIN dim_time dt ON ci.time_id = dt.time_id
    JOIN dim_income_bracket ib ON ci.bracket_id = ib.bracket_id
    WHERE dc.fips IN (:fips1, :fips2)
      AND dt.year BETWEEN :start_year AND :end_year
      AND ib.bracket_order < 17
    GROUP BY dt.year, dc.fips, ib.bracket_order
    ORDER BY dt.year, dc.fips, ib.bracket_order
""")


def load_census_distributions(
    session_factory: object,
) -> dict[tuple[int, str], dict[str, float]]:
    """Load Census ACS income distributions and map to class proxies.

    Returns:
        Dict keyed by (year, fips) with values like:
        {"proletariat": 0.21, "petit_bourgeoisie": 0.19,
         "la": 0.44, "bourgeoisie": 0.07}
    """
    session = session_factory()  # type: ignore[operator]
    try:
        rows = session.execute(
            _CENSUS_QUERY,
            {
                "fips1": WAYNE_FIPS,
                "fips2": OAKLAND_FIPS,
                "start_year": START_YEAR,
                "end_year": END_YEAR,
            },
        ).fetchall()
    finally:
        session.close()

    # Aggregate brackets into class proxies
    # First pass: collect raw counts by (year, fips)
    raw: dict[tuple[int, str], dict[str, int]] = {}
    for row in rows:
        year, fips, bracket_order, count = row[0], row[1], row[2], row[3]
        key = (year, fips)
        if key not in raw:
            raw[key] = {
                "proletariat": 0,
                "petit_bourgeoisie": 0,
                "la": 0,
                "bourgeoisie": 0,
            }

        if bracket_order in _PROLETARIAT_BRACKETS:
            raw[key]["proletariat"] += count
        elif bracket_order in _PETIT_BOURGEOISIE_BRACKETS:
            raw[key]["petit_bourgeoisie"] += count
        elif bracket_order in _LA_BRACKETS:
            raw[key]["la"] += count
        elif bracket_order in _BOURGEOISIE_BRACKETS:
            raw[key]["bourgeoisie"] += count

    # Convert to shares
    result: dict[tuple[int, str], dict[str, float]] = {}
    for key, counts in raw.items():
        total = sum(counts.values())
        if total > 0:
            result[key] = {k: v / total for k, v in counts.items()}
        else:
            result[key] = dict.fromkeys(counts, 0.0)

    return result


def run_simulation() -> list[dict[str, object]]:
    """Run Detroit multi-year simulation and extract time series."""
    print(f"Creating simulation for FIPS {DETROIT_FIPS}, years {START_YEAR}-{END_YEAR}...")
    sim = Simulation.from_sqlite(
        DETROIT_FIPS,
        year=START_YEAR,
        years=YEARS,
    )

    print(f"Running {TOTAL_TICKS} ticks ({len(YEARS)} years x 52 weeks)...")
    max_ticks = TOTAL_TICKS
    for tick_num in range(max_ticks):
        sim.step()
        if (tick_num + 1) % 52 == 0:
            year_num = START_YEAR + (tick_num + 1) // 52
            print(f"  Year {year_num} complete (tick {tick_num + 1})")

    print("Extracting time series...")
    return sim.get_time_series()


def compute_divergence(model_share: float, census_share: float) -> float:
    """Compute absolute divergence between model and census shares."""
    return abs(model_share - census_share)


def format_table(
    time_series: list[dict[str, object]],
    census: dict[tuple[int, str], dict[str, float]],
) -> str:
    """Format comparison table between model and Census data."""
    lines: list[str] = []

    header = (
        f"{'Year':>4}  {'FIPS':>5}  "
        f"{'Model LA':>8}  {'Census LA':>9}  {'Divergence':>10}  "
        f"{'Model Prol':>10}  {'Census Prol':>11}  "
        f"{'Model Bourg':>11}  {'Census Bourg':>12}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    # Get unique FIPS names
    fips_names = {WAYNE_FIPS: "Wayne", OAKLAND_FIPS: "Oakland"}

    for record in sorted(time_series, key=lambda r: (r["year"], r["fips"])):  # type: ignore[arg-type]
        year = record["year"]
        fips = record["fips"]
        model_la = float(record.get("la_share", 0))  # type: ignore[arg-type]
        model_prol = float(record.get("proletariat_share", 0))  # type: ignore[arg-type]
        model_bourg = float(record.get("bourgeoisie_share", 0))  # type: ignore[arg-type]

        census_key = (year, fips)
        if census_key in census:
            census_la = census[census_key]["la"]
            census_prol = census[census_key]["proletariat"]
            census_bourg = census[census_key]["bourgeoisie"]
            divergence = compute_divergence(model_la, census_la)

            county_name = fips_names.get(str(fips), str(fips))
            lines.append(
                f"{year!s:>4}  {county_name:>5}  "
                f"{model_la:>8.3f}  {census_la:>9.3f}  {divergence:>10.3f}  "
                f"{model_prol:>10.3f}  {census_prol:>11.3f}  "
                f"{model_bourg:>11.3f}  {census_bourg:>12.3f}"
            )
        else:
            county_name = fips_names.get(str(fips), str(fips))
            lines.append(
                f"{year!s:>4}  {county_name:>5}  "
                f"{model_la:>8.3f}  {'N/A':>9}  {'N/A':>10}  "
                f"{model_prol:>10.3f}  {'N/A':>11}  "
                f"{model_bourg:>11.3f}  {'N/A':>12}"
            )

    return "\n".join(lines)


def main() -> None:
    """Run Detroit validation harness."""
    logging.basicConfig(level=logging.WARNING)

    print("=" * 70)
    print("Detroit Validation Harness (Feature 020)")
    print("=" * 70)
    print()

    # Step 1: Load Census data
    print("Loading Census ACS income distributions...")
    session_factory = get_normalized_session_factory()
    census = load_census_distributions(session_factory)
    print(f"  Loaded {len(census)} (year, fips) Census records")
    print()

    # Step 2: Run simulation
    time_series = run_simulation()
    print(f"  Extracted {len(time_series)} time series records")
    print()

    # Step 3: Output comparison table
    if not time_series:
        print("WARNING: No time series records extracted from simulation.")
        print("This may indicate TickDynamicsSystem did not execute or")
        print("no year-boundary ticks were reached.")
        return

    print("Comparison Table: Model vs Census (LA = Labor Aristocracy proxy)")
    print()
    table = format_table(time_series, census)
    print(table)

    # Step 4: Summary statistics
    print()
    print("Summary:")
    divergences: list[float] = []
    for record in time_series:
        year = record["year"]
        fips = record["fips"]
        census_key = (year, fips)
        if census_key in census:
            model_la = float(record.get("la_share", 0))  # type: ignore[arg-type]
            census_la = census[census_key]["la"]
            divergences.append(compute_divergence(model_la, census_la))

    if divergences:
        mean_div = sum(divergences) / len(divergences)
        max_div = max(divergences)
        min_div = min(divergences)
        print(f"  Mean LA divergence:  {mean_div:.4f}")
        print(f"  Max LA divergence:   {max_div:.4f}")
        print(f"  Min LA divergence:   {min_div:.4f}")
        print(f"  Records compared:    {len(divergences)}")
    else:
        print("  No overlapping years between model and Census data.")

    print()
    print("NOTE: Census income brackets are a proxy for class position.")
    print("      LA proxy = $50k-$200k income range.")
    print("      Divergence > 0.10 suggests model calibration needed.")


if __name__ == "__main__":
    main()
