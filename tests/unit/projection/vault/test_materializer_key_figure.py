"""Tests for VaultMaterializer.bake_key_figure — the honest-absence key-figure page.

Kept as its own file rather than appended to the shared ``test_materializer.py``
(which every Lane P work order would otherwise collide on in parallel
worktrees) — mirrors the same parallel-safety reasoning as
``render_key_figure.py`` living in its own module.
"""

from __future__ import annotations

from pathlib import Path

from babylon.projection.vault.git_backend import commit_page, init_vault
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.render_key_figure import render_key_figure
from babylon.projection.view_models import KeyFigureView


def _view() -> KeyFigureView:
    return KeyFigureView(key_figure_id="kf-001", verified_tick=500)


class TestBakeKeyFigure:
    def test_it_writes_exactly_key_figure_id_md_and_returns_its_path(self, tmp_path: Path) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_key_figure(_view(), tick=500)

        assert page_path == tmp_path / "vault" / "key_figure" / "kf-001.md"
        assert page_path.is_file()
        written_files = sorted(
            p.relative_to(tmp_path / "vault") for p in (tmp_path / "vault").rglob("*.md")
        )
        assert written_files == [Path("key_figure/kf-001.md")]

    def test_the_written_page_matches_render_key_figure_output(self, tmp_path: Path) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_key_figure(_view(), tick=500)

        assert page_path.read_text(encoding="utf8") == render_key_figure(_view(), verified_tick=500)

    def test_two_independent_bakes_of_the_same_view_are_byte_identical(
        self, tmp_path: Path
    ) -> None:
        materializer_a = VaultMaterializer(tmp_path / "vault_a")
        page_a = materializer_a.bake_key_figure(_view(), tick=500)

        materializer_b = VaultMaterializer(tmp_path / "vault_b")
        page_b = materializer_b.bake_key_figure(_view(), tick=500)

        assert page_a.read_text(encoding="utf8") == page_b.read_text(encoding="utf8")

    def test_two_independent_bakes_of_the_same_view_produce_identical_commit_shas(
        self, tmp_path: Path
    ) -> None:
        def bake(root: Path) -> bytes:
            materializer = VaultMaterializer(root)
            materializer.bake_key_figure(_view(), tick=500)
            from dulwich.repo import Repo

            repo = Repo(str(root))
            try:
                return repo.head()
            finally:
                repo.close()

        sha_a = bake(tmp_path / "vault_a")
        sha_b = bake(tmp_path / "vault_b")
        assert sha_a == sha_b

    def test_it_accepts_an_already_initialized_vault_root(self, tmp_path: Path) -> None:
        """A vault root initialized before construction (e.g. by an earlier
        process) is reused, not re-initialized or rejected."""
        root = tmp_path / "vault"
        init_vault(root)
        commit_page(root, "README.md", "# vault\n", tick=0, message="init: vault root")

        materializer = VaultMaterializer(root)
        page_path = materializer.bake_key_figure(_view(), tick=500)
        assert page_path.is_file()
