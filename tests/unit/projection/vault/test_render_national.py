"""Tests for babylon.projection.vault.render_national: sandboxed deterministic rendering."""

from __future__ import annotations

import jinja2
import pytest

from babylon.projection.vault.render import _build_environment
from babylon.projection.vault.render_national import render_national

_ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN = (
    "class_composition",
    "consciousness",
    "legitimacy",
    "p_acquiescence",
    "p_revolution",
    "bifurcation_score",
    "sovereign_id",
    "c_sum",
    "v_sum",
    "s_sum",
    "k_sum",
    "biocapacity_sum",
    "hex_count",
)


class TestRenderNational:
    """Content contract: frontmatter, statblock, and per-field absence blocks."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(
        self, usa_national_view
    ) -> None:
        page = render_national(usa_national_view, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: national/USA" in page
        assert "verified_tick: 500" in page

    def test_it_renders_the_gas_tank_stock_directly_never_via_absence_walk(
        self, usa_national_view
    ) -> None:
        page = render_national(usa_national_view, verified_tick=500)
        assert "imperial_rent_pool: 100.000000" in page

    def test_it_renders_a_statblock_carrying_the_national_view_numbers(
        self, usa_national_view
    ) -> None:
        page = render_national(usa_national_view, verified_tick=500)
        assert "{statblock} national/USA" in page
        assert "population: 331000000" in page
        assert "median_wage: 22.000000" in page
        assert "class_composition.proletariat: 0.500000" in page
        assert "consciousness.liberal: 0.650000" in page
        assert "sovereign_id: SOV_USA" in page
        assert "c_sum: 1000000.000000" in page
        assert "hex_count: 3156" in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(
        self, usa_national_view_with_absences
    ) -> None:
        page = render_national(usa_national_view_with_absences, verified_tick=500)
        assert page.count("{absence}") == len(_ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN)
        for field in _ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN:
            assert f"{{absence}} {field} —" in page
        # Every absence block names a remedy verb, never a bare field name.
        assert "Census(Territory)" in page
        assert "Claim(Sovereignty)" in page
        assert "Query(v_national_value_aggregate)" in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(
        self, usa_national_view_with_absences
    ) -> None:
        """A present-but-None field must never leak through as the literal
        text 'None' — every absence is a named {absence} block instead."""
        page = render_national(usa_national_view_with_absences, verified_tick=500)
        assert "None" not in page

    def test_it_is_a_pure_function_of_its_inputs(self, usa_national_view) -> None:
        first = render_national(usa_national_view, verified_tick=500)
        second = render_national(usa_national_view, verified_tick=500)
        assert first == second


class TestSandboxedEnvironmentReuse:
    """render_national reuses render.py's sandboxed environment factory, not a copy."""

    def test_strict_undefined_raises_on_a_nonexistent_field(self, usa_national_view) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ national.this_field_does_not_exist }}")
        with pytest.raises(jinja2.exceptions.UndefinedError):
            template.render(national=usa_national_view)
