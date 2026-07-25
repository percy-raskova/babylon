"""Tests for babylon.projection.vault.render_faction's faction-page rendering.

Local fixtures only — deliberately NOT added to the shared
``tests/unit/projection/vault/conftest.py`` (not a listed shared-file-zipper
point per ``specs/24-archive/work-orders-p2-p4.md``, and every parallel Lane
P WO would otherwise collide on the same conftest lines). Mirrors
``test_render_sovereign.py`` exactly.
"""

from __future__ import annotations

import jinja2
import pytest

from babylon.projection.vault.render_faction import _build_environment, render_faction
from babylon.projection.view_models import FactionView, hydrate_faction

_ABSENT_FIELDS_WHEN_ONLY_NAME_KNOWN = (
    "ideology",
    "colonial_stance",
    "is_settler_formation",
    "extraction_modifier",
    "violence_modifier",
    "class_reduction",
    "metabolic_reduction",
    "color_hex",
    "founded_tick",
    "dissolved_tick",
    "territory_influence",
)


@pytest.fixture
def restorationist_view() -> FactionView:
    """A fully-populated ``FactionView`` shaped like FAC_RESTORATIONIST."""
    return hydrate_faction(
        {
            "kind": "faction",
            "faction_id": "FAC_RESTORATIONIST",
            "verified_tick": 500,
            "name": "Restorationist Coalition",
            "ideology": "settler-restorationism",
            "colonial_stance": "uphold",
            "is_settler_formation": True,
            "extraction_modifier": 1.2,
            "violence_modifier": 1.1,
            "class_reduction": 0.3,
            "metabolic_reduction": -0.2,
            "color_hex": "#AA0000",
            "founded_tick": 0,
            "dissolved_tick": None,
            "territory_influence": [
                {
                    "territory_id": "T001",
                    "county_fips": "26163",
                    "influence_level": 0.7,
                    "support_type": "labor",
                },
                {
                    "territory_id": "T002",
                    "county_fips": None,
                    "influence_level": 0.4,
                    "support_type": "ideological",
                },
            ],
        }
    )


@pytest.fixture
def restorationist_view_with_absences() -> FactionView:
    """The same faction with only its name attributed.

    ``territory_influence`` is deliberately ``None`` here (not ``()``): this
    fixture represents "the faction node itself carries almost nothing", not
    "a real faction known to influence zero territories".
    """
    return hydrate_faction(
        {
            "kind": "faction",
            "faction_id": "FAC_RESTORATIONIST",
            "verified_tick": 500,
            "name": "Restorationist Coalition",
        }
    )


class TestRenderFaction:
    """Content contract: frontmatter, statblock, Influence lines, absence blocks."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(
        self, restorationist_view: FactionView
    ) -> None:
        page = render_faction(restorationist_view, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: faction/FAC_RESTORATIONIST" in page
        assert "verified_tick: 500" in page

    def test_it_renders_a_statblock_carrying_the_faction_view_numbers(
        self, restorationist_view: FactionView
    ) -> None:
        page = render_faction(restorationist_view, verified_tick=500)
        assert "{statblock} faction/FAC_RESTORATIONIST" in page
        assert "name: Restorationist Coalition" in page
        assert "ideology: settler-restorationism" in page
        assert "colonial_stance: uphold" in page
        assert "is_settler_formation: True" in page
        assert "extraction_modifier: 1.200000" in page
        assert "violence_modifier: 1.100000" in page
        assert "class_reduction: 0.300000" in page
        assert "metabolic_reduction: -0.200000" in page
        assert "color_hex: #AA0000" in page
        assert "founded_tick: 0" in page

    def test_the_statblock_does_not_carry_territory_influence_rows(
        self, restorationist_view: FactionView
    ) -> None:
        """territory_influence gets its own section, not statblock rows (edge-shaped)."""
        page = render_faction(restorationist_view, verified_tick=500)
        statblock, _, rest = page.partition("```")
        del statblock
        fence_body = rest.split("```", 1)[0]
        assert "territory_influence" not in fence_body

    def test_it_renders_one_line_per_influenced_territory(
        self, restorationist_view: FactionView
    ) -> None:
        page = render_faction(restorationist_view, verified_tick=500)
        assert "T001 county=26163 influence_level=0.700000 support_type=labor" in page
        assert "T002 county=n/a influence_level=0.400000 support_type=ideological" in page

    def test_it_renders_no_influence_lines_when_none_are_known(
        self, restorationist_view_with_absences: FactionView
    ) -> None:
        page = render_faction(restorationist_view_with_absences, verified_tick=500)
        assert "influence_level=" not in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(
        self, restorationist_view_with_absences: FactionView
    ) -> None:
        page = render_faction(restorationist_view_with_absences, verified_tick=500)
        assert page.count("{absence}") == len(_ABSENT_FIELDS_WHEN_ONLY_NAME_KNOWN)
        for field in _ABSENT_FIELDS_WHEN_ONLY_NAME_KNOWN:
            assert f"{{absence}} {field} —" in page
        assert "Survey(Faction)" in page
        assert "Observe(Influence)" in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(
        self, restorationist_view_with_absences: FactionView
    ) -> None:
        """A present-but-None field must never leak through as the literal
        text 'None' — every absence is a named {absence} block instead."""
        page = render_faction(restorationist_view_with_absences, verified_tick=500)
        assert "None" not in page

    def test_a_faction_present_but_influencing_nothing_renders_no_absence_for_it(self) -> None:
        """territory_influence=() is present data — no absence block for it."""
        view = hydrate_faction(
            {
                "kind": "faction",
                "faction_id": "FAC_RESTORATIONIST",
                "verified_tick": 500,
                "name": "Restorationist Coalition",
                "territory_influence": [],
            }
        )
        page = render_faction(view, verified_tick=500)
        assert "{absence} territory_influence" not in page

    def test_it_is_a_pure_function_of_its_inputs(self, restorationist_view: FactionView) -> None:
        first = render_faction(restorationist_view, verified_tick=500)
        second = render_faction(restorationist_view, verified_tick=500)
        assert first == second


class TestSandboxedEnvironmentFactionTemplate:
    """The shared sandboxed environment renders the faction template safely."""

    def test_strict_undefined_raises_on_a_nonexistent_field(
        self, restorationist_view: FactionView
    ) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ faction.this_field_does_not_exist }}")
        with pytest.raises(jinja2.exceptions.UndefinedError):
            template.render(faction=restorationist_view)
