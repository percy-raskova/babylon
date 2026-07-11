# Epoch 4: The Platform

**Status**: VISION
**Theme**: "From Game to Engine"

## Summary

Epoch 4 scales Babylon from a single-player game to a reusable simulation platform:
- DuckDB unification (Ledger + Topology in one database)
- RAG-powered narrative generation
- Multi-scenario parallel simulation
- API layer for external integrations

## Prerequisites

- Epoch 3 complete (full game feature set)
- Performance profiled at continental scale

## Slices

| Slice | Name | Description |
|-------|------|-------------|
| 4.1 | DuckDB Migration | Unify SQLite + NetworkX into DuckDB + DuckPGQ |
| 4.2 | Native H3 | Use DuckDB H3 extension for spatial queries |
| 4.3 | RAG Integration | ChromaDB narrative generation with Marxist corpus |
| 4.4 | Multi-Scenario | Parallel simulation branches, A/B testing |
| 4.5 | API Layer | REST/GraphQL API for simulation-as-service |
| 4.6 | Persistence | Save/load game state, checkpointing |

## Key Architectural Changes

### DuckDB Unification

Currently:
- SQLite for Ledger (cold storage)
- NetworkX for Topology (hot compute)
- Hydration/dehydration between layers

Target:
- DuckDB for both Ledger AND Topology
- DuckPGQ for native graph queries
- H3 extension for spatial operations
- Single database file, no layer translation
