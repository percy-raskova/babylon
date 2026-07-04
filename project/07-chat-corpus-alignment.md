# 07 — Chat-Corpus Alignment (2026-07-03)

**What this is**: Percy asked for the full claude.ai chat history to be mined
and reconciled against this kit so the plan covers a COMPLETE GAME. Three
parallel miners read 271 Babylon conversations (filtered from 1,834 in
`/home/user/projects/claude-chats/conversations.json` by content keywords)
plus all 13 "Babylon Design System" project chats. Citations are chat
titles + dates; the extraction recipe: filter `conversations.json` on
babylon/MLM/imperial-rent/dialectic/… keywords, render messages to markdown.

Endorsement legend: **[E]** Percy proposed/ratified it; **[F]** floated by
Claude, engaged but not ratified; **[V]** Percy's stated long-term vision,
explicitly deferred.

## 1. OWNER DECISIONS — ALL RULED 2026-07-03

Percy ruled on all five inline (her verbatim rulings kept below each
item). Operational consequences are consolidated in the "Rulings
applied" paragraph after the list.

1. **Palette is contested four ways.** Constitution Article VII binds
   CRIMSON/SAFFRON/GREY/BLACK, no decorative glow; design-system V1 "Bunker
   Constructivism" (2026-05-17) uses gold `#c8a860` primary + CRT
   glow/scanlines (the banned chartjunk — and Percy later disowned the
   bunker vibe: "just sounded cool but I'm not particularly attached");
   V8 "Cold Collapse" (2026-06-04) repalettes to cyan `#4dd9e6` primary +
   laser red — **but no Percy quote directs V8; it may be design-agent
   drift**; the logo chat (2026-05-13) says "skip pure crimson and gold"
   for rust-oxide/bone/ink/brass. RECOMMENDATION: anchor on what she
   personally ratified — Kitty-Crimson terminal palette as primary source
   (2026-01-31, "yep!" to GOLD=solidarity semantics), JetBrains Mono (the
   one convergent font across V8+logo+Wire), logo palette scoped to the
   MARK not the UI; treat V8 cyan as unverified until she confirms.

   **I trust the AI judgment on what looks best, impress me.** - percys ruling

   *(Superseded on the facts 2026-07-03 — see §7: a full replay of the
   design-chat export found Percy's verbatim ratification of Cold
   Collapse cyan; "V8 may be drift" was wrong. The ruling above still
   governs authority; the anchor palette is Cold Collapse.)*

