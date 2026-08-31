"""Contracts for the Rust-runtime parameter trace wrapper."""

from __future__ import annotations

import importlib.util
import inspect
import subprocess
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PARAMETER_ANALYSIS_PATH = PROJECT_ROOT / "tools" / "parameter_analysis.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("parameter_analysis", PARAMETER_ANALYSIS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_trace_surface_is_bounded_to_ticks() -> None:
    module = _load_module()

    assert list(inspect.signature(module.run_trace).parameters) == ["max_ticks"]
    assert callable(module.main)


def test_run_trace_delegates_to_the_rust_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert kwargs == {"check": True, "capture_output": True, "text": True}
        return subprocess.CompletedProcess(command, 0, stdout="/tmp/babylon-trace.jsonl\n")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.run_trace(max_ticks=7) == Path("/tmp/babylon-trace.jsonl")
    assert calls == [["babylon-runtime", "run", "--ticks", "7"]]


def test_cli_exposes_ticks_without_python_parameter_injection() -> None:
    source = PARAMETER_ANALYSIS_PATH.read_text(encoding="utf-8")

    assert 'parser.add_argument("--ticks"' in source
    assert "--param" not in source
    assert "--csv" not in source
    assert "headless_runner" not in source
