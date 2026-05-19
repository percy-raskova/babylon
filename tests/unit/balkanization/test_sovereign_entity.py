"""Spec-070 Sovereign entity tests (T016, FR-001 -- FR-004 + FR-040b).

Covers:

- ID pattern validation
- Frozen model semantics
- ``metabolic_impact`` computed-field correctness
- Extraction-policy-vs-ruling-faction validator including the special
  SOV_EXTERIOR_NULL combination (``ruling_faction_id=None`` paired with
  ``extraction_policy=CONTINUE``) per FR-040b.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.sovereign import Sovereign
from babylon.models.enums import ExtractionPolicy, SovereigntyType

pytestmark = pytest.mark.unit


def _make_sovereign(**overrides: object) -> Sovereign:
    base: dict[str, object] = {
        "id": "SOV_USA_FED",
        "name": "United States Federal Government",
        "sovereignty_type": SovereigntyType.RECOGNIZED_STATE,
        "legitimacy": 1.0,
        "color_hex": "#3c3b6e",
        "ruling_faction_id": "FAC_RESTORATIONIST",
        "extraction_policy": ExtractionPolicy.INTENSIFY,
        "founded_tick": 0,
    }
    base.update(overrides)
    return Sovereign.model_validate(base)


def test_sovereign_basic_construction() -> None:
    sov = _make_sovereign()
    assert sov.id == "SOV_USA_FED"
    assert sov.sovereignty_type is SovereigntyType.RECOGNIZED_STATE


def test_sovereign_is_frozen() -> None:
    sov = _make_sovereign()
    with pytest.raises(ValidationError):
        sov.legitimacy = 0.5  # type: ignore[misc]


@pytest.mark.parametrize(
    "bad_id",
    ["sov_usa", "SOV_", "sov_USA", "USA_FED", "SOV_lower"],
)
def test_sovereign_id_pattern_rejects_malformed(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        _make_sovereign(id=bad_id)


def test_metabolic_impact_matches_policy() -> None:
    sov_int = _make_sovereign(extraction_policy=ExtractionPolicy.INTENSIFY)
    assert sov_int.metabolic_impact == pytest.approx(-0.02)
    sov_con = _make_sovereign(
        extraction_policy=ExtractionPolicy.CONTINUE,
        ruling_faction_id="FAC_WORKERS_CONGRESS",
    )
    # Re-build with IGNORE-faction so the validator does not reject.
    assert sov_con.metabolic_impact == pytest.approx(-0.005)
    sov_cease = _make_sovereign(
        extraction_policy=ExtractionPolicy.CEASE,
        ruling_faction_id="FAC_DECOLONIAL",
    )
    assert sov_cease.metabolic_impact == pytest.approx(0.01)


def test_legitimacy_clamped_to_unit_interval() -> None:
    with pytest.raises(ValidationError):
        _make_sovereign(legitimacy=1.5)
    with pytest.raises(ValidationError):
        _make_sovereign(legitimacy=-0.1)


def test_color_hex_pattern_validated() -> None:
    with pytest.raises(ValidationError):
        _make_sovereign(color_hex="blue")
    _make_sovereign(color_hex="#FFFFFF")


def test_sov_exterior_null_special_case_allowed_per_fr_040b() -> None:
    """FR-040b: ``ruling_faction_id=None`` paired with
    ``extraction_policy=CONTINUE`` is the explicit SOV_EXTERIOR_NULL
    combination — the validator MUST permit it."""

    sov = _make_sovereign(
        id="SOV_EXTERIOR_NULL",
        name="Exterior fallback boundary",
        sovereignty_type=SovereigntyType.PROVISIONAL,
        legitimacy=0.0,
        ruling_faction_id=None,
        extraction_policy=ExtractionPolicy.CONTINUE,
    )
    assert sov.ruling_faction_id is None
    assert sov.extraction_policy is ExtractionPolicy.CONTINUE
    assert sov.metabolic_impact == pytest.approx(-0.005)


def test_null_ruling_with_non_continue_policy_rejected() -> None:
    """A NULL ruling_faction with anything OTHER than CONTINUE is
    inconsistent and should raise."""

    with pytest.raises(ValidationError):
        _make_sovereign(
            id="SOV_BAD",
            ruling_faction_id=None,
            extraction_policy=ExtractionPolicy.INTENSIFY,
        )


@pytest.mark.parametrize(
    "ruling_faction_id",
    ["faction1", "FAC_", "fac_RESTORATIONIST"],
)
def test_ruling_faction_id_pattern_validated(ruling_faction_id: str) -> None:
    with pytest.raises(ValidationError):
        _make_sovereign(ruling_faction_id=ruling_faction_id)
