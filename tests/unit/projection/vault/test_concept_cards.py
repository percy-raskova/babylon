"""Contract tests for babylon.projection.vault.concept_cards (Program 24 P2 WO-36).

Pins: the closed four-card registry in WO-listed order; that three cards'
formulas are traceable verbatim to ``docs/reference/formulas.rst`` (the WO's
stated sourcing); that the fourth (nine verbs) documents its sourcing
deviation to ``CONSTITUTION.md`` Article V rather than silently inventing a
``docs/reference`` citation, and that its roster matches both the
constitution's exact verb order and the live ``VERB_RESOLVERS`` registry
size; and the render contract (frontmatter, statblock, formula fence,
implementation/see-also sections, determinism).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.projection.vault.concept_cards import (
    CONCEPT_CARDS,
    ConceptCard,
    ConceptTerm,
    concept_slugs,
    render_concept_card,
)

# tests/unit/projection/vault/test_concept_cards.py -> repo root is four
# parents up (matches test_package_isolation.py's convention in this same
# directory).
_REPO_ROOT = Path(__file__).resolve().parents[4]


class TestRegistry:
    """The closed four-card registry, in the WO's listed order."""

    def test_registry_has_exactly_the_four_wo_named_concepts_in_order(self) -> None:
        """Fundamental Theorem, Survival Calculus, Metabolic Rift, nine verbs."""
        assert concept_slugs() == (
            "fundamental-theorem",
            "survival-calculus",
            "metabolic-rift",
            "nine-verbs",
        )

    def test_every_registry_key_matches_its_cards_own_slug(self) -> None:
        """Dict key and ``card.slug`` never drift apart."""
        for key, card in CONCEPT_CARDS.items():
            assert key == card.slug

    def test_card_rejects_an_unknown_field(self) -> None:
        """``extra='forbid'`` — a shape mismatch surfaces loudly, never swallowed."""
        with pytest.raises(ValidationError):
            ConceptCard(
                slug="test-card",
                title="Test",
                statement="Test statement.",
                citation="nowhere",
                bogus_field="should not be accepted",  # type: ignore[call-arg]
            )

    def test_slug_pattern_rejects_uppercase_or_underscore(self) -> None:
        """The slug pattern is the same stable-id shape county pages use."""
        with pytest.raises(ValidationError):
            ConceptCard(
                slug="Not_A_Valid_Slug",
                title="Test",
                statement="Test statement.",
                citation="nowhere",
            )


class TestFormulaCardsTraceToFormulasRst:
    """Verifiability: a quoted formula must be traceable to its cited doc."""

    @pytest.fixture(scope="module")
    def formulas_rst_text(self) -> str:
        """Raw text of the cited reference doc, read once per test module."""
        path = _REPO_ROOT / "docs" / "reference" / "formulas.rst"
        return path.read_text(encoding="utf-8")

    @pytest.mark.parametrize(
        ("slug", "verbatim_math"),
        [
            ("fundamental-theorem", r"\text{LA Ratio} = \frac{W_c}{V_c}"),
            ("survival-calculus", r"P(S|A) = \frac{1}{1 + e^{-k(W - S_{min})}}"),
            ("survival-calculus", r"P(S|R) = \frac{O}{R + \epsilon}"),
            ("metabolic-rift", r"\Delta B = R - (E \times \eta)"),
            ("metabolic-rift", r"O = \frac{C}{B}"),
        ],
    )
    def test_card_formula_contains_the_docs_verbatim_math(
        self, formulas_rst_text: str, slug: str, verbatim_math: str
    ) -> None:
        """The card's LaTeX substring appears, unaltered, in the cited doc."""
        card = CONCEPT_CARDS[slug]
        assert card.formula is not None
        assert verbatim_math in card.formula
        assert verbatim_math in formulas_rst_text

    @pytest.mark.parametrize("slug", ["fundamental-theorem", "survival-calculus", "metabolic-rift"])
    def test_card_citation_names_formulas_rst(self, slug: str) -> None:
        """The three formula-bearing cards cite the WO's stated source doc."""
        assert "docs/reference/formulas.rst" in CONCEPT_CARDS[slug].citation


