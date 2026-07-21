"""Tests for VaultMaterializer.bake_sovereign (WO-20).

A separate file from ``test_materializer.py`` (not a listed shared-file
zipper point, but every parallel Lane P WO adds a ``bake_<kind>`` test —
splitting per kind avoids nine WOs colliding on one file).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.render import render_sovereign
from babylon.projection.view_models import SovereignView, hydrate_sovereign


@pytest.fixture
def usa_fed_view() -> SovereignView:
    return hydrate_sovereign(
        {
            "kind": "sovereign",
            "sovereign_id": "SOV_USA_FED",
            "verified_tick": 500,
            "name": "United States Federal Government",
            "claimed_county_fips": ["26163"],
        }
    )


class TestBakeSovereign:
    def test_it_writes_exactly_sovereign_id_md_and_returns_its_path(
        self, tmp_path: Path, usa_fed_view: SovereignView
    ) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_sovereign(usa_fed_view, tick=500)

        assert page_path == tmp_path / "vault" / "sovereign" / "SOV_USA_FED.md"
        assert page_path.is_file()
        written_files = sorted(
            p.relative_to(tmp_path / "vault") for p in (tmp_path / "vault").rglob("*.md")
        )
        assert written_files == [Path("sovereign/SOV_USA_FED.md")]

    def test_the_written_page_matches_render_sovereign_output(
        self, tmp_path: Path, usa_fed_view: SovereignView
    ) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_sovereign(usa_fed_view, tick=500)

        assert page_path.read_text(encoding="utf8") == render_sovereign(
            usa_fed_view, verified_tick=500
        )

    def test_two_independent_bakes_of_the_same_view_are_byte_identical(
        self, tmp_path: Path, usa_fed_view: SovereignView
    ) -> None:
        materializer_a = VaultMaterializer(tmp_path / "vault_a")
        page_a = materializer_a.bake_sovereign(usa_fed_view, tick=500)

        materializer_b = VaultMaterializer(tmp_path / "vault_b")
        page_b = materializer_b.bake_sovereign(usa_fed_view, tick=500)

        assert page_a.read_text(encoding="utf8") == page_b.read_text(encoding="utf8")

    def test_two_independent_bakes_produce_identical_commit_shas(
        self, tmp_path: Path, usa_fed_view: SovereignView
    ) -> None:
        def bake(root: Path) -> bytes:
            materializer = VaultMaterializer(root)
            materializer.bake_sovereign(usa_fed_view, tick=500)
            from dulwich.repo import Repo

            repo = Repo(str(root))
            try:
                return repo.head()
            finally:
                repo.close()

        sha_a = bake(tmp_path / "vault_a")
        sha_b = bake(tmp_path / "vault_b")
        assert sha_a == sha_b

    def test_a_county_and_a_sovereign_page_coexist_in_one_vault(
        self, tmp_path: Path, usa_fed_view: SovereignView
    ) -> None:
        """bake_sovereign shares a vault root with bake_county without collision."""
        from babylon.projection.view_models import CountyView

        materializer = VaultMaterializer(tmp_path / "vault")
        county_view = CountyView(county_fips="26163", verified_tick=500, sovereign_id="SOV_USA_FED")
        materializer.bake_county(county_view, tick=500)
        materializer.bake_sovereign(usa_fed_view, tick=500)

        written_files = sorted(
            p.relative_to(tmp_path / "vault") for p in (tmp_path / "vault").rglob("*.md")
        )
        assert written_files == [
            Path("county/26163.md"),
            Path("sovereign/SOV_USA_FED.md"),
        ]
