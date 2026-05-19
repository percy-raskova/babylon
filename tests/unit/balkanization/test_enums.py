"""Spec-070 enum membership tests (T005, FR-002 / FR-003 / FR-006 /
FR-010 / FR-011 / FR-015).

Each enum is asserted to contain exactly the documented set of values
(no missing members, no surprise extras). Catches silent enum drift
where a value is renamed or added without spec-update review.
"""

from __future__ import annotations

import pytest

from babylon.models.enums import (
    ClaimLegalStatus,
    ColonialStance,
    EdgeType,
    EventType,
    ExtractionPolicy,
    FiscalStatus,
    GameOutcome,
    PlayerMode,
    SovereigntyType,
    SupportType,
)

pytestmark = pytest.mark.unit


def _values(enum_cls: type) -> set[str]:
    """Return the set of string values for a StrEnum class."""

    return {member.value for member in enum_cls}


def test_colonial_stance_exact_members() -> None:
    assert _values(ColonialStance) == {"uphold", "ignore", "abolish"}


def test_extraction_policy_exact_members() -> None:
    assert _values(ExtractionPolicy) == {"intensify", "continue", "cease"}


def test_sovereignty_type_exact_members() -> None:
    assert _values(SovereigntyType) == {
        "recognized_state",
        "provisional",
        "insurgent",
        "occupation",
        "secessionist",
        "emergency",
    }


def test_fiscal_status_exact_members() -> None:
    assert _values(FiscalStatus) == {
        "taxed",
        "revolt",
        "blockade",
        "liberated",
        "occupied",
    }


def test_claim_legal_status_exact_members() -> None:
    assert _values(ClaimLegalStatus) == {
        "de_jure",
        "de_facto",
        "disputed",
        "occupied",
        "ceded",
    }


def test_support_type_exact_members() -> None:
    assert _values(SupportType) == {
        "material",
        "ideological",
        "military",
        "electoral",
        "labor",
    }


def test_player_mode_exact_members() -> None:
    assert _values(PlayerMode) == {"campaign", "observer"}


def test_edge_type_has_new_balkanization_values() -> None:
    """FR-009 / FR-014 / FR-018 require CLAIMS, INFLUENCES, ADMINISTERS."""

    assert EdgeType.CLAIMS.value == "claims"
    assert EdgeType.INFLUENCES.value == "influences"
    assert EdgeType.ADMINISTERS.value == "administers"


def test_game_outcome_preserves_existing_and_adds_two() -> None:
    """Spec FR-031 / data-model.md §1.9: preserve 4 existing values, add 2."""

    values = _values(GameOutcome)
    # Existing 4 values preserved.
    assert "in_progress" in values
    assert "revolutionary_victory" in values
    assert "ecological_collapse" in values
    assert "fascist_consolidation" in values
    # New 2 added.
    assert "red_ogv" in values
    assert "fragmented_collapse" in values


def test_event_type_has_nine_new_balkanization_values() -> None:
    """data-model.md §1.10: 9 new EventType members for spec-070."""

    expected = {
        "sovereign_collapse",
        "territory_transition",
        "faction_victory",
        "secession_declared",
        "civil_war_declared",
        "red_settler_trap_detected",
        "dual_power_active",
        "red_ogv_endgame",
        "fragmented_collapse_endgame",
    }
    values = _values(EventType)
    missing = expected - values
    assert missing == set(), f"missing event types: {missing}"


def test_legal_status_collision_disambiguated() -> None:
    """FR-045: spec-070 ClaimLegalStatus does NOT shadow the existing
    spec-022 :class:`babylon.models.enums.legal.LegalStatus`."""

    from babylon.models.enums.legal import LegalStatus as Spec022LegalStatus

    # Spec-070 uses ClaimLegalStatus (CLAIMS-edge nature).
    assert ClaimLegalStatus.DE_JURE.value == "de_jure"
    # Spec-022 keeps LegalStatus (community-repression escalation).
    # Values are intentionally disjoint.
    assert _values(ClaimLegalStatus).isdisjoint(_values(Spec022LegalStatus))
