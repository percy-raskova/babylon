"""Storage budget gate — compare a run bundle's footprint to a baseline.

Spec: 087-storage-foundations (FR-012/FR-013).

Reads the ``storage`` block the headless runner emits into ``manifest.json``
(spec-087 FR-009) and compares per-table **rows/tick** against a committed
baseline. Rows/tick is deterministic for a fixed scenario; byte counts
fluctuate with vacuum/checkpoint timing and are informational only.

This locks in the storage-program wins the same way spec-069's
``bridge_db_reads`` block locked in the reference-read win: a change that
silently re-inflates per-tick writes fails ``mise run qa:storage-budget``.

Usage::

    # Write a baseline from a bundle (after intentional changes)
    python tools/storage_budget.py generate --bundle <dir> \\
        --out tests/baselines/storage-budget-5t.json

    # Gate: compare a bundle against the committed baseline
    python tools/storage_budget.py check --bundle <dir> \\
        --baseline tests/baselines/storage-budget-5t.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_manifest_storage(bundle_dir: Path) -> dict[str, Any]:
    """Load the ``storage`` block from a bundle's manifest.json.

    Args:
        bundle_dir: Artifact bundle directory (contains manifest.json).

    Returns:
        The manifest's ``storage`` dict.

    Raises:
        FileNotFoundError: manifest.json missing from the bundle.
        KeyError: manifest has no ``storage`` block (collection failed —
            treated as a hard gate failure by ``check``).
    """
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if "storage" not in manifest:
        raise KeyError(
            f"manifest at {manifest_path} has no 'storage' block "
            "(storage collection failed or pre-spec-087 runner)"
        )
    storage: dict[str, Any] = manifest["storage"]
    return storage


def generate_baseline(
    storage: dict[str, Any],
    *,
    scope: str,
    ticks: int,
    tolerance_pct: float = 10.0,
) -> dict[str, Any]:
    """Shape a baseline document from a bundle's storage block.

    Args:
        storage: Manifest ``storage`` block.
        scope: Scenario scope name the baseline was generated from.
        ticks: Tick count of the generating run.
        tolerance_pct: Allowed rows/tick overshoot before ``check`` fails.

    Returns:
        Baseline dict ready to be JSON-encoded.
    """
    return {
        "schema_version": "1.0",
        "generated_from": {"scope": scope, "ticks": ticks},
        "tolerance_pct": float(tolerance_pct),
        "rows_per_tick": {
            entry["table"]: float(entry["session_rows_per_tick"]) for entry in storage["tables"]
        },
    }


def check_bundle(
    storage: dict[str, Any],
    baseline: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Compare a storage block against a baseline.

    Per baseline table: actual rows/tick must not exceed
    ``budget * (1 + tolerance_pct/100)``. Under-budget passes (that is the
    point of the storage program); tables absent from the bundle count as
    zero rows; bundle tables missing from the baseline are noted but pass
    (they get budgeted at the next ``generate``).

    Args:
        storage: Manifest ``storage`` block of the run under test.
        baseline: Committed baseline document.

    Returns:
        ``(ok, report_lines)``.
    """
    tolerance_pct = float(baseline["tolerance_pct"])
    budgets: dict[str, float] = {name: float(v) for name, v in baseline["rows_per_tick"].items()}
    actuals: dict[str, float] = {
        entry["table"]: float(entry["session_rows_per_tick"]) for entry in storage["tables"]
    }

    ok = True
    report: list[str] = []
    for table, budget in sorted(budgets.items()):
        actual = actuals.get(table, 0.0)
        limit = budget * (1.0 + tolerance_pct / 100.0)
        if actual > limit:
            ok = False
            report.append(
                f"  ✗ {table}: {actual:g} rows/tick exceeds budget "
                f"{budget:g} (+{tolerance_pct:g}% => limit {limit:g})"
            )
        elif actual < budget:
            report.append(
                f"  ✓ {table}: {actual:g} rows/tick under budget {budget:g} "
                "(improvement — regenerate baseline to lock in)"
            )
        else:
            report.append(f"  ✓ {table}: {actual:g} rows/tick within budget {budget:g}")

    for table in sorted(set(actuals) - set(budgets)):
        report.append(
            f"  • {table}: {actuals[table]:g} rows/tick not in baseline "
            "(new table — regenerate baseline to budget it)"
        )

    return ok, report


def _generate_command(args: argparse.Namespace) -> int:
    storage = load_manifest_storage(args.bundle)
    manifest = json.loads((args.bundle / "manifest.json").read_text())
    inputs = manifest["reproducibility"]["deterministic_inputs"]
    scope = args.scope or "+".join(inputs.get("scope_fips", [])) or "unknown"
    baseline = generate_baseline(
        storage,
        scope=scope,
        ticks=int(inputs["ticks"]),
        tolerance_pct=args.tolerance_pct,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(baseline, indent=2) + "\n")
    print(f"Baseline written: {args.out}")
    for table, rpt in sorted(baseline["rows_per_tick"].items()):
        print(f"  {table}: {rpt:g} rows/tick")
    return 0


def _check_command(args: argparse.Namespace) -> int:
    try:
        storage = load_manifest_storage(args.bundle)
    except (FileNotFoundError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    baseline = json.loads(args.baseline.read_text())

    print("Spec-087 storage budget check")
    print(f"  bundle:   {args.bundle / 'manifest.json'}")
    print(f"  baseline: {args.baseline}")
    print(
        f"  db size:  {storage['db_total_bytes'] / 1_048_576:.1f} MiB over "
        f"{storage['ticks_persisted']} ticks (informational)"
    )
    print()

    ok, report = check_bundle(storage, baseline)
    for line in report:
        print(line)
    print()
    if not ok:
        print("STORAGE BUDGET EXCEEDED.")
        print("If the growth is intentional, regenerate the baseline:")
        print(f"  python tools/storage_budget.py generate --bundle <dir> --out {args.baseline}")
        return 1
    print("Storage budget check passed.")
    return 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Storage budget gate for headless-runner bundles (spec-087)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Write a baseline from a bundle's manifest")
    gen.add_argument("--bundle", type=Path, required=True, help="Artifact bundle directory")
    gen.add_argument("--out", type=Path, required=True, help="Baseline JSON destination")
    gen.add_argument("--scope", type=str, default=None, help="Scope label override")
    gen.add_argument("--tolerance-pct", type=float, default=10.0)
    gen.set_defaults(func=_generate_command)

    chk = sub.add_parser("check", help="Compare a bundle against a committed baseline")
    chk.add_argument("--bundle", type=Path, required=True, help="Artifact bundle directory")
    chk.add_argument("--baseline", type=Path, required=True, help="Committed baseline JSON")
    chk.set_defaults(func=_check_command)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
