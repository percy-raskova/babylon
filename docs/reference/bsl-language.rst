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
A keyword in value position is ``E-PARSE-010``.

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
   * - ``:kind``
     - ``intensive`` | ``extensive``
     - Per-field intensivity declaration, on ``deffield`` forms only (§3.4).
   * - ``:type``
     - type name
     - Scalar type, on ``deffield``/``intrinsic`` forms.
   * - ``:weight``
     - expression
     - The mandatory explicit weight term of a weighted aggregation (§3.4).
   * - ``:strength``
     - expression
     - Edge strength operand of ``add-edge``.
   * - ``:after`` / ``:before``
     - symbol
     - Ordering anchors (§2.8). A raw position float is not expressible.
   * - ``:params`` / ``:returns`` / ``:cost``
     - see §2.7
     - Intrinsic declaration fields.
   * - ``:ceiling``
     - integer
     - Declared cardinality ceiling, on ``manifest`` forms (§3.7).
   * - ``:max-members``
     - integer
     - Declared **member-count** ceiling of one hyperedge type, on the
       ``manifest`` ``ceiling`` rows whose ``<enum-ref>`` is a
       ``HyperedgeType`` member (§3.7). Mandatory there, illegal elsewhere.

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

A content set is the union of all files under the declared content roots. File
boundaries and file names carry **no semantics**: the same forms split across
different files produce the same ``rules_hash`` (§5.5). Duplicate rule ids,
duplicate field declarations, or duplicate intrinsic declarations across the
content set are ``E-LOAD-001``.

2.3 Rules
~~~~~~~~~~~

.. code-block:: text

   <rule>     ::= "(" "rule" <qname>
                      ":material-basis" <string>
                      ":fuel" <int-lit>
                      <anchor>?
                      <bindings>
                      <when>?
                      <effects>
                  ")"

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

2.4 Conditions
~~~~~~~~~~~~~~~~

.. code-block:: text

   <cond>   ::= <bool-lit>
              | "(" "and" <cond>+ ")"
              | "(" "or"  <cond>+ ")"
              | "(" "not" <cond> ")"
              | "(" <cmp> <expr> <expr> ")"
              | "(" "exists" <query> <cond>? ")"
              | "(" "forall" <query> <cond> ")"

   <cmp>    ::= "<" | "<=" | ">" | ">=" | "=" | "!="

``and`` and ``or`` are variadic with at least one operand; ``(and)`` and
``(or)`` are ``E-PARSE-021`` (there is no implicit identity element — the same
correction as the empty precondition set).

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

   <bind-opt>  ::= ":optional" | ":default" <literal>

A binding names a value the rule reads. **A plain (non-``:optional``) declared
binding that is unbound at load is a load error** (``E-LOAD-010``) — the
opt-in to absence is content, not a test list.

``:field`` reads a declared field of ``self``'s node type unless the qualified
name's first segment names a different node type, in which case it is only
legal inside a fold body over that type (``E-TYPE-010``). ``:const`` reads a
coefficient from the defines environment. ``:metric`` reads a registered
graph-level metric; an unregistered metric name is ``E-LOAD-011`` — never
``0.0`` (§6.3). ``:tick`` binds the current tick as ``Int``.

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

2.6 Queries
~~~~~~~~~~~~~

.. code-block:: text

   <query>      ::= "(" "nodes" <enum-ref> <node-pred>? ")"
                  | "(" "edges" <enum-ref> <edge-pred>? ")"
                  | "(" "neighbors" <expr> <enum-ref> <direction> ")"
                  | "(" "hyperedges" <enum-ref> <hedge-pred>? ")"
                  | "(" "members-of" <expr> <enum-ref> ")"
                  | "(" "hyperedges-of" <expr> <enum-ref> ")"

   <direction>  ::= ":out" | ":in" | ":any"
   <node-pred>  ::= <cond>
   <edge-pred>  ::= <cond>
   <hedge-pred> ::= <cond>

The ``<enum-ref>`` operand of ``nodes`` must be a ``NodeType`` member, of
``edges``/``neighbors`` an ``EdgeType`` member, and of
``hyperedges``/``members-of``/``hyperedges-of`` a ``HyperedgeType`` member
(``E-TYPE-011``). Predicates refer to the candidate element as ``it``.

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
     - Nodes reachable from the operand across that ``EdgeType``.
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

