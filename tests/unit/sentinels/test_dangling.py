"""Tests for the dangling sentinel: a dynamic reference must land on something real.

DUAL of ``test_inert.py`` — mirrors its three-tier shape:

- **Efficacy** (AST-helper level, tmp_path fixtures) — the extractors
  correctly SEE each syntactic form of "a typed getattr call" and correctly
  MISS each syntactic form of "not a typed call" (unrelated receiver name,
  computed attribute name, an untyped bare name). This is the load-bearing
  tier: a scanner that silently over- or under-matches passes every
  liveness assertion while enforcing nothing or crying wolf.
- **Regression** (injected registry rows against synthetic files) — proves
  the gating check function actually reds on a genuinely-dangling reference
  and stays clean on a genuinely-real one, independent of the live
  registry's current temporal state.
- **Liveness** (the real, shipped registry) — the founding specimen
  (``web/game/engine_bridge.py:10990``,
  ``getattr(persistence, "persist_action_result", None)``) is still LIVE as
  of this writing (the parallel fix lane, task #43, has not landed yet on
  this branch) — the liveness test asserts the gate is RED and names
  exactly this specimen, proving the sentinel actually functions against
  the real tree rather than only against synthetic fixtures.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.dangling.checks import (
    class_members,
    dangling_references,
    is_test_source,
    typed_getattr_sites,
)
from babylon.sentinels.dangling.registry import (
    WATCHED_CLASSES,
    WATCHED_RECEIVERS,
    WatchedClass,
    WatchedReceiver,
)
from babylon.sentinels.exemptions import SentinelExemption

pytestmark = pytest.mark.unit

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
_TOOL_PATH = _TOOLS_DIR / "sentinel_check.py"


def _write(tmp_path: Path, source: str, name: str = "sample.py") -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# is_test_source (mirrors inert's own — verbatim behavior parity)
# ---------------------------------------------------------------------------


def test_is_test_source_matches_conftest(tmp_path: Path) -> None:
    assert is_test_source(tmp_path / "conftest.py")


def test_is_test_source_matches_nested_tests_directory() -> None:
    assert is_test_source(Path("web/game/tests/test_something.py"))


def test_is_test_source_false_for_ordinary_module() -> None:
    assert not is_test_source(Path("web/game/engine_bridge.py"))


# ---------------------------------------------------------------------------
# typed_getattr_sites -- efficacy
# ---------------------------------------------------------------------------


def test_finds_getattr_on_directly_annotated_parameter(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "def f(persistence: Thing) -> None:\n    getattr(persistence, 'foo', None)\n",
    )
    assert typed_getattr_sites(path, ("Thing",)) == [(2, "persistence", "foo")]


def test_finds_getattr_on_optional_union_annotated_parameter(tmp_path: Path) -> None:
    """`persistence: Thing | None` -- the same optional-union form inert's
    own receiver-typing test documents for its own annotated-parameter rule."""
    path = _write(
        tmp_path,
        "def f(persistence: Thing | None = None) -> None:\n    getattr(persistence, 'foo', None)\n",
    )
    assert typed_getattr_sites(path, ("Thing",)) == [(2, "persistence", "foo")]


def test_finds_getattr_on_self_attribute_aliased_from_typed_parameter(tmp_path: Path) -> None:
    """`self._persistence = persistence` -- the exact engine_bridge.py
    `__init__` pattern; without this closure rule every `self._persistence.*`
    call site in that class is invisible to the sentinel."""
    path = _write(
        tmp_path,
        "class C:\n"
        "    def __init__(self, persistence: Thing) -> None:\n"
        "        self._persistence = persistence\n"
        "    def use(self) -> None:\n"
        "        getattr(self._persistence, 'foo', None)\n",
    )
    assert typed_getattr_sites(path, ("Thing",)) == [(5, "self._persistence", "foo")]


def test_ignores_getattr_on_an_untyped_name(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "def f(request) -> None:\n    getattr(request, 'foo', None)\n",
    )
    assert typed_getattr_sites(path, ("Thing",)) == []


def test_ignores_getattr_with_a_computed_attribute_name(tmp_path: Path) -> None:
    """`getattr(x, name_var, None)` -- cannot resolve without value-flow
    analysis, the same documented limitation inert's rule (b) carries for
    string-keyed indirection."""
    path = _write(
        tmp_path,
        "def f(persistence: Thing) -> None:\n"
        "    name = 'foo'\n"
        "    getattr(persistence, name, None)\n",
    )
    assert typed_getattr_sites(path, ("Thing",)) == []


def test_ignores_getattr_on_a_differently_typed_parameter(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "def f(other: OtherThing) -> None:\n    getattr(other, 'foo', None)\n",
    )
    assert typed_getattr_sites(path, ("Thing",)) == []


def test_typed_getattr_check_raises_on_unparseable_source(tmp_path: Path) -> None:
    path = _write(tmp_path, "def (:\n", name="broken.py")
    with pytest.raises(SentinelCheckError):
        typed_getattr_sites(path, ("Thing",))


# ---------------------------------------------------------------------------
# class_members -- efficacy
# ---------------------------------------------------------------------------


def test_class_members_finds_declared_methods(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "class Thing:\n    def foo(self) -> None: ...\n    def bar(self) -> None: ...\n",
    )
    members = class_members(str((tmp_path / "sample.py").resolve()), "Thing")
    assert members == {"foo", "bar"}


def test_class_members_finds_self_attribute_instance_assignment(tmp_path: Path) -> None:
    """`self._pool = pool` inside `__init__` -- the exact PostgresRuntime
    shape -- must be visible as a valid getattr target, not just methods."""
    _write(
        tmp_path,
        "class Thing:\n    def __init__(self, pool) -> None:\n        self._pool = pool\n",
    )
    members = class_members(str((tmp_path / "sample.py").resolve()), "Thing")
    assert members == {"__init__", "_pool"}


def test_class_members_raises_on_missing_class(tmp_path: Path) -> None:
    _write(tmp_path, "class Thing:\n    def foo(self) -> None: ...\n")
    with pytest.raises(SentinelCheckError):
        class_members(str((tmp_path / "sample.py").resolve()), "NotThere")


def test_class_members_raises_on_missing_file() -> None:
    with pytest.raises(SentinelCheckError):
        class_members("does/not/exist.py", "Thing")


# ---------------------------------------------------------------------------
# Regression: injected rows against synthetic + real repo files
# ---------------------------------------------------------------------------


def test_dangling_check_reds_on_a_getattr_naming_no_real_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A synthetic file where the referenced name matches NO watched class
    member -- proves the check reds on a genuine dangling reference."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "backend.py").write_text(
        "class Backend:\n    def real_method(self) -> None: ...\n",
        encoding="utf-8",
    )
    call_dir = tmp_path / "web"
    call_dir.mkdir()
    (call_dir / "caller.py").write_text(
        "def f(persistence: Backend) -> None:\n"
        "    getattr(persistence, 'real_methdo', None)\n",  # transposed typo of a real name
        encoding="utf-8",
    )
    watched_class = WatchedClass(
        name="synthetic_backend", def_file="src/backend.py", class_name="Backend"
    )
    receiver = WatchedReceiver(
        name="synthetic_receiver",
        annotation_names=("Backend",),
        member_classes=("synthetic_backend",),
    )
    monkeypatch.setattr("babylon.sentinels.dangling.checks._REPO_ROOT", tmp_path)
    violations = dangling_references((receiver,), (watched_class,))
    assert len(violations) == 1
    assert "real_methdo" in violations[0]
    assert (
        "real_method" in violations[0]
    )  # nearest-match suggestion fires (not a substring of the typo)


def test_dangling_check_passes_on_a_getattr_naming_a_real_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "backend.py").write_text(
        "class Backend:\n    def real_method(self) -> None: ...\n",
        encoding="utf-8",
    )
    call_dir = tmp_path / "web"
    call_dir.mkdir()
    (call_dir / "caller.py").write_text(
        "def f(persistence: Backend) -> None:\n    getattr(persistence, 'real_method', None)\n",
        encoding="utf-8",
    )
    watched_class = WatchedClass(
        name="synthetic_backend", def_file="src/backend.py", class_name="Backend"
    )
    receiver = WatchedReceiver(
        name="synthetic_receiver",
        annotation_names=("Backend",),
        member_classes=("synthetic_backend",),
    )
    monkeypatch.setattr("babylon.sentinels.dangling.checks._REPO_ROOT", tmp_path)
    violations = dangling_references((receiver,), (watched_class,))
    assert violations == []


def test_exempted_dangling_reference_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "backend.py").write_text(
        "class Backend:\n    def real_method(self) -> None: ...\n",
        encoding="utf-8",
    )
    call_dir = tmp_path / "web"
    call_dir.mkdir()
    (call_dir / "caller.py").write_text(
        "def f(persistence: Backend) -> None:\n"
        "    getattr(persistence, 'this_does_not_exist', None)\n",
        encoding="utf-8",
    )
    watched_class = WatchedClass(
        name="synthetic_backend", def_file="src/backend.py", class_name="Backend"
    )
    receiver = WatchedReceiver(
        name="synthetic_receiver",
        annotation_names=("Backend",),
        member_classes=("synthetic_backend",),
    )
    exemption = SentinelExemption(
        key=("dangling", "synthetic_receiver", "web/caller.py", "this_does_not_exist"),
        reason="test exemption",
        owner="test",
        date="2026-07-18",
        tracking_task="#1",
    )
    monkeypatch.setattr("babylon.sentinels.dangling.checks._REPO_ROOT", tmp_path)
    monkeypatch.setattr("babylon.sentinels.dangling.checks.DANGLING_EXEMPTIONS", (exemption,))
    violations = dangling_references((receiver,), (watched_class,))
    assert violations == []


def test_dangling_check_raises_on_missing_scan_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    watched_class = WatchedClass(
        name="synthetic_backend", def_file="nowhere/backend.py", class_name="Backend"
    )
    receiver = WatchedReceiver(
        name="synthetic_receiver",
        annotation_names=("Backend",),
        member_classes=("synthetic_backend",),
    )
    monkeypatch.setattr("babylon.sentinels.dangling.checks._REPO_ROOT", tmp_path)
    with pytest.raises(SentinelCheckError):
        dangling_references((receiver,), (watched_class,))


# ---------------------------------------------------------------------------
# Registry shape teeth
# ---------------------------------------------------------------------------


def test_watched_class_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        WatchedClass(name="", def_file="a.py", class_name="Thing")


def test_watched_class_rejects_non_py_def_file() -> None:
    with pytest.raises(ValidationError):
        WatchedClass(name="x", def_file="a.txt", class_name="Thing")


def test_watched_receiver_rejects_empty_annotation_names() -> None:
    with pytest.raises(ValidationError):
        WatchedReceiver(name="x", annotation_names=(), member_classes=("y",))


def test_watched_receiver_rejects_empty_member_classes() -> None:
    with pytest.raises(ValidationError):
        WatchedReceiver(name="x", annotation_names=("Thing",), member_classes=())


def test_unknown_member_classes_flags_an_unresolvable_entry() -> None:
    """The cross-reference guard's pure core: a WatchedReceiver naming a
    member_classes entry absent from the given WatchedClass rows must be
    flagged -- proves the real module-level guard (which calls this same
    function against WATCHED_RECEIVERS/WATCHED_CLASSES at import time) would
    catch a typo'd or stale entry rather than silently shrinking the union."""
    from babylon.sentinels.dangling.registry import _unknown_member_classes

    real_class = WatchedClass(name="ok", def_file="a.py", class_name="Thing")
    bad_receiver = WatchedReceiver(
        name="bad", annotation_names=("Thing",), member_classes=("does_not_exist",)
    )
    result = _unknown_member_classes((bad_receiver,), (real_class,))
    assert result == {"bad": ["does_not_exist"]}


