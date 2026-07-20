"""Tests for the defines-passthrough sentinel (task #42 fix wave 1, review MEDIUM-1).

Mirrors ``test_dangling.py``'s three-tier shape:

- **Efficacy** (AST-helper level, tmp_path fixtures) — the two new
  :mod:`babylon.sentinels._ast` extractors correctly SEE each syntactic form
  of "defines supplied" (keyword, correctly-positioned positional, a
  ``**kwargs`` unpack) and correctly MISS the omitted form, and correctly
  distinguish an OPTIONAL ``defines`` parameter (has a default) from a
  REQUIRED one (no default — out of this sentinel's scope by construction)
  or an absent one.
- **Regression** (injected registry rows against synthetic files) — proves
  the gating check function actually reds on a genuinely-omitted
  ``defines=`` and stays clean on a genuinely-passed one, independent of the
  live registry's current temporal state.
- **Liveness** (the real, shipped registry) — the founding specimens
  (``ideology.py``'s ``route_agitation_to_ternary``/
  ``compute_exploitation_visibility``, and ``sovereignty.py``'s
  ``calculate_metabolic_impact``) were all fixed in the SAME fix wave that
  landed this sentinel, so the liveness test asserts the gate is CLEAN
  against the real tree — proving the sentinel actually functions rather
  than only against synthetic fixtures.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.sentinels._ast import (
    calls_missing_keyword_or_positional_arg,
    optional_defines_param_index,
)
from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.defines_passthrough.checks import (
    is_test_source,
    missing_defines_passthrough,
)
from babylon.sentinels.defines_passthrough.registry import (
    WATCHED_FUNCTIONS,
    WatchedFunction,
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
# is_test_source (mirrors dangling's own — verbatim behavior parity)
# ---------------------------------------------------------------------------


def test_is_test_source_matches_conftest(tmp_path: Path) -> None:
    assert is_test_source(tmp_path / "conftest.py")


def test_is_test_source_matches_nested_tests_directory() -> None:
    assert is_test_source(Path("tests/unit/engine/systems/test_ideology.py"))


def test_is_test_source_false_for_ordinary_module() -> None:
    assert not is_test_source(Path("src/babylon/engine/systems/ideology.py"))


# ---------------------------------------------------------------------------
# optional_defines_param_index -- efficacy
# ---------------------------------------------------------------------------


def test_finds_index_of_an_optional_defines_parameter(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "def f(x: float, defines: Thing | None = None) -> float:\n    return x\n",
    )
    assert optional_defines_param_index(path, "f") == 1


def test_returns_none_for_a_required_defines_parameter(tmp_path: Path) -> None:
    """A required `defines` (no default) cannot be silently omitted -- out
    of scope by construction, not a bug this sentinel should chase."""
    path = _write(
        tmp_path,
        "def f(x: float, defines: Thing) -> float:\n    return x\n",
    )
    assert optional_defines_param_index(path, "f") is None


def test_returns_none_when_function_declares_no_defines_parameter(tmp_path: Path) -> None:
    path = _write(tmp_path, "def f(x: float) -> float:\n    return x\n")
    assert optional_defines_param_index(path, "f") is None


def test_returns_none_when_function_is_absent(tmp_path: Path) -> None:
    path = _write(tmp_path, "def other() -> None:\n    pass\n")
    assert optional_defines_param_index(path, "f") is None


def test_optional_defines_param_index_raises_on_unparseable_source(tmp_path: Path) -> None:
    path = _write(tmp_path, "def (:\n", name="broken.py")
    with pytest.raises(SentinelCheckError):
        optional_defines_param_index(path, "f")


# ---------------------------------------------------------------------------
# calls_missing_keyword_or_positional_arg -- efficacy
# ---------------------------------------------------------------------------


def test_call_supplying_the_keyword_is_not_a_miss(tmp_path: Path) -> None:
    path = _write(tmp_path, "f(1, defines=my_defines)\n")
    assert calls_missing_keyword_or_positional_arg(path, "f", "defines", 1) == []


def test_call_supplying_it_positionally_is_not_a_miss(tmp_path: Path) -> None:
    path = _write(tmp_path, "f(1, my_defines)\n")
    assert calls_missing_keyword_or_positional_arg(path, "f", "defines", 1) == []


def test_call_with_kwargs_unpack_is_not_a_miss(tmp_path: Path) -> None:
    """Cannot resolve whether **kwargs supplies it without value-flow
    analysis -- honest absence, never a false positive."""
    path = _write(tmp_path, "f(1, **overrides)\n")
    assert calls_missing_keyword_or_positional_arg(path, "f", "defines", 1) == []


def test_call_omitting_it_entirely_is_a_miss(tmp_path: Path) -> None:
    path = _write(tmp_path, "f(1)\n")
    assert calls_missing_keyword_or_positional_arg(path, "f", "defines", 1) == [1]


def test_attribute_call_form_is_recognized(tmp_path: Path) -> None:
    path = _write(tmp_path, "module.f(1)\n")
    assert calls_missing_keyword_or_positional_arg(path, "f", "defines", 1) == [1]


def test_differently_named_call_is_ignored(tmp_path: Path) -> None:
    path = _write(tmp_path, "other_func(1)\n")
    assert calls_missing_keyword_or_positional_arg(path, "f", "defines", 1) == []


def test_calls_missing_kwarg_raises_on_unparseable_source(tmp_path: Path) -> None:
    path = _write(tmp_path, "def (:\n", name="broken.py")
    with pytest.raises(SentinelCheckError):
        calls_missing_keyword_or_positional_arg(path, "f", "defines", 1)


# ---------------------------------------------------------------------------
# Regression: injected rows against synthetic + real repo files
# ---------------------------------------------------------------------------


def test_check_reds_on_a_call_omitting_defines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    formulas_dir = tmp_path / "src" / "babylon" / "formulas"
    formulas_dir.mkdir(parents=True)
    (formulas_dir / "mymath.py").write_text(
        "def compute(x: float, defines: object | None = None) -> float:\n    return x\n",
        encoding="utf-8",
    )
    call_dir = tmp_path / "src" / "babylon" / "engine"
    call_dir.mkdir(parents=True)
    (call_dir / "caller.py").write_text(
        "from babylon.formulas.mymath import compute\ncompute(1.0)\n",
        encoding="utf-8",
    )
    row = WatchedFunction(
        name="compute", def_file="src/babylon/formulas/mymath.py", func_name="compute"
    )
    monkeypatch.setattr("babylon.sentinels.defines_passthrough.checks._REPO_ROOT", tmp_path)
    violations = missing_defines_passthrough((row,))
    assert len(violations) == 1
    assert "compute" in violations[0]
    assert "src/babylon/engine/caller.py:2" in violations[0]


def test_check_passes_on_a_call_supplying_defines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    formulas_dir = tmp_path / "src" / "babylon" / "formulas"
    formulas_dir.mkdir(parents=True)
    (formulas_dir / "mymath.py").write_text(
        "def compute(x: float, defines: object | None = None) -> float:\n    return x\n",
        encoding="utf-8",
    )
    call_dir = tmp_path / "src" / "babylon" / "engine"
    call_dir.mkdir(parents=True)
    (call_dir / "caller.py").write_text(
        "from babylon.formulas.mymath import compute\ncompute(1.0, defines=my_defines)\n",
        encoding="utf-8",
    )
    row = WatchedFunction(
        name="compute", def_file="src/babylon/formulas/mymath.py", func_name="compute"
    )
    monkeypatch.setattr("babylon.sentinels.defines_passthrough.checks._REPO_ROOT", tmp_path)
    assert missing_defines_passthrough((row,)) == []


def test_check_ignores_the_formulas_directory_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The declaration site is not a call site -- scanning it should never
    manufacture a false positive off the function's own `def`."""
    formulas_dir = tmp_path / "src" / "babylon" / "formulas"
    formulas_dir.mkdir(parents=True)
    (formulas_dir / "mymath.py").write_text(
        "def compute(x: float, defines: object | None = None) -> float:\n    return x\n",
        encoding="utf-8",
    )
    row = WatchedFunction(
        name="compute", def_file="src/babylon/formulas/mymath.py", func_name="compute"
    )
    monkeypatch.setattr("babylon.sentinels.defines_passthrough.checks._REPO_ROOT", tmp_path)
    assert missing_defines_passthrough((row,)) == []


