"""Tests for babylon.domain.doctrine.tags (Phase 0 foundation).

Golden behavioral traces (Constitution III.12 rewrite test): these pin the
MVP tag-calculation formula from
``ai/epochs/epoch3/doctrine-tree-mvp.yaml`` (``mvp_mechanics.tag_calculation``)
against the corpus's own worked example plus the reformist/scientific
paths that drive the trap/goal thresholds — this is the behavioral
contract the rest of Wave 6 (trap detection, engine wiring) builds on.

All numeric expectations here were independently verified by hand against
the corpus deltas before being encoded as assertions.
"""

from __future__ import annotations

import pytest

from babylon.domain.doctrine.loader import load_doctrine_tree
from babylon.domain.doctrine.tags import compute_tags, starting_tags
from babylon.models.entities.doctrine import DoctrineNode, DoctrineTree
from babylon.models.enums.doctrine import DoctrineTag


@pytest.fixture(scope="module")
def tree() -> DoctrineTree:
    """The real, validated MVP Doctrine Tree."""
    return load_doctrine_tree()


@pytest.mark.math
class TestComputeTagsGoldenTraces:
    """Golden traces from the corpus's own worked example and 2 paths."""

    def test_worked_example_from_corpus(self, tree: DoctrineTree) -> None:
        """The yaml's own worked example (mvp_mechanics.tag_calculation.example).

        Acquired: class_consciousness, trade_unionism, democratic_centralism
        CLASS_ANALYSIS = 1 + 0 + 2 = 3
        MASS_LINK      = 0 + 2 + 1 = 3
        MILITANCY      = 0 + 0 + 1 = 1
        """
        result = compute_tags(
            tree,
            ["class_consciousness", "trade_unionism", "democratic_centralism"],
        )
        assert result[DoctrineTag.CLASS_ANALYSIS] == 3
        assert result[DoctrineTag.MASS_LINK] == 3
        assert result[DoctrineTag.MILITANCY] == 1

    def test_reformist_path_drives_class_analysis_to_the_trap_threshold(
        self, tree: DoctrineTree
    ) -> None:
        """The full reformist path clamps CLASS_ANALYSIS to <= 0.

        Acquired: class_consciousness, trade_unionism, electoral_socialism,
        coalition_politics.
        CLASS_ANALYSIS raw = 1 + 0 - 1 - 2 = -2, clamped to 0.
        MILITANCY raw = 0 + 0 - 2 + 0 = -2, clamped to 0.
        Both satisfy liquidationism's trap_condition
        "CLASS_ANALYSIS <= 0 AND MILITANCY <= 0" (evaluator itself is
        gated engine work; this test only pins the tag math).
        """
        result = compute_tags(
            tree,
            [
                "class_consciousness",
                "trade_unionism",
                "electoral_socialism",
                "coalition_politics",
            ],
        )
        assert result[DoctrineTag.CLASS_ANALYSIS] == 0
        assert result[DoctrineTag.CLASS_ANALYSIS] <= 0
        assert result[DoctrineTag.MILITANCY] <= 0

    def test_scientific_path_reaches_united_front_with_high_class_analysis(
        self, tree: DoctrineTree
    ) -> None:
        """The full scientific path yields a high, un-trapped CLASS_ANALYSIS.

        Acquired: class_consciousness, trade_unionism, democratic_centralism,
        mass_line, united_front.
        CLASS_ANALYSIS = 1 + 0 + 2 + 1 + 2 = 6
        MASS_LINK      = 0 + 2 + 1 + 2 + 2 = 7
        MILITANCY      = 0 + 0 + 1 + 0 + 1 = 2
        """
        result = compute_tags(
            tree,
            [
                "class_consciousness",
                "trade_unionism",
                "democratic_centralism",
                "mass_line",
                "united_front",
            ],
        )
        assert result[DoctrineTag.CLASS_ANALYSIS] == 6
        assert result[DoctrineTag.MASS_LINK] == 7
        assert result[DoctrineTag.MILITANCY] == 2
        # Well clear of any trap threshold (all traps require <= 0 on some tag).
        assert result[DoctrineTag.CLASS_ANALYSIS] > 0

    def test_insurrectionist_path_clamps_mass_link_at_zero(self, tree: DoctrineTree) -> None:
        """The full insurrectionist path drives MASS_LINK below 0, clamped to 0.

        Acquired: class_consciousness, trade_unionism, armed_vanguard,
        urban_guerrilla, adventurism.
        MASS_LINK raw = 0 + 2 - 1 - 2 - 4 = -5, clamped to 0 -- satisfies
        adventurism's trap_condition "MASS_LINK <= 0".
        """
        result = compute_tags(
            tree,
            [
                "class_consciousness",
                "trade_unionism",
                "armed_vanguard",
                "urban_guerrilla",
                "adventurism",
            ],
        )
        assert result[DoctrineTag.MASS_LINK] == 0

    def test_empty_acquisition_yields_all_zeros(self, tree: DoctrineTree) -> None:
        """No acquired nodes means no contributions at all."""
        result = compute_tags(tree, [])
        assert result == {
            DoctrineTag.CLASS_ANALYSIS: 0,
            DoctrineTag.MASS_LINK: 0,
            DoctrineTag.MILITANCY: 0,
        }

    def test_unknown_acquired_id_raises_key_error(self, tree: DoctrineTree) -> None:
        """An id not present in the tree is a loud failure, not a silent skip."""
        with pytest.raises(KeyError):
            compute_tags(tree, ["not_a_real_node"])


@pytest.mark.math
class TestComputeTagsClampingIsSynthetic:
    """Clamp bounds, demonstrated with small hand-built trees (not the corpus)."""

    def test_clamps_at_upper_bound_ten(self) -> None:
        node = DoctrineNode(
            id="overload",
            name="Overload",
            tier=0,
            description="d",
            cost_tl=0,
            tag_deltas={DoctrineTag.MILITANCY: 15},
        )
        tree_fixture = DoctrineTree(nodes={"overload": node}, root_id="overload")
        result = compute_tags(tree_fixture, ["overload"])
        assert result[DoctrineTag.MILITANCY] == 10
        assert result[DoctrineTag.CLASS_ANALYSIS] == 0

    def test_clamps_at_lower_bound_zero(self) -> None:
        node = DoctrineNode(
            id="collapse",
            name="Collapse",
            tier=0,
            description="d",
            cost_tl=0,
            tag_deltas={DoctrineTag.MASS_LINK: -20},
        )
        tree_fixture = DoctrineTree(nodes={"collapse": node}, root_id="collapse")
        result = compute_tags(tree_fixture, ["collapse"])
        assert result[DoctrineTag.MASS_LINK] == 0


@pytest.mark.math
class TestStartingTags:
    """starting_tags() returns the corpus's mvp_tags.*.starting_value verbatim."""

    def test_starting_values(self) -> None:
        assert starting_tags() == {
            DoctrineTag.CLASS_ANALYSIS: 1,
            DoctrineTag.MASS_LINK: 1,
            DoctrineTag.MILITANCY: 0,
        }

    def test_returns_a_fresh_copy_each_call(self) -> None:
        """Callers mutating the returned dict must not affect other callers."""
        first = starting_tags()
        first[DoctrineTag.MILITANCY] = 99
        second = starting_tags()
        assert second[DoctrineTag.MILITANCY] == 0
