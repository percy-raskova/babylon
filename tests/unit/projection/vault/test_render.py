"""Tests for babylon.projection.vault.render: sandboxed deterministic rendering."""

from __future__ import annotations

import jinja2
import pytest

from babylon.projection.vault.render import _build_environment, render_county

_ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN = (
    "class_composition",
    "consciousness",
    "legitimacy",
    "p_acquiescence",
    "p_revolution",
    "bifurcation_score",
    "sovereign_id",
)


class TestRenderCounty:
    """Content contract: frontmatter, statblock, and per-field absence blocks."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(
        self, wayne_county_view
    ) -> None:
        page = render_county(wayne_county_view, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: county/26163" in page
        assert "verified_tick: 500" in page

    def test_it_renders_a_statblock_carrying_the_county_view_numbers(
        self, wayne_county_view
    ) -> None:
        page = render_county(wayne_county_view, verified_tick=500)
        assert "{statblock} county/26163" in page
        assert "population: 1749343" in page
        assert "median_wage: 18.500000" in page
        assert "class_composition.proletariat: 0.550000" in page
        assert "consciousness.liberal: 0.600000" in page
        assert "sovereign_id: SOV_USA" in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(
        self, wayne_county_view_with_absences
    ) -> None:
        page = render_county(wayne_county_view_with_absences, verified_tick=500)
        assert page.count("{absence}") == len(_ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN)
        for field in _ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN:
            assert f"{{absence}} {field} —" in page
        # Every absence block names a remedy verb, never a bare field name.
        assert "Census(Territory)" in page
        assert "Claim(Sovereignty)" in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(
        self, wayne_county_view_with_absences
    ) -> None:
        """A present-but-None field must never leak through as the literal
        text 'None' — every absence is a named {absence} block instead."""
        page = render_county(wayne_county_view_with_absences, verified_tick=500)
        assert "None" not in page

    def test_it_is_a_pure_function_of_its_inputs(self, wayne_county_view) -> None:
        first = render_county(wayne_county_view, verified_tick=500)
        second = render_county(wayne_county_view, verified_tick=500)
        assert first == second


class TestSandboxedEnvironment:
    """The environment factory itself: StrictUndefined + sandbox behavior."""

    def test_strict_undefined_raises_on_a_nonexistent_field(self, wayne_county_view) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ county.this_field_does_not_exist }}")
        with pytest.raises(jinja2.exceptions.UndefinedError):
            template.render(county=wayne_county_view)

    def test_sandbox_blocks_dunder_attribute_access(self, wayne_county_view) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ county.__class__ }}")
        with pytest.raises(jinja2.exceptions.SecurityError):
            template.render(county=wayne_county_view)

    def test_sandbox_blocks_mutation_of_an_injected_mutable(self) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ items.append(1) }}")
        with pytest.raises(jinja2.exceptions.SecurityError):
            template.render(items=[1, 2, 3])