**[draft ruling — Phase 1 review]** The same rule applies *inside* a
hyperedge: ``members-of`` yields members in ascending node-id byte order, and a
hyperedge's **declared** member order — the order ``add-hyperedge`` (§2.8) or a
scenario hydration listed them in — is never observable. A member list is a
set, not a sequence.

2.7 Expressions, intrinsics, folds, guards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   <expr>      ::= <literal> | <symbol> | <enum-ref>
                 | "(" <arith> <expr> <expr> ")"
                 | "(" <intrinsic-name> <expr>* ")"
                 | "(" "if" <cond> <expr> <expr> ")"
                 | <fold>
                 | <accessor>                       ; §2.10

   <arith>     ::= "+" | "-" | "*" | "/"
   <literal>   ::= <int-lit> | <scaled-lit> | <bool-lit>

   <fold>      ::= "(" "fold" <fold-op> <query> <expr> ( ":weight" <expr> )? ")"
   <fold-op>   ::= "sum" | "mean" | "min" | "max" | "count"

Arithmetic is strictly binary; ``(+ a b c)`` is ``E-PARSE-040``. This keeps
the reduction order explicit in the source rather than implied by a
left-fold convention — a cross-language float trap the design document names.

**Guards** are ``(if <cond> <a> <b>)`` in expression position and
``(guard <cond> <effect-item>+)`` in effect position (§2.8). Both branches of
``if`` must have the same static type (``E-TYPE-020``).

**Intrinsic calls** are ordinary forms whose head is a symbol declared in the
intrinsic table. Transcendentals (``sigmoid``, ``exp``, ``log``, ``tanh``,
``sqrt``, ``entropy``) and ``round-half-even`` are **never** language
primitives — they exist only as named intrinsics with pinned deterministic
implementations. BSL cannot define an intrinsic; ``intrinsic`` forms only
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

**Folds** are the only iteration construct. There is no recursion, no
``while``, no ``loop``, no user-defined function, and no way to name a rule
from inside a rule. Totality is therefore syntactic, and the static bound of
§3.7 is computable.

2.8 Effects — the typed structural verbs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   <effect-item> ::= <verb> | "(" "guard" <cond> <effect-item>+ ")"

   <verb> ::= "(" "update-node"  <expr> <qname> <update-op> ")"
            | "(" "update-edge"  <expr> <qname> <update-op> ")"
            | "(" "add-node"     <enum-ref> <expr> <field-init>* ")"
            | "(" "remove-node"  <expr> ")"
            | "(" "add-edge"     <enum-ref> <expr> <expr> ":strength" <expr>
                                 <field-init>* ")"
            | "(" "remove-edge"  <enum-ref> <expr> <expr> ")"
            | "(" "add-hyperedge"    <enum-ref> <expr> <members> <field-init>* ")"
            | "(" "remove-hyperedge" <expr> ")"
            | "(" "emit"         <enum-ref> <payload-item>* ")"

   <update-op>   ::= "(" "add"   <expr> ")"
                   | "(" "sub"   <expr> ")"
                   | "(" "set"   <expr> ")"
                   | "(" "scale" <expr> ")"
   <members>     ::= "(" "members" <expr>+ ")"
   <field-init>  ::= "(" <qname> <expr> ")"
   <payload-item>::= "(" <symbol> <expr> ")"

The four ``<update-op>`` forms are exactly today's four-operation effect enum
— ``add`` = ``increase``, ``sub`` = ``decrease``, ``set`` = ``set``,
``scale`` = ``multiply``. Of the **eight** structural verbs, **five** are the
addition the design document's §6.4 audit found necessary (20 of 39 system
modules mutate graph structure); **two** — ``add-hyperedge`` and
``remove-hyperedge`` — are what the Amendment D ruling adds, since if a
hyperedge is a first-class object, minting and retiring one is a first-class
verb; and **one** — ``update-edge`` — is what R9 chapter C2 adds, below.

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
names its member nodes. The grammar's ``<expr>+`` makes a **zero-member
hyperedge unexpressible**; the upper end is the declared ``:max-members``
ceiling of §3.7, checked statically.

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

