"""Tests for the masked-arithmetic sentinel: no unguarded arithmetic on a
fog-masked field.

Three tiers, mirroring the inert/unconsumed sentinels' own test shape:

- **Efficacy** (AST-helper level) — :func:`unguarded_arithmetic_sites` and
  :func:`guard_exists_for_field` correctly see each syntactic shape of "at
  risk" (``float(o.get(field, default))``, ``float(o[field])``,
  ``sum(o.get(field, default) for o in xs)``) and "guarded"
  (``o.get(field) is not None``, ``o[field] is not None``), and correctly
  miss shapes that are not at risk (a non-arithmetic use, an unrelated
  field name, a ``.get()`` with an explicit ``None`` default which is
  simply redundant, not a footgun).
- **Regression** (synthetic ``tmp_path`` source, injected registry rows) —
  proves the check reds on the exact founding-bug shape and stays clean on
  the shipped fix's shape.
- **Liveness** (the real, shipped registry against the real repo file) —
  the one declared row, ``state_apparatus_dashboard_heat``, must be clean
  against the current ``engine_bridge.py`` (the shipped fix, commit
  ``657e415c6``).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.masked_arithmetic.checks import (
    _REPO_ROOT,
    find_function,
    guard_exists_for_field,
    unguarded_arithmetic_sites,
    unguarded_masked_arithmetic,
)
from babylon.sentinels.masked_arithmetic.registry import (
    DECLARED_FOGGED_CONSUMERS,
    DeclaredFoggedConsumer,
)

pytestmark = pytest.mark.unit


def _fn(source: str, name: str = "target") -> tuple[ast.Module, ast.FunctionDef]:
    tree = ast.parse(source)
    func = find_function(tree, name)
    assert isinstance(func, ast.FunctionDef)
    return tree, func


# ---------------------------------------------------------------------------
# find_function
# ---------------------------------------------------------------------------


def test_find_function_top_level() -> None:
    tree = ast.parse("def target():\n    pass\n")
    func = find_function(tree, "target")
    assert func is not None
    assert func.name == "target"


def test_find_function_dotted_method() -> None:
    tree = ast.parse("class Foo:\n    def bar(self):\n        pass\n")
    func = find_function(tree, "Foo.bar")
    assert func is not None
    assert func.name == "bar"


def test_find_function_missing_returns_none() -> None:
    tree = ast.parse("def other():\n    pass\n")
    assert find_function(tree, "target") is None


# ---------------------------------------------------------------------------
# unguarded_arithmetic_sites -- efficacy
# ---------------------------------------------------------------------------


def test_finds_float_wrapping_get_with_non_none_default() -> None:
    tree, func = _fn("def target(o):\n    return float(o.get('heat', 0.0))\n")
    assert unguarded_arithmetic_sites(tree, func, "heat") == [2]


def test_finds_float_wrapping_bare_subscript() -> None:
    tree, func = _fn("def target(o):\n    return float(o['heat'])\n")
    assert unguarded_arithmetic_sites(tree, func, "heat") == [2]


def test_finds_sum_over_generator_with_get_default() -> None:
    tree, func = _fn("def target(orgs):\n    return sum(o.get('heat', 0.0) for o in orgs)\n")
    assert unguarded_arithmetic_sites(tree, func, "heat") == [2]


def test_ignores_get_with_no_default(tmp_path: Path) -> None:
    """`o.get('heat')` with NO default is not the footgun shape -- the
    default argument is what falsely signals safety."""
    tree, func = _fn("def target(o):\n    return float(o.get('heat'))\n")
    assert unguarded_arithmetic_sites(tree, func, "heat") == []


def test_ignores_get_with_explicit_none_default() -> None:
    """`.get(field, None)` is redundant but not a footgun -- float(None)
    would crash regardless of whether fog masked it, so it is not THIS
    bug's shape (still crashes either way, no false sense of safety)."""
    tree, func = _fn("def target(o):\n    return float(o.get('heat', None))\n")
    assert unguarded_arithmetic_sites(tree, func, "heat") == []


def test_ignores_unrelated_field_name() -> None:
    tree, func = _fn("def target(o):\n    return float(o.get('budget', 0.0))\n")
    assert unguarded_arithmetic_sites(tree, func, "heat") == []


def test_ignores_non_arithmetic_use() -> None:
    """A `.get(field, default)` NOT wrapped in an arithmetic call is out of
    this check's narrow scope (it may still be a bug, but a different
    class -- this sentinel only guards the arithmetic-crash shape)."""
    tree, func = _fn("def target(o):\n    return o.get('heat', 0.0)\n")
    assert unguarded_arithmetic_sites(tree, func, "heat") == []


# ---------------------------------------------------------------------------
# guard_exists_for_field -- efficacy
# ---------------------------------------------------------------------------


def test_guard_finds_get_is_not_none() -> None:
    _tree, func = _fn("def target(o):\n    return [1] if o.get('heat') is not None else []\n")
    assert guard_exists_for_field(func, "heat")


def test_guard_finds_subscript_is_not_none() -> None:
    _tree, func = _fn("def target(o):\n    return o['heat'] is not None\n")
    assert guard_exists_for_field(func, "heat")


def test_guard_finds_comprehension_if_clause() -> None:
    """The real shipped shape: `[... for o in xs if o.get('heat') is not
    None]` -- the guard lives in a comprehension `ifs` clause."""
    _tree, func = _fn(
        "def target(orgs):\n"
        "    return [float(o['heat']) for o in orgs if o.get('heat') is not None]\n"
    )
    assert guard_exists_for_field(func, "heat")


def test_guard_absent_when_no_comparison_present() -> None:
    _tree, func = _fn("def target(o):\n    return float(o.get('heat', 0.0))\n")
    assert not guard_exists_for_field(func, "heat")


