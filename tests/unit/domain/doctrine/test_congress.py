"""Unit 5 — the Party Congress (owner slate ruling 5 + history-sweep DT-5).

The congress convenes every ``congress_interval_ticks`` and resolves the
purge of an opposed element (a held trap line) through a **weighted
seeded-RNG draw**: tag-vector deltas since the last congress bias the odds
(Yugoslavia 1948 — material divergence predicts direction), but a nonzero
contingent term stays live at ANY delta (Lushan 1959 / Gang of Four 1976 —
the decisive information was never in the observable state). Trap escape is
``self_criticism`` at ``trap_escape_tl`` (slate ruling 6): the congress
SPENDS the theoretical labor on the attempt — a failed rectification still
consumed the cadre time (the proposal's "opportunity-cost draw on cadre
time, not a free currency").
"""

from __future__ import annotations

import pytest

from babylon.config.defines.doctrine import DoctrineDefines
from babylon.domain.doctrine import load_doctrine_tree
from babylon.domain.doctrine.congress import (
    held_sprung_traps,
    purge_probability,
    run_congress,
    tag_delta_score,
)
from babylon.models.entities.doctrine import DoctrineTree
from babylon.models.enums.doctrine import DoctrineTag

pytestmark = pytest.mark.unit


@pytest.fixture
def tree() -> DoctrineTree:
    return load_doctrine_tree()


@pytest.fixture
def defines() -> DoctrineDefines:
    return DoctrineDefines()


class TestTagDeltaScore:
    def test_growth_is_positive_decline_negative(self) -> None:
        current = {DoctrineTag.CLASS_ANALYSIS: 3.0, DoctrineTag.MASS_LINK: 1.0}
        snapshot = {DoctrineTag.CLASS_ANALYSIS: 1.0, DoctrineTag.MASS_LINK: 2.0}
        # (3-1) + (1-2) = +1.0
        assert tag_delta_score(current, snapshot) == pytest.approx(1.0)

    def test_missing_keys_baseline_zero_on_both_sides(self) -> None:
        current = {DoctrineTag.MILITANCY: 2.0}
        snapshot = {DoctrineTag.MASS_LINK: 0.5}
        # militancy grew from 0 (+2.0); mass_link fell to 0 (-0.5)
        assert tag_delta_score(current, snapshot) == pytest.approx(1.5)

    def test_empty_snapshot_means_all_growth(self) -> None:
        current = {DoctrineTag.CLASS_ANALYSIS: 1.0}
        assert tag_delta_score(current, {}) == pytest.approx(1.0)


class TestPurgeProbability:
    def test_zero_delta_is_even_odds(self, defines: DoctrineDefines) -> None:
        assert purge_probability(0.0, defines) == pytest.approx(0.5)

    def test_positive_delta_raises_odds_linearly(self, defines: DoctrineDefines) -> None:
        expected = 0.5 + defines.congress_delta_weight * 1.0
        assert purge_probability(1.0, defines) == pytest.approx(expected)

    def test_contingency_floor_holds_both_ways(self, defines: DoctrineDefines) -> None:
        # DT-5: "a nonzero contingent term stays live even at extreme deltas."
        floor = defines.congress_contingency_floor
        assert purge_probability(1e9, defines) == pytest.approx(1.0 - floor)
        assert purge_probability(-1e9, defines) == pytest.approx(floor)
        assert 0.0 < floor < 0.5


class TestHeldSprungTraps:
    def test_lists_held_traps_id_sorted(self, tree: DoctrineTree) -> None:
        acquired = (tree.root_id, "urban_guerrilla", "adventurism", "liquidationism")
        assert held_sprung_traps(tree, acquired) == ("adventurism", "liquidationism")

    def test_empty_when_no_trap_held(self, tree: DoctrineTree) -> None:
        assert held_sprung_traps(tree, (tree.root_id, "trade_unionism")) == ()


