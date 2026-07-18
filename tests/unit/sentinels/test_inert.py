"""Tests for the inert sentinel: a declared construct must be reachable.

Three tiers, mirroring the vocabulary/synthetic sentinels' own test shape:

- **Efficacy** (AST-helper level, tmp_path fixtures) — the extractors
  correctly SEE each syntactic form of "a real caller" and correctly MISS
  each syntactic form of "not a caller" (import alias, ``__all__`` entry,
  unrelated same-named method on a different class, self-recursion). This is
  the load-bearing tier: a scanner that silently over- or under-matches
  passes every liveness assertion while enforcing nothing or crying wolf.
- **Regression** (injected registry rows against REAL repo files) — proves
  the gating check functions actually red on a genuinely-uncalled row and
  stay clean on a genuinely-called one, independent of the live registry's
  current temporal state.
- **Liveness** (the real, shipped registry) — the two declared stores, the
  one declared producer, and the growth check against the current tree. As of
  this writing ``intel_ledger`` IS wired (``web/game/fog/ledger.py::
  ledger_from_events`` — landed by a concurrent agent on this same branch,
  Track 1/Task 9 — constructs an ``IntelLedger`` and calls ``.append()`` in a
  loop, and ``engine_bridge.py`` calls ``ledger_from_events``), so this tier
  asserts clean directly rather than via ``xfail``. See
  ``ai/_inbox``/scratchpad report for the RED evidence captured earlier in
  this same session, before that writer landed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.inert.checks import (
    _REPO_ROOT,
    _is_frozen_model,
    _self_returning_methods,
    detect_accumulator_classes,
    is_test_source,
    producer_reference_sites,
    producers_without_production_caller,
    store_writer_call_sites,
    stores_without_production_writer,
    undeclared_accumulator_stores,
)
from babylon.sentinels.inert.registry import (
    DECLARED_PRODUCERS,
    DECLARED_STORES,
    DeclaredProducer,
    DeclaredStore,
)

pytestmark = pytest.mark.unit

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
_TOOL_PATH = _TOOLS_DIR / "sentinel_check.py"


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
    assert is_test_source(tmp_path / "test_ledger.py")


def test_is_test_source_matches_test_suffix(tmp_path: Path) -> None:
    assert is_test_source(tmp_path / "ledger_test.py")


def test_is_test_source_matches_nested_tests_directory() -> None:
    """web/game/tests/*.py counts the same as top-level tests/ -- the whole
    point is a test-only caller anywhere must never satisfy a reachability
    check."""
    assert is_test_source(Path("web/game/tests/test_something.py"))
    assert is_test_source(Path("tests/unit/web/test_engine_bridge.py"))


def test_is_test_source_false_for_ordinary_module() -> None:
    assert not is_test_source(Path("web/game/fog/ledger.py"))


# ---------------------------------------------------------------------------
# store_writer_call_sites -- efficacy
# ---------------------------------------------------------------------------


def test_store_finds_constructor_assign_then_call(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "ledger = Ledger()\nledger.append(entry)\n",
    )
    assert store_writer_call_sites(path, "Ledger", ("append",)) == [2]


def test_store_finds_annotated_parameter_call(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "def resolve(ledger: Ledger) -> None:\n    ledger.append(entry)\n",
    )
    assert store_writer_call_sites(path, "Ledger", ("append",)) == [2]


def test_store_finds_optional_union_annotated_parameter_call(tmp_path: Path) -> None:
    """`ledger: Ledger | None = None` -- the exact shape every fog call site
    in engine_bridge.py uses for IntelLedger."""
    path = _write(
        tmp_path,
        "def resolve(ledger: Ledger | None = None) -> None:\n"
        "    if ledger is not None:\n"
        "        ledger.append(entry)\n",
    )
    assert store_writer_call_sites(path, "Ledger", ("append",)) == [3]


def test_store_finds_chained_writer_call(tmp_path: Path) -> None:
    """`a.append(x).append(y)` -- both sites found via the fixed-point pass
    (the immutable-update pattern returns the same class)."""
    path = _write(
        tmp_path,
        "a = Ledger()\nb = a.append(x)\nb.append(y)\n",
    )
    assert store_writer_call_sites(path, "Ledger", ("append",)) == [2, 3]


def test_store_ignores_unrelated_list_append(tmp_path: Path) -> None:
    """The `.append` collision case: a plain list is NOT a Ledger."""
    path = _write(
        tmp_path,
        "results = []\nresults.append(x)\n",
    )
    assert store_writer_call_sites(path, "Ledger", ("append",)) == []


def test_store_ignores_same_method_name_on_different_class(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "other = OtherThing()\nother.append(x)\n",
    )
    assert store_writer_call_sites(path, "Ledger", ("append",)) == []


def test_store_check_raises_on_unparseable_source(tmp_path: Path) -> None:
    path = _write(tmp_path, "def (:\n", name="broken.py")
    with pytest.raises(SentinelCheckError):
        store_writer_call_sites(path, "Ledger", ("append",))


# ---------------------------------------------------------------------------
# producer_reference_sites -- efficacy
# ---------------------------------------------------------------------------


def test_producer_finds_direct_call(tmp_path: Path) -> None:
    path = _write(tmp_path, "result = compute_thing(x, y)\n")
    assert producer_reference_sites(path, "compute_thing", "elsewhere.py") == [1]


def test_producer_finds_indirect_registry_reference(tmp_path: Path) -> None:
    """`registry.register("x", compute_thing)` -- a bare reference, never
    itself called at this site (the registry calls it later) -- exactly the
    formula_registry.py pattern this sentinel must not blind itself to."""
    path = _write(tmp_path, 'registry.register("x", compute_thing)\n')
    assert producer_reference_sites(path, "compute_thing", "elsewhere.py") == [1]


def test_producer_finds_attribute_reference_without_import(tmp_path: Path) -> None:
    path = _write(tmp_path, "value = formulas.compute_thing(a, b)\n")
    assert producer_reference_sites(path, "compute_thing", "elsewhere.py") == [1]


def test_producer_ignores_bare_import_alias(tmp_path: Path) -> None:
    """A plain import with no subsequent use is NOT reachability -- the
    exact "re-exported but never called" gap this sentinel exists to catch."""
    path = _write(tmp_path, "from mymodule import compute_thing\n")
    assert producer_reference_sites(path, "compute_thing", "elsewhere.py") == []


def test_producer_ignores_all_list_entry(tmp_path: Path) -> None:
    """A name inside `__all__` is a string literal, not a Name/Attribute node."""
    path = _write(tmp_path, '__all__ = ["compute_thing"]\n')
    assert producer_reference_sites(path, "compute_thing", "elsewhere.py") == []


def test_producer_excludes_self_recursive_reference_in_own_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A function's own recursive call to itself is not evidence anything
    ELSE reaches it -- only counts when `path` is NOT `def_file`.

    `_REPO_ROOT` is monkeypatched to `tmp_path` so `def_file` (a
    tmp_path-relative name) resolves to the SAME file `producer_reference_sites`
    parses, simulating "this file IS the declaring file".
    """
    monkeypatch.setattr("babylon.sentinels.inert.checks._REPO_ROOT", tmp_path)
    path = _write(tmp_path, "def compute_thing(n):\n    return compute_thing(n - 1)\n")
    assert producer_reference_sites(path, "compute_thing", "sample.py") == []


def test_producer_counts_reference_outside_own_function_in_declaring_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sibling function in the SAME declaring file calling the producer
    is a real production caller, not excluded by the self-body guard."""
    monkeypatch.setattr("babylon.sentinels.inert.checks._REPO_ROOT", tmp_path)
    source = (
        "def compute_thing(n):\n    return n * 2\n\ndef helper():\n    return compute_thing(3)\n"
    )
    path = _write(tmp_path, source)
    assert producer_reference_sites(path, "compute_thing", "sample.py") == [5]


def test_producer_check_raises_on_unparseable_source(tmp_path: Path) -> None:
    path = _write(tmp_path, "def (:\n", name="broken.py")
    with pytest.raises(SentinelCheckError):
        producer_reference_sites(path, "compute_thing", "elsewhere.py")


# ---------------------------------------------------------------------------
# Structural detector -- efficacy
# ---------------------------------------------------------------------------


def _first_class(tmp_path: Path, source: str) -> object:
    import ast

    path = _write(tmp_path, source)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            return node
    raise AssertionError("no class found in synthetic source")


def test_detector_matches_frozen_self_returning_class(tmp_path: Path) -> None:
    cls = _first_class(
        tmp_path,
        "class Ledger(BaseModel):\n"
        "    model_config = ConfigDict(frozen=True)\n"
        "    def append(self, entry):\n"
        "        return Ledger(entries=(*self.entries, entry))\n",
    )
    assert _is_frozen_model(cls)
    assert _self_returning_methods(cls) == ("append",)


def test_detector_ignores_non_frozen_class(tmp_path: Path) -> None:
    cls = _first_class(
        tmp_path,
        "class Mutable(BaseModel):\n"
        "    def append(self, entry):\n"
        "        return Mutable(entries=(*self.entries, entry))\n",
    )
    assert not _is_frozen_model(cls)


def test_detector_ignores_frozen_class_with_no_self_returning_method(tmp_path: Path) -> None:
    cls = _first_class(
        tmp_path,
        "class ReadOnly(BaseModel):\n"
        "    model_config = ConfigDict(frozen=True)\n"
        "    def latest(self):\n"
        "        return self.entries[-1]\n",
    )
    assert _is_frozen_model(cls)
    assert _self_returning_methods(cls) == ()


# ---------------------------------------------------------------------------
# Regression: injected rows against REAL repo files (registry-state-independent)
# ---------------------------------------------------------------------------


def test_stores_check_reds_on_a_writer_method_with_no_real_callers() -> None:
    """A synthetic method name guaranteed to have zero call sites anywhere,
    declared against a REAL existing class/file -- proves the check reds on
    genuine absence, independent of what IntelLedger.append looks like today."""
    phantom = DeclaredStore(
        name="phantom_store",
        def_file="web/game/fog/ledger.py",
        class_name="IntelLedger",
        writer_methods=("this_writer_method_does_not_exist_anywhere",),
        what_it_stores="synthetic defect for the efficacy proof",
        failure_if_unwired="n/a",
    )
    violations = stores_without_production_writer((phantom,))
    assert len(violations) == 1
    assert "phantom_store" in violations[0]


def test_stores_check_passes_on_a_writer_method_with_a_real_caller() -> None:
    """`IntelLedger.latest()` IS called in production (`read_intel()`,
    `web/game/fog/ledger.py`, itself called from `web/game/fog/filter.py`)
    -- a stable, real positive-control independent of the append() gap."""
    real = DeclaredStore(
        name="latest_reader",
        def_file="web/game/fog/ledger.py",
        class_name="IntelLedger",
        writer_methods=("latest",),
        what_it_stores="synthetic positive-control row",
        failure_if_unwired="n/a",
    )
    assert stores_without_production_writer((real,)) == []


def test_producers_check_reds_on_a_symbol_with_no_real_references() -> None:
    phantom = DeclaredProducer(
        name="phantom_producer",
        def_file="src/babylon/formulas/consciousness_routing.py",
        symbol="this_symbol_does_not_exist_anywhere_zzz",
        what_it_produces="synthetic defect for the efficacy proof",
    )
    violations = producers_without_production_caller((phantom,))
    assert len(violations) == 1
    assert "phantom_producer" in violations[0]


def test_producers_check_passes_on_the_real_reification_buffer_row() -> None:
    assert producers_without_production_caller(DECLARED_PRODUCERS) == []


def test_stores_check_raises_on_missing_declared_file() -> None:
    phantom = DeclaredStore(
        name="gone_module",
        def_file="web/game/fog/does_not_exist.py",
        class_name="Whatever",
        writer_methods=("append",),
        what_it_stores="synthetic missing-file defect",
        failure_if_unwired="n/a",
    )
    with pytest.raises(SentinelCheckError):
        store_writer_call_sites(
            _REPO_ROOT / phantom.def_file, phantom.class_name, phantom.writer_methods
        )


# ---------------------------------------------------------------------------
# Liveness: the real, shipped registry against the current tree
# ---------------------------------------------------------------------------


def test_registry_declares_the_two_known_stores() -> None:
    names = {row.name for row in DECLARED_STORES}
    assert {"intel_ledger", "class_distribution"} <= names


def test_registry_declares_the_seeded_producer() -> None:
    names = {row.name for row in DECLARED_PRODUCERS}
    assert "reification_buffer" in names


def test_class_distribution_store_is_wired_in_production() -> None:
    """POSITIVE control: with_updated_dynamics() IS called from
    transition_engine.py -- this row must never appear in the violation
    list, proving the check discriminates wired from unwired stores."""
    violations = stores_without_production_writer()
    assert not any("class_distribution" in v for v in violations)


def test_all_declared_stores_are_currently_wired() -> None:
    """As of this writing, IntelLedger.append() DOES have a production caller
    (``web/game/fog/ledger.py::ledger_from_events``, called from
    ``engine_bridge.py``) -- the concurrent agent's writer landed during this
    same session. If this ever regresses, the failure message names exactly
    which store lost its writer."""
    assert stores_without_production_writer() == []


def test_growth_check_is_clean_against_the_real_tree() -> None:
    """Every accumulator-shaped class currently in src/web is declared."""
    assert undeclared_accumulator_stores() == []


def test_growth_check_reds_when_registry_is_emptied() -> None:
    """EFFICACY: with an empty registry, the two real detected classes
    (IntelLedger, ClassDistribution) must both surface as undeclared --
    proves the growth check is actually scanning, not vacuously clean."""
    violations = undeclared_accumulator_stores(registry=())
    assert len(violations) == 2
    joined = "\n".join(violations)
    assert "IntelLedger" in joined
    assert "ClassDistribution" in joined


def test_detect_accumulator_classes_finds_exactly_the_two_known_hits() -> None:
    hits = detect_accumulator_classes()
    names = {class_name for _rel, class_name, _methods in hits}
    assert names == {"IntelLedger", "ClassDistribution"}


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_entry_point_is_clean() -> None:
    """``sentinel_check.py inert --check`` exits 0 today (CI fast-gate idiom),
    mirroring ``test_cli_entry_point_is_clean`` in the vocabulary sentinel's
    own test suite."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "inert", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "INERT sensor reds against the shipped registry:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "INERT clean" in result.stdout
