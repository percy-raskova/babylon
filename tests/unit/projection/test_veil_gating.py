"""Contract tests for WO-41: veil relocation + gate composition.

Three previously-separate gating systems get their Archive-side homes and
one pinned composition rule: the doctrine veil relocates verbatim
(``babylon.projection.veil``; web shim ``is``-identical), the class-vision
gate ports as a pure function, and the documented fog+class-vision
collision hazard (``fog/filter.py`` header) is RESOLVED —
vision-then-fog, both restriction maps, so the composite never reveals
more than either gate alone. Ports the disabled veil-gate assertions from
``test_engine_bridge.py::TestHexFeaturePropertiesVeilGate`` /
``TestDerivedEconomyVeilGate`` at the contract level.
"""

from __future__ import annotations

from babylon.config.defines import GameDefines
from babylon.projection.fog.class_vision import (
    VISION_GATED_CLASS_FIELDS,
    apply_class_vision,
    mud_quantize,
)
from babylon.projection.fog.ledger import IntelLedger
from babylon.projection.fog.precedence import apply_political_gates
from babylon.projection.veil import (
    TIER1_VALUE_RELATION_FIELDS,
    TIER2_SCISSORS_FIELDS,
    gate_value_axis_fields,
)

_HORIZON = GameDefines().epistemic_horizon


def _payload() -> dict[str, object]:
    return {
        "wealth": 12.5,  # material — never gated
        "heat": 0.61,
        "agitation": 0.55,
        "class_consciousness": 0.31,
        "national_identity": 0.72,
        "organization": 0.44,
        "p_revolution": 0.18,
        "consciousness": {"acquiescence": 0.5, "revolution": 0.3, "apathy": 0.2},
    }


class TestVeilRelocation:
    def test_web_shim_is_identity_single_sourced(self) -> None:
        import sys

        sys.path.insert(0, "web")
        try:
            from babylon.projection import veil as canonical
            from game import veil as legacy

            assert legacy.compute_veil_tier is canonical.compute_veil_tier
            assert legacy.TIER1_VALUE_RELATION_FIELDS is canonical.TIER1_VALUE_RELATION_FIELDS
        finally:
            sys.path.remove("web")

    def test_tier0_masks_both_field_families(self) -> None:
        payload = dict.fromkeys((*TIER1_VALUE_RELATION_FIELDS, *TIER2_SCISSORS_FIELDS), 1.0)
        gated = gate_value_axis_fields(payload, tier=0)
        assert all(gated[field] is None for field in payload)

    def test_tier2_reveals_everything(self) -> None:
        payload = dict.fromkeys((*TIER1_VALUE_RELATION_FIELDS, *TIER2_SCISSORS_FIELDS), 1.0)
        gated = gate_value_axis_fields(payload, tier=2)
        assert gated == payload


class TestClassVisionPort:
    def test_water_is_exact_and_marked(self) -> None:
        gated = apply_class_vision(_payload(), "water")
        assert gated["class_vision"] == "water"
        assert gated["agitation"] == 0.55

    def test_desert_withholds_only_fields_holding_a_value(self) -> None:
        payload = _payload()
        payload["organization"] = None  # honest absence, not fog
        gated = apply_class_vision(payload, "desert")
        assert gated["agitation"] is None
        assert "organization" not in gated["vision_masked"]
        assert "consciousness" in gated["vision_masked"]

    def test_mud_quantizes_on_the_04_grid_half_up(self) -> None:
        gated = apply_class_vision(_payload(), "mud")
        for field in VISION_GATED_CLASS_FIELDS:
            assert gated[field] == mud_quantize(_payload()[field])  # type: ignore[arg-type]
        assert gated["consciousness"] == {
            "acquiescence": 0.4,
            "revolution": 0.4,
            "apathy": 0.4,
        }

    def test_no_vision_is_a_no_op_copy(self) -> None:
        payload = _payload()
        gated = apply_class_vision(payload, None)
        assert gated == payload
        assert gated is not payload  # never the same object

    def test_input_payload_is_never_mutated(self) -> None:
        payload = _payload()
        before = dict(payload)
        apply_class_vision(payload, "desert")
        assert payload == before


class TestGateComposition:
    """The previously-hazardous two-gates case is now well-defined."""

    def _compose(self, vision: str | None, reach: frozenset[str]) -> dict[str, object]:
        return apply_political_gates(
            _payload(),
            node_type="social_class",
            node_id="sc-1",
            vision=vision,
            reach=reach,
            ledger=IntelLedger(),
            tick=5,
            staleness_ticks=_HORIZON.intel_staleness_ticks,
            unknown_ticks=_HORIZON.intel_unknown_ticks,
        )

    def test_composition_never_reveals_what_either_gate_withholds(self) -> None:
        """Desert + out-of-reach: every political field the vision gate
        withheld stays withheld after fog — fog only further restricts."""
        composed = self._compose("desert", frozenset())
        for field in VISION_GATED_CLASS_FIELDS:
            assert composed[field] is None
        assert composed["heat"] is None  # fog's own field, out of reach

    def test_reach_does_not_resurrect_vision_withheld_fields(self) -> None:
        """In-reach fog leaves fields exact — but a desert-withheld field is
        already None BEFORE fog sees it, so reach cannot bring it back."""
        composed = self._compose("desert", frozenset({"sc-1"}))
        assert composed["agitation"] is None

    def test_material_fields_pass_through_untouched(self) -> None:
        composed = self._compose("desert", frozenset())
        assert composed["wealth"] == 12.5

    def test_composition_is_deterministic(self) -> None:
        assert self._compose("mud", frozenset()) == self._compose("mud", frozenset())
