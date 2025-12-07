# The Minimum Playable Slice

**Status:** Critical Priority
**Created:** 2024-12-07
**Core Insight:** Beautiful schemas don't make a game. Players do.

## The Problem

We have:
- 17 validated JSON entity collections
- 36 JSON Schema files
- Theoretical coherence that would make Gramsci weep
- Zero playable turns

The risk is **architecture astronautics**—endlessly refining the foundation while never building the house. Every schema improvement feels productive. But productivity without a game loop is just sophisticated procrastination.

## The Critique

### What We Have
```
✓ Data layer (Ledger)         - JSON files, schemas, validation
✓ Theoretical framework       - MLM-TW encoded in data structures
✓ AI documentation           - Machine-readable context
✓ Tooling                    - Migration, validation scripts
```

### What We Don't Have
```
✗ Game loop                  - No turn advances
✗ State mutation             - Nothing changes
✗ Player agency              - No decisions to make
✗ Win/lose conditions        - No stakes
✗ Any actual gameplay        - Nothing to play
```

### The Uncomfortable Truth

The data structures encode political economy beautifully. But political economy is about *dynamics*—how things change, how contradictions intensify, how ruptures occur. Static data, no matter how well-structured, doesn't demonstrate the theory.

**The fundamental theorem (W_c > V_c → no revolution) means nothing if we can't watch it play out.**

## The Prescription

### Vertical Slice, Not Horizontal Layer

Stop building out the full data model. Build a **complete vertical slice**:

```
One location (Detroit)
    ↓
Two factions (Auto Workers Union vs. Ford Corp)
    ↓
One contradiction (Capital vs. Labor)
    ↓
Ten turns of gameplay
    ↓
One possible rupture condition
```

Ugly. Incomplete. Hardcoded values where schemas should be. **But running.**

### The Minimum Game Loop

```python
def game_loop():
    state = load_initial_state()  # Just Detroit, two factions

    while not game_over(state):
        # 1. Display current state
        render(state)

        # 2. Player makes decision
        action = get_player_action(state)

        # 3. Apply action effects
        state = apply_action(state, action)

        # 4. Update contradictions
        state = update_contradictions(state)

        # 5. Check for events/rupture
        state = check_events(state)

        # 6. Advance turn
        state.turn += 1

    show_ending(state)
```

That's it. That's the skeleton. Everything else is flesh on bones.

### What "Playable" Means

The first playable version should answer ONE question:

> "Can I, as a player, make decisions that affect whether a strike succeeds or fails?"

Not "Can I simulate the entire collapse of American hegemony?"

One strike. One location. One decision tree. Does the contradiction intensify or resolve? Does the player's choice matter?

If yes → we have a game, now we scale it.
If no → we have a bug, now we fix it.

## Proposed Sprint

### Week 1: Skeleton
- [ ] `src/babylon/engine/game_loop.py` - The loop above, hardcoded
- [ ] `src/babylon/engine/state.py` - Minimal game state class
- [ ] `src/babylon/engine/actions.py` - 3-5 possible player actions
- [ ] Terminal output only (Rich library)

### Week 2: One Scenario
- [ ] Detroit location with two factions from existing data
- [ ] One contradiction (capital-labor) with intensity tracking
- [ ] Strike event that can trigger at high intensity
- [ ] Win condition: strike succeeds / lose condition: strike crushed

### Week 3: Connect to Data
- [ ] Load factions from `factions.json` instead of hardcoding
- [ ] Load contradiction from `contradictions.json`
- [ ] Effects actually modify state per schema definitions

### Week 4: Iterate
- [ ] Playtest with actual human
- [ ] What's confusing? What's boring? What's broken?
- [ ] Adjust based on feedback, not theory

## The Trap to Avoid

"But first we need to..."
- ✗ Finish all Pydantic models
- ✗ Implement the full Topology layer
- ✗ Set up ChromaDB properly
- ✗ Design the UI framework
- ✗ Complete the wiki engine

No. First we need **ten turns that someone can play**.

Everything else is in service of that. If a feature doesn't contribute to those ten turns, it waits.

## Success Criteria

The minimum playable slice is DONE when:

1. A human can start the game
2. See the state of Detroit (factions, tension, resources)
3. Choose an action (organize workers, negotiate, repress, etc.)
4. Watch the contradiction intensity change
5. Experience an event triggered by intensity threshold
6. Reach an ending (strike succeeds/fails)
7. Want to play again with different choices

That's it. Everything else is scope creep until this exists.

## The Mantra

> "Schemas don't ship. Game loops do."

Write it on a sticky note. Put it on the monitor.

---

*This document exists to counterbalance the theoretical ambition with engineering pragmatism. Both are necessary. Neither is sufficient alone.*
