"""Tests for VaultMaterializer.bake_community (WO-24).

Trimmed mirror of ``test_materializer.py``'s ``TestBakeCounty`` — covers the
write-path contract (stable-ID slug, byte-identical double bake, byte-
identical commit SHA across two independent vault roots) without repeating
that file's git-backend-reuse and already-initialized-root cases, which are
generic to :class:`VaultMaterializer` and not specific to this bake method.
"""

from __future__ import annotations

from pathlib import Path

from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.render_community import render_community
from babylon.projection.view_models import CommunityView

_VIEW = CommunityView(community_id="settler", verified_tick=500, roster=("C001",), overlaps=())


class TestBakeCommunity:
    def test_it_writes_exactly_community_id_md_and_returns_its_path(self, tmp_path: Path) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_community(_VIEW, tick=500)

        assert page_path == tmp_path / "vault" / "community" / "settler.md"
        assert page_path.is_file()
        written_files = sorted(
            p.relative_to(tmp_path / "vault") for p in (tmp_path / "vault").rglob("*.md")
        )
        assert written_files == [Path("community/settler.md")]

    def test_the_written_page_matches_render_community_output(self, tmp_path: Path) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_community(_VIEW, tick=500)

        assert page_path.read_text(encoding="utf8") == render_community(_VIEW, verified_tick=500)

    def test_two_independent_bakes_produce_identical_commit_shas(self, tmp_path: Path) -> None:
        def bake(root: Path) -> bytes:
            materializer = VaultMaterializer(root)
            materializer.bake_community(_VIEW, tick=500)
            from dulwich.repo import Repo

            repo = Repo(str(root))
            try:
                return repo.head()
            finally:
                repo.close()

        sha_a = bake(tmp_path / "vault_a")
        sha_b = bake(tmp_path / "vault_b")
        assert sha_a == sha_b
