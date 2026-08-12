; The organization/* rule pack — Task 10 of the Organization foundation
; plan. ONE probe rule, exercising the enum chain end to end: a
; content-declared closed `OrgKind` (ADR195's `enum` deffield row, Q12)
; read back through a `:field` binding — NOT `field-of`, which is refused
; at load for enum-declared fields (ADR195's FIELD-OF DEFERRAL, D102) —
; compared against a specific member in a `when` guard, and used to gate
; an effect. Nothing here aggregates the kind — §2.13 forbids arithmetic
; on an `Enum<T>` field on purpose (there is no meaningful
; extensive-or-intensive reading of a member identity); this rule only
; ever reads `organization/kind` for equality.
;
; D-1: `EventType/ORGANIZATION_SEEDED` is a KNOWINGLY-UNMINTED, probe-only
; event name — not in ADR196's mint, not a member of the frozen Python
; EventType enum, no consumer anywhere. The scenario deliberately leaves
; EventType undeclared (per-kind opt-in, D119), so the name is inert by
; design and nothing can catch a typo in it. It exists solely so this
; probe has an effect to gate; retire or mint it when the Events-in-BSL
; workstream (WS1, #502) gives emit effects a real observable.
;
; No anchor form: `organization` is already a registered system (Task 8),
; so this rule's own `organization/kind-probe` id resolves it from the
; rule-id's namespace prefix, the same convention `vitality.bsl` uses.
(rule organization/kind-probe
  :material-basis "the state's coercive organs are a distinct material kind; content can see the difference (spec Q1)"
  :fuel 32
  (bindings
    (binding kind :field organization/kind)
    (binding active :field organization/active))
  (when (and (= active 1) (= kind OrgKind/STATE_APPARATUS)))
  (effects
    (emit EventType/ORGANIZATION_SEEDED (probe 1))))
