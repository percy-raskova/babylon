"""Contract tests for :func:`babylon.tui.verb_plate.render_verb_plate` (WO-26).

Fixture-fed only — no engine, no database. Builds real
:class:`~babylon.projection.verbs.view_models.VerbPlateView` fixtures via the
already-contract-tested :func:`babylon.projection.verbs.plate.build_verb_plate`
provider (WO-38) over small hand-built graphs, mirroring
``tests/unit/projection/verbs/test_plate.py``'s own fixture pattern — this
widget is fixture-fed (WO-26); the live provider is WO-38.
"""

from __future__ import annotations

from rich.panel import Panel
from rich.text import Text

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.projection.verbs.plate import build_verb_plate
from babylon.projection.verbs.preview import VERB_TO_ACTION_TYPE
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.topology import BabylonGraph
from babylon.tui.verb_plate import INVESTIGATE_SUB_VERBS, render_verb_plate

ORG = "org-wayne-vanguard"
TERRITORY = "T26163"


def _wayne_graph() -> BabylonGraph:
    """Wayne County (FIPS 26163) tick-0: every verb eligible via TENANCY.

    Mirrors ``verb-submit.spec.ts``'s corrected tick-0 assertion: a resident
    social_class already tenants the player's territory from tick 0 by
    scenario construction, so EDUCATE/AID (and everything else) resolve real
    targets, not a fabricated dead end.
    """
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        name="Wayne County Tenants Union",
        org_type="political_faction",
        cadre_level=0.6,
        cohesion=0.6,
        budget=50.0,
        heat=0.1,
        territory_ids=[TERRITORY],
    )
    graph.add_node(TERRITORY, NodeType.TERRITORY, county_fips="26163")
    graph.add_node(
        "sc-wayne-proles",
        NodeType.SOCIAL_CLASS,
        name="Wayne proletariat",
        population=1000,
    )
    graph.add_edge("sc-wayne-proles", TERRITORY, EdgeType.TENANCY)
    graph.add_node(
        "org-shop",
        NodeType.ORGANIZATION,
        name="Chamber of Commerce",
        org_type="business",
        territory_ids=[TERRITORY],
    )
    graph.add_node(
        "inst-court",
        NodeType.INSTITUTION,
        name="Wayne County Court",
        territory_ids=[TERRITORY],
    )
    return graph


def _barren_graph() -> BabylonGraph:
    """The org alone in an empty world — almost nothing is eligible."""
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        name="Wayne County Tenants Union",
        org_type="political_faction",
        cadre_level=0.6,
        cohesion=0.6,
        budget=50.0,
        heat=0.1,
        territory_ids=[],
    )
    return graph


def _lines_of(result: object) -> list[str]:
    """Extract the plain body lines from a rendered plate panel."""
    assert isinstance(result, Panel)
    assert isinstance(result.renderable, Text)
    return result.renderable.plain.splitlines()


class TestAllNineVerbsRender:
    def test_every_non_investigate_canonical_verb_is_represented(self) -> None:
        view = build_verb_plate(_wayne_graph(), ORG, tick=0)
        assert view is not None
        joined = "\n".join(_lines_of(render_verb_plate(view)))
        for verb in VERB_TO_ACTION_TYPE:
            if verb == "investigate":
                continue
            assert verb.capitalize() in joined

    def test_investigate_expands_to_its_three_sub_verbs_not_collapsed(self) -> None:
        view = build_verb_plate(_wayne_graph(), ORG, tick=0)
        assert view is not None
        lines = _lines_of(render_verb_plate(view))
        for sub in INVESTIGATE_SUB_VERBS:
            label = f"Investigate({sub})"
            assert any(line.startswith(label) for line in lines), label
        # Never a bare, collapsed "Investigate" line standing in for the three.
        assert not any(line.strip() == "Investigate" for line in lines)
        assert not any(line.strip().startswith("Investigate ") for line in lines)

    def test_all_nine_eligible_wayne_tick_zero_shows_legal_not_a_reason(self) -> None:
        """Mirrors verb-submit.spec.ts's corrected tick-0 assertion."""
        view = build_verb_plate(_wayne_graph(), ORG, tick=0)
        assert view is not None
        assert all(row.eligible for row in view.verbs)
        joined = "\n".join(_lines_of(render_verb_plate(view)))
        assert "✓ legal" in joined
        assert "✗" not in joined


