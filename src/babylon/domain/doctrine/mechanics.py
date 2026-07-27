"""DoctrineSystem pure mechanics (Unit 3) — trap evaluation and helpers.

All functions here are pure (no graph, no I/O): the TDD-tested core the
DoctrineSystem (Unit 4) drives. The centrepiece is :func:`evaluate_trap_condition`,
a SAFE boolean-expression evaluator over doctrine tag totals. It NEVER calls
:func:`eval`; it tokenises and walks a small, fixed grammar so a malformed or
hostile ``trap_condition`` string can only ever raise :class:`DoctrineExpressionError`,
never execute code.

Grammar (precedence low→high), matching the corpus's ``trap_condition`` DSL and
generalising it to measured practice for the reformist fork (P25 U11, ADR137)::

    or_expr    := and_expr (OR and_expr)*
    and_expr   := not_expr (AND not_expr)*
    not_expr   := NOT not_expr | primary
    primary    := '(' or_expr ')' | comparison
    comparison := VAR OP operand      # OP ∈ {<=, >=, ==, !=, <, >}
    operand    := INT | COEFF
    VAR        := TAG | PRACTICE
    COEFF      := '@' snake_case_name

``VAR`` is a :class:`~babylon.models.enums.doctrine.DoctrineTag` name
(``CLASS_ANALYSIS``) OR a :class:`~babylon.models.enums.doctrine.PracticeVariable`
name (``CO_OPTIVE_SHARE``), resolved TAG-FIRST; its value is read from the
supplied environment, with an ABSENT variable reading as ``0`` (honest-null: no
accumulated strength / no measured practice). ``COEFF`` is a ``@``-sigilled
coefficient name resolved against the supplied ``coeffs`` map (a ``GameDefines``
subset) — practice thresholds are DEFINES referenced by name, never magic
literals in the tree data (Constitution III.1; the-electoral-question.md §3.1).
Pure-tag ``INT`` conditions (the scientific/insurrectionist trunks) evaluate
identically to the pre-U11 grammar, so this generalisation is byte-inert.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from babylon.models.entities.doctrine import DoctrineTree
from babylon.models.enums.doctrine import DoctrineTag, PracticeVariable

#: A DSL variable: a doctrine tag total OR a measured-practice quantity. Kept
#: internal to this module (not a public model type) — the engine hands in one
#: merged ``Mapping[DoctrineVariable, float]`` per org per tick (P25 U11).
DoctrineVariable = DoctrineTag | PracticeVariable


class DoctrineExpressionError(ValueError):
    """A ``trap_condition`` string is malformed or names an unknown variable/coefficient."""


#: Comparison operators the DSL supports, longest-token-first for the tokenizer.
#: Left operand is a variable total (``float`` accumulator, practice measure, or
#: ``int``); right is either a literal ``int`` threshold or a ``@coeff`` float.
_COMPARISONS: dict[str, Callable[[float, float], bool]] = {
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
}

#: One token: a comparison op, a paren, a keyword, a ``@coeff`` reference, a VAR
#: name, or an integer. Alternation order matters — multi-char ops and keywords
#: precede the bare ``[A-Z_]+`` var pattern so ``<=`` / ``AND`` are never
#: mis-split; the ``@``-sigil coeff is unambiguous (no other token starts ``@``).
_TOKEN_RE = re.compile(r"<=|>=|==|!=|<|>|\(|\)|AND|OR|NOT|@[a-z_][a-z0-9_]*|[A-Z_]+|-?\d+")


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


def _resolve_variable(token: str, expr: str) -> DoctrineVariable:
    """Resolve a ``VAR`` token to a :data:`DoctrineVariable`, or fail loudly.

    Tag-first, then practice: a token names a :class:`DoctrineTag` if it is one,
    otherwise a :class:`PracticeVariable`. The two namespaces are disjoint over
    member names (guarded by ``test_doctrine.py::TestPracticeVariableVocabulary``),
    so the order only fixes the error message, never the resolution.
    """
    try:
        return DoctrineTag[token]
    except KeyError:
        pass
    try:
        return PracticeVariable[token]
    except KeyError:
        raise DoctrineExpressionError(f"unknown doctrine variable {token!r} in {expr!r}") from None


def _resolve_coeff(token: str, coeffs: Mapping[str, float], expr: str) -> float:
    """Resolve an ``@name`` coefficient token against ``coeffs``, or fail loudly.

    The leading ``@`` sigil is stripped; the remaining snake_case name must be a
    key in the supplied coefficient map (a ``GameDefines`` subset). An unknown
    coefficient is a loud error, never a silent ``0`` — a trap gated on a
    misspelled threshold must fail at evaluation, not fire on a phantom default.
    """
    name = token[1:]
    try:
        return float(coeffs[name])
    except KeyError:
        raise DoctrineExpressionError(f"unknown coefficient {token!r} in {expr!r}") from None


class _Parser:
    """Recursive-descent parser/evaluator over a tokenised trap condition.

    Termination is trivially provable: every rule that recurses first consumes
    at least one token via :meth:`_advance` (``NOT`` before :meth:`_not`, ``(``
    before :meth:`_or`), and the index ``_i`` moves monotonically toward the
    fixed ``len(tokens)`` — so no rule can loop or recurse without shrinking the
    remaining input.
    """

    def __init__(
        self,
        tokens: list[str],
        env: Mapping[DoctrineVariable, float],
        coeffs: Mapping[str, float],
        expr: str,
    ) -> None:
        self._tokens = tokens
        self._i = 0
        self._env = env
        self._coeffs = coeffs
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
        var = _resolve_variable(self._advance(), self._expr)
        op_token = self._advance()
        op = _COMPARISONS.get(op_token)
        if op is None:
            raise DoctrineExpressionError(
                f"expected comparison operator, got {op_token!r} in {self._expr!r}"
            )
        threshold = self._operand(self._advance())
        return op(self._env.get(var, 0), threshold)

    def _operand(self, token: str) -> float:
        """Resolve the RHS operand: an ``@coeff`` reference or an integer literal."""
        if token.startswith("@"):
            return _resolve_coeff(token, self._coeffs, self._expr)
        try:
            return float(int(token))
        except ValueError:
            raise DoctrineExpressionError(
                f"expected integer literal or @coefficient, got {token!r} in {self._expr!r}"
            ) from None


def evaluate_trap_condition(
    condition: str,
    env: Mapping[DoctrineVariable, float],
    coeffs: Mapping[str, float] | None = None,
) -> bool:
    """Return whether ``condition`` holds against the current evaluation ``env``.

    :param condition: A ``trap_condition`` expression in the DSL documented in
        this module's docstring.
    :param env: Current per-variable values — doctrine tag totals merged with
        measured-practice quantities (P25 U11); an absent variable reads as ``0``.
        A pure-tag map (the pre-U11 caller) is a valid ``env``, keeping tag-only
        INT conditions byte-identical.
    :param coeffs: ``@name`` threshold coefficients (a ``GameDefines`` subset);
        ``None`` (the default) means no coefficient references are permitted — a
        pure-tag INT condition needs none. An unknown ``@name`` fails loud.
    :returns: ``True`` iff the trap's condition is satisfied (i.e. it should fire).
    :raises DoctrineExpressionError: if ``condition`` is empty, malformed, or
        names a variable/coefficient/operator/literal the grammar does not accept.
    """
    return _Parser(_tokenize(condition), env, coeffs or {}, condition).parse()


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
