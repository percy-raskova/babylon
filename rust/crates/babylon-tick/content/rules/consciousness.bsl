; ConsciousnessSystem (Consequences @17.0) — the class-surface measured
; ternary (issue #588, ADR204 W10). Frozen source:
; src/babylon/engine/systems/ideology.py (ConsciousnessSystem, :94-442) with
; the routing law at src/babylon/formulas/consciousness_routing.py:288-370.
; Port posture (the design's own ruling): measured-ternary read path +
; UNPOSITIONED first — transcribe the INPUTS and the ROUTING LAW re-pointed
; at (r, l, f), NOT a cc/ni transcription; the cc/ni bridge mapping is the
; read path's spec, and it lands in a later task.
;
; TASK 1 SHIPS: `consciousness/p0-position` only — the class-seeding law
; (A-001) plus this port's absence idiom. The read path (dominance readback
; beyond positioning, the simplex normalization) and the routing update law
; accrete as later pN rules on top of the exact qnames
; consciousness-ternary-conformance.bscn declares.
;
; UNPOSITIONED IDIOM (L-ABS, the row-19 disease's death certificate): the
; ternary fields are never defaulted into existence — a never-positioned
; class carries NO r/l/f and NO dominant-worldview, and a raw store read
; errors loud (III.11). Inside a rule, absence is observed ONLY through
; declared literals: `:optional` + `:default 0.0p` bindings, gated on
; `(= (+ r (+ l f)) 0)` — a positioned class is a simplex point (shares sum
; to 1), so a zero sum is EXACTLY never-positioned, by construction, never
; by epsilon and never by a fabricated 0.5 (bindings.rs's own §3.5 law: "no
; rule observes absence — it observes a declared default"). Every later
; rule in this pack optional-binds the ternary the same way and gates on
; `(> (+ r (+ l f)) 0)` for the positive direction.
;
; D116 BYTE-ORDER MAP (docs/reference/bsl-language.rst, the recorded
; cross-rule same-tick visibility divergence this pack deliberately relies
; on, production.bsl-header style): rules run to completion in ascending
; rule-id byte order against the same mutable graph, so
; `consciousness/p0-position` sorts before every later `consciousness/p1-…`
; / `p2-…` rule — positioning ALWAYS precedes the same-tick read path, and
; a class positioned this tick is readable by this tick's later rules
; (class-emergent in the conformance world is the standing witness). Task 1
; ships one rule, so the map is trivially total today; the ordering
; obligation binds every later addition — keep the pN prefixes monotone in
; the frozen engine's own causality order.
;
; D-RECORDS this pack carries (full spike evidence in
; consciousness-ternary-conformance.bscn's header — the two files' records
; are one ledger, split by surface):
;   1. UNPOSITIONED is expressed as `:optional` + `:default 0.0p` + the
;      zero-sum guard (above) — the lawful absence shape in current BSL
;      (no has-field combinator exists; archaeology digest gap 1). The
;      `:default` declarations are deliberate and content-visible;
;      default_lint.rs's allowlist mechanism governs the migration-corpus
;      sites and does not gate this pack's load.
;   2. Anchor presence is tested by SENTINEL, not by a guard combinator:
;      wages-paid / value-produced are non-negative whenever present, so
;      `:default -1` makes `(>= wages 0)` the presence test. An active
;      class with neither anchor (the conformance world's `employer`) is
;      never positioned and never routed.
;   3. p0 RECORDS dominant-worldview = LIBERAL at positioning (a Task-1
;      brief-gap correction, Director-visible): the posture test's own
;      contract requires a positioned class's dominant to read back the
;      LIBERAL member while an unpositioned class's reads absent, and no
;      other Task-1 rule exists to write it. This IS A-001, not a new
;      semantics: the ruled rest state (0, 1, 0) has LIBERAL as its strict
;      argmax, and the frozen tie-break prefers LIBERAL outright
;      (models/entities/consciousness.py:177-192). The full argmax
;      readback for MOVED ternaries lands with the read-path task.
;   4. consciousness/simplex-epsilon is DEFERRED out of the defines
;      environment: the frozen _EPSILON = 1e-10 (consciousness_routing.py:41)
;      is inexpressible as a p/i/c literal (E-LEX-023, scale <= 9,
;      reader.rs::classify_unit_interval). The normalization task that
;      consumes it picks the lawful form.
;   5. Rounding law (spike 4's verdict, the Task-3 conformance mirror's
;      D-row): the store performs NO int coercion — float exprs land
;      verbatim in int-declared fields (numeric_write_value; production-
;      conformance's pinned non-integral wealth). Frozen int() truncations
;      become explicit, declared `floor` intrinsic calls in the rules that
;      need them — never an implicit store-side rounding.
;   6. wages/value-flow is declared but UNSEEDABLE at scenario level
;      (load_edge is strength-only); it starts absent (III.11) and lands
;      via update-edge when the wage-change read path does. WAGES edge
;      strengths are inert placeholder 1s (production-conformance's own
;      posture); nothing in this pack reads wages/strength.
;   7. The `social-class/active` / `organization/active` latches are
;      declared `intensive` here against production-conformance.bscn's and
;      organization-foundation.bscn's `extensive` — a per-node state is
;      never a summed quantity. Kinds are scenario-local; no fold in this
;      pack sums a latch.
;
; "consciousness" is an ALREADY-registered system namespace
; (babylon-tick/src/lib.rs's systems set — the worldview mint's probe
; anchored under it first), so this pack changes no Rust source.

(rule consciousness/p0-position
  :material-basis "A-001 as the class-seeding law (Director flag 1): a class with material anchors (wages-paid + value-produced present) and no ternary record is positioned at the ruled unorganized rest state (0, 1, 0) — liberal hegemonic default, spec 034 A-001, THE one home (the seven scattered frozen sites are named in docs/concepts/consciousness-taxonomy.rst, not re-homed here). Data-absent classes are never positioned: UNPOSITIONED (L-ABS) — the row-19 disease's death certificate. Positioning also RECORDS dominant-worldview = LIBERAL — the rest state's strict argmax, A-001 itself, never a re-derived tie-break (pack D-record 3) — and initializes the agitation accumulator to zero so later routing rules read a positioned class's agitation as present."
  :fuel 64
  (bindings
    (binding active :field social-class/active)
    (binding wages :field social-class/wages-paid :optional :default -1)
    (binding value :field social-class/value-produced :optional :default -1)
    (binding r :field social-class/revolutionary :optional :default 0.0p)
    (binding l :field social-class/liberal :optional :default 0.0p)
    (binding f :field social-class/fascist :optional :default 0.0p))
  (when (and (= active 1)
             (>= wages 0)
             (>= value 0)
             (= (+ r (+ l f)) 0)))
  (effects
    (update-node self social-class/revolutionary (set 0.0p))
    (update-node self social-class/liberal (set 1.0p))
    (update-node self social-class/fascist (set 0.0p))
    (update-node self social-class/dominant-worldview (set WorldView/LIBERAL))
    (update-node self social-class/agitation (set 0))))
