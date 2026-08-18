; The D69/§6.2 "a skipped draw shifts nothing" row (#576 Task 5): mirrors
; src/babylon/engine/systems/doctrine.py:527-537's real `needs_roll`
; guard — an org whose needs_roll is false never calls rng.random(); under a
; STREAMED rng that skip would shift every later org's draw. Under this
; KEYED design, a subject whose guard passes must draw the SAME value
; whether or not another subject's guard also passed — there is no shared
; stream position to perturb.
;
; SAME rule id (domain) as rng_keyed_draw.bsl on purpose: class-b's
; stable_key is identical whether class-a's guard passes (rng_keyed_draw.bsl)
; or is suppressed (this fixture), so its draw must be bit-identical
; whichever fixture ran (r9_chapters.rs::c14_rng_draw).
(rule demo/rng-keyed-draw
  :material-basis "a guard-suppressed draw must not shift another subject's draw (D69)"
  :fuel 64
  (bindings
    (binding needs-roll :field social-class/needs-roll))
  (when (= needs-roll 1))
  (effects
    (update-node self social-class/draw (set (rng-draw 0)))))
