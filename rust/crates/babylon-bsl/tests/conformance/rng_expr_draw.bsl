; The I3 review-round-2 fixture (#576 final-review fix-forward): rng-draw
; called from an `:expr` binding's body, not a guard or an effect. Review
; round 1 refused this shape at RUNTIME with a rationale the whole-branch
; review showed false (rule_pipeline.rs:504-520's own doc, now corrected);
; `collect_pass` now constructs `DrawContext` before resolving `:expr`
; bindings, so this loads AND runs clean — see
; `rng_draw_is_now_legal_in_expr_binding_position_and_keyed_identically_to_
; guard_effect_position` (r9_chapters.rs::c14_rng_draw).
(rule demo/rng-expr-draw
  :role mechanic
  :evidence derived
  :material-basis "rng-draw is legal in :expr binding position, keyed identically to guard/effect position (#576 I3)"
  :fuel 128
  (bindings
    (binding needs-roll :field social-class/needs-roll)
    (binding rolled :expr (rng-draw 0)))
  (when #t)
  (effects
    (update-node self social-class/draw (set rolled))))
