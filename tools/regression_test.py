#!/usr/bin/env python3
"""Regression testing for simulation formula drift detection.

Generates and compares baseline JSON files to detect unintended changes
to simulation behavior during refactoring.

Usage:
    # Generate baselines (after intentional changes)
    poetry run python tools/regression_test.py generate --force

    # Compare against baselines (in CI)
    poetry run python tools/regression_test.py compare

Scenarios:
    - imperial_circuit: 4-node default scenario
    - two_node: Minimal worker vs owner
    - starvation: Low extraction efficiency stress
    - glut: High extraction with metabolic overshoot
    - fascist_bifurcation: Consciousness routing to national identity

See Also:
    :doc:`/ai-docs/tooling.yaml` regression_testing section
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

# Add src and tools to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

# Import from centralized shared module (ADR036)
from shared import (
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    LABOR_ARISTOCRACY_ID,
    PERIPHERY_WORKER_ID,
    inject_parameter,
    is_dead,
)

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import (
    create_imperial_circuit_scenario,
    create_two_node_scenario,
)
from babylon.engine.simulation_engine import step

# Constants
BASELINE_DIR: Final[Path] = Path(__file__).parent.parent / "tests" / "baselines"
DEFAULT_MAX_TICKS: Final[int] = 52
CHECKPOINT_INTERVAL: Final[int] = 10
TOLERANCE: Final[float] = 1e-5

# Scenario configurations
SCENARIOS: Final[dict[str, dict[str, Any]]] = {
    "imperial_circuit": {
        "description": "4-node default scenario",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {},
    },
    "two_node": {
        "description": "Minimal worker vs owner",
        "factory": "create_two_node_scenario",
        "defines_overrides": {},
    },
    "starvation": {
        "description": "Low extraction efficiency stress",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {
            "economy.extraction_efficiency": 0.05,
        },
    },
    "glut": {
        "description": "High extraction with metabolic overshoot",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {
            "economy.extraction_efficiency": 0.99,
            "survival.default_subsistence": 0.0,
        },
    },
    "fascist_bifurcation": {
        "description": "Consciousness routing to national identity",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {
            "economy.extraction_efficiency": 0.7,
            "consciousness.drift_sensitivity_k": 0.3,
        },
    },
}


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


def hash_defines(defines: GameDefines) -> str:
    """Generate hash of GameDefines for change detection.

    Args:
        defines: GameDefines instance

    Returns:
        SHA256 hash string (first 16 chars)
    """
    json_str = defines.model_dump_json(indent=None)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def create_scenario(
    name: str,
) -> tuple[Any, Any, GameDefines]:
    """Create scenario by name.

    Args:
        name: Scenario name from SCENARIOS

    Returns:
        Tuple of (WorldState, SimulationConfig, GameDefines)
    """
    config = SCENARIOS[name]

    # Call factory function
    factory_name = config["factory"]
    if factory_name == "create_imperial_circuit_scenario":
        state, sim_config, base_defines = create_imperial_circuit_scenario()
    elif factory_name == "create_two_node_scenario":
        state, sim_config, base_defines = create_two_node_scenario()
    else:
        raise ValueError(f"Unknown factory: {factory_name}")

    # Apply overrides
    defines = base_defines
    for path, value in config["defines_overrides"].items():
        defines = inject_parameter(defines, path, value)

    return state, sim_config, defines


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
    state, sim_config, defines = create_scenario(name)
    config_info = SCENARIOS[name]
    persistent_context: dict[str, Any] = {}

    checkpoints: list[CheckpointData] = []
    ticks_survived = 0
    final_outcome = "SURVIVED"

    # Capture initial state
    checkpoints.append(capture_checkpoint(state, 0))

    for tick in range(1, max_ticks + 1):
        state = step(state, sim_config, persistent_context, defines)
        ticks_survived = tick

        # Checkpoint at intervals
        if tick % CHECKPOINT_INTERVAL == 0 or tick == max_ticks:
            checkpoints.append(capture_checkpoint(state, tick))

        # Check for death
        p_w = state.entities.get(PERIPHERY_WORKER_ID)
        if p_w and is_dead(p_w):
            final_outcome = "DIED"
            checkpoints.append(capture_checkpoint(state, tick))
            break

    return BaselineData(
        scenario=name,
        description=config_info["description"],
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        defines_hash=hash_defines(defines),
        max_ticks=max_ticks,
        checkpoints=checkpoints,
        final_outcome=final_outcome,
        ticks_survived=ticks_survived,
    )


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

    # Compare defines hash
    if expected.defines_hash != actual.defines_hash:
        diffs.append(
            f"WARNING: defines_hash changed ({expected.defines_hash} -> {actual.defines_hash})"
        )
        diffs.append("  This may indicate GameDefines parameter changes")

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


def generate_all_baselines(output_dir: Path, force: bool = False) -> list[Path]:
    """Generate baselines for all scenarios.

    Args:
        output_dir: Output directory
        force: Overwrite existing files

    Returns:
        List of generated file paths
    """
    generated: list[Path] = []

    for name in SCENARIOS:
        output_path = output_dir / f"{name}.json"

        if output_path.exists() and not force:
            print(f"  SKIP {name}: baseline exists (use --force to overwrite)")
            continue

        print(f"  Generating {name}...", end=" ", flush=True)
        baseline = run_scenario(name)
        path = save_baseline(baseline, output_dir)
        print(f"OK ({baseline.ticks_survived} ticks, {baseline.final_outcome})")
        generated.append(path)

    return generated


def compare_all_baselines(baseline_dir: Path) -> tuple[int, int]:
    """Compare current behavior against all baselines.

    Args:
        baseline_dir: Directory containing baseline JSON files

    Returns:
        Tuple of (passed_count, failed_count)
    """
    passed = 0
    failed = 0

    for name in SCENARIOS:
        baseline_path = baseline_dir / f"{name}.json"

        if not baseline_path.exists():
            print(f"  SKIP {name}: no baseline (run 'generate' first)")
            continue

        print(f"  Comparing {name}...", end=" ", flush=True)

        # Load expected baseline
        expected = load_baseline(baseline_path)

        # Run current simulation
        actual = run_scenario(name, max_ticks=expected.max_ticks)

        # Compare
        ok, diffs = compare_baselines(expected, actual)

        if ok:
            print("PASS")
            passed += 1
        else:
            print("FAIL")
            failed += 1
            for diff in diffs:
                print(f"    {diff}")

    return passed, failed


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

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

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
            baseline = run_scenario(args.scenario)
            path = save_baseline(baseline, args.output)
            print(f"Generated: {path}")
        else:
            generate_all_baselines(args.output, force=args.force)

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
