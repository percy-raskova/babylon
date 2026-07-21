"""Tests for babylon.projection.vault.render_industry: sandboxed deterministic rendering."""

from __future__ import annotations

import jinja2
import pytest

from babylon.projection.vault.render import _build_environment
from babylon.projection.vault.render_industry import render_industry

_ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN = (
    "total_wages",
    "profit_rate",
    "occ",
    "department_weights",
    "member_business_count",
    "member_worker_block_count",
    "county_fips",
)


class TestRenderIndustry:
    """Content contract: frontmatter, statblock, and per-field absence blocks."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(
        self, manufacturing_industry_view
    ) -> None:
        page = render_industry(manufacturing_industry_view, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: industry/ind_31-33" in page
        assert "verified_tick: 500" in page

    def test_it_renders_a_statblock_carrying_the_industry_view_numbers(
        self, manufacturing_industry_view
    ) -> None:
        page = render_industry(manufacturing_industry_view, verified_tick=500)
        assert "{statblock} industry/ind_31-33" in page
        assert "naics_2digit: 31-33" in page
        assert "naics_label: Manufacturing" in page
        assert "total_employment: 2000" in page
        assert "total_wages: 100000.000000" in page
        assert "department_weights.dept_I: 0.400000" in page
        assert "member_business_count: 2" in page
        assert "county_fips: 26125, 26163" in page

    def test_it_renders_county_wikilinks_when_county_fips_is_present(
        self, manufacturing_industry_view
    ) -> None:
        page = render_industry(manufacturing_industry_view, verified_tick=500)
        assert "[[county/26125]]" in page
        assert "[[county/26163]]" in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(
        self, manufacturing_industry_view_with_absences
    ) -> None:
        page = render_industry(manufacturing_industry_view_with_absences, verified_tick=500)
        assert page.count("{absence}") == len(_ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN)
        for field in _ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN:
            assert f"{{absence}} {field} —" in page
        # Every absence block names a remedy verb, never a bare field name.
        assert "Audit(ProfitRate)" in page
        assert "Locate(Industry)" in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(
        self, manufacturing_industry_view_with_absences
    ) -> None:
        """A present-but-None field must never leak through as the literal
        text 'None' — every absence is a named {absence} block instead."""
        page = render_industry(manufacturing_industry_view_with_absences, verified_tick=500)
        assert "None" not in page

    def test_it_is_a_pure_function_of_its_inputs(self, manufacturing_industry_view) -> None:
        first = render_industry(manufacturing_industry_view, verified_tick=500)
        second = render_industry(manufacturing_industry_view, verified_tick=500)
        assert first == second


class TestSandboxedEnvironmentReuse:
    """render_industry reuses render.py's one sandboxed environment factory."""

    def test_strict_undefined_raises_on_a_nonexistent_field(
        self, manufacturing_industry_view
    ) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ industry.this_field_does_not_exist }}")
        with pytest.raises(jinja2.exceptions.UndefinedError):
            template.render(industry=manufacturing_industry_view)
