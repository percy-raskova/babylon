"""Import boundary enforcement test.

Verifies that ONLY ``engine_bridge.py`` imports from the simulation engine.
No other file in ``web/`` may import ``babylon.engine``, ``babylon.models``,
``babylon.config``, ``babylon.ooda``, or ``babylon.persistence``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Root of the web application
WEB_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "web"

# These are the only prefixes that constitute "engine imports"
ENGINE_IMPORT_PREFIXES = (
    "babylon.engine",
    "babylon.models",
    "babylon.config",
    "babylon.ooda",
    "babylon.persistence",
)

# The files allowed to import engine code
ALLOWED_FILES = {
    "game/engine_bridge.py",
    "game/repositories.py",
    "game/migrations/0003_spec037_simulation_tables.py",
}


def _collect_python_files(root: Path) -> list[Path]:
    """Collect all .py files under root, excluding __pycache__."""
    results: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        results.append(path)
    return results


def _extract_imports(filepath: Path) -> list[str]:
    """Parse a Python file and return all import module strings."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules


@pytest.mark.unit
class TestImportBoundary:
    """Verify the sacred import boundary: only allowed files touch engine code."""

    def test_no_engine_imports_outside_bridge(self) -> None:
        """No web/ file except allowed files imports from babylon engine packages."""
        violations: list[str] = []

        for filepath in _collect_python_files(WEB_ROOT):
            relative = filepath.relative_to(WEB_ROOT)
            if str(relative).replace("\\", "/") in ALLOWED_FILES:
                continue

            imports = _extract_imports(filepath)
            for module in imports:
                for prefix in ENGINE_IMPORT_PREFIXES:
                    if module == prefix or module.startswith(prefix + "."):
                        violations.append(f"{relative}: imports {module!r}")

        assert violations == [], (
            "Engine import boundary violated! Only allowed files "
            "may import from babylon.engine/models/config/ooda/persistence.\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_bridge_file_exists(self) -> None:
        """The core bridge file must exist."""
        bridge_path = WEB_ROOT / "game/engine_bridge.py"
        assert bridge_path.exists(), f"Bridge file not found: {bridge_path}"

    def test_bridge_imports_engine(self) -> None:
        """The bridge file must actually import from the engine."""
        bridge_path = WEB_ROOT / "game/engine_bridge.py"
        imports = _extract_imports(bridge_path)
        engine_imports = [
            m
            for m in imports
            if any(m == p or m.startswith(p + ".") for p in ENGINE_IMPORT_PREFIXES)
        ]
        assert len(engine_imports) > 0, (
            "engine_bridge.py should import from babylon engine packages"
        )
