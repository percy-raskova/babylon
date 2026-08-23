; The rng-draw keyed-draw conformance fixture (#576 Task 5, plan §3.2/§3.3):
; every subject draws unconditionally. Paired with
; rng_keyed_draw_guarded.bsl — SAME rule id (domain), differing only in
; whether class-a's draw fires — for the D69/§6.2 "a skipped draw shifts
; nothing" row (r9_chapters.rs::c14_rng_draw).
(rule demo/rng-keyed-draw
  :role mechanic
  :evidence derived
  :material-basis "the rng-draw keyed-draw conformance vector: every subject draws unconditionally"
  :fuel 64
  (bindings
    ; :field binding present ONLY so the subject type (social-class) is
    ; inferable (tick.rs::subject_type_of) — unread by the guard, which
    ; fires unconditionally, on purpose (this is the CONTROL fixture).
    (binding needs-roll :field social-class/needs-roll))
  (when #t)
  (effects
    (update-node self social-class/draw (set (rng-draw 0)))))
