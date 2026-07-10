Determinism Contract
=====================

The language-agnostic, byte-level specification of every constitutional hash
in Babylon. This document exists so that a reimplementation of the engine in
another language could reproduce these hashes without reading the Python —
the **rewrite test** of Constitution III.12 ("Behavioral Contracts",
Amendment Q, corollary (a); see ``CONSTITUTION.md``). It is a reference document: it describes what
the current implementation *does*, byte for byte, not what an idealized
implementation *should* do. Where the implementation's behavior surprises its
own naming or docstrings, this document says so explicitly (see the
*Known Discrepancies* section below) rather than papering over the gap.

.. contents:: On this page
   :local:
   :depth: 2

Scope: What "Deterministic" Guarantees
---------------------------------------

Babylon makes two different determinism claims, and conflating them is a
category error the codebase itself warns against (Constitution III.7,
``CONSTITUTION.md:250``):

**Intra-implementation (byte-identical replay).** Given the same CPython
interpreter, the same platform libm, the same random seed, and the same
input sequence, re-running a tick produces byte-identical output. This holds
because:

- IEEE-754 basic arithmetic (``+``, ``-``, ``*``, ``/``, comparisons) is
  specified to produce the same bit pattern on any conforming
  implementation, so pure arithmetic on ``float`` is reproducible across
  machines.
