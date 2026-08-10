"""Sync guard for the consolidated BSL grammar (``docs/reference/bsl.ebnf``, §7/D92).

``docs/reference/bsl-language.rst`` is the ONE normative home for BSL. §7
collects its scattered productions into ``bsl.ebnf`` and includes that file
back into the document, so the appendix is normative **by inclusion** — which
buys the rigor of a single consolidated grammar only for as long as the
collection actually tracks the sections it collects. Left unguarded, the
failure mode is silent and certain: a chapter adds a form, the section text
carries it, the appendix does not, and two implementations derived from "the
document" disagree about what the language is. That is a III.12(a) failure,
not a formatting drift.

The guard is therefore three containments, each in the safe direction:

1. every ``<name> ::=`` production the rst's §§1/2/6.1 code blocks define
   appears in ``bsl.ebnf``;
2. every form tag §5.2 enumerates appears in ``bsl.ebnf`` as a quoted
   terminal — §5.2 is the CAS-side list of head symbols, so a form with a
   tag and no production is exactly the drift above, caught from the other
   side;
3. every form head the **Rust reference implementation** knows
   (``RESERVED_FORM_TAGS`` in ``babylon-bsl``'s ``declarations.rs``, which is
   that crate's rendering of the same §5.2 list) appears in ``bsl.ebnf``.

Direction matters. The guard never demands the reverse containment — that
every production or tag in the appendix be known to Rust — because the rst
leads the implementation by design: the Amendment AG forms (``member``,
``membership-field-of``, ``update-membership``, ``rung``, ``adjunction``)
are specified and not yet implemented, and a guard that failed on that would
be demanding the spec wait for the code.

No test here parses BSL or checks a program: this is a documents-agree test.
The language's own conformance lives in the crate's vectors (§6.2).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
EBNF = REPO_ROOT / "docs" / "reference" / "bsl.ebnf"
RST = REPO_ROOT / "docs" / "reference" / "bsl-language.rst"
DECLARATIONS_RS = REPO_ROOT / "rust" / "crates" / "babylon-bsl" / "src" / "declarations.rs"

#: Productions of the rst that are deliberately NOT in the appendix. §5.2's
#: ``atom`` / ``form`` / ``opt`` are the canonical-serialization BYTE layout —
#: a schema over octets (``0x01``, ``u8 len(kind)``, …), not a production over
#: the token stream — and collecting them into a surface grammar would be a
#: category error. They are named here rather than filtered by a pattern so
#: that a NEW §5 production cannot slip through the same hole unnoticed.
CAS_ENCODING_PRODUCTIONS = frozenset({"atom", "form", "opt"})

#: The synthetic CAS tag for a keyword option (§5.2). It is a tag with no
#: surface syntax — no BSL source ever spells ``(opt …)`` — so §5.2's list
#: carries it and the surface grammar cannot.
SYNTHETIC_FORM_TAGS = frozenset({"opt"})


def _read(path: Path) -> str:
    assert path.exists(), f"{path} is missing"
    return path.read_text(encoding="utf-8")


def _ebnf_text() -> str:
    return _read(EBNF)


def _ebnf_code() -> str:
    """The appendix with its ``/* … */`` comments stripped.

    Comment prose carries apostrophes and quoted phrases, and a naive scan for
    quoted terminals over the raw file pairs quotes ACROSS them — which found
    zero terminals while looking like it worked. Strip first, then scan.
    """
    return re.sub(r"/\*.*?\*/", " ", _ebnf_text(), flags=re.DOTALL)


def _ebnf_productions() -> set[str]:
    """Left-hand sides defined in the appendix."""
    return set(re.findall(r"^([A-Za-z][A-Za-z0-9-]*)\s*::=", _ebnf_code(), re.MULTILINE))


def _rst_productions() -> set[str]:
    """Left-hand sides the rst's own code blocks define.

    The rst writes nonterminals two ways — bare in §1.4's lexical block
    (``symbol      ::= …``) and angle-bracketed everywhere else
    (``<rule>     ::= …``) — and at least one row omits the space before
    ``::=`` (``<payload-item>::=``). All three spellings are matched.
    """
    pattern = re.compile(r"^\s+<?([a-z][a-z0-9-]*)>?\s*::=", re.MULTILINE)
    return set(pattern.findall(_read(RST)))


def _rst_form_tags() -> set[str]:
    """The form tags §5.2 enumerates, from its own paragraph.

    §5.2 writes them as a parenthesised list of double-backquoted symbols
    followed by "plus the synthetic tag ``opt``"; the operator tags (``<``,
    ``+``, …) are in the same list and are dropped here because they are not
    spellable as symbols.
    """
    body = _read(RST)
    start = body.index("**Form tags** are the form's head symbol verbatim")
    end = body.index("A keyword option is encoded as a two-child form", start)
    section = body[start:end]
    return {
        tag
        for tag in re.findall(r"``([a-z][a-z0-9-]*)``", section)
        if tag not in SYNTHETIC_FORM_TAGS
    }


def _rust_reserved_form_tags() -> set[str]:
    """``RESERVED_FORM_TAGS`` from the Rust crate — its §5.2 rendering."""
    body = _read(DECLARATIONS_RS)
    match = re.search(r"pub const RESERVED_FORM_TAGS: \[&str; \d+\] = \[(.*?)\];", body, re.DOTALL)
    assert match, "RESERVED_FORM_TAGS not found in declarations.rs"
    return set(re.findall(r'"([a-z][a-z0-9-]*)"', match.group(1))) - SYNTHETIC_FORM_TAGS


def _quoted_terminals() -> set[str]:
    """Every quoted terminal in the appendix, both quote styles."""
    code = _ebnf_code()
    return set(re.findall(r'"([^"\n]+)"', code)) | set(re.findall(r"'([^'\n]+)'", code))


class TestTheAppendixCollectsTheSections:
    """§7's claim — "every production of §§1, 2 and 6.1" — held to."""

    def test_every_rst_production_appears_in_the_appendix(self) -> None:
        missing = _rst_productions() - _ebnf_productions() - CAS_ENCODING_PRODUCTIONS
        assert not missing, (
            "productions defined in bsl-language.rst but absent from bsl.ebnf: "
            f"{sorted(missing)}. §7 says the appendix collects EVERY production of "
            "§§1, 2 and 6.1 — add them there (the section text wins, D92)."
        )

    def test_the_cas_encoding_productions_are_still_the_only_exclusion(self) -> None:
        """The exclusion list is an allowlist, so it must stay exact.

        If §5 ever loses one of these, the exclusion silently widens; this row
        fails first and names the drift.
        """
        assert _rst_productions() >= CAS_ENCODING_PRODUCTIONS

    def test_the_appendix_defines_nothing_the_rst_does_not(self) -> None:
        """The other containment, where it IS safe to demand.

        A production in the appendix with no counterpart in the sections would
        be the appendix legislating — exactly what D92 forbids. The lexical
        helpers §1 states in prose rather than in a code block are exempt and
        listed by name.
        """
        prose_only = {
            "whitespace",  # §1.2, stated in prose
            "comment",  # §1.2, stated in prose
            "delimiter",  # §1.4, stated in prose
            "Char",  # §1.1, "a Unicode scalar value"
            "DIGIT",  # §1.4's character terminals
            "LOWER",
            "UPPER",
            "escape",  # §1.5's four escapes, spelled as source sequences
            "operator",  # §1.4's tenth atom class (its draft ruling)
            "literal",  # §2.7's <literal>, also used by §6.1
            "type-name",  # §2.9/§2.11/§2.7 use it; §3.1 names the types
            "vector-file",  # §6.1's "a sequence of vector forms", in prose
            "intrinsic-name",  # §2.7's intrinsic-call head
            "payload-item",  # §2.8 (matched by the rst scan, kept explicit)
            "string-char",  # §1.4
        }
        extra = _ebnf_productions() - _rst_productions() - prose_only
        assert not extra, (
            f"bsl.ebnf defines productions the rst does not: {sorted(extra)}. "
            "The appendix collects; it does not amend (D92)."
        )


