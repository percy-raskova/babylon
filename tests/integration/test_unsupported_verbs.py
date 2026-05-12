"""Spec 061 T078 / FR-025: unsupported verbs are not exposed.

Verifies the bridge's VERB_TO_ACTION_TYPE map excludes ``investigate``
/ ``move`` / ``negotiate`` so player-action submissions targeting those
verbs are rejected at the action-type-mapping boundary. Real handlers
will be added by a follow-up spec.

Pure unit test — no live DB.
"""

from __future__ import annotations

from web.game.engine_bridge import (
    CANONICAL_VERBS,
    UNSUPPORTED_VERBS,
    VERB_TO_ACTION_TYPE,
)


class TestUnsupportedVerbsExcluded:
    """FR-025: spec-061 verbs without engine handlers are filtered out."""

    def test_investigate_not_in_canonical_verbs(self) -> None:
        assert "investigate" not in CANONICAL_VERBS
        assert "investigate" not in VERB_TO_ACTION_TYPE

    def test_move_not_in_canonical_verbs(self) -> None:
        assert "move" not in CANONICAL_VERBS
        assert "move" not in VERB_TO_ACTION_TYPE

    def test_negotiate_not_in_canonical_verbs(self) -> None:
        assert "negotiate" not in CANONICAL_VERBS
        assert "negotiate" not in VERB_TO_ACTION_TYPE

    def test_unsupported_verbs_listed_explicitly(self) -> None:
        """The UNSUPPORTED_VERBS frozenset documents which verbs were removed
        so a future spec can re-enable them by deleting the entry."""
        assert "investigate" in UNSUPPORTED_VERBS
        assert "move" in UNSUPPORTED_VERBS
        assert "negotiate" in UNSUPPORTED_VERBS

    def test_supported_verbs_remain_in_map(self) -> None:
        """Sanity check: educate / reproduce / attack / mobilize / campaign /
        aid are still in the map. These are the verbs with real handlers."""
        for verb in ("educate", "reproduce", "attack", "mobilize", "campaign", "aid"):
            assert verb in CANONICAL_VERBS, f"supported verb {verb!r} missing"
            assert verb in VERB_TO_ACTION_TYPE, f"supported verb {verb!r} missing from map"

    def test_canonical_and_supported_align(self) -> None:
        """CANONICAL_VERBS is derived from VERB_TO_ACTION_TYPE.keys(); the
        sets must be identical."""
        assert frozenset(VERB_TO_ACTION_TYPE.keys()) == CANONICAL_VERBS

    def test_no_overlap_between_supported_and_unsupported(self) -> None:
        assert CANONICAL_VERBS.isdisjoint(UNSUPPORTED_VERBS)
