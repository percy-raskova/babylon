BSL Language Reference (Program 27)
=====================================

The normative, language-agnostic specification of the **Babylon Scripting
Language (BSL)** — the deterministic, total, fuel-metered s-expression DSL that
Program 27 makes the substrate for game rules.

**Status.** Phase-1 draft, produced under
``docs/superpowers/specs/2026-07-28-program-27-refoundation-design.md`` §10
("Phase 1 — Language & Kernel: the BSL specification as the language-agnostic
reference"). The design document is Director-approved; **this document is not
code authorization**. The v3.0.0 amendment (design §4) that Phase 1 was gated
on was **ratified 2026-07-29** — ``CONSTITUTION.md`` v3.0.0, Amendment AE (The
Refoundation), PR #365 — so that gate is closed; this document remains the
reference, not the implementation.

**Amendment D — ruled, and this document revised.** The first revision was
written against the *dyadic working assumption*, with §2.6 (queries), §2.8
(structural verbs) and §3.7 (the edge-side ceiling) flagged as revisable if
Phase 0 ruled otherwise. On **2026-07-29 the Director ruled NATIVE
HYPEREDGE**: hyperedges are **first-class objects** in ``babylon-graph``'s
exposed model and type system, membership is a single typed hyperedge — never
a clique expansion, and never *exposed* as a bipartite incidence encoding
(Levi/incidence is sanctioned as an internal storage strategy only). Source:
Amendment AE clause (vi) (``CONSTITUTION.md`` v3.0.0) recording the ruling in
``ai/_inbox/amendment-d-analysis-p27.md`` §9 (PR #353), sub-rulings D-1…D-7.
Those three sections carry the hyperedge shape as of this revision. The dyadic
query forms and edge verbs are **unchanged and coexist** with it: II.9's
morphism layer stays strictly dyadic, and the two layers are separated by
*type* inside one substrate (sub-ruling D-2 — one substrate, typed homes).

**Third revision — the R9 gap-fill chapters (2026-08-10).** Twelve of the
seventeen systems targeted at pure BSL rule packs carried at least one hard
language blocker: they were BSL-shaped and unauthorable. Thirteen chapters
(C1–C13), planned in ``reports/bsl-gap-analysis-2026-08-10.md`` §7, close them
in place across §§1.6, 2.2–2.11, 3.1, 3.4, 3.6–3.10, 4.2, 4.5–4.7, 5.2, 5.3,
5.5 and 6.2, adding rows **D29–D71** to the register below and vector families
**10–22** to §6.2. One planned item is **not** closed and is recorded as such:
edge-endpoint accessors (gap item Q2), §3.8 item 8 and D78. A three-lens
adversarial verification of the chapters (2026-08-10) added rows **D72–D78**,
which repair what it found: query-result multiplicity, the edge-key uniqueness
obligation at hydration, the enum-ref operand class rule, error-code hygiene,
manifest completeness, and the fuel meter's scope under per-subject firing.

The chapters were held to a stated reach: **query forms, bindings,
iteration and selection structure, and graph-scope state are licensed**
(Amendment AE clause (ii), which re-opens the formalism surface for BSL and for
nothing else), while a new generator, constructor, adjunction, level lattice or
severity rule is not — and neither is an addition to the intrinsic table beyond
``{exp, log}``. Two items reached that boundary and were **escalated rather
than specced**: per-membership hyperedge payload (§2.8's note — a change to the
exposed hyperedge model Amendment AE clause (vi) ruled) and the minting of new
scale-lattice rungs or adjunctions (§3.9's note). **Amendment AG has since
ruled both** (``CONSTITUTION.md`` v3.2.0, ADR189, ratified 2026-08-10), and the
fourth revision below converts the two notes from escalations into
specifications. The rider slate in §3.10 is
recorded as proposals and declares nothing. **This revision is additive**: no
form changes meaning, and §5.6's canonical bytes and both its digests are
unchanged — the one deliberate exception is ``neighbors``, which gains a
mandatory operand (D51) against evidence that no conformance vector exercises
it.

**Fourth revision — the Amendment AG spec sections (2026-08-10).** Amendment AG
(``CONSTITUTION.md`` v3.2.0, ADR189) ruled the two items the third revision
escalated and obliges this document to spec them (clause (iv)). Clause (i)
makes the *(member, hyperedge)* incidence pair a first-class **attributed
membership** carrying declared, typed payload fields; §2.12 states what that
element kind is, and its three language surfaces land in the sections that own
them — the declaration in §2.9 (``deffield``'s ``:member`` operand), the read
in §2.10 (``membership-field-of``), the write in §2.8
(``update-membership``, and ``add-hyperedge``'s annotated member items). Rows
**D79–D84** record the decisions and §6.2 family **23** pins them. Clause (ii)
lets content **declare** scale-lattice rungs and ``allocate``/``aggregate``
adjunction *instances* of the existing schema: the declaration forms join the
``manifest`` in §2.9 and their load-time validation — including the two
standing rulings the amendment binds every rung to — is §3.9's, with rows
**D85–D89** and family **24**. A four-lens adversarial verification of these
sections added row **D90**, which repairs what it found: §3.4's table stated a
result kind for four of its five fold rows and left the weighted intensive
``mean`` blank, and §2.12's worked shape had folded ``sum`` over exactly that
value. A post-merge audit added row **D91**, scoping §6.1's vector-file
format outside §5's canonical encoding (the ``:graph`` flag-vs-valued
spelling collision found by the PR #480 re-verification). This
revision is additive on the same terms as the third: no form changes meaning,
§5.6's canonical bytes and both its digests are unchanged, and the intrinsic
table is untouched.

**Fifth revision — the consolidated grammar (2026-08-10).** §7 collects every
production of §§1, 2 and 6.1 into ``docs/reference/bsl.ebnf`` and includes it
here, adding rows **D92** and **D93** and a *rigor index* (§7.1) that says
where each artifact of the language's rigor lives. The collection **adds no
form and changes no meaning**: it states one EBNF dialect, records in comments
the context conditions a context-free grammar cannot carry, and where the
sections are silent or disagree with themselves it **collects the reference
implementation's reading and flags it** — nine of its productions come from
prose rather than from a code block, so the appendix does choose where it must,
and says which choice it made and what cuts against it. §5.6's bytes and both
its digests are again unchanged.

**Standard this document is written to.** Constitution III.12(a) — the *rewrite
test*: two independent implementations (the Rust ``babylon-bsl`` crate now,
anything later) must be derivable from this document alone, without reading
either implementation's source. Every under-determined point in the design
document is decided here and marked **[draft ruling — Phase 1 review]**; the
complete list is collected in *Draft-Ruling Register* at the end, and each row
is a Phase-1 review item, not a settled law.

**Boundary with the determinism contract.** This document owns the *language*:
lexis, grammar, typing, evaluation, fuel, and the canonical AST byte layout that
``rules_hash`` is computed over. It does **not** restate the tick hash,
``defines_hash``, or the ``ContentDigest`` composition — those live in
:doc:`/reference/determinism-contract`, which Program 27 Phase 0 extends with
three new chapters (tick-hash field set, ``rules_hash``'s place in
``ContentDigest``, and the ``ContentDigest`` byte layout). Where this document
says "``rules_hash``", it defines *what bytes are hashed*; the determinism
contract defines *what that hash is combined with and compared against*.

.. contents:: Contents
   :local:
   :depth: 2

Design intent (non-normative)
-------------------------------

BSL replaces three disjoint substrates that exist in the Python engine today:

- the doctrine trap-condition string DSL
  (``src/babylon/domain/doctrine/mechanics.py``, a recursive-descent evaluator
  over ``OR/AND/NOT``, six comparisons, ``TAG``/``PRACTICE`` variables, and
  ``@coeff`` references);
- the flat Pydantic event-precondition tree
  (``src/babylon/models/entities/event_template.py`` +
  ``src/babylon/engine/event_evaluator.py``: ``NodeCondition`` with a
  dot-notation path, a node filter and a seven-member aggregation;
  ``EdgeCondition``; ``GraphCondition`` over six named graph metrics; an
  ``all``/``any`` combinator);
- the four-operation effect enum (``increase``/``decrease``/``set``/
  ``multiply`` in ``TemplateEffect``).

BSL is a superset of the two condition grammars' **expressible sets**, not of
their failure semantics (see *Grammar-superset honesty* under *Conformance*).
Rules are homoiconic data: stored as content files, diffed in PRs, inspectable
in-game, rewritable by tools, and hashed as declared input.

1. Lexical grammar
--------------------

1.1 Source text
~~~~~~~~~~~~~~~~~

A BSL source file is a sequence of Unicode scalar values encoded as UTF-8.
A byte sequence that is not valid UTF-8 is a load error (``E-LEX-001``).
A UTF-8 BOM at offset 0 is accepted and discarded; a BOM anywhere else is
``E-LEX-001``.

**[draft ruling — Phase 1 review]** String literals must be in Unicode
Normalization Form C. A non-NFC string literal is ``E-LEX-002``. This is what
makes "the source bytes of the string" a canonical form (§5.4) rather than an
implementation accident; it is checked at load, not normalized silently.

1.2 Whitespace and comments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Whitespace is exactly ``U+0020`` (space), ``U+0009`` (tab), ``U+000A`` (LF) and
``U+000D`` (CR). No other character is whitespace; in particular ``U+000C`` and
Unicode space separators are not. Whitespace separates tokens and is otherwise
insignificant.

A comment begins with ``;`` outside a string literal and extends to the next LF
or to end of file. Comments are whitespace.

There are no block comments and no reader macros. **[draft ruling — Phase 1
review]**: rejected because both create formatting/hash coupling the canonical
serialization would then have to define away.

1.3 Delimiters
~~~~~~~~~~~~~~~~

``(`` and ``)`` are the only structural delimiters. There are no square
brackets, no quote/quasiquote reader syntax, no dotted pairs, and no vectors.
Every non-atomic construct is a parenthesised **form** whose first element is a
symbol naming the form.

1.4 Atoms
~~~~~~~~~~~

Lexical productions are given in the same BNF notation as §2 (never as a
regular-expression dialect — dialects differ across implementations). The
character terminals are:

.. code-block:: text

   DIGIT   ::= "0" … "9"
   LOWER   ::= "a" … "z"
   UPPER   ::= "A" … "Z"

The atom classes:

.. code-block:: text

   symbol      ::= LOWER ( LOWER | DIGIT | "-" )*
   qname       ::= symbol ( "/" symbol )+
   keyword     ::= ":" symbol
   enum-ref    ::= enum-type "/" enum-member
   enum-type   ::= UPPER ( UPPER | LOWER | DIGIT )*
   enum-member ::= UPPER ( UPPER | DIGIT | "_" )*
   bool-lit    ::= "#t" | "#f"
   digits      ::= DIGIT ( "_"? DIGIT )*
   int-lit     ::= "-"? digits
   scaled-lit  ::= "-"? digits ( "." digits )? suffix
   suffix      ::= "$" | "p" | "i" | "c"
   string      ::= '"' string-char* '"'
   string-char ::= any scalar value except '"', "\" and LF
                 | "\\" | '\"' | "\n" | "\t"

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Atom class
     - Notes
   * - ``symbol``
     - Form heads, binding names, verb names, intrinsic names, fold operators.
       Lowercase kebab-case only. Maximum length 64 (``E-LEX-010``).
   * - ``qname``
     - Rule ids (``vitality/starvation-mortality``) and field references
       (``social-class/wealth``). Exactly the segment alphabet of ``symbol``,
       joined by ``/``. Maximum 4 segments, 128 bytes total (``E-LEX-011``).
   * - ``keyword``
     - See §1.6.
   * - ``enum-ref``
     - ``NodeType/SOCIAL_CLASS``, ``EdgeType/SOLIDARITY``,
       ``HyperedgeType/ECONOMIC_SECTOR``,
       ``DoctrineTag/CLASS_ANALYSIS``, ``PracticeVariable/CO_OPTIVE_SHARE``.
       The member is the **enum member identifier**, never its serialized
       value: ``NodeType/SOCIAL_CLASS``, never ``NodeType/social_class``.
   * - ``bool-lit``
     - The only two boolean tokens. ``true``/``false`` are ordinary symbols and
       are **not** booleans.
   * - ``int-lit``
     - See §1.5.
   * - ``scaled-lit``
     - See §1.5.
   * - ``string``
     - See §1.5.

**[draft ruling — Phase 1 review, implementation-discovered 2026-07-30]**
The ten operator tokens ``<``, ``<=``, ``>``, ``>=``, ``=``, ``!=``, ``+``,
``-``, ``*``, ``/`` form a distinct atom class, ``operator``, lexed by exact
match against this closed set. §2 quotes them as terminals and §5.2 lists
them as form tags, but this table omitted them — by its letter the reader
had to reject ``(< a b)`` and §5.6's own worked example. An ``operator`` is
valid only in form-head position; CAS encodes it as a form tag, never as an
atom (an operator anywhere else is unencodable and fails loudly per §5.4).
Maximal munch is unchanged: ``<x`` is still ``E-LEX-003``, and ``-5``
still lexes as an integer literal (the exact-match check precedes the
numeric path only for the bare token).

A token ends at whitespace, ``(``, ``)``, ``;``, or end of input. A character
sequence that matches no atom class is ``E-LEX-003``.

Tokenization is **maximal munch within a token run**: the lexer reads to the
next delimiter and then classifies the whole run. ``1000.5$x`` is therefore one
run that classifies as nothing and is ``E-LEX-003`` — it is never split into
``1000.5$`` followed by ``x``. This differs deliberately from the doctrine
DSL's ``re.findall`` tokenizer, which silently drops nothing but does accept
adjacency without separators; BSL requires explicit separation.

1.5 Literals
~~~~~~~~~~~~~~

**Integer literals.** ``int-lit`` per §1.4. Underscores are digit-group
separators and are removed before interpretation; a leading or trailing
underscore, or two adjacent underscores, is ``E-LEX-003``. Leading zeros are
permitted and insignificant (``007`` is ``7``). The value must fit ``i64``
(``E-LEX-020``). Static type: ``Int``.

**Scaled literals.** A decimal numeral with a mandatory one-character **kind
suffix**. There are no unsuffixed non-integer literals — a bare ``0.5`` is
``E-LEX-021``. This is the lexical enforcement of the house prohibition on bare
floats.

.. list-table::
   :header-rows: 1
   :widths: 10 20 22 48

   * - Suffix
     - Static type
     - Closed range
     - Representation
   * - ``$``
     - ``Currency``
     - ``[0, ∞)``
     - Fixed point, ``i128`` **micro-units** (scale 6). A negative currency
       literal is ``E-LEX-022``; a literal with more than 6 fractional digits
       is ``E-LEX-023`` (never rounded at lex time). Value in micro-units =
       ``unscaled × 10^(6 − scale)``; must fit ``i128``.
   * - ``p``
     - ``Probability``
     - ``[0.0, 1.0]``
     - Decimal, canonicalized to ``(unscaled: i128, scale: u8)``.
   * - ``i``
     - ``Intensity``
     - ``[0.0, 1.0]``
     - As ``p``.
   * - ``c``
     - ``Coefficient``
     - ``[0.0, 1.0]``
     - As ``p``.

The ranges are those of the kernel scalars as they exist today
(``src/babylon/models/types.py``): ``Probability``, ``Intensity`` and
``Coefficient`` are all ``[0.0, 1.0]``, and ``Currency`` is ``[0.0, ∞)``.
A ``p``/``i``/``c`` literal outside ``[0,1]`` is ``E-LEX-024``. Maximum scale
for ``p``/``i``/``c`` is 9 (``E-LEX-023``); **[draft ruling — Phase 1 review]**
9 is chosen because ``binary64`` carries ~15–17 significant decimal digits and
the engine's existing quantization grid is ``1e-5`` (``SnapToGrid``), so 9
digits is comfortably beyond any authored precision while remaining exactly
representable in the ``i128`` unscaled form.

*Decimal canonicalization.* Every scaled literal is reduced to its minimal
scale: trailing zeros of the fractional part are stripped, and zero canonicalizes
to ``(0, 0)``. ``0.50c``, ``0.5c`` and ``.5c`` (the last is ``E-LEX-003``, a
leading digit is mandatory) are therefore not three values but one — the first
two hash identically. Currency literals canonicalize further, to their integer
micro-unit value.

**String literals.** ``"`` … ``"``. The only escapes are ``\"``, ``\\``,
``\n`` (LF) and ``\t`` (TAB); any other backslash sequence is ``E-LEX-025``.
A raw LF inside a string literal is ``E-LEX-025`` (strings are single-line).
Maximum length 1024 bytes after escape processing (``E-LEX-026``). Strings
appear only in ``:material-basis`` and in conformance-vector identifiers; there
is no string concatenation, comparison, or interpolation in the language — the
``${var}`` substitution of today's ``TemplateEffect``/``EventEmission`` does
**not** carry over (its job is done by binding references).

**Enum member references.** The enum type name must be a member of the closed
vocabulary registry (§3.6) and the member must exist in it; both checks are
load-time (``E-LOAD-030``, ``E-LOAD-031``). There is no "unknown enum member
reads as default" behavior anywhere in the language.

1.6 Keywords
~~~~~~~~~~~~~~

A keyword is a colon-prefixed symbol. Keywords are never values: they may only
appear in the option position of a form, always immediately followed by their
operand (except for the flag keywords listed below, which take no operand).
A keyword in value position is ``E-PARSE-010``. **[draft ruling — Phase 1
review, R9 verification repair]** So is a **string literal** in expression
position, for the same reason and under the same code: §1.5's strings are
well-formed atoms admitted at ``:material-basis`` and at conformance-vector
identifiers only, ``<expr>`` (§2.7) has no string form, and ``Str`` has no
operations (§3.1). Both are atoms rejected by *position*, not by lexis.

.. list-table::
   :header-rows: 1
   :widths: 22 12 66

   * - Keyword
     - Operand
     - Meaning
   * - ``:material-basis``
     - string
     - **Mandatory on every rule.** The Aleksandrov Test's parse-time half.
       The parser enforces **presence and non-emptiness only** (a string of
       length 0, or one consisting solely of whitespace, is ``E-PARSE-011``).
       The semantic III.8 obligation — does the named material process
       actually ground this construct — is *not* checked here and stays with
       Director review and the sentinel successor's aleksandrov family. The
       string is inside ``rules_hash``: editing a material basis is declared
       input drift.
   * - ``:fuel``
     - integer
     - **Mandatory on every rule.** The rule's fuel budget (§4.5). Must be
       ``> 0`` and ``≤ 1_000_000`` (``E-PARSE-012``).
   * - ``:field``
     - qualified name
     - Binding source: read a declared field of a node (§2.5).
   * - ``:const``
     - qualified name
     - Binding source: read a coefficient from the defines environment. This
       is the successor of the doctrine DSL's ``@snake_case`` sigil; the
       ``@`` sigil does not survive.
   * - ``:metric``
     - symbol
     - Binding source: read a named graph-level metric (§2.5).
   * - ``:expr``
     - expression
     - Binding source: a computed value, a pure function of the bindings
       declared before it (§2.5).
   * - ``:optional``
     - *flag*
     - Marks a binding permitted to be absent at evaluation. Requires
       ``:default`` (§3.5).
   * - ``:default``
     - literal
     - The value an absent ``:optional`` binding takes. Only literals — never
       an expression.
   * - ``:tick``
     - *flag*
     - Binding source: the current tick, as ``Int``.
   * - ``:year`` / ``:tick-of-year``
     - *flags*
     - Binding sources: kernel-computed calendar reads, as ``Int`` (§2.5).
   * - ``:tick-in-cycle``
     - integer
     - Binding source: the current tick's position in a cycle of the given
       length, as ``Int``. The length must be ``> 0`` (``E-PARSE-014``).
   * - ``:kind``
     - ``intensive`` | ``extensive``
     - Per-field intensivity declaration, on ``deffield`` forms only (§3.4).
   * - ``:type``
     - type name
     - Scalar type, on ``deffield``/``intrinsic`` forms.
   * - ``:member``
     - enum-ref
     - The member ``NodeType`` half of an attributed membership's owner pair,
       on ``deffield`` forms only (§2.9, §2.12). Its presence is what makes a
       ``deffield`` a membership-payload declaration; elsewhere it is
       ``E-PARSE-013``.
   * - ``:as``
     - symbol
     - Names the current element of an iterating form, so a nested body can
       still reach it (§2.6).
   * - ``:weight``
     - expression
     - The mandatory explicit weight term of a weighted aggregation (§3.4).
   * - ``:strength``
     - expression
     - Edge strength operand of ``add-edge``.
   * - ``:after`` / ``:before``
     - symbol
     - Ordering anchors (§2.8). A raw position float is not expressible.
   * - ``:out`` / ``:in`` / ``:any``
     - *flags*
     - Traversal direction, on ``neighbors`` queries only (§2.6).
   * - ``:graph``
     - *flag*
     - Graph domain, on ``domain`` forms only (§2.3). Illegal elsewhere
       (``E-PARSE-013``).
   * - ``:params`` / ``:returns`` / ``:cost``
     - see §2.7
     - Intrinsic declaration fields.
   * - ``:provider``
     - symbol
     - The kernel service a ``metric`` declaration binds to (§2.11).
   * - ``:ceiling``
     - integer
     - Declared cardinality ceiling, on ``manifest`` forms (§3.7).
   * - ``:max-members``
     - integer
     - Declared **member-count** ceiling of one hyperedge type, on the
       ``manifest`` ``ceiling`` rows whose ``<enum-ref>`` is a
       ``HyperedgeType`` member (§3.7). Mandatory there, illegal elsewhere.
   * - ``:invariant``
     - *flag*
     - Marks a ``NodeType`` or ``EdgeType`` ``ceiling`` row as invariant
       substrate that no structural verb may add to or remove from (§3.9).
   * - ``:via``
     - enum-ref
     - The ``EdgeType`` carrying a declared scale rung's relation, on
       ``rung`` forms only (§2.9, §3.9).
   * - ``:substrate``
     - *flag*
     - Marks a ``rung`` as running over the invariant substrate, which
       obliges every type it names to carry ``:invariant`` (§3.9).
   * - ``:rung``
     - symbol
     - The declared rung an ``adjunction`` instance runs along (§3.9).
   * - ``:weighted-by``
     - qualified name
     - The extensive field an intensive ``adjunction`` weights by (§3.9).
       Distinct from ``:weight``, whose operand is an expression.

**[draft ruling — Phase 1 review, R9 chapter C4]** The three ``neighbors``
directions were used as bare flags by §2.6 from this document's first revision
and were missing from this table — the same class of omission the operator-atom
ruling of §1.4 records, and it is fixed the same way, by writing down what the
grammar already required. ``:graph`` joins them as a flag keyword so that
``(domain :graph)`` is a legal form rather than a keyword in value position
(``E-PARSE-010``); it encodes as an ``opt`` under D20 like every other flag.

The keyword set is **closed**. An unrecognized keyword is ``E-PARSE-013``; it
is never ignored. Adding a keyword is a language revision and re-blesses the
conformance vectors (§6).

2. Syntactic grammar
----------------------

2.1 Notation
~~~~~~~~~~~~~~

BNF with ``::=`` for production, ``|`` for alternation, ``*`` for zero-or-more,
``+`` for one-or-more, ``?`` for optional. Terminals are quoted. Lexical
classes from §1 appear as ``<symbol>``, ``<qname>``, ``<keyword>``,
``<enum-ref>``, ``<int-lit>``, ``<scaled-lit>``, ``<string>``, ``<bool-lit>``.

2.2 Content files
~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   <file>        ::= <top-form>*
   <top-form>    ::= <rule> | <deffield> | <intrinsic-decl> | <manifest>
                   | <metric-decl>

A content set is the union of all files under the declared content roots. File
boundaries and file names carry **no semantics**: the same forms split across
different files produce the same ``rules_hash`` (§5.5). Duplicate rule ids,
duplicate field declarations, duplicate intrinsic declarations, or — since
Amendment AG (ii) — duplicate ``rung`` or ``adjunction`` names across the
content set are ``E-LOAD-001``.

2.3 Rules
~~~~~~~~~~~

.. code-block:: text

   <rule>     ::= "(" "rule" <qname>
                      ":material-basis" <string>
                      ":fuel" <int-lit>
                      <domain>?
                      <anchor>?
                      <bindings>
                      <when>?
                      <effects>
                  ")"

   <domain>   ::= "(" "domain" ( <enum-ref> | ":graph" ) ")"
   <anchor>   ::= "(" "anchor" ( ":after" | ":before" ) <symbol> ")"
   <bindings> ::= "(" "bindings" <binding>* ")"
   <when>     ::= "(" "when" <cond> ")"
   <effects>  ::= "(" "effects" <effect-item>+ ")"

The keyword options ``:material-basis`` and ``:fuel`` may appear in either
source order; the canonical serialization sorts them (§5.3).

**Omitted ``<when>``.** A rule with no ``<when>`` is unconditional. An
**empty** condition is not expressible: ``(when)`` is ``E-PARSE-020``, and a
rule that means "always" writes ``(when #t)`` or omits the clause. This is one
of the four deliberate III.11 corrections (§6.3).

**[draft ruling — Phase 1 review]** *Anchor default.* A rule with no
``<anchor>`` belongs to the system named by the first segment of its rule id
and takes that system's declared position. A rule whose first id segment names
no registered system, and which carries no anchor, is ``E-LOAD-002``. Mods
therefore cannot land a rule "nowhere", and cannot express a raw position
float. Interleaving an anchor into the Material Base partition is
``E-LOAD-003`` (design §5, modding boundary).

**[draft ruling — Phase 1 review, R9 chapter C4]** *The rule domain — what a
rule fires over, and how many times.* §4.2 says a rule evaluates against "the
subject node" and §5.6 lets the reader *infer* the subject's type from a
binding's qname prefix; the document never stated the inference rule and said
nothing at all about a rule whose only bindings are ``:const``, ``:metric`` and
``:tick``. Six systems (R9 gap analysis §2, Q12) perform exactly one
graph-level check per tick — ControlRatio's four-phase machine, Metabolism's
overshoot check, FieldDerivative's principal-contradiction pick — and under a
per-node reading those would fire once per node.

``<domain>`` is **optional**, with the inference below as its default. It is
optional rather than mandatory for the same reason ``<anchor>`` is (D5): the
document already carries a default-inference convention for rule-level
placement, mandating a new child would make every existing rule form
non-conforming, and §5.6's pinned canonical bytes would need recomputation for
no gain in expressiveness.

*The inference, stated so it is computable at load.* Let ``U`` be the set of
node types owning (§2.9):

- every ``:field`` binding referenced at least once **outside every query
  body**, and
- every ``<qname>`` of an ``update-node`` verb whose element operand is the
  symbol ``self``, and of every ``field-of`` whose element operand is ``self``.

Then ``|U| = 1`` gives the domain; ``|U| = 0`` (nothing is self-scoped) and
``|U| > 1`` (two node types are) are both ``E-LOAD-004``, and both are repaired
by writing ``<domain>`` explicitly. **The surprise the gap analysis names is
removed by construction**: a binding referenced only inside a fold body never
enters ``U``, so adding one cannot change how many times a rule fires.

*Explicit domains.* ``(domain NodeType/SOCIAL_CLASS)`` replaces the inference
outright. Its operand is a ``NodeType`` member — an ``EdgeType`` or
``HyperedgeType`` member there is ``E-TYPE-011`` under §2.6's enum-ref class
rule — and a self-scoped reference owning off a different node type is
``E-TYPE-010``, the existing code for a foreign node type read outside a fold
body over that type, which is exactly what such a reference is.

*The graph domain.* ``(domain :graph)`` fires the rule **exactly once per
tick**, at its anchor position. ``self`` is not bound in a graph-domain rule:
any reference to ``self``, and any ``:field`` binding referenced outside a
query body, is ``E-TYPE-015``. Graph-domain rules read the graph through
queries and through §2.10's accessors, which is what chapter C3's carrier
ruling is for; they read nothing else the language did not already give them.
``(domain :graph)`` is therefore a firing-multiplicity declaration and not a
new capability — it removes an ``N``-fold repetition, it does not reach
further.

2.4 Conditions
~~~~~~~~~~~~~~~~

.. code-block:: text

   <cond>   ::= <bool-lit>
              | "(" "and" <cond>+ ")"
              | "(" "or"  <cond>+ ")"
              | "(" "not" <cond> ")"
              | "(" <cmp> <expr> <expr> ")"
              | "(" "exists" <query> <elem-name>? <cond>? ")"
              | "(" "forall" <query> <elem-name>? <cond> ")"

   <cmp>    ::= "<" | "<=" | ">" | ">=" | "=" | "!="

``and`` and ``or`` are variadic with at least one operand; ``(and)`` and
``(or)`` are ``E-PARSE-021`` (there is no implicit identity element — the same
correction as the empty precondition set).

**[draft ruling — Phase 1 review, R9 chapter C12]** *References compare by
identity, with* ``=`` *and* ``!=`` *only.* Two ``NodeRef``\ s (or two
``EdgeRef``\ s, or two ``HyperedgeRef``\ s) may be compared for identity;
comparing a reference with an ordering operator, or with a reference of a
different kind, or with any non-reference, is ``E-TYPE-017``. This document
had left reference comparison undefined, which made the intersection idiom of
§2.7 unwritable and would have left two implementations free to differ. There
is no ordering on references *in the language* — §2.6's iteration order is the
executor's, and exposing it as a comparison would invite content to depend on
id assignment.

``exists``/``forall`` bind no variable of their own; the query's element is
referred to inside the body as ``it`` **[draft ruling — Phase 1 review]** —
a reserved binding name that may not be declared or shadowed
(``E-PARSE-022``). ``(exists <query>)`` with no body is "the query is
non-empty".

*Coverage of the existing grammars.* This set expresses everything the two
Python grammars express:

.. list-table::
   :header-rows: 1
   :widths: 42 58

   * - Existing construct
     - BSL form
   * - doctrine ``TAG >= 3``
     - ``(>= tag-total 3)`` over a ``:field``/``:metric`` binding
   * - doctrine ``@coeff`` threshold
     - a ``:const`` binding
   * - doctrine ``AND``/``OR``/``NOT``/parens
     - ``and``/``or``/``not`` (parenthesisation is structural)
   * - ``PreconditionSet.logic = "all"`` / ``"any"``
     - ``and`` / ``or``
   * - ``NodeCondition`` aggregation ``any``
     - ``(exists (nodes …) <cmp>)``
   * - ``NodeCondition`` aggregation ``all``
     - ``(forall (nodes …) <cmp>)``
   * - ``NodeCondition`` aggregation ``count``/``sum``/``avg``/``max``/``min``
     - ``(<cmp> (fold count|sum|mean|max|min …) <threshold>)``
   * - ``NodeFilter`` (node type / role / id pattern)
     - ``<node-pred>`` (§2.6)
   * - ``EdgeCondition`` ``count``
     - ``(fold count (edges EdgeType/SOLIDARITY) 1)``
   * - ``EdgeCondition`` ``sum_strength`` / ``avg_strength``
     - ``(fold sum|mean (edges EdgeType/SOLIDARITY)
       (field-of it solidarity/strength))`` — the ``field-of`` accessor of
       §2.10.
   * - ``GraphCondition`` six named metrics
     - ``:metric`` bindings, one per registered metric

**A contradiction this table used to carry, now closed (R9 chapter C1).** The
two ``EdgeCondition`` rows above were one row until the R9 gap analysis
(``reports/bsl-gap-analysis-2026-08-10.md`` §2, Q1), and that row promised
``sum_strength``/``avg_strength`` transcribe as a fold over ``edges`` — while
§2.5 scoped ``:field`` to node types, §2.9's ``deffield`` had no edge case, and
no §2.7 production could read anything off an ``EdgeRef``. The document
committed to a capability its grammar could not express. §2.9 (edge- and
hyperedge-qualified ``deffield``) and §2.10 (``field-of``) close it; the row is
split above because ``count`` needs no attribute read and the other two do.
The frozen Python site the row transcribes is
``engine/event_evaluator.py:174-175``, which reads ``solidarity_strength`` and
defaults it to ``0.0`` — the default is the §6.3 honest-null delta, not part of
the form.

2.5 Bindings
~~~~~~~~~~~~~~

.. code-block:: text

   <binding>   ::= "(" "binding" <symbol> <bind-src> <bind-opt>* ")"

   <bind-src>  ::= ":field"  <qname>
                 | ":const"  <qname>
                 | ":metric" <symbol>
                 | ":tick"
                 | ":year"
                 | ":tick-of-year"
                 | ":tick-in-cycle" <int-lit>
                 | ":expr"   <expr>

   <bind-opt>  ::= ":optional" | ":default" <literal>

A binding names a value the rule reads. **A plain (non-``:optional``) declared
binding that is unbound at load is a load error** (``E-LOAD-010``) — the
opt-in to absence is content, not a test list.

``:field`` reads a declared field of ``self``'s node type unless the qualified
name's first segment names a different node type, in which case it is only
legal inside a fold body over that type (``E-TYPE-010``). ``:const`` reads a
coefficient from the defines environment. ``:metric`` reads a registered
metric whose declared domain is ``:graph`` (§2.11); an unregistered metric name
is ``E-LOAD-011`` — never ``0.0`` (§6.3) — and an element-indexed metric read
through a ``:metric`` binding is ``E-LOAD-012``, since its value depends on an
element a binding does not name. ``:tick`` binds the current tick as ``Int``.

**[draft ruling — Phase 1 review, R9 chapter C13]** *Calendar reads are
bindings, not arithmetic.* Four call sites in the frozen estate compute
``tick % interval`` and ``base_year + tick // ticks_per_year``, and
``<arith>`` provides neither integer modulo nor floor division. The two obvious
repairs are an intrinsic rider for ``mod``/``floor-div`` or three more
bind-srcs; this document takes the second. ``:year``, ``:tick-of-year`` and
``:tick-in-cycle`` all bind ``Int``, all are computed by the kernel's clock,
and all are **seams to a kernel service** rather than mathematics — which is
the category R10 already sanctions without a rider, and a calendar is not a
curve. The epoch and the ticks-per-year figure are the kernel's, pinned in
:doc:`/reference/determinism-contract`; content does not choose them, which is
also what stops a mod-by-anything operator from arriving through the back door.
``:tick-in-cycle``'s length is a **literal**, not an expression, so the value
is a static function of the tick and the content bytes.

**[draft ruling — Phase 1 review, R9 chapter C1]** *A* ``:field`` *binding is
node-scoped, and stays node-scoped.* An edge's or a hyperedge's declared field
is read by the ``field-of`` accessor of §2.10, never by a ``:field`` binding.
Two reasons, both taken from the rest of this document rather than invented
here: a binding is declared once at rule scope and resolved *implicitly*
against an enclosing body, which needs exactly one candidate body to be
unambiguous — and the systems that read edge attributes read several edge types
in one rule; and §2.10's accessor takes its owning type as a qname operand,
which is D24's fix for the identical problem on ``members-of``. The R9 gap
analysis §2 (Q1) sketched an edge-typed ``:field`` binding instead; this
document's conventions override the sketch, and D29 records the divergence.

**[draft ruling — Phase 1 review, R9 chapter C1]** *Implicit resolution
requires a unique candidate.* A foreign-node-type ``:field`` binding
referenced where **two or more** enclosing bodies range over that same node
type is ``E-TYPE-013`` — the reference is ambiguous and the author must write
``field-of`` against a named element (§2.6's ``:as``) instead. This is the
narrow, loud form of the resolution rule §2.5 previously left to inference;
single-body code is unaffected.

Two symbols are **reserved and always in scope**, never declared and never
shadowed (``E-PARSE-022``): ``self``, the node the rule is being evaluated
for (``NodeRef``), and ``it``, the current element inside a query predicate or
fold body (``NodeRef``, ``EdgeRef`` or ``HyperedgeRef``, per the query it
ranges over). ``it`` outside a query context is ``E-TYPE-012``.

Binding names are otherwise rule-scoped; a duplicate name in one rule is
``E-PARSE-030``.

**[draft ruling — Phase 1 review, R9 chapter C7]** ``:expr`` — *a rule may name
an intermediate value.* Every other ``<bind-src>`` names an **external**
source, so before this chapter a rule could not name anything it computed
itself, and every non-trivial rule repeated its sub-expressions verbatim. That
costs three things at once: fuel (a repeated fold is charged at its ceiling
every time it is written), correctness (a transcription that must restate the
same algebra in four places will eventually restate it differently in one), and
reviewability — and the third is the one that matters most here, because the
standing no-imposed-functional-forms line can only be enforced against algebra
a reviewer can read.

.. code-block:: scheme

   (bindings
     (binding wealth      :field social-class/wealth)
     (binding subsistence :const vitality/subsistence-cost)
     (binding drained     :expr (- wealth subsistence)))

- *Type and kind* come from the expression, computed bottom-up like any other
  (§3.1, §3.4). There is no annotation and no inference beyond that.
- *Resolution is in declaration order.* A ``:expr`` may reference bindings
  declared **before** it and no others; a forward reference or a self-reference
  is ``E-PARSE-032``. Order therefore matters inside ``<bindings>``, which is
  the one place in this document where a list's order carries meaning and is
  not a formatting concern — §5.3's group 3 already emits it in source order,
  so CAS needs no change.
- *No cycles are expressible*, by construction: the forward-reference ban makes
  the dependency graph a DAG in source order, so nothing needs a cycle
  analysis.
- *A* ``:expr`` *is evaluated at rule scope*, so ``it`` is ``E-TYPE-012``
  inside one, and referencing a foreign-node-type ``:field`` binding — legal
  only inside a fold body over that type — is ``E-TYPE-010``. A ``:expr``
  **may** contain a fold, a selection or an accessor of its own; that is the
  fuel win, since the ceiling factor is then paid once.
- ``:optional`` *and* ``:default`` *are illegal on a* ``:expr`` (``E-PARSE-033``).
  A computed value is never absent: its operands were resolved at load or the
  rule did not load, and §3.5's whole point is that absence is opted into at
  the external source rather than inherited by everything downstream.

Critically, ``:expr`` does **not** weaken §4.2's law that a rule never observes
its own effects. A computed binding is a pure function of pre-state bindings,
evaluated before any effect applies — it is an abbreviation, not a sequencing
construct, and nothing in it can read a value this rule wrote.

2.6 Queries
~~~~~~~~~~~~~

.. code-block:: text

   <query>      ::= "(" "nodes" <enum-ref> <node-pred>? ")"
                  | "(" "edges" <enum-ref> <edge-pred>? ")"
                  | "(" "neighbors" <expr> <enum-ref> <direction> <enum-ref> ")"
                  | "(" "hyperedges" <enum-ref> <hedge-pred>? ")"
                  | "(" "members-of" <expr> <enum-ref> ")"
                  | "(" "hyperedges-of" <expr> <enum-ref> ")"

   <elem-name>  ::= ":as" <symbol>
   <direction>  ::= ":out" | ":in" | ":any"
   <node-pred>  ::= <cond>
   <edge-pred>  ::= <cond>
   <hedge-pred> ::= <cond>

**[draft ruling — Phase 1 review, R9 verification repair]** *Every*
``<enum-ref>`` *operand position is typed, and* ``E-TYPE-011`` *is the code for
all of them.* The rule is stated once here as a class rather than per form,
because the R9 chapters added four such positions and a per-form restatement
left each new one without a rejection:

- ``NodeType`` — ``nodes``, ``neighbors``' **fourth** operand, ``the``
  (§2.10), ``(domain <enum-ref>)`` (§2.3), ``deffield``'s ``:member`` operand
  (§2.9), the annotation of an ``add-hyperedge`` member item (§2.8) and both
  positional operands of a ``rung`` (§2.9);
- ``EdgeType`` — ``edges``, ``neighbors``' **second** operand,
  ``edge-between`` (§2.10) and a ``rung``'s ``:via`` operand (§2.9);
- ``HyperedgeType`` — ``hyperedges``, ``members-of`` and ``hyperedges-of``;
- ``EventType`` — ``emit`` (§2.8).

An operand naming a member of any other enum kind is ``E-TYPE-011``, checked
statically. It is a *kind* check and nothing more: whether the named type and
member exist at all is ``E-LOAD-030``/``E-LOAD-031`` (§1.5). ``neighbors``
therefore takes two — an ``EdgeType`` for the relation traversed and a
``NodeType`` for the elements yielded (below) — and swapping them is
``E-TYPE-011`` at both positions. Predicates and bodies refer to the candidate
element as ``it``, or by the ``:as`` name of the iterating form.

Element and result types:

.. list-table::
   :header-rows: 1
   :widths: 24 18 20 38

   * - Query
     - Result
     - ``it`` is
     - Ranges over
   * - ``nodes``
     - ``NodeSet``
     - ``NodeRef``
     - Every node of the given ``NodeType``.
   * - ``edges``
     - ``EdgeSet``
     - ``EdgeRef``
     - Every dyadic edge of the given ``EdgeType``.
   * - ``neighbors``
     - ``NodeSet``
     - ``NodeRef``
     - Nodes **of the annotated** ``NodeType`` reachable from the operand
       across that ``EdgeType`` in the given direction. Each such node appears
       **once**, however many qualifying edges reach it (below).
   * - ``hyperedges``
     - ``HyperedgeSet``
     - ``HyperedgeRef``
     - Every hyperedge of the given ``HyperedgeType``.
   * - ``members-of``
     - ``NodeSet``
     - ``NodeRef``
     - The members of the hyperedge the operand denotes.
   * - ``hyperedges-of``
     - ``HyperedgeSet``
     - ``HyperedgeRef``
     - The hyperedges of that type the operand node belongs to.

**Hyperedges are first-class** (Amendment D ruled **NATIVE HYPEREDGE**
2026-07-29; Amendment AE clause (vi), analysis §9 sub-ruling D-1). A hyperedge
is a typed graph object with an identity and a member list — not sugar for a
set of dyadic edges and not a bipartite encoding the language can see.
``(members-of h HyperedgeType/ECONOMIC_SECTOR)`` is therefore **one lookup
against one object**, and there is no member↔member edge anywhere for
``edges``/``neighbors`` to walk: Anti-Pattern VIII.9 is preserved by
construction rather than by policy. The dyadic forms above are untouched —
``edges`` and ``neighbors`` range over the strictly dyadic morphism layer
(II.9), which coexists with the hyperedge layer in one substrate under
sub-ruling D-2 (type-level separation, one substrate, typed homes). Whether an
implementation *stores* hyperedges as a Levi/incidence bipartite graph is its
own business and is unobservable here.

**[draft ruling — Phase 1 review]** ``members-of`` and ``hyperedges-of`` take
the ``HyperedgeType`` as a **mandatory second operand**, even though the first
operand already denotes a hyperedge (or a node incident to one). BSL has no
type variables (§3.1), so a ``HyperedgeRef`` does not carry its type
statically; the annotation is what makes ``ceiling(query)`` computable at load
(§3.7), and therefore what keeps a fold over members statically bounded. At
evaluation, a ``members-of`` whose referent is not of the annotated type is
``E-EVAL-032`` — never a silently empty set.

**Iteration order is part of the contract.** A query yields its elements in
**ascending node-id / (source-id, target-id, edge-type) / hyperedge-id
lexicographic byte order** **[draft ruling — Phase 1 review]** — never in
graph-internal storage order. This is the language-level answer to the
cross-language iteration-order trap; it makes fold results independent of
insertion history and of the underlying graph library.

That order is *total* only because each of the three keys identifies at most
one element. For nodes and hyperedges the id is the identity. For edges the key
is the ``(source-id, target-id, edge-type)`` triple, and it is a **key** rather
than a sort field because both points at which an edge can enter the graph
refuse a second one: an ``add-edge`` duplicating an existing edge is
``E-EVAL-031`` (§2.8) and a hydration seeding the same triple twice is
``E-LOAD-044`` (§3.9).

**[draft ruling — Phase 1 review]** The same rule applies *inside* a
hyperedge: ``members-of`` yields members in ascending node-id byte order, and a
hyperedge's **declared** member order — the order ``add-hyperedge`` (§2.8) or a
scenario hydration listed them in — is never observable. A member list is a
set, not a sequence.

**[draft ruling — Phase 1 review, R9 verification repair]** *A* ``NodeSet``
*is a set, and* ``neighbors`` *yields each node exactly once.* A node reachable
from the operand across two or more qualifying edges — two ``SOLIDARITY`` edges
in opposite directions under ``:any``, an ``:out`` and an ``:in`` edge of one
type — appears **once** in the result. This is the only reading compatible with
the total order above: the order is ascending id byte order and a duplicated id
has no defined position relative to its twin, so a multiset result would leave
``(fold count (neighbors self EdgeType/SOLIDARITY :any NodeType/SOCIAL_CLASS))``
reading 1 or 2 by implementation choice — two conforming implementations
disagreeing on a tick hash, which is the failure this whole section exists to
prevent. The alternative reading (a multiset, one element per traversed edge)
is recorded as **rejected** for that reason (D72).

The consequence is worth stating in the form an author meets it: **a fold over**
``neighbors`` **counts and sums per node, never per edge.** A rule that means
"once per contributing edge" — a per-edge emission, a total of tie strengths —
folds over ``edges`` instead, or iterates one with ``for-each`` (§2.8), and
reads the relation there; ``neighbors`` answers *which nodes*, not *how many
ways*. ``members-of`` and ``hyperedges-of`` carry the same property for the same
reason — which D25 above already said of a member list.

**[draft ruling — Phase 1 review, R9 chapter C8]** ``neighbors`` *carries its
result* ``NodeType`` *as a mandatory fourth operand.* §2.5 permits a foreign
node type's ``:field`` "only inside a fold body over that type", and a fold
over ``nodes`` carries that annotation in the query's operand. ``neighbors``
did not: it yielded an untyped ``NodeSet``, so this document never said whether
``(fold mean (neighbors self EdgeType/TENANCY :in) social-class/consciousness
:weight …)`` typechecks — and six systems need exactly that read. This is
**D24's problem verbatim**, and it takes D24's fix: the type becomes an
operand, because §3.1 gives references no static type and an annotation is the
only thing that can supply one. With it, a fold body over ``neighbors``
legalises the annotated type's fields exactly as a fold over ``nodes`` does,
and a neighbour that is not of the annotated type is simply **not in the set** —
this operand *filters*, where ``members-of``'s D24 operand *asserts*, because a
node's edge may legitimately reach several node types while a hyperedge has one
type.

The operand is mandatory rather than optional, and that is a **breaking change
to a form that already existed**. What the estate holds, stated exactly (all
verified 2026-08-10): **no conformance vector and no content rule exercises**
``neighbors`` — zero occurrences under ``rust/crates/babylon-bsl/tests/``
(twelve ``.bsl`` vectors) and under ``rust/crates/babylon-tick/content/`` — so
no blessed expectation moves and there is no vector re-bless to pay. The
``babylon-bsl`` crate, however, **does** implement the pre-change form:
``bound_checker.rs`` reads the ceiling operand of ``neighbors`` at index 2 and
bounds it against the edge type alone, and a unit test pins that three-operand
spelling together with the edge-type-only bound D52 revises. Those are updated
when Phase 1 implements this chapter — the correction costs a grammar edit and
a crate change, which is the cheapest of the three prices it could have carried
and the reason to pay it now rather than defer. An optional operand would have
left the untyped reading legal and the under-determination alive.

``ceiling(neighbors)`` is correspondingly tightened in §3.7.

**[draft ruling — Phase 1 review, R9 chapter C8]** ``:as`` — *naming the
element, and what* ``it`` *actually means.* Two passages of this document
disagreed: §2.5 declares ``it`` "reserved and always in scope, never declared
and never shadowed (``E-PARSE-022``)", while §3.7's cost model discusses "a
fold over members nested inside a fold over hyperedges", which needs two live
elements at once. Four systems need a two-hop rule and none could be authored
with confidence.

The resolution is a reading, not a repeal. **``it`` always denotes the element
of the innermost enclosing iterating form.** That is rebinding by construction
— ``it`` is never *declared*, so there is no declaration for an inner form to
shadow, and ``E-PARSE-022``'s prohibition (content may not declare or shadow
``it``) is untouched and still means what it said. What was missing was a way
to reach an *outer* element, and ``:as`` supplies it:

.. code-block:: scheme

   (fold sum (hyperedges HyperedgeType/ECONOMIC_SECTOR) :as sector
         (fold sum (members-of sector HyperedgeType/ECONOMIC_SECTOR)
               (field-of it social-class/wealth)))

- A ``:as`` name is in scope for the whole body of its form, **including
  nested bodies**, and has the query's element type.
- Names share the rule's binding namespace: colliding with a binding or another
  ``:as`` name is ``E-PARSE-030``, and naming ``self`` or ``it`` is
  ``E-PARSE-022``.
- A ``:as`` name referenced outside its body is ``E-TYPE-012``, the same code
  and the same reason as ``it`` outside a query context.
- Naming is optional everywhere. Single-level rules keep reading ``it``, and
  **no existing form changes meaning** — which is the property that made
  naming the safer of the two candidate resolutions, against rebinding rules
  that would have had to carve an exception into ``E-PARSE-022``.

2.7 Expressions, intrinsics, folds, guards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   <expr>      ::= <literal> | <symbol> | <enum-ref>
                 | "(" <arith> <expr> <expr> ")"
                 | "(" <intrinsic-name> <expr>* ")"
                 | "(" "if" <cond> <expr> <expr> ")"
                 | <fold>
                 | <accessor>                       ; §2.10
                 | <selection>

   <arith>     ::= "+" | "-" | "*" | "/"
   <literal>   ::= <int-lit> | <scaled-lit> | <bool-lit>

   <fold>      ::= "(" "fold" <fold-op> <query> <elem-name>?
                       <expr> ( ":weight" <expr> )? ")"
   <fold-op>   ::= "sum" | "mean" | "min" | "max" | "count"

   <selection> ::= "(" "select-max" <query> <elem-name>? <expr> ")"
                 | "(" "select-min" <query> <elem-name>? <expr> ")"

Arithmetic is strictly binary; ``(+ a b c)`` is ``E-PARSE-040``. This keeps
the reduction order explicit in the source rather than implied by a
left-fold convention — a cross-language float trap the design document names.

**[draft ruling — Phase 1 review, R9 verification repair]** *Arity and closed
terminal sets each get a code, rather than an unnumbered prose prohibition.*
Every form's operand count is fixed by its production, and a count that differs
from it is ``E-PARSE-042``; ``E-PARSE-040`` remains the arithmetic-specific
spelling of that class, and the three-operand ``neighbors`` of the pre-C8
grammar (§2.6, D51) is the case this revision creates. A head symbol that is
not a member of a closed terminal set — ``<fold-op>`` above, ``<cmp>`` (§2.4),
``<update-op>`` (§2.8) or ``<arith>`` — is ``E-PARSE-015``, which is where two
of §6.3's four silent-degradation corrections (unknown aggregation, unknown
comparison operator) land. Both were previously written as prohibitions with no
code, which left the conformance families that must pin them unable to name
what they expect (§6.2 families 17 and 19).

**Guards** are ``(if <cond> <a> <b>)`` in expression position and
``(guard <cond> <effect-item>+)`` in effect position (§2.8). Both branches of
``if`` must have the same static type (``E-TYPE-020``).

**Intrinsic calls** are ordinary forms whose head is a symbol declared in the
intrinsic table. Transcendentals and ``round-half-even`` are **never** language
primitives — they exist only as named intrinsics with pinned deterministic
implementations. The names this document has used to illustrate that
(``sigmoid``, ``exp``, ``log``, ``tanh``, ``sqrt``, ``entropy``) are
**illustrative of the class, not a table of intrinsics that exist** — a
reading the R9 gap analysis found this document inviting. What is declarable is
governed by §3.10, which holds the set at ``{exp, log}`` and rules ``sigmoid``
prohibited outright. BSL cannot define an intrinsic; ``intrinsic`` forms only
*declare* what the kernel provides, so that the typechecker and the fuel
bound-checker are computable from content alone:

.. code-block:: text

   <intrinsic-decl> ::= "(" "intrinsic" <symbol>
                            ":params" "(" <type-name>* ")"
                            ":returns" <type-name>
                            ":cost" <int-lit>
                        ")"

A declaration whose signature disagrees with the kernel's registration is
``E-LOAD-020``; a call to an undeclared intrinsic is ``E-LOAD-021``. The
*contents* of the intrinsic table are Program 27 Phase 2 work and are not fixed
by this document — only the calling convention, the declaration form, the
reserved-name prohibition below, and the "never a primitive" prohibition are
normative here. §3.10 records the cap the intrinsic table is held to and the
rider slate proposed against it.

**[draft ruling — Phase 1 review, R9 chapter C1]** *Form-head symbols are
reserved against the intrinsic namespace.* An intrinsic call is
``"(" <intrinsic-name> <expr>* ")"``, so an intrinsic whose name collided with
a form head would make ``(field-of it x/y)`` ambiguous between an accessor and
a call. Every head symbol listed as a form tag in §5.2 is therefore reserved:
declaring an intrinsic with one of those names is ``E-LOAD-024``. The
prohibition is checked at load against the §5.2 list, not against a separate
registry, so adding a form tag automatically reserves it.

**Selection** returns the *element* that extremises a score, where a fold
returns the extremised *value*. Eleven systems pick an element and then act on
it — the winning claimant, the winning faction, the best platform, the FPTP
winner, the top claims holder, the principal field (R9 gap analysis §2, Q4) —
and until this chapter no expression form yielded a ``NodeRef`` other than
``self`` and §2.8's effect-list-scoped minted names, so none of them was
authorable.

.. code-block:: scheme

   (update-node (select-max (nodes NodeType/ORGANIZATION)
                            (field-of it organization/claim-strength))
                organization/holds-office (set #t))

- The result type is the query's element type: ``NodeRef`` for ``nodes``,
  ``neighbors`` and ``members-of``; ``EdgeRef`` for ``edges``;
  ``HyperedgeRef`` for ``hyperedges`` and ``hyperedges-of``. ``it`` is bound in
  the score expression exactly as it is in a fold body.
- **The tiebreak is a property of the language, not of each rule.** Ties are
  broken by §2.6's iteration order: the **first** element in ascending id byte
  order wins, for ``select-max`` and ``select-min`` alike. Every frozen system
  that picks an element carries its own tiebreak today, and several carry none;
  hoisting it here means a transcribed rule cannot forget one.
- An empty query is ``E-EVAL-021`` — the same code, for the same reason, as
  ``min``/``max`` over an empty set (§4.4). There is no element to return and
  there is no null.
- The score expression must have a **comparable scalar** static type — ``Int``,
  ``Currency``, ``Probability``, ``Intensity``, ``Coefficient`` or ``Real``.
  ``Bool``, ``Enum<T>``, ``Str``, references and sets are ``E-TYPE-016``.
- **Kind is unconstrained on the score** and the result is kind-neutral (a
  reference has no extent). This is not a hole in §3.4: that law polices
  *aggregation*, where an unweighted mean of an intensive quantity across
  classes or space is the recorded variance error. Ranking elements by an
  intensive field aggregates nothing — it orders — so the weighted-mean
  obligation has nothing to attach to.

**[draft ruling — Phase 1 review, R9 chapter C12]** *No set-algebra operator,
and the deferral is now honest.* One system needs a set intersection (shared
memberships between two nodes). This document adds no ``intersect``,
``union`` or ``difference``: a dedicated operator would need a result type
that is a ``NodeSet`` **not** produced by a ``<query>``, which §3.1's "only
consumable by ``fold``, ``exists``, ``forall``" line and §3.7's
``ceiling(query)`` both assume away. Intersection is expressible today, at
quadratic fuel cost, with C8's naming and C12's reference identity:

.. code-block:: scheme

   (fold count (hyperedges-of a HyperedgeType/COMMUNITY) :as ha
         (if (exists (hyperedges-of b HyperedgeType/COMMUNITY) (= it ha))
             1 0))

The earlier judgement to defer rested on a form that could not actually be
written — ``it`` meant the inner element in both positions and references had
no comparison. Both holes are closed above, so the deferral now stands on its
own: **revisit when a second system asks**, and pay the quadratic cost
visibly in ``:fuel`` until then, where a reviewer can see it.

**Folds and selection are the only expression-position iteration
constructs**, and §2.8's ``for-each`` is the only one in effect position.
There is no recursion, no ``while``, no ``loop``, no user-defined function, and
no way to name a rule from inside a rule. Totality is therefore syntactic, and
the static bound of §3.7 is computable.

2.8 Effects — the typed structural verbs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   <effect-item> ::= <verb>
                   | "(" "guard"    <cond>  <effect-item>+ ")"
                   | "(" "for-each" <query> <elem-name>? <effect-item>+ ")"

   <verb> ::= "(" "update-node"  <expr> <qname> <update-op> ")"
            | "(" "update-edge"  <expr> <qname> <update-op> ")"
            | "(" "add-node"     <enum-ref> <expr> <field-init>* ")"
            | "(" "remove-node"  <expr> ")"
            | "(" "add-edge"     <enum-ref> <expr> <expr> ":strength" <expr>
                                 <field-init>* ")"
            | "(" "remove-edge"  <enum-ref> <expr> <expr> ")"
            | "(" "add-hyperedge"    <enum-ref> <expr> <members> <field-init>* ")"
            | "(" "update-hyperedge" <expr> <qname> <update-op> ")"
            | "(" "remove-hyperedge" <expr> ")"
            | "(" "update-membership" <expr> <expr> <qname> <update-op> ")"
            | "(" "emit"         <enum-ref> <payload-item>* ")"

   <update-op>   ::= "(" "add"   <expr> ")"
                   | "(" "sub"   <expr> ")"
                   | "(" "set"   <expr> ")"
                   | "(" "scale" <expr> ")"
   <members>     ::= "(" "members" <member-item>+ ")"
   <member-item> ::= <expr>
                   | "(" "member" <enum-ref> <expr> <field-init>* ")"
   <field-init>  ::= "(" <qname> <expr> ")"
   <payload-item>::= "(" <symbol> <expr> ")"

The four ``<update-op>`` forms are exactly today's four-operation effect enum
— ``add`` = ``increase``, ``sub`` = ``decrease``, ``set`` = ``set``,
``scale`` = ``multiply``. The set is closed: a fifth head there — the
``(unset …)`` the frozen estate reaches for (§3.8) — is ``E-PARSE-015``.
Of the **ten** structural verbs, **five** are the
addition the design document's §6.4 audit found necessary (20 of 39 system
modules mutate graph structure); **two** — ``add-hyperedge`` and
``remove-hyperedge`` — are what the Amendment D ruling adds, since if a
hyperedge is a first-class object, minting and retiring one is a first-class
verb; **two** — ``update-edge`` and ``update-hyperedge`` — are what R9
chapters C2 and C12 add, below; and **one** — ``update-membership`` — is what
Amendment AG clause (i) adds, below.

**[draft ruling — Phase 1 review, R9 chapter C2]** ``update-edge``, *and why
the dyadic layer differs from D26.* Eight systems overwrite a standing edge's
attributes (R9 gap analysis §2, Q3): ``value_flow`` on four edge types,
SOLIDARITY decay, MEMBERSHIP accrual, ``field_gradients``, the EdgeTransition
mode fields. Before this chapter nothing in the verb set could, and the
question that had to be answered first is whether D26's refusal to mutate a
hyperedge in place carries over. **It does not.** D26's stated rationale is
that a partially-mutated *member list* must be unrepresentable, so membership
changes go through whole-object replacement and the member-count check stays at
a single point. A dyadic edge has no member list; there is no partial state for
in-place mutation to leave behind, and the ``:max-members`` check it protects
does not exist on the dyadic layer. The rationale is therefore specific to the
construct it was written about, and re-using it here would be an argument from
symmetry rather than from the reason. (C12 revisits the *other* half of D26 —
mutation of a hyperedge's own declared fields — on exactly this reasoning.)

**[draft ruling — Phase 1 review, R9 chapter C2]** ``update-edge`` *takes an*
``EdgeRef``, *not a type-and-endpoints triple.* It mirrors ``update-node``
operand for operand — element, field qname, update-op — because the effect
positions that will supply it are ``it`` inside a ``for-each`` over ``edges``
(§2.8, chapter C6) and the result of ``select-max`` (§2.7, chapter C5), both of
which yield refs. Giving the verb a second arity taking ``<enum-ref> <expr>
<expr>`` would have made it the grammar's only overloaded head — the exact
objection D26 raises against an overloaded ``add-edge``. Rules that hold the
endpoints instead of the ref reach the edge through §2.10's ``edge-between``
accessor, which is one form used in expression position rather than a second
shape of a verb. The R9 gap analysis §2 (Q3) sketched the triple form; D36
records the divergence.

A ``<qname>`` whose owning type (§2.9) is not the element type the verb's
``<enum-ref>`` names is ``E-TYPE-014`` — a **static** check on ``add-node``,
``add-edge`` and ``add-hyperedge``, whose element type is an operand. On
``update-node``/``update-edge`` the element is a reference, which §3.1 gives no
static type, so the same disagreement surfaces at evaluation as ``E-EVAL-033``
(§2.10). A ``<field-init>`` on ``add-edge`` naming the implicit
``<edge-type>/strength`` field is ``E-PARSE-041``: the ``:strength`` operand is
that field's only writer at mint time, and two writers for one field in one
form is an authoring bug rather than a precedence question.

``update-edge`` inherits the structural-verb discipline unchanged: it obeys the
I.15 edge-mode state machine, so a write that would take an edge to a mode the
machine does not admit from its current one is ``E-EVAL-030``, and a store
outside the target field's declared range is ``E-EVAL-020`` (§3.3) — never a
clamp, never a silent no-op.

``add-hyperedge``'s ``<enum-ref>`` is a ``HyperedgeType`` member, its ``<expr>``
is the new hyperedge's id (as ``add-node``'s is a node id), and ``<members>``
names its member nodes. The grammar's ``<member-item>+`` makes a **zero-member
hyperedge unexpressible**; the upper end is the declared ``:max-members``
ceiling of §3.7, checked statically. A member item is a bare ``<expr>`` where
the hyperedge type carries no membership payload, and the annotated ``member``
form where it does — the Amendment AG ruling below.

**[draft ruling — Phase 1 review]** *Id operands are effect-list-scoped
names* (implementation-discovered, 2026-07-30, Phase 1 Task 16). The id
operand above is written as ``<expr>``, but no expression form yields a
*fresh* identity and §2.5 gives rules no way to declare one. The executor
therefore reads it as a **symbol introducing an effect-list-scoped name**
for the minted object: later effect items in the same list may reference it
(roster replacement needs exactly this), the substrate mints the actual
identity, and the no-shadowing discipline of ``E-PARSE-022`` extends to
these names. A non-symbol id operand is a loud error pending the review.

**[draft ruling — Phase 1 review]** *Two verbs, not an overloaded* ``add-edge``.
Membership is minted by its own typed verb rather than by an ``add-edge``
variant carrying a member set. Three reasons, each following the rest of this
document rather than inventing a rule for the occasion: the head symbol *names*
the form (§1.3), so one tag with two arities would be the grammar's only
exception; ``add-edge``'s first operand is an ``EdgeType`` and
``add-hyperedge``'s is a ``HyperedgeType``, so overloading needs a union type
§3.1 does not have; and the member-count ceiling attaches to the hyperedge verb
alone. It also keeps the ruling legible in the grammar itself — **a clique
expansion is not expressible**, because no verb takes a member set and emits
edges.

**[draft ruling — Phase 1 review;** *field-mutation half superseded by the C12
ruling below* **]** *Membership changes are whole-hyperedge replacement.* There
is no ``add-member``/``remove-member`` verb: a rule that changes a formation's
roster emits ``(remove-hyperedge h)`` and then ``(add-hyperedge …)`` in one
effect list, applied in source order (below). This keeps the member-count check
at a single point (§3.7) and makes a partially-mutated hyperedge
unrepresentable. The cost was stated rather than hidden: **per-membership
payload** (the role/strength/visibility fields today's Python
``CommunityMembership`` carries) and **mutation of a hyperedge's own declared
fields** were both inexpressible in the revision that made this ruling. The
second of those is retired immediately below (D65); the first was escalated by
D66 and is retired by the Amendment AG rulings below
(D79–D84), which change what a membership *carries* and leave this row's
member-list discipline exactly as written. Neither was a silent omission.

**[draft ruling — Phase 1 review, R9 chapter C12]** *D26's second half is
closed:* ``update-hyperedge`` *writes a hyperedge's own declared fields.* The
verb mirrors ``update-node`` and ``update-edge`` operand for operand, and it is
added on exactly the reasoning C2 sets out above: D26's rationale is that a
partially-mutated **member list** must be unrepresentable, and writing a
declared field of a hyperedge leaves no member list partially anything. The
member list stays whole-object replacement (``remove-hyperedge`` then
``add-hyperedge`` in one effect list), so the ``:max-members`` check stays at
its single point and D26's actual guarantee is untouched. What is retired is
only the *incidental* consequence that a formation's own state was frozen for
the life of the object.

A ``<qname>`` whose owning type is not the referent's ``HyperedgeType`` is
``E-EVAL-033`` (§2.10), since a ``HyperedgeRef`` carries no static type; the
range and I.15 disciplines apply as they do to the other two update verbs.

**[draft ruling — Phase 1 review, Amendment AG (i)]** ``update-membership`` —
*D26's first half is closed, and the member list still crosses whole.* The
verb writes a **payload field of an existing membership** and nothing else. It
mirrors the other three update verbs in its trailing operands (a ``<qname>``
and an ``<update-op>``) and differs only in its element position, which takes
**two** operands rather than one: BSL mints no reference kind for a
membership, so the pair is named by its key — the hyperedge first, the member
second (§2.12).

.. code-block:: scheme

   (for-each (members-of c HyperedgeType/COMMUNITY)
     (update-membership c it community/visibility (scale 0.9c)))

- **The member list is untouched.** There is still no
  ``add-member``/``remove-member`` verb, and a roster change is still
  ``remove-hyperedge`` then ``add-hyperedge`` in one effect list (D26). The
  ``:max-members`` check therefore stays at its single point, a partially
  mutated member list stays unrepresentable, and Anti-Pattern VIII.9 survives
  verbatim — this verb changes what a membership *carries*, never how many
  objects cross. The payload of a member dropped by a roster replacement does
  not survive it, and re-stating the payload is that idiom's price, unchanged.
- **A pair that is not a membership is** ``E-EVAL-038`` — the member node is
  not in that hyperedge's member list — never a silent no-op and never a
  quietly minted membership. A hyperedge operand that is not of the
  ``<qname>``'s owning ``HyperedgeType``, and a member operand that is not of
  the payload declaration's ``:member`` ``NodeType``, are both ``E-EVAL-033``
  (§2.10 discipline 1, which now reads across two operands rather than one);
  neither is statically checkable, because §3.1 gives references no type.
- The range and I.15 disciplines apply exactly as they do to the other update
  verbs: a store outside the payload field's declared range is ``E-EVAL-020``,
  never a clamp.
- *Why a verb at all, given Amendment AG (iii).* Clause (iii)'s "adds no verb"
  is the closure list of NORTH_STAR §0 and Article V's action registry — the
  same register as "no intrinsic, no severity rule, no constructor family".
  Clause (i) of the same amendment obliges payload to **mutate only through
  effects**, and ADR189 clause (iv) names the "accessor/verb surface" as
  exactly what this document owes. An effect-position write is therefore
  required by the amendment, not licensed against it; what stays closed is the
  player/state verb registry and the algebra, neither of which this touches.

**[draft ruling — Phase 1 review, Amendment AG (i)]** *Payload is initialised
at mint, totally, against an annotated member item.* Where a hyperedge type
declares any membership payload (§2.9), every item of ``add-hyperedge``'s
``<members>`` list is the annotated form ``(member <enum-ref> <expr>
<field-init>*)``, and its field-inits are **exactly** the declared payload
fields of that *(hyperedge type, member node type)* pair — no more and no
fewer.

.. code-block:: scheme

   (add-hyperedge HyperedgeType/COMMUNITY h
     (members (member NodeType/SOCIAL_CLASS c1 (community/strength 0.4c)
                                               (community/visibility 0.5p))
              (member NodeType/SOCIAL_CLASS c2 (community/strength 0.7c)
                                               (community/visibility 0.2p))))

- *The annotation is D24's fix, for the third time.* The owed field set
  depends on the member's node type, and §3.1 gives a ``NodeRef`` no static
  type, so without the ``<enum-ref>`` the completeness check would be a
  runtime discovery. With it the check is **static**: a missing payload field,
  or a bare member item under a hyperedge type that declares payload, is
  ``E-LOAD-047``. The annotation *asserts* rather than filters, exactly as
  D24's does: a member that is not of the annotated type is ``E-EVAL-033``.
- *Bare items stay legal where nothing is owed*, so every existing
  ``add-hyperedge`` form keeps its meaning and its bytes. A bare item under a
  payload-declaring type is not a shorthand for defaults — there are none.
- A field-init naming a field owned by another type is ``E-TYPE-014`` (the
  static check the minting verbs already carry) and one naming the same
  payload field twice in one member item is ``E-PARSE-041``, the existing
  two-writers-for-one-field code.
- *Why total rather than optional.* ``add-node`` and ``add-edge`` carry
  ``<field-init>*`` and no completeness rule because hydration and later
  effects can seed a node's field; a membership minted at runtime has exactly
  one writer at that moment and no ``:default`` anywhere in the element-state
  half of the language (§3.5's opt-in is a *binding* property). The
  alternative — permit partial mint and let the first read be ``E-EVAL-033`` —
  converts a decidable authoring error into a runtime one, which is the
  direction §4.6 says a chapter must never move the language. ``add-edge``'s
  mandatory ``:strength`` operand is the same reasoning already applied to the
  one field that had no other writer at mint. Hydration carries the identical
  obligation (§3.9 clause 6).

``emit``'s ``<enum-ref>`` is an ``EventType`` member — a member of another
enum kind there is ``E-TYPE-011`` under §2.6's class rule; payload items are
name/expression pairs. There is no string interpolation in a payload.

**[draft ruling — Phase 1 review, R9 chapter C6]** ``for-each`` — *bounded
iteration in effect position.* Nine systems apply a verb once per matching
element (R9 gap analysis §2, Q5): an emit per contributing SOLIDARITY edge,
a write to both endpoints of every value-bearing edge, a decay on every
incident edge, a transition per territory, the two sibling nodes of a class
split. None was expressible: ``<effect-item>+`` fixes arity at parse time,
folds live in expression position only, and ``it`` outside a query context is
``E-TYPE-012`` — so "for every matching element, apply a verb" had no form at
all, and the surveys reached for one-summed-emit fallbacks that are content
rulings in disguise.

.. code-block:: scheme

   (for-each (edges EdgeType/SOLIDARITY)
     (update-edge it solidarity/strength (scale 0.95c))
     (emit EventType/SOLIDARITY_DECAYED (strength (field-of it
                                                            solidarity/strength))))

- ``it`` is bound inside the body to the current element, with the query's
  element type (§2.6's result table). Outside a ``for-each``, ``for-each``'s
  body, or a query predicate or fold body, ``it`` remains ``E-TYPE-012``.
- **The query is materialized against the rule's pre-state**, in §2.6's
  iteration order, before any effect in the rule's list is applied. This is not
  a convenience: §4.2's law that *a rule can never observe its own effects*
  would otherwise be silently repealed by an iteration whose membership
  depended on an earlier verb in the same list. Every expression anywhere in an
  effects list — a verb's operands, a ``guard``'s condition, a ``for-each``'s
  query — is evaluated against the pre-state, and the collected effects are
  then applied.
- **Application order is total.** The body runs once per element in iteration
  order (outer), and the body's own items apply in source order (inner). Nested
  ``for-each`` composes the same way. With §4.2's subject order this leaves no
  unordered reduction anywhere in the language.
- **An empty query applies nothing, and is not an error.** This is the one
  place where an empty set is quiet, and the distinction is principled: §4.4's
  ``mean``/``min``/``max`` must produce a *value* and have none to produce, so
  they are ``E-EVAL-021``; an iteration is a *command*, and "do it to each of
  no elements" is completely determined. The reading that would make it loud
  would also make a correct rule fail on a legitimately empty graph.
- **Totality holds.** The set is materialized before the body runs and its size
  is bounded by the declared ceiling, so this is a bounded iteration and not a
  loop; §3.7 charges it exactly as it charges ``exists``/``forall``.

One consequence worth recording where the port train will look for it: with
``for-each`` in hand, a bulk structural operation (re-parenting every claim of
a collapsing sovereign, severing every exploitation edge) is **expressible in
content**. A Rust bulk primitive for the same job therefore survives only as a
*performance* escape, which needs measurement rather than assertion.

**Effect ordering and application.** Effects are collected in source order and
applied in source order at the point the rule fires. Structural verbs obey the
I.15 edge-mode state machine; a verb that would violate it is an evaluation
error (``E-EVAL-030``), never a silent no-op. Removing a node that does not
exist, adding a node id that already exists, or adding an edge that already
exists are all ``E-EVAL-031`` — absence is never treated as success. The
hyperedge verbs inherit that discipline exactly: removing a hyperedge that does
not exist, adding a hyperedge id that already exists, naming a member node that
does not exist, and naming the **same member twice** in one ``<members>`` list
are all ``E-EVAL-031``. Members are a set; a duplicate is an authoring bug, and
it is never silently deduplicated.

**Prohibited.** There is no I/O, no time source other than a ``:tick``
binding, no
randomness primitive (RNG draws are kernel intrinsics with the kernel's
per-(session, tick, salt) seeding, specified in
:doc:`/reference/determinism-contract`), no graph mutation outside this verb
set, no reflection, and nothing unbounded. In particular there is **no clique
expansion**: no verb in this set converts a member list into pairwise edges, so
the combinatorial object Anti-Pattern VIII.9 bans has no BSL representation
(Amendment D, D-1).

2.9 Field and manifest declarations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   <deffield> ::= "(" "deffield" <qname>
                      ":type" <type-name>
                      ":kind" ( "intensive" | "extensive" )
                      ( ":member" <enum-ref> )?
                  ")"

   <manifest>   ::= "(" "manifest" <symbol> <ceiling>+ <rung>* <adjunction>* ")"
   <ceiling>    ::= "(" "ceiling" <enum-ref> ":ceiling" <int-lit>
                        ( ":max-members" <int-lit> )? ":invariant"? ")"
   <rung>       ::= "(" "rung" <symbol> <enum-ref> <enum-ref>
                        ":via" <enum-ref> ":substrate"? ")"
   <adjunction> ::= "(" "adjunction" <symbol> <qname> <qname>
                        ":rung" <symbol> ( ":weighted-by" <qname> )? ")"

The ``rung`` and ``adjunction`` rows are Amendment AG clause (ii)'s: a scenario
declares the rungs of its scale lattice and the ``allocate``/``aggregate``
instances that run along them. Their meaning, their validation and the two
standing rulings that bind every rung are §3.9's; what belongs here is only
that they are **manifest children** — the same form, and therefore the same
digest, as the ``:invariant`` ceiling rows the substrate ruling keys off
(D85).

A ``ceiling`` row's ``<enum-ref>`` is a ``NodeType``, ``EdgeType`` or
``HyperedgeType`` member. ``:max-members`` is **mandatory** on a
``HyperedgeType`` row and **illegal** on the other two; ``:invariant`` is legal
on a ``NodeType`` or ``EdgeType`` row and illegal on a ``HyperedgeType`` row
(§3.9). Any of those mismatches is ``E-LOAD-042``. The semantics of the two
numbers are §3.7's; the flag's are §3.9's.

**[draft ruling — Phase 1 review, R9 verification repair]** *The manifest must
be complete for the types the content set actually uses.* The grammar demands
``<ceiling>+`` — one row or more — and nothing until now said which rows were
owed. A content set that queries a type, names it in a structural verb,
reaches it through ``the`` (§2.10), or (since Amendment AG (ii)) names it in a
``rung`` declaration, and whose manifest carries no row for that type, is
``E-LOAD-045``. The omission is not survivable by defaulting:
``ceiling(query)`` (§3.7) is not computable without the row, so ``bound(rule)``
has nothing to compare against ``:fuel``; ``the``'s ``E-LOAD-043`` tests for a
ceiling "other than 1" and a *missing* row is neither 1 nor other than 1; and
``:invariant`` (§3.9) is a flag on a row that does not exist, so its
``E-LOAD-013`` check silently never fires. The obligation is scoped to the
vocabulary the content set mentions, not to the whole registry — a scenario
owes no row for a type nothing touches.

**[draft ruling — Phase 1 review]** The design document says intensivity is "a
per-field declaration (``:kind intensive|extensive``) on model fields" without
saying where the declaration lives. It lives here, in BSL content, as
``deffield``. Rationale: the typechecker must be derivable from content alone
for this document to satisfy III.12(a); a kind that lived only in Rust
attribute macros would make a second implementation impossible to write from
the spec. A ``deffield`` whose type or kind disagrees with the kernel's model
registration is ``E-LOAD-022`` — the two must agree, and the kernel is checked
against content, not the reverse.

**[draft ruling — Phase 1 review, R9 chapter C1]** *A field's owner may be a
node type, an* ``EdgeType`` *or a* ``HyperedgeType``. The first segment of a
``deffield``'s ``<qname>`` names the owning graph-element type; until this
revision it could only name a node type, which is what left §2.4's
``EdgeCondition`` row unwritable. A first segment naming no registered
``NodeType``, ``EdgeType`` or ``HyperedgeType`` member is ``E-LOAD-023``.

*The segment↔member correspondence, stated because it was only ever implied.*
``social-class/wealth`` owns off ``NodeType/SOCIAL_CLASS`` by a rendering the
document used from its first revision and never wrote down: **lowercase the
enum member identifier and replace each** ``_`` **with** ``-``. The result must
be a valid ``symbol`` per §1.4; a member whose rendering is not (a leading
digit, say) is ``E-LOAD-033``. Because one namespace of renderings now spans
three enum types, the registry must keep them **pairwise disjoint**: a
``NodeType`` and an ``EdgeType`` (or either and a ``HyperedgeType``) rendering
to the same symbol is ``E-LOAD-032``, checked at load over the whole closed
vocabulary. Disjointness is a property of the vocabulary, so the check runs
once per content set rather than per field.

**[draft ruling — Phase 1 review, R9 chapter C1]** *Every* ``EdgeType``
*carries one implicitly declared field,* ``<edge-type>/strength``, with
``:type Coefficient`` and ``:kind extensive``. It needs no ``deffield`` — it is
the field ``add-edge``'s ``:strength`` operand writes (§2.8), and before this
revision the language could write it and never read it back. Re-declaring it
explicitly is ``E-LOAD-001`` (a duplicate field declaration), so there is
exactly one home for its type and kind.

The ``Coefficient`` type is the frozen engine's: the ``sum_strength`` /
``avg_strength`` metric of ``engine/event_evaluator.py:174-175`` reads
``solidarity_strength``, declared ``Coefficient`` in
``models/entities/relationship.py:116``. The ``extensive`` kind is the
load-bearing half of the ruling and is chosen so §2.4's coverage row is
honoured rather than half-honoured: under §3.4 an intensive fold body makes
``sum`` an ``E-TYPE-041`` and ``mean`` legal only with a ``:weight``, so an
intensive ``strength`` would have left ``sum_strength`` inexpressible after all.
The extent being aggregated is the **edge population** — a total tie-weight
over a set of edges is additive in exactly the way an intensity across classes
or space is not, which is the distinction §3.4 exists to police. Authors
wanting a genuinely intensive per-edge attribute (``tension``, a rate)
``deffield`` it ``:kind intensive`` and carry the ``:weight`` obligation, and
the recorded variance error stays caught.

**[draft ruling — Phase 1 review, Amendment AG (i)]** *A membership payload
field is a* ``deffield`` *with a* ``:member`` *operand, not a new top-level
form.* The owner of such a field is a **pair** — a member ``NodeType`` inside a
``HyperedgeType`` — and the question the amendment leaves to this document is
whether ``deffield``'s owner axis can carry a pair. It can, because half the
pair is already where a field's owner has always been: the ``<qname>``'s first
segment renders the ``HyperedgeType`` under D31's rendering rule, unchanged,
and ``:member`` names the other half.

.. code-block:: scheme

   (deffield community/strength   :type Coefficient :kind extensive
             :member NodeType/SOCIAL_CLASS)
   (deffield community/visibility :type Probability :kind intensive
             :member NodeType/SOCIAL_CLASS)

*Why not a dedicated top-level form.* Two reasons from this document's own
machinery, and neither is ergonomic:

1. §5.5 hashes ``deffield``, ``intrinsic``, ``manifest`` and ``metric`` forms
   into **sibling digests that** ``ContentDigest`` **combines** — and
   ``ContentDigest``'s composition is
   :doc:`/reference/determinism-contract`'s, not this document's. A new
   top-form would owe a new sibling digest and therefore an edit to a document
   this one deliberately does not reach into. A keyword option lands the
   declaration inside a digest that already exists.
2. A keyword encodes as an ``opt`` form under D20, so the declaration needs no
   new form tag, no numeric id and no new atom kind — the same
   cheapest-available proof of additivity §5.2 relies on, and the reason
   §5.6's bytes survive this revision too.

The rules, all decidable at load:

- The ``<qname>``'s first segment must render a ``HyperedgeType`` member. A
  ``:member`` on a ``deffield`` whose first segment renders a ``NodeType`` or
  an ``EdgeType`` is ``E-LOAD-048``; a first segment that renders nothing
  registered is ``E-LOAD-023`` as before. ``:member``'s own operand is a
  ``NodeType`` member — any other enum kind there is ``E-TYPE-011`` under
  §2.6's class rule.
- **One namespace, one declaration.** A membership payload field shares the
  field namespace with the hyperedge type's own fields, so a ``<qname>``
  resolves to exactly one ``deffield`` and a duplicate is ``E-LOAD-001`` like
  any other. Reading or writing a membership field through ``field-of`` /
  ``update-hyperedge``, or a hyperedge's own field through
  ``membership-field-of`` / ``update-membership``, is ``E-LOAD-046`` — static,
  because the declaration and the reading form are both content, and the same
  shape as §2.11's ``E-LOAD-012``.
- **One declaration is one pair.** A hyperedge type whose members are of two
  node types, both needing an axis of the same name, declares two qnames. The
  cost is real and is taken deliberately: it keeps ``<qname>`` → declaration a
  total function, which is what makes both the wrong-form check above and
  §2.8's mint-time completeness check static rather than runtime.
- Kernel agreement is ``E-LOAD-022``, as for any other ``deffield``: the type,
  the kind and the member half are all checked against the kernel's
  registration of the attributed-membership object.

2.10 Element accessors
~~~~~~~~~~~~~~~~~~~~~~~~

Accessors are the expression forms that read *from a graph element the rule
already holds a reference to*, as against ``:field``/``:const``/``:metric``
bindings, which read from the rule's own environment. They are the R9
chapter-C1/C2/C3/C9 additions and they all share one discipline, stated once
here.

.. code-block:: text

   <accessor> ::= "(" "field-of"     <expr> <qname> ")"
                | "(" "edge-between" <enum-ref> <expr> <expr> ")"
                | "(" "the"          <enum-ref> ")"
                | "(" "metric-of"    <expr> <symbol> ")"
                | "(" "membership-field-of" <expr> <expr> <qname> ")"

.. list-table::
   :header-rows: 1
   :widths: 20 18 62

   * - Form
     - Result
     - Reads
   * - ``field-of``
     - the field's declared type
     - A declared field of the node, edge or hyperedge the ``<expr>``
       denotes. The ``<qname>``'s first segment names the owning type
       (§2.9).
   * - ``edge-between``
     - ``EdgeRef``
     - The edge of the given ``EdgeType`` from the first node operand to the
       second. Absence is ``E-EVAL-034``.
   * - ``the``
     - ``NodeRef``
     - The unique node of a ``NodeType`` whose manifest ``:ceiling`` is 1.
       A ceiling other than 1 is ``E-LOAD-043``; a graph holding no such node
       is ``E-EVAL-035``.
   * - ``metric-of``
     - the metric's declared type
     - A registered **element-indexed** metric, evaluated at the element the
       ``<expr>`` denotes (§2.11).
   * - ``membership-field-of``
     - the field's declared type
     - A declared payload field of the attributed membership keyed by the
       hyperedge the **first** ``<expr>`` denotes and the member node the
       **second** denotes (§2.12). The ``<qname>``'s first segment names the
       owning ``HyperedgeType`` and its declaration names the member
       ``NodeType`` (§2.9). A pair that is not a membership is
       ``E-EVAL-038``.

**The shared discipline.**

1. *The qname carries the type annotation, the reference does not.* §3.1 gives
   ``NodeRef``/``EdgeRef``/``HyperedgeRef`` no type variables, so a reference
   does not carry which ``NodeType``/``EdgeType``/``HyperedgeType`` it belongs
   to. The owning type therefore comes from the ``<qname>``, exactly as D24
   makes the ``HyperedgeType`` a mandatory operand of ``members-of`` for the
   same reason. A ``field-of`` whose referent is not of the qname's owning type
   is ``E-EVAL-033`` at evaluation — **never** a default value and never an
   absent read.
2. *Absence is not a value.* A ``field-of`` against an element that carries no
   value for a declared field is ``E-EVAL-033`` as well; there is no
   ``:optional``/``:default`` on an accessor, because the opt-in to absence is
   a property of a *binding* (§3.5) and an accessor names its element at the
   point of use. §3.8 gives the re-modelling for genuinely optional axes.
3. *Accessors are reads.* No accessor mutates. The verbs of §2.8 are the only
   writes, and §2.8's ``update-edge`` (R9 chapter C2) is the write dual of
   ``field-of`` over an ``EdgeRef``.
4. *Kind and type propagate from the declaration.* A ``field-of`` expression
   has the ``deffield``'s ``:type`` as its static type and its ``:kind`` as its
   kind (§3.4), identically to a ``:field`` binding of the same field.
5. *The enum-ref operand is kind-checked like any other.* ``edge-between``'s
   operand is an ``EdgeType`` member and ``the``'s is a ``NodeType`` member;
   either naming a member of another enum kind is ``E-TYPE-011`` under §2.6's
   class rule, statically and at load.

**Worked shape.** The §2.4 coverage row, written out:

.. code-block:: scheme

   (fold mean (edges EdgeType/EXPLOITATION)
         (field-of it exploitation/tension)
         :weight (field-of it exploitation/value-flow))

``it`` is an ``EdgeRef`` inside a fold over ``edges`` (§2.6's result table), so
both accessors read the edge under the fold. The ``:weight`` is mandatory here
because ``exploitation/tension`` would be declared ``:kind intensive`` — §3.4's
rule is untouched by this chapter and applies to edge fields exactly as it
applies to node fields.

**[draft ruling — Phase 1 review, R9 chapter C2]** ``edge-between`` *is
well-defined because the triple is a key.* §2.6 fixes the edge iteration order
at ascending ``(source-id, target-id, edge-type)`` lexicographic byte order —
which is a *total* order only if no two edges share that triple, and the two
points at which an edge enters the graph both refuse a second one: §2.8 makes
"adding an edge that already exists" ``E-EVAL-031``, and §3.9's hydration
contract makes a scenario seeding one triple twice ``E-LOAD-044``. Parallel
edges of one type between one ordered pair are therefore not representable
(a ceiling-violating hydration is separately ``E-LOAD-041``), and "the edge
between a and b of type T" denotes at most one element. When it denotes none,
that is ``E-EVAL-034`` — the accessor never yields an absent reference and never
degrades to a no-op write, which is what would happen if ``update-edge`` had
been given endpoint operands and left to skip quietly.

.. code-block:: scheme

   (update-edge (edge-between EdgeType/SOLIDARITY self other)
                solidarity/strength (scale 0.95c))

**[draft ruling — Phase 1 review, R9 chapter C3]** ``the`` *reaches a singleton
carrier without a degenerate fold.* Graph-scope state lives on carrier nodes
(§3.6), and a rule whose domain is some other type has to name one. The
alternative the language already had — ``(fold sum (nodes NodeType/POLITY)
(field-of it polity/imperial-rent-pool))`` — reads as an aggregation, costs a
ceiling factor it does not need, and is a fold whose result happens to be a
single element only because the ceiling is 1. ``the`` says that directly and
proves it statically: legality is conditioned on the manifest's ``:ceiling``
being exactly 1 (``E-LOAD-043``), which is the same declared number §3.7
already uses for the fuel bound, so the ruling adds no second registry. A
graph that holds no such node at evaluation is ``E-EVAL-035`` — a carrier the
scenario forgot to hydrate fails loudly rather than reading as zero.

.. code-block:: scheme

   (update-node (the NodeType/POLITY)
                polity/imperial-rent-pool (sub drawn))

**[draft ruling — Phase 1 review, Amendment AG (i)]** ``membership-field-of``
*keys the pair with two operands and annotates with the* ``<qname>`` — D24's
pattern for the third time, and an accessor rather than a binding source.
A ``:membership`` ``<bind-src>`` was the obvious alternative and is
**rejected** on D56's reasoning verbatim: a bind-src encodes as a two-child
``opt`` under D20 and this one needs two element operands, so it would have
been the only bind-src of its shape; and a binding resolves *implicitly*
against an enclosing body, while a rule that scores memberships holds the
hyperedge and the member explicitly (§2.12's example holds both at once
through ``:as``). The accessor names its element at the point of use, which is
the property §2.10 was written around.

.. code-block:: scheme

   (fold mean (members-of c HyperedgeType/COMMUNITY)
         (membership-field-of c it community/visibility)
         :weight (membership-field-of c it community/strength))

- *Operand order is hyperedge-then-member.* Amendment AG names the object as
  the *(member, hyperedge)* pair, and that spelling is the model's naming, not
  an operand order: here the order runs from the half the ``<qname>``
  annotates — the owning ``HyperedgeType`` — outward to the member, which is
  also ``members-of``'s and ``update-membership``'s order. One order, three
  forms.
- *Both operands are subject to discipline 1.* A hyperedge operand not of the
  qname's owning type and a member operand not of the declaration's
  ``:member`` type are each ``E-EVAL-033``; a pair that is a well-typed
  non-membership — both elements exist, the member is simply not in that
  hyperedge's list — is ``E-EVAL-038``, its own code because it is a different
  fact about the graph and a reader should not have to guess which one a code
  meant.
- *Absence past that is unreachable*, not silent: §2.8 makes payload
  initialisation total at mint and §3.9 clause 6 makes it total at hydration,
  so a membership that exists carries every declared payload field of its
  pair. Discipline 2's "a field the element carries no value for" therefore has
  no membership case to cover, which is the point of paying for the completeness
  check at load.
- *It is a keyed lookup* (D38): charged at 1 + its two element operands, never
  multiplied by a ceiling (§3.7). Type and kind propagate from the declaration
  under discipline 4, so the payload's ``:kind`` reaches §3.4 exactly as a
  ``field-of``'s does — the ``:weight`` above is mandatory because
  ``community/visibility`` is declared intensive.

2.11 Metric registration
~~~~~~~~~~~~~~~~~~~~~~~~~~

§2.5 said ``:metric`` "reads a registered graph-level metric" and stopped
there. It never said who may register one, what determinism obligations a
registration carries, whether a Rust domain crate's per-tick output qualifies,
or whether a metric may be **indexed by element**. The last question is the one
that blocks work: every topological score the OODA seam needs — degree and
betweenness centrality, articulation-point cutsets, isolation — is per-node,
and a graph-scope scalar cannot carry any of them to content.

.. code-block:: text

   <metric-decl> ::= "(" "metric" <symbol>
                         ":type" <type-name>
                         ":kind" ( "intensive" | "extensive" )
                         <domain>
                         ":provider" <symbol>
                     ")"

``<domain>`` is §2.3's production, reused unchanged: ``(domain :graph)``
declares a graph-scope metric read by a ``:metric`` binding, and ``(domain
NodeType/ORGANIZATION)`` declares an element-indexed metric read by
``metric-of``.

.. code-block:: scheme

   (metric betweenness-centrality
     :type Coefficient :kind intensive
     (domain NodeType/ORGANIZATION)
     :provider topology-scores)

   (binding centrality :expr (metric-of self betweenness-centrality))

**[draft ruling — Phase 1 review, R9 chapter C9]** *A* ``metric`` *form
declares, it does not define* — exactly as ``intrinsic`` does, and for exactly
the reason D9 gives for ``deffield``: the typechecker and the fuel-bound
checker must be computable from **content alone** for this document to satisfy
III.12(a), and a metric whose type, kind and domain lived only in a Rust
registration would make a second implementation underivable from the spec. The
kernel provides the value; the declaration is checked against the kernel's
registration and a disagreement is ``E-LOAD-025``. An unregistered metric name
remains ``E-LOAD-011`` — never ``0.0``, which is one of §6.3's four corrected
silent degradations.

**Reading a metric through the wrong form for its declared domain is
``E-LOAD-012``** — a graph metric via ``metric-of``, or an element-indexed
metric via a ``:metric`` binding. Both are static: the declaration and the
reading form are both content. At evaluation, a ``metric-of`` whose referent is
not of the declared domain type is ``E-EVAL-036``, and a metric the provider
produced no value for is ``E-EVAL-037`` — the same discipline as §2.10's
accessors, and for the same reason: absence is never a zero.

**Determinism obligations a registration carries.** These are the substance of
the contract, and they are obligations on the *provider*, enforced by review
and by the determinism contract's golden vectors rather than by the
typechecker:

1. A metric is a **pure function of the graph pre-state at the anchor position
   at which it is read**. Not of wall clock, not of RNG, not of I/O, and not of
   any rule's effects within the position.
2. Its value is **stable across every read at one position**. Whether a
   provider recomputes between positions is its own business; what it may not
   do is return two values to two rules at one position.
3. Its arithmetic obeys §4.3 — IEEE-754 basic operations, correctly rounded,
   no FMA contraction, no transcendental that is not a pinned intrinsic. A
   provider that cannot meet that bit-exactly must either declare an ``Int``
   ordinal (which is exact) or carry golden vectors with a **written tolerance
   derivation** in :doc:`/reference/determinism-contract`.
4. **A Rust domain crate's per-tick output qualifies as a provider** only if
   the crate is inside that document's pinned-toolchain set and carries those
   vectors. This is the answer to the question three surveys asked
   independently: the seam is legitimate, and it is not free.

**What enters which hash.** A metric's *name, type, kind and domain* are
content: they are ``metric`` forms, hashed into their own digest exactly as
``deffield``/``intrinsic``/``manifest`` are (§5.5). A metric's *value* is
runtime and appears in **no** content hash — it enters the tick hash only
through the fields rules write from it. An implementation that hashed metric
values directly would be hashing the provider's schedule rather than the
game's state.

**Fuel.** The provider's computation is **not** metered against the reading
rule: a rule cannot bound a betweenness computation, and pretending otherwise
would put a number in ``:fuel`` that means nothing. The *read* costs
``1 + cost(operand)`` (§3.7), the same as any other accessor. The kernel's own
budget for provider work lives in the determinism contract, which is where the
cost honestly went — this document declines to hide it in a rule's meter.

2.12 Attributed membership
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Amendment AG clause (i) (``CONSTITUTION.md`` v3.2.0, ADR189, ratified
2026-08-10) adds a **third element kind** to the exposed hypergraph model of
Amendment D: the *(member, hyperedge)* incidence pair is a first-class
**attributed membership** carrying declared, typed payload fields — the
role/strength/visibility family the frozen ``CommunityMembership`` carries
(``src/babylon/models/entities/community.py``), and the reason a system whose
scoring depends entirely on per-membership payload was unauthorable in the
revision that recorded D66. The amendment rejects the other candidate landing
in its own words: a per-*(member, hyperedge)* dyadic edge would re-expose
precisely the incidence encoding sub-ruling D-1 confines to internal storage.

This section states what the kind **is**. Its three language surfaces live in
the sections that own them: the declaration in §2.9, the read in §2.10, the
write in §2.8.

**[draft ruling — Phase 1 review, Amendment AG (i)]** *A membership is denoted
by its key, and the language mints no fourth reference kind.* A membership is
identified by the pair *(hyperedge, member)* exactly as a dyadic edge is
identified by ``(source-id, target-id, edge-type)``, and every form that
reaches one takes both halves as operands. §3.1 gains no ``MembershipRef``,
§2.6 gains no ``memberships-of`` query head, and §3.1 gains no fourth set
type.

*The rejected alternative, recorded so it is not re-proposed.* A reference
kind would have dragged in a set type, a query head, a ceiling row for a
cardinality ``:max-members`` already declares, and an **ordering key for an
object that has no id** — and the only honest order available is the member
list's, which the keyed forms already give. It would have bought no
expressiveness the pair-keyed forms lack, at the price of four new obligations
in a chapter whose amendment re-seals the closure (AG (iii)). The element kind
is first-class in the *model*, where the amendment puts it; in the *language*
it is named by its key, which is how the language already treats the only
other keyed element it has.

**What the kind carries, stated against the amendment's obligations:**

- **Typing.** Payload fields are typed exactly like node, edge and hyperedge
  fields: one ``deffield``, one ``:type`` from §3.1's table, one ``:kind``
  under §3.4. Nothing about §3.2's currency lane, §3.3's promotion rule or
  §3.4's aggregation law is special-cased for them.
- **Iteration order.** The memberships of one hyperedge iterate in the member
  list's ruled order — **ascending member node-id byte order** (D25) — so a
  fold over ``members-of`` reading payload is ordered, and it is ordered by
  the key §2.6 fixed in this document's first revision. The kind introduces no
  new order and no new tiebreak.
- **Ceiling.** ``:max-members`` remains the *only* membership cardinality axis
  (AG (i)). A payload field adds no axis, ``ceiling(members-of)`` is unchanged
  (§3.7), and a fold over members reading payload is bounded by the same
  declared number as a fold over members reading nothing.
- **Hashing.** Payload is element **state**, hashed exactly as a node's, an
  edge's or a hyperedge's declared field is. This document does not restate
  the tick-hash field set — that is
  :doc:`/reference/determinism-contract`'s — it fixes only that membership
  payload is state of the same standing as the other three kinds' fields and
  is not exempt from it. The *declaration* is content and hashes into the
  ``deffield`` digest (§5.5), whose shape is unchanged because ``:member``
  encodes as an ordinary ``opt`` (D20).
- **Mutation.** Effects only: ``update-membership`` (§2.8) is the sole writer
  after mint, and no accessor mutates (§2.10 discipline 3).
- **Anti-Pattern VIII.9 survives verbatim.** A member list crosses **whole**,
  never ``C(n,2)``. No verb converts a member list into pairwise anything,
  attributed membership changes what a membership carries rather than how many
  objects cross, and the fuel bound over an attributed member list is still
  ``Σ|members|`` at the declared ceilings (§3.7) — linear in the incidence
  count, as it was before the payload existed.

**Worked shape — the read this kind exists for.** A two-hop fold naming the
outer element with ``:as`` (D54), reading payload off the inner one:

.. code-block:: scheme

   (binding peak-exposure :expr
     (fold max (hyperedges-of self HyperedgeType/COMMUNITY) :as c
           (fold mean (members-of c HyperedgeType/COMMUNITY)
                 (membership-field-of c it community/visibility)
                 :weight (membership-field-of c it community/strength))))

Neither operator is decoration. The inner ``:weight`` is mandatory because
``community/visibility`` is declared ``:kind intensive``, so §3.4 makes the
unweighted mean ``E-TYPE-042``. The outer operator is ``max`` — kind-neutral,
legal over a body of any kind — and it is deliberately **not** ``sum``: the
inner weighted mean is itself intensive (D90), and summing per-community
visibilities across the communities one class belongs to is ``E-TYPE-041``,
which is the recorded variance error in the very shape this section exists to
enable. What the binding names is therefore the class's *peak* community
exposure, a measure; a total would have to be built from an extensive payload,
and ``community/strength`` is the extensive one.

The kind law bites on membership payload exactly as it bites on node and edge
fields — which is what "typed exactly like node/edge fields" costs, and the
reason the amendment wrote it that way.

3. Static semantics
---------------------

Every check in this chapter runs at **content load**, before any tick executes.
All of them are loud (Constitution III.11): there is no warning level, no
degraded mode, and no rule that loads "partially".

3.1 Types
~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Type name
     - Domain
     - Notes
   * - ``Int``
     - ``i64``
     - Counts, ticks, thresholds. Overflow is loud (§4.3).
   * - ``Bool``
     - ``{#t, #f}``
     - The result type of every ``<cond>``.
   * - ``Currency``
     - ``i128`` micro-units, ``[0, ∞)``
     - Fixed point. See §3.2.
   * - ``Probability``
     - ``binary64``, ``[0.0, 1.0]``
     - Kernel scalar.
   * - ``Intensity``
     - ``binary64``, ``[0.0, 1.0]``
     - Kernel scalar.
   * - ``Coefficient``
     - ``binary64``, ``[0.0, 1.0]``
     - Kernel scalar.
   * - ``Real``
     - ``binary64``, finite
     - The **unbounded intermediate** type (§3.3). Not storable.
   * - ``Enum<T>``
     - members of closed enum ``T``
     - Comparable with ``=``/``!=`` only, and only to the same ``T``.
   * - ``NodeRef`` / ``EdgeRef`` / ``HyperedgeRef``
     - one graph element
     - Produced by ``self``, ``add-node``, ``add-hyperedge``, and query
       elements (``it``, and the ``:as`` names of §2.6). **No** reference
       carries its ``NodeType``/``EdgeType``/``HyperedgeType`` statically —
       there are no type variables — which is why §2.6's hyperedge queries
       take the type as an operand and why §2.10's accessors take the owning
       type in their ``<qname>``. Consumable by §2.10's accessors and by the
       element-position operands of §2.8's verbs, and comparable for
       **identity** with ``=``/``!=`` against a reference of the same kind
       (``E-TYPE-017`` otherwise, §2.4). There is no ordering on references.
   * - ``NodeSet`` / ``EdgeSet`` / ``HyperedgeSet``
     - the result of a ``<query>``
     - Only consumable by ``fold``, ``exists``, ``forall`` (and §2.7's
       selections, which take a ``<query>`` in the same position). A set holds
       each element **once**: a query result is duplicate-free whatever
       multiplicity of edges or memberships produced it, so a ``count`` over
       ``neighbors`` counts nodes and not traversals (§2.6).
   * - ``Str``
     - UTF-8, NFC
     - Only ``:material-basis`` and vector ids. No operations.

There are no type variables, no subtyping, no coercions, and no user-defined
types. Every expression has exactly one static type, computed bottom-up.

3.2 Currency operator and rounding table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Copied **verbatim** from the design document §6.1, which is the authority:

    Currency is **i128 micro-units** with ``checked_*`` arithmetic everywhere;
    overflow is a loud III.11 failure — never wrapping, never saturating.
    […] Operator semantics are pinned, never implicit:
    ``Currency ± Currency → Currency`` (checked);
    ``Currency × Coefficient → Currency``, rounded half-even to micro-units;
    ``Currency ÷ Currency → Coefficient``, computed at i256 intermediate width
    then rounded half-even; ``Currency ÷ integer → Currency``, half-even.
    Truncation is never implicit; intermediate widths and rounding points live
    in the III.12(a) reference with conformance vectors.

Those are the **only** legal operations mixing ``Currency`` with anything else.
Every other mixed-lane expression is ``E-TYPE-030``. In particular
``Currency + Real``, ``Currency × Currency``, and ``Currency × Int`` are type
errors; multiply by a ``Coefficient`` or divide by an ``Int`` instead.

Filling in the three points the verbatim table leaves to this document:

- ``Currency ± Currency`` is checked on **both** ends: a result below ``0`` is
  ``E-EVAL-010`` (the domain is ``[0, ∞)``, matching the ``ge=0`` constraint
  the Python ``Currency`` type carries today), and a result exceeding ``i128``
  range is ``E-EVAL-011``.
- ``Currency ÷ Currency`` with a zero divisor is ``E-EVAL-012``; the
  ``Coefficient`` result must land in ``[0,1]`` or it is ``E-EVAL-013``.
- ``Currency ÷ integer`` with a zero or negative divisor is ``E-EVAL-012``.

*Half-even, defined.* Given an exact rational result ``r`` and a target
granularity ``g`` (``10^-6`` for micro-units), the stored value is the multiple
of ``g`` nearest ``r``; when ``r`` is exactly midway between two multiples, the
one whose micro-unit integer is **even** is chosen. Implementations must
compute this from exact integer arithmetic at the stated intermediate width
(``i256`` for ``Currency ÷ Currency``) — never by converting to ``binary64``
and rounding there. The same algorithm is what the ``round-half-even``
intrinsic exposes to rules.

3.3 The two numeric lanes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

BSL has exactly two numeric lanes and they never mix implicitly:

1. **Fixed point** — ``Currency``, ``i128`` micro-units, exact, table of §3.2.
2. **Binary64** — ``Probability``, ``Intensity``, ``Coefficient``, ``Real``,
   and ``Int`` when it appears in a binary64 expression.

**[draft ruling — Phase 1 review]** *Bounded-scalar arithmetic promotes to*
``Real``. ``(+ p q)`` where both are ``Probability`` has type ``Real``, not
``Probability``: adding two probabilities can leave ``[0,1]``, and silently
clamping is exactly the kind of quiet degradation III.11 forbids. The range
check happens once, at the **store boundary**: an ``update-node`` whose
resulting value falls outside the target field's declared range is
``E-EVAL-020`` — a loud runtime failure, never a clamp. Comparisons accept
``Real`` on either side. ``Int`` promotes to ``Real`` in a binary64 expression
but never to ``Currency``.

3.4 The intensivity kind rule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every ``deffield`` declares ``:kind intensive`` or ``:kind extensive``. Kind is
a property of the **field**, not of the scalar type: ``wealth`` (Currency) is
extensive, ``consciousness`` (Intensity) is intensive, and there is no type at
which that is decidable. Kind propagates through expressions:

- a literal is **kind-neutral**;
- a ``:field`` binding and a ``field-of`` accessor (§2.10) both carry the
  ``deffield``'s declared kind, whether the owning type is a node type, an
  ``EdgeType`` or a ``HyperedgeType`` — the kind rule does not care which, and
  the implicit ``<edge-type>/strength`` field is ``extensive`` (§2.9); a
  ``membership-field-of`` accessor carries its payload ``deffield``'s declared
  kind the same way **[draft ruling — Phase 1 review, Amendment AG (i)]**, so
  an intensive payload folded with an unweighted ``mean`` is ``E-TYPE-042``
  like any other intensive field;
  a ``:const`` binding is kind-neutral **[draft ruling — Phase 1 review]** (a
  coefficient has no extent); a ``:metric`` binding and a ``metric-of``
  accessor carry the **declared** ``:kind`` of their §2.11 registration
  **[draft ruling — Phase 1 review, R9 chapter C9]**, which supersedes the
  metric half of D12 — the earlier revision made them kind-neutral only
  because there was nowhere to declare a kind, and §2.11 is that place;
- ``+``/``-`` require both operands to have the same kind, or one to be
  kind-neutral; the result carries the non-neutral kind. Mixing intensive with
  extensive is ``E-TYPE-040``;
- ``*``/``/``: the result is extensive if exactly one operand is extensive,
  intensive if exactly one is intensive, kind-neutral if both are neutral, and
  ``E-TYPE-040`` if both are extensive (an area-of-an-area) — this is
  deliberately conservative and a Phase-1 review item;
- ``if`` requires both branches to have the same kind.

The aggregation law, per fold operator:

.. list-table::
   :header-rows: 1
   :widths: 14 30 56

   * - Fold op
     - Body kind
     - Rule
   * - ``sum``
     - extensive or neutral
     - Legal. Result extensive.
   * - ``sum``
     - intensive
     - **``E-TYPE-041``** — summing an intensive quantity is meaningless.
   * - ``mean``
     - extensive or neutral
     - Legal unweighted. Result carries the body kind.
   * - ``mean``
     - intensive
     - Legal **only** with an explicit ``:weight`` whose expression is
       extensive-kinded. Unweighted is ``E-TYPE-042``; a weight that is not
       extensive is ``E-TYPE-043``. **Result intensive** (D90).
   * - ``min`` / ``max``
     - any
     - Kind-neutral operation. Result carries the body kind.
   * - ``count``
     - any
     - Result ``Int``, extensive.

This is the narrow, true form of the law: it rejects the unweighted mean of an
intensive field across classes or space (the recorded variance error), and it
does **not** reject correct weighted code.

**[draft ruling — Phase 1 review, AG verification repair]** *The weighted
intensive* ``mean`` *has a result kind, and it is intensive.* The row above
stated legality and stopped, while the other four rows all state a result —
which left the kind of ``(fold mean … :weight …)`` over an intensive body
undetermined, and undetermined only until such a fold appears in a
kind-checked position, as §2.12's two-hop shape does. Two implementations
free to read the blank differently would disagree on whether that program
loads, which is a III.12(a) failure rather than a style question. The value is
``Σ(w × x) / Σ(w)``, which is in the units of ``x``: a weight-normalised mean
of an intensity is an intensity. Stating it is unit algebra, not new
mathematics, and it is stated **here** because deriving it through the
``*``/``/`` bullet is deliberately unavailable — that bullet rejects
extensive ÷ extensive as ``E-TYPE-040``, which is why the fold operators carry
their result kinds in this table instead of leaving them to decomposition.

*Exemptions.* A field may carry an exemption row in the declared
``EXTENSIVE_INTENSIVE_EXEMPTIONS`` ledger with a mandatory reason string.
Adding a row takes the same sign-off as adding a sentinel exemption. An
exemption suppresses ``E-TYPE-041``/``042``/``043`` **for the named field
only** and is itself content, inside ``rules_hash``.

3.5 Binding resolution
~~~~~~~~~~~~~~~~~~~~~~~~

At load, for every rule and every declared binding:

1. The source must resolve — the field/const/metric must exist in the closed
   vocabulary (``E-LOAD-010`` / ``E-LOAD-011`` / ``E-LOAD-030``).
2. A binding that is **not** ``:optional`` and whose source can be absent for
   any node the rule can be evaluated against is a load error (``E-LOAD-010``).
3. **[draft ruling — Phase 1 review]** ``:optional`` **requires**
   ``:default``. A bare ``:optional`` is ``E-PARSE-031``. The design document
   pairs the two in its single example; requiring the pair removes the need
   for a dominance analysis over ``bound?`` guards, keeps every expression
   total, and means no rule ever observes absence — it observes a declared
   default. There is consequently no ``bound?`` predicate in the language.
4. Every ``:default`` declaration must appear in the migration corpus's
   allowlist (the trap DSL's pinned absent-reads-as-0 sites). A ``:default``
   outside the allowlist is a lint failure requiring Director sign-off — not a
   load error, because the allowlist is program state, not language state.

3.6 Closed vocabulary
~~~~~~~~~~~~~~~~~~~~~~~

Enum types, node types, edge types, **hyperedge types**, event types, field
names, metric names and intrinsic names are all **closed**: a name that is not
in the registry is a load error, never a fallback. Adding a member is
amendment territory, not modding territory (design §5, modding boundary).
Modders author rules and coefficients
over the closed vocabulary; fuel + the closed intrinsic set + no I/O is a
sandbox with no escape to express.

**[draft ruling — Phase 1 review, R9 chapter C3]** *Graph-scope state is
ordinary node state on a declared carrier node type.* Twenty-two of the
thirty-four frozen systems read or write state that belongs to the graph rather
than to any node — the opposition registry, the market-scissors axis, the
electoral registers, the national wealth vector, the imperial-rent pool, the
phase latches — through ``graph.graph[...]``, ``set_graph_attr`` or
``context.persistent_data`` (R9 gap analysis §2, Q6: the single most pervasive
gap in the estate). None of it had a BSL home: ``<bind-src>`` closes at
``:field``/``:const``/``:metric``/``:tick``, ``:metric`` is read-only by
construction, and no §2.8 verb writes anything but a node, an edge, a hyperedge
or an event.

The ruling adds **no new grammar and no new storage class**. A value of
graph scope is declared as an ordinary ``deffield`` owned by a **carrier node
type** — a ``NodeType`` member whose manifest ``:ceiling`` is 1 — read with
``(field-of (the NodeType/…) …)`` and written with ``(update-node (the
NodeType/…) … )``. Everything the rest of this document says about node state
then applies unchanged: the value is hashed as node state, iterated in the
order of §2.6, bounded by the same ceilings, visible to the inspector and to
the write log, and subject to §3.4's kind rule. Adding a carrier ``NodeType``
member costs exactly one closed-vocabulary member and is therefore **amendment
territory** under this section — which is the right weight for a decision this
load-bearing, and is the ruling's price rather than a side effect of it.

*The rejected route, recorded so it is not re-proposed.* The alternative was a
``:global`` bind-src plus an ``update-global`` verb. It was rejected because it
invents a second storage class whose determinism, iteration, hashing, kind and
inspection obligations would every one of them have to be restated — a
document's worth of duplicated law to avoid one enum member — and because
state that is not node state is invisible to the two mechanisms the engine
already built for exactly this scrutiny (the derivation inspector's write log,
and the ceiling-bounded content hash). A closed verb set is a property worth
more than the convenience of writing ``update-global``.

*What the ruling does not do.* It does not make every register a singleton:
per-sovereign and per-county registers are ordinary nodes of ordinary types,
reached by ordinary queries. ``the`` and the carrier discipline are for the
values that are genuinely one-per-graph. And it does not introduce a staging
or double-buffering construct — see §4.7.

3.7 The load-time fuel bound check
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The bound is computed against **declared cardinality ceilings, not the runtime
graph**. Each scenario manifest declares per-``NodeType``, per-``EdgeType`` and
per-``HyperedgeType`` ``:ceiling`` values, themselves inside the content hash.

**[draft ruling — Phase 1 review]** *The member-count axis* (Amendment D). A
hyperedge type has **two** independent cardinalities, so its manifest row
declares two numbers: how many hyperedges of that type may exist
(``:ceiling``) and how many members any one of them may carry
(``:max-members``, §2.9). Without the second number a fold over ``members-of``
would have no static bound at all. This is the ceiling revision the ruling
forces: under the dyadic working assumption an n-member formation was going to
be *some number of edges*, and one edge-type ceiling covered it; under a native
hyperedge the honest cost is ``Σ|members|``, and ``:max-members`` is what makes
that quantity **declarable** at load rather than discovered at hydration.

Define ``cost(n)`` over the AST:

.. code-block:: text

   cost(literal)                = 0
   cost(variable-ref)           = 1
   cost(arith | cmp | bool)     = 1 + Σ cost(children)
   cost(intrinsic call)         = 5 + declared_cost(callee) + Σ cost(args)
   cost(fold)                   = 2 + cost(query)
                                    + ceiling(query) × (cost(body) + cost(weight))

The first five base numbers — literal 0, variable-ref 1,
arithmetic/comparison/boolean 1, intrinsic call 5 + callee, fold
2 + ceiling × body — are copied from the design document's Phase-0 cost model
and are **pinned by conformance vector; revising them is a vector re-bless**
(§6). The remaining rows are this document's completion of that model and are
**[draft ruling — Phase 1 review]**:

.. code-block:: text

   cost(if)                     = 1 + cost(cond) + max(cost(then), cost(else))
   cost(exists | forall)        = 2 + cost(query) + ceiling(query) × cost(body)
   cost(query)                  = 1 + cost(element predicate, if any)
   cost(update-op)              = 1 + cost(operand)      ; add|sub|set|scale
   cost(structural verb)        = 3 + Σ cost(operands)
   cost(members list)           = Σ cost(members)        ; grouping, no base cost
   cost(guard)                  = 1 + cost(cond) + Σ cost(effect-items)
   cost(field path | enum-ref)  = 0                      ; static, like a literal
   cost(field-of)               = 1 + cost(element expr) ; §2.10, R9 C1
   cost(edge-between)           = 1 + Σ cost(operands)   ; §2.10, R9 C2
   cost(the)                    = 1                      ; §2.10, R9 C3
   cost(metric-of)              = 1 + cost(element expr) ; §2.10, R9 C9
                                                         ; provider work is
                                                         ; not rule-metered
   cost(membership-field-of)                             ; §2.10, AG (i)
                                = 1 + Σ cost(element exprs)
   cost(member item)            = Σ cost(children)       ; §2.8, AG (i)
                                                         ; grouping, no base cost
   cost(domain)                 = 0                      ; §2.3, R9 C4
   cost(select-max | select-min)                         ; §2.7, R9 C5
                                = 2 + cost(query)
                                    + ceiling(query) × cost(score)
   cost(for-each)                                        ; §2.8, R9 C6
                                = 2 + cost(query)
                                    + ceiling(query) × Σ cost(effect-items)
   cost(:expr binding)          = cost(expr)             ; §2.5, R9 C7
   cost(:as name)               = 0                      ; §2.6, R9 C8
                                                         ; a reference costs 1
   bound(rule)                  = Σ cost(:expr bindings)
                                    + cost(cond of <when>)
                                    + Σ cost(effect-items)

**[draft ruling — Phase 1 review, R9 chapters C1–C2]** *Accessors are keyed
lookups, not iterations.* Every §2.10 accessor charges a variable-reference
base of 1 plus its operands and is **never multiplied by a ceiling**, because
none of them ranges over a set: ``field-of`` reads one element's one field, and
``edge-between`` resolves one ``(source, target, type)`` key. The static bound
of a rule using them is therefore the same shape as before — the accessors add
constants, and only the iteration constructs (``fold``, ``exists``/``forall``,
and the chapter-C5/C6 forms) carry ceiling factors. That is what keeps the
Power-of-10 Rule 2 claim static as the accessor set grows.

**[draft ruling — Phase 1 review, Amendment AG (i)]** *Attributed membership
adds a lookup, not an axis.* ``membership-field-of`` is a keyed lookup like
the rest and is charged as one; ``update-membership`` charges under the
``cost(structural verb)`` row above, ``3 + Σ cost(operands)``, exactly as the
other three update verbs do, and is given no row of its own because a second
normative statement of one cost is one too many. The **ceiling side is
unchanged**: ``:max-members`` remains the only membership cardinality axis, so
a fold over ``members-of`` whose body reads payload is bounded by the same
declared number as one whose body reads nothing, and the three ceiling axes
below stay three.

**[draft ruling — Phase 1 review, Amendment AG (ii)]** *Lattice declarations
are unmetered.* A ``rung`` or an ``adjunction`` (§2.9, §3.9) is manifest-class
content: no rule AST contains one, so ``bound(rule)`` never sees one and
neither is charged or given a cost row. The folds and ``for-each``\ s that
realise a rung are priced exactly where they already were —
``ceiling(neighbors)``, D52's lesser of the ``:via`` edge type's and the
result node type's ceilings — so declaring a lattice adds no ceiling axis, no
cost row and no term to any bound.

**[draft ruling — Phase 1 review]** *Query operand charging* (implementation-
discovered, 2026-07-30, Phase 1 Task 13). The ``cost(query)`` row names only
the element predicate, but three query heads (``neighbors``, ``members-of``,
``hyperedges-of``) also carry an *operand expression* that §4.5 charges when
it is evaluated; omitting it would make the static bound under-count the
runtime meter — the loud-failure inversion. The bound checker therefore reads
the row as ``1 + Σ cost(children)``: identical for the predicate queries
(enum-refs and direction keywords cost 0), and additionally charging the
operand where one exists.

``ceiling(query)`` is the manifest ceiling of the queried type — which is why
§2.9 makes a queried type carrying no manifest row ``E-LOAD-045`` rather than a
defaulted or skipped bound; for ``neighbors`` it is **[draft ruling — Phase 1
review, revised by R9 chapter C8]** the *lesser* of the queried edge type's
ceiling and the annotated result node type's ceiling — neither bound can be
exceeded, so the smaller is the
honest one, and the annotation C8 makes mandatory is what makes the second
number available. (A per-node degree ceiling would be tighter still and remains
the Phase-1 review item D15 recorded.) For the three hyperedge queries
**[draft ruling — Phase 1 review]**: ``hyperedges`` uses the hyperedge type's
``:ceiling``; ``members-of`` uses that type's ``:max-members``; and
``hyperedges-of`` uses the type's ``:ceiling`` — a per-node *incidence-degree*
ceiling would be tighter there, the exact dual of the ``neighbors`` review item
above, and is deferred with it.

The bound therefore composes over **three** ceiling axes rather than two:
node-type and edge-type cardinality as before, plus per-hyperedge member count
wherever a rule folds over ``members-of``. A fold over members nested inside a
fold over ``hyperedges`` costs ``ceiling(T) × max-members(T) × cost(body)``,
which is exactly ``Σ|members|`` at the declared ceilings — **linear in the
incidence count**, and never the ``C(n,2)`` a clique expansion would have cost.
That is the fuel-side consequence of the ruling: the representation that VIII.9
mandates is also the one whose static bound stays computable at national scale.

``bound(rule) > :fuel`` is ``E-LOAD-040`` — rejected **at content load**, so
the Power-of-10 Rule 2 claim is a static property rather than a dynamic trap.
An ``add-hyperedge`` whose ``<members>`` list is longer than the declared
``:max-members`` is ``E-LOAD-042`` — the list's length is fixed in the source
text, so that check is **static**, not a runtime one. A hydration that
exceeds a declared ceiling — including a hydrated hyperedge carrying more
members than ``:max-members`` — is itself a III.11 load failure
(``E-LOAD-041``). The runtime meter of §4.5 remains as the backstop.

3.8 Deliberate absences and their re-modellings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Seven things the frozen estate reaches for do not exist in BSL and are not
going to. Each is recorded here **with the re-modelling that replaces it**, so
that a future port reads the absence as a decision rather than an oversight and
does not re-propose the construct. None of these adds grammar; several delete a
question. An eighth item follows them under its own heading: it is *not* a
settled absence, and saying so is the point of recording it here.

**1. Absence, and writing it back** (R9 gap analysis §2, Q17). There is no null
literal, no ``unset`` update-op, and no ``bound?`` predicate — D13 removed the
last of those on purpose. But two systems genuinely need to say "this node has
no value on this axis": one writes ``None`` when a node loses an axis, and one
skips permanently when a stock was never seeded.

``:optional``/``:default`` is **not** the answer, and reading it as the answer
changes behaviour silently: ``:default 0.0`` converts *never seeded* into
*seeded with zero stock*, which is a different eligibility population and a
different game. The landing is a **companion presence field**: a
``deffield``-declared ``Bool`` alongside each genuinely optional axis, written
by the same effects list that writes the value, under one ``guard`` so the pair
moves together or not at all. Absence is then representable, hashable and
inspectable — and "unset the axis" is an ordinary ``(set #f)`` on the presence
field rather than a verb the language does not have. The EpistemicHorizon
discipline (all three attributes or none) is already exactly this shape.

**2. No sequence or map type** (Q13). Three systems keep ordered or list-valued
state: a FIFO agenda, an order-significant acquisition list, a set of
suppressed field names. A sequence type would drag ordering into CAS, into the
kind rule and into the fuel model, and a map type would need a key ordering
this document has deliberately confined to graph-element ids. Each case
re-models with what §2 already has:

- a FIFO agenda becomes its own bounded ``NodeType`` carrying a
  ``queued-at-tick`` field, and "the next item" becomes ``select-min`` on that
  field (§2.7);
- an order-significant acquisition list becomes an edge type carrying
  ``acquired-at-tick``, and "the most recent" becomes ``select-max``;
- a set of suppressed field names becomes one ``Bool`` field per suppressible
  field.

All three land inside the closed vocabulary, inside the content hash, and
inside the ceiling-bounded fuel model, which a list type would have left.

**3. No same-tick event-history query** (Q16). ``emit`` is write-only and
§2.6's query heads do not include an emission log; two systems ask "was a
crisis emitted this tick?". The re-modelling is better than the feature: the
**emitting** rule also stamps a field (a ``…-crisis-tick`` on a carrier or
subject node), and the consuming rule reads it as an ordinary ``:field``. That
makes the cross-system dependency visible in content, hashable, and
inspectable — three properties an event-log query would not have, since a query
over emissions would make the dependency invisible in every artifact except a
runtime trace. It also means a crisis-gated system must be ported **together
with its producer**, or the consuming rule reads a field nothing writes.

**4. No string payloads on** ``emit`` (R9 gap analysis §3, B3). ``Str`` has no
operations (§3.1) and ``<expr>`` has no string literal — one in a payload is
``E-PARSE-010``, an atom rejected by position (§1.6) — so every
``<payload-item>`` expression is a number, a bool or an enum-ref. Transcribed
systems carrying ``predicate`` or ``description`` strings, or a field name as a
string, convert them to enum-refs or drop them — the **rule id already
identifies the rule**, and an event whose payload restates its own provenance
in prose is carrying a log line, not state.

**5. No ledger or receipt binding** (B6). §2.8 prohibits I/O outright, and
three surveys independently reached for a "ledger-write binding" anyway. There
is nothing to add: a receipt is a **kernel observation of an effect that
already happened**. The rule emits; the kernel records. Making the rule write
the receipt would put the same fact in the content hash twice and give a
content author a way to record an effect that did not occur.

**6. No cascade semantics in the verb table** (B7). What ``remove-node`` does
to incident edges and memberships is an **engine-level observable**, specified
outside this document (ADR185 R2: incident edges removed, memberships dropped,
one write-log record per cascaded item). §2.8's verb table deliberately does
not restate it, because two normative statements of one behaviour is one too
many.

**7. No bounded numeric iteration** (Q15). One system runs a five-iteration
clamp-then-renormalise with an early-exit convergence check. A loop construct —
even a bounded one — would break the *syntactic* totality argument §2.7 rests
on, which is the property that makes the Power-of-10 Rule 2 claim static rather
than analysed. With ``:expr`` (§2.5) the five iterations unroll into five named
bindings, which is verbose and honest; failing that it is a legitimate Rust
domain-crate binding. Declaring a bespoke ``renormalize`` intrinsic would be
the worst of the three: it hides a mechanism inside the kernel, where neither
the content diff nor the inspector can see it, for a single call site.

**8. No edge-endpoint accessors — an open item, not a settled absence**
(R9 gap analysis §2, Q2; recorded on verification, 2026-08-10). No form yields
an ``EdgeRef``'s source or target node. Twelve systems reach for one, the R9
chapter plan (report §7) assigned Q2 to no chapter, and it is written down here
because the alternative is that it reads as an oversight — which, unlike the
seven above, is closer to the truth: this is the one item of the gap analysis
this revision neither closes nor deliberately refuses.

What is expressible today reaches only the case where one endpoint is already
in hand. A rule holding ``self`` walks to its counterparties and resolves each
edge by key:

.. code-block:: scheme

   (fold sum (neighbors self EdgeType/SOLIDARITY :in NodeType/SOCIAL_CLASS)
         (field-of (edge-between EdgeType/SOLIDARITY it self)
                   solidarity/strength))

That is correct and priced — §3.7 charges the extra keyed lookup per
neighbour — and it does **not** reach the general case: an ``EdgeRef`` taken
from a fold or a ``for-each`` over ``edges`` has *both* endpoints unknown,
which is what most of the twelve call sites need. Two landings are available,
and choosing between them is a chapter rather than a sentence: a
``source-of``/``target-of`` pair in §2.10 — reads of the triple §2.6 already
treats as the edge's key, minting no new kind of object — or leaving those
systems on the ``self``-anchored idiom and accepting that edge-iterating rules
cannot name their endpoints. Until it is chosen, a system that iterates edges
it did not start from is **not authorable in BSL**, and that is a port blocker
(D78) — the standing D66's had until Amendment AG discharged it, and now the
only one this document carries. Amendment AG does not reach this item, and
nothing in the sections it adds should be read as ruling it.

3.9 Invariant substrate, hydrated data, and the scale lattice
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Five systems aggregate up a scale lattice — county to commuting zone to state
to nation, hex link to county pair to national, per-county sums then a reverse
join — and one asks whether the language needs a grouping operator. It does
not, and this section says why, what it needs instead, and where the boundary
of this document's authority to say so lies.

**No** ``group-by``, **and no keyed collection.** A fold that grouped elements
by a runtime attribute value would have to return a *map*, which §3.1
deliberately lacks and §3.8 declines to add: a map drags a key ordering into
CAS, into the kind rule and into the fuel model. Everything the lattice needs
is instead expressible as **graph content**, because a scale level is a thing
in the world and membership in it is a relation:

.. code-block:: scheme

   (fold sum (neighbors self EdgeType/IN_SCALE :in NodeType/TERRITORY)
         (field-of it territory/wage-bill))

Aggregation up one rung is then an ordinary one-hop fold, and distribution down
one rung is an ordinary ``for-each`` over the same query. This costs
closed-vocabulary members and a hydration contract; it costs no grammar.

.. note::

   **The boundary of this section, as Amendment AG (ii) redrew it.** Declaring
   a scale-lattice **rung**, and declaring ``allocate``/``aggregate``
   **instances** of the existing adjunction schema, are content acts — the
   forms are §2.9's and their validation is below. What stays **closed** under
   Amendment AE (ii) is everything that would change the schema rather than
   instantiate it: minting a new adjunction **kind**, altering the
   **conservation obligation** between rungs, and any new level-lattice
   **algebra**. A content set reaching for one of those is proposing
   mathematics, not writing a scenario, and it costs an amendment as it always
   did.

**[draft ruling — Phase 1 review, R9 chapter C11]** *Invariant substrate is
declared, and structural verbs cannot touch it.* The spatial substrate is
immutable (Constitution: political claims are overlays), and the Director's
2026-07-30 spatial-adjacency ruling puts the invariant relations in static
lookup tables rather than per-tick state. A ``manifest`` ``ceiling`` row may
therefore carry the flag ``:invariant``:

.. code-block:: text

   <ceiling>  ::= "(" "ceiling" <enum-ref> ":ceiling" <int-lit>
                      ( ":max-members" <int-lit> )? ":invariant"? ")"

``:invariant`` is legal on a ``NodeType`` or ``EdgeType`` row and illegal on a
``HyperedgeType`` row (``E-LOAD-042``, with the ``:max-members`` mismatches it
already covers). Its meaning is narrow and static: **an** ``add-node``,
``remove-node``, ``add-edge`` **or** ``remove-edge`` **naming an invariant type
is** ``E-LOAD-013``, checked at load off the verb's ``<enum-ref>`` operand.
Field writes are unaffected — a territory's stock changes every tick while the
territory's *existence* and its rung in the lattice do not, and it is exactly
that distinction the flag encodes. The check is worth having in the language
rather than in a sentinel because it is decidable from the content set alone
and because "a rule rewired the substrate" is the failure it prevents.

**[draft ruling — Phase 1 review, R9 chapter C11]** *The hydration contract,
and why there is no* ``:reference`` *bind-src.* Five systems read external
keyed reference data — roughly fourteen ``(fips, year)``-keyed series, a
tensor registry, a county crosswalk — through host calls, and a naive port
would invent a bind-src to match. It must not. ADR174 already draws the
boundary: data sources are Python-glue concerns, and values enter as declared
BSL bindings. The consistent landing is that the **data-build pipeline
materialises keyed series as declared node fields at hydration**, so a rule
reads them with an ordinary ``:field``. That keeps §2.8's no-I/O prohibition
intact, keeps the values inside the content hash rather than beside it, and
needs no language change at all.

What hydration may do, stated once because three chapters now depend on it:

1. It creates elements of declared types and writes declared fields, and
   nothing else. An undeclared field or type at hydration is the same
   ``E-LOAD-0xx`` class as it would be in content — hydration is not a
   back door into the closed vocabulary (§3.6).
2. It is bounded by the declared ceilings, including ``:max-members``; an
   over-ceiling hydration is ``E-LOAD-041`` (§3.7), unchanged.
3. It is the **only** writer of ``:invariant`` structure, which is what makes
   the ``E-LOAD-013`` check above meaningful rather than merely restrictive.
4. A field a rule declares a plain ``:field`` binding against must be seeded by
   hydration or the rule does not load (``E-LOAD-010``, §3.5). This is the
   clause that makes "the reference-series hydration contract" a **blocking
   dependency** for the systems that read those series, rather than a source of
   zeros at tick 1.
5. **[draft ruling — Phase 1 review, R9 verification repair]** It may not seed
   two dyadic edges sharing one ``(source-id, target-id, edge-type)`` triple; a
   scenario that does is ``E-LOAD-044``. §2.8 already refuses the duplicate at
   the verb (``E-EVAL-031``), and hydration is the only other way an edge
   enters the graph, so this is the clause that makes the triple a **key**
   rather than a sort field. Without it §2.6's edge iteration order is not a
   total order — a duplicated triple has no defined position relative to its
   twin — and §2.10's ``edge-between`` has no rule for resolving *two*, having
   one only for none (``E-EVAL-034``). Node ids and hyperedge ids need no such
   clause: they are identities, and seeding one twice is not expressible.
6. **[draft ruling — Phase 1 review, Amendment AG (i)]** A hydrated membership
   carries its **complete** declared payload. A scenario seeding a hyperedge
   whose members' types declare payload fields (§2.9) writes every one of them
   for every member, and an omission is ``E-LOAD-047`` — the same code and the
   same obligation ``add-hyperedge`` carries at mint (§2.8). Hydration and the
   verb are the only two ways a membership enters the graph, so a partly
   attributed membership has to be unrepresentable from both or from neither;
   this clause is the second half of that, and it is what lets §2.10 say that
   an existing membership never reads absent.

**[draft ruling — Phase 1 review, Amendment AG (ii)]** *Rungs and adjunction
instances are* ``manifest`` *children, not a top-level form of their own.* Two
reasons, the first D79's verbatim: §5.5 hashes ``deffield``, ``intrinsic``,
``manifest`` and ``metric`` into sibling digests that ``ContentDigest``
combines, and ``ContentDigest``'s composition is
:doc:`/reference/determinism-contract`'s — a new top-form would owe a new
sibling digest and an edit to a document this one does not reach into. The
second is locality, and it is worth stating exactly because the two standing
rulings do not check against the same thing. The substrate ruling is checked
against ``:invariant`` ``ceiling`` rows — children of the very form a rung
joins — so putting the rung among them keeps that check inside one object. The
weighting ruling is checked against ``deffield`` kinds, so it spans the
manifest and field digests exactly as any content-wide check does; what the
manifest landing buys there is not one digest but **no new one**, which is
reason 1 again. Both checks read *declared content* only, which is the
property that matters for III.12(a).

.. code-block:: scheme

   ; illustrative; the delineation counts are a scenario's, not this document's
   (manifest usa-2026
     (ceiling NodeType/TERRITORY       :ceiling 3143 :invariant)
     (ceiling NodeType/COMMUTING_ZONE  :ceiling 741  :invariant)
     (ceiling EdgeType/IN_SCALE        :ceiling 3143 :invariant)
     (rung county-cz NodeType/TERRITORY NodeType/COMMUTING_ZONE
           :via EdgeType/IN_SCALE :substrate)
     (adjunction wage-bill
                 territory/wage-bill commuting-zone/wage-bill
                 :rung county-cz)
     (adjunction unemployment
                 territory/unemployment-rate commuting-zone/unemployment-rate
                 :rung county-cz :weighted-by territory/labor-force))

**What each form declares.**

- A ``rung`` names **one step** of a lattice. Its two positional
  ``<enum-ref>``\ s are ``NodeType`` members, **finer first and coarser
  second**, and ``:via`` is the ``EdgeType`` member carrying the relation,
  directed **finer → coarser** (a county's edge points at its commuting zone).
  That one convention serves both forms and both directions of travel, so the
  ``neighbors`` reads at the top of this section are unambiguous without a
  second annotation: aggregation *from* the coarser element is
  ``(neighbors self <via> :in <finer>)``, and distribution is the same query
  under ``for-each``.
- An ``adjunction`` names **one instance** of the ``allocate`` ⊣ ``aggregate``
  schema along a declared rung. Its two positional ``<qname>``\ s are the
  fields at the rung's finer and coarser ends **in the rung's own order**,
  ``:rung`` cites the rung by name, and ``:weighted-by`` names the extensive
  field the intensive case is weighted by.
- Names are content-set-unique (``E-LOAD-001``, §2.2), and every type a rung
  names owes a manifest ``ceiling`` row like any other type the content set
  uses (``E-LOAD-045``). An ``<enum-ref>`` of the wrong kind at any of the
  three positions is ``E-TYPE-011`` under §2.6's class rule.

**[draft ruling — Phase 1 review, Amendment AG (ii)]** *The first binding
ruling: a substrate rung resolves through the static lookup estate.* The
Director's 2026-07-30 spatial-adjacency ruling puts the invariant relations in
static per-resolution lookup tables and never in per-tick state, and Amendment
AG (ii) binds it to every declared rung. ``:substrate`` is how a rung says it
is one of those, and the flag obliges all three of its types — finer, coarser
and ``:via`` — to carry ``:invariant`` manifest rows. A ``:substrate`` rung any
of whose three types does not is ``E-LOAD-049``.

With the flag in place the ruling *is* the language's, by composition and not
by promise: ``:invariant`` makes ``add-node``/``remove-node``/``add-edge``/
``remove-edge`` naming those types ``E-LOAD-013`` (D63), and clause 3 of the
hydration contract above makes hydration their **only** writer. A substrate
rung is therefore built once, from the lookup estate the data-build pipeline
materialises, and no rule can rewire it mid-run. The flag is declared rather
than inferred from the three ``:invariant`` rows for the same reason
``:invariant`` is itself declared: an inferred classification would silently
reclassify a rung the day someone marked its edge type invariant for an
unrelated reason. A rung *without* the flag is perfectly legal — the social
lattice's rungs are not substrate — and carries no invariance obligation.

**[draft ruling — Phase 1 review, Amendment AG (ii)]** *The second binding
ruling: an intensive adjunction is weighted or it does not load.* An
``adjunction`` whose two fields are declared ``:kind intensive`` and which
carries no ``:weighted-by`` is ``E-LOAD-050`` — the load error the amendment
names in so many words, and the recorded variance error (an unweighted mean of
an intensive quantity across classes or space) caught one level earlier than
§3.4 catches it. The weight field must be ``:kind extensive``
(``E-TYPE-043``, the code §3.4 already uses for a non-extensive weight).

The two checks are not redundant. §3.4's ``E-TYPE-042`` catches the **fold
that implements** an aggregation; ``E-LOAD-050`` catches the **lattice that
specifies** one, which exists before any rule is written and outlives any
particular transcription of it. A scenario that declares an unweighted
intensive rung has made the error whether or not a rule pack has yet realised
it, and the amendment puts the obligation on the declaration.

**Fit to the schema, in one code.** ``E-LOAD-051`` is "this instance does not
fit the schema at its declared rung": a ``:rung`` naming no declared rung; a
positional ``<qname>`` whose owning type is not the rung's node type at that
end; the two fields disagreeing in ``:kind``; a ``:weighted-by`` on an
extensive pair (there is nothing to weight) or one whose field is not owned by
the rung's finer type. One code because they are one fact — the declaration
and the rung do not agree — and minting five synonyms is the hygiene defect
D75 ruled against.

**The conservation obligation is inherited, and there is nowhere to restate
it.** The grammar gives an ``adjunction`` no clause, no keyword and no
expression in which to state a conservation law: an instance names its rung
and its fields and stops. That is how "instances, not kinds" is enforced *by
construction* rather than by review — the only conservation obligation
available to a declared pair is the schema's, and altering it stays AE (ii)
territory exactly as the note above says.

**What a declaration does not do.** It declares; it does not execute. There is
no new verb, no evaluator behaviour and no runtime object: aggregation up a
rung is still the ordinary one-hop fold at the top of this section and
distribution down it still an ordinary ``for-each``, and this document does
not — cannot — decide which fold in a rule pack *is* a declared adjunction.
What the declarations buy is that the lattice becomes checkable at load, that
the two standing rulings become load errors instead of review notes, and that
a reviewer has a named obligation to read a rule pack against.

**Determinism.** Rungs and adjunctions are validated, and their failures
reported, in **ascending declared-name byte order** — the key §4.2 already
uses for rule ids — so two conforming implementations reject a malformed
lattice with the same first error. Nothing about them is evaluated during a
tick, so none of it reaches a tick hash; the ``manifest`` bytes that carry them
reach ``ContentDigest`` exactly as the ceiling rows do (§5.5).

3.10 The intrinsic cap, the rider slate, and RNG keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

§2.7 fixes the *calling convention* for intrinsics and says their contents are
Phase-2 work. This section fixes what that leaves dangerous: how many
intrinsics there may be, which authority says so, and why passing that test is
not the same as being allowed.

**The cap, and its authority chain, recorded exactly.** The Program 28
roadmap's R10 row holds the intrinsic set at ``{exp, log}`` **at most**, citing
ADR176 r21. r21's own text pins a *mechanism* — transcendentals cross via a
pinned soft-float libm crate with golden vectors per intrinsic — and does not
enumerate a membership; the ``{exp, log}`` enumeration is the roadmap's
rendering of it. **R10 is operative** for R9 and R10 purposes and this document
is written to it. The discrepancy is recorded rather than resolved, because
resolving it is the Director's.

Concretely, as of this revision: **``exp`` and ``log`` are the only declarable
intrinsics.** ``round-half-even`` is *obliged* by §3.2 and §2.7 and sits
outside the enumeration — see row 3 of the slate.

**Cap-legality is not doctrine-legality, and this is the load-bearing
sentence.** ``exp`` sits inside the cap. Three of the five ``exp`` call sites
in the frozen estate stipulate a logistic sigmoid that ADR173 and the standing
2026-07-29 no-imposed-functional-forms ruling retire: ``P(S|A)``, whose S-curve
must **emerge** from within-class wealth dispersion rather than be asserted; a
defection probability; a wage-pressure sigmoid. A verbatim transcription of
those formulas would pass the cap check and violate the theory line. There are
therefore **two gates**, and only one of them is mechanical:

1. *Is the intrinsic declarable?* Mechanical, checked at load against the set
   above (``E-LOAD-021`` for an undeclared call).
2. *Does this use stipulate a functional form?* Not mechanical, and not
   checkable by any typechecker. It belongs to Director review, and the
   question it asks is always the same: **can this be re-derived as a measure
   instead?**

**[draft ruling — Phase 1 review, R9 chapter C13]** ``sigmoid`` *is a reserved
prohibited intrinsic name.* Declaring an intrinsic named ``sigmoid`` is
``E-LOAD-024`` — the same code §2.7 uses for a reserved form-head collision,
and here for a stronger reason: declaring ``sigmoid`` would hand content the
exact mechanism ADR172 ruling 5 forbids, pre-packaged and named. It is the one
part of gate 2 that *can* be made mechanical, so it is.

**The rider slate.** The table below records the R9 gap analysis §4 proposals
**as proposals**. It is **not normative and declares nothing**; every row is a
question for the Director, and the "Proposal" column is the analysis's
recommendation, not this document's ruling.

.. list-table::
   :header-rows: 1
   :widths: 4 20 10 66

   * - #
     - Candidate
     - In cap?
     - Proposal (non-normative)
   * - 1
     - ``mod``, ``floor-div``
     - No
     - **No rider.** Superseded by the calendar bindings of §2.5 — a seam, not
       mathematics.
   * - 2
     - ``floor`` / ``trunc``
     - No
     - **Rider proposed.** §3.1 declares no coercions and ``Int`` promotes to
       ``Real`` one way only, so there is no demotion path at all today.
   * - 3
     - ``round-half-even``
     - No
     - **Housekeeping rider.** §3.2 and §2.7 already oblige the kernel to
       expose it to rules; the enumeration omits it. Affirming it is not a
       widening.
   * - 4
     - ``abs``
     - No
     - **No rider.** ``(if (>= a b) (- a b) (- b a))`` expresses it.
   * - 5
     - scalar ``min`` / ``max``
     - No
     - **No rider.** Nested ``if`` expresses them, and §3.3 already frames
       silent clamping as forbidden quiet degradation — an explicit ``if``
       makes the saturation legible. The ergonomic cost is real and recorded.
   * - 6
     - ``sqrt``
     - No
     - **Both presented.** Preferred: re-derive platform fit as a measure (the
       share of a class's interest dimensions a platform satisfies), which
       needs no norm. Fallback: a rider. A silent switch to squared magnitudes
       changes the metric's scale and must never happen by default.
   * - 7
     - ``exp``
     - **Yes**
     - **No rider needed; a theory ruling is.** Three of five sites are
       imposed sigmoids under ADR173. Ask the Director to dispose each:
       re-derive as a measure, or except it explicitly as a bounded auxiliary.
   * - 8
     - ``tanh``
     - No
     - **Elimination presented first.** Squashing a log-ratio into ``[-1,1]``
       is a stipulated bounded form; re-derive the scissors balance as a
       measure. Rider only if the Director keeps the squash.
   * - 9
     - ``sigmoid``
     - No
     - **Never declarable** — ruled above, ``E-LOAD-024``.
   * - 10
     - ``entropy``
     - No
     - **No proposal.** Nothing in the thirty-four systems asks for it.
   * - 11
     - RNG draw
     - n/a
     - **Not a rider.** §2.8 already sanctions it as a kernel intrinsic; the
       key convention is below.
   * - 12
     - bespoke ``renormalize``
     - No
     - **Recommend against**, per §3.8 item 7: it hides a mechanism in the
       kernel for one call site.

**[draft ruling — Phase 1 review, R9 chapter C13]** *The RNG carrier-key
convention.* §2.8 sanctions RNG as a kernel intrinsic with per-(session, tick,
salt) seeding and stops there; the rst never showed the convention, and five
systems need draws. The signature stays Phase-2 work (§2.7), but the **key**
is language-visible and is fixed here:

- The carrier key is ``(session, tick, domain, stable_key)``.
- ``session`` and ``tick`` are kernel-supplied and are **never operands** — a
  rule cannot name them and therefore cannot replay a stream.
- ``domain`` is a closed-vocabulary enum operand, so content cannot mint a new
  stream; adding one is §3.6 amendment territory like any other member.
- ``stable_key`` derives from the identities of the call's reference operands,
  in operand order, using the same id bytes §2.6 orders by. It is therefore
  stable across runs and independent of insertion history.
- **A draw is a pure function of its key, not a position in a stream.** This is
  the property that matters, and it is stronger than the obvious alternative
  ("the kernel draws only when the guard consuming it passes"): because there
  is no stream position, a guard that skips a draw cannot shift any other
  draw, and §4.1's input-dependent short-circuiting can never perturb the RNG.
  The determinism obligation holds unconditionally rather than by discipline.

4. Dynamic semantics
----------------------

4.1 Evaluation order
~~~~~~~~~~~~~~~~~~~~~~

Evaluation is **strict, call-by-value, left to right**, depth-first. For any
form, operands are evaluated in the order they appear in the *source* (which,
after §5.3's canonicalization, is the order they appear in the canonical AST).

Exceptions, all deliberate:

- ``and`` short-circuits on the first ``#f``; ``or`` on the first ``#t``.
- ``if`` and ``guard`` evaluate only the taken branch.

Short-circuiting makes *consumed* fuel input-dependent; it does not make it
non-deterministic, and the *bound* of §3.7 is a static worst case. Conformance
vectors therefore pin an exact consumed-fuel figure per (rule, environment)
pair (§6.1).

4.2 The environment
~~~~~~~~~~~~~~~~~~~~~

A rule evaluates against: the graph (read-only during condition evaluation),
the defines environment (coefficients), the current tick, the subject node, and
the fuel meter. Bindings resolve first, in declaration order — the external
sources by lookup, the ``:expr`` bindings (§2.5) by evaluation against the
bindings already resolved. Effects are applied only after the whole condition
has been evaluated. **A rule can never observe its own effects**, and rules within one
system position observe the same pre-state.

Rules at the same anchor position evaluate in **ascending rule-id byte order**
**[draft ruling — Phase 1 review]**, and their effects apply in that same
order. File order and load order are never observable.

**[draft ruling — Phase 1 review, R9 chapter C4]** *Subject enumeration order,
which this document had not specified.* A rule whose domain is a node type
(§2.3) fires once per node of that type, in **ascending node-id byte order** —
the same key §2.6 uses for queries. All firings of one rule observe the same
pre-state (the law above is unchanged), and the effects they collect are
applied in that subject order, and within one subject in source order. A
``(domain :graph)`` rule fires once and takes its place among the rules at its
anchor by rule id like any other.

The order is not a formality. Accumulation into a shared target — every class
adding its slice to a carrier node (§3.6) — reduces in exactly this order, and
the binary64 lane of §3.3 is not associative, so an unspecified subject order
would make the result implementation-dependent while every other clause of this
chapter held. Currency's exact integer lane is immune; the bounded scalars are
not, which is why the order is stated rather than left to the executor.

4.3 Arithmetic
~~~~~~~~~~~~~~~~

- Binary64 operations are the IEEE-754 **basic** operations only:
  addition, subtraction, multiplication, division, and comparison, each
  correctly rounded round-to-nearest-even. These reproduce bit-exactly across
  conforming implementations.
- Fixed-point operations are exact integer operations at the widths of §3.2.
- **No transcendental is a language operation.** Any that exists is a named
  intrinsic whose implementation is pinned by the kernel and validated by
  golden vectors with a written tolerance derivation. Which ones may exist is
  §3.10's, and it is a shorter list than the illustrative names above
  suggest. Whether those implementations are polynomial approximations or a
  pinned deterministic libm is an **open Phase-1 Director ruling** (design §13
  item 2) and is deliberately not decided here.
- No fused multiply-add. An implementation that contracts ``a*b+c`` into an FMA
  is non-conforming.
- ``Int`` overflow is ``E-EVAL-011``.
- A binary64 operation producing a non-finite result (``inf``, ``-inf``,
  ``NaN``) is ``E-EVAL-014``. Division by zero in the binary64 lane is
  ``E-EVAL-012``. Non-finite values are therefore **not representable** at any
  observable point, which is what makes the JSON/serialization inf-NaN trap
  unreachable by construction.

4.4 Query evaluation
~~~~~~~~~~~~~~~~~~~~~~

A query is materialized in the sort order of §2.6 before the fold body runs.
The graph is not mutated during condition evaluation, so the materialized set
cannot change under the fold. ``mean`` over an empty set is ``E-EVAL-021``
(never ``0``); ``sum`` over an empty set is the additive identity of the body
type; ``count`` over an empty set is ``0``; ``min``/``max`` over an empty set
are ``E-EVAL-021``. ``exists`` over an empty set is ``#f``; ``forall`` over an
empty set is ``#t``.

4.5 Fuel accounting
~~~~~~~~~~~~~~~~~~~~~

Each AST node charges its **base** cost when it is evaluated — the same base
numbers §3.7 uses to compute the static bound, without the ceiling
multiplication (the multiplication is the static worst case; at runtime each
actual iteration charges the body's cost once). The meter starts at the rule's
declared ``:fuel`` and decrements. A ``:expr`` binding charges its expression
**once**, when the binding resolves; each later *reference* to it charges a
variable-reference 1 like a reference to any other binding. That asymmetry is
the whole of the fuel win C7 buys, and it is why the same algebra written twice
inline costs strictly more than the same algebra named once.

Reaching or passing zero is ``E-EVAL-040``, which aborts the tick (§4.6) — it
never truncates a fold or returns a partial result.

**[draft ruling — Phase 1 review, R9 verification repair]** *The meter is per
firing.* A node-domain rule fires once per subject (§4.2), and **each firing
starts a fresh meter at the declared** ``:fuel``: the budget is a property of
one evaluation, never of a rule's whole pass over its subjects. That is the
only reading consistent with ``bound(rule)`` (§3.7), which carries no
subject-count factor, and the only one under which a rule's legality at load
does not depend on how many nodes the scenario it is later hydrated against
happens to hold. Chapter C4's subject enumeration made the multiplicity
explicit and therefore made this sentence necessary. It follows that a
conformance vector's ``:fuel-used`` (§6.1) is also per firing; a vector whose
rule fires over several subjects — §6.2 family 12's accumulation vector — states
the figure for the **first** subject in §4.2's order, which is well defined
because that order is.

The cost table is **pinned by conformance vector; any revision is a vector
re-bless** (design §5 Totality). This is what makes fuel a stable, hashable
property of content rather than an implementation detail.

**[draft ruling — Phase 1 review]** *The §3.7/§4.5 boundary is off by one*
(implementation-discovered, 2026-07-30, Phase 1 Task 14). §3.7 rejects only
``bound(rule) > :fuel`` at load, while this section's meter must stay
**strictly positive** — "reaching or passing zero" — so a rule whose worst
case consumes exactly its ``:fuel`` loads and then ``E-EVAL-040``\ s at
runtime. Both checks are implemented to the letter; authors should budget
``:fuel ≥ bound + 1``. The Phase-1 review may align the two by making the
load check ``bound ≥ :fuel``.

4.6 Error taxonomy
~~~~~~~~~~~~~~~~~~~~

Every error in this document is loud (Constitution III.11). There are exactly
two times at which an error can occur.

.. list-table::
   :header-rows: 1
   :widths: 18 22 60

   * - Class
     - Codes
     - When, and what happens
   * - Lexical
     - ``E-LEX-0xx``
     - Content load. The content set is rejected; no engine starts.
   * - Syntactic
     - ``E-PARSE-0xx``
     - Content load. As above.
   * - Static/type
     - ``E-TYPE-0xx``
     - Content load. As above.
   * - Load/link
     - ``E-LOAD-0xx``
     - Content load — unresolved bindings, unknown vocabulary, fuel bound
       exceeded, ceiling violated at hydration, a missing or misplaced
       ``:max-members`` or ``:invariant``, a member list over that ceiling,
       anchor interleaved into the Material Base partition, kernel/content
       disagreement; and, from the R9 chapters, an undeterminable or ambiguous
       rule domain, a field owner that names no registered type, a
       node/edge/hyperedge type-rendering collision, a metric read through the
       wrong form for its declared domain, a structural verb naming an
       ``:invariant`` type, a reserved or prohibited intrinsic name, ``the``
       against a type whose ceiling is not 1, a hydration seeding one edge key
       twice, and a manifest with no row for a type the content set uses; and,
       from the Amendment AG sections, a membership payload field read or
       written through the wrong form, a membership minted or hydrated with an
       incomplete payload, a ``:member`` declaration whose owner segment is
       not a hyperedge type, a ``:substrate`` rung over a type that is not
       ``:invariant``, an intensive adjunction with no weight, and an
       adjunction that does not fit the schema at its declared rung.
   * - Evaluation
     - ``E-EVAL-0xx``
     - During a tick — checked-arithmetic failure, range violation at a store,
       non-finite result, empty aggregate, edge-mode violation, hyperedge type
       mismatch, fuel exhaustion; and, from the R9 chapters, an accessor whose
       referent is of the wrong type or carries no value for the named field,
       an ``edge-between`` that resolves to no edge, a ``the`` against an
       unhydrated carrier, and a ``metric-of`` against the wrong element type
       or a value the provider did not produce; and, from the Amendment AG
       sections, a named *(hyperedge, member)* pair that is not a membership.

**Every code the R9 chapters add continues an existing sequence, and no code
that existed before this revision is renumbered.** The new codes are
``E-LOAD-0xx`` (eleven, because most of what those chapters add is decidable
from the content set alone), ``E-PARSE-0xx`` (six), ``E-TYPE-0xx`` (five) and
``E-EVAL-0xx`` (five, all of them the "absence is never a value" discipline of
§2.10 applied at a new referent). That the load class grew fastest is the
intended shape: a chapter that made a new failure mode *runtime*-only would
have moved the language in the wrong direction.

**The Amendment AG sections continue the same sequences.** They add six
``E-LOAD-0xx`` codes — three per construct — and one ``E-EVAL-0xx``, and
**no** ``E-LEX``,
``E-PARSE`` or ``E-TYPE`` code at all: every parse- and type-class failure
they can produce already had one — ``E-PARSE-013`` for a keyword outside its
form, ``E-PARSE-041`` for two writers of one field in one form,
``E-TYPE-011`` for an ``<enum-ref>`` of the wrong kind, ``E-TYPE-014`` for a
field-init owning off the wrong type, ``E-TYPE-041``/``042``/``043`` for the
kind law — and minting a synonym for an existing class is exactly the hygiene
defect D75 ruled against.

Sequence continuation is meant literally, and is checkable by inspection: every
decade block of every family is **contiguous**, with no reserved and no
skipped number — ``E-LOAD`` 001–004, 010–013, 020–025, 030–033, 040–051;
``E-PARSE`` 010–015, 020–022, 030–033, 040–042; ``E-TYPE`` 010–017, 020, 030,
040–043; ``E-EVAL`` 010–014, 020–021, 030–038, 040; ``E-LEX`` 001–003,
010–011, 020–026. The ``E-LOAD`` 040 block now runs past its own decade, and
deliberately: opening a fresh block at 050 for the Amendment AG codes would
have **reserved** 046–049, and a reserved number is precisely what the rule
above forbids. Contiguity outranks decade tidiness.
The R9 chapters allocated per chapter and left two holes in
the ``E-TYPE`` sequence; they were closed by renumbering the two offending
**new** codes before any implementation pinned them, which is a liberty
available exactly once and only to codes this revision minted.

**Load-time errors** report the offending file, line, column, form, and code,
and reject the whole content set — there is no partial load and no "skip the
bad rule" mode.

**Evaluation errors** abort the tick. The whole per-tick envelope transaction
rolls back; there are no partial commits (design §9). The error carries the
rule id, the AST path to the offending node, the binding environment, and the
fuel remaining. An implementation must not convert an evaluation error into a
default value, a skipped effect, or a log line.

4.7 Cross-system registers and one-tick handoffs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once graph-scope state is node state (§3.6), a whole class of construct stops
being necessary, and this section exists to say so rather than to add anything.

Several values in the frozen estate are **one-tick-lagged handoffs** between
systems at different anchor positions — Sovereignty's output read by Metabolism,
MarketScissors' correction read by WealthDistribution, Production's value read
by ImperialRent. In the Python engine those live in ``persistent_data`` and the
lag is a property of where the write and the read happen to sit.

**[draft ruling — Phase 1 review, R9 chapter C3]** *There is no staging,
double-buffering or "previous tick" construct, and none is needed.* A rule
writes a carrier field at its anchor position; a rule at a later anchor
position in the same tick reads the new value; a rule at an earlier position
reads the value the previous tick left. Tick ordering already **is** the
staging mechanism, and it is the one mechanism whose behaviour §4.2 has
specified since this document's first revision. Adding a ``previous`` accessor
or a staged-write verb would introduce a second notion of "when", and every rule
in the estate would then have to be read twice to know which one it meant.

Two obligations follow, and they are content obligations rather than language
ones:

1. **The lag is declared by the anchor, so the anchor is load-bearing.** A rule
   pack that moves a read across the writing system's position silently
   converts a one-tick lag into a same-tick read. The anchor is inside
   ``rules_hash``, so the change is visible in the diff — but it is visible as
   an anchor edit, not as a semantic one, and review should treat it as the
   latter.
2. **A carrier field read before anything has written it reads what hydration
   seeded**, which is why §3.5's plain-binding rule matters here: a carrier
   field is an ordinary declared field, so a rule reading one that the scenario
   never seeded is ``E-LOAD-010`` at load, not a zero at tick 1.

5. Canonical AST serialization
--------------------------------

``rules_hash`` is ``SHA-256`` over the canonical AST serialization (CAS) of the
content set. CAS is **whitespace-insensitive, comment-insensitive, file-layout
insensitive, and option-order insensitive**: a formatting edit produces
identical bytes, while any change to a rule's meaning — including its
``:material-basis`` string and its ``:fuel`` budget — produces different bytes.

This chapter defines the bytes. What ``rules_hash`` is *combined with*
(``ContentDigest``), and how it relates to the tick hash and ``defines_hash``,
belongs to :doc:`/reference/determinism-contract`.

5.1 Primitive encodings
~~~~~~~~~~~~~~~~~~~~~~~~~

All multi-byte integers are **big-endian**, two's complement where signed.

.. list-table::
   :header-rows: 1
   :widths: 16 14 70

   * - Name
     - Width
     - Meaning
   * - ``u8``
     - 1
     - Unsigned length or tag byte.
   * - ``u32``
     - 4
     - Unsigned length or child count.
   * - ``i64``
     - 8
     - Signed integer literal value.
   * - ``i128``
     - 16
     - Signed unscaled decimal / Currency micro-units.
   * - ASCII
     - variable
     - Names; always length-prefixed, never NUL-terminated.
   * - UTF-8
     - variable
     - String payloads; NFC; always length-prefixed.

5.2 Node encodings
~~~~~~~~~~~~~~~~~~~~

There are exactly two node shapes.

.. code-block:: text

   atom ::= 0x01  u8 len(kind)  kind_ascii  u32 len(payload)  payload
   form ::= 0x02  u8 len(tag)   tag_ascii   u32 nchildren     child*

Both are self-delimiting, so the encoding is unambiguously parseable back to the
AST — a property implementations should exercise as a round-trip property test.

**Atom kinds and payloads:**

.. list-table::
   :header-rows: 1
   :widths: 14 86

   * - ``kind``
     - payload
   * - ``int``
     - ``i64`` value
   * - ``cur``
     - ``i128`` micro-units (scale is implicit and always 6)
   * - ``prob``
     - ``i128`` unscaled ``||`` ``u8`` scale (minimal scale; zero is ``0,0``)
   * - ``intn``
     - as ``prob``
   * - ``coef``
     - as ``prob``
   * - ``bool``
     - one byte: ``0x00`` = ``#f``, ``0x01`` = ``#t``
   * - ``sym``
     - ASCII symbol, no sigil
   * - ``qname``
     - ASCII qualified name including its ``/`` separators
   * - ``kw``
     - ASCII keyword name **without** the leading ``:``
   * - ``enum``
     - ASCII ``<EnumType>/<MEMBER_IDENTIFIER>``
   * - ``str``
     - UTF-8 bytes after escape processing, NFC

**Form tags** are the form's head symbol verbatim (``rule``, ``bindings``,
``binding``, ``when``, ``effects``, ``and``, ``or``, ``not``, ``<``, ``<=``,
``>``, ``>=``, ``=``, ``!=``, ``+``, ``-``, ``*``, ``/``, ``if``, ``fold``,
``exists``, ``forall``, ``nodes``, ``edges``, ``neighbors``, ``hyperedges``,
``members-of``, ``hyperedges-of``, ``field-of``, ``edge-between``, ``the``,
``domain``, ``select-max``, ``select-min``, ``metric``, ``metric-of``,
``guard``, ``for-each``,
``update-node``, ``update-edge``,
``add-node``, ``remove-node``, ``add-edge``, ``remove-edge``,
``add-hyperedge``, ``update-hyperedge``, ``remove-hyperedge``, ``members``,
``member``, ``membership-field-of``, ``update-membership``,
``emit``, ``add``, ``sub``, ``set``, ``scale``, ``anchor``, ``deffield``,
``intrinsic``, ``manifest``, ``ceiling``, ``rung``, ``adjunction``), plus the
synthetic tag ``opt`` for a keyword option.

The six tags the Amendment D revision added — ``hyperedges``, ``members-of``,
``hyperedges-of``, ``add-hyperedge``, ``remove-hyperedge``, ``members`` — obey
that same rule (the tag *is* the head symbol), so they need no registry entry,
no numeric id, and **no new atom kind**; ``:max-members`` is an ordinary
keyword and encodes as an ``opt`` form like every other option. Nothing else in
this chapter changes. In particular the §5.6 worked example contains none of
these forms, so **its 421 canonical bytes and both of its digests are unchanged
by this revision** — a hyperedge-bearing example would need its own vector
(§6.2), not a recomputation of that one.

**The R9 tags obey the same rule, and the worked example survives them too.**
Every form tag the R9 spec chapters add — listed in the paragraph above
alongside the originals — is its own head symbol, needs no registry entry, no
numeric id and no new atom kind; every keyword they add encodes as an ``opt``
form. None of them appears in §5.6's example, and none of the R9 chapters makes
a previously-optional child of ``rule`` mandatory, so **§5.6's 421 bytes and
both digests remain correct as written**. That invariance is deliberate: it is
the cheapest available proof that the chapters are additive.

**The Amendment AG tags obey it a third time.** ``member``,
``membership-field-of`` and ``update-membership`` (§2.8, §2.10, §2.12) are
their own head symbols, needing no registry entry, no numeric id and no new
atom kind; ``:member`` encodes as an ``opt`` form under D20 like every other
keyword. ``deffield`` gains one **optional** child and ``add-hyperedge``'s
``<members>`` gains an alternative item shape that a bare member list never
uses, so no existing form's encoding moves. Clause (ii)'s ``rung`` and
``adjunction`` are the same story one level up: their tags are their head
symbols, their keywords are ``opt`` forms, and they are **optional children of
a form that already has a digest** (§5.5's ``manifest``), so a manifest that
declares no lattice encodes byte-for-byte as it did. None of these appears in
§5.6's example, and no previously-optional child of ``rule`` becomes mandatory
— **§5.6's 421 bytes and both digests remain correct as written**.

A keyword option is encoded as a two-child form:

.. code-block:: text

   opt ::= form("opt", atom("kw", <name>), <value node>)

A flag keyword (``:optional``) encodes as ``form("opt", atom("kw","optional"),
atom("bool", 0x01))`` **[draft ruling — Phase 1 review]** so that every option
has the same shape.

5.3 Canonical child order
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Within any form, children are emitted in three groups:

1. the form's **fixed positional operands**, in the order the §2 grammar
   declares them;
2. all **keyword options**, sorted by keyword name in ascending ASCII byte
   order;
3. the **variadic body**, in source order.

Group 2's sort is what makes option order a formatting concern. Group 3's
source order is load-bearing: order is structure (the effect application order
of §2.8 is exactly this order).

**[draft ruling — Phase 1 review, R9 chapter C4]** ``<domain>`` *encodes in
its grammar position.* Like ``<anchor>``, ``<bindings>``, ``<when>`` and
``<effects>``, a ``domain`` form is a child of ``rule`` emitted in the order
the §2.3 grammar declares it — immediately before ``anchor``. It is optional
and absent from §5.6's example, so that example's byte count and both its
digests are unaffected. Its own children follow the general rule: an
``<enum-ref>`` domain encodes as one ``atom enum`` child, and ``(domain
:graph)`` as one ``opt`` form carrying the ``graph`` flag under D20.

5.4 Determinism obligations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Comments and whitespace never appear in CAS.
- Decimal literals are minimal-scale (§1.5), so ``0.50c`` and ``0.5c`` produce
  identical bytes.
- Currency literals are micro-unit integers, so ``1000.5$`` and ``1000.500$``
  produce identical bytes.
- Strings are NFC by load-time check, so "the source bytes" is a canonical
  form.
- No floating-point value is ever serialized. There is no ``binary64`` in CAS
  and therefore no float-formatting ambiguity anywhere in the hash path.
- ``str()``-style fallbacks are banned outright: every node kind has an
  explicit encoding above, and an encoder that meets an unencodable value must
  fail loudly rather than stringify it.

5.5 ``rules_hash``
~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   rules_hash = SHA-256( 0x03 || u32 N || CAS(r_1) || … || CAS(r_N) )

where ``r_1 … r_N`` are all ``rule`` forms in the content set sorted by rule id
in ascending ASCII byte order, and ``N`` is their count. ``deffield``,
``intrinsic``, ``manifest`` and ``metric`` forms are hashed the same way into
their own digests, which ``ContentDigest`` combines
(:doc:`/reference/determinism-contract`). The digest is rendered as **64
lowercase hex characters** — never truncated. (Truncation to 16 hex is exactly
the defect the ``defines_hash`` triad carried; see the determinism contract's
worked-example chapter.)

5.6 Worked example
~~~~~~~~~~~~~~~~~~~~

Source form:

.. code-block:: scheme

   ; a rule is data; this comment is not part of the hash
   (rule demo/hunger
     :material-basis "subsistence deficit at the point of reproduction"
     :fuel 64
     (bindings
       (binding wealth :field social-class/wealth))
     (when (< wealth 1000.5$))
     (effects
       (update-node self social-class/agitation (add 0.05i))))

Canonical AST after §5.3 reordering (note ``:fuel`` now precedes
``:material-basis`` — ``"fuel" < "material-basis"`` in ASCII):

.. code-block:: text

   form "rule" (6 children)
     atom qname "demo/hunger"
     form "opt" : atom kw "fuel",           atom int 64
     form "opt" : atom kw "material-basis",
                  atom str "subsistence deficit at the point of reproduction"
     form "bindings" (1)
       form "binding" (2)
         atom sym "wealth"
         form "opt" : atom kw "field", atom qname "social-class/wealth"
     form "when" (1)
       form "<" (2)
         atom sym "wealth"
         atom cur 1000500000            ; 1000.5 × 10^6 micro-units
     form "effects" (1)
       form "update-node" (3)
         atom sym "self"
         atom qname "social-class/agitation"
         form "add" (1)
           atom intn (unscaled 5, scale 2)

Canonical bytes — 421 bytes, hex (wrapped at 64 characters for display only):

.. code-block:: text

   020472756c65000000060105716e616d650000000b64656d6f2f68756e676572
   02036f70740000000201026b77000000046675656c0103696e74000000080000
   00000000004002036f70740000000201026b770000000e6d6174657269616c2d
   626173697301037374720000003073756273697374656e636520646566696369
   742061742074686520706f696e74206f6620726570726f64756374696f6e0208
   62696e64696e677300000001020762696e64696e6700000002010373796d0000
   00067765616c746802036f70740000000201026b77000000056669656c640105
   716e616d6500000013736f6369616c2d636c6173732f7765616c746802047768
   656e0000000102013c00000002010373796d000000067765616c746801036375
   72000000100000000000000000000000003ba26b200207656666656374730000
   0001020b7570646174652d6e6f646500000003010373796d0000000473656c66
   0105716e616d6500000016736f6369616c2d636c6173732f616769746174696f
   6e0203616464000000010104696e746e00000011000000000000000000000000
   0000000502

Reading the first 32 bytes: ``02`` (form) ``04`` ``72756c65`` (``"rule"``)
``00000006`` (6 children) ``01`` (atom) ``05`` ``716e616d65`` (``"qname"``)
``0000000b`` (11 payload bytes) ``64656d6f2f68756e676572``
(``"demo/hunger"``).

Digest of this single rule alone:

.. code-block:: text

   SHA-256(CAS(rule)) = 8a62d0b5724de24ec36ea0dfb3f4d120a63d90a56bad2a4605e645368f304da3

``rules_hash`` for a content set consisting of exactly this one rule — that is,
``SHA-256(0x03 || 0x00000001 || CAS(rule))``, 426 bytes of input:

.. code-block:: text

   rules_hash = 4e6fbf64c771bd8e2f7874b4c906d0330458ba965911d00a9a731ea8a724238f

Static fuel bound for this rule, by §3.7:
``cost(when) = 1 + 1 + 0 = 2``;
``cost(update-node) = 3 + 1 + 0 + (1 + 0) = 5``;
``bound = 7`` ≤ the declared ``:fuel 64``. The rule loads.

Both digests above are reproducible from this document alone; the reference
encoder used to produce them is 90 lines and derives entirely from §5.1–§5.5.

6. Conformance
----------------

6.1 Vector-file format
~~~~~~~~~~~~~~~~~~~~~~~~

Conformance vectors are written in BSL's surface syntax — homoiconic,
diffable, and hashable at the file level — but they are fixtures, not
canonical content (D91 below). A vector file is a sequence of ``vector``
forms:

.. code-block:: text

   <vector>  ::= "(" "vector" <string>
                     ":rule"   <rule>
                     ":env"    "(" <env-entry>* ")"
                     ":graph"  <graph-lit>?
                     <outcome>
                     ":fuel-used" <int-lit>?
                     ":cas"    <string>?
                 ")"

   <env-entry> ::= "(" <symbol> <literal> ")"
   <outcome>   ::= ":expect" <literal> | ":expect-error" <symbol>
   <graph-lit> ::= "(" "graph" <node-lit>* <edge-lit>* ")"
   <node-lit>  ::= "(" "node" <symbol> <enum-ref> <field-init>* ")"
   <edge-lit>  ::= "(" "edge" <enum-ref> <symbol> <symbol> <expr> ")"

**[draft ruling — Phase 1 review, post-R9 audit]** *Vector files are
fixtures, not content.* A vector file is read by §1's reader, but no
``vector`` form is canonical content: §5 encodes the **content** forms of
§2, and a ``vector`` form is never encoded under §5 nor hashed into any
content digest — "hashable" above is file identity, the byte hash of the
vector file itself. The flag/valued dichotomy of §1.6 and its closed flag
table (D42) therefore govern content forms only. Within a ``vector`` form,
``:graph``, ``:fuel-used`` and ``:cas`` are vector-format keywords carrying
the *optional* values this grammar spells — a shape the content dichotomy
deliberately has no room for — and the collision with ``:graph``'s content
classification as a flag is a scope boundary, not an amendment to it. An
implementation's canonical encoder never sees a ``vector`` form; handing it
one is a caller error, not a defined encoding (D91).

Semantics of a vector: load ``:rule`` (the load must succeed unless
``:expect-error`` names a load-class code), hydrate ``:graph`` if present, bind
``:env``, evaluate, and compare.

- ``:expect`` — the rule's condition value, or for effect-bearing vectors the
  resulting field value, must equal the literal **exactly** (bit-exact for
  binary64, integer-exact for fixed point). Conformance is not
  tolerance-bounded; tolerances belong to the *cross-implementation numeric*
  layer described in :doc:`/reference/determinism-contract`, not to the
  evaluator.
- ``:expect-error`` — the named error code must be raised, at the class's
  declared time (load vs evaluation). Raising the right code at the wrong time
  is a failure.
- ``:fuel-used`` — mandatory on every non-error vector. This is the mechanism
  that pins the cost table: changing any base cost changes these numbers, and a
  cost-model revision is therefore a **vector re-bless ceremony**, visible in
  the diff.
- ``:cas`` — optional expected canonical serialization, as lowercase hex. Every
  syntactic construct in §2 must be covered by at least one ``:cas`` vector so
  the byte layout is pinned independently of the evaluator.

Vector files live under a declared conformance root, are sorted by vector id
for execution, and every implementation must run all of them. A vector that no
implementation can satisfy is a spec defect, not a vector defect.

6.2 Required vector families
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At minimum, an implementation claiming conformance passes:

1. **Lexical** — one accepting and one rejecting vector per ``E-LEX-0xx`` code.
2. **Literal canonicalization** — ``0.50c`` / ``0.5c`` byte-equality;
   ``1000.5$`` / ``1000.500$`` byte-equality; scale and range boundaries.
3. **Currency operators** — every row of §3.2, including half-even ties in both
   directions, the ``i256`` intermediate width for ``Currency ÷ Currency``, and
   both overflow ends.
4. **Kind rule** — the six rows of §3.4's table, accepting and rejecting,
   including the weighted-intensive ``mean``'s **result** kind (D90): the same
   weighted fold nested under an outer ``sum``, which must reject
   ``E-TYPE-041``, and under an outer ``max``, which must accept.
5. **Fuel** — the static bound for a fold at a declared ceiling; a rule
   rejected at load for exceeding its budget; a rule exhausting fuel at
   evaluation; a query against a type the manifest declares no row for
   (``E-LOAD-045``); a node-domain rule fired over three subjects whose
   ``:fuel-used`` is one firing's and not three (§4.5); and per-vector
   ``:fuel-used``.
6. **CAS** — one ``:cas`` vector per form tag and per atom kind, plus the §5.6
   worked example verbatim.
7. **Transcription** — §6.3.
8. **Determinism** — the whole vector set replayed twice in one process and
   once in a fresh process, byte-identical.
9. **Hyperedge** (Amendment D) — the iteration order of ``hyperedges``,
   ``members-of`` and ``hyperedges-of``, including a hyperedge hydrated with
   its members in descending id order to prove declared order is unobservable;
   the ``E-EVAL-032`` type mismatch; ``add-hyperedge`` at exactly
   ``:max-members`` (loads) and one over it (``E-LOAD-042``); a manifest row
   missing ``:max-members`` on a ``HyperedgeType`` and one carrying it on a
   ``NodeType`` (both ``E-LOAD-042``); and a fold over ``members-of`` whose
   static bound equals the declared ``:max-members``.

10. **Edge and hyperedge attributes** (chapter C1) — ``field-of`` over an
    ``EdgeRef``, a ``HyperedgeRef`` and a ``NodeRef``; the §2.4 coverage row
    written as a ``sum`` and as a weighted ``mean`` over
    ``<edge-type>/strength``; ``sum`` over an intensive edge field rejected
    ``E-TYPE-041`` and the same fold accepted with a ``:weight``; a
    ``field-of`` whose referent is of another type (``E-EVAL-033``); a
    ``deffield`` whose first segment names no registered type
    (``E-LOAD-023``); a vocabulary with a ``NodeType``/``EdgeType`` rendering
    collision (``E-LOAD-032``); a re-declaration of
    ``<edge-type>/strength`` (``E-LOAD-001``); an ambiguous foreign-type
    ``:field`` reference under two same-type bodies (``E-TYPE-013``); and an
    ``intrinsic`` declared with a reserved form-head name
    (``E-LOAD-024``).
11. **Edge mutation** (chapter C2) — ``update-edge`` under each of the four
    ``<update-op>`` forms, against ``<edge-type>/strength`` and against a
    ``deffield``-declared edge field; the same write reaching a range boundary
    (``E-EVAL-020``) and an I.15-illegal mode transition (``E-EVAL-030``);
    ``edge-between`` resolving, and failing to resolve (``E-EVAL-034``);
    ``add-edge`` carrying ``<field-init>``\ s, one of them naming ``strength``
    (``E-PARSE-041``) and one owning off the wrong type (``E-TYPE-014``); an
    ``update-edge`` whose referent is of another edge type (``E-EVAL-033``);
    an ``edge-between`` whose enum-ref names a ``NodeType`` (``E-TYPE-011``);
    and a hydration seeding two edges of one type between one ordered pair
    (``E-LOAD-044``).
12. **Graph-scope carriers** (chapter C3) — ``the`` resolving against a
    ``:ceiling 1`` manifest row; ``the`` against a row whose ceiling is not 1
    (``E-LOAD-043``); ``the`` against a graph that hydrated no such node
    (``E-EVAL-035``); a read and a write of one carrier field through
    ``field-of``/``update-node``; ``the`` against an ``EdgeType`` member
    (``E-TYPE-011``); a manifest carrying no row for the carrier type
    (``E-LOAD-045``); and an **accumulation vector** — three subject nodes each
    adding a bounded scalar to one carrier — whose expected value pins the §4.2
    subject order by being sensitive to it, and whose ``:fuel-used`` is the
    first subject's firing (§4.5).
13. **Rule domain** (chapter C4) — an inferred node domain (the §5.6 rule,
    unchanged, is one); a rule with no self-scoped reference and no
    ``<domain>`` (``E-LOAD-004``); a rule whose self-scoped references name two
    node types (``E-LOAD-004``); an explicit ``(domain NodeType/…)`` overriding
    a would-be ambiguity; a rule whose ``<domain>`` and self-scoped reference
    disagree (``E-TYPE-010``); ``(domain :graph)`` firing exactly once against
    a multi-node graph; ``self`` referenced in a graph-domain rule
    (``E-TYPE-015``); ``:graph`` used outside a ``domain`` form
    (``E-PARSE-013``); a ``(domain EdgeType/…)`` (``E-TYPE-011``); and a
    ``:cas`` vector for each of the two ``domain`` shapes.
14. **Element selection** (chapter C5) — ``select-max`` and ``select-min`` over
    each of the six query heads, proving the result's element type; a
    **tie vector** whose two elements score equally, pinning that the lower id
    wins for both operators; selection over an empty query
    (``E-EVAL-021``); a ``Bool`` and an ``Enum<T>`` score (``E-TYPE-016``); a
    selection whose result is the element operand of ``update-node`` and of
    ``field-of``; and a selection over an intensive score, which must
    **accept** (the kind rule polices aggregation, not ordering).
15. **Effect-position iteration** (chapter C6) — ``for-each`` over ``edges``
    applying ``update-edge`` and ``emit`` per element, with the expected
    per-element results in iteration order; ``for-each`` whose query would
    have changed had it seen an earlier verb's effect, proving pre-state
    materialization; nested ``for-each`` and its static bound; ``for-each``
    over an empty query, which applies nothing and **must not** error; and a
    ``for-each`` whose ``:fuel`` is one short of its static bound
    (``E-LOAD-040``).
16. **Computed bindings** (chapter C7) — a ``:expr`` over earlier bindings,
    with ``:fuel-used`` proving the expression is charged once and each
    reference 1; the same rule written with the algebra inlined twice, whose
    ``:fuel-used`` must be strictly larger; a forward reference and a
    self-reference (``E-PARSE-032``); ``:optional`` on a ``:expr``
    (``E-PARSE-033``); ``it`` inside a ``:expr`` (``E-TYPE-012``); a foreign
    node type's ``:field`` referenced from a ``:expr`` (``E-TYPE-010``); and a
    ``:expr`` whose kind is intensive feeding an unweighted ``mean``
    (``E-TYPE-042``), proving kind propagates through the binding.
17. **Typed neighbours and element naming** (chapter C8) — the first
    ``neighbors`` vectors this document has ever required: a fold over
    ``neighbors`` reading the annotated type's field (which must typecheck), a
    graph whose traversal reaches two node types proving the operand *filters*,
    a three-operand ``neighbors`` (``E-PARSE-042``, arity), the two operands
    swapped (``E-TYPE-011`` at both positions), a **multiplicity vector** — a
    graph where two qualifying edges reach one node, whose ``fold count`` over
    ``neighbors`` must be ``1`` — and a static bound
    equal to the **lesser** of the two ceilings; and for ``:as``, a two-hop
    nested fold naming the outer element, ``it`` inside the inner body
    resolving to the *inner* element, a ``:as`` name referenced outside its
    body (``E-TYPE-012``), ``:as it`` and ``:as self`` (``E-PARSE-022``), and a
    ``:as`` colliding with a binding name (``E-PARSE-030``).
18. **Metric registration** (chapter C9) — a graph-domain ``metric`` read by a
    ``:metric`` binding and an element-indexed one read by ``metric-of``; each
    read through the other's form (``E-LOAD-012``); a declaration disagreeing
    with the kernel's registration (``E-LOAD-025``); an unregistered name
    (``E-LOAD-011``, the §6.3 correction, re-proved for both forms); a
    ``metric-of`` against a referent of another type (``E-EVAL-036``) and one
    the provider produced no value for (``E-EVAL-037``); a **stability
    vector** — two rules at one anchor position reading one metric, whose
    expected values must be equal; a metric declared ``:kind intensive``
    feeding an unweighted ``mean`` (``E-TYPE-042``), proving the declared kind
    propagates; and a ``:cas`` vector for the ``metric`` form under both
    ``<domain>`` shapes.
19. **Deliberate absences** (chapter C10) — a family of *rejecting* vectors, so
    the absences of §3.8 are pinned as loudly as the presences: ``(bound? x)``
    (``E-LOAD-021``, an undeclared intrinsic); a string literal in an ``emit``
    payload (``E-PARSE-010`` — the string lexes, the position rejects it); an
    ``(unset …)`` update-op (``E-PARSE-015``); and one *accepting* pair
    proving each re-modelling
    works — a presence-field guard writing value and presence together, a
    ``select-min`` over ``queued-at-tick`` returning the FIFO head, and a
    producer-stamped tick field read by a consumer rule at a later anchor.
20. **Invariant substrate and the lattice** (chapter C11) — a one-hop
    aggregation fold over an ``IN_SCALE`` relation and the ``for-each``
    distribution that mirrors it; ``add-edge`` and ``remove-edge`` naming an
    ``:invariant`` edge type, and ``add-node``/``remove-node`` naming an
    ``:invariant`` node type (all ``E-LOAD-013``); an ``update-node`` field
    write on an invariant type, which must **accept**, proving the flag
    constrains structure and not state; ``:invariant`` on a
    ``HyperedgeType`` row (``E-LOAD-042``); and a hydration that seeds a
    keyed reference series as declared fields against a rule reading them
    with a plain ``:field``, plus the same rule against a hydration that
    omits the series (``E-LOAD-010``).
21. **Hyperedge fields and reference identity** (chapter C12) —
    ``update-hyperedge`` under each ``<update-op>``, and one whose ``<qname>``
    owns off another hyperedge type (``E-EVAL-033``); a roster change proving
    membership is still whole-object replacement; ``=`` and ``!=`` on two
    references of the same kind, both outcomes; a reference compared with
    ``<`` and one compared across kinds (both ``E-TYPE-017``); and the
    intersection idiom above, whose ``:fuel-used`` must show the quadratic
    cost the deferral is paying.
22. **The intrinsic cap and calendar bindings** (chapter C13) — a call to an
    intrinsic outside the declared set (``E-LOAD-021``); an ``intrinsic``
    declaration named ``sigmoid`` (``E-LOAD-024``); ``:year``,
    ``:tick-of-year`` and ``:tick-in-cycle`` at a known tick, with a boundary
    case at each cycle wrap; ``:tick-in-cycle 0`` and a negative length (both
    ``E-PARSE-014``); and — for the RNG — **two vectors with the same carrier
    key whose draws must be equal**, and a pair of rules differing only in a
    guard that skips a draw, whose other draws must be unchanged, pinning that
    a draw is keyed rather than streamed.

23. **Attributed membership** (Amendment AG (i)) — ``membership-field-of``
    reading a payload field of each declared scalar type, inside a fold over
    ``members-of`` and from an effects list; the read against a well-typed
    pair that is not a membership (``E-EVAL-038``); the read whose hyperedge
    operand is of another ``HyperedgeType`` and the read whose member operand
    is of another ``NodeType`` (both ``E-EVAL-033``); ``update-membership``
    under each of the four ``<update-op>`` forms, one reaching a range
    boundary (``E-EVAL-020``) and one against a non-membership pair
    (``E-EVAL-038``); ``add-hyperedge`` whose annotated ``member`` items
    initialise every declared payload field, one omitting a field and one
    using a bare item under a payload-declaring hyperedge type (both
    ``E-LOAD-047``), one initialising a field twice (``E-PARSE-041``), one
    naming a field owned by another type (``E-TYPE-014``) and one whose member
    is not of the annotated type (``E-EVAL-033``); a hydration omitting a
    payload field (``E-LOAD-047``); a ``field-of`` naming a membership qname
    and a ``membership-field-of`` naming a hyperedge's own field (both
    ``E-LOAD-046``); a ``deffield`` carrying ``:member`` whose first segment
    renders a ``NodeType`` (``E-LOAD-048``) and one whose ``:member`` names an
    ``EdgeType`` member (``E-TYPE-011``); an **ordering vector** — a hyperedge
    hydrated with its members in descending id order, folded with a
    non-commutative-in-binary64 body, pinning that iteration follows D25's
    ascending member id; an intensive payload under an unweighted ``mean``
    (``E-TYPE-042``) and the same fold accepted with a ``:weight``; §2.12's
    two-hop worked shape verbatim, which must **load** — its outer ``max`` is
    kind-neutral where a ``sum`` over the same intensive result would be
    ``E-TYPE-041`` (D90); a roster
    replacement proving a dropped member's payload does not survive it; and a
    fold over ``members-of`` reading payload whose static bound equals the
    declared ``:max-members`` — the ceiling axis unchanged by the payload.

24. **Lattice instances** (Amendment AG (ii)) — a ``manifest`` declaring a
    substrate rung with an extensive and an intensive adjunction along it,
    loading clean, with this section's opening aggregation fold and its
    mirrored ``for-each`` distribution evaluated over the declared rung; a
    ``:substrate`` rung one of whose three types carries no ``:invariant`` row
    (``E-LOAD-049``); an intensive adjunction with no ``:weighted-by``
    (``E-LOAD-050``) and the same declaration accepted with one; a
    ``:weighted-by`` naming an intensive field (``E-TYPE-043``); an adjunction
    citing an undeclared rung, one whose ``<qname>`` is owned by the other
    end's node type, one whose two fields disagree in ``:kind``, and a
    ``:weighted-by`` on an extensive pair (all ``E-LOAD-051``); two rungs and
    two adjunctions sharing a name (``E-LOAD-001``); a rung whose positional
    operand names an ``EdgeType`` and one whose ``:via`` names a ``NodeType``
    (both ``E-TYPE-011``); a rung naming a type the manifest carries no row
    for (``E-LOAD-045``); a **diagnostic-order vector** — a manifest carrying
    two independently malformed declarations, whose reported first failure is
    the lower declared name in byte order; an ``update-node`` field write on a
    substrate rung's node type, which must **accept** (the rung constrains
    structure, not state); and ``:cas`` vectors for ``rung`` and
    ``adjunction`` under both the flagged and unflagged, weighted and
    unweighted shapes.

Families 10–22 are the R9 spec chapters' (the chapter letters cite
``reports/bsl-gap-analysis-2026-08-10.md`` §7); families 23 and 24 are
Amendment AG's, one per clause. Two obligations are stated
once here rather than repeated in every family: each new form tag also owes a
``:cas`` vector under family 6, and each new construct owes its exact
``:fuel-used`` figure under family 5. Both make a chapter's landing a
``rules_hash`` surface change and therefore a **vector re-bless ceremony**,
which the teams should plan rather than discover.

6.3 Transcription contract
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The conformance **seed** is the existing Python evaluator test estate: 271
lines in ``tests/unit/domain/doctrine/test_mechanics.py`` plus 628 lines in
``tests/unit/engine/test_event_evaluator.py`` — 899 lines, verified by
``wc -l`` on 2026-07-29.

Each existing test case transcribes to one or more ``vector`` forms. The
transcription is recorded in a ledger with one row per source test:

.. list-table::
   :header-rows: 1
   :widths: 22 18 20 40

   * - Column
     - Type
     - Example
     - Meaning
   * - ``source``
     - test id
     - ``test_mechanics.py::TestTrapCondition::test_and``
     - The Python test being transcribed.
   * - ``vectors``
     - list of vector ids
     - ``doctrine/and-both-true``
     - The BSL vectors that replace it.
   * - ``verdict``
     - ``preserved`` | ``corrected`` | ``retired``
     - ``preserved``
     - Whether BSL reproduces the observed behavior, deliberately differs, or
       the case ceases to exist (e.g. a test of the ``@`` sigil's tokenizer).
   * - ``note``
     - string
     - —
     - Mandatory when ``verdict`` is ``corrected`` or ``retired``.

**Grammar-superset honesty.** BSL is a superset of the two existing grammars'
expressible sets, **not of their failure semantics**. The design document
(§5) names exactly four silent-degradation behaviors that are deliberately
broken; copied verbatim:

    Four silent-degradation behaviors are deliberately broken as III.11
    corrections: unknown graph metric → 0.0 (``event_evaluator.py:313``),
    unknown aggregation → False (``:439``), unknown comparison operator →
    False (``:405``), empty precondition set → True (``:103``). The ~899 lines
    of existing evaluator tests (271 doctrine + 628 event-evaluator)
    transcribe as the conformance seed **with a documented delta** at exactly
    those four points.

Their BSL dispositions:

.. list-table::
   :header-rows: 1
   :widths: 34 22 44

   * - Python behavior
     - BSL behavior
     - Where enforced
   * - unknown graph metric → ``0.0``
     - ``E-LOAD-011`` at load
     - §2.5 (``:metric`` resolution against the closed registry)
   * - unknown aggregation → ``False``
     - ``E-PARSE-015`` at parse
     - §2.7 (``<fold-op>`` is a closed five-member terminal set)
   * - unknown comparison operator → ``False``
     - ``E-PARSE-015`` at parse
     - §2.4 (``<cmp>`` is a closed six-member terminal set)
   * - empty precondition set → ``True``
     - ``E-PARSE-020`` at parse
     - §2.3 (``(when)`` is not expressible; write ``(when #t)``)

Every transcribed test that asserted one of these four behaviors takes
``verdict = corrected`` with a note naming the row. There is a fifth,
lower-profile delta the transcription must also record: the doctrine DSL's
**absent variable reads as ``0``** (honest-null, ``mechanics.py`` module
docstring) becomes an explicit ``:optional``/``:default 0`` declaration
(§3.5), so transcribed doctrine vectors that relied on it carry
``verdict = corrected`` and their rules carry an allowlisted ``:default``.

6.4 Review gates on the transcription
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Transcription is where the design document's failure classes F1–F4 bite. The
ledger is reviewed against them: eyeball-before-golden (F1 — a vector's
expected value is read by a human before it is blessed, never captured from a
run), tautology ban (F2 — a vector whose expectation is computed by the same
code path it tests is invalid), transcription review with an idiom-mismatch
checklist (F3), and spec-completeness (F4 — every construct §2 defines has at
least one vector).

7. Consolidated grammar
-------------------------

Every production of §§1, 2 and 6.1, collected into one file and included here.
**The grammar collects; it does not amend.** On any divergence between the
§1/§2/§6 **text** and this appendix, the **section text wins**, and the
divergence is a defect in the appendix to be repaired there. Nothing in this
section adds a form, retires one, or changes what one means — an inclusion is
not a second home, which is the property that keeps this document the *one*
normative home its Program-27 charter makes it (D92).

*Text, not merely production.* The trigger is deliberately the section **text**
rather than a section production, because nine of the appendix's productions
have no code block behind them at all — the sections state them in **prose**,
and a grammar needs a right-hand side. They are ``Char`` (§1.1),
``whitespace``, ``comment`` and ``delimiter`` (§1.2, §1.4), ``operator``
(§1.4's draft ruling), ``escape`` (§1.5), ``intrinsic-name`` (§2.7),
``type-name`` (§2.9/§2.11 use it, §3.1 names the types) and ``vector-file``
(§6.1). Under a production-only trigger those nine would adjudicate
themselves — the appendix legislating in exactly the places where no section
production exists to check it against, which is the reverse of what this
section is for.

Three things the file carries that the sections do not. It states a **single
EBNF dialect** — W3C EBNF, the XML 1.0 §6 notation whose operator set §1.4 and
§2.1 already use — and applies it uniformly, so that a reader is never left
inferring which dialect a ``?`` came from. It supplies the nine prose-sourced
right-hand sides above, each carrying its citation. And it collects, in
comments, the **context conditions an EBNF cannot express**: maximal munch
within a token run, the string literal's exemption from it, the closed keyword
set, the reserved element names ``self`` and ``it``, and the whole of §3's
static semantics. Read without them the file **both** accepts programs this
language rejects and rejects programs it accepts — the token-run rule applied
naively to a ``string`` would cut every non-trivial ``:material-basis``
apart — and the file says so at the top rather than leaving either direction
to be discovered.

Where the sections are silent or disagree with themselves, the file **collects
the reference implementation's reading and flags it**. That wording is exact,
and an earlier "records the gap instead of choosing" was not: a production must
have a right-hand side, so writing one *is* choosing, and the honest record
names the reading taken and what cuts against it. Two places:

- ``<type-name>`` carries no §1.4 atom class, while §3.1 spells the type names
  capitalized and **§2.11's own worked example writes** ``:type Coefficient``.
  No capitalized spelling is lexable under §1.4, so the appendix collects the
  reference implementation's lowercase-``symbol`` reading — and records the
  worked example that contradicts it. The repair is the Phase-1 review's and
  runs either way: §1.4 gains an atom class for capitalized type names, or
  §3.1's table and §2.11's example are re-spelled lowercase.
- §6.1's ``:graph`` / ``:fuel-used`` / ``:cas`` are written with the ``?``
  binding to the *value*, which makes the keywords themselves mandatory
  against §6.1's own prose. Here the section production exists, so the
  appendix transcribes it verbatim and names the divergence in place.

*What the appendix does not reach.* The ``.bscn`` scenario-file dialect is
outside its scope — no section specifies it, and D91's fixture/content split
is why — so the shape conflict that follows is **recorded as D93, not resolved
here**.

.. literalinclude:: bsl.ebnf
   :language: bnf
   :caption: ``docs/reference/bsl.ebnf`` — the consolidated grammar

7.1 The rigor index
~~~~~~~~~~~~~~~~~~~~~

Where each artifact of this language's rigor lives. **Pointers only**: every
row's content belongs to the place it names, and this table restates none of
it.

.. list-table::
   :header-rows: 1
   :widths: 24 30 46

   * - Artifact
     - Home
     - What it fixes
   * - Consolidated grammar
     - §7 / ``docs/reference/bsl.ebnf``
     - Every production of §§1, 2 and 6.1 in one stated dialect. Normative
       by inclusion; the section text wins on divergence.
   * - Lexis and syntax
     - §1, §2
     - The productions themselves, with the rulings that shaped each.
   * - Static semantics
     - §3
     - Types (§3.1), the currency lane (§3.2–§3.3), the intensivity kind
       rule (§3.4), binding resolution (§3.5), the closed vocabulary
       (§3.6), deliberate absences (§3.8), the invariant substrate and
       scale lattice (§3.9), the intrinsic cap (§3.10).
   * - Dynamic semantics
     - §4
     - Evaluation order (§4.1), the environment and subject order (§4.2),
       arithmetic (§4.3), query evaluation (§4.4), cross-system handoffs
       (§4.7).
   * - Cost model
     - §3.7 (static bound), §4.5 (runtime meter)
     - ``cost(n)`` per AST node and ``bound(rule)``; pinned by conformance
       vector, so a revision is a re-bless ceremony.
   * - Error-code register
     - §4.6
     - The five families (``E-LEX`` / ``E-PARSE`` / ``E-TYPE`` /
       ``E-LOAD`` / ``E-EVAL``), when each fires, and the contiguity rule
       every decade block is checkable against.
   * - Canonical encoding
     - §5, worked example §5.6
     - The CAS byte layout, canonical child order, and ``rules_hash``.
   * - Conformance vectors
     - §6.1 (format), §6.2 (24 required families), §6.3 (transcription)
     - What an implementation must pass to claim conformance, and the four
       silent degradations deliberately broken.
   * - Decision register
     - *Draft-Ruling Register*, below
     - Every point the design document under-determined, D1–D92, each a
       Phase-1 review item.
   * - Reference implementation
     - ``rust/crates/babylon-bsl``
     - The executable reading: ``reader.rs`` (§1), ``grammar.rs`` (§2's
       static shape rules), ``canonical_ast.rs`` (§5), ``bound_checker.rs``
       (§3.7), ``rule_pipeline.rs`` (the §4.6 class ordering). It is *an*
       implementation, not the spec — III.12(a) requires this document to
       be derivable without reading it.
   * - Editor tooling
     - ``tools/tree-sitter-bsl``
     - A tree-sitter grammar **derived** from ``bsl.ebnf`` and normative
       for nothing, with a corpus drawn from real in-tree content. It
       parses; it does not check §3.
   * - Determinism contract
     - :doc:`/reference/determinism-contract`
     - What ``rules_hash`` is combined with and compared against: the
       tick-hash field set, ``ContentDigest`` composition, and the
       float-tolerance regimes.

Draft-Ruling Register
-----------------------

Every decision this document made where the design document under-determined
the language. Each is a Phase-1 review item.

**Resolved — the Amendment D question (was open question 3 on this document's
first revision).** That question read: *"Amendment D is unratified, so*
``<query>``\ *'s data shape is written against the dyadic working assumption.
If Phase 0 rules hyperedge, §2.6, §2.8 and the edge-side ceiling in §3.7 all
need revision."* Phase 0 ruled: **NATIVE HYPEREDGE**, 2026-07-29, Amendment AE
clause (vi) (``CONSTITUTION.md`` v3.0.0), recording
``ai/_inbox/amendment-d-analysis-p27.md`` §9 (PR #353) sub-rulings D-1…D-7.
All three sections were revised in this document's second revision; the dyadic
forms coexist unchanged (D-2). Rows **D24–D28** below are the new
under-determined points that revision introduced — the question is closed, its
consequences are the ordinary kind of review item.

.. list-table::
   :header-rows: 1
   :widths: 8 30 62

   * - #
     - Section
     - Ruling
   * - D1
     - §1.1
     - String literals must be NFC; non-NFC is a load error.
   * - D2
     - §1.2
     - No block comments, no reader macros.
   * - D3
     - §1.5
     - Kind-suffixed literals (``$``, ``p``, ``i``, ``c``); a bare
       non-integer literal is a load error; max scale 9 for ``p``/``i``/``c``,
       6 for ``$``.
   * - D4
     - §1.5
     - Decimal canonicalization to minimal scale; Currency to integer
       micro-units.
   * - D5
     - §2.3
     - Anchorless rules inherit the system named by their rule-id's first
       segment.
   * - D6
     - §2.4
     - ``it`` is the reserved query-element binding; ``exists``/``forall``
       bind no name.
   * - D7
     - §2.6
     - Query iteration order is ascending id byte order, not storage order.
   * - D8
     - §2.7
     - Arithmetic is strictly binary; no variadic ``+``.
   * - D9
     - §2.9
     - ``:kind`` lives in BSL ``deffield`` content, not in host-language
       annotations.
   * - D10
     - §3.2
     - ``Currency`` subtraction below zero is a loud evaluation error, not a
       clamp — the domain stays ``[0, ∞)``.
   * - D11
     - §3.3
     - Bounded-scalar arithmetic promotes to ``Real``; the range check happens
       once, at the store boundary, and never clamps.
   * - D12
     - §3.4
     - ``:const``/``:metric`` bindings are kind-neutral; ``extensive ×
       extensive`` is a type error. **The** ``:metric`` **clause is superseded
       by D55**: a ``:metric`` binding and a ``metric-of`` accessor carry the
       kind their §2.11 registration declares. The ``:const`` clause and the
       ``extensive × extensive`` rule stand.
   * - D13
     - §3.5
     - ``:optional`` requires ``:default``; there is no ``bound?`` predicate.
   * - D14
     - §3.7
     - Cost rows for ``if``, ``exists``/``forall``, ``query``, structural
       verbs, ``guard``, and the ``bound(rule)`` composition — the five base
       rows are the design document's and are **not** a draft ruling.
   * - D15
     - §3.7
     - ``neighbors`` uses the edge-type ceiling; a per-node degree ceiling is
       a review item.
   * - D16
     - §4.2
     - Rules at one anchor position evaluate in ascending rule-id byte order.
   * - D17
     - §4.3
     - No FMA contraction; non-finite results are unrepresentable.
   * - D18
     - §4.4
     - ``mean``/``min``/``max`` over an empty set are loud errors, not ``0``.
   * - D19
     - §5.2
     - The two-shape (atom/form) length-prefixed binary CAS, big-endian, with
       ASCII tag names rather than a numeric tag registry.
   * - D20
     - §5.2
     - Flag keywords encode as ``opt`` with a ``#t`` value so every option has
       one shape.
   * - D21
     - §5.3
     - Canonical child order: positional, then options sorted by keyword name,
       then variadic body in source order.
   * - D22
     - §5.5
     - ``rules_hash`` covers ``rule`` forms only, sorted by id, with
       ``deffield``/``intrinsic``/``manifest`` hashed into sibling digests that
       ``ContentDigest`` combines.
   * - D23
     - §6.1
     - Conformance vectors are BSL content; ``:fuel-used`` is mandatory on
       non-error vectors.
   * - D24
     - §2.6
     - ``members-of``/``hyperedges-of`` take the ``HyperedgeType`` as a
       mandatory operand — ``HyperedgeRef`` carries no static type, and the
       annotation is what makes ``ceiling(query)`` computable; a mismatch at
       evaluation is ``E-EVAL-032``.
   * - D25
     - §2.6
     - A hyperedge's declared member order is unobservable; ``members-of``
       yields ascending node-id byte order. A member list is a set.
   * - D26
     - §2.8
     - Two typed verbs (``add-hyperedge``/``remove-hyperedge``) rather than an
       overloaded ``add-edge``; membership change is whole-hyperedge
       replacement, so per-membership payload and hyperedge-field mutation
       were both inexpressible when this row was written. **The
       hyperedge-field half is superseded by D65** (``update-hyperedge``); the
       per-membership half was escalated by D66 and is **superseded by
       D79–D84** (Amendment AG (i)). The member-list discipline this row rules
       — whole-object replacement, one ``:max-members`` check, no partial
       roster — is untouched by both.
   * - D27
     - §2.9, §3.7
     - A hyperedge manifest row declares two numbers — ``:ceiling`` and
       ``:max-members`` — mandatory together on a ``HyperedgeType`` row and
       illegal elsewhere (``E-LOAD-042``); ``add-hyperedge``'s member count is
       checked against ``:max-members`` **statically**.
   * - D28
     - §3.7
     - ``hyperedges-of`` uses the hyperedge type's ``:ceiling``; a per-node
       incidence-degree ceiling would be tighter and is deferred alongside
       D15's per-node degree ceiling for ``neighbors``.
   * - D29
     - §2.5, §2.10
     - Edge and hyperedge fields are read by the ``field-of`` accessor, not by
       an edge-typed ``:field`` binding. **Divergence recorded:** the R9 gap
       analysis §2 (Q1) sketched the binding form; a binding resolves
       implicitly against an enclosing body and the demanding systems read
       several edge types per rule, so the annotated accessor — D24's fix for
       ``members-of`` — wins.
   * - D30
     - §2.5
     - A foreign-node-type ``:field`` reference under two or more enclosing
       bodies of that type is ``E-TYPE-013``; the author names an element
       (§2.6 ``:as``) and uses ``field-of``.
   * - D31
     - §2.9
     - A ``deffield``'s first segment may name a ``NodeType``, ``EdgeType`` or
       ``HyperedgeType`` member. The segment↔member rendering (lowercase,
       ``_``→``-``) is stated normatively; renderings must be pairwise
       disjoint across the three enum types (``E-LOAD-032``), must be valid
       ``symbol``\ s (``E-LOAD-033``), and an unregistered first segment is
       ``E-LOAD-023``.
   * - D32
     - §2.9
     - ``<edge-type>/strength`` is implicitly declared on every ``EdgeType``:
       ``Coefficient``, ``extensive``, re-declaration is ``E-LOAD-001``. The
       ``extensive`` kind is what makes §2.4's ``sum_strength`` row honourable
       under §3.4 without an exemption.
   * - D33
     - §2.7
     - Every §5.2 form-head symbol is reserved against the intrinsic
       namespace; declaring an intrinsic with one is ``E-LOAD-024``.
   * - D34
     - §2.10
     - Accessors take their owning type in the ``<qname>``; a referent of
       another type, or a field the element carries no value for, is
       ``E-EVAL-033``. ``:optional``/``:default`` are binding options and
       never apply to an accessor.
   * - D35
     - §2.8
     - ``update-edge`` exists. D26's whole-object discipline is specific to the
       member list it protects and does **not** carry to the dyadic layer,
       which has no partial state to leave behind.
   * - D36
     - §2.8, §2.10
     - ``update-edge`` takes an ``EdgeRef`` and has one shape, not two;
       endpoint-holding rules reach the edge through ``edge-between``, whose
       well-definedness follows from §2.6's ``(source, target, type)`` order
       key. Absence is ``E-EVAL-034``. **Divergence recorded:** the R9 gap
       analysis §2 (Q3) sketched a type-and-endpoints verb.
   * - D37
     - §2.8
     - ``add-edge`` carries ``<field-init>*``; a ``<field-init>`` naming the
       implicit ``strength`` field is ``E-PARSE-041``, and one whose owning
       type is not the verb's ``<enum-ref>`` type is ``E-TYPE-014``
       (statically on the minting verbs, ``E-EVAL-033`` on the updating ones).
   * - D38
     - §3.7
     - Accessors are keyed lookups charged at 1 + operands and never
       multiplied by a ceiling, so only iteration constructs carry ceiling
       factors in the static bound.
   * - D39
     - §3.6
     - Graph-scope state is ordinary node state on a carrier ``NodeType``
       whose ceiling is 1 — no new grammar, no second storage class. Adding a
       carrier type is amendment territory. The ``:global``/``update-global``
       route is recorded as rejected.
   * - D40
     - §2.10
     - ``the`` names the unique node of a ``:ceiling 1`` type; a ceiling other
       than 1 is ``E-LOAD-043`` (static, off the manifest) and an unhydrated
       carrier is ``E-EVAL-035``.
   * - D41
     - §4.7
     - No staging, double-buffering or ``previous`` construct: tick ordering
       is the handoff mechanism, and the anchor is where a one-tick lag is
       declared.
   * - D42
     - §1.6
     - ``:out``/``:in``/``:any`` are flag keywords the table had omitted;
       ``:graph`` joins them, legal only in a ``domain`` form.
   * - D43
     - §2.3
     - ``<domain>`` is optional with a stated inference (the unique node type
       of the rule's self-scoped references); ``|U| ≠ 1`` is ``E-LOAD-004``.
       ``(domain :graph)`` fires once per tick and unbinds ``self``
       (``E-TYPE-015``). Explicit declarations override inference; a
       disagreeing self-scoped reference is ``E-TYPE-010``.
   * - D44
     - §4.2
     - A node-domain rule fires over its subjects in ascending node-id byte
       order and applies their effects in that order — previously
       unspecified, and load-bearing because the binary64 lane is not
       associative.
   * - D45
     - §2.7
     - ``select-max``/``select-min`` return the extremising **element**; ties
       break to the first element in §2.6 iteration order, making the
       deterministic tiebreak a property of the language rather than of each
       rule. An empty query is ``E-EVAL-021``.
   * - D46
     - §2.7
     - The score expression must be a comparable scalar (``E-TYPE-016``); its
       kind is unconstrained and the result is kind-neutral, because §3.4
       polices aggregation and selection orders rather than aggregates.
   * - D47
     - §2.8
     - ``for-each`` is bounded iteration in effect position, charged like
       ``exists``/``forall``. ``it`` is bound in its body.
   * - D48
     - §2.8
     - Every expression in an effects list — verb operands, ``guard``
       conditions, ``for-each`` queries — is evaluated against the rule's
       pre-state, which is what keeps §4.2's no-self-observation law true in
       the presence of iteration. Application order is element order (outer)
       then source order (inner), and an empty ``for-each`` query applies
       nothing rather than erroring.
   * - D49
     - §2.5
     - ``:expr`` computed bindings, resolved in declaration order; forward and
       self references are ``E-PARSE-032``, so no cycle analysis is needed.
       ``:optional``/``:default`` on a ``:expr`` is ``E-PARSE-033``.
   * - D50
     - §3.7, §4.5
     - A ``:expr`` is charged once at binding time and 1 per reference, and
       ``bound(rule)`` gains ``Σ cost(:expr bindings)``. A computed binding
       cannot observe the rule's own effects — it is an abbreviation, not a
       sequencing construct.
   * - D51
     - §2.6
     - ``neighbors`` takes a mandatory result-``NodeType`` operand — D24's fix
       applied to D24's problem. It **filters** (a node may reach several
       types) where D24's operand **asserts**. Breaking, and made anyway: no
       conformance vector and no content rule exercises ``neighbors``, so
       nothing is re-blessed, while the ``babylon-bsl`` bound checker *does*
       carry the three-operand form and its edge-type-only bound and is
       updated when Phase 1 implements the chapter.
   * - D52
     - §3.7
     - ``ceiling(neighbors)`` is the lesser of the edge-type and
       result-node-type ceilings, revising D15's edge-type-only reading; the
       per-node degree ceiling stays deferred.
   * - D53
     - §2.5, §2.6
     - ``it`` denotes the element of the **innermost** enclosing iterating
       form. This is rebinding by construction, not shadowing of a
       declaration, so ``E-PARSE-022`` is untouched — the §2.5/§3.7 tension is
       resolved by reading rather than by repeal.
   * - D54
     - §2.6
     - ``:as`` optionally names an iterating form's element, in scope through
       nested bodies, sharing the rule's binding namespace
       (``E-PARSE-030``/``E-PARSE-022``) and ``E-TYPE-012`` outside its body.
       Naming was chosen over rebinding rules because it changes the meaning
       of no existing form.
   * - D55
     - §2.11
     - A ``metric`` form declares what the kernel provides — type, kind,
       domain, provider — so the typechecker and fuel checker stay derivable
       from content (D9's rationale). Kernel disagreement is ``E-LOAD-025``.
       Supersedes D12's clause making ``:metric`` bindings kind-neutral: they
       now carry the declared kind.
   * - D56
     - §2.10, §2.11
     - Element-indexed metrics are read by the ``metric-of`` **accessor**, not
       by a ``:metric-of`` bind-src. **Divergence recorded:** the R9 gap
       analysis §3 (B4) sketched the bind-src; a bind-src encodes as a
       two-child ``opt`` under D20 and this one needs two operands, so it
       would have been the only bind-src of its shape. Wrong-form reads are
       ``E-LOAD-012``; runtime failures are ``E-EVAL-036``/``E-EVAL-037``.
   * - D57
     - §2.11
     - Provider work is **not** metered against the reading rule (the read
       costs 1 + operand); metric *values* enter no content hash and reach the
       tick hash only through the fields rules write from them; a Rust domain
       crate qualifies as a provider only inside the determinism contract's
       pinned toolchain and with golden vectors.
   * - D58
     - §3.8
     - Optional axes take a **companion presence field** written under one
       ``guard`` with their value. ``:optional``/``:default`` is explicitly
       *not* the mechanism, because a default converts "never seeded" into
       "seeded with zero" and changes the eligibility population.
   * - D59
     - §3.8
     - No sequence or map type. FIFO agendas become a ``NodeType`` plus
       ``select-min``; ordered acquisitions become an edge plus
       ``select-max``; name sets become one ``Bool`` per name.
   * - D60
     - §3.8
     - No same-tick event-history query. The emitting rule stamps a field and
       the consumer reads it, which makes the dependency content rather than
       trace — and makes a crisis-gated system unportable apart from its
       producer.
   * - D61
     - §3.8
     - Four standing "nothing to add" rulings recorded so they stop
       returning: no string payloads on ``emit``; no ledger/receipt binding
       (a receipt is a kernel observation); no cascade restatement in the verb
       table (ADR185 R2 owns it); no bounded numeric iteration, and no
       bespoke ``renormalize`` intrinsic in its place.
   * - D62
     - §3.9
     - No ``group-by`` and no keyed collection. A scale lattice is graph
       content — carrier types plus a typed membership relation — so
       aggregation is a one-hop fold and distribution a ``for-each``. The
       no-``group-by`` clause stands. The minting clause — *"minting a rung or
       an adjunction is amendment territory and outside this document"* — is
       **superseded by D85–D89**: Amendment AG (ii) opened rung and
       adjunction-*instance* declaration to content, and the amendment
       territory that remains is the schema itself (new adjunction kinds,
       altered conservation, new level-lattice algebra).
   * - D63
     - §2.9, §3.9
     - ``:invariant`` on a ``NodeType``/``EdgeType`` ``ceiling`` row makes
       ``add-*``/``remove-*`` naming that type ``E-LOAD-013``, statically.
       Field writes are unaffected: the flag constrains structure, not state.
   * - D64
     - §3.9
     - No ``:reference`` bind-src. Keyed reference series are materialised as
       declared node fields at hydration and read with an ordinary ``:field``
       (ADR174's boundary), which makes the hydration contract a blocking
       dependency rather than a source of zeros.
   * - D65
     - §2.8
     - ``update-hyperedge`` closes the second half of D26 on C2's reasoning:
       writing a declared field leaves no member list partially anything.
       Membership change stays whole-object replacement, so D26's actual
       guarantee is untouched.
   * - D66
     - §2.8
     - **Not ruled here** *(when written)*. Per-membership payload — D26's
       first half — is a missing *kind of object*, not a missing verb, and
       changing the exposed hyperedge model is Amendment-AE-(vi) territory.
       Recorded as a **port blocker** with its two candidate landings named
       and neither specced. **Ruled since:** Amendment AG clause (i)
       (``CONSTITUTION.md`` v3.2.0, ADR189, 2026-08-10) took the first of the
       two landings and rejected the second in its own words. **Superseded by
       D79–D84**; the port blocker is discharged.
   * - D67
     - §2.4, §3.1, §2.7
     - References compare by identity with ``=``/``!=`` only
       (``E-TYPE-017``); there is no ordering on references. With that and
       D54's naming, the intersection idiom becomes writable, and the
       deferral of a dedicated set-algebra operator stands on a form that can
       actually be written.
   * - D68
     - §2.5
     - Calendar reads land as ``:year``/``:tick-of-year``/``:tick-in-cycle``
       bindings rather than as ``mod``/``floor-div`` operators or an intrinsic
       rider — a kernel seam, not mathematics. The reach is bounded rather than
       nil, and §2.5 states the bound precisely: ``:tick-in-cycle`` makes
       ``tick mod k`` available for a **literal** ``k`` only, on the tick only,
       with the epoch staying the kernel's — so what cannot arrive behind it is
       a general mod operator over arbitrary expressions.
   * - D69
     - §3.10
     - The RNG carrier key is ``(session, tick, domain, stable_key)``, with
       ``session``/``tick`` never operands and ``domain`` a closed-vocabulary
       member. **A draw is a pure function of its key, not a stream
       position**, so a skipped draw cannot shift any other and §4.1's
       short-circuiting can never perturb the RNG.
   * - D70
     - §2.7, §3.10
     - The cap's authority chain is recorded as it actually reads: R10 holds
       ``{exp, log}`` citing ADR176 r21, whose own text pins the *mechanism*
       rather than the membership. §2.7's transcendental list is illustrative
       of the class, not a table of intrinsics that exist. The rider slate is
       recorded as **proposals**; this document declares none of them.
   * - D71
     - §3.10
     - ``sigmoid`` is a reserved **prohibited** intrinsic name
       (``E-LOAD-024``). Cap-legality is not doctrine-legality: the two gates
       are separate, gate 2 is Director review, and this is the one part of it
       that can be made mechanical.
   * - D72
     - §2.6, §3.1
     - A query result is a **set**: ``neighbors`` yields a node reachable by
       several qualifying edges exactly once, and a fold over it counts and
       sums per node rather than per edge. **Alternative rejected:** the
       multiset reading (one element per traversed edge), because a duplicated
       id has no defined position in §2.6's ascending-id order, so two
       conforming implementations could differ on a ``count`` and therefore on
       a tick hash. Per-edge work folds over ``edges`` or iterates it with
       ``for-each``.
   * - D73
     - §2.6, §2.10, §3.9
     - A hydration seeding two edges with one ``(source-id, target-id,
       edge-type)`` triple is ``E-LOAD-044``. This is what makes the triple a
       key rather than a sort field, and it is the clause §2.6's total order
       and ``edge-between``'s well-definedness were both resting on without
       citing: the pre-existing citations covered the verb (``E-EVAL-031``)
       and the ceiling (``E-LOAD-041``) but not hydration.
   * - D74
     - §2.3, §2.6, §2.8, §2.10
     - ``E-TYPE-011`` is stated once as a class rule covering **every**
       ``<enum-ref>`` operand position — ``NodeType`` for ``nodes``,
       ``neighbors``' fourth operand, ``the`` and ``(domain <enum-ref>)``;
       ``EdgeType`` for ``edges``, ``neighbors``' second operand and
       ``edge-between``; ``HyperedgeType`` for the three hyperedge queries;
       ``EventType`` for ``emit``. The R9 chapters added four positions and
       the per-form phrasing had left each of them without a rejection.
   * - D75
     - §1.6, §2.7, §4.6
     - Error-code hygiene, ruled once. Arity gets ``E-PARSE-042`` (with
       ``E-PARSE-040`` as its arithmetic-specific spelling); an unrecognized
       member of a closed terminal set gets ``E-PARSE-015``; a string literal
       in expression position is ``E-PARSE-010``, the existing
       atom-in-the-wrong-position code. The three ``E-PARSE-0xx`` placeholders
       in §6.2/§6.3 are retired, and the two ``E-TYPE`` holes the chapters left
       are closed by renumbering the offending **new** codes — a liberty that
       exists only before an implementation pins them and is spent here.
   * - D76
     - §2.9, §3.7
     - A manifest owes a ``ceiling`` row for every type the content set
       queries, mutates, reaches with ``the`` or (per D85) names in a
       ``rung``; an omission is
       ``E-LOAD-045``. Without the row ``ceiling(query)`` is not computable,
       ``E-LOAD-043``'s "other than 1" test cannot fire on a missing row, and
       ``:invariant``'s check silently never runs.
   * - D77
     - §4.5, §6.1
     - The fuel meter is **per firing**: each subject of a node-domain rule
       starts a fresh meter at the declared ``:fuel``, which is the only
       reading consistent with ``bound(rule)`` carrying no subject-count
       factor and with load-time legality being independent of graph size. A
       vector's ``:fuel-used`` is one firing's, reported for the first subject
       in §4.2's order.
   * - D78
     - §3.8
     - **Not ruled here.** Edge-endpoint accessors (gap item Q2) are recorded
       as an *open* item rather than a deliberate absence: the chapter plan
       assigned Q2 to no chapter, the ``self``-anchored
       ``neighbors``/``edge-between`` idiom covers only one endpoint-known
       case, and a rule iterating ``edges`` cannot name endpoints at all. The
       two landings — a ``source-of``/``target-of`` pair in §2.10, or leaving
       the systems on the idiom — are named and neither is specced; recorded
       as a **port blocker**. It stays open and unspecced: Amendment AG does
       not reach it, and since AG discharged D66's blocker this is the only
       one this document still carries.
   * - D79
     - §2.9, §2.12
     - A membership payload field is declared by ``deffield`` with a
       ``:member`` ``NodeType`` operand, the ``<qname>``'s first segment
       rendering the owning ``HyperedgeType`` — **not** by a new top-level
       form. Two reasons from this document's machinery: a new top-form would
       owe a new sibling digest and therefore an edit to
       :doc:`/reference/determinism-contract`'s ``ContentDigest`` composition,
       and a keyword encodes as an ``opt`` under D20 so nothing needs a new
       form tag or atom kind. One shared field namespace (duplicate =
       ``E-LOAD-001``); wrong-form read or write = ``E-LOAD-046``;
       ``:member`` on a non-hyperedge owner = ``E-LOAD-048``. One declaration
       is one *(HyperedgeType, NodeType)* pair, which is the price of keeping
       ``<qname>`` → declaration total and both checks static.
   * - D80
     - §2.12, §3.1, §2.6
     - **No fourth reference kind and no** ``memberships-of`` **query.** A
       membership is denoted by its key *(hyperedge, member)*, as a dyadic
       edge is denoted by its triple. **Alternative rejected:** a
       ``MembershipRef`` type would have dragged in a set type, a query head,
       and an ordering key for an object with no id — whose only honest order
       is the member list's, which the keyed forms already give — buying no
       expressiveness at the price of four obligations, in a chapter whose
       amendment re-seals the closure (AG (iii)).
   * - D81
     - §2.10
     - ``membership-field-of`` reads payload from two element operands plus an
       annotating ``<qname>`` — D24/D29's pattern, hyperedge first and member
       second so that one operand order serves ``members-of``, the accessor
       and the verb. **Alternative rejected:** a ``:membership`` bind-src, on
       D56's reasoning verbatim (a bind-src is a two-child ``opt``; this needs
       two element operands; and a binding resolves implicitly where this
       reference is explicit). A wrong-type referent at either operand is
       ``E-EVAL-033``; a well-typed non-membership pair is ``E-EVAL-038``; the
       accessor is a keyed lookup charged at 1 + operands (D38).
   * - D82
     - §2.8
     - ``update-membership`` writes payload of an **existing** membership,
       mirroring the other three update verbs and inheriting the range and
       I.15 disciplines. The member list stays whole-object replacement
       (D26), so ``:max-members`` keeps its single check point and VIII.9
       survives verbatim. AG (iii)'s "adds no verb" is read as the NORTH_STAR
       §0 / Article V closure list, against AG (i)'s "mutate only through
       effects" and ADR189 (iv)'s "accessor/verb surface" — the effect-position
       write is required by the amendment, not licensed against it.
   * - D83
     - §2.8, §3.9
     - Mint-time payload initialisation is **total and annotated**:
       ``(member <enum-ref> <expr> <field-init>*)``, whose field-inits are
       exactly the declared payload of that pair. The annotation supplies the
       member type §3.1 gives no reference, making completeness **static**
       (``E-LOAD-047``, at mint and at hydration alike); duplicate init is
       ``E-PARSE-041`` and a foreign qname ``E-TYPE-014``. Bare member items
       stay legal for payload-free hyperedge types, so no existing form
       changes meaning. **Alternative rejected:** partial mint with a first
       read failing ``E-EVAL-033``, because it converts a decidable authoring
       error into a runtime one.
   * - D84
     - §2.12, §3.4, §3.7
     - What the kind carries: payload types and kinds exactly as node/edge
       fields do (an intensive payload under an unweighted ``mean`` is
       ``E-TYPE-042``); memberships iterate in the member list's ruled order
       (D25, ascending member node id), introducing no new order;
       ``:max-members`` stays the only cardinality axis and the fuel bound
       stays ``Σ|members|``; payload is element **state** of the same standing
       as the other three kinds' fields, this document deliberately not
       restating the tick-hash field set that
       :doc:`/reference/determinism-contract` owns.
   * - D85
     - §2.9, §3.9
     - Scale-lattice **rungs** and ``allocate``/``aggregate`` **instances**
       are declared as ``manifest`` children (``rung``, ``adjunction``), not
       as top-level forms. **The reason is D79's verbatim**: §5.5 gives
       ``deffield``/``intrinsic``/``manifest``/``metric`` sibling digests that
       ``ContentDigest`` combines, and ``ContentDigest``'s composition belongs
       to :doc:`/reference/determinism-contract`, so a new top-form would owe
       a new sibling digest and an edit to a document this one must not reach
       into; a child of an existing form owes neither. The secondary reason is
       narrower than an earlier draft of this row claimed: **one** of the two
       standing rulings — the substrate one — is checked against
       ``:invariant`` ``ceiling`` rows, which are children of the very form a
       rung joins, so that check has a manifest referent and stays local to
       it. The weighting ruling is checked against ``deffield`` kinds and
       spans two digests, as any content-wide check does; §3.9's body states
       the split correctly and this row now matches it. Names are content-set
       unique (``E-LOAD-001``); a rung's types owe ceiling rows
       (``E-LOAD-045``); enum-ref kinds are ``E-TYPE-011`` under the class
       rule.
   * - D86
     - §3.9
     - One orientation convention serves both forms: a ``rung``'s positional
       operands are **finer first, coarser second**, its ``:via`` relation is
       directed finer → coarser, and an ``adjunction``'s two ``<qname>``\ s
       are the fields at those ends **in the rung's order**. That is what
       makes the section's ``neighbors`` reads unambiguous without a second
       annotation.
   * - D87
     - §3.9
     - ``:substrate`` obliges a rung's finer type, coarser type and ``:via``
       type each to carry ``:invariant`` (``E-LOAD-049``), which is how the
       Director's 2026-07-30 spatial-adjacency ruling becomes a property of
       the language: ``:invariant`` (D63) bars the structural verbs and
       hydration clause 3 makes hydration the only writer, so a substrate rung
       is built once from the static lookup estate and no rule rewires it. The
       flag is declared rather than inferred from the three rows, for the
       reason ``:invariant`` is itself declared.
   * - D88
     - §3.9, §3.4
     - An ``adjunction`` over an intensive field pair carries
       ``:weighted-by`` or it is ``E-LOAD-050`` — the amendment's
       intensive-aggregation rule as a load error, catching the **lattice
       that specifies** an aggregation where §3.4's ``E-TYPE-042`` catches the
       **fold that implements** one. A non-extensive weight is ``E-TYPE-043``,
       the existing code. The two checks are not redundant: a declared
       adjunction exists before any rule realises it.
   * - D89
     - §3.9, §3.7
     - An ``adjunction`` **declares, it does not execute**: no verb, no
       evaluator behaviour, no cost row (declarations are manifest-class and
       unmetered), and the grammar gives conservation **no place to be
       restated** — which is how "instances, not kinds" is enforced by
       construction. ``E-LOAD-051`` is the single fit-to-schema code
       (undeclared rung, foreign field owner, kind disagreement, misplaced
       weight); validation and diagnostics run in ascending declared-name byte
       order so two implementations report the same first failure.
   * - D90
     - §3.4, §2.12
     - A **weighted** ``mean`` over an intensive body has result kind
       **intensive** — the one cell §3.4's table left blank while stating a
       result for its four other rows. Unit algebra (``Σ(w × x) / Σ(w)`` is in
       the units of ``x``), not new mathematics, and stated in the table
       because the ``*``/``/`` bullet deliberately rejects the decomposition
       (extensive ÷ extensive is ``E-TYPE-040``). Recorded on adversarial
       verification of the AG sections, which caught §2.12's worked shape
       folding ``sum`` over exactly this value — ``E-TYPE-041``, and the
       recorded variance error itself; the example now folds ``max``, whose
       row is kind-neutral over any body.
   * - D91
     - §6.1, §1.6
     - Scope split between the vector-file format and canonical content:
       ``vector`` forms are reader-parsed **fixtures**, never encoded under
       §5 or hashed into a content digest, so §1.6's closed flag table
       (D42) governs content forms only, and ``:graph <graph-lit>?`` in a
       vector form — optional-valued, a shape the content dichotomy has no
       room for — collides with but does not amend ``:graph``'s flag
       classification. Surfaced by the PR #480 re-verification: the
       implementation's closed flag table would mis-encode a ``vector``
       form if one ever reached the canonical encoder, so the encoder now
       has license to treat that as a caller error. Re-spelling the vector
       keywords was rejected as churn in a fixture format §5 never touches.
   * - D92
     - §7, §1.1, §1.2, §1.4, §2.1, §2.11, §6.1
     - **The grammar is consolidated as an INCLUDED ASSET, not a second
       home.** ``docs/reference/bsl.ebnf`` collects every production of §§1,
       2 and 6.1 and is part of this document by ``literalinclude`` (§7); it
       **collects and does not amend**, so on any divergence the §1/§2/§6
       text wins and the appendix is the defect. The precedence trigger is
       the section **text**, not merely a section production: **nine**
       productions are collected from PROSE rather than from a code block
       (``Char``, ``whitespace``, ``comment``, ``delimiter``, ``operator``,
       ``escape``, ``intrinsic-name``, ``type-name``, ``vector-file``), and
       a production-only trigger would leave exactly those nine adjudicating
       themselves. The dialect is **W3C EBNF**
       (the XML 1.0 §6 notation), chosen because §1.4 and §2.1 already write
       their productions in its operator set — collecting them is
       transcription, where ISO 14977 would have meant translating a
       normative text into comma-concatenation and ``{ }`` repetition:
       transcription risk bought for nothing. Two notation-level deviations
       are stated in the file and are spellings rather than changes —
       nonterminals lose §2's angle brackets, and §1.4's ``"0" … "9"``
       ranges become W3C character classes. **Two under-determined points
       are collected with the reference implementation's reading and
       flagged** — not "recorded instead of chosen", since a production
       needs a right-hand side and writing one is a choice: ``<type-name>``
       has no §1.4 atom class and no capitalized spelling is lexable, so the
       lowercase-``symbol`` reading is taken and **§2.11's own worked
       example** (``:type Coefficient``) is recorded as cutting against it;
       and §6.1's ``:graph`` / ``:fuel-used`` / ``:cas`` are written with
       ``?`` binding to the value, which makes the keywords themselves
       mandatory against §6.1's own prose, so the production is transcribed
       verbatim with the divergence named. Both repairs belong to the
       Phase-1 review, not to an appendix. A derived, non-normative
       tree-sitter grammar lives at ``tools/tree-sitter-bsl``; a sync guard
       (``tests/unit/reference/test_bsl_grammar_sync.py``) requires every
       §5.2 form tag and every ``::=`` production of §§1/2/6.1 to appear in
       the appendix, so the collection cannot silently fall behind the
       sections it collects.
   * - D93
     - §7, §2.9, §6.1
     - **The** ``.bscn`` **scenario dialect is out of the appendix's scope,
       and its** ``deffield`` **is a DIFFERENT form sharing a name with
       §2.9's.** The Rust reference implementation's scenario loader
       (``rust/crates/babylon-bsl/src/scenario.rs``) reads
       ``(scenario …)`` files containing ``(node …)``, ``(edge …)`` and
       ``(deffield <qname> <type-symbol> <kind-symbol>)`` — the last one
       **positional**, where §2.9's ``deffield`` takes ``:type`` and
       ``:kind`` keyword options. No section of this document specifies any
       of those forms. The scope ruling follows D91's fixture/content split
       rather than inventing a second one: a scenario file is a **fixture**
       that hydrates a world (§3.9's hydration contract governs what it may
       do), not canonical content: §5 never encodes it and §7's appendix
       never collects it. **This row records the shape conflict;
       it does not resolve it.** Two repairs are available and both are the
       Director's: rename the scenario form so one name does not denote two
       shapes, or give the scenario format a chapter of its own here. Until
       one is chosen, the conflict is written down in a normative place
       rather than living only in ``tools/tree-sitter-bsl``, which this
       document declares normative for nothing. Recorded on adversarial
       verification of PR #485.

See Also
----------

- :doc:`/reference/determinism-contract` — the constitutional hash catalog,
  the three float-tolerance regimes, and (from Program 27 Phase 0) the
  tick-hash field set, ``ContentDigest`` composition, and ``rules_hash``'s
  place in it. This document defines the bytes ``rules_hash`` covers; that one
  defines what it is compared against.
- :doc:`/reference/precision` — the quantization Gatekeeper Pattern
  (``SnapToGrid``, ``1e-5``), the drift-prevention mechanism BSL's fixed-point
  Currency lane partially supersedes.
- :doc:`/reference/configuration` — ``GameDefines`` and ``defines.yaml``, the
  coefficient environment that ``:const`` bindings read.
- :doc:`/reference/topology` — ``NodeType``/``EdgeType``, the closed graph
  vocabulary ``<enum-ref>`` draws on.
- :doc:`/reference/error-codes` — the engine's existing error-code estate; the
  ``E-LEX``/``E-PARSE``/``E-TYPE``/``E-LOAD``/``E-EVAL`` families defined here
  are registered there when Phase 1 lands code.
- ``docs/superpowers/specs/2026-07-28-program-27-refoundation-design.md`` —
  the Director-approved design; §5 (the language), §6 (the kernel), §8
  (correctness), §9 (error handling and determinism), §10 (sequencing).
- ``CONSTITUTION.md`` III.11 (Loud Failure), III.12 (Behavioral Contracts,
  Amendment Q), III.8 (Aleksandrov Test), **Amendment AE clause (vi)**
  (Amendment D — native hyperedge, ratified v3.0.0), II.9 (the strictly dyadic
  morphism layer that coexists with it), VIII.9 (the clique-expansion
  anti-pattern the ruling discharges structurally), and **Amendment AG**
  (attributed membership and lattice instances, ratified v3.2.0, recorded in
  ``ai/decisions/ADR189_amendment_ag_attributed_membership_lattice_instances.yaml``)
  — the amendment this document's fourth revision specifies.
- ``ai/_inbox/amendment-d-analysis-p27.md`` — the Phase-0 Amendment D analysis
  (PR #353); §9 records the Director's ruling and sub-rulings D-1…D-7 that
  §2.6, §2.8 and §3.7 of this document implement.