class TestRunCongress:
    def test_no_trap_updates_snapshot_only(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        tags = {DoctrineTag.CLASS_ANALYSIS: 2.0}
        result = run_congress(
            acquired=(tree.root_id,),
            theoretical_labor=500.0,
            tags=tags,
            snapshot={},
            tree=tree,
            defines=defines,
            roll=0.0,
        )
        assert result.attempted_trap_id is None
        assert result.escaped is False
        assert result.acquired == (tree.root_id,)
        assert result.theoretical_labor == 500.0
        assert result.snapshot == tags

    def test_unaffordable_purge_is_not_attempted(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        result = run_congress(
            acquired=(tree.root_id, "urban_guerrilla", "adventurism"),
            theoretical_labor=defines.trap_escape_tl - 1.0,
            tags={},
            snapshot={},
            tree=tree,
            defines=defines,
            roll=0.0,
        )
        assert result.attempted_trap_id is None
        assert result.theoretical_labor == defines.trap_escape_tl - 1.0
        assert "adventurism" in result.acquired

    def test_successful_purge_removes_trap_reverses_deltas_spends_tl(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        trap = tree.nodes["adventurism"]
        tags = {DoctrineTag.MILITANCY: 5.0, DoctrineTag.CLASS_ANALYSIS: 1.0}
        result = run_congress(
            acquired=(tree.root_id, "urban_guerrilla", "adventurism"),
            theoretical_labor=400.0,
            tags=tags,
            snapshot=dict(tags),  # zero delta => P = 0.5; roll 0.0 always succeeds
            tree=tree,
            defines=defines,
            roll=0.0,
        )
        assert result.attempted_trap_id == "adventurism"
        assert result.escaped is True
        assert "adventurism" not in result.acquired
        assert result.theoretical_labor == pytest.approx(400.0 - defines.trap_escape_tl)
        # self-criticism REVERSES the trap's tag contribution
        for tag, delta in trap.tag_deltas.items():
            assert result.doctrine_tags[tag] == pytest.approx(tags.get(tag, 0.0) - delta)
        # the new snapshot is the post-congress tag state
        assert result.snapshot == result.doctrine_tags

    def test_failed_purge_keeps_trap_but_spends_the_attempt(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        tags = {DoctrineTag.MILITANCY: 5.0}
        result = run_congress(
            acquired=(tree.root_id, "urban_guerrilla", "adventurism"),
            theoretical_labor=400.0,
            tags=tags,
            snapshot=dict(tags),  # zero delta => P = 0.5; roll 0.99 always fails
            tree=tree,
            defines=defines,
            roll=0.99,
        )
        assert result.attempted_trap_id == "adventurism"
        assert result.escaped is False
        assert "adventurism" in result.acquired
        assert result.theoretical_labor == pytest.approx(400.0 - defines.trap_escape_tl)
        assert result.doctrine_tags == tags

    def test_one_purge_per_congress_first_trap_by_id(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        result = run_congress(
            acquired=(tree.root_id, "urban_guerrilla", "adventurism", "liquidationism"),
            theoretical_labor=1000.0,
            tags={},
            snapshot={},
            tree=tree,
            defines=defines,
            roll=0.0,
        )
        # id-sorted: adventurism before liquidationism; only one attempted
        assert result.attempted_trap_id == "adventurism"
        assert "liquidationism" in result.acquired

    def test_pure_and_deterministic(self, tree: DoctrineTree, defines: DoctrineDefines) -> None:
        kwargs = {
            "acquired": (tree.root_id, "urban_guerrilla", "adventurism"),
            "theoretical_labor": 400.0,
            "tags": {DoctrineTag.MILITANCY: 5.0},
            "snapshot": {DoctrineTag.MILITANCY: 4.0},
            "tree": tree,
            "defines": defines,
            "roll": 0.3,
        }
        assert run_congress(**kwargs) == run_congress(**kwargs)
