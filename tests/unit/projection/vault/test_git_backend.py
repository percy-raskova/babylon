"""Tests for babylon.projection.vault.git_backend: sim-time-pinned dulwich commits."""

from __future__ import annotations

from pathlib import Path

from babylon.projection.vault.git_backend import commit_page, init_vault

_PAGE = "# Wayne County — Dossier\nverified_tick: 42\n"


def _build_vault(root: Path) -> bytes:
    init_vault(root)
    return commit_page(
        root,
        "county/26163.md",
        _PAGE,
        tick=42,
        message="bake: county/26163 @ tick 42",
    )


class TestInitVault:
    def test_it_creates_a_git_repository_at_root(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        init_vault(root)
        assert (root / ".git").exists()

    def test_it_is_idempotent_against_an_already_initialized_root(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        init_vault(root)
        init_vault(root)  # must not raise
        assert (root / ".git").exists()


class TestCommitPage:
    def test_it_writes_the_page_content_verbatim(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        init_vault(root)
        commit_page(root, "county/26163.md", _PAGE, tick=42, message="bake: tick 42")
        assert (root / "county" / "26163.md").read_text(encoding="utf8") == _PAGE

    def test_two_independent_bakes_at_the_same_tick_are_byte_identical_commits(
        self, tmp_path: Path
    ) -> None:
        sha_a = _build_vault(tmp_path / "vault_a")
        sha_b = _build_vault(tmp_path / "vault_b")
        assert sha_a == sha_b

    def test_a_different_tick_yields_a_different_commit_sha(self, tmp_path: Path) -> None:
        """Isolate the timestamp's effect: identical content and message,
        only the tick (and thus the sim-time commit timestamp) differs."""
        root_a = tmp_path / "vault_a"
        init_vault(root_a)
        sha_tick_1 = commit_page(root_a, "county/26163.md", _PAGE, tick=1, message="bake: tick N")

        root_b = tmp_path / "vault_b"
        init_vault(root_b)
        sha_tick_2 = commit_page(root_b, "county/26163.md", _PAGE, tick=2, message="bake: tick N")

        assert sha_tick_1 != sha_tick_2
