"""DoctrineSystem pure mechanics (Unit 3) — trap evaluation and helpers.

All functions here are pure (no graph, no I/O): the TDD-tested core the
DoctrineSystem (Unit 4) drives. The centrepiece is :func:`evaluate_trap_condition`,
a SAFE boolean-expression evaluator over doctrine tag totals. It NEVER calls
:func:`eval`; it tokenises and walks a small, fixed grammar so a malformed or
hostile ``trap_condition`` string can only ever raise :class:`DoctrineExpressionError`,
never execute code.

Grammar (precedence low→high), matching the corpus's ``trap_condition`` DSL and
generalising it for later tree tiers::

    or_expr    := and_expr (OR and_expr)*
    and_expr   := not_expr (AND not_expr)*
    not_expr   := NOT not_expr | primary
    primary    := '(' or_expr ')' | comparison
    comparison := TAG OP INT          # OP ∈ {<=, >=, ==, !=, <, >}

``TAG`` is a :class:`~babylon.models.enums.doctrine.DoctrineTag` *name*
(e.g. ``CLASS_ANALYSIS``); its value is looked up in the supplied totals map,
with an ABSENT tag reading as ``0`` (honest-null: no accumulated strength).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from babylon.models.entities.doctrine import DoctrineTree
from babylon.models.enums.doctrine import DoctrineTag


class DoctrineExpressionError(ValueError):
    """A ``trap_condition`` string is malformed or references an unknown tag."""


#: Comparison operators the DSL supports, longest-token-first for the tokenizer.
#: Left operand is a tag total (``float`` accumulator or ``int``); right is the
#: literal ``int`` threshold from the condition string.
_COMPARISONS: dict[str, Callable[[float, int], bool]] = {
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
}

#: One token: a comparison op, a paren, a keyword, a TAG name, or an integer.
#: Alternation order matters — multi-char ops and keywords precede the bare
#: ``[A-Z_]+`` tag pattern so ``<=`` / ``AND`` are never mis-split.
_TOKEN_RE = re.compile(r"<=|>=|==|!=|<|>|\(|\)|AND|OR|NOT|[A-Z_]+|-?\d+")


def _tokenize(expr: str) -> list[str]:
    """Split ``expr`` into DSL tokens, rejecting any unrecognised character.

    :param expr: The raw ``trap_condition`` string.
    :returns: The ordered token list.
    :raises DoctrineExpressionError: on any non-whitespace character that is not
        part of a valid token (e.g. a lowercase literal, a stray symbol).
    """
    tokens = _TOKEN_RE.findall(expr)
    leftover = _TOKEN_RE.sub("", expr).strip()
    if leftover:
        raise DoctrineExpressionError(f"unrecognized characters {leftover!r} in {expr!r}")
    return tokens


def _resolve_tag(token: str, expr: str) -> DoctrineTag:
    """Resolve a ``TAG`` token to its :class:`DoctrineTag`, or fail loudly."""
    try:
        return DoctrineTag[token]
    except KeyError:
        raise DoctrineExpressionError(f"unknown doctrine tag {token!r} in {expr!r}") from None


class _Parser:
    """Recursive-descent parser/evaluator over a tokenised trap condition.

    Termination is trivially provable: every rule that recurses first consumes
    at least one token via :meth:`_advance` (``NOT`` before :meth:`_not`, ``(``
    before :meth:`_or`), and the index ``_i`` moves monotonically toward the
    fixed ``len(tokens)`` — so no rule can loop or recurse without shrinking the
    remaining input.
    """

    def __init__(self, tokens: list[str], tags: Mapping[DoctrineTag, float], expr: str) -> None:
        self._tokens = tokens
        self._i = 0
        self._tags = tags
        self._expr = expr

    def _peek(self) -> str | None:
        return self._tokens[self._i] if self._i < len(self._tokens) else None

    def _advance(self) -> str:
        tok = self._peek()
        if tok is None:
            raise DoctrineExpressionError(f"unexpected end of condition {self._expr!r}")
        self._i += 1
        return tok

    def parse(self) -> bool:
        """Parse+evaluate the full expression, rejecting empty / trailing input."""
        if not self._tokens:
            raise DoctrineExpressionError(f"empty trap condition {self._expr!r}")
        value = self._or()
        if self._i != len(self._tokens):
            raise DoctrineExpressionError(f"trailing tokens in {self._expr!r}")
        return value

    def _or(self) -> bool:
        value = self._and()
        while self._peek() == "OR":
            self._advance()
            value = self._and() or value
        return value

    def _and(self) -> bool:
        value = self._not()
        while self._peek() == "AND":
            self._advance()
            value = self._not() and value
        return value

    def _not(self) -> bool:
        if self._peek() == "NOT":
            self._advance()
            return not self._not()
        return self._primary()

    def _primary(self) -> bool:
        if self._peek() == "(":
            self._advance()
            value = self._or()
            closer = self._advance()
            if closer != ")":
                raise DoctrineExpressionError(f"expected ')' , got {closer!r} in {self._expr!r}")
            return value
        return self._comparison()

    def _comparison(self) -> bool:
        tag = _resolve_tag(self._advance(), self._expr)
        op_token = self._advance()
        op = _COMPARISONS.get(op_token)
        if op is None:
            raise DoctrineExpressionError(
                f"expected comparison operator, got {op_token!r} in {self._expr!r}"
            )
        int_token = self._advance()
        try:
            threshold = int(int_token)
        except ValueError:
            raise DoctrineExpressionError(
                f"expected integer literal, got {int_token!r} in {self._expr!r}"
            ) from None
        return op(self._tags.get(tag, 0), threshold)


def evaluate_trap_condition(condition: str, tags: Mapping[DoctrineTag, float]) -> bool:
    """Return whether ``condition`` holds against the current doctrine ``tags``.

    :param condition: A ``trap_condition`` expression in the DSL documented in
        this module's docstring.
    :param tags: Current per-tag totals; an absent tag reads as ``0``.
    :returns: ``True`` iff the trap's condition is satisfied (i.e. it should fire).
    :raises DoctrineExpressionError: if ``condition`` is empty, malformed, or
        names a tag/operator/literal the grammar does not accept.
    """
    return _Parser(_tokenize(condition), tags, condition).parse()


def can_acquire(
    tree: DoctrineTree,
    acquired_ids: tuple[str, ...],
    node_id: str,
    theoretical_labor: float,
) -> bool:
    """Report whether ``node_id`` may be deliberately acquired right now.

    A node is acquirable iff it is (1) not already held, (2) not a trap (traps are
    *fallen into* when their ``trap_condition`` fires, never chosen), (3) unlocked
    — every parent already held (the free root has no parents, so it is always
    unlocked), and (4) affordable — its ``cost_tl`` is within the org's current
    theoretical labour.

    :param tree: The doctrine tree.
    :param acquired_ids: Node ids the org already holds.
    :param node_id: The candidate node.
    :param theoretical_labor: The org's current theoretical-labour balance.
    :returns: ``True`` iff all four gates pass.
    :raises KeyError: if ``node_id`` is not a node in ``tree`` (a caller bug, not
        a "cannot acquire" answer — fail loud).
    """
    node = tree.nodes[node_id]
    if node_id in acquired_ids:
        return False
    if node.is_trap:
        return False
    held = set(acquired_ids)
    if not all(parent in held for parent in node.parents):
        return False
    return node.cost_tl <= theoretical_labor


def acquire(acquired_ids: tuple[str, ...], node_id: str) -> tuple[str, ...]:
    """Return ``acquired_ids`` with ``node_id`` appended (idempotent, order-stable).

    Order is preserved (acquisition sequence is deterministic history); a repeat
    acquisition is a no-op rather than a duplicate.
    """
    if node_id in acquired_ids:
        return acquired_ids
    return (*acquired_ids, node_id)


def accrue_theoretical_labor(surplus: float, study_allocation: float) -> float:
    """Theoretical labour gained this tick = ``max(0, surplus) × clamp(allocation)``.

    :param surplus: The org's material surplus this tick (negative surplus accrues
        nothing — you cannot study on an empty stomach).
    :param study_allocation: Fraction of surplus routed to study; clamped to
        ``[0, 1]`` so an out-of-band mod value degrades safely rather than
        producing negative or super-unit labour.
    :returns: The non-negative theoretical-labour increment.
    """
    if surplus <= 0.0:
        return 0.0
    allocation = min(1.0, max(0.0, study_allocation))
    return surplus * allocation


def decay_tags(tags: Mapping[DoctrineTag, float], decay_rate: float) -> dict[DoctrineTag, float]:
    """Multiplicatively decay every accumulated tag strength by ``decay_rate``.

    Doctrine tag strength is a decaying accumulator (owner ruling 3: 0.55%/tick),
    not a pure sum — unexercised theory erodes. This is the per-tick erosion step;
    acquisitions add ``tag_deltas`` on top elsewhere.

    :param tags: Current per-tag float strengths.
    :param decay_rate: Per-tick fractional decay (``0.0055`` = 0.55%); a rate of
        ``0`` is the identity.
    :returns: A new map with each strength scaled by ``(1 - decay_rate)``.
    """
    factor = 1.0 - decay_rate
    return {tag: value * factor for tag, value in tags.items()}


__all__ = [
    "DoctrineExpressionError",
    "accrue_theoretical_labor",
    "acquire",
    "can_acquire",
    "decay_tags",
    "evaluate_trap_condition",
]
