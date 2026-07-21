"""Concept cards — static game-theory reference pages (Program 24 P2 WO-36).

Four vault pages that explain the simulation's foundational math instead of
observing a tick: the **Fundamental Theorem** of MLM-TW, the **Survival
Calculus**, the **Metabolic Rift**, and the **nine Article V verbs**. Each is
condensed, with a citation, from the actual reference docs rather than
re-derived from memory (the Verifiability discipline — a formula quoted here
must be traceable to the doc it claims to come from; ``test_concept_cards.py``
pins that trace).

**Absorption ruling** (``project/programs/24-the-archive.md``, P0 exit batch,
item 5): "``/explain`` + Observatory: absorbed as Archive pages (concept
cards + formula terminals)". A concept card's ``{statblock}`` fence *is* the
"formula terminal" here — the symbol glossary the legacy ``/explain``
endpoint (``web/game/provenance.py::n_metric``) computed live from a session's
inputs is, for these four *unchanging* concepts, baked once from the
reference docs instead of recomputed per click. The Observatory's read-only
debug dashboard (``web/observatory/``) had no dedicated concept-explainer
pane to port; its absorption is satisfied by these pages existing as Archive
content at all, per the charter ruling's phrasing.

**Net-new design, flagged per the WO** (``specs/24-archive/work-orders-p2-p4.md``
WO-36; OPEN QUESTIONS #3): no S-item in
``ai/_inbox/tui/20260719archiveinterfacedesign.md`` specs a "concept card"
idiom — the closest cousin is the entity-scoped ``peek()`` plate (WO-25),
which this is not (a concept card has no ``entity_id``, no tick, no fog
gate). This WO ships the closest-fit shape — the county dossier's page
anatomy (S1 vault-as-contract, S4 honest absence *pattern*, minus the
per-tick staleness stamp, since a mathematical definition does not go stale
the way a committed-tick observation does) — pending BD ratification of a
DESIGN_BIBLE wiki-page-anatomy section (raised in the design brief's own
delivery-shape checklist, item 4, as not-yet-existing).

Unlike :class:`~babylon.projection.view_models.CountyView`, a
:class:`ConceptCard` carries no ``verified_tick`` and Constitution III.11's
honest-``None``-absence discipline does not apply to its fields: every field
is always present by construction (compiled once, at import time, from
:data:`CONCEPT_CARDS` — there is no runtime producer that could withhold a
definition the way a fog gate withholds a county's consciousness reading).
The one legitimately-optional field, :attr:`ConceptCard.formula`, is a
*structural* absence (the nine-verbs card is a roster, not an equation), not
a fog/veil absence, and is handled with a plain ``{% if %}`` in the template
rather than a named ``{absence}`` remedy block.

**Sourcing deviation, recorded rather than silent:** three of the four cards
cite ``docs/reference/formulas.rst`` verbatim math sections, exactly as the
WO specifies. The nine-verbs card has no ``docs/reference/*.rst`` home — no
reference doc names the Article V roster — so it cites ``CONSTITUTION.md``
Article V directly (the actual source of truth for that content) plus
:data:`babylon.engine.actions.VERB_RESOLVERS` as the implementation
cross-check (the Aleksandrov Test: every formal construct traces to a
material relation, here the live resolver registry).
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ConceptTerm",
    "ConceptCard",
    "CONCEPT_CARDS",
    "concept_slugs",
    "render_concept_card",
]


class ConceptTerm(BaseModel):
    """One glossary row on a concept card's ``{statblock}`` fence.

    Doubles as a formula's symbol definition (``W_c`` -> ``"Core wages"``)
    and, for the roster-shaped nine-verbs card, a verb's one-line gloss
    (``"Educate"`` -> ``"..."``) — same shape, same rendering path, one
    fenced-directive vocabulary for both.

    :param label: The symbol or verb name.
    :param meaning: Its one-line definition.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    meaning: str