**[draft ruling — Phase 1 review]** *Membership changes are whole-hyperedge
replacement.* There is no ``add-member``/``remove-member`` verb and no
``update-hyperedge``: a rule that changes a formation's roster emits
``(remove-hyperedge h)`` and then ``(add-hyperedge …)`` in one effect list,
applied in source order (below). This keeps the member-count check at a single
point (§3.7) and makes a partially-mutated hyperedge unrepresentable. The cost
is stated rather than hidden: **per-membership payload** (the
role/strength/visibility fields today's Python ``CommunityMembership`` carries)
and **mutation of a hyperedge's own declared fields** are not expressible in
this revision. Both are Phase-1 review items; neither is a silent omission.

``emit``'s ``<enum-ref>`` is an ``EventType`` member; payload items are
name/expression pairs. There is no string interpolation in a payload.

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
                  ")"

   <manifest> ::= "(" "manifest" <symbol> <ceiling>+ ")"
   <ceiling>  ::= "(" "ceiling" <enum-ref> ":ceiling" <int-lit>
                      ( ":max-members" <int-lit> )? ")"

A ``ceiling`` row's ``<enum-ref>`` is a ``NodeType``, ``EdgeType`` or
``HyperedgeType`` member. ``:max-members`` is **mandatory** on a
``HyperedgeType`` row and **illegal** on the other two; either mismatch is
``E-LOAD-042``. The semantics of both numbers are §3.7's.

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
which is a *total* order only if no two edges share that triple, and §2.8
already makes "adding an edge that already exists" ``E-EVAL-031`` and a
ceiling-violating hydration ``E-LOAD-041``. Parallel edges of one type between
one ordered pair are therefore not representable, and "the edge between a and
b of type T" denotes at most one element. When it denotes none, that is
``E-EVAL-034`` — the accessor never yields an absent reference and never
degrades to a no-op write, which is what would happen if ``update-edge`` had
been given endpoint operands and left to skip quietly.

.. code-block:: scheme

   (update-edge (edge-between EdgeType/SOLIDARITY self other)
                solidarity/strength (scale 0.95c))

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
       element-position operands of §2.8's verbs.
   * - ``NodeSet`` / ``EdgeSet`` / ``HyperedgeSet``
     - the result of a ``<query>``
     - Only consumable by ``fold``, ``exists``, ``forall``.
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
  the implicit ``<edge-type>/strength`` field is ``extensive`` (§2.9);
  ``:const`` and ``:metric`` bindings are kind-neutral
  **[draft ruling — Phase 1 review]** (a coefficient has no extent; a graph
  metric's kind is declared on the metric registration, §2.11);
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
       extensive is ``E-TYPE-043``.
   * - ``min`` / ``max``
     - any
     - Kind-neutral operation. Result carries the body kind.
   * - ``count``
     - any
     - Result ``Int``, extensive.

This is the narrow, true form of the law: it rejects the unweighted mean of an
intensive field across classes or space (the recorded variance error), and it
does **not** reject correct weighted code.

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
   bound(rule)                  = cost(cond of <when>) + Σ cost(effect-items)

**[draft ruling — Phase 1 review, R9 chapters C1–C2]** *Accessors are keyed
lookups, not iterations.* Every §2.10 accessor charges a variable-reference
base of 1 plus its operands and is **never multiplied by a ceiling**, because
none of them ranges over a set: ``field-of`` reads one element's one field, and
``edge-between`` resolves one ``(source, target, type)`` key. The static bound
of a rule using them is therefore the same shape as before — the accessors add
constants, and only the iteration constructs (``fold``, ``exists``/``forall``,
and the chapter-C5/C6 forms) carry ceiling factors. That is what keeps the
Power-of-10 Rule 2 claim static as the accessor set grows.

**[draft ruling — Phase 1 review]** *Query operand charging* (implementation-
discovered, 2026-07-30, Phase 1 Task 13). The ``cost(query)`` row names only
the element predicate, but three query heads (``neighbors``, ``members-of``,
``hyperedges-of``) also carry an *operand expression* that §4.5 charges when
it is evaluated; omitting it would make the static bound under-count the
runtime meter — the loud-failure inversion. The bound checker therefore reads
the row as ``1 + Σ cost(children)``: identical for the predicate queries
(enum-refs and direction keywords cost 0), and additionally charging the
operand where one exists.

``ceiling(query)`` is the manifest ceiling of the queried type; for
``neighbors`` it is the ceiling of the queried edge type
**[draft ruling — Phase 1 review]** (a per-node degree ceiling would be
tighter and is a Phase-1 review item). For the three hyperedge queries
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
the fuel meter. Effects are applied only after the whole condition has been
evaluated. **A rule can never observe its own effects**, and rules within one
system position observe the same pre-state.

Rules at the same anchor position evaluate in **ascending rule-id byte order**
**[draft ruling — Phase 1 review]**, and their effects apply in that same
order. File order and load order are never observable.

4.3 Arithmetic
~~~~~~~~~~~~~~~~

- Binary64 operations are the IEEE-754 **basic** operations only:
  addition, subtraction, multiplication, division, and comparison, each
  correctly rounded round-to-nearest-even. These reproduce bit-exactly across
  conforming implementations.
- Fixed-point operations are exact integer operations at the widths of §3.2.
- **No transcendental is a language operation.** ``exp``, ``log``, ``sigmoid``,
  ``tanh``, ``sqrt`` and ``entropy`` are named intrinsics whose implementations
  are pinned by the kernel and validated by golden vectors with written
  tolerance derivations. Whether those implementations are polynomial
  approximations or a pinned deterministic libm is an **open Phase-1 Director
  ruling** (design §13 item 2) and is deliberately not decided here.
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
declared ``:fuel`` and decrements. Reaching or passing zero is ``E-EVAL-040``,
which aborts the tick (§4.6) — it never truncates a fold or returns a partial
result.

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
       ``:max-members``, a member list over that ceiling, anchor interleaved
       into the Material Base partition, kernel/content disagreement.
   * - Evaluation
     - ``E-EVAL-0xx``
     - During a tick — checked-arithmetic failure, range violation at a store,
       non-finite result, empty aggregate, edge-mode violation, hyperedge type
       mismatch, fuel exhaustion.

**Load-time errors** report the offending file, line, column, form, and code,
and reject the whole content set — there is no partial load and no "skip the
bad rule" mode.

**Evaluation errors** abort the tick. The whole per-tick envelope transaction
rolls back; there are no partial commits (design §9). The error carries the
rule id, the AST path to the offending node, the binding environment, and the
fuel remaining. An implementation must not convert an evaluation error into a
default value, a skipped effect, or a log line.

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
``members-of``, ``hyperedges-of``, ``field-of``, ``edge-between``, ``guard``,
``update-node``, ``update-edge``,
``add-node``, ``remove-node``, ``add-edge``, ``remove-edge``,
``add-hyperedge``, ``remove-hyperedge``, ``members``,
``emit``, ``add``, ``sub``, ``set``, ``scale``, ``anchor``, ``deffield``,
``intrinsic``, ``manifest``, ``ceiling``), plus the synthetic tag ``opt`` for a
keyword option.

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
``intrinsic`` and ``manifest`` forms are hashed the same way into their own
digests, which ``ContentDigest`` combines
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

Conformance vectors are themselves BSL content — homoiconic, diffable, and
hashable. A vector file is a sequence of ``vector`` forms:

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
4. **Kind rule** — the five rows of §3.4's table, accepting and rejecting.
5. **Fuel** — the static bound for a fold at a declared ceiling; a rule
   rejected at load for exceeding its budget; a rule exhausting fuel at
   evaluation; per-vector ``:fuel-used``.
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
    (``E-PARSE-041``) and one owning off the wrong type (``E-TYPE-014``); and
    an ``update-edge`` whose referent is of another edge type
    (``E-EVAL-033``).

Families 10 and up are the R9 spec chapters' (the chapter letters cite
``reports/bsl-gap-analysis-2026-08-10.md`` §7). Two obligations are stated
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
     - ``E-PARSE-0xx`` at parse
     - §2.7 (``<fold-op>`` is a closed five-member terminal set)
   * - unknown comparison operator → ``False``
     - ``E-PARSE-0xx`` at parse
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
       extensive`` is a type error.
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
       replacement, so per-membership payload and hyperedge-field mutation are
       **not expressible in this revision** and are review items.
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
  anti-pattern the ruling discharges structurally).
- ``ai/_inbox/amendment-d-analysis-p27.md`` — the Phase-0 Amendment D analysis
  (PR #353); §9 records the Director's ruling and sub-rulings D-1…D-7 that
  §2.6, §2.8 and §3.7 of this document implement.
