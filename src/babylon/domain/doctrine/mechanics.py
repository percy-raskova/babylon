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

from babylon.models.enums.doctrine import DoctrineTag


class DoctrineExpressionError(ValueError):
    """A ``trap_condition`` string is malformed or references an unknown tag."""


#: Comparison operators the DSL supports, longest-token-first for the tokenizer.
_COMPARISONS: dict[str, Callable[[int, int], bool]] = {
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

    def __init__(self, tokens: list[str], tags: Mapping[DoctrineTag, int], expr: str) -> None:
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


def evaluate_trap_condition(condition: str, tags: Mapping[DoctrineTag, int]) -> bool:
    """Return whether ``condition`` holds against the current doctrine ``tags``.

    :param condition: A ``trap_condition`` expression in the DSL documented in
        this module's docstring.
    :param tags: Current per-tag totals; an absent tag reads as ``0``.
    :returns: ``True`` iff the trap's condition is satisfied (i.e. it should fire).
    :raises DoctrineExpressionError: if ``condition`` is empty, malformed, or
        names a tag/operator/literal the grammar does not accept.
    """
    return _Parser(_tokenize(condition), tags, condition).parse()


__all__ = ["DoctrineExpressionError", "evaluate_trap_condition"]