def test_check_excludes_test_files_from_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    formulas_dir = tmp_path / "src" / "babylon" / "formulas"
    formulas_dir.mkdir(parents=True)
    (formulas_dir / "mymath.py").write_text(
        "def compute(x: float, defines: object | None = None) -> float:\n    return x\n",
        encoding="utf-8",
    )
    call_dir = tmp_path / "src" / "babylon" / "engine"
    call_dir.mkdir(parents=True)
    (call_dir / "test_caller.py").write_text("compute(1.0)\n", encoding="utf-8")
    row = WatchedFunction(
        name="compute", def_file="src/babylon/formulas/mymath.py", func_name="compute"
    )
    monkeypatch.setattr("babylon.sentinels.defines_passthrough.checks._REPO_ROOT", tmp_path)
    assert missing_defines_passthrough((row,)) == []


def test_exempted_call_site_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    formulas_dir = tmp_path / "src" / "babylon" / "formulas"
    formulas_dir.mkdir(parents=True)
    (formulas_dir / "mymath.py").write_text(
        "def compute(x: float, defines: object | None = None) -> float:\n    return x\n",
        encoding="utf-8",
    )
    call_dir = tmp_path / "src" / "babylon" / "models"
    call_dir.mkdir(parents=True)
    (call_dir / "caller.py").write_text("compute(1.0)\n", encoding="utf-8")
    row = WatchedFunction(
        name="compute", def_file="src/babylon/formulas/mymath.py", func_name="compute"
    )
    exemption = SentinelExemption(
        key=("defines_passthrough", "src/babylon/models/caller.py", "compute"),
        reason="test exemption",
        owner="test",
        date="2026-07-20",
        tracking_task="#42",
    )
    monkeypatch.setattr("babylon.sentinels.defines_passthrough.checks._REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        "babylon.sentinels.defines_passthrough.checks.DEFINES_PASSTHROUGH_EXEMPTIONS",
        (exemption,),
    )
    assert missing_defines_passthrough((row,)) == []


