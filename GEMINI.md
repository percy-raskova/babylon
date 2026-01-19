# Babylon - The Fall of America

## Project Overview

**Babylon** is a geopolitical simulation engine that models the collapse of
American hegemony through the lens of Marxist-Leninist-Maoist Third Worldist
(MLM-TW) theory.
**Mantra:** *Graph + Math = History*

The simulation runs locally using the "Embedded Trinity" architecture:

1. **The Ledger** (SQLite/Pydantic): Rigid material state.
1. **The Topology** (NetworkX): Fluid relational state.
1. **The Archive** (ChromaDB): Semantic history for AI narrative.

## Technical Architecture

### Tech Stack

- **Language:** Python 3.12+
- **Dependency Management:** Poetry
- **Data Validation:** Pydantic v2
- **Graph Theory:** NetworkX
- **Vector Database:** ChromaDB
- **Testing:** Pytest, Hypothesis
- **Linting/Formatting:** Ruff, Mypy

### Directory Structure

- `src/babylon/`: Main source code.
  - `engine/`: Simulation engine (step function, systems, observers).
  - `models/`: Pydantic entities (SocialClass, Territory, Relationship).
  - `systems/`: Modular systems (survival, solidarity, contradiction).
  - `rag/`: ChromaDB integration.
- `ai-docs/`: **CRITICAL RESOURCE.** Machine-readable YAML specifications for architecture, systems, and theory.
- `tests/`: Unit and integration tests.
- `tools/`: Utility scripts.

## Getting Started

### Installation

```bash
poetry install
poetry run pre-commit install
```

### Running the Simulation

```bash
poetry run python -m babylon
```

### Running Tests

The project has a robust test suite (1500+ tests).

```bash
# Run all non-AI tests (fastest)
poetry run pytest -m "not ai"

# Run specific markers
poetry run pytest -m unit      # Fast unit tests
poetry run pytest -m integration # Database/IO tests
poetry run pytest -m math      # Deterministic formulas
```

## Development Workflow

### Key Tools

- **Mise**: Task runner (see `mise.toml`).
  - `mise run ci`: Run full CI suite (lint + typecheck + test-fast).
  - `mise run test`: Run standard tests.
- **Pre-commit**: Enforces standards on commit.

### Standards

- **Coding Style:** Follows `ruff` configuration (line length 100).
- **Typing:** Strict `mypy` compliance is required.
- **Commits:** Conventional Commits format (e.g., `feat: ...`, `fix: ...`).

## Documentation Resources

- `ai-docs/README.md`: Entry point for AI understanding.
- `ai-docs/state.yaml`: Current project state and test counts.
- `ai-docs/architecture.yaml`: Technical stack details.
- `ai-docs/epochs/`: Roadmap and specifications for current/future work.
- `CLAUDE.md`: Comprehensive development guidelines and anti-patterns.

## Current Status

**Phase:** Epoch 2 (The Foundation) - In Progress.
**Focus:** Data infrastructure, H3 geographic system, PyQt visualization.
**Completed:** Epoch 1 (The Engine) - Core systems, economic flow, survival calculus.
