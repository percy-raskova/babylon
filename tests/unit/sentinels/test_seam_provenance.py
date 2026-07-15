"""Seam Sensor 3 (provenance) — emission-honesty check + its efficacy proof.

Verifies the AST emission-diff both (1) reports the real declared-but-unemitted
``AdminFeatureProperties`` fields on the live tree, and (2) is not vacuous: it
reds on a planted phantom, excludes a group-key normalisation, and fails loud
(never silently empty) when the emitter or interface it reads has moved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.seam.provenance import (
    _declared_interface_fields,
    _emitted_property_keys,
    check_admin_feature_emission,
)

pytestmark = pytest.mark.unit

# A minimal emitter whose feature.properties emits only ``group_key`` + ``heat``,
# with the same ``group_key_map`` normalisation the real bridge uses.
_FAKE_EMITTER = """
def _aggregate_hex_features(hex_states, zoom):
    group_key_map = {"county": "county_fips", "state": "state_fips"}
    return [{"type": "Feature", "properties": {"group_key": key, "heat": 1.0}}]
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_live_check_reports_the_real_phantoms() -> None:
    """On the live tree the check names the genuine phantoms and no normalisation."""
    findings = check_admin_feature_emission()
    joined = "\n".join(findings)
    # consciousness/wealth are declared by AdminFeatureProperties, never emitted.
    assert any("consciousness" in f for f in findings)
    assert any("wealth" in f for f in findings)
    # county_fips IS declared-but-not-literally-emitted, but it is a group_key
    # normalisation — it must NOT be flagged (that would be a false positive).
    assert "county_fips" not in joined


def test_reds_on_a_planted_phantom(tmp_path: Path) -> None:
    """A declared field with no emission and no normalisation is flagged (efficacy)."""
    engine = _write(tmp_path, "bridge.py", _FAKE_EMITTER)
    ts = _write(
        tmp_path,
        "game.ts",
        "export interface AdminFeatureProperties {\n"
        "  group_key: string;\n"
        "  heat: number;\n"
        "  totally_fake_field: number;\n"
        "}\n",
    )
    findings = check_admin_feature_emission(engine_path=engine, ts_path=ts)
    assert len(findings) == 1
    assert "totally_fake_field" in findings[0]


def test_group_key_normalisation_is_not_flagged(tmp_path: Path) -> None:
    """A declared field that is a group_key_map value is accounted for, not a phantom."""
    engine = _write(tmp_path, "bridge.py", _FAKE_EMITTER)
    ts = _write(
        tmp_path,
        "game.ts",
        "export interface AdminFeatureProperties {\n"
        "  group_key: string;\n"
        "  heat: number;\n"
        "  county_fips: string;\n"  # normalised into group_key by the emitter
        "}\n",
    )
    assert check_admin_feature_emission(engine_path=engine, ts_path=ts) == []


def test_missing_interface_is_loud_not_empty(tmp_path: Path) -> None:
    """A renamed/removed interface raises (III.11), never silently passes clean."""
    ts = _write(tmp_path, "game.ts", "export interface SomethingElse { x: number; }\n")
    with pytest.raises(SentinelCheckError):
        _declared_interface_fields(ts, "AdminFeatureProperties")


def test_moved_emitter_is_loud_not_empty(tmp_path: Path) -> None:
    """An emitter with no literal properties dict raises, never reports empty."""
    engine = _write(tmp_path, "bridge.py", "def _aggregate_hex_features(a, b):\n    return []\n")
    with pytest.raises(SentinelCheckError):
        _emitted_property_keys(engine, "_aggregate_hex_features")
