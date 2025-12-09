# Brainstorm

Ideas, designs, and plans for Babylon development.

## The Good Idea Fairy Protocol

**Problem:** Creative brains generate ideas faster than hands can implement.
**Solution:** Capture → Tag → Quarantine → Return to current task.

```
┌─────────────────────────────────────────────────────┐
│  IDEA APPEARS                                       │
│         ↓                                           │
│  Does it help pass the CURRENT failing test?        │
│         ↓                                           │
│    YES → Implement it                               │
│    NO  → Write ONE sentence in deferred-ideas.md    │
│         with a Phase tag, then STOP                 │
│         ↓                                           │
│  RETURN TO CURRENT TASK IMMEDIATELY                 │
└─────────────────────────────────────────────────────┘
```

**The Mantra:** Two nodes. One edge. Passing tests. Ship.

## Directory Structure

```
brainstorm/
├── plans/              # Approved roadmaps and blueprints
├── deferred-ideas.md   # THE PARKING LOT - ideas tagged by phase
├── *.md                # Ideas not yet ready for implementation
└── README.md
```

## Quarantine Zones

| Location | Purpose |
|----------|---------|
| `~/projects/game/notes/` | Raw AI chatlogs, unprocessed ideas, "shit out" zone |
| `brainstorm/deferred-ideas.md` | Processed ideas tagged with phase numbers |
| `brainstorm/*.md` | Developed brainstorms with detail |
| `brainstorm/plans/` | Approved roadmaps ready for implementation |

**Rule:** If it's not in `ai-docs/state.yaml:next_steps`, it belongs in quarantine.

## How to Use This Directory

1. **Capture ideas quickly** - Don't let good ideas evaporate
2. **Tag with Phase** - Phase 2? Phase 3+? "Never"?
3. **No pressure to implement** - Brainstorms can die without guilt
4. **Promote to plans/** - When a brainstorm becomes an approved roadmap
5. **Promote to docs/** - When implementation is complete

## File Format

```markdown
# Idea Title

**Status:** Brainstorm | Developing | Ready to Implement | Abandoned
**Phase:** 2 | 3 | 4+ | Never
**Created:** YYYY-MM-DD
**Core Insight:** One sentence capturing the "aha"

## The Concept
...

## Open Questions
...
```

## Approved Plans

| File | Status | One-liner |
|------|--------|-----------|
| [plans/four-phase-engine-blueprint.md](plans/four-phase-engine-blueprint.md) | **ACTIVE** | The 4-phase roadmap: Equations → Engine → AI → UI |
| [plans/phase2-game-loop-design.md](plans/phase2-game-loop-design.md) | **ACTIVE** | Data/Logic separation, WorldState, SimulationEngine |

## Deferred Ideas

| File | Purpose |
|------|---------|
| [deferred-ideas.md](deferred-ideas.md) | **THE PARKING LOT** - Good ideas waiting for their phase |

## Current Brainstorms

| File | Status | One-liner |
|------|--------|-----------|
| [minimum-playable-slice.md](minimum-playable-slice.md) | Superseded | Refined by four-phase blueprint |
| [gramscian-wiki-engine.md](gramscian-wiki-engine.md) | Deferred (Phase 4+) | Hegemony as wiki control |
| [rag-input-validation.md](rag-input-validation.md) | Ready (Phase 3) | RAG as semantic firewall for player input |