- CPython's ``random`` module (Mersenne Twister) is itself deterministic
  given a seed, and the engine's RNG usage is threaded through explicit
  seeds (Constitution III.7 / the worktree's ``rng_seed`` convention) rather
  than reseeded from wall-clock time.
- Dict and set iteration in CPython 3.7+ is insertion-ordered for dicts
  (sets remain unordered by the language spec, but this codebase's hot
  paths canonicalize via ``sorted()`` before hashing — see below).

**What does NOT survive across implementations, or even across libm
versions on the same CPU architecture:** the transcendental functions used
in the survival-calculus sigmoids (``exp``, ``log``) and similar functions
are **not** bit-reproducible across different libm implementations (glibc
vs musl vs a from-scratch reimplementation in Rust/Go/etc.), because IEEE-754
does not mandate correctly-rounded transcendentals — different libraries
trade the last 1-2 ULPs for speed differently. A byte-identical
``defines_hash`` or ``tick_commit`` row is therefore **not** a claim that a
Rust or Go reimplementation would produce the identical hash; it is a claim
that *this* Python engine, run twice on *this* machine, reproduces itself.

Cross-implementation validation is necessarily **tolerance-bounded checkpoint
comparison**, not hash equality — see *Float and Tolerance Policy* below.

Catalog of Constitutional Hashes
----------------------------------

Three genuinely different hashes exist in the codebase, all currently named
some variant of "determinism hash." They are **not interchangeable** and, as
of this writing, **not even consistent with each other's docstrings** inside
the same code path — see *Known Discrepancies* below. This section specifies each
one's exact byte-level construction.

``defines_hash`` — GameDefines fingerprint
+++++++++++++++++++++++++++++++++++++++++++

**Purpose:** detect when the tunable-coefficient space (``GameDefines`` /
``defines.yaml``) has moved between a checkpoint baseline's authoring time
and a comparison run. Per Constitution III.7, a ``defines_hash`` mismatch
alone is **input-hash drift** — expected and benign, resolved by
regenerating the baseline — as distinct from **behavioral drift** (a
checkpoint value moved), which is the actual failure the ``qa:regression``
gate exists to catch.

**Computed by:** ``hash_defines()``, ``tools/regression_test.py:131-141``.

.. code-block:: python

   def hash_defines(defines: GameDefines) -> str:
       json_str = defines.model_dump_json(indent=None)
       return hashlib.sha256(json_str.encode()).hexdigest()[:16]

**Inputs:** one ``GameDefines`` instance (the full 39-category coefficient
tree, ``src/babylon/config/defines/_assembler.py:81``) as produced by the
active scenario factory (e.g. ``create_imperial_circuit_scenario()``) after
any ``defines_overrides`` from ``tools/regression_test.py``'s ``SCENARIOS``
table have been applied via ``inject_parameter``.

**Canonical byte serialization:**

- Produced by **Pydantic v2's** ``BaseModel.model_dump_json(indent=None)``
  (pydantic-core's Rust serializer), **not** Python's stdlib ``json.dumps``.
  This distinction matters because the two disagree on whitespace and key
  ordering behavior — see the worked example below.
- **Key ordering:** model field **declaration order**, recursively, at every
  nesting level. Pydantic does **not** sort keys alphabetically. The order
  is therefore whatever order the fields are declared in
  ``GameDefines`` and each of its 39 sub-models
  (``src/babylon/config/defines/_assembler.py:125-141`` for the top level).
  A reimplementation MUST reproduce this exact field order, category by
  category, field by field, to match this hash — sorting alphabetically
  produces a *different*, equally valid-looking, but non-matching hash.
- **Separators:** compact — no space after ``,`` or ``:`` (i.e.
  ``{"a":1,"b":2}``, not ``{"a": 1, "b": 2}``). This is pydantic-core's
  default and differs from stdlib ``json.dumps``'s default (which inserts a
  space after each separator).
- **Unicode:** pydantic-core's JSON serializer emits UTF-8 text without
  escaping non-ASCII characters (no ``ensure_ascii``-style ``\\uXXXX``
  escaping is applied by default); ``GameDefines`` fields are all numeric or
  short ASCII identifiers in practice, so this rarely bites, but a
  reimplementation should not assume ASCII-only escaping.
- **Float formatting:** each float is emitted via the shortest
  round-trippable decimal representation for that IEEE-754 double (the same
  algorithm family Python's own ``repr(float)`` uses, e.g. ``9.8`` stays
  ``9.8``, not ``9.8000000000000007``). Integers that happen to be typed as
  ``int`` fields (many ``GameDefines`` fields are ``int``, e.g.
  ``crisis_period_ticks``) are emitted as bare integers with no decimal
  point, which also affects the byte stream — an ``int`` field and a
  ``float`` field holding the same numeric value do **not** serialize
  identically.
- **Hashing:** UTF-8 encode the JSON string, SHA-256, then **truncate to
  the first 16 hex characters** (64 bits of the 256-bit digest). This
  truncation is a collision-risk tradeoff the code accepts for a
  human-scannable fingerprint — it is not cryptographically full-strength,
  and is not intended to be (its only job is change detection between a
  baseline and a re-run, not adversarial collision resistance).

**Chaining:** none — a fresh, independent hash per ``GameDefines`` snapshot;
no dependency on any prior hash.

**Storage location:** the ``defines_hash`` field of each
``tests/baselines/<scenario>.json`` file
(``tools/regression_test.py:299-311``), written by ``generate`` and read
back by ``compare`` (``tools/regression_test.py:473-512``).

**What drift means:** ``compare_baselines()`` treats a ``defines_hash``
mismatch as a **``WARNING``-prefixed diff, not a failure**
(``tools/regression_test.py:420-425,441``) — ``passed = len([d for d in
diffs if not d.startswith("WARNING")]) == 0``. A coefficient change that
moves ``defines_hash`` but leaves every checkpoint value and outcome
unchanged is a **pass**. This is a real, verified precedent: at the time of
writing, all 5 scenarios in ``tests/baselines/`` carry a ``defines_hash``
that is reproducible from the live code (see the worked example below) and matches
their committed baseline files exactly — there is currently no drift to
observe, but the mechanism has fired benignly before (see
``specs/102-gamma-shocks/proof-2R-baseline-regen.md``, Part 5: "Track A ...
drifted on all 5 scenarios — ``defines_hash`` only. ... Behavior is
byte-identical; only the ``GameDefines`` fingerprint moved.").

``tick_commit.determinism_hash`` — per-tick commit marker
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

**Purpose (as implemented):** an idempotency / commit-identity marker for
the ``tick_commit`` table (spec-089, migration
``src/babylon/persistence/migrations/0029_tick_commit.sql``). Its actual job
is to let crash-recovery code detect **marker shadowing** — an earlier
placeholder envelope (e.g. the tick-0 initialization bootstrap,
``src/babylon/persistence/postgres_initialization.py:603``, which writes a
literal ``"0" * 64`` placeholder) silently winning the
``(session_id, tick)`` primary key via ``ON CONFLICT DO NOTHING`` before the
bridge's real tick-0 envelope arrives. See
``_verify_tick0_commit_marker()``, ``src/babylon/engine/headless_runner/runner.py:1267-1313``,
which reads the marker back and compares it only to the runner's own
just-computed identity string plus the expected hex-row count and checkpoint
flag — it does **not** compare it to anything derived from the tick's actual
computed world state.

**Computed by:**
``src/babylon/engine/headless_runner/runner.py:1357-1359`` (tick 0) and
``:1395-1397`` (tick ≥ 1):

.. code-block:: python

   determinism_hash_t0 = hashlib.sha256(
       f"{session_id}:0:{config.random_seed}".encode()
   ).hexdigest()
   # ... per subsequent tick:
   determinism_hash = hashlib.sha256(
       f"{session_id}:{tick}:{config.random_seed}".encode()
   ).hexdigest()

**Inputs:** the session UUID, the tick number, and the run's RNG seed —
formatted as an f-string ``"{session_id}:{tick}:{config.random_seed}"`` and
UTF-8 encoded. **No world state, no player actions, and no engine output of
any kind enter this hash.** Two ticks with identical ``(session_id, tick,
seed)`` produce the identical hash regardless of what the engine actually
computed for that tick — this hash cannot, by construction, detect a replay
that diverged in its computed values. See *Known Discrepancies* below.

**Canonical byte serialization:** Python f-string interpolation of three
values (a ``uuid.UUID``'s ``str()`` form — canonical 36-character hyphenated
lowercase hex, e.g. ``"4ad75b08-0258-48a4-a29a-61cab92d7d13"`` — a decimal
``int``, and a decimal ``int``), joined with literal ``:``  characters, then
``str.encode()`` (UTF-8), then SHA-256, **full 64 hex-character digest, no
truncation**.

**Chaining:** **none in the cryptographic sense.** Despite the migration
comment calling this "the queryable Constitution-III.7 hash chain"
(``src/babylon/persistence/migrations/0029_tick_commit.sql:9``), each row's
hash does **not** incorporate the previous tick's hash (there is no
``H_n = H(H_{n-1} || data_n)`` construction anywhere in this codebase). "Chain"
here means only: one row per tick, forming a **dense tick spine** — the
``tick_commit`` table is the authoritative source for "which ticks actually
committed," consumed by the fill-forward ``v_*_asof`` views
(``src/babylon/persistence/migrations/0030_views_current.sql``) and by
``get_last_committed_tick()`` (``_spec_062.py:359-386``) for crash-recovery
resumption. A reimplementation reproducing "the tick_commit chain" needs to
reproduce this row-per-tick marker sequence and its idempotency semantics,
not a Merkle-style hash chain.

**Storage location:** one row per ``(session_id, tick)`` in the ``tick_commit``
table (``0029_tick_commit.sql:16-24``), written inside the same Postgres
transaction as the tick's other envelope rows
(``src/babylon/persistence/postgres_runtime/_spec_062.py:341-356``), with
``ON CONFLICT (session_id, tick) DO NOTHING`` for crash-retry idempotency.

**What drift means:** this hash is **never compared across runs or across
sessions** anywhere in the codebase (a session-scoped identity string can
never match a different session's identity string by construction, since
``session_id`` is a fresh UUID per run). The established precedent
(``specs/102-gamma-shocks/proof-2R-baseline-regen.md``, Part 4) is explicit
about this: *"The ``t_commit`` / conservation ``determinism_hash`` chains
are **not** used here — spec-102's proof already established they embed
``session_id`` and can never match across runs; comparing persisted
**values** is the direct, session-id-free equivalent (same method spec-102
Part 2 adopted)."* Cross-run determinism verification in this codebase is
therefore done by a **Postgres ``EXCEPT`` row-diff** over the persisted
value tables (``dynamic_consciousness_state``, ``v_hex_state_asof``, etc.)
between two independent runs sharing a seed — not by hash comparison. A
reimplementation's test harness should adopt the same pattern: don't try to
reproduce this hash across sessions; diff the persisted values instead.

``conservation_audit_log.determinism_hash`` — the III.7 content hash
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

**Purpose:** this is the hash that actually matches Constitution III.7's
literal definition — *"a deterministic SHA-256 hash of its inputs (World
state + player actions + random seed)"* (``CONSTITUTION.md:250``) — because
it is the only hash in the codebase whose bytes depend on the tick's
computed content. This document identifies it with **"the III.7 tick hash"**
named in Amendment Q corollary (a) (``CONSTITUTION.md:268``); no source
comment uses that exact phrase, so this is this document's own reasoned
mapping, stated explicitly as such.

