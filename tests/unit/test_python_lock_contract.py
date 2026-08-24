"""Python lockfile contracts for a clean Babylon archive."""

from __future__ import annotations

import io
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

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


def test_pinned_uv_validates_an_isolated_archive_without_a_hypergraph_sibling() -> None:
    """A clean archive resolves its committed lock without a local sibling checkout."""
    ref = os.environ.get("BABYLON_LOCK_CONTRACT_REF", "HEAD")
    with tempfile.TemporaryDirectory() as temporary_directory:
        archive_root = Path(temporary_directory) / "babylon"
        archive_root.mkdir()
        _extract_archive(ref, archive_root)
        assert not (archive_root.parent / "hypergraph-rs").exists()
        result = subprocess.run(  # noqa: S603
            [_pinned_uv(), "lock", "--check"],  # noqa: S607
            cwd=archive_root,
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0, result.stderr
