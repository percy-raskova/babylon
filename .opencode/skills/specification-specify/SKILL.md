---
name: specification-specify
description: Write API contracts and interface specifications. Ensures all interfaces conform to dyadic morphism constraints and subsystem ownership boundaries. Produces machine-readable specs validated against the constitution.
---

# Specification Specify Phase

## Purpose

Define precise contracts for all interfaces introduced in the plan. This phase answers: **What are the exact boundaries?**

## Prerequisites

You MUST have a ratified plan artifact at `.specify/plans/{YYYYMMDD}-{topic}.md`. If missing, load `specification-plan` first.

## Constitutional Constraints (P1)

- **II.9 Morphism as Dyadic Relation** — All inter-component contracts are dyadic: source → target with typed relation and weight. Five canonical relations: `feeds`, `constrains`, `transforms`, `contains`, `antagonizes`.
- **II.11 Subsystem Table Ownership** — Interface contracts MUST specify which subsystem owns each data structure and how cross-subsystem access occurs (views, RPC, events).
- **II.8 Client as Presentation Layer** — `observe()` output is the durable contract. Frontend is disposable. JSON at every boundary.
- **III.7 Determinism Hash** — Every tick produces a deterministic hash. Interfaces that affect tick inputs or outputs MUST preserve this invariant.
- **III.8 Structural Provenance** — Every formal construct in the spec MUST name the material process it represents.

## Procedure

1. **Read Plan Artifact** — Load `.specify/plans/{YYYYMMDD}-{topic}.md`. Identify all interfaces that need specification.

1. **Load Spec Template** — Read `.specify/templates/spec-template.md`. Use its structure.

1. **Define Interface Contracts** — For each interface:

   - **Name and purpose**
   - **Input schema**: Pydantic models, types, constraints
   - **Output schema**: Pydantic models, types, constraints
   - **Error conditions**: ValidationError types, error messages
   - **Morphism relation**: Which canonical relation (`feeds`, `constrains`, etc.) this interface represents
   - **Subsystem ownership**: Which subsystem owns the data; how cross-subsystem reads occur
   - **Determinism impact**: Does this interface affect tick hash? How?

1. **Define Data Contracts** — For new or modified data structures:

   - **Pydantic model definition** with constrained types (Probability, Currency, Intensity, etc.)
   - **JSON Schema** for validation
   - **Migration strategy** if modifying existing structures
   - **Fixture vs runtime** classification per III.4

1. **Define Event Contracts** — If the plan introduces new events:

   - Event type enum value
   - Payload schema
   - Publisher and subscriber subsystems
   - Ordering guarantees

1. **Validate Against Constitution** — Check each contract against:

   - Dyadic morphism constraint (II.9)
   - Subsystem ownership (II.11)
   - Determinism hash (III.7)
   - Aleksandrov Test (III.8) — can you name the material process?

1. **Output Spec Artifact** — Write to `.specify/specs/{NNN}-{topic}/spec.md` (find next available NNN). Include:

   - Status: DRAFT → REVIEW → RATIFIED
   - Interface contracts
   - Data contracts
   - Event contracts
   - Constitutional compliance checklist
   - Open questions

## Prohibitions

- Do NOT define N-ary morphism interfaces.
- Do NOT leave subsystem ownership ambiguous.
- Do NOT define interfaces that would break determinism hash.
- Do NOT use raw dicts — all data structures MUST be Pydantic models.

## Next Phase

After spec ratification, proceed to `specification-build`. The user may iterate between `specify` and `plan` if issues are found.