**Computed by:** ``compute_determinism_hash()``,
``src/babylon/persistence/conservation_audit.py:70-111``:

.. code-block:: python

   def compute_determinism_hash(
       *, tick: int, rng_seed: int, hex_rows: Iterable[Any],
       action_list: Iterable[Any] | None = None,
   ) -> str:
       sorted_hex = sorted(hex_rows, key=_h3_key)
       payload = {
           "tick": tick,
           "rng_seed": rng_seed,
           "hex_state": [_to_jsonable(r) for r in sorted_hex],
           "actions": [_to_jsonable(a) for a in (action_list or [])],
       }
       canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
       return hashlib.sha256(canon.encode("utf-8")).hexdigest()

**Inputs, as actually wired in the live headless-runner path**
(``src/babylon/engine/headless_runner/bridge.py:544-549``): ``tick``, the
session's fixed ``rng_seed``, and ``hex_rows=hex_frame`` — the **full
per-tick hex checkpoint frame** (every hex, restamped to the current tick;
``bridge.py:492``), not the delta actually persisted to ``dynamic_hex_state``.
``action_list`` is **never passed** at this call site (it defaults to
``None`` → treated as an empty list) — player/organization actions do not
currently enter this hash in the wired path, even though III.7's prose names
them as an input. "World state" here is narrower than the full
``WorldState`` model: only the hex economic frame (``c``, ``v``, ``s``,
``k``, the three substrate stocks, ``internet_access_pct``,
``surveillance_coupling`` plus identity/spatial keys — the 15 fields of
``DynamicHexState``, ``src/babylon/persistence/hex_state.py:20-53``) is
hashed; county-resolution state (consciousness, demographics, employment,
relationships) and national/economy aggregate state are not part of this
payload.

**Canonical byte serialization:** stdlib ``json.dumps``, **not**
pydantic's serializer (contrast with ``defines_hash`` above):

- ``sort_keys=True`` — **alphabetical** key order, applied **recursively**
  to every nested dict, including inside each hex row's ``model_dump(mode="json")``
  output. This is the opposite convention from ``defines_hash``'s
  declaration-order rule; a reimplementation must sort keys here and must
  **not** sort keys there.
