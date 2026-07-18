"""Tests for the unconsumed sentinel: a declared computed value must be read.

Three tiers, mirroring the inert sentinel's own test shape (``test_inert.py``):

- **Efficacy** (AST-helper level, tmp_path fixtures) — :func:`reader_sites`
  correctly SEES each syntactic form of "a real reader" (subscript, ``.get()``,
  ``.pop()``) and correctly MISSES each syntactic form of "not a reader" (a
  same-named key on an unrelated dict access is still a match by design — see
  the checks module's own Scope note on the name-based heuristic; what must
  NOT match is an unrelated string literal, e.g. inside ``__all__`` or a
  docstring, which is not a :class:`ast.Subscript`/``.get()``/``.pop()`` node
  at all).
- **Regression** (injected registry rows against REAL repo files, via
  ``tmp_path`` synthetic trees monkeypatched over ``PRODUCTION_ROOTS``) —
  proves the gating check function actually reds on a genuinely-unread row
  and stays clean on a genuinely-read one.
- **Liveness** (the real, shipped registry) — the one declared row,
  ``reification_buffer``. As of this writing it IS a genuine, unremediated
  gap (Track 1 audit finding) — this tier asserts the CURRENT REAL FINDING
  (the row has no reader), not a clean pass, because that is the honest
  state of the repository today; flipping it to clean requires wiring a real
  consumer, out of scope for the sentinel-suite task that added this gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.unconsumed.checks import (
    _REPO_ROOT,
    computed_fields_without_consumer,
    is_test_source,
    reader_sites,
)
from babylon.sentinels.unconsumed.registry import (
    DECLARED_COMPUTED_FIELDS,
    DeclaredComputedField,
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
# reader_sites -- efficacy
# ---------------------------------------------------------------------------


def test_reader_finds_subscript_read(tmp_path: Path) -> None:
    path = _write(tmp_path, "value = payload['reification_buffer']\n")
    assert reader_sites(path, "reification_buffer") == [1]


def test_reader_finds_get_call(tmp_path: Path) -> None:
    path = _write(tmp_path, "value = payload.get('reification_buffer')\n")
    assert reader_sites(path, "reification_buffer") == [1]


def test_reader_finds_get_call_with_default(tmp_path: Path) -> None:
    path = _write(tmp_path, "value = payload.get('reification_buffer', 0.5)\n")
    assert reader_sites(path, "reification_buffer") == [1]


def test_reader_finds_pop_call(tmp_path: Path) -> None:
    path = _write(tmp_path, "value = payload.pop('reification_buffer')\n")
    assert reader_sites(path, "reification_buffer") == [1]


def test_reader_finds_nested_chained_subscript(tmp_path: Path) -> None:
    """`node["material_conditions"]["reification_buffer"]` -- the real shape
    a graph-node reader would use; the OUTER key is irrelevant, only the
    INNER subscript's constant slice must match."""
    path = _write(
        tmp_path,
        "value = node['material_conditions']['reification_buffer']\n",
    )
    assert reader_sites(path, "reification_buffer") == [1]


def test_reader_ignores_dict_literal_write_key(tmp_path: Path) -> None:
    """A dict-LITERAL key (the write site's own shape) is never a
    Subscript/.get()/.pop() Load -- must not be mistaken for a reader."""
    path = _write(
        tmp_path,
        "material_conditions = {'reification_buffer': compute_it()}\n",
    )
    assert reader_sites(path, "reification_buffer") == []


def test_reader_ignores_unrelated_string_literal(tmp_path: Path) -> None:
    """A bare string mention (docstring, __all__ entry, unrelated literal)
    is a Constant, not a Subscript/.get()/.pop() node -- never a match."""
    path = _write(
        tmp_path,
        '"""Mentions reification_buffer in prose."""\n__all__ = ["reification_buffer"]\n',
    )
    assert reader_sites(path, "reification_buffer") == []


def test_reader_ignores_annotated_field_declaration(tmp_path: Path) -> None:
    """A Pydantic `Field(...)` declaration assigns to a NAME, not a
    Subscript/.get()/.pop() -- the model field declaration itself is not a
    reader of the dict key."""
    path = _write(
        tmp_path,
        "reification_buffer: float = Field(default=0.5)\n",
    )
    assert reader_sites(path, "reification_buffer") == []


def test_reader_check_raises_on_unparseable_source(tmp_path: Path) -> None:
    path = _write(tmp_path, "def (:\n", name="broken.py")
    with pytest.raises(SentinelCheckError):
        reader_sites(path, "reification_buffer")


