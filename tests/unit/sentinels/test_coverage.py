"""Tests for the data-coverage coherence sentinel.

Two tiers, per the sentinel contract:

- **Invariant** — :func:`check_source_classes_exist` passes on the *real*
  :data:`DATA_REQUIREMENTS`: every declared reference-data adapter class is
  still defined at its declared module path.
- **Efficacy** — the sensor REDS on an injected defect: a requirement naming a
  class the file does not define, and an infrastructure failure (missing source
  file) raised loudly rather than swallowed.

This sentinel is **purely static** — it reads source files with :mod:`ast` and
never runs the engine, so it does not consume the ``shared_tick`` dynamic
fixture. The reference-DB *coverage probe* (do the rows exist) is a nightly
concern and is deliberately not exercised here.
"""

from __future__ import annotations

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.coverage.checks import (
    _REPO_ROOT,
    check_source_classes_exist,
    module_class_names,
)
from babylon.sentinels.coverage.registry import DATA_REQUIREMENTS, DataRequirement

pytestmark = pytest.mark.unit


def test_registry_is_non_empty() -> None:
    """The registry declares at least the four known reference-data requirements."""
    names = {req.name for req in DATA_REQUIREMENTS}
    assert {
        "qcew_county_naics",
        "qcew_national_employment",
        "lodes_commuter_flow",
        "bea_import_use",
    } <= names


def test_real_requirements_are_coherent() -> None:
    """INVARIANT: every declared source class exists at its declared module path."""
    assert check_source_classes_exist() == []


def test_module_class_names_finds_a_known_class() -> None:
    """The AST helper resolves a real module-level adapter class."""
    path = _REPO_ROOT / "src/babylon/domain/economics/throughput/adapters.py"
    assert "SQLiteQCEWCountyNAICSSource" in module_class_names(path)


def test_efficacy_reds_on_nonexistent_source_class() -> None:
    """EFFICACY: a requirement naming a class the file lacks reds the gate.

    The source file exists and parses, but declares no such class — this is the
    exact orphaned-dependency drift the sentinel guards against.
    """
    broken = DataRequirement(
        name="phantom_dependency",
        source_class="SQLiteThisClassDoesNotExist",
        source_file="src/babylon/domain/economics/throughput/adapters.py",
        tables=("fact_qcew_annual",),
        material_relation="synthetic defect for the efficacy proof",
    )
    violations = check_source_classes_exist((broken,))
    assert len(violations) == 1
    assert "phantom_dependency" in violations[0]
    assert "SQLiteThisClassDoesNotExist" in violations[0]


def test_efficacy_missing_source_file_is_loud() -> None:
    """EFFICACY: a missing source file raises SentinelCheckError (exit-2, not a pass).

    Infrastructure failure must be loud (III.11), never swallowed into an empty
    (falsely-clean) violation list.
    """
    broken = DataRequirement(
        name="gone_module",
        source_class="Whatever",
        source_file="src/babylon/domain/economics/does_not_exist.py",
        tables=("t",),
        material_relation="synthetic missing-file defect",
    )
    with pytest.raises(SentinelCheckError):
        check_source_classes_exist((broken,))


def test_registry_rejects_blank_source_class() -> None:
    """A malformed row (blank source_class) fails loudly at construction (III.11)."""
    with pytest.raises(ValueError, match="source_class"):
        DataRequirement(
            name="bad",
            source_class="  ",
            source_file="src/babylon/x.py",
            tables=(),
            material_relation="r",
        )


def test_registry_rejects_non_py_source_file() -> None:
    """A source_file that is not a .py path fails loudly at construction."""
    with pytest.raises(ValueError, match="source_file"):
        DataRequirement(
            name="bad",
            source_class="X",
            source_file="src/babylon/x.sqlite",
            tables=(),
            material_relation="r",
        )
