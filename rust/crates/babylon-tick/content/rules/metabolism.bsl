; MetabolismSystem (Material Base @13.0) — the metabolic rift between
; extraction and regeneration.
;
; Every tick, a territory's biocapacity regenerates toward its ceiling and
; is depleted by extraction, at an entropic loss (extraction always costs
; more than it yields — the thermodynamic point behind `entropy_factor`).
; Extraction also PERMANENTLY damages the ceiling itself (the Epoch 1
; hysteresis doctrine, "The Earth Remembers") — the earth cannot recover
; its original ceiling even if extraction stops entirely.
;
; THIS PACK PORTS ONLY PHASE 1 of the frozen system (per-territory
; biocapacity delta + hysteresis ratchet + double clamp) — the gap report's
; own verdict on this system: "Per-territory biocapacity/hysteresis rule
; plus one graph-scoped overshoot rule; blocked on graph-scoped evaluation
; only" (`reports/bsl-gap-analysis-2026-08-10.md` row 13.0). The spec-070
; sovereign pre-pass and Phases 2-3 (global overshoot aggregate +
; `ECOLOGICAL_OVERSHOOT`) are BLOCKED — D-3/D-4 below, full derivation in
; `reports/metabolism-port-assessment-2026-08-11.md`.
;
; ============================================================================
; §5.4 FINDING — D-1: `entropy_factor` cannot be a `Ratio` for THIS formula;
; scaled-Int workaround, open language-surface finding
; ============================================================================
;
; The obvious move — `(defconst metabolism/entropy-factor 1.2r :floor 1r
; :cap 3r)`, `bsl-language.rst` Draft-Ruling Register row D99's OWN worked
; example (#492/ADR194, `currency_scale_op_e2e.rs`) — DOES NOT WORK for
; `calculate_biocapacity_delta`'s actual arithmetic. `Ratio` has exactly one
; legal operator, `Currency x Ratio -> Currency` (D99: "Ratio gets exactly
; this one operator and no other"), confirmed in `evaluator.rs::apply_arith`
; — every `Value::Ratio` operand not paired with a `Value::Currency` falls
; to the generic `real_lane` catch-all, which does not recognize
; `Value::Ratio` at all and refuses outright. This formula's multiplicand,
; `raw_extraction = extraction_intensity * current_biocapacity`
; (`metabolic_rift.py:47`), is NEVER `Currency` — both factors are `:field`
; reads (D-2 below explains why `extraction_intensity`/`biocapacity` must
; be per-node fields, not consts), and slice 1's `scenario.rs::
; attribute_value` refuses to store ANY field as anything but
; `int`-declared — there is no Currency-typed field storage to route
; through. `Currency` can only enter a rule as an inline literal
; (`currency_scale_op_e2e.rs`'s own module doc), never as the result of a
; field read. So `Real x Ratio` is the only shape available, and no such
; operator exists.
;
; This is not a new gap this port invented: `reports/bsl-gap-analysis-2026-
; 08-10.md`'s Appendix item 3, written ONE DAY BEFORE D99 landed, already
; named it precisely — "The residual gap is real only for a runtime-valued
; `:const` outside `[0,1]` (`entropy_factor`, domain `(1.0, 3.0]`), which
; authors cannot split at load time." D99 closes director-gate #492 for the
; shape its OWN worked example tests (`Currency x Ratio`); `entropy_factor`'s
; REAL consumer needs `Real x Ratio`, a shape D99 never added an operator
; for — apparently on the assumption (matching `biocapacity`'s `Currency`
; type annotation in the Python Pydantic model, `territory.py:155-163`)
; that the multiplicand would itself be `Currency`-typed in BSL, which it
; is not and cannot be in slice 1.
;
; **Workaround, not a resolution — and NOT bit-exact against the frozen
; engine. Declared, bounded, deterministic deviation, corrected here after
; adversarial review found the original "exact ... for ANY legal value"
; claim FALSE by execution.** `entropy_factor` is declared as a scaled
; bare-`Int` `:const` — `(defconst metabolism/entropy-factor-x1e6
; 1200000)`, `x1,000,000` — and divided back out inline (`ecological-cost`
; below). This is the SAME escape hatch Dispossession's own D-2/D-4 already
; use and document: a bare, unsuffixed `Int` `:const` carries NO domain
; check at all (`E-LEX-024` only bounds SCALED/suffixed literals).
;
; **The frozen engine computes `raw_extraction * entropy_factor` as ONE
; binary64 multiply.** This pack computes `(raw_extraction *
; entropy_factor_x1e6) / 1000000` — an EXACT integer multiply (both
; operands fit well inside 2^53 for any biocapacity magnitude this game
; uses) followed by a correctly-rounded division. Both are the SAME
; real-valued function; they are DIFFERENT floating-point PROGRAMS for it,
; and correctly-rounded operations composed in a different order are not
; guaranteed to agree. Two independent error sources, bounded honestly
; rather than asserted away:
;
;   1. **Grid quantization** (dominant for an arbitrary modded value). A
;      content author writes `entropy-factor-x1e6` as `round(entropy_factor
;      x 1,000,000)` — an integer, so any TRUE value needing more than 6
;      decimal digits is quantized to the nearest 1e-6, an absolute error
;      up to `5e-7`. `MetabolismDefines.entropy_factor` is a plain `float`
;      with no stated digit-count limit, so this is a real, not merely
;      hypothetical, degradation for SOME legal `(1.0, 3.0]` values — the
;      shipped default `1.2` (and any value exactly representable in <= 6
;      decimal digits) has ZERO quantization error, `1200000 / 1e6 == 1.2`
;      exactly as a real number.
;   2. **Double rounding** (the residual even at zero quantization error).
;      Let `k` = the exact integer `entropy-factor-x1e6`. This pack's value
;      is `round_f64(raw_extraction * k / 1e6)` — ONE correctly-rounded
;      division of an EXACT numerator, i.e. the correctly-rounded `f64`
;      nearest the TRUE mathematical product `raw_extraction x
;      entropy_factor`. The frozen engine's value is `raw_extraction *_f64
;      entropy_factor_f64`, where `entropy_factor_f64 =
;      round_f64(entropy_factor)` already carries its OWN rounding error
;      (<= 0.5 ULP, i.e. relative error <= 2^-53) from the decimal literal.
;      The real number Python's multiply rounds therefore differs from the
;      real number this pack's division rounds by a relative factor of
;      <= 2^-53 — small, but two INDEPENDENT correctly-rounded results of
;      two real numbers that close can still land on ADJACENT (or
;      near-adjacent) representable doubles, because each result is itself
;      only correct to within 0.5 ULP of ITS OWN input. Measured, not just
;      bounded: `metabolism-rounding-divergence-conformance.bscn`
;      (`biocapacity=3`, `entropy_factor` at the shipped default `1.2`,
;      hence ZERO quantization error) diverges from the frozen engine by
;      EXACTLY 2 ULP — `0x3ff6666666666666` (this pack) versus
;      `0x3ff6666666666668` (frozen Python) for `biocapacity`, both
;      printing as `1.4` / `1.4000000000000004`. See
;      `metabolism_rounding_divergence_conformance.py` and
;      `metabolism_rounding_divergence_conformance.rs`, which PIN this
;      deviation rather than deny it.
;
; **Why this is acceptable rather than a defect this port must repair
; (ADR183 §5.4): the frozen Python engine is the contract source for
; STRUCTURE and ORDERING, never a bit-exact correctness oracle.** What is
; constitutional (III.7) is THIS engine's own determinism — the same
; content and the same inputs produce the same output, every time, on any
; conforming implementation — which integer-scaled arithmetic satisfies
; exactly (`the_metabolism_tick_is_deterministic` and its siblings in the
; conformance suites already prove this). Bit parity with a Python
; reference the Constitution never asked this port to reproduce exactly is
; not the bar; a bounded, documented, reproducible deviation is. The
; en-masse retirement of this whole workaround class — a genuine `Real x
; Ratio` operator, or `Ratio`-typed field storage, closing the gap at its
; root instead of per-consumer — is chartered as **workstream 3 of the
; post-port refactor program** (Director directive 2026-08-11, tracked at
; GitHub issue #502), not attempted by this port.
;
; `metabolism-entropy-low-conformance.bscn` /
; `metabolism-entropy-high-conformance.bscn` mutation-verify the workaround
; carries the coefficient's EFFECT end to end (a floor-inert result at
; `1.01` swinging to a floor-bound result at `3.0`) — a magnitude check,
; not a bit-exactness one; `metabolism-rounding-divergence-conformance.bscn`
; is the bit-exactness check, and it is a PASS for "bounded ULP deviation
; from the frozen engine", not a pass for "identical to the frozen engine".
;
; **Recorded as an OPEN finding for the language surface, not resolved
; here**: `Real x Ratio` (or `Ratio`-typed field storage) is a genuine
; follow-up the BSL spec owners should rule on. Minting a new operator or a
; new Draft-Ruling Register row is a language-surface decision outside this
; port's scope — this D-record exists so a later reader does not have to
; re-derive the gap. (Note on numbering: this file's `D-1`..`D-4` are
; LOCAL to this pack, mirroring `dispossession.bsl`'s own `D-1`..`D-5` and
; `lifecycle.bsl`'s own `D-1`..`D-6` exactly — `bsl-language.rst`'s
; Draft-Ruling Register (`D97`-`D99`, sync-guarded by
; `TestTheDraftRulingRegisterHasNoDuplicateRowNumbers`) is a SEPARATE,
; language-spec-level register that neither Dispossession's nor Lifecycle's
; own D-records participate in; this pack follows their actual precedent,
; not a same-named-but-different register.)
;
; ============================================================================
; MODELING CHOICE — D-2: `regeneration_rate` becomes `:const`;
; `extraction_intensity`/`biocapacity`/`max_biocapacity` stay `:field`
; ============================================================================
;
; Applying Dispossession's own D-1 reasoning ("is it PROVABLY uniform, or
; genuinely live?") to each of this system's `attrs.get(field, default)`
; reads gives DIFFERENT answers for different fields — unlike Dispossession,
; where all five rate inputs landed the same way:
;
;   - `regeneration_rate`: grep-verified UNIFORM. No scenario builder in
;     `src/babylon/engine/scenarios/` ever assigns it a value distinct from
;     `Territory.regeneration_rate`'s own Pydantic default (`models/
;     entities/territory.py:165-170`, `default=0.02`), and nothing else in
;     the engine writes it onto a `TERRITORY` node (`SubstrateSystem`'s own
;     `regeneration_rate` reference is a DIFFERENT `SubstrateDefines`
;     coefficient feeding a DIFFERENT formula call on a DIFFERENT attribute,
;     `raw_material_stock` — `substrate.py`'s own module doc: "Does NOT
;     touch `Territory.biocapacity`/`MetabolismSystem`"). Every territory in
;     the shipped engine reads the same `0.02` — exactly the "per-node
;     storage never observably diverges from the global constant" shape
;     Dispossession's D-1 and Lifecycle's D-1 both name.
;   - `extraction_intensity`: NOT uniform, NOT dormant. Written live,
;     per-territory, by `ProductionSystem` (`production.py:268`,
;     `graph.update_node(node.id, extraction_intensity=intensity)`, derived
;     from `total_production / max_biocapacity`) — confirmed by the gap
;     report marking Metabolism "No" under "Dormant on canonical" (row
;     13.0), unlike Dispossession's "Yes (zero-rate inputs)". Treating this
;     as `:const` would misrepresent a live production channel — the
;     OPPOSITE of what justified Dispossession's own choice. Stays `:field`.
;   - `biocapacity`/`max_biocapacity`: self-evidently per-node evolving
;     state (this system's own primary output), AND seeded with genuinely
;     different values per territory at scenario-build time
;     (`_legacy.py:673-677`: `150.0`/`40.0`/`100.0` by sector
;     classification, not a uniform constant). Stay `:field`.
;
; ============================================================================
; TRANSCRIPTION NOTE — one shared `raw-extraction` binding, not two
; ============================================================================
;
; `calculate_biocapacity_delta`'s `raw_extraction = extraction_intensity *
; current_biocapacity` (`metabolic_rift.py:47`) and `calculate_hysteresis_
; damage`'s `raw_extraction = extraction_intensity * current_biocapacity`
; (`:86`) are the IDENTICAL formula over the IDENTICAL inputs — both called
; from `metabolism.py` with the same `attrs.get("extraction_intensity",
; 0.0)` and the same `biocapacity` read (`:98`/`:109`, `:95`/`:99`/`:103`).
; This pack computes it once (`raw-extraction` below) and reuses it for both
; the ecological cost AND the hysteresis damage — a value-preserving
; consolidation, not a transcription deviation (no output changes).
;
; ============================================================================
; BLOCKED — D-3: the spec-070 sovereign pre-pass has no BSL bind-src
; ============================================================================
;
; `metabolism.py:78-88` reads `context.persistent_data["balkanization.
; metabolic_impact_by_territory"]` (a one-tick-lagged handoff from
; `SovereigntySystem` @17.5) and adds it to `territory.habitability` before
; the biocapacity update. `bsl-language.rst` §2.5 closes `<bind-src>` at
; exactly four forms (`:field`/`:const`/`:metric`/`:tick`) — none can name
; `context.persistent_data`. `reports/bsl-gap-analysis-2026-08-10.md`'s Q6
; section ("Graph-scope state... the single most pervasive gap in the
; estate") names Metabolism by name among its 22 affected systems and names
; this EXACT handoff: "three of these values are one-tick-lagged handoffs
; (Sovereignty -> Metabolism..." Dropped whole, matching how Lifecycle's own
; header drops its two blocked rules — this is content-modeling work (Q6's
; own recommended fix routes it onto an ordinary graph field) this port does
; not perform unilaterally.
;
; ============================================================================
; BLOCKED — D-4: Phases 2-3 (global overshoot aggregate + emit)
; ============================================================================
;
; `metabolism.py:120-153` sums `biocapacity` over every `TERRITORY` and
; `(s_bio + s_class) * population` over every ACTIVE `SOCIAL_CLASS`, then
; emits `ECOLOGICAL_OVERSHOOT` when the ratio exceeds a threshold. Confirmed
; BLOCKED at the EXECUTION-ENGINE level, not merely cited: `bsl-language.
; rst`'s `(domain :graph)` construct (the mechanism this exact case needs —
; Q12's own text: "Metabolism's overshoot check... under per-node inference
; [it] would emit once per node") is fully implemented at LOAD time
; (`domain.rs::resolve_domain`/`RuleDomain::Graph`) but
; `tick.rs::run_tick` NEVER reads `loaded.domain` — it unconditionally calls
; `subject_type_of`, which only understands per-node `:field` namespaces.
; `babylon-tick/src/lib.rs` registers zero metrics (`metrics:
; HashSet::new()`), and no scenario/rule/test anywhere in
; `rust/crates/babylon-tick/` exercises `(domain :graph)` or `fold` end to
; end (grep-confirmed, zero hits for both). Even setting the engine gap
; aside, the aggregation spans TWO node-type namespaces in one rule, which
; no landed pack (including `fundamental-theorem.bsl`, single-namespace)
; has ever exercised. Dropped whole; full derivation in
; `reports/metabolism-port-assessment-2026-08-11.md` §4(b).
;
; ============================================================================
; ENGINE MACHINERY
; ============================================================================
;
; `babylon-tick/src/lib.rs`'s `run_once_into` registered-system set gains
; `metabolism`, the same minimal driver-scaffolding addition Vitality,
; Lifecycle and Dispossession each made for their own anchors.

(rule metabolism/biocapacity-update
  :material-basis "a territory's biocapacity regenerates toward its ceiling and is depleted by extraction at an entropic loss every tick, and extraction permanently damages the ceiling itself — the earth cannot recover its original capacity even if extraction stops"
  :fuel 4096
  (bindings
    (binding current :field territory/biocapacity)
    (binding max-cap :field territory/max-biocapacity)
    (binding extraction-intensity :field territory/extraction-intensity)
    (binding regeneration-rate :const metabolism/regeneration-rate)
    ; D-1: scaled bare-Int workaround for entropy_factor's (1.0, 3.0]
    ; domain — Ratio's only operator is Currency x Ratio, and this
    ; formula's multiplicand is never Currency.
    (binding entropy-factor-x1e6 :const metabolism/entropy-factor-x1e6)
    (binding hysteresis-rate :const metabolism/hysteresis-rate)
    ; `regeneration = regeneration_rate * max_biocapacity; if current >=
    ; max_biocapacity: regeneration = 0.0` (`metabolic_rift.py:40-44`).
    ; The Real-zero promotion trick (dispossession.bsl's D-4 header, cited
    ; above): the THEN branch must share regeneration-raw's Real type.
    (binding regeneration-raw :expr (* regeneration-rate max-cap))
    (binding regeneration :expr
      (if (>= current max-cap) (- 0 0c) regeneration-raw))
    ; Shared by both formulas (see the header's TRANSCRIPTION NOTE).
    ; Promoted to Real via +0.0 (the SAME trick, needed here because
    ; `extraction-intensity * current` is Int x Int, which stays Int, and
    ; `Int / Int` has no pinned semantics (`evaluator.rs::arith_int`) —
    ; the division below needs at least one Real operand to reach the
    ; binary64 lane.
    (binding raw-extraction :expr
      (+ (* extraction-intensity current) (- 0 0c)))
    ; `ecological_cost = raw_extraction * entropy_factor`
    ; (`metabolic_rift.py:47-50`) — D-1's scaled-Int workaround, descaled
    ; inline.
    (binding ecological-cost-scaled :expr (* raw-extraction entropy-factor-x1e6))
    (binding ecological-cost :expr (/ ecological-cost-scaled 1000000))
    (binding delta :expr (- regeneration ecological-cost))
    ; `damage = raw_extraction * hysteresis_rate`
    ; (`metabolic_rift.py:86-87`).
    (binding damage :expr (* raw-extraction hysteresis-rate))
    ; `new_max = max(0.0, max_cap - damage)` (`metabolism.py:113`) — the
    ; hysteresis ratchet. No scalar min/max in the grammar (the gap
    ; report's own Appendix item 2 recommends against a min/max rider,
    ; "nested `if` is doctrinally preferable under §3.3") — spelled with
    ; `if`, matching Dispossession/Lifecycle's own clamps.
    (binding max-cap-minus-damage :expr (- max-cap damage))
    (binding new-max :expr
      (if (> max-cap-minus-damage 0) max-cap-minus-damage (- 0 0c)))
    ; `new_biocapacity = max(0.0, min(new_max, current + delta))`
    ; (`metabolism.py:116`) — the double clamp, min then max, exactly.
    (binding current-plus-delta :expr (+ current delta))
    (binding capped-at-ceiling :expr
      (if (< current-plus-delta new-max) current-plus-delta new-max))
    (binding new-biocapacity :expr
      (if (> capped-at-ceiling 0) capped-at-ceiling (- 0 0c))))
  ; No `(when ...)` guard: the frozen Phase 1 loop has no `continue`
  ; (`metabolism.py:91-118`) — every TERRITORY node gets its effects
  ; unconditionally, matching Lifecycle's own unconditional Block 1.
  (effects
    (update-node self territory/biocapacity (set new-biocapacity))
    (update-node self territory/max-biocapacity (set new-max))))
