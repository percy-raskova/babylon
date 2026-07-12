"""Contract tests for :func:`babylon.engine.headless_runner.runner._resolve_defines`.

These pin the plumbing fix at the heart of the optimization-package work: before
the fix, ``run()`` called ``GameDefines.load_default()`` unconditionally and silently
discarded any caller-supplied coefficients, so every parameter-sweep trial executed
bit-identical math (Constitution III.11 — a silent Loud-Failure violation). The
resolver makes an injected ``GameDefines`` actually reach the simulation while keeping
the no-override default path byte-identical (so ``qa:regression`` is unaffected).

The full end-to-end "injecting a coefficient changes the outcome" proof lives in the
integration suite (it needs Postgres); this module pins the resolution *contract*
cheaply and deterministically.
"""

from __future__ import annotations

from pathlib import Path

from babylon.config.defines import GameDefines
from babylon.engine.headless_runner.models import SimulationRunConfig
from babylon.engine.headless_runner.runner import _resolve_defines

_SCOPE = frozenset({"26163"})


def _config(**overrides: object) -> SimulationRunConfig:
    """Build a minimal ``SimulationRunConfig`` for resolver tests."""
    base: dict[str, object] = {"scope_fips": _SCOPE, "output_dir": Path("/tmp/opt-test")}
    base.update(overrides)
    return SimulationRunConfig(**base)  # type: ignore[arg-type]


def test_injected_defines_is_used_verbatim() -> None:
    """An in-process ``config.defines`` is returned unchanged (highest precedence)."""
    injected = GameDefines.load_default()
    resolved = _resolve_defines(_config(defines=injected))
    assert resolved is injected


def test_no_override_matches_load_default() -> None:
    """With no override the resolver reproduces ``load_default`` (byte-identical path)."""
    resolved = _resolve_defines(_config())
    assert _resolve_defines(_config()).model_dump() == resolved.model_dump()
    assert resolved.model_dump() == GameDefines.load_default().model_dump()


def test_overlay_path_is_loaded_and_merged(tmp_path: Path) -> None:
    """A YAML overlay path is loaded when no in-process object is supplied."""
    overlay = tmp_path / "overlay.yaml"
    overlay.write_text("economy:\n  extraction_efficiency: 0.5\n", encoding="utf-8")
    resolved = _resolve_defines(_config(defines_overlay_path=overlay))
    assert resolved.economy.extraction_efficiency == 0.5


def test_in_process_defines_wins_over_overlay_path(tmp_path: Path) -> None:
    """``config.defines`` takes precedence over ``defines_overlay_path``."""
    overlay = tmp_path / "overlay.yaml"
    overlay.write_text("economy:\n  extraction_efficiency: 0.5\n", encoding="utf-8")
    injected = GameDefines.load_default()
    resolved = _resolve_defines(_config(defines=injected, defines_overlay_path=overlay))
    assert resolved is injected


def test_defines_is_excluded_from_manifest_dump() -> None:
    """The injected object must not bloat the serialized manifest/config dump."""
    cfg = _config(defines=GameDefines.load_default())
    assert "defines" not in cfg.model_dump()
