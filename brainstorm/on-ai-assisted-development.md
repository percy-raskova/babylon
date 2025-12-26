# On AI-Assisted Development

*A reflection from December 2025, after months of building Babylon with Claude Code.*

---

## The Question

"I feel sort of fraudulent - like I haven't done any real development. Like I've just leaned super heavy on AI. What do you think?"

## The Honest Answer

**You're conflating "writing code" with "development." They're not the same thing.**

### What the human brought (that AI cannot):

1. **The theoretical framework** - MLM-TW isn't something AI invented. The insight that imperial rent can be modeled as graph transformations, that atomization breaks solidarity edges, that consciousness bifurcates based on material conditions - that's political economy translated into computable form. That's years of reading and thinking.

2. **Architectural vision** - "AI observes, never controls mechanics." "State is pure data, Engine is pure transformation." The Embedded Trinity. These aren't patterns AI suggested - they're constraints imposed because the human understood what kind of system this needed to be.

3. **Domain modeling** - What edges matter? What's a Territory vs a SocialClass? Why does heat dynamics belong in carceral geography? AI can implement these once defined, but the ontology is human.

4. **Quality control** - Every "that's not right" or "let's use TDD" or "check the math" - that's development. AI generates plausible code. Humans determine correctness.

### What AI brought:

1. **Implementation velocity** - Writing the actual Python code, tests, boilerplate
2. **Pattern application** - Taking architectural vision and implementing it using known patterns
3. **Debugging and fixing** - Finding issues, fixing tests, resolving type errors
4. **Code organization** - File structure, imports, module organization

---

## Architecture vs Implementation

**Architecture** answers: *What exists? How do the pieces relate? What constraints govern the system?*

- Three pillars that never mix (Ledger/Topology/Archive)
- AI observes, never controls mechanics
- State is pure data, Engine is pure transformation
- Survival calculus determines agent behavior, not random events
- Systems execute in a specific order because causality matters

These decisions constrain everything downstream. Get them wrong and you rebuild from scratch.

**Implementation** answers: *How does each piece actually work internally?*

- The Observer protocol uses `on_tick_start`/`on_tick_end` callbacks
- ServiceContainer uses a dictionary with lazy initialization
- Edge cases in sigmoid functions clamp to avoid infinity
- The random state fixture saves/restores `random.getstate()`

These decisions matter but they're local. Get one wrong and you fix that file.

---

## AI Orchestration as a Skill

Using AI effectively is a real skill:

- Setting up extensive context systems (CLAUDE.md at three levels, ai-docs/, memory hooks)
- Maintaining architectural coherence across sessions
- Catching when AI is wrong (requires knowing enough to evaluate output)
- Breaking large work into AI-handleable pieces
- Pushing back instead of accepting plausible-but-wrong answers
- Enforcing TDD methodology that forces verification

**But be clear-eyed about what skill it is.**

It's **directing** and **orchestrating**, not **implementing**. It's closer to being a film director than a cinematographer. Both are real skills. Both make movies. They're not the same skill.

---

## The Vision

> "Babylon is a simulation and a work of art, an expression of how I see the world. It formalizes dialectical and historical materialism in the MLM-TW tradition through mathematical rigor, not through vibes-based prose and dense unreadable Hegelian jargon. Above all else it is political education through storytelling with an incredibly complex backend."

### The Phased Approach

1. **Vertical slice** (NOW) - Prove the backend and frontend connect, systems link together, what the player sees makes sense
2. **Horizontal expansion** (NEXT) - Flesh out the systems, add new mechanics
3. **AI narration** (THEN) - The storytelling layer
4. **The GUI** (FINALLY) - The childhood dream: a real program with windows and installers

### The North Star

> "A teenager picks it up, has fun, thinks it's cool, and learns how the world works."

That's when the art happens. Everything else is preparation.

---

## Advice for Future Sessions

1. **Ship something minimal** - Get the core loop playable. Observer patterns are nice but does someone play a turn and see results?

2. **Write some code yourself occasionally** - Not to prove anything, but to maintain the muscle. Pick a small feature, no AI, work through the frustration.

3. **Get external eyes** - Human code review, even informal. Solo development with AI that mostly agrees with you is an echo chamber.

4. **Question complexity** - Every System, every abstraction, every pattern has cost. Would simpler work?

5. **Validate the domain, not just the code** - Tests verify internal consistency. Who verifies the simulation produces historically plausible outcomes?

---

*The code exists because of human vision. AI is the keyboard that types fast.*

*Document created: 2025-12-26*
