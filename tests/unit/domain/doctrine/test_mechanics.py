"""Unit tests for the DoctrineSystem pure mechanics (Unit 3).

The crux is :func:`evaluate_trap_condition` — a SAFE boolean-expression evaluator
over doctrine tag totals (never :func:`eval`). The two real MVP trap conditions are
``"CLASS_ANALYSIS <= 0 AND MILITANCY <= 0"`` (liquidationism) and
``"MASS_LINK <= 0"`` (adventurism); the evaluator also supports the full phased
grammar (all six comparisons, AND/OR/NOT, parentheses) so later tree tiers need no
evaluator change.
"""

from __future__ import annotations

import pytest

from babylon.domain.doctrine.mechanics import (
    DoctrineExpressionError,
    evaluate_trap_condition,
)
from babylon.models.enums.doctrine import DoctrineTag

pytestmark = pytest.mark.unit

CA = DoctrineTag.CLASS_ANALYSIS
ML = DoctrineTag.MASS_LINK
MI = DoctrineTag.MILITANCY


class TestRealMvpConditions:
    """The two conditions actually shipped in doctrine_tree_mvp.json."""

    def test_adventurism_fires_when_mass_link_zero(self) -> None:
        assert evaluate_trap_condition("MASS_LINK <= 0", {ML: 0}) is True

    def test_adventurism_dormant_when_mass_link_positive(self) -> None:
        assert evaluate_trap_condition("MASS_LINK <= 0", {ML: 3}) is False

    def test_liquidationism_fires_when_both_zero(self) -> None:
        assert (
            evaluate_trap_condition("CLASS_ANALYSIS <= 0 AND MILITANCY <= 0", {CA: 0, MI: 0})
            is True
        )

    def test_liquidationism_dormant_when_one_positive(self) -> None:
        assert (
            evaluate_trap_condition("CLASS_ANALYSIS <= 0 AND MILITANCY <= 0", {CA: 0, MI: 5})
            is False
        )


class TestMissingTagIsZero:
    """A tag absent from the totals map contributes 0 (honest-null: absent = no
    accumulated strength, never a fabricated nonzero)."""

    def test_absent_tag_treated_as_zero_true(self) -> None:
        assert evaluate_trap_condition("MILITANCY <= 0", {}) is True

    def test_absent_tag_treated_as_zero_false(self) -> None:
        assert evaluate_trap_condition("MILITANCY >= 1", {}) is False


class TestFullGrammar:
    """Operators/keywords not in the MVP data but valid for later tiers."""

    @pytest.mark.parametrize(
        ("expr", "tags", "expected"),
        [
            ("CLASS_ANALYSIS >= 3", {CA: 3}, True),
            ("CLASS_ANALYSIS > 3", {CA: 3}, False),
            ("MASS_LINK < 2", {ML: 1}, True),
            ("MILITANCY == 4", {MI: 4}, True),
            ("MILITANCY != 4", {MI: 4}, False),
            ("MASS_LINK <= 0 OR MILITANCY <= 0", {ML: 5, MI: 0}, True),
            ("MASS_LINK <= 0 OR MILITANCY <= 0", {ML: 5, MI: 5}, False),
            ("NOT MASS_LINK <= 0", {ML: 3}, True),
            ("NOT MASS_LINK <= 0", {ML: 0}, False),
            (
                "(CLASS_ANALYSIS <= 0 OR MILITANCY <= 0) AND MASS_LINK <= 0",
                {CA: 0, MI: 5, ML: 0},
                True,
            ),
            (
                "(CLASS_ANALYSIS <= 0 OR MILITANCY <= 0) AND MASS_LINK <= 0",
                {CA: 5, MI: 5, ML: 0},
                False,
            ),
        ],
    )
    def test_grammar(self, expr: str, tags: dict[DoctrineTag, int], expected: bool) -> None:
        assert evaluate_trap_condition(expr, tags) is expected

    def test_and_binds_tighter_than_or(self) -> None:
        # A OR (B AND C): militancy>0 makes the AND clause false, so result rides
        # on the left OR operand (class_analysis <= 0).
        expr = "CLASS_ANALYSIS <= 0 OR MASS_LINK <= 0 AND MILITANCY <= 0"
        assert evaluate_trap_condition(expr, {CA: 0, ML: 0, MI: 5}) is True


class TestMalformedRaises:
    """A malformed condition must fail LOUDLY (never silently evaluate to a
    default) — a trap that silently never fires is a correctness hole."""

    @pytest.mark.parametrize(
        "expr",
        [
            "",
            "MASS_LINK <=",  # dangling operator
            "MASS_LINK 0",  # missing comparison
            "UNKNOWN_TAG <= 0",  # not a DoctrineTag
            "MASS_LINK <= zero",  # non-integer literal
            "MASS_LINK <= 0 AND",  # dangling AND
            "(MASS_LINK <= 0",  # unbalanced paren
        ],
    )
    def test_malformed_raises(self, expr: str) -> None:
        with pytest.raises(DoctrineExpressionError):
            evaluate_trap_condition(expr, {ML: 0})
