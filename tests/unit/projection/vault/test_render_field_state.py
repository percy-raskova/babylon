"""Tests for babylon.projection.vault.render_field_state: sandboxed deterministic rendering."""

from __future__ import annotations

import jinja2
import pytest

from babylon.projection.vault.render import _build_environment
from babylon.projection.vault.render_field_state import render_field_state

_ABSENT_FIELDS_WHEN_NOTHING_KNOWN = (
    "nodes",
    "edges",
    "principal_field",
    "dialectical_regime",
)


class TestRenderFieldState:
    """Content contract: frontmatter, statblock, edge section, absences."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(
        self, usa_field_state_view
    ) -> None:
        page = render_field_state(usa_field_state_view, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: field_state/USA" in page
        assert "verified_tick: 500" in page

    def test_it_renders_principal_field_and_dialectical_regime_as_statblock_rows(
        self, usa_field_state_view
    ) -> None:
        page = render_field_state(usa_field_state_view, verified_tick=500)
        assert "{statblock} field_state/USA" in page
        assert "principal_field.field_name: exploitation" in page
        assert "principal_field.max_abs_df_dt: 0.420000" in page
        assert "principal_field.changed: True" in page
        assert "dialectical_regime.regime: crisis" in page
        assert "dialectical_regime.opposition: capital_labor" in page
        assert "dialectical_regime.rate: 0.070000" in page

    def test_it_renders_per_class_field_readings_as_statblock_rows_keyed_by_class_id(
        self, usa_field_state_view
    ) -> None:
        page = render_field_state(usa_field_state_view, verified_tick=500)
        assert "node.C001.name: Periphery Proletariat" in page
        assert "node.C001.fields.exploitation: 0.523000" in page
        assert "node.C001.laplacian.exploitation: 0.400000" in page
        assert "node.C001.df_dt.exploitation: 0.050000" in page
        assert "node.C001.fascist_alignment: 0.200000" in page

    def test_it_renders_the_field_gradients_section(self, usa_field_state_view) -> None:
        page = render_field_state(usa_field_state_view, verified_tick=500)
        assert "## Field Gradients" in page
        assert "C001 -> C002 field=exploitation gradient=0.200000" in page
        assert "source_territory=T001 target_territory=T001" in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(
        self, usa_field_state_view_with_absences
    ) -> None:
        page = render_field_state(usa_field_state_view_with_absences, verified_tick=500)
        assert page.count("{absence}") == len(_ABSENT_FIELDS_WHEN_NOTHING_KNOWN)
        for field in _ABSENT_FIELDS_WHEN_NOTHING_KNOWN:
            assert f"{{absence}} {field} —" in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(
        self, usa_field_state_view_with_absences
    ) -> None:
        page = render_field_state(usa_field_state_view_with_absences, verified_tick=500)
        assert "None" not in page

    def test_it_is_a_pure_function_of_its_inputs(self, usa_field_state_view) -> None:
        first = render_field_state(usa_field_state_view, verified_tick=500)
        second = render_field_state(usa_field_state_view, verified_tick=500)
        assert first == second


class TestSandboxedEnvironmentReuse:
    """render_field_state reuses render.py's sandboxed environment factory, not a copy."""

    def test_strict_undefined_raises_on_a_nonexistent_field(self, usa_field_state_view) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ field_state.this_field_does_not_exist }}")
        with pytest.raises(jinja2.exceptions.UndefinedError):
            template.render(field_state=usa_field_state_view)
