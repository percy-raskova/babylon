"""Tests for babylon.projection.vault.render's sovereign-page rendering.

Local fixtures only — deliberately NOT added to the shared
``tests/unit/projection/vault/conftest.py`` (not a listed shared-file-zipper
point per ``specs/24-archive/work-orders-p2-p4.md``, and every parallel Lane
P WO would otherwise collide on the same conftest lines).
"""

from __future__ import annotations

import jinja2
import pytest

from babylon.projection.vault.render import _build_environment, render_sovereign
from babylon.projection.view_models import SovereignView, hydrate_sovereign

_ABSENT_FIELDS_WHEN_ONLY_NAME_KNOWN = (
    "sovereignty_type",
    "legitimacy",
    "ruling_faction_id",
    "extraction_policy",
    "capital_territory_id",
    "capital_county_fips",
    "founded_tick",
    "dissolved_tick",
    "claimed_county_fips",
)


@pytest.fixture
def usa_fed_view() -> SovereignView:
    """A fully-populated ``SovereignView`` shaped like SOV_USA_FED."""
    return hydrate_sovereign(
        {
            "kind": "sovereign",
            "sovereign_id": "SOV_USA_FED",
            "verified_tick": 500,
            "name": "United States Federal Government",
            "sovereignty_type": "recognized_state",
            "legitimacy": 0.82,
            "ruling_faction_id": "FAC_RESTORATIONIST",
            "extraction_policy": "intensify",
            "capital_territory_id": "T_DC",
            "capital_county_fips": "11001",
            "founded_tick": 0,
            "dissolved_tick": None,
            "claimed_county_fips": ["26125", "26163"],
        }
    )


@pytest.fixture
def usa_fed_view_with_absences() -> SovereignView:
    """The same sovereign with only its name attributed.

    ``claimed_county_fips`` is deliberately ``None`` here (not ``()``): this
    fixture represents "the sovereign node itself carries almost nothing",
    not "a real sovereign known to claim zero counties".
    """
    return hydrate_sovereign(
        {
            "kind": "sovereign",
            "sovereign_id": "SOV_USA_FED",
            "verified_tick": 500,
            "name": "United States Federal Government",
        }
    )


class TestRenderSovereign:
    """Content contract: frontmatter, statblock, Claims links, absence blocks."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(
        self, usa_fed_view: SovereignView
    ) -> None:
        page = render_sovereign(usa_fed_view, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: sovereign/SOV_USA_FED" in page
        assert "verified_tick: 500" in page

    def test_it_renders_a_statblock_carrying_the_sovereign_view_numbers(
        self, usa_fed_view: SovereignView
    ) -> None:
        page = render_sovereign(usa_fed_view, verified_tick=500)
        assert "{statblock} sovereign/SOV_USA_FED" in page
        assert "name: United States Federal Government" in page
        assert "sovereignty_type: recognized_state" in page
        assert "legitimacy: 0.820000" in page
        assert "ruling_faction_id: FAC_RESTORATIONIST" in page
        assert "extraction_policy: intensify" in page
        assert "capital_county_fips: 11001" in page
        assert "claimed_county_fips: 26125, 26163" in page

    def test_it_renders_one_wikilink_per_claimed_county(self, usa_fed_view: SovereignView) -> None:
        page = render_sovereign(usa_fed_view, verified_tick=500)
        assert "[[county/26125]]" in page
        assert "[[county/26163]]" in page

    def test_it_renders_no_claims_links_when_none_are_known(
        self, usa_fed_view_with_absences: SovereignView
    ) -> None:
        page = render_sovereign(usa_fed_view_with_absences, verified_tick=500)
        assert "[[county/" not in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(
        self, usa_fed_view_with_absences: SovereignView
    ) -> None:
        page = render_sovereign(usa_fed_view_with_absences, verified_tick=500)
        assert page.count("{absence}") == len(_ABSENT_FIELDS_WHEN_ONLY_NAME_KNOWN)
        for field in _ABSENT_FIELDS_WHEN_ONLY_NAME_KNOWN:
            assert f"{{absence}} {field} —" in page
        assert "Investigate(Faction)" in page
        assert "Claim(Sovereignty)" in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(
        self, usa_fed_view_with_absences: SovereignView
    ) -> None:
        """A present-but-None field must never leak through as the literal
        text 'None' — every absence is a named {absence} block instead."""
        page = render_sovereign(usa_fed_view_with_absences, verified_tick=500)
        assert "None" not in page

    def test_a_sovereign_present_but_claiming_nothing_renders_no_absence_for_it(self) -> None:
        """claimed_county_fips=() is present data — no absence block for it."""
        view = hydrate_sovereign(
            {
                "kind": "sovereign",
                "sovereign_id": "SOV_USA_FED",
                "verified_tick": 500,
                "name": "United States Federal Government",
                "claimed_county_fips": [],
            }
        )
        page = render_sovereign(view, verified_tick=500)
        assert "{absence} claimed_county_fips" not in page

    def test_it_is_a_pure_function_of_its_inputs(self, usa_fed_view: SovereignView) -> None:
        first = render_sovereign(usa_fed_view, verified_tick=500)
        second = render_sovereign(usa_fed_view, verified_tick=500)
        assert first == second


class TestSandboxedEnvironmentSovereignTemplate:
    """The shared sandboxed environment renders the sovereign template safely."""

    def test_strict_undefined_raises_on_a_nonexistent_field(
        self, usa_fed_view: SovereignView
    ) -> None:
        environment = _build_environment()
        template = environment.from_string("{{ sovereign.this_field_does_not_exist }}")
        with pytest.raises(jinja2.exceptions.UndefinedError):
            template.render(sovereign=usa_fed_view)
