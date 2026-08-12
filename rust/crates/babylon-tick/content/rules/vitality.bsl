; VitalitySystem (Material Base @1.0) — The Drain and The Reaper.
;
; Living costs wealth. A class burns subsistence every tick in proportion to
; its numbers and to the standard of living its position requires, and a
; block that can no longer cover its own reproduction stops existing.
;
; ONE rule, not three. §4.2: rules within one system position observe the
; same pre-state, so a three-rule decomposition would have to restate the
; drain algebra in each downstream rule. The `:expr` bindings of R9 chapter
; C7 name the intermediates once instead.
;
; WHAT THIS RULE DELIBERATELY DOES NOT DO — Grinding Attrition, the frozen
; system's Phase 2. Two independent blockers, recorded in
; docs/superpowers/plans/2026-08-10-vitality-bsl-rule-pack.md §6:
;
;   1. RIDER (Territory port train, P27 PR B, Task 8): `deaths =
;      floor(population × rate)` needing a Real→Int demotion is STALE as a
;      blocker — `floor` landed under ADR188 Row 2
;      (`declarations.rs::DECLARABLE_INTRINSICS`, "pinned libm crate r21",
;      `f64::floor` exact IEEE-754) and clears content, load, and
;      evaluation end to end through `run_once`/`run_once_into`
;      (`floor_intrinsic_e2e.rs`; `territory/p2-eviction-pipeline`'s own
;      `displaced` binding and `territory/p4-camp-decay`'s population
;      decay are the first PRODUCTION consumers). This header predates
;      that landing and was not updated alongside it — corrected here,
;      not because Grinding Attrition itself is now unblocked (blocker 2
;      below still stands on its own), but so a future reader does not
;      re-derive "floor is missing" as a fact about the language from a
;      stale comment in the same file the proof now lives beside.
;   2. The rate itself — deficit × (attrition_base_factor + inequality),
;      clamped — is a stipulated functional form with a tuned knob, and it
;      is the same construct as ADR173's P(S|A): the mass of the
;      within-class wealth distribution that fails to clear subsistence.
;      ADR175 puts its emergent re-derivation behind a per-family Director
;      review, which has not happened.
;
; So a world where the frozen engine's attrition would kill is a world this
; rule under-kills. The conformance scenario shipped beside it is chosen so
; the frozen engine kills nobody, and nothing wires this rule into an
; always-on path.
(rule vitality/subsistence-and-death
  :material-basis "a class reproduces itself out of its own wealth every tick, at a cost set by its numbers and by the standard of living its position in production requires; a block that cannot meet that cost ceases to exist as a class"
  :fuel 512
  (bindings
    (binding active :field social-class/active)
    (binding population :field social-class/population)
    (binding wealth :field social-class/wealth)
    (binding subsistence-multiplier :field social-class/subsistence-multiplier)
    (binding s-bio :field social-class/s-bio)
    (binding s-class :field social-class/s-class)
    (binding base-subsistence :const economy/base-subsistence)
    (binding death-threshold :const economy/death-threshold)
    ; The frozen engine's association order, transcribed exactly:
    ; (base_subsistence * population) * multiplier. `<arith>` is strictly
    ; binary (E-PARSE-040), so the source states it rather than implying it,
    ; and binary64 reproduces the same double.
    (binding cost :expr (* (* base-subsistence population) subsistence-multiplier))
    ; The frozen engine writes max(0.0, wealth - cost): it destroys the part
    ; a class cannot pay rather than carrying a debt. That is a modelling
    ; choice of the reference and part of the structure contract, so this
    ; transcribes it — stated positively, as what the class actually hands
    ; over: subsistence, or everything it has, whichever is less.
    ;
    ; Written this way and not as `(if (> (- wealth cost) 0) … 0)` for two
    ; reasons. §3.10's rider slate row 5 declines a scalar min/max precisely
    ; so a saturation stays legible in the source rather than hiding in an
    ; operator — and §1.5 admits NO bare non-integer literal, so the zero
    ; branch of that form would be an `Int` where the other branch is a
    ; `Real`: two static types under one `if`, in a language that declares
    ; no coercions (§3.1). Subtracting what was paid keeps one type
    ; throughout and lands on exactly 0.0 when a class is wiped out.
    (binding paid :expr (if (> wealth cost) cost wealth))
    (binding drained :expr (- wealth paid))
    (binding consumption-needs :expr (+ s-bio s-class)))
  ; The two `continue`s at the top of the frozen loop.
  (when (and (= active 1) (> population 0)))
  (effects
    (update-node self social-class/wealth (set drained))
    ; The Reaper. `is_extinct` (population <= 0 after attrition) cannot fire
    ; here — the guard above already excludes it and no attrition decrement
    ; runs — so the two surviving causes remain, both of which require a
    ; block of one and both of which set the same two fields:
    ;   wealth_threshold: drained < death_threshold  (the zombie failsafe)
    ;   starvation:       drained < s_bio + s_class
    (guard (and (= population 1)
                (or (< drained death-threshold)
                    (< drained consumption-needs)))
      (update-node self social-class/active (set 0))
      (update-node self social-class/population (set 0))
      ; The frozen payload's `cause` string does not travel: §2.8 admits no
      ; string in a payload and §1.5 admits string literals at
      ; :material-basis and vector ids only (E-PARSE-010). A discriminant
      ; would need a registered closed enum, which is a vocabulary addition
      ; and therefore spec-first. It stays recoverable from the payload:
      ; drained < death_threshold means wealth_threshold, else starvation.
      (emit EventType/ENTITY_DEATH
        (entity-id self)
        (wealth drained)
        (consumption-needs consumption-needs)
        (s-bio s-bio)
        (s-class s-class)))))
