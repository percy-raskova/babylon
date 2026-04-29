---
description: Babylon specification workflow gate. Enters the skill-based governance workflow for planning, specifying, building, validating, and governing code changes against the Babylon Constitution.
---

## Specification Workflow Entry

You are entering the Babylon **specification** skill-based workflow. This replaces the legacy slash-command pipeline with a unified, context-retaining governance system.

### Your Job

1. **Ask the user what they want to work on.**
1. **Determine the appropriate phase** from the six-phase workflow below.
1. **Load the corresponding skill** via the `skill` tool. The available skills are:
   - `specification-discover` — Problem decomposition and scope control
   - `specification-plan` — Design artifacts and implementation planning
   - `specification-specify` — API contracts and interface definitions
   - `specification-build` — TDD implementation and code generation
   - `specification-validate` — Tests, checklists, and acceptance criteria
   - `specification-govern` — Constitutional compliance and amendment review
1. **Execute the loaded skill** and follow its instructions exactly.
1. **When complete, ask:** "Continue to next phase, revisit a previous phase, or exit?"

### Phase Selection Guide

| User says...                                                                 | Phase                         |
| ---------------------------------------------------------------------------- | ----------------------------- |
| "I want to add X", "build Y", "implement Z"                                  | `discover` first, then `plan` |
| "Design the API for...", "How should we structure..."                        | `plan`                        |
| "Write the spec for...", "Define the interface..."                           | `specify`                     |
| "Write the code for...", "Implement..."                                      | `build`                       |
| "Test this...", "Verify...", "Checklist for..."                              | `validate`                    |
| "Does this violate...", "Amendment needed...", "Review against constitution" | `govern`                      |

### Constitutional Awareness

Before loading any skill, verify the user is not asking you to:

- Mutate spatial substrate (I.20)
- Let AI adjudicate engine state (II.5)
- Implement code depending on a `[TRANSITION STATE]` principle
- Invent a new primitive without amendment

If any apply, load `specification-govern` instead of the inferred phase.

### Legacy Commands

The old slash commands (`/speckit.plan`, `/speckit.specify`, etc.) still exist and are independent. Do not reference them unless the user explicitly asks.
