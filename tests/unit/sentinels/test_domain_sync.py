"""Tests for the domain-sync sentinel (ledger DOMAIN <-> models/types.py).

Mirrors ``test_defines_passthrough.py``'s tiered shape:

- **Codegen sync** — the committed ``0039_domain_contracts.sql`` is exactly what
  the shared renderer produces (the generator and the migration cannot drift).
- **Derivation** — the numeric bounds ARE read live from ``models/types.py``
  (not copied), proven by a synthetic type-swap that flows into the expected
  CHECK.
- **Mutation-validated efficacy** — the gating check reds on a bound tampered in
  a copy of the migration (both a numeric range AND a format pattern), on a
  missing domain, and on a types.py-side drift; and stays clean on the real
  committed file. This is the "sentinel every error class" proof.
- **Registry / infrastructure teeth** — malformed rows reject at import; a
  missing migration or an unbounded source type is a loud infrastructure
  failure (exit 2), never a silent pass.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Annotated

import pytest
from pydantic import Field, ValidationError

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.domain_sync.checks import (
    domain_bounds_out_of_sync,
    parse_committed_domains,
    read_committed_migration,
)
from babylon.sentinels.domain_sync.ddl import (
    build_migration_sql,
    format_check_predicate,
    numeric_check_predicate,
    types_py_bounds,
)
from babylon.sentinels.domain_sync.registry import (
    DEFERRED_DOMAINS,
    FORMAT_DOMAINS,
    MIGRATION_FILENAME,
    MIGRATION_PATH,
    NUMERIC_DOMAINS,
    FormatDomainSpec,
    NumericDomainSpec,
)

pytestmark = pytest.mark.unit

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
_TOOL_PATH = _TOOLS_DIR / "sentinel_check.py"
_GENERATOR_PATH = _TOOLS_DIR / "generate_domain_ddl.py"


# ---------------------------------------------------------------------------
# Codegen sync: the committed migration IS the renderer's output
# ---------------------------------------------------------------------------


def test_committed_migration_matches_the_renderer() -> None:
    """The on-disk 0039 migration equals ``build_migration_sql()`` byte-for-byte."""
    assert MIGRATION_PATH.read_text(encoding="utf-8") == build_migration_sql(MIGRATION_FILENAME)


def test_generator_check_mode_reports_in_sync() -> None:
    """``generate_domain_ddl.py --check`` exits 0 against the committed file."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_GENERATOR_PATH), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


# ---------------------------------------------------------------------------
# Derivation: bounds come from models/types.py, live
# ---------------------------------------------------------------------------


def test_numeric_predicates_derive_from_types_py() -> None:
    """Each numeric domain's CHECK is exactly its ``types.py`` range."""
    predicates = {spec.name: numeric_check_predicate(spec) for spec in NUMERIC_DOMAINS}
    assert predicates == {
        "probability": "VALUE >= 0.0 AND VALUE <= 1.0",
        "currency": "VALUE >= 0.0",
        "ratio": "VALUE > 0.0",
        "labor_hours": "VALUE >= 0.0",
    }


def test_format_predicates_render_from_registry() -> None:
    """Regex domains render ``VALUE ~ '<pat>'``; length domains ``length(VALUE) = n``."""
    predicates = {spec.name: format_check_predicate(spec) for spec in FORMAT_DOMAINS}
    assert predicates == {
        "fips5": r"VALUE ~ '^\d{5}$'",
        "fips2": r"VALUE ~ '^\d{2}$'",
        "h3index": "length(VALUE) = 15",
    }


def test_types_py_bounds_reflects_ge_le_gt() -> None:
    """``types_py_bounds`` extracts inclusive/exclusive bounds correctly."""
    from babylon.models.types import Currency, Probability, Ratio

    # The *_inclusive flag is only meaningful when its bound is not None; it
    # defaults to True and is ignored by the renderer for an absent bound.
    assert types_py_bounds(Probability) == (0.0, True, 1.0, True)
    assert types_py_bounds(Currency) == (0.0, True, None, True)
    assert types_py_bounds(Ratio) == (0.0, False, None, True)


def test_a_types_py_bound_change_flows_into_the_expected_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """types.py-side drift: widen Probability's ``le`` and the committed
    migration (still ``<= 1.0``) is flagged — proving the sentinel derives its
    expectation from ``types.py`` live, not from a cached copy of the file."""
    widened = Annotated[float, Field(ge=0.0, le=2.0)]
    monkeypatch.setattr("babylon.models.types.Probability", widened)
    # The expected predicate now reflects the (fake) widened bound...
    probability_spec = next(s for s in NUMERIC_DOMAINS if s.name == "probability")
    assert numeric_check_predicate(probability_spec) == "VALUE >= 0.0 AND VALUE <= 2.0"
    # ...so the UNCHANGED committed migration is now out of sync.
    violations = domain_bounds_out_of_sync(read_committed_migration())
    assert any("probability" in v for v in violations)


# ---------------------------------------------------------------------------
# Mutation-validated efficacy: the gate reds on a tamper, clean otherwise
# ---------------------------------------------------------------------------


def test_live_committed_migration_is_in_sync() -> None:
    """The real, shipped migration matches every source of truth (clean gate)."""
    assert domain_bounds_out_of_sync() == []


