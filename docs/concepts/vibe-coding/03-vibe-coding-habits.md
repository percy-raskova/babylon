# Part III: The User's Vibe Coding Habits

## Burst Development Patterns

The git log reveals a distinctive pattern: periods of intense activity followed by silence, then another burst. This isn't poor time management—it's how creative work actually happens.

**Phase 1 (Nov 30 - Dec 3, 2024):** Initial burst. 310 commits. Project scaffolding, data migration, core architecture. The foundation poured in 4 days.

**Phase 2 (Dec 4-16, 2024):** Consolidation. 87 commits. Feature development, bug fixes, test coverage. Building on the foundation.

**Phase 3 (Dec 17, 2024 - Dec 6, 2025):** Dormancy with sporadic activity. 4 commits total. Life happens.

**Phase 4 (Dec 7-11, 2025):** Revival burst. 140 commits. Major features: Carceral Geography, Observer Layer, Parameter Analysis. The project comes alive again.

This pattern makes sense when you understand vibe coding. The setup cost is high: loading context, remembering where you left off, getting back into flow. Once in flow, staying there is valuable. Traditional development, with its interruption-tolerant workflow, doesn't require this intensity. Vibe coding does.

## The Good Idea Fairy Protocol

One of the hardest challenges in any project is idea management. You're implementing feature X when suddenly you think of feature Y. Traditional approaches: write it down and forget about it, or get derailed implementing Y when X isn't done.

The Babylon project uses what's documented as the "Good Idea Fairy Protocol":

```markdown
# From brainstorm/deferred-ideas.md

**Purpose:** This is where good ideas come to WAIT, not die.
Everything here is valuable but NOT part of the current sprint.

**Rule:** If you're tempted to implement something from this list,
ask: "Does it help pass the current failing test?"

## Phase 4+: Control Room & Beyond

### Procedural MIDI Soundtrack
**Source:** Good Idea Fairy 2025-12-08
**What it does:** Programmatically generate music based on game state
**Why wait:** Pure polish, requires working game loop and UI first
```

The deferred ideas file has 159 lines of structured ideas, each tagged with:

- Source (where the idea came from)
- What it does
- Why we're waiting
- Which phase it belongs to

This is idea management that works *with* vibe coding rather than against it. The flow doesn't get interrupted because there's a trusted place for the interrupting thought. You can note "Procedural MIDI Soundtrack" and immediately return to the failing test, knowing the idea is preserved.

## Theory-First Implementation

The Babylon project implements MLM-TW (Marxist-Leninist-Maoist Third Worldist) theory as game mechanics. This isn't retrofitting theory onto code—it's implementing theory *as* code. The mathematical formulas exist in academic papers; the code translates them:

```python
# From src/babylon/systems/formulas.py

def calculate_consciousness_drift(
    wage: Currency,
    value_produced: Currency,
    current_consciousness: Ideology,
    k: float = 0.1,
    lambda_decay: float = 0.02,
) -> float:
    """
    Calculate consciousness drift based on material conditions.

    Implements: dΨc/dt = k(1 - Wc/Vc) - λΨc

    Where:
    - Ψc: class consciousness
    - Wc: wages received
    - Vc: value produced
    - k: sensitivity to exploitation
    - λ: decay rate (false consciousness effect)

    Returns positive when W < V (exploited → revolutionary)
    Returns negative when W > V (labor aristocracy → reactionary)
    """
```

The docstring IS the theory. The code IS the implementation. The tests VERIFY both. This is theory-driven development: you don't write code and then justify it with theory. You have theory, and the code's job is to encode it faithfully.

## Context Management via claude-mem

One of the biggest challenges in AI-assisted development is context. AI models don't remember previous sessions. Every conversation starts fresh. This would be crippling for a complex project—except we've solved it.

The Babylon project uses claude-mem, a persistent memory system that captures:

- Session summaries
- Architectural decisions
- Bug fixes and their causes
- Implementation patterns
- Project state

Over 100+ sessions, the memory has accumulated thousands of observations. When starting a new session, the system provides context about recent work, key decisions, and project state. The AI doesn't have to rediscover what we learned yesterday—it can read what we documented.

Here's a sample of what gets captured:

```
**#6270** 11:58 AM [FEAT] **Created Comprehensive Architecture Documentation**
The architecture.rst documentation was created for the Babylon project's
Sphinx documentation system. This file provides a comprehensive overview
of the "Embedded Trinity" architecture consisting of three integrated layers:
The Ledger (SQLite/Pydantic for rigid economic state), The Topology
(NetworkX for fluid relational state), and The Archive (ChromaDB for
semantic memory and AI narrative generation).
```

This is memory as infrastructure. The AI's amnesia is compensated by the system's memory. Each session builds on the previous, not because the AI remembers, but because we've built a system that remembers for it.
