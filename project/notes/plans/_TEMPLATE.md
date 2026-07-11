---
date: YYYY-MM-DD
author:
commit:
status: draft
---

# Plan: [Feature/Change Name]

## Goal

One sentence: what are we trying to accomplish?

## Context

Why is this needed? Link to related decisions/research if relevant.

## Approach

High-level strategy.

## Changes

### Phase 1: [Name]

Files to modify:

- `src/babylon/...` - what changes

Success criteria:

- [ ] `mise run check` passes
- [ ] `mise run test:unit` passes
- [ ] [specific behavior works]

### Phase 2: [Name]

...

## NOT Doing

## Explicitly out of scope:

-

## Open Questions

Resolve before implementing:

- \[ \]

## Success Criteria

Automated:

- [ ] `mise run check` passes (lint + format + typecheck + unit)
- [ ] `mise run test:int` passes (integration tests)
- [ ] `mise run qa:audit` shows healthy trajectory

Manual:

- [ ] [thing that requires human judgment]
