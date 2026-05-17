"""Unit test for canonical stderr error-message format (T020c, spec-064 FR-020).

For every non-zero exit code in ``contracts/cli_contract.yaml``, the
runner MUST emit exactly one stderr line matching::

    ERROR <NAME>: <message> | partial_artifacts=<NONE|absolute-path>
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pytest

from babylon.engine.headless_runner import runner as runner_mod

CANONICAL_RE = re.compile(
    r"^ERROR [A-Z_]+: .+ \| partial_artifacts=(NONE|/.*)$",
)


def _capture_emit(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    return buf


class TestCanonicalErrorFormat:
    """The four documented exit codes all produce conforming stderr lines."""

    def test_config_error_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        buf = _capture_emit(monkeypatch)
        runner_mod._emit_error("CONFIG_ERROR", "Unknown scope 'foo'", partial=None)
        line = buf.getvalue().rstrip("\n")
        assert CANONICAL_RE.match(line), f"format violation: {line!r}"
        assert line.endswith("partial_artifacts=NONE")

    def test_reference_data_missing_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        buf = _capture_emit(monkeypatch)
        runner_mod._emit_error(
            "REFERENCE_DATA_MISSING",
            "SQLite reference DB not found at data/sqlite/marxist-data-3NF.sqlite",
            partial=None,
        )
        line = buf.getvalue().rstrip("\n")
        assert CANONICAL_RE.match(line)
        assert "SQLite reference DB" in line

    def test_postgres_unreachable_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        buf = _capture_emit(monkeypatch)
        runner_mod._emit_error(
            "POSTGRES_UNREACHABLE",
            "Connection pool failed to open (port 5433)",
            partial=None,
        )
        line = buf.getvalue().rstrip("\n")
        assert CANONICAL_RE.match(line)

    def test_engine_failure_with_partial_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        partial = tmp_path / "out"
        partial.mkdir()
        buf = _capture_emit(monkeypatch)
        runner_mod._emit_error(
            "ENGINE_FAILURE",
            "ValueError at tick 247",
            partial=partial,
        )
        line = buf.getvalue().rstrip("\n")
        assert CANONICAL_RE.match(line)
        assert str(partial.resolve()) in line

    def test_user_interrupted_with_partial_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        partial = tmp_path / "interrupted"
        partial.mkdir()
        buf = _capture_emit(monkeypatch)
        runner_mod._emit_error(
            "USER_INTERRUPTED",
            "SIGINT received at tick 412",
            partial=partial,
        )
        line = buf.getvalue().rstrip("\n")
        assert CANONICAL_RE.match(line)
        assert "partial_artifacts=/" in line
