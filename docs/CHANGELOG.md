# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Sprint 3.7: Carceral Geography
- Implemented Carceral Geography in TerritorySystem for detention and displacement routing
- Added dynamic displacement priority modes (LABOR_SCARCE, BALANCED, ELIMINATION)
- Displacement routing: detention → incarceration → elimination/expulsion pipeline

#### Sprint 3.1: Observer Layer
- Implemented TopologyMonitor for condensation detection using percolation theory
- Added TopologySnapshot and ResilienceResult Pydantic models
- Narrative logging: gaseous state, phase shift, brittle movement, Sword of Damocles alerts
- Added observer-layer.yaml with Bondi Algorithm aesthetic documentation

#### Agency Layer
- Added StruggleSystem for agency-based responses (EXCESSIVE_FORCE → UPRISING)
- Implemented George Jackson bifurcation model for consciousness drift
- Replaced IdeologicalComponent with empirically-validated bifurcation mechanics

#### Parameter Analysis Tools
- Added `mise run analyze-trace` for single simulation time-series CSV output
- Added `mise run analyze-sweep` for parameter sweep analysis
- Created parameter_analysis.py tool for sensitivity analysis

#### Configuration
- Centralized game coefficients in GameDefines (Pydantic model)
- Added centralized logging configuration in pyproject.toml
- Completed Paradox Refactor: externalized all game coefficients

### Fixed
- Fixed wage calculation to use tribute flow instead of accumulated wealth
- Fixed RAG system to include embeddings in vector store query results
- Fixed create_two_node_scenario unpacking (returns 3 values)

### Changed
- Updated README for accuracy and truthfulness
- Documentation cleanup: removed obsolete files, updated Project-Structure

### Documentation
- Added ai-docs/observer-layer.yaml with Bondi Algorithm narrative style
- Added ai-docs/agency-layer.yaml
- Added ai-docs/carceral-geography.yaml
- Added empirical validation to George Jackson bifurcation model docs
- Updated balance-tuning registry with sweep findings

---

## [0.2.0] - 2024-12-11

### Added
- Complete simulation engine with modular Systems architecture
- Six core systems: Economic, Ideology, Solidarity, Survival, Contradiction, Territory
- Formula system with 12 hot-swappable formulas
- SimulationObserver protocol for extensible monitoring
- Dependency injection via ServiceContainer
- Event-based architecture with EventBus

### Architecture
- Embedded Trinity: Ledger (SQLite/Pydantic), Topology (NetworkX), Archive (ChromaDB)
- WorldState with to_graph()/from_graph() serialization
- Pydantic models with constrained types (Probability, Currency, Intensity)

---

## [0.1.0] - 2024-11-30

### Added
- Initial project structure and Poetry configuration
- Basic Pydantic models for game entities
- ChromaDB integration for vector storage
- Initial test suite

---

To maintain this changelog, document changes in the "Unreleased" section upon committing. Before a release, move entries to a new version section with the release date.
