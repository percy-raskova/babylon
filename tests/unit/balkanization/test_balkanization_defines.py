"""Spec-070 BalkanizationDefines field-presence test (T010).

Verifies that :class:`babylon.config.defines.balkanization.BalkanizationDefines`
exposes every field documented in
``contracts/balkanization_defines.schema.json`` with the correct default.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.config.defines.balkanization import BalkanizationDefines

pytestmark = pytest.mark.unit

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "070-balkanization"
    / "contracts"
    / "balkanization_defines.schema.json"
)


def _schema_defaults() -> dict[str, object]:
    return json.loads(_SCHEMA_PATH.read_text())["properties"]


def test_balkanization_defines_is_frozen() -> None:
    defines = BalkanizationDefines()
    with pytest.raises(ValidationError):
        defines.metabolic_impact_intensify = -0.99  # type: ignore[misc]


def test_metabolic_impact_defaults_match_schema() -> None:
    defines = BalkanizationDefines()
    schema = _schema_defaults()
    assert defines.metabolic_impact_intensify == pytest.approx(
        schema["metabolic_impact_intensify"]["default"]
    )
    assert defines.metabolic_impact_continue == pytest.approx(
        schema["metabolic_impact_continue"]["default"]
    )
    assert defines.metabolic_impact_cease == pytest.approx(
        schema["metabolic_impact_cease"]["default"]
    )


def test_stance_multiplier_defaults_match_schema() -> None:
    defines = BalkanizationDefines()
    schema = _schema_defaults()
    assert defines.stance_extraction_modifier == schema["stance_extraction_modifier"]["default"]
    assert defines.stance_violence_modifier == schema["stance_violence_modifier"]["default"]
    assert defines.stance_class_reduction == schema["stance_class_reduction"]["default"]
    assert defines.stance_metabolic_reduction == schema["stance_metabolic_reduction"]["default"]


def test_secession_and_endgame_thresholds_match_schema() -> None:
    defines = BalkanizationDefines()
    schema = _schema_defaults()
    assert defines.secession_influence_threshold == pytest.approx(
        schema["secession_influence_threshold"]["default"]
    )
    assert defines.secession_hysteresis_ticks == schema["secession_hysteresis_ticks"]["default"]
    assert defines.min_contiguous_hex_count == schema["min_contiguous_hex_count"]["default"]
    assert defines.red_ogv_class_tension_floor == pytest.approx(
        schema["red_ogv_class_tension_floor"]["default"]
    )
    assert defines.red_ogv_habitability_floor == pytest.approx(
        schema["red_ogv_habitability_floor"]["default"]
    )
    assert defines.red_ogv_slope_window_ticks == schema["red_ogv_slope_window_ticks"]["default"]
    assert (
        defines.fragmented_collapse_min_sovereigns
        == schema["fragmented_collapse_min_sovereigns"]["default"]
    )
    assert (
        defines.fragmented_collapse_min_duration_ticks
        == schema["fragmented_collapse_min_duration_ticks"]["default"]
    )
    assert defines.faction_victory_supermajority_threshold == pytest.approx(
        schema["faction_victory_supermajority_threshold"]["default"]
    )
    assert defines.initial_post_collapse_control_level == pytest.approx(
        schema["initial_post_collapse_control_level"]["default"]
    )
    assert defines.red_settler_trap_class_reduction_threshold == pytest.approx(
        schema["red_settler_trap_class_reduction_threshold"]["default"]
    )


def test_remediation_added_fields_match_schema() -> None:
    """C5 + C8 + C1 remediation defaults exist with schema defaults."""

    defines = BalkanizationDefines()
    schema = _schema_defaults()
    assert (
        defines.revolutionary_victory_min_cross_divide_solidarity_edges
        == schema["revolutionary_victory_min_cross_divide_solidarity_edges"]["default"]
    )
    assert defines.liberal_imperial_influence_cap == pytest.approx(
        schema["liberal_imperial_influence_cap"]["default"]
    )
    assert (
        defines.projected_habitability_horizon_ticks
        == schema["projected_habitability_horizon_ticks"]["default"]
    )


def test_every_schema_field_has_pydantic_field() -> None:
    """No silent drift: every JSON-schema property is exposed as an attribute."""

    defines = BalkanizationDefines()
    for property_name in _schema_defaults():
        assert hasattr(defines, property_name), f"missing field: {property_name}"
