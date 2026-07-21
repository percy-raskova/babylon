"""Tests for babylon.projection.vault.render_organization: sandboxed deterministic rendering."""

from __future__ import annotations

import pytest

from babylon.projection.vault.render_organization import render_organization
from babylon.projection.view_models import OrganizationView

_ABSENT_FIELDS_WHEN_ONLY_CORE_FACTS_KNOWN = (
    "legal_standing",
    "territory_ids",
    "headquarters_id",
    "is_institution",
    "heat",
    "consciousness_tendency",
    "cohesion",
    "cadre_level",
)


@pytest.fixture
def rwp_view() -> OrganizationView:
    """A fully-populated ``OrganizationView`` shaped like the RWP fixture."""
    return OrganizationView(
        kind="organization",
        org_id="org_rwp",
        verified_tick=500,
        name="Revolutionary Workers Party",
        org_type="political_faction",
        class_character="proletarian",
        legal_standing="registered",
        budget=5_000.0,
        territory_ids=("territory_detroit",),
        headquarters_id="territory_detroit",
        is_institution=False,
        heat=0.3,
        consciousness_tendency="revolutionary",
        cohesion=0.6,
        cadre_level=0.7,
    )


@pytest.fixture
def rwp_view_with_absences() -> OrganizationView:
    """The same org with only ``name``/``org_type``/``class_character``/``budget`` known."""
    return OrganizationView(
        org_id="org_rwp",
        verified_tick=500,
        name="Revolutionary Workers Party",
        org_type="political_faction",
        class_character="proletarian",
        budget=5_000.0,
    )


@pytest.fixture
def bare_view() -> OrganizationView:
    """An all-absent dossier — the WO-18 no-producer contingency shape."""
    return OrganizationView(org_id="org_rwp", verified_tick=5)


class TestRenderOrganization:
    """Content contract: frontmatter, statblock, and per-field absence blocks."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(
        self, rwp_view: OrganizationView
    ) -> None:
        page = render_organization(rwp_view, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: organization/org_rwp" in page
        assert "verified_tick: 500" in page

    def test_it_renders_a_statblock_carrying_the_organization_view_numbers(
        self, rwp_view: OrganizationView
    ) -> None:
        page = render_organization(rwp_view, verified_tick=500)
        assert "{statblock} organization/org_rwp" in page
        assert "name: Revolutionary Workers Party" in page
        assert "org_type: political_faction" in page
        assert "class_character: proletarian" in page
        assert "budget: 5000.000000" in page
        assert "territory_ids: territory_detroit" in page
        assert "cohesion: 0.600000" in page
        assert "cadre_level: 0.700000" in page

    def test_it_renders_zero_territories_as_a_present_none_marker_not_an_absence(self) -> None:
        """An empty ``territory_ids`` tuple is a real fact — a statblock row, not {absence}."""
        view = OrganizationView(
            org_id="org_rwp", verified_tick=1, territory_ids=(), name="Empty Org"
        )
        page = render_organization(view, verified_tick=1)
        assert "territory_ids: (none)" in page
        assert "{absence} territory_ids" not in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(
        self, rwp_view_with_absences: OrganizationView
    ) -> None:
        page = render_organization(rwp_view_with_absences, verified_tick=500)
        assert page.count("{absence}") == len(_ABSENT_FIELDS_WHEN_ONLY_CORE_FACTS_KNOWN)
        for field in _ABSENT_FIELDS_WHEN_ONLY_CORE_FACTS_KNOWN:
            assert f"{{absence}} {field} —" in page
        # Every absence block names a remedy verb, never a bare field name.
        assert "Survey(Organization)" in page
        assert "Investigate(Organization)" in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(
        self, rwp_view_with_absences: OrganizationView
    ) -> None:
        """A present-but-None field must never leak through as the literal
        text 'None' — every absence is a named {absence} block instead."""
        page = render_organization(rwp_view_with_absences, verified_tick=500)
        assert "None" not in page

    def test_it_renders_every_absence_block_for_a_fully_bare_dossier(
        self, bare_view: OrganizationView
    ) -> None:
        page = render_organization(bare_view, verified_tick=5)
        # 12 declared optional fields, all absent.
        assert page.count("{absence}") == 12
        assert "{statblock} organization/org_rwp" in page

    def test_it_is_a_pure_function_of_its_inputs(self, rwp_view: OrganizationView) -> None:
        first = render_organization(rwp_view, verified_tick=500)
        second = render_organization(rwp_view, verified_tick=500)
        assert first == second
