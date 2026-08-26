"""A real S-expression scan for ``(emit EventType/X ...)`` sites in BSL content.

Theme 7 (event-schema registry, C-1 rescope). Deliberately NOT the "obvious"
``\\(emit `` grep the plan itself warns undercounts: at least two emit sites in
this estate (``solidarity.bsl``'s ``CONSCIOUSNESS_TRANSMISSION``/``MASS_AWAKENING``)
spell the form as ``(emit\\n  EventType/…`` — the operand on its own line — which
a single-line, trailing-space pattern never matches. A grep undercount is silent:
the missed site simply never contributes a row, and nothing says so.

This module instead tokenizes and parses the *whole* rule file into a minimal
S-expression tree (atoms, strings, parenthesised forms — enough structure to
walk, not a validating BSL parser) and finds every form whose head symbol is
``emit`` by tree shape, not by a string pattern. Two properties this buys that
no line-oriented scan can:

1. **Comments and strings are honored.** A rule's ``:material-basis`` doc
   string routinely contains example S-expressions with their own literal
   parentheses (``"...the frozen `if`/`elif`..."``) — a naive paren-counter
   would mis-track depth on those. Strings are read as single opaque tokens;
   ``;``-comments (outside a string, per the language's own lexical rule) are
   dropped before tokenizing.
2. **Payload keys are read from the real child forms**, not guessed from
   indentation — each ``(key expr…)`` child of an ``emit`` form contributes
   its head symbol, in source order, however deeply the ``expr`` itself nests
   (§4.3's repeated-computation idiom means some of these expressions are
   dozens of lines long).

BSL content payload keys are NEVER renamed by this scanner or its registry
consumer (ADR183, port-AS-IS) — it only reads what is there.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from babylon.sentinels.base import SentinelCheckError

#: BSL's own EventType-reference spelling; every emit's first operand is one.
_EVENT_TYPE_PREFIX = "EventType/"


@dataclass(frozen=True)
class EmitSite:
    """One observed ``(emit EventType/X (k1 …) (k2 …) …)`` form.

    :param event_type: The bare member name after ``EventType/`` — BSL's own
        spelling, not necessarily a member of Python's ``EventType`` enum.
    :param path: Repo-relative path of the ``.bsl`` file this site is in.
    :param line: 1-indexed line the ``(emit`` token starts on.
    :param keys: The payload's key symbols, in source order, exactly as
        spelled in content (never normalized, never renamed).
    """

    event_type: str
    path: str
    line: int
    keys: tuple[str, ...]


@dataclass(frozen=True)
class _Token:
    text: str
    line: int


@dataclass
class _Form:
    """One parenthesised S-expression; ``items`` holds ``_Form | str`` children."""

    line: int
    items: list[_Form | str]


def _tokenize(text: str, path: Path) -> list[_Token]:
    """Lex BSL source into parens/atoms/strings, comments and whitespace dropped.

    A ``;`` starts a line comment ONLY outside a string literal — the
    language's own lexical rule — so the scan tracks "inside a string" state
    explicitly rather than stripping comments as a separate text pass (which
    would corrupt any ``;`` that happens to sit inside a doc string, and BSL
    doc strings are prose, not fenced off from stray punctuation).

    An unterminated string refuses loudly (:class:`SentinelCheckError`) rather
    than lexing as one token running to end of file — a to-EOF token swallows
    every later form, including ``(emit …)`` sites, and when the leftover
    parens happen to balance the under-count is silent.
    """
    tokens: list[_Token] = []
    i = 0
    n = len(text)
    line = 1
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch in " \t\r":
            i += 1
            continue
        if ch == ";":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == '"':
            start_line = line
            j = i + 1
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if text[j] == "\n":
                    line += 1
                j += 1
            if j >= n:
                raise SentinelCheckError(
                    f"{path}: unterminated string literal opened at line "
                    f"{start_line} — no closing '\"' before end of file"
                )
            j += 1  # consume the closing quote
            tokens.append(_Token(text[i:j], start_line))
            i = j
            continue
        if ch in "()":
            tokens.append(_Token(ch, line))
            i += 1
            continue
        j = i
        while j < n and text[j] not in ' \t\r\n();"':
            j += 1
        tokens.append(_Token(text[i:j], line))
        i = j
    return tokens


def _parse(tokens: list[_Token], path: Path) -> list[_Form | str]:
    """Parse a flat token stream into a forest of nested ``_Form`` nodes."""
    pos = 0

    def parse_one() -> _Form | str:
        nonlocal pos
        tok = tokens[pos]
        if tok.text == "(":
            start_line = tok.line
            pos += 1
            items: list[_Form | str] = []
            while True:
                if pos >= len(tokens):
                    raise SentinelCheckError(
                        f"{path}: unbalanced '(' opened at line {start_line} — "
                        "no matching ')' before end of file"
                    )
                if tokens[pos].text == ")":
                    pos += 1
                    break
                items.append(parse_one())
            return _Form(line=start_line, items=items)
        if tok.text == ")":
            raise SentinelCheckError(f"{path}:{tok.line}: unmatched ')'")
        pos += 1
        return tok.text

    forest: list[_Form | str] = []
    while pos < len(tokens):
        forest.append(parse_one())
    return forest


def _walk_emit_forms(node: _Form | str) -> list[_Form]:
    """Every ``(emit …)`` form anywhere under ``node``, depth-first."""
    if isinstance(node, str):
        return []
    found: list[_Form] = []
    if node.items and node.items[0] == "emit":
        found.append(node)
    for child in node.items:
        found.extend(_walk_emit_forms(child))
    return found


def _emit_site_from_form(form: _Form, repo_relative_path: str) -> EmitSite:
    """Translate one parsed ``(emit EventType/X (k1 …) …)`` form to an :class:`EmitSite`."""
    # items[0] == "emit"; items[1] should be the "EventType/X" operand atom.
    if len(form.items) < 2 or not isinstance(form.items[1], str):
        raise SentinelCheckError(
            f"{repo_relative_path}:{form.line}: an (emit …) form's first "
            "operand is not a bare EventType/X atom — cannot identify its type"
        )
    operand = form.items[1]
    if not operand.startswith(_EVENT_TYPE_PREFIX):
        raise SentinelCheckError(
            f"{repo_relative_path}:{form.line}: an (emit …) form's first "
            f"operand {operand!r} does not start with {_EVENT_TYPE_PREFIX!r}"
        )
    event_type = operand[len(_EVENT_TYPE_PREFIX) :]
    keys: list[str] = []
    for child in form.items[2:]:
        if isinstance(child, _Form) and child.items and isinstance(child.items[0], str):
            key = child.items[0]
            if key not in keys:
                keys.append(key)
    return EmitSite(
        event_type=event_type, path=repo_relative_path, line=form.line, keys=tuple(keys)
    )


def scan_file(path: Path, repo_root: Path) -> tuple[EmitSite, ...]:
    """Every ``(emit …)`` site in one ``.bsl`` file, in source order.

    :param path: The ``.bsl`` file to scan.
    :param repo_root: Repository root — sites record ``path`` relative to
        this, so a citation reads the same regardless of the caller's cwd.
    :raises SentinelCheckError: If the file is missing, its parens are
        unbalanced, a string literal is unterminated, or an ``emit`` form's
        shape cannot be read.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    forest = _parse(_tokenize(text, path), path)
    repo_relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    sites: list[EmitSite] = []
    for top in forest:
        for form in _walk_emit_forms(top):
            sites.append(_emit_site_from_form(form, repo_relative))
    return tuple(sites)


def scan_directory(rules_dir: Path, repo_root: Path) -> tuple[EmitSite, ...]:
    """Every ``(emit …)`` site across every ``*.bsl`` file in ``rules_dir``.

    :param rules_dir: Directory to scan (non-recursive — matches
        ``content/rules/*.bsl``, the plan's own glob).
    :param repo_root: Repository root, forwarded to :func:`scan_file`.
    :returns: Sites sorted by ``(path, line)`` — deterministic regardless of
        filesystem directory-listing order.
    :raises SentinelCheckError: If ``rules_dir`` has no ``.bsl`` files at all
        — an empty result would read as "content emits nothing," which is
        indistinguishable from a wrong path (Constitution III.11).
    """
    bsl_files = sorted(rules_dir.glob("*.bsl"))
    if not bsl_files:
        raise SentinelCheckError(f"no *.bsl files found in {rules_dir}")
    sites: list[EmitSite] = []
    for bsl_file in bsl_files:
        sites.extend(scan_file(bsl_file, repo_root))
    return tuple(sorted(sites, key=lambda s: (s.path, s.line)))
