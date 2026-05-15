"""Source-discipline invariant test for the hex hydrator (spec-065 T018).

The spec-065 ``contracts/hex_hydrator_input.yaml`` declares the
authoritative list of SQLite reference tables the hex hydrator is
allowed to read from. This test parses the hydrator source via AST +
text inspection and asserts:

  1. Every fact_* / dim_* table referenced in the hydrator's SQL
     strings appears in the contract's ``sqlite_tables_read`` allowlist.
  2. NO forbidden tables (fact_atus_*, fact_eviction_lab_*) appear.

This is an architectural invariant — when a future commit adds a new
SQLite read to the hydrator, this test forces the contract to be
updated too.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import yaml

HYDRATOR_PATH = Path("src/babylon/persistence/hex_hydrator.py")
CONTRACT_PATH = Path("specs/065-engine-bridging/contracts/hex_hydrator_input.yaml")

# Tables we want to flag if they ever appear in the hydrator's SQL.
_FORBIDDEN_TABLE_PREFIXES = ("fact_atus_", "fact_eviction_lab_")

# Pattern matching SQL table references after FROM / JOIN clauses.
# Conservative: only catches identifiers immediately following the
# keywords; we don't need to parse arbitrary SQL.
_TABLE_PATTERN = re.compile(
    r"\b(?:FROM|JOIN)\s+(fact_\w+|dim_\w+|immutable_reference_\w+|view_\w+|dynamic_\w+|boundary_\w+|conservation_\w+|v_\w+|hex_\w+|external_\w+|audit_\w+)\b",
    re.IGNORECASE,
)


def _load_allowed_tables() -> set[str]:
    """Parse the contract YAML's sqlite_tables_read list.

    Accepts the wildcard ``fact_census_*`` as a prefix permission for
    the Census family of tables.
    """
    contract = yaml.safe_load(CONTRACT_PATH.read_text())
    return set(contract.get("sqlite_tables_read", []))


def _extract_sql_table_references(source: str) -> set[str]:
    """Walk the AST, collect string constants, regex-extract table names.

    Returns a set of unique table names referenced in any string literal
    in the module — covers triple-quoted SQL templates as well as
    inline f-strings.
    """
    tree = ast.parse(source)
    tables: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for match in _TABLE_PATTERN.finditer(node.value):
                tables.add(match.group(1).lower())
    return tables


def _table_is_allowed(table: str, allowlist: set[str]) -> bool:
    """Check whether ``table`` is permitted under the contract.

    Direct match OR matches a wildcard pattern like ``fact_census_*``.
    Postgres-only tables (immutable_reference_*, dynamic_*, view_*,
    boundary_*, conservation_*, v_*, hex_*, external_*, audit_*) are
    always permitted — the contract scopes SQLite tables only; the
    hydrator legitimately reads Postgres-resident tables too.
    """
    if table in allowlist:
        return True
    if not table.startswith(("fact_", "dim_")):
        # Not an SQLite reference data table; out of contract scope.
        return True
    for permitted in allowlist:
        if permitted.endswith("*") and table.startswith(permitted[:-1]):
            return True
    return False


def test_hydrator_only_reads_allowed_sqlite_tables() -> None:
    """Every fact_*/dim_* table read by the hydrator must be in the contract."""
    allowlist = _load_allowed_tables()
    source = HYDRATOR_PATH.read_text()
    referenced = _extract_sql_table_references(source)
    violations = [t for t in referenced if not _table_is_allowed(t, allowlist)]
    assert not violations, (
        f"hex_hydrator references SQLite tables not in "
        f"contracts/hex_hydrator_input.yaml.sqlite_tables_read: {sorted(violations)}. "
        f"Either add them to the contract or remove the read."
    )


def test_hydrator_does_not_read_forbidden_tables() -> None:
    """Explicit blacklist enforcement for fact_atus_* and fact_eviction_lab_*."""
    source = HYDRATOR_PATH.read_text()
    referenced = _extract_sql_table_references(source)
    forbidden = [
        t for t in referenced if any(t.startswith(prefix) for prefix in _FORBIDDEN_TABLE_PREFIXES)
    ]
    assert not forbidden, (
        f"hex_hydrator references blacklisted tables: {sorted(forbidden)}. "
        f"These are out-of-scope per spec-065 and must not be read."
    )


def test_contract_has_sqlite_tables_read_section() -> None:
    """Sanity check: the contract YAML actually declares the allowlist."""
    contract = yaml.safe_load(CONTRACT_PATH.read_text())
    assert "sqlite_tables_read" in contract, (
        "contracts/hex_hydrator_input.yaml is missing the "
        "sqlite_tables_read section that T018 depends on."
    )
    assert len(contract["sqlite_tables_read"]) > 0, "sqlite_tables_read is empty"
