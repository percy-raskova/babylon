# Babylon Epochs Overview

> **NOTE (2026-07-02)**: This file is the historical epoch vision. The
> **living roadmap** is `reports/aidocs-vs-code-audit-2026-05-16.md`
> (epoch-vs-code audit + 27-spec full-vision catalog) together with
> `ai/state.yaml`. Statuses below are updated at the table level only;
> per-slice detail in the epoch subdirectories is frozen at ~Jan 2026.

## The Four Epochs

| Epoch | Name | Theme | Status |
|-------|------|-------|--------|
| 1 | The Engine | "Graph + Math = History" | COMPLETE |
| 2 | The Foundation | "Real Data, Real Geography, Real Scale" | IN PROGRESS (2.6 PyQt slice OBSOLETE — React/Django/deck.gl shipped instead) |
| 3 | The Game | "From Theory to Strategy" | IN PROGRESS (substrate via specs 011-066; 3.9 Balkanization shipped as spec-070) |
| 4 | The Platform | "From Game to Engine" | VISION (DuckDB + ChromaDB plans superseded by Postgres 16 + pgvector, spec-037) |

## Epoch 1: The Engine (COMPLETE)

Validated core simulation mechanics:
- 13 deterministic Systems
- Survival calculus (P(S|A), P(S|R))
- Bifurcation formula
- DearPyGui dashboard

[Full documentation](./epoch1-complete.md)

## Epoch 2: The Foundation (IN PROGRESS)

Building infrastructure for continental scale:
- 3NF database schema (COMPLETE)
- 10+ API data loaders (COMPLETE)
- H3 hexagonal coordinates (PLANNED)
- PyQt + pydeck visualization (PLANNED)

[Full documentation](./epoch2/overview.md)

## Epoch 3: The Game (PLANNED)

Game features and mechanics:
- Demographics and population
- Vanguard resource economy
- Fog of war and information
- Kinetic warfare
- Balkanization

[Full documentation](./epoch3/overview.md)

## Epoch 4: The Platform (VISION)

Scaling to simulation platform:
- DuckDB migration
- RAG narrative generation
- Multi-scenario support
- API layer

[Full documentation](./epoch4/overview.md)
