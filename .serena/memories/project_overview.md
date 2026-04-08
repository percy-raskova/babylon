# Babylon - Project Overview

**Purpose**: Geopolitical simulation engine modeling the collapse of American hegemony through Marxist-Leninist-Maoist Third Worldist theory. Models class struggle as deterministic output of material conditions within a compact topological phase space.

**Tech Stack**:

- Python 3.12 (managed via `mise` / `poetry`)
- SQLite / Pydantic (The Ledger)
- NetworkX (The Topology)
- ChromaDB (The Archive)
- Node.js / Vite / React (Front-end interface)

**Architecture ("The Embedded Trinity")**:

- `src/babylon/data/game/` - JSON entity collections (state)
- `src/babylon/models/world_state.py` - NetworkX topology graph
- `src/babylon/rag/` - Semantic history
- **Engine**: Simulation runs via dependency injection, observer pattern, event bus (`src/babylon/engine/`). 17 primary formulas (`src/babylon/formulas/formulas.py`).
