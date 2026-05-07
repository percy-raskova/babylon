"""Property-based tests for the Consequence-after-OODA-actions causal
invariant (INV-014 / spec-056 US2).

See ``specs/056-causal-invariants/contracts/consequence_after_actions.md``
for the full predicate specification. Encodes Constitution I.17 OODA
(organizations deliberate against a fixed material snapshot, not against
mid-loop consequences) and III.7 Determinism (replay requires
order-independence over the organization set).

Three predicates:

  AS1 — Every Consequence System call timestamp > max OODA action timestamp (T018)
  AS2 — Deliberate interleaving (Consequence fires mid-OODA-loop) is caught (T019)
  AS3 — Reversed per-org iteration order produces equivalent post-state (T020)
"""
