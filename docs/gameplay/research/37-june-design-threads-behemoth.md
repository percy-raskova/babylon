# 37 — June 2026: the month with no design record

Read-only memory research, 2026-10-26. Window: **2026-06-01 through 2026-06-30**, inclusive.
Question asked: *what did the Director establish in June 2026 about how the game should feel — the topology
graph as a living/behemoth thing, and any UI-as-art direction?*

The window is empty. Not thin, not partly indexed, not hidden behind a bad query: **empty**. June 2026 contains
no Babylon observation, no Babylon session, no Babylon commit, and no Director statement about game feel. This
briefing proves that, then supplies the two brackets — what the record says immediately before the gap and
immediately after it — so the absence can be used rather than merely reported.

Every claim carries a class. **O** = observed record fact, verifiable in the store or the repository.
**D** = attributable to the Director (owner) rather than to an agent. **A** = an agent's interpretation.
There are **zero D-class claims inside the window**. That is the finding.

---

## 0. Thesis

1. **June 2026 is a dead month in this project's history** — a development gap between 2026-05-20 and
   2026-07-02 with no design discussion of any kind inside it. **O**
2. **The "living/behemoth topology" language did not come from June, and it did not come from July either.**
   The earliest aesthetic use of "behemoth" in memory is **2026-10-26**, in the same research session that
   commissioned this briefing. It is this week's vocabulary, not inherited doctrine. **O**
3. **The only binding aesthetic law the project has ever ratified is anti-ambient.** §9b (2026-07-11) removes
   glow, gradient and rounding from chrome; §11 (adopted 2026-07-14) imposes one motion budget and no ambient
   animation. A "pulsating behemoth" screen therefore has no ratified home. It would have to be legislated,
   not discovered. **D/O**
4. **The two-tier exposure doctrine has no June foundation at all.** It is a 2026-10-26 construction
   (sessions S11166, S11167). Any claim that it "continues" a June line of thinking is false. **O**

---

## 1. Method, and one honest caveat

Semantic search was unavailable for the whole of this pass. Chroma MCP was in backoff and the keyword
fallback rejected every date-filtered call outright (`Semantic search is offline (Chroma MCP unreachable…)`,
triggered on `dateStart`/`dateEnd`). Unfiltered keyword searches did return, and they never surfaced June
Babylon material — but "keyword search found nothing" is weak evidence on its own.

So the window was verified **directly against the memory store in read-only mode**
(`file:/home/user/.claude-mem/claude-mem.db?mode=ro`, tables `observations`, `session_summaries`,
`sdk_sessions`, `user_prompts`) and against repository history (`git log --all`). The counts below are
exhaustive for the window, not sampled. **O**

Two negative results worth recording because they close off "maybe it is filed elsewhere":

- `/home/user/.open-mem/open-mem.db` holds **0** June observations and **0** Babylon observations of any date. **O**
- The repository contains **no file** whose name matches `*2026-06*`. **O**

---

## 2. The window's entire content

June 2026 holds **10 observations**, in **2 memory sessions**, on **2026-06-01 between 00:00:51Z and
00:12:09Z** — twelve minutes, all of it the tail of a session that began 2026-05-28.
All ten have `project = 'cycles'`. None have `project = 'babylon'`. **O**