def test_check_raises_on_a_row_whose_def_file_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A WatchedFunction row naming a def_file that doesn't exist is an
    infrastructure failure (exit 2), never a silent "no violations found"
    (mirrors test_dangling.py's identical missing-watched-file teeth)."""
    row = WatchedFunction(
        name="compute",
        def_file="src/babylon/formulas/does_not_exist.py",
        func_name="compute",
    )
    monkeypatch.setattr("babylon.sentinels.defines_passthrough.checks._REPO_ROOT", tmp_path)
    with pytest.raises(SentinelCheckError):
        missing_defines_passthrough((row,))


def test_check_raises_on_missing_scan_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing PRODUCTION_ROOTS directory is an infrastructure failure too
    -- tests `_production_files` directly (bypassing the module-level
    default binding a monkeypatch of the PRODUCTION_ROOTS *name* cannot
    reach, since the function's default argument value was already bound at
    import time)."""
    from babylon.sentinels.defines_passthrough.checks import _production_files

    monkeypatch.setattr("babylon.sentinels.defines_passthrough.checks._REPO_ROOT", tmp_path)
    with pytest.raises(SentinelCheckError):
        list(_production_files(("nowhere",)))


def test_check_raises_on_a_row_whose_function_no_longer_has_optional_defines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Registry drift teeth: if a watched function's signature changes so
    `defines` becomes required (or is removed), the check must fail LOUD
    (exit 2), never silently shrink to "no violations found"."""
    formulas_dir = tmp_path / "src" / "babylon" / "formulas"
    formulas_dir.mkdir(parents=True)
    (formulas_dir / "mymath.py").write_text(
        "def compute(x: float, defines: object) -> float:\n    return x\n",  # required now
        encoding="utf-8",
    )
    row = WatchedFunction(
        name="compute", def_file="src/babylon/formulas/mymath.py", func_name="compute"
    )
    monkeypatch.setattr("babylon.sentinels.defines_passthrough.checks._REPO_ROOT", tmp_path)
    with pytest.raises(SentinelCheckError):
        missing_defines_passthrough((row,))


# ---------------------------------------------------------------------------
# Registry shape teeth
# ---------------------------------------------------------------------------


def test_watched_function_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        WatchedFunction(name="", def_file="a.py", func_name="f")


def test_watched_function_rejects_blank_func_name() -> None:
    with pytest.raises(ValidationError):
        WatchedFunction(name="x", def_file="a.py", func_name="")


def test_watched_function_rejects_non_py_def_file() -> None:
    with pytest.raises(ValidationError):
        WatchedFunction(name="x", def_file="a.txt", func_name="f")


# ---------------------------------------------------------------------------
# Liveness: the real, shipped registry against the current tree
# ---------------------------------------------------------------------------


def test_registry_declares_all_seven_watched_functions() -> None:
    names = {row.name for row in WATCHED_FUNCTIONS}
    assert names == {
        "compute_agitation_delta",
        "compute_exploitation_visibility",
        "route_agitation_to_ternary",
        "calculate_metabolic_impact",
        "derive_default_multipliers_from_stance",
        "detect_red_settler_trap",
        "contiguous_influence_majority_subregion",
    }


def test_live_tree_is_clean() -> None:
    """Task #42 fix wave 1: ideology.py's two sibling call sites and
    sovereignty.py's calculate_metabolic_impact call were all fixed to pass
    defines= in the same integration that lands this sentinel; sovereign.py's
    computed_field is the one recorded architectural exemption. The red
    capability itself stays covered by the synthetic-fixture tests above;
    THIS pins the desired end-state: no watched call in production omits
    defines=."""
    assert missing_defines_passthrough() == []


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_entry_point_clean_on_live_tree() -> None:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "defines_passthrough", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "expected the DEFINES_PASSTHROUGH sensor to be clean on the integrated tree:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "DEFINES_PASSTHROUGH clean" in result.stdout
