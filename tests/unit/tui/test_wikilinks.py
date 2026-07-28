"""Unit tests for babylon.tui.wikilink_grammar — the pure wikilink grammar.

The Textual render machinery this file used to cover (inline rule tokens,
content-span mixin, parser factory) died with the Textual estate at the M7
cutover; the Rust client parses wikilinks natively in babylon-md, behavior-
pinned by its own Rust test suite and the parity harness. What outlives
both clients is the GRAMMAR: ``WIKILINK_RE`` (which the host's backlink
index is built on) and the resolver semantics.
"""

from __future__ import annotations

from babylon.tui.wikilink_grammar import WIKILINK_RE, known_target_resolver


class TestWikilinkGrammar:
    def test_it_matches_a_bare_target(self) -> None:
        match = WIKILINK_RE.search("see [[county/26163]] for detail")
        assert match is not None
        assert match.group(1) == "county/26163"
        assert match.group(2) is None

    def test_it_matches_a_target_with_an_alias(self) -> None:
        match = WIKILINK_RE.search("see [[county/26163|Wayne County]]")
        assert match is not None
        assert match.group(1) == "county/26163"
        assert match.group(2) == "Wayne County"

    def test_a_pipe_cannot_appear_inside_the_target(self) -> None:
        """Aliasing stays unambiguous: the first pipe ends the target."""
        match = WIKILINK_RE.search("[[a|b|c]]")
        assert match is not None
        assert match.group(1) == "a"
        assert match.group(2) == "b|c"

    def test_an_unclosed_bracket_pair_is_no_match(self) -> None:
        assert WIKILINK_RE.search("[[dangling") is None

    def test_it_finds_every_link_on_a_line(self) -> None:
        found = WIKILINK_RE.findall("[[a]] then [[b|B]] then [[c]]")
        assert [target for target, _alias in found] == ["a", "b", "c"]


class TestKnownTargetResolver:
    def test_it_closes_over_a_frozen_copy_of_the_known_set(self) -> None:
        known = {"a", "b"}
        resolver = known_target_resolver(known)
        known.add("c")
        assert resolver("a") is True
        assert resolver("c") is False

    def test_it_refuses_an_unknown_target(self) -> None:
        assert known_target_resolver(("a",))("z") is False
