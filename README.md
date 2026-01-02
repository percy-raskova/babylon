# Babylon - The Fall of America

A geopolitical simulation engine modeling the collapse of American hegemony through Marxist-Leninist-Maoist Third Worldist (MLM-TW) theory.

**Mantra:** *Graph + Math = History*

## What Is This?

Babylon models class struggle as a deterministic output of material conditions within a compact topological phase space. It simulates imperial rent extraction, consciousness drift, solidarity transmission, and revolutionary rupture using NetworkX graphs and Pydantic-validated state.

The simulation runs locally without external servers, using the "Embedded Trinity" architecture:

- **The Ledger** (SQLite/Pydantic): Rigid material state
- **The Topology** (NetworkX): Fluid relational state
- **The Archive** (ChromaDB): Semantic history for AI narrative

## Quick Start

```bash
# Install dependencies
poetry install
poetry run pre-commit install

# Run tests (1500 tests)
poetry run pytest -m "not ai"

# Run simulation
poetry run python -m babylon
```

**Requirements:** Python 3.12+, Poetry

## Project Structure

```
src/babylon/
├── engine/          # Simulation engine (step function, systems, observers)
├── models/          # Pydantic entities (SocialClass, Territory, Relationship)
├── systems/         # Modular systems (survival, solidarity, contradiction)
├── rag/             # ChromaDB integration for semantic history
├── config/          # GameDefines, logging configuration
└── data/game/       # JSON entity definitions

tests/
├── unit/            # Fast deterministic tests
└── integration/     # Full simulation tests

ai-docs/             # Machine-readable YAML specifications
brainstorm/          # Design documents and mechanics specs
```

## Development

See [`CLAUDE.md`](CLAUDE.md) for comprehensive development guidelines including:

- Available commands (mise tasks, pytest markers)
- Architecture details
- Coding standards
- Mathematical core (Fundamental Theorem, Survival Calculus)

### Key Commands

```bash
mise run ci              # Quick CI: lint + typecheck + test-fast
mise run test            # All non-AI tests
mise run analyze-trace   # Single simulation with CSV output
mise run analyze-sweep   # Parameter sweep analysis
```

## Documentation

| Location                     | Content                                               |
| ---------------------------- | ----------------------------------------------------- |
| [`ai-docs/`](ai-docs/)       | YAML specs for engine systems, formulas, architecture |
| [`brainstorm/`](brainstorm/) | Design documents, mechanics specifications            |
| [`docs/`](docs/)             | Sphinx documentation (API reference)                  |

## Current State

**Phase 3: Narrative Layer** - Observer system implemented

Completed systems:

- Imperial Rent extraction (EXPLOITATION edges)
- Consciousness drift and bifurcation (George Jackson model)
- Solidarity transmission (SOLIDARITY edges)
- Survival calculus (P(S|A), P(S|R))
- Territory dynamics (heat, eviction, displacement)
- Agency layer (EXCESSIVE_FORCE → UPRISING)
- Topology monitoring (percolation, resilience testing)

## Contributing

We welcome contributions! This project uses the [Benevolent Dictator](https://producingoss.com/en/benevolent-dictator.html) governance model.

| Resource                           | Description                             |
| ---------------------------------- | --------------------------------------- |
| [SETUP_GUIDE.md](SETUP_GUIDE.md)   | Step-by-step setup for new contributors |
| [CONTRIBUTORS.md](CONTRIBUTORS.md) | Governance model and git workflow       |
| [CLAUDE.md](CLAUDE.md)             | Coding standards and architecture       |

**Quick Start for Contributors:**

```bash
git checkout dev
git checkout -b feature/your-feature
# Make changes, then PR to dev
```

## License

MIT License - see [LICENSE](LICENSE).

______________________________________________________________________

**Built With**

```
Claude Opus 4.5 🤝 Autistic Trans Woman = Coherent MLM-TW Simulation
```
