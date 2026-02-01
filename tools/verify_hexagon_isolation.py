#!/usr/bin/env python3
"""Verify hexagon visualization isolation from database layer.

This script performs static import analysis to ensure that hexagon visualization
components in src/babylon/ui/ do not directly import database modules.

Feature: 011-fundamental-tensor-primitive
Implements: T044 from tasks.md
Addresses: SC-002 from spec.md

Usage:
    python tools/verify_hexagon_isolation.py
    python tools/verify_hexagon_isolation.py --verbose
    python tools/verify_hexagon_isolation.py --ci  # Exit code 1 on violation

Exit Codes:
    0 - No violations found
    1 - Violations detected (with --ci flag)
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

# Prohibited import patterns for hexagon/UI code
# These modules represent "direct database access"
PROHIBITED_IMPORTS: Final[frozenset[str]] = frozenset(
    {
        # Database layer modules
        "babylon.data",
        "babylon.data.reference",
        "babylon.data.reference.database",
        "babylon.data.reference.hydrator",
        "babylon.data.reference.schema",
        # SQLAlchemy ORM (direct database access)
        "sqlalchemy",
        "sqlalchemy.orm",
        "sqlalchemy.engine",
        # Raw SQLite access
        "sqlite3",
    }
)

# Allowed imports - these are tensor layer, not database layer
ALLOWED_TENSOR_IMPORTS: Final[frozenset[str]] = frozenset(
    {
        "babylon.economics.tensor",
        "babylon.economics.tensor_registry",
        "babylon.economics.snlt",
    }
)

# UI directories to scan
UI_DIRECTORIES: Final[list[str]] = [
    "src/babylon/ui",
]


@dataclass
class ImportViolation:
    """Represents a prohibited import violation."""

    file_path: Path
    line_number: int
    import_name: str
    import_type: str  # "import" or "from"


@dataclass
class ScanResult:
    """Result of scanning a directory for import violations."""

    files_scanned: int = 0
    violations: list[ImportViolation] = field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        """Check if any violations were found."""
        return len(self.violations) > 0


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor that detects prohibited imports."""

    def __init__(self, file_path: Path) -> None:
        """Initialize analyzer for a specific file.

        Args:
            file_path: Path to the file being analyzed.
        """
        self.file_path = file_path
        self.violations: list[ImportViolation] = []

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        """Check direct import statements (import x).

        Args:
            node: AST Import node.
        """
        for alias in node.names:
            module_name = alias.name
            if self._is_prohibited(module_name):
                self.violations.append(
                    ImportViolation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        import_name=module_name,
                        import_type="import",
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        """Check from-import statements (from x import y).

        Args:
            node: AST ImportFrom node.
        """
        if node.module is None:
            return

        module_name = node.module
        if self._is_prohibited(module_name):
            self.violations.append(
                ImportViolation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    import_name=module_name,
                    import_type="from",
                )
            )
        self.generic_visit(node)

    def _is_prohibited(self, module_name: str) -> bool:
        """Check if a module name matches any prohibited pattern.

        Args:
            module_name: The module name to check.

        Returns:
            True if the module is prohibited, False otherwise.
        """
        # Check exact matches
        if module_name in PROHIBITED_IMPORTS:
            return True

        # Check if it's a submodule of any prohibited module
        return any(module_name.startswith(prohibited + ".") for prohibited in PROHIBITED_IMPORTS)


def analyze_file(file_path: Path) -> list[ImportViolation]:
    """Analyze a single Python file for prohibited imports.

    Args:
        file_path: Path to the Python file.

    Returns:
        List of import violations found.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        print(f"Warning: Syntax error in {file_path}: {e}")
        return []
    except OSError as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return []

    analyzer = ImportAnalyzer(file_path)
    analyzer.visit(tree)
    return analyzer.violations


def scan_directory(directory: Path, verbose: bool = False) -> ScanResult:
    """Scan a directory recursively for Python files with prohibited imports.

    Args:
        directory: Directory to scan.
        verbose: If True, print progress messages.

    Returns:
        ScanResult with files scanned and violations found.
    """
    result = ScanResult()

    if not directory.exists():
        if verbose:
            print(f"Directory not found: {directory}")
        return result

    for py_file in directory.rglob("*.py"):
        # Skip __pycache__ and test files
        if "__pycache__" in str(py_file):
            continue

        result.files_scanned += 1
        if verbose:
            print(f"Scanning: {py_file}")

        violations = analyze_file(py_file)
        result.violations.extend(violations)

    return result


def format_violation(violation: ImportViolation) -> str:
    """Format a violation for display.

    Args:
        violation: The violation to format.

    Returns:
        Human-readable violation message.
    """
    return (
        f"{violation.file_path}:{violation.line_number}: "
        f"Prohibited {violation.import_type} '{violation.import_name}'"
    )


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 = success, 1 = violations found with --ci flag).
    """
    parser = argparse.ArgumentParser(
        description="Verify hexagon visualization isolation from database layer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                  # Run analysis, print results
    %(prog)s --verbose        # Show files being scanned
    %(prog)s --ci             # Exit with code 1 if violations found

Prohibited imports:
    - babylon.data.*          (database layer)
    - sqlalchemy.*            (ORM)
    - sqlite3                 (raw database access)

Allowed imports:
    - babylon.economics.tensor         (tensor primitives)
    - babylon.economics.tensor_registry (tensor cache)
    - babylon.economics.snlt           (SNLT configuration)
""",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show files being scanned",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Exit with code 1 if violations found (for CI integration)",
    )
    parser.add_argument(
        "--directory",
        "-d",
        type=Path,
        default=None,
        help="Directory to scan (default: src/babylon/ui)",
    )

    args = parser.parse_args()

    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print("=" * 60)
    print("Hexagon Visualization Isolation Verification")
    print("=" * 60)
    print()
    print("Prohibited imports:")
    for imp in sorted(PROHIBITED_IMPORTS):
        print(f"  - {imp}")
    print()

    total_result = ScanResult()

    directories = [args.directory] if args.directory else [project_root / d for d in UI_DIRECTORIES]

    for directory in directories:
        print(f"Scanning: {directory}")
        result = scan_directory(directory, verbose=args.verbose)
        total_result.files_scanned += result.files_scanned
        total_result.violations.extend(result.violations)

    print()
    print("-" * 60)
    print(f"Files scanned: {total_result.files_scanned}")
    print(f"Violations found: {len(total_result.violations)}")
    print()

    if total_result.has_violations:
        print("VIOLATIONS:")
        print()
        for violation in total_result.violations:
            print(f"  {format_violation(violation)}")
        print()
        print("ERROR: Hexagon visualization imports prohibited database modules!")
        print()
        print("Fix by:")
        print("  1. Remove direct database imports from UI code")
        print("  2. Use TensorConsumerMixin for tensor data access")
        print("  3. Access data via TerritoryState.tensor_year + TensorRegistry")
        print()

        if args.ci:
            return 1
    else:
        print("SUCCESS: No prohibited imports found in UI code")
        print()
        print("Hexagon visualization is properly isolated from database layer.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
