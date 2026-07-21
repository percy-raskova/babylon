"""Wikilink inline rule and its Textual content-span extension (ADR099).

Implements ``[[target]]`` / ``[[target|alias]]`` wikilink syntax as a
markdown-it-py inline rule. Known targets (per a resolver callable) emit
``wikilink_open``/``text``/``wikilink_close`` tokens; unknown ones emit
``redlink_open``/``text``/``redlink_close`` with an ``href`` of
``babylon://redlink/<target>``.

Textual's ``Markdown`` widget builds inline content via
``MarkdownBlock._token_to_content``, a single monolithic method with no
finer extension seam (Textual documents only the ``BLOCKS`` mapping as an
extension point). The throwaway P0 spike worked around this by wrapping
unknown links in fake ``em_open``/``em_close`` tokens purely to borrow the
``.em`` component class's color — a shortcut, not a real answer to "what
does a wikilink look like". ADR099 requires the keel to do better:
:class:`WikilinkContentMixin` below reimplements ``_token_to_content`` with
two first-class branches (``wikilink_open``/``redlink_open``) that build a
combined foreground-color + click-action ``Style`` in one span, so the link
stays genuinely clickable — ``Markdown.LinkClicked`` still fires exactly as
for a standard link — while getting its own visual register instead of
piggy-backing on emphasis.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Final

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token
from mdit_py_plugins.front_matter import front_matter_plugin
from textual.color import Color
from textual.content import Content, Span
from textual.style import Style
from textual.widgets._markdown import (
    MarkdownH1,
    MarkdownH2,
    MarkdownH3,
    MarkdownH4,
    MarkdownH5,
    MarkdownH6,
    MarkdownParagraph,
    MarkdownTD,
    MarkdownTH,
)

from babylon.tui.theme import CRIMSON, GOLD

WIKILINK_RE: Final = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
"""Matches ``[[target]]`` or ``[[target|alias]]``; ``|`` and ``]`` cannot
appear inside ``target`` so aliasing is unambiguous."""

WIKILINK_COLOR: Final = Color.parse(GOLD)
REDLINK_COLOR: Final = Color.parse(CRIMSON)

WikilinkResolver = Callable[[str], bool]
"""A callable returning ``True`` when ``target`` is a known Archive entity id."""


def known_target_resolver(known: Iterable[str]) -> WikilinkResolver:
    """Build a :data:`WikilinkResolver` from a fixed collection of ids.

    :param known: entity ids considered resolvable.
    :returns: a resolver closing over a frozen copy of ``known``.
    """
    known_ids = frozenset(known)
    return lambda target: target in known_ids


def wikilink_plugin(md: MarkdownIt, resolver: WikilinkResolver) -> None:
    """Register the ``[[target]]`` / ``[[target|alias]]`` inline rule.

    Known targets get ``wikilink_open``/``text``/``wikilink_close`` tokens
    with ``href="babylon://<target>"``; unknown ones get
    ``redlink_open``/``text``/``redlink_close`` with
    ``href="babylon://redlink/<target>"``. :class:`WikilinkContentMixin`
    turns both into real, clickable, distinctly-colored spans.

    :param md: the parser instance to extend.
    :param resolver: decides whether a wikilink target is known.
    """

    def rule(state: StateInline, silent: bool) -> bool:
        src = state.src
        pos = state.pos
        if src[pos : pos + 2] != "[[":
            return False
        match = WIKILINK_RE.match(src, pos)
        if match is None:
            return False
        if not silent:
            target = match.group(1).strip()
            alias = (match.group(2) or match.group(1)).strip()
            kind = "wikilink" if resolver(target) else "redlink"
            href = f"babylon://{'redlink/' if kind == 'redlink' else ''}{target}"
            open_token = state.push(f"{kind}_open", "a", 1)
            open_token.attrSet("href", href)
            text_token = state.push("text", "", 0)
            text_token.content = alias
            state.push(f"{kind}_close", "a", -1)
        state.pos = match.end()
        return True

    md.inline.ruler.before("link", "wikilink", rule)


def make_parser_factory(resolver: WikilinkResolver) -> Callable[[], MarkdownIt]:
    """Build a Textual-compatible ``parser_factory`` with wikilinks wired in.

    Matches Textual's own default ``"gfm-like"`` parser configuration, plus
    the ``front_matter`` plugin (frontmatter-safe per ADR099) and the
    wikilink rule.

    :param resolver: decides whether a wikilink target is known.
    :returns: a zero-arg factory producing a configured ``MarkdownIt``.
    """

    def factory() -> MarkdownIt:
        parser = MarkdownIt("gfm-like")
        parser.use(front_matter_plugin)
        wikilink_plugin(parser, resolver)
        return parser

    return factory


class _ContentBuilder:
    """Accumulates text and ``Span`` overlays while walking inline children.

    Mirrors the local closures upstream's ``_token_to_content`` uses
    (``add_content``/``add_style``/``close_tag`` over shared ``position``),
    lifted into an object so the per-token-type handlers below can be
    ordinary module-level functions instead of one long ``if``/``elif``
    chain (keeping cyclomatic complexity down while staying literal about
    what upstream does).
    """

    def __init__(self) -> None:
        self._tokens: list[str] = []
        self._spans: list[Span] = []
        self._style_stack: list[tuple[Style | str, int]] = []
        self.position = 0

    def add_content(self, text: str) -> None:
        self._tokens.append(text)
        self.position += len(text)

    def add_style(self, style: Style | str) -> None:
        self._style_stack.append((style, self.position))

    def close_tag(self) -> None:
        style, start = self._style_stack.pop()
        self._spans.append(Span(start, self.position, style))

    def build(self) -> Content:
        return Content("".join(self._tokens), spans=self._spans)


_InlineHandler = Callable[[_ContentBuilder, Token], None]


def _click_style(href: str) -> Style:
    """The upstream click-action style: ``@click`` meta routing to ``action_link``."""
    return Style.from_meta({"@click": f"link({href!r})"})


def _handle_text(builder: _ContentBuilder, child: Token) -> None:
    builder.add_content(re.sub(r"\s+", " ", child.content))


def _handle_hardbreak(builder: _ContentBuilder, _child: Token) -> None:
    builder.add_content("\n")


def _handle_softbreak(builder: _ContentBuilder, _child: Token) -> None:
    builder.add_content(" ")


def _handle_code_inline(builder: _ContentBuilder, child: Token) -> None:
    builder.add_style(".code_inline")
    builder.add_content(child.content)
    builder.close_tag()


def _open_style(style: str) -> _InlineHandler:
    def handler(builder: _ContentBuilder, _child: Token) -> None:
        builder.add_style(style)

    return handler


def _handle_link_open(builder: _ContentBuilder, child: Token) -> None:
    builder.add_style(_click_style(str(child.attrs.get("href", ""))))


def _handle_image(builder: _ContentBuilder, child: Token) -> None:
    href = str(child.attrs.get("src", ""))
    alt = str(child.attrs.get("alt", ""))
    builder.add_style(_click_style(href))
    builder.add_content("\U0001f5bc  ")
    if alt:
        builder.add_content(f"({alt})")
    if child.children is not None:
        for grandchild in child.children:
            builder.add_content(grandchild.content)
    builder.close_tag()


def _wikilink_handler(color: Color) -> _InlineHandler:
    """A handler for ``wikilink_open``/``redlink_open``: a real content span.

    Combines a foreground color with the same ``@click`` meta upstream's
    ``link_open`` handling uses, in one ``Style`` — the ADR099-mandated
    extension over the P0 spike's ``.em``-wrapper shortcut. The link stays
    genuinely clickable (``Markdown.LinkClicked`` still fires) while getting
    its own visual register.
    """

    def handler(builder: _ContentBuilder, child: Token) -> None:
        href = str(child.attrs.get("href", ""))
        builder.add_style(Style(foreground=color) + _click_style(href))

    return handler


def _handle_close(builder: _ContentBuilder, _child: Token) -> None:
    builder.close_tag()


_INLINE_HANDLERS: Final[dict[str, _InlineHandler]] = {
    "text": _handle_text,
    "hardbreak": _handle_hardbreak,
    "softbreak": _handle_softbreak,
    "code_inline": _handle_code_inline,
    "em_open": _open_style(".em"),
    "strong_open": _open_style(".strong"),
    "s_open": _open_style(".s"),
    "link_open": _handle_link_open,
    "image": _handle_image,
    "wikilink_open": _wikilink_handler(WIKILINK_COLOR),
    "redlink_open": _wikilink_handler(REDLINK_COLOR),
}
"""Dispatch table for known inline child token types. Anything ending in
``_close`` (including ``wikilink_close``/``redlink_close``) closes the most
recently opened span; anything else is silently skipped, matching upstream."""


class WikilinkContentMixin:
    """Extends ``MarkdownBlock._token_to_content`` with wikilink/redlink spans.

    A full reimplementation of the upstream algorithm (textual 8.2.8,
    ``textual/widgets/_markdown.py``) because there is no narrower seam to
    hook: the method walks every inline child token in one pass, building
    ``Content`` spans as it goes. Dispatch is table-driven (``_INLINE_HANDLERS``
    above) rather than one long ``if``/``elif`` chain, adding exactly two
    entries over upstream's set: ``wikilink_open`` and ``redlink_open``.

    Mix in ahead of a concrete ``MarkdownBlock`` subclass, e.g.::

        class BabylonParagraph(WikilinkContentMixin, MarkdownParagraph):
            pass
    """

    def _token_to_content(self, token: Token) -> Content:
        if token.children is None:
            return Content("")

        builder = _ContentBuilder()
        for child in token.children:
            handler = _INLINE_HANDLERS.get(child.type)
            if handler is not None:
                handler(builder, child)
            elif child.type.endswith("_close"):
                _handle_close(builder, child)
        return builder.build()


class BabylonParagraph(WikilinkContentMixin, MarkdownParagraph):
    """Paragraph block with wikilink/redlink content spans."""


class BabylonH1(WikilinkContentMixin, MarkdownH1):
    """H1 block with wikilink/redlink content spans."""


class BabylonH2(WikilinkContentMixin, MarkdownH2):
    """H2 block with wikilink/redlink content spans."""


class BabylonH3(WikilinkContentMixin, MarkdownH3):
    """H3 block with wikilink/redlink content spans."""


class BabylonH4(WikilinkContentMixin, MarkdownH4):
    """H4 block with wikilink/redlink content spans."""


class BabylonH5(WikilinkContentMixin, MarkdownH5):
    """H5 block with wikilink/redlink content spans."""


class BabylonH6(WikilinkContentMixin, MarkdownH6):
    """H6 block with wikilink/redlink content spans."""


class BabylonTableHeaderCell(WikilinkContentMixin, MarkdownTH):
    """Table header cell with wikilink/redlink content spans."""


class BabylonTableDataCell(WikilinkContentMixin, MarkdownTD):
    """Table data cell with wikilink/redlink content spans."""


__all__ = [
    "WIKILINK_RE",
    "WikilinkResolver",
    "known_target_resolver",
    "wikilink_plugin",
    "make_parser_factory",
    "WikilinkContentMixin",
    "BabylonParagraph",
    "BabylonH1",
    "BabylonH2",
    "BabylonH3",
    "BabylonH4",
    "BabylonH5",
    "BabylonH6",
    "BabylonTableHeaderCell",
    "BabylonTableDataCell",
]