| Item | Count | Detail |
|---|---|---|
| June observations | 10 (#39535–#39544) | all `cycles`; Cloudflare Pages deploy of a multiplayer/CPU-select menu |
| June session summaries | 3 (#3069–#3071) | all `cycles`; same deploy, plus an AGENTS.md/README correction |
| Sessions *started* in June | 0 | the surviving row for these rows starts 2026-05-28 (#`45131dae…`) |
| June user prompts | 2 (#4015, #4016) | "deploy the SPA to production"; "correct that section yes" |
| June git commits, all branches | 0 | last before gap 2026-05-20; first after gap 2026-07-02 |
| June `babylon` observations | 0 | — |

The subject matter is unambiguous and irrelevant to game feel. #39537 records a production SPA upload; #39539
documents a two-target Cloudflare deployment model; #39543 corrects a README claim about git integration. The
only sentences in June that touch a player's perception are about a **stale service worker** — users had to
hard-refresh to see a new UI (#39542). That is a caching bug in a different game. It is not design. **O**

May 2026 is likewise not a design month. Its Babylon observations for 2026-05-19 through 2026-05-28 are
Spec-070 balkanization planning, endgame-detector tests, GraphProtocol method contracts, and data-preflight
schema work (#37874–#38291). Topology appears there as an **engineering contract**, never as a felt object. **O**

The nearest thing to a "pulsating" precedent is the *cycles* project on 2026-05-28, where an agent removed
dot drop-shadow halos and reduced a horizon stripe to kill a moiré pulse (#38882, #38891, #38893). Different
project, opposite intent: that work was *removing* a pulse from a website. It is not an antecedent. **O**

---

## 3. The brackets

Both brackets fall outside the assigned window. They are recorded only to locate the null. The July cluster
is the sibling miner's assignment; I cite specific rows and claim no coverage of it.

### 3.1 Before the gap — nothing to inherit

Last Babylon observation before June: **2026-05-28T00:48:07Z**. Between that date and 2026-07-02 the
repository has no commits on any branch. There is no late-May aesthetic ruling, no design bible, no
"living map" note waiting to be continued. The gap is total. **O**

### 3.2 After the gap — the first ratified aesthetic law

The design record opens on **2026-07-11** with commit `42921e1fa` (*docs(program-16): Phase R research corpus
(21 reports) + Design Bible + charter*). Two directives matter here.

**§9b, the Installer ruling — 2026-07-11.** The Director set the chrome language against three Guix 1.5.0
installer screenshots plus the ksbc-new Kitty theme: flat plates, hard shadows, title tabs, inverse-video
selection, chunky button keys, in crimson/gold on near-black instead of Guix blue. The ruling **re-aims the
juice pass** — it *removes* gradient, rounded-corner and glow items and *adds* hard-shadow press,
inverse-video selection, and a gold flash. Cold Collapse tokens are explicitly preserved for the map canvas.
(#52672, #52675, #52680, #105843) **D** — recorded as the owner's binding ruling, not an agent proposal.

**§11, the weather grammar — adopted 2026-07-14, marked binding.** Four laws: *extensive = stuff,
intensive = color*; *quantities flow, qualities cut*; *one motion budget*; *curvature held*. The same bible
records **no ambient animation** as a §11 constraint. (#69421, #64788) **D**

Read together, the ratified position is: **chrome is austere and hard-edged, the canvas carries the
information, and motion is rationed.** That is the ground any new screen-feel proposal actually stands on.

---

## 4. "Behemoth" has no pedigree

This is the correction most likely to matter to the parent session, so it is stated flatly.

A search of every observation title in the store for "behemoth" or "shoggoth" returns:

- **2026-07-23** (#121280) — "origin/101-trade-activation is a 4.5M-line **behemoth** from an earlier era."
  A code-size metaphor. Not design.
- **2026-10-26** (#199016, #199023) — the current research session, framing the topology feel as a
  "living, monstrous entity" and searching for "pulsating behemoth", "shoggoth".

"Shoggoth" occurs **once in the entire store**, at #199013, today. "Pulsating behemoth" occurs nowhere before
today. #199023 is explicit that its own search for "behemoth shoggoth monster alien topology graph feel"
returned only itself plus unrelated Dec-2025 observations about *AI model behaviour*, which it then offered
as "historical context". **O**

Separately, "Behemoth" is also a **game mechanic** with a real October pedigree: the Department of War
meta-cell adversary (research/18), at #195628 and #195830, 2026-10-25. A miner grepping "behemoth" across
memory will collide with this immediately. **O**

> **Consequence.** There is no June or July directive that the topology graph should feel like a behemoth,
> a monster, an alien, or a shoggoth. That vocabulary is a **2026-10-26 framing**, and the §9b/§11 record
> constrains it rather than supporting it. If the Director wants it, it is new law — which is exactly the
> kind of change `AGENTS.md` says to stop and ask about, not to infer from an old ADR.

---

## 5. Contradiction analysis against the two-tier exposure doctrine

The doctrine as established today: **Tier 1** public, verifiable statistics as exact Tufte-clean numbers;
**Tier 2** internal engine mechanics (heat, legitimacy) only as visual cues, derivatives, or second- and
third-order change — "weather", never raw data; sensory channels act as a **precursor** to facts, and
"feeling must always lead to knowing" (S11166, S11167). **D**

No June material contradicts it, because there is no June material. The live contradictions are with the
July laws that would have to host it.

**C1 — Chrome is anti-ambient, and Tier 2 wants a surface. (direct, unresolved)**
§9b removes gradient, rounding and glow from chrome and adds hard shadows and inverse-video flashes
(#52672, #105843). Tier 2's "ambient pressure, low stingers, screen weather" (S11167) is soft, continuous
and peripheral. These are not the same visual language. The escape hatch is already written into the ruling:
Cold Collapse tokens survive **on the map canvas** (#52672). So Tier 2 cues belong to the canvas, and any
attempt to express them through window chrome contradicts a ratified Director ruling. **D**

**C2 — "One motion budget" versus a pulsating graph. (direct, unresolved)**
§11 binds *one motion budget* and the bible separately records *no ambient animation* (#69421, #64788).
A living, breathing, pulsating topology is ambient motion by definition. This is the sharpest conflict in
the record, and it is not a matter of taste: §11 is marked **binding**. A breathing map requires an
amendment to §11 or an explicit carve-out for the canvas. **D**

**C3 — §11's first law is the bridge, not the obstacle. (aligned, exploitable)**
*Extensive = stuff, intensive = color* (#69421) is almost a restatement of the two-tier split: extensive
quantities (money, personnel, materiel) are countable objects and belong to Tier 1; intensive quantities
(heat, legitimacy, solidarity) are field-like and belong to colour and texture, which is Tier 2. The
doctrine can be argued *through* §11 rather than against it — and this is the strongest available precedent
for Tier 2 existing at all. **D**

**C4 — "Feeling must lead to knowing" has no affordance in the aesthetic law. (gap, not contradiction)**
S11167 requires that every sensory cue terminate in a verifiable fact. Neither §9b nor §11 specifies a
verification surface — no inspect action, no drill-down, no receipt view. The doctrine therefore asks the UI
for a step the design bible never designed. That is a missing mechanism, and it is the part most likely to
be skipped by an implementation that only chases atmosphere. **D**

**C5 — A beautiful BI dashboard is still an administrative display. (tension with repository law)**
S11166's note states the goal is "to make the BI dashboard itself a beautiful object, where the artwork
serves as the metric." Repository law holds that *each game display must answer a decision question* and
that *an administrative display cannot pass a game milestone* (`AGENTS.md`, Constitutional compact). Beauty
is not a decision question. This is not a memory contradiction — it is a rule the current doctrine has not
yet reconciled, and it should be resolved before any topology-screen work starts. **D vs repo law**

---

## 6. What the Director would actually have to decide

Ordered by how much downstream work each unblocks.

1. **Does the topology graph get an exemption from §11's "one motion budget" / "no ambient animation"?**
   Without an answer, every "living map" proposal is unbuildable against binding law. (C2)
2. **Is Tier 2 canvas-only or chrome-wide?** §9b already implies canvas-only for soft effects. Confirming it
   turns a contradiction into a boundary. (C1)
3. **What is the verification affordance?** The doctrine's own terminal condition — feeling leads to knowing
   — needs a named interaction. (C4)
4. **Is a beautiful BI dashboard a game display?** If yes, it needs a decision question attached, not just an
   aesthetic. (C5)
5. **Ratify or retire the "behemoth" vocabulary.** It currently exists only as a 2026-10-26 framing and will
   otherwise be mistaken for history by the next miner. (§4)

---

## 7. Evidence index

**Window (June 2026)** — #39535–#39544 (10 `cycles` observations, 2026-06-01T00:00:51Z–00:12:09Z);
#3069–#3071 (3 `cycles` session summaries); #4015, #4016 (2 `cycles` prompts); session `45131dae…` started
2026-05-28T04:58:07Z. Git: no commit between 2026-05-20 and 2026-07-02.

**Pre-gap (May 2026)** — last Babylon observation 2026-05-28T00:48:07Z; May 19–28 content is Spec-070,
GraphProtocol and data-preflight work (#37874–#38291); `cycles` pulsating-effect fixes #38882, #38891, #38893.

**Post-gap (July 2026, sibling's window — bracketing only)** — `42921e1fa` (2026-07-11, Phase R corpus +
Design Bible); §9b Installer ruling #52672, #52675, #52680, #105843; §11 weather grammar #69421 and
no-ambient-animation #64788.

**Vocabulary** — "behemoth" as code-size metaphor #121280 (2026-07-23); as design framing #199016, #199023
(2026-10-26); "shoggoth" #199013 (2026-10-26, sole occurrence); mechanical "Department of War Behemoth"
#195628, #195830 (2026-10-25).

**Doctrine (2026-10-26)** — S11166 (two tiers established), S11167 (sensory refinement, "feeling must always
lead to knowing"), notes recorded under both.

**Tooling** — `claude-mem.db` read-only at `/home/user/.claude-mem/claude-mem.db`; `open-mem.db` holds no
Babylon or June data; semantic search unavailable throughout (Chroma backoff, date filters rejected).
