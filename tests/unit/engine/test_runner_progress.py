"""Unit test for tqdm TTY auto-suppression (T020a, spec-064 FR-012a / SC-007).

When stderr is not a TTY (CI, piped output, tests), the tqdm progress
bar MUST emit zero bytes — both ``ETA: ...`` and the ``\\r`` carriage-
return spam. We assert by redirecting stderr to a ``StringIO`` buffer
and instantiating the tick-iterator with the same arguments the runner
uses.
"""

from __future__ import annotations

import io
import sys
from typing import Any

import pytest


def _make_tqdm_iterator(stderr_stream: Any) -> Any:
    """Mimic ``_tick_loop`` iterator construction (research R2 pattern)."""
    from tqdm import tqdm

    return tqdm(
        range(50),
        desc="ticks",
        file=stderr_stream,
        disable=not stderr_stream.isatty(),
        mininterval=1.0,
        unit="tick",
    )


def test_tqdm_suppressed_when_stderr_is_not_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    """stdout/stderr StringIO buffers are NOT TTYs → tqdm emits nothing."""
    fake_stderr = io.StringIO()
    # StringIO.isatty() returns False by default → disable=True path.
    iterator = _make_tqdm_iterator(fake_stderr)
    consumed = list(iterator)
    assert len(consumed) == 50
    assert fake_stderr.getvalue() == ""


def test_tqdm_imports_when_present() -> None:
    """tqdm is a hard dep per T001; importing it must succeed."""
    import tqdm  # noqa: F401


def test_runner_module_imports_without_postgres() -> None:
    """Importing :mod:`babylon.engine.headless_runner.runner` MUST NOT
    open Postgres; the connection only happens inside :func:`run`."""
    sys.modules.pop("babylon.engine.headless_runner.runner", None)
    import babylon.engine.headless_runner.runner as runner_mod

    assert callable(runner_mod.run)
    assert callable(runner_mod.main_from_argv)
