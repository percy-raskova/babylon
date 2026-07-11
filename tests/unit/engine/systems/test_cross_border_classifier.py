"""Contract tests for CrossBorderCommuteClassifier (Spec 063 T031 / US3)."""

from __future__ import annotations

import pytest

from babylon.domain.economics.node_kinds import NodeKind
from babylon.engine.systems.cross_border_commute import (
    CrossBorderClassification,
    CrossBorderCommuteClassifier,
)

pytestmark = [pytest.mark.unit]


_STUDY_AREA_HEXES = frozenset(["872a307affffff7", "872a307a0ffffff"])
_STUDY_AREA_STATES = frozenset(["26"])
_DOMESTIC_STATES = frozenset(
    [f"{n:02d}" for n in range(1, 57) if n not in (3, 7, 14, 43, 52)]
    + ["60", "66", "69", "72", "78"]
)


def _make_classifier(**overrides) -> CrossBorderCommuteClassifier:  # type: ignore[no-untyped-def]
    return CrossBorderCommuteClassifier(
        study_area_hexes=overrides.get("study_area_hexes", _STUDY_AREA_HEXES),
        study_area_states=overrides.get("study_area_states", _STUDY_AREA_STATES),
        domestic_states=overrides.get("domestic_states", _DOMESTIC_STATES),
    )


def test_rule_1_in_area_hex_returns_hex_kind() -> None:
    """FR-023 rule 1: cell present in study_area_hexes → (HEX, cell)."""
    c = _make_classifier()
    out = c.classify("872a307affffff7")
    assert out == CrossBorderClassification(dest_kind=NodeKind.HEX, dest_node_id="872a307affffff7")


def test_rule_2_domestic_block_routes_to_rest_of_usa() -> None:
    """FR-024 rule 2: block-code with state-prefix in domestic_states → rest_of_usa."""
    c = _make_classifier()
    # 39 = Ohio (Toledo). 15-digit block code.
    out = c.classify("390951234567890")
    assert out.dest_kind == NodeKind.EXTERNAL
    assert out.dest_node_id == "rest_of_usa"


def test_rule_3_non_domestic_state_prefix_routes_to_canada() -> None:
    """FR-023 rule 3: block-code with state-prefix NOT in domestic_states → canada."""
    c = _make_classifier()
    # 99 is outside the US FIPS state code set → routes to canada.
    out = c.classify("990001234567890")
    assert out.dest_kind == NodeKind.EXTERNAL
    assert out.dest_node_id == "canada"


def test_rule_4_unrecognized_format_falls_back_to_rest_of_usa() -> None:
    """FR-028 rule 4: unrecognized format → rest_of_usa + audit-log warning."""
    c = _make_classifier()
    out = c.classify("not-a-block-code")
    assert out.dest_node_id == "rest_of_usa"
    assert out.dest_kind == NodeKind.EXTERNAL


def test_constructor_rejects_empty_sets() -> None:
    """Constructor MUST raise ValueError on empty mandatory frozensets."""
    with pytest.raises(ValueError, match="study_area_hexes"):
        _make_classifier(study_area_hexes=frozenset())
    with pytest.raises(ValueError, match="study_area_states"):
        _make_classifier(study_area_states=frozenset())
    with pytest.raises(ValueError, match="domestic_states"):
        _make_classifier(domestic_states=frozenset())


def test_constructor_rejects_invalid_state_format() -> None:
    """Constructor MUST reject non-2-digit FIPS codes in either state set."""
    with pytest.raises(ValueError, match="2-digit FIPS"):
        _make_classifier(study_area_states=frozenset(["Michigan"]))
    with pytest.raises(ValueError, match="2-digit FIPS"):
        _make_classifier(domestic_states=frozenset(["Michigan"]))


def test_constructor_rejects_non_subset_relationship() -> None:
    """Constructor MUST require domestic_states ⊇ study_area_states."""
    with pytest.raises(ValueError, match="superset"):
        _make_classifier(
            study_area_states=frozenset(["26"]),
            domestic_states=frozenset(["01", "02"]),
        )


def test_unmapped_fallback_emits_audit_only_once_per_dest(caplog) -> None:  # type: ignore[no-untyped-def]
    """FR-028: one audit log entry per unique unmapped destination per session."""
    c = _make_classifier()
    with caplog.at_level("WARNING"):
        c.classify("invalid-1")
        c.classify("invalid-1")  # repeat — should not produce a second warning
        c.classify("invalid-2")
    warnings = [r for r in caplog.records if "unmapped LODES destination" in r.getMessage()]
    assert len(warnings) == 2  # one for invalid-1, one for invalid-2 — not three
