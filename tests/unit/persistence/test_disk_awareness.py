"""Disk preflight + mid-run soft warning (ADR176 ruling 32).

Pure-unit: ``shutil.disk_usage`` is monkeypatched; no Postgres, no real
filesystem pressure. The law: boot ABORTS below the preflight budget with
a player-actionable message; during play the session raises a soft,
non-blocking warning at checkpoint cadence; disk state NEVER enters any
deterministic surface (an attribute and a log line, not an event).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from babylon.persistence import retention
from babylon.persistence.retention import (
    DiskPreflightError,
    check_disk_preflight,
    disk_warning_message,
)

_USAGE = shutil.disk_usage(".").__class__  # the named tuple type


def _patch_free(monkeypatch: pytest.MonkeyPatch, free: int) -> None:
    monkeypatch.setattr(
        retention.shutil,
        "disk_usage",
        lambda _path: _USAGE(total=100 * 1024**3, used=0, free=free),
    )


class TestPreflight:
    def test_below_budget_aborts_with_actionable_message(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _patch_free(monkeypatch, free=1 * 1024**3)
        with pytest.raises(DiskPreflightError) as exc_info:
            check_disk_preflight(tmp_path, required_bytes=10 * 1024**3)
        message = str(exc_info.value)
        assert str(tmp_path) in message
        assert "10.0 GiB" in message  # what the player must free up to
        assert "1.0 GiB" in message  # what they actually have

    def test_at_or_above_budget_passes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _patch_free(monkeypatch, free=10 * 1024**3)
        check_disk_preflight(tmp_path, required_bytes=10 * 1024**3)

    def test_zero_budget_disables_the_check(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The modding escape hatch: 0 means never probe, never raise."""

        def _explode(path: object) -> None:
            raise AssertionError("disk_usage must not be called when disabled")

        monkeypatch.setattr(retention.shutil, "disk_usage", _explode)
        check_disk_preflight(tmp_path, required_bytes=0)


class TestSoftWarning:
    def test_below_floor_yields_a_player_message(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _patch_free(monkeypatch, free=512 * 1024**2)
        message = disk_warning_message(tmp_path, floor_bytes=2 * 1024**3)
        assert message is not None
        assert "0.5 GiB" in message
        assert "free" in message.lower()

    def test_at_or_above_floor_is_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _patch_free(monkeypatch, free=2 * 1024**3)
        assert disk_warning_message(tmp_path, floor_bytes=2 * 1024**3) is None

    def test_zero_floor_disables_the_warning(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        def _explode(path: object) -> None:
            raise AssertionError("disk_usage must not be called when disabled")

        monkeypatch.setattr(retention.shutil, "disk_usage", _explode)
        assert disk_warning_message(tmp_path, floor_bytes=0) is None
