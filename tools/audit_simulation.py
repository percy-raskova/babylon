#!/usr/bin/env python3
"""Generate simulation health audit report.

Spec-064 migration: this tool no longer reads in-memory ``WorldState`` —
the legacy 4-node imperial-circuit scenario is replaced by routed calls
to the headless Postgres-backed runner via ``shared.run_simulation``.
The 3-scenario baseline / starvation / glut structure and the
``reports/audit_latest.md`` output path are preserved (SC-004 /
FR-014); some fields render ``"N/A"`` because the headless MVP does
not surface per-entity death ticks or metabolic overshoot.

Usage:
    poetry run python tools/audit_simulation.py
    poetry run python tools/audit_simulation.py --output reports/audit_latest.md
    poetry run python tools/audit_simulation.py --max-ticks 100
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from shared import inject_parameter, run_simulation  # noqa: E402

from babylon.config.defines import GameDefines  # noqa: E402

DEFAULT_OUTPUT: Final[str] = "reports/audit_latest.md"
DEFAULT_MAX_TICKS: Final[int] = 52

STARVATION_EXTRACTION: Final[float] = 0.05
GLUT_EXTRACTION: Final[float] = 0.99
GLUT_SUBSISTENCE: Final[float] = 0.0

BASELINE_MIN_TICKS: Final[int] = 50
STARVATION_DEATH_THRESHOLD: Final[int] = 40


def run_full_simulation(
    defines: GameDefines,
    max_ticks: int,
    track_comprador: bool = False,  # noqa: ARG001 — kept for signature compat
) -> dict[str, Any]:
    """Run a single headless simulation and return audit-shaped metrics.

    Args:
        defines: GameDefines configuration (rng_seed flows through; other
            fields are accepted for signature compatibility but not
            applied to the MVP runner's no-op carry-forward).
        max_ticks: Maximum ticks to run.
        track_comprador: Accepted for signature compat; the headless MVP
            cannot distinguish per-entity death.

    Returns:
        Dict with the legacy keys: ``ticks_survived``, ``outcome``,
        ``comprador_death_tick`` (always ``None``),
        ``worker_death_tick`` (always ``None``), ``max_overshoot_ratio``
        (always ``0.0``).
    """
    base_result = run_simulation(defines, max_ticks=max_ticks)
    return {
        "final_state": None,
        "ticks_survived": base_result["ticks_survived"],
        "outcome": base_result["outcome"],
        "comprador_death_tick": None,
        "worker_death_tick": None,
        "max_overshoot_ratio": 0.0,
    }


def format_overshoot(ratio: float) -> str:
    """Format overshoot ratio for display."""
    if ratio > 0:
        return f"{ratio:.2f}"
    return "N/A"


def generate_report(
    baseline_result: dict[str, Any],
    starvation_result: dict[str, Any],
    glut_result: dict[str, Any],
) -> str:
    """Generate markdown health report from the three scenario results."""
    baseline_pass = baseline_result["ticks_survived"] >= BASELINE_MIN_TICKS
    # Starvation / glut signals require per-entity tracking the MVP runner
    # does not provide; the report emits "DEGRADED" markers per spec-064
    # transition note. starvation_pass kept as the rendered marker.
    starvation_pass: bool | None = None

    status = "HEALTHY" if baseline_pass else "UNHEALTHY"
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")

    starvation_marker = (
        f"Tick {starvation_result['comprador_death_tick']}"
        if starvation_result["comprador_death_tick"]
        else "DEGRADED (MVP runner — no per-entity death detection)"
    )
    starvation_status = "✓ PASS" if starvation_pass else "⊘ SKIP (spec-064 MVP)"
    glut_status = "⊘ SKIP (spec-064 MVP — no metabolic overshoot)"

    return f"""# Simulation Health Report

**Generated**: {timestamp}
**Status**: {status}
**Backend**: spec-064 headless Postgres runner

## Scenario Results

| Scenario | Expected | Actual | Status |
|----------|----------|--------|--------|
| A: Baseline | Survives ≥{BASELINE_MIN_TICKS} ticks \
| {baseline_result["ticks_survived"]} ticks \
| {"✓ PASS" if baseline_pass else "✗ FAIL"} |
| B: Starvation | Comprador dies <{STARVATION_DEATH_THRESHOLD} ticks \
| {starvation_marker} | {starvation_status} |
| C: Glut | Overshoot >1.0 \
| {format_overshoot(glut_result["max_overshoot_ratio"])} | {glut_status} |

## Scenario Parameters

| Scenario | Parameters |
|----------|------------|
| Baseline | Default GameDefines |
| Starvation | extraction_efficiency={STARVATION_EXTRACTION} |
| Glut | extraction_efficiency={GLUT_EXTRACTION}, default_subsistence={GLUT_SUBSISTENCE} |

## Interpretation

- **Baseline**: Validates that the headless runner completes ``--ticks``
  without erroring out (SC-002 surface check).
- **Starvation / Glut**: Per-entity death and metabolic-overshoot
  signals are degraded under the spec-064 MVP runner. Future commits
  bring them back via real engine→Postgres bridging.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate simulation health audit report (spec-064: headless-runner-backed)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__ or "",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output markdown path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=DEFAULT_MAX_TICKS,
        help=f"Maximum simulation ticks (default: {DEFAULT_MAX_TICKS})",
    )
    args = parser.parse_args()

    base_defines = GameDefines()

    print("Running simulation audit (spec-064 backend)...")
    print()

    print(f"[A] Baseline test ({args.max_ticks} ticks)...", end=" ", flush=True)
    baseline_result = run_full_simulation(base_defines, args.max_ticks)
    baseline_pass = baseline_result["ticks_survived"] >= BASELINE_MIN_TICKS
    print(f"{baseline_result['outcome']} ({baseline_result['ticks_survived']} ticks)")

    print(f"[B] Starvation test (extraction={STARVATION_EXTRACTION})...", end=" ", flush=True)
    starvation_defines = inject_parameter(
        base_defines,
        "economy.extraction_efficiency",
        STARVATION_EXTRACTION,
    )
    starvation_result = run_full_simulation(
        starvation_defines,
        args.max_ticks,
        track_comprador=True,
    )
    print(f"{starvation_result['outcome']} (degraded — no per-entity tracking)")

    print(
        f"[C] Glut test (extraction={GLUT_EXTRACTION}, subsistence={GLUT_SUBSISTENCE})...",
        end=" ",
        flush=True,
    )
    glut_defines = inject_parameter(base_defines, "economy.extraction_efficiency", GLUT_EXTRACTION)
    glut_defines = inject_parameter(glut_defines, "survival.default_subsistence", GLUT_SUBSISTENCE)
    glut_result = run_full_simulation(glut_defines, args.max_ticks)
    print(f"{glut_result['outcome']} (degraded — no overshoot detection)")
    print()

    report = generate_report(baseline_result, starvation_result, glut_result)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    print(f"Audit report saved to {output_path}")
    print()
    print("Summary:")
    print(f"  Baseline:   {'PASS' if baseline_pass else 'FAIL'}")
    print("  Starvation: SKIP (spec-064 MVP)")
    print("  Glut:       SKIP (spec-064 MVP)")
    return 0 if baseline_pass else 1


if __name__ == "__main__":
    sys.exit(main())
