"""Tests for babylon.projection.vault.render_community: sandboxed deterministic rendering."""

from __future__ import annotations

from babylon.projection.vault.render_community import render_community
from babylon.projection.view_models import CommunityOverlap, CommunityView

_FULL_VIEW = CommunityView(
    community_id="settler",
    verified_tick=500,
    roster=("C001", "C002", "C003"),
    overlaps=(
        CommunityOverlap(community_id="patriarchal", shared_member_count=2),
        CommunityOverlap(community_id="women", shared_member_count=1),
    ),
)

_NO_OVERLAP_VIEW = CommunityView(
    community_id="settler",
    verified_tick=500,
    roster=("C001",),
    overlaps=(),
)

_ABSENT_VIEW = CommunityView(community_id="settler", verified_tick=500)


class TestRenderCommunity:
    """Content contract: frontmatter, roster/overlap backlinks, absence blocks."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(self) -> None:
        page = render_community(_FULL_VIEW, verified_tick=500)
        assert page.startswith("---\n")
        assert "id: community/settler" in page
        assert "verified_tick: 500" in page

    def test_it_renders_the_roster_as_social_class_wikilinks(self) -> None:
        page = render_community(_FULL_VIEW, verified_tick=500)
        assert "[[social_class/C001]]" in page
        assert "[[social_class/C002]]" in page
        assert "[[social_class/C003]]" in page

    def test_it_renders_overlaps_as_community_wikilinks_with_shared_counts(self) -> None:
        page = render_community(_FULL_VIEW, verified_tick=500)
        assert "[[community/patriarchal]] (2 shared members)" in page
        assert "[[community/women]] (1 shared members)" in page

    def test_empty_overlaps_renders_an_explicit_none_note_not_an_absence_block(self) -> None:
        page = render_community(_NO_OVERLAP_VIEW, verified_tick=500)
        assert "No other communities currently overlap." in page
        assert "{absence} overlaps" not in page

    def test_it_renders_one_absence_block_per_absent_field_with_remedy_text(self) -> None:
        page = render_community(_ABSENT_VIEW, verified_tick=500)
        assert page.count("{absence}") == 3
        assert "{absence} roster —" in page
        assert "{absence} formation_tick —" in page
        assert "{absence} overlaps —" in page
        assert "Investigate(Community) to attribute a roster" in page
        assert "no producer exists" in page

    def test_it_never_renders_a_bare_none_for_an_absent_field(self) -> None:
        """A present-but-None field must never leak through as the literal
        text 'None' — every absence is a named {absence} block instead."""
        page = render_community(_ABSENT_VIEW, verified_tick=500)
        assert "None" not in page

    def test_statblock_carries_only_formation_tick_when_present(self) -> None:
        view = CommunityView(
            community_id="settler",
            verified_tick=500,
            roster=("C001",),
            formation_tick=3,
            overlaps=(),
        )
        page = render_community(view, verified_tick=500)
        assert "{statblock} community/settler" in page
        assert "formation_tick: 3" in page
        assert "{absence} formation_tick" not in page

    def test_it_is_a_pure_function_of_its_inputs(self) -> None:
        first = render_community(_FULL_VIEW, verified_tick=500)
        second = render_community(_FULL_VIEW, verified_tick=500)
        assert first == second
