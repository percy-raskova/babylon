; ProductionSystem (Material Base @3.0) — "The Soil": workers produce value
; from labor x biocapacity, routed by the Amin/Wallerstein imperial-bribe
; model (RESERVED LINE, Constitution IX.5 — the role partition and the
; WAGES-edge employer lookup are the Director's ideological line,
; transcribed EXACTLY, never touched).
;
; Frozen source: src/babylon/engine/systems/production.py (268 lines, one
; step() over two loops). Port-as-is (Director ruling): frozen defects are
; transcribed and D-recorded, never silently repaired. The frozen engine is
; a structure/ordering contract, NOT a byte oracle (ADR183) — conformance
; expecteds are measured from THIS BSL engine and pinned in
; production_conformance.rs, not copied from the frozen mirror's printed
; floats.
;
; FOUR RULES, byte-ordered `p1-direct-production < p2-employed-routing <
; p3-employed-fallback < p4-extraction-intensity` — deliberately relying on
; D116's recorded cross-rule divergence (docs/reference/bsl-language.rst):
; today's run_once_into/TickSession::advance run each rule in a content set
; to COMPLETION before the next starts, against the SAME mutable graph, so a
; later rule at the same anchor position sees an EARLIER rule's
; already-applied writes from THIS tick. p4 reads `social-class/
; production-value`, which p1-p3 write EARLIER the same tick — this pack
; RELIES on that divergence rather than fighting it, the same way
; territory.bsl's own five-rule chain does (D120 is that pack's version of
; this same record).
;
; The four rules split this way because (a) subject type derives from
; `:field` namespaces (SOCIAL_CLASS for p1-p3, TERRITORY for p4), and (b)
; p2's effect ref `(select-max (neighbors self EdgeType/WAGES :in …) 1)`
; ABORTS on an employer-less subject (E-EVAL-021 class), so employer
; existence must be split at the `when` level: p2 guards `(exists …)`, p3
; guards `(not (exists …))` — `not` is served (grammar.rs:651), and `if`
; evaluates only the taken branch (§4.1, evaluator.rs:18), which is what
; makes the exists-guarded `field-of (select-max …)` bindings below legal.
;
; D-RECORDS this pack transcribes (full text + file:line evidence in the
; Task 5 register rows, docs/reference/bsl-language.rst):
;   1. Byte order relies on D116's cross-rule same-tick visibility — p4
;      reads p1-p3's already-applied writes to `production-value`.
;   2. `social-class/active` is an int 0/1 latch — the
;      `social-class/active`/`organization/active` precedent, no bool store
;      path on the live `.bscn` pipeline.
;   3. `economy/base-labor-power-annual` at `1.0c` sits exactly at the
;      coefficient boundary [0,1] — legal today, fragile under modding (the
;      define's own domain is [0,∞), unbounded above).
;   4. The `fips_code`/`county_fips` dead tensor-registry branch
;      (production.py:160-172) is OMITTED entirely — provably unreachable,
;      nothing to transcribe (no BSL construct exists for an external
;      keyed-cache lookup in any case).
;   5. `social-class/production-value` is a per-node REFORMULATION of the
;      frozen `la_production` graph-scope dict (production.py:129,194) —
;      keyed by worker node id in the frozen engine, an ordinary node field
;      here. The write WIDENS to all three producer rules (p1/p2/p3), not
;      just the employed branch the frozen ledger covers; the read this
;      port's own p4 performs stays exactly as narrow as the frozen
;      `la_production.get(edge.target_id, ...)` call already is, since only
;      LA workers ever have an incoming WAGES edge.
;   6. Tiebreak divergence: the frozen `_find_tenancy_target`/`_find_employer`
;      return the FIRST match in `query_edges` iteration (insertion) order;
;      this language's `select-max` (D46, constant score) tiebreaks by D45
;      ascending-id. `worker-pp-two-lands` (two TENANCY edges) pins the D45
;      winner (`t-alpha`, the lower NodeId) for its OWN bio-ratio
;      computation.
;   7. Extraction-intensity multi-tenancy double-count: because p4's fold
;      reads `production-value` off EVERY TENANCY-incident neighbour of a
;      territory, a producer holding TWO TENANCY edges (worker-pp-two-lands)
;      contributes its single computed production-value to BOTH
;      territories' totals — a genuine divergence from the frozen engine's
;      single-territory `_find_tenancy_target` attribution (which only ever
;      credits the FIRST-found territory). Measured, not assumed: the frozen
;      mirror's own t-beta extraction_intensity (0.009615384615384616,
;      excluding worker-pp-two-lands) diverges from this pack's measured
;      t-beta value, which includes it.
;   8. No-defaults: every fixture seeds every field every rule reads; the
;      frozen `attrs.get(k, default)` affordance is not transcribable.
;   9. Hash-neutral no-op writes: an inactive producer (worker-la-idle)
;      still fires p2 (its `when` guard is role+employer-existence only,
;      not `active`), writing `(add 0)`/`(set 0)` — the D127-class idiom —
;      where the frozen engine's own `continue` at the top of the loop
;      skips the iteration (and therefore any write) entirely.
;
; "production" is a genuinely NEW registered system (babylon-tick/src/lib.rs)
; — unlike Territory, which inherited a pre-existing placeholder from the
; query-evaluation train.

