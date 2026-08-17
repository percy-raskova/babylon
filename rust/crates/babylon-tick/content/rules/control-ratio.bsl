; ControlRatioSystem (Material Base @12.0) — the guard:prisoner census and
; its two crisis/terminal-decision branches. Frozen source:
; src/babylon/engine/systems/control_ratio.py (248 lines, one step()).
; Port posture: ADR183 (structure/ordering contract, not a byte oracle) —
; conformance expecteds are measured from THIS engine, never copied from
; the frozen mirror's printed floats (control_ratio_conformance.py's own
; header makes the same point).
;
; TASK 5 SHIPPED `control-ratio/c01-prisoner-census` + `control-ratio/
; c02-publish-census` — the per-node guard/prisoner census and its
; unconditional carrier-side aggregation. TASK 6 SHIPPED `control-ratio/
; c03-crisis` — the readiness gate, the `<=` capacity boundary, and
; BLOCKER-4's guard-split emit. TASK 7 SHIPS `control-ratio/c04-terminal` —
; the ADR070-RESERVED revolution-vs-genocide branch, transcribed VERBATIM
; under the P19 emergent-class-partition cutover (Constitution IX.5 / ADR070
; / Program 19; `control_ratio.py:210-247`, `_emit_terminal_decision`). This
; task touches the Director-reserved line: TRANSCRIBE, do not redesign —
; same threshold source (`carceral/revolution-threshold`), same `>=`
; comparison, same two outcomes, closing this whole pack.
;
; Branched off MERGED `dev` (never stacked on PR A, #193). No `intrinsic`
; declaration in this file — `control-ratio.bsl` never calls `floor` (or
; any other intrinsic); the frozen `ControlRatioSystem` performs no
; truncation anywhere (`_count_enforcer_population`/`_count_prisoner_
; population_and_org` are pure sums; `avg_organization` is a plain divide,
; Task 7 scope).
;
; D116 BYTE-ORDER MAP (docs/reference/bsl-language.rst) — rules run to
; completion in ascending rule-id byte order against the same mutable
; graph, so every rule below sees every earlier rule's same-tick writes.
; Every same-tick read across this pack is a DELIBERATE reliance on that
; order, decomposition.bsl-header style:
;
;   rule            subject      reads                            writes
;   c01-prisoner-   SOCIAL_CLASS role, active, population,         enforcer-census-
;   census                       organization                      population,
;                                                                   prisoner-census-
;                                                                   population,
;                                                                   prisoner-census-
;                                                                   org-weighted
;   c02-publish-    INSTITUTION  folded c01 census fields (SAME     enforcer-population,
;   census                       TICK via nodes-fold), one          prisoner-population,
;                                :field anchor read (institution/   prisoner-org-weighted
;                                decomposition-fire-tick, unused —
;                                see D-record 2 below)
;   c03-crisis      INSTITUTION  carrier readiness/latch fields,    control-crisis-emitted,
;                                c02's SAME-TICK aggregates          control-crisis-tick,
;                                                                    CONTROL_RATIO_CRISIS
;   c04-terminal    INSTITUTION  carrier control-crisis-emitted/    terminal-decision-emitted,
;                                -tick (c03, SAME TICK), c02's       TERMINAL_DECISION
;                                SAME-TICK aggregates (prisoner-
;                                population, prisoner-org-weighted,
;                                enforcer-population)
;
; D-RECORDS THIS PACK TRANSCRIBES (full global register row lands as
; docs/reference/bsl-language.rst's D165, per the controller-routed
; obligation this task also discharges — see that row for the census
; find-first -> per-node-aggregate reformulation and its p03 inheritance,
; which is a DECOMPOSITION-side, not a control-ratio-side, fact and so is
; NOT re-stated in this Pack B header):
;   1. THE TWO-ROLE PRISONER SET — the frozen `_PRISONER_ROLES =
;      frozenset({INTERNAL_PROLETARIAT, LUMPENPROLETARIAT})`
;      (`control_ratio.py:32-37`) is TWO roles, not one (unlike
;      Decomposition's single LABOR_ARISTOCRACY target). `c01`'s prisoner
;      gate is `(or (= role SocialRole/INTERNAL_PROLETARIAT) (= role
;      SocialRole/LUMPENPROLETARIAT))` conjoined with `(= active 1)` — the
;      D127 hash-neutral operand-gate idiom, matching `p01`'s own no-`when`
;      shape: every SOCIAL_CLASS subject fires and a non-participant writes
;      zero, keeping the census fresh every tick.
;   2. THE UNCONDITIONAL CENSUS PUBLICATION — the frozen `step()` computes
;      the census (`:137-138`) only PAST the readiness gate
;      (`_terminal_decision_emitted` early-return `:124-125`,
;      `_class_decomposition_tick is None` early-return `:128-130`, the
;      delay-elapsed check `:132-134`) — three early returns stand between
;      `step()`'s own entry and its first census read. `c01`/`c02` publish
;      EVERY tick, unconditionally, with no readiness gate of any kind:
;      neither rule reads a single carrier latch. This WIDENS the
;      observable state surface relative to the frozen engine (the carrier
;      now always carries a live, current census, even in ticks/worlds
;      where the frozen engine would never have computed one at all) —
;      `c02_publishes_the_three_aggregates_unconditionally`
;      (`control_ratio_conformance.rs`) proves it directly against an
;      inline NOT-READY world (`decomposition-fired-known 0`).
;      `c02`'s own `institution/decomposition-fire-tick` binding (below)
;      is a SUBJECT-TYPE ANCHOR ONLY, never a gate — `tick.rs::
;      subject_type_of` requires at least one `:field` binding to derive a
;      carrier-anchored rule's subject type (`institution/*` -> INSTITUTION),
;      and `c02` otherwise binds nothing but `nodes`-scoped folds (its
;      three census inputs are all `SOCIAL_CLASS`-scoped, not
;      `INSTITUTION`-scoped), so it has no OTHER institution field to
;      anchor on. Reading it and never using it is the honest shape here,
;      not a design accident.
;   3. THE `<=` BOUNDARY (`c03`, LANDED Task 6) — `control_ratio.py:
;      150`'s `if prisoner_pop <= max_controllable: return` (the frozen
;      suite's own `TestControlRatioMutationKillers` class pins this exact
;      operator), transcribed verbatim as `(> prisoner-population
;      max-controllable)` in `c03`'s own `when` conjunction (the logical
;      negation of the frozen early-return, since `when` states the
;      continue-condition rather than the return-condition).
;      `control-ratio-within-capacity-conformance.bscn` seeds the boundary
;      EXACTLY (prisoner population 40 == enforcer population 10 *
;      `carceral/control-capacity` 4) — `c03_does_not_emit_at_or_below_
;      capacity` (`control_ratio_conformance.rs`) is the mutation killer: a
;      `<=` -> `<` transcription error (i.e. flipping this `when` conjunct
;      from `>` to `>=`) flips it red.
;   4. THE GUARD-SPLIT EMIT (`c03`, LANDED Task 6, BLOCKER-4) —
;      `float("inf")` (`control_ratio.py:185`'s zero-enforcer branch) and
;      `x/0` are both unrepresentable in BSL (`E-EVAL-014`/`E-EVAL-012`).
;      `control-ratio-zero-enforcer-conformance.bscn` seeds a REAL, active,
;      zero-population CARCERAL_ENFORCER class (not an absent one), and
;      `c03` guard-splits its emit in TWO independent ways to survive it:
;      (a) the `actual-ratio` BINDING itself is protected by an internal
;      `(if (= enforcer-population 0) (- 0 0c) (/ prisoner-population
;      enforcer-population)) …` — required because `:expr` bindings
;      evaluate unconditionally every tick this rule's one INSTITUTION
;      subject is visited, regardless of `when`/`guard`
;      (`decomposition.bsl`'s own p03 fuel-note precedent: "every `:expr`
;      binding evaluates eagerly and unconditionally… regardless of what
;      any later binding or guard does") — an UNPROTECTED division would
;      abort EVERY tick of the zero-enforcer world with `E-EVAL-012`, not
;      merely the crisis tick; (b) the EFFECTS themselves guard-split via
;      two `(guard (> enforcer-population 0) …)` / `(guard (=
;      enforcer-population 0) …)` forms, selecting which payload the
;      emitted event actually carries: the ratio keys
;      (`actual-ratio`/`control-ratio`) when `enforcer-population > 0`, the
;      SAME payload MINUS those two keys when `enforcer-population == 0` —
;      loud absence, not a fabricated number. Mutation evidence
;      (`c03_omits_the_ratio_keys_when_there_are_no_enforcers` plus the
;      dedicated mutation exercise recorded in this commit's own message):
;      dropping mechanism (a)'s `if`-protector (not merely (b)'s
;      guard-split) is what reproduces the frozen `float("inf")`
;      unrepresentability as a NAMED `E-EVAL-012` test failure rather than
;      a silent no-emit.
;   5. THE NUMERIC `outcome` ENCODING (`c04`, LANDED Task 7, ADR070/
;      BLOCKER-5) — `emit` carries no string payload values at all (`Str`
;      has no `<payload-item>` production); the frozen `outcome` string
;      ("revolution"/"genocide", `control_ratio.py:222,228`) becomes a
;      numeric `(outcome 1)` = revolution / `(outcome 0)` = genocide, with
;      `narrative_hint` dropped (the same class of omission as
;      Decomposition's own D-record 5). `control-ratio-conformance.bscn`
;      (organization 0.2, genocide) and `control-ratio-revolution-
;      conformance.bscn` (organization 0.6, revolution) make the mapping
;      mutation-provable. Payload key order transcribed verbatim from
;      `:239-245`: `outcome`, `avg_organization`, `revolution_threshold`,
;      `prisoner_population`, `enforcer_population` (`narrative_hint`
;      dropped, five keys not six). THE RESERVED BRANCH ITSELF (`:222,228`):
;      `avg_organization >= revolution_threshold` -> REVOLUTION, else ->
;      GENOCIDE — transcribed as the SAME `>=` comparison against the SAME
;      `carceral/revolution-threshold` source, two `guard`-split emits
;      differing ONLY in the numeric `outcome`, per the Director-reserved-
;      line discipline (Constitution IX.5 / ADR070 / Program 19; this
;      train's own RESERVED LINE global constraint: transcribe verbatim
;      under a P19-cutover-pending D-record; any change to WHICH
;      organization measure decides, or to the partition the roles come
;      from, escalates to the Director — this port changes neither).
;      `avg-organization`'s own division-by-zero protector (`(if (=
;      prisoner-population 0) (- 0 0c) (/ prisoner-org-weighted
;      prisoner-population))`) is ALSO a verbatim transcription, not a new
;      defensive measure: `control_ratio.py:171`'s own `avg_organization =
;      prisoner_org_sum / prisoner_pop if prisoner_pop > 0 else 0.0` carries
;      the identical ternary — BLOCKER-4's "`:expr` bindings evaluate
;      eagerly every tick regardless of `when`/`guard`" mechanism (c03's own
;      precedent) is why it must be an explicit `if`, not a bare `/`, in
;      BSL specifically (the frozen ternary is provably dead code within its
;      OWN single `step()` call — c04's carrier-anchored per-tick evaluation
;      is the general reason a future world COULD reach the zero branch).
;      Honest caveat, checked directly (mutation exercise, not asserted):
;      NONE of this pack's six fixtures ever actually has `prisoner-
;      population == 0` at any tick `c04` evaluates — `c02` republishes the
;      real (nonzero) census the SAME tick, ahead of `c04` in byte order, in
;      every scenario/fixture this pack loads. Replacing the protected
;      `:expr` with a bare `(/ prisoner-org-weighted prisoner-population)`
;      leaves all 22 tests in `control_ratio_conformance.rs` green — the
;      protector is NOT mutation-provable by this task's own fixture set
;      (unlike `c03`'s own BLOCKER-4 protector, which the zero-enforcer
;      world DOES reach). Kept anyway for :171's own transcription fidelity
;      and as the same defensive idiom `c03` established; recorded honestly
;      rather than claimed as proven.
;   6. THE CROSS-PACK BYTE-ORDER INVERSION — `control-ratio/*` sorts
;      BEFORE `decomposition/*` in ascending rule-id byte order (D100's
;      class, `docs/superpowers/plans/2026-08-17-decomposition-
;      controlratio-port.md` §5), inverting the frozen @11.0-then-@12.0
;      system order. Benign here BY CONSTRUCTION, not by luck: every one
;      of this whole Pack B's four scenarios SEEDS
;      `decomposition-fire-tick`/`-fired-known`/`decomposition-complete`
;      directly rather than relying on a co-loaded `decomposition/*`
;      pack to write them the same tick — the "post-decomposition carrier
;      state" design each scenario's own header states. The authoring
;      constraint this seeding discipline exists to satisfy: NO Pack B
;      scenario may set `carceral/control-ratio-delay` to 0 while ALSO
;      relying on `decomposition-fire-tick` being written BY
;      `decomposition/p03-trigger` that same tick — every scenario in
;      this pack seeds it instead, so the hazard never engages. (The
;      executable form of this constraint — a co-loaded-pack test proving
;      an UNSEEDED zero-delay world does NOT crisis on the firing tick —
;      is Task 8's `carceral-arc-conformance` scope, not this pack's own
;      scenarios, none of which co-load `decomposition/*` at all.)

(rule control-ratio/c01-prisoner-census
  :material-basis "Per-node guard/prisoner census, reformulating the frozen engine's two graph-scope loops (_count_enforcer_population, _count_prisoner_population_and_org, control_ratio.py:53-85) as a per-node gated write (plan §2's fold-body compound-expression restriction: the role/active filter and the pop*org PRODUCT cannot live in c02's carrier-side fold, so both live here, D138/p01 precedent). Publishes THREE per-node fields: enforcer-census-population (role==CARCERAL_ENFORCER && active==1), prisoner-census-population and prisoner-census-org-weighted (pop*org PRE-MULTIPLIED per-node, :84 — the two-step sum-then-divide c04 needs, Task 7) for (role==INTERNAL_PROLETARIAT || role==LUMPENPROLETARIAT) && active==1. No when clause — a non-participant writes zero to all three (D127 hash-neutral idiom)."
  :fuel 43
  (bindings
    (binding role :field social-class/role)
    (binding active :field social-class/active)
    (binding population :field social-class/population)
    (binding organization :field social-class/organization)
    (binding enforcer-gate :expr (and (= role SocialRole/CARCERAL_ENFORCER) (= active 1)))
    (binding prisoner-gate :expr (and (or (= role SocialRole/INTERNAL_PROLETARIAT)
                                          (= role SocialRole/LUMPENPROLETARIAT))
                                      (= active 1)))
    (binding enforcer-contribution :expr (if enforcer-gate population 0))
    (binding prisoner-contribution :expr (if prisoner-gate population 0))
    (binding prisoner-org-contribution :expr (if prisoner-gate
                                                  (* population organization)
                                                  (- 0 0c))))
  (when #t)
  (effects
    (update-node self social-class/enforcer-census-population (set enforcer-contribution))
    (update-node self social-class/prisoner-census-population (set prisoner-contribution))
    (update-node self social-class/prisoner-census-org-weighted (set prisoner-org-contribution))))

(rule control-ratio/c02-publish-census
  :material-basis "Carrier-side aggregation, folding c01's three SAME-TICK per-node census-contribution fields (D116) onto the carrier UNCONDITIONALLY — D-record 2 above: the frozen engine gates its own census computation behind three early returns this port does not reproduce here (they belong to c03/c04, Task 6-7, not to the census itself). Bare-accessor fold bodies only (field_ref_for's compound-body refusal, D138): each of the three folds is `(fold sum (nodes NodeType/SOCIAL_CLASS) (field-of it <field>))`, matching decomposition.bsl's p03 shape exactly. The `institution/decomposition-fire-tick` binding is a SUBJECT-TYPE ANCHOR ONLY (tick.rs::subject_type_of requires >=1 :field binding to derive INSTITUTION) — never read again, never gating anything; D-record 2 states this explicitly so a future reader does not mistake it for a dropped readiness check."
  :fuel 64
  (bindings
    (binding decomposition-fire-tick :field institution/decomposition-fire-tick)
    (binding enforcer-population :expr (fold sum (nodes NodeType/SOCIAL_CLASS)
                                             (field-of it social-class/enforcer-census-population)))
    (binding prisoner-population :expr (fold sum (nodes NodeType/SOCIAL_CLASS)
                                             (field-of it social-class/prisoner-census-population)))
    (binding prisoner-org-weighted :expr (fold sum (nodes NodeType/SOCIAL_CLASS)
                                               (field-of it social-class/prisoner-census-org-weighted))))
  (when #t)
  (effects
    (update-node self institution/enforcer-population (set enforcer-population))
    (update-node self institution/prisoner-population (set prisoner-population))
    (update-node self institution/prisoner-org-weighted (set prisoner-org-weighted))))

(rule control-ratio/c03-crisis
  :material-basis "The crisis gate (control_ratio.py:119-159), subject INSTITUTION. `when` conjoins all five frozen early returns (c03 has no unconditional aggregate of its own, unlike p03): the readiness gate (:128-134), prisoner-population > 0 (:141), the `<=` boundary as (> prisoner-population max-controllable) (:150, D-record 3), and the not-yet-emitted latch (:154). max-controllable = enforcer-population * control-capacity (:147). BLOCKER-4/D-record 4: actual-ratio's (if (= enforcer-population 0) ...) protector guards the BINDING itself (bindings evaluate unconditionally every tick); effects guard-split the emit on the same condition, omitting actual-ratio/control-ratio when enforcer-population == 0 (loud absence, not inf). control-ratio duplicates actual-ratio verbatim (:198-199, port-as-is). capacity-threshold casts control-capacity to Real via the c01 (- x 0c) idiom (float(control_capacity), :200). narrative_hint dropped (D-record 5). Emit first, then the two latch writes (:154-159)."
  :fuel 70
  (bindings
    (binding decomposition-fired-known :field institution/decomposition-fired-known)
    (binding decomposition-fire-tick :field institution/decomposition-fire-tick)
    (binding control-crisis-emitted :field institution/control-crisis-emitted)
    (binding enforcer-population :field institution/enforcer-population)
    (binding prisoner-population :field institution/prisoner-population)
    (binding tick :tick)
    (binding control-ratio-delay :const carceral/control-ratio-delay)
    (binding control-capacity :const carceral/control-capacity)
    (binding ready :expr (and (= decomposition-fired-known 1)
                              (>= tick (+ decomposition-fire-tick control-ratio-delay))))
    (binding max-controllable :expr (* enforcer-population control-capacity))
    (binding over-capacity :expr (> prisoner-population max-controllable))
    (binding over-capacity-by :expr (- prisoner-population max-controllable))
    (binding actual-ratio :expr (if (= enforcer-population 0)
                                    (- 0 0c)
                                    (/ prisoner-population enforcer-population)))
    (binding capacity-threshold :expr (- control-capacity 0c)))
  (when (and ready
             (> prisoner-population 0)
             over-capacity
             (= control-crisis-emitted 0)))
  (effects
    (guard (> enforcer-population 0)
      (emit EventType/CONTROL_RATIO_CRISIS
        (enforcer-population enforcer-population)
        (prisoner-population prisoner-population)
        (control-capacity control-capacity)
        (max-controllable max-controllable)
        (actual-ratio actual-ratio)
        (over-capacity-by over-capacity-by)
        (control-ratio actual-ratio)
        (capacity-threshold capacity-threshold)))
    (guard (= enforcer-population 0)
      (emit EventType/CONTROL_RATIO_CRISIS
        (enforcer-population enforcer-population)
        (prisoner-population prisoner-population)
        (control-capacity control-capacity)
        (max-controllable max-controllable)
        (over-capacity-by over-capacity-by)
        (capacity-threshold capacity-threshold)))
    (update-node self institution/control-crisis-emitted (set 1))
    (update-node self institution/control-crisis-tick (set tick))))

(rule control-ratio/c04-terminal
  :material-basis "ADR070-RESERVED BRANCH (control_ratio.py:210-247, _emit_terminal_decision), transcribed VERBATIM under the P19 cutover (Constitution IX.5 / ADR070 / Program 19) -- same threshold source, same >= comparison, same two outcomes; changes neither WHICH measure decides nor the role partition. Subject INSTITUTION. `when` flattens the frozen early-return gates (:124-125, :154-159, :166-168): crisis already fired, decision not yet emitted, delay elapsed. avg-organization = prisoner-org-weighted / prisoner-population (:171), guarded by :171's OWN ternary (`if prisoner_pop > 0 else 0.0`) against eager :expr evaluation -- dead code in the frozen step(), defensive parity with c03 here (D-record 5). THE BRANCH, verbatim (:222,228): >= threshold -> REVOLUTION else GENOCIDE. D-record 5/BLOCKER-5: no Str payload value in BSL, so outcome becomes numeric (outcome 1)=revolution / (outcome 0)=genocide, narrative_hint dropped; keys in :239-245 order. Then the one-time latch (:173)."
  :fuel 46
  (bindings
    (binding control-crisis-emitted :field institution/control-crisis-emitted)
    (binding control-crisis-tick :field institution/control-crisis-tick)
    (binding terminal-decision-emitted :field institution/terminal-decision-emitted)
    (binding enforcer-population :field institution/enforcer-population)
    (binding prisoner-population :field institution/prisoner-population)
    (binding prisoner-org-weighted :field institution/prisoner-org-weighted)
    (binding tick :tick)
    (binding terminal-decision-delay :const carceral/terminal-decision-delay)
    (binding revolution-threshold :const carceral/revolution-threshold)
    (binding ready :expr (and (= control-crisis-emitted 1)
                              (>= tick (+ control-crisis-tick terminal-decision-delay))))
    (binding avg-organization :expr (if (= prisoner-population 0)
                                        (- 0 0c)
                                        (/ prisoner-org-weighted prisoner-population))))
  (when (and ready (= terminal-decision-emitted 0)))
  (effects
    (guard (>= avg-organization revolution-threshold)
      (emit EventType/TERMINAL_DECISION
        (outcome 1)
        (avg-organization avg-organization)
        (revolution-threshold revolution-threshold)
        (prisoner-population prisoner-population)
        (enforcer-population enforcer-population)))
    (guard (< avg-organization revolution-threshold)
      (emit EventType/TERMINAL_DECISION
        (outcome 0)
        (avg-organization avg-organization)
        (revolution-threshold revolution-threshold)
        (prisoner-population prisoner-population)
        (enforcer-population enforcer-population)))
    (update-node self institution/terminal-decision-emitted (set 1))))
