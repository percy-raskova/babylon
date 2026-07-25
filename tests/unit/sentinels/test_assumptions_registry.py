"""Tests for the declared-assumptions ledger sentinel (T1.2 keel, unit K5).

Two tiers, per the sentinel contract (mirrors ``test_synthetic_registry_check.py``):

- **Invariant** — :func:`check_code_refs_exist` passes on the *real*
  :data:`DECLARED_ASSUMPTIONS`: every declared ``code_ref`` still exists.
- **Efficacy** — the check reds on an injected defect: a row citing a
  ``code_ref`` the repo does not contain.

Purely static — reads the filesystem only, no import of ``web``/the engine, so
it needs no Postgres and does not consume the ``shared_tick`` dynamic fixture.
"""

from __future__ import annotations

import pytest

from babylon.sentinels.assumptions.checks import _REPO_ROOT, check_code_refs_exist
from babylon.sentinels.assumptions.registry import (
    DECLARED_ASSUMPTIONS,
    Assumption,
    ledger_lines,
)

pytestmark = pytest.mark.unit


def test_registry_is_non_empty() -> None:
    """The ledger declares at least the genuinely-verified seed assumptions."""
    ids = {row.id for row in DECLARED_ASSUMPTIONS}
    assert {
        "economics_employment_default",
        "lodes_commuter_flow_absent_degrades_to_residence_only",
        "dispossession_unrate_proxy_2021_plus",
        "vol1_national_series_applied_uniformly_per_county",
    } <= ids


def test_ids_are_unique() -> None:
    """No two rows may silently share an id — that would make lookups ambiguous."""
    ids = [row.id for row in DECLARED_ASSUMPTIONS]
    assert len(ids) == len(set(ids))


def test_repo_root_resolves_to_the_real_repo_root() -> None:
    """``_REPO_ROOT`` must actually be the checkout root, not some parent."""
    assert (_REPO_ROOT / "pyproject.toml").is_file()


def test_real_assumptions_cite_existing_code() -> None:
    """INVARIANT: every declared row's code_ref resolves to a real file (green)."""
    assert check_code_refs_exist() == []


def test_efficacy_reds_on_nonexistent_code_ref() -> None:
    """EFFICACY: a row citing a code_ref the repo lacks reds the check.

    This is the exact "the file moved/was deleted, the row wasn't updated"
    drift the sentinel exists to catch.
    """
    broken = Assumption(
        id="phantom_assumption",
        claim="a fabricated claim for the efficacy proof",
        owner="Persephone Raskova",
        code_ref="src/babylon/domain/economics/this_file_does_not_exist.py",
        expiry_condition="n/a",
    )
    violations = check_code_refs_exist((broken,))
    assert len(violations) == 1
    assert "phantom_assumption" in violations[0]
    assert "this_file_does_not_exist.py" in violations[0]


def test_efficacy_multiple_broken_rows_report_all() -> None:
    """EFFICACY: two broken rows both surface, not just the first."""
    broken_a = Assumption(
        id="phantom_a",
        claim="a fabricated claim for the efficacy proof",
        owner="Persephone Raskova",
        code_ref="src/babylon/domain/economics/does_not_exist_a.py",
        expiry_condition="n/a",
    )
    broken_b = Assumption(
        id="phantom_b",
        claim="a fabricated claim for the efficacy proof",
        owner="Persephone Raskova",
        code_ref="src/babylon/domain/economics/does_not_exist_b.py",
        expiry_condition="n/a",
    )
    violations = check_code_refs_exist((broken_a, broken_b))
    assert len(violations) == 2


def test_registry_rejects_blank_id() -> None:
    """A malformed row (blank id) fails loudly at construction (III.11)."""
    with pytest.raises(ValueError, match="id"):
        Assumption(
            id="  ",
            claim="x",
            owner="x",
            code_ref="src/babylon/x.py",
            expiry_condition="x",
        )


def test_registry_rejects_blank_claim() -> None:
    with pytest.raises(ValueError, match="claim"):
        Assumption(
            id="bad",
            claim="  ",
            owner="x",
            code_ref="src/babylon/x.py",
            expiry_condition="x",
        )


def test_registry_rejects_blank_owner() -> None:
    with pytest.raises(ValueError, match="owner"):
        Assumption(
            id="bad",
            claim="x",
            owner="  ",
            code_ref="src/babylon/x.py",
            expiry_condition="x",
        )


def test_registry_rejects_blank_expiry_condition() -> None:
    with pytest.raises(ValueError, match="expiry_condition"):
        Assumption(
            id="bad",
            claim="x",
            owner="x",
            code_ref="src/babylon/x.py",
            expiry_condition="  ",
        )


def test_registry_rejects_non_py_code_ref() -> None:
    """A code_ref that is not a .py path fails loudly at construction."""
    with pytest.raises(ValueError, match="code_ref"):
        Assumption(
            id="bad",
            claim="x",
            owner="x",
            code_ref="src/babylon/data/defines.yaml",
            expiry_condition="x",
        )


def test_registry_is_frozen() -> None:
    """Assumption rows are frozen Pydantic models (Constitution's frozen-model rule)."""
    row = DECLARED_ASSUMPTIONS[0]
    with pytest.raises(ValueError):
        row.id = "mutated"  # type: ignore[misc]


def test_registry_forbids_extra_fields() -> None:
    """extra='forbid' rejects an unknown field loudly at construction."""
    with pytest.raises(ValueError):
        Assumption(
            id="bad",
            claim="x",
            owner="x",
            code_ref="src/babylon/x.py",
            expiry_condition="x",
            not_a_real_field="surprise",  # type: ignore[call-arg]
        )


def test_ledger_lines_renders_one_line_per_row() -> None:
    """ledger_lines() is a pure function: one formatted line per row, in order."""
    lines = ledger_lines(DECLARED_ASSUMPTIONS)
    assert len(lines) == len(DECLARED_ASSUMPTIONS)
    for row, line in zip(DECLARED_ASSUMPTIONS, lines, strict=True):
        assert line.startswith(row.id)
        assert row.claim in line
        assert row.code_ref in line


def test_ledger_lines_defaults_to_the_real_registry() -> None:
    """Calling ledger_lines() with no argument renders the real ledger."""
    assert ledger_lines() == ledger_lines(DECLARED_ASSUMPTIONS)