(rule production/p1-direct-production
  :material-basis "Fundamental Theorem plumbing: the periphery proletariat produces value with its own labor-power on land it occupies (produced = weekly labor-power x population x biocapacity ratio, production.py:151-175) and, as the direct producer with no wage relation, keeps its own product (production.py:179-181)."
  :fuel 160
  (bindings
    (binding role :field social-class/role)
    (binding active :field social-class/active)
    (binding population :field social-class/population)
    (binding annual :const economy/base-labor-power-annual)
    (binding weeks :const timescale/weeks-per-year)
    (binding bio :expr (if (exists (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY))
                           (field-of (select-max (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY) 1)
                                     territory/biocapacity)
                           (- 0 0c)))
    (binding max-bio :expr (if (exists (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY))
                               (field-of (select-max (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY) 1)
                                         territory/max-biocapacity)
                               (- 0 0c)))
    (binding bio-ratio :expr (if (> max-bio 0) (/ bio max-bio) (- 0 0c)))
    (binding produced :expr (* (* (/ annual weeks) population) bio-ratio))
    (binding output :expr (if (= active 1) produced (- 0 0c))))
  (when (= role SocialRole/PERIPHERY_PROLETARIAT))
  (effects
    (update-node self social-class/wealth (add output))
    (update-node self social-class/production-value (set output))))

(rule production/p2-employed-routing
  :material-basis "Amin/Wallerstein: the labor aristocracy's product is appropriated by the employing bourgeoisie through the WAGES relation (production.py:184-194). RESERVED LINE -- the routing structure is the Director's ideological line, transcribed exactly."
  :fuel 192
  (bindings
    (binding role :field social-class/role)
    (binding active :field social-class/active)
    (binding population :field social-class/population)
    (binding annual :const economy/base-labor-power-annual)
    (binding weeks :const timescale/weeks-per-year)
    (binding bio :expr (if (exists (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY))
                           (field-of (select-max (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY) 1)
                                     territory/biocapacity)
                           (- 0 0c)))
    (binding max-bio :expr (if (exists (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY))
                               (field-of (select-max (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY) 1)
                                         territory/max-biocapacity)
                               (- 0 0c)))
    (binding bio-ratio :expr (if (> max-bio 0) (/ bio max-bio) (- 0 0c)))
    (binding produced :expr (* (* (/ annual weeks) population) bio-ratio))
    (binding output :expr (if (= active 1) produced (- 0 0c))))
  (when (and (= role SocialRole/LABOR_ARISTOCRACY)
             (exists (neighbors self EdgeType/WAGES :in NodeType/SOCIAL_CLASS))))
  (effects
    (update-node (select-max (neighbors self EdgeType/WAGES :in NodeType/SOCIAL_CLASS) 1)
                 social-class/wealth
                 (add output))
    (update-node self social-class/production-value (set output))))

(rule production/p3-employed-fallback
  :material-basis "The frozen fallback: an employed-role producer with no employer keeps its own product (production.py:196-198)."
  :fuel 160
  (bindings
    (binding role :field social-class/role)
    (binding active :field social-class/active)
    (binding population :field social-class/population)
    (binding annual :const economy/base-labor-power-annual)
    (binding weeks :const timescale/weeks-per-year)
    (binding bio :expr (if (exists (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY))
                           (field-of (select-max (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY) 1)
                                     territory/biocapacity)
                           (- 0 0c)))
    (binding max-bio :expr (if (exists (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY))
                               (field-of (select-max (neighbors self EdgeType/TENANCY :out NodeType/TERRITORY) 1)
                                         territory/max-biocapacity)
                               (- 0 0c)))
    (binding bio-ratio :expr (if (> max-bio 0) (/ bio max-bio) (- 0 0c)))
    (binding produced :expr (* (* (/ annual weeks) population) bio-ratio))
    (binding output :expr (if (= active 1) produced (- 0 0c))))
  (when (and (= role SocialRole/LABOR_ARISTOCRACY)
             (not (exists (neighbors self EdgeType/WAGES :in NodeType/SOCIAL_CLASS)))))
  (effects
    (update-node self social-class/wealth (add output))
    (update-node self social-class/production-value (set output))))

(rule production/p4-extraction-intensity
  :material-basis "Metabolic coupling: extraction intensity = produced value against the territory's max biocapacity, clamped to [0,1] (production.py:246-268). Reads production-value written by p1-p3 THIS TICK -- the pack relies on D116 byte-order cross-rule visibility (see pack D-1)."
  :fuel 128
  (bindings
    (binding max-bio :field territory/max-biocapacity)
    (binding total :expr (if (exists (neighbors self EdgeType/TENANCY :in NodeType/SOCIAL_CLASS))
                             (fold sum (neighbors self EdgeType/TENANCY :in NodeType/SOCIAL_CLASS)
                                   (field-of it social-class/production-value))
                             (- 0 0c)))
    (binding ratio :expr (if (> max-bio 0) (/ total max-bio) (- 0 0c)))
    (binding clamped :expr (if (< ratio 1) ratio (- 1 0c))))
  (when #t)
  (effects
    (update-node self territory/extraction-intensity (set clamped))))
