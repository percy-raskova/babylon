"""Spec-070 BalkanizationFaction entity tests (T015, FR-005 -- FR-008,
FR-045 naming disambiguation).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.balkanization_faction import BalkanizationFaction
from babylon.models.enums import ColonialStance

pytestmark = pytest.mark.unit


def _make_faction(**overrides: object) -> BalkanizationFaction:
    base: dict[str, object] = {
        "id": "FAC_RESTORATIONIST",
        "name": "Restorationist Coalition",
        "ideology": "settler-restorationism",
        "colonial_stance": ColonialStance.UPHOLD,
        "is_settler_formation": True,
        "extraction_modifier": 1.5,
        "violence_modifier": 2.0,
        "class_reduction": 0.0,
        "metabolic_reduction": -0.5,
        "color_hex": "#aa0000",
        "founded_tick": 0,
    }
    base.update(overrides)
    return BalkanizationFaction.model_validate(base)


def test_faction_basic_construction() -> None:
    faction = _make_faction()
    assert faction.id == "FAC_RESTORATIONIST"
    assert faction.colonial_stance is ColonialStance.UPHOLD
    assert faction.is_settler_formation is True


def test_faction_is_frozen() -> None:
    faction = _make_faction()
    with pytest.raises(ValidationError):
        faction.ideology = "different"  # type: ignore[misc]


@pytest.mark.parametrize(
    "bad_id",
    ["faction1", "FAC_", "FAC_lowercase", "fac_RESTORATIONIST", "POL_RESTORATIONIST"],
)
def test_faction_id_pattern_rejects_malformed(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        _make_faction(id=bad_id)


@pytest.mark.parametrize(
    "good_id",
    ["FAC_X", "FAC_RESTORATIONIST", "FAC_WORKERS_CONGRESS", "FAC_A1_B2"],
)
def test_faction_id_pattern_accepts_well_formed(good_id: str) -> None:
    faction = _make_faction(id=good_id)
    assert faction.id == good_id


def test_color_hex_pattern_validated() -> None:
    with pytest.raises(ValidationError):
        _make_faction(color_hex="red")
    # Both uppercase and lowercase hex digits accepted.
    _make_faction(color_hex="#FF00aa")


def test_class_reduction_clamped_to_unit_interval() -> None:
    with pytest.raises(ValidationError):
        _make_faction(class_reduction=1.5)
    with pytest.raises(ValidationError):
        _make_faction(class_reduction=-0.1)


def test_metabolic_reduction_bounds() -> None:
    with pytest.raises(ValidationError):
        _make_faction(metabolic_reduction=2.0)
    with pytest.raises(ValidationError):
        _make_faction(metabolic_reduction=-2.0)


def test_disambiguated_from_existing_political_faction_class() -> None:
    """FR-045: spec-070 BalkanizationFaction is a SEPARATE concept from
    the existing :class:`babylon.models.entities.organization.PoliticalFaction`."""

    from babylon.models.entities.organization import (
        PoliticalFaction as OrgPoliticalFaction,
    )

    assert BalkanizationFaction is not OrgPoliticalFaction


def test_dissolved_tick_optional() -> None:
    faction = _make_faction(dissolved_tick=None)
    assert faction.dissolved_tick is None
    faction_late = _make_faction(dissolved_tick=100)
    assert faction_late.dissolved_tick == 100
