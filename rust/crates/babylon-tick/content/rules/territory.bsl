; TerritorySystem (Material Base @2.0) — the settler-colonial spatial
; substrate: "Legibility over Stealth" (state legibility accumulates as
; heat; heat past a threshold triggers eviction; eviction routes displaced
; population to carceral sinks; carceral sinks eliminate/suppress).
;
; Frozen source: src/babylon/engine/systems/territory.py (378 lines, four
; SEQUENTIAL phases run in one step()). Port-as-is (Director ruling):
; frozen defects are transcribed and D-recorded, never silently repaired.
; The frozen engine is a structure/ordering contract, NOT a byte oracle
; (ADR183) — conformance expecteds are measured from THIS BSL engine and
; pinned in territory_conformance.rs, not copied from the frozen mirror's
; printed floats.
;
; FOUR RULES, ONE PER PHASE, BYTE-ORDERED `p1 < p2 < p3 < p4-camp-decay <
; p4-penal-suppression` — deliberately relying on D116's recorded
; cross-rule divergence (docs/reference/bsl-language.rst): today's
; run_once_into/TickSession::advance run each rule in a content set to
; COMPLETION before the next starts, against the SAME mutable graph, so a
; later rule at the same anchor position sees an EARLIER rule's
; already-applied writes from THIS tick. The frozen phases are
; SEQUENTIAL BY DESIGN (eviction reads this-tick post-Phase-1 heat; camp
; decay eats this-tick displaced arrivals) — this pack RELIES on that
; divergence rather than fighting it, and D-record #1 (Task 8) names the
; dependency explicitly for when the Q14 repair train lands a real anchor
; registry.
;
; D-RECORDS this pack transcribes (full text + file:line evidence in the
; Task 8 register rows, docs/reference/bsl-language.rst):
;   1. Phase order relies on D116's byte-order/run-to-completion semantics.
;   2. `under-eviction` is an int 0/1 latch — no Bool store path exists on
;      the live `.bscn` pipeline (reports/territory-bsl-surface-facts-
;      2026-08-12.md §1(c)).
;   3. `rent-level-x1e6` is the scaled bare-Int lane (metabolism.bsl's
;      entropy-factor-x1e6 D-1 precedent) — retires with #502 WS3's
;      Real x Ratio operator.
;   4. The sink walk is DIRECTED (`:out`, territory.py:174) while spillover
;      is `:any` (ADR179-T1's canonical-pair caveat, territory.py:279-284)
;      — the frozen asymmetry, transcribed.
;   5. Same-type multi-sink tiebreak: frozen enumeration-order last-wins
;      vs this language's D45 ascending-id first-wins.
;   6. Two-clamp inconsistency: p1 clamps [0,1] both sides
;      (system_base.py::_write_clamped), p3 clamps upper-only
;      (territory.py:315, `min(1.0, …)`) — transcribed faithfully.
;   7. No-defaults: every fixture seeds every field every rule reads; the
;      frozen `attrs.get(k, default)` affordance is not transcribable.
;   8. Hash-neutral no-op writes: p2's no-sink `(add 0)`, p3's isolated
;      unchanged `(set clamped)` where frozen skips the write entirely.
;   9. Summation/apply order vs the frozen engine's float op sequence
;      (rent's Real-promotion lane, p3's pull-side `rate x Σheat` vs the
;      frozen per-edge `Σ(heat x rate)`) — measured BSL expecteds are the
;      oracle (ADR183), never chased to bit-match.
;  10. displacement_mode -> EXTRACTION const (provably uniform on every
;      production path, per the inventory's own finding); the override
;      machinery + defines.yaml:243/241 go to the #502 WS1 ledger.
;
; `territory` is already a registered system (babylon-tick/src/lib.rs) —
; added earlier by the query-evaluation train as a namespace placeholder;
; this pack is the content that namespace was reserved for.

(rule territory/p1-heat-dynamics
  :material-basis "state legibility: HIGH_PROFILE visibility accumulates heat linearly, LOW_PROFILE opacity decays it geometrically (territory.py:107-137)"
  :fuel 128
  (bindings
    (binding profile :field territory/profile)
    (binding heat :field territory/heat)
    (binding gain :const territory/high-profile-heat-gain)
    (binding decay :const territory/heat-decay-rate)
    (binding raw :expr (if (= profile OperationalProfile/HIGH_PROFILE)
                           (+ heat gain)
                           (* heat (- 1 decay))))
    ; _write_clamped [0,1] (system_base.py:189) — nested-if idiom, floor then
    ; ceiling (D-3 class: dispossession.bsl:356-364's Real-zero-promotion
    ; trick — `(- 0 0c)`/`(- 1 0c)` are Real 0.0/1.0 so both `if` branches
    ; share one static type, §3.3/E-TYPE-020):
    (binding floored :expr (if (> raw 0) raw (- 0 0c)))
    (binding clamped :expr (if (< floored 1) floored (- 1 0c))))
  (when #t)
  (effects
    (update-node self territory/heat (set clamped))))
