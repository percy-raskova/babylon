"""Tests for VaultMaterializer.bake_briefing (WO-35).

Mirrors ``test_materializer.py``'s ``TestBakeCounty`` contract for the
briefing dossier: exact path, byte-identical double-bake, identical commit
SHAs across two independent vault roots.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from babylon.config.defines import GameDefines
from babylon.projection.briefing import BriefingView, project_briefing
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.render_briefing import render_briefing

_SESSION = UUID("12345678-1234-5678-1234-567812345678")


def _view() -> BriefingView:
    return project_briefing(_SESSION, tick=0, defines=GameDefines())


class TestBakeBriefing:
    def test_it_writes_exactly_session_id_md_and_returns_its_path(self, tmp_path: Path) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_briefing(_view(), tick=0)

        assert page_path == tmp_path / "vault" / "briefing" / f"{_SESSION}.md"
        assert page_path.is_file()
        written_files = sorted(
            p.relative_to(tmp_path / "vault") for p in (tmp_path / "vault").rglob("*.md")
        )
        assert written_files == [Path(f"briefing/{_SESSION}.md")]

    def test_the_written_page_matches_render_briefing_output(self, tmp_path: Path) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        view = _view()
        page_path = materializer.bake_briefing(view, tick=0)

        assert page_path.read_text(encoding="utf8") == render_briefing(view)

    def test_two_independent_bakes_of_the_same_view_are_byte_identical(
        self, tmp_path: Path
    ) -> None:
        view = _view()
        materializer_a = VaultMaterializer(tmp_path / "vault_a")
        page_a = materializer_a.bake_briefing(view, tick=0)

        materializer_b = VaultMaterializer(tmp_path / "vault_b")
        page_b = materializer_b.bake_briefing(view, tick=0)

        assert page_a.read_text(encoding="utf8") == page_b.read_text(encoding="utf8")

    def test_two_independent_bakes_of_the_same_view_produce_identical_commit_shas(
        self, tmp_path: Path
    ) -> None:
        view = _view()

        def bake(root: Path) -> bytes:
            materializer = VaultMaterializer(root)
            materializer.bake_briefing(view, tick=0)
            from dulwich.repo import Repo

            repo = Repo(str(root))
            try:
                return repo.head()
            finally:
                repo.close()

        sha_a = bake(tmp_path / "vault_a")
        sha_b = bake(tmp_path / "vault_b")
        assert sha_a == sha_b
