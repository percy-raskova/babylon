"""Tests for babylon.projection.vault.render_economy: sandboxed deterministic rendering."""

from __future__ import annotations

import jinja2
import pytest

from babylon.projection.vault.render import _build_environment
from babylon.projection.vault.render_economy import render_economy

_ABSENT_FIELDS_WHEN_ONLY_VERDICT_KNOWN = (
    "class_phi_readings",
    "phi_unequal_exchange",
    "phi_reproduction",
    "phi_domestic",
    "phi_iii_report",
    "phi_decomposition_total",
    "surplus_produced",
    "profit_of_enterprise",
    "interest_burden",
    "ground_rent",
    "taxes_on_surplus",
    "rentier_share",
    "financialization_share",
    "total_consumption",
    "total_biocapacity",
    "overshoot_ratio",
    "biocapacity_ceiling",
    "energy_beta_j",
)


class TestRenderEconomy:
    """Content contract: frontmatter, statblock, per-class Φ, surplus identity, absences."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(
        self, usa_economy_view
    ) -> None:
        page = render_economy(usa_economy_view, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: economy/USA" in page
        assert "verified_tick: 500" in page

    def test_it_renders_a_statblock_carrying_the_economy_view_numbers(
        self, usa_economy_view
    ) -> None:
        page = render_economy(usa_economy_view, verified_tick=500)
        assert "{statblock} economy/USA" in page
        assert "wage_balance: 0.180000" in page
        assert "labor_aristocracy_verdict: True" in page
        assert "surplus_produced: 1500.000000" in page
        assert "financialization_share: 0.100000" in page
        assert "biocapacity_ceiling: 1200.000000" in page

    def test_it_renders_per_class_phi_readings_as_their_own_section(self, usa_economy_view) -> None:
        page = render_economy(usa_economy_view, verified_tick=500)
        assert "C001:" in page
        assert "phi_absolute=20.000000" in page
        assert "is_labor_aristocracy=True" in page

    def test_it_renders_the_surplus_identity_line(self, usa_economy_view) -> None:
        page = render_economy(usa_economy_view, verified_tick=500)
        assert "s = p + i + r + t" in page
        assert "1500.000000 = 600.000000 + 150.000000 + 450.000000 + 300.000000" in page

    def test_it_always_renders_the_energy_vertex_as_an_unpositioned_absence(
        self, usa_economy_view
    ) -> None:
        """Even a fully-populated dossier still carries the one permanent absence."""
        page = render_economy(usa_economy_view, verified_tick=500)
        assert page.count("{absence}") == 1
        assert "{absence} energy_beta_j —" in page
        assert "energy split" in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(
        self, usa_economy_view_with_absences
    ) -> None:
        page = render_economy(usa_economy_view_with_absences, verified_tick=500)
        assert page.count("{absence}") == len(_ABSENT_FIELDS_WHEN_ONLY_VERDICT_KNOWN)
        for field in _ABSENT_FIELDS_WHEN_ONLY_VERDICT_KNOWN:
            assert f"{{absence}} {field} —" in page
        # Every absence block names a remedy, never a bare field name.
        assert "Wire(FundamentalTheorem)" in page
        assert "Distribute(Surplus)" in page
        assert "Survey(Territory)" in page

    def test_it_never_renders_the_surplus_identity_line_when_absent(
        self, usa_economy_view_with_absences
    ) -> None:
        page = render_economy(usa_economy_view_with_absences, verified_tick=500)
        assert "s = p + i + r + t" not in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(
        self, usa_economy_view_with_absences
    ) -> None:
        """A present-but-None field must never leak through as the literal
        text 'None' — every absence is a named {absence} block instead."""
        page = render_economy(usa_economy_view_with_absences, verified_tick=500)
        assert "None" not in page

    def test_it_is_a_pure_function_of_its_inputs(self, usa_economy_view) -> None:
        first = render_economy(usa_economy_view, verified_tick=500)
        second = render_economy(usa_economy_view, verified_tick=500)
        assert first == second


class TestSandboxedEnvironmentReuse:
    """render_economy reuses render.py's sandboxed environment factory, not a copy."""

    def test_strict_undefined_raises_on_a_nonexistent_field(self, usa_economy_view) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ economy.this_field_does_not_exist }}")
        with pytest.raises(jinja2.exceptions.UndefinedError):
            template.render(economy=usa_economy_view)