class TestIneligibleVerbsShowReasonNeverHidden:
    def test_a_barren_world_shows_every_ineligible_reason_inline(self) -> None:
        view = build_verb_plate(_barren_graph(), ORG, tick=0)
        assert view is not None
        joined = "\n".join(_lines_of(render_verb_plate(view)))
        ineligible_rows = [row for row in view.verbs if not row.eligible]
        assert ineligible_rows, "the barren fixture must produce ineligible verbs"
        for row in ineligible_rows:
            assert row.reason is not None
            assert row.reason in joined

    def test_reproduce_is_always_eligible_even_in_a_barren_world(self) -> None:
        view = build_verb_plate(_barren_graph(), ORG, tick=0)
        assert view is not None
        by_verb = {row.verb: row for row in view.verbs}
        assert by_verb["reproduce"].eligible
        joined = "\n".join(_lines_of(render_verb_plate(view)))
        assert "Reproduce" in joined
        assert "✓ legal" in joined


class TestCostsShownFromViewModel:
    def test_every_rendered_row_carries_its_preview_ap_cost(self) -> None:
        view = build_verb_plate(_wayne_graph(), ORG, tick=0)
        assert view is not None
        joined = "\n".join(_lines_of(render_verb_plate(view)))
        for row in view.verbs:
            assert row.preview is not None
            assert f"cost={row.preview.action_point_cost:g} AP" in joined

    def test_one_cost_line_per_rendered_entry_investigate_counted_thrice(self) -> None:
        view = build_verb_plate(_wayne_graph(), ORG, tick=0)
        assert view is not None
        lines = _lines_of(render_verb_plate(view))
        cost_lines = [line for line in lines if "AP" in line]
        non_investigate = len(view.verbs) - 1
        expected = non_investigate + len(INVESTIGATE_SUB_VERBS)
        assert len(cost_lines) == expected


class TestMissingVerbRefusesLoudly:
    def test_a_view_missing_a_canonical_verb_renders_an_absence_marker(self) -> None:
        full_view = build_verb_plate(_wayne_graph(), ORG, tick=0)
        assert full_view is not None
        truncated = VerbPlateView(
            org_id=full_view.org_id,
            tick=full_view.tick,
            verbs=tuple(row for row in full_view.verbs if row.verb != "attack"),
        )
        joined = "\n".join(_lines_of(render_verb_plate(truncated)))
        assert "▌ attack — missing from plate view" in joined

    def test_a_view_missing_investigate_renders_one_marker_not_three(self) -> None:
        full_view = build_verb_plate(_wayne_graph(), ORG, tick=0)
        assert full_view is not None
        truncated = VerbPlateView(
            org_id=full_view.org_id,
            tick=full_view.tick,
            verbs=tuple(row for row in full_view.verbs if row.verb != "investigate"),
        )
        lines = _lines_of(render_verb_plate(truncated))
        investigate_lines = [line for line in lines if "investigate" in line.lower()]
        assert len(investigate_lines) == 1
        assert "missing from plate view" in investigate_lines[0]


class TestHeaderNamesOrgAndTick:
    def test_the_panel_title_names_the_org_and_the_tick(self) -> None:
        view = build_verb_plate(_wayne_graph(), ORG, tick=7)
        assert view is not None
        result = render_verb_plate(view)
        assert isinstance(result, Panel)
        assert isinstance(result.title, Text)
        assert result.title.plain == f"{ORG} — verb plate @ T0007"


class TestDeterminism:
    def test_two_calls_with_the_same_view_render_identically(self) -> None:
        view = build_verb_plate(_wayne_graph(), ORG, tick=0)
        assert view is not None
        first = _lines_of(render_verb_plate(view))
        second = _lines_of(render_verb_plate(view))
        assert first == second
