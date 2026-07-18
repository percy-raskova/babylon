"""Spec-116 FR-116-4.2: the six-epilogue data module contract.

Kills the "THE BUNKER FAILS" x4 duplicate: every ``GameOutcome`` except
``IN_PROGRESS`` (including the fixed-horizon ``UNRESOLVED``) carries its own
headline + body + palette, pairwise distinct (spec-116 acceptance gate 4).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.enums import GameOutcome
from game.epilogues import EPILOGUES, Epilogue

pytestmark = pytest.mark.unit


class TestEpiloguesCoverage:
    """One epilogue per outcome — drift-safe against enum growth."""

    def test_covers_every_outcome_except_in_progress(self) -> None:
        expected = {o.value for o in GameOutcome} - {GameOutcome.IN_PROGRESS.value}
        assert set(EPILOGUES) == expected

    def test_unresolved_is_covered(self) -> None:
        # The sixth epilogue of the fixed-horizon ruling (owner 2026-07-17).
        assert "unresolved" in EPILOGUES


class TestEpiloguesDistinctness:
    """Acceptance gate 4: every recognized outcome renders a DISTINCT epilogue."""

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
