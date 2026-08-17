; The I3 review-round-1 fixture (#576 Task 5): rng-draw called ONCE PER
; ELEMENT inside a real for-each over neighbors — the only fixture that
; exercises evaluator::build_intrinsic_call_ctx -> element_content_id ->
; env.elements end to end, through the REAL KernelIntrinsicHost dispatch
; (rows 5-9 hand-build IntrinsicCallCtx directly, which never resolves an
; element through the C8 element stack the way a fold body does). Two
; neighbors, same subject (hub) -> two draws that differ only by element.
(rule demo/rng-fold-draw
  :material-basis "rng-draw inside a for-each over neighbors reaches the real dispatch path end to end"
  :fuel 4096
  (bindings
    ; :field binding present ONLY so the subject type (social-class) is
    ; inferable (tick.rs::subject_type_of) — unread by the guard, which
    ; fires unconditionally.
    (binding subject-type-probe :field social-class/draw :optional :default 0c))
  (when #t)
  (effects
    (for-each (neighbors self EdgeType/SOLIDARITY :out NodeType/SOCIAL_CLASS)
      (update-node it social-class/draw (set (rng-draw 0))))))
