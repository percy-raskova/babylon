; The I1 review-round-2 fixture (#576 final-review fix-forward): rng-draw
; called once per EDGE, through a real for-each over each of TWO edge
; TYPES' own (edges …) query, over the SAME node pair — the end-to-end
; Element::Edge conformance row `evaluator.rs:2948`'s own note (r9_chapters
; c14 family) says did not exist. ONE firing subject (`hub`, the only
; SOCIAL_CLASS node — `a`/`b` are TERRITORY, so they never fire themselves
; and cannot confound the comparison with a second subject's draw): its
; SOLIDARITY-typed draw and its EXPLOITATION-typed draw must differ, even
; though both edges join the SAME two endpoints — proving `edge_type`
; reaches `stable_key`, not just `source`/`target`.
(rule demo/rng-edge-type-draw
  :material-basis "two parallel edges of different types between the same node pair must draw different values (#576 I1)"
  :fuel 8192
  (bindings
    ; :field binding present ONLY so the subject type (social-class) is
    ; inferable (tick.rs::subject_type_of) — unread by the guard, which
    ; fires unconditionally.
    (binding subject-type-probe :field social-class/probe :optional :default 0c))
  (when #t)
  (effects
    (for-each (edges EdgeType/SOLIDARITY)
      (update-edge it solidarity/draw (set (rng-draw 0))))
    (for-each (edges EdgeType/EXPLOITATION)
      (update-edge it exploitation/draw (set (rng-draw 0))))))