def test_unknown_member_classes_empty_when_everything_resolves() -> None:
    from babylon.sentinels.dangling.registry import _unknown_member_classes

    real_class = WatchedClass(name="ok", def_file="a.py", class_name="Thing")
    good_receiver = WatchedReceiver(
        name="good", annotation_names=("Thing",), member_classes=("ok",)
    )
    assert _unknown_member_classes((good_receiver,), (real_class,)) == {}


def test_real_registry_passes_its_own_cross_reference_guard() -> None:
    """The shipped WATCHED_RECEIVERS/WATCHED_CLASSES already passed this
    guard at import time (the module would have failed to import otherwise)
    -- this test just makes that fact independently assertable."""
    from babylon.sentinels.dangling.registry import _unknown_member_classes

    assert _unknown_member_classes(WATCHED_RECEIVERS, WATCHED_CLASSES) == {}


# ---------------------------------------------------------------------------
# Liveness: the real, shipped registry against the current tree
# ---------------------------------------------------------------------------


def test_registry_declares_the_persistence_receiver() -> None:
    names = {row.name for row in WATCHED_RECEIVERS}
    assert "persistence" in names


def test_registry_declares_all_four_persistence_watched_classes() -> None:
    names = {row.name for row in WATCHED_CLASSES}
    assert names == {
        "runtime_persistence_protocol",
        "postgres_runtime_extensions_protocol",
        "postgres_runtime_impl",
        "sqlite_runtime_impl",
    }


