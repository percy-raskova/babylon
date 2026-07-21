"""Tests for the formula_registration sentinel: a registered formula must be USED.

Four tiers, mirroring the inert/unconsumed sentinels' own test shape
(``test_inert.py``/``test_unconsumed.py``):

- **Efficacy** (AST-helper level, tmp_path fixtures) — :func:`formula_reference_sites`
  correctly SEES a direct call, a module-qualified attribute call, and an
  import-aliased call; correctly MISSES an unrelated string mention (a
  docstring, a ``concept_cards.py``-style citation) and a Store-context
  namesake (a Pydantic field sharing the formula's bare name).
- **Regression** (injected registry rows against a synthetic tree, via
  ``tmp_path`` monkeypatched over ``_REPO_ROOT``) — proves the gating check
  function reds on a genuinely-uncalled row, stays clean on a genuinely-called
  one (including via an import alias), and — the fix this sentinel exists
  for — still reds when the ONLY reference lives inside the synthetic
  ``engine/formula_registry.py`` path itself (the registration act, not
  downstream consumption).
- **Liveness** (the real, shipped registry) — ``labor_aristocracy_ratio`` and
  ``is_labor_aristocracy`` (Vol I U2/ADR109) are genuinely live;
  ``consciousness_drift`` is a real, open gap held GREEN only via the one
  recorded :class:`~babylon.sentinels.exemptions.SentinelExemption`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.formula_registration.checks import (
    _REPO_ROOT,
    formula_reference_sites,
    formulas_without_production_caller,
    is_test_source,
)
from babylon.sentinels.formula_registration.registry import (
    DECLARED_FORMULAS,
    FORMULA_REGISTRY_FILE,
    DeclaredFormula,
)

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, source: str, name: str = "sample.py") -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# is_test_source
# ---------------------------------------------------------------------------


def test_is_test_source_matches_conftest(tmp_path: Path) -> None:
    assert is_test_source(tmp_path / "conftest.py")


def test_is_test_source_matches_test_prefix(tmp_path: Path) -> None:
    assert is_test_source(tmp_path / "test_ideology.py")


def test_is_test_source_matches_nested_tests_directory() -> None:
    assert is_test_source(Path("web/game/tests/test_something.py"))


def test_is_test_source_false_for_ordinary_module() -> None:
    assert not is_test_source(Path("src/babylon/engine/systems/ideology.py"))


# ---------------------------------------------------------------------------
# formula_reference_sites -- efficacy
# ---------------------------------------------------------------------------


def test_finds_direct_call(tmp_path: Path) -> None:
    path = _write(tmp_path, "ratio = calculate_labor_aristocracy_ratio(w, v)\n")
    assert formula_reference_sites(path, "calculate_labor_aristocracy_ratio") == [1]


def test_finds_module_qualified_attribute_call(tmp_path: Path) -> None:
    path = _write(tmp_path, "registry.register('x', formulas.calculate_labor_aristocracy_ratio)\n")
    assert formula_reference_sites(path, "calculate_labor_aristocracy_ratio") == [1]


def test_finds_import_aliased_call(tmp_path: Path) -> None:
    """The exact real shape: ``is_labor_aristocracy`` imported ``as
    _is_labor_aristocracy`` in ``value_form.py`` and called only under the
    alias -- a naive bare-symbol scan would go blind to this."""
    path = _write(
        tmp_path,
        "from babylon.formulas.fundamental_theorem import is_labor_aristocracy as _is_labor_aristocracy\n"
        "result = _is_labor_aristocracy(w, v)\n",
    )
    assert formula_reference_sites(path, "is_labor_aristocracy") == [2]


def test_ignores_unrelated_string_literal(tmp_path: Path) -> None:
    """A bare string mention (docstring, concept_cards.py-style citation) is
    a Constant, never a Name/Attribute Load -- must not be mistaken for a
    caller (the weaker version of the exact bug this sentinel fixes)."""
    path = _write(
        tmp_path,
        '"""Cites calculate_labor_aristocracy_ratio in prose."""\n'
        'IMPLEMENTATION = ("babylon.formulas.calculate_labor_aristocracy_ratio",)\n',
    )
    assert formula_reference_sites(path, "calculate_labor_aristocracy_ratio") == []


def test_ignores_store_context_namesake(tmp_path: Path) -> None:
    """A Pydantic field sharing the formula's bare name
    (``is_labor_aristocracy: bool | None = Field(...)``) assigns to a NAME in
    Store context -- not a Load reference to the formula itself."""
    path = _write(tmp_path, "is_labor_aristocracy: bool | None = None\n")
    assert formula_reference_sites(path, "is_labor_aristocracy") == []


def test_ignores_keyword_argument_namesake(tmp_path: Path) -> None:
    """``ClassPhiReading(is_labor_aristocracy=aristocracy)`` -- the keyword
    NAME is a bare str on ast.keyword, never a Name/Attribute node; only the
    ``aristocracy`` value expression is a Load reference (to a different
    symbol entirely)."""
    path = _write(tmp_path, "reading = ClassPhiReading(is_labor_aristocracy=aristocracy)\n")
    assert formula_reference_sites(path, "is_labor_aristocracy") == []


def test_check_raises_on_unparseable_source(tmp_path: Path) -> None:
    path = _write(tmp_path, "def (:\n", name="broken.py")
    with pytest.raises(SentinelCheckError):
        formula_reference_sites(path, "calculate_labor_aristocracy_ratio")


# ---------------------------------------------------------------------------
# formulas_without_production_caller -- regression (synthetic tree)
# ---------------------------------------------------------------------------


def _row(symbol: str = "my_synthetic_formula") -> DeclaredFormula:
    return DeclaredFormula(
        name=symbol,
        def_file="src/babylon/formulas/synthetic.py",
        symbol=symbol,
        what_it_computes="synthetic test row",
    )


def test_finds_violation_for_genuinely_uncalled_formula(monkeypatch: pytest.MonkeyPatch) -> None:
    """A symbol referenced NOWHERE in production code (a nonsense name) must
    be reported as a violation against the REAL repo tree."""
    row = _row(symbol="totally_synthetic_uncalled_formula_xyz123")
    violations = formulas_without_production_caller((row,))
    assert len(violations) == 1
    assert "totally_synthetic_uncalled_formula_xyz123" in violations[0]


def test_clean_for_a_formula_with_a_real_production_caller(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "src" / "caller.py").write_text(
        "value = my_synthetic_formula(1.0, 2.0)\n", encoding="utf-8"
    )
    monkeypatch.setattr("babylon.sentinels.formula_registration.checks._REPO_ROOT", tmp_path)
    row = _row()
    assert formulas_without_production_caller((row,)) == []


def test_clean_for_a_formula_called_only_via_import_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression harness proof of the alias-resolution fix, end to end
    through the gating function (not just the AST helper)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "src" / "caller.py").write_text(
        "from babylon.formulas.synthetic import my_synthetic_formula as _aliased\n"
        "value = _aliased(1.0, 2.0)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("babylon.sentinels.formula_registration.checks._REPO_ROOT", tmp_path)
    row = _row()
    assert formulas_without_production_caller((row,)) == []


def test_reds_when_only_reference_is_the_registration_file_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """THE fix this sentinel exists for: a formula whose ONLY production
    reference is its own ``engine/formula_registry.py`` registration call
    must still be reported as a violation -- exactly the gap
    :mod:`babylon.sentinels.inert` cannot see (it would count this as a
    satisfied reference)."""
    registry_path = tmp_path / FORMULA_REGISTRY_FILE
    registry_path.parent.mkdir(parents=True)
    (tmp_path / "web").mkdir()
    registry_path.write_text(
        "registry.register('x', formulas.my_synthetic_formula)\n", encoding="utf-8"
    )
    monkeypatch.setattr("babylon.sentinels.formula_registration.checks._REPO_ROOT", tmp_path)
    row = _row()
    violations = formulas_without_production_caller((row,))
    assert len(violations) == 1
    assert "my_synthetic_formula" in violations[0]


def test_test_only_caller_does_not_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_caller.py").write_text(
        "value = my_synthetic_formula(1.0, 2.0)\n", encoding="utf-8"
    )
    monkeypatch.setattr("babylon.sentinels.formula_registration.checks._REPO_ROOT", tmp_path)
    row = _row()
    violations = formulas_without_production_caller((row,))
    assert len(violations) == 1


def test_exempted_row_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    from babylon.sentinels.exemptions import SentinelExemption

    row = _row(symbol="totally_synthetic_uncalled_formula_xyz123")
    exemption = SentinelExemption(
        key=("formula", row.name),
        reason="test exemption",
        owner="test",
        date="2026-07-21",
        tracking_task="#1",
    )
    monkeypatch.setattr(
        "babylon.sentinels.formula_registration.checks.FORMULA_EXEMPTIONS", (exemption,)
    )
    assert formulas_without_production_caller((row,)) == []


def test_exemption_does_not_absorb_a_different_row_of_the_same_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutation-validation of the teeth: an exemption for one formula must
    NOT silently clear a genuinely-different uncalled one."""
    from babylon.sentinels.exemptions import SentinelExemption

    exempted_row = _row(symbol="totally_synthetic_uncalled_formula_xyz123")
    other_row = _row(symbol="a_completely_different_uncalled_formula_abc789")
    exemption = SentinelExemption(
        key=("formula", exempted_row.name),
        reason="test exemption",
        owner="test",
        date="2026-07-21",
        tracking_task="#1",
    )
    monkeypatch.setattr(
        "babylon.sentinels.formula_registration.checks.FORMULA_EXEMPTIONS", (exemption,)
    )
    violations = formulas_without_production_caller((exempted_row, other_row))
    assert len(violations) == 1
    assert "a_completely_different_uncalled_formula_abc789" in violations[0]
    assert "totally_synthetic_uncalled_formula_xyz123" not in violations[0]


