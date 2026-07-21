"""Unit tests for babylon.tui.wikilinks: the inline rule and content-span mixin."""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.token import Token

from babylon.tui.wikilinks import (
    REDLINK_COLOR,
    WIKILINK_COLOR,
    WikilinkContentMixin,
    known_target_resolver,
    make_parser_factory,
    wikilink_plugin,
)


def _inline_children(markdown: str, known: frozenset[str]) -> list[Token]:
    """Parse ``markdown`` and return the first paragraph's inline children."""
    parser = MarkdownIt()
    wikilink_plugin(parser, known_target_resolver(known))
    tokens = parser.parse(markdown)
    inline = next(token for token in tokens if token.type == "inline")
    assert inline.children is not None
    return inline.children


def _wrap_inline(children: list[Token]) -> Token:
    return Token("inline", "", 0, children=children)


class TestWikilinkPlugin:
    def test_it_emits_wikilink_tokens_for_a_known_target(self) -> None:
        children = _inline_children("[[county/26163]]", frozenset({"county/26163"}))
        types = [child.type for child in children]
        assert types == ["wikilink_open", "text", "wikilink_close"]
        assert children[0].attrs["href"] == "babylon://county/26163"
        assert children[1].content == "county/26163"

    def test_it_emits_redlink_tokens_for_an_unknown_target(self) -> None:
        children = _inline_children("[[org/uaw-9999]]", frozenset())
        types = [child.type for child in children]
        assert types == ["redlink_open", "text", "redlink_close"]
        assert children[0].attrs["href"] == "babylon://redlink/org/uaw-9999"
        assert children[1].content == "org/uaw-9999"

    def test_it_uses_the_alias_as_display_text(self) -> None:
        children = _inline_children("[[county/26163|Wayne County]]", frozenset({"county/26163"}))
        text_token = next(child for child in children if child.type == "text")
        assert text_token.content == "Wayne County"
        href_token = next(child for child in children if child.type == "wikilink_open")
        assert href_token.attrs["href"] == "babylon://county/26163"

    def test_it_leaves_ordinary_links_untouched(self) -> None:
        children = _inline_children("[a link](http://example.com)", frozenset())
        assert [child.type for child in children] == [
            "link_open",
            "text",
            "link_close",
        ]

    def test_it_builds_a_parser_factory_that_wires_wikilinks_in(self) -> None:
        factory = make_parser_factory(known_target_resolver({"county/26163"}))
        parser = factory()
        tokens = parser.parse("[[county/26163]]")
        inline = next(token for token in tokens if token.type == "inline")
        assert inline.children is not None
        assert inline.children[0].type == "wikilink_open"


class TestWikilinkContentMixin:
    def test_it_gives_a_known_wikilink_a_gold_clickable_span(self) -> None:
        open_token = Token("wikilink_open", "a", 1, attrs={"href": "babylon://county/26163"})
        text_token = Token("text", "", 0, content="Wayne County")
        close_token = Token("wikilink_close", "a", -1)
        token = _wrap_inline([open_token, text_token, close_token])

        content = WikilinkContentMixin()._token_to_content(token)

        assert content.plain == "Wayne County"
        assert len(content.spans) == 1
        span = content.spans[0]
        assert span.start == 0
        assert span.end == len("Wayne County")
        assert span.style.foreground == WIKILINK_COLOR
        assert span.style.meta == {"@click": "link('babylon://county/26163')"}

    def test_it_gives_a_redlink_a_crimson_clickable_span(self) -> None:
        open_token = Token("redlink_open", "a", 1, attrs={"href": "babylon://redlink/org/uaw-9999"})
        text_token = Token("text", "", 0, content="org/uaw-9999")
        close_token = Token("redlink_close", "a", -1)
        token = _wrap_inline([open_token, text_token, close_token])

        content = WikilinkContentMixin()._token_to_content(token)

        assert content.plain == "org/uaw-9999"
        span = content.spans[0]
        assert span.style.foreground == REDLINK_COLOR
        assert span.style.meta == {"@click": "link('babylon://redlink/org/uaw-9999')"}

    def test_it_still_handles_plain_text_with_no_children(self) -> None:
        token = Token("inline", "", 0, children=None)
        content = WikilinkContentMixin()._token_to_content(token)
        assert content.plain == ""

    def test_it_still_handles_emphasis_as_upstream_does(self) -> None:
        children = [
            Token("em_open", "em", 1),
            Token("text", "", 0, content="urgent"),
            Token("em_close", "em", -1),
        ]
        token = _wrap_inline(children)
        content = WikilinkContentMixin()._token_to_content(token)
        assert content.plain == "urgent"
        assert content.spans[0].style == ".em"