class TestEveryFormTagHasAProduction:
    """A tag with no production is a form the appendix forgot."""

    def test_every_rst_form_tag_is_a_terminal_in_the_appendix(self) -> None:
        missing = _rst_form_tags() - _quoted_terminals()
        assert not missing, (
            "form tags §5.2 enumerates but bsl.ebnf never quotes: "
            f"{sorted(missing)}. Every form the canonical serialization can "
            "encode must have a production to be derived from."
        )

    def test_every_rust_form_head_is_a_terminal_in_the_appendix(self) -> None:
        missing = _rust_reserved_form_tags() - _quoted_terminals()
        assert not missing, (
            "form heads the Rust reference implementation knows "
            f"(RESERVED_FORM_TAGS) but bsl.ebnf never quotes: {sorted(missing)}."
        )

    def test_the_rust_tag_list_stays_a_subset_of_the_rst_list(self) -> None:
        """Rust may lag the spec; it may never lead it.

        A tag the crate knows and §5.2 does not is an implementation that
        invented a form — the direction the Constitution forbids.
        """
        invented = _rust_reserved_form_tags() - _rst_form_tags()
        assert not invented, f"babylon-bsl knows form heads §5.2 does not list: {sorted(invented)}"


class TestTheInclusionIsWired:
    """§7 is only normative if the document actually includes the file."""

    def test_the_rst_literalincludes_the_appendix(self) -> None:
        body = _read(RST)
        assert ".. literalinclude:: bsl.ebnf" in body

    def test_section_seven_exists_and_states_the_precedence_rule(self) -> None:
        body = _read(RST)
        assert "7. Consolidated grammar" in body
        assert "collects; it does not amend" in body

    def test_the_register_carries_d92(self) -> None:
        body = _read(RST)
        assert re.search(r"^\s+\* - D92$", body, re.MULTILINE), (
            "the consolidated grammar is a decision and owes a register row"
        )

    def test_the_appendix_names_its_dialect(self) -> None:
        assert "W3C EBNF" in _ebnf_text()


