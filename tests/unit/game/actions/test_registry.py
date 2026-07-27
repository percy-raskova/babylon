"""Behavioral contract for the unified agent-type-gated action registry (Task 1)."""

import pytest
from pydantic import ValidationError

from babylon.game.actions.registry import ACTION_REGISTRY, ActionSpec, actions_for
from babylon.projection.verbs.preview import CANONICAL_VERBS


def test_all_nine_verbs_present_as_live_organizer_actions():
    for verb in CANONICAL_VERBS:
        spec = ACTION_REGISTRY[verb]
        assert isinstance(spec, ActionSpec)
        assert spec.status == "LIVE"
        assert "organizer" in spec.agent_types


def test_institutional_stub_is_gated_and_marked():
    spec = ACTION_REGISTRY["fund_research"]
    assert spec.status == "STUB"
    assert spec.agent_types == frozenset({"state", "corporation"})
    assert "organizer" not in spec.agent_types


def test_actions_for_filters_by_agent_type():
    organizer = {s.id for s in actions_for("organizer")}
    assert organizer >= CANONICAL_VERBS
    assert "fund_research" not in organizer
    assert "fund_research" in {s.id for s in actions_for("state")}


def test_actionspec_is_frozen():
    spec = ACTION_REGISTRY["educate"]
    with pytest.raises(ValidationError):
        spec.label = "mutated"  # frozen


def test_reproduce_is_the_only_self_targeting_canonical_verb():
    """``reproduce`` always targets the acting org itself (``projection/
    verbs/plate.py``'s own "reproduce": True eligibility-row comment) —
    unit "verb-targeting" declares this as ``target_shape`` metadata."""
    assert ACTION_REGISTRY["reproduce"].target_shape == "self"


def test_every_other_canonical_verb_requires_an_explicit_target():
    for verb in CANONICAL_VERBS - {"reproduce"}:
        assert ACTION_REGISTRY[verb].target_shape == "target", (
            f"{verb} should declare target_shape='target'"
        )


def test_institutional_stubs_declare_a_self_target_shape_placeholder():
    """STUB macro-actions have no wired-effect target concept yet (gated on
    Vol I+II and beyond) — ``"self"`` is the honest placeholder, never a
    fabricated ``"target"`` for mechanics that don't exist in code."""
    for spec in ACTION_REGISTRY.values():
        if spec.status == "STUB":
            assert spec.target_shape == "self"
