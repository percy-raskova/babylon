# T6 ruling — the tutorial IS the BDD acceptance suite (BD, 2026-07-21)

> BD (verbatim intent): "in terms of e2e testing, the tutorial itself can be a kind of
> behavior-driven development final set of checks. 'Does the Babylon System behave? Does
> every option that gets clicked work as advertised?' And the BDD itself can be
> educational about how the game works for developers."

Binding on the T6 lane and the T8 DoD. Supersedes the plan's tutorial section where they
differ; everything else there (opening-arc overlay, authored vault pages, doctor
preflight) stands.

## The unification

ONE artifact — a data-driven tutorial step script — consumed three ways:

1. **Player**: the guided opening-arc overlay renders each step's Given/When/Then as
   instruction text over the live campaign (scripted first-session keyed to real state).
2. **CI**: the e2e harness executes the same steps headlessly (Textual Pilot idiom, the
   WO-50 `test_pilot_first_action.py` pattern) — drives the When, hard-asserts the Then.
3. **Developers**: the scenario suite reads as living documentation of how the game
   works. Scenario names are sentences; the suite is the game-loop's behavioral contract
   (the "rewrite test" for the whole client: a rebuilt TUI is correct iff the tutorial
   suite passes against it).

Because the strings the player reads ARE the scenario definitions CI runs,
advertisement and behavior cannot drift apart — a step that stops being true goes red in
CI before a player ever sees the lie. III.11 Loud Failure applied to UX.

## Design constraints (T6 lane spec)

- **Step script = frozen Pydantic data** (`TutorialStep`: id, given, when, then,
  anchor — the page/binding/verb it exercises, completion predicate). No prose
  duplication: overlay text and scenario name render from the same fields.
- **Coverage check, ADR090-style (declared and proved)**: enumerate every player-facing
  option the campaign shell surfaces (BINDINGS, verb plates, palette commands, lobby
  actions); a static check asserts each appears in ≥1 tutorial/BDD scenario or carries a
  cited exemption. An option with no scenario is a seam (∂L boundary node) — red.
- **Harness**: pytest + Textual Pilot (existing idiom). NO new BDD framework/Gherkin
  dependency — Given/When/Then live in the step model; educational value comes from the
  data and generated docs, not from cucumber tooling.
- **Tiering**: the suite runs headless-deterministic (narrator OFF, fixed seed, Wayne
  golden scenario for CI; nationwide steps tiered to the qa lane if runtime demands).
- **T8 DoD amendment**: "tutorial completes" → "tutorial BDD suite green headlessly AND
  completable interactively" + the option-coverage check green.

## Placement

- T6 lane builds: step-script model + the opening-arc overlay consumer + the Pilot
  executor + the option-coverage sentinel + authored tutorial vault pages (unchanged).
- T4-core's C2 (bindings) and C3 (driver) are upstream anchors — the coverage
  enumeration reads THEIR registries; no T4 rework required.
