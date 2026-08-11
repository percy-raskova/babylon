; DispossessionEventSystem (Material Base @10.0) — primitive accumulation as
; value transfer.
;
; Every tick, a county's foreclosure, eviction and displacement pressure
; combines with two structural ownership factors into one composite
; intensity, which draws a value transfer out of the territory's wealth —
; clamped to what the territory actually holds, split into what changes
; hands and what simply evaporates as deadweight loss (auction fees,
; vacancy, abandonment). The gap report's own verdict on this system: "One
; per-territory rule: five-term weighted intensity, clamped, wealth
; transfer, two emits. Cleanest fit in the estate"
; (`reports/bsl-gap-analysis-2026-08-10.md` row 10.0). THIS PACK PORTS THE
; WHOLE FROZEN SYSTEM — no phase is left un-ported, unlike Lifecycle/Vitality.
;
; ============================================================================
; MODELING CHOICE — D-1: the five per-territory inputs become `:const`
; ============================================================================
;
; `foreclosure_rate`, `eviction_rate`, `displacement_rate`,
; `concentrated_ownership` and `absentee_landlord_share`
; (`dispossession_events.py:70-88`) are read off the TERRITORY NODE, not off
; `GameDefines` — they are meant to be genuinely per-county data (FRED-derived
; foreclosure/eviction rates, institutional-ownership shares), unlike
; Lifecycle's D-1 fields, which were provably the SAME value everywhere
; because nothing else in the tree ever diverged them. This port cannot make
; the identical claim about these five fields — the whole point of the
; frozen design is that they vary by county.
;
; They become `:const` here anyway, for a reason that is a language
; constraint rather than a material claim: `bsl-language.rst`'s known
; constraint that "the slice-1 scenario loader seeds ONLY int-declared node
; attributes" (`scenario.rs::attribute_value`) accepts an INTEGER literal
; into an `int`-declared field and refuses every other combination outright —
; there is no legal way to seed a genuinely fractional per-node value in
; slice 1 at all, on any field, of any declared type. And unlike a
; scaled-integer workaround, that would not even be an honest fiction here:
; the gap report's own row for this system records it dormant on the
; canonical run TODAY for exactly this reason — "Yes (zero-rate inputs)" —
; nothing hydrates real per-county foreclosure/eviction/displacement data
; yet, so there is no live per-territory variation this port could
; misrepresent by flattening. When real per-county hydration lands (Phase 2's
; Currency/Probability-typed field storage), these five become genuine
; per-territory `:field` reads with NO change to the weighted-sum algebra
; below — the arithmetic does not care where its five inputs come from.
;
; Two `:const` environments prove every branch this shared-input design
; still discriminates (learn from #493's verification round): the ACTIVE
; environment (`dispossession-conformance.bscn`) with nonzero rates, and the
; ZERO-RATE environment (`dispossession-zero-rate-conformance.bscn`, all
; three primary rates 0) that proves this system's actual canonical
; behavior — completely inert, matching the gap report's Class C verdict.
; Wealth stays a genuine per-node `:field`, so ONE active scenario still
; discriminates the value-transfer guard below (a wealthy county vs. an
; insolvent one) without needing per-node rates at all.
;
; ============================================================================
; TRANSCRIPTION NOTE — the `:const` environment does not hide the frozen
; gate's exact shape
; ============================================================================
;
; `dispossession_events.py:75-76`: `if foreclosure_rate <= 0.0 and
; eviction_rate <= 0.0 and displacement_rate <= 0.0: continue` reads ONLY
; the three primary rates — NOT `concentrated_ownership` or
; `absentee_landlord_share`. A territory with nonzero structural ownership
; factors but all-zero primary rates is skipped WHOLE: no intensity
; computed, no state written, no event published, even though the intensity
; formula would be nonzero from the structural terms alone if it ever ran.
; This is not a defect ADR183 §5.4 asks this port to repair — it is the
; frozen system's own gate, and `(when …)` below transcribes exactly those
; three fields and no others. `dispossession-zero-rate-conformance.bscn`
; sets `concentrated-ownership`/`absentee-landlord-share` to nonzero
; specifically to prove the gate really does ignore them.
;
; ============================================================================
; DEAD FIELD — fips_code/year are dropped
; ============================================================================
;
; `TerritoryDispossessionState` (`domain/economics/dispossession/types.py`)
; carries `fips_code` and `year` alongside the five rate/structural fields,
; but neither `compute_intensity` nor `compute_value_transfer`
; (`domain/economics/dispossession/intensity.py`) ever reads either —
; grep-verified against both function bodies. They are passthrough
; identification fields on the Pydantic state object, not formula inputs.
; Dropping them changes no observable output.
;
; ============================================================================
; MODELING CHOICE — D-2: the two "clamp to available wealth" checks are
; provably redundant, and omitted
; ============================================================================
;
; `dispossession_events.py:95-96`: `transfer_amount = territory_wealth *
; intensity * transfer_scale; transfer_amount = min(transfer_amount,
; territory_wealth)`. This IS a real clamp in the frozen source, but it
; cannot fire under this port's construction, and — unlike the intensity
; clamp below — the proof does not depend on the CURRENT `defines.yaml`
; tuning:
;
;   - `intensity` is clamped to `[0, 1]` by this pack's own explicit
;     `intensity-floor`/`intensity` bindings below (not assumed — proven by
;     construction, two bindings down).
;   - `transfer-scale` is transcribed as a `c`-suffixed literal, and every
;     legal `c` literal is bounded to `[0, 1]` at LOAD time by `E-LEX-024`
;     (`bsl-language.rst` §1.5) — this is a language-enforced fact about
;     ANY value a modder could legally write for `transfer_scale`, not a
;     coincidence of the shipped `0.01`.
;
;   So `intensity * transfer-scale <= 1 * 1 = 1` always, hence
;   `wealth * (intensity * transfer-scale) <= wealth * 1 = wealth` always
;   (`wealth >= 0` by construction — nothing in this pack or the frozen
;   engine ever writes it negative). The clamp is dead code under ANY legal
;   `transfer_scale` value, not just the shipped one.
;
; The SAME argument, one operand shorter, retires `compute_value_transfer`'s
; internal `fraction = min(max(fraction, 0.0), 1.0)`
; (`intensity.py:74`, applied to `deadweight_loss_fraction`) — a single `c`
; literal is already `[0, 1]`-bounded by `E-LEX-024`, with no second operand
; whose value could push it out of range the way summing five independent
; weights can (see D-3 immediately below). `compute_value_transfer`'s
; leading `if total_value <= 0.0: return (0.0, 0.0)` (`intensity.py:66-67`)
; is dead code from THIS call site specifically — the frozen engine only
; ever calls it inside `if transfer_amount > 0.0:`
; (`dispossession_events.py:98-99`), so that branch never executes from this
; system regardless of which engine implements it.
;
; ============================================================================
; MODELING CHOICE — D-3: the intensity clamp is NOT omitted, for the
; opposite reason
; ============================================================================
;
; `compute_intensity`'s `min(max(intensity, 0.0), 1.0)` (`intensity.py:48`)
; IS transcribed explicitly (`intensity-floor`/`intensity` below), because
; the redundancy argument that retires D-2's clamps does not carry over. The
; floor half is provably redundant on its own (every weight and every rate
; is a non-negative `c` literal, so every term of the sum is non-negative,
; so the sum is non-negative — true under ANY legal per-field modding). The
; CEILING half is not: `weight_foreclosure`/`weight_eviction`/
; `weight_displacement`/`weight_tax_sale`/`weight_eminent_domain` each carry
; their own independent `[0, 1]` `Field(ge=0.0, le=1.0)` constraint in
; `DispossessionDefines` (`config/defines/economy_labor.py:175-`) with NO
; cross-field validator tying their SUM to `<= 1.0` — they currently sum to
; `0.92` (`0.4 + 0.3 + 0.15 + 0.05 + 0.02`), comfortably under 1, but a
; modder is free to raise any one of them within its own declared domain and
; push the sum past 1. This is exactly Lifecycle's D-4 caution, transcribed
; for a sum that is not currently 1.0 rather than exactly 1.0: a fact about
; today's tuning, not a law the type system enforces, so this port spells
; the clamp explicitly rather than asserting a redundancy it cannot prove
; for every legal mod.
;
; ============================================================================
; TRANSCRIPTION NOTE — effect order matches the frozen source's event order
; ============================================================================
;
; `dispossession_events.py`'s `VALUE_TRANSFER` publish (inside
; `if transfer_amount > 0.0:`, lines 98-115) runs BEFORE the unconditional
; `dispossession_intensity` write and `DISPOSSESSION_EVENT` publish (lines
; 117-133, both OUTSIDE that `if`, at the SAME indentation). The frozen
; engine's own printed event log for a wealthy, active subject confirms the
; order: `value_transfer` then `dispossession_event`
; (`dispossession_conformance.py`'s own run). §2.8's effects apply in
; SOURCE ORDER, so the `(guard …)` wrapping the wealth write and
; `VALUE_TRANSFER` emit comes FIRST in the effects list below, and the
; unconditional intensity write and `DISPOSSESSION_EVENT` emit come second —
; reversed from a naive top-to-bottom reading of the Python function, which
; states the intensity write in a comment ("Store intensity on node") after
; the transfer block only because it is un-indented from it, not because it
; runs first.
;
; ============================================================================
; ENGINE MACHINERY
; ============================================================================
;
; `babylon-tick/src/lib.rs`'s `run_once_into` registered-system set gains
; `dispossession`, the same minimal driver-scaffolding addition Vitality and
; Lifecycle each made for their own anchors.

(rule dispossession/territory-transfer
  :material-basis "a county's foreclosure, eviction and displacement pressure, combined with how concentrated and absentee-owned its housing stock already is, draws a value transfer out of its wealth every tick primitive accumulation is live there — split between what changes hands and what evaporates as deadweight loss (auction fees, vacancy, abandonment)"
  :fuel 1536
  (bindings
    (binding wealth :field territory/wealth)
    ; D-1: per-territory rate/structural inputs, `:const` for the reason the
    ; header states.
    (binding foreclosure-rate :const dispossession/foreclosure-rate)
    (binding eviction-rate :const dispossession/eviction-rate)
    (binding displacement-rate :const dispossession/displacement-rate)
    (binding concentrated-ownership :const dispossession/concentrated-ownership)
    (binding absentee-landlord-share :const dispossession/absentee-landlord-share)
    ; `DispossessionDefines` weights, `defines.yaml:425-429`.
    (binding weight-foreclosure :const dispossession/weight-foreclosure)
    (binding weight-eviction :const dispossession/weight-eviction)
    (binding weight-displacement :const dispossession/weight-displacement)
    (binding weight-tax-sale :const dispossession/weight-tax-sale)
    (binding weight-eminent-domain :const dispossession/weight-eminent-domain)
    (binding deadweight-fraction :const dispossession/deadweight-loss-fraction)
    (binding transfer-scale :const dispossession/transfer-scale)
    ; `compute_intensity`'s exact left-to-right association
    ; (`intensity.py:41-47`).
    (binding raw-intensity :expr
      (+ (+ (+ (+ (* weight-foreclosure foreclosure-rate)
                  (* weight-eviction eviction-rate))
               (* weight-displacement displacement-rate))
            (* weight-tax-sale concentrated-ownership))
         (* weight-eminent-domain absentee-landlord-share)))
    ; D-3: `min(max(raw_intensity, 0.0), 1.0)`, spelled explicitly. The
    ; `(- 0 0c)`/`(- 1 0c)` forms are Real zero/one — Lifecycle's own
    ; promotion trick (`lifecycle.bsl:284`'s header) for the same reason:
    ; `if`'s two branches must share one static type (E-TYPE-020), and a
    ; bare `0`/`1` Int literal would not match `raw-intensity`'s Real type.
    (binding intensity-floor :expr
      (if (> raw-intensity 0) raw-intensity (- 0 0c)))
    (binding intensity :expr
      (if (< intensity-floor 1) intensity-floor (- 1 0c)))
    ; `transfer_amount = territory_wealth * intensity * transfer_scale`
    ; (`dispossession_events.py:95`), left-to-right. D-2 retires the
    ; `min(transfer_amount, territory_wealth)` clamp that follows it in the
    ; frozen source.
    (binding wealth-times-intensity :expr (* wealth intensity))
    (binding transfer-amount :expr (* wealth-times-intensity transfer-scale))
    ; `compute_value_transfer` (`intensity.py:50-78`), reached only when
    ; `transfer_amount > 0.0` at the call site — the guard below reproduces
    ; that condition exactly, so these two bindings are safe to compute
    ; unconditionally here (§2.5/§4.2: `:expr` bindings resolve before any
    ; effect, so computing them costs nothing when the guard turns out
    ; false — they are simply not written anywhere).
    (binding deadweight :expr (* transfer-amount deadweight-fraction))
    (binding net-received :expr (- transfer-amount deadweight))
    (binding new-wealth :expr (- wealth transfer-amount)))
  ; The frozen loop's one `continue` (`dispossession_events.py:75-76`) —
  ; transcribed exactly: the three PRIMARY rates only, per the header's
  ; transcription note.
  (when (or (> foreclosure-rate 0) (> eviction-rate 0) (> displacement-rate 0)))
  (effects
    ; `if transfer_amount > 0.0:` (`dispossession_events.py:98`) — wealth
    ; write and VALUE_TRANSFER emit, FIRST in source order (see the header's
    ; effect-order note).
    (guard (> transfer-amount 0)
      (update-node self territory/wealth (set new-wealth))
      (emit EventType/VALUE_TRANSFER
        (territory self)
        (total-transferred transfer-amount)
        (net-received net-received)
        (deadweight-loss deadweight)))
    ; Unconditional: intensity write + DISPOSSESSION_EVENT emit
    ; (`dispossession_events.py:117-133`, outside the `if` above).
    (update-node self territory/dispossession-intensity (set intensity))
    (emit EventType/DISPOSSESSION_EVENT
      (territory self)
      (intensity intensity)
      (foreclosure-rate foreclosure-rate)
      (eviction-rate eviction-rate)
      (displacement-rate displacement-rate))))
