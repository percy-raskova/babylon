---
name: specification-discover
description: Decompose problems and check scope against Babylon's constitutional constraints. Use before planning to ensure work traces to test cases or improves falsifiability. Enforces scope control (Article VI) and prevents feature creep.
---

# Specification Discover Phase

## Purpose

Before planning any implementation, decompose the user's intent into its structural components and verify it survives scope control. This phase answers: **Should we do this at all?**

## Constitutional Constraints (P1)

- **VI.1 Material Base First** — Economic extraction → class formation → solidarity → THEN repression. Do not let the user jump ahead.
- **VI.2 Zoom Where Data Exists** — Resolution must match data availability. If the user wants county-level modeling but only has state-level data, flag it.
- **VI.3 Flag Scope Creep** — Every feature must trace to either: (a) a Detroit prediction, (b) a Michigan test case improvement, or (c) improved falsifiability. Otherwise DEFER.
- **I.20 Spatial Substrate** — Political claims overlay substrate; substrate is immutable. Any request implying substrate mutation must be rejected or escalated.

## Procedure

1. **Capture User Intent** — Restate what the user wants in your own words. Confirm with them before proceeding.

1. **Decompose into Components** — Break the intent into:

   - **Material basis**: What data/structural change is needed?
   - **Strategic intervention**: What organizing/verb mechanics are affected?
   - **Formal construct**: What tensor/graph/operator is involved?
   - **Test case impact**: Does this affect Michigan statewide (IV) or tri-county (IV.2)?

1. **Scope Control Check** — Answer these three questions:

   - Does this trace to a Detroit prediction or improve falsifiability? (VI.3)
   - Do we have data at the requested resolution? (VI.2)
   - Does the material base support this intervention? (VI.1)

   If any answer is NO, tell the user explicitly and ask if they want to:

   - Refine the scope to something tractable
   - Gather missing data first
   - Defer to a future sprint

1. **Identify Affected Principles** — Scan the constitution for principles this work would touch. List them explicitly. Examples:

   - "Transport system" → I.21 Sparrow, II.13 Transport Substrate, II.11 Subsystem Ownership
   - "New edge type" → I.6 Solidarity Edge Mode, II.9 Morphism Dyadic, II.7 Edges vs Hyperedges [TRANSITION STATE]

1. **Check for Transition State Dependencies** — If any affected principle is marked `[TRANSITION STATE]`, STOP. Do not proceed to plan. Tell the user: "This work depends on Amendment X (pending). Implementing now would produce provisional code that may need rewrite. Options: (a) wait for amendment, (b) scope around the transition state, (c) propose spec to resolve transition state."

1. **Output Discover Artifact** — Write a brief markdown file summarizing:

   - Confirmed intent
   - Component decomposition
   - Scope control verdict (PASS / DEFER / ESCALATE)
   - Affected principles
   - Transition state blockers (if any)
   - Recommended next phase

   Save to `.specify/discover/{YYYYMMDD}-{topic}.md` (create directory if needed).

## Escalation Rules

- If the user insists on scope that fails VI.3 → load `specification-govern`
- If the work requires a new primitive → load `specification-govern`
- If transition state blocker exists and user wants to proceed anyway → load `specification-govern`