- ``separators=(",", ":")`` — same compact convention as ``defines_hash``
  (no spaces).
- ``default=str`` — any object stdlib ``json`` cannot natively serialize
  falls back to ``str(obj)``. In practice this rarely fires because
  ``_to_jsonable()`` (``conservation_audit.py:114-120``) pre-converts
  Pydantic models via ``.model_dump(mode="json")`` (which itself renders
  ``UUID`` fields as their canonical hyphenated string form) before they
  reach ``json.dumps``.
- **Row ordering:** ``hex_rows`` are explicitly sorted by ``h3_index``
  (string comparison) before serialization
  (``sorted(hex_rows, key=_h3_key)``, ``conservation_audit.py:103``)
  specifically because Postgres ``SELECT`` order is unspecified — this
  makes the hash independent of database row-return order, a documented
  and necessary canonicalization step for a hash whose hex rows may
  originate from a query.
- ``json.dumps``'s default ``allow_nan=True`` is in effect (not overridden
  here) — if a ``NaN``/``Infinity`` float ever reached this payload it would
  serialize as the bare tokens ``NaN``/``Infinity``/``-Infinity``, which are
  **not valid RFC 8259 JSON** (though they round-trip through Python's own
  parser). This is a latent footgun for a non-Python reimplementation's JSON
  parser, not an observed failure — ``DynamicHexState``'s fields are all
  Pydantic-constrained to be finite and non-negative
  (``Field(ge=0)`` etc., ``hex_state.py:43-53``), so a NaN reaching this
  path would itself indicate an upstream bug.

**Worked example (verified live, see below):** for one synthetic hex row
with ``c=100.0, v=50.0, s=25.0, k=1000.0`` etc., ``tick=1``,
``rng_seed=2010``, the exact canonical payload this codebase produces is:

.. code-block:: text

   {"actions":[],"hex_state":[{"biocapacity_stock":10.0,"c":100.0,
   "county_fips":"26163","energy_stock":5.0,"h3_index":"891f1d48003ffff",
   "internet_access_pct":0.8,"k":1000.0,"raw_material_stock":3.0,
   "region_id":"great_lakes","s":25.0,
   "session_id":"<uuid4, varies per run>","state_fips":"26",
   "surveillance_coupling":0.2,"tick":1,"v":50.0}],"rng_seed":2010,"tick":1}

(line-wrapped here for readability; the real payload is one unbroken line).
Note the alphabetical key order at both the outer level (``actions``,
``hex_state``, ``rng_seed``, ``tick``) and inside the hex-row dict
(``biocapacity_stock`` before ``c`` before ``county_fips``...) — this
confirms ``sort_keys=True`` applies at every nesting depth, not just the
top. Because ``session_id`` is a fresh random UUID each run, this exact
example is **not** hash-reproducible run-to-row — it demonstrates the byte
layout, not a fixed golden value (unlike the ``defines_hash`` worked example
below, which has no session-scoped field and so IS a fixed, reproducible
golden value).

**Chaining:** none — independent per tick, like ``defines_hash``. Every
``ConservationAuditRow`` for the same tick carries the same hash value
(``conservation_audit.py:415-420,438``), computed once per
``evaluate()`` call.

**Storage location:** the ``determinism_hash`` column of every row in
``conservation_audit_log`` (one row per ``(tick, scale, invariant_name)``
triple; ``audit_models.py:36-67``), written inside the same per-tick
transaction as ``tick_commit`` (``_spec_062.py:314-318``) but as a
**separate table with a separate, differently-computed hash value** — see
*Known Discrepancies* below.

Behavioral artifact: ``trace.csv``
+++++++++++++++++++++++++++++++++++

Not a hash, but the other durable artifact Constitution III.12 names
alongside the three hashes above. ``trace.csv``'s column dictionary is
pinned in ``specs/064-headless-sim-runner/contracts/trace_csv_schema.yaml``
(22 columns; format: UTF-8, comma-delimited, RFC 4180 minimal quoting,
``\n`` line terminator, header row, trailing newline, empty string for
null). The schema-parity test
(``tests/unit/persistence/test_trace_view_columns.py``) asserts the
``view_runtime_trace_emission`` Postgres view's columns equal
``["session_id", *contract_columns_minus_simulated_year]`` exactly — a
tripwire against silent column drift when an underlying subsystem table is
renamed. A reimplementation's obligation for this artifact is column-name
and column-order fidelity, not a hash — it is validated by the schema-parity
test and by tolerance-bounded value comparison (see below), not by
byte-identity.

Worked Example: ``defines_hash``
------------------------------------

Per the hand-computation gate in ``project/programs/13-behavioral-contracts.md``,
every value below was independently computed with ``poetry run python``
against this worktree's actual code and dependency-locked Pydantic version
(``pydantic==2.13.4``, per ``poetry.lock`` at the time of writing) — not
hand-derived or guessed.

Minimal synthetic fragment
+++++++++++++++++++++++++++

