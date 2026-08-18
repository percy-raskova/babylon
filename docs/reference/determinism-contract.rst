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

Program 27 Phase 0 (``docs/superpowers/specs/2026-07-28-program-27-refoundation-design.md``)
adds three chapters below — *The P27 Tick Hash*, *ContentDigest and the
Canonical BSL AST Serialization*, and *Fuel Cost Model and RNG Seeding* — that
are a different kind of artifact from the rest of this document: they are
**forward specifications for the Rust kernel** (``babylon-kernel``,
``babylon-bsl``) to be built in Program 27 Phase 1, not descriptions of code
that runs today. Each states plainly, in its own "Today vs. this chapter"
note, what the live Python implementation does differently — the same
discipline the rest of this document applies retrospectively, applied here
prospectively to a not-yet-written implementation.

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

.. note::
   **Superseded (2026-07-29, Program 27 Task 1 — PR #352).** The canonical
   implementation is now ``babylon.config.defines.canonical_defines_hash``
   (``src/babylon/config/defines/_hash.py``), which all three former call
   sites (``headless_runner/runner.py``, ``cli/play.py``,
   ``tools/regression_test.py``) delegate to. Canonical byte layout:
   ``defines.model_dump(mode="json")`` → stdlib ``json.dumps(payload,
   sort_keys=True, separators=(",", ":"), ensure_ascii=True)`` → UTF-8
   encode → SHA-256 → **full 64-char lowercase hex digest** (no
   truncation, no ``default=`` fallback — a non-JSON-native field raises
   ``TypeError`` loudly per III.11). Note the canonical layout sorts keys
   alphabetically via stdlib ``json.dumps``, unlike the retired layout
   below. The remainder of this entry (including its worked examples)
   describes the **retired pre-Task-1 layout** — pydantic-core
   declaration-order serialization truncated to 16 hex — kept as the
   historical record of the values stamped into pre-2026-07-29 baselines
   and Postgres rows (declared invalidated by the Task 1 ceremony,
   ``blessed(defines-hash-unification)``). The ``ContentDigest`` chapter's
   "64 lowercase hex chars" refers to the canonical layout in this note.

**Computed by (retired):** ``hash_defines()``, ``tools/regression_test.py``
(pre-PR-#352 revision; now a delegating shim).

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

``tick_commit.replay_identity_hash`` — per-tick commit marker
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

.. note::
   **Renamed from ``determinism_hash`` (migration 0044, ADR179 T2,
   2026-07-30).** The old name advertised a determinism guarantee this hash
   cannot provide (see *Inputs* below); the Director's no-debt constraint
   renamed it to what it is. Code quotes below reflect the renamed
   identifiers; historical text elsewhere in this document may still cite the
   old column name when quoting the pre-rename record.

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

   replay_identity_hash_t0 = hashlib.sha256(
       f"{session_id}:0:{config.random_seed}".encode()
   ).hexdigest()
   # ... per subsequent tick:
   replay_identity_hash = hashlib.sha256(
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

``conservation_audit_log.hex_frame_hash`` — the III.7 content hash
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

.. note::
   **Renamed from ``determinism_hash`` (migration 0044, ADR179 T2,
   2026-07-30)** — the honest name says what it covers: the 15-field
   ``DynamicHexState`` frame, not the full world state.

**Purpose:** this is the hash that actually matches Constitution III.7's
literal definition — *"a deterministic SHA-256 hash of its inputs (World
state + player actions + random seed)"* (``CONSTITUTION.md:250``) — because
it is the only hash in the codebase whose bytes depend on the tick's
computed content. This document identifies it with **"the III.7 tick hash"**
named in Amendment Q corollary (a) (``CONSTITUTION.md:268``); no source
comment uses that exact phrase, so this is this document's own reasoned
mapping, stated explicitly as such.

**Computed by:** ``compute_hex_frame_hash()`` (renamed with the column),
``src/babylon/persistence/conservation_audit.py:70-111``:

.. code-block:: python

   def compute_hex_frame_hash(
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

**Storage location:** the ``hex_frame_hash`` column of every row in
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
every value below was independently computed with ``uv run python``
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
   * - ``tick_commit.replay_identity_hash``
     - **Not** a cross-run or cross-implementation contract — see
       *Known Discrepancies* below
     - Session-scoped identity marker only; verify replay-integrity by
       Postgres value diff (``EXCEPT``) between runs, not by hash equality.
   * - ``conservation_audit_log.hex_frame_hash``
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
the committed golden. On a mismatch it re-parses both blobs back into
(header, rows) and first compares the two headers: a changed column set
(inserted, appended, removed, or reordered — e.g. a future dense-schema
widening) short-circuits to a ``DivergenceReport`` naming
``column="<header>"`` with both full header lists as ``expected``/``actual``,
rather than either misattributing a shifted cell to the wrong column or
silently reporting no divergence when the trailing columns still happen to
agree cell-for-cell. Only once the headers match does ``attribute_divergence()``
walk rows in lockstep to name the **first divergent tick and column**,
producing a ``DivergenceReport`` (``scenario, tick, column, channel, county,
expected, actual, magnitude, last_agreeing_tick, candidate_systems`` — the
latter looked up from ``tools.regression_scenarios.CHANNEL_WRITERS``, naming
which engine ``System`` classes could have written the diverging column) —
e.g. printed as ``FIRST DIVERGENCE: tick 4, C001_wealth: 999.0 -> 0.557396
(Δ=998.442604); last agreed tick 3; candidate systems: VitalitySystem,
ProductionSystem, ...`` — rather than only reporting "bytes differ."
``compare_all_baselines()`` also writes every failing scenario's
``DivergenceReport`` (JSON, one entry per scenario) to
``reports/qa-first-divergence.json`` for machine consumption; any stale file
from a prior run is removed at the start of a compare, and the file is only
(re)written when at least one scenario actually diverged, so a green run
leaves no misleading report behind. Absence of a dense golden for a scenario
is **not** a failure (dense goldens are additive, per-scenario; a scenario
without one is simply not dense-checked yet) — only a byte mismatch against
an *existing* golden fails the gate, keeping with Constitution III.11's
distinction between a genuine failure and an empty/not-yet-populated domain.

Determinism verified: the five committed goldens were generated twice, in
two independent ``uv run python`` processes, and byte-compared
(``cmp``) identical before being committed — the intra-implementation
guarantee *Scope* above claims, demonstrated rather than assumed.

The P27 Tick Hash (Rust Kernel Reference)
--------------------------------------------

**Status: forward specification, Program 27 Phase 1 target — not yet
implemented.** This chapter names the single canonical per-tick content
hash for ``babylon-kernel`` (Constitution III.7's literal definition —
*"a deterministic SHA-256 hash of its inputs: World state + player actions
+ random seed"*, ``CONSTITUTION.md:250``) that the Rust port is required to
compute, replacing the three-hash tangle documented in *Catalog of
Constitutional Hashes* above (``defines_hash``, ``tick_commit.replay_identity_hash``,
``conservation_audit_log.hex_frame_hash`` — both named ``determinism_hash``
pre-0044) with **one unambiguously named value** — resolving the naming
collision noted in *Known Discrepancies*
item 1 below and owner-queue item 31 (``persistence/envelope.py``).

**Field set, in this order for the worked example below (the canonical
serialization itself sorts keys alphabetically — see *Ordering* — so
declaration order does not affect the byte output; this list is only a
reading aid):**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Field
     - Type
     - Content
   * - ``tick``
     - ``u64``
     - The current tick index.
   * - ``rng_seed``
     - ``u64``
     - The session's fixed RNG seed (Constitution III.7's ``random seed``
       input). **Not** the session UUID — the session identifier never
       enters this hash, keeping it independent of run identity, unlike
       ``tick_commit.replay_identity_hash`` today.
   * - ``nodes``
     - array of node records
     - **Every** graph node (every ``NodeType``, not just
       ``DynamicHexState``'s 15 hex fields as
       ``compute_hex_frame_hash()`` does today) — closes the "World
       state is narrower than the full ``WorldState`` model" gap noted in
       the *Catalog* section above.
   * - ``edges``
     - array of edge records
     - Every graph edge (every ``EdgeType``).
   * - ``actions``
     - array of action records
     - The player/organization actions actually applied this tick —
       closes *Known Discrepancy* item 3 below (today's
       ``action_list`` parameter is always ``[]`` in the live wiring).

**Ordering:**

- **Key ordering:** alphabetical (``sort_keys``-equivalent), applied
  recursively at every nesting level — the ``conservation_audit_log``
  convention, **not** ``defines_hash``'s declaration-order convention.
  This hash exists for cross-run and eventually cross-implementation
  replay verification, and declaration order is not a portable property
  across a Rust ``struct`` and a Python ``BaseModel``.
- **Node ordering:** sorted ascending by ``node_id`` (string comparison),
  matching the dense-golden-trace convention (*Dense Golden Traces*
  above) rather than graph-backend iteration order, which is
  unspecified.
- **Edge ordering:** sorted ascending by the ``(source_id, target_id)``
  tuple, same rationale.

**Float and int encodings — the deliberate departure from
``defines_hash``'s "shortest round-trippable decimal" convention:**

- **Integers** (``tick``, ``rng_seed``, any plain integer scalar field):
  canonical decimal ASCII text, no leading zeros, a leading ``-`` only
  when negative, no thousands separators — e.g. ``1``, ``-42``.
- **Fixed-point ``Currency`` (``i128`` micro-units):** canonical decimal
  ASCII text of the underlying ``i128``, **never** a JSON bare number —
  ``serde_json``'s (and every mainstream JSON library's) number type is
  IEEE-754 ``f64``, which cannot represent the full ``i128`` range without
  silent precision loss; encoding as a decimal string sidesteps that
  entirely.
- **IEEE-754 ``f64`` floats:** the raw 64-bit bit pattern, big-endian byte
  order, encoded as **16 lowercase hex characters** — e.g. ``100.0`` encodes
  as ``4059000000000000``. This is a deliberate departure from
  ``defines_hash``'s shortest-round-trip-decimal convention (documented
  above): a shortest-round-trip decimal *algorithm* (Python's ``repr()``,
  Rust's ``ryu``, Go's ``strconv``) is not guaranteed to agree
  byte-for-byte across languages on every input (tie-breaking at exact
  half-way points, ``-0.0``, subnormals), even though every one of them
  parses back to the identical ``f64`` bit pattern. Encoding the bit
  pattern directly removes the decimal-formatting step from the hash
  entirely, at the cost of human-unreadability — acceptable, since this
  is a change-detection hash, not a human-facing artifact.
- **Booleans:** the literal ASCII tokens ``true`` / ``false`` (JSON's own
  literals), **not** ``defines_hash``'s inherited Python-``bool``-as-``int``
  hazard and **not** the dense-trace convention's ``"True"``/``"False"``
  strings (each artifact in this document keeps its own historically
  correct convention; this chapter specifies the new one for the new
  hash, not a retrofit of the old ones).
- **Enum members / strings:** UTF-8 bytes of the canonical member name
  exactly as declared (e.g. ``NodeType.SOCIAL_CLASS`` → ``"social_class"``,
  ``EdgeType.EXPLOITATION`` → ``"EXPLOITATION"``) — whichever casing the
  enum declares, reproduced verbatim, never re-cased.
- **``null`` (added 2026-07-30, at first implementation):** an unset optional
  field is the bare JSON literal ``null`` (a Rust ``Option::None`` serializes
  to exactly this). An optional field that is unset is real state — the live
  graph carries many (``county_fips``, ``aligned_faction_id``) — and this rule
  does **not** reopen the stringly-fallback ban below, which targets values
  whose *type* has no rule: hashing ``null`` explicitly makes a wrongly
  defaulted field **more** visible, since ``null`` and ``0.0`` are different
  bytes. Records carry their full declared field set, so "key absent" and "key
  present, null" never both occur for the same field.
- **Sets (added 2026-07-30):** a set-valued field serializes as an array of its
  members in ascending canonical-serialization order (sort the members' own
  encoded forms, which yields a total order regardless of member type). Set
  iteration order is hash-seed dependent in Python and is not a property any
  implementation could reproduce. Found by hashing live graphs: the
  ``legal_authorities`` node attribute is a ``frozenset`` — the same
  set-stashed-in-a-node-attribute shape Amendment D sub-ruling D-4 declined to
  grandfather for ``ECONOMIC_SECTOR``. This rule mirrors ``babylon-graph``'s
  ``members_of``, which likewise returns members sorted, never as declared.
- **Non-string-valued enum members are a load failure (added 2026-07-30):** an
  ``IntEnum`` would hash as a bare integer and silently alias a genuine integer
  field, and its numbering is an internal detail no port should be required to
  reproduce. Only string-valued members may enter the hash.
- **Non-string record keys are a load failure (added 2026-07-30):** canonical
  key ordering is undefined for a mixed-type key set, so the byte output would
  silently depend on insertion order.
- **Ban on stringly fallbacks:** a field encountered during serialization
  that has no encoding rule above (i.e. not one of int / ``i128`` / ``f64``
  / bool / enum-or-string / array / nested record) is a **hash-time load
  failure** (Constitution III.11, Loud Failure) — it MUST NOT fall back to
  a generic ``str(obj)``/``Debug``-style rendering. This explicitly bans
  the pattern ``conservation_audit.py``'s ``compute_hex_frame_hash()``
  uses today (``json.dumps(..., default=str)``, ``conservation_audit.py:110``)
  going forward.

**Worked example (synthetic, hand-verified with ``python3``):** one
``social_class`` node and one ``EXPLOITATION`` edge, ``tick=1``,
``rng_seed=2010``, no actions:

.. code-block:: text

   f64_hex(100.0) = 4059000000000000
   f64_hex(12.5)  = 4029000000000000

   canonical bytes (one unbroken line; wrapped here for readability):
   {"actions":[],"edges":[{"edge_type":"EXPLOITATION","source_id":"C001",
   "target_id":"C002","value_flow":"4029000000000000"}],"nodes":[{"active":
   true,"node_id":"C001","node_type":"social_class","wealth":
   "4059000000000000"}],"rng_seed":2010,"tick":1}

   len(canonical bytes) = 246
   sha256 = b256dbbca591c5af2b8cb23b9c4027ed1ac657d10b1e669aadb05670cd75d4a0

.. note::
   **Correction (2026-07-30, at first implementation).** As first published,
   this example rendered the boolean ``active`` as the *quoted* string
   ``"true"`` (248 bytes,
   ``ea6f1d10c6a6fc97d1481158ae1bbfc6b978e80584d984cccf6525af1023470f``),
   contradicting the *Booleans* rule above — and inconsistent with how the
   same example renders integers (``"tick":1``, bare). The published digest
   was self-consistent only in the sense that it re-derived the slip. The
   normative prose governs: booleans are bare JSON literals, so the canonical
   form is the 246-byte string shown. Nothing depended on the superseded
   value — the hash had no implementation at the time — and both forms are
   recorded here so a reader meeting the old digest in an archived document
   can identify it. The example is now executable rather than hand-verified:
   it is pinned byte-for-byte by
   ``tests/unit/kernel/test_tick_hash.py::TestTheWorkedExample``.

**Chaining:** none, matching the established precedent of every other hash
in this document (*Catalog of Constitutional Hashes* above) — a fresh,
independent hash per tick. No ``H_n = H(H_{n-1} || data_n)`` Merkle-style
construction is introduced; cross-run determinism verification stays the
Postgres ``EXCEPT`` row-diff pattern this document already documents (see
``tick_commit.replay_identity_hash`` above), and this hash's job is a single
unambiguous per-tick content fingerprint, not a chain.

**Today vs. this chapter — what changes:** all three of today's hashes
must be reconciled into this one at cutover. Concretely: (1)
``defines_hash`` is unaffected (it stays a separate, independent hash —
see the *ContentDigest* chapter below); (2) ``tick_commit.replay_identity_hash``
today carries **no world state at all** (just
``session_id:tick:rng_seed``) — this chapter's hash replaces it as the
content-bearing marker, with the session-scoped identity role served
separately if a run-identity marker is still needed; (3)
``conservation_audit_log.hex_frame_hash`` today hashes only the 15-field
``DynamicHexState`` hex frame with ``default=str`` and no actions — this
chapter widens scope to the full graph and bans the stringly fallback.

ContentDigest and the Canonical BSL AST Serialization
---------------------------------------------------------

**Status: forward specification.** ``defines_hash`` (documented in full
above, in the *Catalog of Constitutional Hashes* section) is the canonical,
already-specified half of ``ContentDigest``; the authorized fix
unifying today's three mutually-inconsistent implementations is a
separate, already-chartered unit of work (Program 27 Task 1,
``src/babylon/config/defines/_hash.py``'s ``canonical_defines_hash()``) and
this chapter does not restate its byte layout — see *Catalog* above for
that. This chapter specifies the other half, ``rules_hash``, and
``ContentDigest``'s own combining layout.

**``ContentDigest`` layout:**

.. code-block:: text

   ContentDigest {
       defines_hash: String,  // 64 lowercase hex chars, per Catalog above
       rules_hash:   String,  // 64 lowercase hex chars, this chapter
   }

Serialized form (for storage/comparison, e.g. a future
``ContentDigest`` row or log line): compact JSON, **sorted keys**, pinned
separators ``(",", ":")`` — the same convention this document's
``conservation_audit_log`` hash payload already uses, chosen here (over
``defines_hash``'s declaration-order convention) because ``ContentDigest``
is a 2-field struct with an alphabetically-unambiguous ordering and no
benefit from mirroring a 39-category Pydantic model's declaration order:

.. code-block:: text

   {"defines_hash":"<64-hex>","rules_hash":"<64-hex>"}

**``rules_hash`` — canonical AST serialization (CAS): specified in the BSL
Language Reference.** Purpose: a rule-file edit that only reformats
whitespace or adds/removes a comment must **not** move ``rules_hash``
(Constitution III.7's input-hash-drift-vs-behavioral-drift distinction,
generalized to rule content — see *Content pipeline*,
``docs/superpowers/specs/2026-07-28-program-27-refoundation-design.md:404-406``);
a rule edit that changes the parsed AST must move it.

The byte-level serialization behind ``rules_hash`` is normatively defined in
:doc:`/reference/bsl-language` §5 (*Canonical AST serialization*): a two-shape
(atom/form) length-prefixed big-endian binary layout with canonical child
ordering (positional → options sorted by keyword name → variadic body), **no
floating-point value anywhere in the hash path** (BSL's lexicon has no bare
float literals — decimals are kind-suffixed and canonicalized to minimal
scale, §1 of that document), and a fully worked, computed example (source →
canonical AST → bytes → sha256).

.. note::
   **Supersession (2026-07-29).** An earlier draft of this chapter specified
   a text-token re-emission pipeline whose atom encoding admitted float
   literals via IEEE-754 bit-pattern tokens. That draft is superseded by the
   BSL Language Reference §5 definition above, for two reasons: (1) the
   float-literal accommodation contradicted the ratified design's lexicon
   (kind-suffixed literals only — a bare non-integer literal is a lex
   error), and (2) the binary CAS is additionally **option-order
   insensitive**, a strictly stronger normalization than whitespace/comment
   stripping alone. The design spec (§166-175) mandates that the evaluator's
   byte-level semantics, the canonical AST serialization, and the fuel cost
   model live in *one* language-agnostic reference; the current split —
   hash-domain chapters here, language-domain chapters in
   :doc:`/reference/bsl-language` with mutual pointers and no duplicated
   normative text — is the Phase-0 working resolution of that mandate and is
   queued for the Phase-1 review (BSL Language Reference, draft-rulings
   register) to either ratify or consolidate.

**Chaining:** none — independent per content snapshot, matching
``defines_hash``.

**Today vs. this chapter:** there is no ``rules_hash`` implementation
today because BSL does not exist yet — this is new ground, not a port. The
two nearest existing analogues (the doctrine trap-condition string DSL,
``src/babylon/domain/doctrine/mechanics.py``, and the event-precondition
tree, ``src/babylon/engine/event_evaluator.py``) have **no content hash at
all**; rule-content drift in either today is invisible to any determinism
gate. This chapter closes that gap going forward.

Fuel Cost Model and RNG Seeding (Rust Kernel Reference)
------------------------------------------------------------

**Status: forward specification, Program 27 Phase 1 target.**

**Fuel cost model: specified in the BSL Language Reference.** The
per-AST-node base-cost table, the load-time bound composition
(``bound(rule)`` from declared ceilings), and the runtime accounting
semantics are normatively defined in :doc:`/reference/bsl-language`
(§3.7 *static bound*, §4.5 *fuel accounting*, and its draft-rulings
register, which distinguishes ratified base rows from derived rows
awaiting Phase-1 review). Those constants are the Phase-1
conformance-vector inputs (§8.2 of the refoundation design) and **may be
revised only with a vector re-bless** — they are content, not tuning
knobs a system can silently drift. An earlier draft of this chapter
carried its own copy of the cost table; it is replaced by this pointer so
exactly one normative table exists (same rationale as the ``rules_hash``
supersession note above).
**RNG algorithm — PINNED (Phase 1 Task 5, 2026-07-30):** ``ChaCha8Rng``
(``rand_chacha``), implemented in ``rust/crates/babylon-kernel/src/rng.rs``.
Rationale, ratified from that module's own text: (1) it takes an exact
32-byte seed — a SHA-256 digest's width, so the derivation needs no
truncation or expansion step; (2) it is a pure-Rust, no-``unsafe``,
platform-independent stream-cipher construction, fully deterministic from
its seed with no OS-entropy dependency (III.7); (3) 8 rounds is the "fast,
still no known practical distinguisher" configuration — this is not a
cryptographic-security use case, so ``ChaCha8`` over ``ChaCha20`` is pure
speed with no correctness cost. Constructed only per ``(session_id, tick)``
— there is no entropy-seeded constructor.

**Stream layout — PER-CARRIER, the ADR176 ruling-20 rider:** one stream
per ``(session_id, tick, domain, stable_key)``, never one stream per tick.
With a tick-global stream consumed in iteration order, adding one carrier
shifts every later draw that tick — LOD refinement becomes a butterfly
generator (``reports/design-inputs-dossier-2026-07-29.md`` §6.3). Deriving
each stream from the carrier's own identity makes draws grain-invariant by
construction, and refinement needs no RNG state migration. The API offers
NO tick-global constructor, so the butterfly shape cannot be reached by
accident. ChaCha is counter-mode by construction, so a carrier's stream
position is the rider's per-draw counter.

**Seeding derivation — as implemented:**
``seed = SHA256(session_id_utf8 ‖ tick_le8 ‖ salt_le8 ‖ len_le8(domain) ‖
domain_utf8 ‖ len_le8(stable_key) ‖ stable_key_utf8)``, all 32 bytes used
directly as the ``ChaCha8Rng`` seed; ``salt`` is the existing constant
``0xBA1AC1A`` (``_SYSTEM_RNG_SEED_SALT``,
``src/babylon/kernel/system_base.py:32``); ``tick``/``salt`` and both
length prefixes enter as 8-byte **little-endian** integers. The length
prefixes are load-bearing: unframed concatenation would let
``("ab", "c")`` and ``("a", "bc")`` collide, making stream identity depend
on where two strings split.

.. note::
   **Supersession (2026-07-30, at implementation).** An earlier draft of
   this section specified colon-separated decimal *text* forms truncated to
   the digest's first 8 bytes as a big-endian ``u64``. Both choices were
   artifacts of assuming a ``u64``-seeded PRNG. With the pinned 32-byte-seed
   generator, truncation would discard 24 of the derivation's 32 bytes for
   no benefit, and the text encoding added a formatting layer with no
   consumer. The Phase-1 plan's Task-5 byte layout (binary, full-width)
   supersedes; the superseded text form's worked value
   (``…:7:195144730 → u64 4222636361569202174``) is retained here only so an
   archived copy quoting it stays identifiable. Nothing depended on it — no
   implementation existed.

**Within-implementation replay conformance vector** (generated once from
the first green run, byte-pinned thereafter by
``rng.rs::conformance_vector_first_four_u64s`` — any future divergence is a
determinism regression, never "the RNG got better"):

.. code-block:: text

   session_id = "conformance", tick = 1,
   domain = "conformance-domain", stable_key = "carrier-0"
   first four u64 draws:
     0x6774721d2209092f
     0x6d422bc9af8428f1
     0x0ce291abfcb11e7a
     0xdd11962972495117

**``next_f64``:** the top 53 bits of one ``u64`` draw scaled by ``2⁻⁵³`` —
every representable output is an exact multiple of ``2⁻⁵³`` on ``[0, 1)``,
bit-deterministic across platforms (no libm, no rounding-mode dependence).

**R8 declaration — Python streams are a closed epoch.** This seeding
derivation is a **new** construction, not a port: today's
``resolve_rng()`` (``src/babylon/kernel/system_base.py:35-55``) seeds
additively — ``random.Random(0xBA1AC1A + tick)`` — with **no ``session_id``
input at all**, and its ``services.rng`` override path (the only place a
session-scoped seed could enter) is verified, by reading every call site,
to be **never populated in the live wired path**
(``src/babylon/engine/optimization/backends/in_memory.py:99-100`` documents
this explicitly: *"never populated on this path"*). Concretely: today,
``SimulationConfig.random_seed`` reaches the tick-commit identity hash but
**does not** reach the actual System-level PRNG stream — two runs with
different ``random_seed`` values but the same tick produce identical
stochastic System rolls today, which is itself worth flagging as a live
gap rather than a documented feature. R8 (Director ruling, per the
refoundation design) is explicit that this changes at cutover: the Rust
kernel's RNG streams will not match Python's byte-for-byte regardless (no
crate reproduces CPython's Mersenne Twister stream bit-for-bit by design
choice — an agent-recommended bit-exact CPython-RNG crate was considered
and overruled), so Python's RNG streams are declared a **closed epoch**:
stochastic baselines (the electoral goldens; 5 of the 11 canon scenarios)
re-bless at the cutover ceremony under ensemble-envelope comparison (§8.5
of the refoundation design), not byte-identical replay — this is the
compensating instrument, and it is explicitly weaker than stream-compatible
comparison, stated plainly rather than hidden.

Transcendental Crossing — ``exp``/``log`` (Rust Kernel Reference)
------------------------------------------------------------------

**Status: normative as of the #576 intrinsic-host train, Task 1
(2026-08-17) — implemented in**
``rust/crates/babylon-kernel/src/transcendental.rs``. Ruled by ADR176
ruling 21 ("P27 Task 8: transcendentals cross via a **PINNED SOFT-FLOAT
LIBM crate** with **golden vectors per intrinsic**"), reaffirmed by
ADR188's decision paragraph. This repairs :doc:`/reference/bsl-language`
§4.3's stale sentence that the polynomial-vs-libm choice was "an open
Phase-1 Director ruling … deliberately not decided" — ADR176 r21 settles
that question. Only the crate and the tolerance derivation remained as
workforce work, and both close here.

**The chosen policy.** ``exp`` and ``log`` cross via the ``libm`` crate,
version-pinned at ``0.2.16`` with ``default-features = false``, promoted
to a direct dependency of ``babylon-kernel`` and wrapped in
``babylon_kernel::transcendental``. ``f64::exp`` / ``f64::ln`` /
``f64::log*`` / ``f64::powf`` are **banned** at and below the intrinsic
seam by a ``rust/clippy.toml`` ``disallowed-methods`` row (``f64::sqrt``
and ``f64::tanh`` are banned too, for a *different* reason: ADR188 Row 6
and Row 8 ELIMINATED both intrinsics outright — platform fit and the
scissors balance each re-derive as a measure — a permanent disposition,
not an undeclared crossing, so no ``babylon_kernel`` wrapper exists for
either and none is coming). Per-intrinsic golden vectors pin the exact
``u64`` bit patterns
(``rust/crates/babylon-kernel/tests/transcendental_goldens.rs``).
**Rust std is deliberately not the crossing**: ``f64::exp`` / ``f64::ln``
route to the *platform* libm (glibc vs musl vs Apple's) — exactly the
non-reproducibility the *Scope* chapter above names (lines 53-66) — so a
per-build determinism claim would be strictly weaker than the ruling
requires and would silently make the tick hash platform-dependent.
Consequence: **the Rust engine's tick hash is byte-identical across OS,
libc, and CPU architecture** — a *stronger* claim than Constitution
III.12 corollary (b), which continues to govern comparisons against the
frozen Python engine (glibc) and nothing else.

**Why ``libm 0.2.16`` satisfies "pinned soft-float," verified in the
vendored source** (already present transitively via Bevy/glam/naga before
this crossing, so the source, checksum, and license were already vetted;
this train promotes it from a transitive to a *direct* dependency of
``babylon-kernel`` — no prior Babylon crate depended on it directly):

- A pure-Rust MUSL libm port — ``#![no_std]``, no C, no platform libm.
- License ``MIT``, which ``rust/deny.toml`` already permits — no new
  license exception, no new source (crates.io only).
- Feature surface: ``arch = []``, ``default = ["arch"]``,
  ``force-soft-floats = []``, plus ``unstable*`` rows.
  ``babylon-kernel``'s own declaration sets ``default-features = false``.
- ``log`` (``libm::log``) has **no architecture dispatch at all** — its
  source contains no ``select_implementation!`` invocation; the soft-float
  implementation runs unconditionally.
- ``exp``'s only dispatch is **unreachable on every target Babylon
  ships**. Its source reads
  ``select_implementation! { name: x87_exp, use_arch_required:
  x86_no_sse, args: x, }``. ``use_arch_required`` ignores the ``arch``
  feature flag entirely; the guard is the ``x86_no_sse`` cfg, which the
  crate's build script emits only when ``target_arch == "x86"`` (32-bit)
  **and** the target lacks the ``sse`` feature (legacy i586). That
  predicate is false on ``x86_64`` (a distinct ``target_arch``, SSE2
  baseline) and false on ``aarch64``. On both of Babylon's targets,
  ``libm::exp`` takes the generic soft-float path.
- **``default-features = false`` does not mean ``arch`` is off in the
  shipped binary.** Cargo unifies a dependency's enabled features per
  ``(package, version)`` across the whole unit graph, not per-crate:
  ``cargo tree -p babylon-client -i libm -e features --locked`` shows
  ``libm feature "arch"`` **active**, because other workspace dependents
  — independently of each other and of this crate — request ``libm``'s
  default features, and that request wins workspace-wide. Run
  the command above for the current requester set rather than trusting a
  named list here, which would drift the moment a dependency changes.
  The zero-tolerance claim below rests
  on ``exp``'s and ``ln``'s dispatch being **feature-independent**
  (``use_arch_required`` ignores the feature flag outright; ``log`` has
  no dispatch code to gate at all), never on ``arch`` actually being off.
  A future intrinsic whose ``arch`` dispatch is *not* similarly
  feature-independent cannot rely on the crate-level declaration alone —
  checking the resolved feature set needs ``cargo tree -e features``
  against the shipped binary's own unit graph. This chapter records the
  caveat as standing for Task 2 and later intrinsics; this train does not
  fix it.
- ``libm::exp`` and ``libm::log`` are thus **bit-identical across
  ``x86_64`` and ``aarch64``**, independent of which ``libm`` feature set
  the workspace resolves to, by inspection of the dispatch predicates —
  the golden vectors turn that inspection into an executable guard.

**The tolerance derivation (the artifact ADR176 r21 owes):**

1. **Within the Rust engine: tolerance is ZERO.** One pinned crate, one
   pinned version, one soft-float code path, arch dispatch proven
   unreachable. Comparisons are ``assert_eq!`` on ``f64::to_bits()``,
   never ``abs(a - b) < eps``. Any drift is a red gate: a ``libm`` bump, a
   feature flip, or an accidental ``f64::exp`` all fail the golden
   vectors.
2. **Against the frozen Python engine: tolerance is the III.12
   corollary-(b) regime** (*Float and Tolerance Policy* above, regime 1).
   CPython's ``math.exp``/``math.log`` call glibc; glibc and MUSL
   disagree in the last 1-2 ULPs (lines 53-66 above). Derivation: a bound
   of ``2 ulp(result)`` covers the crossing error per call — glibc
   documents ≤1 ulp for ``exp``/``log``, MUSL's libm targets ≤1 ulp, so
   the pairwise difference is ≤2 ulp; for ``f64`` that is a **relative**
   bound of ``2 × 2⁻⁵² ≈ 4.44e-16``. Composed through the one live
   ``exp`` site (``exp(clamp(log(ratio)))`` — Contradiction @18.0's
   financialization index, ADR202 R9), two crossings give a relative
   bound of ``~8.9e-16``, seven orders of magnitude *inside* the
   ``qa:regression`` checkpoint tolerance of ``1e-5`` (*Float and
   Tolerance Policy*, regime 1). **No existing gate needs its tolerance
   widened, as a result** — a fact worth recording, because the
   alternative (widening a gate) would have been a ceremony.
3. **Standing obligation on port trains:** a dual-implementation oracle
   that compares a BSL pack's output against the frozen Python engine
   through an ``exp``/``log`` site **must** use regime-1 tolerance, never
   byte equality. This is the gotcha that will bite the first consuming
   pack; this chapter states it here so it bites the doc instead.

Currency Operator Semantics (Rust Kernel Reference)
------------------------------------------------------

**Status: normative as of Phase 1 Task 3 (2026-07-30) — implemented in**
``rust/crates/babylon-kernel/src/currency.rs``. Added per that task's Step-5
cross-check: this document pinned ``Currency``'s hash *encoding* (i128
micro-units as decimal strings — the *P27 Tick Hash* chapter) but not its
operator *algebra*, and the plan forbids silently diverging code from spec.
The four spec-pinned operators (refoundation design §6.1):

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Operator
     - Result
     - Rule
   * - ``Currency ± Currency``
     - ``Currency``
     - checked i128 add/sub; overflow is a loud III.11 failure, never
       wrapping or saturating
   * - ``Currency × Coefficient``
     - ``Currency``
     - integer-numerator multiply (below), then one half-even division by
       ``10⁶``
   * - ``Currency ÷ Currency``
     - ``Coefficient``
     - i256 intermediate ``(a × 10⁶) / b``, half-even; out-of-``[0,1]``
       result is a loud caller bug
   * - ``Currency ÷ integer``
     - ``Currency``
     - half-even division

**The integer-numerator multiply.** ``Coefficient`` is grid-quantized on
construction, so its exact value is the rational ``n / 10⁶`` with integer
``n ∈ [0, 10⁶]``. The multiply recovers ``n`` (``round(coeff × 10⁶)`` —
exact by construction for a grid value), computes ``value × n`` in checked
i128, and divides by ``10⁶`` half-even in one step. The i128 side is
**never cast to f64**, which would silently lose precision above 2⁵³
(≈ 9.0e15 micro-units) — inside the nationwide-scale headroom i128 exists
to provide.

**Half-even (banker's) rounding division**, the ``round_half_even`` kernel
intrinsic (§6.2): with ``q = n / d`` (truncating) and ``r = n % d``, compare
``|2r|`` to ``|d|`` — less keeps ``q``; greater steps ``q`` one toward the
true quotient; equal (an exact tie) keeps ``q`` if even, else steps.

**Worked examples (hand-verified, pinned as Rust unit tests in
``currency.rs``):**

.. code-block:: text

   3 micro-units × Coefficient(0.5):
     n = 500_000; product = 1_500_000
     half_even(1_500_000 / 1_000_000): q=1, r=500_000, 2r == d (tie), q odd
     -> 2 micro-units          (1.5 rounds to the even neighbor 2)

   Currency(1_000_000) ÷ Currency(3_000_000):
     i256: (1_000_000 × 1_000_000) / 3_000_000 -> q=333_333, 2r < d
     -> Coefficient(0.333333)  (the 10⁻⁶-grid value)

   5 micro-units ÷ 2:
     q=2, r=1, 2r == d (tie), q even -> 2   (2.5 rounds to even 2)

**Sign domain (OPEN question, carried from the Phase-1 plan):** the Python
reference constrains ``Currency`` non-negative; the Rust representation is
signed i128 (intermediate deltas are naturally signed) and does not
re-impose non-negativity at the type level. If ruled otherwise, the fix is
a boundary wrapper, not an operator change — the algebra above is
sign-complete as specified.

Known Discrepancies
-----------------------

Documented here per this task's explicit charge to report anywhere the
implementation contradicts the Constitution's or the code's own description
of itself — these are observations, not fixes; **no code changes accompany
this document** (doc-only lane).

1. **[RESOLVED 2026-07-30 — ADR179 T2, migration 0044.]** The two unrelated
   values no longer share a name: the envelope/``tick_commit`` field is
   ``replay_identity_hash``, the audit field is ``hex_frame_hash``, and the
   envelope docstring now states the two-hash reality outright (this was
   owner-queue item 31). The original finding, kept as history:
   **``PerTickTransactionEnvelope.determinism_hash`` is not "a single ...
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
2. **[RESOLVED in effect by the same rename** — the column no longer claims
   to be a determinism hash; ``0029``'s comment stands as history and
   ``0044`` records the correction.] Original finding: **The ``tick_commit``
   migration's own comment overstates what it stores.**
   ``0029_tick_commit.sql:9`` calls the column "the queryable
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