class TestNineVerbsDeviationIsDocumented:
    """No docs/reference/*.rst page names the roster — the deviation is loud."""

    def test_citation_names_the_constitution_not_a_reference_doc(self) -> None:
        """The primary citation is the constitution, not a fabricated
        ``docs/reference`` page — the string may still *explain* the
        deviation by mentioning ``docs/reference/*.rst`` in prose, so this
        pins the citation's opening clause rather than banning the
        substring outright."""
        card = CONCEPT_CARDS["nine-verbs"]
        assert card.citation.startswith("CONSTITUTION.md")

    def test_roster_matches_constitution_article_v_exact_order(self) -> None:
        """Term order equals ``CONSTITUTION.md``'s '**Player (9 verbs)**' line."""
        constitution_text = (_REPO_ROOT / "CONSTITUTION.md").read_text(encoding="utf-8")
        assert (
            "**Educate, Aid, Attack, Mobilize, Campaign, Move, Investigate, "
            "Reproduce, Negotiate**." in constitution_text
        )
        card = CONCEPT_CARDS["nine-verbs"]
        assert tuple(term.label for term in card.terms) == (
            "Educate",
            "Aid",
            "Attack",
            "Mobilize",
            "Campaign",
            "Move",
            "Investigate",
            "Reproduce",
            "Negotiate",
        )

    def test_roster_size_matches_the_live_verb_resolver_registry(self) -> None:
        """Nine terms on the card == nine registered player-verb resolvers."""
        from babylon.engine.actions import VERB_RESOLVERS

        card = CONCEPT_CARDS["nine-verbs"]
        assert len(card.terms) == len(VERB_RESOLVERS) == 9

    def test_nine_verbs_card_has_no_single_formula(self) -> None:
        """A roster, not an equation — the structural (non-fog) absence case."""
        assert CONCEPT_CARDS["nine-verbs"].formula is None


class TestRenderConceptCard:
    """The render contract: frontmatter, statblock, formula, sections."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_citation(self) -> None:
        card = CONCEPT_CARDS["fundamental-theorem"]
        page = render_concept_card(card)
        assert page.startswith("---\n")
        assert "id: concept/fundamental-theorem" in page
        assert "citation: " in page
        assert card.citation in page

    def test_it_renders_a_baked_statblock_carrying_every_term(self) -> None:
        card = CONCEPT_CARDS["survival-calculus"]
        page = render_concept_card(card)
        assert "{statblock} concept/survival-calculus" in page
        for term in card.terms:
            assert f"{term.label}: {term.meaning}" in page

    def test_it_renders_a_formula_code_fence_when_present(self) -> None:
        card = CONCEPT_CARDS["metabolic-rift"]
        page = render_concept_card(card)
        assert card.formula is not None
        assert card.formula in page

    def test_it_omits_the_formula_fence_when_formula_is_none(self) -> None:
        card = CONCEPT_CARDS["nine-verbs"]
        page = render_concept_card(card)
        # No bare "None" leak, and no dangling empty code fence for a formula
        # this card structurally lacks.
        assert "None" not in page

    def test_it_renders_the_implementation_section(self) -> None:
        card = CONCEPT_CARDS["fundamental-theorem"]
        page = render_concept_card(card)
        assert "## Implementation" in page
        for ref in card.implementation:
            assert f"`{ref}`" in page

    def test_it_renders_see_also_as_wikilinks(self) -> None:
        card = CONCEPT_CARDS["survival-calculus"]
        page = render_concept_card(card)
        assert "## See also" in page
        for slug in card.see_also:
            assert f"[[concept/{slug}]]" in page

    def test_a_card_with_no_see_also_omits_the_section(self) -> None:
        card = CONCEPT_CARDS["nine-verbs"]
        page = render_concept_card(card)
        assert card.see_also == ()
        assert "## See also" not in page

    def test_it_is_a_pure_function_of_its_input(self) -> None:
        card = CONCEPT_CARDS["fundamental-theorem"]
        first = render_concept_card(card)
        second = render_concept_card(card)
        assert first == second

    def test_every_registered_card_renders_without_error(self) -> None:
        """All four cards render — no template/model shape drift for any of them."""
        for card in CONCEPT_CARDS.values():
            page = render_concept_card(card)
            assert page.startswith("---\n")
            assert card.title in page


class TestConceptTerm:
    """The small glossary-row model backing both formula symbols and verbs."""

    def test_frozen_and_extra_forbidden(self) -> None:
        term = ConceptTerm(label="W_c", meaning="Core wages")
        with pytest.raises(ValidationError):
            term.label = "changed"  # type: ignore[misc]
        with pytest.raises(ValidationError):
            ConceptTerm(label="a", meaning="b", extra="nope")  # type: ignore[call-arg]
