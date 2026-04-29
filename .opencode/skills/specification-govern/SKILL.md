---
name: specification-govern
description: Review work for constitutional compliance. Propose amendments when primitives or prohibitions are affected. Checks against amendment registry and enforces the AI Decision Procedure (IX.3). Final gate before merge.
---

# Specification Govern Phase

## Purpose

Audit any work — plan, spec, implementation, or validation — for constitutional compliance. Propose amendments when necessary. This phase answers: **Are we allowed to do this?**

## When to Use

Load this skill when:

- The user asks "does this violate the constitution?"
- The user wants to add/redefine/remove a primitive
- The user wants to relax a prohibition (e.g., allow substrate mutation)
- The user wants to introduce a formalism that may fail the Aleksandrov Test
- A `[TRANSITION STATE]` principle is blocking work and the user wants resolution
- Any phase encounters a constitutional conflict and cannot proceed

## Constitutional Constraints (P0 + P1)

### P0 (Never Drop)

- **I.19 Dialectic Primitive** — `D = (A, Ā, w, T, σ)` is irreducible. No redefinition without MAJOR version bump.
- **I.20 Spatial Substrate** — Immutable. No mutation ever.
- **II.9 Morphism Dyadic** — Strictly dyadic. No N-ary morphisms.
- **III.7 Determinism Hash** — Every tick deterministic. Non-determinism is a bug.
- **III.8 Aleksandrov Test** — Every formal construct traces to material relation.
- **V Verb Atomicity** — Every verb maps to graph operation. Atomic per target instance.

### P1

- **IX.2 Staged Amendment Series** — Primitive changes require downstream translation with invariance proofs. No skipping.
- **IX.3 AI Decision Procedure** — Read-and-Proceed → Read-and-Ask → Escalate → Transition-State-Protocol.
- **IX.4 AI Context Budget** — P0 immutable, P1 domain-mandatory, P2 droppable-with-reporting.

## AI Decision Procedure (IX.3)

Follow this escalation ladder exactly:

### 1. Read and Proceed

If the constitution provides an unambiguous constraint that answers the question, apply it without asking for clarification.

Examples:

- "Can we delete a county from the substrate?" → Banned per I.20. Reject immediately.
- "Should Investigate mutate the graph?" → Required per V. Proceed.

### 2. Read and Ask

If the constitution constrains the shape but not the content, consult the relevant spec before proceeding.

Examples:

- "What's the cost function for AIR_LINK transport?" → II.13 defines types but not costs. Read transport spec.
- "How does Educate create centrality?" → I.21 defines modes but not graph operation. Read verb spec.

### 3. Escalate to Amendment

If the question requires any of:

- Adding a new primitive (new pole type, new morphism relation, new transport edge type not in II.13)
- Redefining an existing primitive (changing dialectic structure in I.19)
- Relaxing a prohibition (allowing substrate mutation despite I.20)
- Introducing a formalism that fails Aleksandrov Test (III.8)

Then: STOP. Propose a constitutional amendment. Include:

- The problem
- Proposed principle text
- Principles affected
- Draft invariance proof
- Version bump rationale (MAJOR/MINOR/PATCH)

### 4. Transition State Protocol

If a principle is marked `[TRANSITION STATE]`, treat it as blocked.

You MAY propose a spec to resolve the transition state.
You MUST NOT implement code that depends on the unresolved principle.

Examples:

- II.7 (hyperedges) is transition state → Do not implement hyperedge logic until Amendment D ratified.
- I.17 (OODA) is transition state → Do not implement OODA profiles until Amendment C ratified.

## Amendment Proposal Format

If escalation is required, draft an amendment following this structure:

```
**Amendment [Next Letter] — [Title]**
Status: PROPOSED
Target Version: [e.g., v2.8.0]
Bump: [MAJOR/MINOR/PATCH]

**Problem:**
[What problem does this solve?]

**Proposed Principle:**
[Exact text of the new/modified principle]

**Affected Principles:**
- [List all downstream principles that must be translated]

**Invariance Proof (Draft):**
[Demonstrate that affected principles are at least as constrained as predecessors]

**Consequences:**
- Positive: [Benefits]
- Negative: [Tradeoffs]
```

Save to `.specify/memory/constitution.md` as a PROPOSED amendment in the IX.2 registry. Do NOT bump the version until ratified.

## Compliance Audit Checklist

For any work under review, verify:

- [ ] No substrate mutation
- [ ] No AI adjudication (AI only parses/narrates)
- [ ] No ungrounded tensor notation
- [ ] No fixture/runtime substitution
- [ ] No transition-state dependency in implementation
- [ ] Determinism hash preserved
- [ ] Aleksandrov Test passed for all new formal constructs
- [ ] Dyadic morphism constraint respected
- [ ] Subsystem ownership documented
- [ ] Falsifiability criteria defined for all new formulas
- [ ] Michigan test case traceability documented

If any unchecked, flag the defect and recommend remediation or amendment.

## Next Phase

Govern is typically terminal. After compliance review, the work either:

- **PASSES** → ready for merge (user's discretion)
- **FAILS** → return to appropriate phase with remediation instructions
- **REQUIRES AMENDMENT** → amendment proposal drafted, awaiting ratification