1. **Steam desktop binary vs. web app.** The endorsed Steam plan
   (2026-02-06) packaged a PyInstaller/PyQt6 desktop binary; the later web
   pivot (Django+React, Unity rejected 2026-05-18) is the current
   commitment. The business model (open core + paid convenience, "I
   deserve compensation and I feel this is fair") survives either way.
   RECOMMENDATION: web app remains the product; Steam ships a wrapped web
   build (or Electron-style shell) as a Wave-6 distribution spec; retire
   the PyQt6-binary plan explicitly (PyQt6 stays a dev tool).

   **We are going to continue with the Web App as we hvae it.** - percys ruling

1. **Workers-AI/LoRA narrator vs. server-side pgvector RAG.** 2026-03-01
   ratified a Cloudflare Workers AI narrator (GPT-OSS-20B, tool-calling);
   2026-05-12 has Claude arguing edge-RAG/LoRA is a constitution-violating
   scope slide while Percy stays enthusiastic — unresolved.
   RECOMMENDATION: they are compatible if separated — narrator (the Wire's
   voice, one tool-call per tick, template fallback) runs on Workers AI
   per the endorsed 12-page Cloudflare spec; the Archive (semantic
   history/RAG) stays server-side pgvector per spec-037. No LoRA.

   **We are using Workers-AI/LoRA narrator** - percys ruling

1. **"No victory state" vs. the `REVOLUTIONARY_VICTORY` GameOutcome.**
   The principle (Tragedy of Inevitability, ~15 chats) coexists awkwardly
   with the 5-outcome enum. RECOMMENDATION: keep the 5 outcomes as
   TERMINAL STATES (characters of collapse, not wins) and ship the
   CK-style **chronicle end-screen** + Victoria-3-style **Journal**
   objectives (2026-04-12, 2026-03-01) as the UX that expresses the
   principle. Attach to spec-081/085.

   **I accept recommendation** - percys ruling

1. **Single-Postgres constitution vs. CONUS/federation ambition.** Percy:
   "I want it at scale for… the entire US." Not urgent (she declined
   FalkorDB: "not implementing"), but the eventual path is a
   constitutional amendment + the **columnar substrate refactor**
   (numpy/Arrow columns for hexes, Pydantic at boundaries only; Kuzu
   favored if a graph backend is ever needed). Park in Wave 7.

   **Lets try to keep it all in postgres** - percys ruling

**Rulings applied (2026-07-03)**:

1. **Palette → AI discretion** ("impress me"). Design authority is
   delegated; constraints that still bind: Constitution VII no-chartjunk,
   JetBrains Mono, GOLD=solidarity semantics she ratified. The palette
   becomes a design deliverable in the Wave-6 visual-identity spec, not a
   blocker before it.
1. **Delivery → web app as-is.** The PyQt6/PyInstaller desktop-binary
   plan is retired (PyQt6 stays a dev tool). Steam (M7) becomes a
   wrapped-web distribution question inside Wave 6.
1. **Narrator → Workers-AI, LoRA in scope.** Percy chose the full
   Workers-AI/LoRA side — this OVERRIDES the "No LoRA" recommendation;
   LoRA fine-tuning of the narrator voice is in scope for the M8/X1
   narrator spec. The Archive (semantic history/RAG) split was not ruled
   against: pgvector stays server-side per spec-037 unless she says
   otherwise.
1. **Victory-UX → recommendation accepted.** 5 outcomes stay as terminal
   characters-of-collapse; chronicle end-screen + Journal ship with
   081/085 (M4).
1. **Scale → single Postgres.** Federation/columnar substrate (M10) stays
   parked in Wave 7; no constitutional amendment now. Scaling work happens
   inside one Postgres.

**Provenance note on the Lawverian foundation**: no historical chat
endorses adjoint functors as the engine foundation (the idea arrived
2026-02-17 in a separate LLM project; the 2026-04-26 "Category theory
meme" chat has Percy mocking duality-chasing, with CT judged to earn its
keep only as: H3 aggregation as a SHEAF, edge modes as a PRESENTED
CATEGORY, material/ideological as a FIBRATION). **Percy's 2026-07-02
directive supersedes this** — the Lawvere refactor is owner-ordered — but
the discipline stands and is now written into `06`: every categorical
construct must earn its keep in laws/predictions, and those three
endorsed structures are explicit targets.

## 2. Endorsed-but-uncatalogued mechanics (add to the wave plan)

| #   | Item                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Status               | Attach to                                     |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | --------------------------------------------- |
| M1  | **Commodity-flow routing ("slime mold")**: per-tick min_cost_flow of firm orders over (hex × SCTG) O-D pairs, `effective_capacity = capacity × condition`, severed edges → 0, unrouted demand → unrealized value → realization crisis; per-edge conductivity EMA `D(t+1) = (1-α)·D + α·abs(Q)` so corridors form/decay visibly (width ∝ log D). Percy asked for the spec-kit prompt herself (2026-04-21 ×2, 2026-05-03). Makes ATTACK/edge-severing economically real; substrate (036/046/023) ~70% exists.       | [E]                  | Wave 3, companion to 075                      |
| M2  | **Prose→stance-vector verb input**: player writes praxis prose → out-of-tick LLM structured-output parser → frozen per-verb `StanceSchema` (mass_vs_vanguard, framing, audience, duration) with coherence invariants that REFUSE incoherent praxis (the refusal is the political education) → confirm → deterministic tick. Presets as fallback. "make it open ended with structure and guardrails" (2026-04-12). Stance = signed intervention on an opposition's balance — front-end of the dialectics refactor. | [E]                  | Wave 3 verb specs + audit-087 (RAG/LLM infra) |
| M3  | **Verb sub-modes**: the 9 verbs are ~20+ interventions (REPRODUCE cadre/mass, MOVE expand/relocate, MOBILIZE strike/demo/blockade, ATTACK targeted/mass, NEGOTIATE edge-type); "the UI needs to surface sub-modes clearly" (2026-04-27).                                                                                                                                                                                                                                                                          | [E]                  | Wave-3 verb specs + frontend                  |
| M4  | **Chronicle end-screen + Journal objectives**: CK-style retrospective ("what character of collapse you produced, which organizations outlived the state"), Vic3-style Journal for goals-without-victory.                                                                                                                                                                                                                                                                                                          | [F, principle E]     | 081 + 085                                     |
| M5  | **Resource-substrate ledger**: parallel physical-units ledger (MWh, tons, GPU-hours) feeding `c` price coefficients via MELT; grounds synthetic biocapacity with EIA-861/USGS MCS; physical shocks = discrete crisis resets; compute instrumented through BEA I-O (NAICS 5182/334413), NOT a first-class primitive (2026-05-10).                                                                                                                                                                                  | [E desire, F design] | Wave 5                                        |
| M6  | **Modding + console**: TOML override files (`config/defaults/` read-only + cited; `mods/` user path; Pydantic model-merge) + sandboxed in-game console (Tcl safe-interp or lupa; `advance N`, `inspect <hex>`, `set_param`), raw REPL gated out of hosted builds (2026-02-06).                                                                                                                                                                                                                                    | [E]                  | Wave 6                                        |
| M7  | **Steam distribution + tiered AI**: open core free + paid Steam convenience; Win/Mac/Linux; type=Game; local sentence-transformers + template fallback default, BYOK toggle, optional managed sub (2026-02-06, 2026-02-24).                                                                                                                                                                                                                                                                                       | [E]                  | Wave 6 (subject to Decision 2)                |
| M8  | **Production deployment track**: Hetzner CX32 (Django+Gunicorn+Nginx+Postgres w/ PostGIS+pgvector+AGE) + Cloudflare (DNS `babylon.percypedia.biz`, TLS/WAF/CDN, R2 for reference-SQLite/replays/assets, Workers AI narrator, AI Gateway, Turnstile, Tunnel, origin lockdown) + Woodpecker CI. A 12-page spec-kit PDF exists (2026-03-01, reaffirmed 2026-05-12). Kit currently stops at "works locally".                                                                                                          | [E]                  | New infra track, Wave 6                       |
| M9  | **International circulation layer ("Volume IV")**: trade blocs as continental world-system zones (Core/Semi-Periphery/Periphery), Layer-0 background metabolism, NOT agentic ("background noise"), exogenous shock source; needs constitutional amendment (recursion currently terminates at national scale) (2026-03-03, 2026-05-03).                                                                                                                                                                            | [V]                  | Wave 7                                        |
| M10 | **Scale-out/federation**: CONUS ≈ 2M hexes/50M edges; the cliff is Pydantic-per-hex (fix: columnar substrate) + Ollivier-Ricci LP (fix: cache/Forman); the graph half got its first concrete step in Amendment L/ADR052 (rustworkx BabylonGraph — `08-graph-substrate.md`); `FederatedBoundaryNode` for interoperating national instances (2026-05-12, 2026-01-29).                                                                                                                                               | [V]                  | Wave 7                                        |
| M11 | **Liberated-zone mechanic**: org→institution transformation creating a bidirectional spatial boundary the state can dissolve (2026-05-10).                                                                                                                                                                                                                                                                                                                                                                        | [F]                  | Wave 4/5                                      |
| M12 | **Speed controls + hard pause** (Vic3-style) (2026-04-12).                                                                                                                                                                                                                                                                                                                                                                                                                                                        | [F]                  | frontend, Wave 3                              |

## 3. Experience layer (the game's skin — kit was thinnest here)

| #   | Item                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Status          | Attach to                                                   |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ----------------------------------------------------------- |
| X1  | **AI narrator voice + stack**: voice = Mao's "Oppose Stereotyped Party Writing" (8 sins as generation constraints); register "wire-service-meets-political-briefing," never editorializes the player's choices, never breaks 4th wall; GPT-OSS-20B one call/tick via `narrate_tick` tool → `{headline, body, strategic_implication, tone∈{ROUTINE,TENSING,CRISIS,RUPTURE}}`; tone drives UI treatment (palette shift, sound cue, rupture moment); JSONB → queryable game log + tension graph; template fallback emits identical JSON (2026-03-01).                                                                                                                                             | [E]             | audit-087 + Wire spec                                       |
| X2  | **Gramscian Wire triptych**: every significant event renders 3 ways — Corporate Feed (hegemonic euphemism), Liberated Signal (counter-hegemonic samizdat), Intel Stream (raw engine data, deterministic fallback); euphemism dictionaries in system prompt; hegemony level drives visibility/presentation-order; API downtime is diegetic ("signal interference"). Triptych UI already designed (2026-05-17 efb8da9e); "this becomes possible with tool calling."                                                                                                                                                                                                                              | [E]             | Wave 3 (077's display surface)                              |
| X3  | **In-game wiki via composable/recursive tooltips** = the onboarding/pedagogy strategy: nested hoverable definitions sourced ONLY from the Constitution (no fresh authoring, no LLM paraphrase; term without constitutional definition gets no tooltip → vocabulary-drift linting); derived quantities drill into the ledger query + primitives; Vic3-style typed EntityRef + panel registry + Zustand nav stack (2026-04-14 "narratively strong", 2026-04-13).                                                                                                                                                                                                                                 | [E]             | Wave 6 (085) but the term-registry linter can start anytime |
| X4  | **Verb-page UX**: feedforward projections, unavailable-targets-with-reasons, real-number tradeoffs ("AID reduces agitation 0.08; your education pressure is 0.12"), ATTACK shows value_tensor_role + consciousness-cascade readout, verb-pairing consequence tables (Panthers/charity/NGO models); never restrict choice — over-budget degrades (I.11); 3×3 verb grid grouping Build Org / Project Power / Manage Resources (2026-04-27, 2026-04-10).                                                                                                                                                                                                                                          | [E]             | Wave-3 verb specs                                           |
| X5  | **Visual identity**: logo direction = ziggurat in cross-section/collapse (internal 4-node recursion visible) or H3-hex with defecting node ("George Jackson moment") — prototyping requested, no final pick; mark palette rust-oxide/bone/ink/brass; aesthetic = "federal statistical report meets brutalist web" (BLS/USGS conventions, no rounded corners, research instrument not video game).                                                                                                                                                                                                                                                                                              | [F→E aesthetic] | Wave 6; Decision 1 governs UI palette                       |
| X6  | **Map/data-viz specs**: value-flow as DISCRETE ARROWS on real graph edges (never interpolated field — "physics cosplay"), one flow type per render (recommend Imperial Rent Φ via CFS antisymmetric component, already computed), density-aware LOD — new lens in spec-042 surface (2026-05-03); BubbleSets hyperedge hulls + 9×9 community co-occurrence heatmap (built artboards 2026-05-17); six named choropleth ramps; unit iconography grammar (skull-with-dagger insignia: piercing = function, flora = region, condition = phase) (2026-01-27); hex-as-invariant-substrate — political boundaries are temporal overlays over the eternal H3 grid (sovereignty rendering) (2026-01-26). | [E]             | Wave-3/6 viz work                                           |
| X7  | **Audio direction**: Detroit industrial/experimental — mathcore, industrial-krautrock, industrial-hardcore (5 commissioned Suno tracks, 2026-05-20); narrator tone enum was DESIGNED to trigger sound cues; no kit item exists.                                                                                                                                                                                                                                                                                                                                                                                                                                                                | [E taste]       | Wave 6                                                      |
| X8  | **Accessibility gap (genuine, not just unrecorded)**: no colorblind/screen-reader/WCAG treatment anywhere, while Article VII makes color carry meaning across six ramps. Luminosity=magnitude is a partial mitigation, never stated as a requirement. ADD: colorblind-safe ramp validation + redundant non-color magnitude channel + keyboard-nav spec (frontend lists it as an open question).                                                                                                                                                                                                                                                                                                | gap             | Wave 6, alongside 085                                       |
| X9  | **Synopticon surface**: the Lavender/Gospel algorithmic-targeting UX (F2T2EA kill chain, Digital Dossier, risk scores) as the player-facing face of state repression (2026-05-17 fd895fa0); also note the PyQt6 "God Mode" desktop dashboard is a RUNNING artifact the React plan ignores — keep as dev tool per Decision 2.                                                                                                                                                                                                                                                                                                                                                                   | [F/E]           | 078/079                                                     |

## 4. Dialectics-engine findings — SHIPPED in ADR051

(Originally written into `06` §9 as requirements; implemented 2026-07-03.)

Endorsed design the Lawvere refactor must absorb: the **composition
algebra** (⊗/⊕/nesting; poles can be dialectics — the fractal); the
**cyclical fixed-point tick ontology** (convergence=reproduction,
non-convergence=crisis, higher-order bifurcation=sublation — "the
unification"); **typed morphism graph** (feeds/constrains/transforms/
contains/antagonizes) with **verbs as morphism mutations**;
**sublation lineage** (parent→successor first-class);
**observation-relativity** (observe() is frame-dependent);
**VIII.9 n-ary protection** (dyadic OppositionSpec must not re-collapse
internal nations into one pole); **Φ tri-decomposition** (Emmanuel-Amin /
Meillassoux / Fortunati components stay separable — three measured
defects, not one scalar); the **RLF simplex constraints** (entropy =
contestation diagnostic ONLY; f→r forbidden/ε-gated breaking detailed
balance → no potential function → standing leak, organizing as the pump;
r→f carries capacity transfer) — feeds 071. Precise formulas the chats
pin are quoted in `06` §9.4.

## 5. Confirmations (kit already right — no action)

Tick=week/520=decade; 9 verbs via Organizations only; Ontario boundary
terminator; Vic3 as UI reference; multi-page anti-god-page (her
most-defended UI conviction, ~5 chats); Briefing=post-tick newspaper;
deck.gl H3 map; hyperedge rendering per VIII.9; AI-observes-never-controls
across narrator/tooltips/Wire; material-base-first tick order; state AI 6
verbs/24 sub-verbs + twin pools; crisis-gated consciousness; conservation
invariant catalog; Postgres runtime + SQLite reference; web pivot (Unity
rejected, PyQt6 dev-only).

## 6. Kit changes made from this review (2026-07-03)

- `06-lawverian-dialectics.md`: added §9 (chat-sourced requirements +
  precise math + earn-its-keep discipline + the three endorsed CT
  structures); Phase C2/D/E scopes amended.
- `05-catalog-execution.md`: wave order updated with M1-M12/X1-X9
  attachments; owner-decision pointers added.
- `00-mission.md`: "complete game" definition now points here.
- This file created as the master record.

## 7. Design-canon recovery + program-09 attachments (2026-07-03, evening)

A second, deeper mining pass replayed the raw `design_chats/` export
(7 core "Babylon Design System" conversations; the mockup source code
is embedded as `write_file`/`str_replace_edit` tool-call payloads).
Corrections and status changes against §§1–3:

- **Palette (Decision 1) — factual correction**: Cold Collapse
  (cyan `#4dd9e6` primary, gold demoted to scarce `rupture #d4a02c`)
  was **Percy-ratified in-chat** (2026-05-17: "YES! LETS FUCKING GO
  CLAUDE!!!! … I want this to become official babylon canon … Lets
  redesign it all"). The §1 caveat "V8 may be design-agent drift" is
  wrong. Anchor = Cold Collapse under the "impress me" authority
  delegation. **Constitution catch**: Article VII literally binds
  "GOLD (action/solidarity)" — the amendment ships with spec-090
  (`09-program-full-game.md` §1 R-VII). Typography ratified in the
  same chat: JetBrains Mono / Space Grotesk / Redaction / Departure
  Mono; Inter + Roboto Mono explicitly rejected.
- **X9 correction**: the PyQt6 "God Mode" desktop dashboard is NOT a
  running artifact — `src/babylon/ui/` was deleted 2026-05-10 (commit
  `323e4d30`). Its web-native successor is the **Observatory**
  (program-09 specs 096/099, over the runtime DB). The in-game
  Synopticon surface (same name collision, different thing) stays
  attached to 078/079.
- **Mockups staged in-repo**: `design/mockups/` (66 files, 643 KiB) —
  final file states recovered by chronological replay; recipe +
  fidelity caveats in `design/mockups/PROVENANCE.md`; per-file
  provenance in `manifest.json`. Nobody needs to re-mine the export.
- **Attachment updates**: X5 visual identity → **executing as
  spec-090**; X2 Wire triptych → **spec-094** (deterministic
  `NarratorProvider` now; Workers-AI/LoRA per Decision 3 lands with
  M8); M4 chronicle/Journal surfaces → **spec-095** (081 enriches
  later); M9 international layer → first spec set = **100–103**
  (owner-scoped 2026-07-03; no amendment needed while blocs stay
  non-agentic — `09` §1 R-AMEND); M12 speed controls + X6 map-viz
  lens work → fold into 093's map upgrade where in scope.
- Trade-UI decision confirmed from the corpus (2026-03-03): blocs are
  background noise, **no interactive world map**; CONUS stays primary.
- Map hierarchy confirmed decided (2026-04-10): CONUS → BEA Economic
  Areas (~300 max) → counties; Michigan modeled whole
  (`specs/040-michigan-statewide-scope`).
