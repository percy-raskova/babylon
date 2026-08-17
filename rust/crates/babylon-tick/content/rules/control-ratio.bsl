; ControlRatioSystem (Material Base @12.0) — the guard:prisoner census and
; its two crisis/terminal-decision branches. Frozen source:
; src/babylon/engine/systems/control_ratio.py (248 lines, one step()).
; Port posture: ADR183 (structure/ordering contract, not a byte oracle) —
; conformance expecteds are measured from THIS engine, never copied from
; the frozen mirror's printed floats (control_ratio_conformance.py's own
; header makes the same point).
;
; TASK 5 SHIP (this file's ONLY content today): `control-ratio/c01-
; prisoner-census` + `control-ratio/c02-publish-census` — the per-node
; guard/prisoner census and its unconditional carrier-side aggregation.
; `control-ratio/c03-crisis` (Task 6) and `control-ratio/c04-terminal`
; (Task 7, the ADR070-RESERVED branch) are NOT this task's scope — this
; header nonetheless carries the FULL `c01 -> c02 -> c03 -> c04` byte-order
; map and reserves D-record rows for all six Pack B topics now (the
; "reserve rows" convention `decomposition.bsl`'s own Task 2 commit
; established: Task 2's plan step explicitly reserved rows for p03/p04-p06
; topics before those rules existed).
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
;   c03-crisis      INSTITUTION  (Task 6) carrier readiness/latch   (Task 6) latches +
;                                fields, c02's SAME-TICK             CONTROL_RATIO_CRISIS
;                                aggregates
;   c04-terminal    INSTITUTION  (Task 7) carrier latches, c02's    (Task 7) latch +
;                                aggregates                          TERMINAL_DECISION
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
;   3. THE `<=` BOUNDARY (`c03`, RESERVED for Task 6) — `control_ratio.py:
;      150`'s `if prisoner_pop <= max_controllable: return` (the frozen
;      suite's own `TestControlRatioMutationKillers` class pins this exact
;      operator). `control-ratio-within-capacity-conformance.bscn` seeds
;      the boundary EXACTLY (prisoner population 40 == enforcer population
;      10 * `carceral/control-capacity` 4) so a `<=` -> `<` mutation is
;      provable the moment `c03` lands.
;   4. THE GUARD-SPLIT EMIT (`c03`, RESERVED for Task 6, BLOCKER-4) —
;      `float("inf")` (`control_ratio.py:185`'s zero-enforcer branch) and
;      `x/0` are both unrepresentable in BSL (`E-EVAL-014`/`E-EVAL-012`).
;      `control-ratio-zero-enforcer-conformance.bscn` seeds a REAL, active,
;      zero-population CARCERAL_ENFORCER class (not an absent one) so
;      `c03` must guard-split its emit: the payload MINUS
;      `actual-ratio`/`control-ratio` when `enforcer-population == 0` —
;      loud absence, not a fabricated number.
;   5. THE NUMERIC `outcome` ENCODING (`c04`, RESERVED for Task 7,
;      ADR070/BLOCKER-5) — `emit` carries no string payload values at all
;      (`Str` has no `<payload-item>` production); the frozen `outcome`
;      string ("revolution"/"genocide", `control_ratio.py:222,228`)
;      becomes a numeric `(outcome 1)` = revolution / `(outcome 0)` =
;      genocide, with `narrative_hint` dropped (the same class of omission
;      as Decomposition's own D-record 5). `control-ratio-conformance.bscn`
;      (organization 0.2, genocide) and `control-ratio-revolution-
;      conformance.bscn` (organization 0.6, revolution) make the mapping
;      mutation-provable the moment `c04` lands.
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