# ---------------------------------------------------------------------------
# Liveness -- the real, shipped registry
# ---------------------------------------------------------------------------


def test_repo_root_resolves_correctly() -> None:
    assert (_REPO_ROOT / "pyproject.toml").is_file()


def test_declared_registry_has_the_three_seeded_rows() -> None:
    assert len(DECLARED_FORMULAS) == 3
    assert {row.name for row in DECLARED_FORMULAS} == {
        "labor_aristocracy_ratio",
        "is_labor_aristocracy",
        "consciousness_drift",
    }


def test_labor_aristocracy_ratio_is_genuinely_live() -> None:
    """Vol I U2 (ADR109): compute_fundamental_theorem calls it directly."""
    row = next(r for r in DECLARED_FORMULAS if r.name == "labor_aristocracy_ratio")
    assert formulas_without_production_caller((row,)) == []


def test_is_labor_aristocracy_is_genuinely_live_via_its_alias() -> None:
    """Vol I U2 (ADR109): called only as ``_is_labor_aristocracy`` in
    value_form.py -- proves the real registry row, not just the synthetic
    fixture, needs alias resolution to pass honestly."""
    row = next(r for r in DECLARED_FORMULAS if r.name == "is_labor_aristocracy")
    assert formulas_without_production_caller((row,)) == []


def test_consciousness_drift_is_clean_only_via_the_recorded_exemption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """calculate_consciousness_drift IS registered and referenced by
    web/game/provenance.py, but that reference only ever reads its __doc__ --
    never invokes it for a value. This pins that the sentinel is GREEN
    *because of the exemption*, not because the gap was fixed: WITHOUT the
    exemption, the real registry row genuinely reds."""
    from babylon.sentinels.exemptions import is_exempt
    from babylon.sentinels.formula_registration.registry import FORMULA_EXEMPTIONS

    assert is_exempt(("formula", "consciousness_drift"), FORMULA_EXEMPTIONS)
    row = next(r for r in DECLARED_FORMULAS if r.name == "consciousness_drift")

    monkeypatch.setattr("babylon.sentinels.formula_registration.checks.FORMULA_EXEMPTIONS", ())
    violations = formulas_without_production_caller((row,))
    assert len(violations) == 1
    assert "consciousness_drift" in violations[0]

    # With the real exemption restored (monkeypatch undone), the whole
    # shipped registry is clean.
    monkeypatch.undo()
    assert formulas_without_production_caller() == []


def test_full_registry_is_clean() -> None:
    """The real, shipped registry — all three rows — gates clean today."""
    assert formulas_without_production_caller() == []
