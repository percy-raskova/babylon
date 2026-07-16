"""Tests for the declared-synthetic-data coherence sentinel.

Two tiers, per the sentinel contract (mirrors ``test_coverage.py``):

- **Invariant** — :func:`check_sources_and_guards_exist` passes on the *real*
  :data:`SYNTHETIC_SOURCES`: every declared source symbol AND its guard symbol
  are still defined at their declared module paths.
- **Efficacy** — the sensor REDS on an injected defect: a row naming a symbol
  the file does not define (source side and guard side, separately), and an
  infrastructure failure (missing source file) raised loudly rather than
  swallowed.

This sentinel is **purely static** — it reads source files with :mod:`ast` and
never imports/runs ``web`` or the engine, so it needs no Postgres and does not
consume the ``shared_tick`` dynamic fixture.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.synthetic.checks import (
    _REPO_ROOT,
    check_sources_and_guards_exist,
    symbol_exists,
)
from babylon.sentinels.synthetic.registry import SYNTHETIC_SOURCES, SyntheticSource

pytestmark = pytest.mark.unit

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
_TOOL_PATH = _TOOLS_DIR / "sentinel_check.py"


def test_registry_is_non_empty() -> None:
    """The registry declares at least the three background-verified sources."""
    names = {row.name for row in SYNTHETIC_SOURCES}
    assert {
        "stub_engine_bridge",
        "economics_employment_default",
        "economics_fallback_tally",
    } <= names


def test_real_sources_are_coherent() -> None:
    """INVARIANT: every declared source AND guard symbol exists (green)."""
    assert check_sources_and_guards_exist() == []


def test_symbol_exists_finds_a_known_top_level_class() -> None:
    """The AST resolver finds a real module-level class by bare name."""
    path = _REPO_ROOT / "web/game/stub_bridge.py"
    assert symbol_exists(path, "StubEngineBridge")


def test_symbol_exists_finds_a_known_dotted_class_attribute() -> None:
    """The AST resolver finds a dataclass field one level inside a class."""
    path = _REPO_ROOT / "src/babylon/engine/services.py"
    assert symbol_exists(path, "ServiceContainer.employment_source")


def test_symbol_exists_finds_a_known_dotted_method() -> None:
    """The AST resolver finds a method one level inside a class."""
    path = _REPO_ROOT / "src/babylon/domain/economics/tick/system/__init__.py"
    assert symbol_exists(path, "TickDynamicsSystem._compute_national_params")


def test_symbol_exists_false_for_unknown_bare_name() -> None:
    """A name that is not defined at module scope resolves to False, not an error."""
    path = _REPO_ROOT / "web/game/stub_bridge.py"
    assert not symbol_exists(path, "ThisClassDoesNotExist")


def test_symbol_exists_false_for_unknown_class_in_dotted_symbol() -> None:
    """A dotted symbol naming a nonexistent class resolves to False."""
    path = _REPO_ROOT / "src/babylon/engine/services.py"
    assert not symbol_exists(path, "NoSuchClass.some_attr")


def test_symbol_exists_false_for_unknown_attribute_in_dotted_symbol() -> None:
    """A dotted symbol naming a real class but a nonexistent attribute resolves to False."""
    path = _REPO_ROOT / "src/babylon/engine/services.py"
    assert not symbol_exists(path, "ServiceContainer.this_field_does_not_exist")


def test_efficacy_reds_on_nonexistent_source_symbol() -> None:
    """EFFICACY: a row naming a source_symbol the file lacks reds the gate.

    The source file exists and parses, but declares no such symbol — the
    exact orphaned-registration drift the sentinel guards against.
    """
    broken = SyntheticSource(
        name="phantom_source",
        source_file="web/game/stub_bridge.py",
        source_symbol="ThisClassDoesNotExist",
        guard_file="web/game/api.py",
        guard_symbol="_get_bridge",
        guard_kind="debug_gate",
        what_it_fakes="synthetic defect for the efficacy proof",
        invariant="n/a",
    )
    violations = check_sources_and_guards_exist((broken,))
    assert len(violations) == 1
    assert "phantom_source" in violations[0]
    assert "ThisClassDoesNotExist" in violations[0]


def test_efficacy_reds_on_nonexistent_guard_symbol() -> None:
    """EFFICACY: a row naming a guard_symbol the file lacks reds the gate.

    This is the "guard was renamed/deleted, source untouched" drift — the
    source stays coherent but is now UNGUARDED, which must still be loud.
    """
    broken = SyntheticSource(
        name="unguarded_source",
        source_file="web/game/stub_bridge.py",
        source_symbol="StubEngineBridge",
        guard_file="web/game/api.py",
        guard_symbol="_this_guard_was_deleted",
        guard_kind="debug_gate",
        what_it_fakes="synthetic defect for the efficacy proof",
        invariant="n/a",
    )
    violations = check_sources_and_guards_exist((broken,))
    assert len(violations) == 1
    assert "unguarded_source" in violations[0]
    assert "_this_guard_was_deleted" in violations[0]
    assert "UNGUARDED" in violations[0]


def test_efficacy_both_symbols_missing_reports_two_violations() -> None:
    """EFFICACY: a row broken on both sides reports both, not just the first."""
    broken = SyntheticSource(
        name="doubly_phantom",
        source_file="web/game/stub_bridge.py",
        source_symbol="NoSuchSource",
        guard_file="web/game/api.py",
        guard_symbol="no_such_guard",
        guard_kind="debug_gate",
        what_it_fakes="synthetic defect for the efficacy proof",
        invariant="n/a",
    )
    violations = check_sources_and_guards_exist((broken,))
    assert len(violations) == 2


def test_efficacy_missing_source_file_is_loud() -> None:
    """EFFICACY: a missing source file raises SentinelCheckError (exit-2, not a pass).

    Infrastructure failure must be loud (III.11), never swallowed into an
    empty (falsely-clean) violation list.
    """
    broken = SyntheticSource(
        name="gone_module",
        source_file="src/babylon/domain/economics/does_not_exist.py",
        source_symbol="Whatever",
        guard_file="web/game/api.py",
        guard_symbol="_get_bridge",
        guard_kind="debug_gate",
        what_it_fakes="synthetic missing-file defect",
        invariant="n/a",
    )
    with pytest.raises(SentinelCheckError):
        check_sources_and_guards_exist((broken,))


def test_registry_rejects_blank_source_symbol() -> None:
    """A malformed row (blank source_symbol) fails loudly at construction (III.11)."""
    with pytest.raises(ValueError, match="source_symbol"):
        SyntheticSource(
            name="bad",
            source_file="web/game/x.py",
            source_symbol="  ",
            guard_file="web/game/api.py",
            guard_symbol="_get_bridge",
            guard_kind="debug_gate",
            what_it_fakes="x",
            invariant="x",
        )


def test_registry_rejects_non_py_source_file() -> None:
    """A source_file that is not a .py path fails loudly at construction."""
    with pytest.raises(ValueError, match="source_file"):
        SyntheticSource(
            name="bad",
            source_file="web/game/x.sqlite",
            source_symbol="X",
            guard_file="web/game/api.py",
            guard_symbol="_get_bridge",
            guard_kind="debug_gate",
            what_it_fakes="x",
            invariant="x",
        )


def test_registry_rejects_unknown_guard_kind() -> None:
    """guard_kind is a closed Literal vocabulary — an unknown value fails loudly."""
    with pytest.raises(ValueError):
        SyntheticSource(
            name="bad",
            source_file="web/game/x.py",
            source_symbol="X",
            guard_file="web/game/api.py",
            guard_symbol="_get_bridge",
            guard_kind="not_a_real_guard_kind",  # type: ignore[arg-type]
            what_it_fakes="x",
            invariant="x",
        )


def test_cli_check_exits_zero_on_real_registry() -> None:
    """``sentinel_check.py synthetic --check`` exits 0 today (CI fast-gate idiom)."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "synthetic", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Synthetic-data sensor reds against the shipped registry:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "sanctioned sources coherent" in result.stdout