A tiny frozen ``BaseModel`` with the exact same construction Pydantic uses
for every ``GameDefines`` sub-model (``model_config = ConfigDict(frozen=True)``,
plain ``float`` fields), small enough to show every byte:

.. code-block:: python

   from pydantic import BaseModel, ConfigDict

   class TinyDefines(BaseModel):
       model_config = ConfigDict(frozen=True)
       gravity: float = 9.8
       friction: float = 0.5

   t = TinyDefines()
   json_str = t.model_dump_json(indent=None)

Verified output:

.. code-block:: text

   json_str  = '{"gravity":9.8,"friction":0.5}'
   len       = 30 bytes
   sha256    = 1c365e6efa6e2c4af0484dd4d486424ce7a00cf2eb69887fe43d130cfac7699
   [:16]     = 1c365e6efa6e2c4a

Note the field order is **declaration order** (``gravity`` before
``friction``, matching the class body), and there is **no space** after
``:`` or ``,``. For contrast, stdlib ``json.dumps(t.model_dump())`` on the
identical data produces ``{"gravity": 9.8, "friction": 0.5}`` — a *different*
byte string (spaces after separators) that would hash to a *different*
value. This is exactly why ``hash_defines()`` must use pydantic's own
serializer rather than round-tripping through ``.model_dump()`` +
``json.dumps()`` — the two are not interchangeable for hashing purposes.

Real production value (reproducible today)
+++++++++++++++++++++++++++++++++++++++++++

Running ``hash_defines()`` against the actual ``GameDefines`` instance the
``imperial_circuit`` scenario constructs (``create_imperial_circuit_scenario()``,
no overrides applied — the scenario with the empty ``defines_overrides``
dict in ``tools/regression_test.py:68``) at this document's HEAD produces:

.. code-block:: text

   hash_defines(...) = fe1ada8c54bec6c0

This is a **real, currently-reproducible value** — it was computed live
during authoring of this document and matches the committed
``tests/baselines/imperial_circuit.json``'s ``defines_hash`` field exactly,
confirming ``mise run qa:regression`` is not currently drifted for this
scenario. The serialized JSON is 19,288 bytes covering all 39
``GameDefines`` categories in declaration order, starting
``{"crisis":{"crisis_period_ticks":13,"r_threshold":0.05,...`` and ending
``...,"lockout_wage_attenuation":0.5}}``.

A note on ``GameDefines.load_default()`` vs a scenario's defines: these are
**not always the same value**. ``hash_defines(GameDefines.load_default())``
at the time of writing produces ``112bb411fb6bda62`` — a *different* 16-hex
prefix from the ``imperial_circuit`` scenario's ``fe1ada8c54bec6c0`` — because
scenario factories may apply their own construction-time adjustments on top
of the loaded defaults before ``defines_overrides`` are even applied. A
reimplementation validating this hash must reproduce the **exact scenario
construction path** (``create_imperial_circuit_scenario()`` /
``create_two_node_scenario()`` plus the named scenario's
``defines_overrides``), not merely ``defines.yaml``'s raw defaults.

Float and Tolerance Policy
-----------------------------

Babylon uses **three distinct, independently-derived tolerance regimes** —
conflating them is a documented anti-pattern (Constitution III.7's
input-hash-drift vs behavioral-drift distinction generalizes to this too).
Each has a written derivation in the codebase, following the pattern
established in ``specs/053-conservation-invariants/contracts/value_conservation.md``:
state the invariant, state the tolerance as a function of a size parameter
where relevant, name the test file, name the failure mode.

1. **Checkpoint value comparison** (``qa:regression`` gate). Absolute
   tolerance ``TOLERANCE = 1e-5`` per float field
   (``tools/regression_test.py:61``), applied field-by-field in
   ``compare_checkpoints()`` (``tools/regression_test.py:353-395``,
   ``if abs(exp_val - act_val) > tolerance``). This is the gate Constitution
   III.7 names as the falsifiability mechanism — "a prediction is a
   checkpointed value, a falsifying observation is a value that drifts
   beyond tolerance." Fixed, not scaled by any size parameter, because a
   checkpoint compares individual scalar fields (wealth, tension,
   consciousness), not a sum over many entities.

2. **Conservation-invariant severity grading** (``ConservationAuditor``,
   per-tick, live during any headless run). Three-level grade against
   ``GameDefines.economy.epsilon_conservation``
   (``src/babylon/config/defines/economy_basic.py:396-404``, default
   ``1e-10``, constrained ``0 < epsilon <= 1e-3``):
   ``|residual| <= epsilon`` → ``ok``; ``epsilon < |residual| <= 1e-6`` →
   ``warn``; ``|residual| > 1e-6`` → ``alarm`` (``grade_severity()``,
   ``conservation_audit.py:51-67``). ``alarm``-severity rows emit a
   ``ConservationAlarmEvent`` (FR-047); a ``--strict`` run treats any alarm
   as a hard stop (``runner.py`` ``_check_strict_alarms``). This tolerance
   is a **fixed absolute epsilon**, not scaled by entity count, because it
   grades a single conservation residual per invariant per tick.

