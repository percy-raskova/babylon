; Phase 1 carrier-load probe (#491 T4, ADR194 R1) -- the K=16 wealth-mass
; ladder, tau, eta and the 15 cuts declared in
; content/scenarios/vitality-attrition-conformance.bscn are INERT at this
; phase: no rule reads them yet (see the scenario's own header for the
; full citation chain, including the T4.3 Currency-drain spike's verdict).
;
; This file exists ONLY because the rule pipeline refuses a zero-rule
; content set outright (rule_pipeline.rs's §2.2 check -- "a content set
; needs at least one (rule …) top-form, found 0"), so the carrier's own
; scenario needs SOME rule to exercise load-and-tick at all for
; `tick_goldens.rs`'s pin. The never-firing-probe idiom is
; production_conformance.rs's own precedent, reused verbatim here from
; content/rules/worldview.bsl (the WorldView mint's identical shape): the
; guard is false for every legal population, so `fired == 0` and
; `before == after` hold by construction. What the byte pin guards is the
; substrate LOAD of the carrier scenario -- the sixteen masses, fifteen
; cuts, eta, tau and the Currency-lane re-seed -- not this rule's own
; (nonexistent) effect.
;
; T5 (Phase 3a -- the dual measure, P(S|A), and the horizon identity) and
; T6 (Phase 3b -- Grinding Attrition, kappa) are the tasks that give this
; namespace its first REAL rule. This probe is a placeholder anchoring the
; carrier's own load path, not a commitment to this file's final shape --
; a future task may extend it in place or replace it outright.
(rule vitality/wealth-mass-carrier-probe
  :material-basis "load-only smoke for the K=16 wealth-mass carrier: the carrier's own pins are the substrate-load hash and this crate's vitality_attrition_conformance.rs posture suite, not this rule's effects"
  :fuel 8
  (bindings (binding population :field social-class/population))
  (when (< population 0))
  (effects
    (update-node self social-class/population (set population))))
