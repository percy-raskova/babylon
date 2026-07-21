"""Tests for ``VaultMaterializer.bake_state`` (Program 24 P2 WO-16).

Mirrors ``TestBakeCounty`` in ``tests/unit/projection/vault/test_materializer.py``
exactly, for the state nesting tier. A dedicated file rather than an append
to that shared test module, matching ``render_state.py``'s own no-shared-file
rationale — keeps this Lane-P work order collision-free against sibling
Lane-P work orders adding their own ``bake_<kind>`` coverage in parallel.
"""

from __future__ import annotations

from pathlib import Path

from babylon.projection.vault.git_backend import commit_page, init_vault
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.render_state import render_state
from babylon.projection.view_models import StateView, hydrate_state


def _michigan_state_view() -> StateView:
    return hydrate_state(
        {
            "kind": "state",
            "state_fips": "26",
            "verified_tick": 500,
            "population": 1749343,
            "median_wage": 18.5,
        }
    )


class TestBakeState:
    def test_it_writes_exactly_state_fips_md_and_returns_its_path(self, tmp_path: Path) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        view = _michigan_state_view()
        page_path = materializer.bake_state(view, tick=500)

        assert page_path == tmp_path / "vault" / "state" / "26.md"
        assert page_path.is_file()
        written_files = sorted(
            p.relative_to(tmp_path / "vault") for p in (tmp_path / "vault").rglob("*.md")
        )
        assert written_files == [Path("state/26.md")]

    def test_the_written_page_matches_render_state_output(self, tmp_path: Path) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        view = _michigan_state_view()
        page_path = materializer.bake_state(view, tick=500)

        assert page_path.read_text(encoding="utf8") == render_state(view, verified_tick=500)

    def test_two_independent_bakes_of_the_same_view_are_byte_identical(
        self, tmp_path: Path
    ) -> None:
        view = _michigan_state_view()
        materializer_a = VaultMaterializer(tmp_path / "vault_a")
        page_a = materializer_a.bake_state(view, tick=500)

        materializer_b = VaultMaterializer(tmp_path / "vault_b")
        page_b = materializer_b.bake_state(view, tick=500)

        assert page_a.read_text(encoding="utf8") == page_b.read_text(encoding="utf8")

    def test_two_independent_bakes_of_the_same_view_produce_identical_commit_shas(
        self, tmp_path: Path
    ) -> None:
        view = _michigan_state_view()

        def bake(root: Path) -> bytes:
            materializer = VaultMaterializer(root)
            materializer.bake_state(view, tick=500)
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
        process, or by a county bake) is reused, not re-initialized or rejected."""
        root = tmp_path / "vault"
        init_vault(root)
        commit_page(root, "README.md", "# vault\n", tick=0, message="init: vault root")

        materializer = VaultMaterializer(root)
        page_path = materializer.bake_state(_michigan_state_view(), tick=500)
        assert page_path.is_file()

    def test_it_coexists_with_a_county_bake_in_the_same_vault(self, tmp_path: Path) -> None:
        """The county and state pages live at distinct paths in one vault
        (R7 nesting: a state page nests county pages via wikilinks, both
        materialized into the same on-disk vault)."""
        from babylon.projection.view_models import hydrate_county

        materializer = VaultMaterializer(tmp_path / "vault")
        county_view = hydrate_county(
            {"kind": "county", "county_fips": "26163", "verified_tick": 500}
        )
        materializer.bake_county(county_view, tick=500)
        materializer.bake_state(_michigan_state_view(), tick=500)

        written_files = sorted(
            p.relative_to(tmp_path / "vault") for p in (tmp_path / "vault").rglob("*.md")
        )
        assert written_files == [Path("county/26163.md"), Path("state/26.md")]
