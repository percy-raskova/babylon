#!/usr/bin/env python3
"""Run mutmut with temporary path configuration.

Usage:
    python tools/run_mutmut.py                    # Use pyproject.toml paths
    python tools/run_mutmut.py --critical         # Critical paths only
    python tools/run_mutmut.py --paths src/foo/   # Custom paths

Results are saved to .mutmut-cache (SQLite database).
View with: poetry run mutmut results
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import tomli
    import tomli_w
except ImportError:
    print("Installing tomli and tomli-w...")
    subprocess.run([sys.executable, "-m", "pip", "install", "tomli", "tomli-w"], check=True)
    import tomli
    import tomli_w


CRITICAL_PATHS = [
    "src/babylon/systems/formulas.py",
    "src/babylon/engine/systems/economic.py",
    "src/babylon/engine/systems/survival.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run mutmut with path configuration")
    parser.add_argument("--critical", action="store_true", help="Test critical paths only")
    parser.add_argument("--paths", nargs="+", help="Custom paths to mutate")
    args = parser.parse_args()

    # Load pyproject.toml
    pyproject_path = Path("pyproject.toml")
    with open(pyproject_path, "rb") as f:
        config = tomli.load(f)

    # Determine paths
    if args.paths:
        paths = args.paths
    elif args.critical:
        paths = CRITICAL_PATHS
    else:
        paths = config.get("tool", {}).get("mutmut", {}).get("paths_to_mutate", ["src/"])

    # Always use unit tests only (integration tests have multiprocessing conflicts)
    config.setdefault("tool", {}).setdefault("mutmut", {})["tests_dir"] = ["tests/unit/"]

    print(f"Mutation testing paths: {paths}")

    # Create temporary pyproject.toml with our paths
    config.setdefault("tool", {}).setdefault("mutmut", {})["paths_to_mutate"] = paths

    # Write to temp file and run mutmut
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as tmp:
        tomli_w.dump(config, tmp)
        tmp_path = Path(tmp.name)

    try:
        # Copy temp to pyproject.toml, run mutmut, restore
        original = pyproject_path.read_bytes()
        pyproject_path.write_bytes(tmp_path.read_bytes())

        try:
            # --max-children=1 avoids multiprocessing conflict with pytest-asyncio
            result = subprocess.run(
                [sys.executable, "-m", "mutmut", "run", "--max-children=1"],
                check=False,
            )
            return result.returncode
        finally:
            # Always restore original
            pyproject_path.write_bytes(original)
            print("\nConfig restored.")
    finally:
        tmp_path.unlink()


if __name__ == "__main__":
    sys.exit(main())
