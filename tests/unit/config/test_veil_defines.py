"""VeilDefines contract — the Veil of Money's tier-gate thresholds (D7, spec-117 §5d).

Pins the two doctrine-node-id thresholds that gate the veil's progressive
disclosure tiers (I-15 calibration: ``class_consciousness`` is the free root,
reachable tick 1 at any cadre_level; ``trade_unionism`` costs 25 TL, reachable
at cadre_level=0.25 — the nationwide Cadre Council seed — by tick ~500 of a
520-tick campaign; see ``web/game/veil.py``'s module docstring for the full
arithmetic). Field-level bounds only — the "these ids must name real,
non-trap tree nodes" invariant lives in ``tests/unit/web/test_veil.py``
(that check needs the domain doctrine tree, which ``config.defines`` may not
import — Program 14 layering: ``config`` sits below ``domain``).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines import VeilDefines

pytestmark = pytest.mark.unit


class TestVeilDefinesDefaults:
    def test_tier_thresholds_default(self) -> None:
        d = VeilDefines()
        assert d.tier1_doctrine_node_id == "class_consciousness"
        assert d.tier2_doctrine_node_id == "trade_unionism"

    def test_frozen(self) -> None:
        d = VeilDefines()
        with pytest.raises(ValidationError):
            d.tier1_doctrine_node_id = "other"  # type: ignore[misc]


class TestVeilDefinesBounds:
    def test_rejects_empty_tier1_id(self) -> None:
        with pytest.raises(ValidationError):
            VeilDefines(tier1_doctrine_node_id="")

    def test_rejects_empty_tier2_id(self) -> None:
        with pytest.raises(ValidationError):
            VeilDefines(tier2_doctrine_node_id="")
