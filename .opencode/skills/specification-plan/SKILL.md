---
name: specification-plan
description: Generate implementation plans with design artifacts. Loads plan-template.md, enforces P0/P1 constitutional principles for the target domain. Produces architecture decisions with traceability to test cases.
---

# Specification Plan Phase

## Purpose

Transform a validated discovery artifact into a concrete implementation plan. This phase answers: **How will we build this?**

## Prerequisites

You MUST have completed `specification-discover` for this topic, OR the user provides a discover artifact. If neither exists, load `specification-discover` first.

## Constitutional Constraints (P1)

- **II.1 Partition Emergence** — The {Core, Periphery} × {Bourgeoisie, Proletariat} schema is a derived partition, not a primitive. Plans must not hardcode four-node assumptions.
- **II.2 Primitives vs Derived** — Store: dialectic poles, morphism graph, reproduction requirements. Compute: ValueTensor4x3, SNLT, Φ, r, etc. NEVER store derived quantities.
- **II.6 State is Data, Engine is Transformation** — World: frozen Pydantic model. Engine: pure `tick(world, actions) → (new_world, events)`. No DB I/O during tick.
- **II.9 Morphism as Dyadic Relation** — Five canonical relations: `feeds`, `constrains`, `transforms`, `contains`, `antagonizes`. No N-ary morphisms.
- **II.11 Subsystem Table Ownership** — Each subsystem owns its tables. Cross-subsystem reads via views/RPC/events only. Document coupling.
- **II.12 Matrix Representation Layer** — NetworkX (authoring) → scipy.sparse (computation) → operator algebra (truth). Never conflate layers.
- **III.1 No Magic Constants** — Every number traces to primitives or data sources.
- **III.2 Falsifiability Required** — Every formula defines prediction, null hypothesis, distinguishing observable, falsifying data.
- **IV Michigan Test Case** — The plan MUST specify how the implementation will be validated against the 83-county Michigan model.

## Procedure

1. **Read Discover Artifact** — Load `.specify/discover/{YYYYMMDD}-{topic}.md`. If missing, ask the user to provide it or run `specification-discover`.

1. **Load Plan Template** — Read `.specify/templates/plan-template.md`. Use its structure for the output.

1. **Architectural Design** — Propose:

   - **Data model changes**: New tables, fields, or graph structures. Specify subsystem ownership per II.11.
   - **Formula changes**: New or modified formulas. Include prediction, null hypothesis, and falsifying observable per III.2.
   - **System changes**: Which engine systems are affected. Maintain the system execution order: ImperialRent → Solidarity → Consciousness → Survival → Struggle → Contradiction → Territory → Metabolism.
   - **API changes**: New or modified interfaces. Ensure dyadic morphism constraints per II.9.

1. **Resolution Strategy** — For each design decision, document:

   - The options considered
   - The constitutional principles that constrain the choice
   - The selected option and rationale
   - Risks and mitigations

1. **Test Strategy** — Specify:

   - Unit tests (pytest, `@pytest.mark.math` for formulas)
   - Integration tests (mechanics & systems)
   - Scenario tests (Michigan statewide, tri-county backward-compat)
   - Falsifiability criteria (III.2)

1. **Output Plan Artifact** — Write the plan to `.specify/plans/{YYYYMMDD}-{topic}.md`. Include:

   - Summary
   - Goals & Non-Goals
   - Design (data model, formulas, systems, API)
   - Resolution strategy
   - Test strategy
   - Risks & Mitigations
   - Timeline (if applicable)
   - Affected constitutional principles

## Prohibitions

- Do NOT produce a plan for code that depends on a `[TRANSITION STATE]` principle.
- Do NOT hardcode the four-node schema as a primitive.
- Do NOT store derived quantities.
- Do NOT propose DB I/O during tick.

## Next Phase

After plan approval, the typical flow is `specification-specify` (API contracts) → `specification-build` (implementation). The user may skip `specify` for internal-only changes.
