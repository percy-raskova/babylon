# The Fall of Babylon

*The Fall of Babylon* is a text-based role-playing game (RPG) that simulates complex social, political, and economic systems using XML data structures and AI components. The game incorporates Marxist theory and dialectical materialism to model contradictions and societal changes.

## Table of Contents

- [The Fall of Babylon](#the-fall-of-babylon)
  - [Table of Contents](#table-of-contents)
  - [Quick Start](#quick-start)
  - [Documentation](#documentation)
  - [Introduction](#introduction)
  - [Project Structure](#project-structure)
  - [Game Mechanics](#game-mechanics)
  - [AI Integration](#ai-integration)
  - [Contributing](#contributing)
  - [License](#license)

## Quick Start

**New to Babylon?** Follow our step-by-step [Getting Started Guide](docs/diataxis/tutorials/getting-started.md)

**Want to contribute?** See the [Development Setup Guide](docs/diataxis/how-to/development-setup.md)

**Need help?** Check the [Troubleshooting Guide](docs/diataxis/how-to/troubleshooting.md)

## Documentation

Our documentation follows the [Diataxis framework](https://diataxis.fr/) for better organization:

### 📚 [**Tutorials**](docs/diataxis/tutorials/) - Learn by doing
- [Getting Started](docs/diataxis/tutorials/getting-started.md) - Install and run your first game
- [First Game Session](docs/diataxis/tutorials/first-game-session.md) - Complete gameplay walkthrough  
- [Basic Configuration](docs/diataxis/tutorials/basic-configuration.md) - Customize your setup

### 🛠️ [**How-to Guides**](docs/diataxis/how-to/) - Solve specific problems
- [Configure ChromaDB](docs/diataxis/how-to/configure-chromadb.md) - Set up vector database
- [Development Setup](docs/diataxis/how-to/development-setup.md) - Prepare for contributing
- [Troubleshooting](docs/diataxis/how-to/troubleshooting.md) - Fix common issues

### 📖 [**Reference**](docs/diataxis/reference/) - Look up details  
- [Configuration Reference](docs/diataxis/reference/configuration.md) - All settings explained
- [API Reference](docs/diataxis/reference/api/) - Technical specifications

### 💡 [**Explanation**](docs/diataxis/explanation/) - Understand concepts
- [Architecture Overview](docs/diataxis/explanation/architecture.md) - How Babylon is built
- [Design Philosophy](docs/diataxis/explanation/design-philosophy.md) - Why we made these choices
- [Dialectical Materialism in Gaming](docs/diataxis/explanation/dialectical-materialism.md) - Theory as game engine

➡️ **[Start with the complete documentation index](docs/diataxis/index.md)**

## Introduction

*The Fall of Babylon* aims to provide an immersive experience where players navigate a dynamically changing world shaped by their decisions and underlying societal contradictions. The game leverages AI for non-player character (NPC) behaviors and incorporates real-time metrics collection and analysis to enhance gameplay dynamics.

## Project Structure

- `docs/`: Documentation including:
  - [CHANGELOG](docs/CHANGELOG.md): Version history and updates
  - [TODO](docs/TODO.md): Planned features and improvements
  - [MECHANICS](docs/MECHANICS.md): Game mechanics documentation
  - [CHROMA](docs/CHROMA.md): ChromaDB integration details
  - [ERROR_CODES](docs/ERROR_CODES.md): Error handling system
  - [LOGGING](docs/LOGGING.md): Logging system documentation
  - [CONFIGURATION](docs/CONFIGURATION.md): Configuration guide
  - [ECONOMY](docs/ECONOMY.md): Economic system documentation
- `src/babylon/`: Main source code
  - `ai/`: AI components and ChromaDB integration
  - `census/`: Census data integration and API
  - `config/`: Configuration management
  - `core/`: Core game systems (contradictions, economy, politics)
  - `data/`: Data management and persistence
    - `xml/`: Game entity and mechanics definitions
    - `models/`: Data models and schemas
    - `chromadb/`: Vector database storage
  - `metrics/`: Performance and gameplay metrics collection
  - `utils/`: Utility functions and helpers
- `tests/`: Comprehensive test suite
  - `unit/`: Unit tests
  - `integration/`: Integration tests
  - `fixtures/`: Test data and fixtures
- `website/`: Game website and documentation
- `pyproject.toml`: Project configuration
- `logging.yaml`: Logging configuration

## Quick Installation

```bash
git clone https://github.com/bogdanscarwash/babylon.git
cd babylon
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m babylon
```

**For detailed installation instructions**, see the [Getting Started Tutorial](docs/diataxis/tutorials/getting-started.md).

**Having issues?** Check the [Troubleshooting Guide](docs/diataxis/how-to/troubleshooting.md).

## Game Mechanics

- **Contradiction Analysis System**: 
  - Advanced engine modeling societal contradictions
  - Network visualization of relationships
  - Real-time intensity tracking
  - Historical data analysis
- **Event Generation System**:
  - Procedural event generation
  - Dynamic consequence chains
  - Contradiction-based escalation
- **Economic System**:
  - Dynamic resource management
  - Market simulation
  - Supply chain modeling
- **Political Systems**:
  - Electoral processes
  - Policy implementation
  - Governance structures

For details, see [MECHANICS.md](docs/MECHANICS.md).

## AI Integration

### ChromaDB Vector Database

- **Entity Storage**: Efficient vector representations
- **Similarity Search**: Fast kNN queries
- **Persistence**: DuckDB+Parquet backend
- **Performance**:
  - Query response < 100ms
  - Memory optimization
  - Cache management
  - Automatic backups

### Metrics Collection

- Real-time performance monitoring
- Gameplay pattern analysis
- System resource tracking
- Cache performance optimization

### Current Features

- Entity embeddings via SentenceTransformer
- Contradiction relationship analysis
- Dynamic event generation
- Performance metrics collection
- Pre-embeddings system with:
  - Content preprocessing and normalization
  - Intelligent content chunking
  - Embedding cache management
  - Integration with lifecycle management

### Planned Features

- Enhanced NPC behaviors
- Advanced decision systems
- Natural language processing
- Dynamic world generation
- Context window management
- Priority queuing for object lifecycle

For implementation details, see [CHROMA.md](docs/CHROMA.md).

## Error Handling & Logging

### Error Management

- Structured error codes by subsystem
- Comprehensive error tracking
- Automatic error recovery
- Detailed error context

### Logging System

- JSON-structured logging
- Multiple log streams
- Automatic rotation
- Performance metrics
- Error context capture

For complete documentation:
- [ERROR_CODES.md](docs/ERROR_CODES.md)
- [LOGGING.md](docs/LOGGING.md)

## Contributing

Contributions welcome! Guidelines coming soon in CONTRIBUTING.md.

## License

MIT License - see [LICENSE](LICENSE).

For detailed progress and updates, see [CHANGELOG.md](docs/CHANGELOG.md).
