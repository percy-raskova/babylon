"""Tests for babylon.projection.vault.render_state: sandboxed deterministic rendering.

Mirrors ``tests/unit/projection/vault/test_render.py`` exactly, for
:class:`~babylon.projection.view_models.StateView` (Program 24 P2 WO-16).
Fixtures are local to this module rather than added to the shared
``tests/unit/projection/vault/conftest.py`` — that conftest isn't named in
the shared-file discipline table either, and keeping each Lane-P work
order's test fixtures self-contained avoids a second collision surface
alongside ``view_models.py``.
"""

from __future__ import annotations

import jinja2
import pytest

from babylon.projection.vault.render_state import _build_environment, render_state
from babylon.projection.view_models import StateView, hydrate_state

_ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN = (
    "class_composition",
    "consciousness",
    "legitimacy",
    "p_acquiescence",
    "p_revolution",
    "bifurcation_score",
    "sovereign_id",
)


@pytest.fixture
def michigan_state_view() -> StateView:
    """A fully-populated ``StateView`` shaped like Michigan."""
    return hydrate_state(
        {
            "kind": "state",
            "state_fips": "26",
            "verified_tick": 500,
            "population": 1749343,
            "class_composition": {
                "bourgeoisie": 0.02,
                "petit_bourgeoisie": 0.08,
                "labor_aristocracy": 0.30,
                "proletariat": 0.55,
                "lumpenproletariat": 0.05,
            },
            "median_wage": 18.5,
            "imperial_rent_phi": 4.2,
            "consciousness": {
                "revolutionary": 0.3,
                "liberal": 0.6,
                "fascist": 0.1,
            },
            "legitimacy": 0.42,
            "p_acquiescence": 0.7,
            "p_revolution": 0.25,
            "bifurcation_score": -0.35,
            "sovereign_id": "SOV_USA",
        }
    )


@pytest.fixture
def michigan_state_view_with_absences() -> StateView:
    """The same state with most optional fields honestly unattributed.

    Only ``population``, ``median_wage``, and ``imperial_rent_phi`` are
    present; every other optional field hydrates to ``None``.
    """
    return hydrate_state(
        {
            "kind": "state",
            "state_fips": "26",
            "verified_tick": 500,
            "population": 1749343,
            "median_wage": 18.5,
            "imperial_rent_phi": 4.2,
        }
    )


class TestRenderState:
    """Content contract: frontmatter, statblock, and per-field absence blocks."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(
        self, michigan_state_view: StateView
    ) -> None:
        page = render_state(michigan_state_view, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: state/26" in page
        assert "verified_tick: 500" in page

    def test_it_renders_a_statblock_carrying_the_state_view_numbers(
        self, michigan_state_view: StateView
    ) -> None:
        page = render_state(michigan_state_view, verified_tick=500)
        assert "{statblock} state/26" in page
        assert "population: 1749343" in page
        assert "median_wage: 18.500000" in page
        assert "class_composition.proletariat: 0.550000" in page
        assert "consciousness.liberal: 0.600000" in page
        assert "sovereign_id: SOV_USA" in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(
        self, michigan_state_view_with_absences: StateView
    ) -> None:
        page = render_state(michigan_state_view_with_absences, verified_tick=500)
        assert page.count("{absence}") == len(_ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN)
        for field in _ABSENT_FIELDS_WHEN_ONLY_CORE_STATS_KNOWN:
            assert f"{{absence}} {field} —" in page
        # Every absence block names a remedy verb, never a bare field name.
        assert "Census(Territory)" in page
        assert "Claim(Sovereignty)" in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(
        self, michigan_state_view_with_absences: StateView
    ) -> None:
        """A present-but-None field must never leak through as the literal
        text 'None' — every absence is a named {absence} block instead."""
        page = render_state(michigan_state_view_with_absences, verified_tick=500)
        assert "None" not in page

    def test_it_is_a_pure_function_of_its_inputs(self, michigan_state_view: StateView) -> None:
        first = render_state(michigan_state_view, verified_tick=500)
        second = render_state(michigan_state_view, verified_tick=500)
        assert first == second


class TestSandboxedEnvironment:
    """The environment factory itself: StrictUndefined + sandbox behavior."""

    def test_strict_undefined_raises_on_a_nonexistent_field(
        self, michigan_state_view: StateView
    ) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ state.this_field_does_not_exist }}")
        with pytest.raises(jinja2.exceptions.UndefinedError):
            template.render(state=michigan_state_view)

    def test_sandbox_blocks_dunder_attribute_access(self, michigan_state_view: StateView) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ state.__class__ }}")
        with pytest.raises(jinja2.exceptions.SecurityError):
            template.render(state=michigan_state_view)

    def test_sandbox_blocks_mutation_of_an_injected_mutable(self) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ items.append(1) }}")
        with pytest.raises(jinja2.exceptions.SecurityError):
            template.render(items=[1, 2, 3])
