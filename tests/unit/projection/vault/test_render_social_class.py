"""Tests for babylon.projection.vault.render_social_class: sandboxed deterministic rendering.

Mirrors ``tests/unit/projection/vault/test_render.py``'s discipline for
:class:`~babylon.projection.view_models.SocialClassView` pages.
"""

from __future__ import annotations

from babylon.projection.vault.render_social_class import render_social_class

_ABSENT_FIELDS_WHEN_ONLY_CORE_FIELDS_KNOWN = (
    "wealth",
    "organization",
    "repression_faced",
    "p_acquiescence",
    "p_revolution",
    "consciousness",
    "county_class_composition",
)


class TestRenderSocialClass:
    """Content contract: frontmatter, statblock, and per-field absence blocks."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(
        self, wayne_social_class_view
    ) -> None:
        page = render_social_class(wayne_social_class_view, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: social_class/C004" in page
        assert "verified_tick: 500" in page

    def test_it_renders_a_statblock_carrying_the_social_class_view_numbers(
        self, wayne_social_class_view
    ) -> None:
        page = render_social_class(wayne_social_class_view, verified_tick=500)
        assert "{statblock} social_class/C004" in page
        assert "role: labor_aristocracy" in page
        assert "county_fips: 26163" in page
        assert "population: 1" in page
        assert "wealth: 0.563657" in page
        assert "consciousness.liberal: 0.500000" in page
        assert "county_class_composition.proletariat: 0.350000" in page

    def test_it_renders_the_county_wikilink_when_attributed(self, wayne_social_class_view) -> None:
        page = render_social_class(wayne_social_class_view, verified_tick=500)
        assert "[[county/26163]]" in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(
        self, wayne_social_class_view_with_absences
    ) -> None:
        page = render_social_class(wayne_social_class_view_with_absences, verified_tick=500)
        assert page.count("{absence}") == len(_ABSENT_FIELDS_WHEN_ONLY_CORE_FIELDS_KNOWN)
        for field in _ABSENT_FIELDS_WHEN_ONLY_CORE_FIELDS_KNOWN:
            assert f"{{absence}} {field} —" in page
        assert "Assess(SurvivalCalculus)" in page
        assert "Census(Territory)" in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(
        self, wayne_social_class_view_with_absences
    ) -> None:
        """A present-but-None field must never leak through as the literal
        text 'None' — every absence is a named {absence} block instead."""
        page = render_social_class(wayne_social_class_view_with_absences, verified_tick=500)
        assert "None" not in page

    def test_it_is_a_pure_function_of_its_inputs(self, wayne_social_class_view) -> None:
        first = render_social_class(wayne_social_class_view, verified_tick=500)
        second = render_social_class(wayne_social_class_view, verified_tick=500)
        assert first == second
