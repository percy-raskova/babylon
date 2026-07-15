# Program Proposal — Doctrine Tree, Theoretical Labor & the Four Trunks

**Status: RATIFIED by owner 2026-07-15** (drafted 2026-07-15 from a full corpus
mine; audit Wave 6's "single largest coherent MISSING cluster"). **Historical grounding:**
50-agent Marxists.org/ProleWiki sweep, owner-directed at ratification —
`project/research/history-sweep/` (`brief-dt-{trunks,traps,patsoc,theoretical-labor}.md` +
`addendum-dt-rulings.md` closes rulings 3-5 with recommendations; coefficient tables inside). Sources:
`ai/epochs/epoch3/doctrine-tree.yaml` (1200 lines, PLANNED — the full spec),
`ai/epochs/epoch3/doctrine-tree-mvp.yaml` (481 lines, SPEC_COMPLETE — 3-trunk/3-tag/15-node
subset), `resource-sinks.yaml:240-280` (TL sinks/decay), `vanguard-economy.yaml` (Reading
Group Trap), `reactionary-subject.yaml:576-583` (class-composition gating),
`reports/epochs-vision-gap-audit.md` §3b/§5 Wave 6 + §6 item 8. Never-authored spec slot:
spec-080 (dependencies 070/071 exist on disk; 072 does not).

## Thesis (the corpus's)

"Your ideology is not neutral infrastructure. It determines what you CAN do and what you
WILL BECOME." A DAG of doctrine nodes with mutually-exclusive splits, purchased with
**Theoretical Labor** (`TL = Cadre_Count × Study_Allocation × Coherence_Factor` — an
opportunity-cost draw on cadre time, not a free currency), summing to a **tag vector**
(CLASS_ANALYSIS vs NATIONAL_CHAUVINISM is the load-bearing pair: "As long as CLASS_ANALYSIS >
NATIONAL_CHAUVINISM, you are safe"), organized into **four trunks** (Reformist / Insurrectionist /
Autonomist / Scientific), each with a mechanically-triggered trap ending (Liquidationism /
Adventurism / Dissociation / Bureaucratic degeneration), plus the **PatSoc Pipeline**: a
five-node drift chain ending in Strasserism with `resource_cost: 0` ("Falls into this,
doesn't choose it") and a faction flip — "You are the fascist who thought he was a
communist." Correction mechanism: the **Party Congress** (500+ TL; trunk_shift /
rectification / theoretical_offensive / self_criticism). "THE TREE MUST HAVE NO 'OPTIMAL
PATH.'"

## Verified engine reality (2026-07-15)

**Nothing exists.** Zero `DoctrineNode`/`DoctrineTree`/`TheoreticalLabor`/trunk-enum code
anywhere in `src/babylon` or the frontend (all rg hits are false friends: `shock_doctrine`
causal detector, "owner's mock doctrine" prose). The audit's §6 item 8 ruling stands: the
resource-balance traps (Reading Group/Influencer) are SUPERSEDED by `trap_detection.py`'s
Liberal/Rightist axes — fold flavor in, build nothing parallel. The ideological TRUNK traps
are a distinct axis and remain in scope.

## Owner rulings required BEFORE spec authoring

1. **MVP vs full**: the corpus itself recommends the 3-trunk/3-tag/15-node MVP first with a
   4-phase upgrade path (`doctrine-tree-mvp.yaml:449-481`). Note the standing
   no-MVP-scoping directive (memory: "full vision is the MVP") — BUT here the MVP is the
   corpus's OWN specced staging, not an external de-scoping; needs your explicit call.
2. **Faction flip on Strasserism**: runtime org-allegiance reassignment ("The State may now
   RECRUIT you") has no engine analog — an org changing sides mid-game is an
   architecture-level ruling (organization model + OODA + endgame interactions).
3. **Maintenance/decay**: full spec has per-node TL upkeep with degeneration-toward-parent;
   MVP strips it ("Once acquired, a doctrine stays forever"). Pick one; don't blend.
4. **`Study_Allocation`**: a cadre time-allocation split that exists nowhere in the Vanguard
   Economy — genuinely new state on the org model.
5. **Party Congress determinism**: "purge of opposed elements" must be a deterministic
   function of tag deltas or route through the seeded tick RNG — spell out which.
6. **Trap escape**: MVP deliberately has none ("teaches the lesson hard"); full spec sells
   self_criticism at 300 TL. Which ships?

## Tag rename + the Lawverian chauvinism⟷internationalism opposition (owner, 2026-07-15)

The reactionary tag `NATIONALISM` was renamed to **`NATIONAL_CHAUVINISM`** across the spec
(`doctrine-tree.yaml`, `-mvp.yaml`, this doc, `history-sweep/brief-dt-patsoc.md`) — docs-only,
no runtime code exists yet. Rationale (owner): the tag is a stand-in for oppressor-nation
chauvinism / white supremacy (Lenin's *great-nation chauvinism*; the CPUSA's own 1930s *white
chauvinism* campaigns), **not** the national question in general. National **liberation** of
oppressed nations is a distinct, progressive phenomenon this tag must never be confused with —
the sweep's African Blood Brotherhood findings draw exactly this line ("bourgeois
[left-]nationalism will betray the real interests of the Black and Latin toiling masses").
Renaming also forced a coherence fix: the old tag's "moderate" effect sold it as *"useful in
anti-imperial struggle"* — the precise conflation now removed (chauvinism is reactionary across
its whole range).

**Owner design direction (2026-07-15):** `NATIONAL_CHAUVINISM ⟷ INTERNATIONALISM` is a natural
Lawverian dialectic `D = (A, Ā, w, T, σ)` — and its Ā pole is **already built**. Model it as a
new `BoundOpposition` in `domain/dialectics/instances/catalog.py`, beside capital_labor / wage /
tenancy / atomization / imperial:

- **A = national-chauvinism, Ā = internationalism.** `OppositionSpec(pole_a="national-chauvinism",
  pole_b="internationalism", level_name="class")`. The progressive pole is not "low chauvinism"
  but a *positive* magnitude — proletarian internationalism, which the engine **already
  computes**: the `SolidaritySystem` ("Proletarian Internationalism," `systems/solidarity.py`,
  SOLIDARITY-edge transmission) is the live source for the Ā reading.
- **w (balance)** = the load-bearing `CLASS_ANALYSIS`-vs-`NATIONAL_CHAUVINISM` safety condition,
  reframed as the opposition's balance: chauvinism-dominant balance is the PatSoc drift gradient.
- **T (gap)** = a `GapMeasure` over (chauvinism accumulation, solidarity/internationalism
  incidence) — the same shape as the existing wealth-asymmetry `GapMeasure`.
- **σ (sublation)** = the correction: a Party Congress `rectification`/`theoretical_offensive`
  raising internationalism to re-close the gap (`aufhebung_of` lineage).
- Ties the Doctrine Tree's tag layer to the ratified dialectics machinery (Amendment S:
  "statics are derived, motion is primitive") — the tag vector becomes a *reading* of an
  opposition's motion, not a free-floating counter. **Phase-1 candidate:** shadow-compute this
  opposition's `PoleReading` (P19's `read_poles` shape) from chauvinism accrual + live
  SOLIDARITY incidence, byte-identical-safe, before any tag UI. Decouples cleanly from Program
  19 (different opposition, same registry). Needs an owner ruling at DT Phase 0: adopt the
  dialectics-opposition modeling, or keep the tag vector as a flat counter?

