"""Tests for the declared liveness registry (correct-but-inert / never-consumed).

The registry is the *declared* half of the two liveness sensors: every output a
production producer stamps is either claimed by at least one production consumer
file, or explicitly declared dormant WITH A REASON. There is no third state —
that is the whole point of the class this gate exists to catch.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.sentinels.liveness.registry import LIVENESS_ROWS, LivenessRow

pytestmark = pytest.mark.unit


def test_registry_declares_the_known_producers() -> None:
    """The seeded rows cover the outputs this program investigated."""
    names = {row.name for row in LIVENESS_ROWS}
    assert {
        "price_divergence",
        "market_balance",
        "pole_readings",
        "national_financial",
        "ground_rent_path_a",
        "fictitious_capital_stock",
        "debt_spiral_threshold",
        "fundamental_theorem",
        "wealth_subsistence_ratio",
        "surplus_strategy_ratio",
    } <= names


def test_every_row_is_live_or_dormant_with_a_reason() -> None:
    """No row may be silently output-with-no-reader — that IS the error class."""
    for row in LIVENESS_ROWS:
        assert row.consumer_files or row.dormant_reason, row.name


def test_pole_readings_is_the_declared_dormant_row() -> None:
    """``pole_readings`` is a live producer with zero production readers (spec 3.7)."""
    row = next(r for r in LIVENESS_ROWS if r.name == "pole_readings")
    assert row.consumer_files == ()
    assert "sentinel" in row.dormant_reason.lower()


def test_fundamental_theorem_is_consumed_by_the_economy_projection() -> None:
    """``fundamental_theorem`` (Vol I U2) is surfaced by the T3 economy dossier.

    Formerly a declared, reasoned dormancy (graph-attribute-only, same as
    ``pole_readings``/``market_balance``); closed out by T3 U2's ADR109 W-P
    wiring motion — ``babylon.projection.economy.project_economy`` is now a
    genuine production reader, not merely a dev-time probe.
    """
    row = next(r for r in LIVENESS_ROWS if r.name == "fundamental_theorem")
    assert row.consumer_files == ("src/babylon/projection/economy.py",)
    assert "veil" in row.material_relation.lower()


def test_vol1_u6_ratio_rows_are_consumed_by_the_opposition_catalog() -> None:
    """``wealth_subsistence_ratio``/``surplus_strategy_ratio`` (U6) feed catalog.py."""
    names = {"wealth_subsistence_ratio", "surplus_strategy_ratio"}
    for row in LIVENESS_ROWS:
        if row.name in names:
            assert row.consumer_files == ("src/babylon/domain/dialectics/instances/catalog.py",)


def test_row_rejects_output_with_neither_consumer_nor_reason() -> None:
    """A row that is neither consumed nor declared dormant is refused at import."""
    with pytest.raises(ValidationError, match="dormant_reason"):
        LivenessRow(
            name="orphan",
            producer_file="src/babylon/engine/systems/market_scissors.py",
            producer_symbol="MarketScissorsSystem",
            output_symbol="orphan_output",
            consumer_files=(),
            material_relation="none",
        )


def test_row_rejects_a_non_python_producer_path() -> None:
    """Producer/consumer paths must be ``.py`` source the AST sensors can read."""
    with pytest.raises(ValidationError, match=r"\.py"):
        LivenessRow(
            name="bad_path",
            producer_file="src/babylon/engine/systems/market_scissors.txt",
            producer_symbol="MarketScissorsSystem",
            output_symbol="x",
            consumer_files=("web/game/engine_bridge.py",),
            material_relation="none",
        )


def test_row_rejects_a_non_python_consumer_path() -> None:
    """A consumer path must also be ``.py`` — the sensor parses it."""
    with pytest.raises(ValidationError, match=r"\.py"):
        LivenessRow(
            name="bad_consumer",
            producer_file="src/babylon/engine/systems/market_scissors.py",
            producer_symbol="MarketScissorsSystem",
            output_symbol="x",
            consumer_files=("web/game/engine_bridge.ts",),
            material_relation="none",
        )