def test_founding_specimen_is_still_live_and_named_exactly() -> None:
    """LIVENESS: as of this writing (before task #43's parallel fix lane
    lands on this branch), engine_bridge.py:10990 is still the SINGULAR
    `persist_action_result` -- the gate must name exactly this site. If this
    ever starts passing spuriously without the fix landing, the gate is
    broken; if the fix lands and this starts failing, update/remove this
    test as part of that same change (it is pinning a KNOWN, tracked defect,
    not asserting desired end-state)."""
    violations = dangling_references()
    assert len(violations) == 1
    assert "web/game/engine_bridge.py:10990" in violations[0]
    assert "persist_action_result" in violations[0]
    assert "persist_action_results" in violations[0]  # nearest-match names the real target


def test_class_members_matches_real_postgres_runtime_shape() -> None:
    """POSITIVE control: PostgresRuntime really does declare the plural
    method and NOT the singular -- pins the real-world fact this whole
    sentinel is built to enforce, independent of engine_bridge.py's state."""
    members = class_members(
        "src/babylon/persistence/postgres_runtime/_legacy.py", "PostgresRuntime"
    )
    assert "persist_action_results" in members
    assert "persist_action_result" not in members


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_entry_point_reds_on_the_live_specimen() -> None:
    """`sentinel_check.py dangling --check` currently exits 1 -- the founding
    specimen (engine_bridge.py:10990) is still live on this branch. Once
    task #43's fix lands, this assertion flips to 0/clean as part of that
    same change (see test_founding_specimen_is_still_live_and_named_exactly
    for the paired liveness pin)."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "dangling", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, (
        "expected the DANGLING sensor to red on the live specimen:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "persist_action_result" in result.stderr