## Constitutional guardrails

- II.9/VIII.9: the Doctrine DAG should be its OWN small structure with its own owner
  (II.11), NOT edges on BabylonGraph — never overload the five canonical morphisms with
  ideology relations.
- II.5 + ADR034: trap conditions are boolean formulas over engine state, engine-evaluated,
  AI-narrated. No LLM ever grades theory, generates line-struggle adjudication, or decides
  NATIONAL_CHAUVINISM > CLASS_ANALYSIS.
- III.12: the PatSoc Pipeline's fully-numeric 5-phase trace (CLASS_ANALYSIS 3→1→0→−3,
  NATIONAL_CHAUVINISM 0→2→5→7→9) is a ready-made golden baseline — seed `tests/baselines/` from it
  directly.
- III.7: all corpus formulas are pure functions of committed state; keep it that way.

## Proposed phasing (post-ratification)

- **Phase 0** — ADR + rulings 1-6 + promotion to `project/programs/`; data file
  (`doctrine_tree.json`/TOML per the Paradox data-driven pattern) authored from the corpus
  node tables; DAG-validity check (the corpus's own error-recovery spec names circular
  dependency as the guard case).
- **Phase 1** — models + TL resource + tag summation, engine system acquiring nodes via a
  new verb or Congress action; shadow attrs + seam rows; goldens seeded from the PatSoc
  trace. qa:regression byte-identical (new system additive; no existing-system inputs
  change — verify, don't assume).
- **Phase 2** — trunk traps + PatSoc drift + (per ruling 2) the faction-flip mechanism.
- **Phase 3** — the 5th takeover: the tree canvas (the corpus even ships an ASCII mockup —
  `[●]` acquired / `[○]` locked / `[!]` trap + live tag bars); DESIGN_BIBLE §9b/§11 bind.
- Explicit dependency note: NATIONAL_CHAUVINISM-tag mechanics interact with spec-071
  (reactionary-subject, on disk) and colonial_stance (spec-070, on disk) — both
  prerequisites already merged per the 05-catalog record.
