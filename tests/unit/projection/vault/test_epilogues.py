"""Contract tests for the epilogue content module (Program 24 P2 WO-34).

Pins three things: (1) the port is a verbatim copy of ``web/game/
epilogues.py``, not a re-authoring; (2) all SIX non-``IN_PROGRESS``
``GameOutcome`` members ship a page, including ``UNRESOLVED`` — flagging the
charter's "five epilogue pages" vs the enum's six members as an open
question rather than silently dropping one; (3) the ``UNRESOLVED`` body
renders exactly as ``src/frontend/e2e/first-session.spec.ts`` (lines
434-439) already asserts against the live web bridge — the same copy in a
new, transport-neutral home.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.enums import GameOutcome
from babylon.projection.vault.epilogues import EPILOGUES, Epilogue
from babylon.projection.vault.render_epilogue import render_epilogue
from game.epilogues import EPILOGUES as WEB_EPILOGUES

pytestmark = pytest.mark.unit

#: Byte-for-byte copy of the string first-session.spec.ts (lines 435-438)
#: asserts against the live end-state screen's ``.end-state-epilogue-body``.
#: Pinned literally here so the contract survives WO-54's eventual deletion
#: of src/frontend/ — this is the durable golden, not a derived comparison.
_UNRESOLVED_BODY_PER_FIRST_SESSION_SPEC = (
    "One hundred years, and no verdict. The contradiction did not resolve; it deepened, "
    "changed terrain, and outlived every administration that claimed to manage it. "
    "History does not end because the observation window closes. The line holds where "
    "you built it; the rest belongs to the next century, and to whoever organizes it."
)


class TestEpiloguesCoverage:
    """One epilogue per outcome — drift-safe against enum growth."""

    def test_covers_every_outcome_except_in_progress(self) -> None:
        expected = {o.value for o in GameOutcome} - {GameOutcome.IN_PROGRESS.value}
        assert set(EPILOGUES) == expected

    def test_ships_all_six_shells_including_unresolved(self) -> None:
        """WO-34 ships all six shells; the sixth's authorship is an owner
        ruling (specs/24-archive/work-orders-p2-p4.md OPEN QUESTIONS #1),
        not something this content module decides by omission."""
        assert len(EPILOGUES) == 6
        assert "unresolved" in EPILOGUES


class TestVerbatimPort:
    """Proves this is a DATA PORT, not a re-authoring (WO-34 deliverable)."""

    def test_same_key_set_as_the_web_source(self) -> None:
        assert set(EPILOGUES) == set(WEB_EPILOGUES)

    def test_every_outcome_matches_the_web_source_field_by_field(self) -> None:
        for outcome, entry in EPILOGUES.items():
            source = WEB_EPILOGUES[outcome]
            assert entry.headline == source.headline, outcome
            assert entry.body == source.body, outcome
            assert entry.palette == source.palette, outcome


class TestUnresolvedPinnedCopy:
    """Pins the UNRESOLVED body exactly as first-session.spec.ts does."""

    def test_headline_is_the_struggle_continues(self) -> None:
        assert EPILOGUES["unresolved"].headline == "THE STRUGGLE CONTINUES"

    def test_body_matches_the_spec_ported_string_exactly(self) -> None:
        assert EPILOGUES["unresolved"].body == _UNRESOLVED_BODY_PER_FIRST_SESSION_SPEC

    def test_palette_is_unresolved(self) -> None:
        assert EPILOGUES["unresolved"].palette == "unresolved"


class TestEpiloguesDistinctness:
    """Acceptance gate 4 (spec-116): every recognized outcome is DISTINCT."""

    def test_headlines_pairwise_distinct(self) -> None:
        headlines = [e.headline for e in EPILOGUES.values()]
        assert len(set(headlines)) == len(headlines)

    def test_bodies_pairwise_distinct(self) -> None:
        bodies = [e.body for e in EPILOGUES.values()]
        assert len(set(bodies)) == len(bodies)

    def test_the_bunker_fails_duplicate_is_dead(self) -> None:
        assert all(e.headline != "THE BUNKER FAILS" for e in EPILOGUES.values())

    def test_bodies_are_prose_not_labels(self) -> None:
        for outcome, entry in EPILOGUES.items():
            assert len(entry.body) >= 120, f"{outcome} body too short to be an epilogue"
            assert entry.body != entry.headline


class TestEpiloguesPalettes:
    """Palette mapping: rupture for victory, unresolved for the open horizon."""

    def test_palette_mapping(self) -> None:
        assert EPILOGUES["revolutionary_victory"].palette == "rupture"
        assert EPILOGUES["unresolved"].palette == "unresolved"
        for outcome in (
            "ecological_collapse",
            "fascist_consolidation",
            "red_ogv",
            "fragmented_collapse",
        ):
            assert EPILOGUES[outcome].palette == "defeat"

    def test_epilogue_is_frozen(self) -> None:
        entry = EPILOGUES["revolutionary_victory"]
        with pytest.raises(ValidationError):
            entry.headline = "MUTATED"  # type: ignore[misc]

    def test_palette_literal_is_enforced(self) -> None:
        with pytest.raises(ValidationError):
            Epilogue(headline="X", body="Y" * 130, palette="triumph")  # type: ignore[arg-type]


class TestRenderEpilogue:
    """render_epilogue: pure, deterministic, one page shell per outcome."""

    def test_renders_headline_and_body_for_every_outcome(self) -> None:
        for outcome, entry in EPILOGUES.items():
            page = render_epilogue(outcome)
            assert entry.headline in page
            assert entry.body in page

    def test_renders_frontmatter_with_the_stable_id_slug(self) -> None:
        page = render_epilogue("unresolved")
        assert page.startswith("---\n")
        assert "id: epilogue/unresolved" in page
        assert "palette: unresolved" in page

    def test_renders_the_headline_as_an_h1(self) -> None:
        page = render_epilogue("revolutionary_victory")
        assert "\n# BABYLON FALLS\n" in page

    def test_unrecognized_outcome_raises_loud(self) -> None:
        """A present-but-wrong outcome string fails loud, never fabricates
        a placeholder ending (Constitution III.11)."""
        with pytest.raises(KeyError):
            render_epilogue("not_a_real_outcome")

    def test_is_a_pure_function_of_its_input(self) -> None:
        first = render_epilogue("revolutionary_victory")
        second = render_epilogue("revolutionary_victory")
        assert first == second
