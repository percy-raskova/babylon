"""Tests for babylon.projection.vault.render_institution: sandboxed rendering.

Also covers :meth:`~babylon.projection.vault.materializer.VaultMaterializer.
bake_institution` — co-located here (rather than a separate file) since
WO-19's contract-test list, like its sibling Lane P WOs, names three files:
``test_institution.py`` (the projection), a render test (this file), and a
TUI snapshot test. The materializer wrapper is thin enough to cover
alongside the renderer it delegates to without needing a fourth file.
"""

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest

from babylon.projection.vault.git_backend import commit_page, init_vault
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.render import _build_environment
from babylon.projection.vault.render_institution import render_institution
from babylon.projection.view_models import FactionalComposition, InstitutionView

_ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN = (
    "apparatus_type",
    "social_function",
    "class_inscription",
    "housed_org_ids",
    "territory_ids",
    "factional_composition",
)


@pytest.fixture
def doj_institution_view() -> InstitutionView:
    """A fully-populated ``InstitutionView`` shaped like the DOJ test fixture."""
    return InstitutionView(
        kind="institution",
        institution_id="doj",
        verified_tick=500,
        name="Department of Justice",
        apparatus_type="rsa_judicial",
        social_function="adjudication",
        class_inscription="bourgeois",
        legitimacy=0.7,
        budget=1_000_000.0,
        housed_org_ids=("fbi",),
        territory_ids=("us_national",),
        factional_composition=FactionalComposition(
            liberal_technocratic=0.5,
            revanchist_fascist=0.3,
            institutionalist_bonapartist=0.2,
        ),
    )


@pytest.fixture
def doj_institution_view_with_absences() -> InstitutionView:
    """The same institution with most optional fields honestly unattributed.

    Only ``name``, ``legitimacy``, and ``budget`` are present; every other
    optional field hydrates to ``None``.
    """
    return InstitutionView(
        kind="institution",
        institution_id="doj",
        verified_tick=500,
        name="Department of Justice",
        legitimacy=0.7,
        budget=1_000_000.0,
    )


class TestRenderInstitution:
    """Content contract: frontmatter, statblock, and per-field absence blocks."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(
        self, doj_institution_view: InstitutionView
    ) -> None:
        page = render_institution(doj_institution_view, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: institution/doj" in page
        assert "verified_tick: 500" in page

    def test_it_renders_a_statblock_carrying_the_institution_view_numbers(
        self, doj_institution_view: InstitutionView
    ) -> None:
        page = render_institution(doj_institution_view, verified_tick=500)
        assert "{statblock} institution/doj" in page
        assert "name: Department of Justice" in page
        assert "legitimacy: 0.700000" in page
        assert "budget: 1000000.000000" in page
        assert "housed_org_ids: fbi" in page
        assert "factional_composition.liberal_technocratic: 0.500000" in page

    def test_it_renders_a_housed_organizations_wikilink_per_id(
        self, doj_institution_view: InstitutionView
    ) -> None:
        page = render_institution(doj_institution_view, verified_tick=500)
        assert "[[organization/fbi]]" in page

    def test_it_renders_no_wikilink_section_body_when_housed_org_ids_is_absent(
        self, doj_institution_view_with_absences: InstitutionView
    ) -> None:
        page = render_institution(doj_institution_view_with_absences, verified_tick=500)
        assert "[[organization/" not in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(
        self, doj_institution_view_with_absences: InstitutionView
    ) -> None:
        page = render_institution(doj_institution_view_with_absences, verified_tick=500)
        assert page.count("{absence}") == len(_ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN)
        for field in _ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN:
            assert f"{{absence}} {field} —" in page
        assert "Investigate(Institution)" in page
        assert "Poll(InternalBalance)" in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(
        self, doj_institution_view_with_absences: InstitutionView
    ) -> None:
        page = render_institution(doj_institution_view_with_absences, verified_tick=500)
        assert "None" not in page

    def test_it_is_a_pure_function_of_its_inputs(
        self, doj_institution_view: InstitutionView
    ) -> None:
        first = render_institution(doj_institution_view, verified_tick=500)
        second = render_institution(doj_institution_view, verified_tick=500)
        assert first == second


class TestSharedSandboxedEnvironment:
    """render_institution reuses render.py's environment factory verbatim."""

    def test_strict_undefined_raises_on_a_nonexistent_field(
        self, doj_institution_view: InstitutionView
    ) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ institution.this_field_does_not_exist }}")
        with pytest.raises(jinja2.exceptions.UndefinedError):
            template.render(institution=doj_institution_view)


class TestBakeInstitution:
    """``VaultMaterializer.bake_institution`` — the per-kind bake wrapper."""

    def test_it_writes_exactly_institution_id_md_and_returns_its_path(
        self, tmp_path: Path, doj_institution_view: InstitutionView
    ) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_institution(doj_institution_view, tick=500)

        assert page_path == tmp_path / "vault" / "institution" / "doj.md"
        assert page_path.is_file()
        written_files = sorted(
            p.relative_to(tmp_path / "vault") for p in (tmp_path / "vault").rglob("*.md")
        )
        assert written_files == [Path("institution/doj.md")]

    def test_the_written_page_matches_render_institution_output(
        self, tmp_path: Path, doj_institution_view: InstitutionView
    ) -> None:
        materializer = VaultMaterializer(tmp_path / "vault")
        page_path = materializer.bake_institution(doj_institution_view, tick=500)

        assert page_path.read_text(encoding="utf8") == render_institution(
            doj_institution_view, verified_tick=500
        )

    def test_two_independent_bakes_of_the_same_view_are_byte_identical(
        self, tmp_path: Path, doj_institution_view: InstitutionView
    ) -> None:
        materializer_a = VaultMaterializer(tmp_path / "vault_a")
        page_a = materializer_a.bake_institution(doj_institution_view, tick=500)

        materializer_b = VaultMaterializer(tmp_path / "vault_b")
        page_b = materializer_b.bake_institution(doj_institution_view, tick=500)

        assert page_a.read_text(encoding="utf8") == page_b.read_text(encoding="utf8")

    def test_two_independent_bakes_produce_identical_commit_shas(
        self, tmp_path: Path, doj_institution_view: InstitutionView
    ) -> None:
        def bake(root: Path) -> bytes:
            materializer = VaultMaterializer(root)
            materializer.bake_institution(doj_institution_view, tick=500)
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
        self, tmp_path: Path, doj_institution_view: InstitutionView
    ) -> None:
        root = tmp_path / "vault"
        init_vault(root)
        commit_page(root, "README.md", "# vault\n", tick=0, message="init: vault root")

        materializer = VaultMaterializer(root)
        page_path = materializer.bake_institution(doj_institution_view, tick=500)
        assert page_path.is_file()