# ---------------------------------------------------------------------------
# computed_fields_without_consumer -- regression (injected rows, real tree)
# ---------------------------------------------------------------------------


def _row(dict_key: str = "reification_buffer") -> DeclaredComputedField:
    return DeclaredComputedField(
        name=dict_key,
        write_file="src/babylon/engine/systems/ideology.py",
        write_symbol="ConsciousnessSystem.step",
        dict_key=dict_key,
        what_it_computes="synthetic test row",
        consequence_if_unread="synthetic test row",
    )


def test_finds_violation_for_genuinely_unread_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A dict key that appears NOWHERE in production code (a nonsense
    string) must be reported as a violation."""
    row = _row(dict_key="totally_synthetic_unread_key_xyz123")
    violations = computed_fields_without_consumer((row,))
    assert len(violations) == 1
    assert "totally_synthetic_unread_key_xyz123" in violations[0]


def test_clean_for_a_key_with_a_real_production_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Injecting a synthetic production tree (monkeypatched PRODUCTION_ROOTS
    equivalent via _REPO_ROOT) with a real reader clears the row."""
    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "src" / "reader.py").write_text(
        "value = payload.get('my_synthetic_field')\n", encoding="utf-8"
    )
    monkeypatch.setattr("babylon.sentinels.unconsumed.checks._REPO_ROOT", tmp_path)
    row = _row(dict_key="my_synthetic_field")
    assert computed_fields_without_consumer((row,)) == []


def test_reds_for_a_key_with_only_a_write_site_no_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact founding shape: a write site exists (dict-literal key), but
    no subscript/.get()/.pop() reader anywhere in the synthetic tree."""
    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "src" / "writer.py").write_text(
        "material_conditions = {'my_synthetic_field': compute_it()}\n", encoding="utf-8"
    )
    monkeypatch.setattr("babylon.sentinels.unconsumed.checks._REPO_ROOT", tmp_path)
    row = _row(dict_key="my_synthetic_field")
    violations = computed_fields_without_consumer((row,))
    assert len(violations) == 1
    assert "my_synthetic_field" in violations[0]


def test_test_only_reader_does_not_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A reader that lives only under tests/ must NOT satisfy the check --
    the exact bug this sentinel exists to catch (a closed loop where only
    the test reads what only the test wrote)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_writer.py").write_text(
        "value = payload.get('my_synthetic_field')\n", encoding="utf-8"
    )
    monkeypatch.setattr("babylon.sentinels.unconsumed.checks._REPO_ROOT", tmp_path)
    row = _row(dict_key="my_synthetic_field")
    # PRODUCTION_ROOTS is ("src", "web") -- tests/ is not scanned at all, so
    # this reproduces the same "no reader" result as if it did not exist.
    violations = computed_fields_without_consumer((row,))
    assert len(violations) == 1


def test_exempted_row_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    from babylon.sentinels.unconsumed.registry import UnconsumedExemption

    row = _row(dict_key="totally_synthetic_unread_key_xyz123")
    exemption = UnconsumedExemption(
        name=row.name,
        reason="test exemption",
        owner="test",
        date="2026-07-18",
    )
    monkeypatch.setattr("babylon.sentinels.unconsumed.checks.UNCONSUMED_EXEMPTIONS", (exemption,))
    assert computed_fields_without_consumer((row,)) == []


# ---------------------------------------------------------------------------
# Liveness -- the real, shipped registry
# ---------------------------------------------------------------------------


def test_repo_root_resolves_correctly() -> None:
    assert (_REPO_ROOT / "pyproject.toml").is_file()


def test_declared_registry_has_the_one_seeded_row() -> None:
    assert len(DECLARED_COMPUTED_FIELDS) == 1
    assert DECLARED_COMPUTED_FIELDS[0].name == "reification_buffer"


def test_live_registry_currently_reports_the_real_unremediated_gap() -> None:
    """Track 1 Task 10 finding: reification_buffer IS computed (a real
    production caller exists -- the inert sentinel's own rule covers that)
    and IS written onto the graph, but NOTHING in src/ or web/ reads
    material_conditions['reification_buffer'] back. This is the CURRENT,
    honest state of the repository -- this test pins that the sentinel
    correctly surfaces it, not that the repository is clean. Fixing this
    (wiring a real consumer, or recording a reasoned
    ``UnconsumedExemption``) is a follow-up, out of scope for the
    sentinel-suite task that built this gate.
    """
    violations = computed_fields_without_consumer()
    assert len(violations) == 1
    assert "reification_buffer" in violations[0]
