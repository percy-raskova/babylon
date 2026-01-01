#!/usr/bin/env python3
"""Monte Carlo uncertainty quantification for simulation outcomes.

Runs N replications of the simulation to capture stochastic variance
from the StruggleSystem's EXCESSIVE_FORCE probability and other
random elements. Provides confidence intervals for outcome metrics.

Usage:
    poetry run python tools/monte_carlo.py --samples 100
    poetry run python tools/monte_carlo.py --samples 1000 --seed 42
    poetry run python tools/monte_carlo.py --samples 100 --param economy.extraction_efficiency=0.5

Output:
    CSV with per-sample results and aggregate statistics.

Sample Size Guidance:
    - 100 samples: Fast exploratory run (~1-2 min)
    - 1000 samples: Good precision for most analyses (~10-20 min)
    - 10000+ samples: Publication-quality (NIST recommended)

See Also:
    :doc:`/ai-docs/tooling.yaml` monte_carlo section
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

# Add src and tools to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

# Import from centralized shared module (ADR036)
from shared import (
    DEFAULT_MAX_TICKS,
    inject_parameter,
    run_simulation,
)

from babylon.config.defines import GameDefines

# Try to import scipy for t-distribution CI, fall back to normal approximation
try:
    from scipy import stats

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# Constants
DEFAULT_SAMPLES: Final[int] = 100
DEFAULT_OUTPUT: Final[str] = "results/monte_carlo.csv"
CONFIDENCE_LEVEL: Final[float] = 0.95


@dataclass
class SampleResult:
    """Result from a single simulation sample."""

    sample_id: int
    seed: int
    ticks_survived: int
    outcome: str
    max_tension: float
    final_wealth: float


@dataclass
class AggregateStats:
    """Aggregate statistics across all samples."""

    n_samples: int
    n_survived: int
    n_died: int
    survival_rate: float

    ticks_mean: float
    ticks_std: float
    ticks_ci_lower: float
    ticks_ci_upper: float

    tension_mean: float
    tension_std: float

    wealth_mean: float
    wealth_std: float


def calculate_confidence_interval(
    data: list[float],
    confidence: float = CONFIDENCE_LEVEL,
) -> tuple[float, float]:
    """Calculate confidence interval using t-distribution.

    Args:
        data: List of sample values
        confidence: Confidence level (default 0.95 for 95% CI)

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    n = len(data)
    if n < 2:
        return (0.0, 0.0)

    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / (n - 1)
    std = variance**0.5

    # Use t-distribution for small samples, fall back to z-score approximation
    t_critical = (
        stats.t.ppf((1 + confidence) / 2, n - 1) if HAS_SCIPY else (1.96 if n > 30 else 2.0)
    )

    margin = t_critical * (std / (n**0.5))
    return (mean - margin, mean + margin)