def test_guard_does_not_match_unrelated_field() -> None:
    _tree, func = _fn("def target(o):\n    return o.get('budget') is not None\n")
    assert not guard_exists_for_field(func, "heat")


# ---------------------------------------------------------------------------
# unguarded_masked_arithmetic -- regression (synthetic files)
# ---------------------------------------------------------------------------


def _row(
    def_file: str, function_name: str = "target", field: str = "heat"
) -> DeclaredFoggedConsumer:
    return DeclaredFoggedConsumer(
        name="synthetic_row",
        def_file=def_file,
        function_name=function_name,
        field=field,
        payload_note="synthetic test row",
        consequence_if_regressed="synthetic test row",
    )


def test_reds_on_the_founding_bug_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("babylon.sentinels.masked_arithmetic.checks._REPO_ROOT", tmp_path)
    rel = "buggy.py"
    (tmp_path / rel).write_text(
        "def target(orgs):\n    return sum(float(o.get('heat', 0.0)) for o in orgs)\n",
        encoding="utf-8",
    )
    violations = unguarded_masked_arithmetic((_row(rel),))
    assert len(violations) == 1
    assert "synthetic_row" in violations[0]


def test_clean_on_the_shipped_fix_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("babylon.sentinels.masked_arithmetic.checks._REPO_ROOT", tmp_path)
    rel = "fixed.py"
    (tmp_path / rel).write_text(
        "def target(orgs):\n"
        "    visible = [float(o['heat']) for o in orgs if o.get('heat') is not None]\n"
        "    return sum(visible) if visible else None\n",
        encoding="utf-8",
    )
    assert unguarded_masked_arithmetic((_row(rel),)) == []


def test_clean_when_field_never_touched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("babylon.sentinels.masked_arithmetic.checks._REPO_ROOT", tmp_path)
    rel = "unrelated.py"
    (tmp_path / rel).write_text("def target(orgs):\n    return len(orgs)\n", encoding="utf-8")
    assert unguarded_masked_arithmetic((_row(rel),)) == []


def test_raises_when_function_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("babylon.sentinels.masked_arithmetic.checks._REPO_ROOT", tmp_path)
    rel = "empty.py"
    (tmp_path / rel).write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError):
        unguarded_masked_arithmetic((_row(rel),))


def test_exempted_row_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from babylon.sentinels.exemptions import SentinelExemption

    monkeypatch.setattr("babylon.sentinels.masked_arithmetic.checks._REPO_ROOT", tmp_path)
    rel = "buggy2.py"
    (tmp_path / rel).write_text(
        "def target(orgs):\n    return sum(float(o.get('heat', 0.0)) for o in orgs)\n",
        encoding="utf-8",
    )
    row = DeclaredFoggedConsumer(
        name="synthetic_row",
        def_file=rel,
        function_name="target",
        field="heat",
        payload_note="synthetic",
        consequence_if_regressed="synthetic",
    )
    exemption = SentinelExemption(
        key=("fogged_consumer", "synthetic_row"),
        reason="test",
        owner="test",
        date="2026-07-18",
        tracking_task="#1",
    )
    monkeypatch.setattr(
        "babylon.sentinels.masked_arithmetic.checks.MASKED_ARITHMETIC_EXEMPTIONS", (exemption,)
    )
    assert unguarded_masked_arithmetic((row,)) == []


def test_exemption_does_not_absorb_a_different_row_of_the_same_class(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation-validation of the teeth: an exemption for one function/field
    row must NOT silently clear a genuinely-different unguarded row."""
    from babylon.sentinels.exemptions import SentinelExemption

    monkeypatch.setattr("babylon.sentinels.masked_arithmetic.checks._REPO_ROOT", tmp_path)
    rel = "buggy3.py"
    (tmp_path / rel).write_text(
        "def target(orgs):\n    return sum(float(o.get('heat', 0.0)) for o in orgs)\n",
        encoding="utf-8",
    )
    exempted_row = DeclaredFoggedConsumer(
        name="synthetic_row",
        def_file=rel,
        function_name="target",
        field="heat",
        payload_note="synthetic",
        consequence_if_regressed="synthetic",
    )
    other_row = DeclaredFoggedConsumer(
        name="a_completely_different_row",
        def_file=rel,
        function_name="target",
        field="heat",
        payload_note="synthetic",
        consequence_if_regressed="synthetic",
    )
    exemption = SentinelExemption(
        key=("fogged_consumer", "synthetic_row"),
        reason="test",
        owner="test",
        date="2026-07-18",
        tracking_task="#1",
    )
    monkeypatch.setattr(
        "babylon.sentinels.masked_arithmetic.checks.MASKED_ARITHMETIC_EXEMPTIONS", (exemption,)
    )
    violations = unguarded_masked_arithmetic((exempted_row, other_row))
    assert len(violations) == 1
    assert "a_completely_different_row" in violations[0]
    assert "synthetic_row" not in violations[0]


# ---------------------------------------------------------------------------
# Liveness -- the real, shipped registry
# ---------------------------------------------------------------------------


def test_repo_root_resolves_correctly() -> None:
    assert (_REPO_ROOT / "pyproject.toml").is_file()


def test_declared_registry_has_the_one_seeded_row() -> None:
    assert len(DECLARED_FOGGED_CONSUMERS) == 1
    assert DECLARED_FOGGED_CONSUMERS[0].name == "state_apparatus_dashboard_heat"


def test_live_registry_is_clean_against_the_shipped_fix() -> None:
    """_build_state_apparatus_dashboard's heat guard (commit 657e415c6) must
    stay in place -- this is the regression this sentinel exists to pin."""
    assert unguarded_masked_arithmetic() == []
