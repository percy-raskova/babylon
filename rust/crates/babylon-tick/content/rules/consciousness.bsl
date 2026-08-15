; ConsciousnessSystem (Consequences @17.0) — the class-surface measured
; ternary (issue #588, ADR204 W10). Frozen source:
; src/babylon/engine/systems/ideology.py (ConsciousnessSystem, :94-442) with
; the routing law at src/babylon/formulas/consciousness_routing.py:288-370.
; Port posture (the design's own ruling): measured-ternary read path +
; UNPOSITIONED first — transcribe the INPUTS and the ROUTING LAW re-pointed
; at (r, l, f), NOT a cc/ni transcription; the cc/ni bridge mapping is the
; read path's spec, and it lands in a later task.
;
; TASK 1+2 SHIP: `consciousness/p0-position` (the class-seeding law, A-001)
; plus `consciousness/p8-dominant-worldview` (Task 2's measured readout —
; the hegemonic tie-break's ONE declared home). The routing update law
; (p1..p7) accretes as Task 3's rules on top of the exact qnames
; consciousness-ternary-conformance.bscn declares; p8 sorts LAST among them
; so once Task 3 lands, the readout reflects the same tick's update (D116) —
; matching the frozen step's post-update read.
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
; / `p8-…` rule — positioning ALWAYS precedes the same-tick read path, and
; a class positioned this tick is readable by this tick's later rules
; (class-emergent in the conformance world is the standing witness: p0
; positions it, p8 reads its (0, 1, 0) rest state back as LIBERAL in the
; same tick). The ordering obligation binds every later addition — keep the
; pN prefixes monotone in the frozen engine's own causality order (Task 3's
; p1..p7 slot between p0 and p8; the readout stays last so it reflects the
; same tick's update).
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
;   3. ONE-HOME LAW for dominant-worldview (controller ruling 1, fix
;      round): the dominant readout's ONLY writer is
;      consciousness/p8-dominant-worldview (below, landed Task 2) — p0
;      does NOT record dominance at positioning. Task 1 pinned the field
;      ABSENT on a freshly-positioned class as the one-home guard; Task 2
;      flipped that pin to the positive LIBERAL readout (the handoff is
;      recorded in consciousness_ternary_conformance.rs's header), and the
;      absence pins survive only for the genuinely unread
;      (class-unpositioned, employer). History, honestly
;      recorded: this pack's first draft carried a fifth p0 effect
;      writing LIBERAL here, defended as A-001's strict argmax of the
;      rest state; the controller ruled the Task-1 brief's test skeleton
;      had asserted a Task-2 artifact — a plan defect — and the write
;      came OUT. A-001's liberal-default content lives in the (0, 1, 0)
;      positioning itself; the dominance readout is a separate law with
;      its own single home. Task-2 addendum (controller ruling
;      2026-08-15, the Task-2 NEEDS_CONTEXT): the tie-break's strict
;      `< 1e-6` is transcribed verbatim — a decimal-1e-6 gap is NOT a
;      tie (strict `<` excludes the boundary; the conformance world's
;      tv-strict-gap / tv-tie-all-true pair witnesses both arms against
;      the frozen ground truth).
;   4. consciousness/simplex-epsilon has NO defconst row anywhere
;      (controller ruling 4, fix round): the frozen _EPSILON = 1e-10
;      (consciousness_routing.py:41) is inexpressible as a p/i/c literal
;      (E-LEX-023, scale <= 9, reader.rs::classify_unit_interval), so the
;      consuming rule (Task 3) binds it as the expr quotient
;      `(/ 1c 10000000000)` — bit-identical to Python's 1e-10 via one
;      correctly-rounded IEEE-754 division, dodging the lex bound
;      entirely.
;   5. Rounding law (spike 4's verdict; controller ruling 3's verbatim
;      text, the Task-3 conformance mirror's D-row): "no implicit
;      truncation at the store; the int lane holds verbatim f64; `floor`
;      is the content-explicit truncation intrinsic, unused in this
;      pack." The two fix rounds mapped the FULL law: fractional WRITES
;      land verbatim in the int lane, fractional SEEDS are loader-refused
;      (scenario.rs::attribute_value_int, exact error quoted in the
;      scenario header). The fix-round-1 escape — agitation declared
;      `intensity` to admit fractional seeds — was RETIRED by the
;      fix-round-2 ruling: the unit-interval E-EVAL-020 [0,1] ceiling is
;      tick-fatal under the frozen [0,∞) agitation domain (Task 3's
;      class-bribed vector writes 1.2 in its first tick). All three
;      machinery accumulators are therefore int-typed verbatim-f64;
;      agitation seeds at 0 (a produced accumulator, R-MEASURED), the
;      others unseeded until their writing tasks.
;   6. The wage flow rides a CLASS-SIDE field (controller ruling 2, fix
;      round): social-class/wages-received carries the per-tick wage
;      inflow as declared content — the frozen engine's incoming-WAGES
;      value_flow fold-sum (ideology.py:299-309) narrows to one declared
;      value per class per tick, exact for single-employer content. The
;      first draft's WAGES edge machinery (three edges + the
;      wages/value-flow edge deffield + social-class/wages-inbox) came
;      OUT: scenario-side edge-attribute seeding is unserved (load_edge
;      is strength-only), a gap recorded for the port train's closing
;      ADR.
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
  :material-basis "A-001 as the class-seeding law (Director flag 1): a class with material anchors (wages-paid + value-produced present) and no ternary record is positioned at the ruled unorganized rest state (0, 1, 0) — liberal hegemonic default, spec 034 A-001, THE one home (the seven scattered frozen sites are named in docs/concepts/consciousness-taxonomy.rst, not re-homed here). Data-absent classes are never positioned: UNPOSITIONED (L-ABS) — the row-19 disease's death certificate. Positioning does NOT record dominance: dominant-worldview's only writer is the read-path task's dominant rule (one-home law, pack D-record 3) — a freshly-positioned class reads it ABSENT until then. The agitation accumulator initializes to zero so later routing rules read a positioned class's agitation as present."
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
    (update-node self social-class/agitation (set 0))))

(rule consciousness/p8-dominant-worldview
  :material-basis "The measured readout: dominant pole = argmax with the ruled tie order LIBERAL > REVOLUTIONARY > FASCIST at 1e-6 (frozen: models/entities/consciousness.py:177-192, transcribed verbatim). ONE DECLARED HOME for the hegemonic tie-break — the frozen estate smeared it across five sites (digest A.5c); here it lives exactly once. UNPOSITIONED classes (sum 0) are skipped: no reading, ever."
  :fuel 96
  (bindings
    (binding active :field social-class/active)
    (binding r :field social-class/revolutionary :optional :default 0.0p)
    (binding l :field social-class/liberal :optional :default 0.0p)
    (binding f :field social-class/fascist :optional :default 0.0p)
    (binding mx :expr (if (>= r l) (if (>= r f) r f) (if (>= l f) l f)))
    (binding eps :expr 0.000001c)
    (binding dr :expr (if (> r mx) (- r mx) (- mx r)))
    (binding dl :expr (if (> l mx) (- l mx) (- mx l)))
    (binding winner :expr (if (< dl eps) WorldView/LIBERAL
                            (if (< dr eps) WorldView/REVOLUTIONARY
                                WorldView/FASCIST))))
  (when (and (= active 1) (> (+ r (+ l f)) 0)))
  (effects
    (update-node self social-class/dominant-worldview (set winner))))