def test_gate_reds_on_a_tampered_numeric_bound() -> None:
    """Mutating a range in a COPY of the migration reds the gate for that domain."""
    tampered = read_committed_migration().replace(
        "CHECK (VALUE >= 0.0 AND VALUE <= 1.0)",
        "CHECK (VALUE >= 0.0 AND VALUE <= 2.0)",
    )
    violations = domain_bounds_out_of_sync(tampered)
    assert len(violations) == 1
    assert "probability" in violations[0]
    assert "ledger-contract-drift" in violations[0]


def test_gate_reds_on_a_tampered_format_pattern() -> None:
    """Mutating the fips5 regex in a copy reds the gate (the format single-source)."""
    tampered = read_committed_migration().replace(r"VALUE ~ '^\d{5}$'", r"VALUE ~ '^[0-9]{5}$'")
    violations = domain_bounds_out_of_sync(tampered)
    assert len(violations) == 1
    assert "fips5" in violations[0]


def test_gate_reds_on_a_missing_domain() -> None:
    """Deleting a CREATE DOMAIN entirely reds the gate as absent, not silent."""
    committed = read_committed_migration()
    tampered = committed.replace(
        "CREATE DOMAIN labor_hours AS double precision CHECK (VALUE >= 0.0);",
        "-- (labor_hours domain removed)",
    )
    violations = domain_bounds_out_of_sync(tampered)
    assert len(violations) == 1
    assert "labor_hours" in violations[0]
    assert "absent" in violations[0]


def test_gate_reds_on_a_tampered_h3index_length() -> None:
    """The length-kind domain is guarded too (nested-paren body parses)."""
    tampered = read_committed_migration().replace("length(VALUE) = 15", "length(VALUE) = 16")
    violations = domain_bounds_out_of_sync(tampered)
    assert len(violations) == 1
    assert "h3index" in violations[0]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def test_parser_captures_all_seven_domains_including_nested_paren_body() -> None:
    """The parser reads every domain, incl. the ``length(VALUE)`` nested paren."""
    parsed = parse_committed_domains(read_committed_migration())
    assert set(parsed) == {
        "probability",
        "currency",
        "ratio",
        "labor_hours",
        "fips5",
        "fips2",
        "h3index",
    }
    assert parsed["h3index"] == "length(VALUE) = 15"


# ---------------------------------------------------------------------------
# Infrastructure teeth (exit 2, never a silent pass)
# ---------------------------------------------------------------------------


def test_missing_migration_is_an_infrastructure_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing migration file raises, never returns "no drift found"."""
    monkeypatch.setattr(
        "babylon.sentinels.domain_sync.checks.MIGRATION_PATH",
        Path("/nonexistent/0039_domain_contracts.sql"),
    )
    with pytest.raises(SentinelCheckError):
        read_committed_migration()


def test_unbounded_source_type_is_an_infrastructure_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A numeric domain pointing at an unbounded type has no CHECK — loud fail."""
    unbounded = Annotated[float, Field()]
    monkeypatch.setattr("babylon.models.types.Currency", unbounded)
    currency_spec = next(s for s in NUMERIC_DOMAINS if s.name == "currency")
    with pytest.raises(SentinelCheckError):
        numeric_check_predicate(currency_spec)


def test_unresolved_source_type_is_an_infrastructure_failure() -> None:
    """A registry row naming a nonexistent types.py type fails loud (registry drift)."""
    ghost = NumericDomainSpec(
        name="ghost",
        source_type="NoSuchType",
        sql_base="double precision",
        evidence=("synthetic",),
    )
    with pytest.raises(SentinelCheckError):
        numeric_check_predicate(ghost)


# ---------------------------------------------------------------------------
# Registry shape teeth
# ---------------------------------------------------------------------------


def test_numeric_spec_rejects_empty_evidence() -> None:
    """A numeric domain with no backing column is the invented domain we forbid."""
    with pytest.raises(ValidationError):
        NumericDomainSpec(
            name="x", source_type="Probability", sql_base="double precision", evidence=()
        )


def test_numeric_spec_rejects_non_lowercase_name() -> None:
    with pytest.raises(ValidationError):
        NumericDomainSpec(
            name="Probability",
            source_type="Probability",
            sql_base="double precision",
            evidence=("e",),
        )


def test_format_spec_rejects_non_integer_length() -> None:
    with pytest.raises(ValidationError):
        FormatDomainSpec(
            name="bad", sql_base="text", kind="length", pattern="fifteen", evidence=("e",)
        )


# ---------------------------------------------------------------------------
# Scope discipline: no invented domains; deferrals documented
# ---------------------------------------------------------------------------


def test_registry_declares_the_expected_domains() -> None:
    """Locks the audited set (numeric backed by CHECK columns; format duplicates)."""
    assert {s.name for s in NUMERIC_DOMAINS} == {
        "probability",
        "currency",
        "ratio",
        "labor_hours",
    }
    assert {s.name for s in FORMAT_DOMAINS} == {"fips5", "fips2", "h3index"}


def test_deferred_types_are_documented_and_not_emitted() -> None:
    """Every deferred types.py type has a recorded reason and NO emitted domain."""
    emitted_sources = {s.source_type for s in NUMERIC_DOMAINS}
    assert emitted_sources.isdisjoint(DEFERRED_DOMAINS)
    assert set(DEFERRED_DOMAINS) == {
        "Intensity",
        "Coefficient",
        "Gini",
        "Ideology",
        "SignedLaborHours",
    }
    assert all(reason.strip() for reason in DEFERRED_DOMAINS.values())


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_entry_point_clean_on_live_tree() -> None:
    """``sentinel_check.py domain_sync --check`` is clean on the integrated tree."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "domain_sync", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "DOMAIN_SYNC clean" in result.stdout