3. **Property-test (Hypothesis) conservation bounds**
   (``specs/053-conservation-invariants``). **Size-scaled** tolerance:
   ``max(1e-10, 1e-11 * N)`` where ``N`` is the number of hexes involved
   (``specs/053-conservation-invariants/contracts/value_conservation.md``,
   Predicates A/C). Unlike regime 2's fixed epsilon, this scales with input
   size because floating-point summation error over ``N`` additions grows
   with ``N`` (each addition can introduce up to one ULP of rounding error;
   the bound reflects an ``O(N)`` worst-case accumulation with a floor at
   ``1e-10`` for small ``N``). This is the derivation pattern this document
   asks a reimplementation to follow for any new size-dependent tolerance:
   name the growth model (here, summation error), not just a number pulled
   from thin air.

Corollary (b) of Constitution III.12 states this policy's boundary
precisely: *"byte-identical replay is guaranteed only within a single
implementation and libm; cross-implementation validation is
tolerance-bounded checkpoint comparison (III.7) with written tolerance
derivations."* A reimplementation should target regime 1's numbers
(checkpoint tolerance) for cross-language validation against
``tests/baselines/*.json``, since regimes 2 and 3 are internal engine
self-consistency checks, not cross-implementation contracts.

What Stays Valid Under Rewrite
----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Artifact
     - Validation mode
     - Notes
   * - ``tests/baselines/*.json`` checkpoint values
     - Tolerance-bounded value comparison (regime 1, ``1e-5``)
     - The primary cross-implementation contract. ``defines_hash`` mismatch
       alone is benign; checkpoint value or ``final_outcome``/
       ``ticks_survived`` mismatch is a real failure.
   * - Dense golden traces (``tests/baselines/dense/<scenario>.csv``,
       Program 13 item 2)
     - Byte-identical (intra-implementation) — see *Dense Golden Traces*
       below
     - ``[IMPLEMENTED]`` — landed alongside this document's item 1. Extends
       regime 1 to every tick (not just the ~6 sampled checkpoints) and
       every entity/relationship field in the column contract; one of the
       corollary (c) redundant-verification strategies (a second,
       independent replay-baseline check layered on the sampled
       checkpoints).
   * - ``defines.yaml`` / ``GameDefines`` coefficient space
     - Structural (field names, types, constraints) — NOT byte-hash
     - The hash (``defines_hash``) detects *that* it changed, not whether a
       reimplementation's copy is "correct" — that's the sync test
       (``tests/unit/config/test_constants_sync.py``) and the YAML file
       itself, which IS the source of truth to reproduce verbatim.
   * - Postgres schema (``src/babylon/persistence/migrations/*.sql``)
     - Structural (DDL) — schema-parity tests
       (``test_trace_view_columns.py`` and siblings)
     - A reimplementation targeting the same Postgres runtime must match
       column names/types/constraints exactly; this is verified by test,
       not by hash.
   * - ``observe()`` / HTTP contracts (Constitution II.8)
     - Contract test per boundary (Constitution III.12 corollary (c))
     - Out of this document's scope; each boundary ships its own contract
       test per III.12(c)'s redundant-verification requirement.
   * - ``tick_commit.determinism_hash``
     - **Not** a cross-run or cross-implementation contract — see
       *Known Discrepancies* below
     - Session-scoped identity marker only; verify replay-integrity by
       Postgres value diff (``EXCEPT``) between runs, not by hash equality.
   * - ``conservation_audit_log.determinism_hash``
     - Intra-run content hash; not compared across runs in current code
     - Reproduces if the hex-frame content, tick, and seed are identical;
       untested across implementations as of this writing.

Dense Golden Traces
-----------------------

Program 13 item 2's answer to the sparsity gap the item-1 audit named: the
sampled checkpoints in ``tests/baselines/<scenario>.json`` pin ~9 variables
at every 10th tick (~54 numbers for a 52-tick scenario) — a
plausible-but-wrong engine could reproduce those 54 numbers without
reproducing the engine's actual per-tick dynamics. ``tests/baselines/dense/
<scenario>.csv`` closes the gap: it pins **every tick** the scenario ran,
for a documented column contract, and is compared **byte-identically**
(regime 0 — stricter than the ``1e-5`` checkpoint tolerance of *Float and
Tolerance Policy* regime 1 above), matching the ``trace.csv`` behavioral
artifact's own byte-identity standard rather than introducing a fourth,
looser regime.

Generated by
+++++++++++++++

``tools/regression_test.py``'s dense-trace machinery
(``_dense_header()``, ``_dense_row()``, ``_run_scenario_ticks()``,
``dense_trace_to_csv_bytes()``). Both the ``generate --dense`` and
``compare`` subcommands route through the same tick-loop core
(``_run_scenario_ticks(name, max_ticks, capture_dense=True)``) that the
sampled-checkpoint path already runs — enabling the dense leg costs zero
extra ``step()`` calls, only cheap per-tick string formatting, which is how
``qa:regression``'s dense comparison avoids materially increasing wall
time (measured: ~7.2s before this feature, ~6.9s after, on this machine —
within noise, not the ~2x ceiling this program's charge allowed).

.. code-block:: bash

   # Regenerate all 5 dense goldens (also regenerates the sampled JSONs,
   # since both paths share one simulation run per scenario):
   mise run qa:regression-generate-dense

   # Compare (byte-identical; runs automatically as part of qa:regression
   # whenever tests/baselines/dense/<scenario>.csv exists):
   mise run qa:regression

Column contract
+++++++++++++++++

The header is derived once from each scenario's **tick-0 topology**
(``_dense_header()``) on the documented assumption that a regression
scenario's entity and relationship set is static for its whole run — true
of all 5 scenarios in ``SCENARIOS`` (no entities or edges are added/removed
mid-run; the two spec-071 decomposition-only entities, e.g.
``CARCERAL_ENFORCER_ID``, are present-but-``active=False`` from tick 0, not
added later). Every subsequent tick's row re-derives the entity/edge set
from the live ``WorldState`` and asserts it still matches the tick-0
header; a scenario that ever violated this assumption would raise
``ValueError`` naming the tick and the topology delta rather than silently
misaligning columns (Constitution III.11, Loud Failure) — this is
untested-because-unreachable by the current 5 scenarios, not a
theoretical-only guard.

Column order, left to right:

1. ``tick`` — the tick number, ``str(int)``.
2. Three global-economy columns, always present in this order:
   ``economy_imperial_rent_pool``, ``economy_current_super_wage_rate``,
   ``economy_current_repression_level`` (the three fields of
   ``GlobalEconomy``, ``src/babylon/models/entities/economy.py``).
3. Per-entity columns, one block per entity ID in **sorted (ascending
   string) order**, each block emitting these 10 suffixes in this fixed
   order (``_DENSE_ENTITY_FIELDS``, ``tools/regression_test.py``):
   ``wealth``, ``effective_wealth``, ``p_acquiescence``, ``p_revolution``,
   ``active``, ``class_consciousness``, ``national_identity``,
   ``agitation``, ``organization``, ``repression_faced``. Column name
   pattern: ``<entity_id>_<suffix>``, e.g. ``C001_wealth``. These are the
   ``SocialClass`` (and nested ``IdeologicalProfile``) fields that survive
   the graph round-trip (excluded from
   ``SOCIAL_CLASS_COMPUTED_FIELDS``, ``src/babylon/models/world_state.py``)
   and are wealth- or tension-relevant: the checkpoint's four tracked
   wealths plus PPP-adjusted wealth, both survival-calculus outputs, the
   liveness flag, all three George Jackson bifurcation ideology axes, and
   both drivers of the survival calculus's organization/repression ratio.
4. Per-relationship columns, one block per **(source_id, target_id) pair**
   in **sorted-tuple order**, each block emitting these 2 suffixes in this
   fixed order (``_DENSE_EDGE_FIELDS``): ``value_flow``, ``tension``.
   Column name pattern: ``edge_<source_id>_<target_id>_<suffix>``, e.g.
   ``edge_C001_C002_value_flow``. One row per relationship is sufficient
   because ``WorldState.to_graph()`` enforces one edge per (source, target)
   pair (``_assert_no_edge_type_collisions``) — the pair alone is a unique
   key, so ``edge_type`` doesn't need to be embedded in the column name.

The five committed goldens' exact column counts (derived from each
scenario's own topology, not a fixed number):
``two_node`` = 4 + 2×10 + 3×2 = 30 columns; ``imperial_circuit`` /
``starvation`` / ``glut`` / ``fascist_bifurcation`` (all 6-entity,
7-relationship topologies) = 4 + 6×10 + 7×2 = 78 columns.

Float and bool serialization
++++++++++++++++++++++++++++++

- **Floats:** Python's ``repr(float)`` — the shortest round-trippable
  decimal representation for the IEEE-754 double, the same family
  ``defines_hash`` above relies on (``_format_dense_value()``,
  ``tools/regression_test.py``). Chosen over a fixed ``%.6f`` because
  ``repr()`` is lossless (a fixed-precision format can silently truncate a
  genuine behavioral divergence smaller than its last printed digit) and
  because this is an intra-implementation byte-identity contract, not a
  cross-implementation one — per corollary (b), byte-identical replay is
  only ever claimed within one CPython + one libm, so ``repr()``'s
  CPython-specific shortest-round-trip algorithm is an acceptable choice
  for *this* artifact (unlike ``defines_hash``, which a reimplementation
  must reproduce byte-for-byte — that one uses pydantic-core's serializer,
  documented separately above).
- **Bools:** ``str(bool)`` → the literal strings ``"True"`` / ``"False"``
  (checked before the float branch, since ``bool`` is an ``int`` subclass
  in Python and would otherwise be silently coerced).
- **Ints** (the ``tick`` column only): ``str(int)``, plain decimal, no
  separators.

CSV framing matches the ``trace.csv`` behavioral-artifact convention
documented above: UTF-8, comma-delimited, RFC 4180 minimal quoting
(``csv.QUOTE_MINIMAL``), ``\n`` line terminator, one header row, trailing
newline, no ``NULL``/empty-cell convention needed (every cell in a dense
row is always populated — there is no sparse/optional field in the column
contract, unlike ``trace.csv``'s hex rows).

Comparison and failure reporting
++++++++++++++++++++++++++++++++++

``compare_dense_trace()`` byte-compares the freshly-regenerated CSV against
the committed golden. On a mismatch it re-parses the golden and walks rows
in lockstep with the fresh trace to name the **first divergent tick and
column** (``_first_dense_divergence()``) — e.g. ``tick 4 column
'C001_wealth': 999.0 != 0.557396`` — rather than only reporting "bytes
differ." Absence of a dense golden for a scenario is **not** a failure
(dense goldens are additive, per-scenario; a scenario without one is simply
not dense-checked yet) — only a byte mismatch against an *existing* golden
fails the gate, keeping with Constitution III.11's distinction between a
genuine failure and an empty/not-yet-populated domain.

Determinism verified: the five committed goldens were generated twice, in
two independent ``poetry run python`` processes, and byte-compared
(``cmp``) identical before being committed — the intra-implementation
guarantee *Scope* above claims, demonstrated rather than assumed.

Known Discrepancies
-----------------------

Documented here per this task's explicit charge to report anywhere the
implementation contradicts the Constitution's or the code's own description
of itself — these are observations, not fixes; **no code changes accompany
this document** (doc-only lane).

1. **``PerTickTransactionEnvelope.determinism_hash`` is not "a single ...
   shared across all rows."** The docstring
   (``src/babylon/persistence/envelope.py:42-43``) states: *"A single
   ``determinism_hash`` is shared across all rows in the tick (GATE-1 /
   Constitution III.7)."* In the live wiring
   (``bridge.py:544-563``), this is **false**: ``envelope.determinism_hash``
   (the trivial ``session_id:tick:seed`` identity string, destined for
   ``tick_commit``) and each ``ConservationAuditRow.determinism_hash``
   inside ``envelope.audit_log_rows`` (the content-based
   ``compute_determinism_hash()`` output, destined for
   ``conservation_audit_log``) are **computed independently, by different
   functions, from different inputs, and are different SHA-256 values** —
   verified by reading both call sites (``runner.py:1395-1397`` vs
   ``conservation_audit.py:415-420``, the latter invoked from
   ``bridge.py:544-549`` with no reference to ``determinism_hash`` at all).
   Both land in the same transaction and the same conceptual "tick," but
   under the field name ``determinism_hash`` they carry two unrelated
   values.
2. **The ``tick_commit`` migration's own comment overstates what it
   stores.** ``0029_tick_commit.sql:9`` calls the column "the queryable
   Constitution-III.7 hash chain," but per III.7's own text
   (``CONSTITUTION.md:250``, "hash of its inputs: World state + player
   actions + random seed"), the stored value contains none of those three
   things — it is a session/tick/seed identity string with no dependency on
   engine output. The value that *does* match III.7's definition
   (``compute_determinism_hash()``) is stored elsewhere
   (``conservation_audit_log``), not in ``tick_commit``.
3. **Player actions are not currently threaded into the III.7 content
   hash.** ``bridge.py:544-549`` calls ``audit_end_of_tick()`` without an
   ``action_list`` argument, so ``compute_determinism_hash()``'s ``actions``
   input is always ``[]`` in the live path — even though both III.7's prose
   and the function's own parameter exist to accommodate them. This is a
   gap between the mechanism's design surface and its current wiring, not a
   correctness bug (there is no current caller with actions to pass), but a
   reimplementation should not assume actions are exercised by any existing
   golden value.

None of the above required a code change to observe or document; they are
reported per this document's scope as facts about the current
implementation, for the orchestrator to weigh against Constitution III.12
corollary (a)'s ``[PENDING CODE]`` marker and Program 13 item 2 (dense
goldens).

See Also
------------

- :doc:`/reference/persistence` — ``PostgresRuntime`` and the runtime-persistence
  protocols; the schema this document's hashes are stored in.
- :doc:`/reference/configuration` — ``GameDefines`` structure and
  ``defines.yaml`` modding surface.
- :doc:`/reference/precision` — the quantization Gatekeeper Pattern, a
  related but distinct drift-prevention mechanism (grid-snapping engine
  values at the type boundary, independent of this document's
  hash/tolerance policy).
- ``CONSTITUTION.md`` III.7 (Determinism and Replayability), III.12
  (Behavioral Contracts, Amendment Q).
- ``specs/053-conservation-invariants/contracts/value_conservation.md`` —
  the tolerance-derivation pattern this document's *Float and Tolerance
  Policy* section follows.
- ``specs/102-gamma-shocks/proof-2R-baseline-regen.md`` Part 4 — the
  precedent for session-id-free cross-run determinism verification via
  Postgres ``EXCEPT`` row-diff.
- ``project/programs/13-behavioral-contracts.md`` — the program this
  document is item 1 of.
