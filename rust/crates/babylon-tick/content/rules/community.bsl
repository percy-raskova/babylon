; community.bsl — CommunitySystem (Material Base @6.0, "Community
; hypergraph: n-ary membership, consciousness from the org landscape,
; reproduction cost modification, state decay"). Frozen source:
; `src/babylon/engine/systems/community.py` (`CommunitySystem`, class at
; :309-323, `step` at :325-370 — 675 lines), with the ternary math at
; `src/babylon/formulas/consciousness.py:55-108` and the cost modifier at
; `src/babylon/formulas/community.py:150-175`. Issue #667, Tasks 8-11 —
; docs/superpowers/plans/2026-08-18-community-port.md.
;
; NAME COLLISION, said first (plan §2.3): `lifecycle.bsl:4,78,104,372`
; mentions "community" and a field `community_tendency` — an INBOUND
; routing weight for the lifecycle/consciousness seeding law, unrelated to
; anything CommunitySystem reads or writes. Nothing here touches it.
;
; §3.7a CARRIER DISCLOSURE: this pack mints NO carrier node. Its
; carrier-subject rules (c00 here; c05-c08/c11 in later tasks) anchor on
; the ONE `NodeType/INSTITUTION` node a world already has, via
; `institution/community-carrier` — a SUBJECT-TYPE ANCHOR ONLY, bound and
; never read again, never gating anything (the binding exists because
; tick.rs::subject_type_of requires >=1 :field binding to derive
; INSTITUTION; this sentence exists so no reader mistakes it for a gate —
; control-ratio.bsl's pattern, verbatim in intent). A second
; INSTITUTION node in any world loading this pack double-applies every
; hyperedge write (each carrier-subject rule iterates EVERY institution);
; §8c guard 4 (`exactly_one_institution_carrier`,
; tests/community_conformance.rs) is the executable bar.
;
; BYTE-ORDER MAP (plan §2; execution order is rule-id byte order, D16):
; c00-census-reset < c01-member-census < c02-org-weight-reset <
; c03f-… < c03l-… < c03r-… < c04-community-contribution-push. The three
; c03 rules run f-then-l-then-r (NOT the plan table's reading order); the
; order is UNOBSERVABLE because the three write disjoint weight fields and
; their one shared field (`org-count`) accumulates integer-exact `add 1`s —
; the mirror transcribes the true order and its output is byte-identical
; either way (proven at Task 7). §8b's D116 ledger (the same-tick
; cross-rule reads this pack relies on) is reproduced in the plan, §8b.
;
; §5 DISCLOSURE — what does NOT land (the #653-gated half, hard-sequenced):
; threat scoring (community.py:579-608), solidarity amplification
; (:527-576), and the infrastructure line WHOLE (its maintenance term is
; non-monotone; a monotone-only port would be a different law, and
; port-as-is (ADR183) forbids it) all wait on the AG(i)
; attributed-membership ceremony — a Director act, never improvised. The
; four repression helpers (:210-279) await a verb layer (D-NF+11). c07/c08
; are DG-2-gated (Director question, unresolved at authoring).
;
; THE EXPLICIT-DOMAIN NOTE (PR #688 review, Copilot finding 1 — a REAL
; latent engine gap, named here for the future pack reader): c00's carrier
; binding is never referenced (its guard is `#t`), which makes the rule
; E-LOAD-004-undeterminable at LOAD — domain.rs::resolve_domain's
; None-branch candidate set is REFERENCE-fed, so an anchor that is bound
; but never read contributes nothing there, while tick.rs's
; subject_type_of counts every :field binding, referenced or not. The two
; derivations can therefore disagree and NOTHING cross-checks them
; (run_tick ignores the loaded domain entirely) — control-ratio.bsl's
; (when #t) precedent passes only because its :expr fold bodies feed the
; candidate set. This pack declares `(domain NodeType/INSTITUTION)`
; explicitly on every carrier rule whose guard is vacuous, which keeps
; both derivations honest by construction. Filed as a follow-up, not
; silently absorbed.
;
; THE FLOOR TABLE: the 14 ADR214 defconst rows live in each WORLD's .bscn
; (the scenario's defconst registry IS the driver's defines env — §6.2's
; "re-declared per scenario" precedent), never in this pack; the
; cross-world parity test (Task 9) pins every world's rows equal to the
; ADR's values.
;
; THE QUANTIZATION DIVERGENCE (found by the Task 7 corroboration artifact,
; reports/community-frozen-corroboration-2026-08-18.md): frozen's
; TernaryConsciousness fields are Probability-typed, snapped to a 10^-6
; ROUND_HALF_UP grid at the Pydantic boundary (kernel/math.py:41,
; _PRECISION=6). This pack computes and stores the UNQUANTIZED f64 chain —
; the mirror is the oracle, frozen's stored values are its grid-snapped
; twins. Where the pack's Tasks-9+ assertions differ from frozen's stored
; prints, this is why; it is recorded here and in the D-row register at
; this pack's landing, not discovered downstream.
;
; LATENT REFUSAL, NAMED (not handled — the plan gates nothing here): c04
; divides by `community/member-count`, the ACTIVE census. A community whose
; members are ALL inactive has count 0, and its members' c04 pushes refuse
; loudly (non-finite store, E-EVAL-014's discipline) rather than write a
; lie. World 1 has no such community (every seeded community has >=1 active
; member); the first world that seeds one owes the gate decision its own
; task's D-row.
;
; Reserved D-N rows this task consumes: D-NF+3 (the per-class org-weight
; decomposition — frozen's per-org weight sum re-expressed as per-class
; accumulators divided by the census, bit-exact in world 1's dyadic
; values), D-NF+25 (frozen's tendency-less org skip (:405-407) is
; inexpressible — the tendency gate is a rule-level `when`, three rules
; PARTITION every org, because fold bodies are bare accessors only (D138)).
; The pack's landed register rows are D203+ in docs/reference/
; bsl-language.rst.

; ============================================================ c00 — the reset
(rule community/c00-census-reset
  :material-basis "The per-tick rebuild (community.py:392-397 mints a fresh community_agents map on every step, and community.py:460-462 writes back via model_copy): every accumulator this pack reads derives from THIS tick's writes, so the tick begins by zeroing them. The institution/community-carrier binding is a SUBJECT-TYPE ANCHOR ONLY (tick.rs::subject_type_of requires >=1 :field binding to derive INSTITUTION) — never read again, never gating anything (`when #t`), so the domain is declared EXPLICITLY: an unreferenced anchor plus a vacuous guard is E-LOAD-004-undeterminable at load (domain.rs's candidate set is reference-fed), and control-ratio.bsl's precedent passes only because its fold bodies feed that set — recorded in the pack header."
  :fuel 79
  (bindings
    (binding carrier :field institution/community-carrier))
  (domain NodeType/INSTITUTION)
  (when #t)
  (effects
    (for-each (hyperedges HyperedgeType/COMMUNITY)
      (update-hyperedge it community/member-count (set 0))
      (update-hyperedge it community/r-raw (set 0))
      (update-hyperedge it community/l-raw (set 0))
      (update-hyperedge it community/f-raw (set 0))
      (update-hyperedge it community/density-sum (set 0)))))

; ============================================================ c01 — the census
(rule community/c01-member-census
  :material-basis "The member census (community.py:465-479's _collect_memberships + :392-397's community_agents): ACTIVE classes only (the :472-474 gate — an inactive member is excluded from the count AND from every downstream write), one +1 per (class, community) membership. The adds collect against the pre-state and combine at apply, so N active members land N exactly."
  :fuel 22
  (bindings
    (binding active :field social-class/active))
  (when (= active 1))
  (effects
    (for-each (hyperedges-of self HyperedgeType/COMMUNITY)
      (update-hyperedge it community/member-count (add 1)))))

; ============================================================ c02 — the per-class accumulator reset
(rule community/c02-org-weight-reset
  :material-basis "Port scaffolding (D-NF+3): the per-class org accumulators frozen never needed (it sums per-org in one pass) are this pack's decomposition of the same sum — reset per tick, all four, EVERY social class (no active gate: the reset is not the census)."
  :fuel 21
  (bindings
    (binding active :field social-class/active))
  (when #t)
  (effects
    (update-node self social-class/org-r-weight (set 0))
    (update-node self social-class/org-l-weight (set 0))
    (update-node self social-class/org-f-weight (set 0))
    (update-node self social-class/org-count (set 0))))

; ============================================ c03f/c03l/c03r — the org pushes
; The tendency gate is a rule-level `when`, NOT a fold body (D138: fold
; bodies are bare accessors), so the partition is three rules — D-NF+25.
; Byte order runs f, l, r; the order is unobservable (disjoint weight
; fields, integer-exact shared count) — see the header's byte-order map.
(rule community/c03f-org-weight-push
  :material-basis "The FASCIST arm of the org-weight push (community.py:403-426 + formulas/consciousness.py:63-72): each FASCIST org pushes cadre x cohesion onto each member class's org-f-weight and +1 onto its org-count. The org iterates only ITS OWN outbound MEMBERSHIP edges (the D136 push idiom, solidarity.bsl's mandatory form) — every edge visited exactly once, by its unique source. Frozen's tendency-less skip (community.py:405-407) is inexpressible as a fold guard, so the three tendency rules partition every org (D-NF+25); a tendency-less org is never written by frozen either, and no world may seed one."
  :fuel 72
  (bindings
    (binding cadre :field organization/cadre-level)
    (binding cohesion :field organization/cohesion)
    (binding tendency :field organization/consciousness-tendency))
  (when (= tendency ConsciousnessTendency/FASCIST))
  (effects
    (for-each (neighbors self EdgeType/MEMBERSHIP :out NodeType/SOCIAL_CLASS)
      (update-node it social-class/org-f-weight (add (* cadre cohesion)))
      (update-node it social-class/org-count (add 1)))))

(rule community/c03l-org-weight-push
  :material-basis "The LIBERAL arm — same law as c03f (community.py:403-426), one tendency over."
  :fuel 72
  (bindings
    (binding cadre :field organization/cadre-level)
    (binding cohesion :field organization/cohesion)
    (binding tendency :field organization/consciousness-tendency))
  (when (= tendency ConsciousnessTendency/LIBERAL))
  (effects
    (for-each (neighbors self EdgeType/MEMBERSHIP :out NodeType/SOCIAL_CLASS)
      (update-node it social-class/org-l-weight (add (* cadre cohesion)))
      (update-node it social-class/org-count (add 1)))))

(rule community/c03r-org-weight-push
  :material-basis "The REVOLUTIONARY arm — same law as c03f (community.py:403-426), one tendency over."
  :fuel 72
  (bindings
    (binding cadre :field organization/cadre-level)
    (binding cohesion :field organization/cohesion)
    (binding tendency :field organization/consciousness-tendency))
  (when (= tendency ConsciousnessTendency/REVOLUTIONARY))
  (effects
    (for-each (neighbors self EdgeType/MEMBERSHIP :out NodeType/SOCIAL_CLASS)
      (update-node it social-class/org-r-weight (add (* cadre cohesion)))
      (update-node it social-class/org-count (add 1)))))

; ============================================================ c04 — the contribution push
(rule community/c04-community-contribution-push
  :material-basis "The density decomposition (plan §1.3, D-NF+3): frozen's per-org weight (overlap/comm_size) x cadre x cohesion re-expressed as per-class sums divided by the census count — each active-in-census class pushes org-weight/member-count onto its communities' raw ternary accumulators and org-count/member-count onto density-sum. The divisor is c01's SAME-TICK census (§8b's D116 ledger row 1: fatal if apply-in-place is ever repaired to collect-across-rules — the Q14 train's acceptance input). The `active` gate is FIDELITY, not caution: frozen's community_agents is built from the active-only membership set (community.py:472-474 -> :392-397), so an inactive class's org weights (c03 pushes to members regardless of the target's active flag) must NEVER enter the sum — gated here, c03's push onto an inactive class stays inert (c02 resets it next tick)."
  :fuel 115
  (bindings
    (binding active :field social-class/active)
    (binding rw :field social-class/org-r-weight)
    (binding lw :field social-class/org-l-weight)
    (binding fw :field social-class/org-f-weight)
    (binding orgs :field social-class/org-count))
  (when (= active 1))
  (effects
    (for-each (hyperedges-of self HyperedgeType/COMMUNITY)
      (update-hyperedge it community/r-raw
        (add (/ rw (field-of it community/member-count))))
      (update-hyperedge it community/l-raw
        (add (/ lw (field-of it community/member-count))))
      (update-hyperedge it community/f-raw
        (add (/ fw (field-of it community/member-count))))
      (update-hyperedge it community/density-sum
        (add (/ orgs (field-of it community/member-count)))))))
