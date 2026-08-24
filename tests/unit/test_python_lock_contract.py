"""Python lockfile contracts for a clean Babylon archive."""

from __future__ import annotations

import io
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _archive_member(member: tarfile.TarInfo, destination: str) -> tarfile.TarInfo | None:
    """Exclude the repository's external data symlink from a portable archive."""
    if member.issym() and Path(member.linkname).is_absolute():
        return None
    return tarfile.data_filter(member, destination)


def _extract_archive(ref: str, destination: Path) -> None:
    """Extract one Git revision without copying untracked sibling directories."""
    archive = subprocess.run(  # noqa: S603
        ["git", "archive", "--format=tar", ref],  # noqa: S607
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=True,
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(destination, filter=_archive_member)  # noqa: S202 -- filtered archive


def _pinned_uv() -> str:
    """Return the repository-managed uv binary before entering the archive."""
    result = subprocess.run(  # noqa: S603
        ["mise", "which", "uv"],  # noqa: S607
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _run_archive_lock_check(ref: str) -> subprocess.CompletedProcess[str]:
    """Run the pinned lock check against an isolated archive of ``ref``."""
    with tempfile.TemporaryDirectory() as temporary_directory:
        archive_root = Path(temporary_directory) / "babylon"
        archive_root.mkdir()
        _extract_archive(ref, archive_root)
        assert not (archive_root.parent / "hypergraph-rs").exists()
        lock_environment = os.environ.copy()
        lock_environment.pop("UV_FROZEN", None)
        result = subprocess.run(  # noqa: S603
            [_pinned_uv(), "lock", "--check"],  # noqa: S607
            cwd=archive_root,
            capture_output=True,
            text=True,
            check=False,
            env=lock_environment,
        )
    return result


def test_pinned_uv_validates_an_isolated_archive_without_a_hypergraph_sibling() -> None:
    """A clean archive resolves its committed lock without a local sibling checkout."""
    ref = os.environ.get("BABYLON_LOCK_CONTRACT_REF", "HEAD")
    result = _run_archive_lock_check(ref)

    assert result.returncode == 0, result.stderr


def test_archive_lock_check_unsets_uv_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The archive check must not inherit the caller's incompatible lock mode."""
    captured_environment = tmp_path / "uv-frozen.txt"
    probe_uv = tmp_path / "uv-probe"
    probe_uv.write_text('#!/bin/sh\nprintf \'%s\' "${UV_FROZEN-absent}" > "$UV_FROZEN_CAPTURE"\n')
    probe_uv.chmod(0o755)
    monkeypatch.setenv("UV_FROZEN", "1")
    monkeypatch.setenv("UV_FROZEN_CAPTURE", str(captured_environment))
    monkeypatch.setattr(__name__ + "._pinned_uv", lambda: str(probe_uv))

    result = _run_archive_lock_check("HEAD")

    assert result.returncode == 0, result.stderr
    assert captured_environment.read_text() == "absent"
