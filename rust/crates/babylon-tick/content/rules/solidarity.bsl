; SolidaritySystem (Material Base @8.0 — "Organization affects bargaining",
; `simulation_engine.py:298`) — Proletarian Internationalism, the
; counterforce to imperial-rent bribery. Frozen source:
; `src/babylon/engine/systems/solidarity.py` (`SolidaritySystem`, class at
; :78-91, `step` at :97-203) with the transmission formula at
; `src/babylon/formulas/solidarity.py:10-36`. Issue #557 umbrella, Wave C,
; Task 2 — docs/superpowers/plans/2026-08-17-solidarity-port.md §2/§6 Task 2.
;
; ONE rule, ONE subject type, `SOCIAL_CLASS` (plan §2.1, D-record 5):
; `Organization.ideology` is a `str` field, so
; `class_consciousness_from_node` always returns `0.0` for an org source —
; the frozen `> activation_threshold` gate fails on every tick,
; unconditionally. Organization-sourced SOLIDARITY edges are therefore
; provably always inert for this system; no second rule is needed the way
; `consciousness.bsl` needs `p2-org-solidarity-push` alongside
; `p3-class-solidarity-push`.
;
; THE CONTENT-MODEL RE-POINT (plan §1, D-record 1): frozen
; `ideology.class_consciousness` ports to the ALREADY-DECLARED
; `social-class/revolutionary` field — no `social-class/class-consciousness`
; scalar is minted. This is the frozen engine's OWN identification, not an
; invention here: `ideology.py:382-386`'s comment reads "class_consciousness
; <- revolutionary (delta_r)", implemented at `ideology.py:410`
; (`new_class = min(1.0, current_profile["class_consciousness"] + delta_r)`).
; ADR204 W1/W11 struck the legacy cc/ni estate; `consciousness.bsl` is the
; ternary surface's only reader; and D152 already re-pointed this exact
; gate's SOURCE-side comparison for `consciousness/p3-class-solidarity-push`.
; A different write target within one train would be incoherent. Consequence
; recorded, not silently absorbed (D-record 4): this write is an
; unconstrained-magnitude `[0,1]` scalar delta into one axis of a three-axis
; simplex (`r + l + f = 1`), so it can open a window off-simplex between this
; system's position (8.0) and `consciousness/p6-route`'s same-tick-or-later
; closure (17.0). No pack besides `consciousness.bsl` reads the ternary
; today, so the window is unobserved in the current estate; filed as a
; non-blocking Director-gate question (plan §4.1) on inflate-vs-displace,
; not re-litigated here — port-as-is proceeds on the inflate path, which is
; what a bare `[0,1]`-clamped scalar write necessarily does.
;
; THE PUSH IDIOM IS MANDATORY, NOT STYLE (plan §2.2): `for-each` iterates a
; query result WITHIN one subject's own effect list; the engine loops the
; subject population outside that (`tick.rs`). A direct transcription
; `(for-each (edges EdgeType/SOLIDARITY) …)` would therefore run once PER
; SOCIAL_CLASS subject, processing every edge N times and multiplying every
; write by the class count — a bug, not a faithful port. This rule instead
; pushes: each source iterates only ITS OWN outbound SOLIDARITY edges
; (`(neighbors self EdgeType/SOLIDARITY :out NodeType/SOCIAL_CLASS)`), so
; every edge is visited exactly once, by its unique source — the same D136
; idiom `consciousness.bsl:243-245`'s `p3-class-solidarity-push` uses,
; `:out` matching frozen's `source_id -> target_id` direction.
;
; `set`, NOT `add` — and the clamp is LOAD-BEARING (plan §2.3): `PendingWrite`
; application reads `current` from the graph AT APPLY TIME
; (`structural_verbs.rs::apply_pending_write`), so `add` would accumulate
; across multiple pushes into one target. `add` is nonetheless wrong here:
; `social-class/revolutionary` is declared `probability` — a unit-interval
; type — and a store landing outside `[0,1]` is `E-EVAL-020`, a TICK-FATAL
; range violation, NEVER an implicit clamp (`structural_verbs.rs:1690`). The
; frozen engine clamps explicitly (`solidarity.py:164-165`:
; `max(0.0, min(1.0, target + delta))`) — a clamp is expressible only on a
; COMPUTED result, i.e. via `set`. Omitting it is not a style choice; it is
; the difference between a rule that loads and one that is tick-fatal on the
; first transmission that would overshoot `1.0` (this pack's own clamp
; witness exercises exactly that). There is no `min`/`max` scalar intrinsic
; and no `abs` (grep-confirmed) — both are `if`-expressed below, the same
; trick `dispossession.bsl`'s header calls out as recurring at every clamp
; in that pack: `(- 0 0c)`/`(- 1 0c)` are Real zero/one (an `if`'s two
; branches must share one static type, E-TYPE-020, and a bare `0`/`1` Int
; literal would not match a Real-typed sibling branch).
;
; THE ACCEPTED TRADE-OFF (plan §2.4, D-record 2 — the genuine behavioural
; divergence, quantified against the frozen fixture
; `TestSolidaritySystemEdgeCases::test_multiple_solidarity_edges`,
; `tests/unit/engine/systems/test_solidarity_system.py:347-392`): frozen
; applies each edge's delta SEQUENTIALLY, each against the PREVIOUS write —
; two 0.3-strength edges from sources at 0.9 and 0.8 into a target at 0.1
; yield 0.1 -> 0.34 -> 0.478. This port collects every subject's writes
; against the SAME pre-tick graph (`tick.rs`'s collect-then-apply split,
; :41-52) and `set` makes the LAST subject in ascending-node-id order win —
; both deltas computed against the unchanged 0.1, and only
; `0.1 + 0.3*(0.8-0.1) = 0.31` (source B, the higher node id) survives. What
; FORCES `set` here is not collect-then-apply alone — `add` would still
; accumulate correctly at apply time — it is the clamp-plus-`E-EVAL-020`
; constraint above (D-record 2's own correction to an earlier mis-reasoned
; draft): a future reader must not "fix" this to `add` expecting cumulative
; transmission, because `add` reintroduces an unclamped, tick-fatal overshoot
; path the very first time two inbound edges' deltas sum past `1.0`. The
; two-rule split that WOULD restore cumulative accumulation (stage deltas
; into an `(add)` accumulator, clamp once) is rejected: it collapses N
; per-edge `CONSCIOUSNESS_TRANSMISSION` events into one per target, breaking
; the frozen event contract (Task 3). This pack's `solidarity-conformance
; .bscn` seeds `multi-source-a`/`multi-source-b` at exactly the frozen
; fixture's 0.9/0.8/0.1 so the 0.478-vs-0.31 divergence is EXECUTED here,
; not merely asserted in prose.
;
; READS A NEIGHBOUR'S FIELD — A FIRST FOR THE ESTATE (plan §2.5, D-record 3):
; the delta needs the TARGET's current value, which no landed pack before
; this one has read (`field-of` over a query-yielded `NodeRef`, not `self`).
; This makes the collect-then-apply pre-state semantics observable for the
; first time — `tick.rs`'s own words: "Verified byte-neutral for every rule
; pack landed at the time of the repair — none reads another node's field,
; so the divergence was unobservable UNTIL A RULE DOES." This is that rule.
;
; TARGET LIVENESS MUST BE SEEDED (D-record 6): the frozen engine defaults a
; missing `active` attribute to `True` (`solidarity.py:127-130`), but
; `(field-of it social-class/active)` on an unwritten attribute is an honest
; -null load error here — there is no `:default` on a bare `field-of` query
; the way a `binding` can declare one. The conformance world therefore seeds
; `social-class/active` on every node (a narrowing of representable content,
; not a behavioural divergence). The SUBJECT-side (`self`) read keeps
; frozen's permissive default, via `:optional :default 1` below — only the
; per-edge TARGET read has no such escape hatch.
;
; THE FORMULA'S OWN GUARD, TRANSCRIBED BY STRUCTURE, NOT DUPLICATED:
; `calculate_solidarity_transmission` (`formulas/solidarity.py:33`) opens
; with `if source_consciousness <= activation_threshold or
; solidarity_strength <= 0: return 0.0` — dead in practice at its one call
; site, because `solidarity.py:135,143` already skip both cases before ever
; calling it. This rule's `(when …)` (the source threshold) and the
; per-edge `(guard …)` (the strength positivity) already express those exact
; two conditions at the exact two points the frozen CALLER checks them; a
; third, textually-separate copy of the same guard inside the delta
; expression would be genuinely dead code here too, so none is added —
; the formula's guard is subsumed by this rule's own gate structure, not
; omitted.
;
; `scaling_factor` (0.5) / `superwage_impact` (1.0) — declared on the same
; `SolidarityDefines` Pydantic model but with ZERO call sites anywhere in
; `solidarity.py` — are not declared as `:const`s here (D-record 7).
;
; FUEL: `:fuel` below is not a guess — no per-iteration binding form exists
; (plan §4.3), so every per-target quantity (the target's `revolutionary`
; field, the edge's `strength` field, and `delta` itself) is repeated
; INLINE, textually, everywhere it is used — the guard, the negligible-floor
; check, and the clamped write each re-evaluate `field-of`/`edge-between`
; rather than naming a shared local. The declared budget is the exact
; `computed_bound` the load-time bound checker reported for this rule
; against `solidarity-conformance.bscn`'s ceilings (measured, not derived):
; `cargo test -p babylon-tick --test solidarity_conformance --locked` with
; `:fuel 1` refused the rule with `E-LOAD-040: rule solidarity/p0-transmit
; static bound 1126 exceeds its declared :fuel 1` — `1126` is that number,
; pasted verbatim, not guessed or rounded up.
;
; "solidarity" is a REGISTERED system namespace as of Task 1
; (`babylon-tick/src/lib.rs`'s `systems` HashSet) — this pack changes no
; further Rust source.

(rule solidarity/p0-transmit
  :material-basis "SolidaritySystem.step (solidarity.py:97-203): skip inactive source/target (:126-130), strength <= 0 (:132-136, Fascist Bifurcation), source at/below activation_threshold (:142-144); delta = solidarity_strength * (source_consciousness - target_consciousness) (calculate_solidarity_transmission, formulas/solidarity.py:36); skip |delta| < negligible_transmission (:159-161); else write target (re-pointed to social-class/revolutionary, D-record 1) to max(0.0, min(1.0, target + delta)) (:164-169). Push form (plan §2.2): each source's own outbound edges, visited once. set not add: the unit-interval store law (E-EVAL-020) forbids unclamped accumulation; only a computed set carries the clamp (plan §2.3). Last-write-wins under multiple inbound edges diverges from the frozen sequential apply, recorded and quantified (D-record 2)."
  :fuel 1126
  (bindings
    (binding active :field social-class/active :optional :default 1)
    (binding r :field social-class/revolutionary :optional :default 0.0p)
    (binding threshold :const solidarity/activation-threshold)
    (binding negligible :const solidarity/negligible-transmission))
  (when (and (= active 1) (> r threshold)))
  (effects
    (for-each
      (neighbors self EdgeType/SOLIDARITY :out NodeType/SOCIAL_CLASS)
      (guard
        (and
          (= (field-of it social-class/active) 1)
          (> (field-of (edge-between EdgeType/SOLIDARITY self it) solidarity/strength) 0))
        (guard
          (>=
            (if
              (>
                (*
                  (field-of (edge-between EdgeType/SOLIDARITY self it) solidarity/strength)
                  (- r (field-of it social-class/revolutionary)))
                0)
              (*
                (field-of (edge-between EdgeType/SOLIDARITY self it) solidarity/strength)
                (- r (field-of it social-class/revolutionary)))
              (-
                0
                (*
                  (field-of (edge-between EdgeType/SOLIDARITY self it) solidarity/strength)
                  (- r (field-of it social-class/revolutionary)))))
            negligible)
          (update-node
            it
            social-class/revolutionary
            (set
              (if
                (<
                  (if
                    (>
                      (+
                        (field-of it social-class/revolutionary)
                        (*
                          (field-of
                            (edge-between EdgeType/SOLIDARITY self it)
                            solidarity/strength)
                          (- r (field-of it social-class/revolutionary))))
                      0)
                    (+
                      (field-of it social-class/revolutionary)
                      (*
                        (field-of
                          (edge-between EdgeType/SOLIDARITY self it)
                          solidarity/strength)
                        (- r (field-of it social-class/revolutionary))))
                    (- 0 0c))
                  1)
                (if
                  (>
                    (+
                      (field-of it social-class/revolutionary)
                      (*
                        (field-of
                          (edge-between EdgeType/SOLIDARITY self it)
                          solidarity/strength)
                        (- r (field-of it social-class/revolutionary))))
                    0)
                  (+
                    (field-of it social-class/revolutionary)
                    (*
                      (field-of (edge-between EdgeType/SOLIDARITY self it) solidarity/strength)
                      (- r (field-of it social-class/revolutionary))))
                  (- 0 0c))
                (- 1 0c)))))))))