class ConceptCard(BaseModel):
    """One static game-concept reference page.

    :param kind: Discriminator literal, ``"concept"``. Deliberately **not**
        joined to :data:`~babylon.projection.view_models.ProjectionRecord` —
        that union is reserved for per-tick observational records hydrated
        from ``observe()`` projections; a concept card is neither (see the
        module docstring).
    :param slug: The page's stable id (materializes as ``concept/<slug>.md``
        per the vault slug ruling — ``project/programs/24-the-archive.md``).
    :param title: The page's display title.
    :param statement: The condensed defining statement, closely paraphrasing
        or directly quoting :attr:`citation`.
    :param formula: LaTeX-source math text, or ``None`` for the roster-shaped
        nine-verbs card, which has no single defining equation.
    :param terms: The ordered symbol/verb glossary, rendered as the page's
        ``{statblock}`` fence — the "formula terminal" the charter's P0
        batch ruling absorbs from ``/explain``.
    :param implementation: Dotted-path code references grounding the concept
        in running code.
    :param citation: The exact reference-doc section this card condenses.
    :param see_also: Related concept slugs, rendered as
        ``[[concept/<slug>]]`` wikilinks.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["concept"] = "concept"
    slug: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    title: str
    statement: str
    formula: str | None = None
    terms: tuple[ConceptTerm, ...] = ()
    implementation: tuple[str, ...] = ()
    citation: str
    see_also: tuple[str, ...] = ()


def _term(label: str, meaning: str) -> ConceptTerm:
    """Build one :class:`ConceptTerm` — a small readability helper.

    :param label: The symbol or verb name.
    :param meaning: Its one-line definition.
    :returns: The frozen term.
    """
    return ConceptTerm(label=label, meaning=meaning)


_FUNDAMENTAL_THEOREM: Final[ConceptCard] = ConceptCard(
    slug="fundamental-theorem",
    title="The Fundamental Theorem of MLM-TW",
    statement=(
        "Revolution in the Core is impossible when W_c > V_c: the material "
        "conditions for revolutionary consciousness do not exist when workers "
        "benefit from the imperial system. A social class crosses into the "
        "Labor Aristocracy exactly when its wage/value ratio exceeds one — "
        "the same inequality, read the other way around."
    ),
    formula=(
        r"\text{LA Ratio} = \frac{W_c}{V_c} \qquad "
        r"\text{ratio} > 1 \implies \text{Labor Aristocracy}"
    ),
    terms=(
        _term("W_c", "Core wages"),
        _term("V_c", "Value produced"),
    ),
    implementation=(
        "babylon.formulas.calculate_labor_aristocracy_ratio",
        "babylon.formulas.is_labor_aristocracy",
    ),
    citation=(
        "docs/reference/formulas.rst, section Labor Aristocracy Ratio "
        "(the theorem statement itself is docs/concepts/imperial-rent.rst, "
        "section Fundamental Theorem)"
    ),
    see_also=("survival-calculus",),
)

_SURVIVAL_CALCULUS: Final[ConceptCard] = ConceptCard(
    slug="survival-calculus",
    title="Survival Calculus",
    statement=(
        "Agents act to maximize their probability of survival P(S), choosing "
        "between acquiescence (working within the system) and revolution "
        "(overturning it). A Rupture Event occurs when P(S|R) > P(S|A): the "
        "crossover threshold where revolution becomes the rational survival "
        "strategy. Losses are weighted 2.25x gains (Kahneman-Tversky loss "
        "aversion)."
    ),
    formula=(
        r"P(S|A) = \frac{1}{1 + e^{-k(W - S_{min})}} \qquad "
        r"P(S|R) = \frac{O}{R + \epsilon} \qquad "
        r"\text{Rupture} \iff P(S|R) > P(S|A)"
    ),
    terms=(
        _term("W", "Current wealth"),
        _term("S_min", "Subsistence threshold"),
        _term("k", "Curve steepness"),
        _term("O", "Organization/cohesion level, in [0, 1]"),
        _term("R", "State repression capacity, in [0, 1]"),
        _term("epsilon", "Small constant preventing division by zero"),
    ),
    implementation=(
        "babylon.formulas.calculate_acquiescence_probability",
        "babylon.formulas.calculate_revolution_probability",
        "babylon.formulas.calculate_crossover_threshold",
        "babylon.formulas.apply_loss_aversion",
    ),
    citation="docs/reference/formulas.rst, section Survival Calculus Formulas",
    see_also=("fundamental-theorem", "metabolic-rift"),
)

_METABOLIC_RIFT: Final[ConceptCard] = ConceptCard(
    slug="metabolic-rift",
    title="Metabolic Rift",
    statement=(
        "Ecological limits on capital accumulation. Biocapacity changes each "
        "tick by regeneration minus extraction times an entropy (waste) "
        "factor; when the delta is negative, the system depletes faster "
        "than it regenerates. Overshoot is total consumption over total "
        "biocapacity — above one is ecological overshoot."
    ),
    formula=r"\Delta B = R - (E \times \eta) \qquad O = \frac{C}{B}",
    terms=(
        _term("R", "Regeneration — fraction of max biocapacity restored per tick"),
        _term("E", "Extraction intensity times current biocapacity"),
        _term("eta", "Entropy factor — waste multiplier, typically 1.2"),
        _term("C", "Total consumption across all entities"),
        _term("B", "Total biocapacity available"),
    ),
    implementation=(
        "babylon.formulas.calculate_biocapacity_delta",
        "babylon.formulas.calculate_overshoot_ratio",
    ),
    citation="docs/reference/formulas.rst, section Metabolic Rift Formulas",
    see_also=("survival-calculus",),
)

_NINE_VERBS: Final[ConceptCard] = ConceptCard(
    slug="nine-verbs",
    title="The Nine Verbs — Article V Action Vocabulary",
    statement=(
        "Educate, Aid, Attack, Mobilize, Campaign, Move, Investigate, "
        "Reproduce, Negotiate: the complete player action vocabulary (3x3 — "
        "Build org, Project power, Manage resources). Every verb maps to a "
        "graph operation, is atomic per target instance, always available, "
        "and deterministic. Investigate decomposes into three atomic "
        "sub-verbs — Territory, Org, Edge — each revealing a different "
        "class of hidden state, one target per tick."
    ),
    formula=None,
    terms=(
        _term("Educate", "Consciousness-raising; can strengthen an org<->class SOLIDARITY edge"),
        _term("Aid", "Material support; strengthens a SOLIDARITY edge"),
        _term("Attack", "Direct action against an org or its infrastructure"),
        _term("Mobilize", "Protest — collective action at a territory"),
        _term("Campaign", "Propagandize — shifts consciousness at range"),
        _term("Move", "Repositions the acting organization"),
        _term("Investigate", "Reveals hidden state — sub-verbs Territory | Org | Edge"),
        _term("Reproduce", "Recruit — grows the acting organization's base"),
        _term("Negotiate", "Proposes an alliance with another actor"),
    ),
    implementation=("babylon.engine.actions.VERB_RESOLVERS",),
    citation=(
        "CONSTITUTION.md, Article V Action Vocabulary, section Player (9 verbs) "
        "(no docs/reference/*.rst page names the roster; a documented sourcing "
        "deviation — see this module's docstring)"
    ),
    see_also=(),
)

CONCEPT_CARDS: Final[dict[str, ConceptCard]] = {
    card.slug: card
    for card in (
        _FUNDAMENTAL_THEOREM,
        _SURVIVAL_CALCULUS,
        _METABOLIC_RIFT,
        _NINE_VERBS,
    )
}
"""The closed registry of shipped concept cards, keyed by slug, in the order
the WO lists them: Fundamental Theorem, Survival Calculus, Metabolic Rift,
the nine verbs (Python ``dict`` insertion order, relied on by
:func:`concept_slugs`)."""


def concept_slugs() -> tuple[str, ...]:
    """Return every shipped concept slug, in declared order.

    :returns: the :data:`CONCEPT_CARDS` keys, in insertion order.
    """
    return tuple(CONCEPT_CARDS.keys())


def render_concept_card(card: ConceptCard) -> str:
    """Render one concept card to a vault Markdown page.

    Reuses :func:`babylon.projection.vault.render._build_environment` — the
    single sandboxed-Jinja factory (ADR099: environment construction is code,
    never data) — rather than constructing a second one; the template lives
    in this same package's ``templates/`` directory (``concept.md.j2``), so
    the shared :class:`~jinja2.PackageLoader` resolves it identically.
    jinja2 is imported lazily here (function-local), matching
    ``babylon.projection.vault``'s package-import-isolation contract
    (``tests/unit/projection/vault/test_package_isolation.py``): importing
    this module never pulls jinja2 into ``sys.modules`` merely by being on
    the import path.

    Pure function of ``card`` — no wall-clock, no randomness, no filesystem
    reads inside the template (Constitution III.13): two calls with an
    identical card produce byte-identical Markdown.

    :param card: the concept card to render.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this function does not resolve (a template/model shape drift).
    """
    from babylon.projection.vault.render import _build_environment

    environment = _build_environment()
    template = environment.get_template("concept.md.j2")
    return template.render(card=card)
