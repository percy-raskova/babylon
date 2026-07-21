"""Tests for babylon.projection.vault.materializer: the VaultMaterializer skeleton."""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.projection.vault.git_backend import commit_page, init_vault
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.view_models import CountyView, NationalView, OrganizationView


class TestBakeCounty:
    def test_it_writes_exactly_county_fips_md_and_returns_its_path(
        self, tmp_path: Path, wayne_county_view: CountyView
    ) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_county(wayne_county_view, tick=500)

        assert page_path == tmp_path / "vault" / "county" / "26163.md"
        assert page_path.is_file()
        written_files = sorted(
            p.relative_to(tmp_path / "vault") for p in (tmp_path / "vault").rglob("*.md")
        )
        assert written_files == [Path("county/26163.md")]

    def test_the_written_page_matches_render_county_output(
        self, tmp_path: Path, wayne_county_view: CountyView
    ) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_county(wayne_county_view, tick=500)

        from babylon.projection.vault.render import render_county

        assert page_path.read_text(encoding="utf8") == render_county(
            wayne_county_view, verified_tick=500
        )

    def test_two_independent_bakes_of_the_same_view_are_byte_identical(
        self, tmp_path: Path, wayne_county_view: CountyView
    ) -> None:
        materializer_a = VaultMaterializer(tmp_path / "vault_a")
        page_a = materializer_a.bake_county(wayne_county_view, tick=500)

        materializer_b = VaultMaterializer(tmp_path / "vault_b")
        page_b = materializer_b.bake_county(wayne_county_view, tick=500)

        assert page_a.read_text(encoding="utf8") == page_b.read_text(encoding="utf8")

    def test_two_independent_bakes_of_the_same_view_produce_identical_commit_shas(
        self, tmp_path: Path, wayne_county_view: CountyView
    ) -> None:
        # Rebuild the commit sha independently via the git_backend layer to
        # compare against what the materializer itself committed, for both
        # of two fresh vault roots — the DoD's determinism double-bake.
        def bake(root: Path) -> bytes:
            materializer = VaultMaterializer(root)
            materializer.bake_county(wayne_county_view, tick=500)
            from dulwich.repo import Repo

            repo = Repo(str(root))
            try:
                return repo.head()
            finally:
                repo.close()

        sha_a = bake(tmp_path / "vault_a")
        sha_b = bake(tmp_path / "vault_b")
        assert sha_a == sha_b

    def test_it_accepts_an_already_initialized_vault_root(
        self, tmp_path: Path, wayne_county_view: CountyView
    ) -> None:
        """A vault root initialized before construction (e.g. by an earlier
        process) is reused, not re-initialized or rejected."""
        root = tmp_path / "vault"
        init_vault(root)
        commit_page(root, "README.md", "# vault\n", tick=0, message="init: vault root")

        materializer = VaultMaterializer(root)
        page_path = materializer.bake_county(wayne_county_view, tick=500)
        assert page_path.is_file()


class TestBakeNational:
    """Mirrors TestBakeCounty exactly, one tier up (WO-17)."""

    def test_it_writes_exactly_national_id_md_and_returns_its_path(
        self, tmp_path: Path, usa_national_view: NationalView
    ) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_national(usa_national_view, tick=500)

        assert page_path == tmp_path / "vault" / "national" / "USA.md"
        assert page_path.is_file()
        written_files = sorted(
            p.relative_to(tmp_path / "vault") for p in (tmp_path / "vault").rglob("*.md")
        )
        assert written_files == [Path("national/USA.md")]

    def test_the_written_page_matches_render_national_output(
        self, tmp_path: Path, usa_national_view: NationalView
    ) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_national(usa_national_view, tick=500)

        from babylon.projection.vault.render_national import render_national

        assert page_path.read_text(encoding="utf8") == render_national(
            usa_national_view, verified_tick=500
        )

    def test_two_independent_bakes_of_the_same_view_are_byte_identical(
        self, tmp_path: Path, usa_national_view: NationalView
    ) -> None:
        materializer_a = VaultMaterializer(tmp_path / "vault_a")
        page_a = materializer_a.bake_national(usa_national_view, tick=500)

        materializer_b = VaultMaterializer(tmp_path / "vault_b")
        page_b = materializer_b.bake_national(usa_national_view, tick=500)

        assert page_a.read_text(encoding="utf8") == page_b.read_text(encoding="utf8")

    def test_two_independent_bakes_of_the_same_view_produce_identical_commit_shas(
        self, tmp_path: Path, usa_national_view: NationalView
    ) -> None:
        def bake(root: Path) -> bytes:
            materializer = VaultMaterializer(root)
            materializer.bake_national(usa_national_view, tick=500)
            from dulwich.repo import Repo

            repo = Repo(str(root))
            try:
                return repo.head()
            finally:
                repo.close()

        sha_a = bake(tmp_path / "vault_a")
        sha_b = bake(tmp_path / "vault_b")
        assert sha_a == sha_b


@pytest.fixture
def rwp_organization_view() -> OrganizationView:
    """A fully-populated ``OrganizationView`` (Program 24 P2 WO-18)."""
    return OrganizationView(
        org_id="org_rwp",
        verified_tick=500,
        name="Revolutionary Workers Party",
        org_type="political_faction",
    )


class TestBakeOrganization:
    def test_it_writes_exactly_organization_id_md_and_returns_its_path(
        self, tmp_path: Path, rwp_organization_view: OrganizationView
    ) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_organization(rwp_organization_view, tick=500)

        assert page_path == tmp_path / "vault" / "organization" / "org_rwp.md"
        assert page_path.is_file()
        written_files = sorted(
            p.relative_to(tmp_path / "vault") for p in (tmp_path / "vault").rglob("*.md")
        )
        assert written_files == [Path("organization/org_rwp.md")]

    def test_the_written_page_matches_render_organization_output(
        self, tmp_path: Path, rwp_organization_view: OrganizationView
    ) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_organization(rwp_organization_view, tick=500)

        from babylon.projection.vault.render_organization import render_organization

        assert page_path.read_text(encoding="utf8") == render_organization(
            rwp_organization_view, verified_tick=500
        )

    def test_two_independent_bakes_of_the_same_view_produce_identical_commit_shas(
        self, tmp_path: Path, rwp_organization_view: OrganizationView
    ) -> None:
        def bake(root: Path) -> bytes:
            materializer = VaultMaterializer(root)
            materializer.bake_organization(rwp_organization_view, tick=500)
            from dulwich.repo import Repo

            repo = Repo(str(root))
            try:
                return repo.head()
            finally:
                repo.close()

        sha_a = bake(tmp_path / "vault_a")
        sha_b = bake(tmp_path / "vault_b")
        assert sha_a == sha_b