class TestTheDerivedGrammarsCorpusCoversEveryForm:
    """Every §5.2 form tag is exercised by a tree-sitter corpus case.

    This row exists because the failure it catches actually happened. A corpus
    case whose source is not terminated by a ``---`` separator is folded into
    the PREVIOUS case's expected tree by ``tree-sitter test --update``, which
    then rewrites the file without it: five cases vanished silently, and
    ``tree-sitter test`` went on reporting 100%% because the cases it no longer
    knew about could not fail. A green suite that quietly shrank is exactly the
    shape III.11 rejects, and coverage measured against the SPEC's tag list —
    rather than against whatever the corpus currently happens to contain — is
    what makes the shrinkage visible.

    The corpus is derived tooling and normative for nothing; what is asserted
    here is only that it exercises what the language has.
    """

    @staticmethod
    def _corpus_sources() -> str:
        """The source halves of every corpus case, expectations excluded."""
        corpus_dir = REPO_ROOT / "tools" / "tree-sitter-bsl" / "test" / "corpus"
        sources: list[str] = []
        for path in sorted(corpus_dir.glob("*.txt")):
            for block in _read(path).split("=" * 50):
                if "\n---\n" in block:
                    sources.append(block.split("\n---\n")[0])
        return "\n".join(sources)

    def test_the_corpus_has_cases_at_all(self) -> None:
        assert self._corpus_sources().strip(), "no corpus case survived parsing"

    def test_every_form_tag_appears_in_a_corpus_source(self) -> None:
        used = set(re.findall(r"\(([a-z][a-z0-9-]*)[\s)]", self._corpus_sources()))
        missing = _rst_form_tags() - used
        assert not missing, (
            f"form tags no tree-sitter corpus case exercises: {sorted(missing)}. "
            "A dropped case is invisible to `tree-sitter test`, which cannot fail "
            "a case it no longer has — check for a source with no `---` separator."
        )


class TestTheRecordedGapsStayRecorded:
    """Two under-determined points are flagged in place rather than settled.

    A future edit that quietly deletes the flag would convert an honest gap
    into a silent ruling — the one thing an appendix must never do.
    """

    @pytest.mark.parametrize(
        "needle",
        [
            "RECORDED GAP",  # <type-name> has no §1.4 atom class
            "TRANSCRIBED VERBATIM",  # §6.1's optional-valued vector keywords
        ],
    )
    def test_the_gap_is_still_flagged(self, needle: str) -> None:
        assert needle in _ebnf_text()