def run_monte_carlo(
    n_samples: int,
    defines: GameDefines,
    max_ticks: int = DEFAULT_MAX_TICKS,
    base_seed: int | None = None,
) -> tuple[list[SampleResult], AggregateStats]:
    """Run N simulation replications sequentially.

    Args:
        n_samples: Number of samples to run
        defines: GameDefines configuration
        max_ticks: Maximum ticks per simulation
        base_seed: Base random seed (None = random)

    Returns:
        Tuple of (list of SampleResults, AggregateStats)
    """
    results: list[SampleResult] = []

    # Use base_seed to generate deterministic per-sample seeds
    if base_seed is not None:
        random.seed(base_seed)

    print(f"Running {n_samples} Monte Carlo samples...")
    print(f"  Max ticks per sample: {max_ticks}")
    if base_seed is not None:
        print(f"  Base seed: {base_seed}")
    print()

    for i in range(n_samples):
        # Generate sample-specific seed
        sample_seed = random.randint(0, 2**31 - 1)
        random.seed(sample_seed)

        # Run simulation
        result = run_simulation(defines, max_ticks=max_ticks)

        sample_result = SampleResult(
            sample_id=i + 1,
            seed=sample_seed,
            ticks_survived=result["ticks_survived"],
            outcome=result["outcome"],
            max_tension=result["max_tension"],
            final_wealth=result["final_wealth"],
        )
        results.append(sample_result)

        # Progress indicator every 10%
        if (i + 1) % max(1, n_samples // 10) == 0 or i == n_samples - 1:
            pct = 100 * (i + 1) // n_samples
            print(f"\r  [{i + 1}/{n_samples}] {pct}% complete", end="", flush=True)

    print()  # Newline after progress

    # Calculate aggregate statistics
    ticks_data = [r.ticks_survived for r in results]
    tension_data = [r.max_tension for r in results]
    wealth_data = [r.final_wealth for r in results]

    n_survived = sum(1 for r in results if r.outcome == "SURVIVED")
    n_died = n_samples - n_survived

    ticks_mean = sum(ticks_data) / n_samples
    ticks_variance = sum((x - ticks_mean) ** 2 for x in ticks_data) / max(1, n_samples - 1)
    ticks_std = ticks_variance**0.5

    tension_mean = sum(tension_data) / n_samples
    tension_variance = sum((x - tension_mean) ** 2 for x in tension_data) / max(1, n_samples - 1)
    tension_std = tension_variance**0.5

    wealth_mean = sum(wealth_data) / n_samples
    wealth_variance = sum((x - wealth_mean) ** 2 for x in wealth_data) / max(1, n_samples - 1)
    wealth_std = wealth_variance**0.5

    ci_lower, ci_upper = calculate_confidence_interval(ticks_data)

    stats_result = AggregateStats(
        n_samples=n_samples,
        n_survived=n_survived,
        n_died=n_died,
        survival_rate=n_survived / n_samples,
        ticks_mean=ticks_mean,
        ticks_std=ticks_std,
        ticks_ci_lower=ci_lower,
        ticks_ci_upper=ci_upper,
        tension_mean=tension_mean,
        tension_std=tension_std,
        wealth_mean=wealth_mean,
        wealth_std=wealth_std,
    )

    return results, stats_result


def write_csv(
    results: list[SampleResult],
    stats: AggregateStats,
    output_path: Path,
) -> None:
    """Write results to CSV file.

    Args:
        results: List of per-sample results
        stats: Aggregate statistics
        output_path: Path to write CSV
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(
            [
                "sample_id",
                "seed",
                "ticks_survived",
                "outcome",
                "max_tension",
                "final_wealth",
            ]
        )

        # Per-sample data
        for r in results:
            writer.writerow(
                [
                    r.sample_id,
                    r.seed,
                    r.ticks_survived,
                    r.outcome,
                    f"{r.max_tension:.6f}",
                    f"{r.final_wealth:.6f}",
                ]
            )

        # Blank row before summary
        writer.writerow([])

        # Summary statistics
        writer.writerow(["# Summary Statistics"])
        writer.writerow(["n_samples", stats.n_samples])
        writer.writerow(["n_survived", stats.n_survived])
        writer.writerow(["n_died", stats.n_died])
        writer.writerow(["survival_rate", f"{stats.survival_rate:.4f}"])
        writer.writerow(["ticks_mean", f"{stats.ticks_mean:.2f}"])
        writer.writerow(["ticks_std", f"{stats.ticks_std:.2f}"])
        writer.writerow(["ticks_ci_lower", f"{stats.ticks_ci_lower:.2f}"])
        writer.writerow(["ticks_ci_upper", f"{stats.ticks_ci_upper:.2f}"])
        writer.writerow(["tension_mean", f"{stats.tension_mean:.4f}"])
        writer.writerow(["tension_std", f"{stats.tension_std:.4f}"])
        writer.writerow(["wealth_mean", f"{stats.wealth_mean:.4f}"])
        writer.writerow(["wealth_std", f"{stats.wealth_std:.4f}"])


def format_report(stats: AggregateStats, base_seed: int | None = None) -> str:
    """Format markdown report.

    Args:
        stats: Aggregate statistics
        base_seed: Random seed used (None if not set)

    Returns:
        Markdown report string
    """
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    seed_info = f"Base Seed: {base_seed}" if base_seed is not None else "Base Seed: (random)"

    ci_width = stats.ticks_ci_upper - stats.ticks_ci_lower

    return f"""# Monte Carlo Uncertainty Quantification Report

**Generated**: {timestamp}
**Samples**: {stats.n_samples}
**{seed_info}**

## Survival Outcomes

| Metric | Value |
|--------|-------|
| Survived | {stats.n_survived} ({100 * stats.survival_rate:.1f}%) |
| Died | {stats.n_died} ({100 * (1 - stats.survival_rate):.1f}%) |

## Ticks Survived

| Statistic | Value |
|-----------|-------|
| Mean | {stats.ticks_mean:.2f} |
| Std Dev | {stats.ticks_std:.2f} |
| 95% CI | [{stats.ticks_ci_lower:.2f}, {stats.ticks_ci_upper:.2f}] |
| CI Width | {ci_width:.2f} |

## Secondary Metrics

| Metric | Mean | Std Dev |
|--------|------|---------|
| Max Tension | {stats.tension_mean:.4f} | {stats.tension_std:.4f} |
| Final Wealth | {stats.wealth_mean:.4f} | {stats.wealth_std:.4f} |

## Interpretation

- **Survival Rate**: {100 * stats.survival_rate:.1f}% of simulations survived to max ticks
- **CI Width**: {ci_width:.2f} ticks (narrower = more deterministic behavior)
- **Variance Ratio**: {stats.ticks_std / max(stats.ticks_mean, 0.01):.2f} (lower = more predictable)

{"**Note**: scipy not available, using z-score approximation for CI" if not HAS_SCIPY else ""}
"""


def parse_param_arg(param_str: str | None) -> dict[str, float]:
    """Parse --param argument in format 'path=value'.

    Args:
        param_str: Parameter string in format 'category.field=value'

    Returns:
        Dict mapping param_path -> value (empty if not provided)

    Raises:
        ValueError: If param_str is invalid format
    """
    if param_str is None:
        return {}

    if "=" not in param_str:
        raise ValueError(f"--param must be in format 'path=value', got: {param_str}")

    path, value_str = param_str.split("=", 1)
    try:
        value = float(value_str)
    except ValueError as e:
        raise ValueError(f"Invalid value '{value_str}' in --param, must be numeric") from e

    return {path.strip(): value}


def main() -> int:
    """Run Monte Carlo uncertainty quantification."""
    parser = argparse.ArgumentParser(
        description="Monte Carlo uncertainty quantification for simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Quick exploratory run (100 samples)
    %(prog)s --samples 100

    # Deterministic run with seed
    %(prog)s --samples 1000 --seed 42

    # With parameter override
    %(prog)s --samples 100 --param economy.extraction_efficiency=0.5
        """,
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=DEFAULT_SAMPLES,
        help=f"Number of simulation samples (default: {DEFAULT_SAMPLES})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Base random seed for reproducibility (default: random)",
    )
    parser.add_argument(
        "--param",
        type=str,
        default=None,
        help="Parameter override in format 'path=value'",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=DEFAULT_MAX_TICKS,
        help=f"Maximum ticks per simulation (default: {DEFAULT_MAX_TICKS})",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(DEFAULT_OUTPUT),
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Output markdown report path (optional)",
    )
    args = parser.parse_args()

    # Parse parameter override
    try:
        params = parse_param_arg(args.param)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Build defines
    base_defines = GameDefines()
    for path, value in params.items():
        base_defines = inject_parameter(base_defines, path, value)

    # Run Monte Carlo
    results, stats = run_monte_carlo(
        n_samples=args.samples,
        defines=base_defines,
        max_ticks=args.max_ticks,
        base_seed=args.seed,
    )

    # Write CSV
    write_csv(results, stats, args.csv)
    print(f"\nResults written to: {args.csv}")

    # Generate and display report
    report = format_report(stats, args.seed)
    print(report)

    # Optionally write report to file
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report)
        print(f"Report written to: {args.report}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
